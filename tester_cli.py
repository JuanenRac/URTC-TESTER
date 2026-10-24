# =============================================================================
# URTC-TESTER - tester_cli.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The tester without a window: ``python urtc_tester.py --headless COMMAND ...``.

For a production line, a bench script or a CI job that has no display. Commands:

    info           who answers: the active tool, the firmware version, the quick state
    selftest       the at-rest communication check of the tool that answers
    run-plan FILE  a test plan (see tester_plan.py and docs/HEADLESS.md)
    validate-plan FILE   check a plan without touching a bus

Every command that touches a bus writes a log of the frames (<out>/<name>_<time>.log) and a result record next to it
(<name>_<time>.json) that names the log by its SHA-256, like the record of the deck. The text it prints is English, as the
command line of the flasher.

Exit status: 0 everything passed, 1 a check failed, 2 the plan or the arguments are wrong, 3 the test could not be carried
out (no transport, a board that did not answer at all, nobody to confirm), 130 cancelled with Ctrl+C.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import tester_plan
from tester_result_record import make_record, save_record

EXIT_PASS, EXIT_FAIL, EXIT_USAGE, EXIT_ERROR, EXIT_CANCELLED = 0, 1, 2, 3, 130
TRANSPORTS = ("serial", "socketcan", "python-can", "simulate", "replay")
BITRATE = 500000


def _say(message: str) -> None:
    print(message, flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="urtc_tester.py --headless", description="URTC Tester without a window: identify, self-test and run test plans against a tool head.")
    parser.add_argument("command", choices=("info", "selftest", "run-plan", "validate-plan"))
    parser.add_argument("plan", nargs="?", help="the plan file, for run-plan and validate-plan")
    parser.add_argument("--transport", choices=TRANSPORTS, default="serial",
                        help="serial (SLCAN adapter, default), socketcan (Linux), python-can (PCAN, Kvaser, gs_usb ...), simulate (an in-memory tool head, "
                             "nothing real is touched) or replay (the frames of a .trc/.asc trace)")
    parser.add_argument("--port", help="serial port (COM3, /dev/ttyACM0), SocketCAN interface (can0), <interface>:<channel> for python-can, or the trace file for replay")
    parser.add_argument("--tool", type=int, default=0, help="with --transport simulate: the tool id the simulated head plays (default 0)")
    parser.add_argument("--fault", choices=("system", "can", "thermal"), default=None, help="with --transport simulate: make the simulated head report this fault")
    parser.add_argument("--out", default="logs", help="folder for the log and the result record (default: logs)")
    parser.add_argument("--json", action="store_true", help="print the result as one JSON object instead of text")
    parser.add_argument("--allow-actuation", action="store_true", help="let a plan that says \"actuation\": true send commands that are not queries (heaters, motors, laser ...)")
    parser.add_argument("--assume-yes", action="store_true", help="answer yes to the confirm steps of a plan (only when a person has looked at what the step asks)")
    parser.add_argument("--timeout", type=float, default=None, help="stop the plan after this many seconds (counted between steps)")
    return parser


def _open_transport(args):
    kind = args.transport
    if kind == "simulate":
        from tester_simulator import make_board
        return make_board(args.tool, fault=args.fault, delay=0.001)
    if kind == "replay":
        from tester_simulator import ReplayCAN
        if not args.port:
            raise ValueError("--port must name the trace file for --transport replay")
        return ReplayCAN(args.port)
    if not args.port:
        raise ValueError(f"--port is required for --transport {kind}")
    import tester_transports as tr
    if kind == "serial":
        if not tr.HAVE_SERIAL:
            raise ValueError("--transport serial requires pyserial (pip install pyserial)")
        return tr.SLCAN(args.port, log=_say)
    if kind == "socketcan":
        return tr.SocketCAN(args.port, log=_say)
    return tr.PythonCAN(args.port, log=_say)


def _synthetic_plan(command: str) -> dict:
    steps = [{"do": "query_version"}, {"do": "check_faults"}]
    if command == "selftest":
        steps.append({"do": "selftest"})
    return {"format": tester_plan.PLAN_FORMAT, "name": command, "steps": steps}


