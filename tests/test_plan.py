# =============================================================================
# URTC-TESTER - tests/test_plan.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Test plans: what is refused before anything is sent, and how each step behaves against the simulated head."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import advanced_protocol as protocol
import tester_plan as tp
from tester_simulator import SimulatedBoard

ROOT = Path(__file__).resolve().parents[1]


class TickClock:
    """A clock that moves a little on every reading, so a wait ends without the test waiting."""

    def __init__(self, step: float = 0.001) -> None:
        self.now = 0.0
        self.step = step

    def __call__(self) -> float:
        self.now += self.step
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def run(plan, board=None, **options):
    clock = TickClock()
    board = board or SimulatedBoard(0, clock=clock)
    return tp.run_plan(plan, board, clock=clock, sleep=clock.sleep, **options), board


def plan_of(*steps, actuation=False, name="t"):
    plan = {"format": 1, "name": name, "steps": list(steps)}
    if actuation:
        plan["actuation"] = True
    return plan


# ---- reading a plan ------------------------------------------------------------------------------------------------------
def test_the_example_plans_are_valid():
    for path in sorted((ROOT / "plans").glob("*.json")):
        assert tp.validate_plan(json.loads(path.read_text(encoding="utf-8"))) == [], path.name


def test_an_empty_or_unknown_plan_is_refused():
    assert tp.validate_plan([]) == ["the plan must be a JSON object"]
    assert any("format" in p for p in tp.validate_plan({"name": "t", "steps": [{"do": "check_faults"}]}))
    assert any("steps" in p for p in tp.validate_plan({"format": 1, "name": "t", "steps": []}))
    assert any("unknown plan fields" in p for p in tp.validate_plan({**plan_of({"do": "check_faults"}), "colour": "red"}))
    assert any("unknown 'do'" in p for p in tp.validate_plan(plan_of({"do": "explode"})))


@pytest.mark.parametrize("name", ["", "../escape", "a b", "x" * 65, ".hidden", "a/b", "a\\b"])
def test_a_name_that_could_leave_the_results_folder_is_refused(name):
    assert any("name" in p for p in tp.validate_plan(plan_of({"do": "check_faults"}, name=name)))


def test_a_step_with_missing_or_extra_fields_is_refused():
    problems = tp.validate_plan(plan_of({"do": "expect_tool"}, {"do": "wait", "ms": 5, "speed": 1}))
    assert any("missing tool" in p for p in problems) and any("unknown fields speed" in p for p in problems)


@pytest.mark.parametrize("can_id", ["0x7F0", "0x7F1", "0x7FD", "0x7FF", "0x192", "0x131", "0x1A0", "0x1A4", "0x1AC", "0x1AE", "0x210", "0x220", 0x7F4])
def test_frames_that_change_what_the_board_is_are_never_sent_even_with_the_switch(can_id):
    problems = tp.validate_plan(plan_of({"do": "send", "id": can_id, "data": "B0071D5A"}, actuation=True))
    assert any("never sent by a plan" in p for p in problems)


def test_a_command_needs_the_plan_to_say_it_actuates():
    step = {"do": "send", "id": "0x130", "data": "0000"}
    assert any("actuation" in p for p in tp.validate_plan(plan_of(step)))
    assert tp.validate_plan(plan_of(step, actuation=True)) == []
    assert tp.validate_plan(plan_of({"do": "send", "id": "0x110", "data": ""})) == []


@pytest.mark.parametrize("step", [
    {"do": "send", "id": "0x130", "data": "0"},
    {"do": "send", "id": "0x130", "data": "ZZ"},
    {"do": "send", "id": "0x130", "data": "00" * 9},
    {"do": "send", "id": "0x800", "data": ""},
    {"do": "send", "id": -1, "data": ""},
    {"do": "send", "id": True, "data": ""},
    {"do": "expect_frame", "id": "0x135", "within_ms": 0},
    {"do": "expect_frame", "id": "0x135", "within_ms": 70000},
    {"do": "expect_frame", "id": "0x135", "length": 9},
    {"do": "expect_frame", "id": "0x135", "value": {"offset": 7, "width": 2, "min": 0}},
    {"do": "expect_frame", "id": "0x135", "value": {"offset": 0, "width": 2}},
    {"do": "wait", "ms": -1},
    {"do": "wait", "ms": 60001},
    {"do": "wait", "ms": 1.5},
    {"do": "confirm", "text": ""},
    {"do": "expect_tool", "tool": 99},
    {"do": "query_version", "min_version": "banana"},
    {"do": "query_version", "hardware_id": "303CC01"},
])
def test_a_badly_formed_step_is_refused(step):
    assert tp.validate_plan(plan_of(step, actuation=True)), step


