# =============================================================================
# URTC Tester - live telemetry readouts and bus health in the Qt Quick deck
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Readout decoding, the recorded series, the watch gate and the periodic bus health check (fake buses only)."""
from __future__ import annotations

import csv
import os
import queue
import struct
import tempfile
import threading
import unittest
from unittest import mock

import tester_config as cfg
import tester_telemetry as tele

try:
    import qt_tester
except ImportError:  # PySide6 is not installed
    qt_tester = None


class DecodeTests(unittest.TestCase):
    def _readout(self, tool_id, key):
        return next(r for r in tele.readouts_for(tool_id) if r.key == key)

    def test_a_temperature_frame_is_big_endian_celsius(self):
        text, value = tele.decode_readout(self._readout(0, "solder_iron_temp_c"), struct.pack(">H", 321))
        self.assertEqual((text, value), ("321 °C", 321.0))

    def test_the_drill_rpm_and_endstop_come_from_different_bytes_of_one_frame(self):
        frame = struct.pack(">H", 1500) + bytes([1])
        self.assertEqual(tele.decode_readout(self._readout(5, "drill_rpm"), frame), ("1500 RPM", 1500.0))
        text, value = tele.decode_readout(self._readout(5, "drill_endstop"), frame)
        self.assertEqual(value, 1.0)
        self.assertEqual(text, cfg._("VAL_TRIGGERED"))

    def test_an_open_endstop_reads_open(self):
        text, value = tele.decode_readout(self._readout(8, "aoi_endstop"), b"\x00")
        self.assertEqual((text, value), (cfg._("VAL_ENDSTOP_OPEN"), 0.0))

    def test_a_short_frame_gives_nothing_instead_of_a_wrong_value(self):
        self.assertIsNone(tele.decode_readout(self._readout(0, "solder_iron_temp_c"), b"\x01"))
        self.assertIsNone(tele.decode_readout(self._readout(8, "aoi_endstop"), b""))
        self.assertIsNone(tele.decode_readout(self._readout(5, "drill_endstop"), b"\x00\x01"))

    def test_every_listed_tool_exists_and_every_caption_has_text_in_every_language(self):
        for tool_id, items in tele.READOUTS.items():
            self.assertIn(tool_id, cfg.TOOL_NAMES)
            for item in items:
                for language in ("english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese"):
                    self.assertTrue(cfg.load_language(language).get(item.label_key), (language, item.label_key))

    def test_only_temperature_readouts_have_a_graph(self):
        for items in tele.READOUTS.values():
            for item in items:
                self.assertEqual(bool(item.graph_max), item.kind == tele.CELSIUS, item.key)

    def test_the_hot_air_station_and_the_soldering_iron_share_the_temperature_frame(self):
        self.assertEqual(tele.readouts_for(0)[0].can_id, tele.readouts_for(19)[0].can_id)


class SeriesTests(unittest.TestCase):
    def test_the_window_rolls_but_the_history_keeps_everything(self):
        series = tele.Series()
        for i in range(tele.GRAPH_POINTS + 25):
            series.add(float(i), 100.0 + i)
        self.assertEqual(len(series.window), tele.GRAPH_POINTS)
        self.assertEqual(series.window[-1], float(tele.GRAPH_POINTS + 24))
        self.assertEqual(len(series.history), tele.GRAPH_POINTS + 25)
        self.assertEqual(series.history[0][0], 0.0)

    def test_the_history_is_bounded(self):
        series = tele.Series()
        for i in range(tele.MAX_HISTORY + 10):
            series.add(1.0, float(i))
        self.assertEqual(len(series.history), tele.MAX_HISTORY)

    def test_the_csv_has_a_header_and_one_row_per_point(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "t.csv")
            self.assertEqual(tele.write_csv(path, "solder_iron_temp_c", [(0.0, 20.0), (0.15, 25.0)]), 2)
            with open(path, newline="", encoding="utf-8") as stream:
                rows = list(csv.reader(stream))
        self.assertEqual(rows, [["seconds", "solder_iron_temp_c"], ["0.0", "20.0"], ["0.15", "25.0"]])


class FakeTransport:
    def __init__(self):
        self.inbox: queue.Queue = queue.Queue()
        self.sent = []

    def read_frame(self, timeout=0.1):
        try:
            return self.inbox.get(timeout=min(timeout, 0.02))
        except queue.Empty:
            return None

    def send_frame(self, can_id, data):
        self.sent.append((can_id, bytes(data)))

    def close(self):
        pass


@unittest.skipIf(qt_tester is None, "PySide6 is not available")
class BridgeTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(qt_tester, "save_config", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.bridge = qt_tester.TesterQtBridge()
        self.logs = []
        self.bridge._log = self.logs.append
        self.transport = FakeTransport()
        self.bridge._transport = self.transport
        self.bridge._listen_only = False
        self.bridge._selected_tool_id = 0
        self.bridge._active_tool_id = 0

    def _feed(self, can_id, data):
        decoded = [(r, tele.decode_readout(r, data)) for r in tele.readouts_for(self.bridge._selected_tool_id) if r.can_id == can_id]
        for readout, result in decoded:
            self.bridge._on_readout(readout.key, result[0], result[1])

    def test_a_tool_with_broadcasts_offers_readouts_and_a_vacuum_pickup_keeps_its_own_panel(self):
        self.assertTrue(self.bridge.readoutsAvailable)
        self.bridge._selected_tool_id = 4
        self.assertFalse(self.bridge.readoutsAvailable)

    def test_the_watch_is_allowed_in_listen_only_mode_because_it_transmits_nothing(self):
        self.bridge._listen_only = True
        self.assertTrue(self.bridge.canWatchTelemetry)

    def test_a_watch_needs_the_detected_tool_to_be_the_selected_profile(self):
        self.bridge._active_tool_id = 5
        self.assertFalse(self.bridge.canWatchTelemetry)

    def test_values_and_the_graph_follow_the_frames(self):
        self._feed(cfg.CAN_ID_SOLDER_TELEMETRY, struct.pack(">H", 250))
        self._feed(cfg.CAN_ID_SOLDER_TELEMETRY, struct.pack(">H", 260))
        self.assertEqual(self.bridge.readoutItems[0]["text"], "260 °C")
        self.assertEqual(self.bridge.readoutGraphPoints, [250.0, 260.0])
        self.assertEqual(self.bridge.readoutGraphMax, 450)

    def test_the_csv_export_writes_every_point(self):
        for value in (20, 30, 40):
            self._feed(cfg.CAN_ID_SOLDER_TELEMETRY, struct.pack(">H", value))
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "out.csv")
            self.assertEqual(self.bridge.exportReadoutCsv(path), path)
            with open(path, newline="", encoding="utf-8") as stream:
                self.assertEqual(len(list(csv.reader(stream))), 4)

    def test_the_csv_export_with_nothing_recorded_writes_no_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "out.csv")
            self.assertEqual(self.bridge.exportReadoutCsv(path), "")
            self.assertFalse(os.path.exists(path))

    def test_the_watch_thread_decodes_frames_and_transmits_nothing(self):
        import time
        from PySide6.QtCore import QCoreApplication

        app = QCoreApplication.instance() or QCoreApplication([])
        self.bridge._selected_tool_id = 5
        self.bridge._active_tool_id = 5
        self.bridge.watchTelemetry()
        self.assertTrue(self.bridge.isWatchingReadouts)
        self.transport.inbox.put((cfg.CAN_ID_DRILL_TELEMETRY, struct.pack(">H", 900) + bytes([0])))
        deadline = time.monotonic() + 3
        while "drill_rpm" not in self.bridge._readout_values and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        self.assertEqual(self.bridge._readout_values.get("drill_rpm"), "900 RPM")
        self.bridge.stopTelemetryWatch()
        self.bridge._end_telemetry_watch()
        deadline = time.monotonic() + 3
        while self.bridge.busy and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        self.assertFalse(self.bridge.isWatchingReadouts)
        self.assertEqual(self.transport.sent, [])

    def test_an_output_may_be_driven_while_a_readout_runs_but_a_bus_reading_command_may_not(self):
        self.bridge._telemetry_stops["readout"] = threading.Event()
        self.bridge._busy = True
        self.assertTrue(self.bridge.canActuateSelectedProfile)
        self.assertFalse(self.bridge.canSelfTest)
        self.bridge._selected_tool_id = 17
        self.bridge._active_tool_id = 17
        self.assertFalse(self.bridge._require_profile({17}, "FLYING_PROBE_READ", reads=True))

    def test_another_kind_of_watch_still_blocks_commands(self):
        self.bridge._telemetry_stops["vacuum"] = threading.Event()
        self.bridge._busy = True
        self.assertFalse(self.bridge.canActuateSelectedProfile)

    # -- bus health ---------------------------------------------------------
    def _health(self, answers):
        """Run the health worker for len(answers) polls; each answer is the 0x111 data or None."""
        answers = list(answers) + [bytes([0, 0, 0, 0, 0])]  # the last poll stops the worker and is not judged
        stop = threading.Event()
        seen = []
        self.bridge._busHealth.connect(lambda bad, reason: seen.append((bad, reason)))
        self.bridge.BUS_HEALTH_INTERVAL_S = 0.0
        guard = threading.Timer(0.5, stop.set)  # a gated worker never consumes an answer: end the run anyway
        guard.start()
        self.addCleanup(guard.cancel)

        def wait_for(can_id, timeout):
            data = answers.pop(0)
            if not answers:
                stop.set()
            return data

        with mock.patch.object(self.bridge, "_wait_for", wait_for):
            self.bridge._bus_health_worker(self.transport, stop)
        return seen

    def test_a_healthy_board_raises_nothing(self):
        self.assertEqual(self._health([bytes([0, 0, 0, 0, 0])] * 3), [])
        self.assertTrue(all(cid == cfg.CAN_ID_QUERY_ACTIVE_TOOL for cid, _d in self.transport.sent))

    def test_a_can_error_bit_is_reported_once_and_recovery_once(self):
        seen = self._health([bytes([0, 0, 1, 0, 0]), bytes([0, 0, 1, 0, 0]), bytes([0, 0, 0, 0, 0])])
        self.assertEqual([bad for bad, _r in seen], [True, False])
        self.assertTrue(seen[0][1])

    def test_one_silent_poll_is_no_verdict_but_two_are(self):
        self.assertEqual(self._health([None, bytes([0, 0, 0, 0, 0])]), [])
        seen = self._health([None, None])
        self.assertEqual([bad for bad, _r in seen], [True])

    def test_listen_only_never_polls(self):
        self.bridge._listen_only = True
        self._health([None, None])
        self.assertEqual(self.transport.sent, [])

    def test_a_busy_deck_is_not_polled(self):
        self.bridge._busy = True
        self._health([None, None])
        self.assertEqual(self.transport.sent, [])

    def test_the_banner_text_follows_the_signal_and_clears_on_recovery(self):
        self.bridge._on_bus_health(True, "Board not responding")
        self.assertEqual(self.bridge.busHealthText, "Board not responding")
        self.bridge._on_bus_health(False, "")
        self.assertEqual(self.bridge.busHealthText, "")

    def test_a_poll_after_disconnect_does_not_raise_a_banner(self):
        self.bridge._transport = None
        self.bridge._on_bus_health(True, "late")
        self.assertEqual(self.bridge.busHealthText, "")


if __name__ == "__main__":
    unittest.main()
