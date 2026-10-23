# =============================================================================
# URTC Tester - bus-monitor trace export (.trc and .asc)
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Text renderers for the raw bus monitor's recorded frames, shared by the original window and the Qt Quick deck.

A row is ``(time, can_id, dlc, data_hex, dt_ms)`` exactly as the monitor tables hold them: ``time`` is
``"HH:MM:SS.mmm"``, ``can_id`` starts with the hex ID (``"0x1A0 (name)"`` or ``"1A0"``), ``data_hex`` is ``""``
for an empty frame. Both formats are the recognizable shape of the PEAK PCAN-View ``.trc`` and Vector ``.asc``
traces, not guaranteed byte-identical to what each vendor's own exporter writes.
"""
from __future__ import annotations

import time


def parse_ts_to_seconds(ts_str):
    """``"HH:MM:SS.mmm"`` to seconds since midnight, or None when it cannot be read."""
    try:
        hms, ms = ts_str.split(".")
        h, m, s = (int(x) for x in hms.split(":"))
        return h * 3600 + m * 60 + s + int(ms) / 1000.0
    except (ValueError, AttributeError):
        return None


def offsets_ms(rows):
    """Offsets in milliseconds from the first readable timestamp.

    A row whose timestamp cannot be parsed falls back to a synthetic 10 ms spacing instead of failing the export.
    """
    parsed = [parse_ts_to_seconds(row[0]) for row in rows]
    t0 = next((t for t in parsed if t is not None), None)
    result = []
    for index, t in enumerate(parsed):
        if t is not None and t0 is not None:
            result.append((t - t0) * 1000.0)
        else:
            result.append(index * 10.0)
    return result


def _id_hex(can_id):
    return str(can_id).split(" ")[0].replace("0x", "")


def render_trc(rows):
    """PEAK PCAN-View style trace text."""
    offsets = offsets_ms(rows)
    lines = [";$FILEVERSION=1.1", ";$STARTTIME=0", ";$COLUMNS=N,O,T,I,d,l,D", ";",
             ";   Message Number", ";   Time Offset (ms)", ";   Type", ";   ID (hex)",
             ";   Data Length Code", ";   Data Bytes (hex)", ";" + "-" * 80]
    for index, (_ts, can_id, dlc, data, _dt) in enumerate(rows, start=1):
        lines.append(f"{index:>6}) {offsets[index - 1]:>10.1f}  Rx    {_id_hex(can_id).zfill(4)}  {dlc}   {data}")
    return "\n".join(lines) + "\n"


def render_asc(rows, now=None):
    """Vector ASCII style trace text. ``now`` is a struct_time for the header (the current time by default)."""
    stamp = time.strftime("%a %b %d %H:%M:%S.000 %Y", now or time.localtime())
    offsets = offsets_ms(rows)
    lines = ["date " + stamp, "base hex  timestamps absolute", "internal events logged",
             "Begin Triggerblock " + stamp]
    for index, (_ts, can_id, dlc, data, _dt) in enumerate(rows):
        lines.append(f"   {offsets[index] / 1000.0:.6f} 1  {_id_hex(can_id):<15} Rx   d {dlc} {data}")
    lines.append("End TriggerBlock")
    return "\n".join(lines) + "\n"


def render(rows, fmt, now=None):
    """``fmt`` is ``"trc"`` or ``"asc"``."""
    if fmt == "trc":
        return render_trc(rows)
    if fmt == "asc":
        return render_asc(rows, now)
    raise ValueError(f"unknown trace format: {fmt}")
