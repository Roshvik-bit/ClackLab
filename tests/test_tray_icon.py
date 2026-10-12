"""
Tests for macOS menu bar / taskbar keyboard tray icon and quick access dashboard menu.
"""

import pytest
from PySide6.QtWidgets import QApplication
from app.ui.tray_icon import TrayIconManager, generate_keyboard_icon

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_generate_keyboard_icon(qapp):
    icon = generate_keyboard_icon()
    assert icon is not None
    assert icon.isMask() is True

def test_tray_icon_menu_structure(qapp):
    tray = TrayIconManager()
    assert tray.tray_icon is not None
    assert tray.menu is not None

    # Check essential actions exist
    action_texts = [a.text() for a in tray.menu.actions()]
    assert any("ClackLab" in t for t in action_texts)
    assert any("Enabled" in t for t in action_texts)
    assert any("Open ClackLab" in t for t in action_texts)
    assert any("Quit" in t for t in action_texts)

def test_tray_icon_profile_population_and_selection(qapp):
    tray = TrayIconManager()
    profiles = [("linear", "Cherry MX Black"), ("tactile", "Holy Panda"), ("thocky", "Boba U4T")]
    tray.set_profiles(profiles, active_id="tactile")

    assert "tactile" in tray.profile_actions
    assert tray.profile_actions["tactile"].isChecked() is True
    assert tray.profile_actions["linear"].isChecked() is False

    # Switch active profile
    tray.update_active_profile("thocky")
    assert tray.profile_actions["thocky"].isChecked() is True
    assert tray.profile_actions["tactile"].isChecked() is False

def test_tray_icon_volume_and_enable_sync(qapp):
    tray = TrayIconManager()

    # Toggle enabled
    tray.update_enabled_state(False)
    assert tray.enable_action.isChecked() is False
    assert "Muted" in tray.enable_action.text()

    tray.update_enabled_state(True)
    assert tray.enable_action.isChecked() is True
    assert "Enabled" in tray.enable_action.text()

    # Volume sync
    tray.update_volume(0.50)
    assert tray.volume_actions[50].isChecked() is True
