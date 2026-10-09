# =============================================================================
# URTC Tester - the Qt Quick session export names its log by SHA-256
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
import hashlib
import json
import os
import tempfile
import unittest
import zipfile

try:
    import qt_tester
except ImportError:  # PySide6 is not installed
    qt_tester = None


@unittest.skipIf(qt_tester is None, "PySide6 is not available")
class QtSessionExportTests(unittest.TestCase):
    def test_export_bundles_the_log_with_a_manifest_that_matches_it(self):
        with tempfile.TemporaryDirectory() as folder:
            original = qt_tester.LOGS_FOLDER
            qt_tester.LOGS_FOLDER = folder
            try:
                bridge = qt_tester.TesterQtBridge()
                bridge._logs[:] = ["first line", "second line"]
                path = bridge.exportSession()
            finally:
                qt_tester.LOGS_FOLDER = original
            self.assertTrue(path and os.path.isfile(path))
            with zipfile.ZipFile(path) as bundle:
                log = bundle.read("session_log.txt")
                manifest = json.loads(bundle.read("session_manifest.json"))
            self.assertEqual(log, b"first line\nsecond line\n")
            self.assertEqual(manifest["log_sha256"], hashlib.sha256(log).hexdigest())
            self.assertEqual(manifest["log_bytes"], len(log))
            self.assertEqual(manifest["connected"], "False")

    def test_a_folder_that_cannot_be_created_reports_and_returns_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            blocker = os.path.join(folder, "file")
            open(blocker, "w").close()
            original = qt_tester.LOGS_FOLDER
            qt_tester.LOGS_FOLDER = os.path.join(blocker, "inside")
            try:
                self.assertEqual(qt_tester.TesterQtBridge().exportSession(), "")
            finally:
                qt_tester.LOGS_FOLDER = original


if __name__ == "__main__":
    unittest.main()
