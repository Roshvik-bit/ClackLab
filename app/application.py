"""
Application coordinator wiring together the decoupled BackgroundRuntime,
single-instance IPC, persistent settings, system tray icon, and UI views.
"""

import time
import logging
from PySide6.QtCore import QObject, Signal, QTimer, QEvent, Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon
from PySide6.QtGui import QKeySequence, QShortcut

from .models import KeyCategory, KeyEvent, EventType, RuntimeState
from .settings import SettingsManager, AppSettings
from .runtime.background_runtime import BackgroundRuntime
from .soundpacks.pack_manager import SoundPackManager
from .ui.main_window import MainWindow
from .ui.tray_icon import TrayIconManager
from .system.login_item import LoginItemManager
from .system.dock_manager import DockManager
from .system.single_instance import SingleInstanceController
from .system.diagnostics_logger import DiagnosticsLogger
from .audio.audio_devices import AudioDeviceManager
from .keyboard.permission_manager import PermissionManager

logger = logging.getLogger(__name__)


class ApplicationEventFilter(QObject):
    """Intercepts application-level quit events to enforce background persistence."""

    def __init__(self, app_coordinator, parent=None):
        super().__init__(parent)
        self.coordinator = app_coordinator

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Quit:
            if not self.coordinator.is_explicit_quit:
                if self.coordinator.settings.run_in_background:
                    logger.info("Intercepted QEvent.Quit: preserving background runtime and hiding window.")
                    self.coordinator.main_window.hide()
                    event.ignore()
                    return True  # Filtered out; do not terminate process
        return super().eventFilter(watched, event)


