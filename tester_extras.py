# =============================================================================
# URTC Tester - fault recorder download and export, rack bench, thermal view, firmware features
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The logic behind five panels of the deck that needs no Qt, so it can be tested without a window.

* the fault recorder (the "black box" of the board): ask for the 22 chunks of the record, check it and save it as CSV and JSON, and
  decide when to do it automatically (once for each rising edge of the error flag the board reports);
* a bench for the tool rack that needs no board: the serial protocol and the behaviour of the rack, simulated, with the identity
  (type and serial number) of each head in the slots;
* the thermal view: a thermal image in false colour as a PNG that the deck can show, made from the chunks of a board or, clearly
  marked as simulated, from a synthetic image;
* the optional firmware features (0x1AE / 0x1AF): the mask, its names and the frames;
* the heater PID (0x1B9 / 0x1BA): the gains, the autotune orders and the state the board reports.

The shared pieces (urtc_can.blackbox, rack_sim, rack_status, thermal_view, tools_catalog) are copies of URTC-COMMON.
"""
from __future__ import annotations

import base64
import datetime
import os
import struct
import time
import zlib
from collections.abc import Callable

import tester_config
from urtc_can import blackbox, rack_sim, rack_status, thermal_view

FEATURES_MAGIC = b"FEAT"
FEATURE_NAMES = ((0x01, "MOTION_RAMPS"), (0x02, "HEALTH_PROFILE"), (0x04, "HSI_AUTOTRIM"), (0x08, "THERMAL_PID"))
FEATURES_SUPPORTED = 0x0F
CAN_ID_SET_FEATURES = tester_config.CAN_ID_SET_FEATURES
CAN_ID_FEATURES_RESP = tester_config.CAN_ID_FEATURES_RESP


# ---- fault recorder ---------------------------------------------------------------------------------------------------------------
def download_black_box(send_frame: Callable[[int, bytes], None], read_frame: Callable[[float], tuple[int, bytes] | None],
                       timeout_s: float = 0.5) -> blackbox.Record:
    """Read the record with the transport of the deck. Each chunk is four frames of 0x1A9; a chunk that does not arrive complete in
    ``timeout_s`` is an error (the record is never completed with guessed bytes)."""

    def request(index: int) -> bytes | None:
        send_frame(tester_config.CAN_ID_BLACKBOX_QUERY, blackbox.chunk_request(index))
        frames: list[bytes] = []
        deadline = time.monotonic() + timeout_s
        while len(frames) < blackbox.FRAMES_PER_CHUNK and time.monotonic() < deadline:
            frame = read_frame(0.05)
            if frame is not None and frame[0] == tester_config.CAN_ID_BLACKBOX_CHUNK and len(frame[1]) == 8:
                frames.append(frame[1])
        return b"".join(frames) if len(frames) == blackbox.FRAMES_PER_CHUNK else None

    return blackbox.download(request)


def save_black_box(record: blackbox.Record, folder: str, stem: str | None = None) -> tuple[str, str]:
    """Write the CSV and the JSON of a record in ``folder``; returns the two paths."""
    os.makedirs(folder, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc)
    stem = stem or now.strftime("urtc_blackbox_%Y%m%d_%H%M%S")
    csv_path = os.path.join(folder, stem + ".csv")
    json_path = os.path.join(folder, stem + ".json")
    with open(csv_path, "w", encoding="utf-8", newline="") as handle:
        handle.write(blackbox.to_csv(record))
    with open(json_path, "w", encoding="utf-8", newline="") as handle:
        handle.write(blackbox.to_json(record, now.strftime("%Y-%m-%dT%H:%M:%SZ")))
    return csv_path, json_path


def summarize_black_box(record: blackbox.Record) -> str:
    """One line for the deck: how many samples, when the fault was recorded and what the board reported."""
    if not record.samples:
        return "empty record"
    trigger = record.trigger_index
    last = record.samples[-1]
    text = f"{len(record.samples)} samples over {(last.tick_ms - record.samples[0].tick_ms) & 0xFFFFFFFF} ms"
    if trigger is not None:
        sample = record.samples[trigger]
        text += f"; error flag set at sample {trigger}, {sample.current_temperature} C of {sample.target_temperature} C"
        if sample.thermal_fault:
            text += f", guard {blackbox.THERMAL_FAULTS[sample.thermal_fault]}"
    else:
        text += "; no error flag in the record"
    return text


class AutoDownload:
    """Decides, from the active-tool answers (0x111), when the black box should be read: once for each fault, and only when switched on."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._trigger = blackbox.FaultTrigger()

    def feed(self, active_tool_payload: bytes) -> bool:
        fire = self._trigger.feed(active_tool_payload)
        return fire and self.enabled


