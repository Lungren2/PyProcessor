"""
Enhanced error handling module for PyProcessor.

This module extends the existing error_manager.py functionality with:
- Context-specific error messages with actionable advice
- Error recovery mechanisms for common failure scenarios
- Graceful degradation for non-critical failures
- Comprehensive error logging with context information
- Error aggregation and reporting
- Retry mechanisms with exponential backoff
- User-friendly error messages for CLI and API
"""

import sys
import os
import time
import json
import traceback
import inspect
import functools
from enum import Enum
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union, TypeVar, Generic, Set

# Import from existing error manager
from pyprocessor.utils.logging.error_manager import (
    PyProcessorError, ErrorCategory, ErrorSeverity, Result,
    get_error_manager, handle_error, convert_exception,
    ErrorContext, retry
)
from pyprocessor.utils.logging.log_manager import get_logger

# Type variables for generic functions
T = TypeVar('T')
R = TypeVar('R')

# Context-specific error messages with actionable advice

class ErrorAdvice:
    """Provides context-specific error messages with actionable advice."""

    # Dictionary mapping error categories to advice templates
    _advice_templates = {
        ErrorCategory.CONFIGURATION: {
            "default": "Check your configuration file for errors. Ensure all required fields are present and have valid values.",
            "missing_field": "The configuration field '{field}' is missing. Please add it to your configuration file.",
            "invalid_value": "The value '{value}' for '{field}' is invalid. {reason}"
        },
        ErrorCategory.FILE_SYSTEM: {
            "default": "Check file paths and permissions. Ensure the file exists and you have the necessary permissions.",
            "file_not_found": "The file '{path}' was not found. Please check if the file exists at the specified location.",
            "permission_denied": "Permission denied for '{path}'. Please check file permissions.",
            "disk_full": "Disk is full. Free up some space and try again."
        },
        ErrorCategory.NETWORK: {
            "default": "Check your network connection and try again.",
            "connection_refused": "Connection to '{host}:{port}' was refused. Ensure the server is running and accessible.",
            "timeout": "Connection to '{host}:{port}' timed out. Check your network connection or server status.",
            "dns_error": "Could not resolve host '{host}'. Check your DNS settings or internet connection."
        },
        ErrorCategory.ENCODING: {
            "default": "There was an error during video encoding. Check the input file and encoding parameters.",
            "unsupported_format": "The format '{format}' is not supported. Supported formats are: {supported_formats}.",
            "codec_error": "Error with codec '{codec}'. {reason}",
            "ffmpeg_error": "FFmpeg error: {message}. Check your encoding parameters and input file."
        },
        ErrorCategory.PROCESS: {
            "default": "An error occurred during processing. Check the logs for more details.",
            "process_killed": "The process was killed. This might be due to insufficient resources.",
            "process_timeout": "The process timed out after {timeout} seconds. Consider increasing the timeout."
        },
        ErrorCategory.VALIDATION: {
            "default": "Input validation failed. Check your input values.",
            "invalid_input": "Invalid input: {reason}",
            "missing_required": "Missing required input: {field}"
        },
        ErrorCategory.RESOURCE: {
            "default": "Insufficient resources. Try closing other applications or reducing batch size.",
            "memory_error": "Out of memory. Try reducing batch size or closing other applications.",
            "cpu_overload": "CPU is overloaded. Try reducing the number of parallel processes.",
            "disk_space": "Insufficient disk space. Free up at least {required_space} and try again."
        },
        ErrorCategory.PERMISSION: {
            "default": "Permission denied. Ensure you have the necessary permissions.",
            "admin_required": "Administrator privileges required for this operation.",
            "file_permission": "Permission denied for file '{path}'. Check file permissions."
        },
        ErrorCategory.SYSTEM: {
            "default": "A system error occurred. Check your system configuration.",
            "os_error": "Operating system error: {message}",
            "environment_error": "Environment error: {message}. Check your system environment."
        },
        ErrorCategory.UNKNOWN: {
            "default": "An unknown error occurred. Please check the logs for more details."
        }
    }

    @classmethod
    def get_advice(cls, error: PyProcessorError) -> str:
        """Get actionable advice for an error.

        Args:
            error: The error to get advice for

        Returns:
            str: Actionable advice for the error
        """
        # Get the error category
        category = error.category

        # Get the error type from details if available
        error_type = error.details.get("error_type", "default") if error.details else "default"

        # Get the advice template
        template = cls._advice_templates.get(category, {}).get(error_type)

        # If no specific template is found, use the default for the category
        if template is None:
            template = cls._advice_templates.get(category, {}).get("default")

        # If still no template, use a generic message
        if template is None:
            return "An error occurred. Please check the logs for more details."

        # Format the template with details from the error
        try:
            if error.details:
                return template.format(**error.details)
            else:
                return template
        except KeyError:
            # If formatting fails, return the template as is
            return template

    @classmethod
    def add_advice_to_error(cls, error: PyProcessorError) -> PyProcessorError:
        """Add actionable advice to an error.

        Args:
            error: The error to add advice to

        Returns:
            PyProcessorError: The error with advice added
        """
        # Get advice for the error
        advice = cls.get_advice(error)

        # Add advice to error details
        if error.details is None:
            error.details = {}
        error.details["advice"] = advice

        return error


