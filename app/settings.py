"""
Settings management and persistent JSON storage for ClackLab.
"""

import os
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Optional

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS_PATH = os.path.expanduser("~/Library/Application Support/ClackLab/settings.json")

@dataclass
class AppSettings:
    version: int = 1
    enabled: bool = True
    profile_id: str = "tactile"
    master_volume: float = 0.85
    press_volume: float = 1.0
    release_volume: float = 0.70
    play_key_up: bool = True
    randomize_samples: bool = True
    pitch_variation_enabled: bool = True
    pitch_variation_amount: float = 0.025  # +/- 2.5% pitch variation
    play_key_repeats: bool = False
    play_modifiers: bool = True
    play_stabilizers: bool = True
    visual_keyboard_feedback: bool = True
    launch_at_login: bool = True
    theme: str = "dark"
    audio_device_index: Optional[int] = None
    buffer_size: int = 128
    sample_rate: int = 48000
    excluded_keys: List[int] = field(default_factory=list)
    custom_soundpack_dirs: List[str] = field(default_factory=list)

class SettingsManager:
    """Manages loading, saving, and validating application settings."""

    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath or DEFAULT_SETTINGS_PATH
        self.settings: AppSettings = self.load()

    def get_defaults(self) -> AppSettings:
        return AppSettings()

    def load(self) -> AppSettings:
        if not os.path.exists(self.filepath):
            logger.info("Settings file not found, creating default settings.")
            settings = self.get_defaults()
            self.save(settings)
            return settings

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate types and fallback if corrupted
            defaults = asdict(self.get_defaults())
            merged = {}
            for k, default_val in defaults.items():
                if k in data and isinstance(data[k], type(default_val)):
                    merged[k] = data[k]
                else:
                    merged[k] = default_val

            return AppSettings(**merged)
        except Exception as e:
            logger.warning(f"Failed to read settings from {self.filepath}: {e}. Falling back to defaults.")
            return self.get_defaults()

    def save(self, settings: Optional[AppSettings] = None) -> bool:
        if settings is not None:
            self.settings = settings
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(asdict(self.settings), f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save settings to {self.filepath}: {e}")
            return False

    def reset_to_defaults(self) -> AppSettings:
        self.settings = self.get_defaults()
        self.save()
        return self.settings

    def update(self, **kwargs) -> AppSettings:
        for k, v in kwargs.items():
            if hasattr(self.settings, k):
                setattr(self.settings, k, v)
        self.save()
        return self.settings
