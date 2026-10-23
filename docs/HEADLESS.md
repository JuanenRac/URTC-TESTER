# Running the tester without a window

`python urtc_tester.py --headless COMMAND [options]` starts no window and needs no PySide6. It is for a production line, a bench script or a CI job that has no display. It uses the same transports as the deck, the same protocol module and the same result record.

| Command | What it does |
|---|---|
| `info` | Asks who answers: the version (0x7F8), the quick state (0x110). Fails when the board reports a fault. |
| `selftest` | The same checks and the same at-rest commands as the self-test of the deck, for the tool that answers. |
| `run-plan FILE` | Runs a test plan (below). |
| `validate-plan FILE` | Checks a plan without opening any bus. |

| Option | Meaning |
|---|---|
| `--transport serial\|socketcan\|python-can\|simulate\|replay` | `serial` is an SLCAN adapter (the default), `socketcan` Linux, `python-can` PCAN, Kvaser, gs_usb and the like; `simulate` plays a simulated tool head in memory; `replay` plays the frames of a recorded `.trc` or `.asc` trace. |
| `--port` | The serial port, the SocketCAN interface, `interface:channel` for python-can, or the trace file for `replay`. |
| `--tool N`, `--fault system\|can\|thermal` | With `simulate`: the tool the head plays and a fault it reports. |
| `--out DIR` | Where the log and the result record go (default `logs`). |
| `--json` | One JSON object with every step instead of text. |
| `--allow-actuation` | Lets a plan that says `"actuation": true` send commands that are not queries. |
| `--assume-yes` | Answers yes to the `confirm` steps. Use it only when a person has looked at what the step asks. |
| `--timeout SECONDS` | Stops starting new steps after this time. |

Exit status: `0` everything passed, `1` a check failed, `2` the plan or the arguments are wrong (nothing was sent), `3` the test could not be carried out (no transport, a step that had to be refused or could not be answered, nobody to confirm), `130` cancelled with Ctrl+C. The text it prints is English, like the command line of the flasher.

## Result files

Every run that touches a bus writes `<name>_<time>.log` (every frame sent and received with its time, the answer of each step) and `<name>_<time>.json`, a result record like the one of the deck: the outcome, the adapter, the firmware version found, the bus settings and the SHA-256 of the log, so that a log edited afterwards no longer matches its result (`tester_result_record.load_record` checks it).

## A test plan

A plan is a JSON file (see `plans/`):

```json
{
  "format": 1,
  "name": "soldering-iron-bench",
  "description": "free text",
  "actuation": true,
  "steps": [
    {"do": "expect_tool", "tool": 0},
    {"do": "send", "id": "0x130", "data": "00A0"},
    {"do": "expect_frame", "id": "0x135", "within_ms": 3000, "length": 2, "value": {"offset": 0, "width": 2, "min": 140, "max": 200}},
    {"do": "confirm", "text": "Is the tip warm and is nothing smoking?"},
    {"do": "send", "id": "0x130", "data": "0000"}
  ]
}
```

`name` is 1 to 64 letters, digits, `.`, `_` or `-` because it names the result files. Every step may have a `label`.

| `do` | Fields | Passes when |
|---|---|---|
| `expect_tool` | `tool` | the active-tool answer (0x111) names that tool |
| `check_faults` | | the quick state reports no system error, no CAN error, no thermal fault and no watchdog reset |
| `query_version` | `min_version`, `hardware_id` (both optional) | the application (not the boot-loader) answers 0x7F8, with at least that version and that hardware id |
| `selftest` | | the self-test of the tool that answers has no failed check |
| `send` | `id`, `data`, `keepalive_ms` (optional, 20 to 200) | the frame was sent (see the rules below); with `keepalive_ms` a command is repeated while the plan waits |
| `expect_frame` | `id`, `within_ms` (default 500), `length`, `value` | a frame with that identifier arrives after the last `send`, with that length and, for `value`, an unsigned big-endian field of `width` 1 to 4 bytes at `offset` between `min` and `max` |
| `wait` | `ms` (up to 60000) | always; the frames that arrive meanwhile are kept for the next `expect_frame` |
| `confirm` | `text` | a person answers yes at the terminal (or `--assume-yes`) |

A failed step does not stop the plan. An error does (a transport that breaks, a refused actuation, a `confirm` with nobody there): the steps after it are reported as skipped and the plan as an error, never as a pass.

### What a plan may send

* Queries (active tool, version, error counters, F-RAM, counters, the read-back requests of the configuration registers and the fault recorder) are always allowed.
* Any other frame is a command. The plan must say `"actuation": true` and the operator must pass `--allow-actuation`; otherwise the step is an error and nothing is sent.
* Never allowed, whatever the switches: the boot-loader and update protocol (`0x7F0` to `0x7FF`), the slave link (`0x210` to `0x22F`), the writes that change what the board is or stores (`0x1A0`, `0x1A2`, `0x1A4`, `0x1A6`, `0x1AC`, `0x1AE`), the F-RAM erase (`0x192`) and the feeder reset (`0x131`). A plan that contains one is refused before the bus is opened.
* The firmware drops an order for a heater, a drill or a laser that is not refreshed within 250 ms. A plan that wants the tip to stay hot sets `keepalive_ms` (for example 100) on that `send`: the command is repeated during the later `wait`, `expect_frame` and `confirm` steps, also while a person is being asked, until a new `send` with the same identifier replaces it (an order of all zeros is not repeated). The simulated head drops the order like the firmware does, so a plan that forgot it fails there.
* After a plan that sent anything beyond a query, every known "off" is sent (the same frames as the stop-all button of the deck), also when the plan ended early or with Ctrl+C.

## The simulated head and the trace player

`--transport simulate` plays the head of the tool chosen with `--tool`: it answers the active-tool and version queries, reports the telemetry of that tool by itself the way the firmware does, and follows the soldering iron and printer set-points (the tip gains 40 degrees per telemetry frame), the drill speed and the laser power (none while the interlock is locked), and it drops each of those orders again when it is not refreshed within 250 ms. `--fault` makes it report a system error, a CAN error or a thermal fault. It shows that a plan and the tester agree with each other; it is the same author's second reading of the protocol, not a board.

`--transport replay --port trace.trc` plays the frames received in a trace saved by the bus monitor (`.trc` or `.asc`) in order (the lines marked as transmitted are not played) and ignores what is sent. A plan made of `expect_frame` steps can be checked against a recorded session this way.

Nothing in this mode has run against a real board.
