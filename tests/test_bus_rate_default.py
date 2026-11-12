# =============================================================================
# URTC Tester - tests/test_bus_rate_default.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The bus of the tool heads runs at 1 Mbit/s: the tester opens it at that speed, tries it first when it looks for the speed of a bus, counts the load against it, and keeps
500 kbit/s (the speed of the early boards) one step behind."""
from __future__ import annotations

import tester_autodetect
import tester_bus_monitor
import tester_cli
import tester_config
from urtc_can import protocol


def test_the_default_speed_is_one_megabit_from_the_specification():
    assert protocol.BITRATE == 1_000_000 and protocol.BITRATE_LEGACY == 500_000
    assert tester_config.BITRATE_DEFAULT_SLCAN_CODE == protocol.SLCAN_BITRATE_DEFAULT_CODE == "8"
    assert tester_config.DEFAULT_BITRATE_LABEL == "1 Mbit/s"
    assert tester_config.bitrate_bps_for_label(tester_config.DEFAULT_BITRATE_LABEL) == protocol.BITRATE
    assert tester_cli.BITRATE == protocol.BITRATE and tester_bus_monitor.BUS_BITRATE_BPS == protocol.BITRATE


def test_the_labels_of_the_two_speeds_of_the_family_are_in_the_table_of_the_adapter():
    labels = dict(tester_config.SLCAN_BITRATES)
    assert labels["1 Mbit/s"] == "8" and labels["500 kbit/s"] == "6"


def test_the_search_for_the_speed_of_a_bus_tries_one_megabit_first_and_the_legacy_speed_second():
    order = tester_autodetect.AUTODETECT_ORDER
    assert order[0] == "1 Mbit/s" and order[1] == "500 kbit/s"
    assert sorted(order) == sorted(label for label, _code in tester_config.SLCAN_BITRATES)


def test_the_bus_load_is_counted_against_the_default_speed():
    stats = tester_bus_monitor.BusStats(clock=lambda: 0.0)
    for _ in range(100):
        stats.record(8)
    fps, load = stats.snapshot()
    assert fps == 100.0
    assert abs(load - 100 * (47 + 64) / 1_000_000 * 100) < 1e-6
    _fps, legacy = stats.snapshot(bitrate_bps=protocol.BITRATE_LEGACY)
    assert abs(legacy - 2 * load) < 1e-6            # the same frames fill twice the bus at half the speed
