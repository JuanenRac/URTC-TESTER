# =============================================================================
# URTC Tester - tests/test_blackbox_view.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The black box viewer: records saved earlier (JSON and CSV) are read back as the tool wrote them, the chart series are right, and a file that is not a record is refused."""
from __future__ import annotations

import json

import pytest

import tester_blackbox_view as view
import tester_extras as extras
from urtc_can import blackbox


def sample(tick, current, target, flags=0):
    return blackbox.Sample(tick_ms=tick, tool_id=0, current_temperature=current, target_temperature=target, flags=flags)


def record(error_at=None, count=6):
    samples = []
    for i in range(count):
        flags = 2 | (1 << 2) if error_at is not None and i >= error_at else 0
        samples.append(sample(1000 + i * 100, 300 + i * 10, 350, flags))
    return blackbox.Record(blackbox.VERSION, len(samples), len(samples) % view.SAMPLE_LIMIT, samples)


def test_a_saved_json_and_a_saved_csv_are_read_back_as_the_same_record(tmp_path):
    original = record(error_at=4)
    csv_path, json_path = extras.save_black_box(original, str(tmp_path), "r")
    for path in (csv_path, json_path):
        again = view.load_record(path)
        assert again.samples == original.samples and again.trigger_index == 4


def test_the_text_decides_between_json_and_csv():
    original = record()
    assert view.record_from_text(blackbox.to_json(original)).samples == original.samples
    assert view.record_from_text("\n\n" + blackbox.to_csv(original)).samples == original.samples


def test_the_chart_series_have_the_samples_the_trigger_and_a_range_in_tens():
    series = view.chart_series(record(error_at=3))
    assert series["ticks"] == [0, 100, 200, 300, 400, 500]
    assert series["current"][0] == 300 and series["target"] == [350] * 6
    assert series["trigger"] == 3 and series["span_ms"] == 500
    assert series["minimum"] == 290 and series["maximum"] == 360
    assert view.chart_series(record())["trigger"] == -1


def test_the_ticks_of_the_chart_survive_the_wrap_of_the_board_clock():
    wrapped = blackbox.Record(blackbox.VERSION, 2, 2, [sample(0xFFFFFF00, 20, 20), sample(0x100, 25, 20)])
    assert view.chart_series(wrapped)["ticks"] == [0, 0x200]
    assert view.chart_series(blackbox.Record(blackbox.VERSION, 0, 0, []))["span_ms"] == 0


def test_the_table_has_one_line_per_sample_with_the_flags_in_words():
    lines = view.table_lines(record(error_at=5))
    assert len(lines) == 6
    assert "ERROR" in lines[5] and "MAX_TEMPERATURE" in lines[5] and "ERROR" not in lines[4]
    assert lines[0].startswith("  0") and "300 C /  350 C" in lines[0]


@pytest.mark.parametrize("text,code", [
    ("not json at all {", "not_json"),
    (json.dumps({"format": "other/1", "samples": []}), "wrong_format"),
    (json.dumps({"format": "urtc-blackbox/1"}), "wrong_format"),
    (json.dumps({"format": "urtc-blackbox/1", "samples": [1, 2]}), "wrong_format"),
    (json.dumps({"format": "urtc-blackbox/1", "samples": []}), "no_samples"),
    ("index,tick_ms\n", "no_samples"),
    ("index,tick_ms\n0,1\n", "missing_column"),
])
def test_a_file_that_is_not_a_record_is_refused_with_a_code(text, code):
    with pytest.raises(view.ViewError) as caught:
        view.record_from_text(text) if code != "not_json" else view.record_from_json(text)
    assert caught.value.code == code


def good_row(**changes):
    row = {"tick_ms": 1, "tool_id": 0, "current_temperature": 20, "target_temperature": 20, "endstop": 0, "system_error": 0, "thermal_fault": 0}
    row.update(changes)
    return row


@pytest.mark.parametrize("changes", [
    {"tick_ms": -1}, {"tick_ms": 2**32}, {"tool_id": 256}, {"current_temperature": 70000}, {"target_temperature": "hot"},
    {"endstop": 2}, {"system_error": True}, {"thermal_fault": 4}, {"thermal_fault": None}, {"tick_ms": 1.5}, {"tick_ms": ""},
])
def test_a_field_that_is_not_a_whole_number_in_range_refuses_the_file(changes):
    with pytest.raises(view.ViewError) as caught:
        view.record_from_rows([good_row(**changes)])
    assert caught.value.code == "bad_field"


def test_a_record_holds_at_most_the_samples_of_the_ring():
    assert len(view.record_from_rows([good_row()] * view.SAMPLE_LIMIT).samples) == view.SAMPLE_LIMIT
    with pytest.raises(view.ViewError) as caught:
        view.record_from_rows([good_row()] * (view.SAMPLE_LIMIT + 1))
    assert caught.value.code == "too_many"


def test_load_record_refuses_a_big_or_missing_or_undecodable_file(tmp_path, monkeypatch):
    path = tmp_path / "r.json"
    path.write_text(blackbox.to_json(record()), encoding="utf-8")
    monkeypatch.setattr(view, "MAX_FILE_BYTES", 20)
    with pytest.raises(view.ViewError) as caught:
        view.load_record(path)
    assert caught.value.code == "too_big"
    with pytest.raises(view.ViewError) as caught:
        view.load_record(tmp_path / "missing.json")
    assert caught.value.code == "unreadable"
    monkeypatch.undo()
    binary = tmp_path / "b.csv"
    binary.write_bytes(b"\xff\xfe\x00\x01")
    with pytest.raises(view.ViewError) as caught:
        view.load_record(binary)
    assert caught.value.code == "unreadable"


def test_a_csv_with_the_columns_in_another_order_and_a_bom_is_read(tmp_path):
    columns = list(blackbox.CSV_COLUMNS)[::-1]
    rows = blackbox.rows(record(count=2))
    text = "﻿" + ",".join(columns) + "\n" + "\n".join(",".join(str(row[c]) for c in columns) for row in rows) + "\n"
    path = tmp_path / "r.csv"
    path.write_text(text, encoding="utf-8")
    assert len(view.load_record(path).samples) == 2
