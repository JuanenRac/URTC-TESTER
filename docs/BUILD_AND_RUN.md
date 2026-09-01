<!-- =============================================================================
URTC-TESTER - Build and run guide
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

# Build and Run

`build-test.bat` and `build-test.sh` are the validation paths and do not change
project version or CHANGELOG. `build_exe.bat` and `build_exe.sh` package the
desktop application after validation. Follow `requirements.txt` before running
`urtc_tester.py`.

The validation scripts syntax-check Python plus the Qt Quick diagnostics deck.
Confirm its visual layout from the desktop app; headless/offscreen graphics
drivers are not a reliable substitute for that visual check. The validation
path never opens a real CAN interface, sends a CAN frame, changes the
manifest, or changes CHANGELOG.

It also extracts every `uiText("KEY")` reference from the QML deck and
requires that key in each of the seven shipped language files. This catches a
missing visual translation without starting Qt or opening a CAN transport.

The Qt Quick deck's **Passive bus window** is a separate, bounded runtime
diagnostic: after connecting in listen-only mode it reads traffic for two
seconds, reports frame and CAN-ID counts, and retains a short visible sample.
It is disabled in active-check mode and has no transmit path.

The deck also shows the real legacy tool-profile catalogue. Its only
write-capable Qt Quick control is a deliberately narrow **one-shot motion**
operation for the existing motion profiles. It remains disabled until all of
these backend-enforced conditions are true: an active transport is connected,
listen-only mode is off, the selected profile exactly matches the reported
identity, and the profile is one of the supported motion profiles. Pressing
the action opens a second confirmation dialog before the established 0x120
motion command is emitted. All advanced actuator, configuration and per-tool
workflows remain in the established Tkinter panels until their individual
workflows have parity and physical evidence.

Keep diagnostic logs and exported bundles separate from source control; they
can contain device identifiers and operational data.
