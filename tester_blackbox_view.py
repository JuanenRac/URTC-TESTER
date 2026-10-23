# =============================================================================
# URTC Tester - tester_blackbox_view.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""What the deck draws of a black box record: the series of the chart, the table, and the records saved earlier (JSON or CSV) opened with no board.

The same rules as the web studio (``blackBox.ts``): the file must be one this tool wrote (``urtc-blackbox/1`` JSON, or the CSV with the
columns of ``urtc_can.blackbox``, in any order), every field is a whole number within the range of the wire format, a record holds at most
67 samples, and a file larger than ``MAX_FILE_BYTES`` is not a record. Nothing is guessed: a field that is not a whole number refuses the file.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from urtc_can import blackbox

MAX_FILE_BYTES = 1024 * 1024
SAMPLE_LIMIT = 67  # the ring of the firmware
FORMAT = "urtc-blackbox/1"


class ViewError(Exception):
    """A saved record that cannot be opened. ``code`` is stable (``too_big``, ``unreadable``, ``not_json``, ``wrong_format``, ``no_samples``, ``too_many``, ``missing_column``, ``bad_field``)."""

    def __init__(self, code: str, text: str = "") -> None:
        super().__init__(text or code)
        self.code = code


def _whole(value: object, maximum: int, what: str) -> int:
    if isinstance(value, bool):
        raise ViewError("bad_field", f"{what} is not a whole number from 0 to {maximum}")
    if isinstance(value, int):
        number = value
    elif isinstance(value, str) and value.strip():
        try:
            number = int(value.strip())
        except ValueError:
            raise ViewError("bad_field", f"{what} is not a whole number from 0 to {maximum}") from None
    else:
        raise ViewError("bad_field", f"{what} is not a whole number from 0 to {maximum}")
    if not 0 <= number <= maximum:
        raise ViewError("bad_field", f"{what} is not a whole number from 0 to {maximum}")
    return number


def record_from_rows(rows: list[dict]) -> blackbox.Record:
    if not rows:
        raise ViewError("no_samples", "the record holds no samples")
    if len(rows) > SAMPLE_LIMIT:
        raise ViewError("too_many", f"a record holds at most {SAMPLE_LIMIT} samples, this one has {len(rows)}")
    samples = []
    for i, row in enumerate(rows):
        where = f"sample {i}"
        fault = _whole(row.get("thermal_fault"), 3, f"{where}: thermal_fault")
        error = _whole(row.get("system_error"), 1, f"{where}: system_error")
        endstop = _whole(row.get("endstop"), 1, f"{where}: endstop")
        samples.append(blackbox.Sample(
            tick_ms=_whole(row.get("tick_ms"), 0xFFFFFFFF, f"{where}: tick_ms"),
            tool_id=_whole(row.get("tool_id"), 255, f"{where}: tool_id"),
            current_temperature=_whole(row.get("current_temperature"), 0xFFFF, f"{where}: current_temperature"),
            target_temperature=_whole(row.get("target_temperature"), 0xFFFF, f"{where}: target_temperature"),
            flags=endstop | (error << 1) | (fault << 2),
        ))
    return blackbox.Record(blackbox.VERSION, len(samples), len(samples) % SAMPLE_LIMIT, samples)


def record_from_json(text: str) -> blackbox.Record:
    try:
        doc = json.loads(text)
    except ValueError:
        raise ViewError("not_json", "not a JSON file") from None
    if not isinstance(doc, dict) or doc.get("format") != FORMAT:
        raise ViewError("wrong_format", f"not a {FORMAT} file")
    samples = doc.get("samples")
    if not isinstance(samples, list) or not all(isinstance(item, dict) for item in samples):
        raise ViewError("wrong_format", "the file has no list of samples")
    return record_from_rows(samples)


def record_from_csv(text: str) -> blackbox.Record:
    reader = csv.reader(io.StringIO(text))
    lines = [row for row in reader if any(cell.strip() for cell in row)]
    if len(lines) < 2:
        raise ViewError("no_samples", "the file has no samples")
    header = [cell.strip() for cell in lines[0]]
    for column in blackbox.CSV_COLUMNS:
        if column not in header:
            raise ViewError("missing_column", f"the file has no {column} column")
    rows = [{name: (cells[i] if i < len(cells) else None) for i, name in enumerate(header)} for cells in lines[1:]]
    return record_from_rows(rows)


def record_from_text(text: str) -> blackbox.Record:
    """A saved record of either kind, by what the text looks like."""
    return record_from_json(text) if text.lstrip().startswith("{") else record_from_csv(text)


def load_record(path: str | Path) -> blackbox.Record:
    target = Path(path)
    try:
        if target.stat().st_size > MAX_FILE_BYTES:
            raise ViewError("too_big", f"{target.name} is too big for a record")
        text = target.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        raise ViewError("unreadable", str(error)) from error
    return record_from_text(text)


def chart_series(record: blackbox.Record) -> dict:
    """The numbers the chart needs: both series, the position of the first error flag, the temperature range (rounded to tens) and the length in milliseconds."""
    samples = record.samples
    first = samples[0].tick_ms if samples else 0
    ticks = [(s.tick_ms - first) & 0xFFFFFFFF for s in samples]
    span = ticks[-1] if ticks else 0
    values = [s.current_temperature for s in samples] + [s.target_temperature for s in samples]
    low = min(values) if values else 0
    high = max(values) if values else 0
    minimum = max(0, ((low - 5) // 10) * 10)
    maximum = max(minimum + 10, -(-(high + 5) // 10) * 10)
    return {
        "ticks": ticks,
        "current": [s.current_temperature for s in samples],
        "target": [s.target_temperature for s in samples],
        "trigger": record.trigger_index if record.trigger_index is not None else -1,
        "minimum": minimum,
        "maximum": maximum,
        "span_ms": span,
    }


def table_lines(record: blackbox.Record) -> list[str]:
    """One line per sample, newest last: index, milliseconds before the last sample, temperature, set-point, flags."""
    lines = []
    for row in blackbox.rows(record):
        flags = []
        if row["endstop"]:
            flags.append("ENDSTOP")
        if row["system_error"]:
            flags.append("ERROR")
        if row["thermal_fault"]:
            flags.append(str(row["thermal_fault_name"]).upper())
        lines.append(f"{row['index']:>3}  -{row['ms_before_last']:>7} ms  {row['current_temperature']:>4} C / {row['target_temperature']:>4} C  tool {row['tool_id']:<3} {' '.join(flags)}".rstrip())
    return lines
