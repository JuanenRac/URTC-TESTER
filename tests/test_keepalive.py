# =============================================================================
# URTC Tester - repeated commands (keepalive): the settings and the shared scheduler
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
import threading
import time

import pytest

import tester_config as cfg
from tester_keepalive import KeepaliveScheduler


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def make(clock=None, fail_ids=()):
    clock = clock or Clock()
    sent, failed, logs = [], [], []

    def send(can_id, data):
        if can_id in fail_ids:
            raise OSError("adapter gone")
        sent.append((can_id, bytes(data), clock.now))

    return KeepaliveScheduler(send, clock=clock, log=logs.append, on_failure=failed.append), clock, sent, failed, logs


# ---- the settings -------------------------------------------------------------------------------------------------------

def test_the_defaults_keep_each_tool_period_and_one_thread_per_command():
    assert cfg.keepalive_settings({}) == {"interval_ms": None, "single_io_thread": False}
    assert cfg.keepalive_period_s(0.15, cfg.keepalive_settings({})) == 0.15


@pytest.mark.parametrize("value, expected", [(20, 20), (100, 100), (200, 200), (19, None), (201, None), (0, None), (-5, None), (True, None), (False, None),
                                              ("100", None), (100.0, None), (None, None), ([100], None)])
def test_the_interval_is_a_whole_number_from_20_to_200(value, expected):
    assert cfg.keepalive_settings({"keepalive": {"interval_ms": value}})["interval_ms"] == expected


@pytest.mark.parametrize("value, expected", [(True, True), (False, False), (1, False), ("true", False), (None, False), ("yes", False)])
def test_the_single_thread_switch_needs_exactly_true(value, expected):
    assert cfg.keepalive_settings({"keepalive": {"single_io_thread": value}})["single_io_thread"] is expected


@pytest.mark.parametrize("config", [{"keepalive": 5}, {"keepalive": "fast"}, {"keepalive": None}, {"keepalive": []}, {}])
def test_a_keepalive_entry_that_is_not_an_object_gives_the_defaults(config):
    assert cfg.keepalive_settings(config) == cfg.KEEPALIVE_DEFAULTS


def test_the_configured_period_replaces_the_tool_own_one():
    settings = cfg.keepalive_settings({"keepalive": {"interval_ms": 80}})
    assert cfg.keepalive_period_s(0.4, settings) == 0.08
    assert cfg.keepalive_period_s(0.15, settings) == 0.08


def test_the_defaults_dictionary_is_not_changed_by_a_read():
    settings = cfg.keepalive_settings({"keepalive": {"interval_ms": 50, "single_io_thread": True}})
    settings["interval_ms"] = 99
    assert cfg.KEEPALIVE_DEFAULTS == {"interval_ms": None, "single_io_thread": False}


# ---- the scheduler ------------------------------------------------------------------------------------------------------

def test_a_registered_frame_goes_out_at_once_and_then_once_per_period():
    hub, clock, sent, _failed, _logs = make()
    hub.register("solder", (0x130, b"\x00\xdc"), 0.15)
    hub.tick()
    assert [s[:2] for s in sent] == [(0x130, b"\x00\xdc")]
    clock.now += 0.125
    hub.tick()
    assert len(sent) == 1
    clock.now += 0.125
    hub.tick()
    assert len(sent) == 2 and hub.sent == 2


def test_tick_returns_the_time_until_the_next_frame_or_half_a_second_when_idle():
    hub, clock, _sent, _failed, _logs = make()
    assert hub.tick() == 0.5
    hub.register("a", (1, b"\x01"), 0.2)
    assert hub.tick() == pytest.approx(0.2)
    clock.now += 0.15
    assert hub.tick() == pytest.approx(0.05)


def test_two_commands_are_sent_one_after_the_other_each_at_its_own_period():
    hub, clock, sent, _failed, _logs = make()
    hub.register("heater", (0x130, b"\x01"), 0.25)   # steps and periods are exact in binary: no rounding decides the count
    hub.register("fan", (0x1D0, b"\x02"), 0.5)
    for _ in range(5):
        hub.tick()
        clock.now += 0.125
    ids = [s[0] for s in sent]
    assert ids.count(0x130) == 3 and ids.count(0x1D0) == 2


def test_cancel_stops_only_its_own_command():
    hub, clock, sent, _failed, _logs = make()
    hub.register("a", (1, b"\x01"), 0.1)
    hub.register("b", (2, b"\x02"), 0.1)
    assert hub.cancel("a") is True and hub.cancel("a") is False
    hub.tick()
    assert [s[0] for s in sent] == [2] and hub.keys() == ["b"]


def test_registering_a_key_again_replaces_the_frame_and_the_period():
    hub, clock, sent, _failed, _logs = make()
    hub.register("a", (1, b"\x01"), 0.5)
    hub.register("a", (1, b"\x09"), 0.1)
    assert len(hub) == 1
    hub.tick()
    clock.now += 0.1
    hub.tick()
    assert [s[1] for s in sent] == [b"\x09", b"\x09"]


