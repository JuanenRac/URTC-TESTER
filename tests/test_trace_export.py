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
    assert body[0].split() == ["1)", "0.0", "Rx", "01A0", "2", "0102"]
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
