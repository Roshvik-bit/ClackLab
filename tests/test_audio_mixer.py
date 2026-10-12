"""
Tests for bounded audio mixer, polyphony voice stealing, and soft limiting.
"""

import numpy as np
import pytest
from app.audio.audio_engine import AudioEngine, MAX_POLYPHONY
from app.audio.latency_metrics import LatencyTracker

class MockStatusFlags:
    output_underflow = False

def test_mixer_silence_when_empty():
    tracker = LatencyTracker()
    engine = AudioEngine(sample_rate=48000, block_size=128, latency_tracker=tracker)
    engine._is_running = True

    outdata = np.ones((128, 2), dtype=np.float32)
    engine._audio_callback(outdata, 128, None, MockStatusFlags())

    # Should be filled with silence (all 0.0)
    assert np.all(outdata == 0.0)

def test_mixer_voice_playback():
    tracker = LatencyTracker()
    engine = AudioEngine(sample_rate=48000, block_size=64, latency_tracker=tracker)
    engine._is_running = True
    engine.master_gain = 1.0

    # 128 frames sample with value 0.5
    sample = np.full((128, 2), 0.5, dtype=np.float32)
    engine.schedule_voice(sample, gain=1.0)

    # First block of 64 frames
    block1 = np.zeros((64, 2), dtype=np.float32)
    engine._audio_callback(block1, 64, None, MockStatusFlags())
    assert np.all(block1 > 0.0)
    # 1 active voice still playing
    assert len(engine._active_voices) == 1

    # Second block of 64 frames (finishes sample)
    block2 = np.zeros((64, 2), dtype=np.float32)
    engine._audio_callback(block2, 64, None, MockStatusFlags())
    assert np.all(block2 > 0.0)
    assert len(engine._active_voices) == 0

def test_bounded_polyphony_capping():
    tracker = LatencyTracker()
    engine = AudioEngine(sample_rate=48000, block_size=64, latency_tracker=tracker)
    engine._is_running = True

    sample = np.ones((1000, 2), dtype=np.float32)

    # Schedule 50 overlapping voices (exceeding MAX_POLYPHONY of 32)
    for _ in range(50):
        engine.schedule_voice(sample, gain=0.1)

    outdata = np.zeros((64, 2), dtype=np.float32)
    engine._audio_callback(outdata, 64, None, MockStatusFlags())

    # Active voices must be capped strictly at MAX_POLYPHONY
    assert len(engine._active_voices) == MAX_POLYPHONY

def test_soft_limiter():
    tracker = LatencyTracker()
    engine = AudioEngine(sample_rate=48000, block_size=64, latency_tracker=tracker)
    engine._is_running = True
    engine.master_gain = 1.0

    # Schedule massive amplitude (would clip digitally without limiter)
    loud_sample = np.full((64, 2), 5.0, dtype=np.float32)
    engine.schedule_voice(loud_sample, gain=1.0)

    outdata = np.zeros((64, 2), dtype=np.float32)
    engine._audio_callback(outdata, 64, None, MockStatusFlags())

    # np.tanh(5.0 * 0.95) should be strictly < 1.0 (no digital clipping!)
    assert np.max(np.abs(outdata)) < 1.0
