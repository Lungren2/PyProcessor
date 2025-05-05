"""
Audit logging for PyProcessor.

This module provides audit logging functionality for security events.
"""

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pyprocessor.utils.file_system.path_utils import (
    ensure_dir_exists,
    get_user_data_dir,
    normalize_path,
)
from pyprocessor.utils.logging.log_manager import get_logger


class AuditLogger:
    """
    Audit logger for security events.

    This class provides audit logging functionality for authentication,
    authorization, and other security-related events.
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        """Create a new instance of AuditLogger or return the existing one."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AuditLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the audit logger."""
        # Only initialize once
        if self._initialized:
            return

        # Get logger
        self.logger = get_logger()

        # Initialize default paths
        self.data_dir = Path(get_user_data_dir()) / "security"
        self.audit_log_dir = self.data_dir / "audit_logs"

        # Initialize configuration
        self.enabled = True
        self.log_to_file = True
        self.log_to_console = True
        self.log_rotation_size = 10 * 1024 * 1024  # 10 MB
        self.log_retention_days = 90  # 90 days

        # Initialize log file
        self.current_log_file = None
        self.current_log_size = 0

        # Mark as initialized
        self._initialized = True
        self.logger.debug("Audit logger initialized")

    def initialize(self, config=None):
        """
        Initialize the audit logger with configuration.

        Args:
            config: Configuration object or dictionary
        """
        # Apply configuration if provided
        if config:
            if hasattr(config, "get"):
                # Config is a dictionary-like object
                self.enabled = config.get(
                    "security.audit_logging.enabled", self.enabled
                )
                self.log_to_file = config.get(
                    "security.audit_logging.log_to_file", self.log_to_file
                )
                self.log_to_console = config.get(
                    "security.audit_logging.log_to_console", self.log_to_console
                )
                self.log_rotation_size = config.get(
                    "security.audit_logging.log_rotation_size", self.log_rotation_size
                )
                self.log_retention_days = config.get(
                    "security.audit_logging.log_retention_days", self.log_retention_days
                )

                # Get data directory from config if available
                data_dir = config.get("security.data_dir")
                if data_dir:
                    self.data_dir = Path(normalize_path(data_dir))
                    self.audit_log_dir = self.data_dir / "audit_logs"

        # Ensure audit log directory exists
        if self.log_to_file:
            ensure_dir_exists(self.audit_log_dir)
            self._init_log_file()
            self._cleanup_old_logs()

        self.logger.info("Audit logger initialized with configuration")

    def shutdown(self):
        """Shutdown the audit logger."""
        self.logger.info("Audit logger shutdown")

    def _init_log_file(self):
        """Initialize the current log file."""
        # Generate log file name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.audit_log_dir / f"audit_{timestamp}.log"

        self.current_log_file = log_file
        self.current_log_size = 0

        # Create log file with header
        with open(log_file, "w") as f:
            f.write(f"# PyProcessor Audit Log\n")
            f.write(f"# Created: {datetime.now().isoformat()}\n")
            f.write(f"# Format: JSON\n")
            f.write("\n")

    def _rotate_log_file(self):
        """Rotate the log file if it exceeds the maximum size."""
        if not self.current_log_file or not self.current_log_file.exists():
            self._init_log_file()
            return

        # Check if log file size exceeds the maximum size
        if self.current_log_size >= self.log_rotation_size:
            self._init_log_file()

    def _cleanup_old_logs(self):
        """Clean up old log files based on retention policy."""
        try:
            # Get all log files
            log_files = list(self.audit_log_dir.glob("audit_*.log"))

            # Sort by modification time (oldest first)
            log_files.sort(key=lambda f: f.stat().st_mtime)

            # Calculate cutoff time
            cutoff_time = time.time() - (self.log_retention_days * 24 * 60 * 60)

            # Delete old log files
            deleted_count = 0
            for log_file in log_files:
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    deleted_count += 1

            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} old audit log files")

        except Exception as e:
            self.logger.error(f"Failed to clean up old audit logs: {e}")

    def _log_event(self, event_type: str, **kwargs):
        """
        Log an event to the audit log.

        Args:
            event_type: Event type
            **kwargs: Event data
        """
        if not self.enabled:
            return

        # Create event data
        event_data = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            **kwargs,
        }

        # Convert to JSON
        event_json = json.dumps(event_data)

        # Log to console
        if self.log_to_console:
            self.logger.info(f"AUDIT: {event_json}")

        # Log to file
        if self.log_to_file:
            try:
                # Rotate log file if needed
                self._rotate_log_file()

                # Write to log file
                with open(self.current_log_file, "a") as f:
                    f.write(f"{event_json}\n")

                # Update log size
                self.current_log_size += len(event_json) + 1

            except Exception as e:
                self.logger.error(f"Failed to write to audit log: {e}")

    def log_auth_event(self, event_type: str, **kwargs):
        """
        Log an authentication event.

        Args:
            event_type: Event type
            **kwargs: Event data
        """
        self._log_event(f"auth.{event_type}", **kwargs)

    def log_access_event(self, event_type: str, **kwargs):
        """
        Log an access control event.

        Args:
            event_type: Event type
            **kwargs: Event data
        """
        self._log_event(f"access.{event_type}", **kwargs)

    def log_admin_event(self, event_type: str, **kwargs):
        """
        Log an administrative event.

        Args:
            event_type: Event type
            **kwargs: Event data
        """
        self._log_event(f"admin.{event_type}", **kwargs)

    def log_security_event(self, event_type: str, **kwargs):
        """
        Log a security event.

        Args:
            event_type: Event type
            **kwargs: Event data
        """
        self._log_event(f"security.{event_type}", **kwargs)

    def get_audit_logs(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        event_types: Optional[List[str]] = None,
        username: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get audit logs.

        Args:
            start_time: Start time (Unix timestamp)
            end_time: End time (Unix timestamp)
            event_types: List of event types to filter by
            username: Username to filter by
            limit: Maximum number of logs to return

        Returns:
            List[Dict[str, Any]]: List of audit log entries
        """
        if not self.log_to_file:
            return []

        logs = []

        try:
            # Get all log files
            log_files = list(self.audit_log_dir.glob("audit_*.log"))

            # Sort by modification time (newest first)
            log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

            # Process log files
            for log_file in log_files:
                if len(logs) >= limit:
                    break

                with open(log_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue

                        try:
                            log_entry = json.loads(line)

                            # Parse timestamp
                            timestamp = datetime.fromisoformat(
                                log_entry["timestamp"]
                            ).timestamp()

                            # Apply filters
                            if start_time and timestamp < start_time:
                                continue
                            if end_time and timestamp > end_time:
                                continue
                            if event_types and not any(
                                log_entry["event_type"].startswith(et)
                                for et in event_types
                            ):
                                continue
                            if username and log_entry.get("username") != username:
                                continue

                            logs.append(log_entry)

                            if len(logs) >= limit:
                                break

                        except Exception:
                            # Skip invalid log entries
                            continue

        except Exception as e:
            self.logger.error(f"Failed to get audit logs: {e}")

        return logs


def get_audit_logger() -> AuditLogger:
    """
    Get the audit logger instance.

    Returns:
        AuditLogger: Audit logger instance
    """
    return AuditLogger()


def log_auth_event(event_type: str, **kwargs):
    """
    Log an authentication event.

    Args:
        event_type: Event type
        **kwargs: Event data
    """
    get_audit_logger().log_auth_event(event_type, **kwargs)


def log_access_event(event_type: str, **kwargs):
    """
    Log an access control event.

    Args:
        event_type: Event type
        **kwargs: Event data
    """
    get_audit_logger().log_access_event(event_type, **kwargs)


def log_admin_event(event_type: str, **kwargs):
    """
    Log an administrative event.

    Args:
        event_type: Event type
        **kwargs: Event data
    """
    get_audit_logger().log_admin_event(event_type, **kwargs)


def log_security_event(event_type: str, **kwargs):
    """
    Log a security event.

    Args:
        event_type: Event type
        **kwargs: Event data
    """
    get_audit_logger().log_security_event(event_type, **kwargs)
