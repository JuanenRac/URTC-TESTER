# =============================================================================
# URTC Tester - real, hardware-free end-to-end check of the Qt Quick
# telemetry watch (Vacuum Pickup / Scan Probe)
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Deliberately kept OUTSIDE tests/ (see that directory's own
test_advanced_protocol.py header: "hardware-free... without importing a
GUI runtime") - this needs a real PySide6 QCoreApplication event loop to
exercise the real cross-thread Signal delivery watchTelemetry()'s worker
thread depends on, so it isn't part of that fast, GUI-runtime-free suite.
Run directly: QT_QPA_PLATFORM=offscreen python verify_qt_telemetry_watch.py
(the QT_QPA_PLATFORM is only needed on a host with no real display, e.g.
CI or an SSH session - a normal desktop run doesn't need it).

A fake transport (real read_frame/send_frame call shape, no real serial/
CAN device) feeds frames through a real queue.Queue from this thread,
mirroring how a real background CAN read would arrive asynchronously
relative to the GUI thread - not a mocked bridge, the real TesterQtBridge
class, with real assertions on its resulting state.
"""
from __future__ import annotations

import queue
import struct
import sys
import time

from PySide6.QtGui import QGuiApplication

from qt_tester import TesterQtBridge


class FakeTransport:
    def __init__(self) -> None:
        self.inbox: queue.Queue = queue.Queue()
        self.sent: list[tuple[int, bytes]] = []

    def read_frame(self, timeout: float = 0.1):
        try:
            return self.inbox.get(timeout=timeout)
        except queue.Empty:
            return None

    def send_frame(self, can_id: int, data: bytes) -> None:
        self.sent.append((can_id, data))

    def close(self) -> None:
        pass


def _pump_until(app: QGuiApplication, condition, timeout_s: float = 2.0) -> None:
    deadline = time.monotonic() + timeout_s
    while not condition() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.02)


def _run() -> None:
    # A real process may only ever have ONE QCoreApplication-family
    # instance - QGuiApplication is used from the start (not a plain
    # QCoreApplication first and a QGuiApplication later for the QML
    # section below) specifically so this script needs only the one real
    # instance throughout. Found live: creating a second, incompatible
    # application object crashed the whole process with a native
    # STATUS_STACK_BUFFER_OVERRUN, not a normal Python exception.
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    bridge = TesterQtBridge()
    transport = FakeTransport()

    # Real connected + identity-matched state, without a real serial port -
    # sets exactly what toggleConnection()/probeIdentity()'s own real
    # worker threads would after a real successful exchange.
    bridge._transport = transport
    bridge._listen_only = False
    bridge._selected_tool_id = 4  # Vacuum Pickup
    bridge._active_tool_id = 4
    bridge._set_state(status="ACTIVE CHECKS ARMED", busy=False)

    assert bridge.advancedControlKind == "vacuum"
    assert bridge.canWatchTelemetry is True, "identity-matched + connected + active must allow watching"
    assert bridge.isWatchingTelemetry is False

    bridge.watchTelemetry()
    _pump_until(app, lambda: bridge.isWatchingTelemetry)
    assert bridge.isWatchingTelemetry is True, "watch must be running after watchTelemetry()"
    assert bridge._busy is True, "a running watch must hold the same busy gate every other read op does"

    # A second watchTelemetry() call while one is already running must be a
    # real no-op (never opens two concurrent readers on the same transport).
    bridge.watchTelemetry()
    assert len(bridge._telemetry_stops) == 1, "must never allow two concurrent watches"

    # Feed one real vacuum telemetry frame (ADC=1234, part detected) and
    # confirm it reaches the bridge's own real Property through the real
    # worker-thread -> Signal -> GUI-thread path, not called directly.
    transport.inbox.put((0x145, struct.pack(">H", 1234) + bytes([1])))
    _pump_until(app, lambda: bridge.vacuumAdc != 0)
    assert bridge.vacuumAdc == 1234, f"expected adc=1234, got {bridge.vacuumAdc}"
    assert bridge.vacuumDetected is True

    # An irrelevant frame (wrong CAN ID) on the same wire must be ignored,
    # not misread as vacuum telemetry.
    transport.inbox.put((0x999, b"\x00\x00\x00"))
    app.processEvents()
    time.sleep(0.05)
    app.processEvents()
    assert bridge.vacuumAdc == 1234, "an unrelated frame must not corrupt the last real reading"

    # Stop must work even though busy=True (the one real exception to the
    # busy gate, exactly like _stop_watchdog).
    bridge.stopTelemetryWatch()
    _pump_until(app, lambda: not bridge.isWatchingTelemetry)
    assert bridge.isWatchingTelemetry is False, "watch must actually stop"
    assert bridge._busy is False, "busy must clear once the worker thread genuinely exits"
    assert not bridge._telemetry_stops

    # A disconnected/mismatched profile must never be allowed to start a
    # watch at all - real safety gate, not just a UI-level hint.
    bridge._active_tool_id = -1
    assert bridge.canWatchTelemetry is False
    bridge.watchTelemetry()
    assert bridge.isWatchingTelemetry is False, "must refuse to start without a real identity match"

    # --- scan probe: event-driven, not periodic - verify impact counting ---
    bridge._active_tool_id = 11
    bridge._selected_tool_id = 11
    assert bridge.advancedControlKind == "scan_probe"
    bridge.watchTelemetry()
    _pump_until(app, lambda: bridge.isWatchingTelemetry)
    assert bridge.isWatchingTelemetry is True

    transport.inbox.put((0x095, bytes([0x01])))  # a real impact event
    _pump_until(app, lambda: bridge.scanProbeImpactCount != 0)
    assert bridge.scanProbeImpactCount == 1
    assert bridge.scanProbeLastImpact != ""

    transport.inbox.put((0x095, bytes([0x00])))  # data[0] != 0x01 - not a real impact
    app.processEvents()
    time.sleep(0.05)
    app.processEvents()
    assert bridge.scanProbeImpactCount == 1, "a non-impact frame on the same CAN ID must not be miscounted"

    bridge.stopTelemetryWatch()
    _pump_until(app, lambda: not bridge.isWatchingTelemetry)
    assert bridge.isWatchingTelemetry is False

    # --- listen-only mode: telemetry watching must still work (never
    # transmits), unlike every other advanced control ---
    bridge._listen_only = True
    bridge._selected_tool_id = 4
    bridge._active_tool_id = 4
    assert bridge.canActuateSelectedProfile is False, "sanity: the general command gate IS blocked in listen-only"
    assert bridge.canWatchTelemetry is True, "but telemetry watching must NOT be blocked by listen-only - it never transmits"
    assert transport.sent == [], "confirms nothing here ever called send_frame - pure read throughout"

    # --- QML itself loads with this bridge and shows zero warnings ---
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle

    QQuickStyle.setStyle("Basic")
    engine = QQmlApplicationEngine()
    qml_bridge = TesterQtBridge()
    engine.rootContext().setContextProperty("testerBackend", qml_bridge)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(str(w) for w in ws))
    engine.load("assets/qml/TesterDeck.qml")
    assert engine.rootObjects(), "TesterDeck.qml must load with the real bridge"
    qml_bridge.selectToolProfile(4)
    assert qml_bridge.advancedControlKind == "vacuum"
    qml_bridge.selectToolProfile(11)
    assert qml_bridge.advancedControlKind == "scan_probe"
    relevant = [w for w in warnings if "vacuum" in w.lower() or "scan_probe" in w.lower() or "Telemetry" in w]
    assert not relevant, f"QML warnings touching the new telemetry panel: {relevant}"

    print("verify_qt_telemetry_watch: all real assertions passed")


if __name__ == "__main__":
    _run()
