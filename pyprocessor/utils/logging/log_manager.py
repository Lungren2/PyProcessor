"""
Centralized logging manager for PyProcessor.

This module provides a singleton logger instance that can be used throughout the application.
It ensures consistent logging behavior and format across all modules.
"""

import logging
import logging.handlers
import sys
import os
import getpass
import platform
import inspect
import threading
import json
import time
import re
import gzip
import shutil
import uuid
import hashlib
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
from typing import Dict, Any, Optional, Union, List, Callable, Tuple, Iterator, Pattern
from collections import defaultdict, Counter

# Avoid circular import with path_manager
# Define simple versions of the functions we need
def ensure_dir_exists(path):
    """Ensure a directory exists, creating it if necessary."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_logs_dir():
    """Get the logs directory."""
    # Simple implementation to avoid circular imports
    base_dir = Path(__file__).parent.parent.parent
    logs_dir = base_dir / "logs"
    return logs_dir

# Thread-local storage for context information
_thread_local = threading.local()

# Global logger instance
_logger_instance = None

# Helper functions for external use
def get_logger(level=logging.INFO):
    """Get the logger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = LogManager(level=level)
    return _logger_instance

def set_context(**kwargs):
    """Set context information for the current thread."""
    logger = get_logger()
    logger.set_context(**kwargs)

def get_context(key, default=None):
    """Get context information for the current thread."""
    logger = get_logger()
    return logger.get_context(key, default)

def clear_context():
    """Clear all context information for the current thread."""
    logger = get_logger()
    logger.clear_context()

def analyze_logs(log_file=None, pattern=None, start_time=None, end_time=None):
    """Analyze logs for patterns and trends."""
    # This is a placeholder for now
    return {"analyzed": True}

def get_metrics():
    """Get logging metrics."""
    logger = get_logger()
    if hasattr(logger, 'metrics'):
        return logger.metrics
    return {}

def reset_metrics():
    """Reset logging metrics."""
    logger = get_logger()
    if hasattr(logger, 'metrics'):
        logger.metrics = {
            "log_counts": defaultdict(int),
            "error_counts": defaultdict(int),
            "performance": defaultdict(list),
            "requests": defaultdict(int),
            "start_time": datetime.now(),
            "last_reset": datetime.now()
        }
    return True


