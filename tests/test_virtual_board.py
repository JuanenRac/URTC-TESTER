# =============================================================================
# URTC-TESTER - tests/test_virtual_board.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The tester against the virtual board of the shared package, reached through its SLCAN transport over TCP.

No adapter and no board are involved: the real pyserial opens a ``socket://`` URL, the server behind it plays an SLCAN
adapter, and a simulated board answers like the application. The command line and the transport run unchanged.
"""
from __future__ import annotations

import json

import pytest

import tester_cli
import tester_transports as tr
from urtc_can import protocol as wire
from urtc_can.transports import is_serial_url
from urtc_can.virtual_board import VirtualBoard, VirtualBoardServer

pytest.importorskip("serial")


def test_a_serial_url_is_told_from_a_port_name():
    assert is_serial_url("socket://127.0.0.1:7777")
    assert not is_serial_url("COM3") and not is_serial_url("/dev/ttyACM0")


def test_the_transport_reads_the_version_of_the_board_over_tcp():
    with VirtualBoardServer(VirtualBoard(version=(0, 4), patch=2)) as server:
        transport = tr.SLCAN(server.url, settle_seconds=0)
        transport.open_channel()
        try:
            transport.send_frame(wire.CAN_ID_QUERY_VERSION, b"\x00")
            first = transport.read_frame(timeout=2)
        finally:
            transport.close()
    assert first is not None
    assert first[0] == wire.CAN_ID_VERSION_RESPONSE and first[1][0] == wire.RESPONDER_APPLICATION


def test_the_command_line_identifies_the_virtual_board(tmp_path, capsys):
    with VirtualBoardServer(VirtualBoard(version=(0, 4), patch=2)) as server:
        code = tester_cli.main(["info", "--transport", "serial", "--port", server.url, "--out", str(tmp_path), "--json", "--timeout", "20"])
    result = json.loads(capsys.readouterr().out)
    assert code == 0
    assert result["steps"][0]["do"] == "query_version"
    assert "application 0.4.2" in result["steps"][0]["message"]


def test_a_port_that_nobody_listens_on_is_reported_not_raised(tmp_path, capsys):
    with VirtualBoardServer(VirtualBoard()) as server:
        url = server.url
    code = tester_cli.main(["info", "--transport", "serial", "--port", url, "--out", str(tmp_path)])
    assert code != 0
    assert "ERROR" in capsys.readouterr().out


def test_the_virtual_ports_come_from_the_environment_variable_and_only_urls_count():
    env = {tr.VIRTUAL_PORT_ENV: "socket://127.0.0.1:7777, COM3 ,rfc2217://host:2217,,/dev/ttyUSB0"}
    assert tr.virtual_ports(env) == ["socket://127.0.0.1:7777", "rfc2217://host:2217"]
    assert tr.virtual_ports({}) == []
