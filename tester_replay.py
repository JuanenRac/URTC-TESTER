# =============================================================================
# URTC Tester - tester_replay.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Replay of a recorded bus trace (PCAN-View ``.trc`` or Vector ``.asc``) into the deck, with no board and no adapter.

Only the frames that were *received* are played: a line marked as transmitted is what the recording tool itself sent and never arrived
from the bus. The player has no timer and no window: the caller passes the clock (``advance(now_ms)``), so the timing rules are tested
directly. A replay never transmits and never answers a request; the deck keeps its frames apart from what a connected board says and
does not export them as if the board had said them. Same rules as the web studio (``traceReplay.ts``): speeds from 0.25x to 10x, a
silence longer than ``MAX_GAP_MS`` is shortened, a looping trace waits ``LOOP_PAUSE_MS`` before it starts again.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tester_simulator import _ASC_ROW, _TRC_ROW

SPEEDS = (0.25, 0.5, 1.0, 2.0, 5.0, 10.0)
MAX_GAP_MS = 2000.0
LOOP_PAUSE_MS = 250.0
MAX_TRACE_FRAMES = 200_000
MAX_TRACE_BYTES = 50 * 1024 * 1024
MAX_ID = 0x1FFFFFFF
MAX_PER_ADVANCE = 500  # a stalled window does not release the whole trace at once

IDLE, PLAYING, PAUSED, FINISHED = "idle", "playing", "paused", "finished"


class ReplayError(Exception):
    """A trace that cannot be played. ``code`` is stable (``too_big``, ``empty``, ``unreadable``) so the deck says it in the language of the person."""

    def __init__(self, code: str, text: str = "") -> None:
        super().__init__(text or code)
        self.code = code


@dataclass(frozen=True)
class Entry:
    time_ms: float  # after the first frame of the trace
    can_id: int
    data: bytes


@dataclass(frozen=True)
class ParsedTrace:
    format: str  # "trc", "asc" or "unknown"
    entries: tuple[Entry, ...]
    rejected: int  # lines that looked like frames but were refused (a length that does not match, more than 8 bytes, an identifier out of range)


def parse_trace(text: str) -> ParsedTrace:
    """The received frames of a ``.trc`` or ``.asc`` trace in time order. Lines that are not frames (headers, comments, events) are skipped."""
    raw: list[tuple[float, int, bytes]] = []
    fmt = "unknown"
    rejected = 0
    for line in text.splitlines():
        if line.startswith(";"):
            continue
        match = _TRC_ROW.match(line)
        if match:
            fmt = "trc" if fmt == "unknown" else fmt
            time_ms, direction, ident, dlc, data = float(match.group(1)), match.group(2), match.group(3), match.group(4), match.group(5)
        else:
            match = _ASC_ROW.match(line)
            if not match:
                continue
            fmt = "asc" if fmt == "unknown" else fmt
            time_ms, ident, direction, dlc, data = float(match.group(1)) * 1000.0, match.group(2), match.group(3), match.group(4), match.group(5)
        if direction != "Rx":
            continue
        compact = data.replace(" ", "")
        try:
            payload = bytes.fromhex(compact)
            can_id = int(ident, 16)
        except ValueError:
            rejected += 1
            continue
        if len(payload) != int(dlc) or int(dlc) > 8 or can_id > MAX_ID:
            rejected += 1
            continue
        if len(raw) >= MAX_TRACE_FRAMES:
            rejected += 1
            continue
        raw.append((time_ms, can_id, payload))
    raw.sort(key=lambda item: item[0])
    origin = raw[0][0] if raw else 0.0
    return ParsedTrace(fmt, tuple(Entry(t - origin, i, d) for t, i, d in raw), rejected)


def load_trace(path: str | Path) -> ParsedTrace:
    """Reads a trace file. ``ReplayError`` for a file that is too big, unreadable or holds no frame that can be replayed."""
    target = Path(path)
    try:
        if target.stat().st_size > MAX_TRACE_BYTES:
            raise ReplayError("too_big", f"{target.name} is larger than {MAX_TRACE_BYTES // (1024 * 1024)} MB")
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        raise ReplayError("unreadable", str(error)) from error
    parsed = parse_trace(text)
    if not parsed.entries:
        raise ReplayError("empty", f"{target.name} holds no received frames")
    return parsed


def checked_speed(speed: float) -> float:
    try:
        value = float(speed)
    except (TypeError, ValueError):
        return 1.0
    if value != value or value <= 0:
        return 1.0
    return min(value, 100.0)


class TracePlayer:
    """Hands the frames of a trace out in order, keeping the gaps between them (divided by the speed, long silences shortened)."""

    def __init__(self, entries: tuple[Entry, ...] | list[Entry], speed: float = 1.0, loop: bool = False) -> None:
        self.entries = tuple(entries)
        self.speed = checked_speed(speed)
        self.loop = bool(loop)
        self.state = IDLE
        self.index = 0
        self._due = 0.0
        self._remaining = 0.0

    @property
    def played(self) -> int:
        return self.index

    @property
    def total(self) -> int:
        return len(self.entries)

    @property
    def progress(self) -> float:
        return self.index / len(self.entries) if self.entries else 0.0

    def _gap_before(self, index: int) -> float:
        if index == 0:
            return 0.0
        gap = self.entries[index].time_ms - self.entries[index - 1].time_ms
        return min(MAX_GAP_MS, max(0.0, gap)) / self.speed

    def start(self, now_ms: float) -> None:
        """From the first frame, or on after a pause."""
        if not self.entries or self.state == PLAYING:
            return
        if self.state == PAUSED:
            self._due = now_ms + self._remaining
        else:
            self.index = 0
            self._due = now_ms
        self.state = PLAYING

    def pause(self, now_ms: float) -> None:
        if self.state != PLAYING:
            return
        self._remaining = max(0.0, self._due - now_ms)
        self.state = PAUSED

    def stop(self) -> None:
        """Back to the first frame."""
        self.state = IDLE
        self.index = 0

    def advance(self, now_ms: float) -> list[Entry]:
        """The frames that are due at ``now_ms`` (none while paused, stopped or finished)."""
        out: list[Entry] = []
        while self.state == PLAYING and len(out) < MAX_PER_ADVANCE and now_ms >= self._due:
            if self.index >= len(self.entries):
                if self.loop:
                    self.index = 0
                    self._due += LOOP_PAUSE_MS
                    continue
                self.state = FINISHED
                break
            out.append(self.entries[self.index])
            self.index += 1
            if self.index >= len(self.entries):
                if self.loop:
                    self._due += LOOP_PAUSE_MS
                    self.index = 0
                else:
                    self.state = FINISHED
            else:
                self._due += self._gap_before(self.index)
        return out
