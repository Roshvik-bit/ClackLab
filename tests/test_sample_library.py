"""
Tests for sample library in-memory preloading, anti-repetition memory, and pitch variation.
"""

import numpy as np
import pytest
from app.audio.sample_library import SampleLibrary
from app.profiles.profile_manager import ProfileManager
from app.models import KeyCategory

def test_sample_library_load_profile():
    mgr = ProfileManager()
    prof = mgr.get_profile("tactile")
    assert prof is not None

    lib = SampleLibrary(target_sample_rate=48000)
    success = lib.load_profile(prof)
    assert success is True
    assert len(lib._standard_down) == 5
    assert len(lib._standard_up) >= 1

def test_sample_retrieval_and_antirepetition():
    mgr = ProfileManager()
    prof = mgr.get_profile("creamy")
    lib = SampleLibrary(target_sample_rate=48000)
    lib.load_profile(prof)

    # Fetch 20 consecutive samples; consecutive samples should avoid immediate identical repetition
    prev_sample = None
    repetitions = 0
    for _ in range(20):
        sample = lib.get_sample(KeyCategory.STANDARD, is_down=True, randomize=True)
        assert sample is not None
        assert sample.data.shape[1] == 2
        assert sample.sample_rate == 48000
        if prev_sample is not None and sample.name == prev_sample.name:
            repetitions += 1
        prev_sample = sample

    # With 5 variations and anti-repetition, immediate repetitions should be 0
    assert repetitions == 0

def test_special_key_selection():
    mgr = ProfileManager()
    prof = mgr.get_profile("linear")
    lib = SampleLibrary(target_sample_rate=48000)
    lib.load_profile(prof)

    space_sample = lib.get_sample(KeyCategory.SPACE, is_down=True, play_stabilizers=True)
    assert space_sample is not None
    assert "space" in space_sample.name.lower()

    enter_sample = lib.get_sample(KeyCategory.ENTER, is_down=True, play_stabilizers=True)
    assert enter_sample is not None
    assert "enter" in enter_sample.name.lower()

def test_pitch_variation():
    # Create simple pulse
    orig = np.ones((100, 2), dtype=np.float32)
    # Pitch shift up (factor 1.05 -> shorter buffer)
    shifted_up = SampleLibrary.apply_pitch_variation(orig, 1.05)
    assert len(shifted_up) < len(orig)

    # Pitch shift down (factor 0.95 -> longer buffer)
    shifted_down = SampleLibrary.apply_pitch_variation(orig, 0.95)
    assert len(shifted_down) > len(orig)
