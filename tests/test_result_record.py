# =============================================================================
# URTC-TESTER - reproducible result record tests
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tester_result_record import RecordError, ResultRecord, load_record, make_record, save_record, session_manifest  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
