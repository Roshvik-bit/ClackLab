"""
Domain models and data definitions for ClackLab.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

class EventType(Enum):
    KEY_DOWN = "key_down"
    KEY_UP = "key_up"
    FLAGS_CHANGED = "flags_changed"

class KeyCategory(Enum):
    STANDARD = "standard"
    SPACE = "space"
    ENTER = "enter"
    BACKSPACE = "backspace"
    MODIFIER = "modifier"
    FUNCTION = "function"
    ARROW = "arrow"
    OTHER = "other"

@dataclass
class KeyEvent:
    event_type: EventType
    keycode: int
    category: KeyCategory
    is_repeat: bool = False
    timestamp_ns: int = 0  # Monotonic time from time.perf_counter_ns()
    process_start_ns: int = 0
    schedule_ns: int = 0
    callback_handoff_ns: int = 0

class ThemeMode(Enum):
    DARK = "dark"
    LIGHT = "light"

@dataclass
class SpecialKeySamples:
    down: Optional[str] = None
    up: Optional[str] = None

@dataclass
class SwitchProfile:
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    author: str = "ClackLab"
    license: str = "MIT"
    sample_rate: int = 48000
    channels: int = 2
    down_samples: List[str] = field(default_factory=list)
    up_samples: List[str] = field(default_factory=list)
    special_keys: Dict[str, Dict[str, Optional[str]]] = field(default_factory=dict)
    gain: float = 1.0
    press_gain: float = 1.0
    release_gain: float = 0.75
    directory_path: str = ""

@dataclass
class LatencyMetricRecord:
    internal_latency_ms: float
    total_handoff_latency_ms: float
    timestamp_ns: int
    is_repeat: bool = False

@dataclass
class LatencyStats:
    count: int = 0
    median_ms: float = 0.0
    p95_ms: float = 0.0
    max_ms: float = 0.0
    last_ms: float = 0.0
    buffer_underruns: int = 0
    active_voices: int = 0
    sample_rate: int = 48000
    block_size: int = 128
