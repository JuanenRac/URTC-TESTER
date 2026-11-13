# =============================================================================
# URTC Tester - tests/test_config_file_edges.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The file of settings at its edges: a missing, broken or foreign file, saving that merges and cleans up, and the bounds of every number read from it.

Everything runs on a temporary file; nothing here opens a bus or a board.
"""
from __future__ import annotations

import json
import os
import random

import pytest

import tester_config as config


@pytest.fixture()
def cfg(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.setattr(config, "CONFIG_PATH", str(path))
    return path


# ---- reading --------------------------------------------------------------------------------------------------------

def test_a_missing_file_is_an_empty_dict(cfg):
    assert config.load_config() == {}


@pytest.mark.parametrize("content", [b"", b"{", b"[1, 2]", b"null", b"\"text\"", b"42", b"\xff\xfe\x00bad", b"{\"a\": }"])
def test_a_broken_or_foreign_file_is_an_empty_dict(cfg, content):
    cfg.write_bytes(content)
    assert config.load_config() == {}


def test_a_good_file_is_read_whole(cfg):
    cfg.write_text(json.dumps({"language": "es", "x": [1, 2]}), encoding="utf-8")
    assert config.load_config() == {"language": "es", "x": [1, 2]}


def test_a_directory_in_place_of_the_file_is_an_empty_dict(cfg):
    cfg.mkdir()
    assert config.load_config() == {}


# ---- saving ---------------------------------------------------------------------------------------------------------

def test_saving_merges_and_leaves_no_temporary_file(cfg):
    cfg.write_text(json.dumps({"keep": 1, "language": "en"}), encoding="utf-8")
    assert config.save_config({"language": "de", "new": True}) is True
    assert json.loads(cfg.read_text(encoding="utf-8")) == {"keep": 1, "language": "de", "new": True}
    assert not os.path.exists(str(cfg) + ".tmp")


def test_saving_over_a_broken_file_starts_again_from_the_updates(cfg):
    cfg.write_bytes(b"{")
    assert config.save_config({"a": 1}) is True
    assert json.loads(cfg.read_text(encoding="utf-8")) == {"a": 1}


def test_a_failed_write_reports_false_cleans_up_and_keeps_the_old_file(cfg, monkeypatch):
    cfg.write_text(json.dumps({"old": 1}), encoding="utf-8")

    def refuse(src, dst):
        raise OSError("read-only")

    monkeypatch.setattr(config.os, "replace", refuse)
    assert config.save_config({"new": 2}) is False
    assert json.loads(cfg.read_text(encoding="utf-8")) == {"old": 1}
    assert not os.path.exists(str(cfg) + ".tmp")


def test_saving_twice_is_the_same_as_saving_once(cfg):
    config.save_config({"a": 1})
    first = cfg.read_text(encoding="utf-8")
    config.save_config({"a": 1})
    assert cfg.read_text(encoding="utf-8") == first


# ---- the bounds of the numbers ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(config.SELFTEST_LIMIT_BOUNDS))
def test_each_limit_of_the_self_test_takes_its_bounds_and_nothing_outside(name):
    low, high = config.SELFTEST_LIMIT_BOUNDS[name]
    default = config.SELFTEST_LIMIT_DEFAULTS[name]
    assert low <= default <= high
    for good in (low, high):
        assert config.selftest_limits({"selftest_limits": {name: good}})[name] == good
    for bad in (low - 1, high + 1, True, False, 1.5, "100", None, [low]):
        assert config.selftest_limits({"selftest_limits": {name: bad}})[name] == default


def test_the_limits_of_the_self_test_are_independent_and_a_foreign_block_changes_nothing():
    assert config.selftest_limits({"selftest_limits": {"cold_c": 30}})["solder_max_c"] == config.SELFTEST_LIMIT_DEFAULTS["solder_max_c"]
    for block in (None, [], "x", 3):
        assert config.selftest_limits({"selftest_limits": block}) == config.SELFTEST_LIMIT_DEFAULTS
    assert config.selftest_limits({"selftest_limits": {"unknown": 5}}) == config.SELFTEST_LIMIT_DEFAULTS


def test_the_interval_of_the_keepalive_takes_its_bounds_and_nothing_outside():
    low, high = config.KEEPALIVE_INTERVAL_BOUNDS_MS
    for good in (low, high, 100):
        assert config.keepalive_settings({"keepalive": {"interval_ms": good}})["interval_ms"] == good
    for bad in (low - 1, high + 1, True, 50.5, "50", None, 0, -20):
        assert config.keepalive_settings({"keepalive": {"interval_ms": bad}})["interval_ms"] is None
    for block in (None, [], "x"):
        assert config.keepalive_settings({"keepalive": block}) == config.KEEPALIVE_DEFAULTS


def test_the_single_thread_switch_is_on_only_for_a_true():
    for value in (1, "true", "yes", None, 0):
        assert config.keepalive_settings({"keepalive": {"single_io_thread": value}})["single_io_thread"] is False
    assert config.keepalive_settings({"keepalive": {"single_io_thread": True}})["single_io_thread"] is True


def test_the_period_of_a_repeated_command_is_the_configured_one_or_the_tools_own():
    assert config.keepalive_period_s(0.1, {"interval_ms": None}) == 0.1
    assert config.keepalive_period_s(0.1, {"interval_ms": 40}) == pytest.approx(0.04)
    assert config.keepalive_period_s(0.1, {}) == 0.1


def test_generated_settings_never_leave_their_bounds():
    rng = random.Random(20260713)
    pool = [None, True, False, 0, -1, 1, 20, 200, 201, 5000, 5001, 1.5, "7", [], {}]
    for _ in range(300):
        block = {name: rng.choice(pool) for name in config.SELFTEST_LIMIT_BOUNDS}
        limits = config.selftest_limits({"selftest_limits": block})
        for name, (low, high) in config.SELFTEST_LIMIT_BOUNDS.items():
            assert low <= limits[name] <= high
        guard = config.power_guard_settings({"power_guard": {"rise_percent": rng.choice(pool), "enabled": rng.choice(pool)}})
        assert 0 <= guard["rise_percent"] <= 500
        assert isinstance(guard["enabled"], bool)
        keep = config.keepalive_settings({"keepalive": {"interval_ms": rng.choice(pool)}})
        assert keep["interval_ms"] is None or 20 <= keep["interval_ms"] <= 200


def test_an_unknown_bitrate_label_gives_the_bus_default_and_a_known_one_its_speed():
    assert config.bitrate_bps_for_label("500 kbit/s") == 500000
    assert config.bitrate_bps_for_label("1 Mbit/s") == 1000000
    for label in ("", "fast", None):
        assert config.bitrate_bps_for_label(label) == config.protocol.BITRATE
