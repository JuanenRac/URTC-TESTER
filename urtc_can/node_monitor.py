# =============================================================================
# URTC-COMMON - src/urtc_common/node_monitor.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""What a bus monitor needs to follow several tool heads on one bus: whose a frame is, and how much of the bus each node uses.

A frame of the multinode extension carries its node in the identifier (``0x420 + node`` and the other node ranges, see ``docs/MULTINODE.md``), so a monitor can
attribute it with no state. A single-head frame has no address: it belongs to the node the host has selected, and only a monitor that knows the selection (it
reads the ``SELECTED`` flag of the status frames, or is told) can say which one; until then it is attributed to nobody. Nothing here sends a frame.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from . import protocol as p
from .multinode import frame_bits

HOST_KINDS = frozenset({"DISCOVER", "SELECT", "SAFE_STOP"})
NODE_TOKEN_PREFIXES = ("n", "N")


def owner(can_id: int) -> tuple[str, int | None]:
    """(kind, node) of an identifier: the name of the extension frame and its node address (``None`` for the three frames the host sends to every node), or
    ``("SINGLE", None)`` for every other identifier, which has no address of its own."""
    for base, count in p.MN_RANGES.items():
        if base <= can_id < base + count:
            kind = p.MN_NAMES[base]
            return (kind, None if kind in HOST_KINDS else can_id - base)
    return ("SINGLE", None)


def label(node: int | None) -> str:
    """The short text the rows of a monitor carry for a node: ``N07``, or empty for no node."""
    return "" if node is None else f"N{node:02d}"


def parse_nodes(text: str) -> set[int]:
    """The node addresses named in a filter text: tokens ``n5`` or ``N05`` (0 to 31), separated by spaces or commas. Anything else is ignored."""
    nodes: set[int] = set()
    for token in str(text).replace(",", " ").split():
        if token[:1] in NODE_TOKEN_PREFIXES and token[1:].isdigit() and 0 <= int(token[1:]) <= p.MN_ADDRESS_MASK:
            nodes.add(int(token[1:]))
    return nodes


@dataclass
class NodeUse:
    node: int
    frames: int = 0
    bits: int = 0
    last_seen: float = 0.0
    kinds: dict[str, int] | None = None


class NodeBusStats:
    """Frames and bus load per node over a sliding window. Every frame counts for the node that owns it (see ``owner``); a single-head frame counts for the selected
    node when one is known, else for nobody (``unattributed``)."""

    def __init__(self, window_s: float = 5.0, clock: Callable[[], float] = time.monotonic, worst_case: bool = False) -> None:
        self.window_s = window_s
        self._clock = clock
        self._worst_case = worst_case
        self._events: deque[tuple[float, int | None, str, int]] = deque()   # (time, node, kind, bits)
        self.selected: int | None = None
        self._lock = threading.Lock()

    def note(self, can_id: int, data: bytes | bytearray) -> int | None:
        """Count one frame; returns the node it was attributed to (``None`` when it belongs to nobody)."""
        kind, node = owner(can_id)
        if kind == "NODE_STATUS" and node is not None and len(data) >= 1 and data[0] & p.MN_STATE_SELECTED:
            self.selected = node
        elif kind == "NODE_STATUS" and node is not None and node == self.selected and len(data) >= 1:
            self.selected = None   # the node that was selected says it no longer is
        if kind == "SINGLE":
            node = self.selected
        now = self._clock()
        with self._lock:
            self._events.append((now, node, kind, frame_bits(len(data), self._worst_case)))
            self._trim(now)
        return node

    def _trim(self, now: float) -> None:
        while self._events and self._events[0][0] < now - self.window_s:
            self._events.popleft()

    def snapshot(self, bitrate_bps: int = 500_000) -> list[dict]:
        """One entry per node seen in the window, by node address, then the entry of the frames of nobody (``node`` None): frames per second, load in percent of the
        bus, and the count of each kind of frame."""
        now = self._clock()
        with self._lock:
            self._trim(now)
            events = list(self._events)
        use: dict[int | None, NodeUse] = {}
        for stamp, node, kind, bits in events:
            entry = use.setdefault(node, NodeUse(node if node is not None else -1, kinds={}))
            entry.frames += 1
            entry.bits += bits
            entry.last_seen = max(entry.last_seen, stamp)
            assert entry.kinds is not None
            entry.kinds[kind] = entry.kinds.get(kind, 0) + 1
        rows = []
        for node in sorted(use, key=lambda value: (value is None, value if value is not None else 0)):
            entry = use[node]
            rows.append({"node": node, "frames_per_s": entry.frames / self.window_s,
                         "load_percent": min(100.0, 100.0 * (entry.bits / self.window_s) / bitrate_bps) if bitrate_bps > 0 else 0.0,
                         "kinds": dict(sorted((entry.kinds or {}).items()))})
        return rows

    def summary_lines(self, bitrate_bps: int = 500_000) -> list[str]:
        """Text for a panel, with no word of a language in it: ``N07  12.4 fr/s  3.1 %  NODE_STATUS 5, SINGLE 40`` (the frames of nobody: ``--``)."""
        lines = []
        for row in self.snapshot(bitrate_bps):
            kinds = ", ".join(f"{name} {count}" for name, count in row["kinds"].items())
            lines.append(f"{label(row['node']) or '--':<4}{row['frames_per_s']:6.1f} fr/s {row['load_percent']:5.1f} %  {kinds}")
        return lines
