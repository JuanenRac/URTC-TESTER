# =============================================================================
# URTC Tester - the self-test, shared by the Qt Quick deck, the plans and the command line
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The safe, at-rest check of the detected tool, judged by what each tool's answer means.

Nothing here knows about a window.  ``run_self_test`` asks the caller for one primitive, ``exchange(send, expect_id,
timeout)``: put the frame ``send`` (a ``(can_id, data)`` pair, or None) on the bus and return the data of the first
frame with ``expect_id`` that arrives within ``timeout`` seconds, or None.  The caller decides how the bus is read
(the Qt deck holds the transport lock, a plan reads its own queue) and what it shows.

Every command is a safe, at-rest value (setpoint 0, speed 0, power 0): this verifies the round trip and that the answer
makes sense for that tool, not that an actuator really moves, because confirming that needs a person watching.

Each check ends in one of three results, never in a pass by mere arrival:

* ``PASS``    the answer arrived, can be read and says what a healthy tool at rest says (right tool, application running,
              no fault flag, every field inside the range of the protocol, a temperature below its limit and cold when the
              heater was told to switch off, a drill that is stopped).
* ``FAIL``    there was no answer, or the answer says something is wrong (another tool, the boot-loader, a fault flag, a
              value outside its range, a temperature over the limit).
* ``UNKNOWN`` the evidence cannot decide: the answer is too short to read, the board is still starting, a heater that is
              still hot or a drill that is still turning after the stop command, a tool that has nothing to measure.

The verdict of the whole run is FAIL when any check failed, UNKNOWN when none failed but some could not be decided or
nothing specific to the tool was measured, and PASS only when every check passed.  The limits are in config.json
(``selftest_limits``).  ``INFO`` lines are notes and never count.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any, Callable

from tester_config import (
    CAN_ID_3DP_HOTEND_TELEM, CAN_ID_3DP_THERMAL_MOTION, CAN_ID_ACTIVE_TOOL_RESP, CAN_ID_AOI_TELEMETRY,
    CAN_ID_DRILL_CMD, CAN_ID_DRILL_TELEMETRY, CAN_ID_LASER_CMD, CAN_ID_LASER_TELEMETRY, CAN_ID_QUERY_ACTIVE_TOOL,
    CAN_ID_QUERY_VERSION, CAN_ID_SOLDER_SETPOINT, CAN_ID_SOLDER_TELEMETRY, CAN_ID_VACUUM_TELEMETRY,
    CAN_ID_VERSION_RESPONSE, MOTION_TOOL_IDS, TOOL_NAMES, _, selftest_limits,
)
from urtc_can import protocol

PASS = "PASS"
FAIL = "FAIL"
UNKNOWN = "UNKNOWN"
INFO = "INFO"

# tool id -> steps of (translation key of the description, command id or None, command data, expected telemetry id or None)
SELF_TEST_STEPS: dict[int, list[tuple[str, int | None, bytes | None, int | None]]] = {
    0: [("SELFTEST_STEP_SOLDER", CAN_ID_SOLDER_SETPOINT, struct.pack(">H", 0), CAN_ID_SOLDER_TELEMETRY)],
    5: [("SELFTEST_STEP_DRILL", CAN_ID_DRILL_CMD, bytes([0, 0]), CAN_ID_DRILL_TELEMETRY)],
    9: [("SELFTEST_STEP_LASER", CAN_ID_LASER_CMD, bytes([0, 0]), CAN_ID_LASER_TELEMETRY)],
    10: [("SELFTEST_STEP_PRINTER", CAN_ID_3DP_THERMAL_MOTION, struct.pack(">H", 0) + bytes([0, 0, 0, 0]), CAN_ID_3DP_HOTEND_TELEM)],
    8: [("SELFTEST_STEP_AOI", None, None, CAN_ID_AOI_TELEMETRY)],
    4: [("SELFTEST_STEP_VACUUM", None, None, CAN_ID_VACUUM_TELEMETRY)],
    11: [("SELFTEST_STEP_SCAN_PROBE", None, None, None)],
}

Exchange = Callable[[tuple[int, bytes] | None, int, float], "bytes | None"]
Verdict = tuple[str, str]  # (status, detail already in the interface language)


@dataclass
class SelfTestLine:
    status: str  # PASS, FAIL, UNKNOWN or INFO
    text: str    # already in the interface language
    summary: bool = False  # the closing line with the verdict: shown with the colour of the verdict, never counted

    def __str__(self) -> str:
        return f"[{self.status}] {self.text}"


