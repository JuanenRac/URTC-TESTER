<!-- =============================================================================
URTC-TESTER - Architecture guide
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

# Architecture

URTC-TESTER is a desktop diagnostic application. `urtc_tester.py` starts the
UI; transport, configuration, shared panels, tools and bus-monitor concerns are
kept in their own modules. The UI must show the selected transport and current
connection state before any operator test is interpreted as physical evidence.

No captured result alone certifies hardware. A real test requires an identified
target, operator confirmation and its saved diagnostic bundle.
