# =============================================================================
# URTC-COMMON - src/urtc_common/tool_panel_model.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The panel of a tool as a model without a screen (standard library only).

The controls, the readings and the commands of a tool panel are data (``panel`` of a tool in ``spec/tools.json``, written as
``tool_panels.py``). This module is everything a screen needs that is not drawing: the frame builders a panel may name, the first
value of every control, a value held to the range of its control, the number a telemetry frame or a query answer holds, the text a
result shows, the temperatures of a picture and the exchange that asks the board for a value or pulls a picture. A Qt window and the
web studio draw the same panel from the same data; this is the Python half, tested without Qt and without a bus.

Frame builders hold the same rule as the ones of the web studio: a value that does not fit its field is brought to the nearest value
that does, never wrapped around into a different command (a speed of 300 is 255, a negative number is 0), and a count that cannot be
sent is an error instead of a different move.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Protocol

from .tool_panels import PANELS

MAX_MOTION_STEPS = 0xFFFFFFFF
WELD_PULSE_MAX_MS = 2000
SOLDER_FEEDER_RESET_MAGIC = (0x52, 0x53, 0x50, 0x30)  # "RSP0"

PanelValue = int | float | str | bool


# ---------------------------------------------------------------------------------------------------------------------
# frame builders
# ---------------------------------------------------------------------------------------------------------------------
def _number(value: Any) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _round(value: float) -> int:
    """Rounded half up, like the rounding of the web studio (Python's own rounds half to even)."""
    return math.floor(value + 0.5)


def byte(value: Any) -> int:
    """One unsigned byte: rounded, and kept between 0 and 255."""
    n = _number(value)
    if not math.isfinite(n):
        return 0
    return max(0, min(255, _round(n)))


def be16(value: Any) -> list[int]:
    """Two bytes, big-endian, as every multi-byte value of the bus is; kept between 0 and 65535."""
    n = _number(value)
    v = max(0, min(0xFFFF, _round(n))) if math.isfinite(n) else 0
    return [(v >> 8) & 0xFF, v & 0xFF]


def steps_to_bytes(steps: Any) -> list[int]:
    """Big-endian 32-bit step count of a move frame; rejects what does not fit instead of wrapping it into a different count."""
    n = _number(steps)
    if not math.isfinite(n) or n != math.floor(n) or n < 1 or n > MAX_MOTION_STEPS:
        raise ValueError("steps must be an integer from 1 to 4294967295")
    s = int(n)
    return [(s >> 24) & 0xFF, (s >> 16) & 0xFF, (s >> 8) & 0xFF, s & 0xFF]


def config_word_to_bytes(text: Any) -> list[int]:
    """Two-byte big-endian configuration word from a hexadecimal field (0x prefix allowed); an empty, longer or non-hexadecimal text is an error."""
    digits = str(text).strip()
    if digits[:2].lower() == "0x":
        digits = digits[2:]
    if not 1 <= len(digits) <= 4 or any(c not in "0123456789abcdefABCDEF" for c in digits):
        raise ValueError("the configuration word must be 1 to 4 hexadecimal digits")
    value = int(digits, 16)
    return [(value >> 8) & 0xFF, value & 0xFF]


def _thermal_motion(celsius: Any, forward: bool, steps: Any) -> list[int]:
    n = _number(steps)
    s = max(0, min(0xFFFFFF, _round(n))) if math.isfinite(n) else 0
    return [*be16(celsius), 1 if forward else 0, (s >> 16) & 0xFF, (s >> 8) & 0xFF, s & 0xFF]


def _weld_fire(pulse_ms: Any) -> list[int]:
    n = _number(pulse_ms)
    ms = max(1, min(WELD_PULSE_MAX_MS, _round(n))) if math.isfinite(n) else 1
    return [1, *be16(ms)]


# The frame builders a panel may name. Each receives the values of the controls the panel lists for it, in that order; the names are the ones
# of the ``encoder`` fields of spec/tools.json.
ENCODERS: dict[str, Callable[..., list[int]]] = {
    "drillCommand": lambda speed, direction: [byte(speed), 1 if direction == "ccw" else 0],
    "drillStop": lambda: [0, 0],
    "aoiRingCommand": lambda mode, period: [byte(mode), *be16(period)],
    "laserCommand": lambda power, interlock: [byte(power), 1 if interlock is True else 0],
    "laserOff": lambda: [0, 0],
    "powerByte": lambda power: [byte(power)],
    "powerOff": lambda: [0],
    "electromagnetCommand": lambda on: [1 if on is True else 0],
    "hotAirCommand": lambda celsius, blower: [*be16(celsius), byte(blower)],
    "hotAirOff": lambda: [0, 0, 0],
    "motionMove": lambda direction, steps: [1 if direction == "fwd" else 0, *steps_to_bytes(steps)],
    "motionStop": lambda direction: [1 if direction == "fwd" else 0, 0, 0, 0, 0],
    "weldFire": _weld_fire,
    "pasteJettingConfig": lambda channel, hertz: [byte(channel), *be16(hertz)],
    "pasteJettingPulse": lambda channel, duty, pulse_ms: [byte(channel), byte(duty), byte(pulse_ms)],
    "emptyFrame": lambda: [],
    "adsConfig": config_word_to_bytes,
    "feederReset": lambda: list(SOLDER_FEEDER_RESET_MAGIC),
    "solderSetpoint": lambda celsius: be16(celsius),
    "solderOff": lambda: [0, 0],
    "thermalMotion": lambda celsius, direction, steps: _thermal_motion(celsius, direction == "fwd", steps),
    "thermalMotionOff": lambda: _thermal_motion(0, True, 0),
}


