# =============================================================================
# URTC Tester - Hardware-free tests for BusStats (frame rate / bus load)
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
import unittest

from tester_bus_monitor import BusStats


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class BusStatsTests(unittest.TestCase):
    def test_empty_window_is_zero(self):
        self.assertEqual(BusStats(clock=FakeClock()).snapshot(), (0.0, 0.0))

    def test_frame_rate_and_load_from_known_traffic(self):
        stats = BusStats(clock=FakeClock())
        for _ in range(100):  # 100 frames of 8 data bytes in one second
            stats.record(8)
        fps, load = stats.snapshot(bitrate_bps=500000)
        self.assertEqual(fps, 100.0)
        self.assertAlmostEqual(load, 100 * (47 + 64) / 500000 * 100, places=6)

    def test_old_frames_leave_the_window(self):
        clock = FakeClock()
        stats = BusStats(clock=clock)
        stats.record(8)
        clock.now += 1.5
        self.assertEqual(stats.snapshot()[0], 0.0)

    def test_load_is_capped_at_100_percent(self):
        stats = BusStats(clock=FakeClock())
        for _ in range(5000):
            stats.record(8)
        self.assertEqual(stats.snapshot(bitrate_bps=10000)[1], 100.0)

    def test_instrumentation_counts_reads_and_sends_but_not_empty_reads(self):
        import tester_transports as tt

        class Dummy:
            def __init__(self):
                self.frames = [(0x100, bytes([1, 2])), None]

            def read_frame(self, timeout=0.05):
                return self.frames.pop(0)

            def send_frame(self, can_id, data):
                return None

        tt._instrument_with_bus_stats(Dummy)
        d = Dummy()
        d.read_frame()
        d.read_frame()  # nothing arrived - must not count
        d.send_frame(0x101, bytes([0]))
        self.assertEqual(d.stats.snapshot()[0], 2.0)


if __name__ == "__main__":
    unittest.main()
