# =============================================================================
# URTC-TESTER - tests/test_image_info_cli.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""``--headless image-info FILE``: what the header inside a firmware image states and what the compatibility switch decides. No bus is touched."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tester_cli
from urtc_can import image_header as ih

MAIN, SLAVE = 0x0303CC01, 0x0303CB01


def _binary(hardware=MAIN, version=(0, 8, 1, 3)):
    raw = bytearray((i * 31 + 7) & 0x7F for i in range(768))
    raw[ih.EMBED_OFFSET:ih.EMBED_OFFSET + 32] = ih.embedded_slot(hardware, version)
    return bytes(raw)


def _file(tmp_path, data, name="URTC_MAIN_FIRMWARE_v0.8.1.3.bin"):
    path = tmp_path / name
    path.write_bytes(data)
    return str(path)


def test_a_sealed_image_is_described_and_accepted(tmp_path, capsys):
    path = _file(tmp_path, ih.seal_embedded(_binary()))
    assert tester_cli.main(["image-info", path]) == tester_cli.EXIT_PASS
    out = capsys.readouterr().out
    assert "0x0303CC01" in out and "0.8.1.3" in out and "ACCEPTED" in out and "768" in out


def test_the_json_form_carries_the_same_facts(tmp_path, capsys):
    path = _file(tmp_path, ih.seal_embedded(_binary()))
    assert tester_cli.main(["image-info", path, "--json", "--hardware", "main"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["accepted"] and data["kind"] == "embedded" and data["version"] == "0.8.1.3" and data["hardware_id"] == "0x0303CC01" and data["length"] == 768


def test_an_image_for_another_board_is_refused(tmp_path, capsys):
    path = _file(tmp_path, ih.seal_embedded(_binary(hardware=SLAVE)))
    assert tester_cli.main(["image-info", path, "--hardware", "main"]) == tester_cli.EXIT_FAIL
    assert "REFUSED" in capsys.readouterr().out
    assert tester_cli.main(["image-info", path, "--hardware", "slave"]) == 0


@pytest.mark.parametrize("policy, code, word", [("accept", 0, "ACCEPTED"), ("warn", 0, "with a warning"), ("require", 1, "REFUSED")])
def test_an_image_without_a_header_follows_the_switch(tmp_path, capsys, policy, code, word):
    path = _file(tmp_path, bytes((i * 31 + 7) & 0x7F for i in range(768)))
    assert tester_cli.main(["image-info", path, "--policy", policy]) == code
    assert word in capsys.readouterr().out


def test_a_damaged_or_unsealed_header_is_refused_under_every_switch(tmp_path, capsys):
    sealed = bytearray(ih.seal_embedded(_binary()))
    sealed[700] ^= 1
    for data in (bytes(sealed), _binary()):
        path = _file(tmp_path, data)
        for policy in ih.POLICIES:
            assert tester_cli.main(["image-info", path, "--policy", policy]) == tester_cli.EXIT_FAIL
    assert "never sealed" in capsys.readouterr().out


def test_bad_arguments_are_a_usage_error(tmp_path, capsys):
    assert tester_cli.main(["image-info"]) == tester_cli.EXIT_USAGE
    assert tester_cli.main(["image-info", str(tmp_path / "missing.bin")]) == tester_cli.EXIT_USAGE
    path = _file(tmp_path, _binary())
    assert tester_cli.main(["image-info", path, "--hardware", "weird"]) == tester_cli.EXIT_USAGE
