# =============================================================================
# URTC Tester - the self-test in the Qt Quick deck: gate, safe commands, result lines
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
import unittest
from unittest import mock

import tester_config

try:
    import qt_tester
except ImportError:  # PySide6 is not installed
    qt_tester = None


class FakeTransport:
    """Answers the queries and the telemetry of a soldering iron; records what is sent."""

    def __init__(self, silent=()):
        self.sent = []
        self.inbox = []
        self.silent = set(silent)

    def send_frame(self, can_id, data):
        self.sent.append((can_id, bytes(data)))
        reply = {
            0x110: (qt_tester.CAN_ID_ACTIVE_TOOL_RESP, bytes([0, 0, 0, 0])),
            qt_tester.CAN_ID_QUERY_VERSION: (qt_tester.CAN_ID_VERSION_RESPONSE, b"\x00" * 8),
            qt_tester.CAN_ID_SOLDER_SETPOINT: (tester_config.CAN_ID_SOLDER_TELEMETRY, b"\x00\x00"),
        }.get(can_id)
        if reply is not None and reply[0] not in self.silent:
            self.inbox.append(reply)

    def read_frame(self, timeout=0.1):
        return self.inbox.pop(0) if self.inbox else None

    def close(self):
        pass


@unittest.skipIf(qt_tester is None, "PySide6 is not available")
class QtSelfTestTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(qt_tester, "save_config", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.bridge = qt_tester.TesterQtBridge()
        self.logs = []
        self.bridge._log = self.logs.append
        # a soldering iron detected on an armed (not listen-only) connection
        self.transport = FakeTransport()
        self.bridge._transport = self.transport
        self.bridge._listen_only = False
        self.bridge._active_tool_id = 0
        self.bridge._selected_tool_id = 0

    def _run_worker(self):
        self.bridge._self_test_running = True
        self.bridge._self_test_worker(self.transport, 0)

    def test_the_gate_needs_armed_active_checks(self):
        self.assertTrue(self.bridge.canSelfTest)
        self.bridge._listen_only = True
        self.assertFalse(self.bridge.canSelfTest)

    def test_the_gate_needs_the_detected_tool_to_be_the_selected_profile(self):
        self.bridge._selected_tool_id = 5
        self.assertFalse(self.bridge.canSelfTest)
        self.bridge._selected_tool_id = 0
        self.bridge._active_tool_id = -1
        self.assertFalse(self.bridge.canSelfTest)

    def test_the_gate_is_closed_while_busy_or_disconnected(self):
        self.bridge._busy = True
        self.assertFalse(self.bridge.canSelfTest)
        self.bridge._busy = False
        self.bridge._transport = None
        self.assertFalse(self.bridge.canSelfTest)

    def test_a_blocked_run_sends_nothing(self):
        self.bridge._listen_only = True
        self.bridge.runSelfTest()
        self.assertEqual(self.transport.sent, [])
        self.assertTrue(any(line.startswith("SELFTEST_BLOCKED") for line in self.logs))

    def test_a_second_run_cannot_start_while_one_is_running(self):
        self.bridge._self_test_running = True
        with mock.patch.object(qt_tester.threading, "Thread") as thread:
            self.bridge.runSelfTest()
        thread.assert_not_called()

    def test_starting_a_run_switches_the_armed_outputs_off_first(self):
        stopped = []
        self.bridge._stop_all_watchdogs = lambda: stopped.append(True)
        with mock.patch.object(qt_tester.threading, "Thread"):
            self.bridge.runSelfTest()
        self.assertEqual(stopped, [True])
        self.assertTrue(self.bridge.busy)
        self.assertTrue(self.bridge.selfTestRunning)

    def test_the_run_only_sends_queries_and_a_zero_setpoint(self):
        self._run_worker()
        self.assertEqual(
            [can_id for can_id, _data in self.transport.sent],
            [0x110, qt_tester.CAN_ID_QUERY_VERSION, qt_tester.CAN_ID_SOLDER_SETPOINT],
        )
        self.assertEqual(self.transport.sent[-1][1], b"\x00\x00")

    def test_a_passing_run_lists_pass_lines_and_frees_the_deck(self):
        self._run_worker()
        statuses = [line["status"] for line in self.bridge.selfTestLines]
        self.assertEqual(statuses.count("PASS"), 3)
        self.assertNotIn("FAIL", statuses)
        self.assertFalse(self.bridge.selfTestRunning)
        self.assertFalse(self.bridge.busy)
        self.assertTrue(any(line.startswith("SELFTEST_COMPLETE failed=0") for line in self.logs))

    def test_missing_telemetry_shows_a_fail_line(self):
        self.transport.silent = {tester_config.CAN_ID_SOLDER_TELEMETRY}
        self._run_worker()
        self.assertIn("FAIL", [line["status"] for line in self.bridge.selfTestLines])
        self.assertTrue(any(line.startswith("SELFTEST_COMPLETE failed=1") for line in self.logs))

    def test_a_bus_error_ends_the_run_and_frees_the_deck(self):
        def boom(can_id, data):
            raise OSError("adapter unplugged")

        self.transport.send_frame = boom
        self._run_worker()
        self.assertFalse(self.bridge.busy)
        self.assertTrue(any(line.startswith("SELFTEST_FAILED") for line in self.logs))

    def test_a_new_run_clears_the_previous_lines(self):
        self.bridge._self_test_lines = [{"status": "PASS", "text": "old"}]
        with mock.patch.object(qt_tester.threading, "Thread"):
            self.bridge.runSelfTest()
        self.assertEqual(self.bridge.selfTestLines, [])


if __name__ == "__main__":
    unittest.main()
