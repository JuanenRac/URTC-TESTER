"""Crash capture of the tool head: read the registers the last HardFault left, check them, show them in words.

When the processor faults, the firmware built with the crash capture switched on (``URTC_CRASH_DUMP``) cuts every output, copies the stacked
registers and the fault status registers into a record in RAM that survives the reset, and waits for the watchdog. After the board is back the
host asks for the record (identifier 0x1BC, one byte: operation 0) and gets six frames of eight bytes on 0x1BD: 48 bytes, every word
little-endian, ending in a CRC-32 of the first 44. The host believes the record only when the magic, the version and the CRC agree.

Standard library only. Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
"""
from __future__ import annotations

import json
import struct
import zlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass

CAN_ID_QUERY = 0x1BC
CAN_ID_RESPONSE = 0x1BD
MAGIC = 0x48535243  # "CRSH" in memory order
VERSION = 1
RECORD_SIZE = 48
FRAME_COUNT = 6
KIND_NONE = 0
KIND_FAULT = 1
KIND_FAULT_NO_FRAME = 2
KIND_NAMES = {KIND_NONE: "none", KIND_FAULT: "fault", KIND_FAULT_NO_FRAME: "fault_no_frame"}
_LAYOUT = struct.Struct("<10I4BI")

# The bit field of the reset cause, the same as byte 1 of 0x1BB and byte 5 of 0x111.
RESET_CAUSES = ((0x01, "independent_watchdog"), (0x02, "window_watchdog"), (0x04, "software"), (0x08, "power_on"),
                (0x10, "reset_pin"), (0x20, "low_power"), (0x40, "option_byte_load"))
# Bits of the configurable fault status register (CFSR) that name a cause, lowest first: memory management, bus and usage faults.
CFSR_BITS = (
    (0, "instruction_access_violation"), (1, "data_access_violation"), (3, "unstacking_error"), (4, "stacking_error"), (5, "lazy_fp_error"),
    (7, "mmfar_valid"), (8, "instruction_bus_error"), (9, "precise_data_bus_error"), (10, "imprecise_data_bus_error"),
    (11, "unstacking_bus_error"), (12, "stacking_bus_error"), (13, "lazy_fp_bus_error"), (15, "bfar_valid"),
    (16, "undefined_instruction"), (17, "invalid_state"), (18, "invalid_pc_load"), (19, "no_coprocessor"),
    (24, "unaligned_access"), (25, "divide_by_zero"),
)
HFSR_BITS = ((1, "vector_table_read"), (30, "forced"), (31, "debug_event"))


class CrashDumpError(ValueError):
    """The record is incomplete or is not a valid record."""


@dataclass(frozen=True)
class CrashDump:
    seq: int
    pc: int
    lr: int
    xpsr: int
    cfsr: int
    hfsr: int
    mmfar: int
    bfar: int
    sp: int
    reset_cause: int
    kind: int
    version: int

    @property
    def crashed(self) -> bool:
        return self.kind != KIND_NONE

    @property
    def kind_name(self) -> str:
        return KIND_NAMES.get(self.kind, "unknown")

    @property
    def reset_cause_names(self) -> list[str]:
        return [name for bit, name in RESET_CAUSES if self.reset_cause & bit]

    @property
    def cfsr_names(self) -> list[str]:
        return [name for bit, name in CFSR_BITS if self.cfsr & (1 << bit)]

    @property
    def hfsr_names(self) -> list[str]:
        return [name for bit, name in HFSR_BITS if self.hfsr & (1 << bit)]

    @property
    def fault_address(self) -> int | None:
        """The address that caused a memory or bus fault, when the status register says the address register holds it."""
        if self.cfsr & (1 << 15):
            return self.bfar
        if self.cfsr & (1 << 7):
            return self.mmfar
        return None


def query_request(operation: int = 0) -> bytes:
    """Payload of the 0x1BC request."""
    if operation != 0:
        raise CrashDumpError("the only operation is 0 (read the record)")
    return bytes([operation])


def join_frames(frames: Iterable[bytes]) -> bytes:
    """The six 0x1BD frames of the answer, in the order received."""
    raw = b"".join(frames)
    if len(raw) != RECORD_SIZE:
        raise CrashDumpError(f"the answer is {RECORD_SIZE} bytes in {FRAME_COUNT} frames, got {len(raw)}")
    return raw