def _confirm_for(args):
    if args.assume_yes:
        return lambda text: True
    if sys.stdin is not None and sys.stdin.isatty():
        return lambda text: input(f"{text} [y/N] ").strip().lower() in ("y", "yes")
    return None


def _exit_code(outcome: str) -> int:
    return {tester_plan.PASS: EXIT_PASS, tester_plan.FAIL: EXIT_FAIL}.get(outcome, EXIT_ERROR)


def _write_results(report, plan_name: str, args, out_dir: Path) -> tuple[Path, Path]:
    return write_report(report, plan_name, f"{args.transport}:{args.port or 'in-memory'}", out_dir)


def write_report(report, plan_name: str, adapter: str, out_dir: Path) -> tuple[Path, Path]:
    """The log of a plan and its result record (naming the log by its SHA-256), side by side in `out_dir`: (log path, record path)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    log_path = out_dir / f"{plan_name}_{stamp}.log"
    log_path.write_text(report.log_text(plan_name), encoding="utf-8")
    record = make_record(
        test_name=plan_name, outcome=report.outcome, adapter=adapter,
        firmware_version=report.firmware_version or "unknown", bus="can", bitrate=BITRATE, log_path=log_path,
        detail=f"tool {report.tool_id if report.tool_id is not None else 'unknown'}; {report.summary()}",
    )
    record_path = log_path.with_suffix(".json")
    save_record(record, record_path)
    return log_path, record_path


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in ("run-plan", "validate-plan"):
        if not args.plan:
            _say(f"ERROR: {args.command} needs the plan file.")
            return EXIT_USAGE
        try:
            plan = tester_plan.load_plan(args.plan)
        except tester_plan.PlanError as exc:
            _say(f"ERROR: {exc}")
            return EXIT_USAGE
        if args.command == "validate-plan":
            _say(f"The plan {plan['name']} is valid: {len(plan['steps'])} steps" + (", it asks to actuate" if plan.get("actuation") else ", read-only"))
            return EXIT_PASS
    else:
        plan = _synthetic_plan(args.command)
    try:
        transport = _open_transport(args)
    except ValueError as exc:
        _say(f"ERROR: {exc}")
        return EXIT_USAGE
    except Exception as exc:
        _say(f"ERROR: cannot open the transport: {exc}")
        return EXIT_ERROR
    deadline = None if args.timeout is None else time.monotonic() + args.timeout
    try:
        transport.open_channel()
        report = tester_plan.run_plan(plan, transport, allow_actuation=args.allow_actuation, confirm=_confirm_for(args),
                                      stop=lambda: deadline is not None and time.monotonic() > deadline)
    except KeyboardInterrupt:
        _say("Cancelled.")
        return EXIT_CANCELLED
    except Exception as exc:
        _say(f"ERROR: {type(exc).__name__}: {exc}")
        return EXIT_ERROR
    finally:
        try:
            transport.close()
        except Exception:
            pass
    log_path, record_path = _write_results(report, plan["name"], args, Path(args.out))
    if args.json:
        _say(json.dumps({
            "name": report.name, "outcome": report.outcome, "tool_id": report.tool_id, "firmware_version": report.firmware_version,
            "steps": [{"index": s.index, "do": s.kind, "label": s.label, "outcome": s.outcome, "message": s.message} for s in report.steps],
            "notes": report.notes, "log": str(log_path), "record": str(record_path),
        }, indent=2))
    else:
        _say(f"Plan: {report.name} ({len(report.steps)} steps)")
        for s in report.steps:
            _say(f"  {s.index:>3}. {s.kind}{' [' + s.label + ']' if s.label else ''}: {s.outcome.upper()} - {s.message}")
        for note in report.notes:
            _say(f"  note: {note}")
        _say(report.summary())
        _say(f"Log: {log_path}")
        _say(f"Result record: {record_path}")
    return _exit_code(report.outcome)


if __name__ == "__main__":
    raise SystemExit(main())
