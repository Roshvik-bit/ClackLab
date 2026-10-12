"""
Tests for switch profiles discovery, metadata completeness, and profile loading.
"""

import os
import pytest
from app.profiles.profile_manager import ProfileManager
from app.profiles.switch_profiles import BUILTIN_PROFILES

def test_builtin_profiles_meta():
    required = ["linear", "tactile", "clicky", "silent", "thocky", "creamy"]
    for prof in required:
        assert prof in BUILTIN_PROFILES
        assert "name" in BUILTIN_PROFILES[prof]
        assert "description" in BUILTIN_PROFILES[prof]
        assert "tag" in BUILTIN_PROFILES[prof]

def test_profile_discovery():
    mgr = ProfileManager()
    profiles = mgr.discover_profiles()
    assert len(profiles) >= 6
    for p_id in ["linear", "tactile", "clicky", "silent", "thocky", "creamy"]:
        assert p_id in profiles
        prof = profiles[p_id]
        assert prof.id == p_id
        assert len(prof.down_samples) > 0
        assert os.path.exists(prof.directory_path)

def test_profile_manifest_samples_exist():
    mgr = ProfileManager()
    for p_id in ["linear", "tactile", "clicky", "silent", "thocky", "creamy"]:
        prof = mgr.get_profile(p_id)
        assert prof is not None
        # Verify down samples exist on disk
        for s in prof.down_samples:
            full_path = os.path.join(prof.directory_path, s)
            assert os.path.exists(full_path), f"Missing {full_path}"
        # Verify up samples exist
        for s in prof.up_samples:
            full_path = os.path.join(prof.directory_path, s)
            assert os.path.exists(full_path), f"Missing {full_path}"
