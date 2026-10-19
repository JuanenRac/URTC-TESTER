# =============================================================================
# URTC Tester - tests/conftest.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""No test may touch the real config.json next to the program (the person's saved language and settings): every test gets its own path for it, and at the end of the
whole run the real file must be exactly as it was (present or absent, same bytes)."""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tester_config  # noqa: E402

REAL_CONFIG = Path(tester_config.CONFIG_PATH)


def _state() -> tuple[bool, str | None, bool]:
    digest = hashlib.sha256(REAL_CONFIG.read_bytes()).hexdigest() if REAL_CONFIG.is_file() else None
    return REAL_CONFIG.exists(), digest, Path(str(REAL_CONFIG) + ".tmp").exists()


@pytest.fixture(scope="session", autouse=True)
def the_real_config_is_left_alone():
    before = _state()
    yield
    assert _state() == before, f"the tests changed the real {REAL_CONFIG}: a test must save its settings through a temporary path"


@pytest.fixture(autouse=True)
def config_goes_to_a_temporary_file(tmp_path, monkeypatch):
    monkeypatch.setattr(tester_config, "CONFIG_PATH", str(tmp_path / "config.json"))
