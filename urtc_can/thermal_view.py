"""What a panel needs to show the thermal inspection tool of the URTC head (tool 22, identifiers 0x250 to 0x255): put the chunks of
an image back together, paint it in false colour and read the minimum, maximum and mean of a region.

The colour ramp is the one of URTC-VISION-TOOL (black, blue, red, yellow, white), so a picture made by the tester, the web studio and
the vision companion looks the same. A pixel that is not a number is painted magenta instead of dragging the scale. Nothing here talks
to a board: it works on the values it is given, and a panel that shows the synthetic frame says so (``simulated_frame``).

Standard library only. Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
"""
from __future__ import annotations

import math
import struct
from dataclasses import dataclass

CAN_ID_TRIGGER = 0x250
CAN_ID_STATUS = 0x251
CAN_ID_CALIBRATED_REQUEST = 0x254
CAN_ID_CALIBRATED_CHUNK = 0x255
PIXELS_PER_CHUNK = 16
FRAMES_PER_CHUNK = 4
SHAPES = {"90640": (32, 24), "90641": (16, 12), "90642": (32, 24)}
MIN_SPAN_C = 1.0
INVALID_COLOR = (255, 0, 255)
STOPS = ((0.0, (0, 0, 0)), (0.33, (0, 0, 255)), (0.66, (255, 0, 0)), (0.85, (255, 255, 0)), (1.0, (255, 255, 255)))


class ThermalError(ValueError):
    """The chunks or the frame cannot be used."""


def chunk_count(variant: str) -> int:
    width, height = shape(variant)
    return width * height // PIXELS_PER_CHUNK


def shape(variant: str) -> tuple[int, int]:
    try:
        return SHAPES[variant]
    except KeyError:
        raise ThermalError(f"unknown sensor variant {variant!r}") from None


def decode_chunk(data: bytes) -> list[float]:
    """The 16 temperatures of a chunk (four frames of eight bytes, big-endian int16, hundredths of a degree)."""
    if len(data) != FRAMES_PER_CHUNK * 8:
        raise ThermalError("a chunk is 32 bytes (four frames of eight)")
    return [v / 100.0 for v in struct.unpack(">16h", data)]


def assemble(chunks: dict[int, bytes], variant: str = "90640") -> list[list[float]]:
    """The image, row by row, from the chunks received (index to 32 bytes). Refuses an image with a chunk missing."""
    width, height = shape(variant)
    count = chunk_count(variant)
    missing = [i for i in range(count) if i not in chunks]
    if missing:
        raise ThermalError(f"{len(missing)} chunk(s) missing, first {missing[0]}")
    flat: list[float] = []
    for i in range(count):
        flat += decode_chunk(chunks[i])
    return [flat[y * width:(y + 1) * width] for y in range(height)]


def encode_chunks(frame: list[list[float]]) -> dict[int, bytes]:
    """The chunks a head would send for an image (values clamped to int16 of hundredths): for the simulator and the tests."""
    flat = [v for row in frame for v in row]
    out = {}
    for i in range(len(flat) // PIXELS_PER_CHUNK):
        words = [max(-32768, min(32767, round(v * 100))) for v in flat[i * PIXELS_PER_CHUNK:(i + 1) * PIXELS_PER_CHUNK]]
        out[i] = struct.pack(">16h", *words)
    return out


def synthetic_frame(width: int = 32, height: int = 24) -> list[list[float]]:
    """A smooth hot spot on a room-temperature background, for a panel that has no board to read (marked simulated by its caller)."""
    cx, cy = width / 2.0, height / 2.0
    rows = []
    for y in range(height):
        rows.append([round(24.0 + 55.0 * math.exp(-(((x - cx) ** 2 + (y - cy) ** 2) / (2 * (width / 4.0) ** 2))), 2) for x in range(width)])
    return rows


def _finite(value: float) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value)


def scale_of(frame: list[list[float]], value_range: tuple[float, float] | None = None) -> tuple[float, float]:
    if value_range is not None:
        lo, hi = float(value_range[0]), float(value_range[1])
        if not hi > lo:
            raise ThermalError("the range must have high above low")
        return lo, hi
    values = [v for row in frame for v in row if _finite(v)]
    if not values:
        return 0.0, MIN_SPAN_C
    lo, hi = min(values), max(values)
    if hi - lo < MIN_SPAN_C:
        middle = (hi + lo) / 2.0
        lo, hi = middle - MIN_SPAN_C / 2.0, middle + MIN_SPAN_C / 2.0
    return lo, hi


def color_of(value: float, lo: float, hi: float) -> tuple[int, int, int]:
    if not _finite(value):
        return INVALID_COLOR
    norm = min(1.0, max(0.0, (value - lo) / (hi - lo)))
    color = (0, 0, 0)
    for (t0, c0), (t1, c1) in zip(STOPS, STOPS[1:], strict=False):
        if t0 <= norm <= t1:
            local = (norm - t0) / (t1 - t0)
            color = tuple(int(c0[k] + (c1[k] - c0[k]) * local) for k in range(3))  # type: ignore[assignment]
    return color


def false_color(frame: list[list[float]], value_range: tuple[float, float] | None = None) -> list[list[tuple[int, int, int]]]:
    lo, hi = scale_of(frame, value_range)
    return [[color_of(v, lo, hi) for v in row] for row in frame]


def to_rgb_bytes(frame: list[list[float]], value_range: tuple[float, float] | None = None) -> bytes:
    """The image as R, G, B bytes, row after row (for a canvas or a QImage)."""
    return bytes(channel for row in false_color(frame, value_range) for pixel in row for channel in pixel)


@dataclass(frozen=True)
class RegionStats:
    minimum: float
    maximum: float
    mean: float
    pixels: int
    invalid: int


def region_stats(frame: list[list[float]], x0: int, y0: int, x1: int, y1: int) -> RegionStats | None:
    """Minimum, maximum and mean of a region (thermal pixels, x1 and y1 excluded); None when it holds no valid pixel."""
    height = len(frame)
    width = len(frame[0]) if height else 0
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise ThermalError("the region is outside the image or empty")
    values, invalid = [], 0
    for row in frame[y0:y1]:
        for v in row[x0:x1]:
            if _finite(v):
                values.append(float(v))
            else:
                invalid += 1
    if not values:
        return None
    return RegionStats(min(values), max(values), sum(values) / len(values), len(values), invalid)
