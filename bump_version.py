#!/usr/bin/env python3
# =============================================================================
# URTC Tester - automatic version bump, run by build_exe.bat/build_exe.sh
# right before every real PyInstaller build (never when just running from
# source with "python urtc_tester.py") - ecosystem-wide versioning policy.
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Increments TESTER_VERSION in tester_config.py in place, following a
base-10 "odometer" rule applied to the last 2 parts of MAJOR.MINOR.PATCH:
PATCH goes up by 1; if that pushes it past 9, PATCH resets to 0 and MINOR
goes up by 1 instead (e.g. 0.1.9 -> 0.2.0). MAJOR is never touched by this
script - bumping the major version is a deliberate human decision, not
something a build script should ever do on its own.

Only this one assignment line is touched via an anchored regex - it does
NOT touch the unrelated ";$FILEVERSION=1.1" line in tester_common_panels.py,
which is a fixed literal inside the PEAK PCAN-View .trc export format (an
external trace-file convention), not this tool's own version number.
"""
import re
import sys
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "tester_config.py"
VERSION_RE = re.compile(r'^(TESTER_VERSION\s*=\s*")(\d+)\.(\d+)\.(\d+)(")', re.MULTILINE)


def bump(major, minor, patch):
    patch += 1
    if patch > 9:
        patch = 0
        minor += 1
    return major, minor, patch


def main():
    try:
        text = CONFIG_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: couldn't read {CONFIG_PATH}: {exc}", file=sys.stderr)
        return 1

    match = VERSION_RE.search(text)
    if not match:
        print(
            f"ERROR: TESTER_VERSION not found in {CONFIG_PATH} in the expected "
            f'MAJOR.MINOR.PATCH form (e.g. TESTER_VERSION = "0.1.0")',
            file=sys.stderr,
        )
        return 1

    major, minor, patch = (int(match.group(i)) for i in (2, 3, 4))
    new_major, new_minor, new_patch = bump(major, minor, patch)
    old_version = f"{major}.{minor}.{patch}"
    new_version = f"{new_major}.{new_minor}.{new_patch}"

    new_text = (
        text[: match.start()]
        + f"{match.group(1)}{new_version}{match.group(5)}"
        + text[match.end() :]
    )
    try:
        CONFIG_PATH.write_text(new_text, encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: couldn't write {CONFIG_PATH}: {exc}", file=sys.stderr)
        return 1

    print(f"      TESTER_VERSION bumped: {old_version} -> {new_version}")
    return 0


def _delegate_to_shared_utility():
    """Hand the bump over to the shared utility once the version has four parts.

    Returns its exit code, or None when this step is an ordinary three-part one.
    """
    import importlib.util
    import json as _json
    from pathlib import Path as _Path

    here = _Path(__file__).resolve().parent
    root = here if (here / "bump_manifest_version.py").is_file() else here.parent
    utility, manifest = root / "bump_manifest_version.py", root / "hydra-umc.project.json"
    if not utility.is_file() or not manifest.is_file():
        return None
    spec = importlib.util.spec_from_file_location("_shared_bump", utility)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    version = _json.loads(manifest.read_text(encoding="utf-8")).get("version", "")
    if not hasattr(module, "FOUR_PART_FROM") or module.next_version(version).count(".") != 3:
        return None
    return module.main()


if __name__ == "__main__":
    _shared_exit = _delegate_to_shared_utility()
    if _shared_exit is not None:
        raise SystemExit(_shared_exit)


if __name__ == "__main__":
    sys.exit(main())
