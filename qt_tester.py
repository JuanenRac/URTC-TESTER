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
    CAN_ID_AOI_CMD,
    CAN_ID_3DP_HOTEND_FAN_CMD,
    CAN_ID_3DP_LAYER_FAN_CMD,
    CAN_ID_3DP_THERMAL_MOTION,
    CAN_ID_ADS1115_CONFIG,
    CAN_ID_ADS1115_RESULT,
    CAN_ID_ADS1115_TRIGGER,
    CAN_ID_CRIMPING_CMD,
    CAN_ID_DRILL_CMD,
    CAN_ID_ELECTROMAGNET_CMD,
    CAN_ID_HOTAIR_CMD,
    CAN_ID_LASER_CMD,
    CAN_ID_MOTION_CMD,
    CAN_ID_PASTE_JETTING_CONFIG,
    CAN_ID_PASTE_JETTING_PULSE,
    CAN_ID_QUERY_ACTIVE_TOOL,
    CAN_ID_QUERY_VERSION,
    CAN_ID_SPOT_WELD_CMD,
    CAN_ID_SOLDER_SETPOINT,
    CAN_ID_UV_CURING_CMD,
    CAN_ID_VERSION_RESPONSE,
    CAN_ID_ULTRASONIC_WELD_CMD,
    CAN_ID_THERMAL_CALIB_CHUNK,
    CAN_ID_THERMAL_CALIB_CHUNK_REQ,
    CAN_ID_THERMAL_TRIGGER,
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
    _flyingProbeResult = Signal(str, str)
    _thermalResult = Signal(object, str)
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
        self._flying_probe_result = "No ADS1115 result read yet"
        self._thermal_cells: list[dict[str, object]] = []
        self._thermal_summary = "No thermal frame captured yet"
        self._logs: list[str] = []
        self._watchdog_stops: dict[str, threading.Event] = {}
        self._watchdog_off_frames: dict[str, tuple[int, bytes]] = {}
        self._connectionResult.connect(self._on_connection_result)
        self._probeResult.connect(self._on_probe_result)
        self._passiveResult.connect(self._on_passive_result)
        self._flyingProbeResult.connect(self._on_flying_probe_result)
        self._thermalResult.connect(self._on_thermal_result)
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
            "QT_ADVANCED_CONTROL": "ADVANCED PROFILE CONTROL",
            "QT_ADVANCED_UNAVAILABLE": "This verified profile has telemetry-only, external-machine or watchdog-controlled functions. Its full established panel remains available in the desktop application.",
            "QT_DRILL_SPEED": "DRILL SPEED (0-255)",
            "QT_DRILL_DIRECTION": "DRILL DIRECTION",
            "QT_AOI_MODE": "AOI RING MODE",
            "QT_AOI_PERIOD": "STROBE PERIOD (us)",
            "QT_MAGNET_STATE": "ELECTROMAGNET STATE",
            "QT_PULSE_DURATION": "PULSE DURATION (ms)",
            "QT_PASTE_CHANNEL": "PWM CHANNEL (0-3)",
            "QT_PASTE_FREQUENCY": "FREQUENCY (Hz)",
            "QT_PASTE_DUTY": "DUTY (%)",
            "QT_CONFIGURE": "CONFIGURE",
            "QT_FIRE_PULSE": "FIRE PULSE",
            "QT_ENERGIZE": "ENERGIZE",
            "QT_RELEASE": "RELEASE",
            "QT_CONFIRM_ACTION": "CONFIRM PHYSICAL ACTION",
            "QT_CONFIRM_ACTION_HELP": "This transmits a real command to the verified tool. Confirm the work area is clear and all physical interlocks are active.",
            "QT_HEATER_SETPOINT": "HEATER SETPOINT (C)",
            "QT_BLOWER_POWER": "BLOWER POWER (0-255)",
            "QT_LASER_POWER": "LASER POWER (0-255)",
            "QT_INTERLOCK_ARMED": "INTERLOCK ARMED",
            "QT_LAYER_FAN_POWER": "LAYER FAN POWER (0-255)",
            "QT_HOTEND_FAN_POWER": "HOTEND FAN POWER (0-255)",
            "QT_WATCHDOG_ENABLE": "ENABLE WATCHDOG OUTPUT",
            "QT_WATCHDOG_DISABLE": "STOP / SEND SAFE OFF",
            "QT_ADS_CONFIG": "ADS1115 CONFIG (hex)",
            "QT_TRIGGER": "TRIGGER",
            "QT_READ_RESULT": "READ RESULT",
            "QT_THERMAL_CAPTURE": "CAPTURE THERMAL FRAME",
            "QT_NO_THERMAL_FRAME": "No thermal frame captured yet.",
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
        motion = {0, 1, 2, 3, 6, 7, 12, 16, 21}
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
            and self._selected_tool_id in {0, 1, 2, 3, 6, 7, 12, 16, 21}
        )

    @Property(bool, notify=changed)
    def canActuateSelectedProfile(self) -> bool:
        """Shared backend gate for every advanced QML action."""
        return (
            self.connected
            and not self._listen_only
            and not self._busy
            and self._active_tool_id == self._selected_tool_id
        )

    @Property(str, notify=changed)
    def advancedControlKind(self) -> str:
        """Expose only the real one-shot protocol families migrated so far."""
        return {
            5: "drill",
            8: "aoi",
            13: "magnet",
            14: "pulse",
            23: "paste",
            24: "pulse",
            0: "solder",
            9: "laser",
            10: "printer",
            18: "uv",
            19: "hotair",
            17: "flying",
            22: "thermal",
        }.get(self._selected_tool_id, "unavailable")

    @Property("QStringList", notify=changed)
    def activeWatchdogs(self) -> list[str]:
        """Visible state only; never fabricates device telemetry."""
        return sorted(self._watchdog_stops)

    @Property(str, notify=changed)
    def flyingProbeResult(self) -> str:
        return self._flying_probe_result

    @Property("QVariantList", notify=changed)
    def thermalCells(self) -> list[dict[str, object]]:
        return self._thermal_cells

    @Property(str, notify=changed)
    def thermalSummary(self) -> str:
        return self._thermal_summary


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
            self._stop_all_watchdogs()
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
            command_id = CAN_ID_CRIMPING_CMD if self._selected_tool_id == 21 else CAN_ID_MOTION_CMD
            transport.send_frame(command_id, bytes([direction_byte]) + struct.pack(">I", steps))
            self._log(
                f"MOTION_SENT profile={self._selected_tool_id} "
                f"can_id=0x{command_id:03X} direction={direction} steps={steps}"
            )
        except Exception as exc:
            self._log(f"MOTION_FAILED {exc}")

    def _require_profile(self, allowed: set[int], action: str) -> bool:
        if not self.canActuateSelectedProfile or self._selected_tool_id not in allowed:
            self._log(f"{action}_BLOCKED profile identity/active-check gate not satisfied")
            return False
        return self._transport is not None

    def _stop_watchdog(self, key: str, off_frame: tuple[int, bytes] | None = None) -> None:
        stop = self._watchdog_stops.pop(key, None)
        if stop is not None:
            stop.set()
        if off_frame is None:
            off_frame = self._watchdog_off_frames.get(key)
        self._watchdog_off_frames.pop(key, None)
        self.changed.emit()
        transport = self._transport
        if off_frame is not None and transport is not None:
            try:
                transport.send_frame(*off_frame)
            except Exception as exc:
                self._log(f"WATCHDOG_SAFE_OFF_FAILED key={key} error={exc}")

    def _stop_all_watchdogs(self) -> None:
        for key in list(self._watchdog_stops):
            self._stop_watchdog(key)

    def _start_watchdog(
        self,
        key: str,
        interval_s: float,
        frame: tuple[int, bytes],
        off_frame: tuple[int, bytes],
    ) -> None:
        self._stop_watchdog(key)
        stop = threading.Event()
        self._watchdog_stops[key] = stop
        self._watchdog_off_frames[key] = off_frame
        self.changed.emit()
        transport = self._transport
        if transport is None:
            return

        def _worker() -> None:
            while not stop.is_set():
                try:
                    transport.send_frame(*frame)
                except Exception as exc:
                    self._log(f"WATCHDOG_FAILED key={key} error={exc}")
                    stop.set()
                    break
                stop.wait(interval_s)
            if self._watchdog_stops.get(key) is stop:
                self._watchdog_stops.pop(key, None)
                self._watchdog_off_frames.pop(key, None)
                self.changed.emit()

        threading.Thread(target=_worker, daemon=True, name=f"urtc-tester-{key}-watchdog").start()
        self._log(f"WATCHDOG_STARTED key={key} can_id=0x{frame[0]:03X} interval_ms={int(interval_s * 1000)}")

    @Slot(str, bool, str, str)
    def setWatchdogOutput(self, kind: str, enabled: bool, first_text: str, second_text: str) -> None:
        """Run only the watchdog protocol already used by the legacy panel.

        The selected, probed profile is checked in the backend for each
        family. A stop always sends that family's documented safe-off frame.
        """
        schemas = {
            "solder": (0, "solder", 0.15, CAN_ID_SOLDER_SETPOINT, 0, 450),
            "laser": (9, "laser", 0.15, CAN_ID_LASER_CMD, 0, 255),
            "printer_heater": (10, "printer_heater", 0.15, CAN_ID_3DP_THERMAL_MOTION, 0, 300),
            "layer_fan": (10, "layer_fan", 0.4, CAN_ID_3DP_LAYER_FAN_CMD, 0, 255),
            "uv": (18, "uv", 0.15, CAN_ID_UV_CURING_CMD, 0, 255),
            "hotair": (19, "hotair", 0.15, CAN_ID_HOTAIR_CMD, 0, 450),
        }
        schema = schemas.get(kind)
        if schema is None or not self._require_profile({schema[0]}, "WATCHDOG"):
            return
        value = self._bounded_int(first_text, schema[4], schema[5])
        secondary = self._bounded_int(second_text, 0, 255)
        if value is None or secondary is None:
            self._log("WATCHDOG_BLOCKED invalid numeric parameters")
            return
        profile_id, key, interval_s, command_id, _minimum, _maximum = schema
        del profile_id, _minimum, _maximum
        if kind == "solder":
            frame, off = (command_id, struct.pack(">H", value)), (command_id, struct.pack(">H", 0))
        elif kind == "laser":
            # Legacy protocol accepts the interlock bit as its second byte.
            frame, off = (command_id, bytes([value, 0x01 if secondary else 0x00])), (command_id, b"\x00\x00")
        elif kind == "printer_heater":
            frame, off = (command_id, struct.pack(">H", value) + b"\x01\x00\x00\x00"), (command_id, b"\x00\x01\x00\x00\x00")
        elif kind == "layer_fan":
            frame, off = (command_id, bytes([value])), (command_id, b"\x00")
        elif kind == "uv":
            frame, off = (command_id, bytes([value])), (command_id, b"\x00")
        else:  # hotair
            frame, off = (command_id, struct.pack(">H", value) + bytes([secondary])), (command_id, b"\x00\x00\x00")
        if enabled:
            self._start_watchdog(key, interval_s, frame, off)
        else:
            self._stop_watchdog(key, off)
            self._log(f"WATCHDOG_STOPPED key={key} safe_off=1")

    @staticmethod
    def _bounded_int(value: str, minimum: int, maximum: int) -> int | None:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return min(maximum, max(minimum, parsed))

    @Slot(str, str)
    def sendDrill(self, speed_text: str, direction: str) -> None:
        if not self._require_profile({5}, "DRILL"):
            return
        speed = self._bounded_int(speed_text, 0, 255)
        if speed is None:
            self._log("DRILL_BLOCKED speed must be an integer")
            return
        try:
            self._transport.send_frame(
                CAN_ID_DRILL_CMD,
                bytes([speed, 0x01 if direction == "counter-clockwise" else 0x00]),
            )
            self._log(f"DRILL_SENT speed={speed} direction={direction}")
        except Exception as exc:
            self._log(f"DRILL_FAILED {exc}")

    @Slot(str, str)
    def sendAoi(self, mode: str, period_text: str) -> None:
        if not self._require_profile({8}, "AOI"):
            return
        period = self._bounded_int(period_text, 1, 65535)
        mode_byte = {"off": 0x00, "strobe": 0x01, "continuous": 0x02}.get(mode)
        if period is None or mode_byte is None:
            self._log("AOI_BLOCKED invalid mode or strobe period")
            return
        try:
            self._transport.send_frame(CAN_ID_AOI_CMD, bytes([mode_byte]) + struct.pack(">H", period))
            self._log(f"AOI_SENT mode={mode} period_us={period}")
        except Exception as exc:
            self._log(f"AOI_FAILED {exc}")

    @Slot(bool)
    def setElectromagnet(self, energized: bool) -> None:
        if not self._require_profile({13}, "ELECTROMAGNET"):
            return
        try:
            self._transport.send_frame(CAN_ID_ELECTROMAGNET_CMD, bytes([0x01 if energized else 0x00]))
            self._log(f"ELECTROMAGNET_SENT state={'energized' if energized else 'released'}")
        except Exception as exc:
            self._log(f"ELECTROMAGNET_FAILED {exc}")

    @Slot(str)
    def fireWeldPulse(self, duration_text: str) -> None:
        if not self._require_profile({14, 24}, "WELD_PULSE"):
            return
        duration = self._bounded_int(duration_text, 1, 2000)
        if duration is None:
            self._log("WELD_PULSE_BLOCKED duration must be an integer")
            return
        command_id = CAN_ID_SPOT_WELD_CMD if self._selected_tool_id == 14 else CAN_ID_ULTRASONIC_WELD_CMD
        try:
            self._transport.send_frame(command_id, bytes([0x01]) + struct.pack(">H", duration))
            self._log(f"WELD_PULSE_SENT profile={self._selected_tool_id} duration_ms={duration}")
        except Exception as exc:
            self._log(f"WELD_PULSE_FAILED {exc}")

    @Slot(str, str)
    def configurePasteJetting(self, channel_text: str, frequency_text: str) -> None:
        if not self._require_profile({23}, "PASTE_CONFIG"):
            return
        channel = self._bounded_int(channel_text, 0, 3)
        frequency = self._bounded_int(frequency_text, 1, 65535)
        if channel is None or frequency is None:
            self._log("PASTE_CONFIG_BLOCKED channel/frequency must be integers")
            return
        try:
            self._transport.send_frame(CAN_ID_PASTE_JETTING_CONFIG, bytes([channel]) + struct.pack(">H", frequency))
            self._log(f"PASTE_CONFIG_SENT channel={channel} frequency_hz={frequency}")
        except Exception as exc:
            self._log(f"PASTE_CONFIG_FAILED {exc}")

    @Slot(str, str, str)
    def firePastePulse(self, channel_text: str, duty_text: str, duration_text: str) -> None:
        if not self._require_profile({23}, "PASTE_PULSE"):
            return
        channel = self._bounded_int(channel_text, 0, 3)
        duty = self._bounded_int(duty_text, 0, 100)
        duration = self._bounded_int(duration_text, 0, 255)
        if channel is None or duty is None or duration is None:
            self._log("PASTE_PULSE_BLOCKED channel/duty/duration must be integers")
            return
        try:
            self._transport.send_frame(CAN_ID_PASTE_JETTING_PULSE, bytes([channel, duty, duration]))
            self._log(f"PASTE_PULSE_SENT channel={channel} duty={duty} duration_ms={duration}")
        except Exception as exc:
            self._log(f"PASTE_PULSE_FAILED {exc}")

    @Slot(str, str, str)
    def sendPrinterOneShot(self, action: str, first_text: str, second_text: str) -> None:
        """Port the non-watchdog printer commands without repeating motion."""
        if not self._require_profile({10}, "PRINTER"):
            return
        if action == "hotend_fan":
            power = self._bounded_int(first_text, 0, 255)
            if power is None:
                self._log("PRINTER_BLOCKED hotend fan power must be an integer")
                return
            frame = (CAN_ID_3DP_HOTEND_FAN_CMD, bytes([power]))
        elif action == "extruder":
            steps = self._bounded_int(first_text, 0, 0xFFFFFF)
            temperature = self._bounded_int(second_text, 0, 300)
            if steps is None or temperature is None:
                self._log("PRINTER_BLOCKED extruder steps/temperature must be integers")
                return
            frame = (
                CAN_ID_3DP_THERMAL_MOTION,
                struct.pack(">H", temperature) + b"\x01" + steps.to_bytes(3, "big"),
            )
        else:
            self._log(f"PRINTER_BLOCKED unknown one-shot action={action}")
            return
        try:
            self._transport.send_frame(*frame)
            self._log(f"PRINTER_SENT action={action} can_id=0x{frame[0]:03X}")
        except Exception as exc:
            self._log(f"PRINTER_FAILED action={action} error={exc}")

    @Slot(str)
    def configureFlyingProbe(self, config_text: str) -> None:
        if not self._require_profile({17}, "FLYING_PROBE_CONFIG"):
            return
        try:
            config = int(config_text, 16) & 0xFFFF
            self._transport.send_frame(CAN_ID_ADS1115_CONFIG, struct.pack(">H", config))
            self._log(f"FLYING_PROBE_CONFIG_SENT value=0x{config:04X}")
        except ValueError:
            self._log("FLYING_PROBE_CONFIG_BLOCKED config must be hexadecimal")
        except Exception as exc:
            self._log(f"FLYING_PROBE_CONFIG_FAILED {exc}")

    @Slot()
    def triggerFlyingProbe(self) -> None:
        if not self._require_profile({17}, "FLYING_PROBE_TRIGGER"):
            return
        try:
            self._transport.send_frame(CAN_ID_ADS1115_TRIGGER, b"")
            self._log("FLYING_PROBE_TRIGGER_SENT")
        except Exception as exc:
            self._log(f"FLYING_PROBE_TRIGGER_FAILED {exc}")

    @Slot()
    def readFlyingProbe(self) -> None:
        if not self._require_profile({17}, "FLYING_PROBE_READ"):
            return
        self._set_state(status="READING FLYING PROBE", busy=True)
        threading.Thread(target=self._read_flying_probe_worker, args=(self._transport,), daemon=True, name="urtc-flying-probe-read").start()

    def _read_flying_probe_worker(self, transport) -> None:
        try:
            transport.send_frame(CAN_ID_ADS1115_RESULT, b"")
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline:
                frame = transport.read_frame(timeout=0.1)
                if frame is not None and frame[0] == CAN_ID_ADS1115_RESULT and len(frame[1]) >= 2:
                    self._flyingProbeResult.emit(str(struct.unpack(">h", frame[1][:2])[0]), "")
                    return
            self._flyingProbeResult.emit("", "No ADS1115 response within 1.0 s")
        except Exception as exc:
            self._flyingProbeResult.emit("", str(exc))

    @Slot(str, str)
    def _on_flying_probe_result(self, result: str, error: str) -> None:
        self._flying_probe_result = f"{result} raw counts" if not error else error
        self._set_state(status="FLYING PROBE READ COMPLETE" if not error else "FLYING PROBE READ FAILED", busy=False)
        self._log(f"FLYING_PROBE_RESULT {self._flying_probe_result}")

    @staticmethod
    def _thermal_color(centi_c: int) -> str:
        """Match the established 0-100 C blue-to-red diagnostic gradient."""
        fraction = max(0.0, min(1.0, centi_c / 10000.0))
        red = int(255 * fraction)
        blue = int(255 * (1 - fraction))
        green = int(128 * (1 - abs(fraction - 0.5) * 2))
        return f"#{red:02x}{green:02x}{blue:02x}"

    @Slot()
    def captureThermalFrame(self) -> None:
        if not self._require_profile({22}, "THERMAL_CAPTURE"):
            return
        self._set_state(status="CAPTURING THERMAL FRAME", busy=True)
        threading.Thread(target=self._capture_thermal_worker, args=(self._transport,), daemon=True, name="urtc-thermal-capture").start()

    def _capture_thermal_worker(self, transport) -> None:
        """Read the documented calibrated 32x24 frame without a write path."""
        cells: list[dict[str, object]] = []
        chunks = 0
        try:
            transport.send_frame(CAN_ID_THERMAL_TRIGGER, b"")
            for chunk_index in range(48):
                frames: list[bytes] = []
                for attempt in range(4):
                    if not frames:
                        transport.send_frame(CAN_ID_THERMAL_CALIB_CHUNK_REQ, bytes([chunk_index]))
                    deadline = time.monotonic() + 0.3
                    while time.monotonic() < deadline:
                        frame = transport.read_frame(timeout=0.05)
                        if frame is not None and frame[0] == CAN_ID_THERMAL_CALIB_CHUNK and len(frame[1]) == 8:
                            frames.append(frame[1])
                            break
                    if len(frames) == 4:
                        break
                if len(frames) != 4:
                    continue
                chunks += 1
                for pixel in range(16):
                    temperature = struct.unpack(">h", b"".join(frames)[pixel * 2:pixel * 2 + 2])[0]
                    cells.append({"temperature": temperature, "color": self._thermal_color(temperature)})
            self._thermalResult.emit(cells, f"THERMAL_CAPTURE chunks={chunks}/48 cells={len(cells)}")
        except Exception as exc:
            self._thermalResult.emit([], f"THERMAL_CAPTURE_FAILED {exc}")

    @Slot(object, str)
    def _on_thermal_result(self, cells: list[dict[str, object]], summary: str) -> None:
        self._thermal_cells = cells
        self._thermal_summary = summary
        failed = summary.startswith("THERMAL_CAPTURE_FAILED")
        self._set_state(status="THERMAL CAPTURE FAILED" if failed else "THERMAL CAPTURE COMPLETE", busy=False)
        self._log(summary)

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
