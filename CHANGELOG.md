# Changelog

All notable changes to this project are documented here.

## [Unreleased]

- **A virtual board stands in for the hardware:** `urtc_can/virtual_board.py` from URTC-COMMON (a SLCAN server over TCP with a model of the board) is reached through `--transport serial --port socket://host:port`, so `info` and plans of queries run end to end with no adapter; the window lists the URLs named in `URTC_VIRTUAL_PORT` (comma separated) next to the real ports; 5 new tests, one of them over the real pyserial URL handler.
- The rack simulator speaks frame version 2 (big-endian temperature in the pre-heat command), and the shared rack vectors were refreshed.
- The CI holds the tests to a coverage floor of 65 percent (measured 73; `pytest-cov` is in `requirements-dev.txt`).

## [0.4.1] - Headless tester with test plans, heater PID panel, kept-alive commands and a development requirements file

- **A plan can keep a command alive:** `keepalive_ms` (20 to 200) on a `send` repeats the command while the plan waits, also while a person is asked, because the firmware drops an order for a heater, a drill or a laser that is not refreshed within 250 ms; a new `send` with the same identifier replaces it, an order of all zeros is not repeated, and the repetition is part of the log. The simulated head now drops those orders like the firmware, so a plan that forgot the keepalive fails there instead of passing on a bench that does not exist. The example plan that heats the tip uses it.

- **A recorded trace is replayed only for what arrived:** the lines of a `.trc` marked as transmitted were played back as if they had come from the bus; only the received lines are played now.

- **The tests and the checks have a requirements file:** `requirements-dev.txt` lists pytest and ruff, and the CI installs from it.

- **Heater PID panel:** reads the state of the heater PID of the firmware (`0x1B9` / `0x1BA`: the gains in force, the state and the output of the last cycle), stores gains from 0 to 600 and starts or aborts the relay autotune, in the language of the interface (19 new keys in the eight language files). Storing gains and starting the autotune ask for the usual confirmation, aborting does not; a gain that is not a number from 0 to 600 is refused before anything is sent. The simulated head of the command line answers these frames, including an autotune that ends with new gains. 16 new tests.

- **The tester without a window:** `python urtc_tester.py --headless COMMAND` runs `info`, `selftest`, `run-plan FILE` and `validate-plan FILE` with no display and no PySide6, over the same transports as the deck (`--transport serial`, `socketcan`, `python-can`) and over two new ones: `simulate`, a simulated tool head that answers the queries, reports the telemetry of its tool and can play a fault, and `replay`, which plays the frames of a recorded `.trc` or `.asc` trace. Every run writes a log of the frames and a result record that names it by its SHA-256 (the record of the deck); the exit status says passed, failed, wrong plan or could not be carried out. See `docs/HEADLESS.md`.

- **Test plans:** a plan is a JSON file of steps (expect a tool, no faults, a minimum firmware version, the self-test, a frame whose value lies in a range, a wait, a question for the person at the bench); `plans/` has two examples. A plan sends only queries unless it says `"actuation": true` and the operator passes `--allow-actuation`; the boot-loader, update, configuration, slave-link and erase frames are never sent and a plan that has them is refused before the bus is opened; every output is switched off again after a plan that commanded something, also when it ends early. A step that cannot be carried out ends the plan as an error, never as a pass. 86 new tests.

## [0.4.0] - Fault recorder, optional functions, rack bench and thermal view

- **Fault recorder**: reads the black box (`0x1A8` / `0x1A9`), checks it and saves it as CSV and JSON in the logs folder, and reads it by itself once for each error the board reports when the option is on (it is on by default and can be switched off in the deck; it needs the active mode).
- **Optional functions**: queries and writes the optional firmware functions (`0x1AE` / `0x1AF`) after the usual confirmation.
- **Rack bench**: a simulated tool rack with the serial protocol of URTC-SMART-RACK, the identity of each head (type and serial number), the limit on pre-heat and the export of a status page as JSON and HTML.
- **Thermal view**: the image of the thermal inspection tool in false colour, read from the board or, marked as simulated, from a synthetic image.
- The tool names and kinds come from the shared tool profiles of URTC-COMMON; the copies of the shared modules follow it (`blackbox`, `rack_sim`, `rack_status`, `thermal_view`, `tools_catalog`).
- The README lists URTC-GATEWAY, the new gateway in front of the CAN bus, among the related projects.

## [0.3.9] - Shared CAN transports and a CI that names its notices like the rest

- `tools/ci_validate.py` fails when a versioned file has the name of a Windows path (a colon, the character a file system uses to store one, or a first folder named like a drive or a user profile): a path handed to WSL without translation once put build output inside a repository. The same check (`tools/_tracked_names.py`) is in every URTC repository.
- The CI workflow is named `URTC CI baseline`, like the other repositories, so that one dashboard notice can follow it.
- The `build-test` scripts use the interpreter named by `URTC_PYTHON` (which URTC-UPDATER sets to its own) and, without it, the first `python3` or `py -3` found, so a build check runs with a Python whose packages are known.
- The dashboard notice is sent only after the CI of the push finished green (`workflow_run`).
- The banner follows the animated style of the ecosystem banners, with the name, the kind and the technologies of the project.
- **The CAN transports (SLCAN, SocketCAN, python-can, the simulated board and the bitrate listen-only detection) now come from the shared module** copied into `urtc_can/` (with the framing, SLCAN codec, versioning, quick-state and conformance helpers), so a fix made once in URTC-COMMON applies here too. `tester_transports.py` keeps its name and only adds what is specific to this program: SocketCAN warnings said in the language of the window, the serial port taken from this module's `serial`, and the frame counters behind the bus-load display. The shared SLCAN keeps writes from two threads apart, clears stale input when the channel opens and turns a failed serial write into a typed error; a channel opened listen-only refuses to transmit.
- The eight copies of shared modules that sat unused at the top of the repository (they could not be imported there) are gone; the one lock file for the shared modules is `urtc_can/urtc_common.lock.json`, and the test that checks the copies are not behind URTC-COMMON now covers every file in it.
- The tests that built a transport object by hand now go through the public classes (`serial_module` for a fake port, `socket_module` for a fake kernel socket).
## [0.3.8] - Follow URTC-COMMON 0.0.5, no signature claim in the session export and only the language entries the Qt window uses

