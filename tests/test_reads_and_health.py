# =============================================================================
# URTC Tester - reads that must not collide, thermal image assembly, board health
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Mock CAN transports: no board is needed. They cover the strobe period unit, the thermal image geometry and chunk assembly, the multi-frame waiter, the queries that
run off the Tkinter thread, the board-health verdicts, and the Qt deck's single reader and stop-everything behaviour."""
import queue
import threading
import time
import unittest

import advanced_protocol as protocol
from tester_bus_monitor import CANBusMonitor
from tester_config import (
    AOI_STROBE_MAX_MS, CAN_ID_AOI_CMD, CAN_ID_MLX_VARIANT_RESP, CAN_ID_THERMAL_CALIB_CHUNK, CAN_ID_THERMAL_CALIB_CHUNK_REQ,
    CAN_ID_THERMAL_STATUS, bitrate_bps_for_label,
)
from tester_panel_helpers import PanelHelpersMixin

try:
    from PySide6.QtCore import QCoreApplication
    import qt_tester
except ImportError:  # PySide6 is not installed
    qt_tester = None


class FakeTransport:
    """A board stand-in: answers requests through `responder(can_id, data) -> list of (can_id, data)` and hands frames back through read_frame."""

    def __init__(self, responder=None):
        self.sent = []
        self._rx = queue.Queue()
        self._responder = responder or (lambda can_id, data: [])
        self.reading = 0
        self.max_readers = 0
        self._lock = threading.Lock()

    def send_frame(self, can_id, data):
        self.sent.append((can_id, bytes(data)))
        for frame in self._responder(can_id, bytes(data)):
            self._rx.put(frame)

    def read_frame(self, timeout=0.1):
        with self._lock:
            self.reading += 1
            self.max_readers = max(self.max_readers, self.reading)
        try:
            return self._rx.get(timeout=min(timeout, 0.02))
        except queue.Empty:
            return None
        finally:
            with self._lock:
                self.reading -= 1


def _chunk_frames(chunk_index, base=2000):
    """4 frames of 8 bytes carrying 16 centi-degree values (base + 100 * chunk + pixel)."""
    values = [base + 100 * chunk_index + i for i in range(16)]
    raw = b"".join(v.to_bytes(2, "big", signed=True) for v in values)
    return [(CAN_ID_THERMAL_CALIB_CHUNK, raw[i * 8:(i + 1) * 8]) for i in range(4)]


class StrobePeriodTests(unittest.TestCase):
    def test_the_period_is_milliseconds_limited_to_the_firmwares_500(self):
        self.assertEqual(protocol.aoi_frame("strobe", "5"), (CAN_ID_AOI_CMD, b"\x01\x00\x05"))
        self.assertEqual(protocol.aoi_frame("strobe", AOI_STROBE_MAX_MS)[1], b"\x01\x01\xf4")
        for bad in (0, AOI_STROBE_MAX_MS + 1, 1000):
            with self.assertRaises(ValueError):
                protocol.aoi_frame("strobe", bad)


class ThermalImageTests(unittest.TestCase):
    def test_the_geometry_follows_the_sensor_variant(self):
        self.assertEqual(protocol.thermal_grid(1), (32, 24, 48))
        self.assertEqual(protocol.thermal_grid(2), (16, 12, 12))
        self.assertEqual(protocol.thermal_grid(3), (32, 24, 48))
        self.assertIsNone(protocol.thermal_grid(0))
        self.assertIsNone(protocol.thermal_grid(9))

    def test_a_lost_chunk_leaves_blanks_and_keeps_the_pixels_after_it_in_place(self):
        chunks = {0: protocol.decode_thermal_chunk([f for _id, f in _chunk_frames(0)]),
                  2: protocol.decode_thermal_chunk([f for _id, f in _chunk_frames(2)])}
        pixels = protocol.thermal_pixels(chunks, 3)
        self.assertEqual(len(pixels), 48)
        self.assertEqual(pixels[0], 2000)
        self.assertEqual(pixels[16:32], [None] * 16)
        self.assertEqual(pixels[32], 2200)

    def test_an_incomplete_chunk_is_not_decoded(self):
        frames = [f for _id, f in _chunk_frames(0)]
        self.assertIsNone(protocol.decode_thermal_chunk(frames[:3]))
        self.assertIsNone(protocol.decode_thermal_chunk(frames[:3] + [b"\x00" * 7]))


