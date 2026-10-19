# =============================================================================
# URTC Tester - the self-test shared by the Qt Quick deck and the Tkinter window
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The self-test steps and runner, checked against a fake bus (no hardware)."""
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

ROOT = Path(__file__).resolve().parent.parent
LANGUAGES = ("english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese")


class FakeBus:
    """Answers the frames a tool would answer; records everything sent."""

    def __init__(self, tool_id, answers=None, silent=()):
        self.tool_id = tool_id
        self.sent: list[tuple[int, bytes]] = []
        self.silent = set(silent)
        self.answers = {
            cfg.CAN_ID_ACTIVE_TOOL_RESP: bytes([tool_id, 0, 0, 0]),
            cfg.CAN_ID_VERSION_RESPONSE: b"\x00" * 8,
        }
        self.answers.update(answers or {})

    def exchange(self, send, expect_id, timeout):
        if send is not None:
            self.sent.append(send)
        if expect_id in self.silent:
            return None
        return self.answers.get(expect_id, b"\x00\x00")


class SelfTestRunnerTests(unittest.TestCase):
    def test_every_step_command_is_a_safe_at_rest_value(self):
        for tool_id, steps in st.SELF_TEST_STEPS.items():
            for _key, command_id, data, _expect in steps:
                if command_id is None:
                    continue
                self.assertTrue(set(data) <= {0}, f"tool {tool_id}: command {command_id:#x} carries a non-zero value")

    def test_the_two_generic_queries_run_for_every_tool(self):
        for tool_id in cfg.TOOL_NAMES:
            bus = FakeBus(tool_id)
            result = st.run_self_test(tool_id, bus.exchange)
            self.assertIn((cfg.CAN_ID_QUERY_ACTIVE_TOOL, b""), bus.sent)
            self.assertIn((cfg.CAN_ID_QUERY_VERSION, b"\x00"), bus.sent)
            self.assertEqual(result.failed, 0, tool_id)

    def test_a_soldering_iron_gets_a_zero_setpoint_and_passes_when_telemetry_arrives(self):
        bus = FakeBus(0)
        result = st.run_self_test(0, bus.exchange)
        self.assertIn((cfg.CAN_ID_SOLDER_SETPOINT, struct.pack(">H", 0)), bus.sent)
        statuses = [line.status for line in result.lines]
        self.assertEqual(statuses.count(st.PASS), 3)
        self.assertEqual(result.failed, 0)

    def test_missing_telemetry_is_a_failure_not_a_pass(self):
        bus = FakeBus(0, silent={cfg.CAN_ID_SOLDER_TELEMETRY})
        result = st.run_self_test(0, bus.exchange)
        self.assertEqual(result.failed, 1)
        self.assertEqual(result.lines[-2].status, st.FAIL)

    def test_a_wrong_active_tool_is_a_failure(self):
        bus = FakeBus(0, answers={cfg.CAN_ID_ACTIVE_TOOL_RESP: bytes([5, 0, 0, 0])})
        result = st.run_self_test(0, bus.exchange)
        self.assertGreaterEqual(result.failed, 1)

    def test_a_motion_tool_sends_only_the_two_queries(self):
        tool_id = sorted(cfg.MOTION_TOOL_IDS)[0]
        bus = FakeBus(tool_id)
        result = st.run_self_test(tool_id, bus.exchange)
        self.assertEqual(len(bus.sent), 2)
        self.assertEqual([line.status for line in result.lines][-2], st.INFO)

    def test_the_scan_probe_is_information_only(self):
        bus = FakeBus(11)
        result = st.run_self_test(11, bus.exchange)
        self.assertEqual(len(bus.sent), 2)
        self.assertEqual(result.failed, 0)

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


class SelfTestTextsTests(unittest.TestCase):
    KEYS = (
        "SELFTEST_STEP_SOLDER", "SELFTEST_STEP_DRILL", "SELFTEST_STEP_LASER", "SELFTEST_STEP_PRINTER", "SELFTEST_STEP_AOI",
        "SELFTEST_STEP_VACUUM", "SELFTEST_STEP_SCAN_PROBE", "SELFTEST_MOTION_INFO", "SELFTEST_NO_STEPS", "SELFTEST_DONE",
        "LOG_SELFTEST_TESTING", "LOG_SELFTEST_ACTIVE_TOOL", "LOG_SELFTEST_VERSION", "BTN_RUN_SELF_TEST", "MSG_SELF_TEST_CONFIRM",
        "TITLE_RUN_SELF_TEST_Q",
    )

    def test_every_step_key_has_text_in_every_language(self):
        used = {step[0] for steps in st.SELF_TEST_STEPS.values() for step in steps}
        for language in LANGUAGES:
            table = load_language(language)
            self.assertEqual([k for k in sorted(used | set(self.KEYS)) if not table.get(k)], [], language)

    def test_the_texts_are_translated_not_copied_from_english(self):
        english = load_language("english")
        for language in LANGUAGES[1:]:
            table = load_language(language)
            same = [k for k in self.KEYS if k.startswith("SELFTEST_") and table[k] == english[k]]
            self.assertEqual(same, [], language)

    def test_placeholders_match_in_every_language(self):
        english = load_language("english")
        for language in LANGUAGES[1:]:
            table = load_language(language)
            for key in self.KEYS:
                self.assertEqual(sorted(re.findall(r"\{\w+\}", english[key])), sorted(re.findall(r"\{\w+\}", table[key])), (language, key))


if __name__ == "__main__":
    unittest.main()
