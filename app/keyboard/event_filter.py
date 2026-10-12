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

# Windows Virtual-Key (VK) codes
VK_SPACE = 32          # 0x20
VK_RETURN = 13         # 0x0D
VK_BACKSPACE = 8       # 0x08

MODIFIER_KEYCODES = {
    # macOS
    54, 55, 56, 57, 58, 59, 60, 61, 62, 63,
    # Windows (Shift, Ctrl, Alt, Caps, Windows keys)
    16, 17, 18, 20, 91, 92, 160, 161, 162, 163, 164, 165
}

ARROW_KEYCODES = {
    # macOS
    123, 124, 125, 126,
    # Windows (Left=37, Up=38, Right=39, Down=40)
    37, 38, 39, 40
}

FUNCTION_KEYCODES = {
    # macOS F1..F12
    122, 120, 99, 118, 96, 97, 98, 100, 101, 109, 103, 111,
    # Windows F1..F12 (112..123)
    112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123
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
        if keycode in (KEYCODE_SPACE, VK_SPACE):
            return KeyCategory.SPACE
        if keycode in (KEYCODE_RETURN, KEYCODE_NUMPAD_ENTER, VK_RETURN):
            return KeyCategory.ENTER
        if keycode in (KEYCODE_BACKSPACE, VK_BACKSPACE):
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