def with_advice(func):
    """Decorator to add actionable advice to errors raised by a function.

    Args:
        func: The function to decorate

    Returns:
        Callable: The decorated function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PyProcessorError as e:
            # Add advice to the error
            ErrorAdvice.add_advice_to_error(e)
            raise
        except Exception as e:
            # Convert to PyProcessorError and add advice
            error = convert_exception(e)
            ErrorAdvice.add_advice_to_error(error)
            raise error
    return wrapper

# Error recovery mechanisms for common failure scenarios

class ErrorRecovery:
    """Provides recovery mechanisms for common failure scenarios."""

    @staticmethod
    def recover_file_not_found(error: PyProcessorError) -> bool:
        """Try to recover from a file not found error.

        Args:
            error: The error to recover from

        Returns:
            bool: True if recovery was successful, False otherwise
        """
        # Check if we have the necessary details
        if not error.details or "path" not in error.details:
            return False

        path = error.details["path"]
        logger = get_logger()

        # Check if it's a directory issue
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            try:
                # Try to create the directory
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created directory: {directory}")
                return True
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {e}")
                return False

        # If it's a file that should exist but doesn't, we can't recover
        return False

    @staticmethod
    def recover_permission_denied(error: PyProcessorError) -> bool:
        """Try to recover from a permission denied error.

        Args:
            error: The error to recover from

        Returns:
            bool: True if recovery was successful, False otherwise
        """
        # Permission issues usually can't be automatically recovered
        # Log a more helpful message instead
        if error.details and "path" in error.details:
            path = error.details["path"]
            logger = get_logger()
            logger.warning(f"Permission denied for {path}. Please check file permissions.")

        return False

    @staticmethod
    def recover_disk_full(error: PyProcessorError) -> bool:
        """Try to recover from a disk full error.

        Args:
            error: The error to recover from

        Returns:
            bool: True if recovery was successful, False otherwise
        """
        # Try to clean up temporary files
        logger = get_logger()

        # Log the error details for debugging
        if error.details:
            logger.debug(f"Attempting to recover from disk full error with details: {error.details}")

        temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ffmpeg_temp")

        if os.path.exists(temp_dir):
            try:
                # Remove all files in the temp directory
                for filename in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, filename)
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                logger.info(f"Cleaned up temporary files in {temp_dir}")
                return True
            except Exception as e:
                logger.error(f"Failed to clean up temporary files: {e}")

        return False

    @staticmethod
    def recover_network_timeout(error: PyProcessorError) -> bool:
        """Try to recover from a network timeout error.

        Args:
            error: The error to recover from

        Returns:
            bool: True if recovery was successful, False otherwise
        """
        # Network timeouts might be temporary, so we can't really recover
        # but we can provide a helpful message
        logger = get_logger()

        # Log the error details for debugging
        if error.details:
            host = error.details.get('host', 'unknown')
            port = error.details.get('port', 'unknown')
            logger.debug(f"Network timeout for {host}:{port}")
            logger.warning(f"Network timeout occurred for {host}:{port}. This might be temporary, please try again later.")
        else:
            logger.warning("Network timeout occurred. This might be temporary, please try again later.")

        return False

    @staticmethod
    def recover_encoding_error(error: PyProcessorError) -> bool:
        """Try to recover from an encoding error.

        Args:
            error: The error to recover from

        Returns:
            bool: True if recovery was successful, False otherwise
        """
        # Most encoding errors can't be automatically recovered
        # but we can check for common issues
        logger = get_logger()

        if error.details and "message" in error.details:
            message = error.details["message"]

            # Check for specific FFmpeg errors that might be recoverable
            if "No such file or directory" in message and "ffmpeg" in message.lower():
                logger.warning("FFmpeg not found. Please ensure FFmpeg is installed and in your PATH.")
            elif "Invalid data found when processing input" in message:
                logger.warning("Invalid input file. The file might be corrupted or in an unsupported format.")

        return False


def register_recovery_handlers():
    """Register recovery handlers for common error categories."""
    error_manager = get_error_manager()

    # Register recovery handlers
    error_manager.register_recovery_handler(ErrorCategory.FILE_SYSTEM, ErrorRecovery.recover_file_not_found)
    error_manager.register_recovery_handler(ErrorCategory.PERMISSION, ErrorRecovery.recover_permission_denied)
    error_manager.register_recovery_handler(ErrorCategory.RESOURCE, ErrorRecovery.recover_disk_full)
    error_manager.register_recovery_handler(ErrorCategory.NETWORK, ErrorRecovery.recover_network_timeout)
    error_manager.register_recovery_handler(ErrorCategory.ENCODING, ErrorRecovery.recover_encoding_error)


# Initialize recovery handlers
register_recovery_handlers()

# Graceful degradation for non-critical failures

class GracefulDegradation:
    """Provides mechanisms for graceful degradation when non-critical failures occur."""

    # Dictionary of fallback functions for different operations
    _fallbacks = {}

    @classmethod
    def register_fallback(cls, operation: str, fallback_func: Callable):
        """Register a fallback function for an operation.

        Args:
            operation: The operation name
            fallback_func: The fallback function to call
        """
        cls._fallbacks[operation] = fallback_func

    @classmethod
    def get_fallback(cls, operation: str) -> Optional[Callable]:
        """Get a fallback function for an operation.

        Args:
            operation: The operation name

        Returns:
            Optional[Callable]: The fallback function, or None if not found
        """
        return cls._fallbacks.get(operation)

    @classmethod
    def with_fallback(cls, operation: str, default_value: Any = None):
        """Decorator to add fallback behavior to a function.

        Args:
            operation: The operation name
            default_value: Default value to return if both the function and fallback fail

        Returns:
            Callable: The decorated function
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    # Try the original function
                    return func(*args, **kwargs)
                except Exception as e:
                    # Log the error
                    logger = get_logger()
                    logger.warning(f"Error in {operation}, trying fallback: {str(e)}")

                    # Convert to PyProcessorError for proper handling
                    error = convert_exception(e)
                    error.details = error.details or {}
                    error.details["operation"] = operation
                    error.details["is_fallback"] = True

                    # Try the fallback if available
                    fallback = cls.get_fallback(operation)
                    if fallback:
                        try:
                            logger.info(f"Using fallback for {operation}")
                            return fallback(*args, **kwargs)
                        except Exception as fallback_error:
                            # Log the fallback error
                            logger.error(f"Fallback for {operation} also failed: {str(fallback_error)}")

                    # Handle the original error
                    handle_error(error)

                    # Return default value if both original and fallback failed
                    return default_value
            return wrapper
        return decorator


