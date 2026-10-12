"""
Application coordinator wiring together audio, keyboard monitoring, settings, and UI.
"""

import time
import threading
import logging
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QApplication

from .models import KeyCategory, KeyEvent, EventType
from .settings import SettingsManager, AppSettings
from .audio.latency_metrics import LatencyTracker
from .audio.audio_devices import AudioDeviceManager
from .audio.sample_library import SampleLibrary
from .audio.audio_engine import AudioEngine
from .audio.sample_player import SamplePlayer
from .keyboard.event_filter import EventFilter
from .keyboard.permission_manager import PermissionManager
from .keyboard.event_monitor import GlobalKeyboardMonitor
from .profiles.profile_manager import ProfileManager
from .soundpacks.pack_manager import SoundPackManager
from .ui.main_window import MainWindow
from .ui.tray_icon import TrayIconManager
from .system.login_item import LoginItemManager

logger = logging.getLogger(__name__)

class KeySignalBridge(QObject):
    """Bridge forwarding background keyboard events to Qt main thread for visual UI updates."""
    key_visually_triggered = Signal(int, bool)  # keycode, is_pressed

class ClackApplication:
    """Master application coordinator managing the lifecycle of ClackLab."""

    def __init__(self, q_app: QApplication):
        self.q_app = q_app

        # 1. State & Managers
        self.settings_manager = SettingsManager()
        self.settings = self.settings_manager.settings
        self.latency_tracker = LatencyTracker()

        # 2. Profiles & Sound Packs
        self.profile_manager = ProfileManager()
        self.pack_manager = SoundPackManager()

        # 3. Audio Subsystem
        self.sample_library = SampleLibrary(target_sample_rate=self.settings.sample_rate)
        self.audio_engine = AudioEngine(
            sample_rate=self.settings.sample_rate,
            block_size=self.settings.buffer_size,
            device_index=self.settings.audio_device_index,
            latency_tracker=self.latency_tracker
        )
        self.sample_player = SamplePlayer(
            audio_engine=self.audio_engine,
            sample_library=self.sample_library,
            latency_tracker=self.latency_tracker
        )
        self.sample_player.update_settings(self.settings)

        # 4. Keyboard Subsystem
        self.event_filter = EventFilter()
        self.event_filter.update_settings(
            excluded_keys=self.settings.excluded_keys,
            allow_repeats=self.settings.play_key_repeats,
            allow_modifiers=self.settings.play_modifiers
        )

        self.bridge = KeySignalBridge()
        self.keyboard_monitor = GlobalKeyboardMonitor(
            event_filter=self.event_filter,
            on_key_event=self._handle_global_key_event
        )

        # 5. User Interface & Taskbar Tray Icon
        self.q_app.setQuitOnLastWindowClosed(False)
        self.tray_manager = TrayIconManager()

        self.main_window = MainWindow(
            profile_manager=self.profile_manager,
            pack_manager=self.pack_manager,
            latency_tracker=self.latency_tracker
        )

        self._wire_connections()
        self._initial_setup()

    def _initial_setup(self):
        """Loads initial profile, starts audio stream, and begins global event tap."""
        # Load switch profile
        prof = self.profile_manager.get_profile(self.settings.profile_id)
        if not prof:
            prof = self.profile_manager.get_active_profile()
            self.settings.profile_id = prof.id

        self.sample_library.load_profile(prof)

        # Populate profiles in UI and Taskbar Tray
        profile_tuples = [(p.id, p.name) for p in self.profile_manager.profiles.values()]
        self.main_window.dashboard_view.set_profiles(profile_tuples, prof.id)
        self.main_window.dashboard_view.vol_slider.setValue(int(self.settings.master_volume * 100))
        self.main_window.dashboard_view.toggle_btn.setChecked(self.settings.enabled)
        self.main_window.sound_settings_view.load_settings(self.settings)
        self.main_window.audio_devices_view.set_current_device_index(self.settings.audio_device_index)
        self.main_window.audio_devices_view.set_current_buffer_size(self.settings.buffer_size)
        self.main_window.update_active_profile_display(prof.id, prof.name)

        # Setup Taskbar Tray Icon
        self.tray_manager.set_profiles(profile_tuples, prof.id)
        self.tray_manager.update_volume(self.settings.master_volume)
        self.tray_manager.update_enabled_state(self.settings.enabled)
        self.tray_manager.update_launch_at_login(self.settings.launch_at_login)
        self.tray_manager.show()

        # Synchronize Launch at Login state with macOS
        if self.settings.launch_at_login:
            if not LoginItemManager.is_launch_at_login_enabled():
                LoginItemManager.enable_launch_at_login()
        else:
            if LoginItemManager.is_launch_at_login_enabled():
                LoginItemManager.disable_launch_at_login()
        self.main_window.dashboard_view.update_launch_at_login_status(self.settings.launch_at_login)

        # Start audio engine
        if self.settings.enabled:
            self.audio_engine.start()

        # Check permissions & start global monitor
        is_trusted = PermissionManager.is_accessibility_granted()
        if not is_trusted:
            logger.info("macOS Accessibility permission pending. Triggering system prompt.")
            PermissionManager.request_accessibility_prompt()

        self.main_window.permissions_view.update_status(is_trusted)
        
        default_dev = AudioDeviceManager.get_default_output_device()
        dev_name = default_dev['name'] if default_dev else "Default Audio Device"
        self.main_window.dashboard_view.update_status(
            engine_active=self.audio_engine.is_running,
            perm_trusted=is_trusted,
            device_name=dev_name
        )
        if is_trusted and self.settings.enabled:
            self.keyboard_monitor.start()

        # Auto-detect Accessibility permission transitions every 1.5s
        self.perm_timer = QTimer(self.q_app)
        self.perm_timer.setInterval(1500)
        self.perm_timer.timeout.connect(self._auto_check_permissions)
        self.perm_timer.start()

    def _wire_connections(self):
        # Taskbar Tray Icon -> Audio / Dashboard
        self.tray_manager.master_toggled.connect(self._on_master_toggled)
        self.tray_manager.profile_selected.connect(self._on_profile_selected)
        self.tray_manager.volume_changed.connect(self._on_volume_changed)
        self.tray_manager.preview_clicked.connect(self._on_preview_clicked)
        self.tray_manager.show_dashboard_requested.connect(self.main_window.show_and_activate)
        self.tray_manager.launch_at_login_toggled.connect(self._on_launch_at_login_toggled)
        self.tray_manager.quit_requested.connect(self.quit_app)

        # UI -> Audio / Settings
        dash = self.main_window.dashboard_view
        dash.master_toggled.connect(self._on_master_toggled)
        dash.profile_selected.connect(self._on_profile_selected)
        dash.volume_changed.connect(self._on_volume_changed)
        dash.preview_clicked.connect(self._on_preview_clicked)
        dash.launch_at_login_toggled.connect(self._on_launch_at_login_toggled)

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

        # Permissions
        self.main_window.permissions_view.verify_requested.connect(self._on_verify_permissions)

        # Diagnostics & Benchmark
        self.main_window.diagnostics_view.run_benchmark_requested.connect(self._run_typing_benchmark)

        # Visual keyboard updates via bridge
        self.bridge.key_visually_triggered.connect(self.main_window.dashboard_view.keyboard_view.trigger_key)

        # Local window typing preview
        self.main_window.local_key_event.connect(self._handle_local_key_event)

        # Dashboard on-screen virtual keyboard clicks
        self.main_window.dashboard_view.key_clicked_down.connect(self._handle_ui_key_down)
        self.main_window.dashboard_view.key_clicked_up.connect(self._handle_ui_key_up)
        self.main_window.dashboard_view.permissions_requested.connect(self._on_verify_permissions)

        # Cleanup on exit
        self.q_app.aboutToQuit.connect(self.shutdown)

    def _handle_ui_key_down(self, keycode: int):
        """Executed when user clicks a keycap on the on-screen virtual keyboard."""
        if not self.settings.enabled:
            return
        t_now = time.perf_counter_ns()
        category = self.event_filter.classify_keycode(keycode)
        self.sample_player.play_key_down(category, is_repeat=False, event_timestamp_ns=t_now)

    def _handle_ui_key_up(self, keycode: int):
        """Executed when user releases click on an on-screen keycap."""
        if not self.settings.enabled:
            return
        t_now = time.perf_counter_ns()
        category = self.event_filter.classify_keycode(keycode)
        self.sample_player.play_key_up(category, event_timestamp_ns=t_now)

    def _handle_global_key_event(self, event: KeyEvent):
        """
        Executed immediately in the background CGEventTap thread.
        Triggers audio without dispatching through Qt event loop for zero latency.
        """
        if event.event_type == EventType.KEY_DOWN:
            self.sample_player.play_key_down(
                category=event.category,
                is_repeat=event.is_repeat,
                event_timestamp_ns=event.timestamp_ns
            )
            if self.settings.visual_keyboard_feedback:
                self.bridge.key_visually_triggered.emit(event.keycode, True)
        elif event.event_type == EventType.KEY_UP:
            self.sample_player.play_key_up(
                category=event.category,
                event_timestamp_ns=event.timestamp_ns
            )
            if self.settings.visual_keyboard_feedback:
                self.bridge.key_visually_triggered.emit(event.keycode, False)

    def _handle_local_key_event(self, event: KeyEvent):
        """Handles keypresses from the focused local ClackLab window."""
        if self.keyboard_monitor.is_running:
            return  # Handled with ultra-low latency by global CGEventTap listener
        t_now = time.perf_counter_ns()
        category = self.event_filter.classify_keycode(event.keycode)
        if event.event_type == EventType.KEY_DOWN:
            self.sample_player.play_key_down(category, is_repeat=False, event_timestamp_ns=t_now)
        elif event.event_type == EventType.KEY_UP:
            self.sample_player.play_key_up(category, event_timestamp_ns=t_now)

    def _auto_check_permissions(self):
        """Automatically starts global keyboard monitoring when user grants permission."""
        is_trusted = PermissionManager.is_accessibility_granted()
        if is_trusted and not self.keyboard_monitor.is_running and self.settings.enabled:
            logger.info("macOS Accessibility granted. Starting global CGEventTap listener.")
            self.keyboard_monitor.start()
        self._refresh_status()

    def _on_master_toggled(self, enabled: bool):
        self.settings.enabled = enabled
        self.settings_manager.update(enabled=enabled)
        self.sample_player.update_settings(self.settings)

        # Synchronize UI toggle button
        self.main_window.dashboard_view.toggle_btn.blockSignals(True)
        self.main_window.dashboard_view.toggle_btn.setChecked(enabled)
        self.main_window.dashboard_view.toggle_btn.setText("ENABLED" if enabled else "MUTED")
        self.main_window.dashboard_view.toggle_btn.blockSignals(False)

        # Synchronize Taskbar Tray
        self.tray_manager.update_enabled_state(enabled)

        if enabled:
            if not self.audio_engine.is_running:
                self.audio_engine.start()
            if not self.keyboard_monitor.is_running and PermissionManager.is_accessibility_granted():
                self.keyboard_monitor.start()
        else:
            self.audio_engine.muted = True

        self._refresh_status()

    def _on_profile_selected(self, prof_id: str):
        prof = self.profile_manager.get_profile(prof_id)
        if prof:
            self.settings.profile_id = prof_id
            self.settings_manager.update(profile_id=prof_id)
            self.sample_library.load_profile(prof)
            self.main_window.update_active_profile_display(prof.id, prof.name)
            # Update combo box if triggered from Switch Library
            self.main_window.dashboard_view.profile_combo.blockSignals(True)
            for idx in range(self.main_window.dashboard_view.profile_combo.count()):
                if self.main_window.dashboard_view.profile_combo.itemData(idx) == prof_id:
                    self.main_window.dashboard_view.profile_combo.setCurrentIndex(idx)
                    break
            self.main_window.dashboard_view.profile_combo.blockSignals(False)
            # Update Taskbar Tray
            self.tray_manager.update_active_profile(prof_id)
            self._refresh_status()

    def _on_preview_profile(self, prof_id: str):
        # Temporarily play a preview from that profile
        prof = self.profile_manager.get_profile(prof_id)
        if prof:
            temp_lib = SampleLibrary(target_sample_rate=self.settings.sample_rate)
            temp_lib.load_profile(prof)
            sample = temp_lib.get_sample(KeyCategory.STANDARD, is_down=True)
            if sample:
                self.audio_engine.schedule_voice(sample.data, gain=self.settings.master_volume)

    def _on_volume_changed(self, vol: float):
        self.settings.master_volume = vol
        self.settings_manager.update(master_volume=vol)
        self.sample_player.update_settings(self.settings)

        # Synchronize Dashboard slider
        self.main_window.dashboard_view.vol_slider.blockSignals(True)
        self.main_window.dashboard_view.vol_slider.setValue(int(vol * 100))
        self.main_window.dashboard_view.vol_value_label.setText(f"{int(vol * 100)}%")
        self.main_window.dashboard_view.vol_slider.blockSignals(False)

        # Synchronize Taskbar Tray
        self.tray_manager.update_volume(vol)

    def _on_preview_clicked(self):
        self.sample_player.play_preview()

    def _on_launch_at_login_toggled(self, enabled: bool):
        self.settings.launch_at_login = enabled
        self.settings_manager.update(launch_at_login=enabled)
        LoginItemManager.set_launch_at_login(enabled)

        # Synchronize all UI representations
        self.tray_manager.update_launch_at_login(enabled)
        self.main_window.dashboard_view.update_launch_at_login_status(enabled)
        self.main_window.sound_settings_view.cb_launch_login.blockSignals(True)
        self.main_window.sound_settings_view.cb_launch_login.setChecked(enabled)
        self.main_window.sound_settings_view.cb_launch_login.blockSignals(False)

    def _on_sound_settings_changed(self, diff: dict):
        if "launch_at_login" in diff:
            self._on_launch_at_login_toggled(diff["launch_at_login"])
        self.settings_manager.update(**diff)
        self.settings = self.settings_manager.settings
        self.sample_player.update_settings(self.settings)
        self.event_filter.update_settings(
            allow_repeats=self.settings.play_key_repeats,
            allow_modifiers=self.settings.play_modifiers
        )

    def _on_reset_sound_settings(self):
        self.settings = self.settings_manager.reset_to_defaults()
        self.sample_player.update_settings(self.settings)
        self.main_window.sound_settings_view.load_settings(self.settings)
        self._on_launch_at_login_toggled(self.settings.launch_at_login)

    def _on_device_selected(self, dev_idx: int):
        self.settings.audio_device_index = dev_idx
        self.settings_manager.update(audio_device_index=dev_idx)
        self.audio_engine.restart(device_index=dev_idx)
        self._refresh_status()

    def _on_buffer_size_selected(self, buf_size: int):
        self.settings.buffer_size = buf_size
        self.settings_manager.update(buffer_size=buf_size)
        self.audio_engine.restart(block_size=buf_size)
        self._refresh_status()

    def _on_verify_permissions(self):
        is_trusted = PermissionManager.is_accessibility_granted()
        self.main_window.permissions_view.update_status(is_trusted)
        if is_trusted and not self.keyboard_monitor.is_running and self.settings.enabled:
            self.keyboard_monitor.start()
        self._refresh_status()

    def _refresh_status(self):
        is_trusted = PermissionManager.is_accessibility_granted()
        default_dev = AudioDeviceManager.get_default_output_device()
        dev_name = default_dev['name'] if default_dev else "Default Output"
        self.main_window.dashboard_view.update_status(
            engine_active=self.audio_engine.is_running,
            perm_trusted=is_trusted,
            device_name=dev_name
        )
        active_prof = self.profile_manager.get_active_profile()
        self.tray_manager.update_status(
            self.audio_engine.is_running,
            is_trusted,
            active_prof.name if active_prof else ""
        )

    def _run_typing_benchmark(self):
        """Executes a 50-keystroke rapid typing burst to test polyphony and record latencies."""
        def benchmark_worker():
            keycodes = [12, 13, 14, 15, 17, 16, 32, 34, 49, 36]  # Q, W, E, R, T, Y, U, I, Space, Return
            for i in range(50):
                kc = keycodes[i % len(keycodes)]
                cat = self.event_filter.classify_keycode(kc)
                t_event = time.perf_counter_ns()
                self.sample_player.play_key_down(cat, is_repeat=False, event_timestamp_ns=t_event)
                time.sleep(0.018)  # ~55 keystrokes/sec (very rapid typing)
                t_up = time.perf_counter_ns()
                self.sample_player.play_key_up(cat, event_timestamp_ns=t_up)
                time.sleep(0.008)

        threading.Thread(target=benchmark_worker, daemon=True, name="ClackLab-BenchmarkThread").start()

    def show(self):
        self.main_window.show()

    def quit_app(self):
        self.main_window.force_close = True
        self.shutdown()
        self.q_app.quit()

    def shutdown(self):
        logger.info("Shutting down ClackLab...")
        self.tray_manager.hide()
        self.keyboard_monitor.stop()
        self.audio_engine.stop()
