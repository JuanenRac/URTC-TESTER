# =============================================================================
# URTC Tester - tests/test_qt_tool_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The generic tool panel of the Qt deck: the controller that holds the values, sends the commands and keeps the readings of the selected
tool (with a fake host and a fake bus, no window), and the QML view that draws it (offscreen, in its own process, without a single QML
error or warning)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

pytest.importorskip("PySide6")
from PySide6.QtCore import QCoreApplication, QObject, Signal  # noqa: E402

import qt_tool_panel  # noqa: E402
from urtc_can import tool_panel_model as model  # noqa: E402

SOLDERING, DRILL, THERMAL = 0, 5, 22


class FakeTransport:
    def __init__(self) -> None:
        self.sent: list[tuple[int, bytes]] = []
        self.incoming: list[tuple[int, bytes]] = []

    def send_frame(self, can_id: int, data: bytes = b"") -> None:
        self.sent.append((can_id, bytes(data)))

    def read_frame(self, timeout: float = 0.05):
        return self.incoming.pop(0) if self.incoming else None


class FakeHost(QObject):
    changed = Signal()

    def __init__(self, tool: int = SOLDERING, can_act: bool = True) -> None:
        super().__init__()
        self._selected_tool_id = tool
        self._transport: FakeTransport | None = FakeTransport()
        self.canActuateSelectedProfile = can_act
        self.connected = True
        self.activeTool = "Soldering iron"
        self._busy = False
        self._telemetry_stops: dict = {}
        self.logs: list[str] = []
        self.watchdogs: dict[str, tuple] = {}
        self.stopped: list[str] = []

    def uiText(self, key: str) -> str:
        return key

    def _log(self, message: str) -> None:
        self.logs.append(message)

    def _set_state(self, *, status=None, busy=None) -> None:
        if busy is not None:
            self._busy = busy
        self.changed.emit()

    def _start_watchdog(self, key, interval, frame, off) -> None:
        self.watchdogs[key] = (interval, frame, off)

    def _stop_watchdog(self, key, off_frame=None) -> None:
        self.stopped.append(key)
        self.watchdogs.pop(key, None)


@pytest.fixture(scope="module")
def app():
    return QCoreApplication.instance() or QCoreApplication([])


def pump(app, until, seconds: float = 3.0) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end and not until():
        app.processEvents()
        time.sleep(0.01)


def test_every_panel_tool_has_sections_with_texts_and_the_translation_key_is_the_catalog_one(app):
    assert qt_tool_panel.translation_key("testertool.setpoint_0_445") == "PANEL_SETPOINT_0_445"
    for tool in sorted(model.PANELS):
        host = FakeHost(tool)
        sections = qt_tool_panel.ToolPanelController(host).sections
        assert sections and all(s["title"] for s in sections)


def test_a_tool_without_a_panel_has_none(app):
    host = FakeHost(15)
    controller = qt_tool_panel.ToolPanelController(host)
    assert controller.available is False and controller.sections == []


def test_a_value_is_held_to_the_range_of_its_control(app):
    controller = qt_tool_panel.ToolPanelController(FakeHost(SOLDERING))
    controller.setValue("temp", "9999")
    assert controller.sections[0]["controls"][0]["value"] == 445
    controller.setValue("temp", "abc")
    assert controller.sections[0]["controls"][0]["value"] == 0


def test_a_command_is_refused_without_the_profile_gate(app):
    host = FakeHost(SOLDERING, can_act=False)
    controller = qt_tool_panel.ToolPanelController(host)
    send = next(a for a in controller.sections[1]["actions"] if a["kind"] == "send")
    controller.run(1, send["index"])
    assert host._transport.sent == [] and any("BLOCKED" in line for line in host.logs)


def test_a_one_off_command_goes_out_with_the_values_of_the_controls(app):
    host = FakeHost(SOLDERING)
    controller = qt_tool_panel.ToolPanelController(host)
    controller.setValue("steps", "300")
    send = next(a for a in controller.sections[1]["actions"] if a["kind"] == "send")
    controller.run(1, send["index"])
    assert host._transport.sent == [(0x120, bytes([1, 0, 0, 1, 0x2C]))]


