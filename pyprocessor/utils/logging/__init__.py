"""
Logging and error handling utilities for PyProcessor.

This module provides utilities for logging and error management.
"""

from pyprocessor.utils.logging.log_manager import (
    LogManager, get_logger, set_context, get_context, clear_context,
    analyze_logs, get_metrics, reset_metrics
)
from pyprocessor.utils.logging.error_manager import (
    ErrorManager, get_error_manager, ErrorSeverity, ErrorCategory,
    PyProcessorError, with_error_handling, handle_error, register_error_handler
)
