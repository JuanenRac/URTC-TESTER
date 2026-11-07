# =============================================================================
# URTC Tester - tests/test_crash_dump.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The crash record of a HardFault: the read over 0x1BC / 0x1BD against a simulated board, the refusals and the file that is saved."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tester_config  # noqa: E402
import tester_extras as extras  # noqa: E402
from urtc_can import crash_dump  # noqa: E402

RECORD = crash_dump.build(seq=2, pc=0x08002468, lr=0x08001235, xpsr=0x61000000, cfsr=0x8200, hfsr=0x40000000, mmfar=0, bfar=0x40021000,
                          sp=0x20009F00, reset_cause=0x01, kind=crash_dump.KIND_FAULT)


class FakeBoard:
    """Answers 0x1BC with six frames of 0x1BD from a record (or none, like a firmware built without the crash capture)."""

    def __init__(self, record=RECORD, answer=True, frames=6, noise=False):
        self.record, self.answer, self.frames, self.noise = record, answer, frames, noise
        self.sent = []
        self.inbox = []

    def send_frame(self, can_id, data):
        self.sent.append((can_id, bytes(data)))
        if can_id == tester_config.CAN_ID_CRASH_DUMP_QUERY and data[:1] == b"\x00" and self.answer:
            if self.noise:
                self.inbox.append((0x1A9, bytes(8)))
            for i in range(self.frames):
                self.inbox.append((tester_config.CAN_ID_CRASH_DUMP_RESP, self.record[i * 8:i * 8 + 8]))

    def read_frame(self, timeout):
        return self.inbox.pop(0) if self.inbox else None


def test_the_identifiers_are_the_ones_of_the_specification():
    assert tester_config.CAN_ID_CRASH_DUMP_QUERY == 0x1BC and tester_config.CAN_ID_CRASH_DUMP_RESP == 0x1BD


def test_the_record_is_asked_for_and_read_back():
    board = FakeBoard()
    dump = extras.download_crash_dump(board.send_frame, board.read_frame)
    assert board.sent == [(0x1BC, b"\x00")]
    assert dump.crashed and dump.seq == 2 and dump.pc == 0x08002468 and dump.reset_cause_names == ["independent_watchdog"]
    assert dump.cfsr_names == ["precise_data_bus_error", "bfar_valid"] and dump.fault_address == 0x40021000


def test_frames_of_other_identifiers_in_between_are_ignored():
    board = FakeBoard(noise=True)
    assert extras.download_crash_dump(board.send_frame, board.read_frame).seq == 2


def test_a_board_without_the_capture_is_an_error_not_a_guess():
    board = FakeBoard(answer=False)
    with pytest.raises(crash_dump.CrashDumpError, match="missing or incomplete"):
        extras.download_crash_dump(board.send_frame, board.read_frame, timeout_s=0.2)


def test_five_frames_are_not_a_record():
    board = FakeBoard(frames=5)
    with pytest.raises(crash_dump.CrashDumpError, match="missing or incomplete"):
        extras.download_crash_dump(board.send_frame, board.read_frame, timeout_s=0.2)


def test_a_damaged_record_is_refused():
    damaged = bytearray(RECORD)
    damaged[9] ^= 0x10
    board = FakeBoard(record=bytes(damaged))
    with pytest.raises(crash_dump.CrashDumpError, match="checksum"):
        extras.download_crash_dump(board.send_frame, board.read_frame)


def test_the_empty_record_is_a_valid_answer_that_says_no_crash():
    board = FakeBoard(record=crash_dump.build())
    dump = extras.download_crash_dump(board.send_frame, board.read_frame)
    assert not dump.crashed and crash_dump.summary(dump) == "no crash since power-up"


def test_the_record_is_saved_as_json_with_the_causes_in_words(tmp_path):
    dump = crash_dump.parse(RECORD)
    path = extras.save_crash_dump(dump, str(tmp_path), stem="crash")
    assert Path(path) == tmp_path / "crash.json"
    doc = json.loads((tmp_path / "crash.json").read_text(encoding="utf-8"))
    assert doc["format"] == "urtc-crashdump/1" and doc["registers"]["pc"] == "0x08002468" and doc["causes"] == ["precise_data_bus_error", "bfar_valid", "forced"]
    assert doc["captured_at"].endswith("Z")
