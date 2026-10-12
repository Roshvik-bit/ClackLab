"""
Audio device enumeration and output device discovery for macOS.
"""

import logging
from typing import List, Dict, Optional, Any
import sounddevice as sd

logger = logging.getLogger(__name__)

class AudioDeviceManager:
    """Discovers and queries macOS output audio devices."""

    @staticmethod
    def get_output_devices() -> List[Dict[str, Any]]:
        devices = []
        try:
            device_list = sd.query_devices()
            default_out = sd.default.device[1]

            for idx, dev in enumerate(device_list):
                if dev['max_output_channels'] > 0:
                    devices.append({
                        'index': idx,
                        'name': dev['name'],
                        'channels': dev['max_output_channels'],
                        'default_samplerate': int(dev['default_samplerate']),
                        'is_default': (idx == default_out),
                        'hostapi': dev.get('hostapi', 0)
                    })
        except Exception as e:
            logger.error(f"Error querying audio devices: {e}")
        return devices

    @staticmethod
    def get_default_output_device() -> Optional[Dict[str, Any]]:
        devices = AudioDeviceManager.get_output_devices()
        for dev in devices:
            if dev['is_default']:
                return dev
        return devices[0] if devices else None

    @staticmethod
    def is_device_valid(device_index: Optional[int]) -> bool:
        if device_index is None:
            return True
        devices = AudioDeviceManager.get_output_devices()
        return any(d['index'] == device_index for d in devices)
