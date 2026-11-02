"""Thread-safe logging system with secret redaction and UI subscriber support."""

import os
import threading
import datetime
from pathlib import Path
from typing import Callable, List, Optional

from devpilot.core.security import redact_secrets


class DevPilotLogger:
    def __init__(self, log_file: Optional[Path] = None):
        self._lock = threading.Lock()
        self._subscribers: List[Callable[[str, str, str], None]] = []
        self._buffer: List[str] = []
        self.log_file = log_file

        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def subscribe(self, callback: Callable[[str, str, str], None]):
        """Subscribe a callback (timestamp, level, message) to receive live logs."""
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[str, str, str], None]):
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def log(self, level: str, message: str):
        """Emit a sanitized log line."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        sanitized = redact_secrets(message)
        formatted_line = f"[{timestamp}] [{level.upper()}] {sanitized}"

        with self._lock:
            self._buffer.append(formatted_line)
            if len(self._buffer) > 1000:
                self._buffer.pop(0)

            # File append
            if self.log_file:
                try:
                    with open(self.log_file, "a", encoding="utf-8") as f:
                        f.write(formatted_line + "\n")
                except Exception:
                    pass

            subscribers_copy = list(self._subscribers)

        # Notify subscribers outside the lock to prevent deadlock with UI
        for sub in subscribers_copy:
            try:
                sub(timestamp, level.upper(), sanitized)
            except Exception:
                pass

    def info(self, msg: str):
        self.log("INFO", msg)

    def warn(self, msg: str):
        self.log("WARN", msg)

    def error(self, msg: str):
        self.log("ERROR", msg)

    def success(self, msg: str):
        self.log("SUCCESS", msg)

    def get_history(self) -> List[str]:
        with self._lock:
            return list(self._buffer)

    def clear(self):
        with self._lock:
            self._buffer.clear()


# Global logger instance
logger = DevPilotLogger()
