"""
Audio coordinator bridging SampleLibrary, AudioEngine, and LatencyTracker.
"""

import time
import random
import logging
from typing import Optional
from .audio_engine import AudioEngine
from .sample_library import SampleLibrary
from .latency_metrics import LatencyTracker
from ..models import KeyCategory, SwitchProfile
from ..settings import AppSettings

logger = logging.getLogger(__name__)

class SamplePlayer:
    """
    High-level player coordinating sample retrieval, pitch micro-variation,
    gain calculation, voice triggering, and latency telemetry.
    """

    def __init__(
        self,
        audio_engine: AudioEngine,
        sample_library: SampleLibrary,
        latency_tracker: LatencyTracker
    ):
        self.audio_engine = audio_engine
        self.sample_library = sample_library
        self.latency_tracker = latency_tracker
        self.settings: AppSettings = AppSettings()

    def update_settings(self, settings: AppSettings):
        self.settings = settings
        self.audio_engine.master_gain = settings.master_volume
        self.audio_engine.muted = not settings.enabled

    def play_key_down(
        self,
        category: KeyCategory,
        is_repeat: bool = False,
        event_timestamp_ns: int = 0
    ):
        """Triggers audio playback for a key press event."""
        if not self.settings.enabled:
            return

        if is_repeat and not self.settings.play_key_repeats:
            return

        if category == KeyCategory.MODIFIER and not self.settings.play_modifiers:
            return

        t_start_ns = time.perf_counter_ns()
        if event_timestamp_ns <= 0:
            event_timestamp_ns = t_start_ns

        sample = self.sample_library.get_sample(
            category=category,
            is_down=True,
            randomize=self.settings.randomize_samples,
            play_stabilizers=self.settings.play_stabilizers
        )

        if sample is None:
            return

        data = sample.data

        # Optional subtle pitch variation (+/- pitch_variation_amount)
        if self.settings.pitch_variation_enabled and self.settings.pitch_variation_amount > 0:
            factor = 1.0 + random.uniform(
                -self.settings.pitch_variation_amount,
                self.settings.pitch_variation_amount
            )
            data = self.sample_library.apply_pitch_variation(data, factor)

        gain = self.settings.press_volume
        self.audio_engine.schedule_voice(data, gain=gain)

        t_sched_ns = time.perf_counter_ns()
        self.latency_tracker.record_event_processed(
            event_timestamp_ns=event_timestamp_ns,
            schedule_timestamp_ns=t_sched_ns,
            is_repeat=is_repeat
        )

    def play_key_up(
        self,
        category: KeyCategory,
        event_timestamp_ns: int = 0
    ):
        """Triggers audio playback for a key release event."""
        if not self.settings.enabled or not self.settings.play_key_up:
            return

        if category == KeyCategory.MODIFIER and not self.settings.play_modifiers:
            return

        t_start_ns = time.perf_counter_ns()
        if event_timestamp_ns <= 0:
            event_timestamp_ns = t_start_ns

        sample = self.sample_library.get_sample(
            category=category,
            is_down=False,
            randomize=self.settings.randomize_samples,
            play_stabilizers=self.settings.play_stabilizers
        )

        if sample is None:
            return

        data = sample.data
        if self.settings.pitch_variation_enabled and self.settings.pitch_variation_amount > 0:
            factor = 1.0 + random.uniform(
                -self.settings.pitch_variation_amount,
                self.settings.pitch_variation_amount
            )
            data = self.sample_library.apply_pitch_variation(data, factor)

        gain = self.settings.release_volume
        self.audio_engine.schedule_voice(data, gain=gain)

        t_sched_ns = time.perf_counter_ns()
        self.latency_tracker.record_event_processed(
            event_timestamp_ns=event_timestamp_ns,
            schedule_timestamp_ns=t_sched_ns,
            is_repeat=False
        )

    def play_preview(self):
        """Plays a preview down stroke."""
        self.play_key_down(KeyCategory.STANDARD, is_repeat=False)

    def play_test_sound(self):
        """Plays a test stroke sequence (alpha down, space down, up)."""
        self.play_key_down(KeyCategory.STANDARD)
