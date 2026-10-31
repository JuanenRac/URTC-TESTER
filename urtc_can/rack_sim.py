"""Simulator of the tool rack (URTC-SMART-RACK) for the programs that talk to it: no board needed.

It follows the rack firmware: the serial frame (start byte 0xA5, version 2, sequence, command, length, payload, CRC-8; every multi-byte value big-endian),
the SET_PREHEAT command with the per-tool limits, the anti-replay sequence per tool, the link watchdog that sends every
target to the safe state, the slot inventory with the identity of each tool (type and serial number) and the longest
pre-heat without a tool swap, and the free-configuration mode of a head (ID jumpers 0x1F: the tool is asked for, never assumed). The vectors in ``conformance/rack_vectors.json`` are checked against the C code of the
rack and against this module, so the two cannot drift apart unnoticed.

Standard library only. Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
"""
from __future__ import annotations

from dataclasses import dataclass, field

SOF = 0xA5
VERSION = 2
MAX_PAYLOAD = 16
CMD_SET_PREHEAT = 0x01
CAN_ID_SET_PREHEAT = 0x260
CAN_ID_REPLY = 0x261  # rack -> host: the reply to a command, an acknowledgement or a refusal, three bytes (command, tool, reason)
TOOL_ID_NONE = 31
TOOL_ID_LAST = 24
RACK_CEILING_C = 400
LINK_TIMEOUT_MS = 250
PREHEAT_MAX_MS = 600_000
COMMAND_MIN_INTERVAL_MS = 20  # two commands for one tool closer than this: the second is held (RACK_COMMAND_MIN_INTERVAL_MS)
CMD_ACK = 0x81
CMD_NACK = 0x82
REPLY_PAYLOAD_LEN = 3
REPLY_TOOL_NONE = 0xFF
# The reason the rack tells the sender, in the order of rack_reply_code_t of the firmware (APPLIED and REPEAT are acknowledgements, the rest refusals).
REPLY_CODES = ("applied", "repeat", "wrong_length", "tool_absent", "temp_out_of_range", "tool_invalid", "not_heatable", "held_rate", "unknown_command")
REPLY_ACKNOWLEDGEMENTS = ("applied", "repeat")
# The status of a SET_PREHEAT check, as the reason the sender is told.
STATUS_TO_REPLY = {"wrong_payload_len": "wrong_length", "tool_id_absent": "tool_absent", "temp_out_of_range": "temp_out_of_range",
                   "tool_id_invalid": "tool_invalid", "tool_not_heatable": "not_heatable"}
SLOTS = 8
# The highest pre-heat target of each tool; a tool that is not listed has no heater and takes only 0.
MAX_PREHEAT_C = {0: RACK_CEILING_C, 10: 310, 19: RACK_CEILING_C}

# status names (same meaning as rack_command_status_t and protocol_status_t of the firmware)
OK = "ok"
FRAME_STATUSES = ("incomplete", "bad_sof", "unsupported_version", "length_out_of_range", "crc_mismatch")
COMMAND_STATUSES = ("wrong_payload_len", "tool_id_absent", "temp_out_of_range", "tool_id_invalid", "tool_not_heatable")


