# =============================================================================
# URTC-TESTER - tests/test_selftest_verdict_reports.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A self-test that cannot decide is reported as unknown all the way: the plan, the exit status, the result record, the evidence record and the report."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import tester_cli
import tester_config as config
import tester_plan as tp
from tester_result_record import OUTCOMES, ResultRecord, load_record
from tester_simulator import SimulatedBoard
from urtc_can import evidence
from urtc_can import evidence_history_strings as hist

LANGUAGES = ("english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese")


@pytest.fixture(autouse=True)
def no_real_config(monkeypatch):
    monkeypatch.setattr(tester_cli, "evidence_signing_settings", lambda config=None: (False, ""))


def run(capsys, out: Path, tool: int):
    code = tester_cli.main(["selftest", "--transport", "simulate", "--tool", str(tool), "--out", str(out)])
    return code, capsys.readouterr().out


def test_a_tool_that_answers_sensibly_passes_with_exit_zero(tmp_path, capsys):
    code, out = run(capsys, tmp_path, 10)
    assert code == tester_cli.EXIT_PASS and "PASS: " in out


def test_a_tool_with_nothing_to_measure_is_unknown_with_its_own_exit_status(tmp_path, capsys):
    code, out = run(capsys, tmp_path, 11)  # the scan probe only speaks on a physical event
    assert code == tester_cli.EXIT_UNKNOWN == 4 and "UNKNOWN: " in out
    (record_path,) = sorted(tmp_path.glob("selftest_*.json"))
    assert load_record(record_path, tmp_path).outcome == "unknown"
    (evidence_path,) = sorted(tmp_path.glob("urtc_evidence_selftest_*.json"))
    record = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert record["outcome"] == "unknown" and evidence.verify(record) == []


def test_a_failing_tool_still_fails_with_exit_one(tmp_path, capsys):
    code = tester_cli.main(["selftest", "--transport", "simulate", "--tool", "0", "--fault", "system", "--out", str(tmp_path)])
    capsys.readouterr()
    assert code == tester_cli.EXIT_FAIL


def test_the_plan_report_counts_unknown_and_the_outcome_is_unknown_when_nothing_failed():
    plan = {"format": 1, "name": "u", "steps": [{"do": "check_faults"}, {"do": "selftest"}]}
    board = SimulatedBoard(11)
    board.open_channel()
    report = tp.run_plan(plan, board)
    assert [s.outcome for s in report.steps] == [tp.PASS, tp.UNKNOWN]
    assert report.outcome == tp.UNKNOWN
    assert report.steps[1].message.key == "QT_PM_SELFTEST_UNKNOWN"
    assert "1 unknown" in report.summary() and report.summary().startswith("UNKNOWN:")


def test_a_failure_wins_over_an_unknown_and_an_error_over_both():
    plan = {"format": 1, "name": "u", "steps": [{"do": "selftest"}, {"do": "expect_tool", "tool": 5}]}
    assert tp.run_plan(plan, SimulatedBoard(11)).outcome == tp.FAIL
    assert tp.run_plan(plan, SimulatedBoard(11, silent=True)).outcome in (tp.FAIL, tp.ERROR)


def test_the_result_record_and_the_evidence_record_accept_unknown_and_nothing_else_new():
    assert "unknown" in OUTCOMES and "unknown" in evidence.OUTCOMES
    sha = "a" * 64
    kwargs = dict(test_name="t", adapter="a", firmware_version="0.4", bus="can", bitrate=500000, log_file="l.log", log_sha256=sha)
    ResultRecord(outcome="unknown", **kwargs)
    with pytest.raises(ValueError):
        ResultRecord(outcome="maybe", **kwargs)


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_word_for_unknown_exists_in_every_language_and_differs_from_the_other_outcomes(language):
    words = {name: hist.text(language, hist.outcome_key(name)) for name in evidence.OUTCOMES}
    assert words["unknown"] and len(set(words.values())) == len(words)
    table = config.load_language(language)
    assert table["QT_PLAN_OUTCOME_UNKNOWN"] and "{unknown}" in table["QT_PLAN_SUMMARY"] and "{unknown}" in table["QT_PM_SELFTEST_UNKNOWN"]


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_report_of_an_unknown_result_says_unknown_in_the_language_of_the_report(tmp_path, capsys, language):
    base = tmp_path / "ev"
    base.mkdir()
    record = evidence.build(kind="test", outcome="unknown", timestamp_utc="2026-01-02T10:00:00Z", tool="URTC-TESTER", tool_version="0.4.8", subject={"name": "head-1"})
    (base / "a.json").write_text(json.dumps(record), encoding="utf-8")
    for fmt in ("html", "pdf"):
        path = tmp_path / f"r.{fmt}"
        code = tester_cli.main(["report", "--evidence-dir", str(base), "--out", str(path), "--format", fmt, "--language", language])
        capsys.readouterr()
        assert code == tester_cli.EXIT_PASS and path.stat().st_size > 0
    page = (tmp_path / "r.html").read_text(encoding="utf-8")
    assert hist.text(language, "EH_OUT_UNKNOWN") in page


def test_the_deck_summary_of_a_plan_names_the_unknown_count():
    table = config.load_language("portuguese")
    text = table["QT_PLAN_SUMMARY"].format(outcome="INDETERMINADO", passed=1, failed=0, unknown=1, errors=0, skipped=0)
    assert "1 indeterminados" in text