def fallback_for(operation: str):
    """Decorator to register a function as a fallback for an operation.

    Args:
        operation: The operation name

    Returns:
        Callable: The decorated function
    """
    def decorator(func):
        GracefulDegradation.register_fallback(operation, func)
        return func
    return decorator


# Example fallback functions

@fallback_for("video_encoding")
def fallback_video_encoding(input_file, output_file, params):
    """Fallback for video encoding that uses simpler parameters.

    Args:
        input_file: Input file path
        output_file: Output file path
        params: Encoding parameters

    Returns:
        bool: True if successful, False otherwise
    """
    logger = get_logger()
    logger.info(f"Using simplified encoding parameters as fallback instead of: {params}")

    # Use simpler encoding parameters
    simplified_params = {
        "codec": "libx264",
        "preset": "medium",
        "crf": "23"
    }

    # Import here to avoid circular imports
    try:
        from pyprocessor.processing.encoder import encode_video
        return encode_video(input_file, output_file, simplified_params)
    except Exception as e:
        logger.error(f"Fallback encoding failed: {str(e)}")
        return False


@fallback_for("thumbnail_generation")
def fallback_thumbnail_generation(video_file, output_file):
    """Fallback for thumbnail generation that extracts a frame from the middle.

    Args:
        video_file: Video file path
        output_file: Output thumbnail path

    Returns:
        bool: True if successful, False otherwise
    """
    logger = get_logger()
    logger.info("Using simplified thumbnail extraction as fallback")

    try:
        import subprocess
        # Extract a frame from the middle of the video
        result = subprocess.run([
            "ffmpeg",
            "-i", video_file,
            "-ss", "00:00:05",  # 5 seconds in
            "-frames:v", "1",
            "-q:v", "2",
            output_file
        ], capture_output=True, text=True, check=False)

        if result.returncode == 0:
            return True
        else:
            logger.error(f"Fallback thumbnail generation failed: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Fallback thumbnail generation failed: {str(e)}")
        return False

