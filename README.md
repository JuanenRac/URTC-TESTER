<p align="center">
  <img src="/images/URTC_TESTER_BANNER.svg" alt="URTC Tester Logo" width="100%">
</p>

# URTC Tester (Windows / Linux)

<p align="center">
  🇺🇸 <b>English</b> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### A live CAN bus exerciser for the URTC board: it shows only the controls and the telemetry of the tool head that is plugged in

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/UI-Qt%20Quick-38d4e6.svg" alt="Qt Quick">
  <img src="https://img.shields.io/badge/Tests-576-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Protocol-CAN-yellow.svg" alt="CAN">
</p>

---

**Honesty check - what actually runs today:** the CAN payload encoders for the migrated Qt Quick control families (`advanced_protocol.py`) are real and covered by the tests in `tests/` (`python -m pytest -q`). This repo's own CI (`.github/workflows/ci.yml`) runs them too, together with `ruff check`, `python -m mypy`, `tools/ci_validate.py`, a syntax compile of every `.py` file and the four `verify_qt_*.py` scripts, so a regression there fails the build. The four `verify_qt_*.py` scripts at the repo root (`verify_qt_custom_frame.py`, `verify_qt_telemetry_watch.py`, `verify_qt_utility_panels.py`, `verify_qt_selftest.py`) are real, deliberately-outside-`tests/` end-to-end checks against a fake transport with real cross-thread Signal delivery - all four pass with `QT_QPA_PLATFORM=offscreen python verify_qt_*.py`, which CI runs too. That's the honest ceiling of what's automatically verified: the transport layer, CAN ID/byte-layout handling, and the Qt Quick bridge logic are real and exercised against mocked frames, not real hardware - as "Known limitations" below already says, this was built with no USB access, so nothing here has been checked against a real board yet. `qt_tester.py` and `assets/qml/TesterDeck.qml` are the real, substantial implementation (thousands of lines combined), exercised by the tests with fake boards and by the verify scripts, never by a real board.

---

> **Safety and security status:** this ecosystem is not a certified safety system, and no populated URTC board exists yet. The bootloaders check firmware images with CRC32 and a shared-key HMAC-SHA256, not with an asymmetric signature (planned); the published application images are signed with the public development key (`signing_key_kind: dev`), so anyone can produce an image the bootloader accepts; nothing has been transmitted to a real board. Read the [security baseline](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md) and the [threat model](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md) before relying on any statement here for the safety of a person.

## 📋 At a glance

| | |
|---|---|
| Version | `0.4.3` |
| Maturity | Functional |
| Tests | 576 (`python -m pytest -q`) |
| Stack | Python / PySide6 / Qt Quick / live CAN bus diagnostics |
| Target | The PC of the person using it |
| On real hardware | Simulated only: tested against emulators, fakes or simulators; no run on real hardware is recorded for this version |

