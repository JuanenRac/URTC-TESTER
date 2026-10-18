# =============================================================================
# URTC Tester - bit rate scan, saved settings, the stop for everything, confirmations and the monitor filter
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""No board is needed: the SLCAN adapter, the bus and the Tk host are stand-ins."""
import re
import struct
import time
import unittest
from pathlib import Path
from unittest import mock

import advanced_protocol as protocol
import tester_config
from tester_bus_monitor import FrameFilter
from tester_config import (
    CAN_ID_ACTIVE_TOOL_RESP, CAN_ID_CRIMPING_CMD, CAN_ID_PASTE_JETTING_PULSE, CAN_ID_QUERY_ACTIVE_TOOL, CAN_ID_SPOT_WELD_CMD, SLCAN_BITRATES,
)
import tester_gui_core
from tester_gui_core import README_SUFFIXES, scan_bitrates

try:
    from PySide6.QtCore import QCoreApplication
    import qt_tester
except ImportError:  # PySide6 is not installed
    qt_tester = None

ROOT = Path(__file__).resolve().parent.parent
CODES = dict(SLCAN_BITRATES)


class FakeSLCAN:
    """An adapter on a bus whose speed is `bus_bitrate` ("500 kbit/s"), with `traffic` frames always flowing and a board that answers a query when `board` is True."""

    instances = []
    bus_bitrate = "250 kbit/s"
    traffic = True
    board = True

    def __init__(self, port, log=None):
        self.port = port
        self.opened = None
        self.listen_only = None
        self.sent = []
        self.closed = False
        FakeSLCAN.instances.append(self)

    def open_channel(self, code, listen_only=False):
        self.opened = code
        self.listen_only = listen_only

    def _on_the_right_rate(self):
        return self.opened == CODES[FakeSLCAN.bus_bitrate]

    def send_frame(self, can_id, data):
        assert not self.listen_only, "a listen-only channel must never transmit"
        self.sent.append(can_id)

    def read_frame(self, timeout=0.05):
        if not self._on_the_right_rate():
            return None
        if self.sent and FakeSLCAN.board and self.sent[-1] == CAN_ID_QUERY_ACTIVE_TOOL:
            self.sent.append(0)
            return (CAN_ID_ACTIVE_TOOL_RESP, bytes([5, 0, 0, 0]))
        if FakeSLCAN.traffic and not self.sent:
            return (0x123, b"\x01")
        return None

    def close(self):
        self.closed = True


def _scan(**overrides):
    FakeSLCAN.instances = []
    kwargs = dict(listen_window=0.05, answer_window=0.1, pause=0)
    kwargs.update(overrides)
    return scan_bitrates("COM1", FakeSLCAN, SLCAN_BITRATES, **kwargs)


class BitrateScanTests(unittest.TestCase):
    def setUp(self):
        FakeSLCAN.bus_bitrate, FakeSLCAN.traffic, FakeSLCAN.board = "250 kbit/s", True, True

    def test_the_search_on_a_live_bus_only_listens_until_it_finds_the_rate(self):
        self.assertEqual(_scan(), "250 kbit/s")
        wrong_rates = [i for i in FakeSLCAN.instances if i.opened != CODES["250 kbit/s"]]
        self.assertTrue(wrong_rates)
        for adapter in wrong_rates:
            self.assertTrue(adapter.listen_only, "a wrong rate must never be opened for transmitting")
            self.assertEqual(adapter.sent, [])
        self.assertTrue(all(i.closed for i in FakeSLCAN.instances))

    def test_a_live_bus_where_nobody_answers_is_never_probed_blind(self):
        FakeSLCAN.board = False
        self.assertIsNone(_scan())
        self.assertTrue(all(i.listen_only or i.opened == CODES["250 kbit/s"] for i in FakeSLCAN.instances))
        wrong_active = [i for i in FakeSLCAN.instances if not i.listen_only and i.opened != CODES["250 kbit/s"]]
        self.assertEqual(wrong_active, [])

    def test_an_idle_bus_falls_back_to_asking_at_each_rate_and_says_so(self):
        FakeSLCAN.traffic = False
        said = []
        self.assertEqual(_scan(on_active_phase=lambda: said.append(True)), "250 kbit/s")
        self.assertEqual(said, [True])

    def test_nothing_found_returns_none(self):
        FakeSLCAN.traffic, FakeSLCAN.board = False, False
        self.assertIsNone(_scan())


class SmallFixesTests(unittest.TestCase):
    def test_the_readme_menu_knows_chinese_japanese_and_portuguese(self):
        for language, suffix in (("chinese", "_zho"), ("japanese", "_jpn"), ("portuguese", "_por"), ("spanish", "_spa")):
            self.assertEqual(README_SUFFIXES[language], suffix)
            self.assertTrue((ROOT / f"README{suffix}.md").is_file())

    def test_the_window_never_asks_for_more_than_the_screen_has(self):
        self.assertEqual(tester_config.fit_to_screen(1360, 1075, 1366, 768), (1346, 688))
        self.assertEqual(tester_config.fit_to_screen(1360, 1075, 2560, 1440), (1360, 1075))
        self.assertEqual(tester_config.fit_to_screen(1360, 1075, 100, 100), (320, 240))

    def test_transport_deadlines_do_not_use_the_wall_clock(self):
        source = (ROOT / "tester_transports.py").read_text(encoding="utf-8")
        self.assertNotIn("time.time()", source)

    def test_the_frame_export_is_written_as_ascii(self):
        source = (ROOT / "tester_common_panels.py").read_text(encoding="utf-8")
        self.assertIn('open(path, "w", encoding="ascii")', source)


class FrameFilterTests(unittest.TestCase):
    def test_ids_are_read_as_hex_and_unreadable_tokens_are_ignored(self):
        frame_filter = FrameFilter()
        frame_filter.set_ids("1A0, 0x110 zz 7F8 FFFF")
        self.assertEqual(frame_filter.ids, {0x1A0, 0x110, 0x7F8})
        self.assertTrue(frame_filter.accept(0x1A0, b"1"))
        self.assertFalse(frame_filter.accept(0x111, b"1"))
        frame_filter.set_ids("   ")
        self.assertIsNone(frame_filter.ids)
        self.assertTrue(frame_filter.accept(0x111, b"1"))

    def test_only_changes_hides_repeats_per_id(self):
        frame_filter = FrameFilter()
        frame_filter.only_changes = True
        self.assertTrue(frame_filter.accept(0x111, b"\x01"))
        self.assertFalse(frame_filter.accept(0x111, b"\x01"))
        self.assertTrue(frame_filter.accept(0x112, b"\x01"), "another ID has its own history")
        self.assertTrue(frame_filter.accept(0x111, b"\x02"))
        frame_filter.reset()
        self.assertTrue(frame_filter.accept(0x111, b"\x02"))


class StopEverythingTests(unittest.TestCase):
    # minimum payload length the firmware needs before it reads each command at all
    MIN_DLC = {0x170: 6, 0x130: 2, 0x1E0: 3, 0x160: 2, 0x140: 2, 0x1D0: 1, 0x173: 1, 0x1B0: 1, 0x120: 5, 0x1F0: 5}

    def test_every_off_frame_is_long_enough_for_the_firmware_and_all_zero_effect(self):
        frames = protocol.all_off_frames()
        self.assertEqual({can_id for can_id, _data in frames}, set(self.MIN_DLC))
        for can_id, data in frames:
            self.assertGreaterEqual(len(data), self.MIN_DLC[can_id], hex(can_id))
        by_id = dict(frames)
        self.assertEqual(by_id[0x170][:2], bytes(2), "hotend heater to 0")
        self.assertEqual(by_id[0x120], bytes(5), "0 steps is the order to stop")

    def test_the_hotend_fan_is_left_running(self):
        self.assertNotIn(tester_config.CAN_ID_3DP_HOTEND_FAN_CMD, {can_id for can_id, _d in protocol.all_off_frames()})

    def test_the_classic_window_stops_everything_and_keeps_going_when_a_send_fails(self):
        sent, stopped, logs = [], [], []

        class Bus:
            def send(self, can_id, data):
                if can_id == 0x130:
                    raise OSError("adapter gone")
                sent.append(can_id)

        class Var:
            value = True

            def set(self, value):
                self.value = value

        fake = mock.Mock()
        fake.bus, fake.transport = Bus(), object()
        fake._keepalive_jobs = {"solder": 1, "custom_frame": 2}
        fake._stop_keepalive = stopped.append
        fake.custom_periodic_var = Var()
        fake._current_tool_id = None
        fake.log = logs.append
        tester_gui_core.TesterGUI.stop_all_outputs(fake)
        self.assertEqual(len(sent), len(protocol.all_off_frames()) - 1)
        self.assertEqual(sorted(stopped), ["custom_frame", "solder"])
        self.assertFalse(fake.custom_periodic_var.value)
        self.assertTrue(logs)

    def test_it_does_nothing_without_a_connection(self):
        fake = mock.Mock()
        fake.bus, fake.transport = None, None
        tester_gui_core.TesterGUI.stop_all_outputs(fake)
        fake.log.assert_not_called()


class LanguageFilesTests(unittest.TestCase):
    NEW_KEYS = (
        "LOG_AUTODETECT_ACTIVE_PHASE", "QT_EXTRUDER_KEEPALIVE_NOTE", "VAL_NOTHING_SENT_YET", "VAL_NOT_QUERIED_YET", "VAL_NONE_YET", "TITLE_RAW_BUS_MONITOR",
        "LBL_BUS_STATS_IDLE", "LBL_BUS_STATS", "LOG_SELFTEST_TESTING", "LOG_SELFTEST_ACTIVE_TOOL", "LOG_SELFTEST_VERSION", "LOG_HW_NOTE_DIFFERENT",
        "TAB_TOOL_CONTROLS", "MSG_NO_TOOL_FOR_JUMPERS", "TITLE_CONFIRM_PHYSICAL_ACTION_Q", "MSG_CONFIRM_PHYSICAL_ACTION", "LBL_FILTER_IDS",
        "BTN_ONLY_CHANGES", "LOG_STOP_ALL_OUTPUTS",
    )

    def _load(self):
        files = sorted((ROOT / "language").glob("*.lng"))
        self.assertEqual(len(files), 8)
        loaded = {}
        for path in files:
            entries = {}
            for line in path.read_text(encoding="utf-8").splitlines():
                if line and not line.startswith("#") and "=" in line:
                    key, _sep, value = line.partition("=")
                    entries[key.strip()] = value
            loaded[path.stem] = entries
        return loaded

    def test_the_eight_files_have_the_same_keys(self):
        loaded = self._load()
        reference = set(loaded["english"])
        for name, entries in loaded.items():
            self.assertEqual(set(entries), reference, name)

    def test_the_new_texts_exist_everywhere_with_the_same_placeholders(self):
        loaded = self._load()
        for key in self.NEW_KEYS:
            wanted = sorted(re.findall(r"\{(\w+)", loaded["english"][key]))
            for name, entries in loaded.items():
                self.assertIn(key, entries, f"{name} lacks {key}")
                self.assertTrue(entries[key].strip(), f"{name} has an empty {key}")
                self.assertEqual(sorted(re.findall(r"\{(\w+)", entries[key])), wanted, f"{name}/{key}")

    def test_every_key_the_code_uses_exists(self):
        english = self._load()["english"]
        used = set()
        for path in list(ROOT.glob("*.py")):
            used |= set(re.findall(r"""\b_\(\s*"([A-Z][A-Z0-9_]+)"?""", path.read_text(encoding="utf-8")))
            used |= set(re.findall(r"""uiText\(\s*"([A-Z][A-Z0-9_]+)""", path.read_text(encoding="utf-8")))
        used |= set(re.findall(r"""uiText\("([A-Z][A-Z0-9_]+)"\)""", (ROOT / "assets" / "qml" / "TesterDeck.qml").read_text(encoding="utf-8")))
        missing = sorted(key for key in used if key not in english and not key.startswith("QT_") and key != "GREETING")  # GREETING is the example in a docstring
        self.assertEqual(missing, [])


