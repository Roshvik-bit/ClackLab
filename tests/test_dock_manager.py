"""
Unit tests for macOS Dock visibility management and UI synchronization.
"""

import sys
import pytest
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QApplication

from app.system.dock_manager import DockManager
from app.settings import AppSettings
from app.ui.tray_icon import TrayIconManager
from app.ui.sound_settings import SoundSettingsView

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_dock_manager_query_and_toggle():
    # Test setting dock visible
    success = DockManager.set_dock_visible(True)
    if sys.platform == "darwin":
        assert success is True
        assert DockManager.is_dock_visible() is True

        # Test hiding from dock (accessory mode)
        success_hide = DockManager.set_dock_visible(False)
        assert success_hide is True
        assert DockManager.is_dock_visible() is False

        # Restore
        DockManager.set_dock_visible(False)

def test_tray_icon_dock_action(qapp):
    tray = TrayIconManager()
    assert hasattr(tray, "dock_action")
    assert tray.dock_action.isCheckable() is True
    assert "Show in macOS Dock" in tray.dock_action.text()

    received = []
    tray.dock_icon_toggled.connect(lambda v: received.append(v))

    tray.dock_action.setChecked(True)
    assert True in received

    tray.dock_action.setChecked(False)
    assert False in received

def test_sound_settings_dock_checkbox(qapp):
    view = SoundSettingsView()
    assert hasattr(view, "cb_show_in_dock")
    assert "Show ClackLab Icon in macOS Dock" in view.cb_show_in_dock.text()

    received = []
    view.settings_changed.connect(lambda d: received.append(d))

    view.cb_show_in_dock.setChecked(True)
    assert {"show_in_dock": True} in received

    # Test load_settings
    settings = AppSettings(show_in_dock=False)
    view.load_settings(settings)
    assert view.cb_show_in_dock.isChecked() is False