def test_a_frame_that_cannot_be_sent_removes_only_its_key_and_reports_it():
    hub, clock, sent, failed, logs = make(fail_ids=(2,))
    hub.register("bad", (2, b"\x01"), 0.1)
    hub.register("good", (3, b"\x01"), 0.1)
    hub.tick()
    assert failed == ["bad"] and hub.keys() == ["good"] and [s[0] for s in sent] == [3]
    assert any("KEEPALIVE_FAILED key=bad" in line and "adapter gone" in line for line in logs)


@pytest.mark.parametrize("period", [0, -1, -0.001, float("nan")])
def test_a_period_that_is_not_positive_is_refused(period):
    hub, *_ = make()
    with pytest.raises(ValueError):
        hub.register("a", (1, b""), period)


def test_the_frame_is_copied_so_a_later_change_of_the_callers_buffer_does_not_alter_it():
    hub, clock, sent, _failed, _logs = make()
    data = bytearray(b"\x01\x02")
    hub.register("a", (1, data), 0.1)
    data[0] = 0xFF
    hub.tick()
    assert sent[0][1] == b"\x01\x02"


def test_cancel_all_empties_the_registry():
    hub, clock, sent, _failed, _logs = make()
    for index in range(4):
        hub.register(f"k{index}", (index, b""), 0.1)
    hub.cancel_all()
    assert len(hub) == 0 and hub.tick() == 0.5 and sent == []


def test_the_worker_thread_repeats_a_frame_and_stops_on_close():
    lock = threading.Lock()
    seen = []

    def send(can_id, data):
        with lock:
            seen.append((threading.current_thread().name, can_id))

    hub = KeepaliveScheduler(send)
    hub.register("a", (7, b"\x01"), 0.02)
    hub.register("b", (8, b"\x01"), 0.02)
    hub.start()
    hub.start()  # a second start does not add a second thread
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        with lock:
            if len(seen) >= 6:
                break
        time.sleep(0.01)
    hub.close()
    with lock:
        count = len(seen)
        names = {name for name, _ in seen}
        ids = {can_id for _, can_id in seen}
    assert count >= 6 and ids == {7, 8} and names == {"urtc-tester-keepalive"}
    time.sleep(0.1)
    with lock:
        assert len(seen) == count  # nothing after close
    assert len([t for t in threading.enumerate() if t.name == "urtc-tester-keepalive"]) == 0


# ---- the deck: the shared thread and the configured period (needs PySide6) ----------------------------------------

try:
    import qt_tester
except ImportError:  # PySide6 is not installed
    qt_tester = None


class _Transport:
    def __init__(self):
        self.frames = []
        self.threads = set()

    def send_frame(self, can_id, data):
        self.frames.append((can_id, bytes(data)))
        self.threads.add(threading.current_thread().name)


@pytest.mark.skipif(qt_tester is None, reason="PySide6 is not available")
def test_the_deck_repeats_from_one_shared_thread_when_the_switch_is_on_and_stops_with_the_key(monkeypatch):
    monkeypatch.setattr(cfg, "keepalive_settings", lambda config=None: {"interval_ms": 20, "single_io_thread": True})
    bridge = qt_tester.TesterQtBridge()
    transport = _Transport()
    bridge._transport = transport
    bridge._log = lambda text: None
    bridge._start_watchdog("solder", 0.4, (0x130, b"\x01"), (0x130, b"\x00"))
    bridge._start_watchdog("laser", 0.4, (0x140, b"\x02"), (0x140, b"\x00"))
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and len(transport.frames) < 6:
        time.sleep(0.01)
    assert {can_id for can_id, _ in transport.frames} == {0x130, 0x140}
    assert transport.threads == {"urtc-tester-keepalive"}
    assert sorted(bridge._watchdog_stops) == ["laser", "solder"]
    bridge._stop_watchdog("solder")
    time.sleep(0.1)
    mark = len(transport.frames)
    time.sleep(0.15)
    new = [can_id for can_id, data in transport.frames[mark:] if data != b"\x00"]
    assert 0x130 not in new and 0x140 in new
    bridge._stop_all_watchdogs()
    bridge._keepalive.close()
    assert not bridge._watchdog_stops


@pytest.mark.skipif(qt_tester is None, reason="PySide6 is not available")
def test_the_deck_keeps_one_thread_per_command_by_default(monkeypatch):
    monkeypatch.setattr(cfg, "keepalive_settings", lambda config=None: dict(cfg.KEEPALIVE_DEFAULTS))
    bridge = qt_tester.TesterQtBridge()
    transport = _Transport()
    bridge._transport = transport
    bridge._log = lambda text: None
    bridge._start_watchdog("solder", 0.02, (0x130, b"\x01"), (0x130, b"\x00"))
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and len(transport.frames) < 3:
        time.sleep(0.01)
    assert transport.threads == {"urtc-tester-solder-watchdog"}
    assert getattr(bridge, "_keepalive", None) is None
    bridge._stop_all_watchdogs()
