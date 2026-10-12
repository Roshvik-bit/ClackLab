"""
macOS Menu Bar / Taskbar Keyboard Status Icon and Quick Access Dashboard Menu.
"""

import os
import logging
from typing import Dict, List, Optional
from PySide6.QtWidgets import (
    QSystemTrayIcon, QMenu, QWidget
)
from PySide6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QAction, QActionGroup
)
from PySide6.QtCore import Qt, QRectF, Signal, QObject

logger = logging.getLogger(__name__)

def get_app_icon() -> QIcon:
    """Returns the full-color high-resolution application logo icon."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    logo_path = os.path.join(base_dir, "assets", "logo.png")
    if os.path.exists(logo_path):
        return QIcon(logo_path)
    return generate_keyboard_icon()

def generate_keyboard_icon(size: int = 40) -> QIcon:
    """
    Renders a crisp, high-resolution mechanical keyboard template icon for the macOS menu bar.
    Sets isMask=True so macOS automatically tints it for dark/light menu bars.
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Keyboard body frame
    pen = QPen(QColor(0, 0, 0), 2.5)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.drawRoundedRect(QRectF(4, 9, 32, 22), 5, 5)

    # Keycaps (Row 1)
    painter.setBrush(QBrush(QColor(0, 0, 0)))
    painter.setPen(Qt.NoPen)
    for x in [8, 14, 20, 26]:
        painter.drawRoundedRect(QRectF(x, 13, 3.5, 3), 1, 1)

    # Keycaps (Row 2)
    for x in [8, 14, 20, 26]:
        painter.drawRoundedRect(QRectF(x, 18, 3.5, 3), 1, 1)

    # Spacebar (Bottom Row)
    painter.drawRoundedRect(QRectF(11, 23, 16, 3), 1, 1)
    painter.end()

    icon = QIcon(pixmap)
    icon.setIsMask(True)
    return icon

