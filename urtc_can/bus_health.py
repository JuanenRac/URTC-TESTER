# =============================================================================
# URTC-COMMON - src/urtc_common/bus_health.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Is the bus of the tool heads healthy, or does it mix speeds? Decided from the symptoms, with no change of the protocol.

A head at another speed than the bus cannot be heard, so it cannot state its speed. What can be seen is what it does to the bus: the error counters of the heads
that ARE heard rise (the health frame 0x1B8 carries ``tec``, ``rec`` and ``bus_off_count``), a search at every speed finds no head, or a head known to have been built for
the legacy speed (500 kbit/s) is on a bus of 1 Mbit/s. This module turns those facts into warning codes; the tools show them in their own words. The thresholds come from
the configuration file of each tool (section ``bus_health``). Standard library only.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

# warning codes, from the most to the least serious
MIXED_BUS_SUSPECTED = "mixed_bus_suspected"      # the heads that are heard show errors and a head of the other speed is known to be there
NO_HEAD_AT_ANY_SPEED = "no_head_at_any_speed"    # a search at every speed found nobody: wiring, power, termination, or a head at a speed that was not tried
BUS_ERRORS = "bus_errors"                        # error counters or bus-off of the heads that are heard: cabling, termination or a speed that does not fit
LEGACY_HEAD_KNOWN = "legacy_head_known"          # a head built for 500 kbit/s is known to be on this bus: it needs the legacy build of every board or its own bus
CODES = (MIXED_BUS_SUSPECTED, NO_HEAD_AT_ANY_SPEED, BUS_ERRORS, LEGACY_HEAD_KNOWN)

TEC_WARN_DEFAULT = 96       # the CAN controller goes error-passive at 128
REC_WARN_DEFAULT = 96
BUS_OFF_WARN_DEFAULT = 1
LIMITS = (1, 255)


@dataclass(frozen=True)
class Thresholds:
    tec_warn: int = TEC_WARN_DEFAULT
    rec_warn: int = REC_WARN_DEFAULT
    bus_off_warn: int = BUS_OFF_WARN_DEFAULT
    legacy_heads: tuple[str, ...] = ()          # names or serial numbers of heads known to be built for the legacy speed


def _whole(value: Any, default: int) -> int:
    ok = isinstance(value, int) and not isinstance(value, bool) and LIMITS[0] <= value <= LIMITS[1]
    return value if ok else default


def thresholds_from_config(section: Any) -> Thresholds:
    """The thresholds from the ``bus_health`` section of a configuration file; a value that is not a whole number inside the limits keeps its default."""
    if not isinstance(section, Mapping):
        return Thresholds()
    heads = section.get("legacy_heads")
    names = tuple(str(item) for item in heads if isinstance(item, (str, int)) and not isinstance(item, bool)) if isinstance(heads, list) else ()
    return Thresholds(_whole(section.get("tec_warn"), TEC_WARN_DEFAULT), _whole(section.get("rec_warn"), REC_WARN_DEFAULT),
                      _whole(section.get("bus_off_warn"), BUS_OFF_WARN_DEFAULT), names)


def is_legacy_head(name: str | int | None, thresholds: Thresholds) -> bool:
    return name is not None and str(name) in thresholds.legacy_heads


def warnings(profiles: Iterable[Mapping[str, Any]], found_nobody_at_any_speed: bool = False, heads_on_bus: Iterable[str | int] = (),
             thresholds: Thresholds | None = None) -> list[str]:
    """The warning codes for what is known about a bus, most serious first; an empty list is a bus with nothing to say.

    ``profiles`` are the decoded 0x1B8 frames of the heads that were heard (``tec``, ``rec``, ``bus_off_count``; a missing field counts as 0); ``found_nobody_at_any_speed``
    is the result of a search that tried every speed; ``heads_on_bus`` are the names or serial numbers of the heads the tool knows about."""
    limits = thresholds or Thresholds()
    errors = False
    off = False
    for profile in profiles:
        errors = errors or int(profile.get("tec", 0) or 0) >= limits.tec_warn or int(profile.get("rec", 0) or 0) >= limits.rec_warn
        off = off or int(profile.get("bus_off_count", 0) or 0) >= limits.bus_off_warn
    legacy = any(is_legacy_head(name, limits) for name in heads_on_bus)
    found: list[str] = []
    if legacy and (errors or off):
        found.append(MIXED_BUS_SUSPECTED)
    if found_nobody_at_any_speed:
        found.append(NO_HEAD_AT_ANY_SPEED)
    if errors or off:
        found.append(BUS_ERRORS)
    if legacy:
        found.append(LEGACY_HEAD_KNOWN)
    return found
