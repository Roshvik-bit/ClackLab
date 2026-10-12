#!/usr/bin/env bash
# ==============================================================================
# ClackLab: macOS Application Bundle Packager (.app)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "Ensuring sound assets are generated..."
if [ ! -f "assets/sounds/manifest.json" ]; then
    python3 scripts/prepare_sound_assets.py
fi

echo "Building standalone macOS Application bundle with PyInstaller..."

# Clean previous dist/build
rm -rf build dist

pyinstaller \
    --name "ClackLab" \
    --windowed \
    --clean \
    --noconfirm \
    --icon "assets/icon.icns" \
    --add-data "assets:assets" \
    --hidden-import "sounddevice" \
    --hidden-import "soundfile" \
    --hidden-import "numpy" \
    --hidden-import "Quartz" \
    --hidden-import "AppKit" \
    --hidden-import "PySide6.QtCore" \
    --hidden-import "PySide6.QtGui" \
    --hidden-import "PySide6.QtWidgets" \
    --osx-bundle-identifier "com.clacklab.macos" \
    main.py

echo ""
if [ -d "dist/ClackLab.app" ]; then
    /usr/libexec/PlistBuddy -c "Add :NSAccessibilityUsageDescription string 'ClackLab plays realistic mechanical keyboard sounds globally across all macOS applications while you type.'" dist/ClackLab.app/Contents/Info.plist 2>/dev/null || true
    echo "Applying stable codesign designated requirement (identifier com.clacklab.macos)..."
    codesign --force --deep --sign - --requirements '=designated => identifier "com.clacklab.macos"' dist/ClackLab.app
    echo "============================================================"
    echo "✓ Build successful! ClackLab.app created at:"
    echo "  $PROJECT_ROOT/dist/ClackLab.app"
    echo "============================================================"
else
    echo "Build failed or ClackLab.app was not generated."
    exit 1
fi
