"""Fault recorder ("black box") of the tool head: read it over CAN, check it, export it as CSV or JSON.

The firmware keeps the last ~10 s of samples in F-RAM and flushes them when the error flag rises. The host asks
for the 678-byte record in 22 chunks of 32 bytes (identifier 0x1A8, one byte: the chunk index); each chunk comes
back as four frames of eight bytes on 0x1A9. The firmware sends the bytes as they are, so the host checks the
magic number, the version and the CRC-8 before it believes the samples.

Standard library only. Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
"""
from __future__ import annotations

import csv
import io
import json
import struct
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

CAN_ID_QUERY = 0x1A8
CAN_ID_CHUNK = 0x1A9
MAGIC = 0x424C4B42
VERSION = 2
SAMPLES = 67
SAMPLE_SIZE = 10
RECORD_SIZE = 4 + 3 + SAMPLES * SAMPLE_SIZE + 1  # 678
CHUNK_BYTES = 32
CHUNK_COUNT = (RECORD_SIZE + CHUNK_BYTES - 1) // CHUNK_BYTES  # 22
FRAMES_PER_CHUNK = 4
THERMAL_FAULTS = {0: "none", 1: "max_temperature", 2: "heating_without_rise", 3: "dropped_at_target"}
CSV_COLUMNS = ("index", "tick_ms", "ms_before_last", "tool_id", "current_temperature", "target_temperature",
               "endstop", "system_error", "thermal_fault", "thermal_fault_name")


class BlackBoxError(ValueError):
    """The record is incomplete or is not a valid record."""


def crc8(data: bytes) -> int:
    """CRC-8/SMBUS (polynomial 0x07), the checksum the firmware puts in the last byte."""
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


@dataclass(frozen=True)
class Sample:
    tick_ms: int
    tool_id: int
    current_temperature: int
    target_temperature: int
    flags: int

    @property
    def endstop(self) -> bool:
        return bool(self.flags & 1)

    @property
    def system_error(self) -> bool:
        return bool(self.flags & 2)

    @property
    def thermal_fault(self) -> int:
        return (self.flags >> 2) & 3


@dataclass
class Record:
    version: int
    sample_count: int
    write_index: int
    samples: list[Sample] = field(default_factory=list)  # oldest first

    @property
    def trigger_index(self) -> int | None:
        """Index (in the oldest-first list) of the first sample with the error flag set, if any."""
        for i, s in enumerate(self.samples):
            if s.system_error:
                return i
        return None


def chunk_request(index: int) -> bytes:
    """Payload of the 0x1A8 request for one chunk."""
    if not 0 <= index < CHUNK_COUNT:
        raise BlackBoxError(f"chunk index {index} out of range 0..{CHUNK_COUNT - 1}")
    return bytes([index])


def join_frames(frames: Iterable[bytes]) -> bytes:
    """The four 0x1A9 frames of one chunk, in the order received."""
    chunk = b"".join(frames)
    if len(chunk) != CHUNK_BYTES:
        raise BlackBoxError(f"a chunk is {CHUNK_BYTES} bytes, got {len(chunk)}")
    return chunk


def parse(raw: bytes) -> Record:
    """Check and decode the 678-byte record (the last chunk's zero padding may follow and is ignored)."""
    if len(raw) < RECORD_SIZE:
        raise BlackBoxError(f"record is {RECORD_SIZE} bytes, got {len(raw)}")
    raw = bytes(raw[:RECORD_SIZE])
    magic, version, count, widx = struct.unpack_from("<IBBB", raw, 0)
    if magic != MAGIC:
        raise BlackBoxError("no record (magic number does not match)")
    if version != VERSION:
        raise BlackBoxError(f"record version {version}, this reader knows {VERSION}")
    if crc8(raw[:-1]) != raw[-1]:
        raise BlackBoxError("checksum mismatch: the record is damaged")
    if count > SAMPLES or widx >= SAMPLES:
        raise BlackBoxError("sample count or write index out of range")
    ring = [Sample(*struct.unpack_from("<IBHHB", raw, 7 + i * SAMPLE_SIZE)) for i in range(SAMPLES)]
    # Oldest first: with a full ring the oldest sample sits at the write index; before that the ring starts at 0.
    ordered = ring[widx:] + ring[:widx] if count == SAMPLES else ring[:count]
    return Record(version, count, widx, ordered)


def build(samples: list[Sample], write_index: int | None = None, version: int = VERSION) -> bytes:
    """Make a record the way the firmware lays it out (used by the simulator and the tests)."""
    if len(samples) > SAMPLES:
        raise BlackBoxError("too many samples")
    count = len(samples)
    ring = list(samples)
    if count == SAMPLES:
        widx = 0 if write_index is None else write_index
        ring = ring[-widx:] + ring[:-widx] if widx else ring  # undo the rotation parse() does
    else:
        widx = count % SAMPLES
    ring += [Sample(0, 0, 0, 0, 0)] * (SAMPLES - len(ring))
    body = struct.pack("<IBBB", MAGIC, version, count, widx)
    body += b"".join(struct.pack("<IBHHB", s.tick_ms, s.tool_id, s.current_temperature, s.target_temperature, s.flags) for s in ring)
    return body + bytes([crc8(body)])


