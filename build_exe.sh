#!/usr/bin/env bash
# Builds a standalone Linux binary for the URTC Tester.
# Run this on the Linux machine you actually want to run it on - unlike
# cross-compiling, PyInstaller builds a binary for whatever OS it runs on,
# so this won't produce something usable on Windows, and build_exe.bat
# won't produce something usable here.
#
# Usage:
#   chmod +x build_exe.sh   (one-time)
#   ./build_exe.sh
#
# Output: dist/URTC_Tester (no Python installation needed to run it)
set -euo pipefail

# Keeps the terminal window open after the script finishes, on both
# success and failure (set -e above means a failed command jumps straight
# to process exit, which would otherwise close a window opened by
# double-clicking this script in a file manager before anyone could read
# why it failed) - runs on every exit path, no need to duplicate it at
# each individual error site.
trap 'echo; read -p "Press Enter to close this window... " _dummy' EXIT

echo
echo " ==============================================================="
echo "  U R T C - T E S T E R  -  Linux build script"
echo " ==============================================================="
echo "  Builds a standalone Linux binary for the URTC Tester (PyInstaller),"
echo "  bumps TESTER_VERSION, then bundles it with language/, README(s)"
echo "  and LICENSE into dist/."
echo "  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>"
echo "  GPL-3.0 - see LICENSE"
echo " ==============================================================="
echo

# python3-tk is a separate OS package on Debian/Ubuntu-family distros -
# tkinter isn't pulled in automatically by "pip install", since it isn't a
# pip package at all. Check for it explicitly with a clear message instead
# of letting the build succeed and then fail confusingly at runtime.
echo "[1/6] Checking for tkinter..."
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "      tkinter isn't available for this Python install."
    echo "      On Debian/Ubuntu:  sudo apt install python3-tk"
    echo "      On Fedora:         sudo dnf install python3-tkinter"
    echo "      On Arch:           sudo pacman -S tk"
    exit 1
fi
echo "      Found."
echo

echo "[2/6] Installing Python dependencies..."
python3 -m pip install --upgrade pip >/dev/null
python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller
echo "      Done."
echo

echo "[3/6] Cleaning previous build..."
# Clean slate before compiling: build/ holds PyInstaller's intermediate
# artifacts, dist/ holds the previous output - removing both first means
# nothing stale from an earlier build can survive into this one.
rm -rf build dist
echo "      Done."
echo

echo "[4/6] Bumping TESTER_VERSION for this build..."
# Ecosystem-wide versioning policy: TESTER_VERSION auto-increments on
# every REAL build (every run of this script), never just from running
# "python3 urtc_tester.py" from source. base-10 "odometer" rule - see
# bump_version.py for the exact carry logic (e.g. 1.1.9 -> 1.2.0).
# set -e (top of this script) already aborts the build if this fails.
python3 bump_version.py || exit 1
python3 "$(dirname "$0")/bump_manifest_version.py" --sync || exit 1
echo "      Done."
echo

echo "[5/6] Compiling URTC_Tester with PyInstaller..."
# --hidden-import for each of this project's own modules: this file was
# split from one large urtc_tester.py into several for readability -
# PyInstaller's static analyzer normally finds these on its own by
# walking the import tree, but listing every one explicitly here
# removes any doubt.
python3 -m PyInstaller --onefile --noconfirm --name "URTC_Tester" \
    --add-data "assets:assets" \
    --hidden-import tester_config \
    --hidden-import tester_transports \
    --hidden-import tester_bus_monitor \
    --hidden-import tester_gui_core \
    --hidden-import tester_common_panels \
    --hidden-import tester_panel_helpers \
    --hidden-import tester_tool_panels \
    urtc_tester.py
if [ ! -f dist/URTC_Tester ]; then
    echo "      ERROR: PyInstaller did not produce dist/URTC_Tester - see the output above."
    exit 1
fi
echo "      Done."
echo

echo "[6/6] Copying files that must sit next to the binary, not inside it..."
# language/ is deliberately NOT bundled into the binary itself (unlike
# assets/ above) - it's meant to stay editable without a rebuild, same
# reasoning as the flasher's own firmware/ folder. Without this, a
# --onefile binary would have nowhere to find its translation files at
# all, since LANGUAGE_FOLDER resolves next to the executable, not inside
# PyInstaller's bundled data.
if [ -d language ]; then
    mkdir -p dist/language
    cp -r language/. dist/language/
    echo "      Copied language/ into dist/language/"
fi
# README.md and LICENSE: read directly by the Help menu's Readme/License
# entries (tester_config.base_dir - next to the executable, same
# reasoning as language above). Missing from dist/ meant those menu
# entries had nothing to open in a built binary, even though they
# worked fine running from source. README_*.md (README_spa.md,
# README_ita.md, etc.) are the per-language versions the Readme menu
# entry picks up automatically based on the active language - copied via
# a glob rather than listing each language explicitly, so a new
# translation added later is picked up without editing this script again.
if [ -f README.md ]; then
    cp README.md dist/README.md
    echo "      Copied README.md into dist/"
fi
for f in README_*.md; do
    if [ -f "$f" ]; then
        cp "$f" "dist/$f"
        echo "      Copied $f into dist/"
    fi
done
if [ -f LICENSE ]; then
    cp LICENSE dist/LICENSE
    echo "      Copied LICENSE into dist/"
fi
echo "      Done."
echo

echo " ==============================================================="
echo "  Build complete: dist/URTC_Tester is ready to run - no Python needed."
echo "  (chmod +x dist/URTC_Tester if it isn't already executable)"
echo " ==============================================================="
echo
