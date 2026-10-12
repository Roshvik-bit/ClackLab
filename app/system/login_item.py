"""
macOS Launch at Login manager for ClackLab.

Integrates with modern macOS SMAppService (macOS 13+ Ventura, Sonoma, Sequoia)
and provides backward-compatible fallback to AppleScript System Events and user LaunchAgents.
"""

import os
import sys
import subprocess
import logging
from typing import Optional, Tuple
from .diagnostics_logger import DiagnosticsLogger

logger = logging.getLogger(__name__)

APP_NAME = "ClackLab"
LAUNCH_AGENT_LABEL = "com.clacklab.macos"
LAUNCH_AGENT_PATH = os.path.expanduser(f"~/Library/LaunchAgents/{LAUNCH_AGENT_LABEL}.plist")

# Test for modern SMAppService availability (macOS 13+)
try:
    from ServiceManagement import (
        SMAppService,
        SMAppServiceStatusNotRegistered,
        SMAppServiceStatusEnabled,
        SMAppServiceStatusRequiresApproval,
        SMAppServiceStatusNotFound
    )
    HAS_SM_APP_SERVICE = True
except Exception:
    HAS_SM_APP_SERVICE = False


class LoginItemManager:
    """Manages automatic startup on macOS login across modern and legacy APIs."""

    last_error: Optional[str] = None

    @staticmethod
    def get_app_bundle_path() -> Optional[str]:
        """Locates the ClackLab .app bundle path across installed and development locations."""
        exec_path = os.path.abspath(sys.executable)
        if ".app/Contents/MacOS" in exec_path:
            bundle_path = exec_path.split(".app/Contents/MacOS")[0] + ".app"
            if os.path.exists(bundle_path):
                return bundle_path

        if os.path.exists("/Applications/ClackLab.app"):
            return "/Applications/ClackLab.app"

        user_apps = os.path.expanduser("~/Applications/ClackLab.app")
        if os.path.exists(user_apps):
            return user_apps

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        dist_app = os.path.join(base_dir, "dist", "ClackLab.app")
        if os.path.exists(dist_app):
            return dist_app

        return None

    @classmethod
    def get_registration_status(cls, app_name: str = APP_NAME) -> Tuple[bool, str]:
        """
        Returns (is_enabled, status_message) reflecting real OS registration.
        """
        if sys.platform != "darwin":
            return False, "Launch at Login is only supported on macOS."

        # 1. Try SMAppService if inside an app bundle
        if HAS_SM_APP_SERVICE and cls.get_app_bundle_path():
            try:
                service = SMAppService.mainAppService()
                status = service.status()
                if status == SMAppServiceStatusEnabled:
                    return True, "Enabled (SMAppService)"
                elif status == SMAppServiceStatusRequiresApproval:
                    return False, "Requires user approval in System Settings > Login Items"
                elif status == SMAppServiceStatusNotRegistered:
                    pass  # Check fallback
            except Exception as e:
                logger.debug(f"SMAppService status check failed: {e}")

        # 2. Check AppleScript System Events login items
        try:
            cmd = ['osascript', '-e', 'tell application "System Events" to get name of every login item']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout:
                items = [item.strip().lower() for item in result.stdout.split(",") if item.strip()]
                if app_name.lower() in items:
                    return True, "Enabled (System Events)"
        except Exception as e:
            logger.debug(f"Could not query login items via System Events: {e}")

        # 3. Check LaunchAgent plist
        if os.path.exists(LAUNCH_AGENT_PATH):
            return True, "Enabled (LaunchAgent)"

        return False, "Disabled"

    @classmethod
    def is_launch_at_login_enabled(cls, app_name: str = APP_NAME) -> bool:
        enabled, _ = cls.get_registration_status(app_name)
        return enabled

    @classmethod
    def enable_launch_at_login(cls, app_path: Optional[str] = None, app_name: str = APP_NAME) -> bool:
        """Registers ClackLab to launch automatically on macOS login."""
        if sys.platform != "darwin":
            cls.last_error = "Launch at login is only supported on macOS."
            return False

        target_path = app_path or cls.get_app_bundle_path()
        if not target_path or not os.path.exists(target_path):
            cls.last_error = "ClackLab application bundle was not found."
            logger.error(f"Cannot enable launch at login: {cls.last_error}")
            DiagnosticsLogger.log_event("LOGIN_ITEM_FAILED", {"reason": cls.last_error}, level=logging.ERROR)
            return False

        # 1. Primary Modern Method: SMAppService on macOS 13+
        if HAS_SM_APP_SERVICE:
            try:
                service = SMAppService.mainAppService()
                success, error = service.registerAndReturnError_(None)
                if success:
                    cls.last_error = None
                    DiagnosticsLogger.log_event("LOGIN_ITEM_REGISTERED", {"method": "SMAppService", "path": target_path})
                    return True
                else:
                    err_msg = str(error) if error else "SMAppService registration failed"
                    logger.debug(f"SMAppService registration note: {err_msg}")
            except Exception as e:
                logger.debug(f"SMAppService call error: {e}")

        # 2. Secondary Method: Native AppleScript System Events
        try:
            cls._remove_system_events_item(app_name)
            escaped_path = target_path.replace('"', '\\"')
            add_script = (
                f'tell application "System Events" to make login item at end with properties '
                f'{{path:"{escaped_path}", hidden:true, name:"{app_name}"}}'
            )
            result = subprocess.run(['osascript', '-e', add_script], capture_output=True, text=True, timeout=7)
            if result.returncode == 0:
                cls.last_error = None
                DiagnosticsLogger.log_event("LOGIN_ITEM_REGISTERED", {"method": "SystemEvents", "path": target_path})
                return True
        except Exception as e:
            logger.debug(f"AppleScript System Events fallback note: {e}")

        # 3. Tertiary Method: User LaunchAgent plist with --background argument
        try:
            success = cls._create_launch_agent(target_path)
            if success:
                cls.last_error = None
                DiagnosticsLogger.log_event("LOGIN_ITEM_REGISTERED", {"method": "LaunchAgent", "path": target_path})
                return True
        except Exception as e:
            cls.last_error = str(e)
            logger.error(f"LaunchAgent fallback failed: {e}")

        DiagnosticsLogger.log_event("LOGIN_ITEM_FAILED", {"reason": cls.last_error}, level=logging.ERROR)
        return False

    @classmethod
    def disable_launch_at_login(cls, app_name: str = APP_NAME) -> bool:
        """Unregisters ClackLab from macOS startup."""
        if sys.platform != "darwin":
            return False

        # 1. SMAppService unregister
        if HAS_SM_APP_SERVICE:
            try:
                service = SMAppService.mainAppService()
                service.unregisterAndReturnError_(None)
            except Exception as e:
                logger.debug(f"SMAppService unregister note: {e}")

        # 2. System Events remove
        cls._remove_system_events_item(app_name)

        # 3. LaunchAgent remove
        cls._remove_launch_agent()

        DiagnosticsLogger.log_event("LOGIN_ITEM_UNREGISTERED")
        return True

    @classmethod
    def set_launch_at_login(cls, enabled: bool, app_path: Optional[str] = None, app_name: str = APP_NAME) -> bool:
        if enabled:
            return cls.enable_launch_at_login(app_path=app_path, app_name=app_name)
        else:
            return cls.disable_launch_at_login(app_name=app_name)

    @staticmethod
    def _remove_system_events_item(app_name: str):
        try:
            del_script = f'tell application "System Events" to delete (every login item whose name is "{app_name}")'
            subprocess.run(['osascript', '-e', del_script], capture_output=True, text=True, timeout=5)
        except Exception as e:
            logger.debug(f"Error deleting login item '{app_name}': {e}")

    @staticmethod
    def _create_launch_agent(target_path: str) -> bool:
        os.makedirs(os.path.dirname(LAUNCH_AGENT_PATH), exist_ok=True)
        
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LAUNCH_AGENT_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/open</string>
        <string>-a</string>
        <string>{target_path}</string>
        <string>--args</string>
        <string>--background</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>ProcessType</key>
    <string>Interactive</string>
</dict>
</plist>
"""
        with open(LAUNCH_AGENT_PATH, "w", encoding="utf-8") as f:
            f.write(plist_content)

        try:
            subprocess.run(["launchctl", "load", "-w", LAUNCH_AGENT_PATH], capture_output=True, timeout=5)
        except Exception as e:
            logger.debug(f"launchctl load warning: {e}")

        logger.info(f"Created LaunchAgent with --background at: {LAUNCH_AGENT_PATH}")
        return True

    @staticmethod
    def _remove_launch_agent():
        if os.path.exists(LAUNCH_AGENT_PATH):
            try:
                subprocess.run(["launchctl", "unload", "-w", LAUNCH_AGENT_PATH], capture_output=True, timeout=5)
            except Exception as e:
                logger.debug(f"launchctl unload warning: {e}")

            try:
                os.remove(LAUNCH_AGENT_PATH)
                logger.info(f"Removed LaunchAgent at: {LAUNCH_AGENT_PATH}")
            except Exception as e:
                logger.warning(f"Could not remove LaunchAgent plist: {e}")
