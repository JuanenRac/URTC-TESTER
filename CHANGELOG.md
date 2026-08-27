# Changelog

All notable changes to URTC Tester are summarized here, newest first. This
is a condensed summary aimed at users of the tool; the full line-by-line
audit trail (internal, not published) lives in a private internal log.

Versioning follows `MAJOR.MINOR.PATCH` (see the "Versioning" note in
`README.md`). Starting with this entry, `TESTER_VERSION` is bumped
automatically by `build_exe.bat`/`build_exe.sh` on every real build, base-10
"odometer" style (PATCH +1, carrying into MINOR past 9).

## [Unreleased] - Chinese and Japanese added to the Language menu

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
