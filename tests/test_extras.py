# =============================================================================
# URTC Tester - tests/test_extras.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The fault recorder download and export, the optional functions, the rack bench and the thermal view of the deck."""
import base64
import csv
import json
import struct
import sys
import zlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tester_extras as extras  # noqa: E402
from urtc_can import blackbox, thermal_view  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
BLACKBOX = json.loads((FIXTURES / "blackbox_vectors.json").read_text(encoding="utf-8"))
THERMAL = json.loads((FIXTURES / "thermal_vectors.json").read_text(encoding="utf-8"))


class FakeBoard:
    """Answers 0x1A8 with four frames of 0x1A9 from a record, and the thermal chunk exchange from an image."""

    def __init__(self, record: bytes = b"", image=None, drop_chunk=None, status=(1, 2)):
        self.record = record.ljust(blackbox.CHUNK_COUNT * blackbox.CHUNK_BYTES, b"\x00")
        self.image = image
        self.chunks = thermal_view.encode_chunks(image) if image else {}
        self.drop_chunk = drop_chunk
        self.status = list(status)
        self.sent = []
        self.inbox = []

    def send_frame(self, can_id, data):
        self.sent.append((can_id, bytes(data)))
        if can_id == blackbox.CAN_ID_QUERY and data and data[0] != self.drop_chunk:
            chunk = self.record[data[0] * 32:(data[0] + 1) * 32]
            self.inbox += [(blackbox.CAN_ID_CHUNK, chunk[i * 8:(i + 1) * 8]) for i in range(4)]
        elif can_id == thermal_view.CAN_ID_STATUS:
            self.inbox.append((thermal_view.CAN_ID_STATUS, bytes([self.status.pop(0) if len(self.status) > 1 else self.status[0]])))
        elif can_id == thermal_view.CAN_ID_CALIBRATED_REQUEST and data[0] != self.drop_chunk:
            chunk = self.chunks[data[0]]
            self.inbox += [(thermal_view.CAN_ID_CALIBRATED_CHUNK, chunk[i * 8:(i + 1) * 8]) for i in range(4)]

    def read_frame(self, timeout=0.1):
        return self.inbox.pop(0) if self.inbox else None


