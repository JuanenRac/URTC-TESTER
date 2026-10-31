# =============================================================================
# URTC-TESTER - tests/test_evidence_trust_cli.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The trust store of public keys in the tester (alias -> key in config.json), the switch to sign the evidence in its Qt interface and the signature column
of its history window."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import tester_cli
import tester_config
from urtc_can import evidence, record_signing

ROOT = Path(__file__).resolve().parents[1]
SEED = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
OTHER = bytes.fromhex("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb")
PUB, OTHER_PUB = record_signing.public_key(SEED), record_signing.public_key(OTHER)


def cli(capsys, *args):
    code = tester_cli.main([str(a) for a in args])
    captured = capsys.readouterr()
    return code, captured.out + captured.err


def record(detail: str) -> dict:
    return evidence.build(kind="test", outcome="pass", timestamp_utc="2026-01-02T10:00:00Z", tool="URTC-TESTER", tool_version="0.4.6", subject={"name": "head-1"}, detail=detail)


@pytest.fixture
def folder(tmp_path):
    base = tmp_path / "evidence"
    base.mkdir()
    files = {"a": record_signing.sign_evidence(record("a"), SEED), "b": record_signing.sign_evidence(record("b"), OTHER), "c": record("c")}
    for name, item in files.items():
        (base / f"{name}.json").write_text(json.dumps(item), encoding="utf-8")
    return base


def with_config(monkeypatch, config):
    monkeypatch.setattr(tester_config, "load_config", lambda: config)


# -- the store in the configuration ------------------------------------------------------------------------------------------------------
def test_the_store_comes_from_the_configuration_and_names_what_it_leaves_out(monkeypatch):
    with_config(monkeypatch, {"trusted_keys": {"Ana": PUB.hex(), "Bad": "zz"}})
    store, problems = tester_config.trusted_keys_store()
    assert store == {"Ana": PUB} and len(problems) == 1 and "Bad" in problems[0] and "zz" not in problems[0]
    with_config(monkeypatch, {})
    assert tester_config.trusted_keys_store() == ({}, [])


# -- characterization: without a store the history and the report say what they said -------------------------------------------------------
def test_without_a_store_the_history_is_as_it_was(folder, capsys, monkeypatch):
    with_config(monkeypatch, {})
    code, out = cli(capsys, "history", folder)
    assert code == 0 and "trust store" not in out and "WARNING" not in out


# -- the matrix ----------------------------------------------------------------------------------------------------------------------------
def test_the_history_counts_trusted_unknown_and_unsigned(folder, capsys, monkeypatch):
    with_config(monkeypatch, {"trusted_keys": {"Ana": PUB.hex()}})
    code, out = cli(capsys, "history", folder)
    assert code == 0                                                   # an unknown key is shown, it does not fail the status
    assert "1 signed by a trusted key (Ana), 1 by an unknown key, 0 not valid, 1 unsigned" in out


def test_a_signature_that_fails_is_a_failure_with_the_store_too(folder, capsys, monkeypatch):
    with_config(monkeypatch, {"trusted_keys": {"Ana": PUB.hex()}})
    forged = json.loads((folder / "a.json").read_text(encoding="utf-8"))
    forged["detail"] = "changed"
    forged["evidence_sha256"] = evidence.digest(forged)
    (folder / "a.json").write_text(json.dumps(forged), encoding="utf-8")
    code, out = cli(capsys, "history", folder)
    assert code == 1 and "1 not valid" in out


def test_the_public_key_given_wins_over_the_store(folder, capsys, monkeypatch):
    with_config(monkeypatch, {"trusted_keys": {"Ana": PUB.hex(), "Bea": OTHER_PUB.hex()}})
    code, out = cli(capsys, "history", folder, "--public-key", PUB.hex())
    assert code == 1 and "trust store" not in out and "1 by another key" in out        # b is by another key than the one given, whatever the store trusts
    code, out = cli(capsys, "history", folder)
    assert code == 0 and "2 signed by a trusted key (Ana, Bea)" in out


