"""
macOS Quartz CGEventTap global keyboard event monitor.
Operates strictly in ListenOnly mode: never consumes, modifies, or intercepts normal input.
"""

import time
import threading
import logging
from typing import Callable, Optional
import Quartz
from AppKit import NSEvent
from .event_filter import EventFilter
from .permission_manager import PermissionManager
from ..models import EventType, KeyEvent

logger = logging.getLogger(__name__)

class GlobalKeyboardMonitor:
    """
    Listens to system-wide keyboard events across all applications via macOS Quartz CGEventTap.
    Uses kCGEventTapOptionListenOnly so normal keyboard input is never blocked or altered.
    """

    def __init__(
        self,
        event_filter: Optional[EventFilter] = None,
        on_key_event: Optional[Callable[[KeyEvent], None]] = None
    ):
        self.event_filter = event_filter or EventFilter()
        self.on_key_event = on_key_event

        self._thread: Optional[threading.Thread] = None
        self._run_loop = None
        self._tap = None
        self._is_running = False
        self._lock = threading.Lock()
        self.last_error: Optional[str] = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self) -> bool:
        """Starts the global keyboard event tap in a dedicated background daemon thread."""
        with self._lock:
            if self._is_running:
                return True

            if not PermissionManager.is_accessibility_granted():
                self.last_error = "macOS Accessibility permission not granted."
                logger.warning(self.last_error)
                return False

            self._is_running = True
            self._thread = threading.Thread(
                target=self._run_tap_thread,
                name="ClackLab-CGEventTapThread",
                daemon=True
            )
            self._thread.start()
            return True

    def stop(self):
        """Stops the global event tap and terminates the background run loop."""
        with self._lock:
            self._is_running = False
            if self._run_loop is not None:
                Quartz.CFRunLoopStop(self._run_loop)
            if self._tap is not None:
                Quartz.CGEventTapEnable(self._tap, False)
                self._tap = None
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=0.5)
            self._thread = None
            self.event_filter.reset_state()
            logger.info("Global keyboard monitor stopped.")

    def _tap_callback(self, proxy, type_, event, refcon):
        """
        Quartz event tap callback.
        Must return 'event' untouched so system and other applications receive input.
        """
        t_recv_ns = time.perf_counter_ns()

        # Handle tap disabled by system timeout
        if type_ == Quartz.kCGEventTapDisabledByTimeout or type_ == Quartz.kCGEventTapDisabledByUserInput:
            if self._tap:
                Quartz.CGEventTapEnable(self._tap, True)
            return event

        if not self._is_running:
            return event

        try:
            keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
            is_repeat = bool(Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventAutorepeat))

            ev_type = None
            if type_ == Quartz.kCGEventKeyDown:
                ev_type = EventType.KEY_DOWN
            elif type_ == Quartz.kCGEventKeyUp:
                ev_type = EventType.KEY_UP
            elif type_ == Quartz.kCGEventFlagsChanged:
                # Modifiers toggle flags: check modifier down state
                flags = Quartz.CGEventGetFlags(event)
                # If any modifier flag active, consider it key down, else key up
                mod_mask = (
                    Quartz.kCGEventFlagMaskAlphaShift |
                    Quartz.kCGEventFlagMaskShift |
                    Quartz.kCGEventFlagMaskControl |
                    Quartz.kCGEventFlagMaskAlternate |
                    Quartz.kCGEventFlagMaskCommand |
                    Quartz.kCGEventFlagMaskSecondaryFn
                )
                ev_type = EventType.KEY_DOWN if (flags & mod_mask) else EventType.KEY_UP

            if ev_type and self.on_key_event:
                filtered = self.event_filter.filter_event(
                    event_type=ev_type,
                    keycode=keycode,
                    is_autorepeat=is_repeat,
                    timestamp_ns=t_recv_ns
                )
                if filtered:
                    self.on_key_event(filtered)
        except Exception as e:
            logger.error(f"Error in CGEventTap callback: {e}")

        # Always return the event unmodified!
        return event

    def _run_tap_thread(self):
        """Initializes Quartz CGEventTap and enters CFRunLoop."""
        mask = (
            (1 << Quartz.kCGEventKeyDown) |
            (1 << Quartz.kCGEventKeyUp) |
            (1 << Quartz.kCGEventFlagsChanged)
        )

        tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionListenOnly,
            mask,
            self._tap_callback,
            None
        )

        if tap is None:
            self.last_error = "Failed to create CGEventTap (insufficient privileges or tap creation error)."
            logger.error(self.last_error)
            self._is_running = False
            return

        self._tap = tap
        source = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
        self._run_loop = Quartz.CFRunLoopGetCurrent()
        Quartz.CFRunLoopAddSource(self._run_loop, source, Quartz.kCFRunLoopCommonModes)
        Quartz.CGEventTapEnable(tap, True)

        logger.info("CGEventTap global listener active and running in background CFRunLoop.")
        Quartz.CFRunLoopRun()
        self._is_running = False
