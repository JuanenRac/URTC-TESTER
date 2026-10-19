# =============================================================================
# URTC Tester - hardware-free check of the Qt Quick self-test
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Run directly: QT_QPA_PLATFORM=offscreen python verify_qt_selftest.py

A fake soldering iron answers on a real worker thread; the self-test runs through the real Signal path to the GUI
thread.  Also loads TesterDeck.qml with the bridge and checks that it shows no warning about the self-test.
"""
from __future__ import annotations

import queue
import sys
import time

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

import qt_tester
from qt_tester import TesterQtBridge


class FakeTransport:
    def __init__(self) -> None:
        self.inbox: queue.Queue = queue.Queue()
        self.sent: list[tuple[int, bytes]] = []

    def send_frame(self, can_id: int, data: bytes) -> None:
        self.sent.append((can_id, bytes(data)))
        reply = {
            qt_tester.CAN_ID_QUERY_ACTIVE_TOOL: (qt_tester.CAN_ID_ACTIVE_TOOL_RESP, bytes([0, 0, 0, 0])),
            qt_tester.CAN_ID_QUERY_VERSION: (qt_tester.CAN_ID_VERSION_RESPONSE, b"\x00" * 8),
            qt_tester.CAN_ID_SOLDER_SETPOINT: (0x135, b"\x00\x00"),
        }.get(can_id)
        if reply is not None:
            self.inbox.put(reply)

    def read_frame(self, timeout: float = 0.1):
        try:
            return self.inbox.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self) -> None:
        pass


def _pump_until(app, condition, timeout_s: float = 5.0) -> None:
    deadline = time.monotonic() + timeout_s
    while not condition() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    bridge = TesterQtBridge()
    transport = FakeTransport()
    bridge._transport = transport
    bridge._listen_only = False
    bridge._selected_tool_id = 0
    bridge._active_tool_id = 0
    bridge._set_state(status="ACTIVE CHECKS ARMED", busy=False)
    assert bridge.canSelfTest, "an armed, identity-matched connection must allow the self-test"
    bridge.runSelfTest()
    assert bridge.selfTestRunning and bridge.busy
    _pump_until(app, lambda: not bridge.selfTestRunning)
    assert not bridge.selfTestRunning and not bridge.busy, "the deck must be released when the run ends"
    statuses = [line["status"] for line in bridge.selfTestLines]
    assert statuses.count("PASS") == 3 and "FAIL" not in statuses, statuses
    assert [can_id for can_id, _data in transport.sent] == [
        qt_tester.CAN_ID_QUERY_ACTIVE_TOOL, qt_tester.CAN_ID_QUERY_VERSION, qt_tester.CAN_ID_SOLDER_SETPOINT,
    ], "the self-test must send only the two queries and the zero setpoint"
    assert transport.sent[-1][1] == b"\x00\x00"

    bridge._listen_only = True
    assert not bridge.canSelfTest, "listen-only must close the gate"

    QQuickStyle.setStyle("Basic")
    engine = QQmlApplicationEngine()
    warnings: list[str] = []
    engine.warnings.connect(lambda items: warnings.extend(str(item) for item in items))
    qml_bridge = TesterQtBridge()  # keep a reference: QML does not own it
    engine.rootContext().setContextProperty("testerBackend", qml_bridge)
    engine.load("assets/qml/TesterDeck.qml")
    assert engine.rootObjects(), "TesterDeck.qml must load"
    relevant = [w for w in warnings if "elf" in w and "est" in w or "SelfTest" in w]
    assert not relevant, relevant
    print("verify_qt_selftest: all real assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
