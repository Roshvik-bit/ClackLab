"""
Main application window with multi-tab navigation, status bar, and local typing preview.
"""

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QStatusBar, QLabel
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent

from .styles import DARK_THEME_QSS, LIGHT_THEME_QSS
from .dashboard import DashboardView
from .switch_library import SwitchLibraryView
from .sound_settings import SoundSettingsView
from .audio_devices_view import AudioDevicesView
from .soundpacks_view import SoundPacksView
from .permissions_view import PermissionsView
from .diagnostics_view import DiagnosticsView

from ..models import KeyCategory, KeyEvent, EventType, LatencyStats
from ..settings import AppSettings
from ..soundpacks.pack_manager import SoundPackManager
from ..profiles.profile_manager import ProfileManager
from ..audio.latency_metrics import LatencyTracker

class MainWindow(QMainWindow):
    """Primary application window for ClackLab."""

    # Internal signals
    local_key_event = Signal(KeyEvent)

    def __init__(
        self,
        profile_manager: ProfileManager,
        pack_manager: SoundPackManager,
        latency_tracker: LatencyTracker,
        parent=None
    ):
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.pack_manager = pack_manager
        self.latency_tracker = latency_tracker

        self.setWindowTitle("ClackLab — Mechanical Keyboard for macOS")
        self.resize(940, 720)
        self.setMinimumSize(880, 640)
        self.force_close = False

        from .tray_icon import get_app_icon
        self.setWindowIcon(get_app_icon())

        self.init_ui()
        self.apply_theme("dark")

    def init_ui(self):
        self.tabs = QTabWidget(self)
        self.tabs.setDocumentMode(True)
        self.setCentralWidget(self.tabs)

        # 1. Dashboard
        self.dashboard_view = DashboardView(self)
        self.tabs.addTab(self.dashboard_view, "Dashboard")

        # 2. Switch Library
        self.switch_library_view = SwitchLibraryView(self)
        self.tabs.addTab(self.switch_library_view, "Switch Library")

        # 3. Sound Settings
        self.sound_settings_view = SoundSettingsView(self)
        self.tabs.addTab(self.sound_settings_view, "Sound Settings")

        # 4. Audio Devices
        self.audio_devices_view = AudioDevicesView(self)
        self.tabs.addTab(self.audio_devices_view, "Audio Devices")

        # 5. Sound Packs
        self.soundpacks_view = SoundPacksView(self.pack_manager, self.profile_manager, self)
        self.tabs.addTab(self.soundpacks_view, "Sound Packs")

        # 6. Permissions & Privacy
        self.permissions_view = PermissionsView(self)
        self.tabs.addTab(self.permissions_view, "Permissions & Privacy")

        # 7. Diagnostics
        self.diagnostics_view = DiagnosticsView(self.latency_tracker, self)
        self.tabs.addTab(self.diagnostics_view, "Diagnostics")

        # Status Bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

        self.sb_engine = QLabel("● Audio Engine: Active", self)
        self.sb_engine.setStyleSheet("color: #34d399; font-weight: 600; margin-left: 10px;")
        self.status_bar.addWidget(self.sb_engine)

        self.sb_profile = QLabel("Switch: Holy Panda", self)
        self.sb_profile.setStyleSheet("color: #818cf8; font-weight: 600; margin-left: 20px;")
        self.status_bar.addWidget(self.sb_profile)

        self.sb_latency = QLabel("Latency: 0.12 ms", self)
        self.sb_latency.setStyleSheet("color: #38bdf8; font-family: Menlo, Monaco, monospace; font-weight: 600; margin-left: 20px;")
        self.status_bar.addPermanentWidget(self.sb_latency)

        # Status bar telemetry timer
        self.sb_timer = QTimer(self)
        self.sb_timer.timeout.connect(self._update_status_bar)
        self.sb_timer.start(250)

    def apply_theme(self, theme: str):
        if theme == "light":
            self.setStyleSheet(LIGHT_THEME_QSS)
        else:
            self.setStyleSheet(DARK_THEME_QSS)

    def update_active_profile_display(self, prof_id: str, prof_name: str):
        self.sb_profile.setText(f"Switch: {prof_name}")
        self.switch_library_view.set_active_profile(prof_id)

    def _update_status_bar(self):
        stats = self.latency_tracker.get_stats()
        self.sb_latency.setText(f"Median: {stats.median_ms} ms | Underruns: {stats.buffer_underruns}")
        self.dashboard_view.update_latency_stats(stats)

    # Local Window Typing Preview Mode
    def keyPressEvent(self, event: QKeyEvent):
        """Allows testing switch sounds when the ClackLab window has focus."""
        if not event.isAutoRepeat():
            keycode = event.nativeScanCode()
            ev = KeyEvent(
                event_type=EventType.KEY_DOWN,
                keycode=keycode,
                category=KeyCategory.STANDARD,
                is_repeat=False
            )
            self.local_key_event.emit(ev)
            self.dashboard_view.keyboard_view.trigger_key(keycode, True)

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        if not event.isAutoRepeat():
            keycode = event.nativeScanCode()
            ev = KeyEvent(
                event_type=EventType.KEY_UP,
                keycode=keycode,
                category=KeyCategory.STANDARD,
                is_repeat=False
            )
            self.local_key_event.emit(ev)
            self.dashboard_view.keyboard_view.trigger_key(keycode, False)
        super().keyReleaseEvent(event)
    def show_and_activate(self):
        """Brings the window to the foreground and unminimizes if hidden."""
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        """Hides to taskbar / system tray on close instead of exiting, so typing sounds continue."""
        if self.force_close:
            event.accept()
        else:
            event.ignore()
            self.hide()
