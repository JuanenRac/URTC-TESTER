# =============================================================================
# URTC Tester - tests/test_tester_config_file.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The settings file, the language files, the custom identifier names and the translations of log and status lines."""
from __future__ import annotations

import json
import sys
import types

import pytest

import tester_config as config


@pytest.fixture()
def settings_file(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.setattr(config, "CONFIG_PATH", str(path))
    return path


# ---- bitrates ------------------------------------------------------------------------------------------------------

def test_a_bitrate_label_gives_its_bits_per_second_and_an_unknown_one_gives_500_kbit(monkeypatch):
    assert config.bitrate_bps_for_label("500 kbit/s") == 500000
    assert config.bitrate_bps_for_label("1 Mbit/s") == 1000000
    assert config.bitrate_bps_for_label("nonsense") == 500000


# ---- config.json -------------------------------------------------------------------------------------------------------

def test_without_a_settings_file_the_configuration_is_empty(settings_file):
    assert config.load_config() == {}


def test_a_broken_settings_file_or_one_that_is_not_an_object_reads_as_empty(settings_file):
    settings_file.write_text("{oops", encoding="utf-8")
    assert config.load_config() == {}
    settings_file.write_text('"text"', encoding="utf-8")
    assert config.load_config() == {}
    settings_file.write_bytes(b"\xff\xfe\x00")
    assert config.load_config() == {}


def test_saving_one_setting_keeps_the_others(settings_file):
    settings_file.write_text(json.dumps({"future_setting": 3}), encoding="utf-8")
    assert config.save_config({"language": "fr"}) is True
    assert json.loads(settings_file.read_text(encoding="utf-8")) == {"future_setting": 3, "language": "fr"}
    assert not settings_file.with_name("config.json.tmp").exists()


def test_saving_where_nothing_can_be_written_returns_false(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_PATH", str(tmp_path / "no_such_folder" / "config.json"))
    assert config.save_config({"language": "fr"}) is False


# ---- language files ---------------------------------------------------------------------------------------------------

def test_a_language_file_is_read_as_key_value_lines(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LANGUAGE_FOLDER", str(tmp_path))
    (tmp_path / "xx.lng").write_text("# comment\n\nA=one\\ntwo\nNOSEPARATOR\nB=x=y\r\n", encoding="utf-8")
    assert config.load_language("xx") == {"A": "one\ntwo", "B": "x=y"}


def test_a_language_name_that_could_leave_the_folder_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LANGUAGE_FOLDER", str(tmp_path))
    (tmp_path.parent / "outside.lng").write_text("A=1\n", encoding="utf-8")
    assert config.load_language("../outside") == {}
    assert config.load_language("a b") == {}


def test_a_missing_or_unreadable_language_file_reads_as_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LANGUAGE_FOLDER", str(tmp_path))
    assert config.load_language("zz") == {}
    (tmp_path / "bad.lng").write_bytes(b"\xff\xfe\x00KEY=1")
    assert config.load_language("bad") == {}


def test_a_text_without_a_translation_is_shown_as_its_key_and_a_bad_template_survives(monkeypatch):
    monkeypatch.setattr(config, "_translations", {"HELLO": "Hello {name}", "BAD": "Hello {missing}", "POS": "Hello {0}"})
    assert config._("HELLO", name="Ana") == "Hello Ana"
    assert config._("BAD", name="Ana") == "Hello {missing}"
    assert config._("POS", name="Ana") == "Hello {0}"
    assert config._("NOT_THERE") == "NOT_THERE"


# ---- translated log and status lines ----------------------------------------------------------------------------------

def test_a_log_line_gets_its_label_and_the_known_detail_translated(monkeypatch):
    monkeypatch.setattr(config, "_translations", {"QTLOG_PROBE_START": "Probe", "QTLOG_PROBE_BLOCKED": "Probe blocked", "QTLOGD_NO_RESPONSE": "no answer"})
    assert config.translate_log_line("PROBE_START no response") == "Probe: no answer"
    assert config.translate_log_line("PROBE_START other detail") == "Probe: other detail"
    assert config.translate_log_line("PROBE_BLOCKED") == "Probe blocked"
    assert config.translate_log_line("lower case") == "lower case"
    assert config.translate_log_line("UNKNOWN_WORD detail") == "UNKNOWN_WORD detail"


def test_a_label_only_word_drops_the_english_detail(monkeypatch):
    monkeypatch.setattr(config, "_translations", {"QTLOG_ERROR": "Error"})
    assert config.translate_log_line("ERROR something broke") == "Error"


def test_a_status_is_translated_by_its_longest_known_run_of_words(monkeypatch):
    monkeypatch.setattr(config, "_translations", {"QTSTATUS_CONNECTED": "Connected", "QTSTATUS_CONNECTED_TO": "Connected to"})
    assert config.translate_status("CONNECTED TO COM3") == "Connected to COM3"
    assert config.translate_status("CONNECTED COM3") == "Connected COM3"
    assert config.translate_status("NOTHING HERE") == "NOTHING HERE"


# ---- custom identifier names ----------------------------------------------------------------------------------------------

def test_custom_identifier_names_are_read_and_a_bad_entry_does_not_spoil_the_rest(tmp_path, monkeypatch):
    path = tmp_path / "urtc_custom_ids.json"
    monkeypatch.setattr(config, "CUSTOM_IDS_PATH", str(path))
    assert config._load_custom_id_names() == {}
    path.write_text(json.dumps({"0x199": "My sensor", "not a number": "x", "300": "Decimal"}), encoding="utf-8")
    assert config._load_custom_id_names() == {0x199: "My sensor", 300: "Decimal"}


def test_a_broken_custom_identifier_file_is_ignored(tmp_path, monkeypatch):
    path = tmp_path / "urtc_custom_ids.json"
    monkeypatch.setattr(config, "CUSTOM_IDS_PATH", str(path))
    path.write_text("{oops", encoding="utf-8")
    assert config._load_custom_id_names() == {}


# ---- serial ports and the thermal summary ---------------------------------------------------------------------------------

def test_the_serial_ports_are_listed_only_when_pyserial_is_there(monkeypatch):
    monkeypatch.setattr(config, "HAVE_SERIAL", False)
    assert config.list_serial_ports() == []
    tools = types.ModuleType("serial.tools")
    list_ports = types.ModuleType("serial.tools.list_ports")
    list_ports.comports = lambda: [types.SimpleNamespace(device="COM3"), types.SimpleNamespace(device="COM7")]
    tools.list_ports = list_ports
    package = types.ModuleType("serial")
    package.tools = tools
    monkeypatch.setitem(sys.modules, "serial", package)
    monkeypatch.setitem(sys.modules, "serial.tools", tools)
    monkeypatch.setitem(sys.modules, "serial.tools.list_ports", list_ports)
    monkeypatch.setattr(config, "HAVE_SERIAL", True)
    assert config.list_serial_ports() == ["COM3", "COM7"]


def test_the_thermal_summary_says_when_there_was_no_answer_and_when_nothing_is_stored(monkeypatch):
    monkeypatch.setattr(config, "_translations", {
        "LBL_THERMAL_STATS_NO_RESPONSE": "no answer", "LBL_THERMAL_STATS_TEXT": "{faults} faults, {hours} h, last {last}",
        "LBL_THERMAL_STATS_NOT_PERSISTED": "not stored", "VAL_NONE": "none"})
    assert config.format_thermal_stats(None) == "no answer"
    stats = {"heater_on_seconds": 5400, "fault_count": 2, "last_fault_name": "", "persisted": True}
    assert config.format_thermal_stats(stats) == "2 faults, 1.50 h, last none"
    stats["persisted"] = False
    assert config.format_thermal_stats(stats).endswith("\nnot stored")


@pytest.mark.xfail(strict=True, raises=AttributeError, reason="a custom identifier file that holds a JSON list instead of an object raises while the module is imported")
def test_a_custom_identifier_file_that_is_a_list_is_ignored(tmp_path, monkeypatch):
    path = tmp_path / "urtc_custom_ids.json"
    monkeypatch.setattr(config, "CUSTOM_IDS_PATH", str(path))
    path.write_text("[1, 2]", encoding="utf-8")
    assert config._load_custom_id_names() == {}
