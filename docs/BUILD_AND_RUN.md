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

Keep diagnostic logs and exported bundles separate from source control; they
can contain device identifiers and operational data.
