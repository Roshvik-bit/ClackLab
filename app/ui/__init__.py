"""
Desktop UI components and views for ClackLab.
"""

from .main_window import MainWindow
from .tray_icon import TrayIconManager, generate_keyboard_icon, get_app_icon

__all__ = [
    "MainWindow",
    "TrayIconManager",
    "generate_keyboard_icon",
    "get_app_icon",
]
