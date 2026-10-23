# =============================================================================
# URTC-TESTER - tester_plan.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Test plans: a short list of steps run against a tool head, with a result that can be checked afterwards.

A plan is a JSON file (``format`` 1): a ``name``, an optional ``description``, an optional ``actuation`` switch and a list
of ``steps``. Each step has a ``do`` and the fields that kind needs:

========== ==================================================================================================
expect_tool    ``tool``: the active tool answers 0x111 with this tool id
check_faults   the quick state (0x111) reports no system error, no CAN error, no thermal fault
query_version  0x7F8: the application answers; optional ``min_version`` (``"0.3.5"``) and ``hardware_id`` (``"0x0303CC01"``)
selftest       the at-rest communication check of the tool that answers (the one of the deck)
send           ``id`` and ``data`` (hex, up to 8 bytes); a read-only query is always allowed, any other frame needs the
               plan's ``"actuation": true`` and the operator's ``--allow-actuation``; the boot-loader, configuration and
               erase frames are never allowed
expect_frame   ``id``, ``within_ms`` (default 500); optional ``length`` and ``value`` (``offset``, ``width``, ``min``,
               ``max``: an unsigned big-endian field) of a frame that arrives after the last ``send``
wait           ``ms``: the frames keep being collected
confirm        ``text``: a person says that what they see is right
========== ==================================================================================================

Nothing here knows about a window or a command line: the runner gets a transport, an operator callback and a clock. After a
plan that sent anything beyond a query, every output is switched off again (the same "all off" frames as the deck).
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import advanced_protocol as protocol
import tester_selftest
from tester_config import TOOL_NAMES
from urtc_can import protocol as wire
from urtc_can.quick_state import decode as decode_quick_state
from urtc_can.versioning import parse_version_answer

PLAN_FORMAT = 1
MAX_STEPS = 200
MAX_WAIT_MS = 60000
DEFAULT_WITHIN_MS = 500
NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
VERSION_PATTERN = re.compile(r"\d{1,5}\.\d{1,3}(\.\d{1,3})?")

PASS, FAIL, ERROR, SKIPPED = "pass", "fail", "error", "skipped"

# Queries: the board answers and nothing changes. A plan may send these without any switch.
READ_ONLY_IDS = frozenset({
    wire.CAN_ID_QUERY_ACTIVE_TOOL, wire.CAN_ID_QUERY_VERSION, wire.CAN_ID_QUERY_ERROR_COUNTERS, wire.CAN_ID_FRAM_QUERY,
    wire.CAN_ID_SOLDER_FEEDER_POS, wire.CAN_ID_EXPANSION_DIAG0_REQ, wire.CAN_ID_THERMAL_STATS_QUERY,
    0x1A1, 0x1A3, 0x1A5, 0x1A7, 0x1A8, 0x1AD, 0x1AF, 0x1BA, 0x242, 0x251,
})
# Frames a plan never sends: the boot-loader and update protocol, the writes that change what the board is or stores, the
# slave link, and the two magic-payload commands that erase or reset something.
FORBIDDEN_IDS = frozenset(
    set(range(0x7F0, 0x800)) | set(range(0x210, 0x230)) | {0x131, 0x192, 0x1A0, 0x1A2, 0x1A4, 0x1A6, 0x1AC, 0x1AE}
)

STEP_FIELDS = {
    "expect_tool": ({"tool"}, {"tool"}),
    "check_faults": (set(), set()),
    "query_version": (set(), {"min_version", "hardware_id"}),
    "selftest": (set(), set()),
    "send": ({"id", "data"}, set()),
    "expect_frame": ({"id"}, {"within_ms", "length", "value"}),
    "wait": ({"ms"}, set()),
    "confirm": ({"text"}, set()),
}
COMMON_STEP_FIELDS = {"do", "label"}


class PlanError(ValueError):
    pass


@dataclass
class StepResult:
    index: int
    kind: str
    label: str
    outcome: str
    message: str


@dataclass
class PlanReport:
    name: str
    outcome: str = PASS
    steps: list[StepResult] = field(default_factory=list)
    firmware_version: str = ""
    tool_id: int | None = None
    trace: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        counts = {key: sum(1 for s in self.steps if s.outcome == key) for key in (PASS, FAIL, ERROR, SKIPPED)}
        return f"{self.outcome.upper()}: {counts[PASS]} passed, {counts[FAIL]} failed, {counts[ERROR]} errors, {counts[SKIPPED]} skipped"

    def log_text(self, plan_name: str | None = None) -> str:
        lines = [f"URTC Tester plan log - {plan_name or self.name}"]
        lines += [f"note: {n}" for n in self.notes]
        lines += self.trace
        lines += [f"STEP {s.index} {s.kind} {s.outcome.upper()} {s.message}" for s in self.steps]
        lines.append(self.summary())
        return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------------------------------------------------
