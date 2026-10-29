# Source map

Every file of the repository with a line on what it does: the annotated tree that the README carried before it was reduced to the first level (the first level, in eight languages, is in the section Repository Structure of the README).

```text
/
├── urtc_tester.py             Entry point - starts the Qt Quick deck
├── qt_tester.py                Qt Quick front end - real default, read-only-by-default command deck
├── tester_config.py            Config/language/protocol constants (CAN IDs, tool
│                                names, MOTION_TOOL_IDS, AVAILABLE_LANGUAGES,
│                                EXPANSION_BOARD_TYPES)
├── tester_transports.py        SLCAN and SocketCAN transport classes
├── tester_bus_monitor.py       Background CAN read thread (CANBusMonitor)
├── tester_autodetect.py        Bit-rate search for an SLCAN adapter
├── tester_selftest.py          Self-test steps and runner (no window code)
├── tester_plan.py              Test plans: validation, runner and the "all off" after them
├── tester_cli.py               The tester without a window (--headless): info, selftest, run-plan
├── tester_simulator.py         Simulated tool head and recorded-trace player
├── plans/                      Example test plans (JSON)
├── tester_telemetry.py         Live readouts of each tool and the recorded series
├── tester_trace_export.py      Writers of the .trc / .asc frame exports
├── tester_replay.py            Replay of a recorded .trc / .asc trace (a player with no timer of its own)
├── tester_blackbox_view.py     The black box record as the deck draws it: chart series, table, saved records opened with no board
├── tester_result_record.py     Result records tied to the adapter, the firmware and a log by its SHA-256 (JSON)
├── tester_extras.py            Logic with no Qt of the fault recorder, optional functions, heater PID, rack bench and thermal view
├── urtc_ui/                    Shared interface helpers (copy from URTC-COMMON)
├── urtc_can/                   Shared code copied from URTC-COMMON: protocol, transports, virtual board, updates, help and the tool heads window
├── advanced_protocol.py        Pure CAN payload encoders for the migrated Qt
│                                Quick control families - hardware-free tests
├── verify_qt_custom_frame.py        Real, outside-tests/ end-to-end check of the Qt Quick Custom CAN Frame panel (needs a real Qt event loop)
├── verify_qt_telemetry_watch.py     Real, outside-tests/ end-to-end check of the Qt Quick telemetry watch (Vacuum Pickup / Scan Probe)
├── verify_qt_utility_panels.py      Real, outside-tests/ end-to-end check of the Qt Quick utility panels (Global Controls / Expansion Board / F-RAM)
├── verify_qt_selftest.py            Real, outside-tests/ end-to-end check of the Qt Quick self-test
├── tests/
│   ├── test_advanced_protocol.py   Hardware-free tests for advanced_protocol.py's encoders - run by CI, see Honesty check above
│   ├── test_*.py                   One file per area of the program; the CI runs them, the Qt ones offscreen
│   └── fixtures/                   Vectors shared with the other programs and recorded traces
├── requirements.txt            pyserial>=3.5 + PySide6>=6.8,<7
├── build_exe.bat               Standalone Windows binary build script (PyInstaller)
├── build_exe.sh                Same, for Linux
├── build-test.bat              Non-versioning build/compile check
├── build-test.sh                Same, for Linux
├── bump.py                     Explicit version bump command (building never bumps)
├── bump_version.py             version bump, called by bump.py
├── bump_manifest_version.py    Syncs urtc.project.json's version to the native one (--sync)
├── URTC_Tester.spec            PyInstaller spec used by both build scripts
├── requirements-dev.txt / requirements*.lock Dependencies of the tests and of the build, closed with hashes
├── mypy.ini / ruff.toml / pytest.ini Settings of the type check and of the static checks
├── urtc_i18n.lock.json         Lock of the language files generated from the catalog of URTC-COMMON
├── urtc.project.json           Project manifest (version, maturity, evidence)
├── run.bat / run.sh            Start the program
├── assets/
│   ├── URTC_APP_ICON.svg       Window/taskbar icon source (small standalone design)
│   ├── URTC_LOGO_TESTER.svg    Banner source (vector)
│   ├── qml/
│   │   ├── TesterDeck.qml      Qt Quick UI for the default command deck
│   │   ├── HelpDialog.qml      The quick-guide window (shared)
│   │   ├── NodePickerDialog.qml The tool heads window (shared)
│   │   ├── UpdateDialog.qml    The Check for updates window (shared)
│   │   └── urtc_common.lock.json Lock of the files copied from URTC-COMMON
│   ├── urtc_icon.ico           Windows icon, built from URTC_APP_ICON.svg
│   └── urtc_icon.png           Same, PNG form (Linux)
├── images/
│   ├── URTC_TESTER_BANNER.svg  Logo banner shown at the top of this README
│   └── URTC_TESTER_V1_1.png    Screenshot of the tool's main window (see Photos below)
├── language/
│   ├── english.lng             Default language, plain-text KEY=Value strings
│   ├── spanish.lng
│   ├── italian.lng
│   ├── french.lng
│   ├── german.lng
│   ├── japanese.lng
│   ├── chinese.lng
│   └── portuguese.lng
├── logs/                       Session logs written here at runtime (safe to delete)
├── LICENSE                     Full license text - see License and Copyright
│                                Notices below
├── NOTICE                      Copyright notice and the license of the documentation
├── README.md                   This file
├── README_spa.md               Spanish translation
├── README_ita.md               Italian translation
├── README_fra.md               French translation
├── README_deu.md               German translation
├── README_por.md               Portuguese translation
├── README_zho.md               Chinese translation
├── docs/
│   ├── ARCHITECTURE.md
│   ├── BUILD_AND_RUN.md
│   ├── INTEGRATION_CONTRACT.md
│   ├── CANBUS.md
│   ├── THERMAL_RUNAWAY_BENCH_TEST.md
│   ├── HEADLESS.md                  The tester without a window: commands, plans and exit codes
│   ├── WINDOW_GUIDE.md              The window step by step, with real pictures in the eight languages
│   └── screenshots/                 The pictures of the window guide, in the eight languages
├── tools/
│   ├── build_test.py                     Non-versioning build/compile check + Qt Quick deck source validation
│   ├── ci_validate.py                    Manifest/CHANGELOG/docs validation used by CI
│   ├── capture_screens.py                Takes the pictures of the window guide without a screen (one language or all)
│   ├── make_update_package.py            Builds and signs the update package of a release
│   └── _doc_policy.py / _readme_parity.py / _tracked_names.py Shared checks used by ci_validate.py
└── README_jpn.md               Japanese translation
```
