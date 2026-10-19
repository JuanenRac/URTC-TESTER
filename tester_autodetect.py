# =============================================================================
# URTC Tester - finding the bit rate of the bus behind an SLCAN adapter
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The bit-rate search used by the Qt Quick deck.  It talks to the adapter only through the factory it is given."""
from __future__ import annotations

import time

from tester_config import CAN_ID_ACTIVE_TOOL_RESP, CAN_ID_QUERY_ACTIVE_TOOL
from tester_transports import SLCANError

AUTODETECT_ORDER = ("500 kbit/s", "250 kbit/s", "125 kbit/s", "1 Mbit/s",
                    "100 kbit/s", "50 kbit/s", "20 kbit/s", "10 kbit/s", "800 kbit/s")


def scan_bitrates(port, slcan_factory, bitrates, log=None, on_try=None, on_traffic=None,
                  on_active_phase=None, listen_window=0.3, answer_window=0.8, pause=0.1):
    """Find the bit rate of the bus behind an SLCAN adapter.

    Phase 1 only listens: the channel is opened listen-only at each
    candidate, so nothing is transmitted and a wrong rate cannot disturb the
    other nodes of a live bus. The first rate at which a valid frame is seen
    is then confirmed by asking for the active tool.
    Phase 2 runs only when no rate showed any traffic (an idle bus): it
    transmits a query at each rate, which is the only way left to find a
    board that is silent until asked.
    Returns the label of the rate found or None.
    """
    codes = dict(bitrates)
    order = [label for label in AUTODETECT_ORDER if label in codes]

    def attempt(label, listen_only):
        trial = None
        try:
            trial = slcan_factory(port, log=lambda m: None)
            trial.open_channel(codes[label], listen_only=listen_only)
            if listen_only:
                seen = 0
                deadline = time.monotonic() + listen_window
                while time.monotonic() < deadline:
                    if trial.read_frame(timeout=0.05) is not None:
                        seen += 1
                return seen
            trial.send_frame(CAN_ID_QUERY_ACTIVE_TOOL, b"")
            deadline = time.monotonic() + answer_window
            while time.monotonic() < deadline:
                frame = trial.read_frame(timeout=0.2)
                if frame is not None and frame[0] == CAN_ID_ACTIVE_TOOL_RESP:
                    return True
            return False
        except (SLCANError, OSError):
            return 0 if listen_only else False
        finally:
            if trial is not None:
                try:
                    trial.close()
                except Exception:
                    pass
            time.sleep(pause)  # lets Windows serial drivers release the port

    traffic_seen = False
    for label in order:
        if on_try:
            on_try(label)
        seen = attempt(label, True)
        if seen:
            traffic_seen = True
            if on_traffic:
                on_traffic(label, seen)
            if attempt(label, False):
                return label
    if traffic_seen:
        return None  # a bus is alive but nothing answered: do not transmit blind
    if on_active_phase:
        on_active_phase()
    for label in order:
        if on_try:
            on_try(label)
        if attempt(label, False):
            return label
    return None
