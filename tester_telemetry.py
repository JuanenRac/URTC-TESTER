# =============================================================================
# URTC Tester - live telemetry readouts of each tool, shared by the Qt Quick deck
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Which broadcast frames each tool sends, how a frame becomes a value on screen, and the recorded series.

Nothing here touches a bus or a window: a reader thread gives ``decode_readout`` the data of a frame and shows the
text it returns.  The frames are the ones the tools broadcast on their own (temperature, RPM, endstop); reading
them transmits nothing, so a readout works in listen-only mode and next to a running output.
"""
from __future__ import annotations

import csv
import struct
from dataclasses import dataclass

from tester_config import (
    CAN_ID_3DP_HOTEND_FAN_RPM, CAN_ID_3DP_HOTEND_TELEM, CAN_ID_3DP_LAYER_FAN_RPM, CAN_ID_AOI_TELEMETRY,
    CAN_ID_DRILL_TELEMETRY, CAN_ID_FLYING_PROBE_BASIC, CAN_ID_LASER_TELEMETRY, CAN_ID_SOLDER_TELEMETRY, _,
)

CELSIUS = "celsius"
RPM = "rpm"
ENDSTOP = "endstop"
ADC = "adc"

MAX_HISTORY = 200_000  # about eight hours of one point every 150 ms; the series no longer grows for ever
GRAPH_POINTS = 60      # the live graph shows a short rolling window


@dataclass(frozen=True)
class Readout:
    key: str            # also the column name of an exported series
    label_key: str      # translation key of the caption
    can_id: int
    kind: str
    offset: int = 0     # where the value starts in the frame
    graph_max: int = 0  # the fixed top of the graph; 0 means the value is not graphed


_TEMP = "LBL_LIVE_TEMPERATURE"

READOUTS: dict[int, tuple[Readout, ...]] = {
    0: (Readout("solder_iron_temp_c", _TEMP, CAN_ID_SOLDER_TELEMETRY, CELSIUS, graph_max=450),),
    5: (
        Readout("drill_rpm", "LBL_ACTUAL_RPM", CAN_ID_DRILL_TELEMETRY, RPM),
        Readout("drill_endstop", "LBL_ENDSTOP_LIMIT_SWITCH", CAN_ID_DRILL_TELEMETRY, ENDSTOP, offset=2),
    ),
    8: (Readout("aoi_endstop", "LBL_ENDSTOP_LIMIT_SWITCH", CAN_ID_AOI_TELEMETRY, ENDSTOP),),
    9: (Readout("laser_endstop", "LBL_ENDSTOP_LIMIT_SWITCH", CAN_ID_LASER_TELEMETRY, ENDSTOP),),
    10: (
        Readout("hotend_nozzle_temp_c", "LBL_HOTEND_TEMPERATURE", CAN_ID_3DP_HOTEND_TELEM, CELSIUS, graph_max=300),
        Readout("layer_fan_rpm", "LBL_LAYER_FAN_RPM", CAN_ID_3DP_LAYER_FAN_RPM, RPM),
        Readout("hotend_fan_rpm", "LBL_HOTEND_FAN_RPM", CAN_ID_3DP_HOTEND_FAN_RPM, RPM),
    ),
    17: (Readout("flying_probe_raw_adc", "LBL_FLYING_PROBE_BASIC", CAN_ID_FLYING_PROBE_BASIC, ADC),),
    # The hot-air station reports on the soldering iron's temperature frame: same loop, same wire format.
    19: (Readout("hot_air_nozzle_temp_c", _TEMP, CAN_ID_SOLDER_TELEMETRY, CELSIUS, graph_max=450),),
}


def readouts_for(tool_id: int) -> tuple[Readout, ...]:
    return READOUTS.get(tool_id, ())


def graphed(tool_id: int) -> Readout | None:
    """The readout that has a graph and a CSV export, if the tool has one."""
    return next((r for r in readouts_for(tool_id) if r.graph_max), None)


def decode_readout(readout: Readout, data: bytes) -> tuple[str, float] | None:
    """The text to show and the number behind it for a frame, or None when the frame is too short to hold the value."""
    start = readout.offset
    if readout.kind == ENDSTOP:
        if len(data) <= start:
            return None
        triggered = bool(data[start])
        return (_("VAL_TRIGGERED") if triggered else _("VAL_ENDSTOP_OPEN")), float(triggered)
    if len(data) < start + 2:
        return None
    value = struct.unpack(">H", data[start:start + 2])[0]
    if readout.kind == CELSIUS:
        return f"{value} °C", float(value)
    if readout.kind == RPM:
        return f"{value} RPM", float(value)
    return f"{value} ADC", float(value)


class Series:
    """The values of one readout over time: a short rolling window for the graph, and the whole run for the export."""

    def __init__(self) -> None:
        self.window: list[float] = []
        self.history: list[tuple[float, float]] = []  # (seconds since the first point, value)
        self._first: float | None = None

    def add(self, value: float, now: float) -> None:
        if self._first is None:
            self._first = now
        self.window.append(value)
        if len(self.window) > GRAPH_POINTS:
            del self.window[0]
        self.history.append((round(now - self._first, 3), value))
        if len(self.history) > MAX_HISTORY:
            del self.history[:len(self.history) - MAX_HISTORY]

    def clear(self) -> None:
        self.window.clear()
        self.history.clear()
        self._first = None


def write_csv(path: str, label: str, history: list[tuple[float, float]]) -> int:
    """Write the series as ``seconds,<label>``; returns the number of points written."""
    with open(path, "w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["seconds", label])
        writer.writerows(history)
    return len(history)
