# =============================================================================
# URTC Tester - tests/test_qt_replay_blackbox.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The replay and the black box viewer of the deck: what the bridge shows, what it refuses, and that a replay never touches the bus."""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QCoreApplication  # noqa: E402

import qt_tester  # noqa: E402
import tester_extras as extras  # noqa: E402
import tester_replay as replay  # noqa: E402
import tester_trace_export as export  # noqa: E402
from urtc_can import blackbox  # noqa: E402

ROWS = [("10:00:00.000", "0x1A0", 2, "0102", 0.0), ("10:00:00.100", "0x110", 0, "", 100.0), ("10:00:00.300", "7F8", 1, "FF", 0.0)]


@pytest.fixture(scope="module")
def qt_app():
    yield QCoreApplication.instance() or QCoreApplication([])


@pytest.fixture
def bridge(qt_app):
    instance = qt_tester.TesterQtBridge()
    instance.clock = [0.0]
    instance._now_ms = lambda: instance.clock[0]
    return instance


@pytest.fixture
def trace(tmp_path):
    path = tmp_path / "t.trc"
    path.write_text(export.render_trc(ROWS), encoding="ascii")
    return str(path)


def test_a_trace_is_loaded_played_with_its_own_rows_and_never_sent(bridge, trace):
    sent = []

    class Transport:
        def send_frame(self, *args):
            sent.append(args)

    bridge.openReplay(trace)
    assert bridge.replayLoaded and bridge.replayState == "idle" and bridge.replayLines == []
    bridge.playReplay()
    assert bridge.replayPlaying
    bridge.clock[0] = 1000.0
    bridge._replay_tick()
    assert not bridge.replayPlaying and bridge.replayState == "finished"
    assert len(bridge.replayLines) == 3 and all(line.startswith("REPLAY") for line in bridge.replayLines)
    assert "0x1A0" in bridge.replayLines[2] or "1A0" in bridge.replayLines[2]
    assert bridge.replayProgressText == "3 / 3 frames" and bridge.replayPercent == 100
    assert bridge.monitorCount == 0 and sent == []  # the monitor table of the bus is untouched


def test_a_replay_starts_again_from_the_first_frame_after_it_finished(bridge, trace):
    bridge.openReplay(trace)
    bridge.playReplay()
    bridge.clock[0] = 5000.0
    bridge._replay_tick()
    bridge.playReplay()
    bridge._replay_tick()
    assert len(bridge.replayLines) == 1  # the list was cleared and the first frame is out


def test_pause_stop_clear_speed_and_loop(bridge, trace):
    bridge.openReplay(trace)
    bridge.setReplaySpeed(10)
    bridge.setReplayLoop(True)
    assert bridge.replaySpeed == 10.0 and bridge.replayLoop and bridge._replay_player.speed == 10.0 and bridge._replay_player.loop
    bridge.playReplay()
    bridge.pauseReplay()
    assert bridge.replayState == "paused"
    bridge.stopReplay()
    assert bridge.replayState == "idle"
    bridge._replay_rows.append((0.0, "1", 0, ""))
    bridge.clearReplay()
    assert bridge.replayLines == [] and bridge.replayNotice == ""
    bridge.setReplaySpeed("nonsense")
    assert bridge.replaySpeed == 1.0
    assert list(bridge.replaySpeeds) == list(replay.SPEEDS)


def test_a_replay_is_blocked_while_a_board_is_connected_and_pauses_if_one_connects(bridge, trace):
    bridge._transport = object()
    bridge.openReplay(trace)
    bridge.playReplay()
    assert not bridge.replayPlaying and "board is connected" in bridge.replayNotice
    bridge._transport = None
    bridge.playReplay()
    assert bridge.replayPlaying
    bridge._transport = object()
    bridge._replay_tick()
    assert bridge.replayState == "paused" and "board is connected" in bridge.replayNotice
    bridge._transport = None


def test_a_trace_that_cannot_be_replayed_says_why_and_clears_the_player(bridge, tmp_path, trace):
    bridge.openReplay(trace)
    empty = tmp_path / "e.trc"
    empty.write_text("; no frames\n")
    bridge.openReplay(str(empty))
    assert not bridge.replayLoaded and "no frames" in bridge.replayNotice
    bridge.openReplay(str(tmp_path / "missing.trc"))
    assert "could not be read" in bridge.replayNotice


def test_lines_that_were_not_frames_are_reported_after_loading(bridge, tmp_path):
    path = tmp_path / "r.trc"
    path.write_text("     1)         0.0  Rx    0100  2   01\n     2)         1.0  Rx    0100  1   01\n")
    bridge.openReplay(str(path))
    assert "1 lines were not valid frames" in bridge.replayNotice


def test_a_saved_black_box_is_opened_and_drawn_without_a_board(bridge, tmp_path):
    samples = [blackbox.Sample(1000 + i * 100, 0, 300 + i * 10, 350, 6 if i >= 3 else 0) for i in range(5)]
    original = blackbox.Record(blackbox.VERSION, 5, 5, samples)
    csv_path, json_path = extras.save_black_box(original, str(tmp_path), "r")
    assert not bridge.hasBlackBoxView and bridge.blackBoxLines == []
    bridge.openBlackBox(json_path)
    assert bridge.hasBlackBoxView and len(bridge.blackBoxLines) == 5
    assert bridge.blackBoxSeries["trigger"] == 3 and bridge.blackBoxSeries["span_ms"] == 400
    assert "r.json: 5 samples" in bridge.blackBoxViewNotice and bridge.blackBoxSpanText == "0.4 s recorded"
    bridge.openBlackBox(csv_path)
    assert len(bridge.blackBoxLines) == 5


def test_a_file_that_is_not_a_record_keeps_the_previous_drawing_and_says_why(bridge, tmp_path):
    good = extras.save_black_box(blackbox.Record(blackbox.VERSION, 1, 1, [blackbox.Sample(1, 0, 20, 20, 0)]), str(tmp_path), "g")[1]
    bridge.openBlackBox(good)
    bad = tmp_path / "bad.json"
    bad.write_text('{"format": "other"}')
    bridge.openBlackBox(str(bad))
    assert bridge.hasBlackBoxView and "bad.json is not a record that can be read" in bridge.blackBoxViewNotice


def test_the_record_read_from_the_board_is_drawn_too(bridge):
    record = blackbox.Record(blackbox.VERSION, 2, 2, [blackbox.Sample(10, 0, 20, 25, 0), blackbox.Sample(20, 0, 22, 25, 2)])
    bridge._on_query_result("black_box", ("ok", "2 samples", "a.csv", "a.json", record))
    assert bridge.hasBlackBoxView and bridge.blackBoxSeries["trigger"] == 1 and bridge.blackBoxViewNotice == ""
    assert "2 samples" in bridge.blackBoxText
    bridge._on_query_result("black_box", ("fail", "no answer"))
    assert bridge.hasBlackBoxView  # a failed read does not clear what is drawn