class FakeBus:
    def __init__(self):
        self.sent = []

    def send(self, can_id, data):
        self.sent.append((can_id, bytes(data)))


def _tk_root():
    import tkinter as tk
    try:
        root = tk.Tk()
    except tk.TclError:
        return None
    root.withdraw()
    return root


class ConfirmationTests(unittest.TestCase):
    """Weld pulses, paste pulses and the crimp ask before they transmit, as the Qt Quick deck does for every physical action."""

    @classmethod
    def setUpClass(cls):
        cls.root = _tk_root()  # one root for the whole class: creating several in a row is unreliable

    @classmethod
    def tearDownClass(cls):
        if cls.root is not None:
            cls.root.destroy()

    def setUp(self):
        if self.root is None:
            self.skipTest("no display for Tk")
        from tkinter import ttk
        from tester_panel_helpers import PanelHelpersMixin
        from tester_tool_panels import ToolPanelsMixin

        class Host(ToolPanelsMixin, PanelHelpersMixin):
            def __init__(inner, root):
                inner.root = root
                inner.bus = FakeBus()
                inner.logs = []

            def log(inner, text):
                inner.logs.append(text)

            def _new_deck_button(inner, parent, text, command, **_kw):
                return ttk.Button(parent, text=text, command=command)

        self.host = Host(self.root)
        self.frame = ttk.Frame(self.root)

    def tearDown(self):
        if self.root is not None:
            self.frame.destroy()

    def _press(self, label_key):
        wanted = tester_config._(label_key)
        stack = [self.frame]
        while stack:
            widget = stack.pop()
            stack.extend(widget.winfo_children())
            try:
                if widget.cget("text") == wanted and widget.winfo_class() == "TButton":
                    widget.invoke()
                    return
            except Exception:
                continue
        self.fail(f"no button {label_key}")

    def _check(self, build, button, expected_id):
        build()
        for answer, sends in ((False, 0), (True, 1)):
            self.host.bus.sent.clear()
            with mock.patch("tester_panel_helpers.messagebox.askyesno", return_value=answer) as ask:
                self._press(button)
            self.assertEqual(ask.call_count, 1)
            self.assertEqual(len(self.host.bus.sent), sends, f"answer={answer}")
            if sends:
                self.assertEqual(self.host.bus.sent[0][0], expected_id)

    def test_spot_weld_pulse(self):
        self._check(lambda: self.host._build_weld_pulse_panel(self.frame, CAN_ID_SPOT_WELD_CMD, True), "BTN_FIRE_PULSE", CAN_ID_SPOT_WELD_CMD)

    def test_paste_pulse(self):
        self._check(lambda: self.host._build_paste_jetting_panel(self.frame), "BTN_FIRE_PULSE", CAN_ID_PASTE_JETTING_PULSE)

    def test_crimp(self):
        self._check(lambda: self.host._build_motion_panel(self.frame, 21, "Crimp", cmd_id=CAN_ID_CRIMPING_CMD, start_row=1), "BTN_MOVE", CAN_ID_CRIMPING_CMD)

    def test_a_plain_stepper_move_is_not_asked_about(self):
        self.host._build_motion_panel(self.frame, 1, "Stepper", start_row=1)
        with mock.patch("tester_panel_helpers.messagebox.askyesno", return_value=False) as ask:
            self._press("BTN_MOVE")
        ask.assert_not_called()
        self.assertEqual(len(self.host.bus.sent), 1)


