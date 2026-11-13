# =============================================================================
# URTC Tester - CANBusMonitor: the one background thread reading frames
# off the transport, dispatching to registered handlers/sniffers
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
import collections
import threading
import time

from tester_config import _
from urtc_can import node_monitor, protocol

BUS_BITRATE_BPS = protocol.BITRATE   # the default speed of the bus of the tool heads (the load is counted against it)

class CANBusMonitor:
    """Owns the one and only background thread reading frames off the
    transport, dispatching each received frame to whichever callbacks are
    currently registered for its CAN ID. This exists because a live
    tester - unlike the flasher's one-request-at-a-time protocol - needs
    to watch several different telemetry IDs at once (temperature, RPM,
    endstops...) without them stepping on each other, and a serial port or
    raw socket can't safely be read from two places at once. Callbacks run
    on this background thread - they must not touch window state directly.
    """
    def __init__(self, transport, log, listen_only=False):
        self.transport = transport
        self.log = log
        self._handlers = {}  # can_id -> list of persistent callback(data) functions, registered by tool panels
        # Kept separate from _handlers: clear_all() (every tool-panel rebuild) wipes _handlers, and must not drop the registration of a wait_for_one()
        # still blocked elsewhere (health poll, self-test), or a board that did answer would read as a timeout.
        self._waiters = {}  # can_id -> list of one-shot callback(data) functions, used only by wait_for_one below
        self._sniffers = []  # callback(can_id, data) functions - called for EVERY frame, regardless of ID
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self.listen_only = listen_only  # mirrors the transport's own flag
        # Checked here first too, so every send() is a quiet no-op while listen-only; a query then simply times out.

    def register(self, can_id, callback):
        with self._lock:
            self._handlers.setdefault(can_id, []).append(callback)

    def unregister(self, can_id, callback):
        with self._lock:
            if can_id in self._handlers and callback in self._handlers[can_id]:
                self._handlers[can_id].remove(callback)
                if not self._handlers[can_id]:
                    del self._handlers[can_id]

    def register_sniffer(self, callback):
        """Registers a callback(can_id, data) that fires for every single
        frame this monitor sees, regardless of ID - for the raw bus
        monitor panel. Separate from the per-ID handlers above; neither
        mechanism affects the other."""
        with self._lock:
            self._sniffers.append(callback)

    def unregister_sniffer(self, callback):
        with self._lock:
            if callback in self._sniffers:
                self._sniffers.remove(callback)

    def clear_all(self):
        # Deliberately doesn't touch _waiters - see __init__'s own comment
        # on why those are tracked separately from _handlers.
        with self._lock:
            self._handlers = {}

    def _register_waiter(self, can_id, callback):
        with self._lock:
            self._waiters.setdefault(can_id, []).append(callback)

    def _unregister_waiter(self, can_id, callback):
        with self._lock:
            if can_id in self._waiters and callback in self._waiters[can_id]:
                self._waiters[can_id].remove(callback)
                if not self._waiters[can_id]:
                    del self._waiters[can_id]

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def _loop(self):
        while self._running:
            try:
                frame = self.transport.read_frame(timeout=0.1)
            except Exception as e:
                self.log(_("LOG_BUS_READ_ERROR", e=e))
                time.sleep(0.2)
                continue
            if frame is None:
                continue
            can_id, data = frame
            with self._lock:
                callbacks = list(self._handlers.get(can_id, []))
                waiters = list(self._waiters.get(can_id, []))
                sniffers = list(self._sniffers)
            for callback in callbacks:
                try:
                    callback(data)
                except Exception as e:
                    self.log(_("LOG_HANDLER_ERROR", can_id=can_id, e=e))
            for waiter in waiters:
                try:
                    waiter(data)
                except Exception as e:
                    self.log(_("LOG_HANDLER_ERROR", can_id=can_id, e=e))
            for sniffer in sniffers:
                try:
                    sniffer(can_id, data)
                except Exception as e:
                    self.log(_("LOG_SNIFFER_ERROR", e=e))

    def send(self, can_id, data):
        if self.listen_only:
            self.log(_("LOG_SEND_BLOCKED_LISTEN_ONLY", can_id=f"0x{can_id:03X}"))
            return
        self.transport.send_frame(can_id, data)

    def wait_for_one(self, can_id, timeout=1.5, send_after_register=None):
        """One-off synchronous wait for a single frame on can_id, layered on the same registration mechanism as everything else
        (never calls read_frame() itself, so it cannot race the background reader).

        send_after_register, when given, is called with no arguments right after the callback is registered and before waiting,
        so a fast answer cannot arrive before anything listens (a false timeout). A caller that sends its request first is still safe, without that guarantee."""
        result = {"data": None}
        event = threading.Event()

        def _capture(data):
            result["data"] = data
            self._unregister_waiter(can_id, _capture)  # right here, not just
            # in the outer finally below - closes the narrow window where a
            # second frame on the same can_id could arrive and get
            # dispatched before the main thread wakes from event.wait(),
            # overwriting result with the wrong frame's data. Safe from
            # inside this callback since _loop dispatches over a copied
            # waiter list, not the live one this mutates.
            event.set()

        self._register_waiter(can_id, _capture)
        try:
            if send_after_register is not None:
                send_after_register()
            event.wait(timeout=timeout)
        finally:
            self._unregister_waiter(can_id, _capture)
        return result["data"]

    def wait_for_n(self, can_id, count, timeout=1.0, send_after_register=None):
        """Like wait_for_one, for a reply made of several consecutive frames
        on the same ID (the firmware answers a thermal chunk request with 4
        frames within about a millisecond). One waiter stays registered
        until `count` frames arrived or the timeout ran out, so none of the
        frames after the first falls between two registrations. Returns the
        list of frames received, which is shorter than `count` on a timeout."""
        frames = []
        event = threading.Event()

        def _capture(data):
            frames.append(data)
            if len(frames) >= count:
                self._unregister_waiter(can_id, _capture)
                event.set()

        self._register_waiter(can_id, _capture)
        try:
            if send_after_register is not None:
                send_after_register()
            event.wait(timeout=timeout)
        finally:
            self._unregister_waiter(can_id, _capture)
        return list(frames[:count])