def encode_action(name: str, values: Mapping[str, PanelValue], args: Sequence[str | int | float] | None, gate_first: bool = False,
                  gate_open: bool = True) -> list[int]:
    """The payload of one command. A number in ``args`` stands for itself; a name is the control whose value goes in that place.

    With ``gate_first`` the first one goes as 0 while the repeated command of the section is off (a heater set point must not be armed
    by a one-off move).
    """
    listed = [a if isinstance(a, (int, float)) and not isinstance(a, bool) else values[str(a)] for a in (args or [])]
    if gate_first and not gate_open and listed:
        listed[0] = 0
    return ENCODERS[name](*listed)


# ---------------------------------------------------------------------------------------------------------------------
# the panel
# ---------------------------------------------------------------------------------------------------------------------
def panel_of(tool_id: int) -> dict | None:
    """The panel of a tool (a panel that borrows another one is already resolved), or None for a tool that has none."""
    return PANELS.get(tool_id)


def panel_controls(panel: Mapping) -> list[dict]:
    """Every control of the panel, section after section; the controls are shared by the sections."""
    return [c for section in panel["sections"] for c in section.get("controls", [])]


def initial_values(panel: Mapping) -> dict[str, PanelValue]:
    """The first value of every control of the panel."""
    return {c["id"]: c["default"] for c in panel_controls(panel)}


def clamp_control(control: Mapping, raw: Any) -> Any:
    """A value held to the range of its control; anything that is not a number falls back to the lowest one. Other controls keep their value."""
    if control["type"] not in ("range", "number"):
        return raw
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        parsed: float = raw
    else:
        text = str(raw).strip()
        sign = -1 if text.startswith("-") else 1
        digits = ""
        for ch in text.lstrip("+-"):
            if not ch.isdigit():
                break
            digits += ch
        parsed = sign * int(digits) if digits else math.nan
    n = parsed if math.isfinite(parsed) else control["min"]
    return max(control["min"], min(control["max"], n))


def reading_of(reading: Mapping, data: Sequence[int]) -> int | None:
    """The number a reading has in a telemetry frame (big-endian), or None when the frame is too short."""
    if len(data) < reading["offset"] + reading["width"]:
        return None
    return data[reading["offset"]] if reading["width"] == 1 else (data[reading["offset"]] << 8) | data[reading["offset"] + 1]


def decode_value(spec: Mapping, data: Sequence[int]) -> int | None:
    """The number a query answer holds: 1, 2 or 4 bytes big-endian from ``offset``, signed when the result says so; None when the frame is too short."""
    if len(data) < spec["offset"] + spec["width"]:
        return None
    value = 0
    for i in range(spec["width"]):
        value = value * 256 + data[spec["offset"] + i]
    span = 2 ** (8 * spec["width"])
    return value - span if spec.get("signed") and value >= span // 2 else value


def is_event_frame(reading: Mapping, data: Sequence[int]) -> bool:
    """True when a frame is the event a reading counts: the byte at its offset equals ``match`` (every frame counts when the reading names none)."""
    if reading.get("match") is None:
        return True
    return reading["offset"] < len(data) and data[reading["offset"]] == reading["match"]


def reading_step(reading: Mapping, data: Sequence[int], timestamp: str, previous: Mapping[str, Any]) -> dict[str, Any]:
    """What a reading holds after a frame: a counter counts the frames of its event, a last-seen reading keeps their time, any other keeps the number it decodes."""
    value, seen = previous.get("value"), previous.get("seen")
    fmt = reading.get("format")
    if fmt in ("count", "last_seen"):
        if not is_event_frame(reading, data):
            return {"value": value, "seen": seen}
        return {"value": (value or 0) + 1, "seen": seen} if fmt == "count" else {"value": value, "seen": timestamp}
    number = reading_of(reading, data)
    return {"value": value if number is None else number, "seen": seen}


