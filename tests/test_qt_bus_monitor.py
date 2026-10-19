# =============================================================================
# URTC Tester - the Qt Quick deck's raw bus monitor
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
import os
import tempfile
import threading
import unittest
from unittest import mock

try:
    import qt_tester
except ImportError:  # PySide6 is not installed
    qt_tester = None


class _Transport:
    """Serves a fixed list of frames, then asks the monitor to stop."""

    def __init__(self, frames, stop):
        self._frames = list(frames)
        self._stop = stop

    def read_frame(self, timeout=0.1):
        if self._frames:
            return self._frames.pop(0)
        self._stop.wait(timeout)
        return None


@unittest.skipIf(qt_tester is None, "PySide6 is not available")
class QtBusMonitorTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(qt_tester, "save_config", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.bridge = qt_tester.TesterQtBridge()
        self.bridge._log = lambda message: None

    def _record(self, *frames):
        for can_id, data in frames:
            self.bridge._record_monitor_frame(can_id, data)

    def test_a_recorded_frame_shows_its_id_length_and_hex_data(self):
        self._record((0x1A0, b"\x01\x02"))
        self.assertEqual(self.bridge.monitorCount, 1)
        line = self.bridge.monitorLines[0]
        self.assertIn("0x1A0", line)
        self.assertIn("[2]", line)
        self.assertIn("0102", line)

    def test_the_id_filter_hides_other_ids(self):
        self.bridge.setMonitorIds("1A0")
        self._record((0x1A0, b"\x01"), (0x110, b"\x02"))
        self.assertEqual(self.bridge.monitorCount, 1)

    def test_only_changes_hides_a_repeated_payload(self):
        self.bridge.setMonitorOnlyChanges(True)
        self._record((0x1A0, b"\x01"), (0x1A0, b"\x01"), (0x1A0, b"\x02"))
        self.assertEqual(self.bridge.monitorCount, 2)

    def test_the_table_is_bounded_and_keeps_the_newest_frames(self):
        for index in range(self.bridge.MONITOR_MAX_ROWS + 50):
            self.bridge._record_monitor_frame(0x100, bytes([index % 256]))
        self.assertEqual(self.bridge.monitorCount, self.bridge.MONITOR_MAX_ROWS)

    def test_clear_empties_the_table(self):
        self._record((0x1A0, b"\x01"))
        self.bridge.clearBusMonitor()
        self.assertEqual(self.bridge.monitorCount, 0)

    def test_export_writes_a_trc_and_an_asc_and_refuses_when_empty(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(qt_tester, "LOGS_FOLDER", folder):
            self.assertEqual(self.bridge.exportMonitor("trc"), "")
            self._record((0x1A0, b"\x01\x02"))
            trc = self.bridge.exportMonitor("trc")
            asc = self.bridge.exportMonitor("asc")
            self.assertTrue(trc.endswith(".trc") and os.path.isfile(trc))
            self.assertTrue(asc.endswith(".asc") and os.path.isfile(asc))
            self.assertIn("01A0", open(trc, encoding="ascii").read())
            self.assertEqual(self.bridge.exportMonitor("csv"), "")

    def test_the_monitor_reads_until_stopped_then_releases_the_bus(self):
        stop = threading.Event()
        self.bridge._transport = _Transport([(0x1A0, b"\x01"), (0x110, b"\x02")], stop)
        self.bridge.startBusMonitor()
        self.assertTrue(self.bridge.isMonitoring)
        self.assertTrue(self.bridge._busy)
        for _ in range(100):
            if self.bridge.monitorCount >= 2:
                break
            threading.Event().wait(0.05)
        self.assertEqual(self.bridge.monitorCount, 2)
        self.bridge.stopBusMonitor()
        stop.set()
        self.bridge._monitor_thread.join(timeout=3)
        self.assertFalse(self.bridge.isMonitoring)
        self.assertFalse(self.bridge._busy)

    def test_it_will_not_start_without_a_connection(self):
        self.bridge.startBusMonitor()
        self.assertFalse(self.bridge.isMonitoring)


if __name__ == "__main__":
    unittest.main()