def crc8(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def encode_frame(seq: int, cmd: int, payload: bytes = b"") -> bytes:
    if len(payload) > MAX_PAYLOAD:
        raise ValueError("payload too long")
    body = bytes([SOF, VERSION, seq & 0xFF, cmd & 0xFF, len(payload)]) + bytes(payload)
    return body + bytes([crc8(body)])


def parse_frame(buf: bytes) -> tuple[str, dict | None]:
    """(status, frame): the frame is a dict with seq, cmd and payload when the status is ``ok``."""
    if len(buf) < 6:
        return "incomplete", None
    if buf[0] != SOF:
        return "bad_sof", None
    if buf[1] != VERSION:
        return "unsupported_version", None
    length = buf[4]
    if length > MAX_PAYLOAD:
        return "length_out_of_range", None
    total = 5 + length + 1
    if len(buf) < total:
        return "incomplete", None
    if crc8(buf[: 5 + length]) != buf[5 + length]:
        return "crc_mismatch", None
    return OK, {"seq": buf[2], "cmd": buf[3], "payload": bytes(buf[5:5 + length])}


DEFRAMER_TIMEOUT_MS = 20      # the longest silence inside a frame of the serial link
MAX_FRAME_SIZE = 5 + MAX_PAYLOAD + 1


@dataclass
class DeframerStats:
    frames_ok: int = 0       # frames handed over
    crc_errors: int = 0      # candidates with the right shape and the wrong CRC
    bad_headers: int = 0     # candidates with an unsupported version or an impossible length
    resyncs: int = 0         # times it restarted from a later start byte
    timeouts: int = 0        # half frames dropped by the inter-byte timeout
    dropped_bytes: int = 0   # bytes thrown away for any reason


class StreamDeframer:
    """Frames out of a stream of bytes, as the rack firmware does it (rack_deframer.c of URTC-SMART-RACK).

    A serial link delivers bytes, not frames: a byte can be lost, a frame can come in pieces, noise can sit between two frames. This
    looks for the start byte, collects what the header says belongs to the frame and hands it over only when its CRC is right; when the
    bytes do not fit (wrong version, impossible length, bad CRC) it throws away the first byte of the candidate and looks again from
    the next start byte it already holds, so the frame after a damaged one is not lost with it. A frame that stops half-way is dropped
    after a silence longer than the timeout. The counters are the ones of the firmware, and ``conformance/rack_vectors.json`` holds
    streams that the firmware and this class both pass.
    """

    def __init__(self, timeout_ms: int = DEFRAMER_TIMEOUT_MS) -> None:
        self.timeout_ms = timeout_ms or DEFRAMER_TIMEOUT_MS
        self.buf = bytearray()
        self.last_byte_ms = 0
        self.stats = DeframerStats()

    def _drop_front(self, n: int) -> None:
        n = min(n, len(self.buf))
        self.stats.dropped_bytes += n
        del self.buf[:n]

    def _next_start(self) -> int:
        skip = 1
        while skip < len(self.buf) and self.buf[skip] != SOF:
            skip += 1
        return skip

    def _resync(self) -> None:
        self.stats.resyncs += 1
        self._drop_front(self._next_start())

    def _extract(self) -> bytes | None:
        while self.buf:
            if self.buf[0] != SOF:
                self._drop_front(self._next_start())
                continue
            if len(self.buf) >= 2 and self.buf[1] != VERSION:
                self.stats.bad_headers += 1
                self._resync()
                continue
            if len(self.buf) < 5:
                return None
            payload_len = self.buf[4]
            if payload_len > MAX_PAYLOAD:
                self.stats.bad_headers += 1
                self._resync()
                continue
            total = 6 + payload_len
            if len(self.buf) < total:
                return None
            status, _frame = parse_frame(bytes(self.buf[:total]))
            if status != OK:
                if status == "crc_mismatch":
                    self.stats.crc_errors += 1
                else:
                    self.stats.bad_headers += 1
                self._resync()
                continue
            frame = bytes(self.buf[:total])
            self.stats.frames_ok += 1
            del self.buf[:total]  # consumed, not dropped
            return frame
        return None

    def push(self, byte: int, now_ms: int) -> bytes | None:
        """One received byte; the frame it completes, if any. Call ``next()`` after a frame until it gives None."""
        if self.buf and ((now_ms - self.last_byte_ms) & 0xFFFFFFFF) > self.timeout_ms:
            self.stats.timeouts += 1
            self.stats.dropped_bytes += len(self.buf)
            self.buf.clear()
        self.last_byte_ms = now_ms & 0xFFFFFFFF
        if len(self.buf) >= MAX_FRAME_SIZE:
            self._drop_front(1)
        self.buf.append(byte & 0xFF)
        return self._extract()

    def next(self) -> bytes | None:
        """Another frame among the bytes already held (after a resynchronisation they can contain a whole one)."""
        return self._extract()

    def feed(self, data: bytes, now_ms: int) -> list[bytes]:
        """Every frame the bytes of ``data``, all received at ``now_ms``, complete."""
        frames: list[bytes] = []
        for byte in data:
            frame = self.push(byte, now_ms)
            while frame is not None:
                frames.append(frame)
                frame = self.next()
        return frames

    def reset(self) -> None:
        self.buf.clear()


def encode_set_preheat(seq: int, tool_id: int, target_c: int) -> bytes:
    return encode_frame(seq, CMD_SET_PREHEAT, bytes([tool_id, (target_c >> 8) & 0xFF, target_c & 0xFF]))


def encode_set_preheat_can(seq: int, tool_id: int, target_c: int) -> bytes:
    """The eight data bytes of the CAN form (identifier 0x260): tool, temperature big-endian, sequence, padding."""
    return bytes([tool_id, (target_c >> 8) & 0xFF, target_c & 0xFF, seq & 0xFF, 0, 0, 0, 0])


def encode_reply(seq: int, cmd: int, tool: int, reason: str) -> bytes:
    """The frame that tells the sender what became of its command: an acknowledgement (0x81) for ``applied`` and ``repeat``, a refusal (0x82) with the reason otherwise.

    Payload: the command answered, the tool byte it carried (0xFF: none) and the reason code; the framing is the one of every frame of the link.
    """
    code = REPLY_CODES.index(reason)
    return encode_frame(seq, CMD_ACK if reason in REPLY_ACKNOWLEDGEMENTS else CMD_NACK, bytes([cmd & 0xFF, tool & 0xFF, code]))


def encode_reply_can(cmd: int, tool: int, reason: str) -> bytes:
    """The three data bytes of the CAN reply (identifier 0x261): the command answered, the tool byte it carried (0xFF: none) and the reason code.

    The same three bytes as the payload of the serial acknowledgement and refusal; on CAN the kind is told by the reason, there is no sequence number.
    """
    return bytes([cmd & 0xFF, tool & 0xFF, REPLY_CODES.index(reason)])


def parse_reply_can(can_id: int, data: bytes) -> dict | None:
    """The reply a rack sent on CAN, or None when the frame is not a well-formed one (identifier 0x261, exactly three bytes, a code that exists)."""
    if can_id != CAN_ID_REPLY or len(data) != REPLY_PAYLOAD_LEN or data[2] >= len(REPLY_CODES):
        return None
    reason = REPLY_CODES[data[2]]
    return {"ack": reason in REPLY_ACKNOWLEDGEMENTS, "cmd": data[0], "tool": data[1], "code": data[2], "reason": reason}


def parse_reply(buf: bytes) -> dict | None:
    """The reply a rack sent, or None when ``buf`` is not a well-formed one (right command, exact payload length, a code that exists and agrees with the command)."""
    status, frame = parse_frame(buf)
    if frame is None or frame["cmd"] not in (CMD_ACK, CMD_NACK) or len(frame["payload"]) != REPLY_PAYLOAD_LEN:
        return None
    code = frame["payload"][2]
    if code >= len(REPLY_CODES):
        return None
    reason = REPLY_CODES[code]
    ack = frame["cmd"] == CMD_ACK
    if ack != (reason in REPLY_ACKNOWLEDGEMENTS):
        return None
    return {"ack": ack, "cmd": frame["payload"][0], "tool": frame["payload"][1], "code": code, "reason": reason, "seq": frame["seq"]}


def validate_set_preheat(payload: bytes) -> tuple[str, int, int]:
    """(status, tool_id, target_c) of a SET_PREHEAT payload."""
    if len(payload) != 3:
        return "wrong_payload_len", 0, 0
    tool = payload[0]
    if tool > 31:
        return "tool_id_invalid", tool, 0
    if tool == TOOL_ID_NONE:
        return "tool_id_absent", tool, 0
    if tool > TOOL_ID_LAST:
        return "tool_id_invalid", tool, 0
    target = (payload[1] << 8) | payload[2]
    if target > RACK_CEILING_C:
        return "temp_out_of_range", tool, target
    ceiling = MAX_PREHEAT_C.get(tool, 0)
    if target > 0 and ceiling == 0:
        return "tool_not_heatable", tool, target
    if target > ceiling:
        return "temp_out_of_range", tool, target
    return OK, tool, target


# ---- free configuration of a head (ID jumpers 0x1F) ---------------------------------------------------------------------------------
# A head whose five ID jumpers all read 1 does not say which tool it is: the tool is a value stored in its F-RAM (CAN 0x1A2 writes it, 0x1A3
# reports it). The rack never assumes "no tool" for such a head and never guesses one: it asks, checks the answer and uses the identity it
# gets exactly like one read from jumpers. Until a valid answer arrives the head has no identity, so nothing is ordered to it.
FREE_TOOL_JUMPER = 31                 # the jumper reading that means "ask the head"
CAN_ID_FREE_TOOL_QUERY = 0x1A3        # the query (payload ignored) and its two-byte answer: jumper reading, selection
FREE_TOOL_SELECTION_MAX = 25          # the answer carries tool id + 1; 0 is "not set"
FREE_TOOL_REPLY_LEN = 2


@dataclass
class FreeToolConfig:
    """Timing of the query. The firmware keeps the same four values in its configuration structure, not in its logic."""

    query_timeout_ms: int = 250       # how long one query waits for the answer
    max_attempts: int = 3             # queries of one round (the first one included) before the round counts as unanswered
    retry_backoff_ms: int = 2000      # pause after an unanswered or invalid round before the next round
    refresh_period_ms: int = 5000     # while resolved, ask again this often to notice a change; 0 = never ask again


def classify_jumper(raw_bits: int) -> tuple[str, int | None]:
    """What a jumper reading means: ("direct", tool) for 0..24, ("free", None) for 31, ("invalid", None) for 25..30. Bits above the fifth are ignored."""
    value = raw_bits & 0x1F
    if value <= TOOL_ID_LAST:
        return "direct", value
    if value == FREE_TOOL_JUMPER:
        return "free", None
    return "invalid", None


def parse_free_tool_reply(payload: bytes) -> int | None:
    """The tool a 0x1A3 answer names, or None when it names none: it needs two bytes, the jumper reading must be 31 (otherwise the
    head is not in free mode), and the selection 1..25 (tool id + 1; 0 is not set, 26 or more is no tool). Extra bytes are ignored."""
    if len(payload) < FREE_TOOL_REPLY_LEN or payload[0] != FREE_TOOL_JUMPER:
        return None
    selection = payload[1]
    return selection - 1 if 1 <= selection <= FREE_TOOL_SELECTION_MAX else None


class FreeToolResolver:
    """The identity of one head in free mode. Time is passed in. ``tool`` is None until a valid answer arrives (and again after it is lost).

    ``step`` hands in the answer (if any) and then asks what to do: it returns (query, event). ``query`` is True when the rack must send the
    0x1A3 query now. ``event`` is one of none, resolved (a first valid answer), confirmed (the same tool again), changed (another tool: handle
    it as a tool change), lost (the answer was invalid or the head stayed silent for a whole round: the identity is withdrawn).
    """

    def __init__(self, config: FreeToolConfig | None = None) -> None:
        self.config = config or FreeToolConfig()
        self.tool: int | None = None
        self.attempts = 0              # queries sent in the round in flight; 0 = none in flight
        self.deadline_ms = 0           # in flight: when the current query gives up
        self.next_ms = 0               # idle: when the next round starts
        self.armed = False             # false until the first query has been sent

    @property
    def resolved(self) -> bool:
        return self.tool is not None

    @staticmethod
    def _due(now_ms: int, when_ms: int) -> bool:
        return ((now_ms - when_ms) & 0xFFFFFFFF) < 0x80000000

    def _settle(self, now_ms: int, backoff: bool) -> None:
        self.attempts = 0
        self.armed = True
        self.next_ms = (now_ms + (self.config.retry_backoff_ms if backoff else self.config.refresh_period_ms)) & 0xFFFFFFFF

    def on_reply(self, payload: bytes, now_ms: int) -> str:
        tool = parse_free_tool_reply(payload)
        if tool is None:
            was = self.tool is not None
            self.tool = None
            self._settle(now_ms, True)
            return "lost" if was else "none"
        previous = self.tool
        self.tool = tool
        self._settle(now_ms, False)
        if previous is None:
            return "resolved"
        return "confirmed" if previous == tool else "changed"

    def poll(self, now_ms: int) -> tuple[bool, str]:
        cfg = self.config
        if self.attempts == 0:
            if self.armed and not self._due(now_ms, self.next_ms):
                return False, "none"
            if self.armed and self.tool is not None and cfg.refresh_period_ms == 0:
                return False, "none"
            self.armed = True
            self.attempts = 1
            self.deadline_ms = (now_ms + cfg.query_timeout_ms) & 0xFFFFFFFF
            return True, "none"
        if not self._due(now_ms, self.deadline_ms):
            return False, "none"
        if self.attempts < max(1, cfg.max_attempts):
            self.attempts += 1
            self.deadline_ms = (now_ms + cfg.query_timeout_ms) & 0xFFFFFFFF
            return True, "none"
        was = self.tool is not None
        self.tool = None
        self._settle(now_ms, True)
        return False, "lost" if was else "none"

    def step(self, now_ms: int, reply: bytes | None = None) -> tuple[bool, str]:
        event = self.on_reply(reply, now_ms) if reply is not None else "none"
        query, polled = self.poll(now_ms)
        return query, event if event != "none" else polled



@dataclass
class Slot:
    occupied: bool = False
    tool_id: int = TOOL_ID_NONE
    serial: int = 0           # 0: the unit did not say which one it is
    target_c: int = 0

    @property
    def unit_key(self) -> str | None:
        """The identity of the physical unit: tool type plus serial number (None when the serial is unknown)."""
        return f"{self.tool_id}:{self.serial}" if self.occupied and self.serial else None


@dataclass
class Reply:
    kind: str                 # "ack", "nack" or "none"
    action: str = "none"      # "set_target", "safe_state", "none"
    tool_id: int | None = None
    target_c: int | None = None
    detail: str = ""
    reason: str = ""          # why it was applied or refused (REPLY_CODES); "" when nobody is told
    frame: bytes = b""        # the reply frame of a serial command (acknowledgement or refusal); empty when nobody is told
    can_frame: tuple[int, bytes] | None = None  # the reply (identifier 0x261, three bytes) of a command that came on CAN; None when nobody is told


@dataclass
class SimulatedRack:
    """What a rack does with the frames it receives. Time is passed in; nothing here reads a clock."""

    preheat_max_ms: int | None = PREHEAT_MAX_MS
    min_interval_ms: int = COMMAND_MIN_INTERVAL_MS  # the least time between two commands accepted for one tool; 0 = no limit
    slots: list[Slot] = field(default_factory=lambda: [Slot() for _ in range(SLOTS)])
    last_rx_ms: int | None = None
    last_seq: dict[int, int] = field(default_factory=dict)
    started_ms: dict[int, int] = field(default_factory=dict)
    last_accept_ms: dict[int, int] = field(default_factory=dict)
    expired: set[int] = field(default_factory=set)
    log: list[str] = field(default_factory=list)
    deframer: StreamDeframer = field(default_factory=StreamDeframer)
    free_config: FreeToolConfig = field(default_factory=FreeToolConfig)
    free: dict[int, FreeToolResolver] = field(default_factory=dict)  # slot -> resolver, for the heads whose jumpers read 31
    invalid_slots: set[int] = field(default_factory=set)  # slots whose head reads an unassigned jumper value

    # -- inventory ----------------------------------------------------------------------------------------------
    def set_slot(self, slot: int, tool_id: int, serial: int = 0) -> None:
        """Put a tool (type and, when it said so, serial number) in a slot; a tool can be in one slot only."""
        if not 0 <= slot < SLOTS:
            raise ValueError("slot out of range")
        if tool_id == TOOL_ID_NONE:
            self.slots[slot] = Slot()
            self.started_ms.pop(slot, None)
            self.expired.discard(slot)
            return
        if tool_id > TOOL_ID_LAST:
            raise ValueError("not a tool profile")
        for other, s in enumerate(self.slots):
            if other != slot and s.occupied and s.tool_id == tool_id and (not serial or s.serial == serial or not s.serial):
                self.slots[other] = Slot()
        self.slots[slot] = Slot(True, tool_id, serial & 0xFF, 0)
        self.started_ms.pop(slot, None)
        self.expired.discard(slot)

    # -- free configuration (jumpers 31) -----------------------------------------------------------------------------
    def set_slot_jumpers(self, slot: int, raw_bits: int, serial: int = 0) -> str:
        """A head is in a slot and its ID jumpers read ``raw_bits``. Returns "direct", "free" or "invalid". Only a direct reading gives the
        slot an identity at once; a free one waits for the answer of the head (see ``free_tool_step``) and an invalid one never gets any.
        In both of the last two cases the slot has no tool, so no target can be set on it."""
        if not 0 <= slot < SLOTS:
            raise ValueError("slot out of range")
        kind, tool = classify_jumper(raw_bits)
        self.free.pop(slot, None)
        self.invalid_slots.discard(slot)
        if tool is not None:
            self.set_slot(slot, tool, serial)
        else:
            self.set_slot(slot, TOOL_ID_NONE)
            if kind == "free":
                self.free[slot] = FreeToolResolver(self.free_config)
            else:
                self.invalid_slots.add(slot)
        return kind

    def free_tool_step(self, slot: int, now_ms: int, reply: bytes | None = None) -> tuple[bool, str]:
        """Time passes for the head of ``slot`` (and, perhaps, its 0x1A3 answer arrives): returns (send the query, event). A new or changed
        identity moves the slot to that tool with no target (a change of tool); a withdrawn one empties the slot."""
        resolver = self.free.get(slot)
        if resolver is None:
            return False, "none"
        query, event = resolver.step(now_ms, reply)
        if event in ("resolved", "changed") and resolver.tool is not None:
            self.set_slot(slot, resolver.tool)
        elif event == "lost":
            self.set_slot(slot, TOOL_ID_NONE)
        return query, event

    def slot_identity(self, slot: int) -> str:
        """"tool" (identity known), "pending" (free mode, no valid answer yet), "invalid" (unassigned jumpers) or "empty"."""
        if self.slots[slot].occupied:
            return "tool"
        if slot in self.free:
            return "pending"
        return "invalid" if slot in self.invalid_slots else "empty"

    def _find(self, tool_id: int) -> int | None:
        for i, s in enumerate(self.slots):
            if s.occupied and s.tool_id == tool_id:
                return i
        return None

    # -- link ---------------------------------------------------------------------------------------------------
    def link_lost(self, now_ms: int) -> bool:
        return self.last_rx_ms is None or (now_ms - self.last_rx_ms) >= LINK_TIMEOUT_MS

    def tick(self, now_ms: int) -> int:
        """Run the watchdog and the pre-heat limit; returns how many slots were sent to the safe state."""
        cut = 0
        if self.last_rx_ms is not None and self.link_lost(now_ms):
            self.last_rx_ms = None
            self.last_seq.clear()
            self.last_accept_ms.clear()
        lost = self.link_lost(now_ms)
        for i, s in enumerate(self.slots):
            if not s.occupied or s.target_c == 0:
                continue
            ran_out = self.preheat_max_ms is not None and now_ms - self.started_ms.get(i, now_ms) >= self.preheat_max_ms
            if lost or ran_out:
                s.target_c = 0
                cut += 1
                if ran_out and not lost:
                    self.expired.add(i)
                self.log.append(f"slot {i}: safe state ({'link lost' if lost else 'pre-heat limit'})")
        return cut

    def receive(self, buf: bytes, now_ms: int) -> Reply:
        status, frame = parse_frame(buf)
        if frame is None:
            return Reply("none", detail=f"frame refused: {status}")
        self.tick(now_ms)
        self.last_rx_ms = now_ms
        if frame["cmd"] != CMD_SET_PREHEAT:
            return Reply("nack", "none", reason="unknown_command", detail="command not acted on",
                         frame=encode_reply(frame["seq"], frame["cmd"], REPLY_TOOL_NONE, "unknown_command"))
        if not frame["payload"]:
            return Reply("nack", "none", reason="wrong_length", detail="wrong_payload_len",
                         frame=encode_reply(frame["seq"], CMD_SET_PREHEAT, REPLY_TOOL_NONE, "wrong_length"))
        return self._set_preheat(frame["seq"], frame["payload"], now_ms, True)

    def receive_stream(self, data: bytes, now_ms: int) -> list[Reply]:
        """The bytes that arrived on the serial line at ``now_ms``: the deframer finds the frames and each one is handled like ``receive``."""
        return [self.receive(frame, now_ms) for frame in self.deframer.feed(data, now_ms)]

    def receive_can(self, can_id: int, data: bytes, now_ms: int) -> Reply:
        if can_id != CAN_ID_SET_PREHEAT or len(data) != 8:
            return Reply("none", detail="not a rack frame")
        self.tick(now_ms)
        self.last_rx_ms = now_ms
        return self._set_preheat(data[3], bytes(data[:3]), now_ms, False)  # the same three bytes as the serial payload: tool, temperature big-endian

    def _set_preheat(self, seq: int, payload: bytes, now_ms: int, serial: bool = True) -> Reply:
        def told(reply: Reply, reason: str) -> Reply:
            """The reply with its reason and the frame that carries it: serial for a serial command, 0x261 for a command that came on CAN."""
            reply.reason = reason
            if serial:
                reply.frame = encode_reply(seq, CMD_SET_PREHEAT, payload[0], reason)
            else:
                reply.can_frame = (CAN_ID_REPLY, encode_reply_can(CMD_SET_PREHEAT, payload[0], reason))
            return reply

        status, tool, target = validate_set_preheat(payload)
        if status != OK:
            readable = len(payload) >= 1 and payload[0] <= TOOL_ID_LAST
            reason = STATUS_TO_REPLY[status]
            if readable:
                slot = self._find(payload[0])
                if slot is not None:
                    self.slots[slot].target_c = 0
                return told(Reply("nack", "safe_state", payload[0], 0, status), reason)
            return told(Reply("nack", "none", None, None, status), reason)
        prev = self.last_seq.get(tool)
        if prev is not None and (((seq - prev) & 0xFF) == 0 or ((seq - prev) & 0xFF) >= 128):
            return told(Reply("ack", "none", tool, None, "retransmission already applied"), "repeat")
        last = self.last_accept_ms.get(tool)
        if self.min_interval_ms > 0 and last is not None and ((now_ms - last) & 0xFFFFFFFF) < self.min_interval_ms:
            return told(Reply("nack", "none", tool, None, "held: too soon after the previous command for this tool"), "held_rate")
        self.last_accept_ms[tool] = now_ms
        self.last_seq[tool] = seq
        slot = self._find(tool)
        if slot is None:
            return told(Reply("ack", "none", tool, target, "tool not racked: target not applied"), "applied")
        if slot in self.expired:
            if target == 0:
                self.expired.discard(slot)
            else:
                return told(Reply("ack", "none", tool, target, "pre-heat limit reached: send 0 or swap the tool"), "applied")
        if target > 0 and self.slots[slot].target_c == 0:
            self.started_ms[slot] = now_ms
        self.slots[slot].target_c = target
        return told(Reply("ack", "set_target", tool, target), "applied")

    def status(self) -> dict:
        """The state a panel shows: one entry per slot."""
        return {
            "slots": [
                {"slot": i, "occupied": s.occupied, "tool_id": s.tool_id if s.occupied else None, "serial": s.serial or None,
                 "unit": s.unit_key, "target_c": s.target_c, "expired": i in self.expired}
                for i, s in enumerate(self.slots)
            ],
            "occupied": sum(1 for s in self.slots if s.occupied),
        }


# ---- thermal check of a slot (a thermal camera looks at the tips in the rack) ------------------------------------------------------
VERIFY_TOLERANCE_C = 15       # a tip this close to its target has reached it
VERIFY_OVERSHOOT_C = 25       # a tip this far above its target is too hot
VERIFY_EMPTY_HOT_C = 40       # above the ambient by this much, an empty slot has a heater on
VERIFY_IDLE_HOT_C = 60        # above the ambient by this much, a slot told to stay cold is still hot
VERIFY_REACH_TIMEOUT_MS = 60_000

SLOT_UNKNOWN = "unknown"            # no reading
SLOT_EMPTY_OK = "empty_ok"
SLOT_EMPTY_HOT = "heater_in_empty_slot"
SLOT_IDLE_OK = "idle_ok"
SLOT_IDLE_HOT = "still_hot"
SLOT_HEATING = "heating"
SLOT_REACHED = "reached"
SLOT_NOT_REACHED = "not_reached"
SLOT_OVERSHOOT = "overshoot"
SLOT_VERDICTS = (SLOT_UNKNOWN, SLOT_EMPTY_OK, SLOT_EMPTY_HOT, SLOT_IDLE_OK, SLOT_IDLE_HOT, SLOT_HEATING, SLOT_REACHED, SLOT_NOT_REACHED, SLOT_OVERSHOOT)


def verify_slot(occupied: bool, commanded_c: int, measured_c: float | None, ambient_c: float, elapsed_ms: int) -> str:
    """What the thermal reading of a slot says about the pre-heat the rack ordered. ``elapsed_ms`` is the time since the target was set."""
    if measured_c is None or measured_c != measured_c:
        return SLOT_UNKNOWN
    if not occupied:
        return SLOT_EMPTY_HOT if measured_c > ambient_c + VERIFY_EMPTY_HOT_C else SLOT_EMPTY_OK
    if commanded_c == 0:
        return SLOT_IDLE_HOT if measured_c > ambient_c + VERIFY_IDLE_HOT_C else SLOT_IDLE_OK
    if measured_c > commanded_c + VERIFY_OVERSHOOT_C:
        return SLOT_OVERSHOOT
    if measured_c >= commanded_c - VERIFY_TOLERANCE_C:
        return SLOT_REACHED
    return SLOT_NOT_REACHED if elapsed_ms >= VERIFY_REACH_TIMEOUT_MS else SLOT_HEATING
