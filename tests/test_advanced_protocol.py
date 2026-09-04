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

    def test_global_status_frame_matches_the_real_documented_shape(self):
        can_id, data = protocol.global_status_frame((0, 255, 0), "night", (0, 0, 255), True)
        self.assertEqual((can_id, data), (0x100, bytes([0, 255, 0, 0x01, 0, 0, 255, 0x01])))
        can_id, data = protocol.global_status_frame((999, -5, 0), "standby", (0, 0, 0), False)
        self.assertEqual(data, bytes([255, 0, 0, 0x0F, 0, 0, 0, 0x00]), "out-of-range RGB values must clamp, never raise")
        with self.assertRaises(ValueError):
            protocol.global_status_frame((0, 0, 0), "not-a-real-mode", (0, 0, 0), False)

    def test_spi_passthrough_frame_bounds_and_rejects_malformed_input(self):
        self.assertEqual(protocol.spi_passthrough_frame("01 02 03"), (0x180, b"\x03\x01\x02\x03"))
        with self.assertRaises(ValueError):
            protocol.spi_passthrough_frame("")  # 0 bytes - below the real 1-byte minimum
        with self.assertRaises(ValueError):
            protocol.spi_passthrough_frame(" ".join(["01"] * 8))  # 8 bytes - above the real 7-byte maximum
        with self.assertRaises(ValueError):
            protocol.spi_passthrough_frame("zz")

    def test_decode_spi_response_matches_the_real_length_prefixed_shape(self):
        self.assertEqual(protocol.decode_spi_response(bytes([2, 0xAA, 0xBB])), bytes([0xAA, 0xBB]))
        self.assertEqual(protocol.decode_spi_response(bytes([0])), b"")
        self.assertIsNone(protocol.decode_spi_response(bytes([2, 0xAA])), "fewer real bytes than the length prefix claims must not be guessed")
        self.assertIsNone(protocol.decode_spi_response(b""))

    def test_decode_diag0_matches_the_real_documented_shape(self):
        self.assertTrue(protocol.decode_diag0(bytes([1])))
        self.assertFalse(protocol.decode_diag0(bytes([0])))
        self.assertIsNone(protocol.decode_diag0(b""))

    def test_decode_fram_state_distinguishes_no_response_from_a_real_empty_state(self):
        # valid=0 - a real, meaningful "nothing was ever saved" state.
        self.assertEqual(
            protocol.decode_fram_state(bytes([0, 0, 0, 0, 0, 0, 0, 0])),
            {"valid": False, "tool_id": 0, "had_error": False, "temp": 0, "speed": 0, "dir_or_interlock": False, "fan": 0},
        )
        # valid=1, tool_id=5 (Drill), temp=0x0190=400, speed=128, dir on, fan=200, had_error=1.
        self.assertEqual(
            protocol.decode_fram_state(bytes([1, 5, 1, 0x01, 0x90, 128, 1, 200])),
            {"valid": True, "tool_id": 5, "had_error": True, "temp": 400, "speed": 128, "dir_or_interlock": True, "fan": 200},
        )
        self.assertIsNone(protocol.decode_fram_state(bytes([1, 2, 3])), "a too-short response must never be guessed")

    def test_decode_expansion_board_type_and_mlx_variant_are_real_lookup_tables(self):
        self.assertEqual(protocol.decode_expansion_board_type(bytes([0])), protocol.EXPANSION_BOARD_TYPES[0])
        self.assertIsNone(protocol.decode_expansion_board_type(bytes([255])), "an out-of-range index is a real older-firmware no-answer, not a guess")
        self.assertIsNone(protocol.decode_expansion_board_type(b""))
        self.assertEqual(protocol.decode_mlx_sensor_variant(bytes([0])), protocol.MLX_SENSOR_VARIANTS[0])
        self.assertIsNone(protocol.decode_mlx_sensor_variant(bytes([255])))

    def test_decode_free_tool_config_resolves_the_real_selection(self):
        self.assertEqual(
            protocol.decode_free_tool_config(bytes([31, 5])),
            {"raw_id_pin": 31, "selection": 5, "tool_name": protocol.TOOL_NAMES[4]},
        )
        self.assertEqual(
            protocol.decode_free_tool_config(bytes([31, 0])),
            {"raw_id_pin": 31, "selection": 0, "tool_name": None},
            "selection=0 is a real 'nothing selected' state, not an error",
        )
        self.assertIsNone(protocol.decode_free_tool_config(bytes([31])))

    def test_decode_peripheral_info_matches_the_real_documented_shape(self):
        self.assertEqual(
            protocol.decode_peripheral_info(bytes([0x03, 42])),
            {"peripheral_type": 0x03, "serial": 42, "is_urtc": True},
        )
        self.assertEqual(
            protocol.decode_peripheral_info(bytes([0x01, 7])),
            {"peripheral_type": 0x01, "serial": 7, "is_urtc": False},
        )
        self.assertIsNone(protocol.decode_peripheral_info(bytes([0x03])))


if __name__ == "__main__":
    unittest.main()
