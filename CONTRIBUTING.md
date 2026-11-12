# Contributing to URTC-TESTER 🧰

## Technology Stack
- **Language**: Python.
- **Framework**: Qt Quick (PySide6).

## Guidelines
1. **Tool Panels**: Add the backend slots and properties of a panel to `qt_tester.py` and its QML to `assets/qml/TesterDeck.qml`; keep the CAN encoders in `advanced_protocol.py`.
2. **Keepalives**: Use the watchdog threads of `qt_tester.py` (`setWatchdogOutput`) for tools requiring heartbeats.
3. **Diagnostics**: Add new CAN IDs to `tester_config.py` for correct labeling in the Bus Monitor.
4. **Documentation language**: the files in `docs/` are written in English only, on purpose: they are technical reference for developers, kept in one language so that a change is made once and cannot drift between eight copies. The README of each repository is the part that is translated into the eight languages.
