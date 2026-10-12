"""
Switch profile definitions and metadata constants for ClackLab.
"""

from typing import Dict, List
from ..models import SwitchProfile

BUILTIN_PROFILES: Dict[str, Dict[str, str]] = {
    "tactile": {
        "name": "Holy Panda (Tactile)",
        "tag": "Tactile Bump",
        "description": "Legendary tactile switch featuring a prominent, rounded bump and a snappy, satisfying clack."
    },
    "linear": {
        "name": "Cherry MX Black (Linear)",
        "tag": "Smooth Linear",
        "description": "Consistent, uninterrupted key travel with a solid, crisp bottom-out sound."
    },
    "clicky": {
        "name": "Cherry MX Blue (Clicky)",
        "tag": "Click Leaf Snap",
        "description": "Crisp metallic click-leaf actuation with high-frequency tactile response."
    },
    "silent": {
        "name": "Cherry MX Silent (Dampened)",
        "tag": "Silicone Muted",
        "description": "Internal silicone dampening pads cushion the bottom-out and top-out for office-friendly quiet typing."
    },
    "thocky": {
        "name": "Boba U4T (Thocky)",
        "tag": "Deep Thock",
        "description": "Low-frequency body resonance and thick PBT bottom-out acoustic response."
    },
    "creamy": {
        "name": "NovelKeys Cream (Creamy)",
        "tag": "Marbly Cream",
        "description": "Silky-smooth POM travel delivering a distinct rounded, marbly mechanical clack."
    }
}
