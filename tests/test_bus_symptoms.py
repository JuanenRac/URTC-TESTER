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
    assert json.dumps(sorted(ap.BUS_SYMPTOM_KEYS)) == json.dumps(sorted(["mixed_bus_suspected", "no_head_at_any_speed", "bus_errors", "legacy_head_known"]))
