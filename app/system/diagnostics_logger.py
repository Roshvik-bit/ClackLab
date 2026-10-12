"""
Structured lifecycle diagnostics logging for ClackLab.
Records high-level operational events, health states, and error diagnostics
without capturing sensitive keystrokes, personal input, or typed text.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import shutil
from typing import Optional

DEFAULT_LOG_DIR = os.path.expanduser("~/Library/Application Support/ClackLab/logs")
LOG_FILENAME = "clacklab_lifecycle.log"
MAX_LOG_BYTES = 2 * 1024 * 1024  # 2 MB
BACKUP_COUNT = 3

logger = logging.getLogger("clacklab.lifecycle")


class DiagnosticsLogger:
    """Manages thread-safe, bounded, privacy-preserving lifecycle logging."""

    _initialized = False
    _log_path = os.path.join(DEFAULT_LOG_DIR, LOG_FILENAME)

    @classmethod
    def setup(cls, log_dir: Optional[str] = None):
        if cls._initialized:
            return

        target_dir = log_dir or DEFAULT_LOG_DIR
        os.makedirs(target_dir, exist_ok=True)
        cls._log_path = os.path.join(target_dir, LOG_FILENAME)

        handler = RotatingFileHandler(
            cls._log_path,
            maxBytes=MAX_LOG_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8"
        )
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            logger.addHandler(handler)

        cls._initialized = True
        cls.log_event("DIAGNOSTICS_INITIALIZED", {
            "pid": os.getpid(),
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "log_path": cls._log_path
        })

    @classmethod
    def log_event(cls, event_name: str, details: Optional[dict] = None, level: int = logging.INFO):
        """Logs a lifecycle milestone. Strictly avoids any keystroke / input recording."""
        if not cls._initialized:
            cls.setup()

        detail_str = ""
        if details:
            safe_details = {k: v for k, v in details.items() if "key" not in k.lower() or k == "key_category"}
            items = [f"{k}={v}" for k, v in safe_details.items()]
            detail_str = f" | {', '.join(items)}"

        message = f"[{event_name}]{detail_str}"
        logger.log(level, message)

    @classmethod
    def get_log_file_path(cls) -> str:
        return cls._log_path

    @classmethod
    def get_recent_logs(cls, max_lines: int = 150) -> str:
        """Returns the most recent lines from the diagnostics log."""
        if not os.path.exists(cls._log_path):
            return "No diagnostics logs recorded yet."

        try:
            with open(cls._log_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            return "".join(lines[-max_lines:])
        except Exception as e:
            return f"Error reading diagnostics logs: {e}"

    @classmethod
    def export_logs(cls, target_path: str) -> bool:
        """Copies the active diagnostics log to an export path chosen by the user."""
        if not os.path.exists(cls._log_path):
            return False
        try:
            shutil.copy2(cls._log_path, target_path)
            cls.log_event("LOGS_EXPORTED", {"destination": target_path})
            return True
        except Exception as e:
            cls.log_event("LOGS_EXPORT_FAILED", {"error": str(e)}, level=logging.ERROR)
            return False

    @classmethod
    def clear_logs(cls):
        """Clears the current log file."""
        if os.path.exists(cls._log_path):
            try:
                with open(cls._log_path, "w", encoding="utf-8") as f:
                    f.truncate(0)
                cls.log_event("LOGS_CLEARED")
            except Exception as e:
                logger.error(f"Failed to clear logs: {e}")
