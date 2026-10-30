# =============================================================================
# URTC-TESTER - tests/test_simulator_and_cli.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The simulated head, the trace player and the command line that runs plans without a window."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import tester_cli
import tester_plan as tp
import tester_trace_export as export
from tester_result_record import load_record
from tester_simulator import ReplayCAN, SimulatedBoard, make_board, parse_trace
from urtc_can import protocol as wire
from urtc_can.quick_state import decode as decode_quick_state

ROOT = Path(__file__).resolve().parents[1]


# ---- the simulated head --------------------------------------------------------------------------------------------------
def drain(board, count=3):
    return [board.read_frame() for _ in range(count)]


def test_the_head_answers_the_active_tool_query_with_its_tool_and_no_fault():
    board = make_board(5)
    board.send_frame(wire.CAN_ID_QUERY_ACTIVE_TOOL, b"")
    can_id, data = board.read_frame()
    quick = decode_quick_state(data)
    assert can_id == wire.CAN_ID_ACTIVE_TOOL_RESP and quick["tool_id"] == 5
    assert not quick["system_error"] and not quick["can_error"] and not quick["thermal_fault"]


@pytest.mark.parametrize("fault,field", [("system", "system_error"), ("can", "can_error"), ("thermal", "thermal_fault")])
def test_a_played_fault_shows_in_the_quick_state(fault, field):
    board = SimulatedBoard(0, fault=fault)
    board.send_frame(wire.CAN_ID_QUERY_ACTIVE_TOOL, b"")
    assert decode_quick_state(board.read_frame()[1])[field]


def test_an_unknown_fault_or_tool_is_refused():
    with pytest.raises(ValueError):
        SimulatedBoard(0, fault="fire")
    with pytest.raises(ValueError):
        make_board(99)


def test_the_head_answers_the_version_query_like_an_application():
    board = SimulatedBoard(0, firmware=(0, 3, 5))
    board.send_frame(wire.CAN_ID_QUERY_VERSION, b"\x00")
    first, second = board.read_frame(), board.read_frame()
    assert first[0] == wire.CAN_ID_VERSION_RESPONSE and first[1][0] == wire.RESPONDER_APPLICATION and len(first[1]) == 8
    assert second[0] == wire.CAN_ID_VERSION_PATCH_RESPONSE and second[1][1] == 5
    legacy = SimulatedBoard(0, firmware=(0, 2, None))
    legacy.send_frame(wire.CAN_ID_QUERY_VERSION, b"")
    assert legacy.read_frame()[0] == wire.CAN_ID_VERSION_RESPONSE and legacy.read_frame()[0] != wire.CAN_ID_VERSION_PATCH_RESPONSE


def test_the_soldering_tip_moves_toward_its_set_point_and_back():
    board = SimulatedBoard(0)
    board.send_frame(wire.CAN_ID_SOLDER_SETPOINT, (200).to_bytes(2, "big"))
    temps = [int.from_bytes(board.read_frame()[1], "big") for _ in range(8)]
    assert temps[0] < temps[-1] == 200 and temps == sorted(temps)
    board.send_frame(wire.CAN_ID_SOLDER_SETPOINT, b"\x00\x00")
    cooling = [int.from_bytes(board.read_frame()[1], "big") for _ in range(8)]
    assert cooling[-1] == 25 and cooling == sorted(cooling, reverse=True)


def test_each_tool_with_telemetry_reports_it_and_a_locked_laser_has_no_power():
    expected = {0: wire.CAN_ID_SOLDER_TELEMETRY, 4: wire.CAN_ID_VACUUM_TELEMETRY, 5: wire.CAN_ID_DRILL_TELEMETRY, 8: wire.CAN_ID_AOI_TELEMETRY,
                9: wire.CAN_ID_LASER_TELEMETRY, 10: wire.CAN_ID_PRINTER_HOTEND_TELEMETRY}
    for tool, can_id in expected.items():
        assert make_board(tool).read_frame()[0] == can_id
    assert make_board(1).read_frame()[0] == wire.CAN_ID_ACTIVE_TOOL_RESP  # no telemetry of its own
    laser = make_board(9)
    laser.send_frame(wire.CAN_ID_LASER_CMD, bytes([200, 0]))
    assert laser.outputs["laser_power"] == 0
    laser.send_frame(wire.CAN_ID_LASER_CMD, bytes([200, 1]))
    assert laser.outputs["laser_power"] == 200
    drill = make_board(5)
    drill.send_frame(wire.CAN_ID_DRILL_CMD, bytes([10, 0]))
    assert drill.outputs["drill_speed"] == 10 and drill.sent[-1] == (wire.CAN_ID_DRILL_CMD, bytes([10, 0]))


