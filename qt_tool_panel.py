# =============================================================================
# URTC Tester - qt_tool_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The panel of the selected tool for the Qt Quick deck, drawn from the profile instead of written for the tool.

``urtc_can.tool_panel_model`` holds everything that is not drawing (frame builders, ranges, decoding, the exchange that asks the board for a
value); ``ToolPanelView.qml`` draws what this controller exposes. The controller holds the values of the controls, the readings, the
queries and the pictures of the tool that is selected, and sends only through the gates the bridge already has: a command needs the
profile gate (``canActuateSelectedProfile``) and a command that reads the bus needs the bus free. A command that repeats while it is
on (a heater set point, a drill, the laser) goes through the bridge's own watchdog, which sends the stop frame when it ends.
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot

import tester_config
from urtc_can import tool_panel_model as model
from urtc_can.protocol import KEEPALIVE_INTERVAL_MS

REPEAT_SECONDS = KEEPALIVE_INTERVAL_MS / 1000.0


def translation_key(key: str) -> str:
    """The key of a panel text in the language files: ``testertool.setpoint`` is ``PANEL_SETPOINT``."""
    return "PANEL_" + key.split(".", 1)[-1].upper()


class TransportBus:
    """What the model needs of the bus (``PanelBus``), on top of the transport of the tester."""

    def __init__(self, transport: Any, clock: Callable[[], float] = time.monotonic) -> None:
        self._transport = transport
        self._clock = clock

    def send_frame(self, can_id: int, data: Sequence[int], description: str = "") -> None:
        self._transport.send_frame(can_id, bytes(data))

    def wait_for_frame(self, can_id: int, timeout_ms: int) -> Sequence[int] | None:
        deadline = self._clock() + timeout_ms / 1000.0
        while True:
            left = deadline - self._clock()
            if left <= 0:
                return None
            frame = self._transport.read_frame(timeout=min(0.05, left))
            if frame is not None and frame[0] == can_id:
                return list(frame[1])

    def request(self, can_id: int, data: Sequence[int], response_id: int, timeout_ms: int, description: str = "") -> Sequence[int] | None:
        self.flush_frames(response_id)
        self.send_frame(can_id, data, description)
        return self.wait_for_frame(response_id, timeout_ms)

    def flush_frames(self, can_id: int | None = None) -> None:
        for _ in range(256):   # frames already waiting; bounded so a chatty bus cannot hold the call
            if self._transport.read_frame(timeout=0) is None:
                return