# Comprehensive error logging with context information

class ContextLogger:
    """Provides context-aware logging for errors."""

    # Thread-local storage for context information
    _context = threading.local()

    @classmethod
    def init_context(cls):
        """Initialize the context for the current thread."""
        if not hasattr(cls._context, "data"):
            cls._context.data = {}

    @classmethod
    def set_context(cls, **kwargs):
        """Set context information for the current thread.

        Args:
            **kwargs: Context information to set
        """
        cls.init_context()
        cls._context.data.update(kwargs)

    @classmethod
    def get_context(cls):
        """Get context information for the current thread.

        Returns:
            dict: Context information
        """
        cls.init_context()
        return cls._context.data.copy()

    @classmethod
    def clear_context(cls):
        """Clear context information for the current thread."""
        if hasattr(cls._context, "data"):
            cls._context.data.clear()

    @classmethod
    def with_context(cls, **context):
        """Decorator to add context information to a function.

        Args:
            **context: Context information to add

        Returns:
            Callable: The decorated function
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Save the current context
                old_context = cls.get_context()

                try:
                    # Add new context information
                    cls.set_context(**context)

                    # Add function information to context
                    cls.set_context(
                        function=func.__name__,
                        module=func.__module__
                    )

                    # Add dynamic context if provided as a function
                    for key, value in context.items():
                        if callable(value) and not key.startswith("_"):
                            try:
                                # Call the function with the same arguments
                                dynamic_value = value(*args, **kwargs)
                                cls.set_context(**{key: dynamic_value})
                            except Exception:
                                # Ignore errors in dynamic context functions
                                pass

                    # Call the function
                    return func(*args, **kwargs)
                finally:
                    # Restore the old context
                    cls.clear_context()
                    cls.set_context(**old_context)
            return wrapper
        return decorator

    @classmethod
    def log_with_context(cls, logger, level, message, *args, **kwargs):
        """Log a message with context information.

        Args:
            logger: The logger to use
            level: The log level
            message: The log message
            *args: Additional arguments for the logger
            **kwargs: Additional keyword arguments for the logger
        """
        # Get context information
        context = cls.get_context()

        # Add context to the message if available
        if context:
            context_str = ", ".join(f"{k}={v}" for k, v in context.items())
            message = f"{message} [Context: {context_str}]"

        # Log the message
        logger.log(level, message, *args, **kwargs)


def log_error_with_context(error: PyProcessorError, logger=None):
    """Log an error with context information.

    Args:
        error: The error to log
        logger: The logger to use (default: get_logger())

    Returns:
        PyProcessorError: The error that was logged
    """
    if logger is None:
        logger = get_logger()

    # Get context information
    context = ContextLogger.get_context()

    # Add context to error details if not already present
    if error.details is None:
        error.details = {}
    if "context" not in error.details:
        error.details["context"] = context

    # Get the log level based on error severity
    if error.severity == ErrorSeverity.INFO:
        level = logging.INFO
    elif error.severity == ErrorSeverity.WARNING:
        level = logging.WARNING
    elif error.severity == ErrorSeverity.CRITICAL:
        level = logging.CRITICAL
    else:  # ERROR
        level = logging.ERROR

    # Get the error message
    message = str(error)

    # Add advice if available
    if "advice" in error.details:
        message = f"{message} - {error.details['advice']}"

    # Log the error with context
    ContextLogger.log_with_context(logger, level, message)

    return error


def with_context_logging(func):
    """Decorator to add context logging to a function.

    Args:
        func: The function to decorate

    Returns:
        Callable: The decorated function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Add function information to context
        ContextLogger.set_context(
            function=func.__name__,
            module=func.__module__
        )

        try:
            # Call the function
            return func(*args, **kwargs)
        except PyProcessorError as e:
            # Log the error with context
            log_error_with_context(e)
            raise
        except Exception as e:
            # Convert to PyProcessorError and log with context
            error = convert_exception(e)
            log_error_with_context(error)
            raise error
    return wrapper

