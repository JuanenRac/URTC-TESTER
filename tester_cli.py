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
    history [FOLDER]     list the evidence records (urtc-evidence/1) of a folder (default: --out), checking each one; touches no bus
    report               write a report of the evidence records of --evidence-dir as one HTML page or a PDF (--out FILE, --format html|pdf);
                         every record is listed, one that fails its check as NOT VALID (exit 1, the report is written all the same); touches no bus

With ``--transport simulate`` a bus scenario (``--scenario FILE``, urtc-scenario/1, see urtc_can/bus_scenario.py) makes the simulated bus lose, repeat, reorder,
delay or cut frames, or the head stay silent or refuse, the same way for the same seed; the records then say they come from a simulation with that scenario.

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
from tester_config import TESTER_VERSION
from tester_result_record import make_record, save_evidence, save_record

EXIT_PASS, EXIT_FAIL, EXIT_USAGE, EXIT_ERROR, EXIT_CANCELLED = 0, 1, 2, 3, 130
TRANSPORTS = ("serial", "socketcan", "python-can", "simulate", "replay")
BITRATE = 500000


def _say(message: str) -> None:
    print(message, flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="urtc_tester.py --headless", description="URTC Tester without a window: identify, self-test and run test plans against a tool head.")
    parser.add_argument("command", choices=("info", "selftest", "run-plan", "validate-plan", "history", "report"))
    parser.add_argument("plan", nargs="?", help="the plan file, for run-plan and validate-plan; the folder of the records, for history")
    parser.add_argument("--transport", choices=TRANSPORTS, default="serial",
                        help="serial (SLCAN adapter, default), socketcan (Linux), python-can (PCAN, Kvaser, gs_usb ...), simulate (an in-memory tool head, "
                             "nothing real is touched) or replay (the frames of a .trc/.asc trace)")
    parser.add_argument("--port", help="serial port (COM3, /dev/ttyACM0), SocketCAN interface (can0), <interface>:<channel> for python-can, or the trace file for replay")
    parser.add_argument("--tool", type=int, default=0, help="with --transport simulate: the tool id the simulated head plays (default 0)")
    parser.add_argument("--fault", choices=("system", "can", "thermal"), default=None, help="with --transport simulate: make the simulated head report this fault")
    parser.add_argument("--scenario", default=None, metavar="FILE",
                        help="with --transport simulate: a bus scenario (urtc-scenario/1) that makes the simulated bus lose, repeat, reorder, delay or cut frames, or the head stay silent or refuse; "
                             "off unless given; never accepted with a real adapter")
    parser.add_argument("--seed", type=int, default=None, help="with --scenario: the seed of the scenario for this run (default: the one in the file)")
    parser.add_argument("--out", default=None, help="folder for the log and the result record (default: logs); for report, the file of the report")
    parser.add_argument("--evidence-dir", default=None, metavar="DIR", help="with report: the folder of the evidence records to report on")
    parser.add_argument("--format", choices=("html", "pdf"), default=None, help="with report: html or pdf (default: by the extension of --out, else html)")
    parser.add_argument("--language", default="english", metavar="NAME",
                        help="with report: the language of the texts (english, spanish, italian, french, german, chinese, japanese, portuguese; the PDF embeds a Chinese and Japanese font subset)")
    parser.add_argument("--json", action="store_true", help="print the result as one JSON object instead of text")
    parser.add_argument("--allow-actuation", action="store_true", help="let a plan that says \"actuation\": true send commands that are not queries (heaters, motors, laser ...)")
    parser.add_argument("--assume-yes", action="store_true", help="answer yes to the confirm steps of a plan (only when a person has looked at what the step asks)")
    parser.add_argument("--timeout", type=float, default=None, help="stop the plan after this many seconds (counted between steps)")
    return parser


def _open_transport(args, virtual=None):
    kind = args.transport
    if kind == "simulate":
        from tester_simulator import make_board
        if virtual is not None:   # a scenario run lives on a clock of its own: no real waiting, the same timing every time
            return make_board(args.tool, fault=args.fault, delay=0.0, clock=virtual.clock)
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


SCENARIO_READ_COST_S = 0.001   # the time one read of the simulated bus takes on the clock of a scenario run


def _scenario_bus(args, transport, virtual=None):
    """The simulated head behind the bus of the scenario named by ``--scenario``, or the head itself when none was asked for."""
    if not args.scenario:
        return transport
    from urtc_can import bus_scenario
    return bus_scenario.FaultyBus(transport, bus_scenario.load(args.scenario), seed=args.seed, clock=virtual.clock, sleep=virtual.sleep,
                                  read_cost_s=SCENARIO_READ_COST_S)


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


def _write_results(report, plan_name: str, args, out_dir: Path, transport=None) -> tuple[Path, Path]:
    adapter, note = f"{args.transport}:{args.port or 'in-memory'}", ""
    if args.scenario and hasattr(transport, "summary"):
        adapter, note = f"{args.transport}:scenario:{transport.scenario.name}", "SIMULATED bus with a scenario; " + transport.summary()
    return write_report(report, plan_name, adapter, out_dir, note)


