"""
Centralized error handling module for PyProcessor.

This module provides a centralized error handling system with custom exception classes,
error categorization, and error recovery mechanisms.
"""

import collections
import functools
import inspect
import json
import os
import subprocess
import threading
import time
import traceback
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from pyprocessor.utils.logging.log_manager import get_logger


# Forward declaration for circular reference
class PyProcessorError(Exception):
    pass


# Type variable for generic return type
T = TypeVar("T")
R = TypeVar("R")


class Result(Generic[T]):
    """
    A result object that can represent either a success or a failure.

    This class is used to represent the result of an operation that might fail.
    It contains either a value (on success) or an error (on failure).

    Attributes:
        success: Whether the operation was successful
        value: The value returned by the operation (if successful)
        error: The error that occurred (if unsuccessful)
    """

    def __init__(
        self,
        success: bool,
        value: Optional[T] = None,
        error: Optional[PyProcessorError] = None,
    ):
        """
        Initialize the result.

        Args:
            success: Whether the operation was successful
            value: The value returned by the operation (if successful)
            error: The error that occurred (if unsuccessful)
        """
        self.success = success
        self.value = value
        self.error = error

    @classmethod
    def ok(cls, value: T) -> "Result[T]":
        """
        Create a successful result.

        Args:
            value: The value returned by the operation

        Returns:
            Result: A successful result
        """
        return cls(True, value=value)

    @classmethod
    def fail(cls, error: Union[PyProcessorError, Exception, str]) -> "Result[T]":
        """
        Create a failed result.

        Args:
            error: The error that occurred

        Returns:
            Result: A failed result
        """
        if isinstance(error, PyProcessorError):
            return cls(False, error=error)
        elif isinstance(error, Exception):
            return cls(False, error=convert_exception(error))
        else:
            return cls(False, error=PyProcessorError(str(error)))

    def __bool__(self) -> bool:
        """
        Convert the result to a boolean.

        Returns:
            bool: True if the operation was successful, False otherwise
        """
        return self.success

    def unwrap(self) -> T:
        """
        Get the value if the operation was successful, otherwise raise the error.

        Returns:
            T: The value returned by the operation

        Raises:
            PyProcessorError: If the operation was unsuccessful
        """
        if self.success:
            return self.value
        else:
            raise self.error

    def unwrap_or(self, default: T) -> T:
        """
        Get the value if the operation was successful, otherwise return the default.

        Args:
            default: The default value to return if the operation was unsuccessful

        Returns:
            T: The value returned by the operation or the default
        """
        if self.success:
            return self.value
        else:
            return default

    def map(self, func: Callable[[T], R]) -> "Result[R]":
        """
        Apply a function to the value if the operation was successful.

        Args:
            func: The function to apply to the value

        Returns:
            Result: A new result with the function applied to the value
        """
        if self.success:
            try:
                return Result.ok(func(self.value))
            except Exception as e:
                return Result.fail(e)
        else:
            return Result(False, error=self.error)

    def flat_map(self, func: Callable[[T], "Result[R]"]) -> "Result[R]":
        """
        Apply a function that returns a Result to the value if the operation was successful.

        Args:
            func: The function to apply to the value

        Returns:
            Result: The result of applying the function to the value
        """
        if self.success:
            try:
                return func(self.value)
            except Exception as e:
                return Result.fail(e)
        else:
            return Result(False, error=self.error)

    def __str__(self) -> str:
        """
        Get a string representation of the result.

        Returns:
            str: A string representation of the result
        """
        if self.success:
            return f"Success: {self.value}"
        else:
            return f"Failure: {self.error}"


class ErrorSeverity(Enum):
    """Enumeration of error severity levels."""

    INFO = 0
    WARNING = 1
    ERROR = 2
    CRITICAL = 3


class ErrorCategory(Enum):
    """Enumeration of error categories."""

    CONFIGURATION = 0
    FILE_SYSTEM = 1
    NETWORK = 2
    ENCODING = 3
    PROCESS = 4
    VALIDATION = 5
    RESOURCE = 6
    PERMISSION = 7
    SYSTEM = 8
    UNKNOWN = 9


