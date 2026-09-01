# =============================================================================
# URTC Tester - Hardware-free assertions for Qt Quick control encoders
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
import unittest

import advanced_protocol as protocol
from tester_config import CAN_ID_CRIMPING_CMD, CAN_ID_MOTION_CMD, CAN_ID_VACUUM_TELEMETRY


class AdvancedProtocolTests(unittest.TestCase):
    def test_motion_boundary_and_crimp_destination(self):
        self.assertEqual(protocol.motion_frame(1, "forward", "9999999999"), (CAN_ID_MOTION_CMD, b"\x01\xff\xff\xff\xff"))
        self.assertEqual(protocol.motion_frame(21, "reverse", "1"), (CAN_ID_CRIMPING_CMD, b"\x00\x00\x00\x00\x01"))

    def test_malformed_values_are_rejected(self):
        with self.assertRaises(ValueError):
            protocol.drill_frame("not-a-number", "clockwise")
        with self.assertRaises(ValueError):
            protocol.aoi_frame("invalid", "1000")

    def test_weld_and_paste_bounds_match_protocol(self):
        self.assertEqual(protocol.weld_frame(14, "9999")[1], b"\x01\x07\xd0")
        self.assertEqual(protocol.paste_pulse_frame("-4", "999", "999")[1], b"\x00\x64\xff")

    def test_watchdog_safe_off_frames_and_printer_zero_steps(self):
        frame, off, interval = protocol.watchdog_frames("printer_heater", "300", "0")
        self.assertEqual(interval, 0.15)
        self.assertEqual(frame[1][-3:], b"\x00\x00\x00")
        self.assertEqual(off[1], b"\x00\x00\x01\x00\x00\x00")
        self.assertEqual(protocol.printer_frame("extruder", "20", "250")[1], b"\x00\xfa\x01\x00\x00\x14")

    def test_telemetry_fixtures_are_test_only_and_decode_documented_shapes(self):
        self.assertEqual(
            protocol.decode_telemetry_fixture(CAN_ID_VACUUM_TELEMETRY, b"\x04\xd2\x01"),
            {"adc": 1234, "detected": True},
        )
        with self.assertRaises(ValueError):
            protocol.decode_telemetry_fixture(CAN_ID_VACUUM_TELEMETRY, b"\x04")


if __name__ == "__main__":
    unittest.main()