def parse(raw: bytes) -> CrashDump:
    """Check and decode the 48-byte record."""
    if len(raw) != RECORD_SIZE:
        raise CrashDumpError(f"record is {RECORD_SIZE} bytes, got {len(raw)}")
    fields = _LAYOUT.unpack(bytes(raw))
    magic, seq, pc, lr, xpsr, cfsr, hfsr, mmfar, bfar, sp, reset_cause, kind, version, reserved, crc = fields
    if magic != MAGIC:
        raise CrashDumpError("no record (magic number does not match)")
    if version != VERSION:
        raise CrashDumpError(f"record version {version}, this reader knows {VERSION}")
    if zlib.crc32(bytes(raw[:-4])) != crc:
        raise CrashDumpError("checksum mismatch: the record is damaged")
    if kind not in KIND_NAMES or reserved != 0:
        raise CrashDumpError("kind or reserved byte out of range")
    return CrashDump(seq, pc, lr, xpsr, cfsr, hfsr, mmfar, bfar, sp, reset_cause, kind, version)


def build(seq: int = 0, pc: int = 0, lr: int = 0, xpsr: int = 0, cfsr: int = 0, hfsr: int = 0, mmfar: int = 0, bfar: int = 0, sp: int = 0,
          reset_cause: int = 0, kind: int = KIND_NONE, version: int = VERSION) -> bytes:
    """Make a record the way the firmware lays it out (used by the simulator and the tests)."""
    body = struct.pack("<10I4B", MAGIC, seq & 0xFFFFFFFF, pc & 0xFFFFFFFF, lr & 0xFFFFFFFF, xpsr & 0xFFFFFFFF, cfsr & 0xFFFFFFFF,
                       hfsr & 0xFFFFFFFF, mmfar & 0xFFFFFFFF, bfar & 0xFFFFFFFF, sp & 0xFFFFFFFF, reset_cause & 0xFF, kind & 0xFF, version & 0xFF, 0)
    return body + struct.pack("<I", zlib.crc32(body))


def download(request: Callable[[], list[bytes] | None]) -> CrashDump:
    """Read the record. ``request()`` sends 0x1BC and returns the data of the 0x1BD frames in the order received, or None when none came."""
    frames = request()
    if frames is None or len(frames) != FRAME_COUNT or any(len(f) != 8 for f in frames):
        raise CrashDumpError(f"the answer is missing or incomplete (expected {FRAME_COUNT} frames of 8 bytes)")
    return parse(join_frames(frames))


def summary(dump: CrashDump) -> str:
    """One line for a log: what happened and where."""
    if not dump.crashed:
        return "no crash since power-up"
    where = f"pc=0x{dump.pc:08X} lr=0x{dump.lr:08X}" if dump.kind == KIND_FAULT else "stack not readable"
    why = ",".join(dump.cfsr_names + dump.hfsr_names) or "no cause bit"
    return f"crash #{dump.seq}: {where} cfsr=0x{dump.cfsr:08X} hfsr=0x{dump.hfsr:08X} ({why}); reset: {','.join(dump.reset_cause_names) or 'unknown'}"


def to_json(dump: CrashDump, captured_at: str | None = None) -> str:
    """JSON with every register in hexadecimal and the causes in words; ``captured_at`` is the host's UTC time, when the caller has it."""
    address = dump.fault_address
    doc = {
        "format": "urtc-crashdump/1", "record_version": dump.version, "captured_at": captured_at, "crashed": dump.crashed,
        "kind": dump.kind_name, "crash_count": dump.seq,
        "registers": {name: f"0x{getattr(dump, name):08X}" for name in ("pc", "lr", "xpsr", "cfsr", "hfsr", "mmfar", "bfar", "sp")},
        "fault_address": None if address is None else f"0x{address:08X}",
        "causes": dump.cfsr_names + dump.hfsr_names, "reset_cause": dump.reset_cause, "reset_cause_names": dump.reset_cause_names,
    }
    return json.dumps(doc, indent=2) + "\n"