class MultiFrameWaiterTests(unittest.TestCase):
    def test_all_four_frames_of_a_reply_arrive_back_to_back(self):
        def responder(can_id, data):
            return _chunk_frames(data[0]) if can_id == CAN_ID_THERMAL_CALIB_CHUNK_REQ else []

        transport = FakeTransport(responder)
        bus = CANBusMonitor(transport, lambda text: None)
        bus.start()
        try:
            frames = bus.wait_for_n(CAN_ID_THERMAL_CALIB_CHUNK, 4, timeout=1.0,
                                    send_after_register=lambda: bus.send(CAN_ID_THERMAL_CALIB_CHUNK_REQ, bytes([5])))
        finally:
            bus.stop()
        self.assertEqual(len(frames), 4)
        self.assertEqual(protocol.decode_thermal_chunk(frames)[0], 2500)

    def test_a_short_reply_returns_what_arrived(self):
        transport = FakeTransport(lambda can_id, data: _chunk_frames(0)[:2])
        bus = CANBusMonitor(transport, lambda text: None)
        bus.start()
        try:
            frames = bus.wait_for_n(CAN_ID_THERMAL_CALIB_CHUNK, 4, timeout=0.3,
                                    send_after_register=lambda: bus.send(CAN_ID_THERMAL_CALIB_CHUNK_REQ, b"\x00"))
        finally:
            bus.stop()
        self.assertEqual(len(frames), 2)
        self.assertEqual(bus._waiters, {})


class QueriesOffTheTkThreadTests(unittest.TestCase):
    class _Panel(PanelHelpersMixin):
        def __init__(self, bus):
            self.bus = bus
            self.logged = []
            self.main_thread = threading.get_ident()
            self.after_calls = []

            class _Root:
                def after(root_self, delay, fn):
                    self.after_calls.append(fn)
            self.root = _Root()

        def log(self, text):
            self.logged.append(text)

    class _SlowBus:
        def __init__(self, response, delay=0.2):
            self.response, self.delay = response, delay
            self.waiting_thread = None

        def wait_for_one(self, can_id, timeout=1.0, send_after_register=None):
            self.waiting_thread = threading.get_ident()
            time.sleep(self.delay)
            return self.response

    def _run(self, panel):
        results = []
        started = time.monotonic()
        panel._query_async(0x182, None, results.append)
        returned_after = time.monotonic() - started
        for _ in range(100):
            if panel.after_calls:
                break
            time.sleep(0.02)
        for fn in panel.after_calls:
            fn()
        return results, returned_after

    def test_the_wait_happens_on_a_worker_and_the_answer_comes_back_through_after(self):
        bus = self._SlowBus(b"\x01")
        panel = self._Panel(bus)
        results, returned_after = self._run(panel)
        self.assertLess(returned_after, 0.1, "the calling (Tk) thread must not wait for the board")
        self.assertNotEqual(bus.waiting_thread, panel.main_thread)
        self.assertEqual(results, [b"\x01"])

    def test_the_answer_is_dropped_when_the_connection_was_replaced(self):
        bus = self._SlowBus(b"\x01", delay=0.05)
        panel = self._Panel(bus)
        results = []
        panel._query_async(0x182, None, results.append)
        panel.bus = None
        for _ in range(100):
            if panel.after_calls:
                break
            time.sleep(0.02)
        for fn in panel.after_calls:
            fn()
        self.assertEqual(results, [])


class BoardHealthTests(unittest.TestCase):
    OK = bytes([0x05, 0, 0, 0, 0, 0])

    def test_silence_counts_after_two_consecutive_polls(self):
        tracker = protocol.BusHealthTracker()
        self.assertIsNone(tracker.evaluate(None))
        self.assertEqual(tracker.evaluate(None), [("STATE_BOARD_NOT_RESPONDING", {})])
        self.assertEqual(tracker.evaluate(self.OK), [])

    def test_one_missed_poll_between_answers_is_forgotten(self):
        tracker = protocol.BusHealthTracker()
        self.assertIsNone(tracker.evaluate(None))
        self.assertEqual(tracker.evaluate(self.OK), [])
        self.assertIsNone(tracker.evaluate(None))

    def test_the_error_bytes_are_reported(self):
        tracker = protocol.BusHealthTracker()
        keys = [key for key, _args in tracker.evaluate(bytes([5, 1, 1, 0, 2, 0]))]
        self.assertEqual(keys, ["STATE_CRITICAL_ERROR", "STATE_CAN_BUS_ERROR", "STATE_THERMAL_FAULT"])
        self.assertEqual(tracker.evaluate(self.OK), [])


class BitrateTests(unittest.TestCase):
    def test_the_labels_give_bits_per_second(self):
        self.assertEqual(bitrate_bps_for_label("500 kbit/s"), 500000)
        self.assertEqual(bitrate_bps_for_label("125 kbit/s"), 125000)
        self.assertEqual(bitrate_bps_for_label("1 Mbit/s"), 1000000)
        self.assertEqual(bitrate_bps_for_label("???"), 500000)


