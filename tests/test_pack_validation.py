"""
Tests for sound pack validation, corruption checking, and pack importing.
"""

import os
import json
import tempfile
import pytest
import soundfile as sf
import numpy as np

from app.soundpacks.pack_validator import SoundPackValidator
from app.soundpacks.pack_manager import SoundPackManager

def test_validate_builtin_packs():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(base_dir, "assets", "sounds")

    for p in ["linear", "tactile", "clicky", "silent", "thocky", "creamy"]:
        dir_path = os.path.join(assets_dir, p)
        report = SoundPackValidator.validate_directory(dir_path)
        assert report.is_valid is True, f"Profile {p} validation failed: {report.errors}"
        assert report.sample_count >= 5
        assert report.sample_rate == 48000

def test_validate_missing_dir():
    report = SoundPackValidator.validate_directory("/non/existent/path/clacklab")
    assert report.is_valid is False
    assert len(report.errors) > 0

def test_validate_corrupt_manifest():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Broken json
        with open(os.path.join(tmpdir, "manifest.json"), "w") as f:
            f.write("{ INVALID JSON")
        report = SoundPackValidator.validate_directory(tmpdir)
        assert report.is_valid is False

def test_pack_manager_import_and_delete():
    with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dest_dir:
        # Create a mini valid sound pack
        wav_path = os.path.join(src_dir, "down_1.wav")
        audio = np.zeros((480, 2), dtype=np.float32)
        sf.write(wav_path, audio, 48000)

        manifest = {
            "name": "Custom Mini Pack",
            "version": "1.0.0",
            "down_samples": ["down_1.wav"]
        }
        with open(os.path.join(src_dir, "manifest.json"), "w") as f:
            json.dump(manifest, f)

        mgr = SoundPackManager(target_dir=dest_dir)
        success, msg, report = mgr.import_from_folder(src_dir)
        assert success is True
        assert report.is_valid is True

        installed = mgr.list_installed_packs()
        assert len(installed) == 1

        deleted = mgr.delete_pack(installed[0])
        assert deleted is True
        assert len(mgr.list_installed_packs()) == 0