@dataclass
class SelfTestResult:
    tool_id: int
    lines: list[SelfTestLine] = field(default_factory=list)
    sent_drill_command: bool = False  # the original window must forget the drill speed it believes is set

    def count(self, status: str) -> int:
        return sum(1 for line in self.lines if line.status == status and not line.summary)

    @property
    def failed(self) -> int:
        return self.count(FAIL)

    @property
    def unknown(self) -> int:
        return self.count(UNKNOWN)

    @property
    def passed(self) -> int:
        return self.count(PASS)

    @property
    def verdict(self) -> str:
        """FAIL when any check failed; UNKNOWN when none failed but one could not be decided or nothing was checked; else PASS."""
        return verdict_of(self.lines)


def verdict_of(lines: list[SelfTestLine]) -> str:
    statuses = [line.status for line in lines if line.status != INFO and not line.summary]
    if FAIL in statuses:
        return FAIL
    if UNKNOWN in statuses or PASS not in statuses:
        return UNKNOWN
    return PASS


def steps_for(tool_id: int) -> list[tuple[str, int | None, bytes | None, int | None]]:
    return SELF_TEST_STEPS.get(tool_id, [])


def commands_sent(tool_id: int) -> list[int]:
    """The CAN identifiers the self-test of this tool transmits (the two generic queries and any step command)."""
    ids = [CAN_ID_QUERY_ACTIVE_TOOL, CAN_ID_QUERY_VERSION]
    if tool_id not in MOTION_TOOL_IDS:
        ids += [step[1] for step in steps_for(tool_id) if step[1] is not None]
    return ids


# ---------------------------------------------------------------------------------------------------------------------
# what an answer means
# ---------------------------------------------------------------------------------------------------------------------
def _unreadable(data: bytes, wanted: int) -> Verdict:
    return UNKNOWN, _("SELFTEST_D_UNREADABLE", have=len(data), want=wanted)


def _out_of_range(layout: str, values: dict) -> Verdict | None:
    """A FAIL when a field of the decoded answer is outside the range the protocol gives it, else None."""
    fields: Any = protocol.LAYOUTS[layout]["fields"]
    for spec in fields:
        low_high = spec.get("range")
        value = values.get(spec["name"])
        if low_high and value is not None and not low_high[0] <= value <= low_high[1]:
            return FAIL, _("SELFTEST_D_OUT_OF_RANGE", field=spec["name"], value=value, low=low_high[0], high=low_high[1])
    return None


def check_active_tool(data: bytes | None, tool_id: int) -> Verdict:
    if data is None:
        return FAIL, _("SELFTEST_D_NO_ANSWER")
    values = protocol.decode_active_tool_resp(bytes(data))
    if values is None:
        return _unreadable(data, 4)
    if values["tool_id"] != tool_id:
        return FAIL, _("SELFTEST_D_WRONG_TOOL", have=values["tool_id"], want=tool_id)
    bad = _out_of_range("active_tool_resp", values)
    if bad is not None:
        return bad
    faults = [name for name in ("system_error", "can_error") if values[name]]
    if values.get("thermal_fault"):
        faults.append("thermal_fault")
    if faults:
        return FAIL, _("SELFTEST_D_FAULTS", faults=", ".join(faults))
    if values["booting"]:
        return UNKNOWN, _("SELFTEST_D_BOOTING")
    return PASS, _("SELFTEST_D_TOOL_OK", tool=TOOL_NAMES.get(tool_id, tool_id))


def check_version(data: bytes | None) -> Verdict:
    if data is None:
        return FAIL, _("SELFTEST_D_NO_ANSWER")
    values = protocol.decode("version_response", bytes(data))
    if values is None:
        return _unreadable(data, 8)
    if values["responder"] == protocol.RESPONDER_BOOTLOADER:
        return FAIL, _("SELFTEST_D_BOOTLOADER")
    if values["responder"] != protocol.RESPONDER_APPLICATION:
        return FAIL, _("SELFTEST_D_UNKNOWN_RESPONDER", value=values["responder"])
    return PASS, _("SELFTEST_D_APPLICATION", version=f"{values['version_major']}.{values['version_minor']}")


def _check_temperature(layout: str, limit_name: str):
    def check(data: bytes, limits: dict) -> Verdict:
        values = protocol.decode(layout, data)
        if values is None:
            return _unreadable(data, 2)
        degrees = values["temperature_c"]
        if degrees > limits[limit_name]:
            return FAIL, _("SELFTEST_D_TEMP_OVER", value=degrees, max=limits[limit_name])
        if degrees > limits["cold_c"]:  # told to switch off, still warm: the reading cannot show that the heater is off
            return UNKNOWN, _("SELFTEST_D_TEMP_HOT", value=degrees, cold=limits["cold_c"])
        return PASS, _("SELFTEST_D_TEMP_OK", value=degrees, max=limits[limit_name])
    return check