def test_a_silent_head_says_nothing_at_all():
    board = SimulatedBoard(0, silent=True)
    board.send_frame(wire.CAN_ID_QUERY_ACTIVE_TOOL, b"")
    assert board.read_frame() is None


# ---- the trace player ----------------------------------------------------------------------------------------------------
ROWS = [("00:00:00.000", "0x111 (ACTIVE_TOOL_RESP)", 6, "000000000000", 0), ("00:00:00.050", "0x135", 2, "0091", 50), ("00:00:00.100", "0x7F9", 8, "000303CC01000004", 50)]


@pytest.mark.parametrize("fmt", ["trc", "asc"])
def test_a_trace_the_monitor_exported_is_read_back_frame_for_frame(fmt):
    frames = parse_trace(export.render(ROWS, fmt))
    assert [(f[1], f[2]) for f in frames] == [(0x111, bytes(6)), (0x135, b"\x00\x91"), (0x7F9, bytes.fromhex("000303CC01000004"))]
    assert [round(f[0], 3) for f in frames] == [0.0, 0.05, 0.1]


def test_text_that_is_not_a_frame_is_skipped_and_a_wrong_length_is_dropped():
    text = ";comment\nnot a frame\n     1)        0.0  Rx    0111  2   0000\n     2)        1.0  Rx    0111  3   0000\n"
    assert [f[1] for f in parse_trace(text)] == [0x111]


def test_replay_plays_the_frames_in_order_and_records_what_is_sent(tmp_path):
    path = tmp_path / "bus.trc"
    path.write_text(export.render(ROWS, "trc"), encoding="utf-8")
    player = ReplayCAN(path)
    player.open_channel()
    player.send_frame(0x110, b"")
    assert player.sent == [(0x110, b"")]
    assert [player.read_frame()[0] for _ in range(3)] == [0x111, 0x135, 0x7F9] and player.read_frame() is None and player.finished


def test_a_plan_can_be_checked_against_a_recorded_trace(tmp_path):
    path = tmp_path / "bus.trc"
    path.write_text(export.render(ROWS, "trc"), encoding="utf-8")
    plan = {"format": 1, "name": "replay", "steps": [{"do": "expect_frame", "id": "0x135", "within_ms": 100, "length": 2, "value": {"offset": 0, "width": 2, "min": 100, "max": 200}}]}
    assert tp.run_plan(plan, ReplayCAN(path)).outcome == tp.PASS
    plan["steps"][0]["value"]["max"] = 100
    assert tp.run_plan(plan, ReplayCAN(path)).outcome == tp.FAIL


def test_an_empty_trace_is_refused(tmp_path):
    path = tmp_path / "empty.trc"
    path.write_text(";nothing\n", encoding="utf-8")
    with pytest.raises(ValueError):
        ReplayCAN(path)


# ---- the command line ----------------------------------------------------------------------------------------------------
def cli(capsys, *args):
    code = tester_cli.main(list(args))
    return code, capsys.readouterr().out


def test_info_and_selftest_pass_against_the_simulated_head_and_leave_a_checkable_record(tmp_path, capsys):
    code, out = cli(capsys, "selftest", "--transport", "simulate", "--tool", "10", "--out", str(tmp_path))
    assert code == 0 and "PASS: 3 passed" in out
    records = sorted(tmp_path.glob("selftest_*.json"))
    assert len(records) == 1
    record = load_record(records[0], tmp_path)  # the log still matches the hash recorded with the result
    assert record.outcome == "pass" and record.firmware_version == "0.4.0" and record.adapter == "simulate:in-memory"
    # next to the result record the run leaves the same result in the shape the flasher and the updater use
    from urtc_can import evidence

    (shape_path,) = sorted(tmp_path.glob("urtc_evidence_selftest_*.json"))
    shape = json.loads(shape_path.read_text(encoding="utf-8"))
    assert evidence.verify(shape) == [] and shape["kind"] == "test" and shape["outcome"] == "pass" and shape["artifacts"][0]["sha256"] == record.log_sha256
    log = (tmp_path / record.log_file)
    log.write_text(log.read_text(encoding="utf-8") + "edited\n", encoding="utf-8")
    with pytest.raises(Exception):
        load_record(records[0], tmp_path)


