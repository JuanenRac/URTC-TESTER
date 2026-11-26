# =============================================================================
# URTC-TESTER - tests/test_damaged_files.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Plans, records, results and option files that are hand-edited, damaged or saved by a Windows editor: each one is a message, never a traceback."""
from __future__ import annotations

import json

import pytest

import tester_blackbox_view as bbview
import tester_config
import tester_plan
import tester_result_record


def plan(step: dict, **extra) -> dict:
    return {"format": 1, "name": "p", "steps": [step], **extra}


@pytest.mark.parametrize("step", [
    {"do": ["send"]},
    {"do": {"kind": "wait"}},
    {"do": "expect_tool", "tool": [1]},
    {"do": "expect_tool", "tool": {}},
    {"do": "send", "id": "0100", "data": "00"},        # a leading zero is not a number in base 0
    {"do": "send", "id": "٣٠", "data": "00"},      # digits of another script
    {"do": "expect_frame", "id": "007"},
])
def test_a_hand_edited_step_is_a_listed_problem_or_valid_never_a_crash(step):
    problems = tester_plan.validate_plan(plan(step, actuation=True))
    assert isinstance(problems, list)


def test_a_decimal_identifier_with_a_leading_zero_means_the_decimal_number():
    assert tester_plan._parse_id("0100") == 100
    assert tester_plan._parse_id("007") == 7
    assert tester_plan._parse_id("0x100") == 0x100
    assert tester_plan._parse_id("٣") is None


@pytest.mark.parametrize("tool", [[1], {}, "1", True, 1.5, None])
def test_a_tool_that_is_not_a_whole_number_is_refused(tool):
    assert any("tool" in problem for problem in tester_plan.validate_plan(plan({"do": "expect_tool", "tool": tool})))


def test_a_plan_saved_with_a_byte_order_mark_is_read(tmp_path):
    path = tmp_path / "plan.json"
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps(plan({"do": "wait", "ms": 1})).encode("utf-8"))
    assert tester_plan.load_plan(path)["name"] == "p"


def test_a_very_deeply_nested_plan_or_record_is_a_message(tmp_path, monkeypatch):
    def too_deep(*args, **kwargs):
        raise RecursionError("maximum recursion depth exceeded")   # what a deeply nested file does on some versions of Python

    path = tmp_path / "deep.json"
    path.write_text('{"format": 1}', encoding="utf-8")
    monkeypatch.setattr(json, "loads", too_deep)
    with pytest.raises(tester_plan.PlanError):
        tester_plan.load_plan(path)
    with pytest.raises(bbview.ViewError):
        bbview.record_from_json("{}")


HEADER = "tick_ms,tool_id,current_temperature,target_temperature,thermal_fault,system_error,endstop"


@pytest.mark.parametrize("text", [
    HEADER + "\n" + "1" * 200_000 + ",1,1,1,0,0,0\n",     # a field longer than the reader takes
    HEADER + '\n"' + "x," * 100_000,                         # a quote that is never closed
], ids=["long-field", "open-quote"])
def test_a_damaged_csv_record_is_a_message(text):
    with pytest.raises(bbview.ViewError):
        bbview.record_from_text(text)


@pytest.mark.parametrize("change", [{"log_file": 5}, {"log_file": None}, {"log_file": ["a"]}])
def test_a_result_record_with_a_wrong_log_name_is_a_message(tmp_path, change):
    fields = {name: "x" for name in tester_result_record.ResultRecord.__dataclass_fields__}
    path = tmp_path / "result.json"
    path.write_text(json.dumps({**fields, **change}), encoding="utf-8")
    with pytest.raises(tester_result_record.RecordError):
        tester_result_record.load_record(path, tmp_path)


def test_option_files_saved_with_a_byte_order_mark_are_read(tmp_path, monkeypatch):
    config = tmp_path / "config.json"
    config.write_bytes(b'\xef\xbb\xbf{"language": "es"}')
    monkeypatch.setattr(tester_config, "CONFIG_PATH", str(config))
    assert tester_config.load_config() == {"language": "es"}
    names = tmp_path / "ids.json"
    names.write_bytes(b'\xef\xbb\xbf{"0x199": "My sensor"}')
    monkeypatch.setattr(tester_config, "CUSTOM_IDS_PATH", str(names))
    assert tester_config._load_custom_id_names() == {0x199: "My sensor"}
