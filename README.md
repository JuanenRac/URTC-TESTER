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
  <a href="README_jpn.md">🇯🇵 日本語</a>
</p>


<p align="left">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/UI-Tkinter%20%7C%20Qt%20Quick-38d4e6.svg" alt="Tkinter and Qt Quick">
  <img src="https://img.shields.io/badge/Protocol-CAN-yellow.svg" alt="CAN">
</p>


**Version:** 0.1.1 · **Author:** JuanenRac (Electro Hobby 3D) &lt;electrohobby3d@gmail.com&gt;

License: **GPL-3.0** for the source code, **CC BY-SA 4.0** for this
documentation - see `LICENSE` in this repository, or the "License and
Copyright Notices" section at the end of this document.

A live CAN bus exerciser for the URTC board. It connects over the same
USB-CAN adapter the flasher uses, asks the board which of its 25 tool
profiles it's currently jumpered for, and shows only that tool's own
controls and telemetry - not one window trying to represent all 25 at
once. Everything it does is a runtime command or a telemetry read against
the currently-running application; it never touches flash, so there's
nothing here that can leave the board any less working than it started.

## 1. 🆚 Relationship to the flasher

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

## 2. 📦 Install and run

Same pattern as the flasher:

```
pip install -r requirements.txt
python urtc_tester.py          # Windows
python3 urtc_tester.py         # Linux
```

Or build a standalone binary: `build_exe.bat` on Windows, `./build_exe.sh`
on Linux. Both clean `build/`/`dist/` first and bundle `assets/` (the
banner and icon) into the executable - see the flasher's own README for
the fuller reasoning behind these scripts, since it applies identically here.

**Versioning:** `TESTER_VERSION` (in `tester_config.py`, shown in the
title bar, About dialog, session logs, and debug bundles) follows
`MAJOR.MINOR.PATCH`. Both build scripts auto-increment it right before
every real build via `bump_version.py`, base-10 "odometer" style: PATCH
+1, carrying into MINOR once PATCH passes 9 (e.g. `0.1.9` → `0.2.0`).
Running from source (`python urtc_tester.py`) never touches it - only an
actual `build_exe.bat`/`build_exe.sh` run does. MAJOR is never bumped
automatically, only by hand. See `CHANGELOG.md` for the version history.

**On startup**, the banner shows centered on screen for 5 seconds before
the main window appears, rather than living inside the window itself -
same as the flasher, and for the same reason (keeps the window itself
compact). The window/taskbar icon is likewise a small standalone design,
not the banner shrunk down.

The connection panel also shows the official animated HYDRA-UMC mark. Its
maintained SVG source is `assets/HYDRA_UMC_ICON.svg`; twelve bundled PNG
frames preserve the animation in Tkinter and in the standalone executable
without adding a runtime GUI dependency. The native URTC window/taskbar icon
remains static by design.

### Visual command deck

The shared **Qt Quick** command deck is available for real connection,
listen-only monitoring and an explicitly armed identity probe:
~~~
python urtc_tester.py --qtquick
~~~
It uses the production SLCAN/SocketCAN transports. It starts in listen-only
mode, so it cannot transmit until you deliberately arm active checks; that
probe sends only the documented active-tool and version queries. The default
Tkinter interface remains the complete tool while its 25 per-tool control
panels are migrated safely.

The established live-CAN diagnostic workflow now uses a dark navy/cyan
command-deck surface: product header, high-contrast connection card, clear
tool tabs, dark session log and visible progress channel. This visual and
accessibility improvement does not change passive monitoring, command routing
or any hardware safety boundary.

### Menu bar

- **File** - Save Logs (the on-screen log as plain text; for a fuller
  bundle including system diagnostics, see "Logs and debug bundles"
  below instead), and Exit.
- **Language** - switch between the 5 available languages (see
  "Language" above for how translations work).
