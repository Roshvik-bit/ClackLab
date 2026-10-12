"""
Unit tests for macOS Launch at Login system integration and UI synchronization.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QApplication

from app.system.login_item import LoginItemManager
from app.settings import AppSettings, SettingsManager
from app.ui.tray_icon import TrayIconManager
from app.ui.dashboard import DashboardView
from app.ui.sound_settings import SoundSettingsView

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_login_item_bundle_path_detection():
    bundle_path = LoginItemManager.get_app_bundle_path()
    assert bundle_path is not None
    assert bundle_path.endswith(".app")
    assert os.path.exists(bundle_path)

def test_login_item_query_and_toggle():
    # Test enable
    enabled_success = LoginItemManager.enable_launch_at_login()
    assert enabled_success is True
    assert LoginItemManager.is_launch_at_login_enabled() is True

    # Test disable
    disabled_success = LoginItemManager.disable_launch_at_login()
    assert disabled_success is True
    assert LoginItemManager.is_launch_at_login_enabled() is False

    # Test convenience setter
    LoginItemManager.set_launch_at_login(True)
    assert LoginItemManager.is_launch_at_login_enabled() is True

def test_tray_launch_at_login_action(qapp):
    tray = TrayIconManager()
    assert hasattr(tray, "launch_login_action")
    assert tray.launch_login_action.isCheckable() is True
    assert "Launch at Login" in tray.launch_login_action.text()

    received_signals = []
    tray.launch_at_login_toggled.connect(lambda val: received_signals.append(val))

    # Trigger action toggle
    tray.launch_login_action.setChecked(False)
    assert False in received_signals

    tray.launch_login_action.setChecked(True)
    assert True in received_signals

    # Test update_launch_at_login does not re-emit signals
    del received_signals[:]
    tray.update_launch_at_login(False)
    assert tray.launch_login_action.isChecked() is False
    assert len(received_signals) == 0

def test_dashboard_launch_at_login_pill(qapp):
    dash = DashboardView()
    assert hasattr(dash, "login_pill")
    assert "Launch at Login" in dash.login_pill.text()

    received_signals = []
    dash.launch_at_login_toggled.connect(lambda val: received_signals.append(val))

    # Click pill to toggle
    dash.login_pill.click()
    assert len(received_signals) == 1
    assert received_signals[0] is False
    assert "Disabled" in dash.login_pill.text()

    dash.login_pill.click()
    assert len(received_signals) == 2
    assert received_signals[1] is True
    assert "Enabled" in dash.login_pill.text()

def test_sound_settings_launch_at_login(qapp):
    view = SoundSettingsView()
    assert hasattr(view, "cb_launch_login")
    assert "Launch ClackLab Automatically" in view.cb_launch_login.text()

    received = []
    view.settings_changed.connect(lambda d: received.append(d))

    view.cb_launch_login.setChecked(False)
    assert len(received) == 1
    assert received[0] == {"launch_at_login": False}

    settings = AppSettings(launch_at_login=True)
    view.load_settings(settings)
    assert view.cb_launch_login.isChecked() is True

def test_settings_launch_at_login_field():
    s = AppSettings()
    assert hasattr(s, "launch_at_login")
    assert s.launch_at_login is True
