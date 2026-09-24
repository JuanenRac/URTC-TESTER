# =============================================================================
# URTC-TESTER - tester_result_record.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""A test result that can be checked away from the computer that produced it.

A bare PASS says nothing about what it was run against. A `ResultRecord`
ties the outcome to the adapter, the firmware, the bus settings and a log
artefact identified by its SHA-256, and round-trips through JSON so it can
be attached to a build or a ticket. The log's hash is verified when the
record is loaded back, so an edited log no longer matches its result.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

OUTCOMES = ("pass", "fail", "error", "skipped")


class RecordError(ValueError):
    pass


@dataclass(frozen=True)
class ResultRecord:
    test_name: str
    outcome: str
    adapter: str
    firmware_version: str
    bus: str
    bitrate: int
    log_file: str
    log_sha256: str
    detail: str = ""

    def __post_init__(self) -> None:
        for name in ("test_name", "adapter", "firmware_version", "bus", "log_file"):
            if not str(getattr(self, name)).strip():
                raise RecordError(f"{name} must not be empty")
        if self.outcome not in OUTCOMES:
            raise RecordError(f"outcome must be one of {OUTCOMES}, got {self.outcome!r}")
        if isinstance(self.bitrate, bool) or not isinstance(self.bitrate, int) or self.bitrate <= 0:
            raise RecordError(f"bitrate must be a positive integer, got {self.bitrate!r}")
        if len(self.log_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.log_sha256):
            raise RecordError("log_sha256 must be 64 lowercase hexadecimal digits")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_record(
    *, test_name: str, outcome: str, adapter: str, firmware_version: str, bus: str, bitrate: int, log_path: Path, detail: str = ""
) -> ResultRecord:
    """Build a record from a log file that already exists; its hash is taken now."""
    return ResultRecord(
        test_name=test_name,
        outcome=outcome,
        adapter=adapter,
        firmware_version=firmware_version,
        bus=bus,
        bitrate=bitrate,
        log_file=log_path.name,
        log_sha256=_sha256(log_path),
        detail=detail,
    )


def save_record(record: ResultRecord, path: Path) -> None:
    path.write_text(json.dumps(asdict(record), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_record(path: Path, log_directory: Path | None = None) -> ResultRecord:
    """Read a record back. When `log_directory` is given, the log must be there and match its hash."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        record = ResultRecord(**data)
    except (OSError, ValueError, TypeError) as exc:
        raise RecordError(f"cannot read the result record: {exc}") from exc
    if log_directory is not None:
        log = log_directory / record.log_file
        if not log.is_file():
            raise RecordError(f"the log {record.log_file!r} is not in {log_directory}")
        if _sha256(log) != record.log_sha256:
            raise RecordError(f"the log {record.log_file!r} does not match the hash recorded with this result")
    return record
