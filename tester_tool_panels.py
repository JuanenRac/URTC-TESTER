# =============================================================================
# URTC Tester - ToolPanelsMixin: the 19 tool-specific panel builders
# covering all 25 tool profiles (several profiles share one builder -
# _build_motion_panel alone covers 7 of them). No standalone class -
# mixed into TesterGUI in tester_gui_core.py alongside the other panel
# mixins. Relies on
# PanelHelpersMixin's methods (_translated_combobox, _safe_int,
# _start_keepalive, _create_live_graph) being present on the same
# instance via multiple inheritance, not imported directly here.
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
import struct
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

import advanced_protocol as protocol
from tester_config import (
    AOI_STROBE_DEFAULT_MS, AOI_STROBE_MAX_MS, SETPOINT_MAX_C, _, CAN_ID_3DP_HOTEND_FAN_CMD, CAN_ID_3DP_HOTEND_FAN_RPM, CAN_ID_3DP_HOTEND_TELEM,
    CAN_ID_3DP_LAYER_FAN_CMD, CAN_ID_3DP_LAYER_FAN_RPM, CAN_ID_3DP_THERMAL_MOTION,
    CAN_ID_AOI_CMD, CAN_ID_AOI_TELEMETRY, CAN_ID_DRILL_CMD, CAN_ID_DRILL_TELEMETRY,
    CAN_ID_IMPACT_EVENT, CAN_ID_LASER_CMD, CAN_ID_LASER_TELEMETRY, CAN_ID_MOTION_CMD,
    CAN_ID_SOLDER_SETPOINT, CAN_ID_SOLDER_TELEMETRY, CAN_ID_VACUUM_TELEMETRY,
    CAN_ID_SOLDER_FEEDER_RESET, CAN_ID_SOLDER_FEEDER_POS,
    CAN_ID_ELECTROMAGNET_CMD, CAN_ID_SPOT_WELD_CMD, CAN_ID_UV_CURING_CMD,
    CAN_ID_HOTAIR_CMD, CAN_ID_CRIMPING_CMD, CAN_ID_ULTRASONIC_WELD_CMD,
    CAN_ID_FLYING_PROBE_BASIC, CAN_ID_ADS1115_CONFIG, CAN_ID_ADS1115_TRIGGER,
    CAN_ID_ADS1115_RESULT, CAN_ID_PASTE_JETTING_CONFIG, CAN_ID_PASTE_JETTING_PULSE,
    CAN_ID_THERMAL_TRIGGER, CAN_ID_THERMAL_STATUS, CAN_ID_THERMAL_CALIB_CHUNK_REQ,
    CAN_ID_THERMAL_CALIB_CHUNK, CAN_ID_MLX_VARIANT_RESP, MLX_SENSOR_VARIANTS,
)


