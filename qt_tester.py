# =============================================================================
# URTC Tester - Qt Quick live CAN diagnostics command deck
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Qt Quick front end for the real tester workflow - the app's own default.

The deck reuses the production SLCAN/SocketCAN classes.  It is read-only by
default.  Every real command is gated on an identity match, explicit active
mode and a user confirmation in QML.  Every one of the 25 real tool profiles'
own commands has real, wired coverage here: motion (the 8 profiles sharing
the plain-stepper 0x120/0x1F0 protocol), drill, AOI, electromagnet, spot/
ultrasonic weld pulse, paste jetting, flying probe, thermal inspection, the
5 watchdog-keepalive actuators (solder iron, laser, the printer's own heater
and layer fan, UV curing, hot-air rework - see `setWatchdogOutput()`) and
vacuum/scan-probe telemetry.  Conformal Coating and Press-Fit Inserter have
no command panel here (the deck says so in words, `noHandlerText`) -
neither has a real CAN command of its own to expose.
The deck has not been checked against a real board yet - this whole project
was built with no USB access (see README.md's own "Known limitations") -
so being the default here is not a hardware-proven claim.
"""
from __future__ import annotations

import collections
import json
import os
import platform
import struct
import sys
import threading
import time
import zipfile
from pathlib import Path

import advanced_protocol as protocol
import tester_extras as extras
from tester_bus_monitor import FrameFilter
import tester_telemetry as tele
from tester_selftest import run_self_test
from tester_trace_export import render as render_trace
from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

import tester_config
from tester_config import (
    _current_language,
    AOI_STROBE_MAX_MS,
    SETPOINT_MAX_C,
    LOGS_FOLDER,
    BITRATE_500K_SLCAN_CODE,
    SLCAN_BITRATES,
    bitrate_bps_for_label,
    load_config,
    save_config,
    translate_log_line,
    CAN_ID_ACTIVE_TOOL_RESP,
    CAN_ID_3DP_LAYER_FAN_CMD,
    CAN_ID_3DP_THERMAL_MOTION,
    CAN_ID_ADS1115_CONFIG,
    CAN_ID_ADS1115_RESULT,
    CAN_ID_ADS1115_TRIGGER,
    CAN_ID_DIAG0_RESP,
    CAN_ID_DRILL_CMD,
    CAN_ID_ERASE_FRAM,
    CAN_ID_EXP_SPI_RESP,
    CAN_ID_EXPANSION_TYPE_RESP,
    CAN_ID_FRAM_STATE_RESP,
    CAN_ID_FREE_TOOL_CONFIG_RESP,
    CAN_ID_HOTAIR_CMD,
    CAN_ID_IMPACT_EVENT,
    CAN_ID_LASER_CMD,
    CAN_ID_MLX_VARIANT_RESP,
    CAN_ID_MOTION_CMD,
    CAN_ID_PERIPHERAL_INFO_RESP,
    CAN_ID_QUERY_ACTIVE_TOOL,
    CAN_ID_QUERY_DIAG0,
    CAN_ID_QUERY_FRAM_STATE,
    CAN_ID_QUERY_THERMAL_STATS,
    CAN_ID_THERMAL_STATS_RESP,
    format_thermal_stats,
    CAN_ID_QUERY_VERSION,
    CAN_ID_SOLDER_FEEDER_POS,
    CAN_ID_SOLDER_FEEDER_RESET,
    CAN_ID_SOLDER_SETPOINT,
    CAN_ID_UV_CURING_CMD,
    CAN_ID_VERSION_RESPONSE,
    CAN_ID_VERSION_PATCH_RESPONSE,
    VERSION_PATCH_GRACE_S,
    CAN_ID_THERMAL_CALIB_CHUNK,
    CAN_ID_THERMAL_CALIB_CHUNK_REQ,
    CAN_ID_THERMAL_STATUS,
    CAN_ID_THERMAL_TRIGGER,
    CAN_ID_VACUUM_TELEMETRY,
    ERASE_FRAM_MAGIC,
    SOLDER_FEEDER_RESET_MAGIC,
    ICON_IMAGE_PATH,
    TESTER_VERSION,
    THIS_HARDWARE_ID,
    TOOL_KINDS,
    TOOL_NAMES,
    _,
    list_serial_ports,
)
from tester_result_record import session_manifest
from tester_transports import SLCAN, SocketCAN, list_socketcan_interfaces, virtual_ports
from urtc_ui import LanguageModel, connection_badge, format_can_id, format_hex



class TesterQtBridge(QObject):
    """QML state model backed by the real CAN transports, not mock telemetry."""

    MONITOR_MAX_ROWS = 2000  # the table keeps the newest frames; older ones are dropped
    MONITOR_SHOWN_ROWS = 14  # the deck shows the newest few

    changed = Signal()
    monitorChanged = Signal()
    logChanged = Signal()
    _connectionResult = Signal(object, str)
    _bitrateDetected = Signal(str)
    _monitorUpdated = Signal()
    _probeResult = Signal(object, object, str)
    _passiveResult = Signal(object, str, float)
    _flyingProbeResult = Signal(str, str)
    _thermalResult = Signal(object, str)
    _logRequested = Signal(str)
    # Real, continuous telemetry - unlike every _XResult signal above (one
    # bounded worker thread, one final emit), these fire repeatedly for as
    # long as a watch is running, marshalled the same way _log() already
    # is (worker thread -> Signal.emit -> Qt's own cross-thread queued
    # delivery -> a @Slot back on the GUI thread). Vacuum/Scan Probe have
    # no commands at all (see watchTelemetry) - nothing here can ever
    # write to a real actuator.
    _vacuumTelemetry = Signal(int, bool)
    _scanProbeImpact = Signal(str)
    _selfTestLine = Signal(str, str)
    _readoutUpdated = Signal(str, str, float)
    _busHealth = Signal(bool, str)
    _selfTestDone = Signal(int, str)
    # Real, tool-independent utility queries (Global Controls/Expansion
    # Board/F-RAM) - one shared signal rather
    # than one per action, since they're all the same real shape (a
    # bounded request/response round trip, or None on timeout); `key`
    # routes each real result to its own real Property below.
    _queryResult = Signal(str, object)

    def __init__(self) -> None:
        super().__init__()
        self._ports: list[str] = []
        self._socketcan_ports: set[str] = set()
        saved = load_config()
        self._preferred_port = str(saved.get("port", ""))
        saved_bitrate = saved.get("bitrate")
        self._bitrate_label = saved_bitrate if saved_bitrate in dict(SLCAN_BITRATES) else "500 kbit/s"
        self._selected_port = ""
        self._transport = None
        self._listen_only = True
        self._busy = False
        # The transport can only be read from one thread at a time: every worker that reads from it holds this for the whole exchange.
        self._io_lock = threading.RLock()
        self._thermal_columns = 32
        self._status = "READ-ONLY READY"
        self._active_tool = "No active probe yet"
        self._active_tool_id = -1
        self._selected_tool_id = 0
        self._version = "No board version received"
        self._version_patch_frame: bytes | None = None
        self._passive_frames: list[dict[str, str]] = []
        self._passive_summary = ""
        self._passive_load_percent = 0.0
        self._flying_probe_result = "No ADS1115 result read yet"
        self._thermal_cells: list[dict[str, object]] = []
        self._thermal_summary = "No thermal frame captured yet"
        self._logs: list[str] = []
        self._watchdog_stops: dict[str, threading.Event] = {}
        self._watchdog_off_frames: dict[str, tuple[int, bytes]] = {}
        # Continuous telemetry watch - same real threading.Event-keyed-dict
        # shape as _watchdog_stops above (one real, proven mechanism for
        # "a background thread that runs until told to stop", not a
        # second one invented for this), but for a read loop rather than
        # a periodic send. At most one key is ever active - only one tool
        # panel is visible at a time - kept as a dict anyway to reuse the
        # exact same stop/cleanup shape _stop_watchdog already has.
        self._telemetry_stops: dict[str, threading.Event] = {}
        # Raw bus monitor: its own stop flag (a monitor is not a telemetry watch) and a bounded frame table.
        self._monitor_stop: threading.Event | None = None
        self._monitor_thread: threading.Thread | None = None
        self._monitor_rows: collections.deque = collections.deque(maxlen=self.MONITOR_MAX_ROWS)
        self._monitor_lock = threading.Lock()
        self._monitor_filter = FrameFilter()
        self._monitor_last_seen: dict[int, float] = {}
        self._vacuum_adc = 0
        self._vacuum_detected = False
        self._scan_probe_impact_count = 0
        self._scan_probe_last_impact = ""
        # Real, tool-independent utility panel state - one string per
        # real result, matching the established flyingProbeResult/
        # thermalSummary convention (already-translated display text
        # built once in _on_query_result, not re-translated by QML).
        self._query_texts: dict[str, str] = {
            "fram_state": "",
            "thermal_stats": "",
            "expansion_type": "",
            "mlx_variant": "",
            "free_tool_config": "",
            "peripheral_info": "",
            "feeder_position": "",
            "diag0": "",
            "spi_response": "",
            "black_box": "",
            "features": "",
            "pid": "",
            "thermal_view": "",
            "rack_bench": "",
        }
        # Fault recorder, optional functions, rack bench and thermal view (tester_extras.py).
        self._auto_black_box = extras.AutoDownload(True)
        self._bench = extras.RackBench()
        self._thermal_view_source = ""
        # Custom CAN Frame - the one real tool-independent action with no
        # per-field validation beyond frame shape (see HELP_SENDS_RAW_FRAME's
        # own real text): whatever is typed goes on the bus exactly as
        # typed. Periodic re-send is owned by a QML Timer (see
        # sendCustomFramePeriodicTick's own docstring for why), not a
        # Python thread like _watchdog_stops/_telemetry_stops above - this
        # flag is the single source of truth the Timer's running binding
        # and the CheckBox's checked binding both read.
        self._custom_periodic_active = False
        self._self_test_lines: list[dict[str, str]] = []
        self._readout_values: dict[str, str] = {}
        self._readout_series = tele.Series()
        self._bus_health_text = ""
        self._bus_health_stop: threading.Event | None = None
        self._self_test_running = False
        self._custom_periodic_last_ok = True
        self._connectionResult.connect(self._on_connection_result)
        self._bitrateDetected.connect(self._on_bitrate_detected)
        self._monitorUpdated.connect(self.monitorChanged)
        self._probeResult.connect(self._on_probe_result)
        self._passiveResult.connect(self._on_passive_result)
        self._flyingProbeResult.connect(self._on_flying_probe_result)
        self._thermalResult.connect(self._on_thermal_result)
        self._logRequested.connect(self._append_log)
        self._vacuumTelemetry.connect(self._on_vacuum_telemetry)
        self._scanProbeImpact.connect(self._on_scan_probe_impact)
        self._queryResult.connect(self._on_query_result)
        self._selfTestLine.connect(self._on_self_test_line)
        self._readoutUpdated.connect(self._on_readout)
        self._busHealth.connect(self._on_bus_health)
        self._selfTestDone.connect(self._on_self_test_done)
        self.scanPorts()

    @Property(str, constant=True)
    def title(self) -> str:
        return "URTC TESTER"

    @Property(str, constant=True)
    def version(self) -> str:
        return TESTER_VERSION

    @Property("QStringList", constant=True)
    def languageNames(self) -> list:
        """The names of the interface languages, each in its own language; the choice is saved and applies on the next start."""
        return LanguageModel(_current_language).names()

    @Property(int, constant=True)
    def languageIndex(self) -> int:
        return LanguageModel(_current_language).index()

    @Slot(int, result=str)
    def selectLanguage(self, index: int) -> str:
        """Saves the chosen language in the configuration file and returns the (already translated) notice to show."""
        code = LanguageModel().code_at(index)
        if code is None or code == _current_language:
            return ""
        if save_config({"language": code}):
            self._log(f"LANGUAGE_SAVED {code}")
            return _("MSG_RESTART_NEEDED")
        self._log(f"LANGUAGE_SAVE_FAILED {code}")
        return ""

    @Property(str, constant=True)
    def iconSource(self) -> str:
        return QUrl.fromLocalFile(str(Path(ICON_IMAGE_PATH))).toString()

    @Slot(str, result=str)
    def uiText(self, key: str) -> str:
        """Expose the established .lng lookup to the QML surface."""
        translated = _(key)
        return translated if translated != key else {
            "QT_TRANSPORT_GATE": "TRANSPORT GATE",
            "QT_MONITOR_START": "START MONITOR",
            "QT_MONITOR_STOP": "STOP MONITOR",
            "QT_TRANSPORT_HELP": "Select a serial SLCAN port or a Linux SocketCAN interface.",
            "QT_SAFETY_MODE": "SAFETY MODE",
            "QT_LISTEN_ONLY": "LISTEN-ONLY (NO CAN TX)",
            "QT_ACTIVE_CHECKS_ARMED": "ACTIVE CHECKS ARMED",
            "QT_PASSIVE_HELP": "Passive transport mode. Probe commands are blocked.",
            "QT_ACTIVE_HELP": "Identity probe transmits only documented queries 0x110 and 0x7F8.",
            "QT_STAGED_LIMIT": "This deck has real, confirmed coverage for every one of the 25 tool profiles' own commands. The deck has not been checked against a real board yet - see README.md's own Known limitations.",
            "QT_IDENTITY_CHECKPOINTS": "IDENTITY & HEALTH CHECKPOINTS",
            "QT_CHECKPOINTS": "1  Connect to the selected production transport\n2  Explicitly arm active checks, if required\n3  Query active tool and board version\n4  Preserve a transparent session log",
            "QT_PROBE": "PROBE ACTIVE TOOL + VERSION",
            "QT_ACTIVE_TOOL": "ACTIVE TOOL",
            "QT_ACTIVITY_LOG": "ACTIVITY LOG",
            "QT_PASSIVE_WINDOW": "PASSIVE BUS WINDOW",
            "QT_PASSIVE_WINDOW_HELP": "Capture live CAN traffic for two seconds. Listen-only mode guarantees no CAN transmission.",
            "QT_CAPTURE_PASSIVE": "CAPTURE PASSIVE WINDOW",
            "QT_NO_PASSIVE_FRAMES": "No passive window captured yet.",
            "QT_BUS_LOAD": "BUS LOAD",
            "QT_TOOL_PROFILE": "TOOL PROFILE",
            "QT_PROFILE_GUARD": "Native controls unlock only when the active identity exactly matches the selected profile and active checks are armed.",
            "QT_MOTION_CONTROL": "ONE-SHOT MOTION",
            "QT_DIRECTION": "DIRECTION",
            "QT_STEPS": "STEPS",
            "QT_SEND_MOTION": "SEND MOTION",
            "QT_STOP_MOTION": "STOP",
            "QT_STOP_ALL_OUTPUTS": "STOP ALL OUTPUTS",
            "QT_PROFILE_NOT_MATCHED": "Select and verify a matching motion profile first.",
            "QT_CONFIRM_MOTION": "CONFIRM MOTION",
            "QT_CONFIRM_MOTION_HELP": "This sends one real CAN motion command to the verified tool. Confirm the machine is clear and its safety interlock is active.",
            "QT_CONFIRM": "CONFIRM",
            "QT_CANCEL": "CANCEL",
            "QT_ADVANCED_CONTROL": "ADVANCED PROFILE CONTROL",
            "QT_DRILL_SPEED": "DRILL SPEED (0-255)",
            "QT_DRILL_DIRECTION": "DRILL DIRECTION",
            "QT_AOI_MODE": "AOI RING MODE",
            "QT_AOI_PERIOD": "STROBE PERIOD (ms)",
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
            "QT_WATCH_TELEMETRY": "START WATCHING",
            "QT_STOP_WATCHING_TELEMETRY": "STOP WATCHING",
            "QT_GLOBAL_CONTROLS": "GLOBAL CONTROLS",
            "QT_EXPANSION_BOARD": "EXPANSION BOARD",
            "QT_FRAM_PANEL": "F-RAM",
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

    @Property("QStringList", constant=True)
    def bitrates(self) -> list[str]:
        return [label for label, _code in SLCAN_BITRATES]

    @Property(str, notify=changed)
    def selectedBitrate(self) -> str:
        return self._bitrate_label

    @Slot(str)
    def selectBitrate(self, label: str) -> None:
        """Bit rate of an SLCAN adapter (a SocketCAN interface keeps the one it was brought up with). Remembered for the next session."""
        if self._transport is None and not self._busy and label in dict(SLCAN_BITRATES):
            self._bitrate_label = label
            save_config({"bitrate": label})
            self._log(f"BITRATE_SELECTED {label}")
            self.changed.emit()

    @Slot()
    def autoDetectBitrate(self) -> None:
        """Find the bus speed: listen-only first, and transmit a query only when the bus is completely silent."""
        if self._transport is not None or self._busy:
            return
        if not self._selected_port or self._selected_port in self._socketcan_ports:
            self._log("AUTODETECT_NEEDS_A_SERIAL_PORT")
            return
        self._set_state(status="DETECTING BITRATE", busy=True)
        threading.Thread(target=self._autodetect_worker, args=(self._selected_port,), daemon=True, name="urtc-qt-autobaud").start()

    def _autodetect_worker(self, port: str) -> None:
        found = ""
        try:
            from tester_autodetect import scan_bitrates

            found = scan_bitrates(
                port, SLCAN, SLCAN_BITRATES, log=self._log,
                on_try=lambda label: self._log(f"AUTODETECT_TRYING {label}"),
                on_traffic=lambda label, count: self._log(f"AUTODETECT_TRAFFIC {label} {count} frames"),
                on_active_phase=lambda: self._log("AUTODETECT_ACTIVE_PHASE the bus is silent, querying at each speed"),
            ) or ""
        except Exception as exc:  # a missing adapter or a busy port must not crash the deck
            self._log(f"AUTODETECT_FAILED {exc}")
        finally:
            self._bitrateDetected.emit(found)

    def _on_bitrate_detected(self, label: str) -> None:
        if label:
            self._bitrate_label = label
            save_config({"bitrate": label})
            self._set_state(status=f"BITRATE {label}", busy=False)
            self._log(f"AUTODETECT_FOUND {label}")
        else:
            self._set_state(status="NO RESPONSE AT ANY BITRATE", busy=False)
            self._log("AUTODETECT_NO_RESPONSE")


    @Property(str, notify=changed)
    def statusColor(self) -> str:
        """Colour of the status line: the shared badge of the connection state (connected, listen-only or disconnected)."""
        return connection_badge(True if self.connected else None, self._listen_only).colour

    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Slot(result=str)
    def refreshBusStats(self) -> str:
        """`"123 fps | 12% bus load"` for the connected transport (an
        estimate - see tester_bus_monitor.BusStats), `""` when not
        connected. QML polls this once a second."""
        stats = getattr(self._transport, "stats", None) if self._transport is not None else None
        if stats is None:
            return ""
        fps, load = stats.snapshot()
        return f"{fps:.0f} fps | {load:.1f}% bus"

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
        return [
            {"id": tool_id, "name": name, "kind": TOOL_KINDS.get(tool_id, "actuator")}
            for tool_id, name in TOOL_NAMES.items()
        ]

    @Property("QVariantList", notify=changed)
    def passiveFrames(self) -> list[dict[str, str]]:
        return self._passive_frames

    @Property(str, notify=changed)
    def passiveSummary(self) -> str:
        return translate_log_line(self._passive_summary)

    @Property(bool, notify=changed)
    def hasPassiveSnapshot(self) -> bool:
        return bool(self._passive_summary)

    @Property(float, notify=changed)
    def passiveLoadPercent(self) -> float:
        """Bus load over the passive capture window, estimated from the
        same real frame count/timing _passive_capture_worker already
        collects - see that worker's own comment for the bit-counting
        method. 0.0 until a window has actually been captured."""
        return self._passive_load_percent

    @Property("QStringList", notify=logChanged)
    def logs(self) -> list[str]:
        """The last lines of the activity log in the interface language (the stored lines stay English)."""
        return [translate_log_line(line) for line in self._logs[-14:]]

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
            and (not self._busy or self.isWatchingReadouts)
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
            4: "vacuum",
            11: "scan_probe",
        }.get(self._selected_tool_id, "unavailable")

    @Property(str, notify=changed)
    def noHandlerText(self) -> str:
        """What to say for a profile with no command or readout of its own: its actuator lives on the robot's mainboard."""
        key = {15: "HELP_NO_HANDLER_CONFORMAL_COATING", 20: "HELP_NO_HANDLER_PRESSFIT_INSERTER"}.get(self._selected_tool_id)
        return _(key) if key else _("MSG_NO_TOOL_FOR_JUMPERS", tool_id=self._selected_tool_id)

    @Property(bool, notify=changed)
    def isWatchingTelemetry(self) -> bool:
        return bool(self._telemetry_stops)

    @Property(bool, notify=monitorChanged)
    def isMonitoring(self) -> bool:
        return self._monitor_stop is not None

    @Property(bool, notify=changed)
    def canMonitorBus(self) -> bool:
        """Monitoring never transmits, so it is available in listen-only mode too; it needs a connection and no other reader."""
        return self._transport is not None and not self._busy and self._monitor_stop is None

    @Property("QVariantList", notify=monitorChanged)
    def monitorLines(self) -> list[str]:
        with self._monitor_lock:
            newest = list(self._monitor_rows)[-self.MONITOR_SHOWN_ROWS:]
        return [f"{ts}  {can_id:<6} [{dlc}]  {data}  +{dt:.1f} ms" for ts, can_id, dlc, data, dt in reversed(newest)]

    @Property(int, notify=monitorChanged)
    def monitorCount(self) -> int:
        with self._monitor_lock:
            return len(self._monitor_rows)

    @Slot()
    def startBusMonitor(self) -> None:
        transport = self._transport
        if transport is None or self._busy or self._monitor_stop is not None:
            self._log("BUS_MONITOR_BLOCKED not connected, or another operation holds the bus")
            return
        stop = threading.Event()
        self._monitor_stop = stop
        self._monitor_filter.reset()
        self._monitor_last_seen.clear()
        self._set_state(status="MONITORING THE BUS", busy=True)
        self._log("BUS_MONITOR_STARTED")

        def _worker() -> None:
            last_emit = 0.0
            try:
                while not stop.is_set():
                    frame = transport.read_frame(timeout=0.1)
                    if frame is not None:
                        self._record_monitor_frame(frame[0], bytes(frame[1]))
                    now = time.monotonic()
                    if now - last_emit >= 0.15:
                        last_emit = now
                        self._monitorUpdated.emit()
            except Exception as exc:  # an unplugged adapter must end the monitor, not the deck
                self._log(f"BUS_MONITOR_FAILED {exc}")
            finally:
                self._monitor_stop = None
                self._monitorUpdated.emit()
                self._set_state(status="ACTIVE CHECKS ARMED", busy=False)
                self._log("BUS_MONITOR_STOPPED")

        self._monitor_thread = threading.Thread(target=_worker, daemon=True, name="urtc-tester-bus-monitor")
        self._monitor_thread.start()
        self.monitorChanged.emit()

    def _record_monitor_frame(self, can_id: int, data: bytes) -> None:
        if not self._monitor_filter.accept(can_id, data):
            return
        now = time.time()
        stamp = time.strftime("%H:%M:%S", time.localtime(now)) + f".{int((now % 1) * 1000):03d}"
        previous = self._monitor_last_seen.get(can_id)
        delta_ms = (now - previous) * 1000.0 if previous is not None else 0.0
        self._monitor_last_seen[can_id] = now
        with self._monitor_lock:
            self._monitor_rows.append((stamp, format_can_id(can_id, extended=can_id > 0x7FF), len(data), format_hex(data, ""), round(delta_ms, 1)))

    @Slot()
    def stopBusMonitor(self) -> None:
        """Deliberately not busy-gated: the worker clears busy itself once its read loop has really ended."""
        if self._monitor_stop is not None:
            self._monitor_stop.set()

    @Slot()
    def clearBusMonitor(self) -> None:
        with self._monitor_lock:
            self._monitor_rows.clear()
        self._monitor_filter.reset()
        self._monitor_last_seen.clear()
        self.monitorChanged.emit()

    @Slot(str)
    def setMonitorIds(self, text: str) -> None:
        """Hex IDs separated by spaces or commas; empty shows every ID."""
        self._monitor_filter.set_ids(text)
        self._monitor_filter.reset()

    @Slot(bool)
    def setMonitorOnlyChanges(self, enabled: bool) -> None:
        self._monitor_filter.only_changes = bool(enabled)
        self._monitor_filter.reset()

    @Slot(str, result=str)
    def exportMonitor(self, fmt: str) -> str:
        """Save the recorded frames as a PEAK .trc or Vector .asc trace in the logs folder; returns the path ('' on failure)."""
        with self._monitor_lock:
            rows = list(self._monitor_rows)
        if fmt not in ("trc", "asc") or not rows:
            self._log("BUS_MONITOR_EXPORT_EMPTY there are no frames to export")
            return ""
        try:
            os.makedirs(LOGS_FOLDER, exist_ok=True)
            path = os.path.join(LOGS_FOLDER, f"urtc_tester_bus_{time.strftime('%Y%m%d_%H%M%S')}.{fmt}")
            with open(path, "w", encoding="ascii") as stream:
                stream.write(render_trace(rows, fmt))
        except OSError as exc:
            self._log(f"BUS_MONITOR_EXPORT_FAILED {exc}")
            return ""
        self._log(f"BUS_MONITOR_EXPORTED {len(rows)} frames {path}")
        return path

    @Property(bool, notify=changed)
    def canWatchTelemetry(self) -> bool:
        """Deliberately NOT canActuateSelectedProfile - that also requires
        active-checks-armed (not listen-only), a restriction that exists
        to keep a real command from transmitting while passive. Watching
        telemetry never transmits, so it stays available in listen-only
        mode too - see _require_telemetry_profile's own docstring."""
        return self._require_telemetry_profile({4, 11} | set(tele.READOUTS))

    @Property(int, notify=changed)
    def vacuumAdc(self) -> int:
        return self._vacuum_adc

    @Property(bool, notify=changed)
    def vacuumDetected(self) -> bool:
        return self._vacuum_detected

    @Property(int, notify=changed)
    def scanProbeImpactCount(self) -> int:
        return self._scan_probe_impact_count

    @Property(str, notify=changed)
    def scanProbeLastImpact(self) -> str:
        return self._scan_probe_last_impact

    # -- tool-independent utility panels (Global Controls/Expansion
    # Board/F-RAM) - real, not gated by a selected tool profile at all. --
    @Property(bool, notify=changed)
    def canUseUtilityPanels(self) -> bool:
        return self.connected and not self._listen_only and not self._busy

    @Property(str, notify=changed)
    def framStateText(self) -> str:
        return self._query_texts["fram_state"]

    @Property(str, notify=changed)
    def thermalStatsText(self) -> str:
        return self._query_texts["thermal_stats"]

    @Property(str, notify=changed)
    def expansionBoardTypeText(self) -> str:
        return self._query_texts["expansion_type"]

    @Property(str, notify=changed)
    def mlxSensorVariantText(self) -> str:
        return self._query_texts["mlx_variant"]

    @Property(str, notify=changed)
    def freeToolConfigText(self) -> str:
        return self._query_texts["free_tool_config"]

    @Property(str, notify=changed)
    def peripheralInfoText(self) -> str:
        return self._query_texts["peripheral_info"]

    @Property(str, notify=changed)
    def feederPositionText(self) -> str:
        return self._query_texts["feeder_position"]

    @Property(str, notify=changed)
    def diag0Text(self) -> str:
        return self._query_texts["diag0"]

    @Property(str, notify=changed)
    def spiResponseText(self) -> str:
        return self._query_texts["spi_response"]

    @Property(bool, notify=changed)
    def customFramePeriodicActive(self) -> bool:
        return self._custom_periodic_active

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

    @Property(int, notify=changed)
    def thermalColumns(self) -> int:
        return self._thermal_columns

    @Property(str, notify=changed)
    def thermalSummary(self) -> str:
        return translate_log_line(self._thermal_summary)


    def _log(self, message: str) -> None:
        """Queue logs from CAN worker threads onto the Qt GUI thread."""
        self._logRequested.emit(str(message))

    @Slot(result=str)
    def exportSession(self) -> str:
        """Save the activity log with a manifest naming it by its SHA-256, so the log can be shown to be unedited.
        The stored lines are the English originals (not the translated ones shown on screen), for support and auditing."""
        log_text = "\n".join(self._logs) + "\n"
        try:
            os.makedirs(LOGS_FOLDER, exist_ok=True)
            path = os.path.join(LOGS_FOLDER, f"urtc_tester_session_{time.strftime('%Y%m%d_%H%M%S')}.zip")
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as bundle:
                bundle.writestr("session_log.txt", log_text)
                bundle.writestr("system_diagnostics.txt", "\n".join([
                    f"URTC Tester version: {TESTER_VERSION}",
                    f"Python: {sys.version}",
                    f"Platform: {platform.platform()}",
                    f"Current port/interface: {self._selected_port}",
                    f"Current bitrate (Serial/SLCAN): {self._bitrate_label}",
                    f"Connected: {self._transport is not None}",
                    f"Listen-only: {self._listen_only}",
                    f"Active tool ID: {self._active_tool_id}",
                ]))
                bundle.writestr("session_manifest.json", json.dumps(session_manifest(
                    log_text,
                    tester_version=TESTER_VERSION,
                    port=self._selected_port,
                    connected=self._transport is not None,
                ), indent=2, sort_keys=True))
        except OSError as exc:
            self._log(f"SESSION_EXPORT_FAILED {exc}")
            return ""
        self._log(f"SESSION_EXPORTED {path}")
        return path

    # -- help texts: README (in the interface language when a translation exists), licence, project page, plain log ---
    README_SUFFIXES = {
        "spanish": "_spa", "italian": "_ita", "french": "_fra", "german": "_deu",
        "chinese": "_zho", "japanese": "_jpn", "portuguese": "_por",
    }

    @Slot(result=str)
    def readmeText(self) -> str:
        folder = tester_config.base_dir
        candidate = os.path.join(folder, f"README{self.README_SUFFIXES.get(_current_language, '')}.md")
        path = candidate if os.path.isfile(candidate) else os.path.join(folder, "README.md")
        try:
            with open(path, encoding="utf-8") as stream:
                return stream.read()
        except OSError as exc:
            return f"{_('TITLE_EXPORT_FAILED')}: {exc}"

    @Slot(result=str)
    def licenseText(self) -> str:
        try:
            with open(os.path.join(tester_config.base_dir, "LICENSE"), encoding="utf-8") as stream:
                return stream.read()
        except OSError:
            return _("MSG_LICENSE_FALLBACK")

    @Property(str, constant=True)
    def githubUrl(self) -> str:
        return "https://github.com/JuanenRac/URTC-TESTER"

    @Slot(str, result=bool)
    def saveLogText(self, save_path: str) -> bool:
        """Save the activity log as plain text, English originals (the lighter counterpart of the debug bundle)."""
        path = QUrl(save_path).toLocalFile() if save_path.startswith("file:") else save_path
        try:
            with open(path, "w", encoding="utf-8") as stream:
                stream.write("\n".join(self._logs) + "\n")
        except OSError as exc:
            self._log(f"LOG_SAVE_FAILED {exc}")
            return False
        self._log(f"LOG_SAVED {path}")
        return True

    @Property(str, constant=True)
    def aboutText(self) -> str:
        return (
            f"URTC Tester v{TESTER_VERSION}\n"
            "JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>\n"
            "GNU General Public License v3.0 or later (GPL-3.0-or-later)"
        )

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
        ports.extend(url for url in virtual_ports() if url not in ports)  # a virtual board named in URTC_VIRTUAL_PORT
        self._ports = ports
        if self._selected_port not in ports:
            self._selected_port = self._preferred_port if self._preferred_port in ports else (ports[0] if ports else "")
        self._log(f"PORT_SCAN count={len(ports)}")
        self.changed.emit()

    @Slot(str)
    def selectPort(self, port: str) -> None:
        if self._transport is None and not self._busy and port in self._ports:
            self._selected_port = port
            self._preferred_port = port
            save_config({"port": port})
            self.changed.emit()

    @Slot(bool)
    def setListenOnly(self, enabled: bool) -> None:
        if self._transport is None and not self._busy:
            self._listen_only = enabled
            self._set_state(status="READ-ONLY READY" if enabled else "ACTIVE CHECKS ARMED")
            self._log("MODE_LISTEN_ONLY" if enabled else "MODE_ACTIVE_CHECKS_ARMED")

    @Slot()
    def toggleConnection(self) -> None:
        if self._monitor_stop is not None and self._transport is not None:
            # a bus monitor has no natural end: disconnecting ends it instead of leaving the app stuck
            self._monitor_stop.set()
            worker = self._monitor_thread
            if worker is not None and worker is not threading.current_thread():
                worker.join(timeout=1.0)
        if self._busy and self._telemetry_stops and self._transport is not None:
            # a telemetry watch has no natural end: disconnecting ends it instead of leaving the app stuck
            self._end_telemetry_watch()
        if self._busy:
            return
        if self._transport is not None:
            self._stop_bus_health()
            self._stop_all_watchdogs()
            self._custom_periodic_active = False
            self.stopMotion()   # a move that was left running does not go on turning after the connection is closed
            try:
                self._transport.close()
            finally:
                self._transport = None
                self._active_tool = "No active probe yet"
                self._active_tool_id = -1
                self._version = "No board version received"
                self._version_patch_frame = None
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
                transport.open_channel(dict(SLCAN_BITRATES).get(self._bitrate_label, BITRATE_500K_SLCAN_CODE), listen_only=self._listen_only)
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
            self._start_bus_health(transport)

    @Slot()
    def probeIdentity(self) -> None:
        if not self.canProbe:
            self._log("PROBE_BLOCKED connect first and explicitly disable listen-only")
            return
        self._stop_all_watchdogs()
        self._set_state(status="PROBING IDENTITY", busy=True)
        self._log("PROBE_STARTED ids=0x110,0x7F8")
        threading.Thread(target=self._probe_worker, daemon=True, name="urtc-tester-qt-probe").start()

    # -- bus health: the board is asked who it is every few seconds while idle ---
    BUS_HEALTH_INTERVAL_S = 3.0

    @Property(str, notify=changed)
    def busHealthText(self) -> str:
        """Empty while the bus looks healthy; otherwise the translated reason (already shown in the log)."""
        return self._bus_health_text

    def _start_bus_health(self, transport) -> None:
        self._stop_bus_health()
        stop = threading.Event()
        self._bus_health_stop = stop
        threading.Thread(target=self._bus_health_worker, args=(transport, stop), daemon=True, name="urtc-tester-qt-bus-health").start()

    def _stop_bus_health(self) -> None:
        stop = self._bus_health_stop
        self._bus_health_stop = None
        if stop is not None:
            stop.set()
        self._bus_health_text = ""

    def _bus_health_worker(self, transport, stop: threading.Event) -> None:
        """Notices a bus that goes bad after the first probe (a loose termination, a node misbehaving, an unplugged adapter).

        It only runs while nothing else holds the bus and never in listen-only mode (it would get no answer by design).
        One silent poll is not a verdict yet: see protocol.BusHealthTracker."""
        tracker = protocol.BusHealthTracker()
        was_bad = False
        while not stop.wait(self.BUS_HEALTH_INTERVAL_S):
            if transport is not self._transport:
                break
            if self._listen_only or self._busy:
                continue
            if not self._io_lock.acquire(blocking=False):
                continue
            try:
                if self._busy:
                    continue
                transport.send_frame(CAN_ID_QUERY_ACTIVE_TOOL, b"")
                tool_data = self._wait_for(CAN_ID_ACTIVE_TOOL_RESP, 1.0)
            except Exception as exc:
                self._log(f"BUS_HEALTH_POLL_FAILED {exc}")
                continue
            finally:
                self._io_lock.release()
            if stop.is_set() or transport is not self._transport:
                break
            problems = tracker.evaluate(tool_data)
            if problems is None:
                continue
            bad = bool(problems)
            reason = ", ".join(_(key, **args) for key, args in problems) if bad else ""
            if isinstance(transport, SocketCAN) and SocketCAN.check_carrier(transport.interface) is False:
                bad = True
                reason = _("MSG_NO_CARRIER_SESSION", interface=transport.interface)
            if bad != was_bad:
                was_bad = bad
                self._busHealth.emit(bad, reason)

    @Slot(bool, str)
    def _on_bus_health(self, bad: bool, reason: str) -> None:
        if self._transport is None:
            return
        self._bus_health_text = reason if bad else ""
        self._log(f"BUS_HEALTH_WARNING {reason}" if bad else "BUS_HEALTH_RECOVERED")
        self.changed.emit()

    # -- self-test --------------------------------------------------------
    @Property(bool, notify=changed)
    def canSelfTest(self) -> bool:
        """Same gate as every command: connected, active checks armed, idle, and the detected tool is the selected profile."""
        return self.canActuateSelectedProfile and self._active_tool_id >= 0 and not self._telemetry_stops

    @Property("QVariantList", notify=changed)
    def selfTestLines(self) -> list[dict[str, str]]:
        return list(self._self_test_lines)

    @Property(bool, notify=changed)
    def selfTestRunning(self) -> bool:
        return self._self_test_running

    @Slot()
    def runSelfTest(self) -> None:
        """Run the at-rest communication checks of the detected tool (QML asks for a confirmation first).

        The commands are the safe values listed in tester_selftest.py (setpoint, speed and power 0).  Any armed
        output is switched off first so a keep-alive thread cannot send its own value in between."""
        if not self.canSelfTest or self._self_test_running:
            self._log("SELFTEST_BLOCKED profile identity/active-check gate not satisfied")
            return
        transport = self._transport
        if transport is None:
            return
        self._stop_all_watchdogs()
        self._self_test_lines = []
        self._self_test_running = True
        self._set_state(status="SELF-TEST RUNNING", busy=True)
        self._log(f"SELFTEST_STARTED tool={self._active_tool_id}")
        threading.Thread(
            target=self._self_test_worker, args=(transport, self._active_tool_id), daemon=True, name="urtc-tester-qt-selftest",
        ).start()

    def _self_test_worker(self, transport, tool_id: int) -> None:
        def exchange(send, expect_id, timeout):
            if send is not None:
                transport.send_frame(*send)
            return self._wait_for(expect_id, timeout)

        with self._io_lock:
            try:
                result = run_self_test(
                    tool_id, exchange,
                    emit=lambda line: self._selfTestLine.emit(line.status, line.text),
                    stop=lambda: self._transport is None,
                )
                self._selfTestDone.emit(result.failed, "")
            except Exception as exc:
                self._selfTestDone.emit(-1, str(exc))

    @Slot(str, str)
    def _on_self_test_line(self, status: str, text: str) -> None:
        self._self_test_lines.append({"status": status, "text": text})
        self.changed.emit()

    @Slot(int, str)
    def _on_self_test_done(self, failed: int, error: str) -> None:
        self._self_test_running = False
        if error:
            self._set_state(status="SELF-TEST FAILED", busy=False)
            self._log(f"SELFTEST_FAILED {error}")
        else:
            self._set_state(status="ACTIVE CHECKS ARMED", busy=False)
            self._log(f"SELFTEST_COMPLETE failed={failed}")

    @Slot(int)
    def selectToolProfile(self, tool_id: int) -> None:
        if tool_id in TOOL_NAMES and not self._busy:
            if tool_id != self._selected_tool_id:
                # an output armed on the previous profile must not keep running behind the new one
                self._stop_all_watchdogs()
            self._selected_tool_id = tool_id
            self.changed.emit()

    @Slot()
    def stopAllOutputs(self) -> None:
        """Switch every armed output off. Not gated by the profile or by busy: stopping must always be one press away."""
        self._stop_all_watchdogs()
        if not self._listen_only:
            self._send_all_off()

    def _send_all_off(self) -> None:
        """Every known "off" (heaters, laser, drill, UV, layer fan, electromagnet, steppers), each tried on its own so one failure never skips the rest."""
        transport = self._transport
        if transport is None:
            return
        failed = 0
        for can_id, data in protocol.all_off_frames():
            try:
                transport.send_frame(can_id, data)
            except Exception as exc:
                failed += 1
                self._log(f"ALL_OFF_FAILED can_id=0x{can_id:03X} {exc}")
        self._log(f"ALL_OFF_SENT failed={failed}")

    # -- fault recorder, optional functions, rack bench and thermal view (the logic is in tester_extras.py) -------------------
    @Property(str, notify=changed)
    def blackBoxText(self) -> str:
        return self._query_texts["black_box"]

    @Property(bool, notify=changed)
    def autoBlackBox(self) -> bool:
        return self._auto_black_box.enabled

    @Slot(bool)
    def setAutoBlackBox(self, enabled: bool) -> None:
        self._auto_black_box.enabled = bool(enabled)
        self._log(f"AUTO_BLACK_BOX {'on' if enabled else 'off'}")
        self.changed.emit()

    @Slot()
    def readBlackBox(self) -> None:
        """Ask the board for its fault recorder (22 chunks of 0x1A8 / 0x1A9) and save it as CSV and JSON in the logs folder."""
        transport = self._transport
        if transport is None or not self.canUseUtilityPanels:
            self._log("BLACK_BOX_BLOCKED not connected or not in active-check mode")
            return

        def _worker() -> None:
            with self._io_lock:
                try:
                    record = extras.download_black_box(transport.send_frame, transport.read_frame)
                    csv_path, json_path = extras.save_black_box(record, tester_config.LOGS_FOLDER)
                    self._queryResult.emit("black_box", ("ok", extras.summarize_black_box(record), csv_path, json_path))
                except Exception as exc:
                    self._queryResult.emit("black_box", ("fail", str(exc)))

        threading.Thread(target=_worker, daemon=True, name="urtc-tester-black-box").start()

    @Property(str, notify=changed)
    def featuresText(self) -> str:
        return self._query_texts["features"]

    @Slot()
    def queryFeatures(self) -> None:
        if not self.canUseUtilityPanels:
            return
        self._run_query("features", (extras.CAN_ID_FEATURES_RESP, b""), extras.CAN_ID_FEATURES_RESP, extras.decode_features)

    @Slot(int)
    def writeFeatures(self, mask: int) -> None:
        """QML asks for the usual confirmation first: this is a persistent setting of the board (it acts after the next power-up)."""
        if not self.canUseUtilityPanels:
            self._log("FEATURES_BLOCKED not connected or not in active-check mode")
            return
        try:
            frame = extras.features_frame(int(mask))
        except ValueError as exc:
            self._log(f"FEATURES_BLOCKED {exc}")
            return
        self._run_query("features", frame, extras.CAN_ID_FEATURES_RESP, extras.decode_features)

    @Property(str, notify=changed)
    def pidText(self) -> str:
        return self._query_texts["pid"]

    @Slot()
    def queryPid(self) -> None:
        if not self.canUseUtilityPanels:
            return
        self._run_query("pid", (extras.CAN_ID_PID_STATE, b""), extras.CAN_ID_PID_STATE, extras.decode_pid_state)

    @Slot(str, str, str)
    def writePidGains(self, kp: str, ki: str, kd: str) -> None:
        """QML asks for the usual confirmation first: the gains are stored by the board and used by the heater from then on."""
        self._send_pid(extras.PID_SET_GAINS, kp, ki, kd)

    @Slot()
    def startPidAutotune(self) -> None:
        """QML asks for the usual confirmation first: the board heats the tip around the current set-point of the soldering iron."""
        self._send_pid(extras.PID_AUTOTUNE_START)

    @Slot()
    def abortPidAutotune(self) -> None:
        """Not behind a confirmation: stopping must always be one press away."""
        self._send_pid(extras.PID_AUTOTUNE_ABORT)

    def _send_pid(self, action: int, kp: str = "0", ki: str = "0", kd: str = "0") -> None:
        if not self.canUseUtilityPanels:
            self._log("HEATER_PID_BLOCKED not connected or not in active-check mode")
            return
        try:
            frame = extras.pid_frame(action, kp, ki, kd)
        except ValueError:
            self._log("HEATER_PID_BLOCKED gains must be numbers from 0 to 600")
            return
        self._run_query("pid", frame, extras.CAN_ID_PID_STATE, extras.decode_pid_state)

    @Property(str, notify=changed)
    def rackBenchText(self) -> str:
        return self._query_texts["rack_bench"]

    def _bench_report(self, headline: str) -> None:
        self._query_texts["rack_bench"] = headline + "\n" + self._bench.state_text()
        self.changed.emit()

    @Slot(int, int, int)
    def rackBenchRack(self, slot: int, tool_id: int, serial: int) -> None:
        try:
            self._bench_report(self._bench.rack_head(int(slot), int(tool_id), int(serial)))
        except ValueError as exc:
            self._bench_report(str(exc))

    @Slot(int, int)
    def rackBenchPreheat(self, tool_id: int, target_c: int) -> None:
        self._bench_report(self._bench.send_preheat(int(tool_id), int(target_c)))

    @Slot(int)
    def rackBenchAdvance(self, ms: int) -> None:
        self._bench_report(self._bench.advance(int(ms)))

    @Slot()
    def rackBenchExport(self) -> None:
        json_path, html_path = self._bench.status_page(tester_config.LOGS_FOLDER)
        self._query_texts["rack_bench"] = _("LBL_RACK_EXPORTED", json=json_path, html=html_path) + "\n" + self._bench.state_text()
        self.changed.emit()

    @Property(str, notify=changed)
    def thermalViewSource(self) -> str:
        return self._thermal_view_source

    @Property(str, notify=changed)
    def thermalViewText(self) -> str:
        return self._query_texts["thermal_view"]

    @Slot()
    def showSimulatedThermal(self) -> None:
        frame = extras.thermal_view.synthetic_frame()
        self._thermal_view_source = extras.thermal_data_url(frame)
        self._query_texts["thermal_view"] = _("LBL_THERMAL_VIEW_TEXT", text=extras.thermal_summary(frame, True))
        self.changed.emit()

    @Slot()
    def readThermalImage(self) -> None:
        transport = self._transport
        if transport is None or not self.canUseUtilityPanels:
            self._log("THERMAL_VIEW_BLOCKED not connected or not in active-check mode")
            return

        def _worker() -> None:
            with self._io_lock:
                try:
                    self._queryResult.emit("thermal_view", ("ok", extras.read_thermal_image(transport.send_frame, transport.read_frame)))
                except Exception as exc:
                    self._queryResult.emit("thermal_view", ("fail", str(exc)))

        threading.Thread(target=_worker, daemon=True, name="urtc-tester-thermal-view").start()

    def shutdownOutputs(self) -> None:
        try:
            self._stop_all_watchdogs()
            if not self._listen_only:
                self._send_all_off()
        except Exception as exc:
            self._log(f"SHUTDOWN_OUTPUTS_FAILED {exc}")

    @Slot()
    def stopMotion(self) -> None:
        """0 steps is the firmware's order to stop a movement (0x120); it is not behind the confirmation, because stopping must always be one press away."""
        transport = self._transport
        if transport is None:
            return
        try:
            transport.send_frame(CAN_ID_MOTION_CMD, b"\x00\x00\x00\x00\x00")
            self._log("MOTION_STOP_SENT")
        except Exception as exc:
            self._log(f"MOTION_STOP_FAILED {exc}")

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
        # `0x01 if direction == "forward" else 0x00` used to
        # let ANY unrecognized value (a typo, wrong case, a stray value
        # from a forged/stale UI state) silently encode as "reverse" - a
        # real, different, valid movement - instead of being rejected.
        # QML only ever offers "forward"/"reverse", but that is a UI
        # constraint, not a protocol-boundary guarantee against a forged
        # call.
        if direction not in ("forward", "reverse"):
            self._log(f"MOTION_BLOCKED unknown direction {direction!r}")
            return
        transport = self._transport
        if transport is None:
            return
        try:
            command_id, payload = protocol.motion_frame(self._selected_tool_id, direction, steps)
            transport.send_frame(command_id, payload)
            self._log(
                f"MOTION_SENT profile={self._selected_tool_id} "
                f"can_id=0x{command_id:03X} direction={direction} steps={steps}"
            )
        except Exception as exc:
            self._log(f"MOTION_FAILED {exc}")

    def _require_profile(self, allowed: set[int], action: str, reads: bool = False) -> bool:
        """Gate of a command. A command that also reads the bus (reads=True) cannot run next to a live readout."""
        if reads and self._telemetry_stops:
            self._log(f"{action}_BLOCKED a live readout holds the bus")
            return False
        if not self.canActuateSelectedProfile or self._selected_tool_id not in allowed:
            self._log(f"{action}_BLOCKED profile identity/active-check gate not satisfied")
            return False
        return self._transport is not None

    def _require_telemetry_profile(self, allowed: set[int]) -> bool:
        """Same real identity-match/connection/busy gate as
        canActuateSelectedProfile, minus the listen-only restriction -
        the one real difference between a command and a pure telemetry
        watch. `not self._listen_only` exists to keep a real CAN
        transmission from firing while passive - it has nothing to
        protect against here, since watchTelemetry() never calls
        transport.send_frame() at all."""
        return (
            self._selected_tool_id in allowed
            and self.connected
            and not self._busy
            and self._active_tool_id == self._selected_tool_id
            and self._transport is not None
        )

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
            "solder": (0, "solder", 0.15, CAN_ID_SOLDER_SETPOINT, 0, SETPOINT_MAX_C),
            "laser": (9, "laser", 0.15, CAN_ID_LASER_CMD, 0, 255),
            "printer_heater": (10, "printer_heater", 0.15, CAN_ID_3DP_THERMAL_MOTION, 0, 300),
            "layer_fan": (10, "layer_fan", 0.4, CAN_ID_3DP_LAYER_FAN_CMD, 0, 255),
            "uv": (18, "uv", 0.15, CAN_ID_UV_CURING_CMD, 0, 255),
            "hotair": (19, "hotair", 0.15, CAN_ID_HOTAIR_CMD, 0, SETPOINT_MAX_C),
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
        # The frames come from the one encoder the tests cover (advanced_protocol.watchdog_frames): this screen had its own copies, and the heater's safe-off had 5 bytes where the
        # firmware needs 6, so the "safe off" button did not turn the heater off.
        try:
            frame, off, _encoded_interval = protocol.watchdog_frames(kind, value, secondary)
        except ValueError:
            self._log("WATCHDOG_BLOCKED invalid numeric parameters")
            return
        if enabled:
            self._start_watchdog(key, interval_s, frame, off)
        else:
            self._stop_watchdog(key, off)
            self._log(f"WATCHDOG_STOPPED key={key} safe_off=1")

    @Slot()
    def watchTelemetry(self) -> None:
        """Starts a continuous, read-only watch for the selected profile's
        own telemetry - Vacuum Pickup (ADC + part-detect) or Scan Probe
        (impact events). Neither sends a single CAN frame; this Slot
        exists purely to marshal the board's own periodic/event-driven
        broadcasts to QML, matching _build_vacuum_panel/
        _build_scan_probe_panel's exact real semantics in the legacy app.

        Sets busy=True like every other read operation - this transport
        can only be read from one thread at a time (see
        tester_bus_monitor.py's own CANBusMonitor docstring for why), so
        a watch genuinely has to hold the same gate a probe/flying-probe-
        read/thermal-capture would. Unlike those, this has no natural end;
        stopTelemetryWatch() (not busy-gated, exactly like
        _stop_watchdog isn't) is what releases it.
        """
        if tele.readouts_for(self._selected_tool_id):
            if not self._require_telemetry_profile(set(tele.READOUTS)) or self._telemetry_stops:
                self._log("TELEMETRY_WATCH_BLOCKED profile identity/connection gate not satisfied")
                return
            self._watch_readouts()
            return
        can_id, key, decode = {
            4: (CAN_ID_VACUUM_TELEMETRY, "vacuum", self._decode_vacuum_frame),
            11: (CAN_ID_IMPACT_EVENT, "scan_probe", self._decode_scan_probe_frame),
        }.get(self._selected_tool_id, (None, None, None))
        if can_id is None or not self._require_telemetry_profile({4, 11}):
            self._log("TELEMETRY_WATCH_BLOCKED profile identity/connection gate not satisfied")
            return
        if self._telemetry_stops:
            self._log("TELEMETRY_WATCH_BLOCKED a watch is already running")
            return
        transport = self._transport
        if transport is None:
            return
        stop = threading.Event()
        self._telemetry_stops[key] = stop
        self._set_state(status=f"WATCHING {key.upper()} TELEMETRY", busy=True)
        self._log(f"TELEMETRY_WATCH_STARTED key={key} can_id=0x{can_id:03X}")

        def _worker() -> None:
            try:
                while not stop.is_set():
                    frame = transport.read_frame(timeout=0.1)
                    if frame is not None and frame[0] == can_id:
                        decode(frame[1])
            except Exception as exc:
                self._log(f"TELEMETRY_WATCH_FAILED key={key} error={exc}")
            finally:
                self._telemetry_stops.pop(key, None)
                self._set_state(status="ACTIVE CHECKS ARMED", busy=False)
                self._log(f"TELEMETRY_WATCH_STOPPED key={key}")

        self._telemetry_thread = threading.Thread(target=_worker, daemon=True, name=f"urtc-tester-{key}-watch")
        self._telemetry_thread.start()

    def _end_telemetry_watch(self, wait_s: float = 1.0) -> None:
        """Ask the running watch to stop and wait for its worker to release the transport."""
        for stop in list(self._telemetry_stops.values()):
            stop.set()
        worker = getattr(self, "_telemetry_thread", None)
        if worker is not None and worker is not threading.current_thread():
            worker.join(timeout=wait_s)

    # -- live readouts (temperature, RPM, endstops) of the selected tool ---
    @Property(bool, notify=changed)
    def readoutsAvailable(self) -> bool:
        return bool(tele.readouts_for(self._selected_tool_id))

    @Property("QVariantList", notify=changed)
    def readoutItems(self) -> list[dict[str, str]]:
        return [
            {"key": item.key, "label": _(item.label_key), "text": self._readout_values.get(item.key, "--")}
            for item in tele.readouts_for(self._selected_tool_id)
        ]

    @Property(bool, notify=changed)
    def readoutHasGraph(self) -> bool:
        return tele.graphed(self._selected_tool_id) is not None

    @Property(int, notify=changed)
    def readoutGraphMax(self) -> int:
        item = tele.graphed(self._selected_tool_id)
        return item.graph_max if item is not None else 0

    @Property("QVariantList", notify=changed)
    def readoutGraphPoints(self) -> list[float]:
        return list(self._readout_series.window)

    @Property(bool, notify=changed)
    def isWatchingReadouts(self) -> bool:
        return "readout" in self._telemetry_stops

    def _watch_readouts(self) -> None:
        """Read-only watch of the frames the selected tool broadcasts; nothing is transmitted.

        It holds the transport for reading like every other watch, but an output may be switched on while it runs
        (that is what a temperature readout is for): see canActuateSelectedProfile."""
        tool_id = self._selected_tool_id
        by_id: dict[int, list] = {}
        for item in tele.readouts_for(tool_id):
            by_id.setdefault(item.can_id, []).append(item)
        transport = self._transport
        if transport is None:
            return
        stop = threading.Event()
        self._telemetry_stops["readout"] = stop
        self._readout_values.clear()
        self._readout_series.clear()
        self._set_state(status="WATCHING LIVE READOUTS", busy=True)
        self._log(f"TELEMETRY_WATCH_STARTED key=readout tool={tool_id}")

        def _worker() -> None:
            try:
                while not stop.is_set():
                    frame = transport.read_frame(timeout=0.1)
                    if frame is None or frame[0] not in by_id:
                        continue
                    for item in by_id[frame[0]]:
                        decoded = tele.decode_readout(item, bytes(frame[1]))
                        if decoded is not None:
                            self._readoutUpdated.emit(item.key, decoded[0], decoded[1])
            except Exception as exc:
                self._log(f"TELEMETRY_WATCH_FAILED key=readout error={exc}")
            finally:
                self._telemetry_stops.pop("readout", None)
                self._set_state(status="ACTIVE CHECKS ARMED" if not self._listen_only else "READ-ONLY READY", busy=False)
                self._log("TELEMETRY_WATCH_STOPPED key=readout")

        self._telemetry_thread = threading.Thread(target=_worker, daemon=True, name="urtc-tester-readout-watch")
        self._telemetry_thread.start()

    @Slot(str, str, float)
    def _on_readout(self, key: str, text: str, value: float) -> None:
        self._readout_values[key] = text
        graphed = tele.graphed(self._selected_tool_id)
        if graphed is not None and graphed.key == key:
            self._readout_series.add(value, time.monotonic())
        self.changed.emit()

    @Slot(str, result=str)
    def exportReadoutCsv(self, path_text: str) -> str:
        """Save the recorded temperature series (every point since the watch started) as seconds,value; returns the path."""
        graphed = tele.graphed(self._selected_tool_id)
        path = QUrl(path_text).toLocalFile() if path_text.startswith("file:") else path_text
        if graphed is None or not self._readout_series.history:
            self._log("READOUT_EXPORT_EMPTY")
            return ""
        try:
            count = tele.write_csv(path, graphed.key, self._readout_series.history)
        except OSError as exc:
            self._log(f"READOUT_EXPORT_FAILED {exc}")
            return ""
        self._log(f"READOUT_EXPORTED {count} points {path}")
        return path

    @Slot()
    def stopTelemetryWatch(self) -> None:
        """Deliberately not busy-gated - see watchTelemetry's own
        docstring. The worker thread itself clears busy once it actually
        exits, not this Slot, so a caller can never observe busy=False
        while the read loop is still genuinely running."""
        for stop in self._telemetry_stops.values():
            stop.set()

    def _decode_vacuum_frame(self, data: bytes) -> None:
        decoded = protocol.decode_vacuum_frame(data)
        if decoded is not None:
            self._vacuumTelemetry.emit(decoded["adc"], decoded["detected"])

    @Slot(int, bool)
    def _on_vacuum_telemetry(self, adc: int, detected: bool) -> None:
        self._vacuum_adc = adc
        self._vacuum_detected = detected
        self.changed.emit()

    def _decode_scan_probe_frame(self, data: bytes) -> None:
        if protocol.is_scan_probe_impact(data):
            self._scanProbeImpact.emit(time.strftime("%H:%M:%S"))

    @Slot(str)
    def _on_scan_probe_impact(self, timestamp: str) -> None:
        self._scan_probe_impact_count += 1
        self._scan_probe_last_impact = timestamp
        self._log(f"SCAN_PROBE_IMPACT ts={timestamp}")
        self.changed.emit()

    # -- tool-independent utility panels (Global Controls/Expansion
    # Board/F-RAM) -------------------------------------------------------

    def _run_query(self, key: str, request: tuple[int, bytes] | None, response_id: int, decode, timeout_s: float = 1.0) -> None:
        """Real, generic bounded request/response worker - every query
        below (F-RAM state, expansion board type, MLX variant, free tool
        config, peripheral info, DIAG0, the SPI passthrough) is the exact
        same real shape: send an optional request, wait up to timeout_s
        for the matching response CAN ID, decode it, and emit the real
        result (or None on a genuine timeout - never a guessed value)
        through the one shared _queryResult signal, keyed so
        _on_query_result routes it to the right real Property."""
        transport = self._transport
        if transport is None:
            return
        if self._busy:
            self._log(f"QUERY_BLOCKED key={key} another read is in progress")
            return

        def _worker() -> None:
            # one exchange at a time: two readers on the same transport would eat each other's answers
            with self._io_lock:
                try:
                    if request is not None:
                        transport.send_frame(*request)
                    deadline = time.monotonic() + timeout_s
                    while time.monotonic() < deadline:
                        frame = transport.read_frame(timeout=0.1)
                        if frame is not None and frame[0] == response_id:
                            self._queryResult.emit(key, decode(frame[1]))
                            return
                    self._queryResult.emit(key, None)
                except Exception as exc:
                    self._log(f"QUERY_FAILED key={key} error={exc}")
                    self._queryResult.emit(key, None)

        threading.Thread(target=_worker, daemon=True, name=f"urtc-tester-query-{key}").start()

    @Slot(str, object)
    def _on_query_result(self, key: str, result: object) -> None:
        # LBL_NO_RESPONSE_OLDER_FW is a real, pre-existing key - no fallback needed here.
        no_response = _("LBL_NO_RESPONSE_OLDER_FW")
        if key == "fram_state":
            if result is None:
                text = _("LBL_FRAM_NO_RESPONSE")
            elif not result["valid"]:
                text = _("LBL_FRAM_NO_VALID_STATE")
            else:
                tool_name = TOOL_NAMES.get(result["tool_id"], f"unknown ({result['tool_id']})")
                text = _(
                    "LBL_FRAM_STATE_TEXT", tool=tool_name, temp=result["temp"], speed=result["speed"],
                    dir_or_interlock=_("VAL_ON") if result["dir_or_interlock"] else _("VAL_OFF"),
                    fan=result["fan"], had_error=_("VAL_YES") if result["had_error"] else _("VAL_NO"),
                )
            self._log(f"FRAM_STATE {result}")
        elif key == "thermal_stats":
            text = format_thermal_stats(result)
            self._log(f"THERMAL_STATS {result}")
        elif key == "black_box":
            if result is not None and result[0] == "ok":
                text = _("LBL_BLACKBOX_SAVED", summary=result[1], csv=result[2], json=result[3])
                self._log(f"BLACK_BOX_SAVED {result[2]} {result[3]}")
            else:
                text = _("LBL_BLACKBOX_FAILED", reason=result[1] if result else "?")
                self._log(f"BLACK_BOX_FAILED {text}")
        elif key == "features":
            if result is None:
                text = _("LBL_FEATURES_NO_RESPONSE")
            else:
                text = _("LBL_FEATURES_TEXT", stored=extras.features_text(result["stored"]), running=extras.features_text(result["running"]),
                         supported=extras.features_text(result["supported"]))
            self._log(f"FIRMWARE_FEATURES {result}")
        elif key == "pid":
            if result is None:
                text = _("LBL_PID_NO_RESPONSE")
            else:
                label_key = extras.PID_STATE_KEYS.get(result["state_name"])
                state = _(label_key) if label_key else result["state_name"]
                text = _("LBL_PID_TEXT", kp=f"{result['kp']:g}", ki=f"{result['ki']:g}", kd=f"{result['kd']:g}", state=state, duty=result["duty_percent"])
            self._log(f"HEATER_PID {result}")
        elif key == "thermal_view":
            if result is not None and result[0] == "ok":
                self._thermal_view_source = extras.thermal_data_url(result[1])
                text = _("LBL_THERMAL_VIEW_TEXT", text=extras.thermal_summary(result[1], False))
            else:
                text = _("LBL_THERMAL_READ_FAILED", reason=result[1] if result else "?")
            self._log(f"THERMAL_VIEW {text}")
        elif key == "expansion_type":
            text = result if result is not None else no_response
            self._log(f"EXPANSION_BOARD_TYPE {result}")
        elif key == "mlx_variant":
            text = result if result is not None else no_response
            self._log(f"MLX_SENSOR_VARIANT {result}")
        elif key == "free_tool_config":
            if result is None:
                text = no_response
            else:
                jumper_desc = _("LBL_FREE_TOOL_JUMPERS_0X1F") if result["raw_id_pin"] == 31 else _("LBL_FREE_TOOL_JUMPERS_OTHER", value=result["raw_id_pin"])
                selection_desc = result["tool_name"] or _("LBL_FREE_TOOL_NONE_SELECTED")
                text = f"{jumper_desc}\n{_('LBL_FREE_TOOL_SELECTION', tool=selection_desc)}"
            self._log(f"FREE_TOOL_CONFIG {result}")
        elif key == "peripheral_info":
            if result is None:
                text = no_response
            else:
                type_desc = _("LBL_PERIPHERAL_TYPE_URTC") if result["is_urtc"] else _("LBL_PERIPHERAL_TYPE_UNKNOWN", value=result["peripheral_type"])
                text = f"{type_desc}\n{_('LBL_DEVICE_SERIAL', serial=result['serial'])}"
            self._log(f"PERIPHERAL_INFO {result}")
        elif key == "feeder_position":
            text = _("VAL_FEEDER_STEPS", n=result) if result is not None else no_response
            self._log(f"FEEDER_POSITION {result}")
        elif key == "diag0":
            text = (_("LBL_DIAG0_HIGH") if result else _("LBL_DIAG0_LOW")) if result is not None else _("LBL_NO_RESPONSE_SHORT")
            self._log(f"DIAG0 {result}")
        elif key == "spi_response":
            text = result.hex(" ") if result else (_("LBL_EMPTY_PARENS") if result == b"" else _("LBL_SPI_NO_RESPONSE"))
            self._log(f"SPI_RESPONSE {result}")
        else:
            return
        self._query_texts[key] = text
        self.changed.emit()

    @Slot(str, str, str, str, str, str, str, bool)
    def sendGlobalStatus(self, status_r: str, status_g: str, status_b: str, night_mode: str, ring_r: str, ring_g: str, ring_b: str, ring_on: bool) -> None:
        if not self.canUseUtilityPanels:
            self._log("GLOBAL_STATUS_BLOCKED not connected or not in active-check mode")
            return
        try:
            can_id, data = protocol.global_status_frame((status_r, status_g, status_b), night_mode, (ring_r, ring_g, ring_b), ring_on)
        except ValueError as exc:
            self._log(f"GLOBAL_STATUS_BLOCKED {exc}")
            return
        transport = self._transport
        if transport is None:
            return
        transport.send_frame(can_id, data)
        self._log(f"GLOBAL_STATUS_SENT {data.hex(' ')}")

    @Slot(str)
    def sendExpansionSpi(self, hex_bytes: str) -> None:
        if not self.canUseUtilityPanels:
            self._log("EXP_SPI_BLOCKED not connected or not in active-check mode")
            return
        try:
            request = protocol.spi_passthrough_frame(hex_bytes)
        except ValueError as exc:
            self._log(f"EXP_SPI_BLOCKED {exc}")
            return
        self._run_query("spi_response", request, CAN_ID_EXP_SPI_RESP, protocol.decode_spi_response)

    @Slot()
    def queryDiag0(self) -> None:
        if not self.canUseUtilityPanels:
            return
        self._run_query("diag0", (CAN_ID_QUERY_DIAG0, b""), CAN_ID_DIAG0_RESP, protocol.decode_diag0)

    @Slot()
    def queryFramState(self) -> None:
        if not self.canUseUtilityPanels:
            return
        self._run_query("fram_state", (CAN_ID_QUERY_FRAM_STATE, b""), CAN_ID_FRAM_STATE_RESP, protocol.decode_fram_state)

    @Slot()
    def queryThermalStats(self) -> None:
        if not self.canUseUtilityPanels:
            return
        self._run_query("thermal_stats", (CAN_ID_QUERY_THERMAL_STATS, b""), CAN_ID_THERMAL_STATS_RESP, protocol.decode_thermal_stats)

    @Slot()
    def eraseFram(self) -> None:
        """QML asks for an explicit confirmation immediately before
        calling this Slot (same real requestAdvanced-style pattern every
        other real physical/destructive action in this deck already
        uses) - a genuine, irreversible erase of the board's own
        recovered-state memory, not something a stray click should reach."""
        if not self.canUseUtilityPanels:
            self._log("ERASE_FRAM_BLOCKED not connected or not in active-check mode")
            return
        self._run_query("fram_state", (CAN_ID_ERASE_FRAM, ERASE_FRAM_MAGIC), CAN_ID_FRAM_STATE_RESP, protocol.decode_fram_state)

    @Slot()
    def queryExpansionBoardType(self) -> None:
        if not self.canUseUtilityPanels:
            return
        self._run_query("expansion_type", (CAN_ID_EXPANSION_TYPE_RESP, b""), CAN_ID_EXPANSION_TYPE_RESP, protocol.decode_expansion_board_type)

    @Slot()
    def queryMlxSensorVariant(self) -> None:
        if not self.canUseUtilityPanels:
            return
        self._run_query("mlx_variant", (CAN_ID_MLX_VARIANT_RESP, b""), CAN_ID_MLX_VARIANT_RESP, protocol.decode_mlx_sensor_variant)

    @Slot()
    def queryFreeToolConfig(self) -> None:
        if not self.canUseUtilityPanels:
            return
        self._run_query("free_tool_config", (CAN_ID_FREE_TOOL_CONFIG_RESP, b""), CAN_ID_FREE_TOOL_CONFIG_RESP, protocol.decode_free_tool_config)

    @Slot()
    def queryFeederPosition(self) -> None:
        if not self.canUseUtilityPanels:
            return
        self._run_query("feeder_position", (CAN_ID_SOLDER_FEEDER_POS, b""), CAN_ID_SOLDER_FEEDER_POS, protocol.decode_feeder_position)

    @Slot()
    def resetFeederPosition(self) -> None:
        """QML asks for an explicit confirmation immediately before calling this: the tracked position goes back to 0
        (done after loading a fresh spool). The board answers with the new position."""
        if not self.canUseUtilityPanels:
            self._log("FEEDER_RESET_BLOCKED not connected or not in active-check mode")
            return
        self._run_query("feeder_position", (CAN_ID_SOLDER_FEEDER_RESET, SOLDER_FEEDER_RESET_MAGIC), CAN_ID_SOLDER_FEEDER_POS, protocol.decode_feeder_position)
        self._log("FEEDER_POSITION_RESET")

    @Slot()
    def queryPeripheralInfo(self) -> None:
        if not self.canUseUtilityPanels:
            return
        self._run_query("peripheral_info", (CAN_ID_PERIPHERAL_INFO_RESP, b""), CAN_ID_PERIPHERAL_INFO_RESP, protocol.decode_peripheral_info)

    # -- Custom CAN Frame - see this class's own __init__ comment on
    # _custom_periodic_active for why periodic re-send is QML-Timer-owned
    # rather than a Python thread like every other periodic mechanism
    # above. ----------------------------------------------------------
    @staticmethod
    def _parse_custom_frame(can_id_text: str, data_text: str) -> tuple[int, bytes]:
        """Validation of the custom frame - 11-bit ID range,
        DLC<=8, space-separated hex bytes. Raises ValueError with a
        message suitable for the activity log directly."""
        try:
            can_id = int(can_id_text, 16)
        except (TypeError, ValueError):
            raise ValueError(f"'{can_id_text}' isn't a valid hex CAN ID.") from None
        if not (0 <= can_id <= 0x7FF):
            raise ValueError(f"CAN ID 0x{can_id:X} is outside the standard 11-bit range (0-0x7FF).")
        text = data_text.strip()
        try:
            values = [int(b, 16) for b in text.split()] if text else []
        except ValueError:
            raise ValueError(f"'{text}' isn't valid space-separated hex bytes, e.g. 01 02 03.") from None
        out_of_range = [v for v in values if not (0 <= v <= 0xFF)]
        if out_of_range:
            raise ValueError(f"{out_of_range[0]:#x} is out of range for a single byte (00-FF).")
        data = bytes(values)
        if len(data) > 8:
            raise ValueError(f"{len(data)} bytes given - a CAN frame carries at most 8.")
        return can_id, data

    @Slot(str, str)
    def sendCustomFrame(self, can_id_hex: str, data_hex: str) -> None:
        """Manual 'Send Once' button - logs every send, matching the
        legacy panel's own _send_custom_frame_once exactly."""
        if not self.canUseUtilityPanels:
            self._log("CUSTOM_FRAME_BLOCKED not connected or not in active-check mode")
            return
        try:
            can_id, data = self._parse_custom_frame(can_id_hex, data_hex)
        except ValueError as exc:
            self._log(f"CUSTOM_FRAME_BLOCKED {exc}")
            return
        transport = self._transport
        if transport is None:
            return
        transport.send_frame(can_id, data)
        self._log(f"CUSTOM_FRAME_SENT can_id=0x{can_id:03X} data={data.hex(' ') if data else '(empty)'}")

    @Slot(bool, str, str, str)
    def setCustomFramePeriodic(self, enabled: bool, can_id_hex: str, data_hex: str, interval_text: str) -> None:
        """Backend-owned toggle for the 'Repeat every' CheckBox - see
        _custom_periodic_active's own comment for why this, not the
        CheckBox's own local state, is the single source of truth.
        Validates once here at the moment of turning on (same real
        gate/parse as sendCustomFrame), then leaves each tick's own
        re-parse to sendCustomFramePeriodicTick - matching the legacy
        _toggle_custom_periodic/_send split exactly."""
        if not enabled:
            self._custom_periodic_active = False
            self.changed.emit()
            return
        if not self.canUseUtilityPanels:
            self._log("CUSTOM_FRAME_PERIODIC_BLOCKED not connected or not in active-check mode")
            return
        try:
            can_id, data = self._parse_custom_frame(can_id_hex, data_hex)
        except ValueError as exc:
            self._log(f"CUSTOM_FRAME_PERIODIC_BLOCKED {exc}")
            return
        interval_ms = self._bounded_int(interval_text, 10, 10000) or 100
        self._custom_periodic_active = True
        self._custom_periodic_last_ok = True
        data_str = data.hex(' ') if data else '(empty)'
        self._log(f"CUSTOM_FRAME_PERIODIC_STARTED interval_ms={interval_ms} can_id=0x{can_id:03X} data={data_str}")
        self.changed.emit()

    @Slot(str, str)
    def sendCustomFramePeriodicTick(self, can_id_hex: str, data_hex: str) -> None:
        """Called every interval by the QML Timer (customFrameTimer in
        TesterDeck.qml) while 'Repeat every' is checked - re-parses the
        fields on every tick, so a live-edited value takes effect without
        needing to stop/restart. Deliberately silent on an ordinary
        successful send (unlike sendCustomFrame's manual button) - only
        logs once on the transition into/out of a parse failure, or the
        activity log (last 14 entries) would show nothing but this at
        any interval faster than a few seconds."""
        if not self.canUseUtilityPanels:
            return
        try:
            can_id, data = self._parse_custom_frame(can_id_hex, data_hex)
        except ValueError as exc:
            if self._custom_periodic_last_ok:
                self._custom_periodic_last_ok = False
                self._log(f"CUSTOM_FRAME_PERIODIC_SKIPPING {exc}")
            return
        if not self._custom_periodic_last_ok:
            self._custom_periodic_last_ok = True
            self._log("CUSTOM_FRAME_PERIODIC_RESUMING")
        transport = self._transport
        if transport is None:
            return
        transport.send_frame(can_id, data)

    @staticmethod
    def _bounded_int(value: str, minimum: int, maximum: int) -> int | None:
        """Parse an operator value STRICTLY - None on anything malformed
        OR out of range, never a silently clamped substitute.

        this used to CLAMP an out-of-range value into range
        (e.g. a garbled 999999 became this command's own maximum - a
        real, different command, not an error). Returning None for that
        case too costs nothing at any call site: every one of them
        already treats a None result as "blocked, log and return" -
        exactly the real rejection this fix needs, not a new code path.
        isinstance(value, bool) is never reachable here (this only ever
        receives a QML string), so no separate bool guard is needed the
        way advanced_protocol.py's own bounded_int() has one.
        """
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        if not (minimum <= parsed <= maximum):
            return None
        return parsed

    @Slot(str, str)
    def sendDrill(self, speed_text: str, direction: str) -> None:
        if not self._require_profile({5}, "DRILL"):
            return
        speed = self._bounded_int(speed_text, 0, 255)
        if speed is None:
            self._log("DRILL_BLOCKED speed must be an integer in range")
            return
        # see sendMotion's own comment - an unrecognized
        # direction must never silently become the opposite valid one.
        if direction not in ("clockwise", "counter-clockwise"):
            self._log(f"DRILL_BLOCKED unknown direction {direction!r}")
            return
        # The firmware cuts the drill after 250 ms without a new command and latches a CRITICAL ERROR, so a drill that runs is refreshed like the laser and the heaters, and speed 0
        # (the active brake) stops that refreshing. A single frame used to spin the drill for 250 ms and leave the board in error.
        frame = protocol.drill_frame(speed, direction)
        off = (CAN_ID_DRILL_CMD, b"\x00\x00")
        if speed == 0:
            self._stop_watchdog("drill", off)
            self._log(f"DRILL_STOPPED direction={direction} (speed 0, active brake)")
            return
        self._start_watchdog("drill", 0.15, frame, off)
        self._log(f"DRILL_SENT speed={speed} direction={direction} (refreshed every 150 ms)")

    @Slot(str, str)
    def sendAoi(self, mode: str, period_text: str) -> None:
        if not self._require_profile({8}, "AOI"):
            return
        period = self._bounded_int(period_text, 1, AOI_STROBE_MAX_MS)
        if period is None or mode not in ("off", "strobe", "continuous"):
            self._log("AOI_BLOCKED invalid mode or strobe period")
            return
        try:
            self._transport.send_frame(*protocol.aoi_frame(mode, period))
            self._log(f"AOI_SENT mode={mode} period_ms={period}")
        except Exception as exc:
            self._log(f"AOI_FAILED {exc}")

    @Slot(bool)
    def setElectromagnet(self, energized: bool) -> None:
        if not self._require_profile({13}, "ELECTROMAGNET"):
            return
        try:
            self._transport.send_frame(*protocol.magnet_frame(energized))
            self._log(f"ELECTROMAGNET_SENT state={'energized' if energized else 'released'}")
        except Exception as exc:
            self._log(f"ELECTROMAGNET_FAILED {exc}")

    @Slot(str)
    def fireWeldPulse(self, duration_text: str) -> None:
        if not self._require_profile({14, 24}, "WELD_PULSE"):
            return
        duration = self._bounded_int(duration_text, 1, 2000)
        if duration is None:
            self._log("WELD_PULSE_BLOCKED duration must be an integer in range")
            return
        try:
            self._transport.send_frame(*protocol.weld_frame(self._selected_tool_id, duration))
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
            self._log("PASTE_CONFIG_BLOCKED channel/frequency must be integers in range")
            return
        try:
            self._transport.send_frame(*protocol.paste_config_frame(channel, frequency))
            self._log(f"PASTE_CONFIG_SENT channel={channel} frequency_hz={frequency}")
        except Exception as exc:
            self._log(f"PASTE_CONFIG_FAILED {exc}")

    @Slot(str, str, str)
    def firePastePulse(self, channel_text: str, duty_text: str, duration_text: str) -> None:
        if not self._require_profile({23}, "PASTE_PULSE"):
            return
        channel = self._bounded_int(channel_text, 0, 3)
        duty = self._bounded_int(duty_text, 0, 100)
        duration = self._bounded_int(duration_text, 1, 255)   # 0 would be a continuous pulse that nothing here can stop
        if channel is None or duty is None or duration is None:
            self._log("PASTE_PULSE_BLOCKED channel/duty/duration must be integers in range")
            return
        try:
            self._transport.send_frame(*protocol.paste_pulse_frame(channel, duty, duration))
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
                self._log("PRINTER_BLOCKED hotend fan power must be an integer in range")
                return
            frame = protocol.printer_frame(action, power, 0)
        elif action == "extruder":
            steps = self._bounded_int(first_text, 0, 0xFFFFFF)
            temperature = self._bounded_int(second_text, 0, 300)
            if steps is None or temperature is None:
                self._log("PRINTER_BLOCKED extruder steps/temperature must be integers in range")
                return
            frame = protocol.printer_frame(action, steps, temperature)
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
        if not self._require_profile({17}, "FLYING_PROBE_READ", reads=True):
            return
        self._set_state(status="READING FLYING PROBE", busy=True)
        threading.Thread(target=self._read_flying_probe_worker, args=(self._transport,), daemon=True, name="urtc-flying-probe-read").start()

    def _read_flying_probe_worker(self, transport) -> None:
        with self._io_lock:
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
        if not self._require_profile({22}, "THERMAL_CAPTURE", reads=True):
            return
        self._set_state(status="CAPTURING THERMAL FRAME", busy=True)
        threading.Thread(target=self._capture_thermal_worker, args=(self._transport,), daemon=True, name="urtc-thermal-capture").start()

    def _read_one(self, transport, can_id: int, timeout: float) -> bytes | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            frame = transport.read_frame(timeout=0.05)
            if frame is not None and frame[0] == can_id:
                return frame[1]
        return None

    def _capture_thermal_worker(self, transport) -> None:
        """Read the documented calibrated frame without a write path: ask which sensor is fitted, trigger, wait until the capture is ready, then read every chunk."""
        with self._io_lock:
            cells: list[dict[str, object]] = []
            try:
                transport.send_frame(CAN_ID_MLX_VARIANT_RESP, b"")
                variant = self._read_one(transport, CAN_ID_MLX_VARIANT_RESP, 0.5)
                if variant:
                    grid = protocol.thermal_grid(variant[0])
                    if grid is None:
                        self._thermalResult.emit([], "THERMAL_CAPTURE_FAILED no thermal sensor is configured on the board")
                        return
                else:
                    grid = (32, 24, 48)  # firmware without the variant register: the full-size sensor
                width, height, chunk_count = grid
                transport.send_frame(CAN_ID_THERMAL_TRIGGER, b"")
                ready = False
                deadline = time.monotonic() + 2.0
                while time.monotonic() < deadline:
                    transport.send_frame(CAN_ID_THERMAL_STATUS, b"")
                    status = self._read_one(transport, CAN_ID_THERMAL_STATUS, 0.25)
                    if status and status[0] == protocol.THERMAL_STATUS_READY:
                        ready = True
                        break
                    if status and status[0] == 0xFF:
                        break
                if not ready:
                    self._thermalResult.emit([], "THERMAL_CAPTURE_FAILED the sensor did not become ready")
                    return
                chunks: dict[int, list[int]] = {}
                for chunk_index in range(chunk_count):
                    for _attempt in range(2):
                        transport.send_frame(CAN_ID_THERMAL_CALIB_CHUNK_REQ, bytes([chunk_index]))
                        frames: list[bytes] = []
                        deadline = time.monotonic() + 0.3
                        while len(frames) < protocol.THERMAL_CHUNK_FRAMES and time.monotonic() < deadline:
                            frame = transport.read_frame(timeout=0.05)
                            if frame is not None and frame[0] == CAN_ID_THERMAL_CALIB_CHUNK and len(frame[1]) == 8:
                                frames.append(frame[1])
                        decoded = protocol.decode_thermal_chunk(frames)
                        if decoded is not None:
                            chunks[chunk_index] = decoded
                            break
                self._thermal_columns = width
                for temperature in protocol.thermal_pixels(chunks, chunk_count):
                    if temperature is None:
                        cells.append({"temperature": 0, "color": "#202020", "missing": True})
                    else:
                        cells.append({"temperature": temperature, "color": self._thermal_color(temperature), "missing": False})
                self._thermalResult.emit(cells, f"THERMAL_CAPTURE size={width}x{height} chunks={len(chunks)}/{chunk_count} cells={len(cells)}")
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
        with self._io_lock:
            self._passive_capture_locked(transport)

    def _passive_capture_locked(self, transport) -> None:
        deadline = time.monotonic() + 2.0
        count = 0
        identifiers: set[int] = set()
        frames: list[dict[str, str]] = []
        # Real bus-load estimate, derived from this same 2.0 s window's own
        # frame count/sizes rather than a second, separate tracking
        # mechanism. Per-frame bit cost uses the standard CAN 2.0A
        # 11-bit-ID data-frame overhead (SOF 1 + arbitration 12 + control
        # 6 + CRC 16 + ACK 2 + EOF 7 + IFS 3 = 47 fixed bits) plus 8 data
        # bits per byte actually seen - bit stuffing is deliberately not
        # modeled (it depends on the actual bit pattern, not just frame
        # count/size), so this reads slightly low on buses with a lot of
        # same-bit runs, never high.
        CAN_FRAME_OVERHEAD_BITS = 47
        total_bits = 0
        try:
            while time.monotonic() < deadline:
                frame = transport.read_frame(timeout=0.1)
                if frame is None:
                    continue
                can_id, data = frame
                count += 1
                identifiers.add(can_id)
                total_bits += CAN_FRAME_OVERHEAD_BITS + 8 * len(data)
                frames.append(
                    {
                        "id": f"0x{can_id:03X}",
                        "data": data.hex(" ").upper() or "(empty)",
                    }
                )
                if len(frames) > 24:
                    frames.pop(0)
            load_percent = (total_bits / (bitrate_bps_for_label(self._bitrate_label) * 2.0)) * 100.0
            summary = f"2.0 s • {count} frame(s) • {len(identifiers)} CAN ID(s) • {load_percent:.1f}% bus load"
            self._passiveResult.emit(frames, summary, load_percent)
        except Exception as exc:
            self._passiveResult.emit([], f"PASSIVE_CAPTURE_FAILED {exc}", 0.0)

    @Slot(object, str, float)
    def _on_passive_result(self, frames: list[dict[str, str]], summary: str, load_percent: float) -> None:
        self._passive_frames = frames
        self._passive_summary = summary
        self._passive_load_percent = load_percent
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
        with self._io_lock:
            try:
                transport = self._transport
                if transport is None:
                    raise RuntimeError("transport disconnected before identity probe")
                transport.send_frame(CAN_ID_QUERY_ACTIVE_TOOL, b"")
                tool_data = self._wait_for(CAN_ID_ACTIVE_TOOL_RESP, 1.5)
                transport.send_frame(CAN_ID_QUERY_VERSION, b"\x00")
                version_data = self._wait_for(CAN_ID_VERSION_RESPONSE, 1.5)
                # Firmware 0.3.5 and newer sends the patch number in the next frame; older firmware sends nothing.
                self._version_patch_frame = self._wait_for(CAN_ID_VERSION_PATCH_RESPONSE, VERSION_PATCH_GRACE_S) if version_data is not None else None
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
            quick = protocol.decode_quick_state(bytes(tool_data))
            if quick is not None and quick["thermal_fault"]:
                state = f"{state} - THERMAL FAULT {quick['thermal_fault_name']}"
            if quick is not None and quick["reset_causes"]:
                self._log(f"RESET_CAUSE {', '.join(quick['reset_causes'])}")
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
            version_text = protocol.firmware_version_text(major, minor, self._version_patch_frame)
            self._version = f"{role} v{version_text} - HW 0x{hardware_id:08X} ({identity})"
            self._log(f"BOARD_VERSION {self._version}")
        else:
            self._version = "No response to version query"
            self._log("BOARD_VERSION no response")
        outcome = "PROBE COMPLETE" if tool_data is not None or version_data is not None else "NO RESPONSE"
        self._set_state(status=outcome, busy=False)
        # The board says it is in error: read its black box once for that fault, if the option is on.
        if tool_data is not None and self._auto_black_box.feed(bytes(tool_data)):
            if self.canUseUtilityPanels:
                self.readBlackBox()
            else:
                self._query_texts["black_box"] = _("LBL_BLACKBOX_AUTO_SKIPPED")
                self.changed.emit()


def run_qtquick() -> int:
    """Run the explicit, bounded Qt Quick diagnostics deck."""
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("URTC Tester")
    icon = QIcon(ICON_IMAGE_PATH)
    if not icon.isNull():
        app.setWindowIcon(icon)
    bridge = TesterQtBridge()
    # Closing the window switches every output off first (the watchdog threads are daemons and die without sending their safe-off frame).
    app.aboutToQuit.connect(bridge.shutdownOutputs)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("testerBackend", bridge)
    qml_path = Path(__file__).resolve().parent / "assets" / "qml" / "TesterDeck.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1
    return app.exec()