def write_report(report, plan_name: str, adapter: str, out_dir: Path, note: str = "") -> tuple[Path, Path]:
    """The log of a plan and its result record (naming the log by its SHA-256), side by side in `out_dir`: (log path, record path)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    log_path = out_dir / f"{plan_name}_{stamp}.log"
    log_path.write_text(report.log_text(plan_name), encoding="utf-8")
    record = make_record(
        test_name=plan_name, outcome=report.outcome, adapter=adapter,
        firmware_version=report.firmware_version or "unknown", bus="can", bitrate=BITRATE, log_path=log_path,
        detail=f"tool {report.tool_id if report.tool_id is not None else 'unknown'}; {report.summary()}" + (f"; {note}" if note else ""),
    )
    record_path = log_path.with_suffix(".json")
    save_record(record, record_path)
    try:
        save_evidence(record, out_dir / f"urtc_evidence_{log_path.stem}.json", tool_version=TESTER_VERSION)
    except (OSError, ValueError):
        pass  # the common-shape copy is an extra: the log and the result record above are what a run leaves, and they are written
    return log_path, record_path


def _history(args) -> int:
    """The evidence records of a folder, listed and checked (the same view as the other programs); 1 when one of them fails its check."""
    from urtc_can import evidence_history
    try:
        loaded = evidence_history.load_folder(args.plan or args.out)
    except FileNotFoundError as exc:
        _say(f"ERROR: {exc}")
        return EXIT_USAGE
    entries, others = evidence_history.select(loaded), evidence_history.others_of(loaded)    # the result records of the tester are not evidence: listed apart, never as not valid
    _say(evidence_history.to_json(entries, others).rstrip("\n") if args.json else evidence_history.to_text(entries, others))
    return EXIT_FAIL if any(not entry.valid for entry in entries) else EXIT_PASS


def _report(args, out: str | None) -> int:
    """The report of the evidence records of a folder written to a file; 1 when a record is not valid (the report is written all the same), 2 for wrong arguments."""
    from urtc_can import evidence_history, evidence_report, evidence_report_strings
    if not args.evidence_dir or not out:
        _say("ERROR: report needs --evidence-dir DIR and --out FILE.")
        return EXIT_USAGE
    if args.language not in evidence_report_strings.LANGUAGES:
        _say(f"ERROR: --language must be one of {', '.join(evidence_report_strings.LANGUAGES)}.")
        return EXIT_USAGE
    target = Path(out)
    fmt = args.format or ("pdf" if target.suffix.lower() == ".pdf" else "html")
    try:
        entries = evidence_history.load_folder(args.evidence_dir)
    except FileNotFoundError as exc:
        _say(f"ERROR: {exc}")
        return EXIT_USAGE
    if target.is_dir():
        _say(f"ERROR: {target} is a folder; --out is the file of the report.")
        return EXIT_USAGE
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(evidence_report.render(entries, fmt, args.language))
    except OSError as exc:
        _say(f"ERROR: cannot write the report: {exc}")
        return EXIT_ERROR
    counts = evidence_history.summary(entries)
    invalid = counts["invalid"]
    other = f", {counts['others']} other record(s), not evidence" if counts["others"] else ""
    _say(f"Report ({fmt}): {target} - {counts['records']} record(s), {counts['valid']} valid, {invalid} not valid{other}")
    return EXIT_FAIL if invalid else EXIT_PASS


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    report_out = args.out
    args.out = args.out or "logs"
    if args.command == "report":
        return _report(args, report_out)
    if args.command == "history":
        return _history(args)
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
    if args.scenario and args.transport != "simulate":
        _say("ERROR: --scenario is only for --transport simulate; a scenario is never applied to a real adapter or a recorded trace.")
        return EXIT_USAGE
    if args.seed is not None and not args.scenario:
        _say("ERROR: --seed goes with --scenario.")
        return EXIT_USAGE
    virtual = None
    if args.scenario:
        from urtc_can import bus_scenario
        virtual = bus_scenario.VirtualTime()
    try:
        transport = _scenario_bus(args, _open_transport(args, virtual), virtual)
    except ValueError as exc:
        _say(f"ERROR: {exc}")
        return EXIT_USAGE
    except Exception as exc:
        _say(f"ERROR: cannot open the transport: {exc}")
        return EXIT_ERROR
    deadline = None if args.timeout is None else time.monotonic() + args.timeout
    try:
        transport.open_channel()
        clock, sleep = (virtual.clock, virtual.sleep) if virtual is not None else (time.monotonic, time.sleep)
        report = tester_plan.run_plan(plan, transport, allow_actuation=args.allow_actuation, confirm=_confirm_for(args), clock=clock, sleep=sleep,
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
    log_path, record_path = _write_results(report, plan["name"], args, Path(args.out), transport)
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
