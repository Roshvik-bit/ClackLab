"""
Preloaded in-memory sample library with anti-repetition memory and pitch randomization.
"""

import os
import json
import random
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
import soundfile as sf
from ..models import KeyCategory, SwitchProfile

logger = logging.getLogger(__name__)

class PreloadedSample:
    """Preloaded audio array in 32-bit float stereo format."""
    def __init__(self, name: str, data: np.ndarray, sample_rate: int = 48000):
        self.name = name
        # Ensure 2D (samples, 2)
        if data.ndim == 1:
            self.data = np.column_stack([data, data]).astype(np.float32)
        else:
            self.data = data.astype(np.float32)
        self.sample_rate = sample_rate
        self.length_frames = len(self.data)

class SampleLibrary:
    """
    In-memory sound sample repository for ultra-low latency playback.
    Preloads all profile samples into RAM to eliminate disk I/O on keypress.
    """

    def __init__(self, target_sample_rate: int = 48000):
        self.target_sample_rate = target_sample_rate
        self.active_profile: Optional[SwitchProfile] = None
        
        # Audio sample pools
        self._standard_down: List[PreloadedSample] = []
        self._standard_up: List[PreloadedSample] = []
        self._special_down: Dict[str, PreloadedSample] = {}
        self._special_up: Dict[str, PreloadedSample] = {}

        # Anti-repetition state
        self._last_down_index: int = -1
        self._last_up_index: int = -1

    def load_profile(self, profile: SwitchProfile) -> bool:
        """Loads all samples for a profile into memory."""
        self.active_profile = profile
        self._standard_down.clear()
        self._standard_up.clear()
        self._special_down.clear()
        self._special_up.clear()
        self._last_down_index = -1
        self._last_up_index = -1

        dir_path = profile.directory_path
        if not os.path.exists(dir_path):
            logger.error(f"Profile directory does not exist: {dir_path}")
            return False

        # Load standard down samples
        for s_name in profile.down_samples:
            s_path = os.path.join(dir_path, s_name)
            loaded = self._read_audio_file(s_path, s_name)
            if loaded:
                self._standard_down.append(loaded)

        # Load standard up samples
        for s_name in profile.up_samples:
            s_path = os.path.join(dir_path, s_name)
            loaded = self._read_audio_file(s_path, s_name)
            if loaded:
                self._standard_up.append(loaded)

        # Load special keys
        for key_type, key_files in profile.special_keys.items():
            down_file = key_files.get("down")
            if down_file:
                loaded = self._read_audio_file(os.path.join(dir_path, down_file), down_file)
                if loaded:
                    self._special_down[key_type] = loaded
            
            up_file = key_files.get("up")
            if up_file:
                loaded = self._read_audio_file(os.path.join(dir_path, up_file), up_file)
                if loaded:
                    self._special_up[key_type] = loaded

        logger.info(
            f"Loaded profile '{profile.name}': {len(self._standard_down)} down, "
            f"{len(self._standard_up)} up, {len(self._special_down)} special down samples."
        )
        return len(self._standard_down) > 0

    def _read_audio_file(self, filepath: str, name: str) -> Optional[PreloadedSample]:
        if not os.path.exists(filepath):
            logger.warning(f"Audio file not found: {filepath}")
            return None
        try:
            data, sr = sf.read(filepath, dtype='float32')
            # Resample if needed
            if sr != self.target_sample_rate:
                num_samples = int(len(data) * self.target_sample_rate / sr)
                if data.ndim == 1:
                    indices = np.linspace(0, len(data) - 1, num_samples)
                    data = np.interp(indices, np.arange(len(data)), data).astype(np.float32)
                else:
                    new_channels = []
                    indices = np.linspace(0, len(data) - 1, num_samples)
                    orig_indices = np.arange(len(data))
                    for ch in range(data.shape[1]):
                        new_channels.append(np.interp(indices, orig_indices, data[:, ch]))
                    data = np.column_stack(new_channels).astype(np.float32)
                sr = self.target_sample_rate
            return PreloadedSample(name, data, sr)
        except Exception as e:
            logger.error(f"Failed to read audio file {filepath}: {e}")
            return None

    def get_sample(
        self,
        category: KeyCategory,
        is_down: bool,
        randomize: bool = True,
        play_stabilizers: bool = True
    ) -> Optional[PreloadedSample]:
        """
        Retrieves the appropriate preloaded sample for the given key category.
        Applies anti-repetition selection for standard keys.
        """
        # 1. Check special keys (space, enter, backspace)
        if play_stabilizers:
            key_tag = None
            if category == KeyCategory.SPACE:
                key_tag = "space"
            elif category == KeyCategory.ENTER:
                key_tag = "enter"
            elif category == KeyCategory.BACKSPACE:
                key_tag = "backspace"

            if key_tag:
                pool = self._special_down if is_down else self._special_up
                if key_tag in pool:
                    return pool[key_tag]

        # 2. Key-up playback
        if not is_down:
            if not self._standard_up:
                return None
            if len(self._standard_up) == 1 or not randomize:
                return self._standard_up[0]
            
            # Anti-repetition selection
            idx = random.randrange(len(self._standard_up))
            if idx == self._last_up_index and len(self._standard_up) > 1:
                idx = (idx + 1) % len(self._standard_up)
            self._last_up_index = idx
            return self._standard_up[idx]

        # 3. Key-down playback
        if not self._standard_down:
            return None
        if len(self._standard_down) == 1 or not randomize:
            return self._standard_down[0]

        # Anti-repetition selection
        idx = random.randrange(len(self._standard_down))
        if idx == self._last_down_index and len(self._standard_down) > 1:
            idx = (idx + 1) % len(self._standard_down)
        self._last_down_index = idx
        return self._standard_down[idx]

    @staticmethod
    def apply_pitch_variation(audio_data: np.ndarray, pitch_factor: float) -> np.ndarray:
        """
        Applies subtle pitch variation factor (e.g. 0.98 to 1.02) using fast linear resampling.
        """
        if abs(pitch_factor - 1.0) < 0.002:
            return audio_data
        
        orig_len = len(audio_data)
        new_len = int(orig_len / pitch_factor)
        if new_len < 4:
            return audio_data

        indices = np.linspace(0, orig_len - 1, new_len)
        orig_indices = np.arange(orig_len)

        if audio_data.ndim == 1:
            return np.interp(indices, orig_indices, audio_data).astype(np.float32)
        else:
            left = np.interp(indices, orig_indices, audio_data[:, 0])
            right = np.interp(indices, orig_indices, audio_data[:, 1])
            return np.column_stack([left, right]).astype(np.float32)
