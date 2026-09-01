@echo off
REM HYDRA_UMC_SCRIPT_STANDARD_HEADER_BEGIN
REM *****************************************************************************
REM Project   : URTC-TESTER
REM Script    : build_exe.bat
REM Purpose   : Incremental standalone executable build and packaging workflow.
REM Author    : JuanenRac (Electro Hobby 3D)
REM Email     : electrohobby3d@gmail.com
REM Copyright : (C) 2026 JuanenRac
REM License   : GPL-3.0 - see LICENSE
REM *****************************************************************************
REM HYDRA_UMC_SCRIPT_STANDARD_HEADER_END
REM HYDRA_UMC_SCRIPT_STANDARD_BANNER_BEGIN
echo.
echo *****************************************************************************
echo * URTC-TESTER - build_exe.bat
echo * Mode      : INCREMENTAL BUILD
echo * Author    : JuanenRac (Electro Hobby 3D)
echo * Email     : electrohobby3d@gmail.com
echo * Copyright : (C) 2026 JuanenRac
echo * License   : GPL-3.0 - see LICENSE
echo * ------------------------------------------------------------------------- *
echo * 1. Increment the project version and synchronise its manifest.
echo * 2. Run this project's declared build, verification and packaging commands.
echo * 3. Report the result and keep an interactive terminal open.
echo *****************************************************************************
echo.
REM HYDRA_UMC_SCRIPT_STANDARD_BANNER_END
setlocal EnableDelayedExpansion
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt
python -m pip install pyinstaller
echo       Done.
echo.

echo [2/6] Cleaning previous build...
REM Clean slate before compiling - see build_exe.sh for the reasoning.
if exist build rmdir /s /q build
if exist dist (
    rmdir /s /q dist
    if exist dist (
        echo       ERROR: couldn't remove dist\ - is URTC_Tester.exe currently running?
        echo       Close it first, then run this script again.
        pause
        exit /b 1
    )
)
echo       Done.
echo.

echo [3/6] Bumping TESTER_VERSION for this build...
REM Ecosystem-wide versioning policy: TESTER_VERSION auto-increments on
REM every REAL build (every run of this script), never just from running
REM "python urtc_tester.py" from source. base-10 "odometer" rule - see
REM bump_version.py for the exact carry logic (e.g. 1.1.9 -> 1.2.0).
REM HYDRA_UMC_SCRIPT_STANDARD_VERSION_STEP
echo [1/6] Incrementing project version and synchronising its manifest...
python bump_version.py
if errorlevel 1 ( echo NATIVE VERSION BUMP FAILED. & pause & exit /b 1 )
REM HYDRA_UMC_SCRIPT_STANDARD_VERSION_CAPTURE_BEFORE
for /f "usebackq delims=" %%V in (`python -c "import json; print(json.load(open(r'%~dp0hydra-umc.project.json', encoding='utf-8'))['version'])"`) do set "HYDRA_UMC_VERSION_BEFORE=%%V"
python "%~dp0bump_manifest_version.py" --sync
if errorlevel 1 ( echo VERSION SYNCHRONIZATION FAILED. & pause & exit /b 1 )
if errorlevel 1 (
    echo       ERROR: version bump failed - see the output above.
    pause
    exit /b 1
)
REM HYDRA_UMC_SCRIPT_STANDARD_VERSION_CAPTURE_AFTER
for /f "usebackq delims=" %%V in (`python -c "import json; print(json.load(open(r'%~dp0hydra-umc.project.json', encoding='utf-8'))['version'])"`) do set "HYDRA_UMC_VERSION_AFTER=%%V"
if not defined HYDRA_UMC_VERSION_BEFORE set "HYDRA_UMC_VERSION_BEFORE=unknown"
if not defined HYDRA_UMC_VERSION_AFTER set "HYDRA_UMC_VERSION_AFTER=unknown"
echo.
echo *****************************************************************************
echo * VERSION INCREMENT COMPLETED
echo * v%HYDRA_UMC_VERSION_BEFORE% ^> v%HYDRA_UMC_VERSION_AFTER%
echo * Project manifest has been synchronised by the project build flow.
echo *****************************************************************************
echo.
echo.

echo [4/6] Compiling URTC_Tester.exe with PyInstaller...
REM --icon sets what Explorer/the taskbar shows for the .exe file itself -
REM separate from root.iconphoto() in the code, which sets the title-bar/
REM Alt-Tab icon of the running window. Both need setting for a consistent
REM icon everywhere.
REM --hidden-import for each of this project's own modules - see the
REM Linux build script's identical comment for the full reasoning.
python -m PyInstaller --onefile --windowed --noconfirm --name "URTC_Tester" ^
    --icon "assets\urtc_icon.ico" ^
    --add-data "assets;assets" ^
    --hidden-import tester_config ^
    --hidden-import tester_transports ^
    --hidden-import tester_bus_monitor ^
    --hidden-import tester_gui_core ^
    --hidden-import tester_common_panels ^
    --hidden-import tester_panel_helpers ^
    --hidden-import tester_tool_panels ^
    --hidden-import qt_tester ^
    --hidden-import PySide6.QtQml ^
    --hidden-import PySide6.QtQuick ^
    --hidden-import PySide6.QtQuickControls2 ^
    --collect-all PySide6.QtQuick ^
    --collect-all PySide6.QtQuickControls2 ^
    urtc_tester.py
if not exist dist\URTC_Tester.exe (
    echo       ERROR: PyInstaller did not produce dist\URTC_Tester.exe - see the output above.
    pause
    exit /b 1
)
echo       Done.
echo.

echo [5/6] Copying files that must sit next to the .exe, not inside it...
REM language/ is deliberately NOT bundled into the .exe itself (unlike
REM assets above) - it's meant to stay editable without a rebuild, same
REM reasoning as the flasher's own firmware\ folder. Without this, the
REM built .exe would have nowhere to find its translation files, since
REM LANGUAGE_FOLDER resolves next to the executable, not inside
REM PyInstaller's bundled data.
if exist language (
    if not exist dist\language mkdir dist\language
    xcopy /e /i /y language dist\language >nul
    echo       Copied language\ into dist\language\
)
REM README.md and LICENSE: read directly by the Help menu's Readme/License
REM entries (tester_config.base_dir - next to the .exe, same reasoning as
REM language above). Missing from dist/ meant those menu entries had
REM nothing to open in a built .exe, even though they worked fine running
REM from source. README_*.md (README_spa.md, README_ita.md, etc.) are the
REM per-language versions the Readme menu entry picks up automatically
REM based on the active language - copied via a for loop rather than
REM listing each language explicitly, so a new translation added later is
REM picked up without editing this script again.
if exist README.md (
    copy /Y README.md dist\README.md >nul
    echo       Copied README.md into dist\
)
for %%f in (README_*.md) do (
    copy /Y "%%f" "dist\%%f" >nul
    echo       Copied %%f into dist\
)
if exist LICENSE (
    copy /Y LICENSE dist\LICENSE >nul
    echo       Copied LICENSE into dist\
)
echo       Done.
echo.

echo [6/6] Build complete.
echo  ===============================================================
echo   dist\URTC_Tester.exe is ready to run - no Python needed.
echo  ===============================================================
echo.
pause
