# =============================================================================
# URTC-TESTER - tests/test_bus_scenario_cli.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A plan run against the simulated head through a bus scenario: off unless asked for, refused on a real adapter, deterministic, and it leaves
evidence that says it was a simulation."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import tester_cli
from urtc_can import bus_scenario as bs
from urtc_can import evidence

ROOT = Path(__file__).resolve().parents[1]
PLAN = str(ROOT / "plans" / "identify_and_selftest.json")


def cli(capsys, *args):
    code = tester_cli.main(list(args))
    return code, capsys.readouterr().out


def scenario_file(tmp_path, faults, seed=3, name="s"):
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps({"format": bs.FORMAT, "name": name, "seed": seed, "faults": faults}), encoding="utf-8")
    return str(path)


def steps(out_json: str) -> list[tuple[str, str]]:
    return [(s["do"], s["outcome"]) for s in json.loads(out_json)["steps"]]


# ---- what the simulator did before is what it does without a scenario ------------------------------------------------------------
def test_without_a_scenario_the_run_is_the_one_it_always_was(tmp_path, capsys):
    code, out = cli(capsys, "run-plan", PLAN, "--transport", "simulate", "--out", str(tmp_path), "--json")
    assert code == 0 and steps(out) == [("query_version", "pass"), ("check_faults", "pass"), ("selftest", "pass")]
    (record,) = sorted(tmp_path.glob("identify-and-selftest_*.json"))
    assert json.loads(record.read_text(encoding="utf-8"))["adapter"] == "simulate:in-memory"


def test_a_scenario_with_no_faults_changes_nothing(tmp_path, capsys):
    scenario = scenario_file(tmp_path, [])
    code, out = cli(capsys, "run-plan", PLAN, "--transport", "simulate", "--scenario", scenario, "--out", str(tmp_path / "o"), "--json")
    assert code == 0 and steps(out) == [("query_version", "pass"), ("check_faults", "pass"), ("selftest", "pass")]


# ---- a faulty bus is felt ---------------------------------------------------------------------------------------------------------
def test_a_bus_that_loses_every_answer_cannot_pass_the_plan(tmp_path, capsys):
    scenario = scenario_file(tmp_path, [{"fault": "drop", "direction": "rx"}])
    code, out = cli(capsys, "run-plan", PLAN, "--transport", "simulate", "--scenario", scenario, "--out", str(tmp_path / "o"), "--json")
    assert code != 0 and json.loads(out)["outcome"] != "pass"


def test_a_silent_head_cannot_pass_the_plan(tmp_path, capsys):
    scenario = scenario_file(tmp_path, [{"fault": "mute", "direction": "tx"}])
    code, out = cli(capsys, "run-plan", PLAN, "--transport", "simulate", "--scenario", scenario, "--out", str(tmp_path / "o"), "--json")
    assert code != 0 and json.loads(out)["outcome"] != "pass"


def test_a_bus_that_only_repeats_and_delays_still_passes(tmp_path, capsys):
    scenario = scenario_file(tmp_path, [{"fault": "duplicate", "copies": 2}, {"fault": "delay", "direction": "rx", "ms": 3}])
    code, out = cli(capsys, "run-plan", PLAN, "--transport", "simulate", "--scenario", scenario, "--out", str(tmp_path / "o"), "--json")
    assert code == 0, out


@pytest.mark.parametrize("seed", range(25))
def test_a_plan_that_must_fail_never_passes_under_a_generated_scenario(tmp_path, capsys, seed):
    """The simulated head is tool 0; a plan that expects tool 5 fails on a clean bus and on every generated faulty one."""
    plan = tmp_path / "wrong_tool.json"
    plan.write_text(json.dumps({"format": 1, "name": "wrong-tool", "steps": [{"do": "expect_tool", "tool": 5}]}), encoding="utf-8")
    scenario = tmp_path / "g.json"
    scenario.write_text(bs.generate(seed, kinds=bs.GENERATED_KINDS + bs.NODE_PROFILES).to_json(), encoding="utf-8")
    code, out = cli(capsys, "run-plan", str(plan), "--transport", "simulate", "--scenario", str(scenario), "--out", str(tmp_path / "o"), "--json", "--timeout", "20")
    assert code != 0 and json.loads(out)["outcome"] != "pass"