class LogManager:
    """
    Singleton logging manager for PyProcessor.

    This class provides a centralized logging system with the following features:
    - Singleton pattern to ensure only one logger instance exists
    - Consistent log format across all modules
    - Log rotation to prevent logs from consuming too much disk space
    - Context-aware logging with module and function information
    - Support for both file and console logging
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LogManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, log_dir=None, max_logs=10, max_size_mb=10, max_days=30, level=logging.INFO, app_name="pyprocessor",
                 compress_logs=True, encrypt_sensitive=False, log_format=None, console_format=None, file_format=None,
                 additional_handlers=None, log_metrics=True, correlation_id_header="X-Correlation-ID"):
        """
        Initialize the logging manager.

        Args:
            log_dir: Directory to store log files (default: pyprocessor/logs)
            max_logs: Maximum number of log files to keep (default: 10)
            max_size_mb: Maximum size of log files in MB (default: 10)
            max_days: Maximum age of log files in days (default: 30)
            level: Logging level (default: INFO)
            app_name: Application name for the logger (default: pyprocessor)
            compress_logs: Whether to compress old log files (default: True)
            encrypt_sensitive: Whether to encrypt sensitive log data (default: False)
            log_format: Custom log format (default: None, uses predefined formats)
            console_format: Custom console log format (default: None, uses predefined format)
            file_format: Custom file log format (default: None, uses predefined format)
            additional_handlers: Additional log handlers to add (default: None)
            log_metrics: Whether to collect log metrics (default: True)
            correlation_id_header: HTTP header for correlation ID (default: X-Correlation-ID)
        """
        # Only initialize once
        if self._initialized:
            return

        # Store configuration
        self.app_name = app_name
        self.max_logs = max_logs
        self.max_size_mb = max_size_mb
        self.max_days = max_days
        self.compress_logs = compress_logs
        self.encrypt_sensitive = encrypt_sensitive
        self.log_metrics = log_metrics
        self.correlation_id_header = correlation_id_header

        # Initialize metrics if enabled
        if self.log_metrics:
            self.metrics = {
                "log_counts": defaultdict(int),  # Counts by level
                "error_counts": defaultdict(int),  # Counts by error type
                "performance": defaultdict(list),  # Performance metrics
                "requests": defaultdict(int),  # Request counts
                "start_time": datetime.now(),  # Start time for metrics
                "last_reset": datetime.now()  # Last time metrics were reset
            }

        # Initialize correlation ID for the main thread
        self.set_correlation_id(str(uuid.uuid4()))

        # Determine log directory
        if log_dir is None:
            # Use the path manager to get the logs directory
            self.log_dir = get_logs_dir()
        else:
            self.log_dir = Path(log_dir)

        # Store custom formats
        self.custom_log_format = log_format
        self.custom_console_format = console_format
        self.custom_file_format = file_format

        # Store additional handlers
        self.additional_handlers = additional_handlers or []

        # Create logs directory if it doesn't exist
        ensure_dir_exists(self.log_dir)

        # Generate log filename with detailed information
        now = datetime.now()
        date_part = now.strftime("%Y-%m-%d")
        time_part = now.strftime("%H-%M-%S")

        # Get log level as a string
        if isinstance(level, str):
            level_str = level.lower()
            # Convert string level to logging level
            level_map = {
                "debug": logging.DEBUG,
                "info": logging.INFO,
                "warning": logging.WARNING,
                "warn": logging.WARNING,
                "error": logging.ERROR,
                "critical": logging.CRITICAL,
            }
            level = level_map.get(level_str, logging.INFO)
        else:
            level_map = {
                logging.DEBUG: "debug",
                logging.INFO: "info",
                logging.WARNING: "warn",
                logging.ERROR: "error",
                logging.CRITICAL: "critical",
            }
            level_str = level_map.get(level, "info")

        # Get username for the log file
        username = getpass.getuser()

        # Get system info
        system_info = platform.system().lower()

        # Create a descriptive filename
        filename = f"{self.app_name}_{date_part}_{time_part}_{level_str}_{username}_{system_info}.log"
        self.log_file = self.log_dir / filename

        # Set up logger
        self.logger = logging.getLogger(self.app_name)
        self.logger.setLevel(level)

        # Remove existing handlers if necessary
        if self.logger.hasHandlers():
            for handler in self.logger.handlers:
                self.logger.removeHandler(handler)

        # Create file handler with rotation
        self.file_handler = logging.handlers.RotatingFileHandler(
            self.log_file,
            maxBytes=self.max_size_mb * 1024 * 1024,  # Convert MB to bytes
            backupCount=5  # Keep 5 backup files
        )
        self.file_handler.setLevel(level)

        # Create console handler
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.setLevel(level)

        # Create formatters
        if self.custom_file_format:
            detailed_formatter = logging.Formatter(self.custom_file_format, "%Y-%m-%d %H:%M:%S")
        else:
            detailed_formatter = logging.Formatter(
                "[%(asctime)s][%(levelname)s][%(module)s.%(funcName)s:%(lineno)d][%(threadName)s] %(message)s",
                "%Y-%m-%d %H:%M:%S"
            )

        if self.custom_console_format:
            simple_formatter = logging.Formatter(self.custom_console_format)
        else:
            simple_formatter = logging.Formatter("[%(levelname)s][%(module)s] %(message)s")

        # Set formatters
        self.file_handler.setFormatter(detailed_formatter)
        self.console_handler.setFormatter(simple_formatter)

        # Add handlers to logger
        self.logger.addHandler(self.file_handler)
        self.logger.addHandler(self.console_handler)

        # Add additional handlers if provided
        for handler in self.additional_handlers:
            if isinstance(handler, logging.Handler):
                if self.custom_log_format:
                    handler.setFormatter(logging.Formatter(self.custom_log_format, "%Y-%m-%d %H:%M:%S"))
                else:
                    handler.setFormatter(detailed_formatter)
                self.logger.addHandler(handler)

        # Perform log rotation
        self._rotate_logs()

        # Mark as initialized
        self._initialized = True

        # Log initialization
        self.info(f"Logging initialized: {self.log_file}")

    def _rotate_logs(self):
        """Rotate old log files based on count, size, and age"""
        try:
            # Get all log files (both .log and .log.gz)
            log_files = list(self.log_dir.glob(f"{self.app_name}_*.log"))
            gz_files = list(self.log_dir.glob(f"{self.app_name}_*.log.gz"))
            all_files = log_files + gz_files

            # Get current time for age-based rotation
            now = datetime.now()
            max_age = timedelta(days=self.max_days)

            # Track files to process
            files_to_delete = []
            files_to_compress = []

            # Check each log file
            for log_file in all_files:
                try:
                    # Skip the current log file
                    if log_file == self.log_file:
                        continue

                    # Get file stats
                    stats = log_file.stat()
                    file_time = datetime.fromtimestamp(stats.st_mtime)
                    file_age = now - file_time
                    file_size_mb = stats.st_size / (1024 * 1024)  # Convert bytes to MB
                    is_compressed = log_file.suffix == ".gz"

                    # Check if file is too old
                    if file_age > max_age:
                        files_to_delete.append((log_file, "age"))
                        continue

                    # Check if file is too large
                    if file_size_mb > self.max_size_mb * 2:  # Double the max size as a safety margin
                        if not is_compressed and self.compress_logs:
                            files_to_compress.append(log_file)
                        else:
                            files_to_delete.append((log_file, "size"))
                        continue

                    # Check if file should be compressed
                    if not is_compressed and self.compress_logs and file_age > timedelta(days=1):
                        files_to_compress.append(log_file)
                except Exception as e:
                    self.logger.error(f"Error checking log file {log_file}: {str(e)}")

            # Sort remaining files by modification time (oldest first)
            remaining_files = [f for f in all_files if f not in [fd[0] for fd in files_to_delete] and f not in files_to_compress]
            remaining_files.sort(key=lambda x: x.stat().st_mtime)

            # If we have more logs than allowed, mark the oldest ones for deletion or compression
            if len(remaining_files) > self.max_logs:
                for old_log in remaining_files[:-self.max_logs]:
                    is_compressed = old_log.suffix == ".gz"
                    if not is_compressed and self.compress_logs:
                        files_to_compress.append(old_log)
                    else:
                        files_to_delete.append((old_log, "count"))

            # Compress files marked for compression
            for log_file in files_to_compress:
                try:
                    gz_file = log_file.with_suffix(".log.gz")
                    with open(log_file, "rb") as f_in:
                        with gzip.open(gz_file, "wb") as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    log_file.unlink()  # Remove the original file
                    self.logger.debug(f"Compressed log file: {log_file} -> {gz_file}")
                except Exception as e:
                    self.logger.error(f"Failed to compress log {log_file}: {str(e)}")

            # Delete all marked files
            for log_file, reason in files_to_delete:
                try:
                    log_file.unlink()
                    self.logger.debug(f"Deleted old log: {log_file} (reason: {reason})")
                except Exception as e:
                    self.logger.error(f"Failed to delete log {log_file}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error during log rotation: {str(e)}")

    def _get_caller_info(self):
        """Get information about the caller of the logging function"""
        # Get the current frame
        current_frame = inspect.currentframe()

        # Go back 3 frames to get the caller of the logging function
        # (1 for this function, 1 for the logging function, 1 for the caller)
        caller_frame = inspect.getouterframes(current_frame)[3]

        # Extract information
        module = caller_frame.frame.f_globals.get('__name__', 'unknown')
        function = caller_frame.function
        lineno = caller_frame.lineno

        return module, function, lineno

    def debug(self, message, **kwargs):
        """
        Log a debug message with optional structured data.

        Args:
            message: The log message
            **kwargs: Additional structured data to include in the log
        """
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message, **kwargs):
        """
        Log an info message with optional structured data.

        Args:
            message: The log message
            **kwargs: Additional structured data to include in the log
        """
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message, **kwargs):
        """
        Log a warning message with optional structured data.

        Args:
            message: The log message
            **kwargs: Additional structured data to include in the log
        """
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message, **kwargs):
        """
        Log an error message with optional structured data.

        Args:
            message: The log message
            **kwargs: Additional structured data to include in the log
        """
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message, **kwargs):
        """
        Log a critical message with optional structured data.

        Args:
            message: The log message
            **kwargs: Additional structured data to include in the log
        """
        self._log(logging.CRITICAL, message, **kwargs)

    def _log(self, level, message, **kwargs):
        """
        Internal method to log a message with structured data.

        Args:
            level: The log level
            message: The log message
            **kwargs: Additional structured data to include in the log
        """
        # Get context information from thread local storage
        context = {}
        for key in vars(_thread_local).keys():
            context[key] = getattr(_thread_local, key)

        # Merge context with kwargs
        data = {**context, **kwargs}

        # Update metrics if enabled
        if self.log_metrics:
            # Update log counts by level
            level_map = {
                logging.DEBUG: "debug",
                logging.INFO: "info",
                logging.WARNING: "warning",
                logging.ERROR: "error",
                logging.CRITICAL: "critical"
            }
            level_name = level_map.get(level, "unknown")
            self.metrics["log_counts"][level_name] += 1

            # Update error counts if this is an error or higher
            if level >= logging.ERROR:
                error_type = kwargs.get("error_type", "unknown")
                self.metrics["error_counts"][error_type] += 1

            # Update performance metrics if duration is provided
            if "duration" in kwargs:
                operation = kwargs.get("operation", "unknown")
                try:
                    duration = float(kwargs["duration"])
                    self.metrics["performance"][operation].append(duration)
                except (ValueError, TypeError):
                    pass

            # Update request metrics if this is a request
            if "request_path" in kwargs:
                path = kwargs["request_path"]
                self.metrics["requests"][path] += 1

        # If encrypt_sensitive is enabled, encrypt sensitive data
        if self.encrypt_sensitive and any(k in kwargs for k in ["password", "token", "secret", "key", "credential"]):
            for sensitive_key in ["password", "token", "secret", "key", "credential"]:
                if sensitive_key in kwargs:
                    # Hash the sensitive value
                    value = str(kwargs[sensitive_key])
                    hashed = hashlib.sha256(value.encode()).hexdigest()[:8]
                    kwargs[sensitive_key] = f"[REDACTED:{hashed}]"

        # If we have structured data, format it as JSON and append to message
        if data:
            try:
                json_data = json.dumps(data, default=str)
                message = f"{message} {json_data}"
            except Exception:
                # If JSON serialization fails, just append the data as a string
                message = f"{message} {str(data)}"

        # Log the message
        self.logger.log(level, message)

    def set_level(self, level):
        """Set the logging level"""
        if isinstance(level, str):
            level_map = {
                "debug": logging.DEBUG,
                "info": logging.INFO,
                "warning": logging.WARNING,
                "warn": logging.WARNING,
                "error": logging.ERROR,
                "critical": logging.CRITICAL,
            }
            level = level_map.get(level.lower(), logging.INFO)

        self.logger.setLevel(level)
        self.file_handler.setLevel(level)
        self.console_handler.setLevel(level)

    def get_log_content(self, lines=50):
        """Get the most recent log content"""
        if not self.log_file.exists():
            return "Log file not found"

        try:
            with open(self.log_file, "r") as f:
                # Read all lines and get the last 'lines' number
                all_lines = f.readlines()
                return "".join(all_lines[-lines:])
        except Exception as e:
            return f"Error reading log: {str(e)}"

    def close(self):
        """Close all handlers to release file locks"""
        try:
            # Remove and close handlers
            if self.logger.hasHandlers():
                for handler in self.logger.handlers:
                    handler.close()
                    self.logger.removeHandler(handler)
            return True
        except Exception as e:
            print(f"Error closing logger: {str(e)}")
            return False

    def set_context(self, **kwargs):
        """
        Set context information for the current thread.

        Args:
            **kwargs: Context information to store
        """
        for key, value in kwargs.items():
            setattr(_thread_local, key, value)

    def get_context(self, key, default=None):
        """
        Get context information for the current thread.

        Args:
            key: Context key to retrieve
            default: Default value if key is not found

        Returns:
            The context value or default if not found
        """
        return getattr(_thread_local, key, default)

    def clear_context(self):
        """Clear all context information for the current thread"""
        for key in list(vars(_thread_local).keys()):
            delattr(_thread_local, key)

    def set_correlation_id(self, correlation_id=None):
        """
        Set a correlation ID for the current thread.

        Args:
            correlation_id: Correlation ID to set (default: None, generates a new UUID)
        """
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        self.set_context(correlation_id=correlation_id)
        return correlation_id

    def get_correlation_id(self):
        """
        Get the correlation ID for the current thread.

        Returns:
            str: Correlation ID or None if not set
        """
        return self.get_context("correlation_id")

    # Log Filtering Methods

    def filter_logs(self, log_file=None, level=None, start_time=None, end_time=None,
                    pattern=None, correlation_id=None, limit=None):
        """
        Filter logs based on various criteria.

        Args:
            log_file: Path to the log file (default: current log file)
            level: Minimum log level to include (default: None, includes all levels)
            start_time: Start time for filtering (default: None)
            end_time: End time for filtering (default: None)
            pattern: Regex pattern to match in log messages (default: None)
            correlation_id: Correlation ID to filter by (default: None)
            limit: Maximum number of log entries to return (default: None)

        Returns:
            List of log entries matching the criteria
        """
        if log_file is None:
            log_file = self.log_file

        log_file = Path(log_file)
        if not log_file.exists():
            return []

        # Compile regex pattern if provided
        if pattern is not None:
            try:
                pattern = re.compile(pattern)
            except re.error:
                self.error(f"Invalid regex pattern: {pattern}")
                return []

        # Parse start and end times if provided as strings
        if isinstance(start_time, str):
            try:
                start_time = datetime.fromisoformat(start_time)
            except ValueError:
                self.error(f"Invalid start time format: {start_time}")
                return []

        if isinstance(end_time, str):
            try:
                end_time = datetime.fromisoformat(end_time)
            except ValueError:
                self.error(f"Invalid end time format: {end_time}")
                return []

        # Convert level to integer if provided as string
        if isinstance(level, str):
            level_map = {
                "debug": logging.DEBUG,
                "info": logging.INFO,
                "warning": logging.WARNING,
                "warn": logging.WARNING,
                "error": logging.ERROR,
                "critical": logging.CRITICAL,
            }
            level = level_map.get(level.lower(), logging.INFO)

        # Read and filter log entries
        results = []

        # Check if the file is compressed
        is_compressed = log_file.suffix == ".gz"

        try:
            # Open the file (compressed or not)
            if is_compressed:
                open_func = gzip.open
                mode = "rt"  # Text mode for gzip
            else:
                open_func = open
                mode = "r"

            with open_func(log_file, mode) as f:
                for line in f:
                    # Skip empty lines
                    if not line.strip():
                        continue

                    # Try to parse the log entry
                    try:
                        # Extract timestamp
                        timestamp_match = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]", line)
                        if timestamp_match:
                            timestamp_str = timestamp_match.group(1)
                            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                        else:
                            # If no timestamp found, skip time filtering
                            timestamp = None

                        # Filter by time range if provided
                        if timestamp is not None:
                            if start_time is not None and timestamp < start_time:
                                continue
                            if end_time is not None and timestamp > end_time:
                                continue

                        # Extract log level
                        level_match = re.search(r"\[(DEBUG|INFO|WARNING|ERROR|CRITICAL)\]", line)
                        if level_match:
                            log_level_str = level_match.group(1)
                            log_level_map = {
                                "DEBUG": logging.DEBUG,
                                "INFO": logging.INFO,
                                "WARNING": logging.WARNING,
                                "ERROR": logging.ERROR,
                                "CRITICAL": logging.CRITICAL,
                            }
                            log_level = log_level_map.get(log_level_str, logging.INFO)
                        else:
                            # If no level found, assume INFO
                            log_level = logging.INFO

                        # Filter by level if provided
                        if level is not None and log_level < level:
                            continue

                        # Filter by pattern if provided
                        if pattern is not None and not pattern.search(line):
                            continue

                        # Filter by correlation ID if provided
                        if correlation_id is not None:
                            if f'"correlation_id": "{correlation_id}"' not in line and f"'correlation_id': '{correlation_id}'" not in line:
                                continue

                        # Add the log entry to results
                        results.append(line.strip())

                        # Check limit
                        if limit is not None and len(results) >= limit:
                            break
                    except Exception as e:
                        self.error(f"Error parsing log entry: {str(e)}")
                        continue
        except Exception as e:
            self.error(f"Error reading log file {log_file}: {str(e)}")

        return results

    def search_logs(self, query, log_files=None, case_sensitive=False, whole_word=False, regex=False, limit=None):
        """
        Search logs for a specific query.

        Args:
            query: Search query
            log_files: List of log files to search (default: None, searches all log files)
            case_sensitive: Whether the search is case-sensitive (default: False)
            whole_word: Whether to match whole words only (default: False)
            regex: Whether the query is a regex pattern (default: False)
            limit: Maximum number of results to return (default: None)

        Returns:
            List of log entries matching the query
        """
        if log_files is None:
            # Get all log files (both .log and .log.gz)
            log_files = list(self.log_dir.glob(f"{self.app_name}_*.log"))
            log_files.extend(list(self.log_dir.glob(f"{self.app_name}_*.log.gz")))

        # Prepare the search pattern
        if regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(query, flags)
            except re.error:
                self.error(f"Invalid regex pattern: {query}")
                return []
        else:
            if whole_word:
                query = r"\b" + re.escape(query) + r"\b"
            else:
                query = re.escape(query)

            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = re.compile(query, flags)

        # Search all log files
        results = []
        for log_file in log_files:
            file_results = self.filter_logs(log_file=log_file, pattern=pattern, limit=limit)
            results.extend(file_results)

            # Check limit
            if limit is not None and len(results) >= limit:
                results = results[:limit]
                break

        return results

    # Log Aggregation Methods

    def aggregate_logs(self, log_files=None, group_by="level", time_window=None, count_only=False):
        """
        Aggregate logs by a specific field.

        Args:
            log_files: List of log files to aggregate (default: None, aggregates all log files)
            group_by: Field to group by (default: "level")
            time_window: Time window for aggregation (default: None)
            count_only: Whether to return only counts (default: False)

        Returns:
            Dictionary with aggregated log data
        """
        if log_files is None:
            # Get all log files (both .log and .log.gz)
            log_files = list(self.log_dir.glob(f"{self.app_name}_*.log"))
            log_files.extend(list(self.log_dir.glob(f"{self.app_name}_*.log.gz")))

        # Define regex patterns for extracting fields
        patterns = {
            "level": re.compile(r"\[(DEBUG|INFO|WARNING|ERROR|CRITICAL)\]"),
            "module": re.compile(r"\[([\w\.]+)\.[\w\.]+:\d+\]"),
            "function": re.compile(r"\[[\w\.]+\.([\w\.]+):\d+\]"),
            "line": re.compile(r"\[[\w\.]+\.[\w\.]+:(\d+)\]"),
            "thread": re.compile(r"\[([\w\-]+)\]\s"),
            "timestamp": re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]"),
            "correlation_id": re.compile(r'"correlation_id":\s*"([^"]+)"'),
            "error_type": re.compile(r'"error_type":\s*"([^"]+)"'),
            "operation": re.compile(r'"operation":\s*"([^"]+)"'),
            "request_path": re.compile(r'"request_path":\s*"([^"]+)"'),
        }

        # Check if the group_by field is supported
        if group_by not in patterns:
            self.error(f"Unsupported group_by field: {group_by}")
            return {}

        # Parse time window if provided as string
        if isinstance(time_window, str):
            try:
                # Parse time window in format "1h", "2d", etc.
                match = re.match(r"(\d+)([hdwmy])", time_window.lower())
                if match:
                    value, unit = match.groups()
                    value = int(value)
                    if unit == "h":
                        time_window = timedelta(hours=value)
                    elif unit == "d":
                        time_window = timedelta(days=value)
                    elif unit == "w":
                        time_window = timedelta(weeks=value)
                    elif unit == "m":
                        time_window = timedelta(days=value * 30)  # Approximate
                    elif unit == "y":
                        time_window = timedelta(days=value * 365)  # Approximate
                else:
                    self.error(f"Invalid time window format: {time_window}")
                    return {}
            except ValueError:
                self.error(f"Invalid time window format: {time_window}")
                return {}

        # Aggregate logs
        aggregated = defaultdict(int)
        entries = defaultdict(list)

        for log_file in log_files:
            # Filter logs by time window if provided
            if time_window is not None:
                start_time = datetime.now() - time_window
                logs = self.filter_logs(log_file=log_file, start_time=start_time)
            else:
                logs = self.filter_logs(log_file=log_file)

            for log in logs:
                # Extract the group_by field
                match = patterns[group_by].search(log)
                if match:
                    key = match.group(1)
                    aggregated[key] += 1
                    if not count_only:
                        entries[key].append(log)

        # Return results
        if count_only:
            return dict(aggregated)
        else:
            return {key: {"count": count, "entries": entries[key]} for key, count in aggregated.items()}

    # Log Analysis Methods

    def analyze_logs(self, log_files=None, analysis_type="error_distribution", time_window=None):
        """
        Analyze logs for patterns and trends.

        Args:
            log_files: List of log files to analyze (default: None, analyzes all log files)
            analysis_type: Type of analysis to perform (default: "error_distribution")
            time_window: Time window for analysis (default: None)

        Returns:
            Dictionary with analysis results
        """
        if log_files is None:
            # Get all log files (both .log and .log.gz)
            log_files = list(self.log_dir.glob(f"{self.app_name}_*.log"))
            log_files.extend(list(self.log_dir.glob(f"{self.app_name}_*.log.gz")))

        # Filter logs by time window if provided
        if time_window is not None:
            if isinstance(time_window, str):
                try:
                    # Parse time window in format "1h", "2d", etc.
                    match = re.match(r"(\d+)([hdwmy])", time_window.lower())
                    if match:
                        value, unit = match.groups()
                        value = int(value)
                        if unit == "h":
                            time_window = timedelta(hours=value)
                        elif unit == "d":
                            time_window = timedelta(days=value)
                        elif unit == "w":
                            time_window = timedelta(weeks=value)
                        elif unit == "m":
                            time_window = timedelta(days=value * 30)  # Approximate
                        elif unit == "y":
                            time_window = timedelta(days=value * 365)  # Approximate
                    else:
                        self.error(f"Invalid time window format: {time_window}")
                        return {}
                except ValueError:
                    self.error(f"Invalid time window format: {time_window}")
                    return {}

            start_time = datetime.now() - time_window
            logs = []
            for log_file in log_files:
                logs.extend(self.filter_logs(log_file=log_file, start_time=start_time))
        else:
            logs = []
            for log_file in log_files:
                logs.extend(self.filter_logs(log_file=log_file))

        # Perform the requested analysis
        if analysis_type == "error_distribution":
            return self._analyze_error_distribution(logs)
        elif analysis_type == "log_volume":
            return self._analyze_log_volume(logs)
        elif analysis_type == "performance":
            return self._analyze_performance(logs)
        elif analysis_type == "request_paths":
            return self._analyze_request_paths(logs)
        elif analysis_type == "error_trends":
            return self._analyze_error_trends(logs)
        else:
            self.error(f"Unsupported analysis type: {analysis_type}")
            return {}

    def _analyze_error_distribution(self, logs):
        """Analyze error distribution in logs"""
        error_types = defaultdict(int)
        error_messages = defaultdict(list)

        # Extract error types and messages
        for log in logs:
            if "[ERROR]" in log or "[CRITICAL]" in log:
                # Try to extract error type
                error_type_match = re.search(r'"error_type":\s*"([^"]+)"', log)
                if error_type_match:
                    error_type = error_type_match.group(1)
                else:
                    error_type = "unknown"

                error_types[error_type] += 1
                error_messages[error_type].append(log)

        # Calculate percentages
        total_errors = sum(error_types.values())
        percentages = {}
        if total_errors > 0:
            for error_type, count in error_types.items():
                percentages[error_type] = round(count / total_errors * 100, 2)

        return {
            "total_errors": total_errors,
            "error_types": dict(error_types),
            "percentages": percentages,
            "error_messages": {k: v[:5] for k, v in error_messages.items()}  # Limit to 5 messages per type
        }

    def _analyze_log_volume(self, logs):
        """Analyze log volume over time"""
        # Group logs by hour
        hourly_counts = defaultdict(int)
        level_counts = defaultdict(int)

        for log in logs:
            # Extract timestamp
            timestamp_match = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}):\d{2}:\d{2}\]", log)
            if timestamp_match:
                hour = timestamp_match.group(1)
                hourly_counts[hour] += 1

            # Extract log level
            level_match = re.search(r"\[(DEBUG|INFO|WARNING|ERROR|CRITICAL)\]", log)
            if level_match:
                level = level_match.group(1)
                level_counts[level] += 1

        return {
            "total_logs": len(logs),
            "hourly_counts": dict(hourly_counts),
            "level_counts": dict(level_counts)
        }

    def _analyze_performance(self, logs):
        """Analyze performance metrics in logs"""
        operation_durations = defaultdict(list)

        for log in logs:
            # Extract operation and duration
            operation_match = re.search(r'"operation":\s*"([^"]+)"', log)
            duration_match = re.search(r'"duration":\s*([\d\.]+)', log)

            if operation_match and duration_match:
                operation = operation_match.group(1)
                try:
                    duration = float(duration_match.group(1))
                    operation_durations[operation].append(duration)
                except ValueError:
                    continue

        # Calculate statistics
        stats = {}
        for operation, durations in operation_durations.items():
            if durations:
                stats[operation] = {
                    "count": len(durations),
                    "min": min(durations),
                    "max": max(durations),
                    "avg": sum(durations) / len(durations),
                    "median": statistics.median(durations) if len(durations) > 0 else 0,
                    "p95": sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 20 else max(durations),
                    "p99": sorted(durations)[int(len(durations) * 0.99)] if len(durations) > 100 else max(durations)
                }

        return {
            "total_operations": sum(len(durations) for durations in operation_durations.values()),
            "operation_stats": stats
        }

    def _analyze_request_paths(self, logs):
        """Analyze request paths in logs"""
        path_counts = defaultdict(int)
        path_durations = defaultdict(list)
        path_errors = defaultdict(int)

        for log in logs:
            # Extract request path
            path_match = re.search(r'"request_path":\s*"([^"]+)"', log)
            if path_match:
                path = path_match.group(1)
                path_counts[path] += 1

                # Check if this is an error
                if "[ERROR]" in log or "[CRITICAL]" in log:
                    path_errors[path] += 1

                # Extract duration if available
                duration_match = re.search(r'"duration":\s*([\d\.]+)', log)
                if duration_match:
                    try:
                        duration = float(duration_match.group(1))
                        path_durations[path].append(duration)
                    except ValueError:
                        continue

        # Calculate statistics
        stats = {}
        for path, count in path_counts.items():
            stats[path] = {
                "count": count,
                "error_count": path_errors[path],
                "error_rate": round(path_errors[path] / count * 100, 2) if count > 0 else 0
            }

            # Add duration statistics if available
            durations = path_durations[path]
            if durations:
                stats[path]["avg_duration"] = sum(durations) / len(durations)
                stats[path]["max_duration"] = max(durations)
                stats[path]["min_duration"] = min(durations)

        return {
            "total_requests": sum(path_counts.values()),
            "total_errors": sum(path_errors.values()),
            "path_stats": stats
        }

    def _analyze_error_trends(self, logs):
        """Analyze error trends over time"""
        # Group errors by hour and type
        hourly_errors = defaultdict(lambda: defaultdict(int))

        for log in logs:
            if "[ERROR]" in log or "[CRITICAL]" in log:
                # Extract timestamp
                timestamp_match = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}):\d{2}:\d{2}\]", log)
                if timestamp_match:
                    hour = timestamp_match.group(1)

                    # Extract error type
                    error_type_match = re.search(r'"error_type":\s*"([^"]+)"', log)
                    if error_type_match:
                        error_type = error_type_match.group(1)
                    else:
                        error_type = "unknown"

                    hourly_errors[hour][error_type] += 1

        # Convert to regular dict for JSON serialization
        result = {}
        for hour, errors in hourly_errors.items():
            result[hour] = dict(errors)

        return {
            "hourly_errors": result
        }

    # Log Metrics Methods

    def get_metrics(self):
        """
        Get log metrics.

        Returns:
            Dictionary with log metrics
        """
        if not self.log_metrics:
            return {"log_metrics_disabled": True}

        # Calculate uptime
        uptime = datetime.now() - self.metrics["start_time"]
        uptime_seconds = uptime.total_seconds()

        # Calculate logs per second
        total_logs = sum(self.metrics["log_counts"].values())
        logs_per_second = total_logs / uptime_seconds if uptime_seconds > 0 else 0

        # Calculate errors per second
        total_errors = sum(self.metrics["error_counts"].values())
        errors_per_second = total_errors / uptime_seconds if uptime_seconds > 0 else 0

        # Calculate performance statistics
        performance_stats = {}
        for operation, durations in self.metrics["performance"].items():
            if durations:
                performance_stats[operation] = {
                    "count": len(durations),
                    "min": min(durations),
                    "max": max(durations),
                    "avg": sum(durations) / len(durations),
                    "median": statistics.median(durations) if len(durations) > 0 else 0,
                    "p95": sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 20 else max(durations),
                    "p99": sorted(durations)[int(len(durations) * 0.99)] if len(durations) > 100 else max(durations)
                }

        # Get top requests
        top_requests = dict(sorted(self.metrics["requests"].items(), key=lambda x: x[1], reverse=True)[:10])

        return {
            "uptime": {
                "seconds": uptime_seconds,
                "formatted": str(uptime).split(".")[0]  # Remove microseconds
            },
            "log_counts": dict(self.metrics["log_counts"]),
            "error_counts": dict(self.metrics["error_counts"]),
            "total_logs": total_logs,
            "total_errors": total_errors,
            "logs_per_second": round(logs_per_second, 2),
            "errors_per_second": round(errors_per_second, 2),
            "performance": performance_stats,
            "top_requests": top_requests,
            "start_time": self.metrics["start_time"].isoformat(),
            "last_reset": self.metrics["last_reset"].isoformat()
        }

    def reset_metrics(self):
        """
        Reset log metrics.

        Returns:
            Dictionary with previous metrics
        """
        if not self.log_metrics:
            return {"log_metrics_disabled": True}

        # Get current metrics
        previous_metrics = self.get_metrics()

        # Reset metrics
        self.metrics = {
            "log_counts": defaultdict(int),
            "error_counts": defaultdict(int),
            "performance": defaultdict(list),
            "requests": defaultdict(int),
            "start_time": datetime.now(),
            "last_reset": datetime.now()
        }

        return previous_metrics


# Create a singleton instance
_log_manager = None


def get_logger(log_dir=None, max_logs=10, max_size_mb=10, max_days=30, level=logging.INFO, app_name="pyprocessor",
              compress_logs=True, encrypt_sensitive=False, log_format=None, console_format=None, file_format=None,
              additional_handlers=None, log_metrics=True, correlation_id_header="X-Correlation-ID"):
    """
    Get the singleton logger instance.

    Args:
        log_dir: Directory to store log files (default: pyprocessor/logs)
        max_logs: Maximum number of log files to keep (default: 10)
        max_size_mb: Maximum size of log files in MB (default: 10)
        max_days: Maximum age of log files in days (default: 30)
        level: Logging level (default: INFO)
        app_name: Application name for the logger (default: pyprocessor)
        compress_logs: Whether to compress old log files (default: True)
        encrypt_sensitive: Whether to encrypt sensitive log data (default: False)
        log_format: Custom log format (default: None, uses predefined formats)
        console_format: Custom console log format (default: None, uses predefined format)
        file_format: Custom file log format (default: None, uses predefined format)
        additional_handlers: Additional log handlers to add (default: None)
        log_metrics: Whether to collect log metrics (default: True)
        correlation_id_header: HTTP header for correlation ID (default: X-Correlation-ID)

    Returns:
        LogManager: The singleton logger instance
    """
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager(
            log_dir=log_dir,
            max_logs=max_logs,
            max_size_mb=max_size_mb,
            max_days=max_days,
            level=level,
            app_name=app_name,
            compress_logs=compress_logs,
            encrypt_sensitive=encrypt_sensitive,
            log_format=log_format,
            console_format=console_format,
            file_format=file_format,
            additional_handlers=additional_handlers,
            log_metrics=log_metrics,
            correlation_id_header=correlation_id_header
        )
    return _log_manager


def set_correlation_id(correlation_id=None):
    """
    Set a correlation ID for the current thread.

    Args:
        correlation_id: Correlation ID to set (default: None, generates a new UUID)
    """
    return get_logger().set_correlation_id(correlation_id)


def get_correlation_id():
    """
    Get the correlation ID for the current thread.

    Returns:
        str: Correlation ID or None if not set
    """
    return get_logger().get_correlation_id()


def filter_logs(log_file=None, level=None, start_time=None, end_time=None, pattern=None, correlation_id=None, limit=None):
    """
    Filter logs based on various criteria.

    Args:
        log_file: Path to the log file (default: current log file)
        level: Minimum log level to include (default: None, includes all levels)
        start_time: Start time for filtering (default: None)
        end_time: End time for filtering (default: None)
        pattern: Regex pattern to match in log messages (default: None)
        correlation_id: Correlation ID to filter by (default: None)
        limit: Maximum number of log entries to return (default: None)

    Returns:
        List of log entries matching the criteria
    """
    return get_logger().filter_logs(log_file, level, start_time, end_time, pattern, correlation_id, limit)


def search_logs(query, log_files=None, case_sensitive=False, whole_word=False, regex=False, limit=None):
    """
    Search logs for a specific query.

    Args:
        query: Search query
        log_files: List of log files to search (default: None, searches all log files)
        case_sensitive: Whether the search is case-sensitive (default: False)
        whole_word: Whether to match whole words only (default: False)
        regex: Whether the query is a regex pattern (default: False)
        limit: Maximum number of results to return (default: None)

    Returns:
        List of log entries matching the query
    """
    return get_logger().search_logs(query, log_files, case_sensitive, whole_word, regex, limit)


def aggregate_logs(log_files=None, group_by="level", time_window=None, count_only=False):
    """
    Aggregate logs by a specific field.

    Args:
        log_files: List of log files to aggregate (default: None, aggregates all log files)
        group_by: Field to group by (default: "level")
        time_window: Time window for aggregation (default: None)
        count_only: Whether to return only counts (default: False)

    Returns:
        Dictionary with aggregated log data
    """
    return get_logger().aggregate_logs(log_files, group_by, time_window, count_only)


def analyze_logs(log_files=None, analysis_type="error_distribution", time_window=None):
    """
    Analyze logs for patterns and trends.

    Args:
        log_files: List of log files to analyze (default: None, analyzes all log files)
        analysis_type: Type of analysis to perform (default: "error_distribution")
        time_window: Time window for analysis (default: None)

    Returns:
        Dictionary with analysis results
    """
    return get_logger().analyze_logs(log_files, analysis_type, time_window)


def get_metrics():
    """
    Get log metrics.

    Returns:
        Dictionary with log metrics
    """
    return get_logger().get_metrics()


def reset_metrics():
    """
    Reset log metrics.

    Returns:
        Dictionary with previous metrics
    """
    return get_logger().reset_metrics()


def with_logging(func=None, *, level=logging.DEBUG, log_args=False, log_result=False):
    """
    Decorator to add logging to a function.

    This decorator adds entry and exit logging to a function.

    Args:
        func: The function to decorate
        level: The log level to use (default: DEBUG)
        log_args: Whether to log function arguments (default: False)
        log_result: Whether to log function result (default: False)

    Returns:
        The decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()

            # Prepare entry log
            entry_data = {}
            if log_args:
                # Convert args to a dictionary
                try:
                    # Get function signature
                    import inspect
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()

                    # Convert to dictionary, excluding 'self' for methods
                    arg_dict = {}
                    for k, v in bound_args.arguments.items():
                        if k != 'self':
                            # Try to make values JSON serializable
                            try:
                                json.dumps({k: v}, default=str)
                                arg_dict[k] = v
                            except:
                                arg_dict[k] = str(v)

                    entry_data['args'] = arg_dict
                except Exception:
                    # If we can't get the signature, just log the number of args
                    entry_data['args_count'] = len(args)
                    entry_data['kwargs_count'] = len(kwargs)

            # Log function entry
            logger._log(level, f"Entering {func.__name__}", **entry_data)

            try:
                # Call the function
                result = func(*args, **kwargs)

                # Prepare exit log
                exit_data = {}
                if log_result:
                    # Try to make result JSON serializable
                    try:
                        json.dumps({'result': result}, default=str)
                        exit_data['result'] = result
                    except:
                        exit_data['result'] = str(result)

                # Log function exit
                logger._log(level, f"Exiting {func.__name__}", **exit_data)

                return result
            except Exception as e:
                # Log the error
                logger.error(f"Error in {func.__name__}: {str(e)}", exception=e)
                raise
        return wrapper

    # Handle both @with_logging and @with_logging(level=logging.INFO)
    if func is None:
        return decorator
    return decorator(func)


