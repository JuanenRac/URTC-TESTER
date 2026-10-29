# =============================================================================
# URTC-TESTER - reproducible result record tests
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tester_result_record import RecordError, ResultRecord, load_record, make_record, save_evidence, save_record, session_manifest, evidence_record  # noqa: E402


class ResultRecordTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.log = self.dir / "run-001.log"
        self.log.write_text("frame 0x123 ok\nframe 0x124 ok\n", encoding="utf-8")

    def _record(self, **overrides):
        args = dict(
            test_name="can-self-test", outcome="pass", adapter="usb-can-1", firmware_version="0.3.1",
            bus="can0", bitrate=500000, log_path=self.log,
        )
        args.update(overrides)
        return make_record(**args)

    def test_a_record_names_everything_the_result_depends_on(self):
        record = self._record()
        self.assertEqual((record.adapter, record.firmware_version, record.bus, record.bitrate), ("usb-can-1", "0.3.1", "can0", 500000))
        self.assertEqual(record.log_file, "run-001.log")
        self.assertEqual(len(record.log_sha256), 64)

    def test_it_round_trips_and_verifies_the_log(self):
        record = self._record()
        path = self.dir / "result.json"
        save_record(record, path)
        self.assertEqual(load_record(path, self.dir), record)

    def test_an_edited_log_no_longer_matches_its_result(self):
        path = self.dir / "result.json"
        save_record(self._record(), path)
        self.log.write_text("frame 0x123 FAIL\n", encoding="utf-8")
        with self.assertRaises(RecordError):
            load_record(path, self.dir)

    def test_a_missing_log_is_reported(self):
        path = self.dir / "result.json"
        save_record(self._record(), path)
        self.log.unlink()
        with self.assertRaises(RecordError):
            load_record(path, self.dir)

    def test_the_record_can_be_read_without_checking_the_log(self):
        path = self.dir / "result.json"
        save_record(self._record(), path)
        self.log.unlink()
        self.assertEqual(load_record(path).outcome, "pass")

    def test_malformed_values_are_refused(self):
        good = self._record()
        for change in (
            dict(outcome="maybe"), dict(bitrate=0), dict(bitrate=True), dict(adapter="  "), dict(log_sha256="xyz"),
        ):
            data = {**good.__dict__, **change}
            with self.assertRaises(RecordError, msg=change):
                ResultRecord(**data)

    def test_an_unreadable_record_file_is_a_record_error(self):
        broken = self.dir / "broken.json"
        broken.write_text("{not json", encoding="utf-8")
        with self.assertRaises(RecordError):
            load_record(broken)
        with self.assertRaises(RecordError):
            load_record(self.dir / "absent.json")

    def test_a_session_manifest_names_the_log_by_its_hash(self):
        import hashlib

        manifest = session_manifest("line one\nline two\n", transport="SLCAN", bitrate=500000)
        self.assertEqual(manifest["log_sha256"], hashlib.sha256(b"line one\nline two\n").hexdigest())
        self.assertEqual(manifest["log_bytes"], 18)
        self.assertEqual((manifest["transport"], manifest["bitrate"]), ("SLCAN", "500000"))
        self.assertNotIn("outcome", manifest)
        self.assertNotEqual(manifest["log_sha256"], session_manifest("other", transport="SLCAN")["log_sha256"])


class EvidenceShapeTests(unittest.TestCase):
    """The result as a ``urtc-evidence/1`` record."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.log = self.dir / "run-001.log"
        self.log.write_text("frame 0x123 ok\n", encoding="utf-8")

    def _record(self, **overrides):
        args = dict(test_name="can-self-test", outcome="pass", adapter="usb-can-1", firmware_version="0.3.1", bus="can0", bitrate=500000, log_path=self.log)
        args.update(overrides)
        return make_record(**args)

    def test_a_result_becomes_a_checkable_record_of_the_common_shape(self):
        from urtc_can import evidence

        shape = evidence_record(self._record(), tool_version="0.4.2", timestamp_utc="2026-01-02T03:04:05Z")
        self.assertEqual(evidence.verify(shape), [])
        self.assertEqual((shape["kind"], shape["outcome"], shape["tool_version"]), ("test", "pass", "0.4.2"))
        self.assertEqual(shape["transport"], {"adapter": "usb-can-1", "bus": "can0", "bitrate": 500000})
        self.assertEqual(shape["artifacts"][0]["sha256"], self._record().log_sha256)

    def test_an_unknown_firmware_version_is_left_out_and_the_time_defaults_to_now(self):
        shape = evidence_record(self._record(firmware_version="unknown"), tool_version="0.4.2")
        self.assertNotIn("version_after", shape["subject"])
        self.assertTrue(shape["timestamp_utc"].endswith("Z"))

    def test_it_is_written_as_json(self):
        import json

        path = self.dir / "shape.json"
        save_evidence(self._record(outcome="fail"), path, tool_version="0.4.2", timestamp_utc="2026-01-02T03:04:05Z")
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["outcome"], "fail")

if __name__ == "__main__":
    unittest.main()
