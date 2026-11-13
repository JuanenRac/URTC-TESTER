# =============================================================================
# URTC Tester - repeated commands against a simulated head with the 250 ms watchdog of the firmware
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The shared keepalive scheduler in a closed loop with a simulated soldering iron whose setpoint watchdog is 250 ms.

Every interval the settings accept (20 to 200 ms) is run on a virtual clock where each frame costs bus time, with one to eight repeated commands sharing the one
thread. The iron must never lose its target, and the longest silence on any command must stay under the watchdog. A period the settings refuse (above 200 ms)
is run as a control: the same simulation does detect a watchdog that expires, so a green result is not an artefact of the model. Nothing here replaces a bench
run with a real head; it only shows that the scheduling arithmetic cannot be the cause of a dropped actuator.
"""
import pytest

import tester_config as cfg
from tester_keepalive import KeepaliveScheduler
from urtc_can.heater_sim import SolderingIronModel

WATCHDOG_S = 0.250
HEATER_ID = 0x130
OTHER_IDS = (0x140, 0x160, 0x170, 0x180, 0x190, 0x1A0, 0x1B0)   # more commands repeated on the same thread (drill, laser ...)
FRAME_COST_S = 0.001      # generous bus time per frame (a data frame at 1 Mbit/s lasts about 0.13 ms)


class World:
    """A virtual clock that also advances the simulated iron, and the record of when each command went out."""

    def __init__(self):
        self.now = 0.0
        self.iron = SolderingIronModel({"setpoint_watchdog_ms": 250})
        self.sent_at: dict[int, list[float]] = {}
        self.target_lost = False

    def clock(self):
        return self.now

    def elapse(self, seconds):
        self.iron.advance(seconds)
        self.now += seconds
        if self.iron.setpoint_c == 0 and self.sent_at.get(HEATER_ID):
            self.target_lost = True

    def send(self, can_id, data):
        self.sent_at.setdefault(can_id, []).append(self.now)
        if can_id == HEATER_ID:
            self.iron.set_target(int.from_bytes(data[:2], "big"))
        self.elapse(FRAME_COST_S)


def run(period_s, commands, seconds=6.0):
    world = World()
    hub = KeepaliveScheduler(world.send, clock=world.clock)
    hub.register("heater", (HEATER_ID, (220).to_bytes(2, "big")), period_s)
    for index in range(commands - 1):
        hub.register(f"other{index}", (OTHER_IDS[index], b"\x01"), period_s)
    while world.now < seconds:
        wait = hub.tick()
        world.elapse(max(wait, 0.0005))
    return world


def longest_silence(world, can_id):
    times = world.sent_at[can_id]
    return max(b - a for a, b in zip(times, times[1:], strict=False))


@pytest.mark.parametrize("interval_ms", [20, 50, 100, 150, 200])
@pytest.mark.parametrize("commands", [1, 2, 4, 8])
def test_no_accepted_interval_lets_the_iron_lose_its_target(interval_ms, commands):
    settings = cfg.keepalive_settings({"keepalive": {"interval_ms": interval_ms}})
    assert settings["interval_ms"] == interval_ms
    world = run(cfg.keepalive_period_s(0.15, settings), commands)
    assert not world.target_lost, "the watchdog of the iron expired although the command was repeated"
    assert world.iron.setpoint_c == 220
    for can_id in world.sent_at:
        assert longest_silence(world, can_id) < WATCHDOG_S, f"command {can_id:#x} was silent for too long"
    assert world.iron.peak_c > 150.0, "the iron is heating, so the target really reached it"


@pytest.mark.parametrize("commands", [1, 8])
def test_the_bus_stays_quiet_at_the_fastest_interval(commands):
    world = run(0.020, commands, seconds=2.0)
    frames = sum(len(times) for times in world.sent_at.values())
    # a frame lasts about 0.13 ms on the wire: even eight commands every 20 ms use a small part of the bus
    bus_load = frames * 0.00013 / world.now
    assert bus_load < 0.10


def test_the_single_thread_keeps_each_command_within_its_period_plus_the_frames_before_it():
    world = run(0.100, 8)
    for can_id in world.sent_at:
        assert longest_silence(world, can_id) <= 0.100 + 8 * FRAME_COST_S + 1e-9


@pytest.mark.parametrize("value", [201, 250, 300, 1000])
def test_the_settings_refuse_every_interval_the_watchdog_would_not_forgive(value):
    assert cfg.keepalive_settings({"keepalive": {"interval_ms": value}})["interval_ms"] is None
    assert value / 1000.0 >= WATCHDOG_S - 0.05


@pytest.mark.parametrize("period_s", [0.300, 0.500])
def test_control_a_period_above_the_watchdog_does_lose_the_target(period_s):
    world = run(period_s, 1, seconds=3.0)
    assert world.target_lost, "the control must show that the simulation can see a watchdog expire"
    assert longest_silence(world, HEATER_ID) >= WATCHDOG_S


def test_every_whole_interval_from_20_to_200_is_accepted_and_leaves_margin():
    low, high = cfg.KEEPALIVE_INTERVAL_BOUNDS_MS
    assert (low, high) == (20, 200)
    for value in range(low, high + 1):
        assert cfg.keepalive_settings({"keepalive": {"interval_ms": value}})["interval_ms"] == value
    # even the slowest accepted period leaves at least 50 ms of margin below the watchdog before any frame time
    assert WATCHDOG_S - high / 1000.0 >= 0.050 - 1e-9
