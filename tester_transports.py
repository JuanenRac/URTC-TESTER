# =============================================================================
# URTC Tester - CAN transports: SLCAN (serial), SocketCAN (Linux), python-can
# and the simulated board
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The transports themselves live in urtc_can/transports.py, a checked copy of the module the URTC tools share
(see urtc_can/urtc_common.lock.json), so a fix made there applies to every tool. This module is the one place
this program imports them from; what it adds is specific to the Tester: SocketCAN says its warnings in the
language of the window, the serial port is taken from this module's ``serial``, and every frame sent or read
through SLCAN or SocketCAN is counted in ``transport.stats`` for the bus-load display.
"""
import os  # noqa: F401  (tests redirect the sysfs paths through this name)
import time  # noqa: F401  (tests speed the transports up through this name)

try:
    import serial
    HAVE_SERIAL = True
except ImportError:
    serial = None
    HAVE_SERIAL = False  # SLCAN's constructor is what actually needs this - SocketCAN works fine without it

from tester_bus_monitor import BusStats
from tester_config import _
from urtc_can.transports import (  # noqa: F401
    MESSAGES,
    CanTransport,
    MockCAN,
    PythonCAN,
    PythonCANError,
    SLCANError,
    SocketCANError,
    TransportError,
    as_frames,
    detect_bitrate_listen_only,
    list_socketcan_interfaces,
)
from urtc_can.transports import SLCAN as _SharedSLCAN
from urtc_can.transports import SocketCAN as _SharedSocketCAN


class SLCAN(_SharedSLCAN):
    """The shared SLCAN transport, opening the serial port through this module's ``serial``."""

    def __init__(self, port, baud=115200, log=None, serial_module=None, settle_seconds=0.2):
        super().__init__(port, baud, log, serial_module=serial_module or serial, settle_seconds=settle_seconds)


class SocketCAN(_SharedSocketCAN):
    """The shared SocketCAN transport with its warnings translated into the language of the window."""

    def __init__(self, interface, log=None, socket_module=None):
        super().__init__(interface, log=log, socket_module=socket_module, translate=_)


def _instrument_with_bus_stats(cls):
    """Counts every frame this transport sends or successfully reads into a
    per-instance BusStats (`transport.stats`), whoever calls it."""
    original_read, original_send = cls.read_frame, cls.send_frame

    def read_frame(self, *args, **kwargs):
        frame = original_read(self, *args, **kwargs)
        if frame is not None:
            self.__dict__.setdefault("stats", BusStats()).record(len(frame[1]))
        return frame

    def send_frame(self, can_id, data, *args, **kwargs):
        result = original_send(self, can_id, data, *args, **kwargs)
        self.__dict__.setdefault("stats", BusStats()).record(len(data))
        return result

    cls.read_frame, cls.send_frame = read_frame, send_frame
    return cls


_instrument_with_bus_stats(SLCAN)
_instrument_with_bus_stats(SocketCAN)
