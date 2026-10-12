"""
macOS Launch at Login manager for ClackLab.

Integrates with native macOS System Settings (General > Login Items & Extensions)
using AppleScript System Events, with fallback support for user LaunchAgents.
"""

import os
import sys
import subprocess
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

APP_NAME = "ClackLab"
LAUNCH_AGENT_LABEL = "com.clacklab.macos"
LAUNCH_AGENT_PATH = os.path.expanduser(f"~/Library/LaunchAgents/{LAUNCH_AGENT_LABEL}.plist")


class LoginItemManager:
    """Manages automatic startup on macOS login."""

    @staticmethod
    def get_app_bundle_path() -> Optional[str]:
        """
        Locates the ClackLab .app bundle path across installed and development locations.
        """
        # 1. Running inside a packaged macOS .app bundle
        exec_path = os.path.abspath(sys.executable)
        if ".app/Contents/MacOS" in exec_path:
            bundle_path = exec_path.split(".app/Contents/MacOS")[0] + ".app"
            if os.path.exists(bundle_path):
                return bundle_path

        # 2. Installed in system /Applications
        if os.path.exists("/Applications/ClackLab.app"):
            return "/Applications/ClackLab.app"

        # 3. Installed in user ~/Applications
        user_apps = os.path.expanduser("~/Applications/ClackLab.app")
        if os.path.exists(user_apps):
            return user_apps

        # 4. Built distribution bundle in workspace
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        dist_app = os.path.join(base_dir, "dist", "ClackLab.app")
        if os.path.exists(dist_app):
            return dist_app

        return None

    @classmethod
    def is_launch_at_login_enabled(cls, app_name: str = APP_NAME) -> bool:
        """
        Checks whether ClackLab is currently registered to launch at login.
        """
        if sys.platform != "darwin":
            return False

        # 1. Check AppleScript System Events login items
        try:
            cmd = ['osascript', '-e', 'tell application "System Events" to get name of every login item']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout:
                items = [item.strip().lower() for item in result.stdout.split(",") if item.strip()]
                if app_name.lower() in items:
                    return True
        except Exception as e:
            logger.debug(f"Could not query login items via System Events: {e}")

        # 2. Check LaunchAgent plist
        if os.path.exists(LAUNCH_AGENT_PATH):
            return True

        return False

    @classmethod
    def enable_launch_at_login(cls, app_path: Optional[str] = None, app_name: str = APP_NAME) -> bool:
        """
        Registers ClackLab to launch automatically on macOS login.
        Appears in macOS System Settings > General > Login Items & Extensions.
        """
        if sys.platform != "darwin":
            logger.warning("Launch at login is only supported on macOS.")
            return False

        target_path = app_path or cls.get_app_bundle_path()
        if not target_path or not os.path.exists(target_path):
            logger.error("Cannot enable launch at login: ClackLab application bundle was not found.")
            return False

        success = False

        # 1. Primary Method: Native AppleScript System Events
        try:
            # First remove existing entry if any to avoid duplicates
            cls._remove_system_events_item(app_name)

            # Register new login item with target path
            escaped_path = target_path.replace('"', '\\"')
            add_script = (
                f'tell application "System Events" to make login item at end with properties '
                f'{{path:"{escaped_path}", hidden:false, name:"{app_name}"}}'
            )
            result = subprocess.run(['osascript', '-e', add_script], capture_output=True, text=True, timeout=7)
            if result.returncode == 0:
                logger.info(f"Registered '{app_name}' login item at: {target_path}")
                success = True
            else:
                logger.warning(f"AppleScript login item registration failed: {result.stderr.strip()}")
        except Exception as e:
            logger.warning(f"Error registering login item with System Events: {e}")

        # 2. Fallback / Complementary: User LaunchAgent plist if System Events failed
        if not success:
            try:
                success = cls._create_launch_agent(target_path)
            except Exception as e:
                logger.error(f"Failed to create LaunchAgent fallback: {e}")

        return success

    @classmethod
    def disable_launch_at_login(cls, app_name: str = APP_NAME) -> bool:
        """
        Unregisters ClackLab from macOS startup.
        """
        if sys.platform != "darwin":
            return False

        # 1. Remove from System Events login items
        cls._remove_system_events_item(app_name)

        # 2. Remove LaunchAgent plist if present
        cls._remove_launch_agent()

        return True

    @classmethod
    def set_launch_at_login(cls, enabled: bool, app_path: Optional[str] = None, app_name: str = APP_NAME) -> bool:
        """Convenience method to set launch at login state."""
        if enabled:
            return cls.enable_launch_at_login(app_path=app_path, app_name=app_name)
        else:
            return cls.disable_launch_at_login(app_name=app_name)

    @staticmethod
    def _remove_system_events_item(app_name: str):
        """Removes all login items with matching name via AppleScript."""
        try:
            del_script = f'tell application "System Events" to delete (every login item whose name is "{app_name}")'
            subprocess.run(['osascript', '-e', del_script], capture_output=True, text=True, timeout=5)
        except Exception as e:
            logger.debug(f"Error deleting login item '{app_name}': {e}")

    @staticmethod
    def _create_launch_agent(target_path: str) -> bool:
        """Creates and loads a user LaunchAgent property list."""
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

        logger.info(f"Created LaunchAgent at: {LAUNCH_AGENT_PATH}")
        return True

    @staticmethod
    def _remove_launch_agent():
        """Unloads and removes the user LaunchAgent plist."""
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