# Compatibility with old Logger class
class Logger:
    """
    Compatibility class for the old Logger interface.

    This class provides the same interface as the old Logger class,
    but uses the new LogManager internally.
    """

    def __init__(self, log_dir=None, max_logs=10, max_size_mb=10, max_days=30, level=logging.INFO):
        """
        Initialize the logger.

        Args:
            log_dir: Directory to store log files (default: pyprocessor/logs)
            max_logs: Maximum number of log files to keep (default: 10)
            max_size_mb: Maximum size of log files in MB (default: 10)
            max_days: Maximum age of log files in days (default: 30)
            level: Logging level (default: INFO)
        """
        self.log_manager = get_logger(log_dir, max_logs, max_size_mb, max_days, level)

    def debug(self, message, **kwargs):
        """Log a debug message with optional structured data"""
        self.log_manager.debug(message, **kwargs)

    def info(self, message, **kwargs):
        """Log an info message with optional structured data"""
        self.log_manager.info(message, **kwargs)

    def warning(self, message, **kwargs):
        """Log a warning message with optional structured data"""
        self.log_manager.warning(message, **kwargs)

    def error(self, message, **kwargs):
        """Log an error message with optional structured data"""
        self.log_manager.error(message, **kwargs)

    def critical(self, message, **kwargs):
        """Log a critical message with optional structured data"""
        self.log_manager.critical(message, **kwargs)

    def set_level(self, level):
        """Set the logging level"""
        self.log_manager.set_level(level)

    def get_log_content(self, lines=50):
        """Get the most recent log content"""
        return self.log_manager.get_log_content(lines)

    def close(self):
        """Close all handlers to release file locks"""
        return self.log_manager.close()

    def set_context(self, **kwargs):
        """Set context information for the current thread"""
        self.log_manager.set_context(**kwargs)

    def get_context(self, key, default=None):
        """Get context information for the current thread"""
        return self.log_manager.get_context(key, default)

    def clear_context(self):
        """Clear all context information for the current thread"""
        self.log_manager.clear_context()
