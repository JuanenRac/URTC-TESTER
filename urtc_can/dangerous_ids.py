# =============================================================================
# URTC-COMMON - src/urtc_common/dangerous_ids.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Which identifiers change what a board is, taken from the protocol specification.

A host can send an identifier that erases the saved state, puts a board in its bootloader, updates the expansion slave or rewrites a setting that is kept after a
restart. The gateway refuses them unless the operator unlocks them, and a test plan asks before it sends one. Both use this one rule, so the answer is the same.

The rule reads the table of messages of the specification (the ``MESSAGES`` of the protocol module): it needs nothing else, so a program that carries a copy of the
protocol table can carry a copy of this file with it.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

LOCKED_GROUPS = frozenset({"bootloader", "slave_bridge"})
PERSISTENT_NAMES = frozenset({"PID_CONFIG"})


def dangerous_reason(can_id: int, messages: Mapping[int, Mapping[str, Any]]) -> str | None:
    """Why an identifier is dangerous to send, or None when it is not (or when the specification does not know it)."""
    info = messages.get(can_id)
    if info is None:
        return None
    if info.get("gates", {}).get("needs_magic"):
        return "it needs a magic payload: it erases, resets or rewrites something that stays"
    if info["name"].startswith("QUERY_"):
        return None   # a question changes nothing, whatever group it is in (the version query, the error counters)
    if info["group"] in LOCKED_GROUPS:
        return "it belongs to the bootloader or to the update of the expansion slave"
    if info["name"].startswith("SET_") or info["name"] in PERSISTENT_NAMES:
        return "it changes a setting that is kept after a restart"
    return None
