# =============================================================================
# URTC-TESTER - tests/test_evidence_signing_cli.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The Ed25519 signature of the evidence records the tester writes: off by default, on by the setting or the flag, the key from a file and never printed,
checked by the history and shown by the report."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import tester_cli
import tester_config
from urtc_can import evidence, record_signing

SEED = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
OTHER = bytes.fromhex("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb")
PUBLIC = record_signing.public_key(SEED).hex()


def cli(capsys, *args):
    code = tester_cli.main([str(a) for a in args])
    captured = capsys.readouterr()
    return code, captured.out + captured.err


@pytest.fixture
def key_file(tmp_path, monkeypatch):
    path = tmp_path / "keys" / "records.key"
    path.parent.mkdir()
    path.write_text(SEED.hex() + "\n", encoding="ascii")
    monkeypatch.setenv(record_signing.KEY_ENV, str(path))
    return path


@pytest.fixture(autouse=True)
def no_real_config(monkeypatch):
    """The tests never read the config.json next to the program: the setting is whatever the test says."""
    monkeypatch.setattr(tester_cli, "evidence_signing_settings", lambda config=None: (False, ""))


def run_selftest(capsys, out: Path, *extra):
    return cli(capsys, "selftest", "--transport", "simulate", "--tool", "10", "--out", out, *extra)


def evidence_file(out: Path) -> dict:
    (path,) = sorted(out.glob("urtc_evidence_selftest_*.json"))
    return json.loads(path.read_text(encoding="utf-8"))


# -- the setting -------------------------------------------------------------------------------------------------------------------------------
def test_the_setting_is_off_unless_it_is_exactly_true():
    assert tester_config.evidence_signing_settings({}) == (False, "")
    for value in ("true", "yes", 1, 0, None, [], {"on": True}, "false", False):
        assert tester_config.evidence_signing_settings({"sign_evidence": value})[0] is False
    assert tester_config.evidence_signing_settings({"sign_evidence": True}) == (True, "")
    assert tester_config.evidence_signing_settings({"sign_evidence": True, "record_key_file": " /k/x.key "}) == (True, " /k/x.key ")
    assert tester_config.evidence_signing_settings({"record_key_file": 5}) == (False, "")


# -- characterization: what a run left before the signature existed is what it leaves now --------------------------------------------------
def test_by_default_the_evidence_is_not_signed(tmp_path, capsys, key_file):
    code, _ = run_selftest(capsys, tmp_path)
    assert code == 0
    shape = evidence_file(tmp_path)
    assert "signature" not in shape and evidence.verify(shape) == []


# -- signing -----------------------------------------------------------------------------------------------------------------------------
def test_the_flag_signs_the_evidence_and_the_signature_matches_the_key_file(tmp_path, capsys, key_file):
    code, out = run_selftest(capsys, tmp_path, "--sign-evidence")
    assert code == 0
    shape = evidence_file(tmp_path)
    assert evidence.verify(shape) == []
    assert shape["signature"]["public_key"] == PUBLIC
    assert record_signing.verify_evidence(shape, bytes.fromhex(PUBLIC))
    assert SEED.hex() not in out and SEED.hex() not in json.dumps(shape)


def test_signing_leaves_the_digest_and_the_other_files_as_they_were(tmp_path, capsys, key_file):
    plain, signed = tmp_path / "plain", tmp_path / "signed"
    run_selftest(capsys, plain)
    run_selftest(capsys, signed, "--sign-evidence")
    a, b = evidence_file(plain), evidence_file(signed)
    assert {k: v for k, v in b.items() if k != "signature"}.keys() == a.keys()
    assert len(list(plain.glob("*"))) == len(list(signed.glob("*")))      # the log, the result record and the evidence in both


def test_the_setting_in_the_configuration_signs_too(tmp_path, capsys, key_file, monkeypatch):
    monkeypatch.setattr(tester_cli, "evidence_signing_settings", lambda config=None: (True, str(key_file)))
    run_selftest(capsys, tmp_path)
    assert evidence_file(tmp_path)["signature"]["public_key"] == PUBLIC


def test_the_key_file_of_the_setting_is_the_one_used(tmp_path, capsys, monkeypatch):
    other = tmp_path / "other.key"
    other.write_text(OTHER.hex() + "\n", encoding="ascii")
    monkeypatch.setattr(tester_cli, "evidence_signing_settings", lambda config=None: (True, str(other)))
    run_selftest(capsys, tmp_path / "out")
    assert evidence_file(tmp_path / "out")["signature"]["public_key"] == record_signing.public_key(OTHER).hex()