# ---- fault recorder ---------------------------------------------------------------------------------------------------------------
def test_the_black_box_is_downloaded_checked_and_saved_as_csv_and_json(tmp_path):
    vector = BLACKBOX["valid"][1]
    board = FakeBoard(bytes.fromhex(vector["hex"]))
    record = extras.download_black_box(board.send_frame, board.read_frame)
    assert [c[1][0] for c in board.sent] == list(range(22)) and record.trigger_index == vector["trigger_index"]
    csv_path, json_path = extras.save_black_box(record, str(tmp_path), "run")
    rows = list(csv.DictReader(Path(csv_path).read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 67 and rows[0]["ms_before_last"] == "9900" and rows[-1]["system_error"] == "1"
    doc = json.loads(Path(json_path).read_text(encoding="utf-8"))
    assert doc["format"] == "urtc-blackbox/1" and doc["trigger_index"] == 60 and doc["captured_at"].endswith("Z")
    assert "error flag set at sample 60" in extras.summarize_black_box(record)


def test_a_missing_chunk_or_a_damaged_record_is_an_error_not_a_guess():
    board = FakeBoard(bytes.fromhex(BLACKBOX["valid"][0]["hex"]), drop_chunk=5)
    with pytest.raises(blackbox.BlackBoxError, match="chunk 5"):
        extras.download_black_box(board.send_frame, board.read_frame, timeout_s=0.2)
    damaged = FakeBoard(bytes.fromhex(BLACKBOX["invalid"][0]["hex"]))
    with pytest.raises(blackbox.BlackBoxError, match="checksum"):
        extras.download_black_box(damaged.send_frame, damaged.read_frame)


def test_the_automatic_download_fires_once_per_fault_and_can_be_switched_off():
    auto = extras.AutoDownload(True)
    answers = [bytes([0, 0, 0, 0]), bytes([0, 1, 0, 0]), bytes([0, 1, 0, 0]), bytes([0, 0, 0, 0]), bytes([0, 1, 0, 0])]
    assert [auto.feed(a) for a in answers] == [False, True, False, False, True]
    off = extras.AutoDownload(False)
    assert [off.feed(a) for a in answers] == [False] * 5
    off.enabled = True
    assert off.feed(bytes([0, 0, 0, 0])) is False


# ---- optional functions ------------------------------------------------------------------------------------------------------------
def test_the_features_frame_and_its_answer():
    assert extras.features_frame(0x0A) == (0x1AE, b"FEAT\x0a")
    for bad in (-1, 16):
        with pytest.raises(ValueError):
            extras.features_frame(bad)
    assert extras.decode_features(bytes([2, 0, 15])) == {"stored": 2, "running": 0, "supported": 15}
    assert extras.decode_features(b"\x00\x00") is None
    assert extras.features_text(0x0A) == "HEALTH_PROFILE, THERMAL_PID" and extras.features_text(0) == "none"


# ---- rack bench --------------------------------------------------------------------------------------------------------------------
def test_the_rack_bench_follows_the_rack_protocol_and_its_identity_rules(tmp_path):
    bench = extras.RackBench()
    assert "serial 7" in bench.rack_head(0, 0, 7)
    bench.rack_head(1, 0, 9)
    assert "unit" not in bench.state_text() and "(0:7)" in bench.state_text() and "(0:9)" in bench.state_text()
    assert bench.send_preheat(0, 250).startswith("ACK set_target")
    assert bench.send_preheat(0, 500).startswith("NACK safe_state")
    assert "target 0 C" in bench.state_text().splitlines()[0]
    assert bench.send_preheat(0, 200).startswith("ACK set_target")
    held = bench.send_preheat(0, 210, gap_ms=5)     # sooner than the rack accepts a second command for one tool
    assert held.startswith("NACK") and bench.last_reply is not None and bench.last_reply["reason"] == "held_rate" and not bench.last_reply["ack"]
    assert "safe state" in bench.advance(5000) and "target 0 C" in bench.state_text().splitlines()[0]
    json_path, html_path = bench.status_page(str(tmp_path))
    snap = json.loads(Path(json_path).read_text(encoding="utf-8"))
    assert snap["source"] == "simulation" and snap["occupied"] == 2
    assert "<table>" in Path(html_path).read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        bench.rack_head(9, 0, 1)


# ---- thermal view ------------------------------------------------------------------------------------------------------------------
def _decode_png(png: bytes):
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    pos, chunks = 8, {}
    while pos < len(png):
        length, kind = struct.unpack(">I4s", png[pos:pos + 8])
        body = png[pos + 8:pos + 8 + length]
        assert struct.unpack(">I", png[pos + 8 + length:pos + 12 + length])[0] == zlib.crc32(kind + body) & 0xFFFFFFFF
        chunks[kind] = body
        pos += 12 + length
    width, height = struct.unpack(">II", chunks[b"IHDR"][:8])
    return width, height, zlib.decompress(chunks[b"IDAT"])


def test_the_png_is_valid_and_scaled():
    rgb = bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 9, 9, 9])
    width, height, raw = _decode_png(extras.png_bytes(2, 2, rgb, scale=3))
    assert (width, height) == (6, 6) and len(raw) == 6 * (1 + 6 * 3)
    assert raw[1:4] == bytes([255, 0, 0]) and raw[4:7] == bytes([255, 0, 0]) and raw[10:13] == bytes([0, 255, 0])
    with pytest.raises(ValueError):
        extras.png_bytes(2, 2, b"\x00")


def test_the_data_url_decodes_to_the_false_color_image():
    frame = [[20.0, 80.0], [50.0, 60.0]]
    url = extras.thermal_data_url(frame, (20.0, 80.0), scale=2)
    assert url.startswith("data:image/png;base64,")
    width, height, raw = _decode_png(base64.b64decode(url.split(",", 1)[1]))
    assert (width, height) == (4, 4) and raw[1:4] == bytes(thermal_view.color_of(20.0, 20.0, 80.0))