# Error aggregation and reporting

class ErrorAggregator:
    """Provides error aggregation and reporting functionality."""

    # Dictionary to store error counts by fingerprint
    _error_counts = {}

    # Dictionary to store error instances by fingerprint
    _error_instances = {}

    # Lock for thread safety
    _lock = threading.Lock()

    # Maximum number of error instances to store per fingerprint
    _max_instances = 10

    @classmethod
    def add_error(cls, error: PyProcessorError):
        """Add an error to the aggregator.

        Args:
            error: The error to add
        """
        # Generate a fingerprint for the error
        fingerprint = cls._generate_fingerprint(error)

        with cls._lock:
            # Increment the error count
            if fingerprint not in cls._error_counts:
                cls._error_counts[fingerprint] = 0
            cls._error_counts[fingerprint] += 1

            # Store the error instance
            if fingerprint not in cls._error_instances:
                cls._error_instances[fingerprint] = []

            # Only store up to _max_instances per fingerprint
            if len(cls._error_instances[fingerprint]) < cls._max_instances:
                cls._error_instances[fingerprint].append(error)

    @classmethod
    def get_error_counts(cls):
        """Get the error counts.

        Returns:
            dict: Dictionary mapping error fingerprints to counts
        """
        with cls._lock:
            return cls._error_counts.copy()

    @classmethod
    def get_error_instances(cls, fingerprint=None):
        """Get the error instances.

        Args:
            fingerprint: Optional fingerprint to filter by

        Returns:
            dict or list: Dictionary mapping error fingerprints to lists of errors,
                         or list of errors for a specific fingerprint
        """
        with cls._lock:
            if fingerprint is not None:
                return cls._error_instances.get(fingerprint, []).copy()
            else:
                return {k: v.copy() for k, v in cls._error_instances.items()}

    @classmethod
    def clear(cls):
        """Clear all error counts and instances."""
        with cls._lock:
            cls._error_counts.clear()
            cls._error_instances.clear()

    @classmethod
    def _generate_fingerprint(cls, error: PyProcessorError):
        """Generate a fingerprint for an error.

        Args:
            error: The error to generate a fingerprint for

        Returns:
            str: The error fingerprint
        """
        # Use the error category, message, and traceback to generate a fingerprint
        components = [
            str(error.category),
            str(error)
        ]

        # Add the traceback if available
        if hasattr(error, "__traceback__") and error.__traceback__ is not None:
            tb = traceback.extract_tb(error.__traceback__)
            # Only use the first 3 frames to avoid too much detail
            for frame in tb[:3]:
                components.append(f"{frame.filename}:{frame.lineno}")

        # Join the components and hash them
        fingerprint = "|".join(components)
        return fingerprint

    @classmethod
    def generate_report(cls, min_count=1, sort_by="count", limit=None):
        """Generate a report of aggregated errors.

        Args:
            min_count: Minimum error count to include in the report
            sort_by: Field to sort by ("count" or "latest")
            limit: Maximum number of errors to include in the report

        Returns:
            list: List of dictionaries with error information
        """
        with cls._lock:
            # Get all fingerprints with counts above the minimum
            fingerprints = [fp for fp, count in cls._error_counts.items() if count >= min_count]

            # Create a report for each fingerprint
            report = []
            for fp in fingerprints:
                # Get the error instances for this fingerprint
                instances = cls._error_instances.get(fp, [])
                if not instances:
                    continue

                # Get the most recent instance
                latest = instances[-1]

                # Create a report entry
                entry = {
                    "fingerprint": fp,
                    "category": latest.category,
                    "message": str(latest),
                    "count": cls._error_counts.get(fp, 0),
                    "latest": latest.timestamp,
                    "severity": latest.severity,
                    "details": latest.details,
                    "instances": len(instances)
                }

                report.append(entry)

            # Sort the report
            if sort_by == "count":
                report.sort(key=lambda x: x["count"], reverse=True)
            elif sort_by == "latest":
                report.sort(key=lambda x: x["latest"], reverse=True)

            # Limit the report if requested
            if limit is not None:
                report = report[:limit]

            return report