- The copies of the CAN protocol module and of the conformance vectors follow URTC-COMMON 0.0.5, so the tool carries the multinode extension of the protocol that the firmware already speaks.
- The English name of the session export no longer says "signed": the export writes a manifest with the SHA-256 of the log, not a signature, as the other seven languages already said.
- The language files no longer carry the entries that only the retired window used (247 per language); the log labels and the entries built from a prefix are kept.
- The manifest declares how far the project has been shown to work (`evidence`: simulator) and `tools/ci_validate.py` checks the value.
- Build version synchronized with `urtc.project.json` and the repository-native version source.

## [0.3.7] - The activity log speaks the interface language

- The Qt Quick deck now shows its activity log, the thermal and passive-capture summaries in the interface language (English, Spanish, German, French, Italian, Japanese, Chinese, Portuguese); every log token has a label in each language file.
- The saved log and the exported session bundle keep the English original lines, so support and the manifest hash see exactly what happened.
- A test regenerates the list of logged tokens from the source, so a new token without labels in all eight languages fails the checks.

## [0.3.6] - Follow URTC-COMMON 0.0.5 and the 0.3.8 firmware

- The shared protocol and widget copies follow URTC-COMMON 0.0.5, which adds the multinode identifiers and the two frames that read and set its switch.

## [0.3.5] - Self-test, live readouts and bus health in the Qt Quick deck; the Tkinter window is retired

- New self-test in the deck: the same safe, at-rest checks as before (the two generic queries and a zero setpoint, speed or power for the tools that have telemetry), now in `tester_selftest.py`, shared by the tests and the deck. It needs an armed connection, the detected tool to be the selected profile and a confirmation, and it switches every armed output off first. The step texts exist in the eight languages.
- New live readouts for the soldering iron, drill, AOI, laser, 3D printer, hot-air station and flying probe: temperature with a rolling graph and CSV export, RPM and endstops. The watch only listens, so it works in listen-only mode, and an output can be switched on while it runs; a command that also reads the bus is refused while it is running.
- New bus health check: while the deck is idle the active tool is queried every three seconds, one silent answer is not a verdict and two are, and the header shows the reason until the bus recovers.
- New About dialog with the Readme, the License and the GitHub page, Save Logs, and the session export now carries system diagnostics. Profiles with no command of their own say why.
- The Tkinter window is retired: `urtc_tester.py` always starts the Qt Quick deck (`--legacy` prints a note and does the same). `tester_gui_core.py`, `tester_common_panels.py`, `tester_tool_panels.py`, `tester_panel_helpers.py`, the animated-mark widgets, their frames and the startup banner are removed. The bit-rate search moved to `tester_autodetect.py`, and the tests that exercised the Tk window are replaced by tests of the deck and of the shared logic.
- The PyInstaller spec now collects the Qt Quick plugins and lists the modules like the build scripts do.
- The language list and selector, the colour of the connection state, the bit-rate parsing and the monitor's identifier and byte formatting come from the `urtc_ui` copy of URTC-COMMON; the protocol copies follow URTC-COMMON 0.0.4.
- New tests for the self-test runner and the deck's gate, the readouts and their CSV, the bus health verdicts, and the confirmation of every physical action in the QML.

## [0.3.4] - The Qt Quick deck gets the raw bus monitor

- The Qt Quick deck has a raw bus monitor: it reads every frame without transmitting, shows the newest ones, filters by CAN ID and by changed payload, keeps the last 2000 frames, and exports them as a PEAK `.trc` or a Vector `.asc` trace in the logs folder.
- The monitor holds the bus like any other read (one reader at a time), is available in listen-only mode, and ends cleanly when the adapter is disconnected.
- The trace writers are one shared module used by both the Tk window and the Qt Quick deck, with tests for the offsets, both formats and plain-ASCII output.

## [0.3.3] - The Qt Quick deck can search for the bus speed

- The Qt Quick deck has an auto-detect button for serial CAN adapters: it listens at each speed first (nothing is transmitted), asks for the active tool only when the whole bus is silent, adopts and remembers the speed found, and leaves the selection untouched when nothing answers.
- Tests cover a found speed, a silent bus, an adapter that fails, and the remembered selection.

## [0.3.2] - An explicit bump command: building never changes the version

- Building no longer changes the version: build_exe.bat and build_exe.sh only read TESTER_VERSION, and raising it is the explicit `python bump.py` step.
- Every licence statement and source header says GPL-3.0-or-later.

## [0.3.1] - Shared protocol constants, language selector and wire feeder position

- The CAN identifiers, the hardware id and the erase-memory magic bytes are now aliases of the generated protocol module (urtc_can/protocol.py, a copy of URTC-COMMON kept honest by a lock file); a new test fails when the copy is edited by hand or falls behind, and the shared conformance vectors are refreshed.
- The header of the Qt Quick deck has a language selector (the eight languages); the choice is saved and applies on the next start.
- The Qt Quick deck queries and resets the position of the soldering iron's wire feeder (open-loop estimate; the reset asks for confirmation); until now only the Tkinter window could.
- The build and run scripts read URTC_CI as their non-interactive switch.
- The identity probe of the Qt Quick deck shows the firmware patch number (v0.3.5 instead of v0.3) when the board sends the companion frame 0x7E9 right after the version answer (URTC firmware 0.3.5 and newer); older firmware keeps showing major.minor and the patch is never guessed. New function firmware_version_text with tests.
- The six translated READMEs (Spanish, German, French, Italian, Japanese, Chinese) describe the Qt Quick deck as the default and the Tkinter window as --legacy, like the English one; the flag --qtquick, which does not exist, is gone from the text and the file trees.
- The README of every language lists URTC-UPDATER among the related projects.
- The CI workflow no longer carries steps for stacks this repository does not have.
- LICENSE holds the full text of the GNU General Public License v3.0; the copyright notice and the license of the documentation moved to a new NOTICE file. The license is GPL-3.0-or-later everywhere: LICENSE.md, source headers, script banners, About texts and READMEs (eight languages).
- A test compares hydra_umc_animation.py and hydra_umc_deck_widgets.py with the copies in the other desktop tool (by syntax tree, so comments and layout do not count) and fails when one of them changes alone; it skips when the other repository is not next to this one.

## [0.3.0] - Claims aligned with what has been tested

