# =============================================================================
# URTC Tester - tests/test_power_guard.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A tool that is on asks the person again before it goes up by more than a set percentage over the value that was confirmed.

The settings (``power_guard`` in config.json) are tested without Qt; the panel controller is tested with the same fake host and transport as the
other panel tests (the ones that need PySide6 skip without it). Nothing here has run against a real board.
"""
from __future__ import annotations

import pytest

import tester_config as config

DEFAULT = {"enabled": True, "rise_percent": 10}


# ---- the settings and the rule (no Qt) -----------------------------------------------------------------------------

def test_without_a_setting_the_guard_is_on_and_allows_twenty_percent():
    assert config.power_guard_settings({}) == DEFAULT
    assert config.power_guard_settings({"power_guard": "oops"}) == DEFAULT


@pytest.mark.parametrize("value, expected", [(0, 0), (35, 35), (500, 500), (-1, 10), (501, 10), (12.5, 10), ("30", 10), (True, 10), (None, 10)])
def test_the_percentage_is_a_whole_number_from_0_to_500(value, expected):
    assert config.power_guard_settings({"power_guard": {"rise_percent": value}})["rise_percent"] == expected


@pytest.mark.parametrize("value, expected", [(False, False), (True, True), (0, True), ("false", True), (None, True)])
def test_only_an_explicit_false_turns_the_guard_off(value, expected):
    assert config.power_guard_settings({"power_guard": {"enabled": value}})["enabled"] is expected


def test_a_rise_over_the_percentage_needs_confirmation_and_a_fall_never_does():
    rule = config.power_rise_needs_confirmation
    assert rule(100, 110, DEFAULT) is False          # exactly 10 % is allowed
    assert rule(100, 111, DEFAULT) is True
    assert rule(100, 10, DEFAULT) is False
    assert rule(100, 100, DEFAULT) is False
    assert rule(0, 1, DEFAULT) is True               # a rise from zero is always more than any percentage
    assert rule(0, 0, DEFAULT) is False
    assert rule(100, 101, {"enabled": True, "rise_percent": 0}) is True
    assert rule(100, 600, {"enabled": True, "rise_percent": 500}) is False
    assert rule(100, 601, {"enabled": True, "rise_percent": 500}) is True


def test_the_switch_off_and_values_that_are_not_numbers_never_ask():
    assert config.power_rise_needs_confirmation(10, 255, {"enabled": False, "rise_percent": 20}) is False
    assert config.power_rise_needs_confirmation("10", 255, DEFAULT) is False
    assert config.power_rise_needs_confirmation(10, True, DEFAULT) is False


# ---- the panel controller ------------------------------------------------------------------------------------------

pytest.importorskip("PySide6")
import test_qt_tool_panel as panel_tests  # noqa: E402  (the fake host and transport of the panel tests)

import qt_tool_panel  # noqa: E402

app = panel_tests.app
DRILL = panel_tests.DRILL


@pytest.fixture()
def guard(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_PATH", str(tmp_path / "config.json"))
    return tmp_path / "config.json"


def drill_on(speed: int = 100):
    host = panel_tests.FakeHost(DRILL)
    controller = qt_tool_panel.ToolPanelController(host)
    controller.setValue("speed", speed)
    controller.toggle(0, 0, True)
    return host, controller


def speed_of(controller) -> int:
    return next(c["value"] for c in controller.sections[0]["controls"] if c["id"] == "speed")


def test_a_big_rise_while_the_tool_is_on_is_held_back_until_the_person_confirms(app, guard):
    host, controller = drill_on(100)
    assert controller.needsConfirm("speed", 111) is True
    controller.setValue("speed", 111)
    assert speed_of(controller) == 100 and host.logs[-1] == "PANEL_POWER_RAISE_BLOCKED"
    assert host.watchdogs["panel5_0"][1][1][0] == 100            # the repeated frame still carries the confirmed value
    controller.setValueConfirmed("speed", 111)
    assert speed_of(controller) == 111 and host.watchdogs["panel5_0"][1][1][0] == 111


def test_a_small_rise_and_any_fall_go_through_without_asking(app, guard):
    host, controller = drill_on(100)
    assert controller.needsConfirm("speed", 110) is False
    controller.setValue("speed", 110)
    assert speed_of(controller) == 110
    controller.setValue("speed", 10)
    assert speed_of(controller) == 10 and "PANEL_POWER_RAISE_BLOCKED" not in host.logs
    controller.setValue("speed", 110)                              # back up to what the person confirmed
    assert speed_of(controller) == 110


def test_a_drag_in_small_steps_cannot_creep_past_the_limit(app, guard):
    host, controller = drill_on(100)
    for value in range(101, 130):
        controller.setValue("speed", value)
    assert speed_of(controller) == 110 and host.logs.count("PANEL_POWER_RAISE_BLOCKED") == 19


def test_a_value_confirmed_is_the_new_reference_for_the_next_rise(app, guard):
    host, controller = drill_on(100)
    controller.setValueConfirmed("speed", 150)
    controller.setValue("speed", 165)                              # 10 % over 150
    assert speed_of(controller) == 165
    controller.setValue("speed", 166)
    assert speed_of(controller) == 165


def test_a_tool_that_is_off_takes_any_value_and_switching_on_confirms_the_value(app, guard):
    host = panel_tests.FakeHost(DRILL)
    controller = qt_tool_panel.ToolPanelController(host)
    controller.setValue("speed", 10)
    controller.setValue("speed", 250)                              # nothing is on: no question
    assert speed_of(controller) == 250 and controller.needsConfirm("speed", 255) is False
    controller.toggle(0, 0, True)
    assert controller.needsConfirm("speed", 255) is False          # 250 was the value confirmed by switching on
    controller.toggle(0, 0, False)
    controller.setValue("speed", 10)
    controller.toggle(0, 0, True)
    assert controller.needsConfirm("speed", 13) is True            # a new session starts from the new value


def test_the_percentage_and_the_switch_come_from_the_settings_file(app, guard):
    guard.write_text('{"power_guard": {"rise_percent": 50}}', encoding="utf-8")
    host, controller = drill_on(100)
    assert controller.needsConfirm("speed", 150) is False and controller.needsConfirm("speed", 151) is True
    guard.write_text('{"power_guard": {"enabled": false}}', encoding="utf-8")
    assert controller.needsConfirm("speed", 255) is False
    controller.setValue("speed", 255)
    assert speed_of(controller) == 255


def test_a_control_that_is_not_a_number_or_an_unknown_one_never_asks(app, guard):
    host, controller = drill_on(100)
    assert controller.needsConfirm("nonsense", 5) is False
    controller.setValue("nonsense", 5)
    assert speed_of(controller) == 100


def test_the_default_percentage_of_the_guard_is_ten_and_a_file_can_change_it():
    assert config.POWER_GUARD_DEFAULTS["rise_percent"] == 10
    rule = config.power_rise_needs_confirmation
    assert rule(200, 220, config.power_guard_settings({})) is False
    assert rule(200, 221, config.power_guard_settings({})) is True
    assert rule(200, 221, config.power_guard_settings({"power_guard": {"rise_percent": 25}})) is False
