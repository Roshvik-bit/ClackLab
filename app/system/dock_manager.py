"""
macOS Dock visibility and NSApplication activation policy manager.
Allows ClackLab to run as a clean accessory / menu bar app (hidden from Dock)
or as a standard regular application (visible in Dock), dynamically controllable
by user preference.
"""

import sys
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from AppKit import (
        NSApplication,
        NSApplicationActivationPolicyRegular,
        NSApplicationActivationPolicyAccessory
    )
    HAS_APPKIT = True
except Exception as e:
    HAS_APPKIT = False
    logger.debug(f"AppKit not available for Dock management: {e}")


class DockManager:
    """Manages application visibility in the macOS Dock."""

    @staticmethod
    def is_dock_visible() -> bool:
        """Returns True if the application currently appears in the macOS Dock."""
        if not HAS_APPKIT or sys.platform != "darwin":
            return True
        try:
            ns_app = NSApplication.sharedApplication()
            return ns_app.activationPolicy() == NSApplicationActivationPolicyRegular
        except Exception as e:
            logger.debug(f"Failed to query NSApplication activation policy: {e}")
            return True

    @staticmethod
    def set_dock_visible(visible: bool) -> bool:
        """
        Dynamically adjusts whether ClackLab appears in the macOS Dock.
        
        Args:
            visible: If True, uses NSApplicationActivationPolicyRegular (shows in Dock).
                     If False, uses NSApplicationActivationPolicyAccessory (removes from Dock,
                     leaving the app active in the macOS menu bar / status item).
        """
        if not HAS_APPKIT or sys.platform != "darwin":
            logger.debug("Dock visibility management skipped (non-macOS or AppKit unavailable).")
            return False

        try:
            ns_app = NSApplication.sharedApplication()
            policy = NSApplicationActivationPolicyRegular if visible else NSApplicationActivationPolicyAccessory
            current_policy = ns_app.activationPolicy()
            if current_policy == policy:
                return True

            success = ns_app.setActivationPolicy_(policy)
            logger.info(f"macOS Dock visibility updated to {visible} (policy={policy}, success={success})")
            return bool(success)
        except Exception as e:
            logger.error(f"Failed to update macOS Dock activation policy: {e}")
            return False
