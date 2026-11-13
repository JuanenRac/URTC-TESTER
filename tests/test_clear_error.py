# =============================================================================
# URTC Tester - tests/test_clear_error.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The button that lifts a latched error of the head and the three switches next to the other optional functions.

The frame, the reading of the answer and the settings are tested without Qt; the head is the virtual board of URTC-COMMON, which answers with the same
decisions as the firmware (the switch off by default). Nothing here has run against a real board.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import tester_config as config  # noqa: E402
import tester_extras as extras  # noqa: E402
from urtc_can import protocol  # noqa: E402
from urtc_can.virtual_board import VirtualBoard  # noqa: E402

LANGUAGES = ("english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese")
NEW_KEYS = ("BTN_CLEAR_ERROR", "LBL_CLEAR_ERROR_RESULT", "LBL_ERROR_REASON", "LBL_FEATURE_CLEAR_ERROR", "LBL_FEATURE_COMMS_WATCHDOG", "LBL_FEATURE_MAGNET_RELEASE",
            *(f"LBL_CLEAR_RESULT_{n}" for n in ("CLEARED", "SWITCH_OFF", "NO_ERROR", "NOT_CLEARABLE", "HOT", "ACTUATOR_ON")),
            *(f"LBL_ERROR_REASON_{n}" for n in ("UNKNOWN", "THERMAL", "SENSOR", "TOOL_ID", "COMMS_WATCHDOG", "FAN_STALL", "STEPPER_SILENCE", "MAGNET_RELEASE")))


# ---- the frame, the answer and the switches ---------------------------------------------------------------------------------------
def test_the_command_is_the_identifier_with_its_magic_payload():
    assert extras.clear_error_frame() == (0x1B2, b"CLER")


def test_the_three_switches_are_named_and_reach_the_seventh_bit():
    assert extras.FEATURES_SUPPORTED == 0x7F
    assert extras.features_text(0x70) == "CLEAR_ERROR, COMMS_WATCHDOG, MAGNET_RELEASE"
    assert extras.features_frame(0x7F) == (0x1AE, b"FEAT\x7f")
    for bad in (-1, 0x80):
        with pytest.raises(ValueError):
            extras.features_frame(bad)


def test_a_head_that_does_not_send_the_last_byte_gives_no_result():
    assert extras.decode_clear_error(bytes([0, 0, 0, 0, 0, 8])) is None
    assert extras.decode_clear_error(b"\x00\x00") is None


def test_every_outcome_and_reason_has_a_language_key():
    assert set(extras.CLEAR_RESULT_KEYS) == set(range(1, 7))
    assert set(extras.ERROR_REASON_KEYS) == set(range(1, 9))


def test_the_new_texts_exist_in_the_eight_languages():
    for name in LANGUAGES:
        found = {line.split("=", 1)[0] for line in (ROOT / "language" / f"{name}.lng").read_text(encoding="utf-8").splitlines() if "=" in line}
        assert set(NEW_KEYS) <= found, (name, sorted(set(NEW_KEYS) - found))


# ---- the settings -----------------------------------------------------------------------------------------------------------------
def test_without_a_setting_the_button_asks_first():
    assert config.clear_error_settings({}) == {"confirm": True}
    assert config.clear_error_settings({"clear_error": "oops"}) == {"confirm": True}


@pytest.mark.parametrize("value, expected", [(False, False), (True, True), (0, True), ("false", True), (None, True)])
def test_only_an_explicit_false_stops_the_question(value, expected):
    assert config.clear_error_settings({"clear_error": {"confirm": value}})["confirm"] is expected


# ---- with the head: the virtual board answers with the decisions of the firmware ------------------------------------------------------
def ask(board: VirtualBoard) -> dict:
    ((identifier, data),) = board.handle(*extras.clear_error_frame())
    assert identifier == extras.CAN_ID_ACTIVE_TOOL_RESP
    result = extras.decode_clear_error(data)
    assert result is not None
    return result


def test_a_head_with_the_switch_off_keeps_its_error_and_says_so():
    board = VirtualBoard(system_error=True, error_reason=protocol.ERROR_REASON_COMMS_WATCHDOG)
    result = ask(board)
    assert result["clear_result_name"] == "REFUSED_SWITCH_OFF" and result["system_error"] is True and result["error_reason_name"] == "COMMS_WATCHDOG"


def test_a_cool_quiet_head_with_the_switch_on_lifts_the_error():
    board = VirtualBoard(system_error=True, error_reason=protocol.ERROR_REASON_STEPPER_SILENCE, features=protocol.FEATURE_CLEAR_ERROR)
    result = ask(board)
    assert result["clear_result_name"] == "CLEARED" and result["system_error"] is False and result["error_reason_name"] is None


@pytest.mark.parametrize("kwargs, outcome", [
    ({"temperature_c": 50}, "REFUSED_HOT"),
    ({"temperature_c": 0xFFFF}, "REFUSED_HOT"),
    ({"actuators_off": False}, "REFUSED_ACTUATOR_ON"),
    ({"error_reason": protocol.ERROR_REASON_TOOL_ID}, "REFUSED_NOT_CLEARABLE"),
])
def test_a_head_that_is_hot_busy_or_without_a_tool_refuses(kwargs, outcome):
    board = VirtualBoard(system_error=True, features=protocol.FEATURE_CLEAR_ERROR, **{"error_reason": protocol.ERROR_REASON_THERMAL, **kwargs})
    result = ask(board)
    assert result["clear_result_name"] == outcome and result["system_error"] is True


def test_a_head_with_no_error_has_nothing_to_lift():
    assert ask(VirtualBoard(features=protocol.FEATURE_CLEAR_ERROR))["clear_result_name"] == "REFUSED_NO_ERROR"


def test_any_other_payload_is_ignored_by_the_head():
    board = VirtualBoard(system_error=True, features=protocol.FEATURE_CLEAR_ERROR)
    assert board.handle(0x1B2, b"CLES") == [] and board.handle(0x1B2, b"") == [] and board.handle(0x1B2, b"CLER\x00") == []
    assert board.system_error is True


# ---- the deck ---------------------------------------------------------------------------------------------------------------------
def make_bridge(monkeypatch):
    pytest.importorskip("PySide6")
    import qt_tester  # noqa: PLC0415
    monkeypatch.setattr(qt_tester, "save_config", lambda updates: True)
    bridge = qt_tester.TesterQtBridge()
    bridge._log = lambda text: None
    return bridge


def test_the_deck_writes_what_the_head_answered(monkeypatch):
    bridge = make_bridge(monkeypatch)
    bridge._on_query_result("clear_error", {"system_error": True, "error_reason": 7, "error_reason_name": "STEPPER_SILENCE", "clear_result": 5, "clear_result_name": "REFUSED_HOT"})
    assert "50" in bridge.clearErrorText and bridge.clearErrorText.count("\n") == 1
    bridge._on_query_result("clear_error", {"system_error": False, "error_reason": 0, "error_reason_name": None, "clear_result": 1, "clear_result_name": "CLEARED"})
    assert "\n" not in bridge.clearErrorText
    bridge._on_query_result("clear_error", None)
    assert bridge.clearErrorText != ""


def test_the_button_does_nothing_without_a_connection_and_asks_by_default(monkeypatch):
    bridge = make_bridge(monkeypatch)
    bridge.clearError()      # not connected: nothing is sent and nothing breaks
    assert bridge.clearErrorNeedsConfirmation is True