@unittest.skipIf(qt_tester is None, "PySide6 is not available")
class QtDeckReadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QCoreApplication.instance() or QCoreApplication([])

    def _bridge(self, transport):
        bridge = qt_tester.TesterQtBridge()
        bridge._transport = transport
        bridge._log = lambda text: None
        return bridge

    def test_queries_launched_together_read_the_transport_one_at_a_time(self):
        def responder(can_id, data):
            return [(can_id + 1, b"\x01")]

        transport = FakeTransport(responder)
        bridge = self._bridge(transport)
        results = []
        bridge._queryResult.connect(lambda key, value: results.append((key, value)))
        for key, request_id in (("a", 0x100), ("b", 0x200), ("c", 0x300)):
            bridge._run_query(key, (request_id, b""), request_id + 1, lambda data: data)
        deadline = time.monotonic() + 3
        while len(results) < 3 and time.monotonic() < deadline:
            QCoreApplication.processEvents()  # the results come from the worker threads as queued signals
            time.sleep(0.02)
        self.assertEqual(sorted(key for key, _v in results), ["a", "b", "c"])
        self.assertTrue(all(value == b"\x01" for _k, value in results), "no query may eat another one's answer")
        self.assertEqual(transport.max_readers, 1)

    def test_a_query_is_refused_while_another_read_owns_the_transport(self):
        transport = FakeTransport()
        bridge = self._bridge(transport)
        bridge._busy = True
        bridge._run_query("a", (0x100, b""), 0x101, lambda data: data)
        time.sleep(0.1)
        self.assertEqual(transport.sent, [])

    def test_changing_profile_switches_the_armed_outputs_off(self):
        bridge = self._bridge(FakeTransport())
        bridge._selected_tool_id = 0
        stopped = []
        bridge._watchdog_stops = {"solder": threading.Event()}
        bridge._stop_watchdog = lambda key, off=None: stopped.append(key)
        bridge.selectToolProfile(9)
        self.assertEqual(stopped, ["solder"])
        self.assertEqual(bridge._selected_tool_id, 9)

    def test_stop_all_outputs_works_even_when_busy_and_for_any_profile(self):
        transport = FakeTransport()
        bridge = self._bridge(transport)
        bridge._listen_only = False
        bridge._busy = True
        stopped = []
        bridge._watchdog_stops = {"laser": threading.Event()}
        bridge._stop_watchdog = lambda key, off=None: stopped.append(key)
        bridge.stopAllOutputs()
        self.assertEqual(stopped, ["laser"])
        self.assertTrue(any(data == b"\x00\x00\x00\x00\x00" for _id, data in transport.sent), "the motion stop goes out too")

    def test_stop_all_outputs_does_not_transmit_in_listen_only(self):
        transport = FakeTransport()
        bridge = self._bridge(transport)
        bridge._listen_only = True
        bridge.stopAllOutputs()
        self.assertEqual(transport.sent, [])

    def _thermal(self, variant, lose_chunk=None, ready=True):
        def responder(can_id, data):
            if can_id == CAN_ID_MLX_VARIANT_RESP:
                return [(CAN_ID_MLX_VARIANT_RESP, bytes([variant]))]
            if can_id == CAN_ID_THERMAL_STATUS:
                return [(CAN_ID_THERMAL_STATUS, bytes([0x02 if ready else 0x01]))]
            if can_id == CAN_ID_THERMAL_CALIB_CHUNK_REQ:
                return [] if data[0] == lose_chunk else _chunk_frames(data[0])
            return []

        transport = FakeTransport(responder)
        bridge = self._bridge(transport)
        out = []
        bridge._thermalResult.connect(lambda cells, summary: out.append((cells, summary)))
        bridge._capture_thermal_worker(transport)
        return transport, bridge, out[0]

    def test_the_small_sensor_reads_12_chunks_in_a_16_wide_grid(self):
        transport, bridge, (cells, summary) = self._thermal(2)
        requested = [data[0] for can_id, data in transport.sent if can_id == CAN_ID_THERMAL_CALIB_CHUNK_REQ]
        self.assertEqual(requested, list(range(12)))
        self.assertEqual(len(cells), 16 * 12)
        self.assertEqual(bridge.thermalColumns, 16)
        self.assertIn("size=16x12", summary)

    def test_a_lost_chunk_does_not_shift_the_image(self):
        _transport, _bridge, (cells, _summary) = self._thermal(1, lose_chunk=3)
        self.assertEqual(len(cells), 32 * 24)
        self.assertTrue(all(cell["missing"] for cell in cells[48:64]))
        self.assertEqual(cells[64]["temperature"], 2000 + 100 * 4)

    def test_no_sensor_or_not_ready_is_reported_not_painted(self):
        _t, _b, (cells, summary) = self._thermal(0)
        self.assertEqual(cells, [])
        self.assertTrue(summary.startswith("THERMAL_CAPTURE_FAILED"))
        _t, _b, (cells, summary) = self._thermal(1, ready=False)
        self.assertEqual(cells, [])
        self.assertIn("did not become ready", summary)


if __name__ == "__main__":
    unittest.main()
