"""
Unit tests for virtual key-to-character translation and live typing playground.
"""

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

from app.keyboard.key_mapping import (
    keycode_to_char, is_backspace, is_shift, is_caps_lock
)
from app.ui.dashboard import DashboardView
from app.ui.main_window import MainWindow
from app.profiles.profile_manager import ProfileManager
from app.soundpacks.pack_manager import SoundPackManager
from app.audio.latency_metrics import LatencyTracker

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_keycode_mapping_characters():
    assert keycode_to_char(0, is_shift=False, is_caps=False) == "a"
    assert keycode_to_char(0, is_shift=True, is_caps=False) == "A"
    assert keycode_to_char(0, is_shift=False, is_caps=True) == "A"
    assert keycode_to_char(0, is_shift=True, is_caps=True) == "a"  # Shift + Caps returns to lowercase

    # Numbers and symbols
    assert keycode_to_char(18, is_shift=False) == "1"
    assert keycode_to_char(18, is_shift=True) == "!"
    assert keycode_to_char(49) == " "
    assert is_backspace(51) is True
    assert is_shift(56) is True
    assert is_caps_lock(57) is True

def test_virtual_keyboard_click_inserts_text(qapp):
    dash = DashboardView()
    assert hasattr(dash, "typing_edit")
    dash.typing_edit.clear()

    # Click key "A" (keycode 0)
    dash.keyboard_view.key_map[0].click() if hasattr(dash.keyboard_view.key_map[0], "click") else None
    dash._handle_virtual_key_down(0)
    assert dash.typing_edit.toPlainText() == "a"

    # Click space (keycode 49)
    dash._handle_virtual_key_down(49)
    assert dash.typing_edit.toPlainText() == "a "

    # Click key "B" (keycode 11)
    dash._handle_virtual_key_down(11)
    assert dash.typing_edit.toPlainText() == "a b"

def test_virtual_keyboard_caps_and_shift(qapp):
    dash = DashboardView()
    dash.typing_edit.clear()

    # Shift + A -> "A"
    dash._handle_virtual_key_down(56)  # Shift
    assert dash.shift_active is True
    dash._handle_virtual_key_down(0)   # 'A'
    assert dash.typing_edit.toPlainText() == "A"
    assert dash.shift_active is False  # Shift consumed

    # Caps Lock -> "B"
    dash._handle_virtual_key_down(57)  # Caps Lock
    assert dash.caps_lock_active is True
    dash._handle_virtual_key_down(11)  # 'B'
    assert dash.typing_edit.toPlainText() == "AB"

def test_virtual_keyboard_backspace(qapp):
    dash = DashboardView()
    dash.typing_edit.clear()
    dash._handle_virtual_key_down(0)  # Type 'a'
    dash._handle_virtual_key_down(1)  # Type 's'
    assert dash.typing_edit.toPlainText() == "as"

    dash._handle_virtual_key_down(51)  # Backspace deletes 's'
    assert dash.typing_edit.toPlainText() == "a"

    dash._handle_virtual_key_down(51)  # Backspace deletes 'a'
    assert dash.typing_edit.toPlainText() == ""

def test_playground_sample_and_clear_buttons(qapp):
    dash = DashboardView()
    dash._clear_playground_text()
    assert dash.typing_edit.toPlainText() == ""

    dash._load_sample_text()
    assert "The quick brown fox" in dash.typing_edit.toPlainText()

    dash._clear_playground_text()
    assert dash.typing_edit.toPlainText() == ""

def test_playground_text_edit_typing(qapp):
    pm = ProfileManager()
    sm = SoundPackManager()
    lt = LatencyTracker()
    win = MainWindow(pm, sm, lt)
    win.dashboard_view.typing_edit.clear()

    # Typing directly in playground
    ev = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_A, Qt.NoModifier, "a")
    win.dashboard_view.typing_edit.keyPressEvent(ev)
    assert win.dashboard_view.typing_edit.toPlainText() == "a"
