# =============================================================================
# URTC Tester - TesterGUI: the main window, organized across 4 files by
# responsibility - this one holds __init__, connection/detection, and
# window lifecycle; the panel-building methods live in the 3 mixins
# below, combined here via multiple inheritance.
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
import logging
import os
import platform
import struct
import sys
import threading
import time
import zipfile
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from tester_config import (
    _, AVAILABLE_LANGUAGES, BANNER_IMAGE_PATH, BITRATE_500K_SLCAN_CODE, CAN_ID_3DP_HOTEND_FAN_CMD,
    CAN_ID_3DP_LAYER_FAN_CMD, CAN_ID_3DP_THERMAL_MOTION, CAN_ID_ACTIVE_TOOL_RESP,
    CAN_ID_DRILL_CMD, CAN_ID_LASER_CMD, CAN_ID_QUERY_ACTIVE_TOOL, CAN_ID_QUERY_VERSION,
    CAN_ID_UV_CURING_CMD, CAN_ID_HOTAIR_CMD,
    CAN_ID_SOLDER_SETPOINT, CAN_ID_VERSION_RESPONSE, CONFIG_PATH, ICON_IMAGE_PATH,
    LOGS_FOLDER, MOTION_TOOL_IDS, SLCAN_BITRATES, TESTER_AUTHOR, TESTER_VERSION, THIS_HARDWARE_ID,
    TOOL_NAMES, list_serial_ports, load_language, save_config, _center_geometry,
)
from tester_transports import SLCAN, SLCANError, SocketCAN, SocketCANError, list_socketcan_interfaces
from tester_bus_monitor import CANBusMonitor
from tester_common_panels import CommonPanelsMixin
from tester_panel_helpers import PanelHelpersMixin
from tester_tool_panels import ToolPanelsMixin

try:
    import serial
    import serial.tools.list_ports
    HAVE_SERIAL = True
except ImportError:
    HAVE_SERIAL = False

import socket
HAVE_SOCKETCAN = hasattr(socket, "AF_CAN")


