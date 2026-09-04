# =============================================================================
# URTC Tester - real, hardware-free end-to-end check of the Qt Quick
# utility panels (Global Controls / Expansion Board / F-RAM)
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Deliberately kept OUTSIDE tests/ - same real reason as
verify_qt_telemetry_watch.py's own header: needs a real PySide6 event
loop for the real cross-thread Signal delivery every query worker uses.
Run directly: QT_QPA_PLATFORM=offscreen python verify_qt_utility_panels.py

A fake transport (real read_frame/send_frame call shape) answers each
real request with the real documented response shape, from a separate
thread - the real _run_query worker still does its own real polling
read loop against it, exactly like it would against a real SLCAN/
SocketCAN transport.
"""
from __future__ import annotations

import queue
import struct
import sys
import threading
import time

from PySide6.QtGui import QGuiApplication

from qt_tester import TesterQtBridge


class FakeTransport:
    def __init__(self) -> None:
        self.inbox: queue.Queue = queue.Queue()
        self.sent: list[tuple[int, bytes]] = []
        self._lock = threading.Lock()
        self._responders: dict[int, tuple[int, bytes]] = {}

    def respond(self, request_can_id: int, response_data: bytes, response_can_id: int | None = None) -> None:
        """Whenever send_frame(request_can_id, ...) is called, queue this
        real response data - tagged with response_can_id (defaults to
        request_can_id, real for the EEPROM/F-RAM queries that answer on
        the same ID; SPI's own real request/response pair is 0x180/0x181,
        two different real IDs, so it always passes response_can_id
        explicitly)."""
        with self._lock:
            self._responders[request_can_id] = (response_can_id if response_can_id is not None else request_can_id, response_data)

    def read_frame(self, timeout: float = 0.1):
        try:
            return self.inbox.get(timeout=timeout)
        except queue.Empty:
            return None

    def send_frame(self, can_id: int, data: bytes) -> None:
        self.sent.append((can_id, data))
        with self._lock:
            response = self._responders.get(can_id)
        if response is not None:
            self.inbox.put(response)

    def close(self) -> None:
        pass


def _pump_until(app: QGuiApplication, condition, timeout_s: float = 2.0) -> None:
    deadline = time.monotonic() + timeout_s
    while not condition() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.02)


def _run() -> None:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    bridge = TesterQtBridge()
    transport = FakeTransport()

    bridge._transport = transport
    bridge._listen_only = False
    bridge._set_state(status="ACTIVE CHECKS ARMED", busy=False)
    assert bridge.canUseUtilityPanels is True

    # --- Global Controls: fire-and-forget send, real frame shape ---
    bridge.sendGlobalStatus("0", "255", "0", "night", "0", "0", "255", True)
    assert transport.sent[-1] == (0x100, bytes([0, 255, 0, 0x01, 0, 0, 255, 0x01]))

    # A malformed/unknown night mode must be rejected, not silently
    # coerced to some default.
    before = len(transport.sent)
    bridge.sendGlobalStatus("0", "0", "0", "not-a-real-mode", "0", "0", "0", False)
    assert len(transport.sent) == before, "an invalid OLED mode must never reach the transport"

    # --- Expansion Board: SPI passthrough, real request/response ---
    transport.respond(0x180, bytes([2, 0xAA, 0xBB]), response_can_id=0x181)
    bridge.sendExpansionSpi("01 02 03")
    _pump_until(app, lambda: bridge.spiResponseText != "")
    assert bridge.spiResponseText == "aa bb", f"got {bridge.spiResponseText!r}"

    # DIAG0 query
    transport.respond(0x182, bytes([1]), response_can_id=0x183)
    bridge.queryDiag0()
    _pump_until(app, lambda: bridge.diag0Text != "")
    diag0_high = bridge.diag0Text
    assert diag0_high, "a real DIAG0=1 response must produce real display text"

    # --- F-RAM: query state, then a real erase, then re-query ---
    transport.respond(0x190, bytes([1, 5, 0, 0x01, 0x90, 128, 1, 200]), response_can_id=0x191)  # valid, Drill, temp=400
    bridge.queryFramState()
    _pump_until(app, lambda: bridge.framStateText != "")
    assert "400" in bridge.framStateText, f"real temp must appear in the display text, got {bridge.framStateText!r}"

    # Real erase: sends the real magic payload to CAN_ID_ERASE_FRAM
    # (0x192), and the board answers on CAN_ID_FRAM_STATE_RESP (0x191)
    # with its new (now-erased) state - same real CAN ID the plain query
    # above uses, confirming both real paths converge on the one real
    # decoder/property.
    from tester_config import ERASE_FRAM_MAGIC
    transport.respond(0x192, bytes([0, 0, 0, 0, 0, 0, 0, 0]), response_can_id=0x191)  # erased -> valid=0
    bridge.eraseFram()
    _pump_until(app, lambda: "not been saved" in bridge.framStateText or bridge.framStateText != "400" and "400" not in bridge.framStateText)
    assert transport.sent[-1] == (0x192, ERASE_FRAM_MAGIC), "erase must send the real documented magic payload"

    # --- F-RAM tab's own 3 read-only EEPROM queries ---
    transport.respond(0x1A1, bytes([2]))  # a real expansion_type index
    bridge.queryExpansionBoardType()
    _pump_until(app, lambda: bridge.expansionBoardTypeText != "")
    assert bridge.expansionBoardTypeText, "must show a real label, not stay empty"

    transport.respond(0x1A7, bytes([1]))
    bridge.queryMlxSensorVariant()
    _pump_until(app, lambda: bridge.mlxSensorVariantText != "")
    assert bridge.mlxSensorVariantText

    transport.respond(0x1A3, bytes([31, 5]))  # jumpers=0x1F, selection=5 (Vacuum Pickup)
    bridge.queryFreeToolConfig()
    _pump_until(app, lambda: bridge.freeToolConfigText != "")
    assert "Vacuum" in bridge.freeToolConfigText, f"real resolved tool name must appear, got {bridge.freeToolConfigText!r}"

    transport.respond(0x1A5, bytes([0x03, 42]))  # real URTC peripheral, serial 42
    bridge.queryPeripheralInfo()
    _pump_until(app, lambda: bridge.peripheralInfoText != "")
    assert "42" in bridge.peripheralInfoText

    # --- a genuine timeout (no responder registered) must show a real
    # "no response" state, never hang or fabricate a value ---
    bridge._query_texts["diag0"] = ""
    transport._responders.pop(0x182, None)  # remove the earlier real responder - this call must get a genuine timeout
    bridge.queryDiag0()
    _pump_until(app, lambda: bridge.diag0Text != "", timeout_s=2.0)
    assert bridge.diag0Text != "" and bridge.diag0Text != diag0_high, "a real timeout must show its own distinct 'no response' text"

    # --- listen-only mode must block every one of these (unlike
    # telemetry watching, all of these genuinely transmit) ---
    bridge._listen_only = True
    assert bridge.canUseUtilityPanels is False
    before = len(transport.sent)
    bridge.sendGlobalStatus("0", "0", "0", "standard", "0", "0", "0", False)
    bridge.queryFramState()
    assert len(transport.sent) == before, "listen-only must block every real utility-panel transmission"

    # --- QML itself loads with a fresh bridge and shows zero warnings ---
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
    relevant = [w for w in warnings if "Global" in w or "Expansion" in w or "Fram" in w or "fram" in w.lower() or "Utility" in w]
    assert not relevant, f"QML warnings touching the new utility panels: {relevant}"
    assert not warnings, f"QML must load with zero warnings, got: {warnings}"

    print("verify_qt_utility_panels: all real assertions passed")


if __name__ == "__main__":
    _run()