def test_a_key_that_cannot_be_used_writes_no_evidence_and_says_so_without_the_key(tmp_path, capsys, monkeypatch):
    bad = tmp_path / "bad.key"
    bad.write_text("not hexadecimal secret-ish text\n", encoding="ascii")
    monkeypatch.setenv(record_signing.KEY_ENV, str(bad))
    code, out = run_selftest(capsys, tmp_path / "out", "--sign-evidence")
    assert code == 0                                              # the test itself passed
    assert "WARNING: the evidence record was not written because it could not be signed" in out
    assert "secret-ish" not in out
    assert not list((tmp_path / "out").glob("urtc_evidence_*.json"))
    assert list((tmp_path / "out").glob("selftest_*.log")) and list((tmp_path / "out").glob("selftest_*.json"))     # the log and the result record are written


def test_the_key_is_made_on_first_use_with_the_switch_on(tmp_path, capsys, monkeypatch):
    fresh = tmp_path / "new" / "records.key"
    monkeypatch.setenv(record_signing.KEY_ENV, str(fresh))
    assert not fresh.exists()
    run_selftest(capsys, tmp_path / "out", "--sign-evidence")
    assert fresh.is_file() and len(bytes.fromhex(fresh.read_text().strip())) == 32
    assert evidence_file(tmp_path / "out")["signature"]["key_id"] == record_signing.key_id(record_signing.public_key(bytes.fromhex(fresh.read_text().strip())))


# -- history and report ------------------------------------------------------------------------------------------------------------------
def signed_folder(tmp_path: Path) -> Path:
    base = tmp_path / "evidence"
    base.mkdir()
    good = record_signing.sign_evidence(evidence.build(kind="test", outcome="pass", timestamp_utc="2026-01-02T10:00:00Z", tool="URTC-TESTER", tool_version="0.4.6", subject={"name": "head-1"}), SEED)
    (base / "a.json").write_text(json.dumps(good), encoding="utf-8")
    return base


def test_the_history_checks_the_signatures_against_the_key_given(tmp_path, capsys):
    base = signed_folder(tmp_path)
    code, out = cli(capsys, "history", base)
    assert code == 0 and "SIGNATURE NOT VALID" not in out
    code, out = cli(capsys, "history", base, "--public-key", PUBLIC)
    assert code == 0 and "1 match" in out
    code, out = cli(capsys, "history", base, "--public-key", record_signing.public_key(OTHER).hex())
    assert code == 1 and "1 by another key" in out


def test_the_history_fails_on_a_record_whose_signature_does_not_match(tmp_path, capsys):
    base = signed_folder(tmp_path)
    forged = json.loads((base / "a.json").read_text(encoding="utf-8"))
    forged["detail"] = "changed"
    forged["evidence_sha256"] = evidence.digest(forged)         # an editor who fixes the digest cannot fix the signature
    (base / "a.json").write_text(json.dumps(forged), encoding="utf-8")
    code, out = cli(capsys, "history", base)
    assert code == 1 and "SIGNATURE NOT VALID" in out


def test_a_public_key_that_is_not_a_key_is_a_usage_error(tmp_path, capsys):
    base = signed_folder(tmp_path)
    for command in (("history", base), ("report", "--evidence-dir", base, "--out", tmp_path / "r.html")):
        code, out = cli(capsys, *command, "--public-key", "zz")
        assert code == 2 and "--public-key" in out


def test_the_report_shows_the_signature_and_fails_on_one_that_does_not_match(tmp_path, capsys):
    base = signed_folder(tmp_path)
    code, out = cli(capsys, "report", "--evidence-dir", base, "--out", tmp_path / "r.html", "--public-key", PUBLIC)
    assert code == 0 and "1 signed (0 with a signature that does not match)" in out
    page = (tmp_path / "r.html").read_text(encoding="utf-8")
    assert "Signature matches" in page and record_signing.key_id(bytes.fromhex(PUBLIC)) in page
    code, _ = cli(capsys, "report", "--evidence-dir", base, "--out", tmp_path / "r2.html", "--public-key", record_signing.public_key(OTHER).hex())
    assert code == 1
    assert "Signed by another key" in (tmp_path / "r2.html").read_text(encoding="utf-8")
    forged = json.loads((base / "a.json").read_text(encoding="utf-8"))
    forged["detail"] = "changed"
    forged["evidence_sha256"] = evidence.digest(forged)
    (base / "a.json").write_text(json.dumps(forged), encoding="utf-8")
    code, out = cli(capsys, "report", "--evidence-dir", base, "--out", tmp_path / "r3.html")
    assert code == 1 and "1 with a signature that does not match" in out
    assert "SIGNATURE NOT VALID" in (tmp_path / "r3.html").read_text(encoding="utf-8")


@pytest.mark.parametrize("language", ["english", "spanish", "italian", "french", "german", "chinese", "japanese", "portuguese"])
def test_the_report_with_a_signature_is_written_in_every_language_and_format(tmp_path, capsys, language):
    base = signed_folder(tmp_path)
    for fmt in ("html", "pdf"):
        code, _ = cli(capsys, "report", "--evidence-dir", base, "--out", tmp_path / f"r_{language}.{fmt}", "--format", fmt, "--language", language)
        assert code == 0
    assert (tmp_path / f"r_{language}.pdf").read_bytes().startswith(b"%PDF")