class Recorder:
    """What the firmware does once every ~150 ms (``BlackBox_Sample``), written down independently of the C code.

    Each tick appends one sample to a ring of ``SAMPLES``; on the rising edge of the error flag (and only once for each fault: the latch is
    re-armed when the flag falls) the whole ring is flushed as one record. ``flags`` of a sample are bit 0 the end-stop, bit 1 the error flag
    and bits 2-3 the code of the thermal guard. The vectors of the recorder (``conformance/blackbox_vectors.json``) are produced by this
    class and replayed against ``firmware_blackbox.c`` by the host tests of the firmware.
    """

    def __init__(self) -> None:
        self.ring = [Sample(0, 0, 0, 0, 0)] * SAMPLES
        self.write_index = 0
        self.sample_count = 0
        self._previous_error = False
        self._flushed_for_this_fault = False

    def tick(self, tick_ms: int, tool_id: int, current: int, target: int, endstop: bool, error: bool, thermal_code: int) -> bytes | None:
        """Takes one sample; returns the record flushed by this tick, or None."""
        flags = (1 if endstop else 0) | (2 if error else 0) | ((thermal_code & 3) << 2)
        self.ring[self.write_index] = Sample(tick_ms & 0xFFFFFFFF, tool_id & 0xFF, current & 0xFFFF, target & 0xFFFF, flags)
        self.write_index = (self.write_index + 1) % SAMPLES
        if self.sample_count < SAMPLES:
            self.sample_count += 1
        record = None
        if error and not self._previous_error and not self._flushed_for_this_fault:
            record = self.record()
            self._flushed_for_this_fault = True
        if not error:
            self._flushed_for_this_fault = False
        self._previous_error = error
        return record

    def record(self) -> bytes:
        body = struct.pack("<IBBB", MAGIC, VERSION, self.sample_count, self.write_index)
        body += b"".join(struct.pack("<IBHHB", x.tick_ms, x.tool_id, x.current_temperature, x.target_temperature, x.flags) for x in self.ring)
        return body + bytes([crc8(body)])


def download(request: Callable[[int], bytes | None]) -> Record:
    """Read the whole record. ``request(index)`` sends 0x1A8 and returns the 32 bytes of the answer, or None when none came."""
    raw = bytearray()
    for index in range(CHUNK_COUNT):
        chunk = request(index)
        if chunk is None or len(chunk) != CHUNK_BYTES:
            raise BlackBoxError(f"chunk {index} is missing or incomplete")
        raw += chunk
    return parse(bytes(raw))


class FaultTrigger:
    """Tells when to read the black box: once for each rising edge of the error flag in 0x111 (byte 1)."""

    def __init__(self) -> None:
        self._was_set = False

    def feed(self, active_tool_payload: bytes) -> bool:
        if len(active_tool_payload) < 2:
            return False
        is_set = bool(active_tool_payload[1])
        fire = is_set and not self._was_set
        self._was_set = is_set
        return fire

    def reset(self) -> None:
        self._was_set = False


def rows(record: Record) -> list[dict]:
    """One row per sample with its timestamp (board milliseconds and milliseconds before the last sample)."""
    last = record.samples[-1].tick_ms if record.samples else 0
    out = []
    for i, s in enumerate(record.samples):
        out.append({
            "index": i, "tick_ms": s.tick_ms, "ms_before_last": (last - s.tick_ms) & 0xFFFFFFFF,
            "tool_id": s.tool_id, "current_temperature": s.current_temperature,
            "target_temperature": s.target_temperature, "endstop": int(s.endstop),
            "system_error": int(s.system_error), "thermal_fault": s.thermal_fault,
            "thermal_fault_name": THERMAL_FAULTS[s.thermal_fault],
        })
    return out


def to_csv(record: Record) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows(record))
    return buf.getvalue()


def to_json(record: Record, captured_at: str | None = None) -> str:
    """JSON with the samples and what triggered the record; ``captured_at`` is the host's UTC time, when the caller has it."""
    trig = record.trigger_index
    doc = {
        "format": "urtc-blackbox/1", "record_version": record.version, "captured_at": captured_at,
        "sample_count": record.sample_count, "trigger_index": trig,
        "trigger_tick_ms": record.samples[trig].tick_ms if trig is not None else None,
        "samples": rows(record),
    }
    return json.dumps(doc, indent=2) + "\n"