@pytest.mark.parametrize("case", THERMAL["false_color"], ids=lambda c: c["name"])
def test_the_copy_of_the_thermal_module_reproduces_the_shared_vectors(case):
    frame = [[float("nan") if v is None else v for v in row] for row in case["frame"]]
    assert thermal_view.to_rgb_bytes(frame, tuple(case["range"]) if case["range"] else None).hex().upper() == case["rgb"]


def test_a_thermal_image_is_read_from_a_board_that_answers():
    image = thermal_view.synthetic_frame(32, 24)
    board = FakeBoard(image=image)
    assert extras.read_thermal_image(board.send_frame, board.read_frame) == image
    assert board.sent[0] == (0x250, b"") and sum(1 for c in board.sent if c[0] == 0x254) == 48


def test_a_thermal_read_reports_a_head_that_fails():
    image = thermal_view.synthetic_frame(32, 24)
    with pytest.raises(thermal_view.ThermalError, match="capture error"):
        board = FakeBoard(image=image, status=(0xFF,))
        extras.read_thermal_image(board.send_frame, board.read_frame)
    with pytest.raises(thermal_view.ThermalError, match="not become ready"):
        board = FakeBoard(image=image, status=(1,))
        extras.read_thermal_image(board.send_frame, board.read_frame, polls=3)
    with pytest.raises(thermal_view.ThermalError, match="chunk 4"):
        board = FakeBoard(image=image, drop_chunk=4)
        extras.read_thermal_image(board.send_frame, board.read_frame, chunk_timeout_s=0.1)


def test_the_summary_says_when_the_image_is_simulated():
    frame = [[20.0, 40.0], [60.0, float("nan")]]
    assert extras.thermal_summary(frame, True).startswith("SIMULATED")
    assert "min 20.0 C, max 60.0 C" in extras.thermal_summary(frame, False)
    assert "no valid pixel" in extras.thermal_summary([[float("nan")]], False)


# ---- the deck ------------------------------------------------------------------------------------------------------------------------
def test_every_new_text_exists_in_the_eight_languages():
    keys = {line.split("=", 1)[0] for line in (ROOT / "language" / "english.lng").read_text(encoding="utf-8").splitlines()
            if line.startswith(("QT_EXTRAS_PANEL=", "BTN_READ_BLACK_BOX=", "LBL_BLACKBOX_", "BTN_QUERY_FEATURES=", "BTN_WRITE_FEATURES=", "LBL_FEATURE", "LBL_RACK_", "QT_RACK_BENCH=", "QT_THERMAL_VIEW=", "BTN_THERMAL_", "LBL_THERMAL_VIEW", "LBL_THERMAL_READ"))}
    assert len(keys) >= 20
    for name in ("english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese"):
        found = {line.split("=", 1)[0] for line in (ROOT / "language" / f"{name}.lng").read_text(encoding="utf-8").splitlines() if "=" in line}
        assert keys <= found, (name, sorted(keys - found))


def test_the_bridge_exposes_the_new_panels(monkeypatch):
    pytest.importorskip("PySide6")
    import qt_tester  # noqa: PLC0415
    monkeypatch.setattr(qt_tester, "save_config", lambda updates: True)
    bridge = qt_tester.TesterQtBridge()
    bridge._log = lambda text: None
    assert bridge.autoBlackBox is True
    bridge.setAutoBlackBox(False)
    assert bridge.autoBlackBox is False
    bridge.showSimulatedThermal()
    assert bridge.thermalViewSource.startswith("data:image/png") and "SIMULATED" in bridge.thermalViewText
    bridge.rackBenchRack(0, 0, 7)
    bridge.rackBenchPreheat(0, 200)
    assert "target 200 C" in bridge.rackBenchText
    bridge.rackBenchAdvance(700000)
    assert "target 0 C" in bridge.rackBenchText.splitlines()[1]
    bridge._on_query_result("features", {"stored": 2, "running": 0, "supported": 15})
    assert "HEALTH_PROFILE" in bridge.featuresText
    bridge._on_query_result("features", None)
    bridge._on_query_result("black_box", ("fail", "chunk 3 is missing or incomplete"))
    assert "chunk 3" in bridge.blackBoxText
    assert bridge.toolProfiles[22]["kind"] == "telemetry" and len(bridge.toolProfiles) == 25
    bridge.readBlackBox()          # not connected: nothing is sent and nothing breaks
    bridge.writeFeatures(99)