class TesterGUI(CommonPanelsMixin, PanelHelpersMixin, ToolPanelsMixin):

    def __init__(self, root):
        self.root = root
        root.title(f"URTC Tester v{TESTER_VERSION}")
        self._build_menu_bar()
        # Geometry (size + centered position) is set once in main(), before
        # this class is constructed - not here, so it isn't overwritten by
        # a second, uncentered geometry() call.
        root.resizable(True, True)

        self._file_logger = None
        try:
            os.makedirs(LOGS_FOLDER, exist_ok=True)
            log_path = os.path.join(LOGS_FOLDER, f"urtc_tester_{time.strftime('%Y%m%d_%H%M%S')}.log")
            self._file_logger = logging.getLogger(f"urtc_tester_{id(self)}")
            self._file_logger.setLevel(logging.INFO)
            handler = logging.FileHandler(log_path, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
            self._file_logger.addHandler(handler)
            self._file_logger.info(f"=== URTC Tester v{TESTER_VERSION} session started ===")
        except OSError:
            self._file_logger = None

        try:
            self._icon_img = tk.PhotoImage(file=ICON_IMAGE_PATH)
            root.iconphoto(True, self._icon_img)
        except (tk.TclError, OSError):
            pass

        self.transport = None
        self.bus = None  # CANBusMonitor, created on connect
        self.active_tool_id = None
        self._keepalive_jobs = {}  # name -> root.after() id, for watchdog-guarded commands currently repeating
        self._current_tool_id = None  # which tool's panel is currently showing, if any - see _send_tool_off_command
        self._bus_health_running = False  # guards _bus_health_worker's own loop - see _start_bus_health_monitor
        self._bus_health_was_bad = False  # tracks the last reported state, so a warning is only logged/popped up once per transition into trouble, not once per poll while it stays that way
        self._self_test_running = False  # guards _run_self_test against a second overlapping run - see that method's own comment
        # Bumped by _clear_tool_panel on every tool-panel rebuild (each
        # Detect) AND on disconnect. Long-running background workers a
        # tool panel starts (currently just the thermal inspection
        # panel's multi-second 48-chunk image read) capture this value at
        # launch and compare it on every iteration - once it no longer
        # matches, the panel that started them has been torn down (its
        # widgets destroyed), so they stop querying the bus and touching
        # now-dead widgets instead of running to completion regardless.
        self._tool_panel_generation = 0

        pad = {"padx": 8, "pady": 4}
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=1)  # notebook row
        root.grid_rowconfigure(3, weight=1)  # log row

        # --- Connect (fixed at the top, outside the tabs below - connection
        # state and the detected-tool status are relevant no matter which
        # tab is currently open, so these don't get hidden behind a tab
        # switch the way the rest of the controls do) ---
        conn_frame = ttk.LabelFrame(root, text=_("TAB_CONNECT_TITLE"))
        conn_frame.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        # Column weights - without these the frame just sits left-aligned
        # with blank space on the right as the window widens, since grid()
        # gives extra space only to columns with weight>0. Column 0 is
        # always a fixed-width label (LBL_TRANSPORT/LBL_COM_PORT/
        # LBL_BITRATE/LBL_ACTIVE_TOOL/LBL_ID_PINS/LBL_BOARD_STATE), so it
        # gets none. Columns 1-4 are where the actual variable-length
        # content lives - combo boxes plus the columnspan=3 status labels
        # (active_tool_label, id_pins_frame, board_state_label, the listen-
        # only help text, bitrate_status) - column 1 gets extra weight
        # since it's the anchor column those spans all start from, and
        # column 4 also carries conn_status, the single most important
        # value in this panel. Column 5 is only ever a small fixed button
        # or short value (selftest_btn/tool_number_label), so it stays at
        # the default weight of 0 like column 0.
        conn_frame.grid_columnconfigure(1, weight=2)
        conn_frame.grid_columnconfigure(2, weight=1)
        conn_frame.grid_columnconfigure(3, weight=1)
        conn_frame.grid_columnconfigure(4, weight=1)

        row = 0
        if HAVE_SOCKETCAN:
            ttk.Label(conn_frame, text=_("LBL_TRANSPORT")).grid(row=row, column=0, sticky="w", **pad)
            self.transport_var = tk.StringVar(value="serial" if HAVE_SERIAL else "socketcan")
            transport_sub = ttk.Frame(conn_frame)
            transport_sub.grid(row=row, column=1, columnspan=3, sticky="w")
            self.transport_radio_serial = ttk.Radiobutton(
                transport_sub, text=_("RADIO_SERIAL_SLCAN"), value="serial",
                variable=self.transport_var, command=self.on_transport_change,
                state="normal" if HAVE_SERIAL else "disabled",
            )
            self.transport_radio_serial.pack(side="left", padx=(4, 12))
            self.transport_radio_socketcan = ttk.Radiobutton(
                transport_sub, text=_("RADIO_SOCKETCAN_NATIVE"), value="socketcan",
                variable=self.transport_var, command=self.on_transport_change,
            )
            self.transport_radio_socketcan.pack(side="left")
            row += 1
        else:
            self.transport_var = tk.StringVar(value="serial")

        self.port_label = ttk.Label(conn_frame, text=_("LBL_COM_PORT") if self.transport_var.get() == "serial" else _("LBL_CAN_INTERFACE"))
        self.port_label.grid(row=row, column=0, sticky="w", **pad)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var, width=20, state="readonly")
        self.port_combo.grid(row=row, column=1, **pad)
        self.refresh_btn = ttk.Button(conn_frame, text=_("BTN_REFRESH"), command=self.refresh_ports)
        self.refresh_btn.grid(row=row, column=2, **pad)
        self.connect_btn = ttk.Button(conn_frame, text=_("BTN_CONNECT"), command=self.toggle_connect)
        self.connect_btn.grid(row=row, column=3, **pad)
        self.conn_status = ttk.Label(conn_frame, text=_("STATUS_NOT_CONNECTED"), foreground="red")
        self.conn_status.grid(row=row, column=4, **pad)
        row += 1

        self.bitrate_label = ttk.Label(conn_frame, text=_("LBL_BITRATE"))
        self.bitrate_label.grid(row=row, column=0, sticky="w", **pad)
        self.bitrate_var = tk.StringVar(value="500 kbit/s")
        self.bitrate_combo = ttk.Combobox(
            conn_frame, textvariable=self.bitrate_var, width=20, state="readonly",
            values=[label for label, _ in SLCAN_BITRATES],
        )
        self.bitrate_combo.grid(row=row, column=1, **pad)
        self.autobaud_btn = ttk.Button(conn_frame, text=_("BTN_AUTO_DETECT"), command=self.auto_detect_bitrate)
        self.autobaud_btn.grid(row=row, column=2, **pad)
        self.bitrate_status = ttk.Label(conn_frame, text="", foreground="gray")
        self.bitrate_status.grid(row=row, column=3, columnspan=2, sticky="w", **pad)
        if self.transport_var.get() != "serial":
            self.bitrate_combo.config(state="disabled")
            self.autobaud_btn.config(state="disabled")
        row += 1

        # --- Listen Only mode - purely passive monitoring, this tool never
        # puts a single bit on the wire while connected this way (not even
        # an ACK). Genuinely enforced at the transport level for SLCAN (the
        # adapter itself is told to open in Lawicel's own listen-only mode,
        # "L" instead of "O" - see tester_transports.py's own comment) and
        # at the application level for SocketCAN (real hardware listen-only
        # there needs the interface configured before it's brought up,
        # outside this app's control - see SocketCAN.open_channel's own
        # comment for the full reasoning). Locked once connected, same as
        # the bitrate controls above - changing transmit behavior mid-
        # session isn't a thing either transport supports without a full
        # reconnect anyway. ---
        self.listen_only_var = tk.BooleanVar(value=False)
        self.listen_only_check = ttk.Checkbutton(conn_frame, text=_("CHK_LISTEN_ONLY"), variable=self.listen_only_var)
        self.listen_only_check.grid(row=row, column=0, columnspan=2, sticky="w", padx=4, pady=(0, 4))
        ttk.Label(
            conn_frame, text=_("HELP_LISTEN_ONLY"),
            foreground="gray", wraplength=460, justify="left",
        ).grid(row=row, column=2, columnspan=3, sticky="w", padx=4, pady=(0, 4))
        row += 1

        # --- Detected tool status (replaces the flasher's firmware-version row) ---
        ttk.Label(conn_frame, text=_("LBL_ACTIVE_TOOL")).grid(row=row, column=0, sticky="w", **pad)
        self.active_tool_label = ttk.Label(conn_frame, text=_("STATUS_CONNECT_TO_DETECT"), foreground="gray")
        self.active_tool_label.grid(row=row, column=1, columnspan=3, sticky="w", **pad)
        self.detect_btn = ttk.Button(conn_frame, text=_("BTN_DETECT"), command=self.detect_active_tool)
        self.detect_btn.grid(row=row, column=4, **pad)
        self.selftest_btn = ttk.Button(conn_frame, text=_("BTN_RUN_SELF_TEST"), command=self._run_self_test)
        self.selftest_btn.grid(row=row, column=5, **pad)
        row += 1

        # ID jumper pins (ID4 down to ID0, matching ECOVIA.TXT's documented
        # MSB-to-LSB order) plus the resulting tool number - decoded
        # straight from the same active_tool byte the 0x111 response
        # already carries (it IS the raw 5-bit jumper reading - confirmed
        # against Identify_PhysicalTool() in firmware_identify.c, which
        # builds it bit by bit from ID0..ID4 the same way), so no separate
        # query or firmware change is needed for this display.
        ttk.Label(conn_frame, text=_("LBL_ID_PINS")).grid(row=row, column=0, sticky="w", **pad)
        id_pins_frame = ttk.Frame(conn_frame)
        id_pins_frame.grid(row=row, column=1, columnspan=3, sticky="w", **pad)
        self._id_pin_squares = []
        for bit_label in ("ID4", "ID3", "ID2", "ID1", "ID0"):
            cell = ttk.Frame(id_pins_frame)
            cell.pack(side="left", padx=(0, 10))
            ttk.Label(cell, text=bit_label, font=("", 8)).pack()
            sq = tk.Label(cell, text="?", width=2, height=1, relief="solid", borderwidth=1,
                          font=("", 11, "bold"), bg="#DDDDDD", fg="#666666")
            sq.pack()
            self._id_pin_squares.append(sq)
        ttk.Label(conn_frame, text=_("LBL_TOOL_NUMBER")).grid(row=row, column=4, sticky="w", padx=(0, 2))
        self.tool_number_label = ttk.Label(conn_frame, text="--", font=("", 13, "bold"))
        self.tool_number_label.grid(row=row, column=5, sticky="w", padx=(0, 8))
        row += 1

        ttk.Label(conn_frame, text=_("LBL_BOARD_STATE")).grid(row=row, column=0, sticky="w", **pad)
        self.board_state_label = ttk.Label(conn_frame, text=_("STATUS_CONNECT_TO_CHECK"), foreground="gray")
        self.board_state_label.grid(row=row, column=1, columnspan=3, sticky="w", **pad)

        # --- Tabbed body: everything below Connect lives in one of these
        # pages instead of being permanently visible side by side - the
        # window only needs to be wide enough to show whichever single
        # tab is open, not 3 columns of sections at once. ---
        notebook = ttk.Notebook(root)
        notebook.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        self._notebook = notebook

        global_tab = ttk.Frame(notebook, padding=8)
        exp_tab = ttk.Frame(notebook, padding=8)
        fram_tab = ttk.Frame(notebook, padding=8)
        self.tool_tab = ttk.Frame(notebook, padding=8)
        custom_tab = ttk.Frame(notebook, padding=8)
        notebook.add(global_tab, text=_("TAB_GLOBAL_CONTROLS"))
        notebook.add(exp_tab, text=_("TAB_EXPANSION_BOARD"))
        notebook.add(fram_tab, text=_("TAB_FRAM"))
        notebook.add(self.tool_tab, text=_("TAB_TOOL_CONTROLS"))
        notebook.add(custom_tab, text=_("TAB_CUSTOM_FRAME"))

        # --- Global controls (0x100) - status LED, ring LED, OLED mode.
        # Applies regardless of which tool is active, so this frame is
        # built once and never torn down/rebuilt the way the per-tool
        # frame below is. ---
        self._build_global_panel(global_tab)

        # --- Expansion board (CONN_EXPANSION) - also global, not tied to
        # any specific active_tool, so built once here the same as the
        # panel above. ---
        self._build_expansion_panel(exp_tab)

        # --- Persistence F-RAM - a core board component (shares I2C2 with
        # the OLED), not part of the expansion connector at all, so this
        # gets its own tab rather than living inside "Expansion Board". ---
        self._build_fram_panel(fram_tab)

        # --- Custom/arbitrary CAN frame injector - also global. Useful for
        # exercising a command that doesn't have its own dedicated panel
        # control yet, testing something not (or not yet) documented in
        # CANBUS.TXT, or just sending a raw frame to see what happens. ---
        self._build_custom_frame_panel(custom_tab)

        # --- Dynamic per-tool tab - populated by rebuild_tool_panel() once
        # the active tool is known. Its own inner frame is destroyed and
        # rebuilt from scratch on every detect, rather than trying to
        # selectively show/hide 12 pre-built panels at once - simpler, and
        # matches the "only show what's actually relevant right now" goal
        # directly instead of hiding the other 11 behind the scenes.
        # _show_detect_result switches the notebook to this tab
        # automatically once a tool is identified, so the user doesn't
        # have to go hunting for it after pressing Detect. ---
        self.tool_panel_inner = ttk.Frame(self.tool_tab)
        self.tool_panel_inner.pack(fill="both", expand=True)
        ttk.Label(
            self.tool_panel_inner,
            text=_("LBL_CONNECT_AND_DETECT_PROMPT"),
            foreground="gray", wraplength=380, justify="left",
        ).pack(padx=8, pady=8, anchor="w")

        self.progress = ttk.Progressbar(root, orient="horizontal", mode="determinate", maximum=100)
        self.progress.grid(row=2, column=0, sticky="ew", padx=8, pady=(4, 8))

        log_frame = ttk.LabelFrame(root, text=_("TITLE_LOG"))
        log_frame.grid(row=3, column=0, sticky="nsew", **pad)
        log_toolbar = ttk.Frame(log_frame)
        log_toolbar.pack(fill="x", side="top")
        ttk.Button(log_toolbar, text=_("BTN_EXPORT_DEBUG_BUNDLE"), command=self.export_debug_bundle).pack(
            side="left", padx=4, pady=2
        )
        self.log_text = tk.Text(log_frame, height=5, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, side="left")
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)

        self.refresh_ports()
        self.log(_("LOG_TESTER_READY", hw_id=THIS_HARDWARE_ID))
        if self.transport_var.get() == "serial":
            self.log(_("LOG_EXPECTING_SLCAN_MODE"))
        else:
            self.log(_("LOG_EXPECTING_SOCKETCAN_MODE"))
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def log(self, msg):
        if self._file_logger:
            try:
                self._file_logger.info(msg)
            except OSError:
                pass
        def _append():
            self.log_text.config(state="normal")
            self.log_text.insert("end", msg + "\n")
            # Bounded the same way the Raw Bus Monitor's own row count
            # already is (tester_common_panels.py's _open_bus_monitor) - an
            # hours-long session otherwise grows this Text widget's line
            # count, and Tk's own internal representation of it, without
            # limit. The full session is still on disk regardless (every
            # message reaching this point was already written to
            # self._file_logger above before this widget ever sees it), so
            # trimming what's kept on-screen loses nothing permanently.
            # Counted via the widget's own line index rather than a
            # separately tracked counter - "end-1c linestart" is one past
            # the last real line (plain "end" always has one further,
            # empty trailing line Tk keeps), so this always reflects the
            # widget's own true line count without a hand-maintained total
            # that could drift out of sync with it. One delete() call
            # covering however many lines are over the cap, not one call
            # per line - same reasoning as the Bus Monitor's own single
            # delete(*to_remove) over a batch of rows.
            line_count = int(self.log_text.index("end-1c").split(".")[0])
            if line_count > 500:
                self.log_text.delete("1.0", f"{line_count - 500 + 1}.0")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.root.after(0, _append)

    def on_transport_change(self):
        self.port_label.config(text=_("LBL_COM_PORT") if self.transport_var.get() == "serial" else _("LBL_CAN_INTERFACE"))
        self.port_var.set("")
        is_serial = self.transport_var.get() == "serial"
        self.bitrate_combo.config(state="readonly" if is_serial else "disabled")
        self.autobaud_btn.config(state="normal" if is_serial else "disabled")
        self.bitrate_status.config(text="" if is_serial else _("HELP_SOCKETCAN_BITRATE_OS_LEVEL"))
        self.refresh_ports()

    def _on_language_change(self, chosen):
        if save_config({"language": chosen}):
            messagebox.showinfo(_("TITLE_RESTART_NEEDED"), _("MSG_RESTART_NEEDED"))
        else:
            messagebox.showerror(_("TITLE_COULDNT_SAVE"), _("MSG_LANGUAGE_NOT_SAVED", path=CONFIG_PATH))

    def refresh_ports(self):
        # list_serial_ports()/list_socketcan_interfaces() below can block
        # for a noticeable moment - pyserial's own port enumeration goes
        # through Windows WMI/registry queries (COMx friendly-name lookups)
        # under the hood, which have been observed to take a couple hundred
        # ms on a system with several USB-serial devices having been
        # enumerated before. Run synchronously on the Tkinter main thread,
        # that would freeze the entire window (no repaint, no other button
        # responds) for however long the query takes - run in a background
        # worker instead, same pattern already used by
        # _auto_detect_worker/_detect_active_tool_worker below, so a port
        # refresh (including the one this class's own __init__ triggers on
        # startup, and the one on_transport_change triggers on every
        # transport switch) never blocks the UI.
        self.refresh_btn.config(state="disabled")
        self.port_combo.config(state="disabled")
        transport_mode = self.transport_var.get()
        threading.Thread(target=self._refresh_ports_worker, args=(transport_mode,), daemon=True).start()

    def _refresh_ports_worker(self, transport_mode):
        ports = list_serial_ports() if transport_mode == "serial" else list_socketcan_interfaces()
        self.root.after(0, lambda: self._refresh_ports_done(ports))

    def _refresh_ports_done(self, ports):
        if not self.root.winfo_exists():
            return  # window closed while this background worker was still running
        self.refresh_btn.config(state="normal")
        self.port_combo.config(state="readonly")
        self.port_combo["values"] = ports
        if ports and not self.port_var.get():
            self.port_var.set(ports[0])

    def toggle_connect(self):
        if self.transport is None:
            port = self.port_var.get()
            if not port:
                messagebox.showerror(_("TITLE_NOTHING_SELECTED"), _("MSG_SELECT_PORT_FIRST"))
                return
            is_serial = self.transport_var.get() == "serial"
            listen_only = self.listen_only_var.get()
            try:
                if is_serial:
                    bitrate_label = self.bitrate_var.get()
                    bitrate_code = next((code for label, code in SLCAN_BITRATES if label == bitrate_label),
                                         BITRATE_500K_SLCAN_CODE)
                    self.transport = SLCAN(port, log=self.log)
                    self.transport.open_channel(bitrate_code, listen_only=listen_only)
                else:
                    self.transport = SocketCAN(port, log=self.log)
                    self.transport.open_channel(listen_only=listen_only)
                self.bus = CANBusMonitor(self.transport, self.log, listen_only=listen_only)
                self.bus.start()
                status_text = _("STATUS_CONNECTED_PORT", port=port)
                if listen_only:
                    status_text += _("LBL_LISTEN_ONLY_SUFFIX")
                self.conn_status.config(text=status_text, foreground="green")
                self.connect_btn.config(text=_("BTN_DISCONNECT"))
                self.refresh_btn.config(state="disabled")
                self.listen_only_check.config(state="disabled")
                self.log(_("LOG_CONNECTED_TO_PORT", port=port)
                          + (_("LOG_AT_BITRATE_SUFFIX", bitrate=self.bitrate_var.get()) if is_serial else "."))
                if listen_only:
                    # Detect needs to send 0x110/0x7F8 to get anything back
                    # at all - CANBusMonitor.send() would just quietly
                    # no-op every one of those (see its own guard), so
                    # running it automatically here would only produce a
                    # guaranteed, misleading "no response" a few seconds
                    # into every listen-only connection. Skipped outright
                    # instead, with a status message that explains why
                    # rather than leaving the label sitting on "connect to
                    # detect" with no indication anything's different.
                    self.log(_("LOG_LISTEN_ONLY_ACTIVE"))
                    self.active_tool_label.config(text=_("STATUS_LISTEN_ONLY_NO_DETECT"), foreground="gray")
                    self._reset_id_pin_display()
                else:
                    self.detect_active_tool()
                self._start_bus_health_monitor()
            except Exception as e:
                self.transport = None
                msg = str(e)
                if is_serial and ("Permission denied" in msg or "Errno 13" in msg):
                    messagebox.showerror(
                        _("TITLE_CONNECTION_FAILED_PERMISSION"),
                        _("MSG_PERMISSION_DENIED_HELP", msg=msg),
                    )
                else:
                    messagebox.showerror(_("TITLE_CONNECTION_FAILED"), msg)
        else:
            self._stop_bus_health_monitor()
            self._clear_tool_panel()
            if self.bus is not None:
                self.bus.stop()
                self.bus = None
            try:
                self.transport.close()
            except Exception:
                pass
            self.transport = None
            self.active_tool_id = None
            self.conn_status.config(text=_("STATUS_NOT_CONNECTED"), foreground="red")
            self.connect_btn.config(text=_("BTN_CONNECT"))
            self.active_tool_label.config(text=_("STATUS_CONNECT_TO_DETECT"), foreground="gray")
            self.board_state_label.config(text=_("STATUS_CONNECT_TO_CHECK"), foreground="gray")
            self._reset_id_pin_display()
            self.refresh_btn.config(state="normal")
            self.listen_only_check.config(state="normal")
            self.log(_("LOG_DISCONNECTED"))

    def auto_detect_bitrate(self):
        if not HAVE_SERIAL:
            messagebox.showerror(_("TITLE_PYSERIAL_NOT_INSTALLED"), _("MSG_PYSERIAL_NEEDED_AUTODETECT"))
            return
        if self.transport is not None:
            messagebox.showerror(_("TITLE_ALREADY_CONNECTED"), _("MSG_DISCONNECT_FIRST_AUTODETECT"))
            return
        port = self.port_var.get()
        if not port:
            messagebox.showerror(_("TITLE_NOTHING_SELECTED"), _("MSG_SELECT_COM_PORT_FIRST"))
            return
        self.bitrate_status.config(text=_("STATUS_TRYING_EACH_BITRATE"), foreground="gray")
        self.connect_btn.config(state="disabled")
        self.port_combo.config(state="disabled")
        self.autobaud_btn.config(state="disabled")
        threading.Thread(target=self._auto_detect_worker, args=(port,), daemon=True).start()

    def _auto_detect_worker(self, port):
        found_label = None
        try:
            try_order = ["500 kbit/s", "250 kbit/s", "125 kbit/s", "1 Mbit/s",
                         "100 kbit/s", "50 kbit/s", "20 kbit/s", "10 kbit/s", "800 kbit/s"]
            for label in try_order:
                code = next(c for l, c in SLCAN_BITRATES if l == label)
                self.log(_("LOG_AUTODETECT_TRYING", label=label))
                trial = None
                try:
                    trial = SLCAN(port, log=lambda m: None)
                    trial.open_channel(code)
                    # Passive listen window before this transmits anything
                    # of its own - a probe frame sent in blind is aimed at
                    # a bus this tool has no actual knowledge is idle. If
                    # some other device is already talking at THIS
                    # candidate bitrate, that traffic is real and this
                    # tool's own probe would be landing in the middle of
                    # it purely by luck of the timing; if some other
                    # device is talking at a DIFFERENT bitrate than the one
                    # currently being tried, every byte of it decodes as
                    # noise on this one, and this tool has no way to tell
                    # those two cases apart without listening first. A
                    # short silent window here (~120ms, small next to the
                    # 0.8s already budgeted per candidate below - 9
                    # candidates x 120ms adds a little over 1s total to
                    # the whole scan) means every transmission this tool
                    # ever makes during auto-detect is at least preceded by
                    # a real look at what's already on the wire, rather
                    # than firing blind the instant the channel opens.
                    passive_deadline = time.time() + 0.12
                    passive_frames_seen = 0
                    while time.time() < passive_deadline:
                        if trial.read_frame(timeout=0.05) is not None:
                            passive_frames_seen += 1
                    if passive_frames_seen:
                        self.log(_("LOG_AUTODETECT_TRAFFIC_SEEN", label=label, n=passive_frames_seen))
                    trial.send_frame(CAN_ID_QUERY_ACTIVE_TOOL, b"")
                    deadline = time.time() + 0.8
                    while time.time() < deadline:
                        frame = trial.read_frame(timeout=0.2)
                        if frame is not None and frame[0] == CAN_ID_ACTIVE_TOOL_RESP:
                            found_label = label
                            break
                    if found_label:
                        break
                except (SLCANError, OSError):
                    pass
                finally:
                    if trial is not None:
                        try:
                            trial.close()
                        except Exception:
                            pass
                    if not found_label:
                        time.sleep(0.1)  # lets Windows serial drivers
                        # (FTDI/CH340) actually release the port before the
                        # next iteration's open attempt - reopening too
                        # quickly can otherwise fail with PermissionError,
                        # silently skipping a bitrate that might have been
                        # the correct one
        finally:
            self.root.after(0, lambda: self._auto_detect_done(found_label))

    def _auto_detect_done(self, found_label):
        if not self.root.winfo_exists():
            return  # window closed while the background worker was still running
        self.connect_btn.config(state="normal")
        self.port_combo.config(state="readonly")
        self.autobaud_btn.config(state="normal")
        if found_label:
            self.bitrate_var.set(found_label)
            self.bitrate_status.config(text=_("STATUS_AUTODETECT_FOUND", label=found_label), foreground="green")
            self.log(_("LOG_AUTODETECT_RESPONDED", label=found_label))
        else:
            self.bitrate_status.config(text=_("STATUS_NO_RESPONSE_ANY_BITRATE"), foreground="red")
            self.log(_("LOG_AUTODETECT_NO_RESPONSE"))

    # First attempt plus this many automatic retries before Detect actually
    # gives up and shows "no response" to the user - see
    # _detect_active_tool_worker's own comment for the reasoning.
    _DETECT_MAX_ATTEMPTS = 3

    def detect_active_tool(self):
        if self.transport is None or self.bus is None:
            messagebox.showerror(_("TITLE_NOT_CONNECTED"), _("MSG_CONNECT_FIRST"))
            return
        self.detect_btn.config(state="disabled")
        self.active_tool_label.config(text=_("STATUS_DETECTING"), foreground="gray")
        self.board_state_label.config(text=_("STATUS_DETECTING"), foreground="gray")
        self.progress["value"] = 0
        threading.Thread(target=self._detect_active_tool_worker, args=(1,), daemon=True).start()

    def _detect_active_tool_worker(self, attempt):
        bus = self.bus  # local reference - self.bus can be reassigned to
        # None by toggle_connect() running on the main thread while this
        # worker is still blocked inside wait_for_one below; using this
        # local copy for the rest of the function means that reassignment
        # can't turn a subsequent bus.send/wait_for_one call here into an
        # AttributeError on a None.
        if bus is None:
            self.root.after(0, lambda: self.detect_btn.config(state="normal"))
            return
        # try/finally around the actual querying: if the transport closes
        # out from under this worker mid-query (the local bus reference
        # above only protects against self.bus becoming None, not against
        # the underlying connection this same object wraps being torn
        # down), bus.send()/wait_for_one() can raise - without this, that
        # would kill the thread before detect_btn's re-enable at the
        # bottom ever ran, leaving it stuck disabled. Same pattern already
        # used successfully in _auto_detect_worker.
        try:
            self.log(_("LOG_QUERYING_ACTIVE_TOOL") if attempt == 1 else
                      _("LOG_QUERYING_ACTIVE_TOOL_RETRY", attempt=attempt, max=self._DETECT_MAX_ATTEMPTS))
            self.root.after(0, lambda: self.progress.configure(value=35))
            tool_data = bus.wait_for_one(CAN_ID_ACTIVE_TOOL_RESP, timeout=1.5,
                                          send_after_register=lambda: bus.send(CAN_ID_QUERY_ACTIVE_TOOL, b""))

            self.log(_("LOG_QUERYING_VERSION"))
            self.root.after(0, lambda: self.progress.configure(value=70))
            version_data = bus.wait_for_one(CAN_ID_VERSION_RESPONSE, timeout=1.5,
                                              send_after_register=lambda: bus.send(CAN_ID_QUERY_VERSION, b"\x00"))
            self.root.after(0, lambda: self.progress.configure(value=100))
        except Exception as e:
            self.log(_("LOG_DETECT_FAILED", e=e))
            self.root.after(0, lambda: self.detect_btn.config(state="normal"))
            return

        if self.bus is not bus:
            # Disconnected (or disconnected and reconnected to something
            # new) while this was waiting - this result is stale, and the
            # widgets it would update may now belong to a different
            # connection, or no connection at all. Silently dropped rather
            # than risk showing a detection result for a board that isn't
            # even the one currently connected.
            self.root.after(0, lambda: self.detect_btn.config(state="normal"))
            return

        # Auto-retry on a total no-response, same "try again a couple more
        # times before bothering the user" reasoning as _auto_detect_worker's
        # own per-bitrate loop above - a single missed 0x111/0x7F9 reply is
        # common enough (a board that's mid-boot right when Detect was
        # pressed, one dropped frame on a noisy bus) to be worth another
        # automatic look before showing "check your wiring". Recurses on
        # this same background thread rather than spawning a new one each
        # time - it's already off the Tkinter main thread, so there's
        # nothing to gain from a fresh thread per attempt, only more
        # bookkeeping. Only retries on a COMPLETE non-response (both
        # queries got nothing back) - a real, if incomplete, answer (e.g.
        # the tool query worked but the version query didn't) is shown to
        # the user as-is rather than silently re-queried, since retrying
        # would risk masking a genuinely flaky version-query path behind an
        # eventual lucky success.
        if tool_data is None and version_data is None and attempt < self._DETECT_MAX_ATTEMPTS:
            self.log(_("LOG_DETECT_NO_RESPONSE_RETRYING", attempt=attempt, max=self._DETECT_MAX_ATTEMPTS))
            time.sleep(0.3)
            if self.bus is not bus:
                self.root.after(0, lambda: self.detect_btn.config(state="normal"))
                return
            self._detect_active_tool_worker(attempt + 1)
            return

        self.root.after(0, lambda: self.detect_btn.config(state="normal"))
        self.root.after(0, lambda: self._show_detect_result(tool_data, version_data))

    def _update_id_pin_display(self, tool_id):
        # bit0=ID0 .. bit4=ID4, matching ECOVIA.TXT's table and
        # Identify_PhysicalTool()'s own bit-building order in
        # firmware_identify.c exactly - the squares are drawn
        # ID4..ID0 (left to right, matching the documented MSB-to-LSB
        # convention), so index 0 in self._id_pin_squares is ID4, needing
        # bit 4, down to index 4 being ID0, needing bit 0.
        for i, square in enumerate(self._id_pin_squares):
            bit_index = 4 - i
            bit_value = (tool_id >> bit_index) & 1
            if bit_value:
                square.config(text="1", bg="#2E7D32", fg="white")  # jumper installed
            else:
                square.config(text="0", bg="#EEEEEE", fg="#666666")  # no jumper
        self.tool_number_label.config(text=str(tool_id))

    def _reset_id_pin_display(self):
        """Reverts the ID4..ID0 squares and tool-number label to their
        pre-detect "?" placeholder state - called on disconnect and when
        connecting in Listen Only (which deliberately skips Detect - see
        toggle_connect). Without this, the squares and tool number kept
        showing whichever board was detected LAST until a fresh detection
        overwrote them, which after a disconnect (or a Listen Only
        connection to a completely different physical board) is stale
        information from a board that is no longer even connected, with
        nothing in the UI indicating it's now stale rather than current."""
        for square in self._id_pin_squares:
            square.config(text="?", bg="#DDDDDD", fg="#666666")
        self.tool_number_label.config(text="--")

    def _format_board_state(self, err, can_err, booting):
        """Turns the 3 status bits carried in every CAN_ID_ACTIVE_TOOL_RESP
        (0x111) reply into the same translated summary text/severity used
        both right after a Detect (_show_detect_result below) and by the
        periodic in-session bus health check (_bus_health_worker) - one
        shared place for this rather than 2 copies that could drift apart
        on wording or on what counts as "bad"."""
        state_bits = []
        if err:
            state_bits.append(_("STATE_CRITICAL_ERROR"))
        if can_err:
            state_bits.append(_("STATE_CAN_BUS_ERROR"))
        if booting:
            state_bits.append(_("STATE_BOOT_SPLASH"))
        state_text = ", ".join(state_bits) if state_bits else _("STATE_NORMAL")
        return state_text, bool(err or can_err)

    def _show_detect_result(self, tool_data, version_data):
        if tool_data is None and version_data is None:
            self.active_tool_label.config(text=_("STATUS_NO_RESPONSE_CHECK_WIRING"), foreground="red")
            self.board_state_label.config(text=_("STATUS_NO_RESPONSE_SHORT"), foreground="red")
            self.log(_("LOG_DETECTION_FAILED"))
            return

        if tool_data is not None and len(tool_data) >= 4:
            tool_id = tool_data[0]
            err = tool_data[1]
            can_err = tool_data[2]
            booting = tool_data[3]
            name = TOOL_NAMES.get(tool_id, f"none assigned (raw ID {tool_id})")
            self.active_tool_label.config(text=f"{name} (ID {tool_id})",
                                           foreground="green" if tool_id in TOOL_NAMES else "orange")
            self._update_id_pin_display(tool_id)
            state_text, is_bad = self._format_board_state(err, can_err, booting)
            self.board_state_label.config(text=state_text, foreground="red" if is_bad else "green")
            self.log(_("LOG_ACTIVE_TOOL_STATE", name=name, tool_id=tool_id, state=state_text))
            self.active_tool_id = tool_id
            self.rebuild_tool_panel(tool_id)
            self._notebook.select(self.tool_tab)
        else:
            self.active_tool_label.config(text=_("STATUS_NO_RESPONSE_0X110"),
                                           foreground="orange")
            self.log(_("LOG_NO_RESPONSE_0X110_HELP"))

        if version_data is not None and len(version_data) >= 8:
            role = "bootloader" if version_data[0] == 0x01 else "application"
            hw_id = struct.unpack(">I", version_data[1:5])[0]
            ver_major = struct.unpack(">H", version_data[5:7])[0]
            ver_minor = version_data[7]
            hw_note = "" if hw_id == THIS_HARDWARE_ID else f" (expected 0x{THIS_HARDWARE_ID:08X} - different board/rig?)"
            self.log(_("LOG_VERSION_INFO", role=role, hw_id=hw_id, hw_note=hw_note, major=ver_major, minor=ver_minor))

    # Polling interval for the in-session bus health check below - a
    # deliberately gentle 3s, not tied to any of the firmware's own
    # 150-1000ms comms watchdogs. This isn't standing in for those (a tool
    # panel's own keepalive already handles "did MY command get through
    # recently"); it exists purely to notice "did the BUS ITSELF go bad"
    # sometime after Detect - _show_detect_result's own check only runs
    # once, at connect/Detect time, so without this loop a bus that goes
    # bad partway through a session would go unnoticed until the next
    # manual Detect or self-test - see this method's own docstring below
    # for the known limitation on exactly what "bad" can mean here.
    _BUS_HEALTH_INTERVAL_S = 3.0

    def _start_bus_health_monitor(self):
        self._bus_health_running = True
        self._bus_health_was_bad = False
        threading.Thread(target=self._bus_health_worker, args=(self.bus,), daemon=True).start()

    def _stop_bus_health_monitor(self):
        self._bus_health_running = False

    def _bus_health_worker(self, bus):
        """Background loop, started alongside every connection (see
        toggle_connect) and stopped on disconnect, that periodically re-
        checks bus health for as long as a session stays connected.
        _show_detect_result's own look at the CAN_ID_ACTIVE_TOOL_RESP
        (0x111) error bits only ever runs once, at connect/Detect time -
        this loop is what catches a bus that goes bad sometime AFTER that
        (a marginal termination resistor working loose, another device on
        the bus starting to misbehave mid-session, ...), which would
        otherwise go completely unnoticed until the next manual Detect or
        self-test.

        KNOWN LIMITATION: this firmware's own 0x111 reply only ever
        exposes one generic "a CAN bus error was seen" boolean (byte 2,
        the same can_err bit _format_board_state already turns into
        STATE_CAN_BUS_ERROR) - there's no separate bit for Error-Passive
        vs. Bus-Off vs. anything else on that wire protocol, so this can't
        actually distinguish those from each other, only report "the board
        itself is currently flagging a bus problem". SocketCAN.check_carrier
        (tester_transports.py) adds one more, independent signal
        specifically for Bus-Off on that transport only (the kernel drops
        carrier on bus-off - see that method's own comment) - not
        available for SLCAN at all, since a Lawicel adapter's own serial
        link to the USB host stays up regardless of what's happening on the
        CAN side of it. Getting genuine REC/TEC error-counter-level detail
        would need either a firmware protocol change (a new response
        field) or, for SocketCAN specifically, a netlink query this project
        deliberately doesn't take a dependency for (see
        SocketCAN.read_interface_stats's own comment on that same
        tradeoff) - both are real, if incomplete, signals worth surfacing
        with what's already available today, rather than leaving this
        entirely unmonitored between manual Detects until one of those
        larger changes happens.
        """
        while self._bus_health_running and self.bus is bus:
            time.sleep(self._BUS_HEALTH_INTERVAL_S)
            if not self._bus_health_running or self.bus is not bus:
                break
            if bus.listen_only:
                continue  # would never get a response by design - see the Listen Only note in toggle_connect
            try:
                tool_data = bus.wait_for_one(CAN_ID_ACTIVE_TOOL_RESP, timeout=1.0,
                                              send_after_register=lambda: bus.send(CAN_ID_QUERY_ACTIVE_TOOL, b""))
            except Exception as e:
                # bus.send() inside send_after_register raises on a real
                # transport failure (e.g. the adapter physically unplugged
                # mid-session) - letting that propagate out of this loop
                # would silently kill this whole background thread for the
                # rest of the session (an uncaught exception in a Python
                # thread just ends it, with nothing surfaced to the user),
                # which is exactly the kind of swallowed communication
                # failure this monitor exists to catch, not become an
                # instance of. CANBusMonitor's own read loop already logs
                # the same underlying failure repeatedly on its own
                # (LOG_BUS_READ_ERROR); this logs it once more here, then
                # retries on the next poll instead of giving up for good.
                self.log(_("LOG_BUS_HEALTH_POLL_FAILED", e=e))
                continue
            if self.bus is not bus:
                break  # disconnected (or reconnected to something new) while this was waiting

            is_bad = tool_data is not None and len(tool_data) >= 3 and bool(tool_data[2])
            reason = _("STATE_CAN_BUS_ERROR") if is_bad else None

            transport = self.transport  # local snapshot - same "main thread
            # can reassign this out from under a background worker" concern
            # as the bus local reference above, just for self.transport
            # instead of self.bus.
            if isinstance(transport, SocketCAN):
                carrier = SocketCAN.check_carrier(transport.interface)
                if carrier is False:
                    is_bad = True
                    reason = _("MSG_NO_CARRIER_SESSION", interface=transport.interface)

            if is_bad and not self._bus_health_was_bad:
                self._bus_health_was_bad = True
                self.root.after(0, lambda r=reason: self._on_bus_health_bad(r))
            elif not is_bad and self._bus_health_was_bad:
                self._bus_health_was_bad = False
                self.root.after(0, self._on_bus_health_recovered)

    def _on_bus_health_bad(self, reason):
        if self.bus is None:
            return  # disconnected between the worker's root.after() and this actually running
        self.board_state_label.config(text=reason, foreground="red")
        self.log(_("LOG_BUS_HEALTH_WARNING", reason=reason))
        messagebox.showwarning(_("TITLE_BUS_HEALTH_WARNING"), _("MSG_BUS_HEALTH_WARNING", reason=reason))

    def _on_bus_health_recovered(self):
        if self.bus is None:
            return
        self.log(_("LOG_BUS_HEALTH_RECOVERED"))

    def _send_tool_off_command(self):
        """Sends an explicit, immediate safe/off command for whichever
        tool's panel is currently showing, if any - called before tearing
        down its keepalive timers. The firmware's own communication
        watchdog (250ms for the soldering iron/laser/3D nozzle, 1000ms for
        the layer fan) would shut the same actuator off on its own once
        this tool stops resending anyway, so this isn't covering a real
        safety gap - it just means the actuator stops within one CAN frame
        of switching away, instead of coasting for however long that
        watchdog takes to notice the silence."""
        if self.bus is None or self._current_tool_id is None:
            return
        def _send_3dp_off():
            # Each send attempted independently, not as a single
            # short-circuiting expression - a failure sending to one fan
            # must not prevent the others from getting their own
            # off-command.
            for cmd_id, data in (
                (CAN_ID_3DP_THERMAL_MOTION, struct.pack(">H", 0) + bytes([0, 0, 0, 0])),
                (CAN_ID_3DP_LAYER_FAN_CMD, bytes([0])),
                (CAN_ID_3DP_HOTEND_FAN_CMD, bytes([0])),
            ):
                try:
                    self.bus.send(cmd_id, data)
                except Exception as e:
                    self.log(_("LOG_OFF_COMMAND_FAILED_ID", cmd_id=cmd_id, tool_id=self._current_tool_id, e=e))

        off_commands = {
            0: lambda: self.bus.send(CAN_ID_SOLDER_SETPOINT, struct.pack(">H", 0)),
            5: lambda: self.bus.send(CAN_ID_DRILL_CMD, bytes([0, 0])),
            9: lambda: self.bus.send(CAN_ID_LASER_CMD, bytes([0, 0])),
            10: _send_3dp_off,
            18: lambda: self.bus.send(CAN_ID_UV_CURING_CMD, bytes([0])),
            19: lambda: self.bus.send(CAN_ID_HOTAIR_CMD, struct.pack(">H", 0) + bytes([0])),
        }.get(self._current_tool_id)
        if off_commands is not None:
            try:
                off_commands()
            except Exception as e:
                self.log(_("LOG_OFF_COMMAND_FAILED", tool_id=self._current_tool_id, e=e))

    # Keepalive job names NOT tied to whichever tool panel is currently
    # showing - every keepalive (tool-panel ones and this one alike)
    # shares the same self._keepalive_jobs dict via PanelHelpersMixin's
    # _start_keepalive/_stop_keepalive, so blindly cancelling every entry
    # below would also kill these. "custom_frame" is the periodic sender
    # in the always-present Custom Frame tab (see
    # CommonPanelsMixin._build_custom_frame_panel) - completely
    # independent of which tool is currently detected. Without this
    # exclusion, clicking Detect (or anything else that rebuilds the tool
    # panel) while a custom periodic frame is running would silently
    # cancel it out from under its own "Repeat Every" checkbox, which
    # stays checked with nothing left actually being sent - misleading
    # during a session where that custom frame could be pointed at
    # anything, including a hazardous CAN ID.
    _GLOBAL_KEEPALIVE_NAMES = {"custom_frame"}

    def _clear_tool_panel(self):
        self._send_tool_off_command()
        if self.bus is not None:
            self.bus.clear_all()  # drops every per-tool telemetry handler, not the connection itself
        self._tool_panel_generation += 1  # see __init__'s own comment - signals any
        # still-running background worker from the panel about to be torn
        # down (e.g. a thermal-image read mid-flight) to stop on its next
        # check, before the widgets it might still try to touch below are
        # actually destroyed.
        for child in self.tool_panel_inner.winfo_children():
            child.destroy()
        for name, job_id in list(self._keepalive_jobs.items()):
            if name in self._GLOBAL_KEEPALIVE_NAMES:
                continue
            try:
                self.root.after_cancel(job_id)
            except Exception:
                pass
            del self._keepalive_jobs[name]

    def rebuild_tool_panel(self, tool_id):
        self._clear_tool_panel()
        self._current_tool_id = tool_id
        name = TOOL_NAMES.get(tool_id, "No tool assigned")
        self._notebook.tab(self.tool_tab, text=f"Tool Controls - {name}")
        builder = {
            0: lambda p: self._build_soldering_iron_panel(p, tool_id, name),
            1: self._build_motion_panel, 2: self._build_motion_panel,
            3: self._build_motion_panel, 6: self._build_motion_panel,
            7: self._build_motion_panel,
            4: self._build_vacuum_panel,
            5: self._build_drill_panel,
            8: self._build_aoi_panel,
            9: self._build_laser_panel,
            10: self._build_3dprinter_panel,
            11: self._build_scan_probe_panel,
            12: self._build_motion_panel,
            13: self._build_electromagnet_panel,
            14: self._build_spot_welder_panel,
            15: lambda p: self._build_no_handler_panel(p, "HELP_NO_HANDLER_CONFORMAL_COATING"),
            16: self._build_motion_panel,
            17: self._build_flying_probe_panel,
            18: self._build_uv_curing_panel,
            19: self._build_hotair_rework_panel,
            20: lambda p: self._build_no_handler_panel(p, "HELP_NO_HANDLER_PRESSFIT_INSERTER"),
            21: lambda p: self._build_crimping_actuator_panel(p, tool_id, name),
            22: self._build_thermal_inspection_panel,
            23: self._build_paste_jetting_panel,
            24: self._build_ultrasonic_welder_panel,
        }.get(tool_id)
        if builder is None:
            ttk.Label(
                self.tool_panel_inner,
                text=f"No tool is assigned to this jumper setting (raw ID {tool_id}). "
                     f"Nothing to test here - set the board's ID jumpers to a real tool profile.",
                foreground="gray", wraplength=380, justify="left",
            ).pack(padx=8, pady=8, anchor="w")
            return
        if tool_id in MOTION_TOOL_IDS:
            builder(self.tool_panel_inner, tool_id, name)
        else:
            builder(self.tool_panel_inner)


    def export_debug_bundle(self):
        save_path = filedialog.asksaveasfilename(
            title=_("TITLE_SAVE_DEBUG_BUNDLE"),
            defaultextension=".zip",
            initialfile=f"urtc_tester_debug_{time.strftime('%Y%m%d_%H%M%S')}.zip",
            filetypes=[(_("LBL_ZIP_FILES"), "*.zip")],
        )
        if not save_path:
            return
        try:
            with zipfile.ZipFile(save_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("session_log.txt", self.log_text.get("1.0", "end"))
                diag = [
                    f"URTC Tester version: {TESTER_VERSION}",
                    f"Python: {sys.version}",
                    f"Platform: {platform.platform()}",
                    f"pyserial available: {HAVE_SERIAL}",
                    f"SocketCAN available: {HAVE_SOCKETCAN}",
                    f"Current transport: {self.transport_var.get()}",
                    f"Current port/interface: {self.port_var.get()}",
                    f"Current bitrate (Serial/SLCAN): {self.bitrate_var.get()}",
                    f"Connected: {self.transport is not None}",
                    f"Active tool ID: {self.active_tool_id}",
                ]
                zf.writestr("system_diagnostics.txt", "\n".join(diag))
            messagebox.showinfo(_("TITLE_DEBUG_BUNDLE_SAVED"), _("MSG_SAVED_TO", path=save_path))
            self.log(_("LOG_DEBUG_BUNDLE_EXPORTED", path=save_path))
        except OSError as e:
            messagebox.showerror(_("TITLE_EXPORT_FAILED"), str(e))

    def _build_menu_bar(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label=_("MENU_SAVE_LOGS"), command=self._menu_save_logs)
        file_menu.add_separator()
        file_menu.add_command(label=_("MENU_EXIT"), command=self.on_close)
        menubar.add_cascade(label=_("MENU_FILE"), menu=file_menu)

        # Radiobutton-style menu items so the current language shows a
        # checkmark - purely cosmetic (each one calls _on_language_change
        # with its own fixed code regardless of this variable's value),
        # but confirms at a glance which one is actually active without
        # opening a submenu of plain, unmarked entries.
        language_menu = tk.Menu(menubar, tearoff=False)
        import tester_config
        self._menu_lang_var = tk.StringVar(value=tester_config._current_language)
        for code, display in AVAILABLE_LANGUAGES:
            language_menu.add_radiobutton(
                label=display, value=code, variable=self._menu_lang_var,
                command=lambda c=code: self._on_language_change(c),
            )
        menubar.add_cascade(label=_("MENU_LANGUAGE"), menu=language_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label=_("MENU_README"), command=self._menu_show_readme)
        help_menu.add_command(label=_("MENU_GITHUB"), command=self._menu_show_github)
        help_menu.add_separator()
        help_menu.add_command(label=_("MENU_LICENSE"), command=self._menu_show_license)
        help_menu.add_command(label=_("MENU_ABOUT"), command=self._menu_show_about)
        menubar.add_cascade(label=_("MENU_HELP"), menu=help_menu)

    def _menu_save_logs(self):
        """Saves just the on-screen log as plain text - the lighter-weight
        counterpart to export_debug_bundle's full zip (log + diagnostics),
        for when only the log itself is actually needed."""
        save_path = filedialog.asksaveasfilename(
            title=_("MENU_SAVE_LOGS"),
            defaultextension=".txt",
            initialfile=f"urtc_tester_log_{time.strftime('%Y%m%d_%H%M%S')}.txt",
            filetypes=[(_("LBL_TEXT_FILES"), "*.txt")],
        )
        if not save_path:
            return
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(self.log_text.get("1.0", "end"))
            self.log(_("LOG_LOGS_SAVED", path=save_path))
        except OSError as e:
            messagebox.showerror(_("TITLE_EXPORT_FAILED"), str(e))

    def _menu_show_github(self):
        import webbrowser
        # This tool's own dedicated repository - not the URTC monorepo
        # (github.com/JuanenRac/URTC), which holds the firmware and
        # documentation this tool talks to but not this tool's own source.
        webbrowser.open("https://github.com/JuanenRac/URTC-TESTER")

    def _show_text_window(self, title, text, width=90, height=30):
        """Shared plain-text viewer window - used by both the Readme and
        License menu entries. Read-only Text widget with a scrollbar,
        rather than trying to render Markdown (no renderer is bundled, and
        adding one just for this would be a lot of weight for a "view the
        file" feature). Centered here, once, so every caller gets it for
        free rather than each one needing its own centering call."""
        win = tk.Toplevel(self.root)
        win.title(title)
        win.transient(self.root)
        frame = ttk.Frame(win, padding=8)
        frame.pack(fill="both", expand=True)
        text_widget = tk.Text(frame, wrap="word", width=width, height=height)
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame, command=text_widget.yview)
        scrollbar.pack(side="right", fill="y")
        text_widget.config(yscrollcommand=scrollbar.set)
        text_widget.insert("1.0", text)
        text_widget.config(state="disabled")
        win.update_idletasks()
        win.geometry(_center_geometry(win, win.winfo_reqwidth(), win.winfo_reqheight()))
        return win

    def _menu_show_readme(self):
        # Language-specific filename first (readme_spa.md etc.), falling
        # back to the English readme.md if that translation doesn't exist
        # yet - matches the Flasher's identical Readme menu behavior.
        import tester_config
        lang_suffix = {"spanish": "_spa", "italian": "_ita", "french": "_fra", "german": "_deu"}.get(
            tester_config._current_language, ""
        )
        # tester_config.base_dir, not a fresh __file__-based calculation -
        # see that module's own comment on why: __file__ resolves into
        # PyInstaller's temporary extraction folder when this is running
        # as a frozen .exe, not to wherever the .exe actually sits on disk.
        candidate = os.path.join(tester_config.base_dir, f"README{lang_suffix}.md")
        readme_path = candidate if os.path.isfile(candidate) else os.path.join(tester_config.base_dir, "README.md")
        try:
            with open(readme_path, encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            messagebox.showerror(_("TITLE_EXPORT_FAILED"), str(e))
            return
        self._show_text_window(_("MENU_README"), content)

    def _menu_show_license(self):
        # Looks next to the executable/script (build_exe.bat/.sh both copy
        # LICENSE there - see those scripts), not via a "../../../" relative
        # path up to the repository root - that only ever resolved
        # correctly when running from within the source tree, never for a
        # standalone distributed exe with no repository around it at all.
        import tester_config
        try:
            license_path = os.path.join(tester_config.base_dir, "LICENSE")
            with open(license_path, encoding="utf-8") as f:
                content = f.read()
        except OSError:
            content = _("MSG_LICENSE_FALLBACK")
        win = self._show_text_window(_("MENU_LICENSE"), content, width=80, height=24)
        ttk.Button(win, text=_("BTN_ACCEPT"), command=win.destroy).pack(pady=(0, 8))

    def _menu_show_about(self):
        win = tk.Toplevel(self.root)
        win.title(_("MENU_ABOUT"))
        win.transient(self.root)
        win.resizable(False, False)
        try:
            banner_img = tk.PhotoImage(file=BANNER_IMAGE_PATH)
            banner_label = ttk.Label(win, image=banner_img)
            banner_label.image = banner_img  # keep a reference - PhotoImage is garbage-collected otherwise
            banner_label.pack(padx=8, pady=8)
        except tk.TclError:
            pass  # banner image missing/unreadable - still show the text below
        ttk.Label(
            win, text=f"URTC Tester v{TESTER_VERSION}\n{_('LBL_ABOUT_AUTHOR', author=TESTER_AUTHOR)}",
            justify="center",
        ).pack(padx=8, pady=(0, 8))
        ttk.Button(win, text=_("BTN_ACCEPT"), command=win.destroy).pack(pady=(0, 8))
        win.update_idletasks()
        win.geometry(_center_geometry(win, win.winfo_reqwidth(), win.winfo_reqheight()))

    def on_close(self):
        self._stop_bus_health_monitor()
        for job_id in list(self._keepalive_jobs.values()):
            try:
                self.root.after_cancel(job_id)
            except Exception:
                pass
        if self.bus is not None:
            self.bus.stop()
        if self.transport is not None:
            try:
                self.transport.close()
            except Exception:
                pass
        if self._file_logger is not None:
            for h in list(self._file_logger.handlers):
                try:
                    h.close()
                    self._file_logger.removeHandler(h)
                except Exception:
                    pass
        self.root.destroy()


