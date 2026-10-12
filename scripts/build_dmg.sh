#!/usr/bin/env bash
# ==============================================================================
# ClackLab: macOS DMG Package Builder
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

if [ -d ".venv" ]; then
    source .venv/bin/activate 2>/dev/null || true
    export PATH="$PROJECT_ROOT/.venv/bin:$PATH"
fi

REBUILD=false
if [ ! -d "dist/ClackLab.app" ] || [ "$1" == "--rebuild" ] || [ "$1" == "-r" ]; then
    REBUILD=true
fi

if [ "$REBUILD" = true ]; then
    echo "Running ./scripts/build_app.sh..."
    ./scripts/build_app.sh
fi

VERSION="v1.0.0"
DMG_NAME="ClackLab-${VERSION}-macOS.dmg"
DMG_PATH="dist/${DMG_NAME}"

echo "Creating compressed DMG: ${DMG_PATH}..."
rm -f "${DMG_PATH}"

# Create temporary staging directory for DMG layout
STAGING_DIR="dist/dmg_staging"
rm -rf "${STAGING_DIR}"
mkdir -p "${STAGING_DIR}"

cp -R "dist/ClackLab.app" "${STAGING_DIR}/"
ln -s /Applications "${STAGING_DIR}/Applications"

xattr -cr "${STAGING_DIR}/ClackLab.app" 2>/dev/null || true

hdiutil create \
    -volname "ClackLab" \
    -srcfolder "${STAGING_DIR}" \
    -ov \
    -format UDZO \
    "${DMG_PATH}"

rm -rf "${STAGING_DIR}"

echo "============================================================"
echo "✓ DMG created successfully:"
echo "  ${PROJECT_ROOT}/${DMG_PATH}"
ls -lh "${DMG_PATH}"
echo "============================================================"