def _check_drill(data: bytes, limits: dict) -> Verdict:
    values = protocol.decode("drill_telemetry", data)
    if values is None:
        return _unreadable(data, 3)
    bad = _out_of_range("drill_telemetry", values)
    if bad is not None:
        return bad
    if values["rpm"] > limits["idle_rpm"]:  # a spindle takes seconds to stop: one early reading cannot say the stop was ignored
        return UNKNOWN, _("SELFTEST_D_RPM_TURNING", value=values["rpm"], idle=limits["idle_rpm"])
    return PASS, _("SELFTEST_D_RPM_STOPPED", value=values["rpm"])


def _check_fields(layout: str, wanted: int):
    def check(data: bytes, limits: dict) -> Verdict:
        values = protocol.decode(layout, data)
        if values is None:
            return _unreadable(data, wanted)
        bad = _out_of_range(layout, values)
        if bad is not None:
            return bad
        return PASS, _("SELFTEST_D_FIELDS_OK")
    return check


# step description key -> how the answer to that step is judged
CHECKS: dict[str, Callable[[bytes, dict], Verdict]] = {
    "SELFTEST_STEP_SOLDER": _check_temperature("solder_telemetry", "solder_max_c"),
    "SELFTEST_STEP_PRINTER": _check_temperature("printer_hotend_telemetry", "printer_max_c"),
    "SELFTEST_STEP_DRILL": _check_drill,
    "SELFTEST_STEP_LASER": _check_fields("laser_telemetry", 1),
    "SELFTEST_STEP_AOI": _check_fields("aoi_telemetry", 1),
    "SELFTEST_STEP_VACUUM": _check_fields("vacuum_telemetry", 3),
}


def run_self_test(
    tool_id: int,
    exchange: Exchange,
    emit: Callable[[SelfTestLine], None] | None = None,
    stop: Callable[[], bool] = lambda: False,
    timeout: float = 1.5,
    limits: dict | None = None,
) -> SelfTestResult:
    """Run the checks of ``tool_id`` and return every line; ``emit`` also gets each line as soon as it is known."""
    result = SelfTestResult(tool_id)
    limits = limits if limits is not None else selftest_limits()

    def add(status: str, text: str, summary: bool = False) -> None:
        line = SelfTestLine(status, text, summary)
        result.lines.append(line)
        if emit is not None:
            emit(line)

    def add_check(description: str, verdict: Verdict) -> None:
        add(verdict[0], f"{description}: {verdict[1]}")

    add(INFO, _("LOG_SELFTEST_TESTING", tool=TOOL_NAMES.get(tool_id, "?")))
    # Generic checks first: meaningful for every tool.
    add_check(_("LOG_SELFTEST_ACTIVE_TOOL"), check_active_tool(exchange((CAN_ID_QUERY_ACTIVE_TOOL, b""), CAN_ID_ACTIVE_TOOL_RESP, timeout), tool_id))
    if stop():
        return result
    add_check(_("LOG_SELFTEST_VERSION"), check_version(exchange((CAN_ID_QUERY_VERSION, b"\x00"), CAN_ID_VERSION_RESPONSE, timeout)))

    if tool_id in MOTION_TOOL_IDS:
        add(UNKNOWN, _("SELFTEST_MOTION_INFO"))
    elif steps_for(tool_id):
        for key, command_id, command_data, expect_id in steps_for(tool_id):
            if stop():
                return result
            description = _(key)
            if expect_id is None:
                add(UNKNOWN, description)
                continue
            send = (command_id, command_data) if command_id is not None and command_data is not None else None
            response = exchange(send, expect_id, timeout)
            if command_id == CAN_ID_DRILL_CMD:
                result.sent_drill_command = True
            add_check(description, (FAIL, _("SELFTEST_D_NO_ANSWER")) if response is None else CHECKS[key](bytes(response), limits))
    else:
        add(UNKNOWN, _("SELFTEST_NO_STEPS"))
    verdict = result.verdict
    add(verdict, _("SELFTEST_VERDICT", verdict=_(f"QT_PLAN_OUTCOME_{verdict}"), passed=result.passed, failed=result.failed, unknown=result.unknown), summary=True)
    return result
