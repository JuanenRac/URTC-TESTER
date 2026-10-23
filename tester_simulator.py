# =============================================================================
# URTC-TESTER - tester_simulator.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A simulated tool head and a trace player, with the same interface as the real CAN transports.

``SimulatedBoard`` answers what a running application answers at rest: the active-tool query (0x110 -> 0x111), the
version query (0x7F8 -> 0x7F9 and the patch frame 0x7E9) and the telemetry of the tool it plays, which it also sends
by itself the way the firmware does. The few commands that change something (the soldering iron and printer
set-points, the drill speed, the laser power) are kept in ``outputs`` and move the simulated temperature or speed, so
a test plan can be tried before it meets a board. It can also play a fault (``fault``) to see how a plan reacts.

It is a second reading of the protocol by the same author as the tester: it shows that a plan and the tester agree
with each other, not that a board behaves this way. Nothing here is a reason to believe a real board passes.

``ReplayCAN`` plays back a bus trace saved by the bus monitor (``.trc`` or ``.asc``): the frames it holds are read in
order, what is sent to it is only recorded. It lets a plan or a reader be run against a recorded session.
"""
from __future__ import annotations

import re
import struct
import time
from collections.abc import Callable
from pathlib import Path

from tester_config import TOOL_NAMES
from urtc_can import protocol as wire

Frame = tuple[int, bytes]

CAN_ID_PID_STATE = wire.CAN_ID_PID_STATE_RESP
FAULTS = (None, "system", "can", "thermal")
WATCHDOG_S = 0.25  # an order for a heater, a drill or a laser is dropped again when it is not refreshed within this time
WATCHED = {  # command identifier -> the output it sets
    wire.CAN_ID_SOLDER_SETPOINT: "solder_setpoint_c", wire.CAN_ID_PRINTER_THERMAL_MOTION: "nozzle_setpoint_c",
    wire.CAN_ID_DRILL_CMD: "drill_speed", wire.CAN_ID_LASER_CMD: "laser_power",
}
AMBIENT_C = 25.0
HEAT_STEP_C = 40.0  # degrees the simulated tip or nozzle gains per telemetry frame
SIMULATED_FIRMWARE = (0, 4, 0)  # major, minor, patch of the application it pretends to run


class SimulatedBoard:
    """A tool head that answers like a running application."""

    def __init__(self, tool_id: int = 0, firmware: tuple[int, int, int | None] = SIMULATED_FIRMWARE, fault: str | None = None,
                 delay: float = 0.0, silent: bool = False, clock: Callable[[], float] = time.monotonic, watchdog_s: float | None = WATCHDOG_S) -> None:
        if fault not in FAULTS:
            raise ValueError(f"fault must be one of {FAULTS}")
        self.tool_id = tool_id
        self.firmware = firmware
        self.fault = fault
        self.delay = delay
        self.silent = silent  # a board that answers nothing (to see a plan fail the way a missing board does)
        self.clock = clock
        self.watchdog_s = watchdog_s  # None: the orders are kept for ever
        self._ordered_at: dict[int, float] = {}
        self.sent: list[Frame] = []
        self.outputs: dict[str, int] = {}
        self.temperature = AMBIENT_C
        self.pid = {"kp": 800, "ki": 20, "kd": 150, "state": 1}  # the gains times 100 and the 0x1BA state, as the heater PID reports them
        self._tune_frames = 0
        self._queue: list[Frame] = []
        self.opened = False

    # -- the interface of the real transports ---------------------------------------------------------------------------
    def open_channel(self, bitrate_code: str | None = None, listen_only: bool = False) -> None:
        self.opened = True
        self.listen_only = listen_only

    def close_channel(self) -> None:
        self.opened = False

    def close(self) -> None:
        self.opened = False

    def send_frame(self, can_id: int, data: bytes = b"") -> None:
        data = bytes(data)
        self.sent.append((can_id, data))
        self._apply_watchdog()
        if can_id in WATCHED:
            self._ordered_at[can_id] = self.clock()
        if self.silent:
            return
        if can_id == wire.CAN_ID_QUERY_ACTIVE_TOOL:
            self._queue.append(self._active_tool_answer())
        elif can_id == wire.CAN_ID_QUERY_VERSION:
            major, minor, patch = self.firmware
            self._queue.append((wire.CAN_ID_VERSION_RESPONSE, bytes([wire.RESPONDER_APPLICATION]) + struct.pack(">I", wire.HARDWARE_ID_MAIN)
                                + struct.pack(">H", major) + bytes([minor])))
            if patch is not None:
                self._queue.append((wire.CAN_ID_VERSION_PATCH_RESPONSE, bytes([wire.RESPONDER_APPLICATION, patch, 0])))
        elif can_id == wire.CAN_ID_PID_CONFIG and len(data) == 7:
            self._pid_order(data)
        elif can_id == CAN_ID_PID_STATE:
            self._queue.append(self._pid_answer())
        elif can_id == wire.CAN_ID_SOLDER_SETPOINT and self.tool_id == 0 and len(data) == 2:
            self.outputs["solder_setpoint_c"] = int.from_bytes(data, "big")
            self._queue.append(self._telemetry())
        elif can_id == wire.CAN_ID_PRINTER_THERMAL_MOTION and self.tool_id == 10 and len(data) == 6:
            self.outputs["nozzle_setpoint_c"] = int.from_bytes(data[:2], "big")
            self._queue.append(self._telemetry())
        elif can_id == wire.CAN_ID_DRILL_CMD and self.tool_id == 5 and len(data) == 2:
            self.outputs["drill_speed"] = data[0]
            self._queue.append(self._telemetry())
        elif can_id == wire.CAN_ID_LASER_CMD and self.tool_id == 9 and len(data) == 2:
            self.outputs["laser_power"] = data[0] if data[1] == 1 else 0  # locked: no power
            self._queue.append(self._telemetry())

    def _apply_watchdog(self) -> None:
        """Drop the orders that were not refreshed in time, like the firmware: the output falls back to off."""
        if self.watchdog_s is None:
            return
        now = self.clock()
        for can_id, when in list(self._ordered_at.items()):
            if now - when > self.watchdog_s:
                self.outputs[WATCHED[can_id]] = 0
                del self._ordered_at[can_id]

    def read_frame(self, timeout: float = 0.05) -> Frame | None:
        self._apply_watchdog()
        if self.delay:
            time.sleep(self.delay)
        if self._queue:
            return self._queue.pop(0)
        if self.silent:
            return None
        if self.pid["state"] == 2:  # an autotune takes a few control cycles
            self._tune_frames += 1
            if self._tune_frames >= 5:
                self.pid.update(kp=1250, ki=45, kd=310, state=3)
        return self._telemetry()  # like the firmware, the tool reports by itself

    def _pid_order(self, data: bytes) -> None:
        kp, ki, kd, action = struct.unpack(">HHHB", data)
        if action == 0 and max(kp, ki, kd) <= 60000:
            self.pid.update(kp=kp, ki=ki, kd=kd, state=1)
        elif action == 1 and self.tool_id == 0 and self.outputs.get("solder_setpoint_c", 0) >= 100:
            self.pid["state"], self._tune_frames = 2, 0
        elif action == 2 and self.pid["state"] == 2:
            self.pid["state"] = 1
        self._queue.append(self._pid_answer())

    def _pid_answer(self) -> Frame:
        duty = 37 if self.pid["state"] in (1, 2) and self._target_c() else 0
        return CAN_ID_PID_STATE, struct.pack(">HHHBB", self.pid["kp"], self.pid["ki"], self.pid["kd"], self.pid["state"], duty)

    # -- what the board says --------------------------------------------------------------------------------------------
    def _active_tool_answer(self) -> Frame:
        system = 1 if self.fault in ("system", "thermal") else 0
        can_error = 1 if self.fault == "can" else 0
        thermal = 2 if self.fault == "thermal" else 0
        return wire.encode_active_tool_resp(self.tool_id, system, can_error, 0, thermal, 0)

    def _target_c(self) -> float:
        return float(self.outputs.get("solder_setpoint_c", self.outputs.get("nozzle_setpoint_c", 0)))

    def _telemetry(self) -> Frame:
        """The telemetry frame of the tool it plays, moving the simulated temperature a step toward its set-point."""
        target = max(self._target_c(), AMBIENT_C)
        if self.temperature < target:
            self.temperature = min(target, self.temperature + HEAT_STEP_C)
        elif self.temperature > target:
            self.temperature = max(target, self.temperature - HEAT_STEP_C)
        degrees = int(round(self.temperature))
        if self.tool_id == 0:
            return wire.encode_solder_telemetry(degrees)
        if self.tool_id == 10:
            return wire.encode_printer_hotend_telemetry(degrees)
        if self.tool_id == 5:
            return wire.encode_drill_telemetry(self.outputs.get("drill_speed", 0) * 50, 0)
        if self.tool_id == 4:
            return wire.encode_vacuum_telemetry(100, 0)
        if self.tool_id == 8:
            return wire.encode_aoi_telemetry(0)
        if self.tool_id == 9:
            return wire.encode_laser_telemetry(0)
        return self._active_tool_answer()  # a tool with no telemetry of its own: the quick state stands in for it


# =============================================================================
# trace player
# =============================================================================
_TRC_ROW = re.compile(r"^\s*\d+\)\s+([0-9.]+)\s+(Rx|Tx)\s+([0-9A-Fa-f]+)\s+(\d+)\s*([0-9A-Fa-f ]*)$")
_ASC_ROW = re.compile(r"^\s*([0-9.]+)\s+\d+\s+([0-9A-Fa-f]+)\s+(Rx|Tx)\s+d\s+(\d+)\s*([0-9A-Fa-f ]*)$")


def parse_trace(text: str) -> list[tuple[float, int, bytes]]:
    """The frames of a ``.trc`` or ``.asc`` trace as (offset in seconds, identifier, data); lines that are not frames are skipped."""
    frames: list[tuple[float, int, bytes]] = []
    for line in text.splitlines():
        if line.startswith(";"):
            continue
        m = _TRC_ROW.match(line)
        if m:
            if m.group(2) != "Rx":
                continue  # what the monitor itself transmitted did not arrive from the bus
            offset, ident, dlc, data = float(m.group(1)) / 1000.0, m.group(3), int(m.group(4)), m.group(5)
        else:
            m = _ASC_ROW.match(line)
            if not m or m.group(3) != "Rx":
                continue
            offset, ident, dlc, data = float(m.group(1)), m.group(2), int(m.group(4)), m.group(5)
        raw = bytes.fromhex(data.replace(" ", ""))
        if len(raw) != dlc or dlc > 8:
            continue
        frames.append((offset, int(ident, 16), raw))
    return frames


class ReplayCAN:
    """Plays the frames of a recorded trace, in order, as if they were arriving from the bus.

    ``realtime`` waits for the gap between frames (up to ``max_wait``), otherwise they come as fast as they are read.
    What is sent to it is kept in ``sent`` and answers nothing.
    """

    def __init__(self, path: str | Path, realtime: bool = False, max_wait: float = 1.0) -> None:
        self.path = Path(path)
        self.frames = parse_trace(self.path.read_text(encoding="utf-8", errors="replace"))
        if not self.frames:
            raise ValueError(f"{self.path} holds no frames that can be read")
        self.realtime = realtime
        self.max_wait = max_wait
        self.sent: list[Frame] = []
        self._index = 0

    def open_channel(self, bitrate_code: str | None = None, listen_only: bool = False) -> None:
        self._index = 0

    def close_channel(self) -> None:
        return None

    def close(self) -> None:
        return None

    def send_frame(self, can_id: int, data: bytes = b"") -> None:
        self.sent.append((can_id, bytes(data)))

    def read_frame(self, timeout: float = 0.05) -> Frame | None:
        if self._index >= len(self.frames):
            return None
        offset, can_id, data = self.frames[self._index]
        if self.realtime and self._index:
            time.sleep(min(self.max_wait, max(0.0, offset - self.frames[self._index - 1][0])))
        self._index += 1
        return can_id, data

    @property
    def finished(self) -> bool:
        return self._index >= len(self.frames)


def make_board(tool_id: int = 0, **options) -> SimulatedBoard:
    """A simulated board for a tool of the catalogue; an identifier the catalogue does not have is refused."""
    if tool_id not in TOOL_NAMES:
        raise ValueError(f"unknown tool id {tool_id}")
    return SimulatedBoard(tool_id, **options)
