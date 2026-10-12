#!/usr/bin/env bash
# ==============================================================================
# ClackLab: Development Launch Script
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Check virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment in .venv..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Ensure sound assets exist
if [ ! -f "assets/sounds/manifest.json" ]; then
    echo "Preparing sound assets..."
    python3 scripts/prepare_sound_assets.py
fi

echo "Launching ClackLab..."
exec python3 main.py "$@"
