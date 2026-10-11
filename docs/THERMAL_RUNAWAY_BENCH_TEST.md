# Thermal runaway bench test (URTC firmware 0.3.3+)

Copyright (C) 2026 JuanenRac (Electro Hobby 3D) - CC BY-SA 4.0

URTC firmware 0.3.2 added a thermal runaway guard (`thermal_guard.c` in the
URTC repo) and 0.3.3 lifetime thermal counters. Both are host-tested with a
simulated heater; this procedure is how to confirm them on a **real board**,
the first time it is brought up and after any change to the heater wiring.

> **Safety.** Do this on a bench, never on a robot. Use a T12 or a 3D hotend
> clamped to a non-flammable surface, keep a fire extinguisher at hand, never
> leave it unattended and be ready to cut the supply. The test *expects* the
> board to cut the heater - if it does not within the window below, cut power
> yourself.

## What the board must do

| Fault | How to provoke it on the bench | Expected `0x111` byte 4 |
|---|---|---|
| Heating with no rise | Pull the thermistor (hotend) out of the block, or run the T12 with the tip not seated, then set a target well above room temperature | `2` HEATING_NO_RISE within 40 s (hotend) / 20 s (T12) |
| Sag at target | Let the hotend reach and hold its target, then pull the thermistor out of the block | `3` DROPPED_AT_TARGET within 40 s |
| MAXTEMP | Only with a stuck heater simulated by an external supply - normally skip | `1` MAXTEMP |

In every case `0x111` byte 1 must read `1` (critical error latched), the
heater output must be off, and the lifetime counter must grow by exactly one.

## Steps with URTC Tester

1. Connect, run **Detect**, and press **Thermal counters** (F-RAM panel, or
   the Qt deck's F-RAM section). Note the fault count. If the answer is
   "No answer to 0x1AA", the board runs firmware older than 0.3.3.
2. Set the heater target from the tool panel and provoke one fault from the
   table above.
3. Within the window, the board state turns red with
   `THERMAL RUNAWAY: <fault>` (Detect again if the panel was not polling).
4. Press **Thermal counters** again: the count is one higher and *last fault*
   matches the code shown in step 3.
5. Power-cycle the board and query once more: the count must still be there
   (if it says "RAM-only", the F-RAM is not answering - fix that first).

`advanced_protocol.evaluate_thermal_runaway_bench_test(before, after, quick)`
implements this verdict for scripted runs: give it the 0x1AB answers from
steps 1 and 4 (decoded with `decode_thermal_stats`) and the 0x111 answer from
step 3 (`decode_quick_state`); it returns `(passed, reasons)`.
