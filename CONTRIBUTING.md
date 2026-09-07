# Contributing to URTC-TESTER 🧰

## Technology Stack
- **Language**: Python.
- **Framework**: Tkinter.

## Guidelines
1. **Tool Panels**: Add new panels as mixins in `tester_tool_panels.py`.
2. **Keepalives**: Use the `After()` loop for tools requiring watchdog heartbeats.
3. **Diagnostics**: Add new CAN IDs to `tester_config.py` for correct labeling in the Bus Monitor.
