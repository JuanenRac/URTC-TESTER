# =============================================================================
# URTC Tester - the labels of the Qt Quick deck can be read, and its left panel stays inside the smallest window
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The Basic style writes the label of a check box or a switch in the window text colour of the palette, which is black unless it is set: on the dark
panels of the deck the label of the listen-only switch could barely be seen. The deck is loaded headless, in its own process, and every labelled check
box, switch and radio button is asked for the colour it writes with."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

try:
    import PySide6
except ImportError:  # PySide6 is not installed
    PySide6 = None

PROBE = r"""
import os, sys, time
root_folder = sys.argv[1]
sys.path.insert(0, root_folder)
from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication, QWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
import qt_tester
QQuickStyle.setStyle("Basic")
app = QGuiApplication([])
bridge = qt_tester.TesterQtBridge()
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("testerBackend", bridge)
engine.load(QUrl.fromLocalFile(os.path.join(root_folder, "assets", "qml", "TesterDeck.qml")))
if not engine.rootObjects():
    raise SystemExit("the deck did not load")
window = engine.rootObjects()[0]
end = time.time() + 0.6
while time.time() < end:
    app.processEvents()
    time.sleep(0.01)
seen, dark = [], []


def walk(item):
    kind = item.metaObject().className().split("_QML")[0]
    if any(word in kind for word in ("CheckBox", "Switch", "RadioButton")) and item.property("text"):
        content = item.property("contentItem")
        color = content.property("color") if content is not None else None
        if color is not None:
            seen.append(kind)
            if color.lightnessF() < 0.35:
                dark.append("%s %s %s" % (kind, ascii(str(item.property("text"))[:40]), color.name()))
    for child in item.childItems():
        walk(child)


walk(window.contentItem())
# at the smallest window the note under the list of tool profiles must still be inside it
window.setVisibility(QWindow.Visibility.Windowed)
window.setWidth(1080)
window.setHeight(680)
for _ in range(2):
    end = time.time() + 0.5
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)
    window.grabWindow()          # without a rendered frame the layout of an offscreen window is not brought up to date


def find(item, text):
    if item.property("text") == text:
        return item
    for child in item.childItems():
        found = find(child, text)
        if found is not None:
            return found
    return None


note = find(window.contentItem(), bridge.uiText("QT_STAGED_LIMIT"))
bottom = note.mapToScene(note.boundingRect().bottomLeft()).y()
print("NOTE-INSIDE" if bottom <= window.height() else "NOTE-OUTSIDE %d of %d" % (bottom, window.height()))
print(len(seen))
print("\n".join(dark) or "READABLE")
sys.stdout.flush()
os._exit(0)
"""


@unittest.skipIf(PySide6 is None, "PySide6 is not available")
class DeckLabelsAreReadableTests(unittest.TestCase):
    def test_no_switch_or_check_box_writes_dark_on_the_dark_deck(self):
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONDONTWRITEBYTECODE="1")
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            result = subprocess.run([sys.executable, "-c", PROBE, str(ROOT)], cwd=folder, env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        note, count, verdict = result.stdout.strip().split("\n", 2)
        self.assertEqual(note, "NOTE-INSIDE", "the note under the tool profiles is below the smallest window")
        self.assertGreaterEqual(int(count), 10, "the labelled controls of the deck were not found")
        self.assertEqual(verdict, "READABLE")


if __name__ == "__main__":
    unittest.main()