def reading_shown(reading: Mapping, value: int | None, seen: str | None, yes: str, no: str) -> tuple[str, str]:
    """The text of a reading and the tone it is drawn in (on, off or plain): a yes/no flag, a count, the time of the last event or a number with its unit."""
    fmt = reading.get("format")
    if fmt == "yes_no":
        return (yes, "on") if value else (no, "off")
    if fmt == "count":
        return str(value or 0), "plain"
    if fmt == "last_seen":
        return (seen if seen is not None else "--"), "plain"
    unit = f" {reading['unit']}" if reading.get("unit") else ""
    return f"{'--' if value is None else value}{unit}", "plain"


def panel_text(translate: Callable[[str, str], str] | None, text: Mapping, params: Mapping[str, Any] | None = None) -> str:
    """The text of a label: the translation of its key (the English default when there is no translator), or its plain text."""
    params = params or {}
    if "text" in text:
        return str(text["text"]).replace("{tool}", str(params.get("tool", "")))
    shown = translate(text["key"], text["default"]) if translate else text["default"]
    for name, value in params.items():
        shown = shown.replace("{{" + name + "}}", str(value))
    return shown


def result_text(translate: Callable[[str, str], str] | None, result: Mapping, value: int | None) -> str:
    """The text a query result shows: the name of the state the number stands for, the number itself, or its hexadecimal form for a state nobody named."""
    if value is None:
        return "--"
    states = result.get("states")
    if not states:
        return str(value)
    for state in states:
        if state["value"] == value:
            return panel_text(translate, state["label"])
    return f"0x{value:x}"


def label_params(control: Mapping, value: PanelValue) -> dict[str, Any]:
    """The values a label may use: the control's value under the name the label gives it, and the range of the control as min and max."""
    params: dict[str, Any] = {}
    label = control["label"]
    if label.get("param"):
        params[label["param"]] = value
    if control["type"] in ("range", "number"):
        params["min"] = control["min"]
        params["max"] = control["max"]
    return params


def image_pixels(data: Sequence[int], scale: float) -> list[float]:
    """The temperatures of a picture: the bytes of its chunks as signed 16-bit numbers (big-endian) divided by ``scale``."""
    out: list[float] = []
    for i in range(0, len(data) - 1, 2):
        v = (data[i] << 8) | data[i + 1]
        if v & 0x8000:
            v -= 0x10000
        out.append(v / scale)
    return out


def heat_colour(value: float, maximum: float) -> tuple[int, int, int]:
    """The colour of a pixel as red, green and blue: blue at 0 up to red at ``maximum``, held to that range."""
    fraction = max(0.0, min(maximum, value)) / maximum if maximum else 0.0
    hue = (240 - fraction * 240) / 60.0   # HSV with saturation 0.9 and value 1.0
    sat, val = 0.9, 1.0
    c = val * sat
    x = c * (1 - abs(hue % 2 - 1))
    base = [(c, x, 0), (x, c, 0), (0, c, x), (0, x, c), (x, 0, c), (c, 0, x)][min(5, int(hue))]
    m = val - c
    return tuple(_round((component + m) * 255) for component in base)  # type: ignore[return-value]


# ---------------------------------------------------------------------------------------------------------------------
# asking the board
# ---------------------------------------------------------------------------------------------------------------------
class PanelBus(Protocol):
    """What a panel needs of the bus to ask the board for something."""

    def send_frame(self, can_id: int, data: Sequence[int], description: str = "") -> None: ...
    def wait_for_frame(self, can_id: int, timeout_ms: int) -> Sequence[int] | None: ...
    def request(self, can_id: int, data: Sequence[int], response_id: int, timeout_ms: int, description: str = "") -> Sequence[int] | None: ...
    def flush_frames(self, can_id: int | None = None) -> None: ...


def ask_value(bus: PanelBus, action: Mapping) -> int | None:
    """Asks the board for the value of a ``query`` action: the number its answer holds, or None when nothing came back or the frame was too short."""
    answer = bus.request(action["canId"], [], action.get("respCanId", action["canId"]), action["timeout_ms"], action.get("description", ""))
    if answer is None or not action.get("result"):
        return None
    return decode_value(action["result"], answer)


def pull_image(bus: PanelBus, action: Mapping, on_progress: Callable[[int], None] = lambda percent: None) -> list[float]:
    """Pulls the picture of an ``image`` action chunk by chunk and returns its temperatures; raises TimeoutError when a frame of a chunk does not arrive."""
    chunks, per_chunk = action["chunks"], action["frames_per_chunk"]
    response_id = action.get("respCanId", action["canId"])
    data: list[int] = []
    for chunk in range(chunks):
        bus.flush_frames(response_id)   # frames left over from an earlier, aborted reading must not be mixed into this chunk
        bus.send_frame(action["canId"], [chunk], f"{action.get('description', '')} {chunk}")
        for frame_index in range(per_chunk):
            frame = bus.wait_for_frame(response_id, action["timeout_ms"])
            if frame is None:
                raise TimeoutError(f"Timeout on chunk {chunk}, frame {frame_index}")
            data.extend(frame)
        on_progress((chunk + 1) * 100 // chunks)
    return image_pixels(data, action["scale"])
