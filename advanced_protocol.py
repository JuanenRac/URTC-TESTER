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
    CAN_ID_GLOBAL_STATUS,
    EXPANSION_BOARD_TYPES,
    MLX_SENSOR_VARIANTS,
    TOOL_NAMES,
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


def global_status_frame(
    status_rgb: tuple[str | int, str | int, str | int],
    night_mode: str,
    ring_rgb: tuple[str | int, str | int, str | int],
    ring_on: bool,
) -> tuple[int, bytes]:
    """CAN_ID_GLOBAL_STATUS (0x100) - any tool, not gated by a selected
    profile at all (see tester_common_panels.py's own real
    _send_global_status). A 10s hold before the board falls back to its
    own automatic color scheme - real, but low-stakes if it lapses."""
    night_code = {"standard": 0x00, "night": 0x01, "standby": 0x0F}.get(night_mode)
    if night_code is None:
        raise ValueError("unknown OLED mode")
    return CAN_ID_GLOBAL_STATUS, bytes([
        bounded_int(status_rgb[0], 0, 255), bounded_int(status_rgb[1], 0, 255), bounded_int(status_rgb[2], 0, 255),
        night_code,
        bounded_int(ring_rgb[0], 0, 255), bounded_int(ring_rgb[1], 0, 255), bounded_int(ring_rgb[2], 0, 255),
        0x01 if ring_on else 0x00,
    ])


def spi_passthrough_frame(hex_bytes: str) -> tuple[int, bytes]:
    """CAN_ID_EXP_SPI_CMD (0x180) - CONN_EXPANSION's generic, non-TMC5160-
    aware bit-banged SPI passthrough (see tester_common_panels.py's own
    real _send_expansion_spi). 1-7 real raw bytes, never guessed from a
    malformed hex string."""
    try:
        tx = bytes(int(b, 16) for b in hex_bytes.split())
    except ValueError as exc:
        raise ValueError("not valid space-separated hex bytes, e.g. 01 02 03") from exc
    if not 1 <= len(tx) <= 7:
        raise ValueError("must be 1 to 7 bytes")
    return 0x180, bytes([len(tx)]) + tx


def decode_spi_response(data: bytes) -> bytes | None:
    """Decodes CAN_ID_EXP_SPI_RESP (0x181) - a length-prefixed byte
    string. None on a malformed/truncated response, never a guessed
    partial read."""
    if not data:
        return None
    n = data[0]
    rx = data[1:1 + n]
    if len(rx) < n:
        return None
    return rx


def decode_diag0(data: bytes) -> bool | None:
    """Decodes CAN_ID_DIAG0_RESP (0x183) - the diode-ORed TMC_DIAG0
    stall/fault line, real high/low, never a guessed default."""
    if len(data) < 1:
        return None
    return bool(data[0])


def decode_fram_state(data: bytes) -> dict[str, object] | None:
    """Decodes CAN_ID_FRAM_STATE_RESP (0x191) - the FM24CL64B's own real
    recovered-state record (also what an erase's own response carries,
    now genuinely empty). `valid=False` is a real, meaningful state
    (nothing was ever saved) distinct from `None` (no response at all)."""
    if len(data) < 8:
        return None
    valid, tool_id, had_error, temp_hi, temp_lo, speed, dir_or_interlock, fan = data[:8]
    return {
        "valid": bool(valid),
        "tool_id": tool_id,
        "had_error": bool(had_error),
        "temp": (temp_hi << 8) | temp_lo,
        "speed": speed,
        "dir_or_interlock": bool(dir_or_interlock),
        "fan": fan,
    }


def decode_expansion_board_type(data: bytes) -> str | None:
    """Decodes CAN_ID_EXPANSION_TYPE_RESP (0x1A1) - real, read-only (the
    Flasher is the only tool that ever writes this). Out-of-range and
    too-short responses are both real "no answer" conditions from an
    older firmware that predates this register, not a value to guess."""
    if len(data) < 1 or data[0] >= len(EXPANSION_BOARD_TYPES):
        return None
    return EXPANSION_BOARD_TYPES[data[0]]


def decode_mlx_sensor_variant(data: bytes) -> str | None:
    """Decodes CAN_ID_MLX_VARIANT_RESP (0x1A7) - same real read-only
    reasoning as decode_expansion_board_type above."""
    if len(data) < 1 or data[0] >= len(MLX_SENSOR_VARIANTS):
        return None
    return MLX_SENSOR_VARIANTS[data[0]]


def decode_free_tool_config(data: bytes) -> dict[str, object] | None:
    """Decodes CAN_ID_FREE_TOOL_CONFIG_RESP (0x1A3) - the real raw
    ID-jumper reading plus what it resolves to (0 or >12 = none
    selected), read-only here (only the Flasher ever writes it)."""
    if len(data) < 2:
        return None
    raw_id_pin, selection = data[0], data[1]
    tool_name = TOOL_NAMES.get(selection - 1) if 1 <= selection <= 12 else None
    return {"raw_id_pin": raw_id_pin, "selection": selection, "tool_name": tool_name}


def decode_peripheral_info(data: bytes) -> dict[str, object] | None:
    """Decodes CAN_ID_PERIPHERAL_INFO_RESP (0x1A5) - real peripheral type
    + device serial (lets multiple otherwise-identical boards be told
    apart on the same bus), read-only here (only the Flasher ever writes
    the serial; the type is a fixed constant, never writable)."""
    if len(data) < 2:
        return None
    return {"peripheral_type": data[0], "serial": data[1], "is_urtc": data[0] == 0x03}


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
