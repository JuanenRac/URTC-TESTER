# =============================================================================
# URTC Tester - tests/test_transports_and_monitor.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The serial (SLCAN) and SocketCAN transports against stand-ins for the
adapter and the kernel socket, and the bus monitor that fans received frames
out to the tool panels: what is put on the wire, what is refused (listen-only,
oversized, out of range), what is dropped from the receive side, and that one
failing callback never stops the others."""
from __future__ import annotations

import socket
import struct
import sys
import time
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tester_transports  # noqa: E402
from tester_bus_monitor import BusStats, CANBusMonitor  # noqa: E402
from tester_transports import SLCAN, SLCANError, SocketCAN, SocketCANError  # noqa: E402


class _SerialException(Exception):
    pass


class _FakeSerial:
    def __init__(self):
        self.written = b""
        self.incoming = bytearray()
        self.fail_writes = False
        self.closed = False
        self.resets = 0

    @property
    def in_waiting(self):
        return len(self.incoming)

    def read(self, count):
        chunk = bytes(self.incoming[:count])
        del self.incoming[:count]
        return chunk

    def write(self, data):
        if self.fail_writes:
            raise _SerialException("unplugged")
        self.written += data

    def reset_input_buffer(self):
        self.resets += 1
        self.incoming.clear()

    def close(self):
        self.closed = True


@pytest.fixture
def slcan(monkeypatch):
    monkeypatch.setattr(tester_transports.time, "sleep", lambda seconds: None)
    port = _FakeSerial()
    serial_module = types.SimpleNamespace(SerialException=_SerialException, Serial=lambda *args, **kwargs: port)
    return SLCAN("COMX", serial_module=serial_module, settle_seconds=0.0)


# ---- SLCAN ---------------------------------------------------------------------------------
def test_opening_the_channel_closes_sets_the_bitrate_then_opens(slcan):
    slcan.open_channel()
    assert slcan.ser.written == b"C\rS6\rO\r"
    assert slcan.listen_only is False


def test_listen_only_opens_with_L_and_then_refuses_to_transmit(slcan):
    slcan.open_channel(listen_only=True)
    assert slcan.ser.written.endswith(b"L\r")
    written = slcan.ser.written
    with pytest.raises(SLCANError, match="listen-only"):
        slcan.send_frame(0x100, b"\x00")
    assert slcan.ser.written == written


def test_a_write_to_an_unplugged_adapter_is_a_typed_error(slcan):
    slcan.ser.fail_writes = True
    with pytest.raises(SLCANError, match="serial write failed"):
        slcan.send_frame(0x100, b"\x01")


def test_a_negative_identifier_is_refused(slcan):
    with pytest.raises(SLCANError, match="negative"):
        slcan.send_frame(-1, b"")


def test_close_sends_C_and_closes_the_port_even_if_the_write_fails(slcan):
    slcan.ser.fail_writes = True
    slcan.close()
    assert slcan.ser.closed


def test_a_line_split_across_reads_is_reassembled(slcan):
    slcan.ser.incoming.extend(b"t1112")
    assert slcan.read_frame(timeout=0.02) is None
    slcan.ser.incoming.extend(b"AABB\r")
    assert slcan.read_frame(timeout=0.2) == (0x111, b"\xAA\xBB")


def test_acknowledge_characters_between_frames_are_skipped(slcan):
    slcan.ser.incoming.extend(b"z\rZ\r\x07\rt1000\r")
    assert slcan.read_frame(timeout=0.2) == (0x100, b"")


def test_non_ascii_noise_is_skipped_and_the_next_frame_still_arrives(slcan):
    slcan.ser.incoming.extend(b"\xff\xfe\x80\rt1000\r")
    assert slcan.read_frame(timeout=0.2) == (0x100, b"")


def test_a_runaway_line_without_a_terminator_is_discarded_not_buffered_forever(slcan):
    slcan.ser.incoming.extend(b"A" * 5000)
    assert slcan.read_frame(timeout=0.05) is None
    slcan.ser.incoming.extend(b"t1000\r")
    assert slcan.read_frame(timeout=0.2) == (0x100, b"")


def test_two_frames_in_one_read_come_out_in_order(slcan):
    slcan.ser.incoming.extend(b"t1001AA\rt1011BB\r")
    assert slcan.read_frame(timeout=0.2) == (0x100, b"\xAA")
    assert slcan.read_frame(timeout=0.2) == (0x101, b"\xBB")


def test_frames_are_counted_by_the_bus_statistics(slcan):
    slcan.send_frame(0x100, b"\x01\x02")
    slcan.ser.incoming.extend(b"t1000\r")
    slcan.read_frame(timeout=0.2)
    assert len(slcan.stats._events) == 2


# ---- SocketCAN ----------------------------------------------------------------------------
class _FakeSocket:
    def __init__(self):
        self.sent = []
        self.incoming = []
        self.timeouts = []
        self.fail = None

    def send(self, frame):
        if self.fail:
            raise OSError(self.fail)
        self.sent.append(frame)

    def recv(self, size):
        if self.fail == "timeout":
            raise socket.timeout()
        if self.fail:
            raise OSError(self.fail)
        return self.incoming.pop(0) if self.incoming else (_ for _ in ()).throw(socket.timeout())

    def settimeout(self, value):
        self.timeouts.append(value)

    def close(self):
        pass


class _FakeSocketModule:
    """Stands in for the socket module: ``socket(...)`` hands out one fake kernel socket."""

    AF_CAN = SOCK_RAW = CAN_RAW = 0

    def __init__(self):
        self.created = _FakeSocket()

    def socket(self, *args):
        return self.created

    def __getattr__(self, name):
        return getattr(socket, name)


@pytest.fixture
def can_socket(monkeypatch):
    monkeypatch.setattr(tester_transports.time, "sleep", lambda seconds: None)
    module = _FakeSocketModule()
    module.created.bind = lambda address: None
    transport = SocketCAN("can0", socket_module=module)
    module.created.timeouts.clear()  # the constructor's own first setting is not what these tests look at
    return transport


def _raw(can_id, data, dlc=None):
    return struct.pack("=IB3x8s", can_id, len(data) if dlc is None else dlc, bytes(data) + bytes(8 - len(data)))


def test_socketcan_sends_a_padded_kernel_frame(can_socket):
    can_socket.send_frame(0x111, b"\x01\x02")
    assert can_socket.sock.sent == [struct.pack("=IB3x8s", 0x111, 2, b"\x01\x02" + bytes(6))]


def test_socketcan_accepts_buffer_types(can_socket):
    can_socket.send_frame(0x100, bytearray(b"\x05"))
    can_socket.send_frame(0x100, memoryview(b"\x06"))
    assert len(can_socket.sock.sent) == 2


@pytest.mark.parametrize("can_id, data", [(0x800, b""), (-1, b""), (0x100, bytes(9))])
def test_socketcan_refuses_bad_frames(can_socket, can_id, data):
    with pytest.raises(SocketCANError):
        can_socket.send_frame(can_id, data)
    assert can_socket.sock.sent == []


def test_socketcan_listen_only_never_transmits(can_socket):
    can_socket.open_channel(listen_only=True)
    with pytest.raises(SocketCANError, match="listen-only"):
        can_socket.send_frame(0x100, b"")
    assert can_socket.sock.sent == []


def test_socketcan_send_failure_is_typed(can_socket):
    can_socket.sock.fail = "network down"
    with pytest.raises(SocketCANError, match="send failed"):
        can_socket.send_frame(0x100, b"")


def test_socketcan_reads_a_standard_frame(can_socket):
    can_socket.sock.incoming.append(_raw(0x123, b"\xDE\xAD"))
    assert can_socket.read_frame(timeout=0.05) == (0x123, b"\xDE\xAD")


@pytest.mark.parametrize("flag", [0x80000000, 0x40000000, 0x20000000])
def test_socketcan_drops_extended_remote_and_error_frames_before_masking(can_socket, flag):
    can_socket.sock.incoming.append(_raw(flag | 0x111, b"\x01"))
    assert can_socket.read_frame(timeout=0.05) is None


def test_socketcan_clamps_an_impossible_dlc(can_socket):
    can_socket.sock.incoming.append(_raw(0x100, bytes(range(8)), dlc=15))
    assert can_socket.read_frame(timeout=0.05) == (0x100, bytes(range(8)))


def test_socketcan_ignores_a_short_read_and_a_dead_socket(can_socket):
    can_socket.sock.incoming.append(b"\x00\x01")
    assert can_socket.read_frame(timeout=0.05) is None
    can_socket.sock.fail = "closed"
    assert can_socket.read_frame(timeout=0.05) is None


def test_socketcan_only_changes_the_socket_timeout_when_it_differs(can_socket):
    can_socket.read_frame(timeout=0.05)
    can_socket.read_frame(timeout=0.3)
    can_socket.read_frame(timeout=0.3)
    assert can_socket.sock.timeouts == [0.3]


def test_socketcan_statistics_come_from_sysfs_files(tmp_path, monkeypatch):
    base = tmp_path / "net" / "can0" / "statistics"
    base.mkdir(parents=True)
    for name, value in {"rx_packets": 5, "tx_packets": 6, "rx_errors": 0, "tx_errors": 1, "rx_dropped": 2, "tx_dropped": 3, "collisions": 4}.items():
        (base / name).write_text(f"{value}\n")
    real_isdir, real_open = tester_transports.os.path.isdir, open
    monkeypatch.setattr(tester_transports.os.path, "isdir", lambda path: real_isdir(str(path).replace("/sys/class", str(tmp_path))))

    def redirected(path, *args, **kwargs):
        return real_open(str(path).replace("/sys/class", str(tmp_path)), *args, **kwargs)
    monkeypatch.setattr("builtins.open", redirected)
    stats = SocketCAN.read_interface_stats("can0")
    assert stats["rx_packets"] == 5 and stats["collisions"] == 4
    (base / "tx_errors").write_text("not a number")
    assert SocketCAN.read_interface_stats("can0") is None
    assert SocketCAN.read_interface_stats("nothere") is None


# ---- bus statistics ------------------------------------------------------------------------
def test_bus_load_counts_framing_bits_and_ages_out_old_frames():
    now = [0.0]
    stats = BusStats(window_s=1.0, clock=lambda: now[0])
    for _ in range(10):
        stats.record(8)
    fps, load = stats.snapshot(bitrate_bps=500000)
    assert fps == 10
    assert load == pytest.approx(100.0 * (10 * (47 + 64)) / 500000)
    now[0] = 5.0
    assert stats.snapshot() == (0.0, 0.0)
    assert stats.snapshot(bitrate_bps=0)[1] == 0.0


def test_bus_load_never_exceeds_one_hundred_percent():
    stats = BusStats(window_s=1.0, clock=lambda: 0.0)
    for _ in range(100000):
        stats.record(8)
    assert stats.snapshot(bitrate_bps=500000)[1] == 100.0


# ---- bus monitor ---------------------------------------------------------------------------
class _ScriptedTransport:
    def __init__(self, frames):
        self.frames = list(frames)
        self.sent = []

    def read_frame(self, timeout=0.1):
        if self.frames:
            item = self.frames.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        time.sleep(0.002)
        return None

    def send_frame(self, can_id, data):
        self.sent.append((can_id, bytes(data)))


def _wait(predicate, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return False


@pytest.fixture
def monitors():
    created = []

    def make(frames, listen_only=False):
        logs = []
        monitor = CANBusMonitor(_ScriptedTransport(frames), logs.append, listen_only=listen_only)
        monitor.logs = logs
        created.append(monitor)
        return monitor
    yield make
    for monitor in created:
        monitor.stop()


def test_frames_reach_only_the_handlers_of_their_identifier(monitors):
    monitor = monitors([(0x111, b"\x01"), (0x222, b"\x02"), (0x111, b"\x03")])
    seen = []
    monitor.register(0x111, seen.append)
    monitor.start()
    assert _wait(lambda: len(seen) == 2)
    assert seen == [b"\x01", b"\x03"]


def test_a_failing_handler_does_not_stop_the_others_or_the_loop(monitors):
    monitor = monitors([(0x111, b"\x01"), (0x111, b"\x02")])
    seen = []

    def broken(data):
        raise RuntimeError("panel bug")
    monitor.register(0x111, broken)
    monitor.register(0x111, seen.append)
    monitor.start()
    assert _wait(lambda: len(seen) == 2)
    assert any("0x111" in str(line) or "111" in str(line) for line in monitor.logs)


def test_a_read_error_is_logged_and_reading_continues(monitors, monkeypatch):
    monkeypatch.setattr(sys.modules["tester_bus_monitor"].time, "sleep", lambda seconds: None)
    monitor = monitors([OSError("usb glitch"), (0x100, b"\x09")])
    seen = []
    monitor.register(0x100, seen.append)
    monitor.start()
    assert _wait(lambda: seen == [b"\x09"])
    assert monitor.logs


def test_sniffers_see_every_frame_and_can_be_removed(monitors):
    monitor = monitors([(0x100, b"a"), (0x200, b"b")])
    seen = []
    sniffer = lambda can_id, data: seen.append((can_id, data))  # noqa: E731
    monitor.register_sniffer(sniffer)
    monitor.start()
    assert _wait(lambda: len(seen) == 2)
    monitor.unregister_sniffer(sniffer)
    monitor.unregister_sniffer(sniffer)


def test_unregister_removes_the_entry_when_the_last_callback_goes(monitors):
    monitor = monitors([])
    callback = lambda data: None  # noqa: E731
    monitor.register(0x100, callback)
    monitor.unregister(0x100, callback)
    assert 0x100 not in monitor._handlers
    monitor.unregister(0x100, callback)
    monitor.register(0x100, callback)
    monitor.clear_all()
    assert monitor._handlers == {}


def test_listen_only_sends_nothing(monitors):
    monitor = monitors([], listen_only=True)
    monitor.send(0x100, b"\x01")
    assert monitor.transport.sent == [] and monitor.logs


def test_send_reaches_the_transport_when_not_listening_only(monitors):
    monitor = monitors([])
    monitor.send(0x100, b"\x01")
    assert monitor.transport.sent == [(0x100, b"\x01")]


def test_wait_for_one_returns_the_answer_to_a_request_sent_after_registering(monitors):
    monitor = monitors([])
    monitor.start()
    answer = monitor.wait_for_one(0x111, timeout=1.0, send_after_register=lambda: monitor.transport.frames.append((0x111, b"\x07")))
    assert answer == b"\x07"


def test_wait_for_one_times_out_with_none(monitors):
    monitor = monitors([])
    monitor.start()
    assert monitor.wait_for_one(0x111, timeout=0.05) is None
    assert monitor._waiters == {}


def test_wait_for_n_collects_a_multi_frame_answer(monitors):
    monitor = monitors([])
    monitor.start()
    frames = monitor.wait_for_n(0x253, 4, timeout=1.0, send_after_register=lambda: monitor.transport.frames.extend([(0x253, bytes([i])) for i in range(4)]))
    assert frames == [bytes([i]) for i in range(4)]


def test_wait_for_n_returns_what_arrived_before_the_timeout(monitors):
    monitor = monitors([])
    monitor.start()
    frames = monitor.wait_for_n(0x253, 4, timeout=0.2, send_after_register=lambda: monitor.transport.frames.extend([(0x253, b"\x01"), (0x253, b"\x02")]))
    assert frames == [b"\x01", b"\x02"]
