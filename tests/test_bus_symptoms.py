# =============================================================================
# URTC Tester - tests/test_bus_symptoms.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A bus that mixes speeds is recognised by its symptoms (the health frames of the heads that are heard, a search that finds nobody, a head known to be of the legacy
speed); the thresholds come from config.json. No change of the protocol."""
from __future__ import annotations

import pytest

import advanced_protocol as ap
import tester_config as config
from urtc_can import protocol


def health_frame(tec=0, rec=0, bus_off=0) -> bytes:
    return protocol.encode_health_profile(tec=tec, rec=rec, bus_off_count=bus_off, hsi_trim=16, loop_max_ms=7, mcu_temp_plus_40=65, vdda_mv=3300)[1]


def keys(result):
    return [key for key, _args in result]


def test_a_quiet_bus_gives_no_warning():
    assert ap.bus_symptoms([health_frame(), health_frame()]) == []


def test_the_error_counters_and_a_bus_off_of_the_heads_that_are_heard_warn():
    assert keys(ap.bus_symptoms([health_frame(tec=100)])) == ["STATE_BUS_ERRORS"]
    assert keys(ap.bus_symptoms([health_frame(rec=100)])) == ["STATE_BUS_ERRORS"]
    assert keys(ap.bus_symptoms([health_frame(bus_off=1)])) == ["STATE_BUS_ERRORS"]


def test_a_search_that_found_nobody_at_any_speed_warns():
    assert keys(ap.bus_symptoms([], found_nobody_at_any_speed=True)) == ["STATE_NO_HEAD_AT_ANY_SPEED"]


def test_a_known_legacy_head_with_errors_on_the_bus_means_a_mixed_bus():
    limits = config.bus_health_thresholds({"bus_health": {"legacy_heads": ["HEAD-OLD"]}})
    assert keys(ap.bus_symptoms([health_frame(tec=120)], heads_on_bus=["HEAD-OLD"], thresholds=limits)) == ["STATE_MIXED_BUS_SUSPECTED", "STATE_BUS_ERRORS", "STATE_LEGACY_HEAD_KNOWN"]
    assert keys(ap.bus_symptoms([health_frame()], heads_on_bus=["HEAD-OLD"], thresholds=limits)) == ["STATE_LEGACY_HEAD_KNOWN"]


@pytest.mark.parametrize("raw, expected", [
    ({}, (96, 96, 1, ())),
    ({"bus_health": {"tec_warn": 40, "rec_warn": 50, "bus_off_warn": 3, "legacy_heads": ["A"]}}, (40, 50, 3, ("A",))),
    ({"bus_health": {"tec_warn": 0, "rec_warn": 300, "bus_off_warn": "2"}}, (96, 96, 1, ())),
    ({"bus_health": "nonsense"}, (96, 96, 1, ())),
])
def test_the_thresholds_come_from_config_json_and_a_bad_value_keeps_its_default(raw, expected):
    limits = config.bus_health_thresholds(raw)
    assert (limits.tec_warn, limits.rec_warn, limits.bus_off_warn, limits.legacy_heads) == expected


def test_a_lower_threshold_from_the_configuration_warns_earlier():
    frame = health_frame(tec=50)
    assert ap.bus_symptoms([frame]) == []
    assert keys(ap.bus_symptoms([frame], thresholds=config.bus_health_thresholds({"bus_health": {"tec_warn": 50}}))) == ["STATE_BUS_ERRORS"]


def test_a_frame_too_short_to_decode_is_ignored():
    assert ap.bus_symptoms([b"\x01\x02"]) == []


def test_every_warning_has_its_text_in_the_eight_languages():
    import json
    import os
    for language in ("english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese"):
        path = os.path.join(os.path.dirname(os.path.abspath(config.__file__)), "language", f"{language}.lng")
        text = open(path, encoding="utf-8").read()
        for key in ap.BUS_SYMPTOM_KEYS.values():
            assert f"\n{key}=" in text, (language, key)
    assert json.dumps(sorted(ap.BUS_SYMPTOM_KEYS)) == json.dumps(sorted(["rates_declared_differ", "mixed_bus_suspected", "no_head_at_any_speed", "bus_errors", "legacy_head_known"]))


# ---- the live reading: the window judges the health frames that go by while it polls the board ------------------------------------------------------
def test_the_poll_keeps_the_health_frames_that_go_by_and_the_window_turns_them_into_a_warning(monkeypatch):
    qt = pytest.importorskip("qt_tester")
    frames = [(protocol.CAN_ID_HEALTH_PROFILE, health_frame(tec=120)), (protocol.CAN_ID_ACTIVE_TOOL_RESP, bytes([0, 0, 0, 0, 0, 0, 0, 0]))]

    class Transport:
        def read_frame(self, timeout=0.1):
            return frames.pop(0) if frames else None

    bridge = qt.TesterQtBridge.__new__(qt.TesterQtBridge)
    bridge._transport = Transport()
    kept: list[bytes] = []
    answer = qt.TesterQtBridge._wait_for(bridge, protocol.CAN_ID_ACTIVE_TOOL_RESP, 0.5, health_frames=kept)
    assert answer is not None and kept == [health_frame(tec=120)]
    bridge._active_tool_id = 0
    monkeypatch.setattr(qt, "bus_health_thresholds", lambda: config.bus_health_thresholds({}))
    assert [key for key, _args in qt.TesterQtBridge._bus_symptoms(bridge, kept)] == ["STATE_BUS_ERRORS"]


def test_without_a_list_the_wait_behaves_as_before():
    qt = pytest.importorskip("qt_tester")
    frames = [(protocol.CAN_ID_HEALTH_PROFILE, health_frame(tec=120)), (0x111, b"\x01")]

    class Transport:
        def read_frame(self, timeout=0.1):
            return frames.pop(0) if frames else None

    bridge = qt.TesterQtBridge.__new__(qt.TesterQtBridge)
    bridge._transport = Transport()
    assert qt.TesterQtBridge._wait_for(bridge, 0x111, 0.5) == b"\x01"


# ---- the speed the heads declare in their identity frames (0x1BB, protocol version 2) -----------------------------------------------------------------
from urtc_can import health_info  # noqa: E402


def info_frame(rate=1_000_000, version=2) -> bytes:
    return health_info.encode(version, 8, 4, 4, 0, 600, rate)


def test_two_heads_that_declare_different_speeds_are_a_mixed_bus_and_come_first():
    result = ap.bus_symptoms([health_frame()], info_frames=[info_frame(1_000_000), info_frame(500_000)])
    assert keys(result) == ["STATE_RATES_DECLARED_DIFFER"]


def test_equal_declared_speeds_or_heads_that_declare_nothing_add_no_warning():
    assert ap.bus_symptoms([health_frame()], info_frames=[info_frame(), info_frame()]) == []
    assert ap.bus_symptoms([health_frame()], info_frames=[info_frame(version=1), info_frame(500_000)]) == []
    assert ap.bus_symptoms([health_frame()], info_frames=[b"\x02", b""]) == []


def test_the_symptoms_still_work_for_a_head_that_declares_nothing():
    limits = config.bus_health_thresholds({"bus_health": {"legacy_heads": ["HEAD-OLD"]}})
    result = ap.bus_symptoms([health_frame(tec=120)], heads_on_bus=["HEAD-OLD"], thresholds=limits, info_frames=[info_frame(version=1)])
    assert keys(result) == ["STATE_MIXED_BUS_SUSPECTED", "STATE_BUS_ERRORS", "STATE_LEGACY_HEAD_KNOWN"]


def test_the_line_with_the_declared_speed():
    assert ap.declared_rate_line([]) is None and ap.declared_rate_line([b"\x02\x01"]) is None
    assert ap.declared_rate_line([info_frame(1_000_000)]) == ("STATE_RATE_DECLARED", {"rate": "1 Mbit/s"})
    assert ap.declared_rate_line([info_frame(500_000), info_frame(1_000_000)]) == ("STATE_RATE_DECLARED", {"rate": "1 Mbit/s / 500 kbit/s"})
    assert ap.declared_rate_line([info_frame(version=1)]) == ("STATE_RATE_NOT_DECLARED", {})
    assert ap.declared_rate_line([info_frame(version=1), info_frame(250_000)]) == ("STATE_RATE_DECLARED", {"rate": "250 kbit/s"})


@pytest.mark.parametrize("language", ["english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese"])
def test_the_texts_of_the_declared_speed_exist_in_every_language(language):
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(config.__file__)), "language", f"{language}.lng")
    text = open(path, encoding="utf-8").read()
    for key in ("STATE_RATES_DECLARED_DIFFER", "STATE_RATE_DECLARED", "STATE_RATE_NOT_DECLARED"):
        assert f"\n{key}=" in text, (language, key)
    assert "{rate}" in text.split("\nSTATE_RATE_DECLARED=")[1].split("\n")[0]


def test_the_poll_keeps_the_identity_frames_that_go_by_and_the_window_judges_two_heads_together():
    qt = pytest.importorskip("qt_tester")
    frames = [(protocol.CAN_ID_HEALTH_INFO, info_frame(1_000_000)), (protocol.CAN_ID_HEALTH_INFO, info_frame(500_000)), (protocol.CAN_ID_ACTIVE_TOOL_RESP, bytes(8))]

    class Transport:
        def read_frame(self, timeout=0.1):
            return frames.pop(0) if frames else None

    bridge = qt.TesterQtBridge.__new__(qt.TesterQtBridge)
    bridge._transport = Transport()
    kept: list[bytes] = []
    assert qt.TesterQtBridge._wait_for(bridge, protocol.CAN_ID_ACTIVE_TOOL_RESP, 0.5, info_frames=kept) is not None
    assert kept == [info_frame(1_000_000), info_frame(500_000)]
    bridge._active_tool_id = 0
    assert [key for key, _args in qt.TesterQtBridge._bus_symptoms(bridge, [], kept)] == ["STATE_RATES_DECLARED_DIFFER"]
