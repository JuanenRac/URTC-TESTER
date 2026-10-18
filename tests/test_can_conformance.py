# =============================================================================
# URTC Tester - tests/test_can_conformance.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The tester's reading of the CAN protocol, against the shared vectors.

tests/fixtures/can_conformance_vectors.json is a committed copy of the vectors
the other URTC clients (the Flasher and the Web Studio) are checked against too,
so the three implementations are compared with the same expected bytes. This
file only reads its own copy."""
from __future__ import annotations

import json
import re
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import advanced_protocol  # noqa: E402
import tester_config  # noqa: E402
from tester_transports import SLCAN, SLCANError  # noqa: E402

VECTORS = json.loads((Path(__file__).parent / "fixtures" / "can_conformance_vectors.json").read_text(encoding="utf-8"))


class _FakeSerial:
    def __init__(self):
        self.written = b""
        self.incoming = bytearray()

    @property
    def in_waiting(self):
        return len(self.incoming)

    def read(self, count):
        chunk = bytes(self.incoming[:count])
        del self.incoming[:count]
        return chunk

    def write(self, data):
        self.written += data

    def reset_input_buffer(self):
        self.incoming.clear()

    def close(self):
        pass


def _slcan():
    transport = SLCAN.__new__(SLCAN)
    transport.log = lambda message: None
    transport.ser = _FakeSerial()
    transport._rx_buf = b""
    transport._write_lock = threading.Lock()
    transport.listen_only = False
    return transport


def _hex(text):
    return bytes.fromhex(text)


def _id(text):
    return int(text, 16)


@pytest.mark.parametrize("entry", [e for e in VECTORS["identifiers"] if "tester" in e["names"]], ids=lambda entry: entry["id"])
def test_identifiers_match_the_shared_table(entry):
    assert getattr(tester_config, entry["names"]["tester"]) == _id(entry["id"])


def test_erase_fram_magic_matches():
    magic = next(m for m in VECTORS["magic_payloads"] if m["name"] == "erase_fram")
    assert tester_config.ERASE_FRAM_MAGIC == _hex(magic["data"])
    assert tester_config.CAN_ID_ERASE_FRAM == _id(magic["id"])


def test_the_feeder_reset_panel_sends_the_shared_magic():
    magic = next(m for m in VECTORS["magic_payloads"] if m["name"] == "solder_feeder_reset")
    source = (ROOT / "tester_tool_panels.py").read_text(encoding="utf-8")
    sent = re.search(r"CAN_ID_SOLDER_FEEDER_RESET, bytes\(\[([^\]]*)\]\)", source)
    assert sent is not None
    assert bytes(int(token, 16) for token in sent.group(1).split(",")) == _hex(magic["data"])
    assert tester_config.CAN_ID_SOLDER_FEEDER_RESET == _id(magic["id"])


@pytest.mark.parametrize("vector", VECTORS["slcan_encode"], ids=lambda vector: vector["line"])
def test_slcan_encode(vector):
    transport = _slcan()
    transport.send_frame(_id(vector["id"]), _hex(vector["data"]))
    assert transport.ser.written == vector["line"].encode("ascii") + b"\r"


@pytest.mark.parametrize("vector", VECTORS["slcan_encode_rejected"], ids=lambda vector: vector["id"] + "-" + str(len(vector["data"]) // 2))
def test_slcan_encode_rejected(vector):
    transport = _slcan()
    with pytest.raises(SLCANError):
        transport.send_frame(_id(vector["id"]), _hex(vector["data"]))
    assert transport.ser.written == b""


@pytest.mark.parametrize("vector", VECTORS["slcan_decode"], ids=lambda vector: vector["name"])
def test_slcan_decode(vector):
    transport = _slcan()
    transport.ser.incoming.extend(vector["line"].encode("ascii") + b"\r")
    got = transport.read_frame(timeout=0.05)
    if "note" in vector:
        assert got is None or isinstance(got, tuple)
        return
    if vector["frame"] is None:
        assert got is None
    else:
        assert got == (_id(vector["frame"]["id"]), _hex(vector["frame"]["data"]))


@pytest.mark.parametrize("vector", VECTORS["quick_state"], ids=lambda vector: vector["name"])
def test_quick_state(vector):
    got = advanced_protocol.decode_quick_state(_hex(vector["data"]))
    expect = vector["expect"]
    if expect is None:
        assert got is None
        return
    for key, value in expect.items():
        assert got[key] == value, key
