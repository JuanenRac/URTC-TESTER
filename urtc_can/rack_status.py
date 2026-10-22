"""The status of the tool rack as a page: slots, heads, maintenance and alarms, in a form a dashboard can show.

``snapshot`` builds the data (JSON-ready) from the state of a rack (:class:`urtc_common.rack_sim.SimulatedRack`, or the same dictionary
made by a real rack bridge), the wear of each unit and the thermal verdicts; ``to_html`` writes a self-contained page (no script, no
external file, every value escaped); ``card`` is the short form a central dashboard puts on its overview. Which alarm is raised is
decided here from the values it is given, never invented: a rack that was not read says so.

Standard library only. Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
"""
from __future__ import annotations

import html
import json
from typing import Any

SCHEMA = 1
FAULT_VERDICTS = {"heater_in_empty_slot", "still_hot", "not_reached", "overshoot"}


def snapshot(rack_status: dict[str, Any], units: dict[str, dict[str, Any]] | None = None, verdicts: dict[int, str] | None = None,
             name: str = "rack", source: str = "simulation") -> dict[str, Any]:
    """``rack_status`` is what ``SimulatedRack.status()`` returns; ``units`` maps ``"<tool>:<serial>"`` to ``{"cycles", "heater_seconds",
    "faults", "maintenance": bool}``; ``verdicts`` maps a slot to its thermal verdict. ``source`` says where the numbers come from."""
    units = units or {}
    verdicts = verdicts or {}
    slots = []
    alarms: list[str] = []
    for item in rack_status["slots"]:
        slot = dict(item)
        unit = units.get(item["unit"]) if item.get("unit") else None
        slot["wear"] = unit
        slot["thermal"] = verdicts.get(item["slot"])
        slot["maintenance_due"] = bool(unit and unit.get("maintenance"))
        if slot["maintenance_due"]:
            alarms.append(f"slot {item['slot']}: maintenance due for unit {item['unit']}")
        if item.get("expired"):
            alarms.append(f"slot {item['slot']}: pre-heat limit reached, the target was switched off")
        if slot["thermal"] in FAULT_VERDICTS:
            alarms.append(f"slot {item['slot']}: thermal check says {slot['thermal']}")
        slots.append(slot)
    return {
        "schema": SCHEMA, "name": name, "source": source, "occupied": rack_status["occupied"], "slot_count": len(slots),
        "heating": sum(1 for s in slots if s["occupied"] and s["target_c"] > 0),
        "maintenance_due": sum(1 for s in slots if s["maintenance_due"]), "alarms": alarms, "slots": slots,
    }


def card(snap: dict[str, Any]) -> dict[str, Any]:
    """The overview entry of a dashboard: a title, a state and a few counters."""
    state = "alarm" if snap["alarms"] else "ok"
    return {
        "title": snap["name"], "state": state, "source": snap["source"],
        "items": [
            {"label": "slots in use", "value": f"{snap['occupied']}/{snap['slot_count']}"},
            {"label": "heating", "value": snap["heating"]},
            {"label": "maintenance due", "value": snap["maintenance_due"]},
            {"label": "alarms", "value": len(snap["alarms"])},
        ],
    }


def to_json(snap: dict[str, Any]) -> str:
    return json.dumps(snap, indent=2, sort_keys=True) + "\n"


def to_html(snap: dict[str, Any]) -> str:
    esc = html.escape
    rows = []
    for s in snap["slots"]:
        wear = s["wear"] or {}
        rows.append(
            "<tr><td>{slot}</td><td>{tool}</td><td>{unit}</td><td>{target}</td><td>{thermal}</td><td>{wear}</td></tr>".format(
                slot=esc(str(s["slot"])), tool=esc("-" if s["tool_id"] is None else str(s["tool_id"])), unit=esc(s["unit"] or "-"),
                target=esc(str(s["target_c"])), thermal=esc(s["thermal"] or "-"),
                wear=esc("maintenance due" if s["maintenance_due"] else (f"{wear.get('cycles', 0)} cycles, {wear.get('heater_seconds', 0)} s heater" if wear else "-"))))
    alarms = "".join(f"<li>{esc(a)}</li>" for a in snap["alarms"]) or "<li>none</li>"
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{esc(snap['name'])}</title>"
        "<style>body{font:16px system-ui,sans-serif;margin:16px;background:#fff;color:#111}table{border-collapse:collapse;width:100%}"
        "th,td{border:1px solid #888;padding:4px 8px;text-align:left}@media (prefers-color-scheme:dark){body{background:#111;color:#eee}}</style></head><body>"
        f"<h1>{esc(snap['name'])}</h1><p>Source: {esc(snap['source'])}. Slots in use: {snap['occupied']}/{snap['slot_count']}. Heating: {snap['heating']}. "
        f"Maintenance due: {snap['maintenance_due']}.</p><h2>Alarms</h2><ul>{alarms}</ul><h2>Slots</h2>"
        "<table><tr><th>Slot</th><th>Tool</th><th>Unit</th><th>Target C</th><th>Thermal check</th><th>Wear</th></tr>" + "".join(rows) + "</table></body></html>\n"
    )