def test_a_fault_makes_the_exit_status_1_and_json_has_the_steps(tmp_path, capsys):
    code, out = cli(capsys, "info", "--transport", "simulate", "--fault", "thermal", "--out", str(tmp_path), "--json")
    data = json.loads(out)
    assert code == 1 and data["outcome"] == "fail" and data["steps"][1]["do"] == "check_faults" and data["steps"][1]["outcome"] == "fail"
    assert Path(data["log"]).is_file() and Path(data["record"]).is_file()


def test_the_example_plans_pass_against_the_simulated_head(tmp_path, capsys):
    code, out = cli(capsys, "run-plan", str(ROOT / "plans" / "identify_and_selftest.json"), "--transport", "simulate", "--out", str(tmp_path))
    assert code == 0, out
    code, out = cli(capsys, "run-plan", str(ROOT / "plans" / "soldering_iron_bench.json"), "--transport", "simulate", "--out", str(tmp_path), "--allow-actuation", "--assume-yes")
    assert code == 0 and "all outputs switched off" in out, out


def test_a_plan_that_heats_is_not_run_without_the_operators_switch(tmp_path, capsys):
    code, out = cli(capsys, "run-plan", str(ROOT / "plans" / "soldering_iron_bench.json"), "--transport", "simulate", "--out", str(tmp_path), "--assume-yes")
    assert code == 3 and "did not allow actuation" in out


def test_a_confirm_step_without_a_person_is_an_error_not_a_pass(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(tester_cli.sys, "stdin", None)
    code, out = cli(capsys, "run-plan", str(ROOT / "plans" / "soldering_iron_bench.json"), "--transport", "simulate", "--out", str(tmp_path), "--allow-actuation")
    assert code == 3 and "none is there" in out
    # the heater was switched on before the question, and is switched off again
    assert "all outputs switched off" in out


def test_a_bad_plan_or_bad_arguments_exit_with_2_and_touch_no_bus(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"format": 1, "name": "bad", "steps": [{"do": "send", "id": "0x7F0", "data": "B0071D5A"}]}), encoding="utf-8")
    code, out = cli(capsys, "run-plan", str(bad), "--transport", "simulate", "--out", str(tmp_path / "out"))
    assert code == 2 and "never sent by a plan" in out and not (tmp_path / "out").exists()
    assert cli(capsys, "run-plan")[0] == 2
    assert cli(capsys, "run-plan", str(tmp_path / "missing.json"))[0] == 2
    assert cli(capsys, "info", "--transport", "serial")[0] == 2  # no --port
    assert cli(capsys, "info", "--transport", "replay")[0] == 2
    code, out = cli(capsys, "validate-plan", str(ROOT / "plans" / "soldering_iron_bench.json"))
    assert code == 0 and "asks to actuate" in out


def test_a_replay_of_a_trace_runs_a_plan(tmp_path, capsys):
    trace = tmp_path / "bus.trc"
    trace.write_text(export.render(ROWS, "trc"), encoding="utf-8")
    plan = tmp_path / "p.json"
    plan.write_text(json.dumps({"format": 1, "name": "from-trace", "steps": [{"do": "expect_frame", "id": "0x135", "within_ms": 100}]}), encoding="utf-8")
    code, out = cli(capsys, "run-plan", str(plan), "--transport", "replay", "--port", str(trace), "--out", str(tmp_path / "out"))
    assert code == 0 and "PASS" in out


def test_the_program_entry_point_starts_no_window_with_headless(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / "urtc_tester.py"), "--headless", "info", "--transport", "simulate", "--out", str(tmp_path)],
                            capture_output=True, text=True, timeout=60, cwd=ROOT)
    assert result.returncode == 0 and "query_version: PASS" in result.stdout, result.stdout + result.stderr


