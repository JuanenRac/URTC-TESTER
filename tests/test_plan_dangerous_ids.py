# =============================================================================
# URTC-TESTER - tests/test_plan_dangerous_ids.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A plan that sends an identifier which changes what the board is (the bootloader, an update, an erase, a setting that is kept): sent, asked about or refused,
as the setting plan_dangerous_ids says. Against the simulated head; no bus."""
from __future__ import annotations

import pytest

import tester_config
import tester_plan as tp
from tester_simulator import SimulatedBoard


class TickClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        self.now += 0.001
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def run(plan, **options):
    clock = TickClock()
    board = SimulatedBoard(0, clock=clock)
    return tp.run_plan(plan, board, clock=clock, sleep=clock.sleep, **options), board


def plan_sending(identifier: str, data: str = "0000"):
    return {"format": 1, "name": "t", "actuation": True, "steps": [{"do": "send", "id": identifier, "data": data}]}


def test_the_default_is_to_send_as_plans_always_did():
    assert tester_config.PLAN_DANGEROUS_IDS in ("allow", "confirm", "refuse")
    assert tp.PLAN_DANGEROUS_IDS == tester_config.PLAN_DANGEROUS_IDS


def test_the_list_of_forbidden_identifiers_leaves_only_a_few_dangerous_ones_to_this_setting():
    from urtc_can import dangerous_ids
    from urtc_can import protocol as wire

    host_sent = {i for i, info in wire.MESSAGES.items() if info["direction"] in ("host_to_board", "both")}
    left = {i for i in host_sent if dangerous_ids.dangerous_reason(i, wire.MESSAGES) and i not in tp.FORBIDDEN_IDS}
    assert left == {0x1B2, 0x1B9, 0x7EA, 0x7EC, 0x7EE}


def test_allow_sends_a_dangerous_identifier_without_asking(monkeypatch):
    monkeypatch.setattr(tp, "PLAN_DANGEROUS_IDS", "allow")
    asked: list[str] = []
    report, board = run(plan_sending("0x1B9", "A5A5"), allow_actuation=True, confirm=lambda text: asked.append(text) or True)
    assert report.steps[0].outcome == tp.PASS and asked == []
    assert any(frame[0] == 0x1B9 for frame in board.sent)


def test_refuse_never_sends_it_and_names_the_setting(monkeypatch):
    monkeypatch.setattr(tp, "PLAN_DANGEROUS_IDS", "refuse")
    report, board = run(plan_sending("0x1B9", "A5A5"), allow_actuation=True, confirm=lambda text: True)
    assert report.steps[0].outcome == tp.ERROR
    assert "plan_dangerous_ids" in report.steps[0].message and "0x1B9" in report.steps[0].message
    assert not any(frame[0] == 0x1B9 for frame in board.sent)


def test_confirm_asks_the_operator_and_sends_only_when_the_answer_is_yes(monkeypatch):
    monkeypatch.setattr(tp, "PLAN_DANGEROUS_IDS", "confirm")
    asked: list[str] = []
    report, board = run(plan_sending("0x1B2", "A5A5"), allow_actuation=True, confirm=lambda text: asked.append(text) or True)
    assert report.steps[0].outcome == tp.PASS and len(asked) == 1 and "0x1B2" in asked[0]
    assert any(frame[0] == 0x1B2 for frame in board.sent)
    report, board = run(plan_sending("0x1B2", "A5A5"), allow_actuation=True, confirm=lambda text: False)
    assert report.steps[0].outcome == tp.ERROR and "did not confirm" in report.steps[0].message
    assert not any(frame[0] == 0x1B2 for frame in board.sent)


def test_confirm_with_nobody_to_ask_ends_the_step_and_sends_nothing(monkeypatch):
    monkeypatch.setattr(tp, "PLAN_DANGEROUS_IDS", "confirm")
    report, board = run(plan_sending("0x1B9", "A5A5"), allow_actuation=True)
    assert report.steps[0].outcome == tp.ERROR and "person" in report.steps[0].message
    assert not any(frame[0] == 0x1B9 for frame in board.sent)


@pytest.mark.parametrize("policy", ["confirm", "refuse"])
def test_an_identifier_that_is_not_dangerous_is_sent_in_every_mode(monkeypatch, policy):
    monkeypatch.setattr(tp, "PLAN_DANGEROUS_IDS", policy)
    asked: list[str] = []
    report, board = run(plan_sending("0x130", "00A0"), allow_actuation=True, confirm=lambda text: asked.append(text) or True)
    assert report.steps[0].outcome == tp.PASS and asked == []
    assert (0x130, bytes.fromhex("00A0")) in board.sent


def test_the_actuation_switch_still_comes_first(monkeypatch):
    monkeypatch.setattr(tp, "PLAN_DANGEROUS_IDS", "confirm")
    asked: list[str] = []
    report, _board = run(plan_sending("0x1B9", "A5A5"), allow_actuation=False, confirm=lambda text: asked.append(text) or True)
    assert report.steps[0].outcome == tp.ERROR and "allow actuation" in report.steps[0].message and asked == []


def test_the_two_texts_exist_in_every_language():
    import tester_config as config

    for code in ("english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese"):
        words = config.load_language(code)
        assert "{id}" in words["QT_PM_DANGEROUS_REFUSED"] and "{id}" in words["QT_PM_DANGEROUS_ASK"], code