def test_the_report_names_the_alias_the_unknown_key_and_the_public_key_wins(folder, tmp_path, capsys, monkeypatch):
    with_config(monkeypatch, {"trusted_keys": {"Ana": PUB.hex()}})
    code, _ = cli(capsys, "report", "--evidence-dir", folder, "--out", tmp_path / "r.html")
    page = (tmp_path / "r.html").read_text(encoding="utf-8")
    assert code == 0 and "Signed by Ana" in page and "Valid signature, unknown key" in page
    code, _ = cli(capsys, "report", "--evidence-dir", folder, "--out", tmp_path / "p.html", "--public-key", PUB.hex())
    page = (tmp_path / "p.html").read_text(encoding="utf-8")
    assert code == 1 and "Signed by Ana" not in page and "Signed by another key" in page


@pytest.mark.parametrize("language", ["english", "spanish", "italian", "french", "german", "chinese", "japanese", "portuguese"])
def test_the_report_with_a_store_is_written_in_every_language_and_format(folder, tmp_path, capsys, monkeypatch, language):
    with_config(monkeypatch, {"trusted_keys": {"Ana": PUB.hex()}})
    for fmt in ("html", "pdf"):
        code, _ = cli(capsys, "report", "--evidence-dir", folder, "--out", tmp_path / f"r_{language}.{fmt}", "--format", fmt, "--language", language)
        assert code == 0
    assert (tmp_path / f"r_{language}.pdf").read_bytes().startswith(b"%PDF")


def test_a_bad_entry_of_the_store_is_a_warning_and_not_trusted(folder, capsys, monkeypatch):
    with_config(monkeypatch, {"trusted_keys": {"Ana": "not a key"}})
    code, out = cli(capsys, "history", folder)
    assert code == 0 and "WARNING" in out and "not a key" not in out and "trusted key" not in out


# -- the switch in the Qt interface ----------------------------------------------------------------------------------------------------------
def test_the_text_of_the_switch_exists_in_the_eight_languages():
    for name in ("english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese"):
        lines = (ROOT / "language" / f"{name}.lng").read_text(encoding="utf-8").splitlines()
        assert any(line.startswith("LBL_SIGN_EVIDENCE=") and len(line) > 25 for line in lines), name


def test_the_switch_is_off_by_default_and_saves_the_setting(monkeypatch):
    pytest.importorskip("PySide6")
    import qt_tester  # noqa: PLC0415

    saved = {}
    monkeypatch.setattr(qt_tester, "save_config", lambda updates: saved.update(updates) or True)
    with_config(monkeypatch, {})
    bridge = qt_tester.TesterQtBridge()
    bridge._log = lambda text: None
    assert bridge.signEvidence is False
    bridge.setSignEvidence(True)
    assert saved == {"sign_evidence": True}
    with_config(monkeypatch, {"sign_evidence": True})
    assert bridge.signEvidence is True
    bridge.setSignEvidence(False)
    assert saved == {"sign_evidence": False}


def test_the_deck_has_the_checkbox_bound_to_the_setting():
    qml = (ROOT / "assets" / "qml" / "TesterDeck.qml").read_text(encoding="utf-8")
    assert 'objectName: "signEvidenceCheck"' in qml and "testerBackend.signEvidence" in qml and "testerBackend.setSignEvidence(checked)" in qml


def test_the_history_window_has_the_signature_column_with_the_store_of_the_tester(folder, monkeypatch):
    pytest.importorskip("PySide6")
    import qt_tester  # noqa: PLC0415

    with_config(monkeypatch, {"trusted_keys": {"Ana": PUB.hex()}})
    monkeypatch.setattr(tester_config, "LOGS_FOLDER", str(folder))
    bridge = qt_tester.TesterQtBridge()
    model = bridge.history
    assert len(model.headers) == 8
    assert {r["signatureText"] for r in model.rows} == {"Signed by Ana", "Valid signature, unknown key", "Not signed"}
    assert "historySignature" in (ROOT / "assets" / "qml" / "EvidenceHistoryDialog.qml").read_text(encoding="utf-8")
