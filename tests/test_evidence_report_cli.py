# =============================================================================
# URTC-TESTER - tests/test_evidence_report_cli.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""``--headless report``: a report of the evidence of a folder in HTML or PDF, the same bytes for the same records, every record shown (a record that
fails its check as NOT VALID), the simulated runs marked as such, and the history command unchanged."""
from __future__ import annotations

import json
from pathlib import Path

import tester_cli
from urtc_can import evidence

ROOT = Path(__file__).resolve().parents[1]
PLAN = str(ROOT / "plans" / "identify_and_selftest.json")


def cli(capsys, *args):
    code = tester_cli.main([str(a) for a in args])
    return code, capsys.readouterr().out


def make_record(name: str, when: str = "2026-01-02T10:00:00Z", **extra) -> dict:
    return evidence.build(kind="test", outcome="pass", timestamp_utc=when, tool="URTC-TESTER", tool_version="0.4.4", subject={"name": name}, **extra)


def folder(tmp_path: Path) -> Path:
    base = tmp_path / "evidence"
    base.mkdir()
    (base / "a.json").write_text(json.dumps(make_record("head-1")), encoding="utf-8")
    edited = dict(make_record("head-2", "2026-01-03T10:00:00Z"), outcome="fail")
    (base / "b.json").write_text(json.dumps(edited), encoding="utf-8")
    return base


# -- what the history command did before is what it does now -------------------------------------------------------------------------
def test_the_history_command_is_unchanged_by_the_report_command(tmp_path, capsys):
    base = folder(tmp_path)
    code, out = cli(capsys, "history", base)
    assert code == tester_cli.EXIT_FAIL and "NOT VALID" in out and "head-1" in out
    code, out = cli(capsys, "history", base, "--json")
    assert json.loads(out)["summary"]["invalid"] == 1
    assert tester_cli.main(["history", str(tmp_path / "none")]) == tester_cli.EXIT_USAGE


# -- the report --------------------------------------------------------------------------------------------------------------------------
def test_the_report_is_written_in_html_and_pdf_and_the_invalid_record_is_in_it(tmp_path, capsys):
    base = folder(tmp_path)
    code, out = cli(capsys, "report", "--evidence-dir", base, "--out", tmp_path / "r.html")
    assert code == tester_cli.EXIT_FAIL and "2 record(s), 1 valid, 1 not valid" in out
    page = (tmp_path / "r.html").read_text(encoding="utf-8")
    assert page.count('<section class="record') == 2 and "NOT VALID" in page and "head-2" in page
    code, _ = cli(capsys, "report", "--evidence-dir", base, "--out", tmp_path / "r.pdf")
    assert code == tester_cli.EXIT_FAIL and (tmp_path / "r.pdf").read_bytes().startswith(b"%PDF-1.4")
    code, _ = cli(capsys, "report", "--evidence-dir", base, "--out", tmp_path / "x.dat", "--format", "pdf", "--language", "portuguese")
    assert (tmp_path / "x.dat").read_bytes().startswith(b"%PDF-") and b"Relat" in (tmp_path / "x.dat").read_bytes()


def test_all_valid_records_exit_zero_and_the_same_records_give_the_same_file(tmp_path, capsys):
    base = tmp_path / "ev"
    base.mkdir()
    (base / "a.json").write_text(json.dumps(make_record("head-1")), encoding="utf-8")
    for fmt in ("html", "pdf"):
        for language in ("english", "japanese", "spanish"):
            outs = []
            for n in (1, 2):
                path = tmp_path / f"{n}.{fmt}"
                code, _ = cli(capsys, "report", "--evidence-dir", base, "--out", path, "--format", fmt, "--language", language)
                assert code == tester_cli.EXIT_PASS
                outs.append(path.read_bytes())
            assert outs[0] == outs[1]


def test_an_empty_folder_gives_a_report_that_says_so(tmp_path, capsys):
    base = tmp_path / "empty"
    base.mkdir()
    code, out = cli(capsys, "report", "--evidence-dir", base, "--out", tmp_path / "e.html")
    assert code == tester_cli.EXIT_PASS and "0 record(s)" in out
    assert "There are no records in the folder." in (tmp_path / "e.html").read_text(encoding="utf-8")


def test_wrong_arguments_are_a_usage_error_and_write_nothing(tmp_path, capsys):
    base = folder(tmp_path)
    for args in (("report",), ("report", "--evidence-dir", base), ("report", "--out", tmp_path / "r.html"),
                 ("report", "--evidence-dir", tmp_path / "missing", "--out", tmp_path / "r.html"),
                 ("report", "--evidence-dir", base, "--out", tmp_path / "r.html", "--language", "klingon"),
                 ("report", "--evidence-dir", base, "--out", tmp_path)):
        code, out = cli(capsys, *args)
        assert code == tester_cli.EXIT_USAGE and out.startswith("ERROR"), args
    assert not (tmp_path / "r.html").exists()


def test_a_hostile_record_cannot_inject_markup_through_the_command(tmp_path, capsys):
    base = tmp_path / "h"
    base.mkdir()
    bad = make_record('<script>alert(1)</script>"><b onmouseover=x>', detail="<img src=x onerror=alert(2)>")
    (base / "h.json").write_text(json.dumps(bad), encoding="utf-8")
    cli(capsys, "report", "--evidence-dir", base, "--out", tmp_path / "h.html")
    page = (tmp_path / "h.html").read_text(encoding="utf-8")
    assert "<script" not in page and "<img" not in page and "<b onmouseover" not in page and "&lt;script&gt;alert(1)&lt;/script&gt;" in page


# -- a run against the simulated bus is marked as a simulation ----------------------------------------------------------------------------
def test_the_evidence_of_a_scenario_run_is_reported_as_simulated(tmp_path, capsys):
    scenario = tmp_path / "s.json"
    scenario.write_text(json.dumps({"format": "urtc-scenario/1", "name": "quiet", "seed": 1, "faults": []}), encoding="utf-8")
    out_dir = tmp_path / "o"
    code, _ = cli(capsys, "run-plan", PLAN, "--transport", "simulate", "--scenario", scenario, "--out", out_dir, "--json")
    assert code == 0
    only = tmp_path / "only_evidence"                   # the run also leaves its own result record next to the evidence; the history lists that one as not valid
    only.mkdir()
    for path in out_dir.glob("urtc_evidence_*.json"):
        (only / path.name).write_bytes(path.read_bytes())
    code, out = cli(capsys, "report", "--evidence-dir", only, "--out", tmp_path / "sim.html")
    assert code == tester_cli.EXIT_PASS and "1 record(s), 1 valid" in out
    page = (tmp_path / "sim.html").read_text(encoding="utf-8")
    assert '<td class="flag">SIMULATED</td>' in page and '<td class="flag">REAL ADAPTER</td>' not in page