def test_load_plan_reports_a_file_that_is_not_json(tmp_path):
    path = tmp_path / "p.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(tp.PlanError):
        tp.load_plan(path)
    with pytest.raises(tp.PlanError):
        tp.load_plan(tmp_path / "missing.json")


def test_run_plan_refuses_a_plan_that_was_not_validated():
    with pytest.raises(tp.PlanError):
        tp.run_plan({"format": 1}, SimulatedBoard(0))


# ---- running a plan ------------------------------------------------------------------------------------------------------
def test_a_read_only_plan_passes_against_a_head_that_is_fine():
    report, board = run(plan_of({"do": "expect_tool", "tool": 0}, {"do": "check_faults"}, {"do": "query_version", "min_version": "0.3.5"}, {"do": "selftest"}))
    assert report.outcome == tp.PASS, report.log_text()
    assert report.firmware_version == "0.4.0" and report.tool_id == 0
    assert all(s.outcome == tp.PASS for s in report.steps)


def test_the_wrong_tool_is_a_failure_that_does_not_stop_the_plan():
    report, _ = run(plan_of({"do": "expect_tool", "tool": 5}, {"do": "check_faults"}))
    assert [s.outcome for s in report.steps] == [tp.FAIL, tp.PASS] and report.outcome == tp.FAIL
    assert "expects 5" in report.steps[0].message


@pytest.mark.parametrize("fault,text", [("system", "system_error"), ("can", "can_error"), ("thermal", "thermal fault")])
def test_a_fault_of_the_head_fails_check_faults(fault, text):
    report, _ = run(plan_of({"do": "check_faults"}), SimulatedBoard(0, fault=fault))
    assert report.outcome == tp.FAIL and text in report.steps[0].message


def test_a_head_that_answers_nothing_fails_every_question_instead_of_passing():
    report, _ = run(plan_of({"do": "expect_tool", "tool": 0}, {"do": "query_version"}, {"do": "selftest"}), SimulatedBoard(0, silent=True))
    assert report.outcome == tp.FAIL and all(s.outcome == tp.FAIL for s in report.steps)


def test_the_version_checks():
    old = SimulatedBoard(0, firmware=(0, 3, 1))
    report, _ = run(plan_of({"do": "query_version", "min_version": "0.3.5"}), old)
    assert report.steps[0].outcome == tp.FAIL and "older" in report.steps[0].message
    report, _ = run(plan_of({"do": "query_version", "min_version": "0.3"}), old)
    assert report.steps[0].outcome == tp.PASS
    report, _ = run(plan_of({"do": "query_version", "hardware_id": "0x0303CC02"}))
    assert report.steps[0].outcome == tp.FAIL and "hardware id" in report.steps[0].message
    report, _ = run(plan_of({"do": "query_version", "hardware_id": "0x0303CC01"}))
    assert report.steps[0].outcome == tp.PASS
    report, _ = run(plan_of({"do": "query_version"}), SimulatedBoard(0, firmware=(1, 0, None)))
    assert report.firmware_version == "1.0"


def test_the_selftest_step_fails_when_the_tool_does_not_answer_its_command():
    class DeafToCommands(SimulatedBoard):
        def send_frame(self, can_id, data=b""):
            if can_id == 0x130:
                self.sent.append((can_id, bytes(data)))
                return
            super().send_frame(can_id, data)

    class NoTelemetry(DeafToCommands):
        def _telemetry(self):
            return (0x7FF, b"")

    report, _ = run(plan_of({"do": "selftest"}), NoTelemetry(0))
    assert report.steps[0].outcome == tp.FAIL and "failed" in report.steps[0].message


def test_a_command_without_the_operators_switch_is_an_error_that_ends_the_plan():
    step = {"do": "send", "id": "0x130", "data": "00A0"}
    report, board = run(plan_of(step, {"do": "check_faults"}, actuation=True))
    assert report.outcome == tp.ERROR
    assert [s.outcome for s in report.steps] == [tp.ERROR, tp.SKIPPED]
    assert (0x130, bytes.fromhex("00A0")) not in board.sent
    assert "allow actuation" in report.steps[0].message