class TrayIconManager(QObject):
    """
    Manages the macOS taskbar / menu bar keyboard icon and quick access menu.
    Allows instant access to all Dashboard controls from anywhere in macOS.
    """

    master_toggled = Signal(bool)
    profile_selected = Signal(str)
    volume_changed = Signal(float)
    preview_clicked = Signal()
    show_dashboard_requested = Signal()
    launch_at_login_toggled = Signal(bool)
    quit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon = generate_keyboard_icon()
        self.tray_icon = QSystemTrayIcon(self.icon, parent)
        self.tray_icon.setToolTip("ClackLab — Virtual Mechanical Keyboard")

        self.menu = QMenu()
        self.profile_actions: Dict[str, QAction] = {}
        self.profile_action_group = QActionGroup(self.menu)
        self.profile_action_group.setExclusive(True)

        self.volume_actions: Dict[int, QAction] = {}
        self.volume_action_group = QActionGroup(self.menu)
        self.volume_action_group.setExclusive(True)

        self._build_menu()
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.activated.connect(self._on_tray_activated)

    def _build_menu(self):
        self.menu.clear()

        # 1. Title / Header
        self.title_action = QAction("⌨ ClackLab Dashboard", self.menu)
        font = self.title_action.font()
        font.setBold(True)
        self.title_action.setFont(font)
        self.title_action.setEnabled(False)
        self.menu.addAction(self.title_action)

        # Status text action
        self.status_action = QAction("● Audio: Active | Accessibility: Trusted", self.menu)
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)

        self.menu.addSeparator()

        # 2. Master Enable / Disable Toggle
        self.enable_action = QAction("Enabled (Typing Sounds Active)", self.menu)
        self.enable_action.setCheckable(True)
        self.enable_action.setChecked(True)
        self.enable_action.toggled.connect(self.master_toggled.emit)
        self.menu.addAction(self.enable_action)

        self.menu.addSeparator()

        # 3. Active Profile Submenu
        self.profile_submenu = self.menu.addMenu("Switch Profile")
        # (Profiles populated dynamically via set_profiles)

        # 4. Volume Submenu
        self.volume_submenu = self.menu.addMenu("Master Volume")
        for vol_percent in [100, 85, 70, 50, 25, 0]:
            label = f"{vol_percent}%" if vol_percent > 0 else "Mute (0%)"
            act = QAction(label, self.volume_submenu)
            act.setCheckable(True)
            if vol_percent == 85:
                act.setChecked(True)
            self.volume_action_group.addAction(act)
            self.volume_submenu.addAction(act)
            self.volume_actions[vol_percent] = act
            act.triggered.connect(lambda checked=False, vp=vol_percent: self.volume_changed.emit(vp / 100.0))

        # 5. Quick Test Sound
        self.test_action = QAction("▶ Test Keystroke Sound", self.menu)
        self.test_action.triggered.connect(self.preview_clicked.emit)
        self.menu.addAction(self.test_action)

        self.menu.addSeparator()

        # 6. Open Main Window / Dashboard
        self.open_action = QAction("Open ClackLab Window...", self.menu)
        open_font = self.open_action.font()
        open_font.setBold(True)
        self.open_action.setFont(open_font)
        self.open_action.triggered.connect(self.show_dashboard_requested.emit)
        self.menu.addAction(self.open_action)

        # 7. Launch at Login
        self.launch_login_action = QAction("Launch at Login", self.menu)
        self.launch_login_action.setCheckable(True)
        self.launch_login_action.setChecked(True)
        self.launch_login_action.toggled.connect(self.launch_at_login_toggled.emit)
        self.menu.addAction(self.launch_login_action)

        self.menu.addSeparator()

        # 8. Quit
        self.quit_action = QAction("Quit ClackLab", self.menu)
        self.quit_action.triggered.connect(self.quit_requested.emit)
        self.menu.addAction(self.quit_action)

    def set_profiles(self, profiles: List[tuple[str, str]], active_id: str):
        """Populates the Switch Profile submenu with radio-selectable actions."""
        self.profile_submenu.clear()
        self.profile_actions.clear()

        for prof_id, prof_name in profiles:
            act = QAction(prof_name, self.profile_submenu)
            act.setCheckable(True)
            if prof_id == active_id:
                act.setChecked(True)
            self.profile_action_group.addAction(act)
            self.profile_submenu.addAction(act)
            self.profile_actions[prof_id] = act
            act.triggered.connect(lambda checked=False, pid=prof_id: self.profile_selected.emit(pid))

    def update_active_profile(self, active_id: str):
        if active_id in self.profile_actions:
            self.profile_actions[active_id].setChecked(True)

    def update_volume(self, vol: float):
        percent = int(round(vol * 100))
        # Find closest match
        closest = min(self.volume_actions.keys(), key=lambda v: abs(v - percent))
        if closest in self.volume_actions:
            self.volume_actions[closest].setChecked(True)

    def update_enabled_state(self, enabled: bool):
        self.enable_action.blockSignals(True)
        self.enable_action.setChecked(enabled)
        self.enable_action.setText("Enabled (Typing Sounds Active)" if enabled else "Muted (Sounds Disabled)")
        self.enable_action.blockSignals(False)

    def update_launch_at_login(self, enabled: bool):
        self.launch_login_action.blockSignals(True)
        self.launch_login_action.setChecked(enabled)
        self.launch_login_action.blockSignals(False)

    def update_status(self, engine_active: bool, perm_trusted: bool, active_prof_name: str = ""):
        eng_txt = "Active" if engine_active else "Stopped"
        perm_txt = "Trusted" if perm_trusted else "Needs Perm"
        prof_txt = f" [{active_prof_name}]" if active_prof_name else ""
        self.status_action.setText(f"● Audio: {eng_txt} | Access: {perm_txt}{prof_txt}")

    def show(self):
        self.tray_icon.show()

    def hide(self):
        self.tray_icon.hide()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        # On single left-click, activate/show the main window dashboard
        if reason == QSystemTrayIcon.Trigger:
            self.show_dashboard_requested.emit()
