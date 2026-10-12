"""
Ultra-low-latency real-time callback-driven audio engine with bounded polyphony mixing.
"""

import time
import logging
import threading
from collections import deque
from typing import List, Optional, Tuple, Callable
import numpy as np
import sounddevice as sd
from .latency_metrics import LatencyTracker

logger = logging.getLogger(__name__)

MAX_POLYPHONY = 32

class ActiveVoice:
    """Represents a currently playing audio voice in the mixer."""
    __slots__ = ('sample_data', 'position', 'length', 'gain')

    def __init__(self, sample_data: np.ndarray, gain: float):
        self.sample_data = sample_data
        self.position = 0
        self.length = len(sample_data)
        self.gain = gain

class AudioEngine:
    """
    Continuously running, preinitialized PortAudio callback stream.
    Provides lock-free voice scheduling, bounded polyphony, and soft limiting.
    """

    def __init__(
        self,
        sample_rate: int = 48000,
        block_size: int = 128,
        device_index: Optional[int] = None,
        latency_tracker: Optional[LatencyTracker] = None
    ):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.device_index = device_index
        self.latency_tracker = latency_tracker or LatencyTracker()

        self._stream: Optional[sd.OutputStream] = None
        self._is_running = False
        self._lock = threading.Lock()

        # Voice scheduling queues
        self._pending_voices = deque()
        self._active_voices: List[ActiveVoice] = []
        self._master_gain: float = 0.85
        self._muted: bool = False

        # Status tracking
        self.last_error: Optional[str] = None
        self.callback_count: int = 0

    @property
    def is_running(self) -> bool:
        return self._is_running and self._stream is not None and self._stream.active

    @property
    def master_gain(self) -> float:
        return self._master_gain

    @master_gain.setter
    def master_gain(self, value: float):
        self._master_gain = max(0.0, min(1.5, float(value)))

    @property
    def muted(self) -> bool:
        return self._muted

    @muted.setter
    def muted(self, value: bool):
        self._muted = bool(value)

    def start(self) -> bool:
        """Starts the continuously running low-latency output stream."""
        with self._lock:
            if self.is_running:
                return True

            try:
                self._stream = sd.OutputStream(
                    samplerate=self.sample_rate,
                    blocksize=self.block_size,
                    device=self.device_index,
                    channels=2,
                    dtype='float32',
                    latency='low',
                    callback=self._audio_callback
                )
                self._stream.start()
                self._is_running = True
                self.last_error = None
                logger.info(
                    f"Audio engine started: SR={self.sample_rate}Hz, "
                    f"BlockSize={self.block_size} ({round(self.block_size / self.sample_rate * 1000, 2)}ms latency)"
                )
                return True
            except Exception as e:
                self.last_error = str(e)
                self._is_running = False
                self._stream = None
                logger.error(f"Failed to start audio stream: {e}")
                return False

    def stop(self):
        """Stops and cleans up the audio stream."""
        with self._lock:
            self._is_running = False
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception as e:
                    logger.warning(f"Error stopping stream: {e}")
                self._stream = None
            self._active_voices.clear()
            self._pending_voices.clear()
            logger.info("Audio engine stopped.")

    def restart(self, device_index: Optional[int] = None, block_size: Optional[int] = None) -> bool:
        """Safely restarts the stream with new parameters outside time-critical paths."""
        self.stop()
        if device_index is not None:
            self.device_index = device_index
        if block_size is not None:
            self.block_size = block_size
        return self.start()

    def schedule_voice(self, sample_data: np.ndarray, gain: float = 1.0):
        """
        Ultra-fast, non-blocking voice scheduling called from keypress handler.
        Zero file I/O or heavy computation.
        """
        if not self._is_running or self._muted or self._master_gain <= 0.0:
            return

        final_gain = float(gain) * self._master_gain
        voice = ActiveVoice(sample_data, final_gain)
        # Push to pending queue
        self._pending_voices.append(voice)

    def _audio_callback(self, outdata: np.ndarray, frames: int, time_info, status: sd.CallbackFlags):
        """
        Real-time audio callback executed in high-priority audio thread.
        NO locks, NO allocations, NO I/O, NO UI calls.
        """
        self.callback_count += 1
        if status.output_underflow:
            self.latency_tracker.record_underrun()

        # Fast zero out buffer
        outdata.fill(0.0)

        if self._muted or self._master_gain <= 0.0:
            return

        # 1. Drain pending voices into active voice list
        while self._pending_voices:
            new_voice = self._pending_voices.popleft()
            if len(self._active_voices) >= MAX_POLYPHONY:
                # Steal oldest voice to strictly bound polyphony
                self._active_voices.pop(0)
            self._active_voices.append(new_voice)

        if not self._active_voices:
            return

        # 2. Mix active voices into outdata
        surviving_voices: List[ActiveVoice] = []

        for voice in self._active_voices:
            pos = voice.position
            remaining = voice.length - pos
            chunk_len = min(frames, remaining)

            if chunk_len > 0:
                chunk = voice.sample_data[pos : pos + chunk_len]
                outdata[:chunk_len] += chunk * voice.gain
                voice.position += chunk_len

            # Keep voice if it still has samples to play
            if voice.position < voice.length:
                surviving_voices.append(voice)

        self._active_voices = surviving_voices

        # 3. Musical soft-limiter to prevent harsh clipping on rapid typing
        # Fast rational approximation: x / (1 + 0.3 * |x|)
        np.tanh(outdata * 0.95, out=outdata)

        # Update voice count telemetry
        self.latency_tracker.update_audio_state(
            active_voices=len(self._active_voices),
            sample_rate=self.sample_rate,
            block_size=frames
        )
