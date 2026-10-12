"""
Sound pack validator verifying manifest schema, file presence, audio headers, and duration.
"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any
import soundfile as sf

logger = logging.getLogger(__name__)

SUPPORTED_AUDIO_EXTENSIONS = ('.wav', '.mp3', '.ogg', '.flac')
MAX_SAMPLE_DURATION_SEC = 5.0  # Keystroke sounds shouldn't exceed 5 seconds

@dataclass
class ValidationReport:
    is_valid: bool
    pack_name: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sample_count: int = 0
    sample_rate: int = 0
    channels: int = 0

class SoundPackValidator:
    """Validates structural and acoustic integrity of mechanical keyboard sound packs."""

    @staticmethod
    def validate_directory(dir_path: str) -> ValidationReport:
        report = ValidationReport(is_valid=True)

        if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
            report.is_valid = False
            report.errors.append(f"Directory does not exist: {dir_path}")
            return report

        manifest_path = os.path.join(dir_path, "manifest.json")
        mechvibes_path = os.path.join(dir_path, "config.json")

        if os.path.exists(manifest_path):
            return SoundPackValidator._validate_native_manifest(manifest_path, dir_path)
        elif os.path.exists(mechvibes_path):
            return SoundPackValidator._validate_mechvibes_config(mechvibes_path, dir_path)
        else:
            # Check if there are loose audio files
            audio_files = [f for f in os.listdir(dir_path) if f.lower().endswith(SUPPORTED_AUDIO_EXTENSIONS)]
            if audio_files:
                report.warnings.append("No manifest.json or config.json found; directory contains raw audio files.")
                report.pack_name = os.path.basename(dir_path)
                report.sample_count = len(audio_files)
                return report
            else:
                report.is_valid = False
                report.errors.append("No manifest.json, config.json, or supported audio files found.")
                return report

    @staticmethod
    def _validate_native_manifest(manifest_path: str, dir_path: str) -> ValidationReport:
        report = ValidationReport(is_valid=True)
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            report.is_valid = False
            report.errors.append(f"Invalid JSON in manifest.json: {e}")
            return report

        report.pack_name = data.get("name", os.path.basename(dir_path))

        # Check required fields
        down_samples = data.get("down_samples", [])
        if not down_samples:
            report.is_valid = False
            report.errors.append("Manifest specifies no down_samples.")

        # Validate audio files
        all_samples = list(down_samples) + list(data.get("up_samples", []))
        for key, key_files in data.get("special_keys", {}).items():
            if isinstance(key_files, dict):
                if key_files.get("down"):
                    all_samples.append(key_files["down"])
                if key_files.get("up"):
                    all_samples.append(key_files["up"])

        report.sample_count = len(all_samples)
        for s_name in all_samples:
            s_path = os.path.join(dir_path, s_name)
            if not os.path.exists(s_path):
                report.is_valid = False
                report.errors.append(f"Referenced sample not found: {s_name}")
                continue

            try:
                info = sf.info(s_path)
                report.sample_rate = info.samplerate
                report.channels = info.channels
                if info.duration > MAX_SAMPLE_DURATION_SEC:
                    report.warnings.append(f"Sample {s_name} is unusually long ({round(info.duration, 2)}s).")
            except Exception as e:
                report.is_valid = False
                report.errors.append(f"Audio file is unreadable or corrupt: {s_name} ({e})")

        return report

    @staticmethod
    def _validate_mechvibes_config(config_path: str, dir_path: str) -> ValidationReport:
        report = ValidationReport(is_valid=True)
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            report.is_valid = False
            report.errors.append(f"Invalid JSON in config.json: {e}")
            return report

        report.pack_name = data.get("name", os.path.basename(dir_path))
        audio_files = [f for f in os.listdir(dir_path) if f.lower().endswith(SUPPORTED_AUDIO_EXTENSIONS)]
        report.sample_count = len(audio_files)

        if not audio_files:
            report.is_valid = False
            report.errors.append("No audio files found in Mechvibes sound pack folder.")

        return report
