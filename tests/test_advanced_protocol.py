# =============================================================================
# URTC Tester - Hardware-free assertions for Qt Quick control encoders
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
import unittest

import advanced_protocol as protocol
from tester_config import CAN_ID_CRIMPING_CMD, CAN_ID_MOTION_CMD, CAN_ID_VACUUM_TELEMETRY, CAN_ID_IMPACT_EVENT


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

    def test_decode_vacuum_frame_matches_the_real_documented_shape(self):
        # Real, live-path decoder (qt_tester.py's own continuous watch
        # calls this directly) - decode_telemetry_fixture above delegates
        # to this same function for its own vacuum case, so this is the
        # one real place this shape is decoded, tested from both angles.
        self.assertEqual(protocol.decode_vacuum_frame(b"\x04\xd2\x01"), {"adc": 1234, "detected": True})
        self.assertEqual(protocol.decode_vacuum_frame(b"\x00\x00\x00"), {"adc": 0, "detected": False})
        # A too-short/malformed frame on the wire is a real condition a
        # live watch must skip, not raise on - None, never a guessed value.
        self.assertIsNone(protocol.decode_vacuum_frame(b"\x04"))
        self.assertIsNone(protocol.decode_vacuum_frame(b""))

    def test_is_scan_probe_impact_matches_only_the_documented_contact_byte(self):
        self.assertTrue(protocol.is_scan_probe_impact(bytes([0x01])))
        self.assertFalse(protocol.is_scan_probe_impact(bytes([0x00])), "0x00 is real bus traffic, not an impact")
        self.assertFalse(protocol.is_scan_probe_impact(bytes([0x02])), "any non-0x01 value must not be miscounted as contact")
        self.assertFalse(protocol.is_scan_probe_impact(b""), "an empty payload must never be read as a real impact")


if __name__ == "__main__":
    unittest.main()