# ---- heater PID ---------------------------------------------------------------------------------------------------------------------
def test_the_pid_frames_carry_the_gains_times_100_and_the_action():
    assert extras.pid_frame(extras.PID_SET_GAINS, 8, "0.2", 1.5) == (0x1B9, bytes.fromhex("03200014009600"))
    assert extras.pid_frame(extras.PID_AUTOTUNE_START) == (0x1B9, bytes.fromhex("00000000000001"))
    assert extras.pid_frame(extras.PID_AUTOTUNE_ABORT, 9, 9, 9) == (0x1B9, bytes.fromhex("00000000000002"))  # gains are read only for a store
    assert extras.pid_frame(extras.PID_QUERY)[1][-1] == 3
    assert extras.pid_frame(extras.PID_SET_GAINS, 600, 600, 600)[1].hex().upper().startswith("EA60EA60EA60")


@pytest.mark.parametrize("bad", ["x", "", None, float("nan"), float("inf"), -0.01, 600.01, True, [1]])
def test_a_gain_that_is_not_a_number_from_0_to_600_is_refused(bad):
    with pytest.raises(ValueError):
        extras.pid_frame(extras.PID_SET_GAINS, bad, 0, 0)


def test_an_unknown_pid_action_is_refused():
    with pytest.raises(ValueError):
        extras.pid_frame(7)


def test_the_pid_answer_is_decoded_and_a_wrong_length_is_not_guessed():
    state = extras.decode_pid_state(bytes.fromhex("0320001400960125"))
    assert state == {"kp": 8.0, "ki": 0.2, "kd": 1.5, "state": 1, "state_name": "RUNNING", "duty_percent": 37}
    assert extras.decode_pid_state(bytes.fromhex("03200014009601"))is None
    assert extras.decode_pid_state(bytes.fromhex("0320001400960925"))["state_name"] == "CODE_9"


def test_the_pid_panel_of_the_bridge_blocks_when_not_active_and_shows_the_state(monkeypatch):
    pytest.importorskip("PySide6")
    import qt_tester  # noqa: PLC0415
    monkeypatch.setattr(qt_tester, "save_config", lambda updates: True)
    bridge = qt_tester.TesterQtBridge()
    logged = []
    bridge._log = logged.append
    bridge.writePidGains("8", "0.2", "1.5")      # not connected: nothing is sent
    bridge.startPidAutotune()
    bridge.queryPid()
    assert logged == ["HEATER_PID_BLOCKED not connected or not in active-check mode"] * 2
    bridge._on_query_result("pid", extras.decode_pid_state(bytes.fromhex("0320001400960225")))
    assert "Kp 8" in bridge.pidText and "autotuning" in bridge.pidText and "37 %" in bridge.pidText
    bridge._on_query_result("pid", None)
    assert "No answer" in bridge.pidText


def test_every_pid_key_exists_in_the_eight_languages():
    from tester_config import load_language
    keys = ["QT_PID_PANEL", "BTN_QUERY_PID", "BTN_SET_PID_GAINS", "BTN_PID_AUTOTUNE", "BTN_PID_ABORT", "LBL_PID_TEXT", "LBL_PID_NO_RESPONSE", "HELP_PID_AUTOTUNE",
            "QTLOG_HEATER_PID", "QTLOG_HEATER_PID_BLOCKED", "QTLOGD_PID_GAINS", *extras.PID_STATE_KEYS.values()]
    english = load_language("english")
    for language in ("english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese"):
        table = load_language(language)
        assert [k for k in keys if not table.get(k)] == [], language
        assert set(table["LBL_PID_TEXT"].split("{")[1:]) and all(f"{{{name}}}" in table["LBL_PID_TEXT"] for name in ("kp", "ki", "kd", "state", "duty")), language
    assert english["QT_PID_PANEL"] == "Heater PID"
