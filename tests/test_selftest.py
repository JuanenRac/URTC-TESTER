# =============================================================================
# URTC Tester - the self-test shared by the Qt Quick deck, the plans and the command line
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The self-test steps and runner: what each answer means (pass, fail or unknown), checked against a fake bus and the simulated heads (no hardware)."""
from __future__ import annotations

import re
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tester_config as cfg
import tester_selftest as st
from tester_config import load_language
from tester_simulator import SimulatedBoard

ROOT = Path(__file__).resolve().parent.parent
LANGUAGES = ("english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese")

# A healthy tool at rest answers these (the frames of the protocol, not just any bytes).
HEALTHY = {
    cfg.CAN_ID_SOLDER_TELEMETRY: struct.pack(">H", 25),
    cfg.CAN_ID_3DP_HOTEND_TELEM: struct.pack(">H", 25),
    cfg.CAN_ID_DRILL_TELEMETRY: struct.pack(">HB", 0, 0),
    cfg.CAN_ID_LASER_TELEMETRY: bytes([0]),
    cfg.CAN_ID_AOI_TELEMETRY: bytes([0]),
    cfg.CAN_ID_VACUUM_TELEMETRY: struct.pack(">HB", 100, 0),
}
VERSION_APPLICATION = bytes([0]) + struct.pack(">I", 0x10) + struct.pack(">H", 0) + bytes([4])


class FakeBus:
    """Answers the frames a tool would answer; records everything sent."""

    def __init__(self, tool_id, answers=None, silent=()):
        self.tool_id = tool_id
        self.sent: list[tuple[int, bytes]] = []
        self.silent = set(silent)
        self.answers = {
            cfg.CAN_ID_ACTIVE_TOOL_RESP: bytes([tool_id, 0, 0, 0]),
            cfg.CAN_ID_VERSION_RESPONSE: VERSION_APPLICATION,
            **HEALTHY,
        }
        self.answers.update(answers or {})

    def exchange(self, send, expect_id, timeout):
        if send is not None:
            self.sent.append(send)
        if expect_id in self.silent:
            return None
        return self.answers.get(expect_id)


def simulated_exchange(board):
    """The exchange primitive over a simulated head: send, then read until the expected identifier shows up."""
    def exchange(send, expect_id, timeout):
        if send is not None:
            board.send_frame(*send)
        for _ in range(20):
            frame = board.read_frame(0.01)
            if frame is not None and frame[0] == expect_id:
                return frame[1]
        return None
    return exchange


def statuses(result):
    return [line.status for line in result.lines]


class SelfTestRunnerTests(unittest.TestCase):
    def test_every_step_command_is_a_safe_at_rest_value(self):
        for tool_id, steps in st.SELF_TEST_STEPS.items():
            for _key, command_id, data, _expect in steps:
                if command_id is None:
                    continue
                self.assertTrue(set(data) <= {0}, f"tool {tool_id}: command {command_id:#x} carries a non-zero value")

    def test_every_step_that_expects_an_answer_has_a_judge(self):
        for steps in st.SELF_TEST_STEPS.values():
            for key, _command, _data, expect_id in steps:
                self.assertEqual(expect_id is not None, key in st.CHECKS, key)

    def test_the_two_generic_queries_run_for_every_tool(self):
        for tool_id in cfg.TOOL_NAMES:
            bus = FakeBus(tool_id)
            result = st.run_self_test(tool_id, bus.exchange)
            self.assertIn((cfg.CAN_ID_QUERY_ACTIVE_TOOL, b""), bus.sent)
            self.assertIn((cfg.CAN_ID_QUERY_VERSION, b"\x00"), bus.sent)
            self.assertEqual(result.failed, 0, tool_id)

    def test_a_soldering_iron_gets_a_zero_setpoint_and_passes_when_its_telemetry_makes_sense(self):
        bus = FakeBus(0)
        result = st.run_self_test(0, bus.exchange)
        self.assertIn((cfg.CAN_ID_SOLDER_SETPOINT, struct.pack(">H", 0)), bus.sent)
        self.assertEqual(statuses(result).count(st.PASS), 4)  # active tool, version, telemetry and the closing line
        self.assertEqual(result.failed, 0)
        self.assertEqual(result.verdict, st.PASS)

    def test_missing_telemetry_is_a_failure_not_a_pass(self):
        bus = FakeBus(0, silent={cfg.CAN_ID_SOLDER_TELEMETRY})
        result = st.run_self_test(0, bus.exchange)
        self.assertEqual(result.failed, 1)
        self.assertEqual(result.lines[-2].status, st.FAIL)
        self.assertEqual(result.verdict, st.FAIL)

    def test_a_wrong_active_tool_is_a_failure(self):
        bus = FakeBus(0, answers={cfg.CAN_ID_ACTIVE_TOOL_RESP: bytes([5, 0, 0, 0])})
        result = st.run_self_test(0, bus.exchange)
        self.assertEqual(result.lines[1].status, st.FAIL)
        self.assertEqual(result.verdict, st.FAIL)

    def test_a_fault_flag_in_the_quick_state_is_a_failure(self):
        for flags in (bytes([0, 1, 0, 0]), bytes([0, 0, 1, 0]), bytes([0, 0, 0, 0, 2])):
            result = st.run_self_test(0, FakeBus(0, answers={cfg.CAN_ID_ACTIVE_TOOL_RESP: flags}).exchange)
            self.assertEqual(result.lines[1].status, st.FAIL, flags)

    def test_a_board_that_is_still_booting_is_unknown(self):
        result = st.run_self_test(0, FakeBus(0, answers={cfg.CAN_ID_ACTIVE_TOOL_RESP: bytes([0, 0, 0, 1])}).exchange)
        self.assertEqual(result.lines[1].status, st.UNKNOWN)
        self.assertEqual(result.verdict, st.UNKNOWN)

    def test_an_answer_too_short_to_read_is_unknown_never_a_pass(self):
        for answers in ({cfg.CAN_ID_ACTIVE_TOOL_RESP: b"\x00"}, {cfg.CAN_ID_VERSION_RESPONSE: b"\x00\x00"}, {cfg.CAN_ID_SOLDER_TELEMETRY: b"\x00"}):
            result = st.run_self_test(0, FakeBus(0, answers=answers).exchange)
            self.assertIn(st.UNKNOWN, statuses(result), answers)
            self.assertNotEqual(result.verdict, st.PASS, answers)

    def test_the_bootloader_answering_the_version_query_is_a_failure(self):
        bootloader = bytes([1]) + VERSION_APPLICATION[1:]
        result = st.run_self_test(0, FakeBus(0, answers={cfg.CAN_ID_VERSION_RESPONSE: bootloader}).exchange)
        self.assertEqual(result.lines[2].status, st.FAIL)

    def test_a_temperature_over_the_limit_fails_and_a_warm_tip_is_unknown(self):
        over = st.run_self_test(0, FakeBus(0, answers={cfg.CAN_ID_SOLDER_TELEMETRY: struct.pack(">H", 800)}).exchange)
        self.assertEqual(over.lines[-2].status, st.FAIL)
        warm = st.run_self_test(0, FakeBus(0, answers={cfg.CAN_ID_SOLDER_TELEMETRY: struct.pack(">H", 200)}).exchange)
        self.assertEqual(warm.lines[-2].status, st.UNKNOWN)
        self.assertEqual(warm.verdict, st.UNKNOWN)
        hot_printer = st.run_self_test(10, FakeBus(10, answers={cfg.CAN_ID_3DP_HOTEND_TELEM: struct.pack(">H", 350)}).exchange)
        self.assertEqual(hot_printer.lines[-2].status, st.FAIL)  # over the 300 degree limit of the printer head

    def test_the_limits_come_from_the_settings_and_a_bad_value_keeps_the_default(self):
        limits = cfg.selftest_limits({"selftest_limits": {"cold_c": 90, "idle_rpm": "fast", "solder_max_c": True, "printer_max_c": 10_000}})
        self.assertEqual(limits["cold_c"], 90)
        self.assertEqual((limits["idle_rpm"], limits["solder_max_c"], limits["printer_max_c"]), (300, 450, 300))
        bus = FakeBus(0, answers={cfg.CAN_ID_SOLDER_TELEMETRY: struct.pack(">H", 80)})
        self.assertEqual(st.run_self_test(0, bus.exchange).lines[-2].status, st.UNKNOWN)  # warm for the default limit of 60
        self.assertEqual(st.run_self_test(0, bus.exchange, limits=limits).lines[-2].status, st.PASS)
        self.assertEqual(cfg.selftest_limits({}), cfg.SELFTEST_LIMIT_DEFAULTS)

    def test_a_drill_that_is_stopped_passes_and_one_still_turning_is_unknown(self):
        self.assertEqual(st.run_self_test(5, FakeBus(5).exchange).verdict, st.PASS)
        turning = st.run_self_test(5, FakeBus(5, answers={cfg.CAN_ID_DRILL_TELEMETRY: struct.pack(">HB", 6000, 0)}).exchange)
        self.assertEqual(turning.lines[-2].status, st.UNKNOWN)
        self.assertEqual(turning.verdict, st.UNKNOWN)

    def test_a_field_outside_the_range_of_the_protocol_is_a_failure(self):
        for tool_id, frame_id, data in (
            (9, cfg.CAN_ID_LASER_TELEMETRY, bytes([7])),
            (8, cfg.CAN_ID_AOI_TELEMETRY, bytes([2])),
            (4, cfg.CAN_ID_VACUUM_TELEMETRY, struct.pack(">HB", 5000, 0)),
            (4, cfg.CAN_ID_VACUUM_TELEMETRY, struct.pack(">HB", 100, 3)),
            (5, cfg.CAN_ID_DRILL_TELEMETRY, struct.pack(">HB", 0, 9)),
        ):
            result = st.run_self_test(tool_id, FakeBus(tool_id, answers={frame_id: data}).exchange)
            self.assertEqual(result.lines[-2].status, st.FAIL, (tool_id, data))

    def test_a_tool_with_nothing_to_measure_is_unknown_not_a_pass(self):
        motion = sorted(cfg.MOTION_TOOL_IDS)[0]
        bus = FakeBus(motion)
        result = st.run_self_test(motion, bus.exchange)
        self.assertEqual(len(bus.sent), 2)
        self.assertEqual(result.failed, 0)
        self.assertEqual(result.lines[-2].status, st.UNKNOWN)
        self.assertEqual(result.verdict, st.UNKNOWN)

    def test_the_scan_probe_cannot_be_decided_without_a_physical_event(self):
        bus = FakeBus(11)
        result = st.run_self_test(11, bus.exchange)
        self.assertEqual(len(bus.sent), 2)
        self.assertEqual(result.failed, 0)
        self.assertEqual(result.verdict, st.UNKNOWN)

    def test_a_tool_with_no_steps_defined_is_unknown(self):
        unlisted = next(t for t in cfg.TOOL_NAMES if t not in st.SELF_TEST_STEPS and t not in cfg.MOTION_TOOL_IDS)
        self.assertEqual(st.run_self_test(unlisted, FakeBus(unlisted).exchange).verdict, st.UNKNOWN)

    def test_the_closing_line_carries_the_verdict_and_is_not_counted(self):
        result = st.run_self_test(0, FakeBus(0, silent={cfg.CAN_ID_SOLDER_TELEMETRY}).exchange)
        last = result.lines[-1]
        self.assertTrue(last.summary)
        self.assertEqual(last.status, st.FAIL)
        self.assertEqual((result.passed, result.failed, result.unknown), (2, 1, 0))

    def test_the_drill_step_reports_that_a_drill_command_went_out(self):
        result = st.run_self_test(5, FakeBus(5).exchange)
        self.assertTrue(result.sent_drill_command)
        self.assertFalse(st.run_self_test(0, FakeBus(0).exchange).sent_drill_command)

    def test_a_stop_request_ends_the_run_before_the_next_command(self):
        bus = FakeBus(0)
        result = st.run_self_test(0, bus.exchange, stop=lambda: True)
        self.assertEqual(len(bus.sent), 1)
        self.assertLess(len(result.lines), 4)

    def test_every_line_is_also_given_to_the_emit_callback(self):
        seen = []
        result = st.run_self_test(8, FakeBus(8).exchange, emit=seen.append)
        self.assertEqual(seen, result.lines)

    def test_the_commands_listed_for_a_tool_are_the_ones_it_sends(self):
        for tool_id in cfg.TOOL_NAMES:
            bus = FakeBus(tool_id)
            st.run_self_test(tool_id, bus.exchange)
            self.assertEqual([c for c, _d in bus.sent], st.commands_sent(tool_id), tool_id)


class SelfTestAgainstTheSimulatedHeadTests(unittest.TestCase):
    """The same judgement over the head the tester simulates (the nearest to a board there is without one)."""

    def test_every_simulated_tool_with_telemetry_passes(self):
        for tool_id in (0, 4, 5, 8, 9, 10):
            board = SimulatedBoard(tool_id)
            result = st.run_self_test(tool_id, simulated_exchange(board), limits=cfg.selftest_limits({}))
            self.assertEqual(result.verdict, st.PASS, (tool_id, [str(line) for line in result.lines]))

    def test_a_simulated_fault_is_a_failure(self):
        for fault in ("system", "can", "thermal"):
            board = SimulatedBoard(0, fault=fault)
            self.assertEqual(st.run_self_test(0, simulated_exchange(board)).verdict, st.FAIL, fault)

    def test_a_simulated_head_that_answers_nothing_fails(self):
        self.assertEqual(st.run_self_test(0, simulated_exchange(SimulatedBoard(0, silent=True))).verdict, st.FAIL)

    def test_an_iron_that_is_still_hot_cannot_be_called_a_pass(self):
        board = SimulatedBoard(0)
        board.temperature = 300.0
        board.outputs["solder_setpoint_c"] = 300
        result = st.run_self_test(0, simulated_exchange(board))
        self.assertEqual(result.verdict, st.UNKNOWN)
        self.assertEqual(result.failed, 0)

    def test_a_simulated_tool_without_telemetry_is_unknown(self):
        self.assertEqual(st.run_self_test(11, simulated_exchange(SimulatedBoard(11))).verdict, st.UNKNOWN)


class SelfTestTextsTests(unittest.TestCase):
    DETAIL_KEYS = (
        "SELFTEST_D_NO_ANSWER", "SELFTEST_D_UNREADABLE", "SELFTEST_D_OUT_OF_RANGE", "SELFTEST_D_WRONG_TOOL", "SELFTEST_D_FAULTS", "SELFTEST_D_BOOTING",
        "SELFTEST_D_TOOL_OK", "SELFTEST_D_BOOTLOADER", "SELFTEST_D_UNKNOWN_RESPONDER", "SELFTEST_D_APPLICATION", "SELFTEST_D_TEMP_OVER",
        "SELFTEST_D_TEMP_HOT", "SELFTEST_D_TEMP_OK", "SELFTEST_D_RPM_TURNING", "SELFTEST_D_RPM_STOPPED", "SELFTEST_D_FIELDS_OK",
    )
    KEYS = (
        "SELFTEST_STEP_SOLDER", "SELFTEST_STEP_DRILL", "SELFTEST_STEP_LASER", "SELFTEST_STEP_PRINTER", "SELFTEST_STEP_AOI",
        "SELFTEST_STEP_VACUUM", "SELFTEST_STEP_SCAN_PROBE", "SELFTEST_MOTION_INFO", "SELFTEST_NO_STEPS", "SELFTEST_VERDICT",
        "QT_PLAN_OUTCOME_PASS", "QT_PLAN_OUTCOME_FAIL", "QT_PLAN_OUTCOME_UNKNOWN", "QT_PM_SELFTEST_UNKNOWN",
        "LOG_SELFTEST_TESTING", "LOG_SELFTEST_ACTIVE_TOOL", "LOG_SELFTEST_VERSION", "BTN_RUN_SELF_TEST", "MSG_SELF_TEST_CONFIRM",
        "TITLE_RUN_SELF_TEST_Q",
    ) + DETAIL_KEYS

    def test_every_step_key_has_text_in_every_language(self):
        used = {step[0] for steps in st.SELF_TEST_STEPS.values() for step in steps}
        for language in LANGUAGES:
            table = load_language(language)
            self.assertEqual([k for k in sorted(used | set(self.KEYS)) if not table.get(k)], [], language)

    def test_the_texts_are_translated_not_copied_from_english(self):
        english = load_language("english")
        for language in LANGUAGES[1:]:
            table = load_language(language)
            same = [k for k in self.KEYS if k.startswith(("SELFTEST_", "QT_PM_SELFTEST_")) and table[k] == english[k]
                    and k not in ("SELFTEST_D_TOOL_OK",)]
            # a text that is only a number and a unit (for instance "{value} RPM") reads the same everywhere
            same = [k for k in same if re.sub(r"\{\w+\}|RPM|°C|[ ,]", "", english[k])]
            self.assertEqual(same, [], language)

    def test_placeholders_match_in_every_language(self):
        english = load_language("english")
        for language in LANGUAGES[1:]:
            table = load_language(language)
            for key in self.KEYS:
                self.assertEqual(sorted(re.findall(r"\{\w+\}", english[key])), sorted(re.findall(r"\{\w+\}", table[key])), (language, key))

    def test_every_text_the_judge_uses_is_in_the_table(self):
        source = (ROOT / "tester_selftest.py").read_text(encoding="utf-8")
        used = set(re.findall(r'"(SELFTEST_D_[A-Z_]+)"', source))
        self.assertEqual(used, set(self.DETAIL_KEYS))

    def test_a_line_says_its_detail_in_the_language_of_the_program(self):
        try:
            cfg._translations = load_language("portuguese")
            result = st.run_self_test(0, FakeBus(0, silent={cfg.CAN_ID_SOLDER_TELEMETRY}).exchange)
        finally:
            cfg._translations = load_language("english")
        self.assertIn("sem resposta", result.lines[-2].text)
        self.assertIn("REPROVADO", result.lines[-1].text)


if __name__ == "__main__":
    unittest.main()
