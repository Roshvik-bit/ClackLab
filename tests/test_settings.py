"""
Tests for settings persistence, schema migration, corruption recovery, and reset defaults.
"""

import os
import json
import tempfile
import pytest
from app.settings import SettingsManager, AppSettings

def test_default_settings_creation():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test_settings.json")
        mgr = SettingsManager(filepath=path)
        assert os.path.exists(path)
        assert mgr.settings.enabled is True
        assert mgr.settings.profile_id == "tactile"
        assert mgr.settings.master_volume == 0.85
        assert mgr.settings.buffer_size == 128

def test_settings_save_and_reload():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test_settings.json")
        mgr = SettingsManager(filepath=path)
        mgr.update(profile_id="thocky", master_volume=0.92, buffer_size=64)

        # Re-instantiate from file
        mgr2 = SettingsManager(filepath=path)
        assert mgr2.settings.profile_id == "thocky"
        assert mgr2.settings.master_volume == 0.92
        assert mgr2.settings.buffer_size == 64

def test_corrupted_settings_recovery():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "corrupt_settings.json")
        # Write invalid garbage JSON
        with open(path, "w") as f:
            f.write("{ INVALID JSON DATA --- broken !!! }")

        mgr = SettingsManager(filepath=path)
        # Should gracefully recover to defaults
        assert mgr.settings.profile_id == "tactile"
        assert mgr.settings.enabled is True

def test_reset_to_defaults():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test_settings.json")
        mgr = SettingsManager(filepath=path)
        mgr.update(master_volume=0.20, profile_id="clicky")
        assert mgr.settings.master_volume == 0.20

        reset = mgr.reset_to_defaults()
        assert reset.master_volume == 0.85
        assert reset.profile_id == "tactile"
