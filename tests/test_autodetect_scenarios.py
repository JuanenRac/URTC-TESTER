# =============================================================================
# URTC Tester - tests/test_autodetect_scenarios.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The search for the bit rate of a bus against modelled buses (no port is opened and the windows are a few milliseconds): the order of the rates, a live bus that is found while
listening, a live bus that does not answer (nothing is transmitted), an idle bus that is found by asking, an adapter that fails or cannot be closed, and the callbacks."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tester_autodetect as ad
from tester_config import CAN_ID_ACTIVE_TOOL_RESP, CAN_ID_QUERY_ACTIVE_TOOL
from tester_transports import SLCANError

BITRATES = {label: index for index, label in enumerate(ad.AUTODETECT_ORDER)}
FAST = dict(listen_window=0.02, answer_window=0.02, pause=0.0)


class Bus:
    """A bus that runs at one rate. ``talks``: frames are heard at that rate while listening; ``answers``: the active tool answers a query."""

    def __init__(self, rate_label, talks=True, answers=True, fail_open=(), fail_close=False):
        self.rate = BITRATES[rate_label] if rate_label else None
        self.talks, self.answers = talks, answers
        self.fail_open, self.fail_close = {BITRATES[label] for label in fail_open}, fail_close
        self.opened: list[tuple[int, bool]] = []
        self.sent: list[tuple[int, bytes]] = []
        self.closed = 0

    def factory(self, port, log=None):
        return Trial(self)


class Trial:
    def __init__(self, bus):
        self.bus, self.code, self.listen_only = bus, None, True
        self.queried = False

    def open_channel(self, code, listen_only=False):
        self.bus.opened.append((code, listen_only))
        if code in self.bus.fail_open:
            raise SLCANError("cannot open")
        self.code, self.listen_only = code, listen_only

    def send_frame(self, can_id, data):
        assert not self.listen_only, "nothing may be transmitted from a listen-only channel"
        self.bus.sent.append((can_id, data))
        self.queried = can_id == CAN_ID_QUERY_ACTIVE_TOOL

    def read_frame(self, timeout=0.0):
        right = self.code == self.bus.rate
        if self.listen_only:
            return (0x1B8, b"\x00\x00\x00") if right and self.bus.talks else None
        if self.queried and right and self.bus.answers:
            self.queried = False
            return (CAN_ID_ACTIVE_TOOL_RESP, b"\x01")
        return None

    def close(self):
        self.bus.closed += 1
        if self.bus.fail_close:
            raise OSError("cannot close")


def scan(bus, labels=None, **callbacks):
    bitrates = {label: BITRATES[label] for label in (labels or ad.AUTODETECT_ORDER)}
    return ad.scan_bitrates("COM1", bus.factory, bitrates, **FAST, **callbacks)


def test_the_speed_of_the_tool_heads_is_tried_first_and_the_legacy_one_second():
    assert ad.AUTODETECT_ORDER[:2] == ("1 Mbit/s", "500 kbit/s")
    assert len(set(ad.AUTODETECT_ORDER)) == len(ad.AUTODETECT_ORDER)


def test_a_live_bus_is_found_while_listening_and_confirmed_by_the_active_tool():
    for label in ad.AUTODETECT_ORDER:
        bus = Bus(label)
        assert scan(bus) == label
        assert all(listen for _code, listen in bus.opened[:-1]) and bus.opened[-1] == (BITRATES[label], False)


def test_listening_never_transmits_and_the_query_is_sent_only_after_traffic_was_seen():
    bus = Bus("500 kbit/s")
    scan(bus)
    assert bus.sent == [(CAN_ID_QUERY_ACTIVE_TOOL, b"")]
    assert [code for code, listen in bus.opened if not listen] == [BITRATES["500 kbit/s"]]


def test_a_live_bus_that_does_not_answer_is_not_transmitted_to_at_any_other_rate():
    bus = Bus("250 kbit/s", answers=False)
    started = []
    assert scan(bus, on_active_phase=lambda: started.append(True)) is None
    assert started == []
    assert [code for code, listen in bus.opened if not listen] == [BITRATES["250 kbit/s"]]


def test_an_idle_bus_is_found_by_asking_at_each_rate_in_order():
    bus = Bus("125 kbit/s", talks=False)
    tried, phases = [], []
    assert scan(bus, on_try=tried.append, on_active_phase=lambda: phases.append(True)) == "125 kbit/s"
    assert phases == [True]
    order = list(ad.AUTODETECT_ORDER)
    assert tried[:len(order)] == order and tried[len(order):len(order) + 4] == order[:4]
    asked = [code for code, listen in bus.opened if not listen]
    assert asked == [BITRATES[label] for label in order[:4]]


def test_no_bus_at_all_gives_none_after_trying_every_rate_both_ways():
    bus = Bus(None)
    assert scan(bus) is None
    assert len(bus.opened) == 2 * len(ad.AUTODETECT_ORDER)
    assert bus.closed == len(bus.opened)


def test_rates_that_are_not_in_the_order_are_ignored_and_an_empty_list_gives_none():
    bus = Bus("1 Mbit/s")
    assert ad.scan_bitrates("COM1", bus.factory, {"1 Mbit/s": 0, "tuned": 9}, **FAST) == "1 Mbit/s"
    assert ad.scan_bitrates("COM1", bus.factory, {"odd": 1}, **FAST) is None
    assert ad.scan_bitrates("COM1", bus.factory, {}, **FAST) is None


def test_an_adapter_that_cannot_open_at_a_rate_is_skipped_and_the_next_rate_is_tried():
    bus = Bus("500 kbit/s", fail_open=("1 Mbit/s",))
    assert scan(bus) == "500 kbit/s"


def test_an_adapter_that_cannot_be_closed_does_not_stop_the_search():
    bus = Bus("500 kbit/s", fail_close=True)
    assert scan(bus) == "500 kbit/s" and bus.closed >= 3


def test_the_callbacks_say_each_rate_tried_and_the_traffic_that_was_seen():
    bus = Bus("500 kbit/s")
    tried, traffic = [], []
    assert scan(bus, on_try=tried.append, on_traffic=lambda label, seen: traffic.append((label, seen > 0))) == "500 kbit/s"
    assert tried == ["1 Mbit/s", "500 kbit/s"] and traffic == [("500 kbit/s", True)]
