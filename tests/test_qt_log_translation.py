# =============================================================================
# URTC Tester - tests/test_qt_log_translation.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The log lines of the Qt Quick deck start with a token; it is shown in the interface language."""
from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tester_config
from tester_config import load_language, translate_log_line

ROOT = Path(__file__).resolve().parent.parent
LANGUAGES = ("english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese")


def test_a_known_token_is_translated_and_its_detail_is_kept(monkeypatch):
    monkeypatch.setattr(tester_config, "_translations", load_language("spanish"))
    assert translate_log_line("PORT_SCAN count=3") == "Búsqueda de puertos: count=3"
    assert translate_log_line("TRANSPORT_DISCONNECTED") == "Desconectado"


def test_a_whole_sentence_label_replaces_the_english_detail(monkeypatch):
    monkeypatch.setattr(tester_config, "_translations", load_language("german"))
    text = translate_log_line("BUS_MONITOR_BLOCKED not connected, or another operation holds the bus")
    assert "not connected" not in text and "blockiert" in text


def test_a_shared_english_sentence_is_translated_too(monkeypatch):
    monkeypatch.setattr(tester_config, "_translations", load_language("spanish"))
    text = translate_log_line("MOTION_BLOCKED steps must be an integer")
    assert "must be" not in text and text.startswith("Comando de movimiento bloqueado")
    assert translate_log_line("MOTION_BLOCKED unknown direction 'x'").endswith("unknown direction 'x'")


def test_an_unknown_line_is_returned_unchanged(monkeypatch):
    monkeypatch.setattr(tester_config, "_translations", load_language("english"))
    assert translate_log_line("Connected to COM3") == "Connected to COM3"
    assert translate_log_line("SOMETHING_NEW detail") == "SOMETHING_NEW detail"
    assert translate_log_line("2.0 s • 4 frame(s) • 1 CAN ID(s) • 0.5% bus load") == "2.0 s • 4 frame(s) • 1 CAN ID(s) • 0.5% bus load"
    assert translate_log_line("") == ""


def _logged_tokens() -> set[str]:
    """Every token the deck logs, found again in the source so that a new one cannot be forgotten."""
    source = (ROOT / "qt_tester.py").read_text(encoding="utf-8")
    tokens = set(re.findall(r"""(?:_log|emit)\([^"'\n]*f?["']([A-Z][A-Z0-9_]+)""", source))
    tokens |= set(re.findall(r"""(?:_log|emit)\(\s*f?["']([A-Z][A-Z0-9_]+)""", source))
    # self._log(f"{action}_BLOCKED ...") in _require_profile: one token per action that asks for it
    tokens |= {action + "_BLOCKED" for action in re.findall(r"""_require_profile\([^"\n]*"([A-Z][A-Z_]+)\"""", source)}
    return {t for t in tokens if not t.endswith("_")}


def test_every_token_the_deck_logs_has_a_label_in_every_language():
    tokens = _logged_tokens()
    assert {"PORT_SCAN", "SELFTEST_FAILED", "MOTION_SENT", "THERMAL_CAPTURE_FAILED", "PRINTER_BLOCKED", "WATCHDOG_STARTED"} <= tokens
    assert len(tokens) >= 119
    for language in LANGUAGES:
        table = load_language(language)
        assert [t for t in sorted(tokens) if "QTLOG_" + t not in table] == [], language
        assert [k for k in tester_config._LOG_DETAILS.values() if k not in table] == [], language


def test_the_other_modules_do_not_log_tokens_the_table_misses():
    # tester_selftest, tester_bus_monitor, tester_transports ... log translated sentences, not tokens
    for name in ("tester_selftest.py", "tester_bus_monitor.py", "tester_autodetect.py", "tester_telemetry.py", "tester_transports.py"):
        source = (ROOT / name).read_text(encoding="utf-8")
        assert not re.findall(r"""\blog\(\s*f?["'][A-Z][A-Z0-9_]+[ "']""", source), name


def test_the_session_export_keeps_the_english_original_lines(monkeypatch):
    qt_tester = pytest.importorskip("qt_tester")
    monkeypatch.setattr(tester_config, "_translations", load_language("spanish"))
    monkeypatch.setattr(qt_tester, "translate_log_line", translate_log_line)
    with tempfile.TemporaryDirectory() as folder:
        monkeypatch.setattr(qt_tester, "LOGS_FOLDER", folder)
        bridge = qt_tester.TesterQtBridge()
        bridge._logs[:] = []
        bridge._append_log("PORT_SCAN count=3")
        assert bridge.logs[-1] == "Búsqueda de puertos: count=3"  # the deck shows the interface language
        saved = bridge.saveLogText(str(Path(folder) / "plain.txt"))
        assert saved
        assert "PORT_SCAN count=3" in (Path(folder) / "plain.txt").read_text(encoding="utf-8")
        path = bridge.exportSession()
        with zipfile.ZipFile(path) as bundle:
            text = bundle.read("session_log.txt").decode("utf-8")
            manifest = json.loads(bundle.read("session_manifest.json"))
    assert "PORT_SCAN count=3" in text and "Búsqueda" not in text
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() in json.dumps(manifest)