# ---- features -----------------------------------------------------------------------------------------------------------------------
def features_frame(mask: int) -> tuple[int, bytes]:
    if not 0 <= mask <= FEATURES_SUPPORTED:
        raise ValueError("the mask uses bits this firmware does not have")
    return CAN_ID_SET_FEATURES, FEATURES_MAGIC + bytes([mask])


def decode_features(data: bytes) -> dict | None:
    if len(data) != 3:
        return None
    stored, running, supported = data
    return {"stored": stored, "running": running, "supported": supported}


def features_text(mask: int) -> str:
    names = [name for bit, name in FEATURE_NAMES if mask & bit]
    return ", ".join(names) if names else "none"


# ---- heater PID ---------------------------------------------------------------------------------------------------------------------
CAN_ID_PID_CONFIG = tester_config.CAN_ID_PID_CONFIG
CAN_ID_PID_STATE = tester_config.CAN_ID_PID_STATE
PID_SET_GAINS, PID_AUTOTUNE_START, PID_AUTOTUNE_ABORT, PID_QUERY = 0, 1, 2, 3
PID_STATE_NAMES = {0: "OFF", 1: "RUNNING", 2: "AUTOTUNING", 3: "AUTOTUNE_DONE", 4: "AUTOTUNE_FAILED"}
# the language key of each state name
PID_STATE_KEYS = {name: "VAL_PID_STATE_" + name for name in PID_STATE_NAMES.values()}
PID_GAIN_MAX = 600.0  # the firmware refuses a gain above 600.00 (it keeps them times 100 in 16 bits and limits them to 60000)


def pid_gain_x100(value: object, name: str = "gain") -> int:
    """A gain as the board keeps it: times 100, from 0 to 600.00. Text, a number, a NaN or a negative value is not guessed at."""
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number")
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number") from None
    if number != number or not 0.0 <= number <= PID_GAIN_MAX:
        raise ValueError(f"{name} must be a number from 0 to {PID_GAIN_MAX:g}")
    return int(round(number * 100.0))


def pid_frame(action: int, kp: object = 0.0, ki: object = 0.0, kd: object = 0.0) -> tuple[int, bytes]:
    """The 0x1B9 frame: store the gains, start or abort the autotune, or ask for the state. The gains are read only for the first."""
    if action not in (PID_SET_GAINS, PID_AUTOTUNE_START, PID_AUTOTUNE_ABORT, PID_QUERY):
        raise ValueError("unknown PID action")
    gains = (pid_gain_x100(kp, "Kp"), pid_gain_x100(ki, "Ki"), pid_gain_x100(kd, "Kd")) if action == PID_SET_GAINS else (0, 0, 0)
    return CAN_ID_PID_CONFIG, struct.pack(">HHHB", *gains, action)


def decode_pid_state(data: bytes) -> dict | None:
    """The 0x1BA answer: the gains in force, the state and the heater output of the last control cycle; None when it is not 8 bytes."""
    if len(data) != 8:
        return None
    kp, ki, kd, state, duty = struct.unpack(">HHHBB", bytes(data))
    return {"kp": kp / 100.0, "ki": ki / 100.0, "kd": kd / 100.0, "state": state, "state_name": PID_STATE_NAMES.get(state, f"CODE_{state}"), "duty_percent": duty}


# ---- rack bench ---------------------------------------------------------------------------------------------------------------------
class RackBench:
    """A simulated rack with a clock: rack it, send pre-heat orders, advance time and read the state as text."""

    def __init__(self) -> None:
        self.rack = rack_sim.SimulatedRack()
        self.now_ms = 0
        self.seq = 0
        self.log: list[str] = []

    def rack_head(self, slot: int, tool_id: int, serial: int = 0) -> str:
        self.rack.set_slot(slot, tool_id, serial)
        return f"slot {slot}: {'empty' if tool_id == rack_sim.TOOL_ID_NONE else f'tool {tool_id}' + (f' serial {serial}' if serial else '')}"

    def send_preheat(self, tool_id: int, target_c: int) -> str:
        self.seq = (self.seq + 1) & 0xFF
        frame = rack_sim.encode_set_preheat(self.seq, tool_id, target_c)
        reply = self.rack.receive(frame, self.now_ms)
        text = f"{reply.kind.upper()}" + (f" {reply.action}" if reply.action != "none" else "") + (f" ({reply.detail})" if reply.detail else "")
        self.log.append(text)
        return text

    def advance(self, ms: int) -> str:
        self.now_ms += max(0, ms)
        cut = self.rack.tick(self.now_ms)
        return f"time {self.now_ms} ms" + (f"; {cut} slot(s) sent to the safe state" if cut else "")

    def state_text(self) -> str:
        lines = []
        for item in self.rack.status()["slots"]:
            if item["occupied"]:
                unit = item["unit"] or "no serial"
                lines.append(f"slot {item['slot']}: tool {item['tool_id']} ({unit}) target {item['target_c']} C" + (" LIMIT" if item["expired"] else ""))
            else:
                lines.append(f"slot {item['slot']}: empty")
        return "\n".join(lines)

    def status_page(self, folder: str) -> tuple[str, str]:
        """Write the status of this bench as JSON and as a page; returns the two paths."""
        snap = rack_status.snapshot(self.rack.status(), name="URTC rack bench", source="simulation")
        os.makedirs(folder, exist_ok=True)
        json_path, html_path = os.path.join(folder, "rack_status.json"), os.path.join(folder, "rack_status.html")
        with open(json_path, "w", encoding="utf-8", newline="") as handle:
            handle.write(rack_status.to_json(snap))
        with open(html_path, "w", encoding="utf-8", newline="") as handle:
            handle.write(rack_status.to_html(snap))
        return json_path, html_path