def test_the_same_scenario_and_seed_give_the_same_steps(tmp_path, capsys):
    scenario = scenario_file(tmp_path, [{"fault": "drop", "direction": "rx", "per_mille": 600}], seed=11)
    runs = [steps(cli(capsys, "run-plan", PLAN, "--transport", "simulate", "--scenario", scenario, "--out", str(tmp_path / f"o{n}"), "--json")[1]) for n in range(2)]
    assert runs[0] == runs[1]


# ---- refused cases ----------------------------------------------------------------------------------------------------------------
def test_a_scenario_is_never_applied_to_a_real_adapter_or_a_trace(tmp_path, capsys):
    scenario = scenario_file(tmp_path, [])
    for transport in ("serial", "socketcan", "python-can", "replay"):
        code, out = cli(capsys, "info", "--transport", transport, "--port", "x", "--scenario", scenario, "--out", str(tmp_path / "o"))
        assert code == 2 and "only for --transport simulate" in out
    assert not (tmp_path / "o").exists()


def test_a_scenario_that_is_not_valid_runs_nothing(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text('{"format": "urtc-scenario/1", "name": "x", "faults": [{"fault": "drop", "bogus": 1}]}', encoding="utf-8")
    code, out = cli(capsys, "info", "--transport", "simulate", "--scenario", str(bad), "--out", str(tmp_path / "o"))
    assert code == 2 and "not valid" in out and not (tmp_path / "o").exists()
    code, out = cli(capsys, "info", "--transport", "simulate", "--scenario", str(tmp_path / "missing.json"), "--out", str(tmp_path / "o"))
    assert code == 2 and not (tmp_path / "o").exists()


def test_a_seed_without_a_scenario_is_refused(tmp_path, capsys):
    code, out = cli(capsys, "info", "--transport", "simulate", "--seed", "4", "--out", str(tmp_path))
    assert code == 2 and "--seed goes with --scenario" in out


# ---- the evidence -----------------------------------------------------------------------------------------------------------------
def test_the_evidence_says_it_was_a_simulation_with_a_scenario_and_its_seed(tmp_path, capsys):
    scenario = scenario_file(tmp_path, [{"fault": "duplicate", "direction": "rx"}], seed=9, name="echoes")
    out_dir = tmp_path / "o"
    code, _ = cli(capsys, "run-plan", PLAN, "--transport", "simulate", "--scenario", scenario, "--seed", "21", "--out", str(out_dir))
    assert code == 0
    (shape_path,) = sorted(out_dir.glob("urtc_evidence_*.json"))
    shape = json.loads(shape_path.read_text(encoding="utf-8"))
    assert evidence.verify(shape) == [] and shape["kind"] == "test"
    assert shape["transport"]["adapter"] == "simulate:scenario:echoes"
    assert "SIMULATED bus with a scenario" in shape["detail"] and "scenario echoes seed 21" in shape["detail"] and "duplicate" in shape["detail"]


def test_the_log_of_a_scenario_run_is_the_same_every_time(tmp_path, capsys):
    scenario = scenario_file(tmp_path, [{"fault": "drop", "direction": "rx", "per_mille": 300}, {"fault": "delay", "direction": "rx", "min_ms": 1, "max_ms": 9},
                                        {"fault": "reorder", "direction": "rx", "window": 3}], seed=5)
    logs = []
    for n in range(2):
        data = json.loads(cli(capsys, "run-plan", PLAN, "--transport", "simulate", "--scenario", scenario, "--out", str(tmp_path / f"o{n}"), "--json")[1])
        logs.append(Path(data["log"]).read_text(encoding="utf-8"))
    assert logs[0] == logs[1] and "RX 0x" in logs[0]
