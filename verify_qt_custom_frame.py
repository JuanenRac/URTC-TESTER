# =============================================================================
# URTC Tester - real, hardware-free end-to-end check of the Qt Quick
# Custom CAN Frame panel (manual send + QML-Timer-owned periodic resend)
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Deliberately kept OUTSIDE tests/ - same real reason as
verify_qt_utility_panels.py's own header: exercises the real bridge
against a fake transport with a real Qt event loop present. Run
directly: QT_QPA_PLATFORM=offscreen python verify_qt_custom_frame.py
"""
from __future__ import annotations

import sys

from PySide6.QtGui import QGuiApplication

from qt_tester import TesterQtBridge


class FakeTransport:
    def __init__(self) -> None:
        self.sent: list[tuple[int, bytes]] = []

    def read_frame(self, timeout: float = 0.1):
        return None

    def send_frame(self, can_id: int, data: bytes) -> None:
        self.sent.append((can_id, data))

    def close(self) -> None:
        pass


def _run() -> None:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    bridge = TesterQtBridge()
    transport = FakeTransport()
    bridge._transport = transport
    bridge._listen_only = False
    bridge._set_state(status="ACTIVE CHECKS ARMED", busy=False)
    assert bridge.canUseUtilityPanels is True

    # --- manual "Send Once" ---
    bridge.sendCustomFrame("100", "01 02 03")
    assert transport.sent[-1] == (0x100, bytes([0x01, 0x02, 0x03]))
    sent_before = len(transport.sent)
    assert any("CUSTOM_FRAME_SENT" in line for line in bridge.logs), "manual send must log, unlike periodic ticks"

    # --- bad hex must be rejected, never reach the transport ---
    bridge.sendCustomFrame("zzz", "01")
    assert len(transport.sent) == sent_before, "malformed CAN ID must never reach the transport"
    assert any("CUSTOM_FRAME_BLOCKED" in line for line in bridge.logs)

    # --- out-of-range ID / oversized payload rejected ---
    bridge.sendCustomFrame("800", "")  # 0x800 is outside the 11-bit range
    assert len(transport.sent) == sent_before
    bridge.sendCustomFrame("100", "01 02 03 04 05 06 07 08 09")  # 9 bytes
    assert len(transport.sent) == sent_before

    # --- periodic toggle-on: validates once, flips the backend-owned flag ---
    assert bridge.customFramePeriodicActive is False
    bridge.setCustomFramePeriodic(True, "200", "AA", "50")
    assert bridge.customFramePeriodicActive is True
    assert any("CUSTOM_FRAME_PERIODIC_STARTED" in line for line in bridge.logs)

    # --- each tick sends silently (no new log line) ---
    logs_before = len(bridge.logs)
    for _ in range(5):
        bridge.sendCustomFramePeriodicTick("200", "AA")
    assert transport.sent[-1] == (0x200, bytes([0xAA]))
    assert len(bridge.logs) == logs_before, "periodic ticks must stay silent on an ordinary successful send"

    # --- a tick with now-invalid fields logs once on the transition, then stays silent ---
    bridge.sendCustomFramePeriodicTick("zzz", "AA")
    after_first_bad_tick = len(bridge.logs)
    assert any("CUSTOM_FRAME_PERIODIC_SKIPPING" in line for line in bridge.logs)
    bridge.sendCustomFramePeriodicTick("zzz", "AA")
    bridge.sendCustomFramePeriodicTick("zzz", "AA")
    assert len(bridge.logs) == after_first_bad_tick, "repeated bad ticks must not spam the log"

    # --- recovering back to valid fields logs the resume transition once ---
    bridge.sendCustomFramePeriodicTick("200", "BB")
    assert any("CUSTOM_FRAME_PERIODIC_RESUMING" in line for line in bridge.logs)
    assert transport.sent[-1] == (0x200, bytes([0xBB]))

    # --- toggle-off flips the flag back, Timer's running binding follows it ---
    bridge.setCustomFramePeriodic(False, "200", "AA", "50")
    assert bridge.customFramePeriodicActive is False

    # --- toggling on while disconnected/listen-only must be rejected, not silently armed ---
    bridge._listen_only = True
    bridge.setCustomFramePeriodic(True, "100", "01", "50")
    assert bridge.customFramePeriodicActive is False, "listen-only must block arming periodic send"
    bridge._listen_only = False

    # --- disconnecting must force periodic off, mirroring _stop_all_watchdogs ---
    bridge.setCustomFramePeriodic(True, "100", "01", "50")
    assert bridge.customFramePeriodicActive is True
    bridge.toggleConnection()  # real disconnect path (transport is set, not None)
    assert bridge.customFramePeriodicActive is False, "disconnect must stop periodic custom-frame resend"

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
    assert not warnings, f"QML must load with zero warnings, got: {warnings}"

    print("verify_qt_custom_frame: all real assertions passed")


if __name__ == "__main__":
    _run()