def test_a_command_is_sent_with_both_switches_and_every_output_is_switched_off_afterwards():
    plan = plan_of({"do": "send", "id": "0x130", "data": "00A0"}, {"do": "expect_frame", "id": "0x135", "within_ms": 800, "value": {"offset": 0, "width": 2, "min": 100, "max": 200}}, actuation=True)
    report, board = run(plan, allow_actuation=True)
    assert report.outcome == tp.PASS, report.log_text()
    assert (0x130, bytes.fromhex("00A0")) in board.sent
    for frame in protocol.all_off_frames():
        assert frame in board.sent
    assert any("switched off" in note for note in report.notes)
    assert board.outputs["solder_setpoint_c"] == 0  # the last order the head got is "off"


def test_a_plan_that_only_asks_questions_sends_no_all_off():
    report, board = run(plan_of({"do": "check_faults"}))
    assert not report.notes
    assert all(frame[0] in tp.READ_ONLY_IDS for frame in board.sent)


def test_listen_only_blocks_a_command_but_not_a_question():
    plan = plan_of({"do": "check_faults"}, {"do": "send", "id": "0x130", "data": "0000"}, actuation=True)
    report, board = run(plan, allow_actuation=True, listen_only=True)
    assert report.steps[0].outcome == tp.PASS and report.steps[1].outcome == tp.ERROR and "listen-only" in report.steps[1].message
    assert not any(frame[0] == 0x130 for frame in board.sent)
    assert report.notes == []  # nothing beyond a query went out, so nothing had to be switched off


def test_expect_frame_checks_the_length_and_the_value_of_a_frame_after_the_last_send():
    base = {"do": "expect_frame", "id": "0x135", "within_ms": 300}
    report, _ = run(plan_of(dict(base, length=2)))
    assert report.steps[0].outcome == tp.PASS
    report, _ = run(plan_of(dict(base, length=3)))
    assert report.steps[0].outcome == tp.FAIL and "length 2" in report.steps[0].message
    report, _ = run(plan_of(dict(base, value={"offset": 0, "width": 2, "min": 500})))
    assert report.steps[0].outcome == tp.FAIL and "below 500" in report.steps[0].message
    report, _ = run(plan_of(dict(base, value={"offset": 0, "width": 2, "max": 10})))
    assert report.steps[0].outcome == tp.FAIL and "above 10" in report.steps[0].message
    report, _ = run(plan_of(dict(base, id="0x165")))
    assert report.steps[0].outcome == tp.FAIL and "no frame 0x165" in report.steps[0].message


def test_a_frame_from_before_the_last_send_does_not_satisfy_expect_frame():
    class SaysOnlyAtFirst(SimulatedBoard):
        def __init__(self):
            super().__init__(0)
            self.reads = 0

        def read_frame(self, timeout=0.05):
            self.reads += 1
            if self._queue:
                return self._queue.pop(0)
            return (0x135, b"\x00 ") if self.reads <= 3 else None

    stale = plan_of({"do": "wait", "ms": 20}, {"do": "send", "id": "0x1BA", "data": ""}, {"do": "expect_frame", "id": "0x135", "within_ms": 50})
    report, _ = run(stale, SaysOnlyAtFirst())
    assert report.steps[2].outcome == tp.FAIL and "no frame 0x135" in report.steps[2].message
    fresh = plan_of({"do": "send", "id": "0x1BA", "data": ""}, {"do": "wait", "ms": 20}, {"do": "expect_frame", "id": "0x135", "within_ms": 50})
    report, _ = run(fresh, SaysOnlyAtFirst())
    assert report.steps[2].outcome == tp.PASS


def test_wait_keeps_collecting_and_confirm_needs_a_person():
    report, _ = run(plan_of({"do": "wait", "ms": 20}, {"do": "confirm", "text": "Is it lit?"}))
    assert report.steps[0].outcome == tp.PASS and report.steps[1].outcome == tp.ERROR and "none is there" in report.steps[1].message
    report, _ = run(plan_of({"do": "confirm", "text": "Is it lit?"}), confirm=lambda text: True)
    assert report.outcome == tp.PASS
    asked = []
    report, _ = run(plan_of({"do": "confirm", "text": "Is it lit?"}), confirm=lambda text: asked.append(text) or False)
    assert report.outcome == tp.FAIL and asked == ["Is it lit?"]


def test_a_transport_that_breaks_in_the_middle_is_an_error_of_that_step():
    class Breaks(SimulatedBoard):
        def send_frame(self, can_id, data=b""):
            raise OSError("adapter unplugged")

    report, _ = run(plan_of({"do": "check_faults"}, {"do": "check_faults"}), Breaks(0))
    assert report.outcome == tp.ERROR and "adapter unplugged" in report.steps[0].message and report.steps[1].outcome == tp.SKIPPED