def test_a_repeated_command_goes_through_the_watchdog_and_follows_its_control(app):
    host = FakeHost(SOLDERING)
    controller = qt_tool_panel.ToolPanelController(host)
    controller.setValue("temp", "230")
    controller.toggle(0, 0, True)
    interval, frame, off = host.watchdogs["panel0_0"]
    assert frame == (304, bytes([0, 230])) and off == (304, bytes([0, 0])) and interval == pytest.approx(0.15)
    assert controller.sections[0]["active"] is True
    controller.setValue("temp", "240")
    assert host.watchdogs["panel0_0"][1] == (304, bytes([0, 240]))
    controller.toggle(0, 0, False)
    assert "panel0_0" in host.stopped and controller.sections[0]["active"] is False


def test_a_stop_ends_the_repeat_and_sends_its_frame(app):
    host = FakeHost(DRILL)
    controller = qt_tool_panel.ToolPanelController(host)
    controller.toggle(0, 0, True)
    assert "panel5_0" in host.watchdogs
    stop = next(a for a in controller.sections[0]["actions"] if a["kind"] == "stop")
    controller.run(0, stop["index"])
    assert "panel5_0" in host.stopped and host._transport.sent[-1] == (model.panel_of(DRILL)["sections"][0]["actions"][1]["canId"], bytes([0, 0]))


def test_a_reading_follows_the_frames_of_its_identifier(app):
    host = FakeHost(SOLDERING)
    controller = qt_tool_panel.ToolPanelController(host)
    assert controller.sections[0]["readings"][0]["text"] == "-- C"
    controller.feed_frame(309, bytes([0x00, 0xDC]))
    assert controller.sections[0]["readings"][0]["text"] == "220 C"
    controller.feed_frame(0x999, bytes([1, 2]))
    assert controller.sections[0]["readings"][0]["text"] == "220 C"


def test_a_query_asks_the_board_and_shows_the_answer(app):
    host = FakeHost(SOLDERING)
    controller = qt_tool_panel.ToolPanelController(host)
    query = next((si, a) for si, s in enumerate(model.panel_of(SOLDERING)["sections"]) for a in s["actions"] if a["type"] == "query")
    section, spec = query
    index = model.panel_of(SOLDERING)["sections"][section]["actions"].index(spec)
    host._transport.incoming = []
    answer = [0] * (spec["result"]["offset"] + spec["result"]["width"])
    answer[spec["result"]["offset"] + spec["result"]["width"] - 1] = 7

    class Answering(FakeTransport):
        def send_frame(self, can_id, data=b""):
            super().send_frame(can_id, data)
            self.incoming.append((spec.get("respCanId", spec["canId"]), bytes(answer)))

    host._transport = Answering()
    controller.run(section, index)
    pump(app, lambda: not host._busy and controller._queries)
    assert host._transport.sent[0][0] == spec["canId"]
    assert controller._queries[(SOLDERING, section, index)] == 7
    assert host._busy is False


def test_a_query_is_refused_while_the_bus_is_busy(app):
    host = FakeHost(SOLDERING)
    host._busy = True
    controller = qt_tool_panel.ToolPanelController(host)
    section, index = next((si, i) for si, s in enumerate(model.panel_of(SOLDERING)["sections"]) for i, a in enumerate(s["actions"]) if a["type"] == "query")
    controller.run(section, index)
    assert host._transport.sent == [] and any("BUS_IS_BUSY".lower() in line.lower().replace(" ", "_") for line in host.logs)