def aggregate_error(error: PyProcessorError):
    """Add an error to the aggregator.

    Args:
        error: The error to add

    Returns:
        PyProcessorError: The error that was added
    """
    ErrorAggregator.add_error(error)
    return error


def generate_error_report(min_count=1, sort_by="count", limit=None):
    """Generate a report of aggregated errors.

    Args:
        min_count: Minimum error count to include in the report
        sort_by: Field to sort by ("count" or "latest")
        limit: Maximum number of errors to include in the report

    Returns:
        list: List of dictionaries with error information
    """
    return ErrorAggregator.generate_report(min_count, sort_by, limit)


def clear_error_aggregation():
    """Clear all error counts and instances."""
    ErrorAggregator.clear()

# Retry mechanisms with exponential backoff

class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        retry_on: List[Union[Type[Exception], ErrorCategory]] = None,
        retry_if: Optional[Callable[[Exception], bool]] = None,
    ):
        """Initialize the retry configuration.

        Args:
            max_attempts: Maximum number of attempts (default: 3)
            initial_delay: Initial delay in seconds (default: 1.0)
            max_delay: Maximum delay in seconds (default: 60.0)
            backoff_factor: Backoff factor (default: 2.0)
            jitter: Whether to add jitter to the delay (default: True)
            retry_on: List of exceptions or error categories to retry on (default: None)
            retry_if: Function that takes an exception and returns True if it should be retried (default: None)
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retry_on = retry_on or []
        self.retry_if = retry_if

    def get_delay(self, attempt: int) -> float:
        """Get the delay for a specific attempt.

        Args:
            attempt: The attempt number (1-based)

        Returns:
            float: The delay in seconds
        """
        # Calculate the delay using exponential backoff
        delay = min(self.initial_delay * (self.backoff_factor ** (attempt - 1)), self.max_delay)

        # Add jitter if enabled
        if self.jitter:
            # Add up to 20% jitter
            jitter_amount = delay * 0.2
            delay = delay + (random.random() * jitter_amount - jitter_amount / 2)

        return delay

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Check if an exception should be retried.

        Args:
            exception: The exception to check
            attempt: The current attempt number (1-based)

        Returns:
            bool: True if the exception should be retried, False otherwise
        """
        # Check if we've reached the maximum number of attempts
        if attempt >= self.max_attempts:
            return False

        # Check if the exception is in the retry_on list
        for exc_type in self.retry_on:
            if isinstance(exc_type, ErrorCategory):
                # If it's a PyProcessorError, check the category
                if isinstance(exception, PyProcessorError) and exception.category == exc_type:
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