def test_stop_skips_the_steps_that_have_not_run():
    seen = []
    report, _ = run(plan_of({"do": "check_faults"}, {"do": "check_faults"}), stop=lambda: bool(seen.append(1)) or len(seen) > 1)
    assert [s.outcome for s in report.steps] == [tp.PASS, tp.SKIPPED] and report.outcome == tp.ERROR


def test_the_log_has_every_frame_and_every_step():
    report, _ = run(plan_of({"do": "check_faults", "label": "x"}))
    text = report.log_text("name")
    assert "TX 0x110" in text and "RX 0x111" in text and "STEP 1 check_faults PASS" in text and text.rstrip().endswith("0 skipped")


def test_the_plan_given_is_not_changed_by_running_it():
    plan = plan_of({"do": "check_faults"})
    before = copy.deepcopy(plan)
    run(plan)
    assert plan == before


# ---- commands the firmware drops again unless they are refreshed ---------------------------------------------------------------------
HEAT = {"do": "send", "id": "0x130", "data": "00A0"}


def test_without_a_keepalive_the_firmware_drops_a_heater_order_and_the_plan_sees_it():
    plan = plan_of(HEAT, {"do": "wait", "ms": 600}, {"do": "send", "id": "0x1BA", "data": ""},
                   {"do": "expect_frame", "id": "0x135", "within_ms": 300, "value": {"offset": 0, "width": 2, "min": 140}}, actuation=True)
    report, board = run(plan, allow_actuation=True)
    assert report.steps[3].outcome == tp.FAIL and board.outputs["solder_setpoint_c"] == 0


def test_with_a_keepalive_the_order_is_repeated_and_the_tip_stays_hot():
    plan = plan_of(dict(HEAT, keepalive_ms=100), {"do": "wait", "ms": 600},
                   {"do": "expect_frame", "id": "0x135", "within_ms": 300, "value": {"offset": 0, "width": 2, "min": 140}}, actuation=True)
    report, board = run(plan, allow_actuation=True)
    assert report.outcome == tp.PASS, report.log_text()
    repeats = [line for line in report.trace if "TX 0x130 00A0 (repeated)" in line]
    assert 4 <= len(repeats) <= 8  # about every 100 ms over about 600 ms
    assert board.sent.count((0x130, bytes.fromhex("00A0"))) == len(repeats) + 1


def test_a_new_order_for_the_same_identifier_stops_the_repetition_and_off_is_never_repeated():
    plan = plan_of(dict(HEAT, keepalive_ms=50), {"do": "wait", "ms": 120}, {"do": "send", "id": "0x130", "data": "0000", "keepalive_ms": 50},
                   {"do": "wait", "ms": 300}, actuation=True)
    report, board = run(plan, allow_actuation=True)
    after_off = board.sent[board.sent.index((0x130, b"\x00\x00")):]
    assert after_off.count((0x130, b"\x00\x00")) == 2  # the order itself and the all-off at the end, nothing repeated in between
    assert not any(frame == (0x130, bytes.fromhex("00A0")) for frame in after_off)


def test_the_repetition_goes_on_while_a_person_is_asked():
    seen = []

    def slow_confirm(text):
        import time as real_time
        real_time.sleep(0.05)  # a person takes a moment: the loop keeps the order alive meanwhile
        seen.append(text)
        return True

    plan = plan_of(dict(HEAT, keepalive_ms=20), {"do": "confirm", "text": "Is it warm?"},
                   {"do": "expect_frame", "id": "0x135", "within_ms": 300, "value": {"offset": 0, "width": 2, "min": 140}}, actuation=True)
    report, board = run(plan, allow_actuation=True, confirm=slow_confirm)
    assert report.outcome == tp.PASS and seen == ["Is it warm?"]
    assert any("(repeated)" in line for line in report.trace)


def test_a_confirm_callback_that_raises_is_an_error_of_the_step():
    def broken(text):
        raise RuntimeError("no terminal")

    report, _ = run(plan_of({"do": "confirm", "text": "Is it warm?"}), confirm=broken)
    assert report.outcome == tp.ERROR and "no terminal" in report.steps[0].message


@pytest.mark.parametrize("keep", [0, 19, 201, 1.5, "100", True])
def test_a_keepalive_outside_the_watchdog_window_or_not_a_number_is_refused(keep):
    assert any("keepalive_ms" in p for p in tp.validate_plan(plan_of(dict(HEAT, keepalive_ms=keep), actuation=True)))


def test_a_keepalive_on_a_query_is_refused():
    assert any("not for a query" in p for p in tp.validate_plan(plan_of({"do": "send", "id": "0x110", "data": "", "keepalive_ms": 100})))