class ToolPanelController(QObject):
    """The panel of the tool selected on the bridge (the ``host``), as data for QML."""

    changed = Signal()
    _queryDone = Signal(int, int, object)
    _imageDone = Signal(int, int, object, str)
    _frameSeen = Signal(int, object)

    def __init__(self, host: Any, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._host = host
        self._values: dict[int, dict[str, model.PanelValue]] = {}
        self._active: set[tuple[int, int]] = set()          # (tool, section) with a repeated command on
        self._confirmed: dict[tuple[int, int], dict[str, float]] = {}   # the value the person confirmed for each control of a command that repeats
        self._latched: dict[tuple[int, int, int], bool] = {}
        self._readings: dict[tuple[int, str], dict[str, Any]] = {}
        self._queries: dict[tuple[int, int, int], int | None] = {}
        self._images: dict[tuple[int, int, int], dict[str, Any]] = {}
        self._queryDone.connect(self._on_query_done)
        self._imageDone.connect(self._on_image_done)
        self._frameSeen.connect(self.feed_frame)
        changed = getattr(host, "changed", None)
        if changed is not None:
            changed.connect(self.changed)

    # ------------------------------------------------------------------ the tool
    def _tool(self) -> int:
        return int(self._host._selected_tool_id)

    def _panel(self) -> Mapping | None:
        return model.panel_of(self._tool())

    def _translate(self, key: str, default: str) -> str:
        shown = self._host.uiText(translation_key(key))
        return default if shown == translation_key(key) else shown

    def _text(self, text: Mapping, params: Mapping[str, Any] | None = None) -> str:
        return model.panel_text(self._translate, text, params or {"tool": getattr(self._host, "activeTool", "")})

    def _values_of(self, tool: int) -> dict[str, model.PanelValue]:
        if tool not in self._values:
            panel = model.panel_of(tool)
            self._values[tool] = model.initial_values(panel) if panel else {}
        return self._values[tool]

    @Property(bool, notify=changed)
    def available(self) -> bool:
        return self._panel() is not None

    @Property("QVariantList", notify=changed)
    def sections(self) -> list[dict[str, Any]]:
        panel = self._panel()
        if panel is None:
            return []
        tool = self._tool()
        values = self._values_of(tool)
        out: list[dict[str, Any]] = []
        for si, section in enumerate(panel["sections"]):
            controls = []
            for c in section.get("controls", []):
                value = values[c["id"]]
                item: dict[str, Any] = {"id": c["id"], "type": c["type"], "value": value,
                                        "label": self._text(c["label"], model.label_params(c, value)),
                                        "valid": c["type"] != "hex" or _is_config_word(str(value))}
                if c["type"] in ("range", "number"):
                    item.update({"min": c["min"], "max": c["max"]})
                if c["type"] == "select":
                    item["options"] = [{"value": o["value"], "label": self._text(o["label"])} for o in c["options"]]
                controls.append(item)
            actions = []
            for ai, a in enumerate(section.get("actions", [])):
                actions.append(self._action_item(tool, si, ai, a))
            readings = []
            for r in section.get("telemetry", []):
                state = self._readings.get((tool, r["id"]), {})
                text, tone = model.reading_shown(r, state.get("value"), state.get("seen"), self._translate("testertool.yes", "YES"), self._translate("testertool.no", "no"))
                readings.append({"id": r["id"], "label": self._text(r["label"]), "text": text, "tone": tone})
            out.append({"index": si, "title": self._text(section["title"]), "notice": self._text(section["notice"]) if section.get("notice") else "",
                        "controls": controls, "actions": actions, "readings": readings,
                        "active": (tool, si) in self._active})
        return out

    def _action_item(self, tool: int, si: int, ai: int, a: Mapping) -> dict[str, Any]:
        kind = a["type"]
        item: dict[str, Any] = {"index": ai, "kind": kind, "label": self._text(a["label"]) if a.get("label") else "", "confirm": bool(a.get("confirm"))}
        if kind == "latched":
            item["on"] = self._latched.get((tool, si, ai), False)
        if kind == "query":
            result = a["result"]
            item["resultLabel"] = self._text(result["label"]) if result.get("label") else ""
            item["resultText"] = model.result_text(self._translate, result, self._queries.get((tool, si, ai)))
        if kind == "image":
            image = self._images.get((tool, si, ai), {})
            item["cells"] = image.get("cells", [])
            item["columns"] = a["columns"]
            item["error"] = image.get("error", "")
            item["busy"] = bool(image.get("busy"))
        if kind in ("send", "stop"):
            item["enabled"] = not any(c["type"] == "hex" and not _is_config_word(str(self._values_of(tool).get(c["id"], "")))
                                      for c in model.panel_controls(self._panel() or {"sections": []}) if c["id"] in (a.get("args") or []))
        return item

    @Property(bool, notify=changed)
    def canAsk(self) -> bool:
        host = self._host
        return bool(host.canActuateSelectedProfile and not host._busy and not host._telemetry_stops)

    @Property(bool, notify=changed)
    def hasReadings(self) -> bool:
        panel = self._panel()
        return bool(panel and any(s.get("telemetry") for s in panel["sections"]))

    @Property(bool, notify=changed)
    def canWatch(self) -> bool:
        host = self._host
        return bool(self.hasReadings and host.connected and not host._busy and not host._telemetry_stops)

    @Property(bool, notify=changed)
    def watching(self) -> bool:
        return "panel" in self._host._telemetry_stops

    @Property(str, constant=True)
    def uiActive(self) -> str:
        return self._host.uiText("PANEL_ACTIVE")

    @Property(str, constant=True)
    def uiWatch(self) -> str:
        return self._host.uiText("PANEL_WATCH")

    @Property(str, constant=True)
    def uiStopWatch(self) -> str:
        return self._host.uiText("PANEL_STOP_WATCH")

    @Property(str, constant=True)
    def uiShow(self) -> str:
        return self._host.uiText("PANEL_SHOW_PROFILE_PANEL")

    # ------------------------------------------------------------------ controls
    def _control(self, control_id: str) -> Mapping | None:
        panel = self._panel()
        return next((c for c in model.panel_controls(panel) if c["id"] == control_id), None) if panel else None

    def _coerce(self, control: Mapping, raw: Any) -> model.PanelValue | None:
        """The value a control takes from ``raw`` (None when it does not take it)."""
        if control["type"] in ("range", "number"):
            return model.clamp_control(control, raw)
        if control["type"] == "checkbox":
            return bool(raw)
        if control["type"] == "select":
            return next((o["value"] for o in control["options"] if str(o["value"]) == str(raw)), None)
        return str(raw)

    def _repeating_sections_using(self, tool: int, control_id: str) -> list[int]:
        """The sections with a repeated command that is on and takes the control as one of its values."""
        panel = model.panel_of(tool)
        found: list[int] = []
        for si, section in enumerate(panel["sections"] if panel else []):
            if (tool, si) in self._active and any(a["type"] == "keepalive" and control_id in (a.get("args") or []) for a in section.get("actions", [])):
                found.append(si)
        return found

    def _raise_needs_confirmation(self, tool: int, control_id: str, value: Any) -> bool:
        """True when a command that repeats and is on would take a value above the confirmed one by more than the configured percentage."""
        settings = tester_config.power_guard_settings()
        for si in self._repeating_sections_using(tool, control_id):
            confirmed = self._confirmed.get((tool, si), {}).get(control_id)
            if confirmed is not None and tester_config.power_rise_needs_confirmation(confirmed, value, settings):
                return True
        return False

    @Slot(str, "QVariant", result=bool)
    def needsConfirm(self, control_id: str, raw: Any) -> bool:
        """True when setting the control to ``raw`` would raise a tool that is on too far above the value the person confirmed (ask, then ``setValueConfirmed``)."""
        control = self._control(control_id)
        value = self._coerce(control, raw) if control else None
        return value is not None and self._raise_needs_confirmation(self._tool(), control_id, value)

    @Slot(str, "QVariant")
    def setValue(self, control_id: str, raw: Any) -> None:
        self._set_value(control_id, raw, confirmed=False)

    @Slot(str, "QVariant")
    def setValueConfirmed(self, control_id: str, raw: Any) -> None:
        """Sets a value after the person confirmed it: it becomes the value the next rise is measured from."""
        self._set_value(control_id, raw, confirmed=True)

    def _set_value(self, control_id: str, raw: Any, confirmed: bool) -> None:
        panel = self._panel()
        control = self._control(control_id)
        if panel is None or control is None:
            return
        tool = self._tool()
        value = self._coerce(control, raw)
        if value is None:
            return
        if not confirmed and self._raise_needs_confirmation(tool, control_id, value):
            self._host._log("PANEL_POWER_RAISE_BLOCKED")
            self.changed.emit()          # the control goes back to the value the tool really has
            return
        if confirmed:
            for si in self._repeating_sections_using(tool, control_id):
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    self._confirmed.setdefault((tool, si), {})[control_id] = value
        self._values_of(tool)[control_id] = value
        for si, section in enumerate(panel["sections"]):     # a command that repeats follows the control it uses
            if (tool, si) in self._active:
                for ai, a in enumerate(section.get("actions", [])):
                    if a["type"] == "keepalive":
                        self._start_repeat(tool, si, ai, a)
        self.changed.emit()

    def _gate(self, what: str, reads: bool = False) -> bool:
        host = self._host
        if reads and (host._telemetry_stops or host._busy):
            host._log(f"{what}_BLOCKED the bus is busy")
            return False
        if not host.canActuateSelectedProfile or host._transport is None:
            host._log(f"{what}_BLOCKED profile identity/active-check gate not satisfied")
            return False
        return True

    # ------------------------------------------------------------------ commands
    def _frame(self, a: Mapping, tool: int, section: int, off: bool = False) -> tuple[int, bytes]:
        values = self._values_of(tool)
        if off:
            return a["canId"], bytes(model.ENCODERS[a["off_encoder"]]())
        return a["canId"], bytes(model.encode_action(a["encoder"], values, a.get("args"), a.get("gate_first", False), (tool, section) in self._active))

    def _action(self, section: int, index: int) -> tuple[int, Mapping, Mapping] | None:
        panel = self._panel()
        try:
            sec = panel["sections"][section] if panel else None
            return self._tool(), sec, sec["actions"][index] if sec else None   # type: ignore[return-value]
        except (IndexError, KeyError, TypeError):
            return None

    @Slot(int, int)
    def run(self, section: int, index: int) -> None:
        """A button: a one-off command, a stop, a question to the board or a picture."""
        found = self._action(section, index)
        if found is None:
            return
        tool, sec, a = found
        kind = a["type"]
        if kind == "query":
            self._start_query(tool, section, index, a)
        elif kind == "image":
            self._start_image(tool, section, index, a)
        elif kind in ("send", "stop"):
            if not self._gate("PANEL"):
                return
            if kind == "stop":
                self._stop_repeat(tool, section)
                for cid in a.get("reset") or []:
                    self._values_of(tool)[cid] = model.initial_values(self._panel())[cid]    # type: ignore[arg-type]
            try:
                can_id, data = self._frame(a, tool, section)
                self._host._transport.send_frame(can_id, data)
                self._host._log(f"PANEL_SENT {a.get('description', a['encoder'])}")
            except (ValueError, KeyError) as exc:
                self._host._log(f"PANEL_BLOCKED {exc}")
            self.changed.emit()

    @Slot(int, int, bool)
    def toggle(self, section: int, index: int, on: bool) -> None:
        """A check box: a command that repeats while it is on, or one that latches an output."""
        found = self._action(section, index)
        if found is None:
            return
        tool, sec, a = found
        if not self._gate("PANEL"):
            self.changed.emit()
            return
        if a["type"] == "keepalive":
            if on:
                self._start_repeat(tool, section, index, a)
            else:
                self._stop_repeat(tool, section)
                for cid in a.get("reset") or []:
                    self._values_of(tool)[cid] = model.initial_values(self._panel())[cid]    # type: ignore[arg-type]
        elif a["type"] == "latched":
            self._latched[(tool, section, index)] = on
            can_id = a["canId"]
            self._host._transport.send_frame(can_id, bytes(model.ENCODERS[a["encoder"]](on)))
            self._host._log("PANEL_SENT " + a.get("description_on" if on else "description_off", a["encoder"]))
        self.changed.emit()

    def _start_repeat(self, tool: int, section: int, index: int, a: Mapping) -> None:
        try:
            frame = self._frame(a, tool, section)
        except (ValueError, KeyError) as exc:
            self._host._log(f"PANEL_BLOCKED {exc}")
            return
        if (tool, section) not in self._active:      # switching it on is the confirmation of the values it starts with
            values = self._values_of(tool)
            self._confirmed[(tool, section)] = {c: v for c, v in values.items() if c in (a.get("args") or []) and isinstance(v, (int, float)) and not isinstance(v, bool)}
        self._active.add((tool, section))
        off = self._frame(a, tool, section, off=True)
        interval = (a.get("interval_ms") or KEEPALIVE_INTERVAL_MS) / 1000.0
        self._host._start_watchdog(f"panel{tool}_{section}", interval, frame, off)
        self._host._log(f"PANEL_REPEATING {a.get('description', a['encoder'])}")

    def _stop_repeat(self, tool: int, section: int) -> None:
        if (tool, section) in self._active:
            self._active.discard((tool, section))
            self._confirmed.pop((tool, section), None)
            self._host._stop_watchdog(f"panel{tool}_{section}")

    # ------------------------------------------------------------------ asking the board
    def _start_query(self, tool: int, section: int, index: int, a: Mapping) -> None:
        if not self._gate("PANEL_QUERY", reads=True):
            return
        bus = TransportBus(self._host._transport)
        self._host._set_state(busy=True)

        def worker() -> None:
            value = None
            try:
                value = model.ask_value(bus, a)
            except Exception as exc:
                self._host._log(f"PANEL_QUERY_FAILED {exc}")
            self._queryDone.emit(tool, section * 1000 + index, value)

        threading.Thread(target=worker, daemon=True, name="urtc-tester-panel-query").start()

    def _on_query_done(self, tool: int, packed: int, value: object) -> None:
        self._queries[(tool, packed // 1000, packed % 1000)] = value if isinstance(value, int) else None
        self._host._set_state(busy=False)
        self.changed.emit()

    def _start_image(self, tool: int, section: int, index: int, a: Mapping) -> None:
        if not self._gate("PANEL_IMAGE", reads=True):
            return
        bus = TransportBus(self._host._transport)
        self._images[(tool, section, index)] = {"cells": [], "error": "", "busy": True}
        self._host._set_state(busy=True)

        def worker() -> None:
            try:
                pixels = model.pull_image(bus, a)
                self._imageDone.emit(tool, section * 1000 + index, pixels, "")
            except Exception as exc:
                self._imageDone.emit(tool, section * 1000 + index, None, str(exc))

        threading.Thread(target=worker, daemon=True, name="urtc-tester-panel-image").start()

    def _on_image_done(self, tool: int, packed: int, pixels: object, error: str) -> None:
        section, index = packed // 1000, packed % 1000
        a = self._panel()["sections"][section]["actions"][index] if self._tool() == tool and self._panel() else None   # type: ignore[index]
        cells: list[str] = []
        if isinstance(pixels, list) and a is not None:
            for v in pixels[: a["chunks"] * a["frames_per_chunk"] * 4]:
                r, g, b = model.heat_colour(v, a["max_value"])
                cells.append(f"#{r:02x}{g:02x}{b:02x}")
        message = ""
        if error and a is not None:
            message = self._text(a["error"], {"message": error})
        self._images[(tool, section, index)] = {"cells": cells, "error": message, "busy": False}
        self._host._set_state(busy=False)
        self.changed.emit()

    # ------------------------------------------------------------------ readings
    def feed_frame(self, can_id: int, data: object) -> None:
        """A frame of the bus: every reading of the selected tool that listens to its identifier takes it."""
        panel = self._panel()
        if panel is None or not isinstance(data, (bytes, bytearray, list, tuple)):
            return
        tool = self._tool()
        moved = False
        for section in panel["sections"]:
            for r in section.get("telemetry", []):
                if r["canId"] != can_id:
                    continue
                key = (tool, r["id"])
                previous = self._readings.get(key, {})
                self._readings[key] = model.reading_step(r, list(data), time.strftime("%H:%M:%S"), previous)
                moved = True
        if moved:
            self.changed.emit()

    @Slot()
    def watchReadings(self) -> None:
        """Listens to the telemetry of the tool without sending a frame (it holds the bus like the other live readouts)."""
        host = self._host
        panel = self._panel()
        ids = {r["canId"] for s in (panel or {"sections": []})["sections"] for r in s.get("telemetry", [])}
        if not ids or host._transport is None or host._busy or host._telemetry_stops or not host.connected:
            host._log("PANEL_WATCH_BLOCKED nothing to read, or the bus is busy")
            return
        stop = threading.Event()
        host._telemetry_stops["panel"] = stop
        host._set_state(status="WATCHING THE TOOL PANEL", busy=True)
        transport = host._transport

        def worker() -> None:
            try:
                while not stop.is_set():
                    frame = transport.read_frame(timeout=0.1)
                    if frame is not None and frame[0] in ids:
                        self._frameSeen.emit(frame[0], bytes(frame[1]))
            except Exception as exc:
                host._log(f"PANEL_WATCH_FAILED {exc}")
            finally:
                host._telemetry_stops.pop("panel", None)
                host._set_state(status="ACTIVE CHECKS ARMED", busy=False)

        threading.Thread(target=worker, daemon=True, name="urtc-tester-panel-watch").start()

    @Slot()
    def stopReadings(self) -> None:
        stop = self._host._telemetry_stops.get("panel")
        if stop is not None:
            stop.set()


def _is_config_word(text: str) -> bool:
    try:
        model.config_word_to_bytes(text)
    except ValueError:
        return False
    return True
