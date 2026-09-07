<!--
=============================================================================
URTC-TESTER - CAN bus protocol reference index
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
=============================================================================
-->

# URTC-TESTER CAN bus protocol reference

## Canonical protocol source

This desktop tester uses the public URTC CAN-bus command map. The canonical,
versioned wire-protocol source belongs to the URTC firmware repository:

[URTC CAN bus command map](https://github.com/JuanenRac/URTC/blob/main/docs/CANBUS.TXT)

## Integration rule

Do not duplicate frame definitions here: a copied table would silently drift
from the firmware. Before adding a tester control, verify its CAN ID, DLC,
byte order, tool applicability, interlock and response frame against the
canonical document, then add deterministic parser and UI tests.

An unknown or incomplete frame definition must be displayed as unsupported;
it must never be guessed or represented as a passing physical test.
