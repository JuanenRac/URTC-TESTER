# =============================================================================
# URTC Tester - Pure encoders for the migrated Qt Quick control families
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Pure CAN payload encoders used as hardware-free migration evidence.

No transport is imported here. Tests can therefore prove payload boundaries
and safe-off frames on a normal host without PySide6, serial hardware or a
CAN adapter.
"""
from __future__ import annotations

import struct

from tester_config import (
    CAN_ID_3DP_HOTEND_FAN_CMD,
    CAN_ID_3DP_LAYER_FAN_CMD,
    CAN_ID_3DP_THERMAL_MOTION,
    CAN_ID_AOI_CMD,
    CAN_ID_CRIMPING_CMD,
    CAN_ID_DRILL_CMD,
    CAN_ID_ELECTROMAGNET_CMD,
    CAN_ID_HOTAIR_CMD,
    CAN_ID_LASER_CMD,
    CAN_ID_MOTION_CMD,
    CAN_ID_PASTE_JETTING_CONFIG,
    CAN_ID_PASTE_JETTING_PULSE,
    CAN_ID_SOLDER_SETPOINT,
    CAN_ID_SPOT_WELD_CMD,
    CAN_ID_ULTRASONIC_WELD_CMD,
    CAN_ID_UV_CURING_CMD,
    CAN_ID_VACUUM_TELEMETRY,
    CAN_ID_IMPACT_EVENT,
    CAN_ID_DRILL_TELEMETRY,
    CAN_ID_AOI_TELEMETRY,
    CAN_ID_LASER_TELEMETRY,
    CAN_ID_3DP_HOTEND_TELEM,
    CAN_ID_3DP_LAYER_FAN_RPM,
    CAN_ID_3DP_HOTEND_FAN_RPM,
)


def bounded_int(value: str | int, minimum: int, maximum: int) -> int:
    """Parse and clamp an operator value; malformed input is never guessed."""
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("value must be an integer") from exc
    return min(maximum, max(minimum, parsed))


def motion_frame(profile_id: int, direction: str, steps: str | int) -> tuple[int, bytes]:
    if profile_id not in {0, 1, 2, 3, 6, 7, 12, 16, 21}:
        raise ValueError("profile does not support one-shot motion")
    count = bounded_int(steps, 1, 0xFFFFFFFF)
    command = CAN_ID_CRIMPING_CMD if profile_id == 21 else CAN_ID_MOTION_CMD
    return command, bytes([0x01 if direction == "forward" else 0x00]) + struct.pack(">I", count)


def drill_frame(speed: str | int, direction: str) -> tuple[int, bytes]:
    return CAN_ID_DRILL_CMD, bytes([bounded_int(speed, 0, 255), 0x01 if direction == "counter-clockwise" else 0x00])


def aoi_frame(mode: str, period_us: str | int) -> tuple[int, bytes]:
    mode_byte = {"off": 0x00, "strobe": 0x01, "continuous": 0x02}.get(mode)
    if mode_byte is None:
        raise ValueError("unknown AOI mode")
    return CAN_ID_AOI_CMD, bytes([mode_byte]) + struct.pack(">H", bounded_int(period_us, 1, 65535))


def magnet_frame(energized: bool) -> tuple[int, bytes]:
    return CAN_ID_ELECTROMAGNET_CMD, bytes([0x01 if energized else 0x00])


def weld_frame(profile_id: int, duration_ms: str | int) -> tuple[int, bytes]:
    command = {14: CAN_ID_SPOT_WELD_CMD, 24: CAN_ID_ULTRASONIC_WELD_CMD}.get(profile_id)
    if command is None:
        raise ValueError("profile does not support weld pulse")
    return command, b"\x01" + struct.pack(">H", bounded_int(duration_ms, 1, 2000))


def paste_config_frame(channel: str | int, frequency_hz: str | int) -> tuple[int, bytes]:
    return CAN_ID_PASTE_JETTING_CONFIG, bytes([bounded_int(channel, 0, 3)]) + struct.pack(">H", bounded_int(frequency_hz, 1, 65535))


def paste_pulse_frame(channel: str | int, duty: str | int, duration_ms: str | int) -> tuple[int, bytes]:
    return CAN_ID_PASTE_JETTING_PULSE, bytes([
        bounded_int(channel, 0, 3),
        bounded_int(duty, 0, 100),
        bounded_int(duration_ms, 0, 255),
    ])


def printer_frame(action: str, first: str | int, second: str | int) -> tuple[int, bytes]:
    if action == "hotend_fan":
        return CAN_ID_3DP_HOTEND_FAN_CMD, bytes([bounded_int(first, 0, 255)])
    if action == "extruder":
        return (
            CAN_ID_3DP_THERMAL_MOTION,
            struct.pack(">H", bounded_int(second, 0, 300))
            + b"\x01"
            + bounded_int(first, 0, 0xFFFFFF).to_bytes(3, "big"),
        )
    raise ValueError("unknown printer action")


def watchdog_frames(kind: str, first: str | int, second: str | int) -> tuple[tuple[int, bytes], tuple[int, bytes], float]:
    """Return (refresh frame, safe-off frame, interval seconds)."""
    if kind == "solder":
        return (CAN_ID_SOLDER_SETPOINT, struct.pack(">H", bounded_int(first, 0, 450))), (CAN_ID_SOLDER_SETPOINT, b"\x00\x00"), 0.15
    if kind == "laser":
        return (CAN_ID_LASER_CMD, bytes([bounded_int(first, 0, 255), 0x01 if bounded_int(second, 0, 1) else 0x00])), (CAN_ID_LASER_CMD, b"\x00\x00"), 0.15
    if kind == "printer_heater":
        return (CAN_ID_3DP_THERMAL_MOTION, struct.pack(">H", bounded_int(first, 0, 300)) + b"\x01\x00\x00\x00"), (CAN_ID_3DP_THERMAL_MOTION, b"\x00\x00\x01\x00\x00\x00"), 0.15
    if kind == "layer_fan":
        return (CAN_ID_3DP_LAYER_FAN_CMD, bytes([bounded_int(first, 0, 255)])), (CAN_ID_3DP_LAYER_FAN_CMD, b"\x00"), 0.4
    if kind == "uv":
        return (CAN_ID_UV_CURING_CMD, bytes([bounded_int(first, 0, 255)])), (CAN_ID_UV_CURING_CMD, b"\x00"), 0.15
    if kind == "hotair":
        return (CAN_ID_HOTAIR_CMD, struct.pack(">H", bounded_int(first, 0, 450)) + bytes([bounded_int(second, 0, 255)])), (CAN_ID_HOTAIR_CMD, b"\x00\x00\x00"), 0.15
    raise ValueError("unknown watchdog family")


def decode_vacuum_frame(data: bytes) -> dict[str, int | bool] | None:
    """Real decoder for CAN_ID_VACUUM_TELEMETRY (0x145) - the one real
    shape both qt_tester.py's live watch and this module's own test
    fixture below decode, so there is exactly one place that shape is
    ever written down. Returns None on a too-short frame rather than
    raising - a malformed/truncated frame on the wire is a real
    condition a live watch must just skip, not a hard error."""
    if len(data) < 3:
        return None
    return {"adc": struct.unpack(">H", data[:2])[0], "detected": bool(data[2])}


def is_scan_probe_impact(data: bytes) -> bool:
    """Real decoder for CAN_ID_IMPACT_EVENT (0x095) - true only for the
    documented "contact" byte (0x01); any other/empty payload on the same
    ID is real bus traffic that isn't an actual impact and must not be
    counted as one."""
    return len(data) >= 1 and data[0] == 0x01


def decode_telemetry_fixture(can_id: int, data: bytes) -> dict[str, int | bool]:
    """Decode only documented telemetry shapes for test fixtures.

    This has no UI or transport path, so a test cannot accidentally make
    simulated values appear as a real device reading.
    """
    if can_id == CAN_ID_VACUUM_TELEMETRY:
        decoded = decode_vacuum_frame(data)
        if decoded is not None:
            return decoded
    if can_id == CAN_ID_DRILL_TELEMETRY and len(data) >= 3:
        return {"rpm": struct.unpack(">H", data[:2])[0], "endstop": bool(data[2])}
    if can_id in {CAN_ID_AOI_TELEMETRY, CAN_ID_LASER_TELEMETRY} and data:
        return {"endstop": bool(data[0])}
    if can_id in {CAN_ID_3DP_HOTEND_TELEM, CAN_ID_3DP_LAYER_FAN_RPM, CAN_ID_3DP_HOTEND_FAN_RPM} and len(data) >= 2:
        return {"value": struct.unpack(">H", data[:2])[0]}
    raise ValueError("unsupported or malformed telemetry fixture")
