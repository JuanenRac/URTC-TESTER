# =============================================================================
# URTC Tester - tests/test_features_second_byte.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The second byte of the switch map of the optional functions: the frames, the answers of both forms and the box of the deck."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import tester_extras as extras  # noqa: E402

LANGUAGES = ("english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese")


def test_the_query_asks_for_the_six_byte_answer():
    assert extras.FEATURES_QUERY_EXTENDED == b"\x02"


def test_the_five_byte_form_is_unchanged_and_the_six_byte_form_carries_the_second_byte():
    assert extras.features_frame(0x20) == (0x1AE, b"FEAT\x20")
    assert extras.features_frame(0x20, 1) == (0x1AE, b"FEAT\x20\x01")
    assert extras.features_frame(0x00, 0) == (0x1AE, b"FEAT\x00\x00")


def test_the_host_only_switch_stays_off_unless_the_communication_watchdog_is_on():
    assert extras.features_frame(0x00, 1)[1][5] == 0
    assert extras.features_frame(0x10, 1)[1][5] == 0
    assert extras.features_frame(0x20, 1)[1][5] == 1


@pytest.mark.parametrize("bad", [-1, 4, 255, 256])
def test_a_switch_of_the_second_byte_that_the_firmware_does_not_have_is_refused(bad):
    with pytest.raises(ValueError):
        extras.features_frame(0x20, bad)


def test_both_forms_of_the_answer_are_read():
    assert extras.decode_features(bytes([0x0A, 0x02, 0xFF])) == {"stored": 0x0A, "running": 2, "supported": 0xFF, "stored_ext": 0, "running_ext": 0, "supported_ext": 0}
    assert extras.decode_features(bytes([0x20, 0, 0xFF, 1, 0, 1])) == {"stored": 0x20, "running": 0, "supported": 0xFF, "stored_ext": 1, "running_ext": 0, "supported_ext": 1}
    for length in (0, 1, 2, 4, 5, 7):
        assert extras.decode_features(bytes(length)) is None


def test_the_name_of_the_switch_is_listed_with_the_others():
    assert extras.features_text(0x20, 1) == "COMMS_WATCHDOG, WATCHDOG_HOST_ONLY"
    assert extras.features_text(0x20, 3) == "COMMS_WATCHDOG, WATCHDOG_HOST_ONLY, ALLOW_UPDATE_ACTIVE_ACTUATOR"
    assert extras.features_text(0, 2) == "ALLOW_UPDATE_ACTIVE_ACTUATOR"
    assert extras.features_text(0, 0) == "none"
    assert extras.features_text(0x20) == "COMMS_WATCHDOG"


def test_the_deck_box_starts_unticked_is_shown_only_for_a_head_that_has_it_and_needs_the_watchdog():
    deck = (ROOT / "assets" / "qml" / "TesterDeck.qml").read_text(encoding="utf-8")
    box = next(line for line in deck.splitlines() if "id: featHostOnly" in line)
    assert "LBL_FEATURE_WATCHDOG_HOST_ONLY" in box and "checked: false" in box
    assert "featComms.checked" in box and "featuresSupportedExt" in box and "visible:" in box
    assert "(featHostOnly.checked && featComms.checked ? 1 : 0)" in deck
    assert "testerBackend.writeFeaturesExt(" in deck


def test_the_text_of_the_switch_exists_in_the_eight_languages():
    for name in LANGUAGES:
        found = {line.split("=", 1)[0] for line in (ROOT / "language" / f"{name}.lng").read_text(encoding="utf-8").splitlines() if "=" in line}
        assert "LBL_FEATURE_WATCHDOG_HOST_ONLY" in found, name


def test_the_switch_for_the_end_of_a_slave_update_is_the_second_bit_and_does_not_need_the_watchdog():
    assert extras.FEATURE_EXT_ALLOW_UPDATE_ACTIVE_ACTUATOR == 0x02
    assert extras.features_frame(0x00, 2)[1][5] == 2
    assert extras.features_frame(0x00, 3)[1][5] == 2
    assert extras.features_frame(0x20, 3)[1][5] == 3
    assert extras.features_frame(0x00, 0)[1][5] == 0


def test_the_switch_for_the_end_of_a_slave_update_is_off_unless_asked_for():
    assert extras.features_frame(0x20, 1)[1][5] & 2 == 0


def test_the_deck_box_of_the_slave_update_switch_starts_unticked_and_is_shown_only_for_a_head_that_has_it():
    deck = (ROOT / "assets" / "qml" / "TesterDeck.qml").read_text(encoding="utf-8")
    box = next(line for line in deck.splitlines() if "id: featAllowUpdate" in line)
    assert "LBL_FEATURE_ALLOW_UPDATE_ACTIVE_ACTUATOR" in box and "checked: false" in box
    assert "featuresSupportedExt & 2" in box and "visible:" in box
    assert "(featAllowUpdate.checked ? 2 : 0)" in deck


def test_turning_the_slave_update_switch_on_is_written_to_the_log_and_the_text_exists_in_the_eight_languages():
    source = (ROOT / "qt_tester.py").read_text(encoding="utf-8")
    assert 'self._log("FEATURES_UPDATE_ACTIVE_ON")' in source
    for name in LANGUAGES:
        found = {line.split("=", 1)[0] for line in (ROOT / "language" / f"{name}.lng").read_text(encoding="utf-8").splitlines() if "=" in line}
        assert "LBL_FEATURE_ALLOW_UPDATE_ACTIVE_ACTUATOR" in found, name
        assert "QTLOG_FEATURES_UPDATE_ACTIVE_ON" in found, name
