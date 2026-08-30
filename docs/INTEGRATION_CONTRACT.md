<!-- =============================================================================
URTC-TESTER - Integration contract
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

# Integration Contract

Inputs are selected tester settings and transport observations. Outputs are
displayed test results and optional diagnostic bundles. Every result must carry
the selected transport, timestamp and pass/fail/unknown state; absent evidence
is unknown, never pass.

The project does not grant firmware-flash authority. Use URTC-FLASHER for a
separate, operator-controlled firmware workflow.
