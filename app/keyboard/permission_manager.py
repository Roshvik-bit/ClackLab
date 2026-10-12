"""
macOS Accessibility & Input Monitoring permissions manager.
"""

import sys
import ctypes
import subprocess
import logging

logger = logging.getLogger(__name__)

class PermissionManager:
    """Detects and guides macOS Accessibility trust status without bypassing OS security."""

    @staticmethod
    def is_accessibility_granted() -> bool:
        """
        Queries native macOS ApplicationServices and tests CGEventTap creation
        to determine if global background keyboard monitoring is authorized.
        """
        if sys.platform != "darwin":
            return True

        # 1. Primary check via ApplicationServices
        try:
            app_services = ctypes.cdll.LoadLibrary(
                "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
            )
            if app_services.AXIsProcessTrusted():
                return True
        except Exception as e:
            logger.warning(f"Could not query AXIsProcessTrusted: {e}")

        # 2. Ground-truth fallback probe: test if Quartz allows tap creation
        try:
            import Quartz
            mask = (1 << Quartz.kCGEventKeyDown)
            tap = Quartz.CGEventTapCreate(
                Quartz.kCGSessionEventTap,
                Quartz.kCGHeadInsertEventTap,
                Quartz.kCGEventTapOptionListenOnly,
                mask,
                lambda p, t, e, r: e,
                None
            )
            if tap is not None:
                Quartz.CFRelease(tap)
                return True
        except Exception:
            pass

        return False

    @staticmethod
    def request_accessibility_prompt() -> bool:
        """
        Triggers the native macOS system dialog prompting the user to grant Accessibility
        and registers the application in System Settings > Privacy & Security > Accessibility.
        """
        if sys.platform != "darwin":
            return True

        try:
            app_services = ctypes.cdll.LoadLibrary(
                "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
            )
            core_foundation = ctypes.cdll.LoadLibrary(
                "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
            )

            kAXTrustedCheckOptionPrompt = ctypes.c_void_p.in_dll(app_services, "kAXTrustedCheckOptionPrompt")
            kCFBooleanTrue = ctypes.c_void_p.in_dll(core_foundation, "kCFBooleanTrue")
            kCFTypeDictionaryKeyCallBacks = ctypes.c_void_p.in_dll(core_foundation, "kCFTypeDictionaryKeyCallBacks")
            kCFTypeDictionaryValueCallBacks = ctypes.c_void_p.in_dll(core_foundation, "kCFTypeDictionaryValueCallBacks")

            keys = (ctypes.c_void_p * 1)(kAXTrustedCheckOptionPrompt.value)
            values = (ctypes.c_void_p * 1)(kCFBooleanTrue.value)

            core_foundation.CFDictionaryCreate.restype = ctypes.c_void_p
            core_foundation.CFDictionaryCreate.argtypes = [
                ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
                ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p
            ]

            options = core_foundation.CFDictionaryCreate(
                None, keys, values, 1,
                ctypes.byref(kCFTypeDictionaryKeyCallBacks),
                ctypes.byref(kCFTypeDictionaryValueCallBacks)
            )

            app_services.AXIsProcessTrustedWithOptions.restype = ctypes.c_bool
            app_services.AXIsProcessTrustedWithOptions.argtypes = [ctypes.c_void_p]
            trusted = app_services.AXIsProcessTrustedWithOptions(options)

            core_foundation.CFRelease.argtypes = [ctypes.c_void_p]
            core_foundation.CFRelease(options)
            return bool(trusted)
        except Exception as e:
            logger.error(f"Error requesting accessibility prompt: {e}")
            PermissionManager.open_accessibility_settings()
            return PermissionManager.is_accessibility_granted()

    @staticmethod
    def open_accessibility_settings():
        """Opens macOS System Settings directly to Privacy & Security -> Accessibility."""
        try:
            subprocess.run([
                "open",
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
            ], check=False)
        except Exception as e:
            logger.error(f"Failed to open System Settings: {e}")

    @staticmethod
    def get_instructions() -> str:
        return (
            "1. Open System Settings > Privacy & Security > Accessibility.\n"
            "2. Find ClackLab (or your Terminal / Python environment) in the list.\n"
            "3. Toggle the switch to ON to allow global keyboard listening.\n"
            "4. Return to ClackLab and click 'Verify Permission'."
        )

    @staticmethod
    def restart_app():
        """Restarts ClackLab so newly granted macOS permissions take immediate effect."""
        import sys, os, subprocess
        if getattr(sys, 'frozen', False):
            app_path = os.path.abspath(sys.argv[0])
            if ".app/Contents/MacOS" in app_path:
                bundle_path = app_path.split(".app/Contents/MacOS")[0] + ".app"
                subprocess.Popen(["open", "-n", bundle_path])
            else:
                subprocess.Popen([app_path] + sys.argv[1:])
        else:
            subprocess.Popen([sys.executable] + sys.argv)
        from PySide6.QtWidgets import QApplication
        q_app = QApplication.instance()
        if q_app:
            q_app.quit()
        else:
            sys.exit(0)
