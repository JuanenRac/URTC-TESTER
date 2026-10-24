# =============================================================================
# URTC Tester - the test plans in the Qt Quick deck: the list, the gate, a run against the simulated head, the answers of the person
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
import json
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest import mock

import tester_config
import tester_plan
from tester_simulator import SimulatedBoard

try:
    import qt_tester
    from PySide6.QtCore import QCoreApplication, Qt
except ImportError:  # PySide6 is not installed
    qt_tester = None
    QCoreApplication = None
    Qt = None

ROOT = Path(__file__).resolve().parents[1]


class InlineThread:
    """A thread that runs its function when it is started, in the thread that starts it."""

    def __init__(self, target=None, args=(), kwargs=None, name=None, daemon=None):
        self._target, self._args, self._kwargs = target, args, kwargs or {}

    def start(self):
        self._target(*self._args, **self._kwargs)

    def is_alive(self):
        return False

    def join(self, timeout=None):
        pass


READ_ONLY = {
    "format": 1, "name": "read-only-check", "description": "Asks and changes nothing.",
    "steps": [{"do": "query_version", "label": "the application answers"}, {"do": "check_faults", "label": "no fault"}],
}
ASKS = {
    "format": 1, "name": "asks-a-person", "description": "Asks a person.",
    "steps": [{"do": "query_version"}, {"do": "confirm", "text": "Is the lamp on?", "label": "look at the lamp"}],
}


