# =============================================================================
# URTC Tester - Qt Quick live CAN diagnostics command deck
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Qt Quick front end for a deliberately bounded, real tester workflow.

The deck reuses the production SLCAN/SocketCAN classes.  It is read-only by
default.  A bounded one-shot motion command is available only after an
identity match, explicit active mode and a user confirmation in QML.  The full
Tkinter tester remains the default until all 25 per-tool control panels have
Qt Quick parity.
"""
from __future__ import annotations

import struct
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from tester_config import (
    BITRATE_500K_SLCAN_CODE,
    CAN_ID_ACTIVE_TOOL_RESP,
    CAN_ID_MOTION_CMD,
    CAN_ID_QUERY_ACTIVE_TOOL,
    CAN_ID_QUERY_VERSION,
    CAN_ID_VERSION_RESPONSE,
    ICON_IMAGE_PATH,
    TESTER_VERSION,
    THIS_HARDWARE_ID,
    TOOL_NAMES,
    _,
    list_serial_ports,
)
from tester_transports import SLCAN, SocketCAN, list_socketcan_interfaces


class TesterQtBridge(QObject):
    """QML state model backed by the real CAN transports, not mock telemetry."""

    changed = Signal()
    logChanged = Signal()
    _connectionResult = Signal(object, str)
    _probeResult = Signal(object, object, str)
    _passiveResult = Signal(object, str)
    _logRequested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._ports: list[str] = []
        self._socketcan_ports: set[str] = set()
        self._selected_port = ""
        self._transport = None
        self._listen_only = True
        self._busy = False
        self._status = "READ-ONLY READY"
        self._active_tool = "No active probe yet"
        self._active_tool_id = -1
        self._selected_tool_id = 0
        self._version = "No board version received"
        self._passive_frames: list[dict[str, str]] = []
        self._passive_summary = ""
        self._logs: list[str] = []
        self._connectionResult.connect(self._on_connection_result)
        self._probeResult.connect(self._on_probe_result)
        self._passiveResult.connect(self._on_passive_result)
        self._logRequested.connect(self._append_log)
        self.scanPorts()

    @Property(str, constant=True)
    def title(self) -> str:
        return "URTC TESTER"

    @Property(str, constant=True)
    def version(self) -> str:
        return TESTER_VERSION

    @Property(str, constant=True)
    def iconSource(self) -> str:
        return QUrl.fromLocalFile(str(Path(ICON_IMAGE_PATH))).toString()

    @Slot(str, result=str)
    def uiText(self, key: str) -> str:
        """Expose the established .lng lookup to the QML surface."""
        translated = _(key)
        return translated if translated != key else {
            "QT_TRANSPORT_GATE": "TRANSPORT GATE",
            "QT_TRANSPORT_HELP": "Select a serial SLCAN port or a Linux SocketCAN interface.",
            "QT_SAFETY_MODE": "SAFETY MODE",
            "QT_LISTEN_ONLY": "LISTEN-ONLY (NO CAN TX)",
            "QT_ACTIVE_CHECKS_ARMED": "ACTIVE CHECKS ARMED",
            "QT_PASSIVE_HELP": "Passive transport mode. Probe commands are blocked.",
            "QT_ACTIVE_HELP": "Identity probe transmits only documented queries 0x110 and 0x7F8.",
            "QT_STAGED_LIMIT": "The legacy desktop panels remain the authority for advanced actuator workflows. This deck currently exposes only bounded, confirmed motion for matching motion profiles.",
            "QT_IDENTITY_CHECKPOINTS": "IDENTITY & HEALTH CHECKPOINTS",
            "QT_CHECKPOINTS": "1  Connect to the selected production transport\n2  Explicitly arm active checks, if required\n3  Query active tool and board version\n4  Preserve a transparent session log",
            "QT_PROBE": "PROBE ACTIVE TOOL + VERSION",
            "QT_ACTIVE_TOOL": "ACTIVE TOOL",
            "QT_ACTIVITY_LOG": "ACTIVITY LOG",
            "QT_PASSIVE_WINDOW": "PASSIVE BUS WINDOW",
            "QT_PASSIVE_WINDOW_HELP": "Capture live CAN traffic for two seconds. Listen-only mode guarantees no CAN transmission.",
            "QT_CAPTURE_PASSIVE": "CAPTURE PASSIVE WINDOW",
            "QT_NO_PASSIVE_FRAMES": "No passive window captured yet.",
            "QT_TOOL_PROFILE": "TOOL PROFILE",
            "QT_PROFILE_GUARD": "Native controls unlock only when the active identity exactly matches the selected profile and active checks are armed.",
            "QT_MOTION_CONTROL": "ONE-SHOT MOTION",
            "QT_DIRECTION": "DIRECTION",
            "QT_STEPS": "STEPS",
            "QT_SEND_MOTION": "SEND MOTION",
            "QT_PROFILE_NOT_MATCHED": "Select and verify a matching motion profile first.",
            "QT_CONFIRM_MOTION": "CONFIRM MOTION",
            "QT_CONFIRM_MOTION_HELP": "This sends one real CAN motion command to the verified tool. Confirm the machine is clear and its safety interlock is active.",
            "QT_CONFIRM": "CONFIRM",
            "QT_CANCEL": "CANCEL",
        }.get(key, key)

    @Property("QVariantList", notify=changed)
    def ports(self) -> list[str]:
        return self._ports

    @Property(str, notify=changed)
    def selectedPort(self) -> str:
        return self._selected_port

    @Property(bool, notify=changed)
    def connected(self) -> bool:
        return self._transport is not None

    @Property(bool, notify=changed)
    def listenOnly(self) -> bool:
        return self._listen_only

    @Property(bool, notify=changed)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property(str, notify=changed)
    def activeTool(self) -> str:
        return self._active_tool

    @Property(str, notify=changed)
    def boardVersion(self) -> str:
        return self._version

    @Property(int, notify=changed)
    def activeToolId(self) -> int:
        return self._active_tool_id

    @Property(int, notify=changed)
    def selectedToolId(self) -> int:
        return self._selected_tool_id

    @Property("QVariantList", constant=True)
    def toolProfiles(self) -> list[dict[str, object]]:
        """Catalog mirrors every real legacy profile; it is not a fake tool."""
        motion = {1, 2, 3, 6, 7, 12, 16}
        telemetry = {4, 8, 11, 17, 22}
        external = {15, 20}
        return [
            {
                "id": tool_id,
                "name": name,
                "kind": (
                    "motion" if tool_id in motion
                    else "telemetry" if tool_id in telemetry
                    else "external" if tool_id in external
                    else "actuator"
                ),
            }
            for tool_id, name in TOOL_NAMES.items()
        ]

    @Property("QVariantList", notify=changed)
    def passiveFrames(self) -> list[dict[str, str]]:
        return self._passive_frames

    @Property(str, notify=changed)
    def passiveSummary(self) -> str:
        return self._passive_summary

    @Property(bool, notify=changed)
    def hasPassiveSnapshot(self) -> bool:
        return bool(self._passive_summary)

    @Property("QStringList", notify=logChanged)
    def logs(self) -> list[str]:
        return self._logs[-14:]

    @Property(bool, notify=changed)
    def canProbe(self) -> bool:
        return self.connected and not self._listen_only and not self._busy

    @Property(bool, notify=changed)
    def canCapturePassive(self) -> bool:
        return self.connected and self._listen_only and not self._busy

    @Property(bool, notify=changed)
    def canSendMotion(self) -> bool:
        return (
            self.connected
            and not self._listen_only
            and not self._busy
            and self._active_tool_id == self._selected_tool_id
            and self._selected_tool_id in {1, 2, 3, 6, 7, 12, 16}
        )

    def _log(self, message: str) -> None:
        """Queue logs from CAN worker threads onto the Qt GUI thread."""
        self._logRequested.emit(str(message))

    @Slot(str)
    def _append_log(self, message: str) -> None:
        self._logs.append(message)
        self.logChanged.emit()

    def _set_state(self, *, status: str | None = None, busy: bool | None = None) -> None:
        if status is not None:
            self._status = status
        if busy is not None:
            self._busy = busy
        self.changed.emit()

    @Slot()
    def scanPorts(self) -> None:
        if self._transport is not None or self._busy:
            self._log("PORT_SCAN_BLOCKED disconnect before selecting another transport")
            return
        ports = list_serial_ports()
        if sys.platform.startswith("linux"):
            self._socketcan_ports = set(list_socketcan_interfaces())
            ports.extend(name for name in sorted(self._socketcan_ports) if name not in ports)
        else:
            self._socketcan_ports = set()
        self._ports = ports
        if self._selected_port not in ports:
            self._selected_port = ports[0] if ports else ""
        self._log(f"PORT_SCAN count={len(ports)}")
        self.changed.emit()

    @Slot(str)
    def selectPort(self, port: str) -> None:
        if self._transport is None and not self._busy and port in self._ports:
            self._selected_port = port
            self.changed.emit()

    @Slot(bool)
    def setListenOnly(self, enabled: bool) -> None:
        if self._transport is None and not self._busy:
            self._listen_only = enabled
            self._set_state(status="READ-ONLY READY" if enabled else "ACTIVE CHECKS ARMED")
            self._log("MODE_LISTEN_ONLY" if enabled else "MODE_ACTIVE_CHECKS_ARMED")

    @Slot()
    def toggleConnection(self) -> None:
        if self._busy:
            return
        if self._transport is not None:
            try:
                self._transport.close()
            finally:
                self._transport = None
                self._active_tool = "No active probe yet"
                self._active_tool_id = -1
                self._version = "No board version received"
                self._passive_frames = []
                self._passive_summary = ""
                self._set_state(status="DISCONNECTED")
                self._log("TRANSPORT_DISCONNECTED")
            return
        if not self._selected_port:
            self._log("ERROR select a serial or SocketCAN interface first")
            return
        self._set_state(status="CONNECTING", busy=True)
        threading.Thread(target=self._connect_worker, daemon=True, name="urtc-tester-qt-connect").start()

    def _connect_worker(self) -> None:
        try:
            if self._selected_port in self._socketcan_ports:
                transport = SocketCAN(self._selected_port, log=self._log)
                transport.open_channel(listen_only=self._listen_only)
            else:
                transport = SLCAN(self._selected_port, log=self._log)
                transport.open_channel(BITRATE_500K_SLCAN_CODE, listen_only=self._listen_only)
            self._connectionResult.emit(transport, "")
        except Exception as exc:
            self._connectionResult.emit(None, str(exc))

    def _on_connection_result(self, transport, error: str) -> None:
        self._transport = transport
        if error:
            self._set_state(status="CONNECTION FAILED", busy=False)
            self._log(f"CONNECTION_FAILED {error}")
        else:
            mode = "LISTEN-ONLY" if self._listen_only else "ACTIVE CHECKS"
            self._set_state(status=f"CONNECTED {mode}", busy=False)
            self._log(f"TRANSPORT_CONNECTED port={self._selected_port} mode={mode}")

    @Slot()
    def probeIdentity(self) -> None:
        if not self.canProbe:
            self._log("PROBE_BLOCKED connect first and explicitly disable listen-only")
            return
        self._set_state(status="PROBING IDENTITY", busy=True)
        self._log("PROBE_STARTED ids=0x110,0x7F8")
        threading.Thread(target=self._probe_worker, daemon=True, name="urtc-tester-qt-probe").start()

    @Slot(int)
    def selectToolProfile(self, tool_id: int) -> None:
        if tool_id in TOOL_NAMES and not self._busy:
            self._selected_tool_id = tool_id
            self.changed.emit()

    @Slot(str, str)
    def sendMotion(self, direction: str, steps_text: str) -> None:
        """Send only the established bounded one-shot 0x120 motion protocol.

        QML asks the operator for a second, explicit confirmation immediately
        before calling this slot.  Backend gates remain mandatory so a forged
        or stale UI state cannot bypass the profile, transport or active-mode
        checks.
        """
        if not self.canSendMotion:
            self._log("MOTION_BLOCKED profile identity/active-check gate not satisfied")
            return
        try:
            steps = int(steps_text)
        except ValueError:
            self._log("MOTION_BLOCKED steps must be an integer")
            return
        if not 1 <= steps <= 0xFFFFFFFF:
            self._log("MOTION_BLOCKED steps outside 1..4294967295")
            return
        transport = self._transport
        if transport is None:
            return
        try:
            direction_byte = 0x01 if direction == "forward" else 0x00
            transport.send_frame(CAN_ID_MOTION_CMD, bytes([direction_byte]) + struct.pack(">I", steps))
            self._log(
                f"MOTION_SENT profile={self._selected_tool_id} "
                f"direction={direction} steps={steps}"
            )
        except Exception as exc:
            self._log(f"MOTION_FAILED {exc}")

    @Slot()
    def capturePassiveWindow(self) -> None:
        """Capture a bounded read-only CAN window while listen-only is active."""
        if not self.canCapturePassive:
            self._log("PASSIVE_CAPTURE_BLOCKED connect in listen-only mode first")
            return
        transport = self._transport
        if transport is None:
            return
        self._set_state(status="CAPTURING PASSIVE WINDOW", busy=True)
        self._log("PASSIVE_CAPTURE_STARTED duration_s=2.0 tx=0")
        threading.Thread(
            target=self._passive_capture_worker,
            args=(transport,),
            daemon=True,
            name="urtc-tester-qt-passive-capture",
        ).start()

    def _passive_capture_worker(self, transport) -> None:
        deadline = time.monotonic() + 2.0
        count = 0
        identifiers: set[int] = set()
        frames: list[dict[str, str]] = []
        try:
            while time.monotonic() < deadline:
                frame = transport.read_frame(timeout=0.1)
                if frame is None:
                    continue
                can_id, data = frame
                count += 1
                identifiers.add(can_id)
                frames.append(
                    {
                        "id": f"0x{can_id:03X}",
                        "data": data.hex(" ").upper() or "(empty)",
                    }
                )
                if len(frames) > 24:
                    frames.pop(0)
            summary = f"2.0 s • {count} frame(s) • {len(identifiers)} CAN ID(s)"
            self._passiveResult.emit(frames, summary)
        except Exception as exc:
            self._passiveResult.emit([], f"PASSIVE_CAPTURE_FAILED {exc}")

    @Slot(object, str)
    def _on_passive_result(self, frames: list[dict[str, str]], summary: str) -> None:
        self._passive_frames = frames
        self._passive_summary = summary
        if summary.startswith("PASSIVE_CAPTURE_FAILED"):
            self._set_state(status="PASSIVE CAPTURE FAILED", busy=False)
            self._log(summary)
        else:
            self._set_state(status="PASSIVE WINDOW COMPLETE", busy=False)
            self._log(f"PASSIVE_CAPTURE_COMPLETE {summary}")

    def _wait_for(self, can_id: int, timeout: float) -> bytes | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            frame = self._transport.read_frame(timeout=0.1)
            if frame is not None and frame[0] == can_id:
                return frame[1]
        return None

    def _probe_worker(self) -> None:
        try:
            transport = self._transport
            if transport is None:
                raise RuntimeError("transport disconnected before identity probe")
            transport.send_frame(CAN_ID_QUERY_ACTIVE_TOOL, b"")
            tool_data = self._wait_for(CAN_ID_ACTIVE_TOOL_RESP, 1.5)
            transport.send_frame(CAN_ID_QUERY_VERSION, b"\x00")
            version_data = self._wait_for(CAN_ID_VERSION_RESPONSE, 1.5)
            self._probeResult.emit(tool_data, version_data, "")
        except Exception as exc:
            self._probeResult.emit(None, None, str(exc))

    def _on_probe_result(self, tool_data, version_data, error: str) -> None:
        if error:
            self._set_state(status="PROBE FAILED", busy=False)
            self._log(f"PROBE_FAILED {error}")
            return
        if tool_data is not None and len(tool_data) >= 4:
            tool_id, critical, can_error, booting = tool_data[:4]
            name = TOOL_NAMES.get(tool_id, f"Unknown tool {tool_id}")
            state = "CRITICAL" if critical else ("CAN ERROR" if can_error else ("BOOTING" if booting else "NORMAL"))
            self._active_tool = f"{name} (ID {tool_id}) - {state}"
            self._active_tool_id = tool_id
            self._log(f"ACTIVE_TOOL id={tool_id} name={name} state={state}")
        else:
            self._active_tool = "No response to active-tool query"
            self._active_tool_id = -1
            self._log("ACTIVE_TOOL no response")
        if version_data is not None and len(version_data) >= 8:
            role = "bootloader" if version_data[0] == 0x01 else "application"
            hardware_id = struct.unpack(">I", version_data[1:5])[0]
            major = struct.unpack(">H", version_data[5:7])[0]
            minor = version_data[7]
            identity = "MATCH" if hardware_id == THIS_HARDWARE_ID else "DIFFERENT BOARD"
            self._version = f"{role} v{major}.{minor} - HW 0x{hardware_id:08X} ({identity})"
            self._log(f"BOARD_VERSION {self._version}")
        else:
            self._version = "No response to version query"
            self._log("BOARD_VERSION no response")
        outcome = "PROBE COMPLETE" if tool_data is not None or version_data is not None else "NO RESPONSE"
        self._set_state(status=outcome, busy=False)


def run_qtquick() -> int:
    """Run the explicit, bounded Qt Quick diagnostics deck."""
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("URTC Tester")
    icon = QIcon(ICON_IMAGE_PATH)
    if not icon.isNull():
        app.setWindowIcon(icon)
    bridge = TesterQtBridge()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("testerBackend", bridge)
    qml_path = Path(__file__).resolve().parent / "assets" / "qml" / "TesterDeck.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1
    return app.exec()