class ClackApplication:
    """Master application coordinator managing the lifecycle of ClackLab."""

    def __init__(self, q_app: QApplication, single_instance=None, start_minimized: bool = False):
        self.q_app = q_app
        self.start_minimized = start_minimized
        self.is_explicit_quit = False
        self._notified_background_once = False

        # Initialize structured lifecycle diagnostics
        DiagnosticsLogger.setup()
        DiagnosticsLogger.log_event("APP_LAUNCHED", {
            "start_minimized": start_minimized
        })

        # Configure Qt application behavior
        self.q_app.setQuitOnLastWindowClosed(False)

        # 1. Single Instance Controller
        self.single_instance = single_instance or SingleInstanceController(parent=self.q_app)
        if not single_instance:
            self.single_instance.acquire_lock()
        self.single_instance.show_window_requested.connect(self._on_single_instance_activate)

        # 2. Persistent Settings & Background Runtime
        self.settings_manager = SettingsManager()
        self.settings: AppSettings = self.settings_manager.settings
        self.runtime = BackgroundRuntime(settings_manager=self.settings_manager)

        # 3. Sound Packs & UI
        self.pack_manager = SoundPackManager()
        self.tray_manager = TrayIconManager()

        self.main_window = MainWindow(
            profile_manager=self.runtime.profile_manager,
            pack_manager=self.pack_manager,
            latency_tracker=self.runtime.latency_tracker
        )

        # 4. Quit Event Interception Filter & Command+Q Shortcut
        self.app_filter = ApplicationEventFilter(self, self.q_app)
        self.q_app.installEventFilter(self.app_filter)

        self.cmd_q_shortcut = QShortcut(QKeySequence.Quit, self.main_window)
        self.cmd_q_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.cmd_q_shortcut.activated.connect(self._handle_cmd_q)

        self._wire_connections()
        self._initial_setup()

    def _initial_setup(self):
        """Initializes runtime components, synchronizes UI, and verifies startup state."""
        # Start background runtime
        self.runtime.start()

        # Populate profiles in UI and Taskbar Tray
        profile_tuples = [(p.id, p.name) for p in self.runtime.profile_manager.profiles.values()]
        active_prof = self.runtime.profile_manager.get_profile(self.settings.profile_id)
        if not active_prof:
            active_prof = self.runtime.profile_manager.get_active_profile()

        self.main_window.dashboard_view.set_profiles(profile_tuples, active_prof.id)
        self.main_window.dashboard_view.vol_slider.setValue(int(self.settings.master_volume * 100))
        self.main_window.dashboard_view.toggle_btn.setChecked(self.settings.enabled)
        self.main_window.sound_settings_view.load_settings(self.settings)
        self.main_window.audio_devices_view.set_current_device_index(self.settings.audio_device_index)
        self.main_window.audio_devices_view.set_current_buffer_size(self.settings.buffer_size)
        self.main_window.update_active_profile_display(active_prof.id, active_prof.name)

        # Setup Taskbar Tray Icon
        self.tray_manager.set_profiles(profile_tuples, active_prof.id)
        self.tray_manager.update_volume(self.settings.master_volume)
        self.tray_manager.update_launch_at_login(self.settings.launch_at_login)
        self.tray_manager.update_dock_visibility(self.settings.show_in_dock)
        self.tray_manager.show()

        # Synchronize macOS Dock visibility
        DockManager.set_dock_visible(self.settings.show_in_dock)

        # Synchronize Launch at Login state with macOS
        if self.settings.launch_at_login:
            if not LoginItemManager.is_launch_at_login_enabled():
                LoginItemManager.enable_launch_at_login()
        else:
            if LoginItemManager.is_launch_at_login_enabled():
                LoginItemManager.disable_launch_at_login()
        self.main_window.dashboard_view.update_launch_at_login_status(self.settings.launch_at_login)

        # Check permissions and request once if pending
        is_trusted = PermissionManager.is_accessibility_granted()
        if not is_trusted and not self.settings.accessibility_prompted:
            logger.info("First-time launch: prompting for macOS Accessibility permission.")
            self.settings.accessibility_prompted = True
            self.settings_manager.update(accessibility_prompted=True)
            PermissionManager.request_accessibility_prompt()

        self.main_window.permissions_view.update_status(is_trusted)
        self._refresh_status()

        # Periodic permission re-checker (detects permissions granted in System Settings without restart)
        self.perm_timer = QTimer(self.q_app)
        self.perm_timer.setInterval(1500)
        self.perm_timer.timeout.connect(self._auto_check_permissions)
        self.perm_timer.start()

    def _wire_connections(self):
        # Background Runtime state changes
        self.runtime.state_changed.connect(self._on_runtime_state_changed)
        self.runtime.key_visually_triggered.connect(self.main_window.dashboard_view.keyboard_view.trigger_key)

        # Taskbar Tray Icon
        self.tray_manager.show_dashboard_requested.connect(self.main_window.show_and_activate)
        self.tray_manager.open_settings_requested.connect(self.main_window.open_settings)
        self.tray_manager.open_diagnostics_requested.connect(self.main_window.open_diagnostics)
        self.tray_manager.open_permissions_requested.connect(self.main_window.open_permissions)
        self.tray_manager.pause_resume_toggled.connect(self._on_tray_pause_resume_toggled)
        self.tray_manager.stop_runtime_requested.connect(self.runtime.stop)
        self.tray_manager.start_runtime_requested.connect(self.runtime.start)
        self.tray_manager.profile_selected.connect(self._on_profile_selected)
        self.tray_manager.volume_changed.connect(self._on_volume_changed)
        self.tray_manager.preview_clicked.connect(self._on_preview_clicked)
        self.tray_manager.launch_at_login_toggled.connect(self._on_launch_at_login_toggled)
        self.tray_manager.dock_icon_toggled.connect(self._on_dock_visibility_toggled)
        self.tray_manager.quit_requested.connect(self.quit_app)

        # Main Window / Dashboard controls
        dash = self.main_window.dashboard_view
        dash.master_toggled.connect(self._on_master_toggled)
        dash.profile_selected.connect(self._on_profile_selected)
        dash.volume_changed.connect(self._on_volume_changed)
        dash.preview_clicked.connect(self._on_preview_clicked)
        dash.launch_at_login_toggled.connect(self._on_launch_at_login_toggled)
        dash.key_clicked_down.connect(self.runtime.trigger_virtual_key_down)
        dash.key_clicked_up.connect(self.runtime.trigger_virtual_key_up)
        dash.permissions_requested.connect(self._on_verify_permissions)

        # Switch Library
        sw_lib = self.main_window.switch_library_view
        sw_lib.profile_selected.connect(self._on_profile_selected)
        sw_lib.preview_requested.connect(self._on_preview_profile)

        # Sound Settings
        s_set = self.main_window.sound_settings_view
        s_set.settings_changed.connect(self._on_sound_settings_changed)
        s_set.reset_requested.connect(self._on_reset_sound_settings)

        # Audio Devices
        a_dev = self.main_window.audio_devices_view
        a_dev.device_selected.connect(self._on_device_selected)
        a_dev.buffer_size_selected.connect(self._on_buffer_size_selected)
        a_dev.test_sound_requested.connect(self._on_preview_clicked)

        # Permissions view
        self.main_window.permissions_view.verify_requested.connect(self._on_verify_permissions)

        # Diagnostics & Benchmark
        self.main_window.diagnostics_view.run_benchmark_requested.connect(self._run_typing_benchmark)

        # Local window typing preview
        self.main_window.local_key_event.connect(self._handle_local_key_event)

        # Qt teardown
        self.q_app.aboutToQuit.connect(self.shutdown)

    def _on_single_instance_activate(self):
        """Brings existing window to front when another launch of ClackLab is initiated."""
        logger.info("Secondary instance requested activation. Revealing main window.")
        DiagnosticsLogger.log_event("SECONDARY_INSTANCE_ACTIVATED")
        self.main_window.show_and_activate()

    def _handle_cmd_q(self):
        """
        Deliberate Command+Q policy:
        Allows keeping the background runtime operational while closing the foreground window,
        or explicitly quitting completely based on user preferences.
        """
        behavior = self.settings.cmd_q_behavior

        if not self.settings.run_in_background:
            self.quit_app()
            return

        if behavior == "close_to_tray":
            self.main_window.hide()
            if not self._notified_background_once:
                self._notified_background_once = True
                self.tray_manager.tray_icon.showMessage(
                    "ClackLab",
                    "ClackLab is running in the background. Use the menu bar icon to quit completely.",
                    QSystemTrayIcon.MessageIcon.Information,
                    2500
                )
            DiagnosticsLogger.log_event("CMD_Q_CLOSE_TO_TRAY")
        elif behavior == "ask":
            msg_box = QMessageBox(self.main_window)
            msg_box.setWindowTitle("ClackLab Background Operation")
            msg_box.setText("Do you want to keep ClackLab running in the background?")
            msg_box.setInformativeText("ClackLab will continue playing mechanical typing sounds from the menu bar.")
            btn_keep = msg_box.addButton("Keep in Background", QMessageBox.ButtonRole.AcceptRole)
            btn_quit = msg_box.addButton("Quit Completely", QMessageBox.ButtonRole.DestructiveRole)
            btn_cancel = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            msg_box.setDefaultButton(btn_keep)
            msg_box.exec()

            clicked = msg_box.clickedButton()
            if clicked == btn_keep:
                self.main_window.hide()
                DiagnosticsLogger.log_event("CMD_Q_KEEP_BACKGROUND_CHOSEN")
            elif clicked == btn_quit:
                self.quit_app()
        else:  # "quit_completely"
            self.quit_app()

    def _handle_local_key_event(self, event: KeyEvent):
        """Handles local keypresses while the window has focus."""
        if self.runtime.keyboard_monitor.is_running:
            return  # Handled with zero latency by global listener
        t_now = time.perf_counter_ns()
        category = self.runtime.event_filter.classify_keycode(event.keycode)
        if event.event_type == EventType.KEY_DOWN:
            self.runtime.sample_player.play_key_down(category, is_repeat=False, event_timestamp_ns=t_now)
        elif event.event_type == EventType.KEY_UP:
            self.runtime.sample_player.play_key_up(category, event_timestamp_ns=t_now)

    def _auto_check_permissions(self):
        """Auto-detects Accessibility permissions transitions every 1.5s."""
        self.runtime.recheck_permissions()
        self._refresh_status()

    def _on_runtime_state_changed(self, state: RuntimeState):
        self._refresh_status()

    def _on_tray_pause_resume_toggled(self, should_resume: bool):
        if should_resume:
            self.runtime.resume()
        else:
            self.runtime.pause()
        self._refresh_status()

    def _on_master_toggled(self, enabled: bool):
        if enabled:
            self.runtime.resume()
        else:
            self.runtime.pause()

        self.main_window.dashboard_view.toggle_btn.blockSignals(True)
        self.main_window.dashboard_view.toggle_btn.setChecked(enabled)
        self.main_window.dashboard_view.toggle_btn.setText("ENABLED" if enabled else "MUTED")
        self.main_window.dashboard_view.toggle_btn.blockSignals(False)

        self._refresh_status()

    def _on_profile_selected(self, prof_id: str):
        success = self.runtime.set_profile(prof_id)
        if success:
            prof = self.runtime.profile_manager.get_profile(prof_id)
            if prof:
                self.main_window.update_active_profile_display(prof.id, prof.name)
                self.main_window.dashboard_view.profile_combo.blockSignals(True)
                for idx in range(self.main_window.dashboard_view.profile_combo.count()):
                    if self.main_window.dashboard_view.profile_combo.itemData(idx) == prof_id:
                        self.main_window.dashboard_view.profile_combo.setCurrentIndex(idx)
                        break
                self.main_window.dashboard_view.profile_combo.blockSignals(False)
                self.tray_manager.update_active_profile(prof_id)
                self._refresh_status()

    def _on_preview_profile(self, prof_id: str):
        prof = self.runtime.profile_manager.get_profile(prof_id)
        if prof:
            temp_lib = self.runtime.sample_library
            sample = temp_lib.get_sample(KeyCategory.STANDARD, is_down=True)
            if sample:
                self.runtime.audio_engine.schedule_voice(sample.data, gain=self.settings.master_volume)

    def _on_volume_changed(self, vol: float):
        self.runtime.set_master_volume(vol)
        self.main_window.dashboard_view.vol_slider.blockSignals(True)
        self.main_window.dashboard_view.vol_slider.setValue(int(vol * 100))
        self.main_window.dashboard_view.vol_value_label.setText(f"{int(vol * 100)}%")
        self.main_window.dashboard_view.vol_slider.blockSignals(False)
        self.tray_manager.update_volume(vol)

    def _on_preview_clicked(self):
        self.runtime.sample_player.play_preview()

    def _on_launch_at_login_toggled(self, enabled: bool):
        self.settings.launch_at_login = enabled
        self.settings_manager.update(launch_at_login=enabled)
        LoginItemManager.set_launch_at_login(enabled)

        self.tray_manager.update_launch_at_login(enabled)
        self.main_window.dashboard_view.update_launch_at_login_status(enabled)
        self.main_window.sound_settings_view.cb_launch_login.blockSignals(True)
        self.main_window.sound_settings_view.cb_launch_login.setChecked(enabled)
        self.main_window.sound_settings_view.cb_launch_login.blockSignals(False)

    def _on_dock_visibility_toggled(self, visible: bool):
        self.settings.show_in_dock = visible
        self.settings_manager.update(show_in_dock=visible)
        DockManager.set_dock_visible(visible)
        self.tray_manager.update_dock_visibility(visible)
        self.main_window.sound_settings_view.cb_show_in_dock.blockSignals(True)
        self.main_window.sound_settings_view.cb_show_in_dock.setChecked(visible)
        self.main_window.sound_settings_view.cb_show_in_dock.blockSignals(False)
        DiagnosticsLogger.log_event("DOCK_VISIBILITY_CHANGED", {"show_in_dock": visible})

    def _on_sound_settings_changed(self, diff: dict):
        if "launch_at_login" in diff:
            self._on_launch_at_login_toggled(diff["launch_at_login"])
        if "show_in_dock" in diff:
            self._on_dock_visibility_toggled(diff["show_in_dock"])
        self.settings_manager.update(**diff)
        self.settings = self.settings_manager.settings
        self.runtime.sample_player.update_settings(self.settings)
        self.runtime.event_filter.update_settings(
            allow_repeats=self.settings.play_key_repeats,
            allow_modifiers=self.settings.play_modifiers
        )

    def _on_reset_sound_settings(self):
        self.settings = self.settings_manager.reset_to_defaults()
        self.runtime.sample_player.update_settings(self.settings)
        self.main_window.sound_settings_view.load_settings(self.settings)
        self._on_launch_at_login_toggled(self.settings.launch_at_login)
        self._on_dock_visibility_toggled(self.settings.show_in_dock)

    def _on_device_selected(self, dev_idx: int):
        self.settings.audio_device_index = dev_idx
        self.settings_manager.update(audio_device_index=dev_idx)
        self.runtime.audio_engine.restart(device_index=dev_idx)
        self._refresh_status()

    def _on_buffer_size_selected(self, buf_size: int):
        self.settings.buffer_size = buf_size
        self.settings_manager.update(buffer_size=buf_size)
        self.runtime.audio_engine.restart(block_size=buf_size)
        self._refresh_status()

    def _on_verify_permissions(self):
        is_trusted = self.runtime.recheck_permissions()
        self.main_window.permissions_view.update_status(is_trusted)
        self._refresh_status()

    def _refresh_status(self):
        health = self.runtime.get_health_status()
        is_trusted = health["accessibility_trusted"]
        default_dev = AudioDeviceManager.get_default_output_device()
        dev_name = default_dev['name'] if default_dev else "Default Output"

        self.main_window.dashboard_view.update_status(
            engine_active=health["audio_active"],
            perm_trusted=is_trusted,
            device_name=dev_name
        )
        self.tray_manager.update_runtime_health(health)

    def _run_typing_benchmark(self):
        """Executes rapid typing burst to test polyphony and measure latencies."""
        import threading
        def worker():
            keycodes = [12, 13, 14, 15, 17, 16, 32, 34, 49, 36]
            for i in range(50):
                kc = keycodes[i % len(keycodes)]
                cat = self.runtime.event_filter.classify_keycode(kc)
                t_ev = time.perf_counter_ns()
                self.runtime.sample_player.play_key_down(cat, is_repeat=False, event_timestamp_ns=t_ev)
                time.sleep(0.018)
                t_up = time.perf_counter_ns()
                self.runtime.sample_player.play_key_up(cat, event_timestamp_ns=t_up)
                time.sleep(0.008)

        threading.Thread(target=worker, daemon=True, name="ClackLab-Benchmark").start()

    def show(self):
        """Displays main window unless launched in background/hidden mode."""
        if not self.start_minimized:
            self.main_window.show()

    def quit_app(self):
        """Explicit, documented user action terminating all ClackLab processes."""
        logger.info("Explicit application quit initiated.")
        DiagnosticsLogger.log_event("EXPLICIT_QUIT_REQUESTED")
        self.is_explicit_quit = True
        self.main_window.force_close = True
        self.shutdown()
        self.q_app.quit()

    def shutdown(self):
        """Releases all hardware and system hooks."""
        logger.info("Shutting down ClackLab background runtime...")
        self.single_instance.release_lock()
        self.tray_manager.hide()
        self.runtime.stop()
        DiagnosticsLogger.log_event("APP_SHUTDOWN_COMPLETED")
