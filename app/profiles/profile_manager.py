"""
Switch profile manager managing profile discovery, manifest parsing, and active selection.
"""

import os
import json
import logging
from typing import Dict, List, Optional
from ..models import SwitchProfile
from .switch_profiles import BUILTIN_PROFILES

logger = logging.getLogger(__name__)

class ProfileManager:
    """Discovers, loads, and maintains switch profiles from assets and user storage."""

    def __init__(self, builtin_assets_dir: Optional[str] = None, user_packs_dir: Optional[str] = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.builtin_assets_dir = builtin_assets_dir or os.path.join(base_dir, "assets", "sounds")
        self.user_packs_dir = user_packs_dir or os.path.expanduser("~/Library/Application Support/ClackLab/soundpacks")
        
        self.profiles: Dict[str, SwitchProfile] = {}
        self.active_profile_id: str = "tactile"
        self.discover_profiles()

    def discover_profiles(self) -> Dict[str, SwitchProfile]:
        """Scans builtin sounds directory and user packs directory for manifests."""
        self.profiles.clear()

        # 1. Scan builtin sound profiles
        if os.path.exists(self.builtin_assets_dir):
            for entry in os.listdir(self.builtin_assets_dir):
                sub_path = os.path.join(self.builtin_assets_dir, entry)
                if os.path.isdir(sub_path):
                    prof = self._load_profile_from_dir(sub_path)
                    if prof:
                        self.profiles[prof.id] = prof

        # 2. Scan user sound packs
        if os.path.exists(self.user_packs_dir):
            for entry in os.listdir(self.user_packs_dir):
                sub_path = os.path.join(self.user_packs_dir, entry)
                if os.path.isdir(sub_path):
                    prof = self._load_profile_from_dir(sub_path)
                    if prof:
                        self.profiles[prof.id] = prof

        logger.info(f"Discovered {len(self.profiles)} switch profiles: {list(self.profiles.keys())}")
        return self.profiles

    def _load_profile_from_dir(self, dir_path: str) -> Optional[SwitchProfile]:
        manifest_path = os.path.join(dir_path, "manifest.json")
        if not os.path.exists(manifest_path):
            # Check for Mechvibes config.json
            config_path = os.path.join(dir_path, "config.json")
            if os.path.exists(config_path):
                return self._convert_mechvibes_config(config_path, dir_path)
            return None

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            prof_id = data.get("id", os.path.basename(dir_path))
            meta = BUILTIN_PROFILES.get(prof_id, {})
            name = data.get("name", meta.get("name", prof_id.capitalize()))
            desc = data.get("description", meta.get("description", "Mechanical switch sound profile."))

            return SwitchProfile(
                id=prof_id,
                name=name,
                description=desc,
                version=data.get("version", "1.0.0"),
                author=data.get("author", "ClackLab"),
                license=data.get("license", "MIT"),
                sample_rate=data.get("sample_rate", 48000),
                channels=data.get("channels", 2),
                down_samples=data.get("down_samples", []),
                up_samples=data.get("up_samples", []),
                special_keys=data.get("special_keys", {}),
                gain=data.get("gain", 1.0),
                press_gain=data.get("press_gain", 1.0),
                release_gain=data.get("release_gain", 0.75),
                directory_path=dir_path
            )
        except Exception as e:
            logger.error(f"Error loading manifest from {dir_path}: {e}")
            return None

    def _convert_mechvibes_config(self, config_path: str, dir_path: str) -> Optional[SwitchProfile]:
        """Auto-converts a Mechvibes config.json pack into a SwitchProfile."""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            prof_id = os.path.basename(dir_path)
            name = data.get("name", prof_id)
            
            # Find WAV/MP3 files in folder
            wavs = [f for f in os.listdir(dir_path) if f.endswith(('.wav', '.mp3', '.ogg'))]
            down_samples = [f for f in wavs if 'generic' in f.lower() or 'key' in f.lower() or 'press' in f.lower()]
            if not down_samples and wavs:
                down_samples = wavs[:5]

            up_samples = [f for f in wavs if 'up' in f.lower() or 'release' in f.lower()]

            special_keys = {}
            for f in wavs:
                fl = f.lower()
                if 'space' in fl:
                    special_keys['space'] = {'down': f, 'up': None}
                elif 'enter' in fl:
                    special_keys['enter'] = {'down': f, 'up': None}
                elif 'back' in fl:
                    special_keys['backspace'] = {'down': f, 'up': None}

            return SwitchProfile(
                id=prof_id,
                name=name,
                description=f"Imported custom pack: {name}",
                down_samples=down_samples,
                up_samples=up_samples,
                special_keys=special_keys,
                directory_path=dir_path
            )
        except Exception as e:
            logger.error(f"Error converting Mechvibes config {config_path}: {e}")
            return None

    def get_profile(self, profile_id: str) -> Optional[SwitchProfile]:
        return self.profiles.get(profile_id)

    def get_active_profile(self) -> SwitchProfile:
        if self.active_profile_id in self.profiles:
            return self.profiles[self.active_profile_id]
        # Fallback to first available
        if self.profiles:
            first_key = next(iter(self.profiles))
            return self.profiles[first_key]
        # Return fallback empty profile
        return SwitchProfile(id="default", name="Default", description="Default Profile")