# ---- the heater PID of the simulated head -------------------------------------------------------------------------------------------
def pid_answer(board):
    can_id, data = board.read_frame()
    assert can_id == wire.CAN_ID_PID_STATE_RESP
    return decode_pid(data)


def decode_pid(data):
    import tester_extras as extras
    return extras.decode_pid_state(data)


def test_the_simulated_pid_stores_gains_and_runs_an_autotune_only_with_a_set_point():
    import tester_extras as extras
    board = SimulatedBoard(0)
    board.send_frame(*extras.pid_frame(extras.PID_QUERY))
    assert pid_answer(board)["state_name"] == "RUNNING"
    board.send_frame(*extras.pid_frame(extras.PID_SET_GAINS, 12.5, 0.45, 3.1))
    state = pid_answer(board)
    assert (state["kp"], state["ki"], state["kd"]) == (12.5, 0.45, 3.1)
    board.send_frame(*extras.pid_frame(extras.PID_AUTOTUNE_START))        # no set-point yet: the order is refused, as the firmware does
    assert pid_answer(board)["state_name"] == "RUNNING"
    board.send_frame(wire.CAN_ID_SOLDER_SETPOINT, (200).to_bytes(2, "big"))
    board.read_frame()
    board.send_frame(*extras.pid_frame(extras.PID_AUTOTUNE_START))
    assert pid_answer(board)["state_name"] == "AUTOTUNING"
    for _ in range(8):
        board.read_frame()
    board.send_frame(*extras.pid_frame(extras.PID_QUERY))
    done = pid_answer(board)
    assert done["state_name"] == "AUTOTUNE_DONE" and (done["kp"], done["ki"], done["kd"]) == (12.5, 0.45, 3.1)  # the gains the simulated autotune found
    board.send_frame(*extras.pid_frame(extras.PID_AUTOTUNE_START))
    pid_answer(board)
    board.send_frame(*extras.pid_frame(extras.PID_AUTOTUNE_ABORT))
    assert pid_answer(board)["state_name"] == "RUNNING"


def test_a_plan_can_read_the_pid_state():
    plan = {"format": 1, "name": "pid", "steps": [{"do": "send", "id": "0x1BA", "data": ""},
                                                   {"do": "expect_frame", "id": "0x1BA", "within_ms": 200, "length": 8}]}
    assert tp.run_plan(plan, SimulatedBoard(0)).outcome == tp.PASS


def test_a_trace_replays_only_what_arrived_not_what_the_monitor_transmitted():
    text = ";$FILEVERSION=1.1\n     1)        0.0  Tx    0110  0   \n     2)        5.0  Rx    0111  2   0001\n     3)        9.0  Tx    0130  2   00A0\n"
    asc = "   0.000000 1  110             Tx   d 0 \n   0.005000 1  111             Rx   d 2 0001\n"
    assert [(f[1], f[2]) for f in parse_trace(text)] == [(0x111, b"\x00\x01")]
    assert [(f[1], f[2]) for f in parse_trace(asc)] == [(0x111, b"\x00\x01")]


def test_the_history_command_lists_the_evidence_records_and_fails_on_one_that_was_edited(tmp_path, capsys):
    from urtc_can import evidence

    good = evidence.build(kind="test", outcome="pass", timestamp_utc="2026-01-02T10:00:00Z", tool="URTC-TESTER", tool_version="0.4.3", subject={"name": "head-1"})
    (tmp_path / "urtc_evidence_a.json").write_text(json.dumps(good), encoding="utf-8")
    assert tester_cli.main(["history", str(tmp_path)]) == tester_cli.EXIT_PASS
    assert "URTC-TESTER" in capsys.readouterr().out
    assert tester_cli.main(["history", str(tmp_path), "--json"]) == tester_cli.EXIT_PASS
    assert json.loads(capsys.readouterr().out)["summary"]["valid"] == 1
    edited = dict(good, outcome="fail")                                  # changed after it was written: its digest no longer matches
    (tmp_path / "urtc_evidence_b.json").write_text(json.dumps(edited), encoding="utf-8")
    assert tester_cli.main(["history", str(tmp_path)]) == tester_cli.EXIT_FAIL
    assert "NOT VALID" in capsys.readouterr().out
    assert tester_cli.main(["history", str(tmp_path / "missing")]) == tester_cli.EXIT_USAGE
