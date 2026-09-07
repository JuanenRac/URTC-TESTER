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

## Advanced Qt Quick profile controls

After an active identity match, the Qt Quick deck selects controls by the
reported tool profile instead of exposing a generic raw-CAN sender. The
migrated operations reuse the existing production frame layouts:

- one-shot motion for the motion tools, solder wire feeder and crimping
  actuator;
- drill speed/direction, AOI ring mode, electromagnet state, spot/ultrasonic
  weld pulses, and paste-jetting configuration/pulse;
- watchdog-backed solder heater, laser (with an explicit software interlock
  checkbox), 3D-printer heater/layer fan, UV curing, and hot-air output.
- The printer profile also exposes its established one-shot hotend-fan and
  extruder frames. The heater hold path always sends zero extruder steps, so
  maintaining temperature cannot repeat a previously selected extrusion.

Every energising action requires the connected active transport, an exact
selected-profile/identity match and a second confirmation dialog. Watchdog
outputs use the established refresh intervals and send their documented
safe-off frame when stopped or before disconnect. The remaining profiles are
still presented honestly as telemetry-only, external-machine or
multi-packet/legacy workflows; they are not represented by fake controls.

| Profile family | Qt Quick status | Hardware-free evidence | Physical evidence still required |
| --- | --- | --- | --- |
| Motion, crimping and solder feeder | Migrated | payload/range tests | direction, travel and endstop safety |
| Drill, AOI, electromagnet | Migrated | payload/range tests | interlocks and telemetry |
| Spot/ultrasonic weld and paste jetting | Migrated | bounded pulse tests | contact gate, output and safe workpiece |
| Solder, laser, printer, UV and hot air | Migrated with watchdog | refresh/safe-off encoding tests | watchdog timeout and thermal/light output |
| Vacuum, scan probe and passive bus | Read-only | fixture decoder and passive-window logic | live telemetry shape and rate |
| Flying probe | Migrated config/trigger/result read | bounded request/response route | response ordering and probe hardware |
| Thermal inspection | Migrated calibrated 48-chunk capture | bounded sequential read and Qt grid | chunk order, sensor data and thermal scale |
| Conformal coating and press-fit | External-machine workflow | no CAN actuator route exists | integration at the owning controller |

The test-only telemetry fixture decoder is deliberately isolated in
`advanced_protocol.py` and is never connected to QML. A simulated value can
therefore prove byte interpretation in a unit test but cannot be mistaken for
a live sensor reading.

Keep diagnostic logs and exported bundles separate from source control; they
can contain device identifiers and operational data.