- Maturity is functional: nothing here has been verified on real hardware yet.
- The README (all eight languages) no longer calls the SLCAN/SocketCAN transports production transports, states that STOP ALL OUTPUTS is a software command and not an emergency stop, and says that the laser lock output is a firmware output and not a hardware interlock.
- The README states that nothing here has been tried on a real board.

## [0.2.9] - Serial reader ignores line noise that looked like a frame

- **Identifiers and data digits must be real hexadecimal.** A signed, `0x`-prefixed or underscore-separated field in a received serial line used to be accepted by the number parser and delivered as a frame; the line is now ignored.
- **More of the tool is covered by tests.** The CAN protocol is checked against vectors shared with the other URTC tools (identifiers, magic payloads, serial framing, the 0x111 quick-state answer), and the serial and SocketCAN transports and the bus monitor now have their own tests (listen-only never transmits, extended/remote/error frames are dropped, one failing callback never stops the others).

## [0.2.8] - A bit rate search that stays silent on a live bus, a stop for every output, confirmations and settings that are remembered

- **The bit rate search no longer transmits on a live bus.** Each rate is first opened listen-only and is accepted only when valid frames are heard there, then confirmed with one query; asking at every rate happens only when the whole bus is silent, and the log says so. A bus that is alive but where nobody answers is never probed blind.
- **STOP ALL OUTPUTS in the classic window**, next to Detect and Self-test: it sends every known off command (heaters, laser, drill, UV lamp, layer fan, electromagnet release, plain steppers and crimper) whatever tool is fitted, stops every refresh and puts the Active boxes back to unchecked. The Qt deck button now does the same, is shown whenever the deck is connected with active checks armed, and closing the deck sends the same set. The hotend fan is left running on purpose, because the nozzle may still be hot.
- **Disconnecting ends a telemetry watch** in the Qt deck instead of leaving the app stuck until STOP WATCHING was pressed; a probe or a capture in progress still blocks it.
- **One encoder for every one-shot output of the Qt deck**: motion, drill, strobe, electromagnet, weld pulses, paste and printer commands are now built by the same functions the tests cover, and new tests compare what each sender puts on the bus with them. A paste pulse of 0 ms (a continuous pulse nothing can stop) is refused in both windows.
- **Bit rate selector in the Qt deck**, and the port and bit rate are remembered for the next session in both windows (the bus load figure follows the selected rate).
- **The classic window asks for a confirmation** before a weld pulse, a paste pulse or a crimp, as the Qt deck already did for every physical action.
- **Raw Bus Monitor filters**: show only some CAN IDs (hex, separated by spaces or commas) and/or only frames whose data changed. The counters keep counting every frame. Exported trace files are written as plain ASCII.
- **The extruder limitation is stated in both windows.** While the 3D-printer heater is held, its 150 ms refresh carries 0 extruder steps, which the firmware reads as a stop order, so an extruder move started in that state is cancelled; the help text, the log line and a note in the Qt deck say so. Moving the extruder with the heater held needs a firmware mode that leaves the extruder alone.
- **More of the interface is translated** in the eight languages: the option lists of the Qt deck (directions, strobe modes, display modes), the bus monitor title and statistics, the self-test steps, the tool tab title, the jumper message, the hardware identity note and the empty-state texts.
- The Qt deck probe shows a latched thermal fault and the reset causes, as the classic window does.
- Small fixes: the Readme menu opens the Chinese and Japanese translations, deadlines in the transports use the monotonic clock, the classic window is never taller or wider than the screen, and the unused imports and exception chaining flagged by the linter are cleaned up.
- **Builds**: a failed build puts the version files back as they were instead of leaving a version that was never built, the step numbering is coherent, Tk is only a warning for the Linux build (the default deck does not need it) and every own module is a hidden import.
- **Checks and documents**: CI now runs pytest, the linter and the three Qt deck checks (headless); the licence file lists every README translation and the guides, the guides carry the documentation licence, and the workflow, issue forms and manifest no longer carry another project name or describe the old default window.
- Tests: 102 (before 69): the bit rate scan on a live, a silent and an idle bus, the stop for everything in both windows, the confirmations, the monitor filter, the sender-versus-encoder comparison, the remembered settings, the disconnect during a watch, and the eight language files (same keys, same placeholders, every key used exists).

## [0.2.7] - Reads that no longer collide, a stop for everything, a thermal image that keeps its shape and a board that cannot go silent unnoticed

