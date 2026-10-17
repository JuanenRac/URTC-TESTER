# =============================================================================
# URTC Tester - the safe-off frames and the limits of the heaters
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The firmware only processes the hotend frame (0x170) when it has 6 bytes, and refuses (with a latched critical error) a setpoint above 445 C. The Qt deck had its own copy of the
frames, with a 5-byte "safe off" the firmware ignored, and offered 450 C; it now uses the one encoder these tests cover."""
import unittest

import advanced_protocol as protocol
from tester_config import CAN_ID_3DP_THERMAL_MOTION, CAN_ID_HOTAIR_CMD, CAN_ID_SOLDER_SETPOINT, SETPOINT_MAX_C

try:
    import qt_tester
except ImportError:  # PySide6 is not installed
    qt_tester = None


class EncoderTests(unittest.TestCase):
    def test_the_hotend_safe_off_has_the_six_bytes_the_firmware_needs(self):
        refresh, off, _interval = protocol.watchdog_frames("printer_heater", 200, 0)
        self.assertEqual(refresh[0], CAN_ID_3DP_THERMAL_MOTION)
        self.assertEqual(len(refresh[1]), 6)
        self.assertEqual(off, (CAN_ID_3DP_THERMAL_MOTION, b"\x00\x00\x01\x00\x00\x00"))

    def test_the_setpoint_ceiling_is_the_firmwares(self):
        self.assertEqual(SETPOINT_MAX_C, 445)
        for kind, can_id in (("solder", CAN_ID_SOLDER_SETPOINT), ("hotair", CAN_ID_HOTAIR_CMD)):
            refresh, _off, _interval = protocol.watchdog_frames(kind, SETPOINT_MAX_C, 0)
            self.assertEqual(refresh[0], can_id)
            self.assertEqual(int.from_bytes(refresh[1][:2], "big"), 445)
            with self.assertRaises(ValueError):
                protocol.watchdog_frames(kind, SETPOINT_MAX_C + 1, 0)


@unittest.skipIf(qt_tester is None, "PySide6 is not available")
class QtDeckTests(unittest.TestCase):
    def _bridge(self):
        bridge = qt_tester.TesterQtBridge()
        bridge._require_profile = lambda allowed, action: True
        started, stopped = [], []
        bridge._start_watchdog = lambda key, interval, frame, off: started.append((key, frame, off))
        bridge._stop_watchdog = lambda key, off=None: stopped.append((key, off))
        bridge._log = lambda text: None
        return bridge, started, stopped

    def test_the_safe_off_of_the_heater_in_the_deck_has_six_bytes(self):
        bridge, started, stopped = self._bridge()
        bridge.setWatchdogOutput("printer_heater", True, "220", "0")
        self.assertEqual(len(started[0][2][1]), 6)
        bridge.setWatchdogOutput("printer_heater", False, "220", "0")
        self.assertEqual(stopped[0][1], (CAN_ID_3DP_THERMAL_MOTION, b"\x00\x00\x01\x00\x00\x00"))

    def test_the_deck_refuses_a_setpoint_above_the_ceiling(self):
        bridge, started, _stopped = self._bridge()
        bridge.setWatchdogOutput("solder", True, "446", "0")
        self.assertEqual(started, [])
        bridge.setWatchdogOutput("solder", True, "445", "0")
        self.assertEqual(len(started), 1)


if __name__ == "__main__":
    unittest.main()


class DrillTests(unittest.TestCase):
    def test_the_drill_is_refreshed_and_its_off_is_the_brake(self):
        refresh, off, interval = protocol.watchdog_frames("drill", 120, 1)
        self.assertEqual(refresh, (protocol.CAN_ID_DRILL_CMD, bytes([120, 1])))
        self.assertEqual(off, (protocol.CAN_ID_DRILL_CMD, b"\x00\x00"))
        self.assertLess(interval, 0.25, "faster than the 250 ms watchdog of the firmware")

    @unittest.skipIf(qt_tester is None, "PySide6 is not available")
    def test_the_deck_keeps_a_running_drill_alive_and_speed_zero_stops_it(self):
        bridge = qt_tester.TesterQtBridge()
        bridge._require_profile = lambda allowed, action: True
        started, stopped = [], []
        bridge._start_watchdog = lambda key, interval, frame, off: started.append((key, interval, frame))
        bridge._stop_watchdog = lambda key, off=None: stopped.append((key, off))
        bridge._log = lambda text: None
        bridge.sendDrill("120", "clockwise")
        self.assertEqual(started, [("drill", 0.15, (protocol.CAN_ID_DRILL_CMD, bytes([120, 0])))])
        bridge.sendDrill("0", "clockwise")
        self.assertEqual(stopped, [("drill", (protocol.CAN_ID_DRILL_CMD, b"\x00\x00"))])


class StopTests(unittest.TestCase):
    @unittest.skipIf(qt_tester is None, "PySide6 is not available")
    def test_the_deck_has_a_stop_that_sends_zero_steps(self):
        bridge = qt_tester.TesterQtBridge()
        sent = []

        class Transport:
            def send_frame(self, can_id, data):
                sent.append((can_id, data))

        bridge._transport = Transport()
        bridge._log = lambda text: None
        bridge.stopMotion()
        self.assertEqual(sent, [(qt_tester.CAN_ID_MOTION_CMD, b"\x00\x00\x00\x00\x00")])

    def test_every_language_has_the_stop_texts(self):
        from pathlib import Path
        for lng in sorted((Path(__file__).resolve().parent.parent / "language").glob("*.lng")):
            text = lng.read_text(encoding="utf-8")
            for key in ("BTN_STOP_MOTION=", "LOG_TOOL_STOP=", "QT_STOP_MOTION=", "LOG_DRILL_STOPPED="):
                self.assertIn("\n" + key, text, f"{lng.name} lacks {key}")


class SmallFixesTests(unittest.TestCase):
    def test_every_tool_of_the_free_configuration_is_named(self):
        for selection in range(1, len(protocol.TOOL_NAMES) + 1):
            self.assertIsNotNone(protocol.decode_free_tool_config(bytes([0x1F, selection]))["tool_name"], selection)
        self.assertIsNone(protocol.decode_free_tool_config(bytes([0x1F, 0]))["tool_name"])
        self.assertIsNone(protocol.decode_free_tool_config(bytes([0x1F, len(protocol.TOOL_NAMES) + 1]))["tool_name"])

    def test_a_paste_pulse_cannot_be_continuous(self):
        with self.assertRaises(ValueError):
            protocol.paste_pulse_frame(0, 50, 0)
        self.assertEqual(protocol.paste_pulse_frame(0, 50, 10)[1], bytes([0, 50, 10]))
