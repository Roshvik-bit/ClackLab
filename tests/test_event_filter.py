"""
Tests for keyboard event filtering, semantic classification, repeat suppression, and exclusion.
"""

import pytest
from app.keyboard.event_filter import EventFilter
from app.models import KeyCategory, EventType

def test_classify_keycodes():
    filter_ = EventFilter()

    # Space
    assert filter_.classify_keycode(49) == KeyCategory.SPACE
    # Return
    assert filter_.classify_keycode(36) == KeyCategory.ENTER
    # Backspace
    assert filter_.classify_keycode(51) == KeyCategory.BACKSPACE
    # Modifiers
    assert filter_.classify_keycode(56) == KeyCategory.MODIFIER  # Left Shift
    assert filter_.classify_keycode(55) == KeyCategory.MODIFIER  # Left Command
    assert filter_.classify_keycode(58) == KeyCategory.MODIFIER  # Left Option
    # Arrows
    assert filter_.classify_keycode(123) == KeyCategory.ARROW   # Left Arrow
    # Function
    assert filter_.classify_keycode(122) == KeyCategory.FUNCTION  # F1
    # Standard alpha keys
    assert filter_.classify_keycode(0) == KeyCategory.STANDARD    # 'A'
    assert filter_.classify_keycode(12) == KeyCategory.STANDARD   # 'Q'

def test_repeat_suppression():
    filter_ = EventFilter()
    filter_.update_settings(allow_repeats=False)

    # First press of 'A' (keycode 0)
    ev1 = filter_.filter_event(EventType.KEY_DOWN, keycode=0, is_autorepeat=False)
    assert ev1 is not None
    assert ev1.is_repeat is False

    # Second press without release (holding key)
    ev2 = filter_.filter_event(EventType.KEY_DOWN, keycode=0, is_autorepeat=True)
    assert ev2 is None  # Suppressed!

    # Key up
    ev_up = filter_.filter_event(EventType.KEY_UP, keycode=0)
    assert ev_up is not None

    # Press again after release
    ev3 = filter_.filter_event(EventType.KEY_DOWN, keycode=0, is_autorepeat=False)
    assert ev3 is not None
    assert ev3.is_repeat is False

def test_excluded_keys():
    filter_ = EventFilter()
    filter_.update_settings(excluded_keys=[53])  # Exclude Escape (53)

    ev_esc = filter_.filter_event(EventType.KEY_DOWN, keycode=53)
    assert ev_esc is None

    ev_other = filter_.filter_event(EventType.KEY_DOWN, keycode=12)
    assert ev_other is not None
