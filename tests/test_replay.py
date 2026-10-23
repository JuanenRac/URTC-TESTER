# =============================================================================
# URTC Tester - tests/test_replay.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Replay of a recorded bus trace: parsing of .trc and .asc, the timing rules of the player with a manual clock, and the refusals."""
from __future__ import annotations

import pytest

import tester_replay as replay
import tester_trace_export as export

ROWS = [
    ("10:00:00.000", "0x1A0", 2, "0102", 0.0),
    ("10:00:00.100", "0x110", 0, "", 100.0),
    ("10:00:00.300", "7F8", 1, "FF", 0.0),
]


def entries(*times):
    return tuple(replay.Entry(t, 0x100 + i, bytes([i % 256])) for i, t in enumerate(times))


# ---- parsing --------------------------------------------------------------------------------------------------------------------
def test_a_trc_written_by_the_monitor_is_read_back_frame_for_frame():
    parsed = replay.parse_trace(export.render_trc(ROWS))
    assert parsed.format == "trc" and parsed.rejected == 0
    assert [(e.time_ms, e.can_id, e.data) for e in parsed.entries] == [(0.0, 0x1A0, b"\x01\x02"), (100.0, 0x110, b""), (300.0, 0x7F8, b"\xff")]


def test_an_asc_written_by_the_monitor_is_read_back_with_the_same_gaps():
    parsed = replay.parse_trace(export.render_asc(ROWS))
    assert parsed.format == "asc"
    assert [(round(e.time_ms), e.can_id) for e in parsed.entries] == [(0, 0x1A0), (100, 0x110), (300, 0x7F8)]


def test_only_received_frames_are_played_and_the_time_is_relative_and_sorted():
    text = "\n".join([
        "     1)       500.0  Rx    0100  1   01",
        "     2)       200.0  Tx    0101  1   02",
        "     3)       300.0  Rx    0102  1   03",
    ])
    parsed = replay.parse_trace(text)
    assert [(e.time_ms, e.can_id) for e in parsed.entries] == [(0.0, 0x102), (200.0, 0x100)]


def test_lines_that_look_like_frames_but_are_wrong_are_counted_and_skipped():
    text = "\n".join([
        "     1)         0.0  Rx    0100  2   01",          # length does not match
        "     2)         1.0  Rx    0100  9   0102030405060708FF",  # more than 8 bytes
        "     3)         2.0  Rx    0100  1   ZZ",            # not hexadecimal: not even a frame line
        "     4)         3.0  Rx    0100  1   01",            # good
        "; a comment",
        "garbage",
    ])
    parsed = replay.parse_trace(text)
    assert len(parsed.entries) == 1 and parsed.rejected == 2


def test_a_trace_longer_than_the_limit_is_cut_and_the_rest_counted(monkeypatch):
    monkeypatch.setattr(replay, "MAX_TRACE_FRAMES", 2)
    text = "\n".join(f"     {i})       {i}.0  Rx    0100  0" for i in range(1, 5))
    parsed = replay.parse_trace(text)
    assert len(parsed.entries) == 2 and parsed.rejected == 2


def test_load_trace_refuses_a_file_that_is_too_big_empty_or_missing(tmp_path, monkeypatch):
    empty = tmp_path / "empty.trc"
    empty.write_text("; nothing here\n")
    with pytest.raises(replay.ReplayError) as caught:
        replay.load_trace(empty)
    assert caught.value.code == "empty"
    with pytest.raises(replay.ReplayError) as caught:
        replay.load_trace(tmp_path / "missing.trc")
    assert caught.value.code == "unreadable"
    big = tmp_path / "big.trc"
    big.write_text(export.render_trc(ROWS))
    monkeypatch.setattr(replay, "MAX_TRACE_BYTES", 10)
    with pytest.raises(replay.ReplayError) as caught:
        replay.load_trace(big)
    assert caught.value.code == "too_big"


def test_load_trace_reads_a_file(tmp_path):
    path = tmp_path / "t.trc"
    path.write_text(export.render_trc(ROWS))
    assert len(replay.load_trace(path).entries) == 3


# ---- the player -----------------------------------------------------------------------------------------------------------------
def test_the_frames_come_out_when_they_are_due_and_the_player_finishes():
    player = replay.TracePlayer(entries(0, 100, 300))
    player.start(1000)
    assert [e.can_id for e in player.advance(1000)] == [0x100]
    assert player.advance(1099) == []
    assert [e.can_id for e in player.advance(1100)] == [0x101]
    assert [e.can_id for e in player.advance(2000)] == [0x102]
    assert player.state == replay.FINISHED and player.progress == 1.0 and player.advance(5000) == []


def test_the_speed_divides_the_gaps_and_a_long_silence_is_shortened():
    fast = replay.TracePlayer(entries(0, 1000), speed=10)
    fast.start(0)
    fast.advance(0)
    assert fast.advance(99) == [] and len(fast.advance(100)) == 1
    slow = replay.TracePlayer(entries(0, 1000), speed=0.25)
    slow.start(0)
    slow.advance(0)
    assert slow.advance(3999) == [] and len(slow.advance(4000)) == 1
    silent = replay.TracePlayer(entries(0, 600_000))
    silent.start(0)
    silent.advance(0)
    assert silent.advance(1999) == [] and len(silent.advance(2000)) == 1  # a silence of ten minutes waits MAX_GAP_MS


def test_pause_keeps_the_time_that_was_left_and_stop_goes_back_to_the_first_frame():
    player = replay.TracePlayer(entries(0, 1000))
    player.start(0)
    player.advance(0)
    player.pause(400)  # 600 ms were left
    assert player.state == replay.PAUSED and player.advance(10_000) == []
    player.start(5000)
    assert player.advance(5599) == [] and len(player.advance(5600)) == 1
    player.stop()
    assert player.state == replay.IDLE and player.played == 0
    player.start(0)
    assert [e.can_id for e in player.advance(0)] == [0x100]


def test_a_looping_trace_waits_a_moment_and_starts_again():
    player = replay.TracePlayer(entries(0, 100), loop=True)
    player.start(0)
    assert len(player.advance(0)) == 1 and len(player.advance(100)) == 1
    assert player.state == replay.PLAYING
    assert player.advance(100 + replay.LOOP_PAUSE_MS - 1) == []
    assert len(player.advance(100 + replay.LOOP_PAUSE_MS)) == 1
    player.loop = False
    player.advance(100 + replay.LOOP_PAUSE_MS + 100)
    assert player.state == replay.FINISHED


def test_a_stalled_window_does_not_release_the_whole_trace_at_once():
    player = replay.TracePlayer(entries(*([0] * (replay.MAX_PER_ADVANCE + 50))))
    player.start(0)
    assert len(player.advance(0)) == replay.MAX_PER_ADVANCE
    assert len(player.advance(0)) == 50


def test_an_empty_player_does_nothing_and_the_speed_is_checked():
    player = replay.TracePlayer(())
    player.start(0)
    assert player.state == replay.IDLE and player.advance(0) == [] and player.progress == 0.0
    for bad in (0, -3, float("nan"), "fast", None):
        assert replay.checked_speed(bad) == 1.0
    assert replay.checked_speed(1000) == 100.0
    assert replay.checked_speed(2) == 2.0
