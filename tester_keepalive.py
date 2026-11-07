# =============================================================================
# URTC Tester - repeated commands (keepalive) on one I/O thread
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""One thread that repeats every command the firmware drops again if it is not refreshed (a heater, a drill, a laser, a fan).

By default the deck starts one thread per repeated command. With ``keepalive.single_io_thread`` set to true in ``config.json`` all of them share this scheduler
instead: one thread, one frame sent at a time, so two repeated commands can never talk on the transport at the same moment. The scheduler holds no clock of its own
beyond the two callables it is given, so the order and the timing are tested without a thread (``tick``) or with one (``start``).
"""
from __future__ import annotations

import threading
import time
from typing import Callable

Frame = tuple[int, bytes]


class KeepaliveScheduler:
    """Repeats registered frames, each at its own period, from a single worker thread."""

    def __init__(self, send: Callable[[int, bytes], None], clock: Callable[[], float] = time.monotonic,
                 log: Callable[[str], None] | None = None, on_failure: Callable[[str], None] | None = None) -> None:
        self._send = send
        self._on_failure = on_failure or (lambda key: None)
        self._clock = clock
        self._log = log or (lambda message: None)
        self._items: dict[str, list] = {}      # key -> [frame, period, next due]
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.sent = 0

    # -- the registry -------------------------------------------------------------------------------------------------------------
    def register(self, key: str, frame: Frame, period_s: float) -> None:
        """Start (or replace) the repetition of ``frame`` every ``period_s`` seconds; the first frame goes out on the next tick."""
        if not period_s > 0:
            raise ValueError("the period of a repeated command must be positive")
        with self._lock:
            self._items[key] = [(int(frame[0]), bytes(frame[1])), float(period_s), self._clock()]
        self._wake.set()

    def cancel(self, key: str) -> bool:
        """Stop repeating ``key``; True when it was being repeated."""
        with self._lock:
            return self._items.pop(key, None) is not None

    def cancel_all(self) -> None:
        with self._lock:
            self._items.clear()

    def keys(self) -> list[str]:
        with self._lock:
            return sorted(self._items)

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)

    # -- the work -----------------------------------------------------------------------------------------------------------------
    def tick(self) -> float:
        """Send every frame that is due, one after the other, and return how many seconds until the next one is (0.5 when nothing is registered).

        A frame that cannot be sent removes only its own key and is logged; the others keep being repeated.
        """
        with self._lock:
            now = self._clock()
            due = [(key, item) for key, item in self._items.items() if now >= item[2]]
        for key, item in due:
            try:
                self._send(*item[0])
            except Exception as exc:  # the transport went away or refused: this command stops, the rest go on
                self._log(f"KEEPALIVE_FAILED key={key} error={exc}")
                self.cancel(key)
                self._on_failure(key)
                continue
            self.sent += 1
            with self._lock:
                if self._items.get(key) is item:
                    item[2] = now + item[1]
        with self._lock:
            if not self._items:
                return 0.5
            return max(0.0, min(item[2] for item in self._items.values()) - self._clock())

    def start(self) -> None:
        """Run ``tick`` from one daemon thread until ``close``."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()

        def _loop() -> None:
            while not self._stop.is_set():
                wait = self.tick()
                self._wake.wait(min(wait, 0.5))
                self._wake.clear()

        self._thread = threading.Thread(target=_loop, daemon=True, name="urtc-tester-keepalive")
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        self._wake.set()
        self.cancel_all()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        self._thread = None