- **Help** - Readme (opens this file in a read-only viewer window;
  picks up a translated version automatically once one exists for the
  current language), URTC GitHub (opens the project's repository in
  your browser), License (this tool's GPL-3.0 license, read from the
  repository's own `LICENSE` file), and About (version and author).

### File structure

This tool is organized into modules by responsibility, purely for
readability - there's no functional difference between having them as
separate files versus one large one. See the
"📂 Repository Structure" section near the end of this document for
the full file-by-file breakdown.

**Language**: English by default. Switched via the **Language** menu
(in the menu bar at the top of the window) rather than a dropdown in
the main window - switches the interface (labels, buttons, dialogs,
and log messages) to any of the 5 available languages, saved
immediately to `config.json` next to this tool, applied on the next
launch. Translations live in plain text files under `language/`
(`english.lng`, `spanish.lng`, `italian.lng`, `french.lng`,
`german.lng`) as simple `KEY=Value` pairs, one per line - lines starting
with `#` and blank lines are ignored, and a literal `\n` inside a value
becomes a real line break (used by the handful of multi-line dialog
messages). Editable directly if a translation needs correcting, or as a
starting point for another language (add `language/<name>.lng`, add
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

## 3. ⚙️ How it works

The window is laid out in three columns: left and center hold the
always-visible sections below (1-4, then 6), right holds section 5's
per-tool panel, which is the one part of the window that actually
changes based on what's detected. Splitting the always-visible sections
across two columns instead of stacking them all in one keeps the window
from growing tall enough to not fit on an ordinary screen as more of
these sections were added over time. The 3D printer's own tool panel
(the tallest of the 25) goes a step further and splits its own controls
into 2 sub-columns internally, for the same reason.

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
control (per `docs/CANBUS.md`) - color still applies either way.

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
temperature reading - a plain Tkinter Canvas widget, not a new
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

## 4. 🧰 Tool coverage

Every one of the 25 profiles has its own panel, built directly from
`docs/CANBUS.md`:

| Tool | Controls | Live telemetry |
|---|---|---|
| Soldering Iron | Setpoint temperature, on/off; wire feeder direction + step count (one-shot); feeder position query + reset to 0 | Actual temperature; feeder position (open-loop estimate) |
| Paste/Liquid Dispenser, Screwdriver, both Grippers, SMT Pick & Place, Vacuum Gripper (LG) | Direction + step count (one-shot move) | none (shared 0x120, no telemetry for any of these 7) |
| Vacuum Pickup | none | Analog reading, part-detected |
| Drill | Speed + direction | Actual RPM, endstop |
| AOI Inspection | Ring mode (off/strobe/continuous) + strobe period | Endstop |
| Laser Engraver | Power + interlock arm/safe | Endstop |
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

## 5. 📋 Logs and debug bundles

Same as the flasher: a timestamped session log is written automatically
to `logs/` (safe to delete), and **Export Debug Bundle**
saves a `.zip` with the current on-screen log plus basic system
diagnostics (OS, Python version, current transport/port/bitrate, detected
tool) for handing to whoever's debugging a tool head issue.

## 6. ⚠️ Known limitations

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
  push mode in this tool's own CAN protocol to make it faster. A
  capture has to already be triggered and reported ready (Check Status)
  before Read Thermal Image returns real data - reading too early just
  paints whatever the sensor's own buffer happened to hold last.
- **Run Self-Test only covers 7 of the 25 tools** (soldering iron,
  drill, laser, 3D printer, AOI, vacuum, scan probe) - see "How it
  works" above for the full explanation. The other 18 tools get no
  automated check from that button; verifying them still means
  watching the actual hardware respond to their own panel's controls.

## 📂 Repository Structure

The `assets/` directory also contains `HYDRA_UMC_ICON.svg`, the maintained
animated vector source, and `hydra_umc_icon_frames/`, its twelve bundled
Tkinter PNG frames. `tools/render_hydra_umc_icon_frames.py` regenerates them
from the SVG during development; it is not required to run the application.

```
/
├── urtc_tester.py             Entry point - CLI-free startup and the splash screen
├── qt_tester.py                Qt Quick front end - bounded, read-only-by-default `--qtquick` command deck
├── tester_config.py            Config/language/protocol constants (CAN IDs, tool
│                                names, MOTION_TOOL_IDS, AVAILABLE_LANGUAGES,
│                                EXPANSION_BOARD_TYPES)
├── tester_transports.py        SLCAN and SocketCAN transport classes
├── tester_bus_monitor.py       Background CAN read thread (CANBusMonitor)
├── tester_gui_core.py          TesterGUI core - connection, detection, window
│                                lifecycle, and the menu bar; the class the 3
│                                mixins below combine into
├── tester_common_panels.py     CommonPanelsMixin - global/F-RAM/expansion/
│                                self-test/bus-monitor/custom-frame panels
│                                (the always-visible sections)
├── tester_panel_helpers.py     PanelHelpersMixin - shared utilities every tool
│                                panel builder uses
├── tester_tool_panels.py       ToolPanelsMixin - 19 tool-specific panel builders
│                                covering all 25 tool profiles (several tools
│                                share one builder, e.g. `_build_motion_panel`
│                                alone covers 7 of them)
├── advanced_protocol.py        Pure CAN payload encoders for the migrated Qt
│                                Quick control families - hardware-free tests
├── hydra_umc_animation.py      Animated HYDRA-UMC identity widget for Tkinter
├── hydra_umc_deck_widgets.py   Rounded HYDRA-UMC command-deck widgets shared
│                                by the live diagnostic surfaces
├── tests/
│   └── test_advanced_protocol.py   Hardware-free tests for advanced_protocol.py's encoders
├── requirements.txt            pyserial>=3.5 (Tkinter tester) + PySide6>=6.8,<7 (`--qtquick` deck)
├── build_exe.bat               Standalone Windows binary build script (PyInstaller)
├── build_exe.sh                Same, for Linux
├── build-test.bat              Non-versioning build/compile check
├── build-test.sh                Same, for Linux
├── bump_version.py             Odometer-style version bump, run by the build scripts
├── bump_manifest_version.py    Syncs hydra-umc.project.json's version to the native one (--sync)
├── URTC_Tester.spec            PyInstaller spec used by both build scripts
├── assets/
│   ├── URTC_APP_ICON.svg       Window/taskbar icon source (small standalone design)
│   ├── URTC_LOGO_TESTER.svg    Startup banner source
│   ├── HYDRA_UMC_ICON.svg      Maintained animated HYDRA-UMC vector source
│   ├── hydra_umc_icon_frames/  Twelve bundled Tkinter PNG frames rendered from the SVG above
│   ├── qml/
│   │   └── TesterDeck.qml      Qt Quick UI for the bounded --qtquick command deck
│   ├── urtc_icon.ico           Windows icon, built from URTC_APP_ICON.svg
│   ├── urtc_icon.png           Same, PNG form (Linux)
│   └── urtc_tester_banner.png  Startup banner PNG, rendered from the SVG above
├── images/
│   ├── URTC_LOGO_TESTER.svg    Logo banner shown at the top of this README
│   └── URTC_TESTER_V1_1.png    Screenshot of the tool's main window (see Photos below)
├── language/
│   ├── english.lng             Default language, plain-text KEY=Value strings
│   ├── spanish.lng
│   ├── italian.lng
│   ├── french.lng
│   ├── german.lng
│   ├── japanese.lng
│   └── chinese.lng
├── logs/                       Session logs written here at runtime (safe to delete)
├── LICENSE                     Full license text - see License and Copyright
│                                Notices below
├── README.md                   This file
├── README_spa.md               Spanish translation
├── README_ita.md               Italian translation
├── README_fra.md               French translation
├── README_deu.md               German translation
├── README_zho.md               Chinese translation
├── docs/
│   ├── ARCHITECTURE.md
│   ├── BUILD_AND_RUN.md
│   ├── INTEGRATION_CONTRACT.md
│   └── CANBUS.md
├── tools/
│   ├── ci_validate.py                    Manifest/CHANGELOG/docs validation used by CI
│   └── render_hydra_umc_icon_frames.py   Regenerates assets/hydra_umc_icon_frames/ from the SVG (dev-only)
└── README_jpn.md               Japanese translation
```

## 📸 Photos

<p align="center">
  <img src="images/URTC_TESTER_V1_1.png" alt="URTC Tester window" width="700">
</p>

## 🔗 Related Projects

This project is part of the HYDRA-UMC robotics ecosystem by the same author (JuanenRac / Electro Hobby 3D). Worth knowing about, since a request might actually be about one of these rather than this repository.

**Parent Project**
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware for the physical Universal Robot Tool Controller PCB, 25+ tool profiles over CAN bus; the parent this repo is one specific tool of, within its own CAN-bus tooling family.

**Sibling Projects** — the other tools of URTC's own CAN-bus tooling family
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — desktop GUI flashing tool for URTC boards, CAN-OTA plus full-chip SWD/JTAG.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browser-based alternative to URTC-TESTER via the Web Serial API, no local install needed.

**Directly Related**
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — fleet CLI with a real, stable exit-code contract, a genuine live client of HYDRA-UMC-SERVER's own API — runs fleet-wide audits (the `audit` command) across every tool head at once, going beyond the single-board scope this tester covers.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware plus a real Python vision companion for a thermal/RGB inspection tool head — complements this project's live CAN-bus diagnostics with its own visual quality-assurance checks on the tool head.

**Also Part of the Ecosystem**

*Core Hardware & Platform*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — the physical robot-arm motherboard: CM5 host + dual-core STM32H745, orchestrating up to 8 tool arms over CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — reproducible Raspberry Pi OS product layer for the CM5: read-only agent, validated config/profiles, WiFi first-contact provisioning.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — the shared JSON-Schema contract and safety-gate boundary every bridge validates its commands against.

*Core Backend & Clients*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — the real headless backend (REST/WebSocket) every control client actually talks to.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — web control dashboard with real-time multi-robot 3D visualization.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — desktop (PySide6) swarm command center for multiple servers at once, packaged as a standalone executable.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — native Android control app with biometric login and a paired Wear OS companion.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS control app (Flutter) with real-time WebSocket sync.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native touch UI for the onboard 7" DSI touchscreen, embedded on the CM5 itself.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — desktop graphical URDF creator/editor that pushes finished models into STUDIO's own catalog.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — coordination boundary for AGV/AMR fleets via a real VDA 5050 MQTT publisher.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — high-level CNC-cell coordinator with real GRBL status/control-byte access.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — coordination boundary for legged/humanoid droids, with a real Boston Dynamics Spot command sender.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — laser-cell safety coordinator reading 3 real key/enclosure/interlock GPIO safeguards.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — safe high-level board-flow coordinator for OpenPnP pick-and-place.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — safe coordination boundary for Moonraker/Klipper 3D printers, with real gated job commands.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — safety coordinator with a real, lazily-imported rclpy ROS 2 transport.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — coordination boundary for camera-equipped UAVs, with a real MAVLink command sender.

*Vision AI Node (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — integration hub for the Hailo-8 vision pipeline, with a real per-stage hardware-readiness check.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — real compiled-model registry with Hailo-architecture/checksum safe-load verification.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — real GStreamer pipeline + MediaMTX config generator with a real HailoRT integration boundary.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — real Position-Based Visual Servoing correction law, safety-gated on upstream zone state.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — real zone-breach checking and E-STOP requesting, with calibration-freshness enforcement.

*Cognitive AI Node (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — integration hub for the Hailo-10 cognitive pipeline (LLM/VLA/voice orchestration).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — real action-token encoding/decoding and trajectory generation for a Vision-Language-Action model.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — real voice front-end (VAD + intent parser) with a bounded, confirmation-gated Watch relay.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — real rule-based task decomposition and semantic error recovery over MCU error codes.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — real stdlib-only TF-IDF document search over this ecosystem's own Markdown docs.

*Orchestration & Swarm*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — integration hub with a real gRPC/Protobuf health-report contract and mission state machine.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — real priority-based job queue with deduplication, over a real HTTP API.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — real gRPC-based fleet health watchdog with retry/backoff and identity-mismatch detection.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — real RRT-based 3D path planner with real obstacle/workspace collision validation.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — real CRDT LWW-Element-Map state sync, property-tested for multi-cell convergence.

*Digital Twin & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — integration hub for the digital-twin engine, with a real version-compatibility sync contract.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — real hardware-in-the-loop safety interlock routing commands between simulation and real hardware.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — real forward kinematics and joint-limit validation over a real URDF subset.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — real procedural 2D scene generator with YOLO/COCO annotation export.

*Data & Analytics*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — real sqlite3-backed time-series store with a real ingest/query HTTP API.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — real FFT + statistical baseline anomaly detector with drift monitoring.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — real OEE/availability calculation over DATALAKE history, with reproducible CSV export.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — real CAN/WebSocket ingestion pipeline into DATALAKE, with sequence deduplication.

*Industrial Gateway*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — integration hub relaying to industrial protocols, with a real command allowlist/backpressure layer.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — real OPC-UA address space, verified with a real binary-protocol client session.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — real MQTT broker with optional per-client authentication and topic ACLs.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — real MTConnect `/probe` and `/current` XML endpoints with degraded-mode output.

*Complementary Tools & Ecosystem Operations*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — Smart Summaries and Anomaly Highlighting panels over DATALAKE/ANOMALY-DETECTOR, with an honest statistical fallback.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS companion app with real haptic alerts and a paired-phone voice relay.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware for a board-mounting rack with real tool-ID decoding and Smart Idle pre-heating logic.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — administrative desktop tool that discovers, clones and updates every repo in this ecosystem.

## 📜 LICENSE

URTC Tester is (c) 2026 JuanenRac (Electro Hobby 3D). This notice must
be included in any distributions of this project or derivative works.

This project consists of source code and its own documentation, made
available under different licenses - each suited to what it actually
covers:

1. The source code (`urtc_tester.py` and every `tester_*.py` module)
   and any binary built from it via `build_exe.bat`/`build_exe.sh` are
   available under the **GNU General Public License v3.0 (GPL-3.0)**.
   Full text at https://www.gnu.org/licenses/gpl-3.0.html.

2. The documentation (this README and its own translations -
   `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`,
   `README_zho.md`, `README_jpn.md`)
   is available under **Creative Commons Attribution-ShareAlike 4.0
   International (CC BY-SA 4.0)**. Full text at
   https://creativecommons.org/licenses/by-sa/4.0/.

This tool is the live CAN-bus diagnostic companion to the
[URTC (Universal Robot Tool Controller)](https://github.com/JuanenRac/URTC)
project - see that project's own repository for the board firmware,
hardware designs, and full protocol documentation this tool exercises
against. URTC's own firmware is GPL-3.0 and its hardware designs are
CERN-OHL-S v2; this tool's own license here doesn't extend to that
separate project, and vice versa. A web-based alternative covering
similar ground also exists at
[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO).

If you build on this project, keep the licensing split in mind: code
changes should stay GPL-3.0, documentation derivatives should stay CC
BY-SA - each with attribution back to this project and its author.

## 👤 AUTHOR

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)