# ---- thermal view -------------------------------------------------------------------------------------------------------------------
def png_bytes(width: int, height: int, rgb: bytes, scale: int = 1) -> bytes:
    """A PNG (8-bit RGB) of the image, every pixel repeated ``scale`` times in both directions. Standard library only."""
    if len(rgb) != width * height * 3:
        raise ValueError("the pixel data does not match the size")
    rows = bytearray()
    for y in range(height):
        row = rgb[y * width * 3:(y + 1) * width * 3]
        wide = b"".join(row[x * 3:x * 3 + 3] * scale for x in range(width))
        rows += (b"\x00" + wide) * scale

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width * scale, height * scale, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(bytes(rows), 6)) + chunk(b"IEND", b"")


def thermal_data_url(frame: list[list[float]], value_range: tuple[float, float] | None = None, scale: int = 12) -> str:
    height, width = len(frame), len(frame[0])
    png = png_bytes(width, height, thermal_view.to_rgb_bytes(frame, value_range), scale)
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def thermal_summary(frame: list[list[float]], simulated: bool) -> str:
    stats = thermal_view.region_stats(frame, 0, 0, len(frame[0]), len(frame))
    prefix = "SIMULATED image (no board read): " if simulated else ""
    if stats is None:
        return prefix + "no valid pixel"
    return prefix + f"{len(frame[0])}x{len(frame)} min {stats.minimum:.1f} C, max {stats.maximum:.1f} C, mean {stats.mean:.1f} C"


def read_thermal_image(send_frame: Callable[[int, bytes], None], read_frame: Callable[[float], tuple[int, bytes] | None],
                       variant: str = "90640", polls: int = 50, chunk_timeout_s: float = 0.5) -> list[list[float]]:
    """Capture an image from the thermal inspection tool: trigger (0x250), wait for ready (0x251), then every calibrated chunk
    (0x254 / four frames of 0x255). Raises ThermalError when the head reports an error, never becomes ready or leaves a chunk unanswered."""
    send_frame(thermal_view.CAN_ID_TRIGGER, b"")
    for _ in range(polls):
        send_frame(thermal_view.CAN_ID_STATUS, b"")
        frame = read_frame(0.1)
        if frame is not None and frame[0] == thermal_view.CAN_ID_STATUS and len(frame[1]) == 1:
            if frame[1][0] == 0xFF:
                raise thermal_view.ThermalError("the head reports a capture error")
            if frame[1][0] == 0x02:
                break
    else:
        raise thermal_view.ThermalError("the head did not become ready")
    chunks: dict[int, bytes] = {}
    for index in range(thermal_view.chunk_count(variant)):
        send_frame(thermal_view.CAN_ID_CALIBRATED_REQUEST, bytes([index]))
        parts: list[bytes] = []
        deadline = time.monotonic() + chunk_timeout_s
        while len(parts) < thermal_view.FRAMES_PER_CHUNK and time.monotonic() < deadline:
            frame = read_frame(0.05)
            if frame is not None and frame[0] == thermal_view.CAN_ID_CALIBRATED_CHUNK and len(frame[1]) == 8:
                parts.append(frame[1])
        if len(parts) != thermal_view.FRAMES_PER_CHUNK:
            raise thermal_view.ThermalError(f"chunk {index} was not answered with four frames")
        chunks[index] = b"".join(parts)
    return thermal_view.assemble(chunks, variant)
