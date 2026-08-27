# =============================================================================
# URTC Tester - CANBusMonitor: the one background thread reading frames
# off the transport, dispatching to registered handlers/sniffers
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
import threading
import time

from tester_config import _

class CANBusMonitor:
    """Owns the one and only background thread reading frames off the
    transport, dispatching each received frame to whichever callbacks are
    currently registered for its CAN ID. This exists because a live
    tester - unlike the flasher's one-request-at-a-time protocol - needs
    to watch several different telemetry IDs at once (temperature, RPM,
    endstops...) without them stepping on each other, and a serial port or
    raw socket can't safely be read from two places at once. Callbacks run
    on this background thread - they must only touch Tkinter state via
    root.after(), never touch widgets directly.
    """
    def __init__(self, transport, log, listen_only=False):
        self.transport = transport
        self.log = log
        self._handlers = {}  # can_id -> list of persistent callback(data) functions, registered by tool panels
        # Kept deliberately SEPARATE from _handlers above, even though
        # wait_for_one's own _capture callback is conceptually "just
        # another handler" - clear_all() (called by the GUI on every
        # tool-panel rebuild, i.e. every Detect) wipes _handlers wholesale,
        # and it's meant to: that's specifically the per-tool telemetry
        # registrations left over from whichever panel was showing before.
        # But if wait_for_one() shared that same dict, a clear_all() firing
        # while ANY wait_for_one() elsewhere is still blocked in
        # event.wait() - the bus health background loop's own periodic
        # poll, a self-test in progress, another panel's query button, all
        # of which run concurrently with the GUI thread that can trigger a
        # rebuild - would silently drop that in-flight wait's registration.
        # The real response frame would then arrive with nothing left
        # listening for it, and the wait would time out as if the board
        # never answered at all, even though it did. For the bus health
        # monitor specifically this is worse than a missed poll: a None
        # result there reads as "no error bit set", so a genuine ongoing
        # bus problem could get silently reported as "recovered" purely
        # because Detect happened to be clicked at the wrong moment.
        self._waiters = {}  # can_id -> list of one-shot callback(data) functions, used only by wait_for_one below
        self._sniffers = []  # callback(can_id, data) functions - called for EVERY frame, regardless of ID
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self.listen_only = listen_only  # mirrors the transport's own flag
        # (set at open_channel time) - checked here too, first, so every
        # caller across the whole GUI that goes through self.bus.send()
        # (which is all of them) gets a quiet no-op instead of an
        # SLCANError/SocketCANError bubbling up out of a button click.
        # wait_for_one's own send_after_register callbacks funnel through
        # this same send() too, so a query that can never get an answer
        # (nothing was actually transmitted to prompt one) just times out
        # normally rather than raising - the correct, expected outcome
        # while genuinely listen-only, not a bug to report.

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
        """One-off synchronous wait for a single frame on can_id, layered
        on top of the same registration mechanism everything else uses -
        never calls read_frame() directly, so this never races against
        the background thread's own reading.

        send_after_register, when given, is called with no arguments
        right after the callback is registered but before waiting - this
        closes the window where a fast enough response could otherwise
        arrive and get processed by the background thread before
        anything was listening for it, which would cause a false timeout
        on an otherwise-successful exchange. A caller that sends its
        request frame itself before calling this method instead of using
        send_after_register is still safe, just without that race closed
        for
        them specifically) since this parameter is optional."""
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