**Jump to:** [Overview](#-overview) · [Architecture](#-architecture) · [Features](#-features) · [Security](#-security--safety) · [Interfaces](#-interfaces) · [Quick start](#-quick-start) · [Testing](#-testing) · [Structure](#-repository-structure) · [Related](#-related-projects)

<!-- urtc-section:status_tester -->
## 🚦 Project status

🟢 done and verified · 🟡 works, with known limits · 🟠 half done or not verified · 🔴 not done or not working. Nothing is green if it never ran on real hardware.

| Part | Status | What the repository can show |
| --- | :---: | --- |
| Software | 🟡 | Works on a PC and against the simulator; never run against a real board. |
| Interface | 🟡 | The window runs and is checked against a simulated board; not tried with a real adapter. |
| Tests | 🟢 | The test suite passes in the CI on every push. |
| Real hardware | 🟠 | No run on a real board yet: the bench test is still pending. |
| Documentation | 🟡 | README in eight languages and reference documents; the translations were not reviewed by native speakers. |

<!-- /urtc-section:status_tester -->

## 🎯 Overview

A live CAN bus exerciser for the URTC board. It connects over the same
USB-CAN adapter the flasher uses, asks the board which of its 25 tool
profiles it's currently jumpered for, and shows only that tool's own
controls and telemetry - not one window trying to represent all 25 at
once. Everything it does is a runtime command or a telemetry read against
the currently-running application; it never touches flash, so there's
nothing here that can leave the board any less working than it started.

### Relationship to the flasher

This tool and [URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER) share the same transport layer (SLCAN and
SocketCAN classes are identical) since both ultimately just need to get
CAN frames on and off the same kind of adapter, but they do fundamentally
different jobs:

| | Flasher | Tester |
|---|---|---|
| Touches flash | Yes (that's the whole point) | Never |
| Talks to | The bootloader, mostly | The running application |
| Purpose | Update firmware | Exercise/verify a tool head's actual hardware |

If you're not sure which one you need: if the board is already running
firmware and you want to check a tool actually works (heater heats,
motor turns, LED lights up), you want this one.

## 🧩 Role in URTC

URTC-TESTER is the program that checks what a URTC tool head actually does while it runs its application: it connects over the same USB-CAN adapter as URTC-FLASHER, asks the board which of its 25 tool profiles it is jumpered for and shows only the controls and the telemetry of that tool, never a window that tries to represent all 25. Everything it does is a runtime command or a telemetry read; it never touches flash, so it cannot leave a board less working than it found it. The protocol it speaks is the one of URTC-COMMON, and URTC-WEB-STUDIO offers the same workflows in a browser.

## 🏛️ Architecture

<p align="center">
  <img src="images/architecture.svg" alt="URTC-TESTER architecture: who uses it, what it holds and what it depends on" width="100%">
</p>

How the parts of this repository fit together: who uses it, what it holds and what it depends on. The picture is drawn from `docs/architecture.json` and checked against the code.

<!-- urtc-section:updates -->
### How it updates

This program can look for a newer version of itself: the "Check for updates" button asks GitHub once and offers a signed package only if it is for your system and newer. Nothing is checked or installed on its own unless you turn the check on, and an update needs your confirmation. The package must match its SHA-256 and the signature of the releases key pinned in the program; the previous version is kept, and it is restored by itself if the new one does not start. `urtc-updater --cli package list|check|install|rollback` does the same from the command line for the flasher and the tester, and `install --file` works without a network.
<!-- /urtc-section:updates -->

## 🖼️ Screenshots

<!-- urtc-shots -->
Captured at 1920×1080 on a test bench, with sample data and no real installation behind them.

<table>
<tr>
<td width="50%" valign="top"><img src="images/screenshots/deck.png" alt="The window as it opens: the transport gate, the listen-only safety mode, the tool profiles and the identity and health checkpoints." width="100%"><br><sub>The window as it opens: the transport gate, the listen-only safety mode, the tool profiles and the identity and health checkpoints.</sub></td>
<td width="50%" valign="top"><img src="images/screenshots/heads.png" alt="Tool heads on the bus: a modelled bus with six heads, one in each state a head can be in (selected, address conflict, fault latched, in its bootloader, lost and ready)." width="100%"><br><sub>Tool heads on the bus: a modelled bus with six heads, one in each state a head can be in (selected, address conflict, fault latched, in its bootloader, lost and ready).</sub></td>
</tr>
<tr>
<td width="50%" valign="top"><img src="images/screenshots/help.png" alt="The Help window: the steps for using the program, written in the language of the window." width="100%"><br><sub>The Help window: the steps for using the program, written in the language of the window.</sub></td>
<td width="50%" valign="top"><img src="images/screenshots/updates.png" alt="The update window: a newer signed package is installed only after you confirm it." width="100%"><br><sub>The update window: a newer signed package is installed only after you confirm it.</sub></td>
</tr>
</table>
<!-- /urtc-shots -->

**Fault recorder, optional functions, rack bench and thermal view (new, checked with fakes only):** the deck reads the black box of the board (`0x1A8` / `0x1A9`) and saves it as CSV and JSON, automatically once for each error the board reports when that option is on; it switches the optional firmware functions (`0x1AE` / `0x1AF`, off by default, acting after the next power-up); it has a simulated tool rack with the serial protocol of URTC-SMART-RACK, the identity of each head (type and serial number) and an export of a status page; and it shows the thermal inspection image in false colour (a simulated image says so). The tool names and kinds now come from the shared tool profiles of URTC-COMMON. None of it has been used with a real board.

**Heater PID (new, checked with fakes only):** the deck reads the state of the heater PID of the firmware (`0x1B9` / `0x1BA`: the gains in force, the state and the output of the last control cycle), stores gains (0 to 600) and starts or aborts the relay autotune, which heats the tip around the current set-point of the soldering iron (100 to 445 C) and stores the gains it finds. Storing gains and starting the autotune ask for the usual confirmation; aborting does not. The simulated head of the command line (`--transport simulate`) answers these frames too. The function must be switched on first among the optional functions; none of it has been used with a real board.

These pictures are the real window, drawn without a screen as it opens (nothing connected, nothing sent). The guide goes through the deck, the Help window and the update window.

[Guide with pictures](docs/WINDOW_GUIDE.md)

## ✨ Features

### How it works

The window is laid out in three columns: left and center hold the
always-visible sections below (1-4, then 6), right holds section 5's
per-tool panel, which is the one part of the window that actually
changes based on what's detected. Splitting the always-visible sections
across two columns instead of stacking them all in one keeps the window
from growing tall enough to not fit on an ordinary screen as more of
these sections were added over time. The 3D printer's own tool panel
(the tallest of the 25) goes a step further and splits its own controls
into 2 sub-columns internally, for the same reason. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the module-level
architecture this section walks through.

**Connect** (section 1, identical to the flasher): pick Serial/SLCAN or
SocketCAN, the port/interface, optionally auto-detect the bitrate, then
Connect.

**Detection happens automatically on connect** (or click **Detect** to
redo it): the tool sends `0x110` (query active tool) and `0x7F8` (query
version), and uses the response to:
- Show which of the 25 tool profiles is active, and the board's overall
  state (any declared error, CAN bus fault, still-in-boot-splash).
- Show the reporting HardwareID and firmware version, flagging a mismatch
  if it doesn't match this project's own `THIS_HARDWARE_ID`.
- Build the **Tool Controls** panel on the right for that specific tool -
  and only that tool. Switching which tool is jumpered and detecting
  again tears down the old panel and builds the new one from scratch.

**Global Controls** (section 2, always visible regardless of which tool
is active): the status LED color override, the ring LED color and
on/off, and OLED display mode (`0x100`) - these apply to every tool, so
they don't move to the dynamic panel. In AOI Inspection mode specifically,
the ring's on/off here is ignored in favor of that tool's own strobe
control (per [docs/CANBUS.md](docs/CANBUS.md)) - color still applies either way.

**Expansion Board** (section 3, always visible): `CONN_EXPANSION`'s own
generic SPI bus and DIAG0 line - the raw passthrough every driver-
carrying expansion board variant shares. The ADS1115 and MLX9064x
sensors, and the crimping actuator's own driver, aren't controlled from
here - they live inside their own tool's own panel instead (Flying
Probe, Thermal Inspection, Crimping Actuator - see section 4
below), since which of those actually applies depends on which tool
profile is jumpered.

**Persistence F-RAM** (section 4, also always visible, but deliberately
separate from Expansion Board above): the FM24CL64B shares the OLED's
own hardware I2C2 bus - a core board component, not something wired to
`CONN_EXPANSION` at all. Grouping the two together would imply a connection between them
that isn't real - the expansion connector itself has no F-RAM, no EEPROM,
nothing non-volatile on it.
- **SPI passthrough**: type space-separated hex bytes (1-7 of them, e.g.
  `01 02 03`), hit Send, and see exactly what came back on MISO during
  that same transfer (`0x180`/`0x181`) - a raw byte transport, not
  TMC5160-register-aware, matching the firmware's own approach. Useful
  for exercising the bus itself before a specific expansion board's
  register protocol is worth building a dedicated panel for.
- **DIAG0 level**: **Query DIAG0** reads the current state of a TMC5160's
  stall/fault diagnostic line (`0x182`/`0x183`) - HIGH (inactive) or LOW
  (asserted). A simple polled read, not a live/pushed value - hit the
  button again to refresh it.
- **Persistence F-RAM**: **Query State** reads back whatever the board
  last saved before a power loss (`0x190`/`0x191`) - which tool it was,
  the setpoint, whether a critical error was active at the time.
  **Erase F-RAM...** wipes it (`0x192`, with a confirmation dialog first
  - this can't be undone).
- **Expansion board type**: **Query** shows which of the 7 possible
  `CONN_EXPANSION` configurations is currently set (`0x1A1` - see
  `EXPANSION.TXT`). Read-only here - set it from `URTC Flasher`'s own CAN
  OTA section instead, since it's a one-time hardware-configuration step,
  not something to change casually from a live diagnostic tool.
- **MLX9064x sensor variant**: **Query** shows which of the 3 MLX9064x
  family members (or none at all) is currently configured (`0x1A7` -
  see `CANBUS.md`) - only meaningful when the expansion board type
  above is an Advanced variant or Basic+MLX9064x. Read-only here, same
  reasoning as expansion board type above.
- **Free tool configuration**: **Query** shows the raw ID-jumper reading
  (0-31) alongside what the F-RAM's `free_tool_selection` register
  currently says (`0x1A3` - see `EEPROM.TXT` section 5) - only actually
  consulted by a board whose jumpers read 0x1F/11111b. Read-only here,
  same reasoning as expansion board type above - `URTC Flasher` is the
  only tool that writes it.
- **Peripheral type & serial number**: **Query** shows the fixed
  peripheral type (always URTC/0x03) alongside the currently-set device
  serial number (`0x1A5` - see `EEPROM.TXT` section 6), a host-assigned
  label for telling multiple otherwise-identical boards apart on the
  same CAN bus. Read-only here too - `URTC Flasher` writes the serial
  number, this tool only ever reads it back.

**Custom CAN Frame** (section 6, also always visible): a raw ID + hex
bytes entry with one-shot and periodic send - for a command that doesn't
have its own control here yet, or for testing something not (or not yet)
documented in `docs/CANBUS.md`. No validation beyond ID range and DLC≤8;
whatever this sends is exactly what goes on the bus. Same section also
opens the **Raw Bus Monitor** (see below).

**Run Self-Test** (next to Detect): runs a small set of safe, at-rest
communication checks for whichever tool is currently detected - confirms
the active-tool query and version query both respond, then (for tools
with telemetry) sends a safe setpoint/speed/power of 0 and checks the
expected telemetry arrives. Deliberately never sends anything that would
actually heat, fire, or spin at meaningful power - this verifies the
communication round-trip works, not that an actuator physically responds,
since confirming that needs a human watching anyway. Asks for
confirmation before sending anything. Tools with no telemetry (plain
motion) or that are purely event-driven (scan probe) get an info-only
note instead of a real pass/fail. **Coverage is partial**: only 7 of
the 25 tools have a defined self-test step (soldering iron, drill,
laser, 3D printer, AOI, vacuum, scan probe) - the other 18 tools don't
run any check when this button is pressed.

**Live temperature graphs**: the soldering iron and 3D-printer nozzle
panels both show a small rolling line graph alongside their live
temperature reading - a plain Qt Quick Canvas, not a new
dependency (matplotlib/pyqtgraph would break this tool's zero-dependency
policy beyond pyserial). Fixed Y-axis scale (0 to that tool's own
setpoint ceiling) rather than auto-scaling, so the trend is easy to read
at a glance rather than the scale shifting under it.

**Raw Bus Monitor** (opened from the Custom CAN Frame section): a
separate window showing every frame seen, any ID, independent of the
active tool panel - a live-scrolling table (Time/ID/DLC/Data/Δt),
Pause/Clear, and an approximate bus-load/frame-rate readout (updated
once a second; the load figure doesn't model bit-stuffing overhead, so
treat it as a rough diagnostic figure, not a certified measurement).
**Export .trc...**/**Export .asc...** save the currently-shown table as a
simplified PEAK PCAN-View / Vector CANalyzer-style trace file
respectively - close enough to be readable by most tools that expect
those formats, not guaranteed byte-identical to what the real
applications produce. If `urtc_custom_ids.json` exists next to this
script (optional, not included by default - `{"0x199": "My Sensor"}`),
the ID column shows that friendly name alongside the raw hex ID -
useful for anyone testing a custom expansion board's own traffic without
needing to modify this tool's source.

### Tool coverage

Every one of the 25 profiles has its own panel, built directly from
`docs/CANBUS.md`:

| Tool | Controls | Live telemetry |
|---|---|---|
| Soldering Iron | Setpoint temperature, on/off; wire feeder direction + step count (one-shot); feeder position query + reset to 0 | Actual temperature; feeder position (open-loop estimate) |
| Paste/Liquid Dispenser, Screwdriver, both Grippers, SMT Pick & Place, Vacuum Gripper (LG) | Direction + step count (one-shot move) | none (shared 0x120, no telemetry for any of these 7) |
| Vacuum Pickup | none | Analog reading, part-detected |
| Drill | Speed + direction | Actual RPM, endstop |
| AOI Inspection | Ring mode (off/strobe/continuous) + strobe period | Endstop |
| Laser Engraver | Power + laser-lock arm/safe (a firmware output, not a hardware interlock) | Endstop |
| 3D Printer | Nozzle setpoint, extruder direction/steps, layer fan power, hotend fan power | Hotend temperature, layer fan RPM, hotend fan RPM |
| Scan Probe | none | Impact event count + timestamp (max-priority `0x095`) |
| Electromagnet | Energize/release checkbox | none |
| Spot Welder | Pulse duration + Fire | none (fires only if the contact sensor reads HIGH first - see `docs/CANBUS.md`'s own `0x1C0`) |
| Conformal Coating, Press-Fit Inserter | none - informational panel only | none - both tool IDs have no CAN handler at all, their own actuator and sensor live on the robot's own mainboard, see `docs/TOOLS.TXT` |
| Flying Probe | Basic reading is automatic; advanced reading needs a raw ADS1115 config word (hex) + Trigger Conversion + Read Result | Basic onboard-ADC reading (automatic, `0x243`) |
| UV Curing | Power slider (0-255) + Send/Off | none |
| Hot Air Rework | Setpoint temperature, blower power, on/off | Live temperature (shares the soldering iron's own `0x135` telemetry and live graph - same physical thermal loop) |
| Crimping Actuator | Direction + step count (one-shot move, same shape as the shared motion tools above, but reaches an expansion board's own driver via `0x1F0` instead of the onboard `0x120`) | none |
| Thermal Inspection | Trigger Capture, Check Status, Read Thermal Image | 32x24 pixel heat-map canvas (blue-to-red gradient), pulled chunk-by-chunk over CAN on request - not a live video feed, see section 6 below |
| Solder Paste Jetting | PWM channel + frequency (Configure), then duty + duration (Fire Pulse) | none |
| Ultrasonic Welder | Pulse duration + Fire | none (same shape as Spot Welder, but no contact-sensor gate) |

**Communication watchdogs are handled for you.** The soldering iron,
Hot Air Rework (shares the same thermal loop and watchdog as the
soldering iron), laser, and 3D-printer nozzle each have a 250ms
watchdog in firmware; the layer fan has a 1000ms one. Checking the
relevant "Active" box doesn't just send the command once - it resends
automatically (150ms for the 250ms-watchdog tools, 400ms for the layer
fan) for as long as the box stays checked, the same way a real master
controller has to. Unchecking it sends a single zero/off frame and
stops. The hotend fan has no watchdog (a stall detector instead - see
`docs/CANBUS.md`), so it's a plain one-shot send.

**Convenience notes (software conveniences, not safety functions).**

- **STOP ALL OUTPUTS** (in both windows, available while connected with active checks armed) sends every known off command - the heaters, the laser, the drill, the UV lamp, the layer fan, the electromagnet release, the plain steppers and the crimper - whatever tool is fitted, and stops every refresh. The hotend fan is left running on purpose, because the nozzle may still be hot. This is a software command sent over the CAN bus, not an emergency stop: it cannot act if the bus, the adapter, the PC or the board fails.
- The one-shot weld pulses, the paste pulse and the crimp ask for a confirmation in the classic window too, as the Qt Quick deck always does.
- The drill and the UV lamp are refreshed like the laser and the heaters. While the 3D-printer heater is held, its 150 ms refresh carries 0 extruder steps, which the firmware reads as a stop order: an extruder move started in that state is cancelled within 150 ms, so move the extruder with the heater off until the firmware offers a mode that leaves the extruder alone.
- The port and the bit rate are remembered for the next session (`config.json`) and the Qt Quick deck has its own bit rate selector. **Auto-detect** first only listens at each rate (nothing is transmitted on a live bus) and asks at each rate only when the bus is completely silent.
- The Raw Bus Monitor can be limited to some CAN IDs (**ID filter**) and to frames whose data changed (**Only changes**).

#### 🔥 Thermal runaway bench test (URTC firmware 0.3.2+ / 0.3.3+)

Detect now shows *why* a board latched an error: `0x111` byte 4 (thermal
runaway guard: MAXTEMP, HEATING_NO_RISE or DROPPED_AT_TARGET) is shown in the
board state, and a reset caused by the hardware watchdog (`0x111` byte 5) is
logged. **Thermal counters** (F-RAM panel in both UIs) reads `0x1AA`/`0x1AB`:
lifetime thermal faults, total heater-on hours and the last fault. Answers
from older firmware (4-byte `0x111`, no `0x1AB`) are reported as "not
reported", never as zero. The step-by-step procedure to confirm the guard on
a real board is [`docs/THERMAL_RUNAWAY_BENCH_TEST.md`](docs/THERMAL_RUNAWAY_BENCH_TEST.md).

<!-- urtc-section:heads -->
### Several tool heads on one bus

The firmware can let several tool heads share one CAN bus (the multinode extension). It is **off by default**, and a bus with one head works exactly as before. The **Tool heads** window finds the heads, lists each with its address, tool and serial number, and shows its state: ready, selected, address conflict, fault latched, in its bootloader or lost. You select one, the program asks you to confirm, and only then does it send anything to that head; while several heads are on the bus, a command is refused until one is selected and has confirmed it. If the selected head is lost, every head is put in its safe state (a checkbox of the window switches that off). It has been tried against a model of the bus only, not against boards. See `docs/MULTINODE.md` in URTC-COMMON.
<!-- /urtc-section:heads -->

## 🔒 Security & Safety

| Risk | Defence |
|---|---|
| An order sent to a board that is not the tool the window shows | The panel of a tool is shown only for the tool the board itself reported, and each command is gated by an identity match |
| Transmitting without meaning to | The window starts in listen-only mode: it cannot transmit until active checks are deliberately armed, and each action that acts on the board asks for a confirmation in the window first |
| Damaging the board | The tester never touches flash: everything it does is a runtime command or a telemetry read against the application that is running |
| A log that someone could alter | The session export is a zip with the log, a manifest that names it by its SHA-256 and the diagnostics of the system |

None of this has been tried on a real board, and none of it is a certified safety function; see the limitations below.

## 🔌 Interfaces

Same as the flasher: a timestamped session log is written automatically
to `logs/` (safe to delete), and **Export Debug Bundle**
saves a `.zip` with the current on-screen log plus basic system
diagnostics (OS, Python version, current transport/port/bitrate, detected
tool) for handing to whoever's debugging a tool head issue.

### 🤖 Without a window: test plans

`python urtc_tester.py --headless COMMAND` runs the tester without a window, for a production line, a bench script or a CI job: `info` (who answers: tool, firmware, quick state), `selftest`, `run-plan FILE` and `validate-plan FILE`. A plan is a short JSON file of steps kept in `plans/` (expect a tool, no faults, a minimum firmware version, the self-test, a frame whose value lies in a range, a wait, a question for the person at the bench). The command writes a log of every frame and a result record that names the log by its SHA-256, the same record as the deck. A plan sends only queries unless it says `"actuation": true` and the operator adds `--allow-actuation`; the boot-loader, update, configuration and erase frames are never sent, a command that the firmware drops unless it is refreshed (a heater, a drill, a laser) can be repeated while the plan waits (`keepalive_ms`), and every output is switched off again after a plan that commanded something. `--transport simulate` plays a simulated tool head and `--transport replay --port FILE` a recorded `.trc` or `.asc` trace, so a plan can be tried without a board. Exit status: 0 passed, 1 a check failed, 2 the plan or the arguments are wrong, 3 the test could not be carried out. The text it prints is English, like the command line of the flasher. Details in [`docs/HEADLESS.md`](docs/HEADLESS.md). Nothing here has run against a real board.

**Plans in the window (new, checked with tests and the simulated head only):** the section TEST PLANS at the bottom of the right column of the deck lists the plans of `plans/`, runs the one you choose against the connected board with the same engine (not in listen-only mode, and only while nothing else reads the bus), shows each step as soon as it ends, asks the questions of a confirm step in a dialog and saves the log and the result record. A plan that commands outputs asks for a confirmation first and every output is switched off at the end; Cancel stops it after the step that is running.

**Check for updates.** The button "Check for updates" asks GitHub once for the latest release and, only if it carries a package for this system that is newer than the installed version, offers to download it. The package is accepted only if its SHA-256 and its Ed25519 signature (the key of the releases, pinned in the program) are valid; it is installed only after you confirm it, never while an output is on, and the previous version is kept so you can go back (and is restored by itself if the new one does not start). Nothing is ever checked or installed on its own: the check when the program opens is an option, off by default, and the confirmation can only be turned off in the same window after a warning.

**Replay a recorded trace.** "Open Trace" loads a `.trc` or `.asc` trace (the ones the bus monitor exports, or PCAN-View and CANalyzer ones) and plays its received frames into a list of their own, marked REPLAY, at 0.25x to 10x, with pause, stop and repeat; a silence longer than two seconds is shortened. A replay never transmits, never answers a request, never mixes with the monitor of the bus or with its export, and it will not play while a board is connected (it pauses itself if one connects). A file larger than 50 MB or with no received frame is refused and says so.

**Black box viewer.** The record read from the board, and any record saved earlier (`.json` or `.csv` written by this program, opened with "Open a saved record", no board needed), is drawn as the measured temperature and the set-point over time with a mark where the error flag was first set, and listed sample by sample with the flags in words. Every field must be a whole number in range and a record holds at most 67 samples; a file that is not a record is refused with the reason and the previous drawing stays.

**Without hardware:** a virtual board stands in for the adapter and the board. Start `python -m urtc_can.virtual_board`, then give its serial URL to the port (`--transport serial --port socket://127.0.0.1:7777`); the board answers the version query and the quick state like an application, so `info` and plans of queries run end to end with nothing connected. It is a model written from the protocol description, not a tool head: the self-test of a tool reports what it cannot read.

## 🚀 Quick start

Same pattern as the flasher:

```
pip install -r requirements.txt
python urtc_tester.py          # Windows
python3 urtc_tester.py         # Linux
```

### Visual command deck

The **Qt Quick** command deck is now the real default:
~~~
python urtc_tester.py
~~~
It uses the SLCAN/SocketCAN transports and starts in listen-only
mode, so it cannot transmit until you deliberately arm active checks. Every
one of the 25 tool profiles' own commands has real, confirmed coverage here
(motion, drill, AOI, electromagnet, spot/ultrasonic weld pulse, paste
jetting, flying probe, thermal inspection, the 5 watchdog-keepalive
actuators, vacuum/scan-probe telemetry), each gated the same way: an
identity match, an explicitly armed active mode, and a user confirmation in
QML before anything transmits. Nothing here has been checked against a real board yet - see "Known limitations" below.

The deck also shows the **live readouts** of the detected tool (temperature with a rolling graph and CSV export, RPM, endstops; they only listen, so they work in listen-only mode and next to a running output), runs the **self-test**, warns in the header when the **bus health check** (a query of the active tool every 3 seconds while nothing else uses the bus) sees a problem, and has an **About URTC Tester** dialog with the Readme, the License and the GitHub page, next to **Save Logs...**.

The header of the Qt Quick window has a language selector; the choice is saved and applies on the next start. It also queries and resets the position of the soldering iron's wire feeder (open-loop estimate; the reset asks for confirmation). The identity probe also shows the firmware patch number when the board sends it (URTC firmware 0.3.5 and newer); older firmware shows major.minor only.

The existing live-CAN diagnostic workflow now uses a dark navy/cyan command-deck surface: product header, high-contrast connection card, clear tool tabs, dark session log and visible progress channel. This visual and accessibility change does not alter passive monitoring or command routing, and none of it has been tried on a real board.

### Header and tools

- **Header** - the connection state, the bus-health warning, the language selector (the choice is saved and applies on the next start) and the version.
- **Save Logs...** and **EXPORT SESSION (LOG WITH HASH)** - the on-screen log as plain text, or a zip with the log, a manifest that names it by its SHA-256 and system diagnostics (see "Logs and debug bundles" below).
- **About URTC Tester** - version and author, with buttons for the **Readme** (in the language of the interface when a translation exists), the **License** and the project's **URTC GitHub** page.

### File structure

This tool is organized into modules by responsibility, purely for
readability - there's no functional difference between having them as
separate files versus one large one. See the
"📂 Repository Structure" section near the end of this document for
the full file-by-file breakdown.

**Language**: English by default. Chosen with the selector in the header of the window - switches the interface (labels, buttons, dialogs, and log messages) to any of the 8 available languages, saved
immediately to `config.json` next to this tool, applied on the next
launch. Translations live in plain text files under `language/`
(`english.lng`, `spanish.lng`, `italian.lng`, `french.lng`,
`german.lng`, `chinese.lng`, `japanese.lng`, `portuguese.lng`) as simple `KEY=Value`
pairs, one per line - lines starting
with `#` and blank lines are ignored, and a literal `\n` inside a value
becomes a real line break (used by the handful of multi-line dialog
messages). Generated from the catalog of URTC-COMMON (a translation is corrected there and the files are written again, never edited by hand), or a starting point for another language (add `language/<name>.lng`, add
`("<name>", "Native Name")` to `AVAILABLE_LANGUAGES` near the top of
`tester_config.py`, and set `"language": "<name>"` in `config.json`). A
key missing from a language file falls back to showing that key's own
name rather than crashing, and a missing or unreadable language file
(bad edit, wrong filename) falls back to English for the whole
interface - either way the tool stays usable while the mismatch gets
sorted out.

**Linux SLCAN/SocketCAN setup** (adapter reflash, serial permissions,
`ip link` bring-up) is exactly the same as the flasher's section 1 - see
[URTC Flasher's own README](https://github.com/JuanenRac/URTC-FLASHER)
sections 1 and 2 rather than duplicating it here.

<!-- urtc-section:compatibility -->
### Requirements & compatibility

Which versions of the URTC programs work together, and which protocol version each one speaks, is listed in the compatibility table that URTC-COMMON generates: [docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md).
<!-- /urtc-section:compatibility -->

## 🧪 Testing

The suite has 576 tests (`python -m pytest -q`; with Qt on a machine with no screen, `QT_QPA_PLATFORM=offscreen`; the ones that need PySide6 skip without it): the CAN payload encoders and decoders of every tool family, the SLCAN and SocketCAN transports against fakes, the identity probe, the self-test, the watchdog keepalives, the bus-health check, the test plans and the headless mode, the session export with its hash, the language files and the Qt Quick panels. Four scripts at the root (`verify_qt_*.py`) drive the Qt Quick panels end to end with a real Qt event loop. CI also runs `ruff check`, `python -m mypy` and `tools/ci_validate.py`. None of it has run against a real board.

## 🏗️ Build & Release

Or build a standalone binary: `build_exe.bat` on Windows, `./build_exe.sh`
on Linux. Both clean `build/`/`dist/` first and bundle `assets/` (the
banner and icon) into the executable - see
[docs/BUILD_AND_RUN.md](docs/BUILD_AND_RUN.md) for the non-versioning
`build-test.bat`/`build-test.sh` validation path these packaging scripts
build on, and the flasher's own README for the fuller reasoning behind
the packaging scripts themselves, since it applies identically here.

**Version:** `TESTER_VERSION` (in `tester_config.py`, shown in the title bar, the About dialog, the session logs and the debug bundles) follows `MAJOR.MINOR.PATCH` and is raised only by the explicit `python bump.py` step. Running from source (`python urtc_tester.py`) and building (`build_exe.bat` / `build_exe.sh`) never touch it. See `CHANGELOG.md` for the version history.

## 📂 Repository Structure

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of URTC-TESTER" width="100%">
</p>

<details>
<summary>Text version of the tree</summary>

```text
URTC-TESTER/
├── urtc_tester.py                                     entry point
├── qt_tester.py                                       the Qt Quick deck
├── tester_*.py                                        transports, monitor, self-test, plans, telemetry
├── advanced_protocol.py                               pure CAN payload encoders
├── verify_qt_*.py                                     end-to-end checks of the Qt panels
├── urtc_can/                                          protocol, transports and updates (copy)
├── urtc_ui/                                           interface helpers (copy)
├── tests/                                             one test file per area
├── plans/                                             example test plans (JSON)
├── language/                                          the eight .lng language files
├── assets/                                            QML, banner and icon
├── docs/                                              architecture, build and run
├── logs/                                              session logs (kept out of Git)
├── tools/                                             build check and shared tools
├── images/                                            banner and the pictures of this README
├── .github/                                           CI workflow, issue and pull-request templates
├── test.sh test.bat                                   run the tests
├── run.sh run.bat                                     start the program
├── build-test.sh build-test.bat                       build and test scripts that change nothing in the repository
├── urtc.project.json                                  manifest: version, role, maturity and build command
├── CHANGELOG.md                                       what changed in each version
├── SECURITY.md SUPPORT.md LICENSE                     security policy, support and license
├── CONTRIBUTING.md CODE_OF_CONDUCT.md                 how to contribute and the code of conduct
├── .gitattributes .gitignore                          Git settings
├── build_exe.sh build_exe.bat                         standalone program (PyInstaller)
├── bump.py bump_version.py bump_manifest_version.py   scripts that raise the version
├── requirements*.txt requirements*.lock               dependencies, with their locks
├── mypy.ini ruff.toml .coveragerc                     type check, lint and coverage settings
├── urtc_i18n.lock.json                                lock of the generated language files
└── NOTICE LICENSE.md                                  copyright notice and documentation license
```

</details>

The annotated list of every source file, one line each, is in [docs/SOURCE_MAP.md](docs/SOURCE_MAP.md).

## 🗺️ Roadmap & Known limits

This tool's evidence contract - what counts as pass/fail/unknown, why
absent evidence is always unknown rather than pass, and why it grants no
firmware-flash authority of its own - is documented in
[docs/INTEGRATION_CONTRACT.md](docs/INTEGRATION_CONTRACT.md).

- **Not tested against real hardware.** Every piece here - the transport
  layer, the CAN ID/byte-layout handling, the watchdog keepalive timing -
  was checked in isolation (mocked frames, a real subprocess for timing
  where relevant) but the environment that built this has no USB access.
  Treat a first real session with the same caution the flasher's own
  README asks for.
- **One tool panel at a time, by design**, not a current limitation to be
  removed later - see the intro above for why.
- **Global LED colors are a straight override**, not a live readback -
  there's no telemetry for what the status/ring LEDs are actually
  currently showing, only what was last commanded.
- **Thermal Inspection's own thermal image is pull-based, not a
  live feed.** Reading a full frame means requesting all 48 chunks
  sequentially over CAN (worst case, MLX90640/MLX90642's own
  resolution) - this can take a few seconds, and there's no streaming
  push mode in this tool's own CAN protocol to make it faster. A capture has to be triggered first; Read Thermal Image then waits up to two seconds for the sensor to report ready and, if it does not, reads nothing, because the firmware does not answer chunk requests before that. The sensor fitted is asked first (48 chunks for the MLX90640/MLX90642, 12 for the MLX90641), and a chunk that is lost leaves its pixels blank instead of shifting the rest of the image.
- **Run Self-Test only covers 7 of the 25 tools** (soldering iron,
  drill, laser, 3D printer, AOI, vacuum, scan probe) - see "How it
  works" above for the full explanation. The other 18 tools get no
  automated check from that button; verifying them still means
  watching the actual hardware respond to their own panel's controls.

## 🌍 Languages

README and texts exist in English, Spanish, French, Italian, German, Chinese, Japanese and European Portuguese.

## 🔗 Related Projects

URTC is made of independent repositories, each with its own version, tests and README. This is the family, by group:

* **URTC Tool Platform:**
  * [URTC](https://github.com/JuanenRac/URTC) - firmware of the tool-head board (25 tool profiles, CAN bootloader) and the CAN protocol reference.
  * [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON) - the CAN protocol written once as data (specification, generated tables, conformance vectors) and the code the programs share.
  * [URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER) - desktop tool that updates the board firmware over CAN or over SWD/JTAG.
  * [URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY) - gateway in front of the CAN bus: lets only listed identifiers through, limits their rate and asks for a session key.
  * [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK) - hardware-independent C logic and command protocol for a tool rack with pre-heating and lifecycle tracking.
  * **URTC-TESTER** (this repository) - desktop live CAN-bus tester that shows the controls and telemetry of the tool profile a board reports.
  * [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL) - sensor-frame protocol in C and a Python thermal/RGB companion for an inspection tool head.
  * [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO) - browser app that flashes and tests the board over Web Serial and SLCAN, with nothing to install.
* **Ecosystem Operations:**
  * [URTC-DEVTOOLS](https://github.com/JuanenRac/URTC-DEVTOOLS) - the shared repository tools of the family as one versioned set, with a lock file that tells a copy that was edited from one that fell behind.
  * [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS) - architecture, interfaces, security baseline and generated catalogue of the ecosystem, plus the tools that compare all repositories.
  * [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER) - desktop tool that detects, installs and updates the repositories of the URTC family, one explicit action at a time.

**Sister projects (independent, with the same base and tools):**

* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - sister project: the documentation hub of HYDRA-UMC, an independent ecosystem that shares this one's base and tools
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - sister project: the documentation hub of A.R.M.O.R., the security ecosystem, also independent and on the same base
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - the profile and the status dashboard of all the ecosystems

## 📚 Documentation

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — tech stack and coding guidelines for a pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — the standards of behavior expected in this community.
- **[SECURITY.md](SECURITY.md)** — how to report a vulnerability, and this project's own real security focus areas.
- **[SUPPORT.md](SUPPORT.md)** — where to ask questions and report bugs.
- **[LICENSE.md](LICENSE.md)** — this project's own license.

## 🤝 Contributing & Community

* Before a pull request run `URTC_CI=1 python tools/ci_validate.py`: it must pass. See [CONTRIBUTING.md](CONTRIBUTING.md) and the [code of conduct](CODE_OF_CONDUCT.md).
* The README exists in eight languages: a change to the text is made in all eight files, and the sections shared with other repositories are written by `tools/readme_sections.py` of URTC-COMMON.
* A change to the CAN protocol starts in URTC-COMMON (`spec/can_protocol.json`) and reaches this repository through the checked copy.
* Do not describe as working on a board what has only been built.
* Report a vulnerability privately: [SECURITY.md](SECURITY.md). Questions, ideas and reports: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTHOR

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENSE

License: **GPL-3.0-or-later** for the source code, **CC BY-SA 4.0** for this
documentation - see `LICENSE` in this repository, or the "License and
Copyright Notices" section at the end of this document.

URTC Tester is (c) 2026 JuanenRac (Electro Hobby 3D). This notice must
be included in any distributions of this project or derivative works.

This project consists of source code and its own documentation, made
available under different licenses - each suited to what it actually
covers:

1. The source code (`urtc_tester.py` and every `tester_*.py` module)
   and any binary built from it via `build_exe.bat`/`build_exe.sh` are
   available under the **GNU General Public License v3.0 or later (GPL-3.0-or-later)**.
   Full text at https://www.gnu.org/licenses/gpl-3.0.html.

2. The documentation (this README and its own translations -
   `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`,
   `README_zho.md`, `README_jpn.md`, `README_por.md`, and the guides in `docs/`)
   is available under **Creative Commons Attribution-ShareAlike 4.0
   International (CC BY-SA 4.0)**. Full text at
   https://creativecommons.org/licenses/by-sa/4.0/.

This tool is the live CAN-bus diagnostic companion to the
[URTC (Universal Robot Tool Controller)](https://github.com/JuanenRac/URTC)
project - see that project's own repository for the board firmware,
hardware designs, and full protocol documentation this tool exercises
against. URTC's own firmware is GPL-3.0-or-later and its hardware designs are
CERN-OHL-S v2; this tool's own license here doesn't extend to that
separate project, and vice versa. A web-based alternative covering
similar ground also exists at
[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO).

If you build on this project, keep the licensing split in mind: code
changes should stay GPL-3.0-or-later, documentation derivatives should stay CC
BY-SA - each with attribution back to this project and its author.
