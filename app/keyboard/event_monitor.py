"""
Global keyboard event monitor.
- macOS: Native Quartz CGEventTap in ListenOnly mode.
- Windows: Native Low-Level Keyboard Hook (WH_KEYBOARD_LL) via ctypes.
Operates strictly in ListenOnly mode: never consumes, modifies, or intercepts normal input.
"""

import sys
import time
import threading
import logging
from typing import Callable, Optional
from .event_filter import EventFilter
from .permission_manager import PermissionManager
from ..models import EventType, KeyEvent

logger = logging.getLogger(__name__)

# Platform imports
if sys.platform == "darwin":
    try:
        import Quartz
        from AppKit import NSEvent
    except ImportError:
        Quartz = None
        NSEvent = None
elif sys.platform == "win32":
    import ctypes
    from ctypes import wintypes


class GlobalKeyboardMonitor:
    """
    Listens to system-wide keyboard events across all applications.
    - On macOS: Quartz CGEventTap (kCGEventTapOptionListenOnly).
    - On Windows: WH_KEYBOARD_LL hook.
    Normal keyboard input is never blocked or altered.
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
        self._win_hook = None
        self._win_hook_proc = None
        self._win_thread_id = None
        self._is_running = False
        self._lock = threading.Lock()
        self.last_error: Optional[str] = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self) -> bool:
        """Starts the global keyboard event tap/hook in a dedicated background thread."""
        with self._lock:
            if self._is_running:
                return True

            if sys.platform == "darwin":
                if not PermissionManager.is_accessibility_granted():
                    self.last_error = "macOS Accessibility permission not granted."
                    logger.warning(self.last_error)
                    return False

            self._is_running = True
            target_fn = self._run_tap_thread if sys.platform == "darwin" else self._run_windows_hook_thread
            thread_name = "ClackLab-CGEventTapThread" if sys.platform == "darwin" else "ClackLab-WinHookThread"

            self._thread = threading.Thread(
                target=target_fn,
                name=thread_name,
                daemon=True
            )
            self._thread.start()
            return True

    def stop(self):
        """Stops the global event monitor and cleans up background loops."""
        with self._lock:
            self._is_running = False

            if sys.platform == "darwin":
                if Quartz is not None:
                    if self._run_loop is not None:
                        Quartz.CFRunLoopStop(self._run_loop)
                    if self._tap is not None:
                        Quartz.CGEventTapEnable(self._tap, False)
                        self._tap = None
            elif sys.platform == "win32":
                try:
                    if self._win_thread_id:
                        ctypes.windll.user32.PostThreadMessageW(self._win_thread_id, 0x0012, 0, 0)  # WM_QUIT
                    if self._win_hook:
                        ctypes.windll.user32.UnhookWindowsHookEx(self._win_hook)
                        self._win_hook = None
                except Exception as e:
                    logger.debug(f"Windows unhook note: {e}")

            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=0.5)
            self._thread = None
            self.event_filter.reset_state()
            logger.info("Global keyboard monitor stopped.")

    # -------------------------------------------------------------------------
    # macOS Implementation (Quartz CGEventTap)
    # -------------------------------------------------------------------------
    def _tap_callback(self, proxy, type_, event, refcon):
        """Quartz event tap callback. Returns event untouched."""
        t_recv_ns = time.perf_counter_ns()

        if Quartz is None:
            return event

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
                flags = Quartz.CGEventGetFlags(event)
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

        return event

    def _run_tap_thread(self):
        """Initializes Quartz CGEventTap on macOS."""
        if Quartz is None:
            logger.error("Quartz module is not available.")
            self._is_running = False
            return

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

    # -------------------------------------------------------------------------
    # Windows Implementation (WH_KEYBOARD_LL)
    # -------------------------------------------------------------------------
    def _run_windows_hook_thread(self):
        """Initializes WH_KEYBOARD_LL hook and runs Windows message pump."""
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            WH_KEYBOARD_LL = 13
            WM_KEYDOWN = 0x0100
            WM_KEYUP = 0x0101
            WM_SYSKEYDOWN = 0x0104
            WM_SYSKEYUP = 0x0105

            class KBDLLHOOKSTRUCT(ctypes.Structure):
                _fields_ = [
                    ("vkCode", wintypes.DWORD),
                    ("scanCode", wintypes.DWORD),
                    ("flags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", ctypes.c_ulong),
                ]

            HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

            def hook_proc(nCode, wParam, lParam):
                if nCode >= 0 and self._is_running:
                    t_recv_ns = time.perf_counter_ns()
                    try:
                        kbd = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                        vk_code = kbd.vkCode
                        flags = kbd.flags
                        is_repeat = bool(flags & 0x40000000)

                        ev_type = None
                        if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                            ev_type = EventType.KEY_DOWN
                        elif wParam in (WM_KEYUP, WM_SYSKEYUP):
                            ev_type = EventType.KEY_UP

                        if ev_type and self.on_key_event:
                            filtered = self.event_filter.filter_event(
                                event_type=ev_type,
                                keycode=vk_code,
                                is_autorepeat=is_repeat,
                                timestamp_ns=t_recv_ns
                            )
                            if filtered:
                                self.on_key_event(filtered)
                    except Exception as err:
                        logger.error(f"Error in Windows hook proc: {err}")

                return user32.CallNextHookEx(None, nCode, wParam, lParam)

            self._win_hook_proc = HOOKPROC(hook_proc)
            self._win_thread_id = kernel32.GetCurrentThreadId()

            self._win_hook = user32.SetWindowsHookExW(
                WH_KEYBOARD_LL,
                self._win_hook_proc,
                kernel32.GetModuleHandleW(None),
                0
            )

            if not self._win_hook:
                self.last_error = "Failed to install Windows WH_KEYBOARD_LL hook."
                logger.error(self.last_error)
                self._is_running = False
                return

            logger.info("Windows WH_KEYBOARD_LL hook active and pumping messages.")
            msg = wintypes.MSG()
            while self._is_running and user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

            if self._win_hook:
                user32.UnhookWindowsHookEx(self._win_hook)
                self._win_hook = None
        except Exception as e:
            logger.error(f"Windows keyboard hook fatal error: {e}")
            self.last_error = str(e)
        finally:
            self._is_running = False
