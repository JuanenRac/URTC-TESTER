#!/usr/bin/env python3
"""
URTC Tester - live CAN bus exerciser for the URTC (Universal Robot Tool
Controller) board.
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>

Licensed under the GNU General Public License v3.0 or later (GPL-3.0-or-later), matching the
URTC firmware and the flasher tool. See LICENSE in the repository root.

Connects over the same USB-CAN adapter/interface the flasher uses, asks
the board which of its 25 tool profiles it's currently jumpered for, and
shows only that tool's own controls and live telemetry - per CANBUS.TXT -
rather than one window trying to represent all 25 at once.

Shares its transport layer (SLCAN/SocketCAN) with urtc_flasher.py, since
both tools ultimately just need to get CAN frames on and off the same
kind of adapter - but this tool never touches flash: everything it does
is runtime commands and telemetry against the currently-running
application, nothing that can leave the board any less working than it
started.

This is the entry point only: it starts the Qt Quick deck (qt_tester.py with
assets/qml/TesterDeck.qml).  The rest lives in its own module:
tester_config.py (config/language/protocol constants), tester_transports.py
(SLCAN/SocketCAN), tester_bus_monitor.py (frame filter and bus statistics),
tester_selftest.py, tester_telemetry.py and tester_autodetect.py.
"""

import sys


def main():
    if "--legacy" in sys.argv:
        print(
            "Note: the classic Tkinter window has been retired; the Qt Quick deck starts instead.",
            file=sys.stderr,
        )
    try:
        from qt_tester import run_qtquick
    except ImportError as exc:
        print(
            "ERROR: URTC Tester needs PySide6 (Qt Quick). "
            "Install this repository's requirements.txt first. "
            f"Details: {exc}",
            file=sys.stderr,
        )
        return 2
    return run_qtquick()


if __name__ == "__main__":
    raise SystemExit(main())
