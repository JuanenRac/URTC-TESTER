# =============================================================================
# URTC Tester - tests/test_language_selector.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The window offers the eight languages, saves the choice and says it applies on the next start."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

pytest.importorskip("PySide6")
import tester_config  # noqa: E402
import qt_tester  # noqa: E402


def test_the_eight_languages_are_offered_each_in_its_own_name():
    bridge = qt_tester.TesterQtBridge()
    assert len(bridge.languageNames) == 8
    assert "Português" in bridge.languageNames and "日本語" in bridge.languageNames


def test_choosing_another_language_saves_it_and_returns_the_restart_notice(monkeypatch):
    saved = []
    monkeypatch.setattr(qt_tester, "save_config", lambda updates: saved.append(updates) or True)
    bridge = qt_tester.TesterQtBridge()
    other = next(index for index, (code, _name) in enumerate(tester_config.AVAILABLE_LANGUAGES) if code != qt_tester._current_language)
    assert bridge.selectLanguage(other)
    assert saved == [{"language": tester_config.AVAILABLE_LANGUAGES[other][0]}]


def test_the_current_language_and_an_invalid_index_save_nothing(monkeypatch):
    saved = []
    monkeypatch.setattr(qt_tester, "save_config", lambda updates: saved.append(updates) or True)
    bridge = qt_tester.TesterQtBridge()
    assert bridge.selectLanguage(bridge.languageIndex) == ""
    assert bridge.selectLanguage(99) == "" and bridge.selectLanguage(-1) == ""
    assert saved == []


def test_the_list_the_selector_the_bitrate_and_the_badge_come_from_the_shared_interface_package():
    import tester_config
    import urtc_ui

    assert tester_config.AVAILABLE_LANGUAGES == list(urtc_ui.LANGUAGES)
    bridge = qt_tester.TesterQtBridge()
    assert bridge.languageNames == urtc_ui.LanguageModel().names()
    assert bridge.statusColor == urtc_ui.connection_badge(None, True).colour
    bridge._transport = object()
    assert bridge.statusColor == urtc_ui.connection_badge(True, bridge._listen_only).colour
    assert tester_config.bitrate_bps_for_label("1 Mbit/s") == 1_000_000
    assert tester_config.bitrate_bps_for_label("125 kbit/s") == 125_000
    assert tester_config.bitrate_bps_for_label("nonsense") == 500_000
