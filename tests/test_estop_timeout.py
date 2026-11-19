# =============================================================================
# URTC Tester - tests/test_estop_timeout.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The silence of the master of the emergency stop in the Tester: read with the queries 3 and 4 of 0x1AF, written with the eight-byte 0x1AE after the
usual confirmation, never with a value outside 0 and the limits. The head is a small fake of the firmware's answers; nothing here has run on a board.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import tester_extras as extras  # noqa: E402
from urtc_can import estop_follow as ef  # noqa: E402
from urtc_can import protocol  # noqa: E402

LANGUAGES = ("english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese")
KEYS = ("LBL_ESTOP_TIMEOUT", "BTN_ESTOP_TIMEOUT_READ", "BTN_ESTOP_TIMEOUT_WRITE", "LOG_ESTOP_TIMEOUT_READ", "LOG_ESTOP_TIMEOUT_INVALID",
        "LOG_ESTOP_TIMEOUT_MISMATCH", "LOG_ESTOP_TIMEOUT_UNSUPPORTED")


def test_the_limits_and_the_valid_values():
    assert (extras.ESTOP_TIMEOUT_MIN_MS, extras.ESTOP_TIMEOUT_MAX_MS) == (40, 500)
    for ms in (0, 40, 100, 500):
        assert extras.estop_timeout_valid(ms)
    for ms in (-1, 1, 39, 501, 65535, True, 50.0, "50", None):
        assert not extras.estop_timeout_valid(ms), ms


def test_the_frames_are_the_ones_of_the_specification():
    assert extras.estop_timeout_query(True) == (0x1AF, b"\x04")
    assert extras.estop_timeout_query(False) == (0x1AF, b"\x03")
    assert extras.estop_timeout_write_frame(0x91, 0x02, 80) == (0x1AE, bytes.fromhex("464541549102" + "0050"))
    assert extras.estop_timeout_write_frame(0x80, 0, 0)[1][-2:] == b"\x00\x00"
    for ms in (1, 39, 501, 65535):
        with pytest.raises(ValueError):
            extras.estop_timeout_write_frame(0x80, 0, ms)
    answer = ef.encode_timeout_answer(0x80, 0x80, 0, 0, 500)
    assert extras.decode_estop_timeout(answer)["timeout_ms"] == 500
    assert extras.decode_estop_timeout(answer[:6]) is None and extras.decode_estop_timeout(answer[:3]) is None


def test_the_deck_has_the_field_the_two_buttons_and_asks_before_writing():
    deck = (ROOT / "assets" / "qml" / "TesterDeck.qml").read_text(encoding="utf-8")
    write = next(line for line in deck.splitlines() if "estopTimeoutWriteButton" in line or "testerBackend.writeEstopTimeout" in line)
    assert "requestUtilityAction" in deck[deck.index("estopTimeoutWriteButton"):deck.index("estopTimeoutWriteButton") + 600]
    assert write and "readEstopTimeout" in deck and "estopTimeoutSpin" in deck


def test_every_text_is_in_the_eight_languages():
    for language in LANGUAGES:
        lines = (ROOT / "language" / f"{language}.lng").read_text(encoding="utf-8").splitlines()
        for key in KEYS:
            assert any(line.startswith(key + "=") and len(line) > len(key) + 3 for line in lines), (language, key)


class FakeHead:
    """What the firmware does with the new forms: answers 3 and 4, stores a valid eight-byte write, ignores an invalid one."""

    def __init__(self, stored=0x11, stored_ext=0x02, stored_timeout=0, running_timeout=100, old=False, keeps=True):
        self.sent: list[tuple[int, bytes]] = []
        self.queue: list[tuple[int, bytes]] = []
        self.stored, self.stored_ext, self.stored_timeout, self.running_timeout = stored, stored_ext, stored_timeout, running_timeout
        self.old, self.keeps = old, keeps

    def send_frame(self, can_id, data=b""):
        self.sent.append((can_id, bytes(data)))
        if self.old:
            return
        write = ef.parse_features_write(bytes(data)) if can_id == protocol.CAN_ID_SET_FEATURES else None
        if write is not None and write.timeout_ms is not None:
            self.stored, self.stored_ext = write.mask, write.mask_ext
            if self.keeps:
                self.stored_timeout = write.timeout_ms
            self.queue.append((0x1AF, ef.encode_timeout_answer(self.stored, 0, self.stored_ext, 0, self.stored_timeout)))
        elif can_id == protocol.CAN_ID_FEATURES_RESP:
            form = ef.query_form(bytes(data))
            ms = self.stored_timeout if form == ef.QUERY_TIMEOUT_STORED else self.running_timeout
            self.queue.append((0x1AF, ef.encode_timeout_answer(self.stored, 0, self.stored_ext, 0, ms)))

    def read_frame(self, timeout=0.1):
        return self.queue.pop(0) if self.queue else None


