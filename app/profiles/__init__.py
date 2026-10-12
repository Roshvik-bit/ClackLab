"""
Switch profile definitions and profile discovery manager.
"""

from .switch_profiles import BUILTIN_PROFILES
from .profile_manager import ProfileManager

__all__ = [
    "BUILTIN_PROFILES",
    "ProfileManager",
]