@unittest.skipIf(qt_tester is None, "PySide6 is not available")
class QtPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        for patcher in (mock.patch.object(qt_tester, "save_config", return_value=True),):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        base = Path(self.folder.name)
        (base / "plans").mkdir()
        for name, plan in (("read_only.json", READ_ONLY), ("asks.json", ASKS)):
            (base / "plans" / name).write_text(json.dumps(plan), encoding="utf-8")
        (base / "plans" / "broken.json").write_text('{"format": 1, "name": "x"}', encoding="utf-8")
        (base / "plans" / "notes.txt").write_text("not a plan", encoding="utf-8")
        for patcher in (mock.patch.object(tester_config, "base_dir", str(base)), mock.patch.object(qt_tester, "LOGS_FOLDER", str(base / "logs"))):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.bridge = qt_tester.TesterQtBridge()
        self.logs = []
        self.bridge._log = self.logs.append
        self.board = SimulatedBoard(0, delay=0.001)
        self.bridge._transport = self.board
        self.bridge._listen_only = False

    def _on_question(self, answer):
        """What the person in front of the board does when a plan asks something; the connection is undone at the end of the test."""
        self.bridge.planConfirmRequested.connect(answer, Qt.ConnectionType.DirectConnection)
        self.addCleanup(self.bridge.planConfirmRequested.disconnect)

    def _run(self, name, allow=False):
        """Starts the plan the way the window does. The worker threads run inline (no thread at all): the plan, the question to the person and
        the signals that report them all happen in the thread of the test, so nothing is left running when the test ends."""
        proxy = types.SimpleNamespace(Thread=InlineThread, Event=threading.Event, RLock=threading.RLock, Lock=threading.Lock)
        with mock.patch.object(qt_tester, "threading", proxy), mock.patch.object(tester_plan, "threading", proxy):
            self.bridge.refreshPlans()
            self.bridge.runPlan(name, allow)
        self.assertFalse(self.bridge.planRunning)

    def test_the_plans_next_to_the_program_are_listed_and_a_broken_one_is_reported(self):
        self.bridge.refreshPlans()
        names = [item["name"] for item in self.bridge.planList]
        self.assertEqual(names, ["asks-a-person", "read-only-check"])
        self.assertTrue(all(item["actuates"] is False for item in self.bridge.planList))
        self.assertIn("broken.json", self.bridge.planProblems)
        self.assertNotIn("notes.txt", self.bridge.planProblems)

    def test_no_plans_folder_is_an_empty_list(self):
        with mock.patch.object(tester_config, "base_dir", str(Path(self.folder.name) / "nowhere")):
            self.bridge.refreshPlans()
        self.assertEqual(self.bridge.planList, [])
        self.assertEqual(self.bridge.planProblems, "")

    def test_the_gate_needs_an_armed_idle_connection_with_no_other_reader(self):
        self.assertTrue(self.bridge.canRunPlan)
        self.bridge._listen_only = True
        self.assertFalse(self.bridge.canRunPlan)
        self.bridge._listen_only = False
        self.bridge._busy = True
        self.assertFalse(self.bridge.canRunPlan)
        self.bridge._busy = False
        self.bridge._transport = None
        self.assertFalse(self.bridge.canRunPlan)
        self.bridge._transport = self.board
        self.bridge._monitor_stop = threading.Event()
        self.assertFalse(self.bridge.canRunPlan)

    def test_a_plan_is_not_started_when_the_gate_is_closed_or_the_name_is_unknown(self):
        self.bridge._listen_only = True
        self.bridge.refreshPlans()
        self.bridge.runPlan("read-only-check", False)
        self.bridge._listen_only = False
        self.bridge.runPlan("no-such-plan", False)
        self.assertFalse(self.bridge.planRunning)
        self.assertEqual([line for line in self.logs if line.startswith("PLAN_BLOCKED")], ["PLAN_BLOCKED read-only-check", "PLAN_BLOCKED no-such-plan"])

    def test_a_read_only_plan_runs_against_the_simulated_head_and_saves_its_log_and_record(self):
        self._run("read-only-check")
        self.assertEqual([line["status"] for line in self.bridge.planLines], ["PASS", "PASS"])
        self.assertIn("1. query_version [the application answers]", self.bridge.planLines[0]["text"])
        self.assertIn("2 passed", self.bridge.planSummary)
        logs = list((Path(self.folder.name) / "logs").glob("read-only-check_*"))
        self.assertEqual(sorted(path.suffix for path in logs), [".json", ".log"])
        record = json.loads(next(path for path in logs if path.suffix == ".json").read_text(encoding="utf-8"))
        self.assertEqual((record["test_name"], record["outcome"]), ("read-only-check", "pass"))
        self.assertTrue(record["adapter"].startswith("deck:"))
        self.assertTrue(any(line == "PLAN_COMPLETE pass" for line in self.logs))
        self.assertFalse(self.bridge._busy)

    def test_the_summary_is_said_in_the_language_of_the_deck(self):
        with mock.patch.dict(tester_config._translations, {
            "QT_PLAN_SUMMARY": "{outcome}: {passed} superadas, {failed} falladas, {errors} errores, {skipped} omitidas",
            "QT_PLAN_OUTCOME_PASS": "SUPERADO",
        }):
            self._run("read-only-check")
        self.assertTrue(self.bridge.planSummary.startswith("SUPERADO: 2 superadas, 0 falladas, 0 errores, 0 omitidas"))

    def test_a_confirm_step_waits_for_the_answer_of_the_person(self):
        asked = []
        self._on_question(lambda text: (asked.append(text), self.bridge.answerPlanConfirm(True)))
        self._run("asks-a-person")
        self.assertEqual(asked, ["Is the lamp on?"])
        self.assertEqual([line["status"] for line in self.bridge.planLines], ["PASS", "PASS"])

    def test_a_no_from_the_person_fails_the_step(self):
        self._on_question(lambda text: self.bridge.answerPlanConfirm(False))
        self._run("asks-a-person")
        self.assertEqual([line["status"] for line in self.bridge.planLines], ["PASS", "FAIL"])
        self.assertIn("1 failed", self.bridge.planSummary)

    def test_cancelling_while_a_question_is_open_answers_no_and_skips_the_rest(self):
        self._on_question(lambda text: self.bridge.cancelPlan())
        self._run("asks-a-person")
        self.assertEqual(self.bridge.planLines[0]["status"], "PASS")
        self.assertNotEqual(self.bridge.planLines[-1]["status"], "PASS")

    def test_a_plan_that_commands_outputs_needs_the_switch_of_the_person_as_well(self):
        bench = json.loads((ROOT / "plans" / "soldering_iron_bench.json").read_text(encoding="utf-8"))
        (Path(self.folder.name) / "plans" / "bench.json").write_text(json.dumps(bench), encoding="utf-8")
        self.bridge.refreshPlans()
        listed = next(item for item in self.bridge.planList if item["name"] == "soldering-iron-bench")
        self.assertTrue(listed["actuates"])
        self._on_question(lambda text: self.bridge.answerPlanConfirm(True))
        self._run("soldering-iron-bench", allow=False)
        self.assertIn("ERROR", [line["status"] for line in self.bridge.planLines])
        self.assertFalse(any(frame[0] == 0x130 and frame[1] != b"\x00\x00" for frame in self.board.sent), "no heating order may have been sent")

    def test_the_window_looks_for_plans_when_it_opens_and_has_a_place_for_them(self):
        qml = (ROOT / "assets" / "qml" / "TesterDeck.qml").read_text(encoding="utf-8")
        for needle in ("testerBackend.refreshPlans()", "testerBackend.planList", "testerBackend.runPlan(", "onPlanConfirmRequested", "testerBackend.answerPlanConfirm("):
            self.assertIn(needle, qml)


if __name__ == "__main__":
    unittest.main()
