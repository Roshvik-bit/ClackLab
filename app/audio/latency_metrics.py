"""
High-resolution latency metrics tracking and statistical analysis for ClackLab.
"""

import time
import threading
from collections import deque
from typing import List, Optional
from ..models import LatencyStats, LatencyMetricRecord

class LatencyTracker:
    """
    Thread-safe tracker measuring internal event processing, audio scheduling,
    and callback handoff latency using monotonic nanosecond resolution clocks.
    """

    def __init__(self, max_history: int = 500):
        self._lock = threading.Lock()
        self._records = deque(maxlen=max_history)
        self._buffer_underruns: int = 0
        self._active_voices: int = 0
        self._sample_rate: int = 48000
        self._block_size: int = 128
        self._last_latency_ms: float = 0.0

    def record_event_processed(
        self,
        event_timestamp_ns: int,
        schedule_timestamp_ns: int,
        callback_handoff_ns: int = 0,
        is_repeat: bool = False
    ) -> float:
        """
        Records an event scheduling milestone.
        Returns internal processing latency in milliseconds.
        """
        now_ns = time.perf_counter_ns()
        sched_ns = schedule_timestamp_ns or now_ns
        
        # Calculate internal processing latency (event detection -> voice scheduling)
        internal_ms = max(0.0, (sched_ns - event_timestamp_ns) / 1_000_000.0)
        
        # Calculate handoff latency if available
        if callback_handoff_ns > 0:
            handoff_ms = max(0.0, (callback_handoff_ns - event_timestamp_ns) / 1_000_000.0)
        else:
            handoff_ms = internal_ms

        record = LatencyMetricRecord(
            internal_latency_ms=internal_ms,
            total_handoff_latency_ms=handoff_ms,
            timestamp_ns=now_ns,
            is_repeat=is_repeat
        )

        with self._lock:
            self._records.append(record)
            self._last_latency_ms = internal_ms

        return internal_ms

    def record_underrun(self):
        with self._lock:
            self._buffer_underruns += 1

    def update_audio_state(self, active_voices: int, sample_rate: int, block_size: int):
        with self._lock:
            self._active_voices = active_voices
            self._sample_rate = sample_rate
            self._block_size = block_size

    def get_stats(self) -> LatencyStats:
        with self._lock:
            if not self._records:
                return LatencyStats(
                    count=0,
                    median_ms=0.0,
                    p95_ms=0.0,
                    max_ms=0.0,
                    last_ms=0.0,
                    buffer_underruns=self._buffer_underruns,
                    active_voices=self._active_voices,
                    sample_rate=self._sample_rate,
                    block_size=self._block_size
                )

            latencies = [r.internal_latency_ms for r in self._records]
            count = len(latencies)
            sorted_lat = sorted(latencies)
            
            # Median (50th percentile)
            mid = count // 2
            if count % 2 == 1:
                median = sorted_lat[mid]
            else:
                median = (sorted_lat[mid - 1] + sorted_lat[mid]) / 2.0

            # 95th percentile
            p95_idx = int(0.95 * (count - 1))
            p95 = sorted_lat[p95_idx]
            max_lat = sorted_lat[-1]

            return LatencyStats(
                count=count,
                median_ms=round(median, 3),
                p95_ms=round(p95, 3),
                max_ms=round(max_lat, 3),
                last_ms=round(self._last_latency_ms, 3),
                buffer_underruns=self._buffer_underruns,
                active_voices=self._active_voices,
                sample_rate=self._sample_rate,
                block_size=self._block_size
            )

    def reset(self):
        with self._lock:
            self._records.clear()
            self._buffer_underruns = 0
            self._last_latency_ms = 0.0
