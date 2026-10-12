"""
Independent Background Runtime for ClackLab.

Decoupled completely from any window, controller, or UI lifecycle.
Maintains audio streams, in-memory sample libraries, global event taps,
anti-repetition logic, and telemetry metrics with a formal state machine.
"""

import time
import threading
import logging
from typing import Optional, Dict, Any
from PySide6.QtCore import QObject, Signal

from ..models import RuntimeState, KeyCategory, KeyEvent, EventType
from ..settings import SettingsManager, AppSettings
from ..audio.audio_engine import AudioEngine
from ..audio.sample_library import SampleLibrary
from ..audio.sample_player import SamplePlayer
from ..audio.latency_metrics import LatencyTracker
from ..keyboard.event_filter import EventFilter
from ..keyboard.event_monitor import GlobalKeyboardMonitor
from ..keyboard.permission_manager import PermissionManager
from ..profiles.profile_manager import ProfileManager
from ..system.diagnostics_logger import DiagnosticsLogger

logger = logging.getLogger(__name__)


class BackgroundRuntime(QObject):
    """
    Dedicated background runtime service managing core mechanical keyboard audio
    and global event tapping independent of any user interface.
    """

    state_changed = Signal(RuntimeState)
    key_visually_triggered = Signal(int, bool)  # keycode, is_pressed
    health_updated = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, settings_manager: Optional[SettingsManager] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._lock = threading.RLock()
        self._state = RuntimeState.NOT_STARTED

        # Settings
        self.settings_manager = settings_manager or SettingsManager()
        self.settings: AppSettings = self.settings_manager.settings

        # Telemetry & Profiles
        self.latency_tracker = LatencyTracker()
        self.profile_manager = ProfileManager()

        # Audio Subsystem
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

        # Keyboard Subsystem
        self.event_filter = EventFilter()
        self.event_filter.update_settings(
            excluded_keys=self.settings.excluded_keys,
            allow_repeats=self.settings.play_key_repeats,
            allow_modifiers=self.settings.play_modifiers
        )
        self.keyboard_monitor = GlobalKeyboardMonitor(
            event_filter=self.event_filter,
            on_key_event=self._handle_global_key_event
        )

        self._active_profile_id = self.settings.profile_id

    @property
    def state(self) -> RuntimeState:
        with self._lock:
            return self._state

    def _set_state(self, new_state: RuntimeState, reason: str = ""):
        with self._lock:
            if self._state == new_state:
                return
            prev_state = self._state
            self._state = new_state
            logger.info(f"Runtime state transition: {prev_state.value} -> {new_state.value} ({reason})")
            DiagnosticsLogger.log_event("RUNTIME_STATE_CHANGED", {
                "previous": prev_state.value,
                "current": new_state.value,
                "reason": reason
            })
            self.state_changed.emit(new_state)

    def start(self) -> bool:
        """Starts the background runtime service idempotently."""
        with self._lock:
            if self._state in (RuntimeState.RUNNING, RuntimeState.DEGRADED):
                logger.debug("Runtime start called while already active; ignoring duplicate start.")
                return True

            self._set_state(RuntimeState.STARTING, "Starting background runtime components")
            DiagnosticsLogger.log_event("RUNTIME_START_REQUESTED", {"profile": self.settings.profile_id})

            # 1. Load active switch profile
            prof = self.profile_manager.get_profile(self.settings.profile_id)
            if not prof:
                prof = self.profile_manager.get_active_profile()
                self.settings.profile_id = prof.id
            self.sample_library.load_profile(prof)

            # 2. Start audio stream
            if self.settings.enabled:
                started = self.audio_engine.start()
                if not started:
                    err = self.audio_engine.last_error or "AudioEngine failed to start stream"
                    self._set_state(RuntimeState.FAILED, err)
                    self.error_occurred.emit(err)
                    DiagnosticsLogger.log_event("RUNTIME_START_FAILED", {"error": err}, level=logging.ERROR)
                    return False
            else:
                self.audio_engine.muted = True

            # 3. Check macOS Accessibility authorization
            is_trusted = PermissionManager.is_accessibility_granted()
            DiagnosticsLogger.log_event("PERMISSION_CHECK", {"accessibility_trusted": is_trusted})

            if not self.settings.enabled:
                self._set_state(RuntimeState.PAUSED, "Audio generation disabled by user preference")
            elif is_trusted:
                monitor_started = self.keyboard_monitor.start()
                if monitor_started:
                    self._set_state(RuntimeState.RUNNING, "Audio engine and global keyboard monitor active")
                else:
                    self._set_state(RuntimeState.DEGRADED, "Event monitor failed to start")
            else:
                self._set_state(RuntimeState.DEGRADED, "Accessibility permission required for global monitoring")

            return True

    def stop(self):
        """Cleanly stops the background runtime service and releases hardware resources."""
        with self._lock:
            if self._state == RuntimeState.STOPPED:
                return

            self._set_state(RuntimeState.STOPPING, "Stopping background runtime")
            DiagnosticsLogger.log_event("RUNTIME_STOP_REQUESTED")

            try:
                self.keyboard_monitor.stop()
            except Exception as e:
                logger.warning(f"Error stopping keyboard monitor: {e}")

            try:
                self.audio_engine.stop()
            except Exception as e:
                logger.warning(f"Error stopping audio engine: {e}")

            self._set_state(RuntimeState.STOPPED, "All components stopped")
            DiagnosticsLogger.log_event("RUNTIME_STOPPED")

    def pause(self):
        """Temporarily mutes sound generation without tearing down the audio stream."""
        with self._lock:
            self.settings.enabled = False
            self.settings_manager.update(enabled=False)
            self.audio_engine.muted = True
            self.sample_player.update_settings(self.settings)
            self._set_state(RuntimeState.PAUSED, "Sound playback paused")
            DiagnosticsLogger.log_event("RUNTIME_PAUSED")

    def resume(self):
        """Resumes sound generation."""
        with self._lock:
            self.settings.enabled = True
            self.settings_manager.update(enabled=True)
            self.sample_player.update_settings(self.settings)
            self.audio_engine.muted = False

            if not self.audio_engine.is_running:
                self.audio_engine.start()

            is_trusted = PermissionManager.is_accessibility_granted()
            if is_trusted and not self.keyboard_monitor.is_running:
                self.keyboard_monitor.start()

            if is_trusted:
                self._set_state(RuntimeState.RUNNING, "Sound playback resumed")
            else:
                self._set_state(RuntimeState.DEGRADED, "Resumed with accessibility missing")

            DiagnosticsLogger.log_event("RUNTIME_RESUMED", {"accessibility_trusted": is_trusted})

    def restart(self) -> bool:
        """Restarts the audio stream and event monitor cleanly."""
        with self._lock:
            logger.info("Restarting background runtime...")
            DiagnosticsLogger.log_event("RUNTIME_RESTART_REQUESTED")
            self.stop()
            return self.start()

    def set_profile(self, profile_id: str) -> bool:
        """Loads and activates a switch profile by ID."""
        with self._lock:
            prof = self.profile_manager.get_profile(profile_id)
            if not prof:
                logger.warning(f"Profile {profile_id} not found.")
                return False

            self.settings.profile_id = profile_id
            self.settings_manager.update(profile_id=profile_id)
            success = self.sample_library.load_profile(prof)
            DiagnosticsLogger.log_event("PROFILE_CHANGED", {"profile_id": profile_id, "success": success})
            return success

    def set_master_volume(self, volume: float):
        """Updates master volume level (0.0 to 1.5)."""
        vol = max(0.0, min(1.5, float(volume)))
        self.settings.master_volume = vol
        self.settings_manager.update(master_volume=vol)
        self.sample_player.update_settings(self.settings)

    def recheck_permissions(self) -> bool:
        """
        Revalidates macOS Accessibility trust.
        Starts global event tap if newly granted; downgrades to DEGRADED if revoked.
        """
        with self._lock:
            is_trusted = PermissionManager.is_accessibility_granted()
            if is_trusted:
                if not self.keyboard_monitor.is_running and self.settings.enabled:
                    logger.info("macOS Accessibility granted. Starting global event monitor.")
                    self.keyboard_monitor.start()
                    DiagnosticsLogger.log_event("KEYBOARD_MONITOR_STARTED", {"trigger": "permission_granted"})
                if self._state == RuntimeState.DEGRADED:
                    self._set_state(RuntimeState.RUNNING, "Accessibility granted")
            else:
                if self.keyboard_monitor.is_running:
                    self.keyboard_monitor.stop()
                    DiagnosticsLogger.log_event("KEYBOARD_MONITOR_STOPPED", {"trigger": "permission_revoked"})
                if self._state == RuntimeState.RUNNING:
                    self._set_state(RuntimeState.DEGRADED, "Accessibility permission missing")

            return is_trusted

    def trigger_virtual_key_down(self, keycode: int):
        """Called by UI on-screen keyboard or local window typing."""
        if not self.settings.enabled:
            return
        t_now = time.perf_counter_ns()
        category = self.event_filter.classify_keycode(keycode)
        self.sample_player.play_key_down(category, is_repeat=False, event_timestamp_ns=t_now)

    def trigger_virtual_key_up(self, keycode: int):
        if not self.settings.enabled:
            return
        t_now = time.perf_counter_ns()
        category = self.event_filter.classify_keycode(keycode)
        self.sample_player.play_key_up(category, event_timestamp_ns=t_now)

    def _handle_global_key_event(self, event: KeyEvent):
        """
        Executed immediately in the background CGEventTap/WinHook thread.
        Dispatches audio directly to PortAudio with zero Qt event loop latency.
        """
        if event.event_type == EventType.KEY_DOWN:
            self.sample_player.play_key_down(
                category=event.category,
                is_repeat=event.is_repeat,
                event_timestamp_ns=event.timestamp_ns
            )
            if self.settings.visual_keyboard_feedback:
                self.key_visually_triggered.emit(event.keycode, True)
        elif event.event_type == EventType.KEY_UP:
            self.sample_player.play_key_up(
                category=event.category,
                event_timestamp_ns=event.timestamp_ns
            )
            if self.settings.visual_keyboard_feedback:
                self.key_visually_triggered.emit(event.keycode, False)

    def get_health_status(self) -> Dict[str, Any]:
        """Provides an authoritative, consistent snapshot of runtime health."""
        stats = self.latency_tracker.get_stats()
        active_prof = self.profile_manager.get_profile(self.settings.profile_id)
        is_trusted = PermissionManager.is_accessibility_granted()

        return {
            "state": self._state,
            "state_name": self._state.value,
            "is_running": self._state in (RuntimeState.RUNNING, RuntimeState.DEGRADED),
            "is_muted": self.audio_engine.muted or not self.settings.enabled,
            "audio_active": self.audio_engine.is_running,
            "monitor_active": self.keyboard_monitor.is_running,
            "accessibility_trusted": is_trusted,
            "active_profile_id": self.settings.profile_id,
            "active_profile_name": active_prof.name if active_prof else "Unknown",
            "master_volume": self.settings.master_volume,
            "buffer_size": self.settings.buffer_size,
            "sample_rate": self.settings.sample_rate,
            "underruns": stats.buffer_underruns,
            "active_voices": stats.active_voices,
            "median_ms": stats.median_ms,
            "p95_ms": stats.p95_ms,
            "max_ms": stats.max_ms
        }
