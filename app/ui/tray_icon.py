"""
macOS Menu Bar / Taskbar Keyboard Status Icon and Quick Access Dashboard Menu.
Reflects live background runtime health, accessibility authorization, and lifecycle controls.
"""

import os
import logging
from typing import Dict, List, Optional
from PySide6.QtWidgets import (
    QSystemTrayIcon, QMenu, QWidget
)
from PySide6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QAction, QActionGroup, QFont
)
from PySide6.QtCore import Qt, QRectF, Signal, QObject

from ..models import RuntimeState

logger = logging.getLogger(__name__)

def get_app_icon() -> QIcon:
    """Returns the full-color high-resolution application logo icon."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    logo_path = os.path.join(base_dir, "assets", "logo.png")
    if os.path.exists(logo_path):
        return QIcon(logo_path)
    return generate_keyboard_icon()

def generate_keyboard_icon(state: RuntimeState = RuntimeState.RUNNING, size: int = 40) -> QIcon:
    """
    Renders a crisp, high-resolution mechanical keyboard icon for the macOS menu bar.
    Dynamically decorates badges for RUNNING, PAUSED, DEGRADED, and STOPPED states.
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    is_dimmed = (state in (RuntimeState.STOPPED, RuntimeState.FAILED, RuntimeState.NOT_STARTED))
    stroke_color = QColor(120, 120, 120) if is_dimmed else QColor(0, 0, 0)

    # Keyboard body frame
    pen = QPen(stroke_color, 2.5)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.drawRoundedRect(QRectF(4, 9, 32, 22), 5, 5)

    # Keycaps
    painter.setBrush(QBrush(stroke_color))
    painter.setPen(Qt.NoPen)
    for x in [8, 14, 20, 26]:
        painter.drawRoundedRect(QRectF(x, 13, 3.5, 3), 1, 1)
    for x in [8, 14, 20, 26]:
        painter.drawRoundedRect(QRectF(x, 18, 3.5, 3), 1, 1)
    # Spacebar
    painter.drawRoundedRect(QRectF(11, 23, 16, 3), 1, 1)

    # State badges
    if state == RuntimeState.PAUSED:
        # Pause badge bars (bottom-right)
        painter.setBrush(QBrush(QColor(234, 88, 12)))
        painter.drawRoundedRect(QRectF(25, 20, 3, 9), 1, 1)
        painter.drawRoundedRect(QRectF(30, 20, 3, 9), 1, 1)
    elif state == RuntimeState.DEGRADED:
        # Warning badge circle with '!'
        painter.setBrush(QBrush(QColor(217, 119, 6)))
        painter.drawEllipse(QRectF(24, 18, 13, 13))
        painter.setPen(QPen(QColor(255, 255, 255), 1.5))
        painter.drawLine(30, 21, 30, 26)
        painter.drawPoint(30, 28)
    elif state in (RuntimeState.STOPPED, RuntimeState.FAILED):
        # Slash across bottom right
        painter.setPen(QPen(QColor(239, 68, 68), 2.5))
        painter.drawLine(24, 28, 35, 19)

    painter.end()

    icon = QIcon(pixmap)
    if state == RuntimeState.RUNNING:
        icon.setIsMask(True)
    return icon


