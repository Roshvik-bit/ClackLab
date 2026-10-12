"""
Tests for latency tracking, percentile calculations, and thread-safe metrics recording.
"""

import time
import pytest
from app.audio.latency_metrics import LatencyTracker

def test_empty_latency_tracker():
    tracker = LatencyTracker()
    stats = tracker.get_stats()
    assert stats.count == 0
    assert stats.median_ms == 0.0
    assert stats.p95_ms == 0.0
    assert stats.max_ms == 0.0

def test_latency_calculation():
    tracker = LatencyTracker()
    
    t0 = time.perf_counter_ns()
    # Simulate 0.5 ms delay
    t_sched = t0 + 500_000  # 500,000 ns = 0.5 ms
    tracker.record_event_processed(t0, t_sched)

    # Simulate 1.0 ms delay
    t_sched2 = t0 + 1_000_000
    tracker.record_event_processed(t0, t_sched2)

    # Simulate 1.5 ms delay
    t_sched3 = t0 + 1_500_000
    tracker.record_event_processed(t0, t_sched3)

    stats = tracker.get_stats()
    assert stats.count == 3
    assert stats.median_ms == 1.0
    assert stats.max_ms == 1.5
    assert stats.last_ms == 1.5

def test_underrun_recording():
    tracker = LatencyTracker()
    assert tracker.get_stats().buffer_underruns == 0
    tracker.record_underrun()
    tracker.record_underrun()
    assert tracker.get_stats().buffer_underruns == 2
    tracker.reset()
    assert tracker.get_stats().buffer_underruns == 0
