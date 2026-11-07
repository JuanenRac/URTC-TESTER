# =============================================================================
# URTC Tester - bus-monitor trace export
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
import time

import tester_trace_export as export

ROWS = [
    ("10:00:00.000", "0x1A0 (tool state)", 2, "0102", 0.0),
    ("10:00:00.250", "0x110", 0, "", 250.0),
    ("not-a-time", "7F8", 1, "FF", 0.0),
]


def test_offsets_follow_the_recorded_timestamps_and_fall_back_for_an_unreadable_one():
    assert export.offsets_ms(ROWS) == [0.0, 250.0, 20.0]


def test_a_timestamp_that_cannot_be_read_is_none():
    assert export.parse_ts_to_seconds("10:00:00.250") == 36000.25
    assert export.parse_ts_to_seconds("garbage") is None
    assert export.parse_ts_to_seconds(None) is None


def test_trc_has_the_header_and_one_line_per_frame():
    lines = export.render_trc(ROWS).splitlines()
    assert lines[0] == ";$FILEVERSION=1.1"
    body = [line for line in lines if not line.startswith(";")]
    assert len(body) == 3
    assert body[0].split() == ["1)", "0.0", "Rx", "01A0", "2", "01", "02"]
    assert body[1].split()[-2:] == ["0", "0"] or body[1].split()[-1] == "0"  # an empty frame has no data bytes


def test_asc_has_the_blocks_and_hex_ids():
    now = time.strptime("2026-01-02 03:04:05", "%Y-%m-%d %H:%M:%S")
    lines = export.render_asc(ROWS, now).splitlines()
    assert lines[0].startswith("date ") and "2026" in lines[0]
    assert lines[1] == "base hex  timestamps absolute"
    assert lines[-1] == "End TriggerBlock"
    frames = [line for line in lines if " Rx " in line]
    assert frames[0].split()[:4] == ["0.000000", "1", "1A0", "Rx"]
    assert frames[1].split()[0] == "0.250000"


def test_an_unknown_format_is_refused():
    try:
        export.render(ROWS, "csv")
    except ValueError:
        return
    raise AssertionError("an unknown format was accepted")


def test_both_formats_are_plain_ascii():
    export.render_trc(ROWS).encode("ascii")
    export.render_asc(ROWS).encode("ascii")


def test_a_trace_that_runs_past_midnight_keeps_counting_forward():
    rows = [("23:59:59.900", "1A0", 0, "", 0.0), ("00:00:00.100", "1A0", 0, "", 200.0), ("00:00:01.100", "1A0", 0, "", 1000.0)]
    assert [round(v, 3) for v in export.offsets_ms(rows)] == [0.0, 200.0, 1200.0]
    assert [float(line.split()[1]) for line in export.render_trc(rows).splitlines() if line.lstrip()[:1].isdigit()] == [0.0, 200.0, 1200.0]


# ---- the data bytes of a frame are separated by a space, as PCAN-View and CANalyzer write them -------------------

import pytest


@pytest.mark.parametrize("raw, expected", [
    ("", ""), (None, ""), ("0102", "01 02"), ("0102FF", "01 02 FF"), ("01 02 ff", "01 02 FF"), ("a", "a"), ("0g", "0g"), ("abc", "abc"),
    ("00 11 22 33 44 55 66 77", "00 11 22 33 44 55 66 77"), ("  AA  ", "AA"), ("aabbccddeeff0011", "AA BB CC DD EE FF 00 11"),
])
def test_spaced_bytes_separates_whole_bytes_and_keeps_anything_else_as_it_came(raw, expected):
    assert export.spaced_bytes(raw) == expected


def test_the_trc_data_column_has_the_bytes_separated_by_spaces():
    body = [line for line in export.render_trc(ROWS).splitlines() if not line.startswith(";")]
    assert body[0].split()[-2:] == ["01", "02"]
    assert body[0].endswith("2   01 02")
    assert body[1].rstrip().endswith("0")  # an empty frame: no data column and no trailing space


def test_the_asc_data_column_has_the_bytes_separated_by_spaces():
    frames = [line for line in export.render_asc(ROWS).splitlines() if " Rx " in line]
    assert frames[0].split()[-4:] == ["d", "2", "01", "02"]
    assert frames[1].split()[-2:] == ["d", "0"] and frames[1] == frames[1].rstrip()


def test_an_eight_byte_frame_keeps_all_its_bytes_in_both_formats():
    rows = [("10:00:00.000", "1A0", 8, "0011223344556677", 0.0)]
    assert export.render_trc(rows).splitlines()[-1].endswith("8   00 11 22 33 44 55 66 77")
    assert export.render_asc(rows).splitlines()[-2].endswith("d 8 00 11 22 33 44 55 66 77")


def test_the_spaced_output_stays_plain_ascii_and_one_line_per_frame():
    rows = [("10:00:00.000", "1A0", 3, "0A0B0C", 0.0), ("10:00:00.010", "1A1", 0, "", 10.0)]
    for text in (export.render_trc(rows), export.render_asc(rows)):
        text.encode("ascii")
        assert text.count("\n") == len(text.splitlines())
