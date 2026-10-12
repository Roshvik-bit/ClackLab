@echo off
REM ==============================================================================
REM ClackLab: Windows Standalone Executable Packager (.exe)
REM ==============================================================================
setlocal EnableDelayedExpansion

cd /d "%~dp0.."

echo [1/3] Ensuring sound assets are present...
if not exist "assets\sounds\manifest.json" (
    python scripts\prepare_sound_assets.py
)

echo [2/3] Building standalone Windows executable with PyInstaller...
if not exist "dist" mkdir dist

pyinstaller ^
    --name "ClackLab-v1.0.0-Windows" ^
    --onefile ^
    --windowed ^
    --clean ^
    --noconfirm ^
    --icon "assets\icon.ico" ^
    --version-file "scripts\windows_version_info.txt" ^
    --add-data "assets;assets" ^
    --hidden-import "sounddevice" ^
    --hidden-import "soundfile" ^
    --hidden-import "numpy" ^
    --hidden-import "PySide6.QtCore" ^
    --hidden-import "PySide6.QtGui" ^
    --hidden-import "PySide6.QtWidgets" ^
    main.py

echo [3/3] Creating Windows ZIP bundle...
if exist "dist\ClackLab-v1.0.0-Windows.exe" (
    powershell -Command "Compress-Archive -Path 'dist\ClackLab-v1.0.0-Windows.exe' -DestinationPath 'dist\ClackLab-v1.0.0-Windows.zip' -Force"
    echo ============================================================
    echo Windows build successful:
    echo   dist\ClackLab-v1.0.0-Windows.exe
    echo   dist\ClackLab-v1.0.0-Windows.zip
    echo ============================================================
) else (
    echo Build failed. Check pyinstaller output above.
    exit /b 1
)
