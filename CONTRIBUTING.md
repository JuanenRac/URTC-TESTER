# Contributing to URTC-TESTER 🧰

## Technology Stack
- **Language**: Python.
- **Framework**: Qt Quick (PySide6).

## Guidelines
1. **Tool Panels**: Add the backend slots and properties of a panel to `qt_tester.py` and its QML to `assets/qml/TesterDeck.qml`; keep the CAN encoders in `advanced_protocol.py`.
2. **Keepalives**: Use the watchdog threads of `qt_tester.py` (`setWatchdogOutput`) for tools requiring heartbeats.
3. **Diagnostics**: Add new CAN IDs to `tester_config.py` for correct labeling in the Bus Monitor.