class PyProcessorError(Exception):
    """Base exception class for all PyProcessor errors."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        original_exception: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
        error_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            severity: Error severity level
            category: Error category
            original_exception: Original exception that caused this error
            details: Additional details about the error
            error_id: Unique ID for the error (default: auto-generated UUID)
            timestamp: Timestamp when the error occurred (default: current time)
        """
        self.message = message
        self.severity = severity
        self.category = category
        self.original_exception = original_exception
        self.details = details or {}
        self.error_id = error_id or str(uuid.uuid4())
        self.timestamp = timestamp or datetime.now()
        self.handled = False
        self.recovery_attempts = 0
        self.recovery_successful = False

        # Build the full message
        full_message = f"[{severity.name}] [{category.name}] {message}"
        if original_exception:
            full_message += f" (Caused by: {type(original_exception).__name__}: {str(original_exception)})"

        super().__init__(full_message)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the error to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the error
        """
        return {
            "error_id": self.error_id,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "severity": self.severity.name,
            "category": self.category.name,
            "original_exception": (
                str(self.original_exception) if self.original_exception else None
            ),
            "original_exception_type": (
                type(self.original_exception).__name__
                if self.original_exception
                else None
            ),
            "details": self.details,
            "handled": self.handled,
            "recovery_attempts": self.recovery_attempts,
            "recovery_successful": self.recovery_successful,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PyProcessorError":
        """
        Create an error from a dictionary.

        Args:
            data: Dictionary representation of the error

        Returns:
            PyProcessorError: The error
        """
        # Convert string severity and category to enum values
        severity = ErrorSeverity[data["severity"]]
        category = ErrorCategory[data["category"]]

        # Create the error
        error = cls(
            message=data["message"],
            severity=severity,
            category=category,
            details=data["details"],
            error_id=data["error_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )

        # Set additional attributes
        error.handled = data["handled"]
        error.recovery_attempts = data["recovery_attempts"]
        error.recovery_successful = data["recovery_successful"]

        return error

    def mark_as_handled(self):
        """
        Mark the error as handled.
        """
        self.handled = True

    def increment_recovery_attempts(self):
        """
        Increment the number of recovery attempts.
        """
        self.recovery_attempts += 1

    def mark_recovery_successful(self):
        """
        Mark the recovery as successful.
        """
        self.recovery_successful = True

    def get_stack_trace(self) -> str:
        """
        Get the stack trace for the error.

        Returns:
            str: Stack trace
        """
        if self.original_exception:
            return "".join(
                traceback.format_exception(
                    type(self.original_exception),
                    self.original_exception,
                    self.original_exception.__traceback__,
                )
            )
        return "".join(traceback.format_exception(type(self), self, self.__traceback__))


class ConfigurationError(PyProcessorError):
    """Exception raised for configuration errors."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        original_exception: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            severity: Error severity level
            original_exception: Original exception that caused this error
            details: Additional details about the error
        """
        super().__init__(
            message,
            severity,
            ErrorCategory.CONFIGURATION,
            original_exception,
            details,
        )


class FileSystemError(PyProcessorError):
    """Exception raised for file system errors."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        original_exception: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            severity: Error severity level
            original_exception: Original exception that caused this error
            details: Additional details about the error
        """
        super().__init__(
            message,
            severity,
            ErrorCategory.FILE_SYSTEM,
            original_exception,
            details,
        )


class NetworkError(PyProcessorError):
    """Exception raised for network errors."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        original_exception: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            severity: Error severity level
            original_exception: Original exception that caused this error
            details: Additional details about the error
        """
        super().__init__(
            message,
            severity,
            ErrorCategory.NETWORK,
            original_exception,
            details,
        )


class EncodingError(PyProcessorError):
    """Exception raised for encoding errors."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        original_exception: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            severity: Error severity level
            original_exception: Original exception that caused this error
            details: Additional details about the error
        """
        super().__init__(
            message,
            severity,
            ErrorCategory.ENCODING,
            original_exception,
            details,
        )


class ProcessError(PyProcessorError):
    """Exception raised for process errors."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        original_exception: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            severity: Error severity level
            original_exception: Original exception that caused this error
            details: Additional details about the error
        """
        super().__init__(
            message,
            severity,
            ErrorCategory.PROCESS,
            original_exception,
            details,
        )


class ValidationError(PyProcessorError):
    """Exception raised for validation errors."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        original_exception: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            severity: Error severity level
            original_exception: Original exception that caused this error
            details: Additional details about the error
        """
        super().__init__(
            message,
            severity,
            ErrorCategory.VALIDATION,
            original_exception,
            details,
        )


class ResourceError(PyProcessorError):
    """Exception raised for resource errors."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        original_exception: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            severity: Error severity level
            original_exception: Original exception that caused this error
            details: Additional details about the error
        """
        super().__init__(
            message,
            severity,
            ErrorCategory.RESOURCE,
            original_exception,
            details,
        )


class PermissionError(PyProcessorError):
    """Exception raised for permission errors."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        original_exception: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            severity: Error severity level
            original_exception: Original exception that caused this error
            details: Additional details about the error
        """
        super().__init__(
            message,
            severity,
            ErrorCategory.PERMISSION,
            original_exception,
            details,
        )


class SystemError(PyProcessorError):
    """Exception raised for system errors."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        original_exception: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the exception.

        Args:
            message: Error message
            severity: Error severity level
            original_exception: Original exception that caused this error
            details: Additional details about the error
        """
        super().__init__(
            message,
            severity,
            ErrorCategory.SYSTEM,
            original_exception,
            details,
        )


class ErrorManager:
    """
    Singleton error manager for PyProcessor.

    This class provides a centralized error handling system with the following features:
    - Singleton pattern to ensure only one error manager instance exists
    - Error categorization and severity levels
    - Error recovery mechanisms
    - Error reporting and logging
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ErrorManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, logger=None):
        """
        Initialize the error manager.

        Args:
            logger: Optional logger object
        """
        # Only initialize once
        if self._initialized:
            return

        # Get logger
        self.logger = logger or get_logger()

        # Initialize error handlers
        self._error_handlers = {}
        self._recovery_handlers = {}
        self._notification_handlers = {}

        # Initialize error history
        self._error_history = []
        self._max_history = 100

        # Initialize error metrics
        self._error_counts = collections.Counter()
        self._error_counts_by_category = collections.defaultdict(collections.Counter)
        self._error_counts_by_severity = collections.defaultdict(collections.Counter)
        self._last_error_time = collections.defaultdict(datetime.now)

        # Initialize error aggregation
        self._similar_errors = collections.defaultdict(list)
        self._error_fingerprints = {}

        # Initialize notification settings
        self._notification_threshold = ErrorSeverity.ERROR
        self._notification_cooldown = timedelta(minutes=5)
        self._last_notification_time = {}

        # Register default error handlers
        self._register_default_handlers()

        # Mark as initialized
        self._initialized = True

        self.logger.debug("Error manager initialized")

    def _register_default_handlers(self):
        """Register default error handlers."""
        # Register default handlers for each error category
        for category in ErrorCategory:
            self.register_error_handler(category, self._default_error_handler)

    def _default_error_handler(self, error: PyProcessorError) -> bool:
        """
        Default error handler that logs the error.

        Args:
            error: The error to handle

        Returns:
            bool: True if the error was handled, False otherwise
        """
        # Log the error based on severity
        if error.severity == ErrorSeverity.INFO:
            self.logger.info(str(error))
        elif error.severity == ErrorSeverity.WARNING:
            self.logger.warning(str(error))
        elif error.severity == ErrorSeverity.ERROR:
            self.logger.error(str(error))
        elif error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(str(error))

        # Update error metrics
        self._update_error_metrics(error)

        # Try to recover from the error
        self._try_recover(error)

        # Add to error history
        self._add_to_history(error)

        # Check if notification is needed
        self._check_notification(error)

        # Mark the error as handled
        error.mark_as_handled()

        # Return True to indicate the error was handled
        return True

    def _add_to_history(self, error: PyProcessorError):
        """
        Add an error to the error history.

        Args:
            error: The error to add
        """
        # Add to history
        self._error_history.append(error)

        # Trim history if it's too long
        if len(self._error_history) > self._max_history:
            self._error_history = self._error_history[-self._max_history :]

        # Add to similar errors
        fingerprint = self._get_error_fingerprint(error)
        self._similar_errors[fingerprint].append(error)
        self._error_fingerprints[error.error_id] = fingerprint

    def _update_error_metrics(self, error: PyProcessorError):
        """
        Update error metrics.

        Args:
            error: The error to update metrics for
        """
        # Update error counts
        self._error_counts[error.message] += 1
        self._error_counts_by_category[error.category][error.message] += 1
        self._error_counts_by_severity[error.severity][error.message] += 1

        # Update last error time
        self._last_error_time[error.message] = error.timestamp

    def _try_recover(self, error: PyProcessorError) -> bool:
        """
        Try to recover from an error.

        Args:
            error: The error to recover from

        Returns:
            bool: True if recovery was successful, False otherwise
        """
        # Increment recovery attempts
        error.increment_recovery_attempts()

        # Check if there's a recovery handler for this category
        recovery_handler = self._recovery_handlers.get(error.category)
        if recovery_handler:
            try:
                # Try to recover
                if recovery_handler(error):
                    # Mark recovery as successful
                    error.mark_recovery_successful()
                    self.logger.info(f"Successfully recovered from error: {error}")
                    return True
            except Exception as e:
                # Log recovery failure
                self.logger.error(f"Error during recovery attempt: {e}")

        return False

    def _check_notification(self, error: PyProcessorError):
        """
        Check if notification is needed for an error.

        Args:
            error: The error to check notification for
        """
        # Check if the error severity is above the notification threshold
        if error.severity.value < self._notification_threshold.value:
            return

        # Check if we've sent a notification for this type of error recently
        fingerprint = self._get_error_fingerprint(error)
        last_notification = self._last_notification_time.get(fingerprint)
        if (
            last_notification
            and (error.timestamp - last_notification) < self._notification_cooldown
        ):
            return

        # Check if there's a notification handler for this category
        notification_handler = self._notification_handlers.get(error.category)
        if notification_handler:
            try:
                # Send notification
                notification_handler(error)

                # Update last notification time
                self._last_notification_time[fingerprint] = error.timestamp

                self.logger.debug(f"Sent notification for error: {error}")
            except Exception as e:
                # Log notification failure
                self.logger.error(f"Error sending notification: {e}")

    def _get_error_fingerprint(self, error: PyProcessorError) -> str:
        """
        Get a fingerprint for an error to identify similar errors.

        Args:
            error: The error to get a fingerprint for

        Returns:
            str: Error fingerprint
        """
        # Use category, message, and original exception type as the fingerprint
        original_type = (
            type(error.original_exception).__name__
            if error.original_exception
            else "None"
        )
        return f"{error.category.name}:{error.message}:{original_type}"

    def register_error_handler(
        self,
        error_category: Union[ErrorCategory, Type[PyProcessorError]],
        handler: Callable[[PyProcessorError], bool],
    ):
        """
        Register an error handler for a specific error category or exception type.

        Args:
            error_category: Error category or exception type to handle
            handler: Function that takes an error and returns True if handled
        """
        # Convert exception type to category if needed
        if isinstance(error_category, type) and issubclass(
            error_category, PyProcessorError
        ):
            # Get the category from a dummy instance
            dummy = error_category("dummy")
            category = dummy.category
        else:
            category = error_category

        # Register the handler
        self._error_handlers[category] = handler

    def handle_error(self, error: Union[PyProcessorError, Exception]) -> bool:
        """
        Handle an error using the appropriate error handler.

        Args:
            error: The error to handle

        Returns:
            bool: True if the error was handled, False otherwise
        """
        # Convert standard exception to PyProcessorError if needed
        if not isinstance(error, PyProcessorError):
            error = self.convert_exception(error)

        # Get the appropriate handler
        handler = self._error_handlers.get(error.category, self._default_error_handler)

        # Handle the error
        return handler(error)

    def convert_exception(
        self,
        exception: Exception,
        message: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: Optional[ErrorCategory] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> PyProcessorError:
        """
        Convert a standard exception to a PyProcessorError.

        Args:
            exception: The exception to convert
            message: Optional custom message (default: exception message)
            severity: Error severity level
            category: Optional error category (default: based on exception type)
            details: Additional details about the error

        Returns:
            PyProcessorError: The converted error
        """
        # Use exception message if no custom message is provided
        if message is None:
            message = str(exception)

        # Determine the error category based on the exception type
        if category is None:
            category = self._categorize_exception(exception)

        # Create the appropriate PyProcessorError subclass
        if category == ErrorCategory.CONFIGURATION:
            return ConfigurationError(message, severity, exception, details)
        elif category == ErrorCategory.FILE_SYSTEM:
            return FileSystemError(message, severity, exception, details)
        elif category == ErrorCategory.NETWORK:
            return NetworkError(message, severity, exception, details)
        elif category == ErrorCategory.ENCODING:
            return EncodingError(message, severity, exception, details)
        elif category == ErrorCategory.PROCESS:
            return ProcessError(message, severity, exception, details)
        elif category == ErrorCategory.VALIDATION:
            return ValidationError(message, severity, exception, details)
        elif category == ErrorCategory.RESOURCE:
            return ResourceError(message, severity, exception, details)
        elif category == ErrorCategory.PERMISSION:
            return PermissionError(message, severity, exception, details)
        elif category == ErrorCategory.SYSTEM:
            return SystemError(message, severity, exception, details)
        else:
            return PyProcessorError(message, severity, category, exception, details)

    def _categorize_exception(self, exception: Exception) -> ErrorCategory:
        """
        Categorize a standard exception.

        Args:
            exception: The exception to categorize

        Returns:
            ErrorCategory: The error category
        """
        # Categorize based on exception type
        if isinstance(
            exception,
            (FileNotFoundError, FileExistsError, IsADirectoryError, NotADirectoryError),
        ):
            return ErrorCategory.FILE_SYSTEM
        elif isinstance(
            exception,
            (
                ConnectionError,
                ConnectionRefusedError,
                ConnectionResetError,
                TimeoutError,
            ),
        ):
            return ErrorCategory.NETWORK
        elif isinstance(exception, (PermissionError, OSError)) and "Permission" in str(
            exception
        ):
            return ErrorCategory.PERMISSION
        elif isinstance(exception, (MemoryError, ResourceWarning)):
            return ErrorCategory.RESOURCE
        elif isinstance(exception, (ValueError, TypeError, AttributeError)):
            return ErrorCategory.VALIDATION
        elif isinstance(exception, (OSError, SystemError)):
            return ErrorCategory.SYSTEM
        elif isinstance(
            exception, (subprocess.SubprocessError, subprocess.CalledProcessError)
        ):
            return ErrorCategory.PROCESS
        else:
            return ErrorCategory.UNKNOWN

    def get_error_history(self) -> List[PyProcessorError]:
        """
        Get the error history.

        Returns:
            List[PyProcessorError]: The error history
        """
        return self._error_history.copy()

    def get_filtered_error_history(
        self,
        category: Optional[ErrorCategory] = None,
        severity: Optional[ErrorSeverity] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        handled_only: bool = False,
        unhandled_only: bool = False,
        recovered_only: bool = False,
        max_results: Optional[int] = None,
    ) -> List[PyProcessorError]:
        """
        Get filtered error history.

        Args:
            category: Filter by error category
            severity: Filter by error severity
            start_time: Filter by start time
            end_time: Filter by end time
            handled_only: Only include handled errors
            unhandled_only: Only include unhandled errors
            recovered_only: Only include recovered errors
            max_results: Maximum number of results to return

        Returns:
            List[PyProcessorError]: Filtered list of errors
        """
        # Start with all errors
        filtered_errors = self._error_history.copy()

        # Apply filters
        if category is not None:
            filtered_errors = [e for e in filtered_errors if e.category == category]

        if severity is not None:
            filtered_errors = [e for e in filtered_errors if e.severity == severity]

        if start_time is not None:
            filtered_errors = [e for e in filtered_errors if e.timestamp >= start_time]

        if end_time is not None:
            filtered_errors = [e for e in filtered_errors if e.timestamp <= end_time]

        if handled_only:
            filtered_errors = [e for e in filtered_errors if e.handled]

        if unhandled_only:
            filtered_errors = [e for e in filtered_errors if not e.handled]

        if recovered_only:
            filtered_errors = [e for e in filtered_errors if e.recovery_successful]

        # Sort by timestamp (newest first)
        filtered_errors.sort(key=lambda e: e.timestamp, reverse=True)

        # Limit results
        if max_results is not None:
            filtered_errors = filtered_errors[:max_results]

        return filtered_errors

    def get_similar_errors(
        self, error: Union[PyProcessorError, str]
    ) -> List[PyProcessorError]:
        """
        Get errors similar to the given error.

        Args:
            error: The error or error ID to find similar errors for

        Returns:
            List[PyProcessorError]: List of similar errors
        """
        # Get the fingerprint for the error
        if isinstance(error, str):
            # If error is an error ID, get the fingerprint from the cache
            fingerprint = self._error_fingerprints.get(error)
            if not fingerprint:
                return []
        else:
            # Otherwise, calculate the fingerprint
            fingerprint = self._get_error_fingerprint(error)

        # Return similar errors
        return self._similar_errors.get(fingerprint, []).copy()

    def get_error_metrics(self) -> Dict[str, Any]:
        """
        Get error metrics.

        Returns:
            Dict[str, Any]: Error metrics
        """
        return {
            "total_errors": sum(self._error_counts.values()),
            "unique_errors": len(self._error_counts),
            "errors_by_category": {
                k.name: dict(v) for k, v in self._error_counts_by_category.items()
            },
            "errors_by_severity": {
                k.name: dict(v) for k, v in self._error_counts_by_severity.items()
            },
            "most_common_errors": dict(self._error_counts.most_common(10)),
        }

    def register_recovery_handler(
        self,
        error_category: Union[ErrorCategory, Type[PyProcessorError]],
        handler: Callable[[PyProcessorError], bool],
    ):
        """
        Register a recovery handler for a specific error category.

        Args:
            error_category: Error category or exception class
            handler: Recovery handler function that takes an error and returns True if recovery was successful
        """
        # Convert exception class to category if needed
        if isinstance(error_category, type) and issubclass(
            error_category, PyProcessorError
        ):
            error_category = error_category().category

        # Register the handler
        self._recovery_handlers[error_category] = handler
        self.logger.debug(f"Registered recovery handler for {error_category.name}")

    def register_notification_handler(
        self,
        error_category: Union[ErrorCategory, Type[PyProcessorError]],
        handler: Callable[[PyProcessorError], None],
    ):
        """
        Register a notification handler for a specific error category.

        Args:
            error_category: Error category or exception class
            handler: Notification handler function that takes an error
        """
        # Convert exception class to category if needed
        if isinstance(error_category, type) and issubclass(
            error_category, PyProcessorError
        ):
            error_category = error_category().category

        # Register the handler
        self._notification_handlers[error_category] = handler
        self.logger.debug(f"Registered notification handler for {error_category.name}")

    def set_notification_threshold(self, threshold: ErrorSeverity):
        """
        Set the notification threshold.

        Args:
            threshold: Minimum severity level for notifications
        """
        self._notification_threshold = threshold
        self.logger.debug(f"Set notification threshold to {threshold.name}")

    def set_notification_cooldown(self, cooldown: timedelta):
        """
        Set the notification cooldown.

        Args:
            cooldown: Cooldown period between notifications for similar errors
        """
        self._notification_cooldown = cooldown
        self.logger.debug(f"Set notification cooldown to {cooldown}")

    def serialize_errors(self, errors: List[PyProcessorError]) -> str:
        """
        Serialize errors to JSON.

        Args:
            errors: List of errors to serialize

        Returns:
            str: JSON string
        """
        return json.dumps([error.to_dict() for error in errors], indent=2)

    def deserialize_errors(self, json_str: str) -> List[PyProcessorError]:
        """
        Deserialize errors from JSON.

        Args:
            json_str: JSON string

        Returns:
            List[PyProcessorError]: List of deserialized errors
        """
        data = json.loads(json_str)
        return [PyProcessorError.from_dict(error_dict) for error_dict in data]

    def export_error_history(self, file_path: str):
        """
        Export error history to a file.

        Args:
            file_path: Path to the file
        """
        try:
            with open(file_path, "w") as f:
                f.write(self.serialize_errors(self._error_history))
            self.logger.info(f"Exported error history to {file_path}")
        except Exception as e:
            self.logger.error(f"Error exporting error history: {e}")

    def import_error_history(self, file_path: str):
        """
        Import error history from a file.

        Args:
            file_path: Path to the file
        """
        try:
            with open(file_path, "r") as f:
                json_str = f.read()
            errors = self.deserialize_errors(json_str)
            self._error_history.extend(errors)

            # Trim history if it's too long
            if len(self._error_history) > self._max_history:
                self._error_history = self._error_history[-self._max_history :]

            # Update metrics and similar errors
            for error in errors:
                self._update_error_metrics(error)
                fingerprint = self._get_error_fingerprint(error)
                self._similar_errors[fingerprint].append(error)
                self._error_fingerprints[error.error_id] = fingerprint

            self.logger.info(f"Imported {len(errors)} errors from {file_path}")
        except Exception as e:
            self.logger.error(f"Error importing error history: {e}")

    def clear_error_history(self):
        """Clear the error history."""
        self._error_history = []

    def set_max_history(self, max_history: int):
        """
        Set the maximum number of errors to keep in history.

        Args:
            max_history: Maximum number of errors to keep
        """
        self._max_history = max_history

        # Trim history if it's too long
        if len(self._error_history) > self._max_history:
            self._error_history = self._error_history[-self._max_history :]

    def get_last_error(self) -> Optional[PyProcessorError]:
        """
        Get the last error.

        Returns:
            Optional[PyProcessorError]: The last error or None if no errors
        """
        if not self._error_history:
            return None
        return self._error_history[-1]

    def format_exception(self, exception: Exception) -> str:
        """
        Format an exception with traceback.

        Args:
            exception: The exception to format

        Returns:
            str: Formatted exception with traceback
        """
        return "".join(
            traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
        )


# Create a singleton instance
_error_manager = None


def get_error_manager(logger=None) -> ErrorManager:
    """
    Get the singleton error manager instance.

    Args:
        logger: Optional logger object

    Returns:
        ErrorManager: The singleton error manager instance
    """
    global _error_manager
    if _error_manager is None:
        _error_manager = ErrorManager(logger)
    return _error_manager


def handle_error(error: Union[PyProcessorError, Exception]) -> bool:
    """
    Handle an error using the error manager.

    Args:
        error: The error to handle

    Returns:
        bool: True if the error was handled, False otherwise
    """
    return get_error_manager().handle_error(error)


def get_filtered_error_history(
    category: Optional[ErrorCategory] = None,
    severity: Optional[ErrorSeverity] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    handled_only: bool = False,
    unhandled_only: bool = False,
    recovered_only: bool = False,
    max_results: Optional[int] = None,
) -> List[PyProcessorError]:
    """
    Get filtered error history.

    Args:
        category: Filter by error category
        severity: Filter by error severity
        start_time: Filter by start time
        end_time: Filter by end time
        handled_only: Only include handled errors
        unhandled_only: Only include unhandled errors
        recovered_only: Only include recovered errors
        max_results: Maximum number of results to return

    Returns:
        List[PyProcessorError]: Filtered list of errors
    """
    return get_error_manager().get_filtered_error_history(
        category,
        severity,
        start_time,
        end_time,
        handled_only,
        unhandled_only,
        recovered_only,
        max_results,
    )


def get_similar_errors(error: Union[PyProcessorError, str]) -> List[PyProcessorError]:
    """
    Get errors similar to the given error.

    Args:
        error: The error or error ID to find similar errors for

    Returns:
        List[PyProcessorError]: List of similar errors
    """
    return get_error_manager().get_similar_errors(error)


def get_error_metrics() -> Dict[str, Any]:
    """
    Get error metrics.

    Returns:
        Dict[str, Any]: Error metrics
    """
    return get_error_manager().get_error_metrics()


def register_recovery_handler(
    error_category: Union[ErrorCategory, Type[PyProcessorError]],
    handler: Callable[[PyProcessorError], bool],
):
    """
    Register a recovery handler for a specific error category.

    Args:
        error_category: Error category or exception class
        handler: Recovery handler function that takes an error and returns True if recovery was successful
    """
    get_error_manager().register_recovery_handler(error_category, handler)


def register_notification_handler(
    error_category: Union[ErrorCategory, Type[PyProcessorError]],
    handler: Callable[[PyProcessorError], None],
):
    """
    Register a notification handler for a specific error category.

    Args:
        error_category: Error category or exception class
        handler: Notification handler function that takes an error
    """
    get_error_manager().register_notification_handler(error_category, handler)


def register_error_handler(
    error_category: Union[ErrorCategory, Type[PyProcessorError]],
    handler: Callable[[PyProcessorError], bool],
):
    """
    Register an error handler for a specific error category or exception type.

    Args:
        error_category: Error category or exception type to handle
        handler: Function that takes an error and returns True if handled
    """
    get_error_manager().register_error_handler(error_category, handler)


def set_notification_threshold(threshold: ErrorSeverity):
    """
    Set the notification threshold.

    Args:
        threshold: Minimum severity level for notifications
    """
    get_error_manager().set_notification_threshold(threshold)


def set_notification_cooldown(cooldown: timedelta):
    """
    Set the notification cooldown.

    Args:
        cooldown: Cooldown period between notifications for similar errors
    """
    get_error_manager().set_notification_cooldown(cooldown)


def serialize_errors(errors: List[PyProcessorError]) -> str:
    """
    Serialize errors to JSON.

    Args:
        errors: List of errors to serialize

    Returns:
        str: JSON string
    """
    return get_error_manager().serialize_errors(errors)


def deserialize_errors(json_str: str) -> List[PyProcessorError]:
    """
    Deserialize errors from JSON.

    Args:
        json_str: JSON string

    Returns:
        List[PyProcessorError]: List of deserialized errors
    """
    return get_error_manager().deserialize_errors(json_str)


def export_error_history(file_path: str):
    """
    Export error history to a file.

    Args:
        file_path: Path to the file
    """
    get_error_manager().export_error_history(file_path)


def import_error_history(file_path: str):
    """
    Import error history from a file.

    Args:
        file_path: Path to the file
    """
    get_error_manager().import_error_history(file_path)


def convert_exception(
    exception: Exception,
    message: Optional[str] = None,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    category: Optional[ErrorCategory] = None,
    details: Optional[Dict[str, Any]] = None,
) -> PyProcessorError:
    """
    Convert a standard exception to a PyProcessorError.

    Args:
        exception: The exception to convert
        message: Optional custom message (default: exception message)
        severity: Error severity level
        category: Optional error category (default: based on exception type)
        details: Additional details about the error

    Returns:
        PyProcessorError: The converted error
    """
    return get_error_manager().convert_exception(
        exception, message, severity, category, details
    )


def safe_call(
    func: Callable, *args, **kwargs
) -> Tuple[bool, Any, Optional[PyProcessorError]]:
    """
    Call a function safely, catching any exceptions.

    Args:
        func: The function to call
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        Tuple[bool, Any, Optional[PyProcessorError]]: (success, result, error)
    """
    try:
        result = func(*args, **kwargs)
        return True, result, None
    except Exception as e:
        error = convert_exception(e)
        handle_error(error)
        return False, None, error


def try_call(func: Callable[..., T], *args, **kwargs) -> Result[T]:
    """
    Call a function and return a Result.

    Args:
        func: The function to call
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        Result: A Result object containing either the return value or an error
    """
    try:
        result = func(*args, **kwargs)
        return Result.ok(result)
    except Exception as e:
        error = convert_exception(e)
        handle_error(error)
        return Result.fail(error)


class RetryConfig:
    """
    Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        backoff_factor: Factor to increase delay between retries
        max_delay: Maximum delay between retries in seconds
        retry_on: List of exception types or error categories to retry on
        retry_if: Function that takes an exception and returns True if it should be retried
    """

    def __init__(
        self,
        max_attempts: int = 3,
        retry_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        retry_on: Optional[List[Union[Type[Exception], ErrorCategory]]] = None,
        retry_if: Optional[Callable[[Exception], bool]] = None,
    ):
        """
        Initialize the retry configuration.

        Args:
            max_attempts: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            backoff_factor: Factor to increase delay between retries
            max_delay: Maximum delay between retries in seconds
            retry_on: List of exception types or error categories to retry on
            retry_if: Function that takes an exception and returns True if it should be retried
        """
        self.max_attempts = max_attempts
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.retry_on = retry_on or []
        self.retry_if = retry_if

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Determine if a retry should be attempted.

        Args:
            exception: The exception that was raised
            attempt: The current attempt number (1-based)

        Returns:
            bool: True if a retry should be attempted, False otherwise
        """
        # Check if we've exceeded the maximum number of attempts
        if attempt >= self.max_attempts:
            return False

        # Check if the exception is in the retry_on list
        for exc_type in self.retry_on:
            if isinstance(exc_type, ErrorCategory):
                # If it's a PyProcessorError, check the category
                if (
                    isinstance(exception, PyProcessorError)
                    and exception.category == exc_type
                ):
                    return True
                # If it's a standard exception, convert it and check the category
                error_manager = get_error_manager()
                category = error_manager._categorize_exception(exception)
                if category == exc_type:
                    return True
            elif isinstance(exception, exc_type):
                return True

        # Check the retry_if function if provided
        if self.retry_if is not None:
            return self.retry_if(exception)

        return False

    def get_delay(self, attempt: int) -> float:
        """
        Get the delay for a retry attempt.

        Args:
            attempt: The current attempt number (1-based)

        Returns:
            float: The delay in seconds
        """
        delay = self.retry_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)


def with_retry(retry_config: Optional[RetryConfig] = None):
    """
    Decorator to add retry behavior to a function.

    This decorator will retry the function if it raises an exception
    that matches the retry configuration.

    Args:
        retry_config: Retry configuration

    Returns:
        The decorated function
    """
    if retry_config is None:
        retry_config = RetryConfig()

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1

            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:

                    # Check if we should retry
                    if retry_config.should_retry(e, attempt):
                        # Get the delay for this attempt
                        delay = retry_config.get_delay(attempt)

                        # Log the retry
                        logger = get_logger()
                        logger.warning(
                            f"Retrying {func.__name__} after error: {str(e)}. "
                            f"Attempt {attempt}/{retry_config.max_attempts}. "
                            f"Retrying in {delay:.2f}s."
                        )

                        # Wait before retrying
                        time.sleep(delay)

                        # Increment the attempt counter
                        attempt += 1
                    else:
                        # Convert and handle the exception
                        error = convert_exception(e)
                        handle_error(error)
                        raise error

        return wrapper

    return decorator


def retry(
    func: Optional[Callable] = None,
    *,
    max_attempts: int = 3,
    retry_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    retry_on: Optional[List[Union[Type[Exception], ErrorCategory]]] = None,
    retry_if: Optional[Callable[[Exception], bool]] = None,
):
    """
    Decorator to add retry behavior to a function.

    This decorator will retry the function if it raises an exception
    that matches the retry configuration.

    Args:
        func: The function to decorate
        max_attempts: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        backoff_factor: Factor to increase delay between retries
        max_delay: Maximum delay between retries in seconds
        retry_on: List of exception types or error categories to retry on
        retry_if: Function that takes an exception and returns True if it should be retried

    Returns:
        The decorated function
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        retry_delay=retry_delay,
        backoff_factor=backoff_factor,
        max_delay=max_delay,
        retry_on=retry_on,
        retry_if=retry_if,
    )

    return with_retry(config)(func) if func else with_retry(config)


