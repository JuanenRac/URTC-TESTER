# =============================================================================
# URTC Tester - the Qt Quick deck can search for the bus speed
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
import unittest
from unittest import mock

try:
    import qt_tester
except ImportError:  # PySide6 is not installed
    qt_tester = None


@unittest.skipIf(qt_tester is None, "PySide6 is not available")
class QtAutodetectTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(qt_tester, "save_config", return_value=True)
        self.saved = patcher.start()
        self.addCleanup(patcher.stop)
        self.bridge = qt_tester.TesterQtBridge()
        self.bridge._log = lambda message: None
        self.results = []
        self.bridge._bitrateDetected.connect(self.results.append)

    def test_the_speed_the_scan_finds_is_reported(self):
        with mock.patch("tester_autodetect.scan_bitrates", return_value="250 kbit/s"):
            self.bridge._autodetect_worker("COM9")
        self.assertEqual(self.results, ["250 kbit/s"])

    def test_a_silent_bus_reports_nothing_found(self):
        with mock.patch("tester_autodetect.scan_bitrates", return_value=None):
            self.bridge._autodetect_worker("COM9")
        self.assertEqual(self.results, [""])

    def test_a_failing_adapter_never_raises_into_the_deck(self):
        with mock.patch("tester_autodetect.scan_bitrates", side_effect=OSError("port busy")):
            self.bridge._autodetect_worker("COM9")
        self.assertEqual(self.results, [""])

    def test_a_found_speed_replaces_the_selected_one_and_is_remembered(self):
        self.bridge._on_bitrate_detected("125 kbit/s")
        self.assertEqual(self.bridge.selectedBitrate, "125 kbit/s")
        self.saved.assert_called_with({"bitrate": "125 kbit/s"})

    def test_no_speed_found_keeps_the_selected_one(self):
        before = self.bridge.selectedBitrate
        self.bridge._on_bitrate_detected("")
        self.assertEqual(self.bridge.selectedBitrate, before)


if __name__ == "__main__":
    unittest.main()