# reading and checking a plan
# ---------------------------------------------------------------------------------------------------------------------
def load_plan(path: str | Path) -> dict:
    try:
        text = Path(path).read_text(encoding="utf-8")
        plan = json.loads(text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PlanError(f"cannot read the plan {path}: {exc}") from exc
    problems = validate_plan(plan)
    if problems:
        raise PlanError("the plan is not valid: " + "; ".join(problems))
    return plan


def _parse_id(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        number = value
    elif isinstance(value, str) and re.fullmatch(r"(0[xX][0-9A-Fa-f]{1,3}|\d{1,4})", value.strip()):
        number = int(value.strip(), 0)
    else:
        return None
    return number if 0 <= number <= 0x7FF else None


def _parse_data(value: object) -> bytes | None:
    if not isinstance(value, str):
        return None
    text = value.replace(" ", "")
    if len(text) % 2 or len(text) > 16 or not re.fullmatch(r"[0-9A-Fa-f]*", text):
        return None
    return bytes.fromhex(text)


def _version_tuple(text: str) -> tuple[int, int, int]:
    parts = [int(p) for p in text.split(".")]
    return parts[0], parts[1], parts[2] if len(parts) > 2 else 0


def validate_plan(plan: object) -> list[str]:
    """Every problem of a plan, as text; an empty list means the plan can be run."""
    problems: list[str] = []
    if not isinstance(plan, dict):
        return ["the plan must be a JSON object"]
    unknown = set(plan) - {"format", "name", "description", "actuation", "steps"}
    if unknown:
        problems.append(f"unknown plan fields: {', '.join(sorted(unknown))}")
    if plan.get("format") != PLAN_FORMAT:
        problems.append(f"format must be {PLAN_FORMAT}")
    name = plan.get("name")
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        problems.append("name must be 1 to 64 letters, digits, '.', '_' or '-' (it names the result files)")
    if "description" in plan and not isinstance(plan["description"], str):
        problems.append("description must be text")
    if "actuation" in plan and not isinstance(plan["actuation"], bool):
        problems.append("actuation must be true or false")
    steps = plan.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
        problems.append(f"steps must be a list of 1 to {MAX_STEPS} steps")
        return problems
    for number, step in enumerate(steps, start=1):
        where = f"step {number}"
        if not isinstance(step, dict):
            problems.append(f"{where}: must be an object")
            continue
        kind = step.get("do")
        if kind not in STEP_FIELDS:
            problems.append(f"{where}: unknown 'do' {kind!r}")
            continue
        required, optional = STEP_FIELDS[kind]
        missing = required - set(step)
        extra = set(step) - required - optional - COMMON_STEP_FIELDS
        if missing:
            problems.append(f"{where} ({kind}): missing {', '.join(sorted(missing))}")
        if extra:
            problems.append(f"{where} ({kind}): unknown fields {', '.join(sorted(extra))}")
        if "label" in step and (not isinstance(step["label"], str) or len(step["label"]) > 80):
            problems.append(f"{where}: label must be text of at most 80 characters")
        problems += _validate_step(where, kind, step, plan.get("actuation") is True)
    return problems


def _validate_step(where: str, kind: str, step: dict, plan_actuates: bool) -> list[str]:
    problems: list[str] = []
    if kind == "expect_tool" and step.get("tool") not in TOOL_NAMES:
        problems.append(f"{where}: tool must be one of the tool ids 0 to {max(TOOL_NAMES)}")
    if kind == "query_version":
        if "min_version" in step and not (isinstance(step["min_version"], str) and VERSION_PATTERN.fullmatch(step["min_version"])):
            problems.append(f"{where}: min_version must look like 0.3 or 0.3.5")
        if "hardware_id" in step and not (isinstance(step["hardware_id"], str) and re.fullmatch(r"0[xX][0-9A-Fa-f]{1,8}", step["hardware_id"])):
            problems.append(f"{where}: hardware_id must look like 0x0303CC01")
    if kind == "send":
        can_id, data = _parse_id(step.get("id")), _parse_data(step.get("data"))
        if can_id is None:
            problems.append(f"{where}: id must be a CAN identifier (0 to 0x7FF)")
        elif can_id in FORBIDDEN_IDS:
            problems.append(f"{where}: 0x{can_id:03X} is never sent by a plan (boot-loader, update, configuration or erase frame)")
        elif can_id not in READ_ONLY_IDS and not plan_actuates:
            problems.append(f"{where}: 0x{can_id:03X} is not a query; a plan that sends it must say \"actuation\": true")
        if data is None:
            problems.append(f"{where}: data must be hex text of at most 8 bytes")
    if kind == "expect_frame":
        if _parse_id(step.get("id")) is None:
            problems.append(f"{where}: id must be a CAN identifier (0 to 0x7FF)")
        within = step.get("within_ms", DEFAULT_WITHIN_MS)
        if isinstance(within, bool) or not isinstance(within, int) or not 1 <= within <= MAX_WAIT_MS:
            problems.append(f"{where}: within_ms must be 1 to {MAX_WAIT_MS}")
        if "length" in step and (isinstance(step["length"], bool) or not isinstance(step["length"], int) or not 0 <= step["length"] <= 8):
            problems.append(f"{where}: length must be 0 to 8")
        value = step.get("value")
        if "value" in step:
            ok = isinstance(value, dict) and set(value) <= {"offset", "width", "min", "max"} and {"offset", "width"} <= set(value)
            ok = ok and all(isinstance(value[k], int) and not isinstance(value[k], bool) for k in value)
            ok = ok and 0 <= value.get("offset", -1) <= 7 and 1 <= value.get("width", 0) <= 4 and value["offset"] + value["width"] <= 8
            ok = ok and ("min" in value or "max" in value)
            if not ok:
                problems.append(f"{where}: value needs offset (0-7), width (1-4) and a min and/or max")
    if kind == "wait":
        ms = step.get("ms")
        if isinstance(ms, bool) or not isinstance(ms, int) or not 0 <= ms <= MAX_WAIT_MS:
            problems.append(f"{where}: ms must be 0 to {MAX_WAIT_MS}")
    if kind == "confirm" and not (isinstance(step.get("text"), str) and 1 <= len(step["text"]) <= 200):
        problems.append(f"{where}: text must be 1 to 200 characters")
    return problems


# ---------------------------------------------------------------------------------------------------------------------
# the bus, as the runner sees it
# ---------------------------------------------------------------------------------------------------------------------
class Bus:
    """A transport with a clock, a buffer of the frames that arrived and a trace of everything that went by."""

    def __init__(self, transport, trace: list[str], clock: Callable[[], float], sleep: Callable[[float], None]) -> None:
        self.transport = transport
        self.trace = trace
        self.clock = clock
        self.sleep = sleep
        self.start = clock()
        self.buffer: list[tuple[int, bytes]] = []
        self.sent_beyond_queries = False

    def _stamp(self) -> str:
        return f"[{(self.clock() - self.start) * 1000.0:9.1f}]"

    def send(self, can_id: int, data: bytes = b"", clear: bool = True) -> None:
        if clear:
            self.buffer.clear()
        self.trace.append(f"{self._stamp()} TX 0x{can_id:03X} {data.hex().upper()}")
        self.transport.send_frame(can_id, data)
        if can_id not in READ_ONLY_IDS:
            self.sent_beyond_queries = True

    def _pump(self, deadline: float) -> bool:
        remaining = deadline - self.clock()
        if remaining <= 0:
            return False
        frame = self.transport.read_frame(min(0.05, remaining))
        if frame is None:
            self.sleep(0.002)
            return True
        can_id, data = frame[0], bytes(frame[1])
        self.trace.append(f"{self._stamp()} RX 0x{can_id:03X} {data.hex().upper()}")
        self.buffer.append((can_id, data))
        if len(self.buffer) > 2000:
            del self.buffer[:1000]
        return True

    def wait_for(self, can_id: int, timeout: float) -> bytes | None:
        deadline = self.clock() + timeout
        scanned = 0
        while True:
            for index in range(scanned, len(self.buffer)):
                if self.buffer[index][0] == can_id:
                    return self.buffer[index][1]
            scanned = len(self.buffer)
            if not self._pump(deadline):
                for index in range(scanned, len(self.buffer)):
                    if self.buffer[index][0] == can_id:
                        return self.buffer[index][1]
                return None

    def drain(self, seconds: float) -> None:
        deadline = self.clock() + seconds
        while self._pump(deadline):
            pass

    def exchange(self, send: tuple[int, bytes] | None, expect_id: int, timeout: float) -> bytes | None:
        """The primitive of the self-test: put ``send`` on the bus and return the first frame with ``expect_id`` that follows."""
        if send is not None:
            self.send(send[0], bytes(send[1]))
        return self.wait_for(expect_id, timeout)

    def frames(self, can_id: int) -> list[tuple[int, bytes]]:
        return [f for f in self.buffer if f[0] == can_id]


# ---------------------------------------------------------------------------------------------------------------------
# the runner
# ---------------------------------------------------------------------------------------------------------------------
Confirm = Callable[[str], bool]


def run_plan(plan: dict, transport, *, allow_actuation: bool = False, confirm: Confirm | None = None, clock: Callable[[], float] = time.monotonic,
             sleep: Callable[[float], None] = time.sleep, stop: Callable[[], bool] = lambda: False, listen_only: bool = False) -> PlanReport:
    """Run the steps of an already valid plan. A step that fails does not stop the plan, an error (the board did not answer at all
    when it had to, a refused actuation, an operator who is not there) ends it; the outputs are switched off afterwards."""
    problems = validate_plan(plan)
    if problems:
        raise PlanError("the plan is not valid: " + "; ".join(problems))
    report = PlanReport(name=plan["name"])
    bus = Bus(transport, report.trace, clock, sleep)
    state: dict = {"tool": None}
    ended = False
    try:
        for number, step in enumerate(plan["steps"], start=1):
            kind = step["do"]
            label = step.get("label", "")
            if ended or stop():
                report.steps.append(StepResult(number, kind, label, SKIPPED, "not run"))
                continue
            try:
                outcome, message = _RUNNERS[kind](step, bus, state, plan, allow_actuation, confirm, listen_only)
            except _StepError as exc:
                outcome, message = ERROR, str(exc)
            except Exception as exc:  # a transport that fails mid-plan is an error of that step, not a crash
                outcome, message = ERROR, f"{type(exc).__name__}: {exc}"
            report.steps.append(StepResult(number, kind, label, outcome, message))
            if outcome == ERROR:
                ended = True
    finally:
        if bus.sent_beyond_queries:
            report.notes.append(_all_off(bus, listen_only))
    report.tool_id = state.get("tool")
    report.firmware_version = state.get("firmware", "")
    if any(s.outcome == ERROR for s in report.steps):
        report.outcome = ERROR
    elif any(s.outcome == FAIL for s in report.steps):
        report.outcome = FAIL
    elif any(s.outcome == SKIPPED for s in report.steps):
        report.outcome = ERROR
    return report


def _all_off(bus: Bus, listen_only: bool) -> str:
    if listen_only:
        return "all-off not sent: the bus was opened listen-only"
    failed = 0
    for can_id, data in protocol.all_off_frames():
        try:
            bus.send(can_id, data, clear=False)
        except Exception:
            failed += 1
    return f"all outputs switched off after the plan ({failed} frames could not be sent)"


class _StepError(Exception):
    pass


def _tool_name(tool_id: int) -> str:
    return f"{tool_id} ({TOOL_NAMES.get(tool_id, '?')})"


def _quick_state(bus: Bus, state: dict) -> dict | None:
    data = bus.exchange((wire.CAN_ID_QUERY_ACTIVE_TOOL, b""), wire.CAN_ID_ACTIVE_TOOL_RESP, 1.0)
    if data is None:
        return None
    quick = decode_quick_state(bytes(data))
    if quick is not None:
        state["tool"] = quick["tool_id"]
    return quick


def _run_expect_tool(step, bus, state, plan, allow_actuation, confirm, listen_only):
    quick = _quick_state(bus, state)
    if quick is None:
        return FAIL, "no answer to the active-tool query (0x110)"
    if quick["tool_id"] != step["tool"]:
        return FAIL, f"the board runs tool {_tool_name(quick['tool_id'])}, the plan expects {_tool_name(step['tool'])}"
    return PASS, f"tool {_tool_name(quick['tool_id'])}"


def _run_check_faults(step, bus, state, plan, allow_actuation, confirm, listen_only):
    quick = _quick_state(bus, state)
    if quick is None:
        return FAIL, "no answer to the active-tool query (0x110)"
    found = [name for name in ("system_error", "can_error") if quick[name]]
    if quick["thermal_fault"]:
        found.append(f"thermal fault {quick['thermal_fault_name']}")
    if quick["watchdog_reset"]:
        found.append("the last reset was the watchdog")
    return (FAIL, "reported: " + ", ".join(found)) if found else (PASS, "no fault reported")


def _run_query_version(step, bus, state, plan, allow_actuation, confirm, listen_only):
    bus.send(wire.CAN_ID_QUERY_VERSION, b"\x00")
    first = bus.wait_for(wire.CAN_ID_VERSION_RESPONSE, 1.0)
    if first is None:
        return FAIL, "no answer to the version query (0x7F8)"
    bus.drain(0.1)  # the patch frame follows right behind
    answer = parse_version_answer(bus.buffer)
    if answer is None:
        return FAIL, "the version answer is not a valid 0x7F9"
    text = f"{answer['major']}.{answer['minor']}" + (f".{answer['patch']}" if answer["patch"] is not None else "")
    state["firmware"] = text
    if answer["responder"] != "application":
        return FAIL, f"the board answered from its boot-loader (version {text}), not from the application"
    if "hardware_id" in step and int(answer["hardware_id"], 16) != int(step["hardware_id"], 16):
        return FAIL, f"hardware id {answer['hardware_id']}, the plan expects {step['hardware_id']}"
    if "min_version" in step:
        have = (answer["major"], answer["minor"], answer["patch"] or 0)
        if have < _version_tuple(step["min_version"]):
            return FAIL, f"firmware {text} is older than {step['min_version']}"
    return PASS, f"application {text}, hardware {answer['hardware_id']}"


def _run_selftest(step, bus, state, plan, allow_actuation, confirm, listen_only):
    if state.get("tool") is None:
        quick = _quick_state(bus, state)
        if quick is None:
            return FAIL, "no answer to the active-tool query (0x110): nothing to test"
    result = tester_selftest.run_self_test(state["tool"], bus.exchange, timeout=1.0)
    for line in result.lines:
        bus.trace.append(f"           {line}")
    if result.failed:
        return FAIL, f"{result.failed} of the self-test checks failed for tool {_tool_name(state['tool'])}"
    return PASS, f"self-test of tool {_tool_name(state['tool'])} passed"


def _run_send(step, bus, state, plan, allow_actuation, confirm, listen_only):
    can_id, data = _parse_id(step["id"]), _parse_data(step["data"])
    if can_id not in READ_ONLY_IDS:
        if not allow_actuation:
            raise _StepError(f"0x{can_id:03X} is not a query and the operator did not allow actuation (--allow-actuation)")
        if listen_only:
            raise _StepError("the bus was opened listen-only: nothing can be sent")
    bus.send(can_id, data)
    return PASS, f"sent 0x{can_id:03X} {data.hex().upper()}"


def _run_expect_frame(step, bus, state, plan, allow_actuation, confirm, listen_only):
    can_id = _parse_id(step["id"])
    within = step.get("within_ms", DEFAULT_WITHIN_MS) / 1000.0
    deadline = bus.clock() + within
    candidates_seen = 0
    while True:
        for _id, data in bus.frames(can_id)[candidates_seen:]:
            candidates_seen += 1
            problem = _frame_problem(step, data)
            if problem is None:
                return PASS, f"0x{can_id:03X} {data.hex().upper()}"
        if bus.clock() >= deadline:
            break
        if not bus._pump(deadline):
            break
    last = bus.frames(can_id)
    if not last:
        return FAIL, f"no frame 0x{can_id:03X} within {step.get('within_ms', DEFAULT_WITHIN_MS)} ms"
    return FAIL, f"0x{can_id:03X} {last[-1][1].hex().upper()}: {_frame_problem(step, last[-1][1])}"


def _frame_problem(step: dict, data: bytes) -> str | None:
    if "length" in step and len(data) != step["length"]:
        return f"length {len(data)}, expected {step['length']}"
    value = step.get("value")
    if value:
        end = value["offset"] + value["width"]
        if len(data) < end:
            return f"too short ({len(data)} bytes) for the field at offset {value['offset']}"
        number = int.from_bytes(data[value["offset"]:end], "big")
        if "min" in value and number < value["min"]:
            return f"value {number} is below {value['min']}"
        if "max" in value and number > value["max"]:
            return f"value {number} is above {value['max']}"
    return None


def _run_wait(step, bus, state, plan, allow_actuation, confirm, listen_only):
    bus.drain(step["ms"] / 1000.0)
    return PASS, f"waited {step['ms']} ms"


def _run_confirm(step, bus, state, plan, allow_actuation, confirm, listen_only):
    if confirm is None:
        raise _StepError("a person has to confirm this step and none is there (use --assume-yes only when someone has looked)")
    answer = confirm(step["text"])
    bus.trace.append(f"           operator asked: {step['text']} -> {'yes' if answer else 'no'}")
    return (PASS, "the operator confirmed") if answer else (FAIL, "the operator did not confirm")


_RUNNERS = {
    "expect_tool": _run_expect_tool,
    "check_faults": _run_check_faults,
    "query_version": _run_query_version,
    "selftest": _run_selftest,
    "send": _run_send,
    "expect_frame": _run_expect_frame,
    "wait": _run_wait,
    "confirm": _run_confirm,
}