try:
    import qt_tester
except ImportError:  # PySide6 is not installed
    qt_tester = None


@pytest.mark.skipif(qt_tester is None, reason="PySide6 is not available")
class TestBridge:
    def make(self, head):
        bridge = qt_tester.TesterQtBridge()
        bridge._log = lambda text: None
        bridge._transport = head
        results: list[tuple] = []
        bridge._queryResult.connect(lambda key, result: results.append((key, result)))
        return bridge, results

    def run(self, bridge, call):
        class Inline:
            def __init__(self, target, daemon=None, name=None):
                self.target = target

            def start(self):
                self.target()

        with mock.patch.object(qt_tester.threading, "Thread", Inline), mock.patch.object(type(bridge), "canUseUtilityPanels", mock.PropertyMock(return_value=True)):
            call()

    def test_reading_asks_the_stored_and_the_running_value_and_writes_nothing(self):
        head = FakeHead(stored_timeout=250, running_timeout=100)
        bridge, results = self.make(head)
        self.run(bridge, bridge.readEstopTimeout)
        assert head.sent == [(0x1AF, b"\x04"), (0x1AF, b"\x03")]
        assert results == [("estop_timeout", ("read", 100, 250))]

    def test_writing_keeps_the_switches_of_both_bytes_and_shows_what_is_stored(self):
        head = FakeHead(stored=0x91, stored_ext=0x02)
        bridge, results = self.make(head)
        self.run(bridge, lambda: bridge.writeEstopTimeout(80))
        writes = [frame for frame in head.sent if frame[0] == 0x1AE]
        assert writes == [(0x1AE, bytes.fromhex("464541549102" + "0050"))]
        assert results == [("estop_timeout", ("read", 100, 80))]

    @pytest.mark.parametrize("ms", [1, 39, 501, 65535, -5])
    def test_a_value_outside_the_limits_never_reaches_the_bus(self, ms):
        head = FakeHead()
        bridge, results = self.make(head)
        self.run(bridge, lambda: bridge.writeEstopTimeout(ms))
        assert head.sent == []
        assert results == [("estop_timeout", ("invalid", ms))]

    def test_a_head_that_does_not_keep_the_value_is_reported(self):
        head = FakeHead(keeps=False, stored_timeout=0)
        bridge, results = self.make(head)
        self.run(bridge, lambda: bridge.writeEstopTimeout(80))
        assert results == [("estop_timeout", ("written", 0))]

    def test_an_older_head_is_told_so_and_nothing_is_written(self):
        head = FakeHead(old=True)
        bridge, results = self.make(head)
        with mock.patch.object(qt_tester.time, "monotonic", side_effect=[0.0, 5.0, 5.0, 5.0]):
            self.run(bridge, lambda: bridge.writeEstopTimeout(80))
        assert results == [("estop_timeout", ("unsupported",))]
        assert all(frame[0] != 0x1AE for frame in head.sent)

    def test_nothing_is_sent_when_the_utility_panels_are_blocked(self):
        head = FakeHead()
        bridge, results = self.make(head)
        bridge.writeEstopTimeout(80)
        bridge.readEstopTimeout()
        assert head.sent == [] and results == []

    def test_the_text_for_each_result(self):
        bridge = qt_tester.TesterQtBridge()
        bridge._log = lambda text: None
        bridge._on_query_result("estop_timeout", ("read", 100, 0))
        assert "100" in bridge.estopTimeoutText
        bridge._on_query_result("estop_timeout", ("invalid", 5))
        assert "40" in bridge.estopTimeoutText and "500" in bridge.estopTimeoutText
        bridge._on_query_result("estop_timeout", ("unsupported",))
        assert bridge.estopTimeoutText
        assert threading is not None