def with_error_handling(func=None, *, category=None, reraise=True, context=None):
    """
    Decorator to add error handling to a function.

    This decorator catches any exceptions raised by the function,
    converts them to PyProcessorError, and handles them using the error manager.

    Args:
        func: The function to decorate
        category: Optional error category to use for all exceptions
        reraise: Whether to reraise the exception after handling
        context: Additional context to include in the error details

    Returns:
        The decorated function
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get function information for better error context
            module = func.__module__
            qualname = func.__qualname__

            # Build error context
            error_context = {
                "function": f"{module}.{qualname}",
                "args": str(args),
                "kwargs": str(kwargs),
                "timestamp": datetime.now().isoformat(),
            }

            # Add custom context if provided
            if context:
                if callable(context):
                    try:
                        ctx = context(*args, **kwargs)
                        if isinstance(ctx, dict):
                            error_context.update(ctx)
                    except Exception as ctx_error:
                        error_context["context_error"] = str(ctx_error)
                elif isinstance(context, dict):
                    error_context.update(context)

            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Convert the exception to a PyProcessorError
                error = convert_exception(
                    e,
                    message=f"Error in {qualname}: {str(e)}",
                    category=category,
                    details=error_context,
                )

                # Handle the error
                handle_error(error)

                # Reraise if requested
                if reraise:
                    raise error
                return None

        return wrapper

    # Handle both @with_error_handling and @with_error_handling(category=...)
    if func is None:
        return decorator
    return decorator(func)


class ErrorContext:
    """
    Context manager for error handling.

    This context manager catches any exceptions raised within its scope,
    converts them to PyProcessorError, and handles them using the error manager.

    Example:
        with ErrorContext("Processing file", category=ErrorCategory.FILE_SYSTEM) as ctx:
            ctx.set_context(file_path=file_path)
            process_file(file_path)
    """

    def __init__(self, operation: str, category=None, reraise=True, details=None):
        """
        Initialize the context manager.

        Args:
            operation: Description of the operation being performed
            category: Optional error category to use for all exceptions
            reraise: Whether to reraise the exception after handling
            details: Additional details to include in the error
        """
        self.operation = operation
        self.category = category
        self.reraise = reraise
        self.details = details or {}
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, _):
        # Calculate duration
        duration = time.time() - self.start_time
        self.details["duration"] = f"{duration:.2f}s"

        # If no exception, just return
        if exc_type is None:
            return False

        # Get caller information
        frame = inspect.currentframe().f_back
        filename = frame.f_code.co_filename
        lineno = frame.f_lineno
        function = frame.f_code.co_name

        # Add caller information to details
        self.details["caller"] = {
            "file": os.path.basename(filename),
            "line": lineno,
            "function": function,
        }

        # Convert the exception to a PyProcessorError
        error = convert_exception(
            exc_val,
            message=f"Error during {self.operation}: {str(exc_val)}",
            category=self.category,
            details=self.details,
        )

        # Handle the error
        handle_error(error)

        # Return True to suppress the exception, False to propagate it
        return not self.reraise

    def set_context(self, **kwargs):
        """
        Set additional context information.

        Args:
            **kwargs: Context information to add to the error details
        """
        self.details.update(kwargs)
