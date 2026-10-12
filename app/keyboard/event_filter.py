"""
macOS keyboard event filter and semantic key classification.
"""

from typing import Set, Optional
from ..models import KeyCategory, KeyEvent, EventType

# macOS virtual keycodes mapping
KEYCODE_SPACE = 49
KEYCODE_RETURN = 36
KEYCODE_NUMPAD_ENTER = 76
KEYCODE_BACKSPACE = 51

MODIFIER_KEYCODES = {
    54,  # Right Command
    55,  # Left Command
    56,  # Left Shift
    57,  # Caps Lock
    58,  # Left Option
    59,  # Left Control
    60,  # Right Shift
    61,  # Right Option
    62,  # Right Control
    63,  # Function (Fn)
}

ARROW_KEYCODES = {
    123,  # Left
    124,  # Right
    125,  # Down
    126,  # Up
}

FUNCTION_KEYCODES = {
    122, 120, 99, 118, 96, 97, 98, 100, 101, 109, 103, 111  # F1..F12
}

class EventFilter:
    """Classifies raw key events, handles repeat suppression, and checks exclusions."""

    def __init__(self):
        self.excluded_keys: Set[int] = set()
        self.allow_repeats: bool = False
        self.allow_modifiers: bool = True
        # In-memory tracking of held keys for repeat detection
        self._pressed_keys: Set[int] = set()

    def update_settings(self, excluded_keys: Optional[list] = None, allow_repeats: bool = False, allow_modifiers: bool = True):
        if excluded_keys is not None:
            self.excluded_keys = set(excluded_keys)
        self.allow_repeats = allow_repeats
        self.allow_modifiers = allow_modifiers

    def classify_keycode(self, keycode: int) -> KeyCategory:
        """Translates virtual keycode into semantic Category."""
        if keycode == KEYCODE_SPACE:
            return KeyCategory.SPACE
        if keycode in (KEYCODE_RETURN, KEYCODE_NUMPAD_ENTER):
            return KeyCategory.ENTER
        if keycode == KEYCODE_BACKSPACE:
            return KeyCategory.BACKSPACE
        if keycode in MODIFIER_KEYCODES:
            return KeyCategory.MODIFIER
        if keycode in ARROW_KEYCODES:
            return KeyCategory.ARROW
        if keycode in FUNCTION_KEYCODES:
            return KeyCategory.FUNCTION
        return KeyCategory.STANDARD

    def filter_event(
        self,
        event_type: EventType,
        keycode: int,
        is_autorepeat: bool = False,
        timestamp_ns: int = 0
    ) -> Optional[KeyEvent]:
        """
        Filters and converts raw key event.
        Returns a KeyEvent if sound should be scheduled, or None if filtered out.
        """
        # Excluded keys check
        if keycode in self.excluded_keys:
            return None

        category = self.classify_keycode(keycode)

        # Modifier sound check
        if category == KeyCategory.MODIFIER and not self.allow_modifiers:
            return None

        # Repeat detection
        is_repeat = is_autorepeat
        if event_type == EventType.KEY_DOWN:
            if keycode in self._pressed_keys:
                is_repeat = True
            else:
                self._pressed_keys.add(keycode)
        elif event_type == EventType.KEY_UP:
            self._pressed_keys.discard(keycode)

        # Repeat filtering
        if is_repeat and not self.allow_repeats:
            return None

        return KeyEvent(
            event_type=event_type,
            keycode=keycode,
            category=category,
            is_repeat=is_repeat,
            timestamp_ns=timestamp_ns
        )

    def reset_state(self):
        self._pressed_keys.clear()