def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retry_on: List[Union[Type[Exception], ErrorCategory]] = None,
    retry_if: Optional[Callable[[Exception], bool]] = None,
):
    """Decorator to add retry behavior to a function.

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        backoff_factor: Backoff factor (default: 2.0)
        jitter: Whether to add jitter to the delay (default: True)
        retry_on: List of exceptions or error categories to retry on (default: None)
        retry_if: Function that takes an exception and returns True if it should be retried (default: None)

    Returns:
        Callable: The decorated function
    """
    # Create the retry configuration
    retry_config = RetryConfig(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        max_delay=max_delay,
        backoff_factor=backoff_factor,
        jitter=jitter,
        retry_on=retry_on,
        retry_if=retry_if,
    )

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


def retry_on_network_errors(func=None, max_attempts=3, initial_delay=1.0):
    """Decorator to retry a function on network errors.

    Args:
        func: The function to decorate (default: None)
        max_attempts: Maximum number of attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)

    Returns:
        Callable: The decorated function
    """
    if func is None:
        return lambda f: retry_on_network_errors(f, max_attempts, initial_delay)

    return with_retry(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        retry_on=[ErrorCategory.NETWORK, ConnectionError, TimeoutError]
    )(func)


def retry_on_resource_errors(func=None, max_attempts=3, initial_delay=2.0):
    """Decorator to retry a function on resource errors.

    Args:
        func: The function to decorate (default: None)
        max_attempts: Maximum number of attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 2.0)

    Returns:
        Callable: The decorated function
    """
    if func is None:
        return lambda f: retry_on_resource_errors(f, max_attempts, initial_delay)

    return with_retry(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        retry_on=[ErrorCategory.RESOURCE, MemoryError]
    )(func)

# User-friendly error messages for CLI and API