- **The queries of the classic window no longer freeze it.** F-RAM, thermal counters, DIAG0, the SPI passthrough, the expansion board, the sensor variant, the free tool configuration, the peripheral info, the F-RAM erase, the ADS1115 read and the thermal status wait for the board on a worker thread: while the window waited, the 150 ms refresh of an armed heater, laser or UV lamp stopped and the firmware latched a critical error.
- **The Qt deck reads the transport one exchange at a time.** Queries launched together used to eat each other's answers (false "no response") and corrupted the SLCAN receive buffer; they now take turns, and a query is refused while another read (probe, thermal capture, telemetry watch) owns the transport.
- **STOP ALL OUTPUTS in the Qt deck**, always enabled while an output is armed, whatever the profile or the busy state. Selecting another profile or pressing Probe also switches the armed outputs off, so a laser or a heater no longer keeps running behind a different profile.
- **The thermal image keeps its shape.** The sensor fitted is asked first (16x12 for the MLX90641, 32x24 for the others, drawn at its real size), the capture is waited for until it reports ready, the four frames of a chunk are collected together instead of losing the last three, and a lost chunk leaves blank pixels instead of shifting everything after it.
- **The ID jumper squares show the real jumper reading** (read from the board), not the resolved tool: with the jumpers on 11111 the tool kept in F-RAM was drawn as if it were the jumpers. They stay "?" on a firmware that does not answer.
- **The board health check notices a board that stops answering** (two silent polls in a row) and also reports a latched critical error and a thermal fault, instead of treating silence as healthy.
- **The strobe period is in milliseconds**, 1 to 500 (the firmware's range), default 5: it was labelled microseconds and sent 1000, which the firmware turned into a half-second flash. The label says so in the eight languages.
- **The raw bus monitor follows the connection**: it closes when the connection does, and its bus load uses the selected bit rate instead of always 500 kbit/s. The classic window's free tool configuration names all 25 tools too.
- The extruder keepalive note now says what the firmware really does with 0 steps (it stops the extruder); moving the extruder while the hotend is held still needs a firmware change.
- Tests: 69 (before 49): the strobe range, the thermal geometry and chunk assembly, the multi-frame waiter, the queries off the Tk thread, the board health verdicts, and in the Qt deck the single reader, the stop-all and the thermal capture with a mock board.

## [0.2.6] - Safe-off that really switches off, a drill that no longer trips the board, a stop for the motors and the limits of the firmware

- **Portuguese (Portugal) is a language of the interface** (`language/portuguese.lng`, in the language menu), and the Readme menu opens `README_por.md`; the README exists in Portuguese too.
- **The hotend heater's safe-off now switches the heater off.** The Qt deck had its own copy of the frames, with a 5-byte "safe off" that the firmware (which needs 6) ignores; every output of the Qt deck now uses the one encoder that the tests cover.
- **Turning the hotend heater off in the classic window sends 0 °C** instead of the setpoint of the spinbox (which re-armed the heater with nothing to keep it alive and ended in a latched critical error), and "Move extruder once" no longer heats for 250 ms when the heater is not on.
- **The drill is refreshed like the laser and the heaters** (a tick box and a 150 ms refresh in the classic window; Send starts it and speed 0 stops it in the Qt deck): the firmware cuts a drill that is not refreshed after 250 ms and latches a critical error, which a single frame always caused. Switching it off sends speed 0, the active brake, and the help text says so in the seven languages.
- **A STOP for the plain steppers and the crimping actuator** (classic window and Qt deck): 0 steps is the firmware's order to stop, and no screen offered it, so a long move could only be ended by cutting the power. It also goes out when the connection is closed, when the panel is left and when the tool is switched off.
- **Closing the window switches the tool off first** (classic window and Qt deck), instead of leaving a heater, a laser or a motor to the watchdog of the firmware, which latches an error, or to nothing at all for the outputs that have none.
- **No screen offers a setpoint above 445 °C** for the soldering iron and the hot air: the firmware refuses it and declares a latched critical error (the screens went up to 450).
- **The free tool configuration names all 25 tools** (it said "none selected" from the 13th), a paste pulse can no longer be continuous with nothing to stop it, and the exported graph data is what was measured, not what fitted the graph (and no longer grows without limit).
- Tests: 49 (before 39): the safe-off frames and the ceilings, the drill, the stop, the 25 tools and the paste pulse, in the classic encoder and in the Qt deck.

## [0.2.5] - Copy-log icon button

- **Copy-log button:** the activity log has a small copy icon (two sheets) that puts the whole log on the clipboard and flashes green when done.

## [0.2.4] - Thermal runaway guard and lifetime thermal counters (URTC firmware 0.3.2+/0.3.3+)

- `advanced_protocol.py`: `decode_quick_state()` reads `0x111` byte 4
  (thermal runaway fault code) and byte 5 (reset cause - bit0 = hardware
  watchdog); `decode_thermal_stats()` reads `0x1AB` (lifetime faults, heater-on
  seconds, last fault, F-RAM persisted); `evaluate_thermal_runaway_bench_test()`
  gives the pass/fail verdict of the bench procedure. Missing bytes from older
  firmware are "not reported", never zero.
- Detect shows `THERMAL RUNAWAY: <fault>` in the board state and logs a
  watchdog reset. New **Thermal counters** button (`0x1AA`) in the F-RAM panel
  of both the Tk UI and the Qt Quick deck.
- `docs/THERMAL_RUNAWAY_BENCH_TEST.md` (new): how to confirm the guard on a
  real board. READMEs in all 7 languages describe it; new strings in all 7
  `.lng` files.
- Tests: 4 new unit tests (`tests/test_advanced_protocol.py`) and a new
  check in `verify_qt_utility_panels.py`.

## [0.2.3] - The Qt Quick Tester can export a session that proves its log

- A new **Export session** button in the Qt Quick deck saves the activity log in `logs/` as a zip with `session_log.txt` and a `session_manifest.json` that names the log by its SHA-256 and size, with the Tester version, the port and whether it was connected, so a saved log can be shown to be unedited. It was already available in the Tk window; the label exists in the seven languages and two tests cover the bundle and the failure to create the folder.

## [0.2.2] - Session manifest in the debug bundle

- The exported debug bundle now includes session_manifest.json, which names the session log by its SHA-256 and byte count together with the tester version, transport, port, bitrate and active tool, so an edited log can be told apart from the original.

## [0.2.1] - Reproducible result records

- `tester_result_record.py`: a `ResultRecord` ties an outcome to the adapter, firmware version,
  bus, bitrate and a log file identified by its SHA-256, saves and loads as JSON, and checks
  the log against its hash when loaded so an edited log no longer matches its result.
  Seven new tests. Not yet wired into the test panels.

## [0.2.0] - Live frame-rate and bus-load readout in the deck header

The Passive Bus Window already showed a bus-load percentage for its own
short capture; nothing showed the live rate while just connected. Both
transports (SLCAN, SocketCAN) now count every frame they send or read into
a `BusStats` sliding window (`transport.stats`), so it works for every
reader in the app without touching any of them, and the Qt Quick deck
header shows `N fps | X% bus` once a second while connected. Same
estimate as the Passive Bus Window (47 framing bits + 8 per data byte
against 500 kbit/s, stuff bits not modelled). Hardware-free tests cover
the window maths and the instrumentation; not yet checked against a real
adapter.

## [0.1.9] - Qt Quick is now the real default UI

Verified, not assumed: every one of the 25 tool profiles' own commands
already had real, wired coverage in the Qt Quick deck (`qt_tester.py`/
`TesterDeck.qml`) - motion (8 profiles), drill, AOI, electromagnet,
spot/ultrasonic weld pulse, paste jetting, flying probe, thermal
inspection, the 5 watchdog-keepalive actuators (solder iron, laser, the
printer's own heater/layer fan, UV curing, hot-air rework), and vacuum/
scan-probe telemetry - each gated on identity match + explicit active
mode + a QML confirmation. Only the module docstring, in-app help text
(`QT_STAGED_LIMIT`, all 7 languages) and README still described this as
a bounded, motion-only deck. `urtc_tester.py` now launches Qt Quick by
default; `--legacy` opts into the original 25-panel Tkinter GUI instead
(kept, not removed). Neither UI has been checked against a real board
yet - this is a real default-mode change, not a claim that either path
is hardware-proven.

## [0.1.8] - Real-time bus load indicator on the Passive Bus Window

- The **Passive Bus Window** capture (Qt Quick deck) now also reports a real
  CAN bus load percentage alongside its existing frame/ID counts, plus a
  colour-coded bar (green/yellow/red at 40%/80% thresholds). The percentage
  is derived from the same real frame count and per-frame byte sizes the
  2-second capture window already collects - no separate tracking loop was
  needed. Per-frame bit cost uses the standard CAN 2.0A 11-bit-ID data-frame
  overhead (47 fixed bits) plus 8 bits per data byte actually seen, divided
  by the tester's own established 500 kbit/s SLCAN default
  (`BITRATE_500K_SLCAN_CODE`); bit stuffing is deliberately not modelled,
  so the estimate reads slightly low rather than ever overstating load.
  New `QT_BUS_LOAD` key across all 7 languages.

## [0.1.7] - Custom CAN Frame panel completes the Qt Quick migration, real About window, Chinese and Japanese added

- **Custom CAN Frame** is now available in the Qt Quick deck, completing
  its migration from the legacy Tkinter panel - the last of the
  tool-independent utility panels. Same real validation as the legacy
  panel (11-bit ID range, DLC≤8, space-separated hex bytes) and the same
  no-profile-gating semantics (only `canUseUtilityPanels`: connected,
  active-check mode, not busy - this panel can address any CAN ID,
  unlike every profile-gated action elsewhere in the deck). "Repeat
  every" periodic resend is a real QML `Timer` reading the live text
  fields each tick (not a Python thread re-checking stale copies), so an
  edit mid-run takes effect immediately without stopping/restarting,
  matching the legacy panel's own re-parse-per-tick behavior. Periodic
  ticks stay silent on an ordinary send and only log on a parse-failure
  transition (start/stop/skip/resume) - logging every tick at a fast
  interval would otherwise flood the 14-entry activity log with nothing
  else. Disconnecting force-stops any running periodic resend, the same
  real safety net `_stop_all_watchdogs()` already gives every other
  periodic send.
- **Real About window**, matching HYDRA-UMC-STUDIO's own `About.tsx` and
  URTC-FLASHER's own Tkinter AboutDialog: a tagline, a one-paragraph
  description, and a real Version/Author/Email/License info block, not
  just a banner and one line of text. New `TITLE_ABOUT`/`ABOUT_TAGLINE`/
  `ABOUT_DESCRIPTION`/`ABOUT_VERSION`/`ABOUT_AUTHOR`/`ABOUT_EMAIL`/
  `ABOUT_LICENSE`/`BTN_CLOSE` keys across all 7 languages, replacing the
  old `LBL_ABOUT_AUTHOR` - full key parity verified.

- The Qt Quick deck's own header `ToolBar` relied on the Basic style's
  implicit sizing, which collapsed to 0 height for this specific window -
  the branding/status text all overlapped at the top-left corner instead
  of laying out in a real row. The same real bug HYDRA-UMC-SUITE's own
  Qt Quick shell already found and fixed (an explicit `height: 84`,
  sized to fit the header's own 50px icon plus its Card/RowLayout
  margins) - never propagated back to this sibling app until now.
- **`QT_PASSIVE_HELP` was defined twice in every one of the 7 `.lng`
  files** (and in `qt_tester.py`'s own fallback dict) with two different
  meanings - the transport-mode explanation next to the Listen-Only
  toggle, and the Passive Bus Window capture explanation. The second
  definition silently won in every language, so the transport-mode
  toggle showed the wrong help text ("Capture live CAN traffic for two
  seconds...") instead of its own ("Passive transport mode. Probe
  commands are blocked."). Renamed the capture-window one to
  `QT_PASSIVE_WINDOW_HELP` everywhere (language files, Python fallback,
  `TesterDeck.qml`) - each now shows its own real text.

- The Qt Quick deck now exposes the complete real legacy profile catalogue
  and a deliberately bounded one-shot motion action for the existing motion
  profiles. The backend requires a connected active transport, a matching
  probed identity and an allowed profile; QML then requires a second operator
  confirmation immediately before it sends the existing 0x120 command.
  Advanced actuator and configuration flows remain in the established Tkinter
  panels pending physical validation.
- The Qt Quick deck now also migrates the real one-shot drill, AOI,
  electromagnet, weld-pulse and paste-jetting frame layouts, plus the
  established watchdog-backed solder, laser, printer heater/layer fan, UV
  and hot-air outputs. Energising actions receive a second confirmation; a
  stop/disconnect sends the matching safe-off frame. Telemetry-only,
  external-machine and multi-packet profiles remain explicitly unavailable
  rather than receiving a simulated control.
- The printer profile additionally exposes the established one-shot hotend
  fan and extruder frame paths. The watchdog heater frame always carries zero
  extruder steps, preventing temperature maintenance from repeating motion.
- Added a hardware-free control-protocol unit suite. It exercises bounded
  command payloads, crimp routing, safe-off watchdog frames and isolated
  telemetry fixtures without importing a GUI runtime or opening a CAN
  transport. The baseline CI workflow runs the suite.
- The Flying Probe profile now exposes its established ADS1115 configuration,
  conversion trigger and bounded result-read sequence in the Qt Quick deck.
- The Thermal Inspection profile now triggers and reads the established,
  bounded 48-chunk calibrated frame sequence in a worker, then renders the
  received cells in a Qt Quick grid. Missing chunks remain visibly absent;
  the operation never substitutes fixture data for a device response.
- The Qt Quick deck now includes a bounded **Passive bus window**. It is
  available only after a listen-only connection and captures two seconds of
  real received traffic, displaying frame/CAN-ID counts and a capped sample.
  It has no transmit path and is intentionally unavailable in active-check
  mode; the separately armed identity probe remains unchanged.
- The Qt Quick transport selector cannot refresh or switch ports while a
  connection is active. The same guard is enforced by the backend, not only
  by the visual control.
- The Qt Quick transport selector now uses the actual discovered SocketCAN
  interface set instead of guessing from names such as `can0`, so valid
  interfaces including `vcan0` are routed to SocketCAN correctly.
- Qt Quick worker logs are now marshalled to the GUI thread before the QML
  log model changes, avoiding a possible cross-thread UI race during
  connection and identity probes. Selecting `--qtquick` without PySide6
  now returns a clear dependency message rather than an import traceback.
- Fixed `urtc_tester.py` crashing on every launch (`NameError: name 'sys'
  is not defined`) - the `--qtquick` mode check at the top of the file
  used `sys.argv` without `sys` ever being imported. Both the default
  Tkinter mode and `--qtquick` were affected; `run.bat`/`run.sh` never
  actually got the app running.
- A staged Qt Quick desktop deck can now be launched with
  python urtc_tester.py --qtquick. It uses the real SLCAN/SocketCAN
  transports for connection and begins in real listen-only mode. Its
  explicitly armed identity check emits only the documented 0x110 and 0x7F8
  queries, then reports the active-tool and version responses. It does not
  expose actuator controls; the established Tkinter application remains the
  default while its 25 tool panels are migrated safely.
- PyInstaller scripts now collect the Qt Quick/QML runtime and the staged
  command-deck entry point.
- A full dark navy/cyan command-deck presentation now wraps the established
  live-CAN UI: product/status header, real 16px rounded canvas cards on the
  connection and session-log surfaces, 10px curved primary actions, plus
  coherent tab surfaces,
  high-contrast controls, readable tool navigation and a dark monospace
  session log. It is visual-only; monitoring, routing and safety flows are
  unchanged.
- The fixed connection panel now displays the official animated HYDRA-UMC
  mark. Tkinter plays twelve bundled PNG frames rendered from
  `assets/HYDRA_UMC_ICON.svg`, so both source and PyInstaller runs retain the
  animation without adding a heavyweight GUI runtime dependency. The
  URTC-specific native window/taskbar icon remains static and unchanged.
- `tools/render_hydra_umc_icon_frames.py` regenerates those frames with
  PySide6 when the source SVG changes. PySide6 is also the runtime
  dependency of the explicit Qt Quick deck.

- New `language/chinese.lng` (简体中文) and `language/japanese.lng` (日本語),
  full translation of all 349 keys, matching the coverage of the existing
  english/spanish/italian/french/german files. Added to `tester_config.py`'s
  own `AVAILABLE_LANGUAGES` list, which the Language menu builds from
  dynamically - no other UI code needed changing. Verified two ways: a real
  `load_language()` call for both new files confirmed all 349 keys present
  with zero gaps or extras against `english.lng`, and a real Tkinter
  `TesterGUI` instantiation confirmed both new entries render correctly in
  the actual Language menu alongside the other 5. New `README_zho.md` /
  `README_jpn.md` documentation translations, plus the 5 existing README
  files' language selectors updated to link them. Doesn't bump
  `TESTER_VERSION` on its own - this project's own versioning convention
  only advances it on a real `build_exe.bat`/`build_exe.sh` packaged build.

- SLCAN reception now discards impossible CAN 2.0 DLC values (`9`-`F`) rather
  than passing oversized frames to GUI handlers. Valid standard frames are
  unaffected.

## [0.1.6] - The protocol boundary can no longer turn invalid input into a different valid command

Found on code review:

- **`advanced_protocol.py`'s `bounded_int()`** used to silently CLAMP an
  out-of-range value into range (a garbled 9999999999-step motion
  request became the protocol's own 4294967295 maximum - a real,
  different command, not an error). Now strictly rejects anything
  malformed or out of range; a genuinely display-only clamp (the RGB
  status/ring LED color, explicitly cosmetic - see
  `global_status_frame`'s own comment) keeps the old clamping behavior
  through a new, separately-named `clamp_for_display()` instead. Also
  now rejects a bare `bool` even though `isinstance(True, int)` is true
  in Python.
- **`motion_frame`/`drill_frame`'s own `direction` ternary**
  (`0x01 if direction == "forward" else 0x00`) let ANY unrecognized
  value - a typo, wrong case, a bool, a forged/stale UI state - silently
  fall through to the `else` branch and encode as the OTHER, opposite,
  equally-valid physical direction, instead of being rejected. New
  `_direction_byte()` validates against the exact two labels a command
  actually supports. The real UI only ever offering these two labels
  through an enum control is a UI constraint, not a protocol-boundary
  guarantee against a forged call - the same class of duplicated bug was
  also found and fixed in `qt_tester.py`'s own separate inline
  encoding (`sendMotion`/`sendDrill`, plus its own separate `_bounded_int`
  static method, same clamp-to-reject fix) and in the legacy Tkinter
  `tester_tool_panels.py`'s own inline motion/drill direction checks -
  three independently duplicated copies of the same real bug, all
  fixed. `tester_tool_panels.py`'s own numeric step-count clamp (an
  explicit, documented `struct.pack` overflow guard, not a
  direction-style "different command" risk) was deliberately left as-is.
- 6 new tests in `tests/test_advanced_protocol.py` (out-of-range
  rejection across motion/weld/paste, the bool rejection, the
  deliberate display-clamp exception, and unrecognized-direction
  rejection for both `motion_frame` and `drill_frame`); 2 existing
  tests that had asserted the old clamping as correct behavior updated
  to their new, real in-range values.
- Removed 6 dangling references to two private tracking
  documents across `CHANGELOG.md` and `tester_tool_panels.py` - neither
  file is tracked in this repo.

Verified with `python tools/build_test.py` (this repo's own real CI
check - `PYTHON_COMPILE=PASS`, `UNIT_TESTS=PASS` 20/20, `QML_I18N=PASS`,
`BUILD_TEST=PASS`) and a direct load of all 7 `.lng` files confirming
the new `LOG_TOOL_MOVE_BLOCKED_DIRECTION` key.

## [0.1.5]

- **The Qt Quick deck now has real Global Controls / Expansion Board /
  F-RAM sections**, matching the 3 real Tkinter tabs of the same names -
  the last major real gap left in the deck. Unlike every tool-specific
  advanced control migrated so far, none of this is gated by which tool
  profile is selected (see tester_common_panels.py's own
  `CommonPanelsMixin`): Status LED/ring LED/OLED mode (any tool, one
  plain Send, no confirmation - low-stakes, reverts to automatic after
  10s if the override lapses); CONN_EXPANSION's generic SPI passthrough
  (1-7 raw bytes, real request/response) plus a TMC_DIAG0 level query;
  and the FM24CL64B's recovered state (query, plus a real, genuinely
  destructive **Erase** - the one action here that asks for the same
  real confirmation every other hazardous action in this deck already
  requires) alongside 3 real read-only EEPROM fields (expansion board
  type, MLX sensor variant, free tool configuration, peripheral
  info/serial - all four only ever written by the Flasher, never by
  this tool).
- New `_run_query()` in `qt_tester.py` - one real generic bounded
  request/response worker every one of the 7 queries above shares
  (send an optional request, wait up to 1s for the matching response
  CAN ID, decode, emit through one shared `_queryResult` signal keyed
  by which real query it was) - not 7 near-duplicate workers.
- New pure decoders in `advanced_protocol.py`
  (`global_status_frame`/`spi_passthrough_frame`/`decode_spi_response`/
  `decode_diag0`/`decode_fram_state`/`decode_expansion_board_type`/
  `decode_mlx_sensor_variant`/`decode_free_tool_config`/
  `decode_peripheral_info`) - 9 new hardware-free unit tests.
- The right-hand card **now scrolls** - real content no longer reliably
  fit the window's own `minimumHeight: 680` once these 3 new sections
  were added; the Activity Log's own real height, previously
  `Layout.fillHeight: true` against a fixed-height parent, is now a
  real fixed 220px viewport instead (meaningless inside a now-scrolling
  container).
- New `verify_qt_utility_panels.py` (repo root, not `tests/` - same
  real reason as `verify_qt_telemetry_watch.py`): a fake transport
  answers each real request/response pair from a separate thread: real
  Global Status frame shape (and a real invalid-mode rejection), real
  SPI round trip, a real F-RAM erase (verified against the real
  documented magic payload), the 3 read-only EEPROM queries, a genuine
  timeout producing its own real "no response" text rather than
  hanging or reusing a stale value, listen-only correctly blocking
  every one of these (unlike telemetry watching, all of them genuinely
  transmit), and a final real QML load with zero warnings.
- **Custom CAN Frame - the one remaining Tkinter tab - was deliberately
  NOT migrated in this pass.** Every other advanced control in this
  deck (including the ones added here) is a specific, documented,
  bounded protocol for a known real register; Custom CAN Frame is a
  genuinely open-ended raw-frame sender (any CAN ID, any 0-8 data
  bytes, with an optional unattended periodic repeat) - a real,
  qualitatively different risk profile from everything else this deck
  has ever exposed, and porting it deserves its own explicit decision
  rather than folding it into this same pass.

## [0.1.4]

- **The Qt Quick deck now watches real, continuous telemetry for Vacuum
  Pickup and Scan Probe** - the last 2 real tool profiles with no
  advanced-control panel at all in the deck (both are telemetry-only:
  neither has a single command to send). A new `watchTelemetry()`/
  `stopTelemetryWatch()` pair starts/stops a real background read loop
  (the same `threading.Event`-per-key shape `_start_watchdog`/
  `_stop_watchdog` already use for a periodic send, adapted for a
  continuous read instead), holding the same `busy` gate every other
  read operation already does - this transport can only be read from one
  thread at a time - except `stopTelemetryWatch()` itself, which (like
  `_stop_watchdog`) is deliberately not busy-gated, so a running watch
  can always be stopped. Unlike every other advanced control, watching
  telemetry is available in listen-only mode too, since it never
  transmits a single frame - confirmed with a real assertion that
  `canWatchTelemetry` stays true while `canActuateSelectedProfile`
  (the general command gate) is correctly false.
- New pure decoders `decode_vacuum_frame()`/`is_scan_probe_impact()` in
  `advanced_protocol.py` - the one real place either shape is decoded;
  `decode_telemetry_fixture()`'s own vacuum case and the live Qt Quick
  watch both now call the same function rather than duplicating it.
- New `verify_qt_telemetry_watch.py` (repo root, not `tests/` - needs a
  real PySide6 event loop, kept out of the hardware-free suite on
  purpose): a fake transport feeds real frames through a real
  `queue.Queue` from the test thread, and real assertions cover the
  full watch lifecycle - start, live value updates via the real
  cross-thread Signal path, an unrelated frame on the wire correctly
  ignored, double-start blocked, stop-while-busy working, a real
  identity mismatch refusing to start a watch at all, and listen-only
  mode correctly still allowed.

## [0.1.3]

- **Converted every remaining `ttk.Button` in the tool-specific panels to
  the app's own `RoundedDeckButton`** (`tester_common_panels.py`,
  `tester_tool_panels.py`, `tester_panel_helpers.py` - 31 call sites) -
  the real, larger follow-up v0.1.2's own changelog entry named. Both
  files are real mixins into `TesterGUI` (per their own module
  docstrings), so `self._new_deck_button` was already reachable at every
  one of these call sites without any further plumbing - a mechanical,
  low-risk change verified with a real launch plus a real syntax check
  of all 3 files.

## [0.1.2]

- **Real user feedback: button shapes and the header didn't fully match
  HYDRA-UMC-UPDATER's own visual language, despite `RoundedDeckCard`/
  `RoundedDeckButton` already existing for exactly that purpose.**
  Found the real, concrete gap: several genuinely visible buttons
  (Refresh, Auto-Detect, Export Debug Bundle, and both the License/About
  dialogs' own Accept/Close) were still plain `ttk.Button` instead of
  the app's own `RoundedDeckButton` - now consistent. Separately, the
  animated HYDRA-UMC mark used to live inside the Connect card, nowhere
  near the app name/slogan - moved into the header row itself
  (`_build_command_deck_header`), directly left of the "URTC Tester"
  wordmark, matching UPDATER's own icon-left header layout. Many more
  `ttk.Button` calls remain in the individual tool panels
  (`tester_common_panels.py`/`tester_tool_panels.py`) - not converted
  in this pass, a real, larger follow-up (those are standalone
  functions without direct access to the app's own
  `_new_deck_button` factory today).

## [0.1.1] - Export live graphs to CSV

- `_create_live_graph()` (`tester_panel_helpers.py`) now keeps its own
  unbounded history alongside the rolling display window it already had,
  and a new "Export CSV" button under each graph (solder iron, hotend
  nozzle, hot-air nozzle temperature) writes that full history to a
  file the operator picks. The live canvas stays a short rolling window
  on purpose (that's for watching a trend, not logging one) - the
  export is deliberately backed by its own separate, never-trimmed list,
  since exporting only the last 60 rolling points "for external
  analysis" would defeat the point.
- Verified with a real Tk instantiation (no display needed via the
  offscreen-safe test itself creating a real, if hidden, root window):
  fed 4 real values through `add_point`, invoked the real export button,
  and confirmed the written CSV has the correct header and all 4 rows
  with the right values.

## [0.1.0]

- **Versioning policy adopted (ecosystem-wide).** `TESTER_VERSION`
  normalized from the 2-part `"0.1"` to the 3-part `"0.1.0"`. Added
  `bump_version.py`, invoked by both `build_exe.bat` and `build_exe.sh`
  right before the PyInstaller step, which auto-increments the version
  with a base-10 carry rule (e.g. `0.1.9` → `0.2.0`). Running from source
  never bumps it - only an actual packaged build does. `README.md` and its
  4 translations updated to document the scheme; this `CHANGELOG.md`
  created as the seed of the version history going forward. The
  `;$FILEVERSION=1.1` line in `tester_common_panels.py` was checked and
  left untouched - it's a fixed literal inside the PEAK PCAN-View `.trc`
  export format (an external trace-file convention), unrelated to this
  tool's own version number.
- Both build scripts now also print a startup banner (project name, what
  the script does, author, license) and pause before closing on both
  success and failure, so a window opened by double-clicking the script
  never disappears before its output can be read.

## Earlier history

### [0.1]

Work done across several passes while `TESTER_VERSION` was `"0.1"`,
newest first.

- **Known-issues review, 2 rounds:** completed translation
  coverage in `tester_common_panels.py` - 11 new strings across all 5
  languages (DIAG0 level text, "no response" branches for
  expansion/MLX/free-config/peripheral-info queries, and the F-RAM state
  readout, including embedded `on`/`off`/`YES`/`no` values that used to be
  hardcoded English), verified with a real Tkinter build of the full GUI
  in each language plus a simulated CAN bus exercising every modified
  query branch. Separately, added `grid_columnconfigure` weights to
  `conn_frame` (the top connection bar) so its columns share extra window
  width sensibly instead of leaving it blank on the right, verified with a
  real `Tk()` window. Left untouched, by design: power/speed
  re-confirmation policy for an already-active laser/drill, main-thread
  serial I/O blocking in keepalives, "soft" SocketCAN listen-only, Bus-Off
  vs Error-Passive distinction, and firmware mailbox starvation (out of
  scope for this repository).
- **Fixes found on code review:** fixed a real race between `clear_all()`
  (run on every panel rebuild / Detect) and `wait_for_one()` (used by
  background health polling, Self-Test, and query buttons) silently
  dropping in-flight waiters - split into a separate waiter registry from
  the persistent panel-handler registry. `_bus_health_worker` no longer
  dies silently for the rest of the session if the CAN adapter disconnects
  mid-poll. `_clear_tool_panel()` no longer cancels the global "custom
  frame" periodic-send keepalive when a tool panel rebuilds. Synchronized
  all 5 READMEs (2 missing sections, 1 missing Known Limitations bullet).
- **Hardware/protocol catch-up:** corrected inverted DIAG0 polarity
  readout after the diode-OR + pull-down hardware topology change (was
  showing HIGH/LOW backwards). `_detect_active_tool_worker` hardened with
  the same try/finally pattern already used elsewhere, so a mid-detection
  disconnect can no longer leave the Detect button permanently disabled.
  Added the MLX9064x sensor-variant query control (`0x1A7`). Version
  migrated project-wide from `0.0` to `0.1`; splash/banner assets,
  screenshots and README version references updated to match (found and
  fixed in 3 separate follow-up passes after the initial migration missed
  a duplicated `/images/` copy, real screenshots, and a bare "0.0" without
  a leading "v").

### [0.0]

Work done across several passes while `TESTER_VERSION` was `"0.0"`,
newest first.

- **Full tool/expansion-board coverage, restructuring:** built the tool
  panels for all remaining tool profiles so the Tester genuinely supports
  the full 25-tool, 6-expansion-board lineup (was previously silently
  unsupported for 13 of them). Split the single-file tool into 8 modules
  by responsibility (mixin-based architecture: `CommonPanelsMixin`,
  `PanelHelpersMixin`, `ToolPanelsMixin` combined into `TesterGUI`).
  Restructured the main window from a 3-column layout into a fixed
  connection bar plus a 5-tab notebook, with window size verified
  quantitatively (`winfo_reqheight()` vs `winfo_height()`), not just by
  eye. Added a full menu bar (File / Language / Help). README translated
  into Spanish, Italian, French and German (English already existed).
- **Internationalization:** added the `language/` `.lng` file system and
  the `_()` lookup helper, English and Spanish first, then Italian, French
  and German - a 5-language selector replacing the original
  English/Spanish checkbox. Designed a safe pattern
  (`_translated_combobox`) for the 5 comboboxes whose selected value is
  compared directly against an English string in the CAN-send logic, so
  translating the display text couldn't silently break what actually gets
  sent - verified by checking the real CAN bytes sent after a simulated
  language-translated selection, not just the displayed text.
- **External audits (5th and 6th rounds):** 5th audit (25 findings) - 17
  real fixes (thread-safety races, unvalidated Spinbox input, TRC/ASC
  export timestamp corruption, an independent copy of the SLCAN code that
  had drifted from earlier fixes elsewhere), 4 confirmed false positives,
  4 documented/known limitations. 6th audit (27 findings) - 13 real fixes
  (missing `HAVE_SERIAL` checks, a write lock missing around the actual
  port/socket write, event-queue flooding under high CAN traffic batched
  into a 50ms flush, a real bug where a failed frame send in a tuple
  silently skipped the remaining sends), 10 confirmed false positives
  (several verified empirically rather than taken on faith), 3 more
  attributable to the auditor reading a truncated view of the file.

---

Earlier work (initial feature set: CAN frame injector, raw bus monitor,
live telemetry graphs, `.trc`/`.asc` log export, Pass/Fail self-test, and
the original single-file `V0.0` tool) predates this changelog's level of
detail.