class TrayIconManager(QObject):
    """
    Manages the macOS menu bar status item and quick-access dashboard menu.
    Allows inspection, control, and background persistence from anywhere in macOS.
    """

    show_dashboard_requested = Signal()
    open_settings_requested = Signal()
    open_diagnostics_requested = Signal()
    open_permissions_requested = Signal()
    pause_resume_toggled = Signal(bool)  # True = resume, False = pause
    stop_runtime_requested = Signal()
    start_runtime_requested = Signal()
    profile_selected = Signal(str)
    volume_changed = Signal(float)
    preview_clicked = Signal()
    launch_at_login_toggled = Signal(bool)
    dock_icon_toggled = Signal(bool)
    quit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_state = RuntimeState.RUNNING
        self.icon = generate_keyboard_icon(RuntimeState.RUNNING)
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

        # 1. Header / Runtime Status Action
        self.title_action = QAction("⌨ ClackLab", self.menu)
        font = self.title_action.font()
        font.setBold(True)
        self.title_action.setFont(font)
        self.title_action.setEnabled(False)
        self.menu.addAction(self.title_action)

        self.status_action = QAction("● Runtime: Running (Active)", self.menu)
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)

        # Warning action for missing permissions
        self.perm_warning_action = QAction("⚠️ macOS Accessibility Permission Required...", self.menu)
        self.perm_warning_action.setVisible(False)
        self.perm_warning_action.triggered.connect(self.open_permissions_requested.emit)
        self.menu.addAction(self.perm_warning_action)

        self.menu.addSeparator()

        # 2. Open ClackLab Window
        self.open_action = QAction("Open ClackLab Window...", self.menu)
        open_font = self.open_action.font()
        open_font.setBold(True)
        self.open_action.setFont(open_font)
        self.open_action.triggered.connect(self.show_dashboard_requested.emit)
        self.menu.addAction(self.open_action)

        self.menu.addSeparator()

        # 3. Pause / Resume Sounds
        self.pause_resume_action = QAction("Pause Background Sounds (Enabled)", self.menu)
        self.pause_resume_action.setCheckable(True)
        self.pause_resume_action.setChecked(True)
        self.pause_resume_action.triggered.connect(self._on_pause_resume_clicked)
        self.enable_action = self.pause_resume_action
        self.menu.addAction(self.pause_resume_action)

        # 4. Active Profile Submenu
        self.profile_submenu = self.menu.addMenu("Switch Profile")

        # 5. Volume Submenu
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

        # 6. Test Keystroke Sound
        self.test_action = QAction("▶ Test Keystroke Sound", self.menu)
        self.test_action.triggered.connect(self.preview_clicked.emit)
        self.menu.addAction(self.test_action)

        self.menu.addSeparator()

        # 7. Open Settings & Diagnostics
        self.settings_action = QAction("Settings...", self.menu)
        self.settings_action.triggered.connect(self.open_settings_requested.emit)
        self.menu.addAction(self.settings_action)

        self.diagnostics_action = QAction("Diagnostics & Logs...", self.menu)
        self.diagnostics_action.triggered.connect(self.open_diagnostics_requested.emit)
        self.menu.addAction(self.diagnostics_action)

        # 8. Launch at Login
        self.launch_login_action = QAction("Launch at Login", self.menu)
        self.launch_login_action.setCheckable(True)
        self.launch_login_action.setChecked(True)
        self.launch_login_action.toggled.connect(self.launch_at_login_toggled.emit)
        self.menu.addAction(self.launch_login_action)

        # 9. Show in macOS Dock
        self.dock_action = QAction("Show in macOS Dock", self.menu)
        self.dock_action.setCheckable(True)
        self.dock_action.setChecked(False)
        self.dock_action.toggled.connect(self.dock_icon_toggled.emit)
        self.menu.addAction(self.dock_action)

        self.menu.addSeparator()

        # 10. Stop / Start Runtime Action
        self.runtime_toggle_action = QAction("Stop Background Runtime", self.menu)
        self.runtime_toggle_action.triggered.connect(self._on_runtime_toggle_clicked)
        self.menu.addAction(self.runtime_toggle_action)

        # 11. Quit ClackLab Completely
        self.quit_action = QAction("Quit ClackLab Completely", self.menu)
        self.quit_action.triggered.connect(self.quit_requested.emit)
        self.menu.addAction(self.quit_action)

    def set_profiles(self, profiles: List[tuple[str, str]], active_id: str):
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
        closest = min(self.volume_actions.keys(), key=lambda v: abs(v - percent))
        if closest in self.volume_actions:
            self.volume_actions[closest].setChecked(True)

    def update_runtime_health(self, health: dict):
        """Synchronizes tray menu items and icon with the authoritative runtime health."""
        state = health.get("state", RuntimeState.RUNNING)
        self.current_state = state
        self.icon = generate_keyboard_icon(state)
        self.tray_icon.setIcon(self.icon)

        prof_name = health.get("active_profile_name", "")
        trusted = health.get("accessibility_trusted", True)
        is_muted = health.get("is_muted", False)

        # Tooltip
        tooltip_state = state.value.capitalize()
        self.tray_icon.setToolTip(f"ClackLab — {tooltip_state} ({prof_name})")

        # Status action text
        if state == RuntimeState.RUNNING:
            self.status_action.setText(f"● Status: Running ({prof_name})")
            self.pause_resume_action.setText("Pause Background Sounds")
            self.pause_resume_action.setEnabled(True)
            self.runtime_toggle_action.setText("Stop Background Runtime")
            self.perm_warning_action.setVisible(False)
        elif state == RuntimeState.DEGRADED:
            self.status_action.setText("⚠️ Status: Degraded (Permissions Needed)")
            self.pause_resume_action.setText("Pause Background Sounds")
            self.pause_resume_action.setEnabled(True)
            self.runtime_toggle_action.setText("Stop Background Runtime")
            self.perm_warning_action.setVisible(True)
        elif state == RuntimeState.PAUSED:
            self.status_action.setText("⏸ Status: Paused (Muted)")
            self.pause_resume_action.setText("Resume Background Sounds")
            self.pause_resume_action.setEnabled(True)
            self.runtime_toggle_action.setText("Stop Background Runtime")
            self.perm_warning_action.setVisible(not trusted)
        elif state in (RuntimeState.STOPPED, RuntimeState.FAILED):
            self.status_action.setText(f"⏹ Status: {state.value.capitalize()}")
            self.pause_resume_action.setEnabled(False)
            self.runtime_toggle_action.setText("Start Background Runtime")
            self.perm_warning_action.setVisible(not trusted)

    def update_launch_at_login(self, enabled: bool):
        self.launch_login_action.blockSignals(True)
        self.launch_login_action.setChecked(enabled)
        self.launch_login_action.blockSignals(False)

    def update_dock_visibility(self, visible: bool):
        self.dock_action.blockSignals(True)
        self.dock_action.setChecked(visible)
        self.dock_action.blockSignals(False)

    def update_enabled_state(self, enabled: bool):
        self.pause_resume_action.blockSignals(True)
        self.pause_resume_action.setChecked(enabled)
        self.pause_resume_action.setText("Pause Background Sounds (Enabled)" if enabled else "Resume Background Sounds (Muted)")
        self.pause_resume_action.blockSignals(False)

    def _on_pause_resume_clicked(self):
        is_paused = (self.current_state == RuntimeState.PAUSED)
        self.pause_resume_toggled.emit(is_paused)

    def _on_runtime_toggle_clicked(self):
        if self.current_state in (RuntimeState.STOPPED, RuntimeState.FAILED):
            self.start_runtime_requested.emit()
        else:
            self.stop_runtime_requested.emit()

    def show(self):
        self.tray_icon.show()

    def hide(self):
        self.tray_icon.hide()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_dashboard_requested.emit()