@unittest.skipIf(qt_tester is None, "PySide6 is not available")
class QtDeckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        patcher = mock.patch.object(qt_tester, "save_config", return_value=True)
        self.save = patcher.start()
        self.addCleanup(patcher.stop)
        self.sent = []
        sent = self.sent

        class Transport:
            closed = False

            def send_frame(inner, can_id, data):
                sent.append((can_id, bytes(data)))

            def read_frame(inner, timeout=0.1):
                time.sleep(min(timeout, 0.01))
                return None

            def close(inner):
                inner.closed = True

        self.transport = Transport()
        self.bridge = qt_tester.TesterQtBridge()
        self.bridge._log = lambda text: None
        self.bridge._transport = self.transport
        self.bridge._listen_only = False
        self.bridge._require_profile = lambda allowed, action: True

    def test_every_sender_produces_the_frame_of_the_one_encoder(self):
        bridge = self.bridge
        bridge._selected_tool_id = 14
        bridge.fireWeldPulse("120")
        bridge.configurePasteJetting("2", "300")
        bridge.firePastePulse("1", "40", "9")
        bridge.sendAoi("strobe", "7")
        bridge.setElectromagnet(True)
        bridge.sendPrinterOneShot("hotend_fan", "128", "0")
        bridge.sendPrinterOneShot("extruder", "500", "200")
        self.assertEqual(self.sent, [
            protocol.weld_frame(14, 120),
            protocol.paste_config_frame(2, 300),
            protocol.paste_pulse_frame(1, 40, 9),
            protocol.aoi_frame("strobe", 7),
            protocol.magnet_frame(True),
            protocol.printer_frame("hotend_fan", 128, 0),
            protocol.printer_frame("extruder", 500, 200),
        ])

    def test_motion_goes_through_the_encoder_for_both_command_ids(self):
        bridge = self.bridge
        bridge._active_tool_id = bridge._selected_tool_id = 21
        bridge.sendMotion("reverse", "1000")
        bridge._active_tool_id = bridge._selected_tool_id = 1
        bridge.sendMotion("forward", "5")
        self.assertEqual(self.sent, [protocol.motion_frame(21, "reverse", 1000), protocol.motion_frame(1, "forward", 5)])

    def test_a_paste_pulse_of_zero_is_refused(self):
        self.bridge.firePastePulse("1", "40", "0")
        self.assertEqual(self.sent, [])

    def test_stop_all_sends_every_off_and_the_hotend_fan_is_not_among_them(self):
        self.bridge.stopAllOutputs()
        self.assertEqual(self.sent, protocol.all_off_frames())

    def test_stop_all_transmits_nothing_in_listen_only(self):
        self.bridge._listen_only = True
        self.bridge.stopAllOutputs()
        self.assertEqual(self.sent, [])

    def test_closing_the_deck_switches_everything_off(self):
        self.bridge.shutdownOutputs()
        self.assertEqual(self.sent, protocol.all_off_frames())

    def test_disconnecting_ends_a_telemetry_watch_instead_of_staying_stuck(self):
        bridge = self.bridge
        bridge._active_tool_id = bridge._selected_tool_id = 4
        bridge._require_telemetry_profile = lambda allowed: True
        bridge.watchTelemetry()
        deadline = time.monotonic() + 2
        while not bridge._busy and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(bridge._busy)
        bridge.toggleConnection()
        self.assertTrue(self.transport.closed)
        self.assertIsNone(bridge._transport)
        self.assertFalse(bridge._busy)

    def test_a_probe_in_progress_still_blocks_disconnecting(self):
        bridge = self.bridge
        bridge._busy = True
        bridge.toggleConnection()
        self.assertFalse(self.transport.closed)

    def test_the_bit_rate_is_remembered_and_used_to_open_the_channel(self):
        bridge = self.bridge
        bridge._transport = None
        bridge.selectBitrate("125 kbit/s")
        self.save.assert_called_with({"bitrate": "125 kbit/s"})
        bridge.selectBitrate("not a rate")
        self.assertEqual(bridge.selectedBitrate, "125 kbit/s")

        opened = []

        class Adapter:
            def __init__(inner, port, log=None):
                pass

            def open_channel(inner, code, listen_only=False):
                opened.append((code, listen_only))

        bridge._selected_port = "COM9"
        bridge._socketcan_ports = set()
        with mock.patch.object(qt_tester, "SLCAN", Adapter):
            bridge._connect_worker()
        self.assertEqual(opened, [(CODES["125 kbit/s"], False)])
        self.assertIn("125 kbit/s", bridge.bitrates)

    def test_the_bit_rate_cannot_change_while_connected(self):
        self.bridge.selectBitrate("10 kbit/s")
        self.assertEqual(self.bridge.selectedBitrate, "500 kbit/s")

    def test_the_port_is_remembered(self):
        bridge = self.bridge
        bridge._transport = None
        bridge._ports = ["COM3", "COM4"]
        bridge.selectPort("COM4")
        self.save.assert_called_with({"port": "COM4"})

    def test_a_thermal_fault_shows_in_the_probe_result(self):
        bridge = self.bridge
        logs = []
        bridge._log = logs.append
        bridge._on_probe_result(bytes([0, 0, 0, 0, 1, 0x01]), None, "")
        self.assertIn("THERMAL FAULT", bridge.activeTool)
        self.assertTrue(any(line.startswith("RESET_CAUSE") for line in logs))

    def test_the_firmware_patch_number_is_shown_when_the_board_sends_it(self):
        bridge = self.bridge
        logs = []
        bridge._log = logs.append
        version = bytes([0x00]) + struct.pack(">I", tester_config.THIS_HARDWARE_ID) + struct.pack(">H", 0) + bytes([3])
        bridge._version_patch_frame = bytes([0x00, 5, 0x01])
        bridge._on_probe_result(None, version, "")
        self.assertIn("v0.3.5", bridge._version)
        bridge._version_patch_frame = None
        bridge._on_probe_result(None, version, "")
        self.assertIn("v0.3 ", bridge._version)
        self.assertNotIn("v0.3.", bridge._version)


class FirmwareVersionTextTests(unittest.TestCase):
    def test_the_patch_is_added_only_when_the_board_reported_one(self):
        self.assertEqual(protocol.firmware_version_text(0, 3, bytes([0x00, 5, 0x01])), "0.3.5")
        self.assertEqual(protocol.firmware_version_text(0, 3, None), "0.3")
        self.assertEqual(protocol.firmware_version_text(0, 3, b""), "0.3")
        self.assertEqual(protocol.firmware_version_text(0, 3, bytes([0x00, 0xFF, 0x00])), "0.3")
        self.assertEqual(protocol.firmware_version_text(0, 3, bytes([0x00])), "0.3", "a frame that is too short is not a patch")


if __name__ == "__main__":
    unittest.main()
