# =============================================================================
# URTC Tester - tests/test_window_geometry.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The window fits the screen it opens on and stays resizable: the size is chosen from the free area of the screen and the file of settings (a small screen gets a smaller window and
a smaller minimum, a large one the configured size), and the real deck, loaded offscreen on a small screen, opens inside it, can be resized both ways and draws at the size it has.
Nothing here opens a bus or a board."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import tester_config as config

ROOT = Path(__file__).resolve().parent.parent


# ---- the settings -----------------------------------------------------------------------------------------------------

def test_the_defaults_are_the_size_the_deck_always_had():
    assert config.window_settings({}) == {"width": 1440, "height": 900, "min_width": 1080, "min_height": 680, "screen_fraction": 0.95}


def test_the_settings_are_read_from_the_window_section_and_bounded_per_field():
    given = {"window": {"width": 1600, "height": "tall", "min_width": True, "min_height": 500, "screen_fraction": 0.8}}
    settings = config.window_settings(given)
    assert settings["width"] == 1600 and settings["min_height"] == 500 and settings["screen_fraction"] == 0.8
    assert settings["height"] == 900 and settings["min_width"] == 1080  # a text and a boolean keep the default of their field


@pytest.mark.parametrize("value", [-1, 0, 100, 639, 7681, 1.5, None, "1440", [1440], True])
def test_a_width_that_is_not_a_whole_number_inside_its_bounds_keeps_the_default(value):
    assert config.window_settings({"window": {"width": value}})["width"] == 1440


@pytest.mark.parametrize("value", [0.49, 1.01, -0.5, "0.9", None, True, [0.9]])
def test_a_screen_fraction_outside_half_to_all_of_the_screen_keeps_the_default(value):
    assert config.window_settings({"window": {"screen_fraction": value}})["screen_fraction"] == 0.95


@pytest.mark.parametrize("window", [None, 5, "x", [1], True])
def test_a_window_section_that_is_not_a_table_is_ignored(window):
    assert config.window_settings({"window": window}) == config.WINDOW_DEFAULTS


def test_the_settings_come_from_the_file_when_none_are_given(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"window": {"width": 1200}}), encoding="utf-8")
    monkeypatch.setattr(config, "CONFIG_PATH", str(path))
    assert config.window_settings()["width"] == 1200
    assert config.window_geometry(0, 0)["width"] == 1200


# ---- the geometry -------------------------------------------------------------------------------------------------------

def test_a_large_screen_gets_the_configured_size_and_minimum():
    assert config.window_geometry(2560, 1400, config.WINDOW_DEFAULTS) == {"width": 1440, "height": 900, "minimumWidth": 1080, "minimumHeight": 680}


def test_a_small_screen_gets_a_window_that_fits_and_a_minimum_that_fits_too():
    geometry = config.window_geometry(1024, 600, config.WINDOW_DEFAULTS)
    assert geometry["width"] == int(1024 * 0.95) and geometry["height"] == int(600 * 0.95)
    assert geometry["minimumWidth"] <= geometry["width"] and geometry["minimumHeight"] <= geometry["height"]


def test_a_screen_in_between_keeps_the_minimum_the_deck_needs():
    geometry = config.window_geometry(1366, 768, config.WINDOW_DEFAULTS)
    assert geometry["width"] == int(1366 * 0.95) and geometry["height"] == int(768 * 0.95)
    assert geometry["minimumWidth"] == 1080 and geometry["minimumHeight"] == min(680, geometry["height"])


@pytest.mark.parametrize("unknown", [0, -5, None, "wide", True, float("nan")])
def test_a_screen_that_is_not_known_gets_the_configured_size(unknown):
    geometry = config.window_geometry(unknown, unknown, config.WINDOW_DEFAULTS)
    assert (geometry["width"], geometry["height"]) == (1440, 900)


def test_the_minimum_never_exceeds_the_window_for_any_screen():
    for available in range(200, 5000, 37):
        geometry = config.window_geometry(available, available, config.WINDOW_DEFAULTS)
        assert 0 < geometry["minimumWidth"] <= geometry["width"] and 0 < geometry["minimumHeight"] <= geometry["height"]


# ---- the real deck, offscreen, on a small screen ----------------------------------------------------------------------

LOADER = """
import json, sys
sys.path.insert(0, sys.argv[1])
from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtQuickControls2 import QQuickStyle
import qt_tester
real = qt_tester.window_geometry
qt_tester.window_geometry = lambda w, h, settings=None: real(1024, 600, settings)  # a screen of 1024 x 600
QQuickStyle.setStyle("Basic")
app = QGuiApplication([])
bridge = qt_tester.TesterQtBridge()
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("testerBackend", bridge)
engine.load(QUrl.fromLocalFile(sys.argv[2]))
root = engine.rootObjects()[0]
def pump():
    for _ in range(40):
        app.processEvents()
opened = (root.width(), root.height(), root.minimumWidth(), root.minimumHeight())
root.setWidth(1500); root.setHeight(950); pump()
grown = (root.width(), root.height())
root.setWidth(300); root.setHeight(300); pump()
shrunk = (root.width(), root.height())
root.setWidth(900); root.setHeight(570); pump()
image = QQuickWindow.grabWindow(root)
print("RESULT " + json.dumps({"opened": opened, "grown": grown, "shrunk": shrunk, "grab": (image.width(), image.height())}))
sys.stdout.flush()
import os
os._exit(0)
"""


def test_the_real_deck_opens_inside_a_small_screen_and_resizes_both_ways():
    pytest.importorskip("PySide6")
    environment = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    done = subprocess.run([sys.executable, "-c", LOADER, str(ROOT), str(ROOT / "assets" / "qml" / "TesterDeck.qml")], capture_output=True, text=True, env=environment,
                          timeout=120, cwd=str(ROOT))
    line = next((l for l in done.stdout.splitlines() if l.startswith("RESULT ")), None)
    assert line is not None, done.stderr[-2000:]
    result = json.loads(line[len("RESULT "):])
    width, height, minimum_width, minimum_height = result["opened"]
    assert (width, height) == (int(1024 * 0.95), int(600 * 0.95))
    assert minimum_width <= width and minimum_height <= height
    assert tuple(result["grown"]) == (1500, 950)  # it can be made larger than it opened
    assert tuple(result["shrunk"]) == (300, 300)  # and smaller (the minimum is enforced by the window manager of a real desktop, which an offscreen run does not have)
    assert tuple(result["grab"]) == (900, 570)  # what is drawn has the size the window has
