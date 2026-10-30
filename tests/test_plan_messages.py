# =============================================================================
# URTC-TESTER - tests/test_plan_messages.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The line a test plan shows for each step is said in the language of the program; reports and the command line keep the English text."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

import tester_config as config
import tester_plan as tp
from tester_simulator import SimulatedBoard

LANGUAGES = ("english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese")
ROOT = Path(__file__).resolve().parents[1]


def _placeholders(text: str) -> set[str]:
    return set(re.findall(r"\{(\w+)\}", text))


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_message_of_a_step_has_a_text_in_every_language(language):
    table = config.load_language(language)
    missing = [key for key in tp.MESSAGES if key not in table]
    assert missing == [], language
    for key, english in tp.MESSAGES.items():
        assert _placeholders(table[key]) == _placeholders(english), (language, key)


def test_the_english_file_says_what_the_engine_says():
    table = config.load_language("english")
    assert {key: table[key] for key in tp.MESSAGES} == tp.MESSAGES


def test_every_message_the_engine_builds_is_in_the_table():
    source = (ROOT / "tester_plan.py").read_text(encoding="utf-8")
    used = set(re.findall(r'"(QT_PM_[A-Z_]+)"', source.split("class Msg", 1)[1]))
    assert used and used <= set(tp.MESSAGES)
    assert set(tp.MESSAGES) - used == set()


def test_a_message_keeps_its_english_text_and_is_translated_with_its_values():
    message = tp.Msg("QT_PM_NO_FRAME", id="0x165", ms=500)
    assert message == "no frame 0x165 within 500 ms"
    seen = []

    def translate(key, **values):
        seen.append((key, values))
        return f"<{key}>"

    assert tp.translate_message(message, translate) == "<QT_PM_NO_FRAME>"
    assert seen == [("QT_PM_NO_FRAME", {"id": "0x165", "ms": 500})]


def test_a_message_inside_a_message_and_a_list_of_messages_are_translated_too(monkeypatch):
    monkeypatch.setattr(config, "_translations", config.load_language("spanish"))
    inner = tp.Msg("QT_PM_LENGTH", have=2, want=8)
    outer = tp.Msg("QT_PM_FRAME_BAD", id="0x165", data="0102", problem=inner)
    assert outer == "0x165 0102: length 2, expected 8"
    assert tp.translate_message(outer, config._) == "0x165 0102: longitud 2, se esperaba 8"
    faults = tp.Msg("QT_PM_REPORTED", faults=[tp.Msg("QT_PM_FAULT_CAN"), tp.Msg("QT_PM_FAULT_WATCHDOG")])
    assert faults == "reported: can_error, the last reset was the watchdog"
    assert tp.translate_message(faults, config._).startswith("informado: error CAN, ")


def test_a_text_that_is_not_a_message_is_left_alone():
    assert tp.translate_message("ValueError: broken", lambda key, **values: "x") == "ValueError: broken"


def test_a_step_of_a_real_run_carries_its_message_and_an_error_is_translated(monkeypatch):
    board = SimulatedBoard(0)
    plan = {"format": 1, "name": "msg", "actuation": True, "steps": [{"do": "expect_tool", "tool": 5}, {"do": "send", "id": "0x120", "data": "01"}]}
    report = tp.run_plan(plan, board)
    assert all(isinstance(step.message, tp.Msg) for step in report.steps)
    assert report.steps[0].message.key == "QT_PM_WRONG_TOOL"
    monkeypatch.setattr(config, "_translations", config.load_language("german"))
    assert tp.translate_message(report.steps[0].message, config._).startswith("die Platine führt Werkzeug")