def test_a_picture_is_pulled_chunk_by_chunk_and_coloured(app):
    host = FakeHost(THERMAL)
    controller = qt_tool_panel.ToolPanelController(host)
    section, index = next((si, i) for si, s in enumerate(model.panel_of(THERMAL)["sections"]) for i, a in enumerate(s["actions"]) if a["type"] == "image")
    spec = model.panel_of(THERMAL)["sections"][section]["actions"][index]

    class Chunks(FakeTransport):
        def send_frame(self, can_id, data=b""):
            super().send_frame(can_id, data)
            for _ in range(spec["frames_per_chunk"]):
                self.incoming.append((spec.get("respCanId", spec["canId"]), bytes([0x01, 0x90] * 4)))

    host._transport = Chunks()
    controller.run(section, index)
    pump(app, lambda: not host._busy and controller._images.get((THERMAL, section, index), {}).get("busy") is False)
    image = controller._images[(THERMAL, section, index)]
    assert image["error"] == "" and image["cells"] and all(c.startswith("#") and len(c) == 7 for c in image["cells"])
    assert len(host._transport.sent) == spec["chunks"]


def test_the_transport_bus_waits_for_the_frame_it_asks_for(app):
    transport = FakeTransport()
    transport.incoming = [(0x10, b"\x01"), (0x20, b"\x02\x03")]
    bus = qt_tool_panel.TransportBus(transport)
    assert bus.wait_for_frame(0x20, 500) == [2, 3]
    assert bus.wait_for_frame(0x20, 60) is None


LOADER = """
import json, sys
sys.path.insert(0, sys.argv[1])
from PySide6.QtCore import QObject, QUrl, Signal, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
import qt_tool_panel

class Host(QObject):
    changed = Signal()
    def __init__(self, tool):
        super().__init__()
        self._selected_tool_id = tool
        self._transport = None
        self.canActuateSelectedProfile = False
        self.connected = False
        self.activeTool = "Tool"
        self._busy = False
        self._telemetry_stops = {}
    def uiText(self, key): return key
    def _log(self, message): pass

QQuickStyle.setStyle("Basic")
app = QGuiApplication([])
messages = []
qInstallMessageHandler(lambda mode, context, message: messages.append(message))
out = {}
for tool in (0, 5, 22, 9, 15):
    host = Host(tool)
    panel = qt_tool_panel.ToolPanelController(host)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("panelModel", panel)
    engine.loadData(b'''
import QtQuick
import QtQuick.Window
Window { visible: true; width: 800; height: 600
  ToolPanelView { objectName: "view"; anchors.fill: parent; model: panelModel } }
''', QUrl.fromLocalFile(sys.argv[2] + "/host.qml"))
    roots = engine.rootObjects()
    def named(item, name):
        found = [item] if item.objectName() == name else []
        for child in item.childItems():
            found += named(child, name)
        return found
    content = roots[0].contentItem() if roots else None
    buttons = named(content, "panelButton") if content else []
    fields = named(content, "panelField") if content else []
    out[tool] = {"loaded": bool(roots), "sections": len(panel.sections), "buttons": len(buttons), "fields": len(fields)}
print("RESULT " + json.dumps({"tools": out, "messages": messages}))
sys.stdout.flush()
import os
os._exit(0)
"""


def test_the_generic_view_loads_for_every_kind_of_panel_without_qml_errors():
    environment = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    done = subprocess.run([sys.executable, "-c", LOADER, str(ROOT), str(ROOT / "assets" / "qml")], capture_output=True, text=True, env=environment, timeout=180, cwd=str(ROOT))
    line = next((l for l in done.stdout.splitlines() if l.startswith("RESULT ")), None)
    assert line is not None, done.stderr[-2000:]
    result = json.loads(line[len("RESULT "):])
    problems = [m for m in result["messages"] if ".qml" in m or "QML" in m or "qrc:" in m]
    assert problems == []
    tools = result["tools"]
    assert all(t["loaded"] for t in tools.values())
    assert tools["0"]["sections"] >= 2 and tools["0"]["buttons"] >= 2 and tools["0"]["fields"] >= 2
    assert tools["22"]["buttons"] >= 1 and tools["15"]["sections"] == 0