class BusStats:
    """Sliding-window frame rate and estimated bus load, counted at the
    transport (every frame either direction), so it works for every
    reader in the app - the original GUI's one monitor thread and the Qt UI's
    many ad-hoc readers alike - without touching any of them.

    Bus load is an ESTIMATE from the standard CAN base-frame size (47 bits
    of framing/interframe space + 8 per data byte, stuff bits not
    counted) against the configured bitrate - a real bus with heavy bit
    stuffing runs a little higher than this reports."""

    FRAME_OVERHEAD_BITS = 47

    def __init__(self, window_s=1.0, clock=time.monotonic):
        self.window_s = window_s
        self._clock = clock
        self._events = collections.deque()  # (timestamp, bits)
        self._lock = threading.Lock()

    def record(self, data_len):
        now = self._clock()
        with self._lock:
            self._events.append((now, self.FRAME_OVERHEAD_BITS + 8 * data_len))
            self._trim(now)

    def _trim(self, now):
        cutoff = now - self.window_s
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()

    def snapshot(self, bitrate_bps=BUS_BITRATE_BPS):
        """(frames_per_second, bus_load_percent) over the last window."""
        now = self._clock()
        with self._lock:
            self._trim(now)
            frames = len(self._events)
            bits = sum(b for _, b in self._events)
        fps = frames / self.window_s
        load = min(100.0, 100.0 * (bits / self.window_s) / bitrate_bps) if bitrate_bps > 0 else 0.0
        return fps, load


class FrameFilter:
    """What the raw bus monitor window shows: only some CAN IDs, and/or only frames whose data changed.

    The counters of the window keep counting every frame; the filter only decides which ones become rows.
    """

    def __init__(self):
        self.ids = None  # None shows every ID
        self.nodes = None  # None shows every node (and the frames of nobody)
        self.only_changes = False
        self._last = {}

    def set_ids(self, text):
        """Accepts hex IDs separated by spaces or commas ("1A0 0x110, 7F8") and node addresses written n0 to n31 ("n3 n12"), which keep only the frames of those
        nodes of a bus with several tool heads. Unreadable tokens are ignored; nothing readable means no filter."""
        ids = set()
        for token in str(text).replace(",", " ").split():
            try:
                value = int(token, 16)
            except ValueError:
                continue
            if 0 <= value <= 0x7FF:
                ids.add(value)
        self.ids = ids or None
        self.nodes = node_monitor.parse_nodes(text) or None

    def reset(self):
        self._last.clear()

    def accept(self, can_id, data, node=None):
        """``node`` is the node the frame belongs to (see urtc_can.node_monitor), None when it belongs to nobody."""
        if self.ids is not None and can_id not in self.ids:
            return False
        if self.nodes is not None and node not in self.nodes:
            return False
        if self.only_changes:
            data = bytes(data)
            if self._last.get(can_id) == data:
                return False
            self._last[can_id] = data
        return True
