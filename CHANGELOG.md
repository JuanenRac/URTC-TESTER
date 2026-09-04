# Changelog

All notable changes to URTC Tester are summarized here, newest first. This
is a condensed summary aimed at users of the tool; the full line-by-line
audit trail (internal, not published) lives in a private internal log.

Versioning follows `MAJOR.MINOR.PATCH` (see the "Versioning" note in
`README.md`). Starting with this entry, `TESTER_VERSION` is bumped
automatically by `build_exe.bat`/`build_exe.sh` on every real build, base-10
"odometer" style (PATCH +1, carrying into MINOR past 9).

## [Unreleased] - Chinese and Japanese added to the Language menu

### Added
- **Real About window**, matching HYDRA-UMC-STUDIO's own `About.tsx` and
  URTC-FLASHER's own Tkinter AboutDialog: a tagline, a one-paragraph
  description, and a real Version/Author/Email/License info block, not
  just a banner and one line of text. New `TITLE_ABOUT`/`ABOUT_TAGLINE`/
  `ABOUT_DESCRIPTION`/`ABOUT_VERSION`/`ABOUT_AUTHOR`/`ABOUT_EMAIL`/
  `ABOUT_LICENSE`/`BTN_CLOSE` keys across all 7 languages, replacing the
  old `LBL_ABOUT_AUTHOR` - full key parity verified.

### Fixed
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

### Fixed
- SLCAN reception now discards impossible CAN 2.0 DLC values (`9`-`F`) rather
  than passing oversized frames to GUI handlers. Valid standard frames are
  unaffected.

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

## [0.1]

Work done across several passes while `TESTER_VERSION` was `"0.1"`,
newest first.

- **`mejoras_futuras.txt` review, 2 rounds:** completed translation
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
- **Ecosystem-wide audit fixes:** fixed a real race between `clear_all()`
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

## [0.0]

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
detail; the complete record lives in the private internal log.