class ToolPanelsMixin:

    def _build_soldering_iron_panel(self, parent, tool_id=None, tool_name=None):
        setpoint = tk.IntVar(value=0)
        active = tk.BooleanVar(value=False)
        temp_var = tk.StringVar(value="-- °C")

        ttk.Label(parent, text=_("LBL_SETPOINT_TEMPERATURE")).grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Spinbox(parent, from_=0, to=SETPOINT_MAX_C, textvariable=setpoint, width=6).grid(row=0, column=1, sticky="w", padx=4)

        def _send_setpoint():
            value = max(0, min(SETPOINT_MAX_C, self._safe_int(setpoint, 0)))
            self.bus.send(CAN_ID_SOLDER_SETPOINT, struct.pack(">H", value))

        def _toggle():
            # No *_ catch-all here (there used to be one) - this is only
            # ever wired up as a ttk widget's own command= callback, which
            # Tk always invokes with zero arguments, never as a .bind()
            # handler (which would pass an event). A bare *_ parameter
            # would otherwise shadow tester_config._ (the translation
            # function every _("...") call below actually needs) with
            # this callback's own empty args tuple for the entire body of
            # this function - every _(...) call inside would then raise
            # TypeError: 'tuple' object is not callable the moment this
            # runs, silently swallowed by Tkinter's own callback exception
            # handler (a traceback printed to stderr, nothing more) rather
            # than crashing outright - which meant clicking this "Active"
            # checkbox appeared to do nothing at all: the exception fires
            # on this function's very first _(...) call, before
            # _start_keepalive ever runs, so no keepalive is ever armed
            # and no CAN frame for this control ever gets sent. Confirmed
            # empirically with a real ttk.Checkbutton.invoke() before this
            # fix (raised exactly that TypeError), and confirmed fixed
            # after (keepalive registers, a real frame is sent).
            if active.get():
                self.log(_("LOG_SOLDER_SETPOINT_ACTIVE", temp=self._safe_int(setpoint, 0)))
                self._start_keepalive("solder", 150, _send_setpoint, on_failure=lambda: active.set(False))
            else:
                self._stop_keepalive("solder")
                self.bus.send(CAN_ID_SOLDER_SETPOINT, struct.pack(">H", 0))
                self.log(_("LOG_SOLDER_TURNED_OFF"))

        ttk.Checkbutton(parent, text=_("LBL_ACTIVE_250MS_WATCHDOG"),
                         variable=active, command=_toggle).grid(row=0, column=2, sticky="w", padx=8)

        ttk.Separator(parent, orient="horizontal").grid(row=1, column=0, columnspan=3, sticky="ew", pady=6)
        ttk.Label(parent, text=_("LBL_LIVE_TEMPERATURE")).grid(row=2, column=0, sticky="w", padx=4, pady=2)
        ttk.Label(parent, textvariable=temp_var, font=("", 11, "bold")).grid(row=2, column=1, sticky="w")
        graph_frame = ttk.Frame(parent)
        graph_frame.grid(row=3, column=0, columnspan=3, sticky="w", padx=4)
        add_temp_point = self._create_live_graph(graph_frame, y_max=450, label="solder_iron_temp_c")

        def _on_telemetry(data):
            if len(data) < 2:
                return
            temp = struct.unpack(">H", data[0:2])[0]
            self.root.after(0, lambda: temp_var.set(f"{temp} °C"))
            self.root.after(0, lambda: add_temp_point(temp))

        self.bus.register(CAN_ID_SOLDER_TELEMETRY, _on_telemetry)

        # doc #16's own solder-wire-feeder motor - same CONN_MOT connector
        # and 0x120 protocol as the 7 tools _build_motion_panel already
        # covers, reused here rather than duplicated. This tool's own
        # heater section above uses rows 0-3, so the shared panel starts
        # at row 4.
        ttk.Separator(parent, orient="horizontal").grid(row=4, column=0, columnspan=3, sticky="ew", pady=6)
        self._build_motion_panel(parent, tool_id, tool_name or _("TOOL_SOLDERING_IRON_FEEDER_LABEL"), start_row=5)

        # Position tracking - open-loop (no encoder on this motor), so this
        # is this board's own best estimate of how much wire has been fed
        # since the last reset, not a physical measurement. Query/response
        # and reset both live on 0x131/0x132 - see CANBUS.TXT.
        pos_row = 9  # _build_motion_panel above occupies rows 5-8 (title, direction, steps+move, help text)
        ttk.Separator(parent, orient="horizontal").grid(row=pos_row, column=0, columnspan=3, sticky="ew", pady=6)
        position_var = tk.StringVar(value="--")
        ttk.Label(parent, text=_("LBL_FEEDER_POSITION")).grid(row=pos_row+1, column=0, sticky="w", padx=4, pady=4)
        ttk.Label(parent, textvariable=position_var, font=("", 11, "bold")).grid(row=pos_row+1, column=1, sticky="w")

        def _on_position(data):
            if len(data) < 4:
                return
            pos = struct.unpack(">i", data[0:4])[0]
            self.root.after(0, lambda: position_var.set(_("VAL_FEEDER_STEPS", n=pos)))

        self.bus.register(CAN_ID_SOLDER_FEEDER_POS, _on_position)

        def _query_position():
            self.bus.send(CAN_ID_SOLDER_FEEDER_POS, b"")

        def _reset_position():
            if messagebox.askyesno(_("TITLE_RESET_FEEDER_POSITION_Q"), _("CONFIRM_RESET_FEEDER_POSITION")):
                self.bus.send(CAN_ID_SOLDER_FEEDER_RESET, bytes([0x52, 0x53, 0x50, 0x30]))
                self.log(_("LOG_FEEDER_POSITION_RESET"))

        self._new_deck_button(parent, text=_("BTN_QUERY"), command=_query_position).grid(row=pos_row+1, column=2, padx=8)
        self._new_deck_button(parent, text=_("BTN_RESET_FEEDER_POSITION"), command=_reset_position).grid(row=pos_row+2, column=0, columnspan=2, sticky="w", padx=4, pady=(4, 0))
        ttk.Label(
            parent,
            text=_("HELP_FEEDER_POSITION_OPEN_LOOP"),
            foreground="gray", wraplength=380, justify="left",
        ).grid(row=pos_row+3, column=0, columnspan=3, sticky="w", padx=4, pady=(8, 0))

        _query_position()

    def _build_motion_panel(self, parent, tool_id, tool_name, cmd_id=None, start_row=0):
        # 7 tools (paste/liquid dispenser, screwdriver, both grippers,
        # SMT pick&place, large-format vacuum gripper) share the exact
        # same command (0x120 by default) and have no telemetry of
        # their own - a plain stepper: direction + step count, one-shot,
        # no watchdog to satisfy. cmd_id lets Crimping Actuator reuse
        # this same panel with 0x1F0 instead - identical byte layout,
        # different destination (the expansion board's own driver
        # rather than the onboard one) - see CANBUS.TXT's own 0x1F0.
        if cmd_id is None:
            cmd_id = CAN_ID_MOTION_CMD
        steps = tk.IntVar(value=200)
        r = start_row

        ttk.Label(parent, text=_("TITLE_PLAIN_STEPPER_MOTION", tool=tool_name),
                  font=("", 10, "bold")).grid(row=r, column=0, columnspan=3, sticky="w", padx=4, pady=(4, 8))
        ttk.Label(parent, text=_("LBL_DIRECTION")).grid(row=r+1, column=0, sticky="w", padx=4, pady=4)
        direction, direction_combo = self._translated_combobox(parent, ["Forward", "Reverse"], "OPT", width=12)
        direction_combo.grid(row=r+1, column=1, sticky="w", padx=4)
        ttk.Label(parent, text=_("LBL_STEPS")).grid(row=r+2, column=0, sticky="w", padx=4, pady=4)
        ttk.Spinbox(parent, from_=1, to=4294967295, textvariable=steps, width=12).grid(row=r+2, column=1, sticky="w", padx=4)

        def _send_move():
            # `0x01 if direction.get == "Forward" else 0x00`
            # let ANY value the combobox itself never actually offers
            # (a real bug in the widget, or a future refactor accidentally
            # feeding this a raw untranslated key) silently encode as the
            # OTHER, opposite, equally-valid physical direction instead of
            # being caught - the combobox constraining what an operator
            # CAN pick is a UI guarantee, not a protocol-boundary one.
            raw_direction = direction.get()
            if raw_direction not in ("Forward", "Reverse"):
                self.log(_("LOG_TOOL_MOVE_BLOCKED_DIRECTION", tool=tool_name, direction=raw_direction))
                return
            dir_byte = 0x01 if raw_direction == "Forward" else 0x00
            # Spinbox's own to=4294967295 only constrains the arrow
            # buttons, not text typed directly into the field (confirmed
            # empirically) - clamping here is what actually keeps this
            # inside struct.pack(">I", ...)'s valid range.
            n = min(max(1, self._safe_int(steps, 1)), 0xFFFFFFFF)
            if cmd_id == CAN_ID_CRIMPING_CMD and not self._confirm_physical_action():
                return
            data = bytes([dir_byte]) + struct.pack(">I", n)
            self.bus.send(cmd_id, data)
            self.log(_("LOG_TOOL_MOVE", tool=tool_name, direction=self._opt_display(direction.get()), n=n))

        self._new_deck_button(parent, text=_("BTN_MOVE"), command=_send_move).grid(row=r+2, column=2, padx=8)

        def _send_stop():
            # 0 steps is the firmware's order to stop a movement (firmware_can_motion.c); the Spinbox only allows 1 or more, so this is the one way to stop a long move
            self.bus.send(cmd_id, bytes([0x00]) + struct.pack(">I", 0))
            self.log(_("LOG_TOOL_STOP", tool=tool_name))

        self._new_deck_button(parent, text=_("BTN_STOP_MOTION"), command=_send_stop).grid(row=r+2, column=3, padx=8)
        ttk.Label(
            parent,
            text=_("HELP_ONE_SHOT_NO_TELEMETRY"),
            foreground="gray", wraplength=380, justify="left",
        ).grid(row=r+3, column=0, columnspan=3, sticky="w", padx=4, pady=(8, 0))

    def _build_vacuum_panel(self, parent):
        # Telemetry only - no commands for this tool at all.
        adc_var = tk.StringVar(value="--")
        detect_var = tk.StringVar(value="--")

        ttk.Label(parent, text=_("TITLE_VACUUM_TELEMETRY"),
                  font=("", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=4, pady=(4, 8))
        ttk.Label(parent, text=_("LBL_ANALOG_READING")).grid(row=1, column=0, sticky="w", padx=4, pady=4)
        ttk.Label(parent, textvariable=adc_var, font=("", 11, "bold")).grid(row=1, column=1, sticky="w")
        ttk.Label(parent, text=_("LBL_PART_DETECTED_LM393")).grid(row=2, column=0, sticky="w", padx=4, pady=4)
        ttk.Label(parent, textvariable=detect_var, font=("", 11, "bold")).grid(row=2, column=1, sticky="w")

        def _on_telemetry(data):
            if len(data) < 3:
                return
            adc = struct.unpack(">H", data[0:2])[0]
            detected = data[2]
            self.root.after(0, lambda: adc_var.set(str(adc)))
            self.root.after(0, lambda: detect_var.set(_("VAL_PART_PICKED_UP") if detected else _("VAL_PART_NOT_DETECTED")))

        self.bus.register(CAN_ID_VACUUM_TELEMETRY, _on_telemetry)

    def _build_drill_panel(self, parent):
        speed = tk.IntVar(value=0)
        rpm_var = tk.StringVar(value="--")
        endstop_var = tk.StringVar(value="--")

        ttk.Label(parent, text=_("LBL_SPEED_0_255")).grid(row=0, column=0, sticky="w", padx=4, pady=4)
        speed_scale = ttk.Scale(parent, from_=0, to=255, variable=speed, orient="horizontal", length=160)
        speed_scale.grid(row=0, column=1, sticky="w", padx=4)
        speed_label = ttk.Label(parent, text="0")
        speed_label.grid(row=0, column=2, sticky="w")
        speed_scale.config(command=lambda v: speed_label.config(text=str(int(float(v)))))

        ttk.Label(parent, text=_("LBL_DIRECTION")).grid(row=1, column=0, sticky="w", padx=4, pady=4)
        direction, direction_combo = self._translated_combobox(parent, ["Clockwise", "Counter-clockwise"], "OPT", width=14)
        direction_combo.grid(row=1, column=1, sticky="w", padx=4)

        # Physical-safety confirmation, same askyesno/icon="warning" pattern
        # already used elsewhere for irreversible/hazardous actions (see
        # CommonPanelsMixin._erase_fram) - a spinning drill bit is real,
        # physical, at-hand equipment, not something a stray click should
        # ever be able to start unconfirmed. Only asked on the actual
        # off->on transition (tracked in self._drill_last_sent_speed
        # below), not on every Send click while it's already running -
        # re-confirming a speed change on an already-spinning drill would
        # just train the user to reflexively click through the dialog,
        # defeating the point of asking at all; the transition into motion
        # is the one moment this can actually still prevent something.
        #
        # Kept as an instance attribute rather than a plain closure-local -
        # CommonPanelsMixin._run_self_test's own drill step sends a real,
        # physical zero-speed command straight to CAN_ID_DRILL_CMD to
        # verify telemetry, bypassing this panel's own _send_drill()
        # entirely. A closure-local here would never learn that the
        # physical drill was actually stopped that way, so running
        # Self-Test while the drill was spinning would leave this thinking
        # it was still on - the very next Send click with an unchanged
        # nonzero speed would then skip the confirmation dialog even
        # though it's a genuine off->on transition for the real hardware.
        # _run_self_test resets this same attribute after its own drill
        # step for exactly that reason.
        self._drill_last_sent_speed = 0

        drill_active = tk.BooleanVar(value=False)

        def _drill_frame():
            # an unrecognized direction must never silently become the opposite valid one just because the combobox itself is only ever supposed to offer these two labels
            raw_direction = direction.get()
            if raw_direction not in ("Clockwise", "Counter-clockwise"):
                self.log(_("LOG_TOOL_MOVE_BLOCKED_DIRECTION", tool="Drill", direction=raw_direction))
                return None
            dir_byte = 0x01 if raw_direction == "Counter-clockwise" else 0x00
            return bytes([max(0, min(255, self._safe_int(speed, 0))), dir_byte])

        def _drill_tick():
            frame = _drill_frame()
            if frame is not None:
                self.bus.send(CAN_ID_DRILL_CMD, frame)

        def _toggle_drill():
            # The firmware cuts the drill after 250 ms without a new command and latches a CRITICAL ERROR (firmware_telemetry_watchdog.c): it must be refreshed like the laser or
            # the heaters, and switching it off sends speed 0 (the active brake). A single send used to spin it for 250 ms and leave the board in error.
            if drill_active.get():
                frame = _drill_frame()
                if frame is None:
                    drill_active.set(False)
                    return
                if frame[0] > 0 and not messagebox.askyesno(
                    _("TITLE_CONFIRM_DRILL_ACTIVATION_Q"),
                    _("MSG_CONFIRM_DRILL_ACTIVATION"),
                    icon="warning",
                ):
                    drill_active.set(False)
                    return
                self._drill_last_sent_speed = frame[0]
                self._start_keepalive("drill", 150, _drill_tick, on_failure=lambda: drill_active.set(False))
            else:
                self._stop_keepalive("drill")
                self._drill_last_sent_speed = 0
                self.bus.send(CAN_ID_DRILL_CMD, bytes([0x00, 0x00]))
                self.log(_("LOG_DRILL_STOPPED"))

        ttk.Checkbutton(parent, text=_("LBL_ACTIVE_250MS_WATCHDOG"), variable=drill_active, command=_toggle_drill).grid(row=1, column=2, sticky="w", padx=8)
        ttk.Label(
            parent, text=_("HELP_NO_WATCHDOG_HOLDS_VALUE"),
            foreground="gray", wraplength=380, justify="left",
        ).grid(row=2, column=0, columnspan=3, sticky="w", padx=4, pady=(4, 8))

        ttk.Separator(parent, orient="horizontal").grid(row=3, column=0, columnspan=3, sticky="ew", pady=4)
        ttk.Label(parent, text=_("LBL_ACTUAL_RPM")).grid(row=4, column=0, sticky="w", padx=4, pady=2)
        ttk.Label(parent, textvariable=rpm_var, font=("", 11, "bold")).grid(row=4, column=1, sticky="w")
        ttk.Label(parent, text=_("LBL_ENDSTOP_LIMIT_SWITCH")).grid(row=5, column=0, sticky="w", padx=4, pady=2)
        ttk.Label(parent, textvariable=endstop_var).grid(row=5, column=1, sticky="w")

        def _on_telemetry(data):
            if len(data) < 3:
                return
            rpm = struct.unpack(">H", data[0:2])[0]
            endstop = data[2]
            self.root.after(0, lambda: rpm_var.set(f"{rpm} RPM"))
            self.root.after(0, lambda: endstop_var.set(_("VAL_TRIGGERED") if endstop else _("VAL_ENDSTOP_OPEN")))

        self.bus.register(CAN_ID_DRILL_TELEMETRY, _on_telemetry)

    def _build_aoi_panel(self, parent):
        period_ms = tk.IntVar(value=AOI_STROBE_DEFAULT_MS)
        endstop_var = tk.StringVar(value="--")

        ttk.Label(parent, text=_("LBL_RING_MODE")).grid(row=0, column=0, sticky="w", padx=4, pady=4)
        mode, mode_combo = self._translated_combobox(
            parent, ["Off", "Synchronous strobe", "Fixed continuous"], "OPT", width=16,
        )
        mode_combo.grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(parent, text=_("LBL_STROBE_PERIOD")).grid(row=1, column=0, sticky="w", padx=4, pady=4)
        ttk.Spinbox(parent, from_=1, to=AOI_STROBE_MAX_MS, textvariable=period_ms, width=8).grid(row=1, column=1, sticky="w", padx=4)

        def _send_aoi():
            mode_byte = {"Off": 0x00, "Synchronous strobe": 0x01, "Fixed continuous": 0x02}[mode.get()]
            data = bytes([mode_byte]) + struct.pack(">H", max(1, min(AOI_STROBE_MAX_MS, self._safe_int(period_ms, AOI_STROBE_DEFAULT_MS))))
            self.bus.send(CAN_ID_AOI_CMD, data)
            self.log(_("LOG_AOI_MODE_PERIOD", mode=self._opt_display(mode.get()), period=self._safe_int(period_ms, AOI_STROBE_DEFAULT_MS)))

        self._new_deck_button(parent, text=_("BTN_SEND"), command=_send_aoi).grid(row=1, column=2, padx=8)
        ttk.Label(
            parent, text=_("HELP_RING_COLOR_FROM_GLOBAL"),
            foreground="gray", wraplength=380, justify="left",
        ).grid(row=2, column=0, columnspan=3, sticky="w", padx=4, pady=(4, 8))

        ttk.Separator(parent, orient="horizontal").grid(row=3, column=0, columnspan=3, sticky="ew", pady=4)
        ttk.Label(parent, text=_("LBL_ENDSTOP_LIMIT_SWITCH")).grid(row=4, column=0, sticky="w", padx=4, pady=2)
        ttk.Label(parent, textvariable=endstop_var).grid(row=4, column=1, sticky="w")

        def _on_telemetry(data):
            if len(data) < 1:
                return
            endstop = data[0]
            self.root.after(0, lambda: endstop_var.set(_("VAL_TRIGGERED") if endstop else _("VAL_ENDSTOP_OPEN")))

        self.bus.register(CAN_ID_AOI_TELEMETRY, _on_telemetry)

    def _build_laser_panel(self, parent):
        power = tk.IntVar(value=0)
        interlock = tk.BooleanVar(value=False)
        active = tk.BooleanVar(value=False)
        endstop_var = tk.StringVar(value="--")

        ttk.Label(
            parent, text=_("HELP_INTERLOCK_MUST_BE_ARMED"),
            foreground="#b35900", wraplength=380, justify="left",
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=4, pady=(4, 8))

        ttk.Label(parent, text=_("LBL_POWER_0_255")).grid(row=1, column=0, sticky="w", padx=4, pady=4)
        power_scale = ttk.Scale(parent, from_=0, to=255, variable=power, orient="horizontal", length=160)
        power_scale.grid(row=1, column=1, sticky="w", padx=4)
        power_label = ttk.Label(parent, text="0")
        power_label.grid(row=1, column=2, sticky="w")
        power_scale.config(command=lambda v: power_label.config(text=str(int(float(v)))))

        ttk.Checkbutton(parent, text=_("LBL_INTERLOCK_ARMED"),
                         variable=interlock).grid(row=2, column=0, columnspan=3, sticky="w", padx=4, pady=4)

        def _send_laser():
            self.bus.send(CAN_ID_LASER_CMD, bytes([
                max(0, min(255, power.get())),
                0x01 if interlock.get() else 0x00,
            ]))

        def _toggle():
            # No *_ catch-all here (there used to be one) - this is only
            # ever wired up as a ttk widget's own command= callback, which
            # Tk always invokes with zero arguments, never as a .bind()
            # handler (which would pass an event). A bare *_ parameter
            # would otherwise shadow tester_config._ (the translation
            # function every _("...") call below actually needs) with
            # this callback's own empty args tuple for the entire body of
            # this function - every _(...) call inside would then raise
            # TypeError: 'tuple' object is not callable the moment this
            # runs, silently swallowed by Tkinter's own callback exception
            # handler (a traceback printed to stderr, nothing more) rather
            # than crashing outright - which meant clicking this "Active"
            # checkbox appeared to do nothing at all: the exception fires
            # on this function's very first _(...) call, before
            # _start_keepalive ever runs, so no keepalive is ever armed
            # and no CAN frame for this control ever gets sent. Confirmed
            # empirically with a real ttk.Checkbutton.invoke() before this
            # fix (raised exactly that TypeError), and confirmed fixed
            # after (keepalive registers, a real frame is sent).
            if active.get():
                # Same physical-safety confirmation as the drill's own Send
                # button above (see that panel's own comment) - this is a
                # real laser, not a simulated one, and the software
                # interlock checkbox just above is a separate signal sent
                # to the firmware, not a substitute for a human explicitly
                # confirming "yes, energize this now". Declining reverts
                # the checkbox rather than leaving it checked-but-inactive,
                # so the UI never shows "Active" for something that never
                # actually started.
                if not messagebox.askyesno(
                    _("TITLE_CONFIRM_LASER_ACTIVATION_Q"),
                    _("MSG_CONFIRM_LASER_ACTIVATION"),
                    icon="warning",
                ):
                    active.set(False)
                    return
                interlock_state = _("LBL_ARMED") if interlock.get() else _("LBL_SAFE")
                self.log(_("LOG_LASER_POWER_INTERLOCK", power=power.get(), interlock=interlock_state))
                self._start_keepalive("laser", 150, _send_laser, on_failure=lambda: active.set(False))
            else:
                self._stop_keepalive("laser")
                self.bus.send(CAN_ID_LASER_CMD, bytes([0x00, 0x00]))
                self.log(_("LOG_LASER_STOPPED"))

        ttk.Checkbutton(parent, text=_("LBL_ACTIVE_250MS_WATCHDOG"),
                         variable=active, command=_toggle).grid(row=3, column=0, columnspan=3, sticky="w", padx=4)

        ttk.Separator(parent, orient="horizontal").grid(row=4, column=0, columnspan=3, sticky="ew", pady=6)
        ttk.Label(parent, text=_("LBL_ENDSTOP_LIMIT_SWITCH")).grid(row=5, column=0, sticky="w", padx=4, pady=2)
        ttk.Label(parent, textvariable=endstop_var).grid(row=5, column=1, sticky="w")

        def _on_telemetry(data):
            if len(data) < 1:
                return
            endstop = data[0]
            self.root.after(0, lambda: endstop_var.set(_("VAL_TRIGGERED") if endstop else _("VAL_ENDSTOP_OPEN")))

        self.bus.register(CAN_ID_LASER_TELEMETRY, _on_telemetry)

    def _build_scan_probe_panel(self, parent):
        # No commands at all - this tool only monitors PB3 and fires an
        # instant, max-priority event on contact.
        count_var = tk.StringVar(value="0")
        last_var = tk.StringVar(value=_("VAL_NONE_YET"))
        self._probe_impact_count = 0

        ttk.Label(parent, text=_("TITLE_SCAN_PROBE_TELEMETRY"),
                  font=("", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=4, pady=(4, 8))
        ttk.Label(parent, text=_("LBL_IMPACTS_DETECTED_SESSION")).grid(row=1, column=0, sticky="w", padx=4, pady=4)
        ttk.Label(parent, textvariable=count_var, font=("", 11, "bold")).grid(row=1, column=1, sticky="w")
        ttk.Label(parent, text=_("LBL_LAST_IMPACT")).grid(row=2, column=0, sticky="w", padx=4, pady=4)
        ttk.Label(parent, textvariable=last_var).grid(row=2, column=1, sticky="w")
        ttk.Label(
            parent,
            text=_("HELP_SCAN_PROBE_INTERRUPT"),
            foreground="gray", wraplength=380, justify="left",
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=4, pady=(8, 0))

        def _on_impact(data):
            if len(data) >= 1 and data[0] == 0x01:
                self._probe_impact_count += 1
                ts = time.strftime("%H:%M:%S")
                self.root.after(0, lambda: count_var.set(str(self._probe_impact_count)))
                self.root.after(0, lambda: last_var.set(ts))
                self.log(_("LOG_SCAN_PROBE_IMPACT", ts=ts))

        self.bus.register(CAN_ID_IMPACT_EVENT, _on_impact)

    def _build_3dprinter_panel(self, parent):
        nozzle_setpoint = tk.IntVar(value=0)
        nozzle_active = tk.BooleanVar(value=False)
        extruder_steps = tk.IntVar(value=200)
        layer_fan_power = tk.IntVar(value=0)
        layer_fan_active = tk.BooleanVar(value=False)
        hotend_fan_power = tk.IntVar(value=0)
        hotend_temp_var = tk.StringVar(value="-- °C")
        layer_rpm_var = tk.StringVar(value="--")
        hotend_rpm_var = tk.StringVar(value="--")

        # 2 columns rather than one long stack - left column is the
        # extruder/hotend heater controls, right column is both fans plus
        # telemetry/graph. Roughly balances the 2 columns' height rather
        # than splitting strictly by section count.
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)
        left = ttk.Frame(parent)
        left.grid(row=0, column=0, sticky="new")
        right = ttk.Frame(parent)
        right.grid(row=0, column=1, sticky="new")

        ttk.Label(left, text=_("LBL_NOZZLE_SETPOINT")).grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Spinbox(left, from_=0, to=300, textvariable=nozzle_setpoint, width=6).grid(row=0, column=1, sticky="w", padx=4)

        def _send_thermal_motion(steps_override=None, temp_override=None):
            # temp_override is how the heater is turned OFF: the frame must say 0 C. Sending the spinbox's setpoint here re-armed the heater with nothing to keep it alive,
            # and the firmware's 250 ms watchdog then cut it and latched a critical error.
            temp = max(0, min(300, self._safe_int(nozzle_setpoint, 0))) if temp_override is None else temp_override
            dir_byte = 0x01 if extruder_dir.get() == "Forward" else 0x00
            # steps_override lets a caller force this frame's step count
            # regardless of whatever the Spinbox currently holds - see
            # _send_temp_keepalive_tick below for why the periodic
            # temperature-hold keepalive needs that.
            steps = (max(0, self._safe_int(extruder_steps, 0)) & 0xFFFFFF) if steps_override is None else steps_override
            data = struct.pack(">H", temp) + bytes([dir_byte]) + steps.to_bytes(3, "big")
            self.bus.send(CAN_ID_3DP_THERMAL_MOTION, data)

        def _send_temp_keepalive_tick():
            # CAN_ID_3DP_THERMAL_MOTION carries the setpoint temperature AND
            # the extruder direction/steps in one frame, so the heater
            # keepalive cannot repeat the Spinbox step count (that would
            # command another identical move every 150 ms). It sends 0 steps
            # instead, which the firmware reads as an order to STOP the
            # extruder: a move started with "Move Extruder Once" while the
            # heater is armed is cancelled by the next keepalive. Moving the
            # extruder while a temperature is held needs a firmware change.
            _send_thermal_motion(steps_override=0)

        def _toggle_nozzle():
            # See the generic _toggle() callbacks elsewhere in this file
            # for the full explanation - a bare *_ parameter here used to
            # shadow tester_config._ for this whole function body, so
            # every _(...) call below raised TypeError the moment this
            # ran, silently swallowed by Tkinter, meaning the nozzle
            # heater's "Active" checkbox never actually armed its
            # keepalive.
            if nozzle_active.get():
                self.log(_("LOG_3DP_NOZZLE_SETPOINT_ACTIVE", temp=self._safe_int(nozzle_setpoint, 0)))
                self._start_keepalive("nozzle", 150, _send_temp_keepalive_tick, on_failure=lambda: nozzle_active.set(False))
            else:
                self._stop_keepalive("nozzle")
                _send_thermal_motion(steps_override=0, temp_override=0)
                self.log(_("LOG_3DP_NOZZLE_TURNED_OFF"))

        ttk.Checkbutton(left, text=_("LBL_HEATER_ACTIVE_250MS"), variable=nozzle_active,
                         command=_toggle_nozzle).grid(row=0, column=2, sticky="w", padx=8)

        ttk.Label(left, text=_("LBL_EXTRUDER_DIRECTION")).grid(row=1, column=0, sticky="w", padx=4, pady=4)
        extruder_dir, extruder_dir_combo = self._translated_combobox(left, ["Forward", "Retract"], "OPT", width=10)
        extruder_dir_combo.grid(row=1, column=1, sticky="w", padx=4)
        ttk.Label(left, text=_("LBL_EXTRUDER_STEPS")).grid(row=2, column=0, sticky="w", padx=4, pady=4)
        ttk.Spinbox(left, from_=0, to=16777215, textvariable=extruder_steps, width=10).grid(row=2, column=1, sticky="w", padx=4)
        # a single move only carries the setpoint when the heater is really on (kept alive); otherwise it must not heat for 250 ms and latch an error
        self._new_deck_button(left, text=_("BTN_MOVE_EXTRUDER_ONCE"), command=lambda: _send_thermal_motion(temp_override=None if nozzle_active.get() else 0)).grid(row=2, column=2, padx=8)
        ttk.Label(
            left, text=_("HELP_EXTRUDER_MOTION_SHARED_FRAME"),
            foreground="gray", wraplength=380, justify="left",
        ).grid(row=3, column=0, columnspan=3, sticky="w", padx=4, pady=(0, 8))

        ttk.Label(right, text=_("LBL_LAYER_FAN_POWER")).grid(row=0, column=0, sticky="w", padx=4, pady=4)
        layer_scale = ttk.Scale(right, from_=0, to=255, variable=layer_fan_power, orient="horizontal", length=140)
        layer_scale.grid(row=0, column=1, sticky="w", padx=4)
        layer_label = ttk.Label(right, text="0")
        layer_label.grid(row=0, column=2, sticky="w")
        layer_scale.config(command=lambda v: layer_label.config(text=str(int(float(v)))))

        def _send_layer_fan():
            self.bus.send(CAN_ID_3DP_LAYER_FAN_CMD, bytes([max(0, min(255, layer_fan_power.get()))]))

        def _toggle_layer_fan():
            # Same *_ shadowing bug as the generic _toggle() callbacks
            # elsewhere in this file - see one of those for the full
            # explanation.
            if layer_fan_active.get():
                self.log(_("LOG_LAYER_FAN_ACTIVE", power=layer_fan_power.get()))
                self._start_keepalive("layer_fan", 400, _send_layer_fan, on_failure=lambda: layer_fan_active.set(False))
            else:
                self._stop_keepalive("layer_fan")
                self.bus.send(CAN_ID_3DP_LAYER_FAN_CMD, bytes([0x00]))
                self.log(_("LOG_LAYER_FAN_STOPPED"))

        ttk.Checkbutton(right, text=_("LBL_ACTIVE_1000MS_WATCHDOG"), variable=layer_fan_active,
                         command=_toggle_layer_fan).grid(row=1, column=0, columnspan=2, sticky="w", padx=4)

        ttk.Label(right, text=_("LBL_HOTEND_FAN_POWER")).grid(row=2, column=0, sticky="w", padx=4, pady=4)
        hotend_fan_scale = ttk.Scale(right, from_=0, to=255, variable=hotend_fan_power, orient="horizontal", length=140)
        hotend_fan_scale.grid(row=2, column=1, sticky="w", padx=4)
        hotend_fan_label = ttk.Label(right, text="0")
        hotend_fan_label.grid(row=2, column=2, sticky="w")
        hotend_fan_scale.config(command=lambda v: hotend_fan_label.config(text=str(int(float(v)))))

        def _send_hotend_fan():
            self.bus.send(CAN_ID_3DP_HOTEND_FAN_CMD, bytes([max(0, min(255, hotend_fan_power.get()))]))

        self._new_deck_button(right, text=_("BTN_SEND"), command=_send_hotend_fan).grid(row=2, column=3, padx=8)
        ttk.Label(
            right, text=_("HELP_NO_WATCHDOG_STALL_DETECTOR"),
            foreground="gray", wraplength=380, justify="left",
        ).grid(row=3, column=0, columnspan=4, sticky="w", padx=4, pady=(0, 8))

        ttk.Separator(right, orient="horizontal").grid(row=4, column=0, columnspan=4, sticky="ew", pady=4)
        ttk.Label(right, text=_("LBL_HOTEND_TEMPERATURE")).grid(row=5, column=0, sticky="w", padx=4, pady=2)
        ttk.Label(right, textvariable=hotend_temp_var, font=("", 11, "bold")).grid(row=5, column=1, sticky="w")
        ttk.Label(right, text=_("LBL_LAYER_FAN_RPM")).grid(row=6, column=0, sticky="w", padx=4, pady=2)
        ttk.Label(right, textvariable=layer_rpm_var).grid(row=6, column=1, sticky="w")
        ttk.Label(right, text=_("LBL_HOTEND_FAN_RPM")).grid(row=7, column=0, sticky="w", padx=4, pady=2)
        ttk.Label(right, textvariable=hotend_rpm_var).grid(row=7, column=1, sticky="w")
        graph_frame = ttk.Frame(right)
        graph_frame.grid(row=8, column=0, columnspan=4, sticky="w", padx=4)
        add_nozzle_temp_point = self._create_live_graph(graph_frame, y_max=300, label="hotend_nozzle_temp_c")

        def _on_hotend_temp(data):
            if len(data) < 2:
                return
            temp = struct.unpack(">H", data[0:2])[0]
            self.root.after(0, lambda: hotend_temp_var.set(f"{temp} °C"))
            self.root.after(0, lambda: add_nozzle_temp_point(temp))

        def _on_layer_rpm(data):
            if len(data) < 2:
                return
            rpm = struct.unpack(">H", data[0:2])[0]
            self.root.after(0, lambda: layer_rpm_var.set(f"{rpm} RPM"))

        def _on_hotend_rpm(data):
            if len(data) < 2:
                return
            rpm = struct.unpack(">H", data[0:2])[0]
            self.root.after(0, lambda: hotend_rpm_var.set(f"{rpm} RPM"))

        self.bus.register(CAN_ID_3DP_HOTEND_TELEM, _on_hotend_temp)
        self.bus.register(CAN_ID_3DP_LAYER_FAN_RPM, _on_layer_rpm)
        self.bus.register(CAN_ID_3DP_HOTEND_FAN_RPM, _on_hotend_rpm)

    def _build_electromagnet_panel(self, parent):
        state = tk.BooleanVar(value=False)

        def _toggle():
            # No *_ catch-all here (there used to be one) - this is only
            # ever wired up as a ttk widget's own command= callback, which
            # Tk always invokes with zero arguments, never as a .bind()
            # handler (which would pass an event). A bare *_ parameter
            # would otherwise shadow tester_config._ (the translation
            # function every _("...") call below actually needs) with
            # this callback's own empty args tuple for the entire body of
            # this function - every _(...) call inside would then raise
            # TypeError: 'tuple' object is not callable the moment this
            # runs, silently swallowed by Tkinter's own callback exception
            # handler (a traceback printed to stderr, nothing more) rather
            # than crashing outright - which meant clicking this "Active"
            # checkbox appeared to do nothing at all: the exception fires
            # on this function's very first _(...) call, before
            # _start_keepalive ever runs, so no keepalive is ever armed
            # and no CAN frame for this control ever gets sent. Confirmed
            # empirically with a real ttk.Checkbutton.invoke() before this
            # fix (raised exactly that TypeError), and confirmed fixed
            # after (keepalive registers, a real frame is sent).
            self.bus.send(CAN_ID_ELECTROMAGNET_CMD, bytes([0x01 if state.get() else 0x00]))
            self.log(_("LOG_ELECTROMAGNET_STATE", state=_("LBL_ENERGIZED") if state.get() else _("LBL_RELEASED")))

        ttk.Checkbutton(parent, text=_("LBL_ELECTROMAGNET_ENERGIZE"),
                         variable=state, command=_toggle).grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Label(
            parent, text=_("HELP_ELECTROMAGNET"),
            foreground="gray", wraplength=380, justify="left",
        ).grid(row=1, column=0, sticky="w", padx=4, pady=(2, 4))

    def _build_weld_pulse_panel(self, parent, cmd_id, has_contact_gate):
        # Shared by Spot Welder (0x1C0, gated on the contact sensor) and
        # Ultrasonic Welder (0x200, no gate) - same 3-byte fire/duration
        # protocol either way, see CANBUS.TXT. The Spinbox's own ceiling
        # (and _fire's own clamp) match the firmware's real 2000ms cap
        # (firmware_can_weldpulse.c) - without it, entering something
        # higher would still get sent, but the firmware would silently
        # truncate it to 2000ms with nothing in this UI to show that
        # happened.
        duration = tk.IntVar(value=100)

        ttk.Label(parent, text=_("LBL_PULSE_DURATION_MS")).grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Spinbox(parent, from_=1, to=2000, textvariable=duration, width=8).grid(row=0, column=1, sticky="w", padx=4)

        def _fire():
            # _require_int, not _safe_int - this button fires a real,
            # physical weld pulse immediately. Silently substituting a
            # default duration (as _safe_int would) if the Spinbox
            # happens to be empty mid-edit right when this is clicked
            # would weld for however long that default says, not for
            # whatever the user actually meant to enter - see
            # _require_int's own docstring.
            raw = self._require_int(duration)
            if raw is None:
                return
            ms = max(1, min(2000, raw))
            if not self._confirm_physical_action():
                return
            self.bus.send(cmd_id, bytes([0x01]) + struct.pack(">H", ms))
            self.log(_("LOG_WELD_PULSE_FIRED", ms=ms))

        self._new_deck_button(parent, text=_("BTN_FIRE_PULSE"), command=_fire).grid(row=0, column=2, sticky="w", padx=8)

        if has_contact_gate:
            ttk.Label(
                parent, text=_("HELP_WELD_CONTACT_GATE"),
                foreground="gray", wraplength=380, justify="left",
            ).grid(row=1, column=0, columnspan=3, sticky="w", padx=4, pady=(4, 4))
        ttk.Label(
            parent, text=_("HELP_WELD_RESOLUTION"),
            foreground="gray", wraplength=380, justify="left",
        ).grid(row=2, column=0, columnspan=3, sticky="w", padx=4, pady=(0, 4))
        ttk.Label(
            parent, text=_("HELP_WELD_MAX_DURATION"),
            foreground="gray", wraplength=380, justify="left",
        ).grid(row=3, column=0, columnspan=3, sticky="w", padx=4, pady=(0, 4))

    def _build_spot_welder_panel(self, parent):
        self._build_weld_pulse_panel(parent, CAN_ID_SPOT_WELD_CMD, has_contact_gate=True)

    def _build_no_handler_panel(self, parent, help_key):
        # Shared by Conformal Coating and Press-Fit Inserter - both tool
        # IDs exist purely for identification, their own actuator and
        # sensor live on the robot's own mainboard rather than this
        # board, so there's no CAN handler at all to test here. See
        # TOOLS.TXT for the full reasoning.
        ttk.Label(
            parent, text=_(help_key),
            foreground="gray", wraplength=380, justify="left",
        ).grid(row=0, column=0, sticky="w", padx=4, pady=8)

    def _build_uv_curing_panel(self, parent):
        # UV Curing (0x1D0) has the same 250ms comms-loss watchdog as the
        # laser (both share TIM1_CH1) - see _build_laser_panel above for
        # the identical Active-checkbox/keepalive pattern this mirrors. A
        # plain one-shot Send would auto-extinguish ~250ms after every
        # click with no indication why, since the firmware cuts power the
        # moment this stops resending.
        power = tk.IntVar(value=0)
        active = tk.BooleanVar(value=False)

        ttk.Label(parent, text=_("LBL_POWER_0_255")).grid(row=0, column=0, sticky="w", padx=4, pady=4)
        power_scale = ttk.Scale(parent, from_=0, to=255, variable=power, orient="horizontal", length=160)
        power_scale.grid(row=0, column=1, sticky="w", padx=4)
        power_label = ttk.Label(parent, text="0")
        power_label.grid(row=0, column=2, sticky="w")
        power_scale.config(command=lambda v: power_label.config(text=str(int(float(v)))))

        def _send():
            self.bus.send(CAN_ID_UV_CURING_CMD, bytes([max(0, min(255, power.get()))]))

        def _toggle():
            # No *_ catch-all here (there used to be one) - this is only
            # ever wired up as a ttk widget's own command= callback, which
            # Tk always invokes with zero arguments, never as a .bind()
            # handler (which would pass an event). A bare *_ parameter
            # would otherwise shadow tester_config._ (the translation
            # function every _("...") call below actually needs) with
            # this callback's own empty args tuple for the entire body of
            # this function - every _(...) call inside would then raise
            # TypeError: 'tuple' object is not callable the moment this
            # runs, silently swallowed by Tkinter's own callback exception
            # handler (a traceback printed to stderr, nothing more) rather
            # than crashing outright - which meant clicking this "Active"
            # checkbox appeared to do nothing at all: the exception fires
            # on this function's very first _(...) call, before
            # _start_keepalive ever runs, so no keepalive is ever armed
            # and no CAN frame for this control ever gets sent. Confirmed
            # empirically with a real ttk.Checkbutton.invoke() before this
            # fix (raised exactly that TypeError), and confirmed fixed
            # after (keepalive registers, a real frame is sent).
            if active.get():
                self.log(_("LOG_UV_CURING_POWER", power=power.get()))
                self._start_keepalive("uvcuring", 150, _send, on_failure=lambda: active.set(False))
            else:
                self._stop_keepalive("uvcuring")
                power.set(0)
                _send()
                self.log(_("LOG_UV_CURING_STOPPED"))

        ttk.Checkbutton(parent, text=_("LBL_ACTIVE_250MS_WATCHDOG"),
                         variable=active, command=_toggle).grid(row=1, column=0, columnspan=3, sticky="w", padx=4, pady=4)

    def _build_hotair_rework_panel(self, parent):
        setpoint = tk.IntVar(value=0)
        blower = tk.IntVar(value=0)
        active = tk.BooleanVar(value=False)
        temp_var = tk.StringVar(value="-- °C")

        ttk.Label(parent, text=_("LBL_SETPOINT_TEMPERATURE")).grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Spinbox(parent, from_=0, to=SETPOINT_MAX_C, textvariable=setpoint, width=6).grid(row=0, column=1, sticky="w", padx=4)

        ttk.Label(parent, text=_("LBL_BLOWER_0_255")).grid(row=1, column=0, sticky="w", padx=4, pady=4)
        blower_scale = ttk.Scale(parent, from_=0, to=255, variable=blower, orient="horizontal", length=160)
        blower_scale.grid(row=1, column=1, sticky="w", padx=4)
        blower_label = ttk.Label(parent, text="0")
        blower_label.grid(row=1, column=2, sticky="w")
        blower_scale.config(command=lambda v: blower_label.config(text=str(int(float(v)))))

        def _send_setpoint():
            temp = max(0, min(SETPOINT_MAX_C, self._safe_int(setpoint, 0)))
            blow = max(0, min(255, blower.get()))
            self.bus.send(CAN_ID_HOTAIR_CMD, struct.pack(">H", temp) + bytes([blow]))

        def _toggle():
            # No *_ catch-all here (there used to be one) - this is only
            # ever wired up as a ttk widget's own command= callback, which
            # Tk always invokes with zero arguments, never as a .bind()
            # handler (which would pass an event). A bare *_ parameter
            # would otherwise shadow tester_config._ (the translation
            # function every _("...") call below actually needs) with
            # this callback's own empty args tuple for the entire body of
            # this function - every _(...) call inside would then raise
            # TypeError: 'tuple' object is not callable the moment this
            # runs, silently swallowed by Tkinter's own callback exception
            # handler (a traceback printed to stderr, nothing more) rather
            # than crashing outright - which meant clicking this "Active"
            # checkbox appeared to do nothing at all: the exception fires
            # on this function's very first _(...) call, before
            # _start_keepalive ever runs, so no keepalive is ever armed
            # and no CAN frame for this control ever gets sent. Confirmed
            # empirically with a real ttk.Checkbutton.invoke() before this
            # fix (raised exactly that TypeError), and confirmed fixed
            # after (keepalive registers, a real frame is sent).
            if active.get():
                self.log(_("LOG_HOTAIR_ACTIVE", temp=self._safe_int(setpoint, 0), blower=blower.get()))
                self._start_keepalive("hotair", 150, _send_setpoint, on_failure=lambda: active.set(False))
            else:
                self._stop_keepalive("hotair")
                self.bus.send(CAN_ID_HOTAIR_CMD, struct.pack(">H", 0) + bytes([0]))
                self.log(_("LOG_HOTAIR_STOPPED"))

        ttk.Checkbutton(parent, text=_("LBL_ACTIVE_250MS_WATCHDOG"),
                         variable=active, command=_toggle).grid(row=2, column=0, columnspan=3, sticky="w", padx=4, pady=4)

        ttk.Separator(parent, orient="horizontal").grid(row=3, column=0, columnspan=3, sticky="ew", pady=6)
        ttk.Label(parent, text=_("LBL_LIVE_TEMPERATURE")).grid(row=4, column=0, sticky="w", padx=4, pady=2)
        ttk.Label(parent, textvariable=temp_var, font=("", 11, "bold")).grid(row=4, column=1, sticky="w")
        ttk.Label(
            parent, text=_("HELP_HOTAIR_SHARED_LOOP"),
            foreground="gray", wraplength=380, justify="left",
        ).grid(row=5, column=0, columnspan=3, sticky="w", padx=4, pady=(4, 4))
        graph_frame = ttk.Frame(parent)
        graph_frame.grid(row=6, column=0, columnspan=3, sticky="w", padx=4)
        add_temp_point = self._create_live_graph(graph_frame, y_max=450, label="hot_air_nozzle_temp_c")

        def _on_telemetry(data):
            if len(data) < 2:
                return
            temp = struct.unpack(">H", data[0:2])[0]
            self.root.after(0, lambda: temp_var.set(f"{temp} °C"))
            self.root.after(0, lambda: add_temp_point(temp))

        # Same telemetry ID the soldering iron's own panel already
        # listens to - shared physical loop, shared wire format. Only
        # this panel is ever active at once (a board can only have one
        # tool ID configured), so both panels registering their own
        # handler on the same ID never actually collides in practice.
        self.bus.register(CAN_ID_SOLDER_TELEMETRY, _on_telemetry)

    def _build_crimping_actuator_panel(self, parent, tool_id, tool_name):
        ttk.Label(
            parent, text=_("HELP_CRIMPING_NEEDS_EXPANSION"),
            foreground="#b35900", wraplength=380, justify="left",
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=4, pady=(4, 8))
        self._build_motion_panel(parent, tool_id, tool_name, cmd_id=CAN_ID_CRIMPING_CMD, start_row=1)

    def _build_ultrasonic_welder_panel(self, parent):
        self._build_weld_pulse_panel(parent, CAN_ID_ULTRASONIC_WELD_CMD, has_contact_gate=False)

    def _build_flying_probe_panel(self, parent):
        # 2 independent reading paths, per EXPANSION.TXT and TOOLS.TXT -
        # both shown here, since the board doesn't tell the host which
        # one it's actually using (it works the same way regardless of
        # whether an ADS1115 is direct-wired or relayed through the
        # slave chip - see firmware_can_flyingprobe.c's own header
        # comment).
        basic_var = tk.StringVar(value="-- (waiting for 0x243)")
        config_hex = tk.StringVar(value="8583")
        result_var = tk.StringVar(value="-- (not read yet)")

        ttk.Label(parent, text=_("LBL_FLYING_PROBE_BASIC"), font=("", 10, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=4, pady=(4, 2))
        ttk.Label(parent, textvariable=basic_var).grid(row=1, column=0, columnspan=2, sticky="w", padx=4, pady=(0, 8))

        ttk.Separator(parent, orient="horizontal").grid(row=2, column=0, columnspan=3, sticky="ew", pady=4)
        ttk.Label(parent, text=_("LBL_FLYING_PROBE_ADVANCED"), font=("", 10, "bold")).grid(
            row=3, column=0, columnspan=3, sticky="w", padx=4, pady=(4, 2))
        ttk.Label(
            parent, text=_("HELP_ADS1115_RAW_CONFIG"),
            foreground="gray", wraplength=380, justify="left",
        ).grid(row=4, column=0, columnspan=3, sticky="w", padx=4, pady=(0, 4))

        ttk.Label(parent, text=_("LBL_ADS1115_CONFIG_HEX")).grid(row=5, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(parent, textvariable=config_hex, width=8).grid(row=5, column=1, sticky="w", padx=4)

        def _send_config():
            try:
                value = int(config_hex.get(), 16) & 0xFFFF
            except ValueError:
                messagebox.showerror(_("TITLE_INVALID_VALUE"), _("MSG_INVALID_HEX"))
                return
            self.bus.send(CAN_ID_ADS1115_CONFIG, struct.pack(">H", value))
            self.log(_("LOG_ADS1115_CONFIG_SENT", value=f"0x{value:04X}"))

        self._new_deck_button(parent, text=_("BTN_SEND"), command=_send_config).grid(row=5, column=2, sticky="w", padx=8)

        def _trigger():
            self.bus.send(CAN_ID_ADS1115_TRIGGER, b"")
            self.log(_("LOG_ADS1115_TRIGGERED"))

        self._new_deck_button(parent, text=_("BTN_TRIGGER_CONVERSION"), command=_trigger).grid(row=6, column=0, sticky="w", padx=4, pady=4)

        def _read():
            def _done(response):
                if response is None or len(response) < 2:
                    result_var.set(_("LBL_NO_RESPONSE"))
                    self.log(_("LOG_ADS1115_READ_NO_RESPONSE"))
                    return
                raw = struct.unpack(">h", response[0:2])[0]
                result_var.set(f"{raw} (raw counts)")
                self.log(_("LOG_ADS1115_RESULT", raw=raw))

            self._query_async(CAN_ID_ADS1115_RESULT, lambda: self.bus.send(CAN_ID_ADS1115_RESULT, b""), _done)

        self._new_deck_button(parent, text=_("BTN_READ_RESULT"), command=_read).grid(row=6, column=1, sticky="w", padx=4)
        ttk.Label(parent, textvariable=result_var).grid(row=7, column=0, columnspan=2, sticky="w", padx=4, pady=(2, 4))

        def _on_basic_telemetry(data):
            if len(data) < 2:
                return
            raw = struct.unpack(">H", data[0:2])[0]
            self.root.after(0, lambda: basic_var.set(f"{raw} (raw ADC counts, onboard channel)"))

        self.bus.register(CAN_ID_FLYING_PROBE_BASIC, _on_basic_telemetry)

    def _build_paste_jetting_panel(self, parent):
        channel = tk.IntVar(value=0)
        freq = tk.IntVar(value=100)
        duty = tk.IntVar(value=50)
        pulse_ms = tk.IntVar(value=10)

        ttk.Label(parent, text=_("LBL_PWM_CHANNEL_0_3")).grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Spinbox(parent, from_=0, to=3, textvariable=channel, width=4).grid(row=0, column=1, sticky="w", padx=4)

        ttk.Label(parent, text=_("LBL_FREQUENCY_HZ")).grid(row=1, column=0, sticky="w", padx=4, pady=4)
        ttk.Spinbox(parent, from_=1, to=65535, textvariable=freq, width=8).grid(row=1, column=1, sticky="w", padx=4)

        def _configure():
            ch = max(0, min(3, self._safe_int(channel, 0)))
            hz = max(1, min(65535, self._safe_int(freq, 100)))
            self.bus.send(CAN_ID_PASTE_JETTING_CONFIG, bytes([ch]) + struct.pack(">H", hz))
            self.log(_("LOG_PASTE_JETTING_CONFIGURED", channel=ch, freq=hz))

        self._new_deck_button(parent, text=_("BTN_CONFIGURE"), command=_configure).grid(row=1, column=2, sticky="w", padx=8)

        ttk.Separator(parent, orient="horizontal").grid(row=2, column=0, columnspan=3, sticky="ew", pady=6)
        ttk.Label(parent, text=_("LBL_DUTY_PERCENT")).grid(row=3, column=0, sticky="w", padx=4, pady=4)
        ttk.Spinbox(parent, from_=0, to=100, textvariable=duty, width=6).grid(row=3, column=1, sticky="w", padx=4)
        ttk.Label(parent, text=_("LBL_PULSE_DURATION_MS")).grid(row=4, column=0, sticky="w", padx=4, pady=4)
        ttk.Spinbox(parent, from_=1, to=255, textvariable=pulse_ms, width=6).grid(row=4, column=1, sticky="w", padx=4)

        def _fire():
            # _require_int, not _safe_int, for the same reason as the weld
            # pulse panel's own _fire above - this dispenses a real paste
            # pulse immediately, so an empty field mid-edit must abort the
            # send rather than quietly firing with a phantom default duty/
            # duration the user never entered.
            ch_raw = self._require_int(channel)
            duty_raw = self._require_int(duty)
            ms_raw = self._require_int(pulse_ms)
            if ch_raw is None or duty_raw is None or ms_raw is None:
                return
            ch = max(0, min(3, ch_raw))
            d = max(0, min(100, duty_raw))
            ms = max(1, min(255, ms_raw))
            if not self._confirm_physical_action():
                return
            self.bus.send(CAN_ID_PASTE_JETTING_PULSE, bytes([ch, d, ms]))
            self.log(_("LOG_PASTE_JETTING_FIRED", channel=ch, duty=d, ms=ms))

        self._new_deck_button(parent, text=_("BTN_FIRE_PULSE"), command=_fire).grid(row=4, column=2, sticky="w", padx=8)

    def _build_thermal_inspection_panel(self, parent):
        # Captured now, at panel-build time - see _tool_panel_generation's
        # own comment in tester_gui_core.py. _read_frame below (a
        # multi-second, 48-chunk background read) compares against this
        # fixed snapshot rather than the live self._tool_panel_generation
        # on every check, so it notices being torn down (Detect run again,
        # a different tool selected, disconnect) even if several rebuilds
        # happen in a row.
        panel_gen = self._tool_panel_generation
        status_var = tk.StringVar(value=_("LBL_NOT_TRIGGERED_YET"))
        # The canvas is the 32x24 resolution of the MLX90640/90642; the
        # MLX90641 (16x12) is drawn on it in 2x2 blocks (see _read_frame).
        GRID_W, GRID_H, CELL = 32, 24, 8
        canvas = tk.Canvas(parent, width=GRID_W * CELL, height=GRID_H * CELL, bg="black", highlightthickness=1)
        canvas.grid(row=2, column=0, columnspan=3, padx=4, pady=8)
        cells = [[canvas.create_rectangle(x * CELL, y * CELL, (x + 1) * CELL, (y + 1) * CELL,
                                            fill="#000030", outline="")
                  for x in range(GRID_W)] for y in range(GRID_H)]

        def _temp_to_color(centi_c):
            # Simple blue->red heat gradient, clamped to a 0-100°C
            # display range - wide enough to be useful for PCB
            # inspection without needing a user-adjustable scale for a
            # first pass at this panel.
            t = max(0, min(100, centi_c / 100.0))
            frac = t / 100.0
            r = int(255 * frac)
            b = int(255 * (1 - frac))
            g = int(128 * (1 - abs(frac - 0.5) * 2))
            return f"#{r:02x}{g:02x}{b:02x}"

        def _trigger():
            self.bus.send(CAN_ID_THERMAL_TRIGGER, b"")
            status_var.set(_("LBL_CAPTURE_TRIGGERED"))
            self.log(_("LOG_THERMAL_TRIGGERED"))

        self._new_deck_button(parent, text=_("BTN_TRIGGER_CAPTURE"), command=_trigger).grid(row=0, column=0, sticky="w", padx=4, pady=4)

        def _check_status():
            def _done(response):
                if response is None or len(response) < 1:
                    status_var.set(_("LBL_NO_RESPONSE"))
                    return
                code = response[0]
                labels = {0x00: _("LBL_STATUS_IDLE"), 0x01: _("LBL_STATUS_BUSY"),
                          0x02: _("LBL_STATUS_READY"), 0xFF: _("LBL_STATUS_ERROR")}
                status_var.set(labels.get(code, f"0x{code:02X}"))
                self.log(_("LOG_THERMAL_STATUS", status=status_var.get()))

            self._query_async(CAN_ID_THERMAL_STATUS, lambda: self.bus.send(CAN_ID_THERMAL_STATUS, b""), _done)

        self._new_deck_button(parent, text=_("BTN_CHECK_STATUS"), command=_check_status).grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(parent, textvariable=status_var).grid(row=1, column=0, columnspan=2, sticky="w", padx=4, pady=(0, 4))

        def _paint_cell(row, col, color, gen):
            # Runs on the Tkinter main thread via root.after below - the
            # panel (and this very canvas) may have been torn down by a
            # rebuild that started after this specific update was already
            # queued, so both the generation check and winfo_exists() are
            # needed: the generation check catches "torn down, but a new
            # thermal panel with a live canvas of its own now exists"
            # (canvas would still exist, just be the WRONG one), and
            # winfo_exists() catches "torn down, no thermal panel at all
            # right now" (this exact canvas object is gone).
            if gen != panel_gen or not canvas.winfo_exists():
                return
            canvas.itemconfig(cells[row][col], fill=color)

        def _read_frame():
            # Runs on a background thread. Asks which sensor is fitted (0x1A7)
            # so the right grid is read and painted, waits until the capture
            # is ready (0x251; the firmware does not answer chunk requests
            # before that), then reads every chunk. A chunk is 4 consecutive
            # frames, collected by one persistent waiter, and a lost chunk
            # leaves its 16 pixels blank instead of shifting the rest of the
            # image. If the user switches away mid-read (Detect again, another
            # tool, disconnect) the panel generation check stops the querying
            # and the painting.
            bus = self.bus
            width, height, chunk_count = 32, 24, 48
            variant = bus.wait_for_one(CAN_ID_MLX_VARIANT_RESP, timeout=0.5,
                                       send_after_register=lambda: bus.send(CAN_ID_MLX_VARIANT_RESP, b""))
            if variant:
                grid = protocol.thermal_grid(variant[0])
                if grid is None:
                    self.root.after(0, lambda: status_var.set(MLX_SENSOR_VARIANTS[0]))
                    return
                width, height, chunk_count = grid
            ready = False
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline and self._tool_panel_generation == panel_gen:
                status = bus.wait_for_one(CAN_ID_THERMAL_STATUS, timeout=0.25,
                                          send_after_register=lambda: bus.send(CAN_ID_THERMAL_STATUS, b""))
                if status and status[0] == protocol.THERMAL_STATUS_READY:
                    ready = True
                    break
                if status and status[0] == 0xFF:
                    break
            if not ready:
                self.root.after(0, lambda: status_var.set(_("LBL_STATUS_BUSY")))
                return
            chunks = {}
            for chunk_idx in range(chunk_count):
                if self._tool_panel_generation != panel_gen:
                    return
                for _attempt in range(2):
                    frames = bus.wait_for_n(
                        CAN_ID_THERMAL_CALIB_CHUNK, protocol.THERMAL_CHUNK_FRAMES, timeout=0.3,
                        send_after_register=lambda ci=chunk_idx: bus.send(CAN_ID_THERMAL_CALIB_CHUNK_REQ, bytes([ci])))
                    decoded = protocol.decode_thermal_chunk(frames)
                    if decoded is not None:
                        chunks[chunk_idx] = decoded
                        break
            scale = GRID_W // width  # a 16x12 image fills the 32x24 canvas with 2x2 blocks
            for pixel_idx, value in enumerate(protocol.thermal_pixels(chunks, chunk_count)):
                row, col = divmod(pixel_idx, width)
                color = "#202020" if value is None else _temp_to_color(value)
                for dy in range(scale):
                    for dx in range(scale):
                        self.root.after(0, lambda r=row * scale + dy, c=col * scale + dx, col_=color: _paint_cell(r, c, col_, panel_gen))
            if self._tool_panel_generation == panel_gen:
                self.log(_("LOG_THERMAL_FRAME_READ"))

        self._new_deck_button(parent, text=_("BTN_READ_THERMAL_IMAGE"), command=lambda: threading.Thread(target=_read_frame, daemon=True).start()
                   ).grid(row=0, column=2, sticky="w", padx=8)
        ttk.Label(
            parent, text=_("HELP_THERMAL_READ_SLOW"),
            foreground="gray", wraplength=380, justify="left",
        ).grid(row=3, column=0, columnspan=3, sticky="w", padx=4, pady=(4, 4))

