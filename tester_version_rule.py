# =============================================================================
# URTC-TESTER - tester_version_rule.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""``version-rule``: read how a main bootloader reads an image without a patch number, and send it a signed command that was made elsewhere.

Used only when the command is asked for. A bootloader built without the feature (the default of the firmware) answers nothing, and that is what this reports.
The tester never signs and never holds a key: the 84-byte command comes from a file. The head must already be in its bootloader.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from urtc_can import version_compat as vc

ANSWER_TIMEOUT_S = 3.0      # the bootloader verifies a signature and writes a flash page before it answers a command
MODE_TEXT = {vc.MODE_STRICT: "strict (an image without a patch counts as patch 0)", vc.MODE_ACCEPT_PATCHLESS: "accept an image without a patch"}
NO_ANSWER = ("No answer: the head is not in its bootloader, the command is for another head, or its bootloader does not have the stored version rule "
             "(it is off in the released builds).")


def read_command(path: str | Path) -> bytes:
    """The 84 bytes of a signed command file; ``ValueError`` when the file is not one."""
    data = Path(path).read_bytes()
    if len(data) != vc.COMMAND_SIZE:
        raise ValueError(f"{Path(path).name}: a signed command is {vc.COMMAND_SIZE} bytes, this file has {len(data)}")
    return data


def exchange(transport, frames: list[bytes], timeout: float = ANSWER_TIMEOUT_S, clock: Callable[[], float] = time.monotonic) -> vc.Answer | None:
    """Sends the frames on 0x7EE and returns the first answer of this kind on 0x7EF, or None."""
    for frame in frames:
        transport.send_frame(vc.ID_COMMAND, frame)
    deadline = clock() + timeout
    while clock() < deadline:
        got = transport.read_frame(0.05)
        if got is None or got[0] != vc.ID_RESULT:
            continue
        answer = vc.parse_answer(bytes(got[1]))
        if answer is not None:
            return answer
    return None


def query(transport, **kw) -> vc.Answer | None:
    return exchange(transport, [vc.query_frame()], **kw)


def send(transport, command: bytes, **kw) -> vc.Answer | None:
    return exchange(transport, vc.chunks(command), **kw)


def describe(answer: vc.Answer) -> dict:
    return {"status": vc.STATUS_NAMES[answer.status], "mode": "accept_patchless" if answer.mode == vc.MODE_ACCEPT_PATCHLESS else "strict",
            "stored": answer.stored, "counter": answer.counter}


def text(answer: vc.Answer) -> str:
    where = f"stored in the head (counter {answer.counter})" if answer.stored else "nothing stored, the rule of the build"
    return f"Status: {vc.STATUS_NAMES[answer.status]}\nRule in force: {MODE_TEXT[answer.mode]}\n{where}"
