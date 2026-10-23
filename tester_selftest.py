# =============================================================================
# URTC Tester - the self-test, shared by the Qt Quick deck and the original window
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The safe, at-rest communication check of the detected tool.

Nothing here knows about a window.  ``run_self_test`` asks the caller for one primitive, ``exchange(send, expect_id,
timeout)``: put the frame ``send`` (a ``(can_id, data)`` pair, or None) on the bus and return the data of the first
frame with ``expect_id`` that arrives within ``timeout`` seconds, or None.  The caller decides how the bus is read
(the original window has a reader thread of its own, the Qt deck holds the transport lock) and what it shows.

Every command is a safe, at-rest value (setpoint 0, speed 0, power 0): this verifies that the round trip works, not
that an actuator really moves, because confirming that needs a person watching.  Tools with no telemetry (plain
motion) or that only speak on a physical event (the scan probe) get an information line instead of a pass or fail.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Callable

from tester_config import (
    CAN_ID_3DP_HOTEND_TELEM, CAN_ID_3DP_THERMAL_MOTION, CAN_ID_ACTIVE_TOOL_RESP, CAN_ID_AOI_TELEMETRY,
    CAN_ID_DRILL_CMD, CAN_ID_DRILL_TELEMETRY, CAN_ID_LASER_CMD, CAN_ID_LASER_TELEMETRY, CAN_ID_QUERY_ACTIVE_TOOL,
    CAN_ID_QUERY_VERSION, CAN_ID_SOLDER_SETPOINT, CAN_ID_SOLDER_TELEMETRY, CAN_ID_VACUUM_TELEMETRY,
    CAN_ID_VERSION_RESPONSE, MOTION_TOOL_IDS, TOOL_NAMES, _,
)

PASS = "PASS"
FAIL = "FAIL"
INFO = "INFO"

# tool id -> steps of (translation key of the description, command id or None, command data, expected telemetry id or None)
SELF_TEST_STEPS: dict[int, list[tuple[str, int | None, bytes | None, int | None]]] = {
    0: [("SELFTEST_STEP_SOLDER", CAN_ID_SOLDER_SETPOINT, struct.pack(">H", 0), CAN_ID_SOLDER_TELEMETRY)],
    5: [("SELFTEST_STEP_DRILL", CAN_ID_DRILL_CMD, bytes([0, 0]), CAN_ID_DRILL_TELEMETRY)],
    9: [("SELFTEST_STEP_LASER", CAN_ID_LASER_CMD, bytes([0, 0]), CAN_ID_LASER_TELEMETRY)],
    10: [("SELFTEST_STEP_PRINTER", CAN_ID_3DP_THERMAL_MOTION, struct.pack(">H", 0) + bytes([0, 0, 0, 0]), CAN_ID_3DP_HOTEND_TELEM)],
    8: [("SELFTEST_STEP_AOI", None, None, CAN_ID_AOI_TELEMETRY)],
    4: [("SELFTEST_STEP_VACUUM", None, None, CAN_ID_VACUUM_TELEMETRY)],
    11: [("SELFTEST_STEP_SCAN_PROBE", None, None, None)],
}

Exchange = Callable[[tuple[int, bytes] | None, int, float], "bytes | None"]


@dataclass
class SelfTestLine:
    status: str  # PASS, FAIL or INFO
    text: str    # already in the interface language

    def __str__(self) -> str:
        return f"[{self.status}] {self.text}"


@dataclass
class SelfTestResult:
    tool_id: int
    lines: list[SelfTestLine] = field(default_factory=list)
    sent_drill_command: bool = False  # the original window must forget the drill speed it believes is set

    @property
    def failed(self) -> int:
        return sum(1 for line in self.lines if line.status == FAIL)


def steps_for(tool_id: int) -> list[tuple[str, int | None, bytes | None, int | None]]:
    return SELF_TEST_STEPS.get(tool_id, [])


def commands_sent(tool_id: int) -> list[int]:
    """The CAN identifiers the self-test of this tool transmits (the two generic queries and any step command)."""
    ids = [CAN_ID_QUERY_ACTIVE_TOOL, CAN_ID_QUERY_VERSION]
    if tool_id not in MOTION_TOOL_IDS:
        ids += [step[1] for step in steps_for(tool_id) if step[1] is not None]
    return ids


def run_self_test(
    tool_id: int,
    exchange: Exchange,
    emit: Callable[[SelfTestLine], None] | None = None,
    stop: Callable[[], bool] = lambda: False,
    timeout: float = 1.5,
) -> SelfTestResult:
    """Run the checks of ``tool_id`` and return every line; ``emit`` also gets each line as soon as it is known."""
    result = SelfTestResult(tool_id)

    def add(status: str, text: str) -> None:
        line = SelfTestLine(status, text)
        result.lines.append(line)
        if emit is not None:
            emit(line)

    add(INFO, _("LOG_SELFTEST_TESTING", tool=TOOL_NAMES.get(tool_id, "?")))
    # Generic checks first: meaningful for every tool.
    response = exchange((CAN_ID_QUERY_ACTIVE_TOOL, b""), CAN_ID_ACTIVE_TOOL_RESP, timeout)
    add(PASS if response is not None and len(response) >= 1 and response[0] == tool_id else FAIL, _("LOG_SELFTEST_ACTIVE_TOOL"))
    if stop():
        return result
    response = exchange((CAN_ID_QUERY_VERSION, b"\x00"), CAN_ID_VERSION_RESPONSE, timeout)
    add(PASS if response is not None else FAIL, _("LOG_SELFTEST_VERSION"))

    if tool_id in MOTION_TOOL_IDS:
        add(INFO, _("SELFTEST_MOTION_INFO"))
    elif steps_for(tool_id):
        for key, command_id, command_data, expect_id in steps_for(tool_id):
            if stop():
                return result
            description = _(key)
            if expect_id is None:
                add(INFO, description)
                continue
            send = (command_id, command_data) if command_id is not None else None
            response = exchange(send, expect_id, timeout)
            if command_id == CAN_ID_DRILL_CMD:
                result.sent_drill_command = True
            add(PASS if response is not None else FAIL, description)
    else:
        add(INFO, _("SELFTEST_NO_STEPS"))
    add(INFO, _("SELFTEST_DONE"))
    return result
