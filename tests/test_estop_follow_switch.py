# =============================================================================
# URTC Tester - tests/test_estop_follow_switch.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The switch of the optional function that makes a tool head follow the emergency stop of the stack.

It is a safety option, so it starts off: the check box is not ticked, the head answers with the bit clear until the bit is written, and the texts that
name it exist in the eight languages. The head is the virtual board of URTC-COMMON; nothing here has run against a real board.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import tester_extras as extras  # noqa: E402
from urtc_can import protocol  # noqa: E402
from urtc_can.virtual_board import VirtualBoard  # noqa: E402

LANGUAGES = ("english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese")
ESTOP_BIT = 0x80


def test_the_bit_is_the_one_of_the_protocol_and_has_its_name():
    assert protocol.FEATURE_ESTOP_FOLLOW == ESTOP_BIT
    assert (ESTOP_BIT, "ESTOP_FOLLOW") in extras.FEATURE_NAMES
    assert extras.features_text(ESTOP_BIT) == "ESTOP_FOLLOW"
    assert extras.features_text(0x01 | ESTOP_BIT) == "MOTION_RAMPS, ESTOP_FOLLOW"
    assert extras.features_frame(ESTOP_BIT) == (0x1AE, b"FEAT\x80")


def test_the_deck_check_box_starts_unticked_and_writes_the_eighth_bit():
    deck = (ROOT / "assets" / "qml" / "TesterDeck.qml").read_text(encoding="utf-8")
    box = next(line for line in deck.splitlines() if "id: featEstop" in line)
    assert "LBL_FEATURE_ESTOP_FOLLOW" in box and "checked: false" in box
    assert "(featEstop.checked ? 128 : 0)" in deck


def test_the_two_new_error_reasons_have_a_name_and_a_text_key():
    assert extras.ERROR_REASON_KEYS[9] == "LBL_ERROR_REASON_ESTOP"
    assert extras.ERROR_REASON_KEYS[10] == "LBL_ERROR_REASON_ESTOP_SILENCE"
    for name in LANGUAGES:
        found = {line.split("=", 1)[0] for line in (ROOT / "language" / f"{name}.lng").read_text(encoding="utf-8").splitlines() if "=" in line}
        assert {"LBL_FEATURE_ESTOP_FOLLOW", "LBL_ERROR_REASON_ESTOP", "LBL_ERROR_REASON_ESTOP_SILENCE"} <= found, name


def test_the_virtual_head_ignores_the_stop_frame_until_the_switch_is_on():
    off = VirtualBoard()
    assert off.estop is None and not off.system_error
    on = VirtualBoard(features=ESTOP_BIT)
    assert on.estop is not None and on.system_error
    assert on.error_reason == protocol.ERROR_REASON_ESTOP
