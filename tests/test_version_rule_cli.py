# =============================================================================
# URTC-TESTER - tests/test_version_rule_cli.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""``version-rule``: the query, a signed command from a file, a head without the feature, and the vectors of the shared command."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import tester_cli
import tester_version_rule as vr
from urtc_can import ed25519
from urtc_can import version_compat as vc

VECTORS = json.loads((Path(__file__).parent / "fixtures" / "version_compat_vectors.json").read_text(encoding="utf-8"))
SEED = os.urandom(32)                   # an ephemeral key, no key of the workshop
UID, SERIAL = (1, 2, 3), 0x11223344


class Head:
    """A main bootloader with (or without) the stored version rule, decided by the shared reference."""

    def __init__(self, feature: bool = True) -> None:
        self.feature, self.mode, self.counter = feature, vc.MODE_NONE, 0
        self.parts: dict[int, bytes] = {}
        self.queue: list[tuple[int, bytes]] = []
        self.sent: list[tuple[int, bytes]] = []

    def open_channel(self, *a, **k):
        return None

    def close_channel(self):
        return None

    def close(self):
        return None

    def _answer(self, status: int) -> None:
        self.queue.append((vc.ID_RESULT, vc.answer_frame(status, vc.effective_mode(self.mode), self.mode != vc.MODE_NONE, self.counter)))

    def send_frame(self, can_id, data):
        self.sent.append((can_id, bytes(data)))
        if not self.feature or can_id != vc.ID_COMMAND:
            return
        if data[0] == vc.QUERY_INDEX:
            self._answer(vc.OK)
            return
        self.parts[data[0] - vc.CHUNK_BASE] = bytes(data[1:])
        if len(self.parts) < vc.CHUNKS:
            return
        command = b"".join(self.parts[i] for i in range(vc.CHUNKS))
        self.parts = {}
        status, mode, counter = vc.decide(command, UID, SERIAL, [ed25519.public_key(SEED)], self.counter)
        if status == vc.NOT_FOR_ME:
            return
        if status == vc.OK:
            self.mode, self.counter = mode, counter
        self._answer(status)

    def read_frame(self, timeout=0.0):
        return self.queue.pop(0) if self.queue else None


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        self.now += 0.5
        return self.now


def test_a_query_changes_nothing_and_reports_the_rule():
    head = Head()
    answer = vr.query(head)
    assert vr.describe(answer) == {"status": "ok", "mode": "strict", "stored": False, "counter": 0}
    assert head.sent == [(vc.ID_COMMAND, vc.query_frame())] and "nothing stored" in vr.text(answer)


def test_a_signed_command_is_sent_in_twelve_frames_and_a_repeat_is_refused(tmp_path):
    head = Head()
    file = tmp_path / "accept.bin"
    file.write_bytes(vc.make_command(SEED, UID, SERIAL, vc.MODE_ACCEPT_PATCHLESS, 1))
    answer = vr.send(head, vr.read_command(file))
    assert vr.describe(answer) == {"status": "ok", "mode": "accept_patchless", "stored": True, "counter": 1}
    assert [f[1][0] for f in head.sent] == list(range(0x40, 0x4C))
    assert vr.describe(vr.send(head, vr.read_command(file)))["status"] == "replay"
    bad = file.read_bytes()[:-1] + bytes([file.read_bytes()[-1] ^ 1])
    assert vr.describe(vr.send(head, bad))["status"] == "bad_signature" and head.counter == 1


def test_a_head_without_the_feature_answers_nothing():
    assert vr.query(Head(feature=False), clock=Clock()) is None


def test_frames_that_are_not_this_answer_are_ignored():
    head = Head()
    head.queue = [(vc.ID_RESULT, bytes([0, 0, 0, 0, 1])), (0x7F9, bytes(8))]    # the answer of the serial command and another frame
    assert vr.describe(vr.query(head))["status"] == "ok"


def test_a_file_of_another_size_is_refused(tmp_path):
    file = tmp_path / "x.bin"
    file.write_bytes(bytes(83))
    with pytest.raises(ValueError):
        vr.read_command(file)


@pytest.mark.parametrize("feature, expected", [(True, tester_cli.EXIT_PASS), (False, tester_cli.EXIT_UNKNOWN)])
def test_the_command_line(monkeypatch, capsys, feature, expected):
    monkeypatch.setattr(tester_cli, "_open_transport", lambda args, virtual=None: Head(feature))
    monkeypatch.setattr(vr, "ANSWER_TIMEOUT_S", 0.2)
    assert tester_cli.main(["version-rule", "--transport", "serial", "--port", "x", "--json"]) == expected
    out = capsys.readouterr().out
    assert ('"strict"' in out) if feature else ("No answer" in out)


def test_the_command_line_refuses_a_bad_file_before_it_opens_a_bus(monkeypatch, tmp_path):
    monkeypatch.setattr(tester_cli, "_open_transport", lambda *a, **k: pytest.fail("no bus for a bad file"))
    assert tester_cli.main(["version-rule", str(tmp_path / "missing.bin")]) == tester_cli.EXIT_USAGE


def test_the_reference_the_tester_carries_reproduces_the_shared_vectors():
    keys = [bytes.fromhex(k) for k in VECTORS["public_keys"]]
    for case in VECTORS["commands"]:
        uid = tuple(int(w, 16) for w in case["uid"])
        got = vc.decide(bytes.fromhex(case["command"]), uid, int(case["current_serial"], 16), [keys[i] for i in case["trusted"]], case["stored_counter"],
                        case["enabled"], case["busy"])
        assert got == (case["status"], case["mode"], case["counter"]), case["name"]