class UserFriendlyErrors:
    """Provides user-friendly error messages for CLI and API."""

    # Dictionary mapping error categories to user-friendly messages
    _cli_messages = {
        ErrorCategory.CONFIGURATION: "Configuration error: {message}",
        ErrorCategory.FILE_SYSTEM: "File system error: {message}",
        ErrorCategory.NETWORK: "Network error: {message}",
        ErrorCategory.ENCODING: "Encoding error: {message}",
        ErrorCategory.PROCESS: "Process error: {message}",
        ErrorCategory.VALIDATION: "Validation error: {message}",
        ErrorCategory.RESOURCE: "Resource error: {message}",
        ErrorCategory.PERMISSION: "Permission error: {message}",
        ErrorCategory.SYSTEM: "System error: {message}",
        ErrorCategory.UNKNOWN: "Error: {message}"
    }

    # Dictionary mapping error categories to API error codes and messages
    _api_errors = {
        ErrorCategory.CONFIGURATION: {
            "code": "CONFIG_ERROR",
            "status": 400,
            "message": "Configuration error"
        },
        ErrorCategory.FILE_SYSTEM: {
            "code": "FILE_ERROR",
            "status": 400,
            "message": "File system error"
        },
        ErrorCategory.NETWORK: {
            "code": "NETWORK_ERROR",
            "status": 503,
            "message": "Network error"
        },
        ErrorCategory.ENCODING: {
            "code": "ENCODING_ERROR",
            "status": 400,
            "message": "Encoding error"
        },
        ErrorCategory.PROCESS: {
            "code": "PROCESS_ERROR",
            "status": 500,
            "message": "Process error"
        },
        ErrorCategory.VALIDATION: {
            "code": "VALIDATION_ERROR",
            "status": 400,
            "message": "Validation error"
        },
        ErrorCategory.RESOURCE: {
            "code": "RESOURCE_ERROR",
            "status": 503,
            "message": "Resource error"
        },
        ErrorCategory.PERMISSION: {
            "code": "PERMISSION_ERROR",
            "status": 403,
            "message": "Permission error"
        },
        ErrorCategory.SYSTEM: {
            "code": "SYSTEM_ERROR",
            "status": 500,
            "message": "System error"
        },
        ErrorCategory.UNKNOWN: {
            "code": "UNKNOWN_ERROR",
            "status": 500,
            "message": "Unknown error"
        }
    }

    @classmethod
    def get_cli_message(cls, error: PyProcessorError) -> str:
        """Get a user-friendly CLI message for an error.

        Args:
            error: The error to get a message for

        Returns:
            str: User-friendly CLI message
        """
        # Get the template for this error category
        template = cls._cli_messages.get(error.category, cls._cli_messages[ErrorCategory.UNKNOWN])

        # Format the template with the error message
        message = template.format(message=str(error))

        # Add advice if available
        if error.details and "advice" in error.details:
            message = f"{message}\nAdvice: {error.details['advice']}"

        return message

    @classmethod
    def get_api_error(cls, error: PyProcessorError) -> Dict[str, Any]:
        """Get a user-friendly API error for an error.

        Args:
            error: The error to get an API error for

        Returns:
            Dict[str, Any]: API error object
        """
        # Get the API error for this error category
        api_error = cls._api_errors.get(error.category, cls._api_errors[ErrorCategory.UNKNOWN])

        # Create a copy of the API error
        result = api_error.copy()

        # Add the error message
        result["detail"] = str(error)

        # Add advice if available
        if error.details and "advice" in error.details:
            result["advice"] = error.details["advice"]

        # Add error ID if available
        if hasattr(error, "error_id") and error.error_id:
            result["error_id"] = error.error_id

        return result


def format_cli_error(error: PyProcessorError) -> str:
    """Format an error for CLI output.

    Args:
        error: The error to format

    Returns:
        str: Formatted error message
    """
    return UserFriendlyErrors.get_cli_message(error)


def format_api_error(error: PyProcessorError) -> Dict[str, Any]:
    """Format an error for API output.

    Args:
        error: The error to format

    Returns:
        Dict[str, Any]: Formatted API error
    """
    return UserFriendlyErrors.get_api_error(error)


# Import random for jitter in retry mechanism
import random

# Export public API
__all__ = [
    # Error advice
    'ErrorAdvice', 'with_advice',

    # Error recovery
    'ErrorRecovery', 'register_recovery_handlers',

    # Graceful degradation
    'GracefulDegradation', 'fallback_for',

    # Context logging
    'ContextLogger', 'log_error_with_context', 'with_context_logging',

    # Error aggregation
    'ErrorAggregator', 'aggregate_error', 'generate_error_report', 'clear_error_aggregation',

    # Retry mechanisms
    'RetryConfig', 'with_retry', 'retry_on_network_errors', 'retry_on_resource_errors',

    # User-friendly errors
    'UserFriendlyErrors', 'format_cli_error', 'format_api_error',
]
