# Error Handling in PyProcessor

This document describes the error handling system in PyProcessor, including custom exception classes, error categorization, and error recovery mechanisms.

## Error Manager

PyProcessor uses a centralized error handling system through the `ErrorManager` class in the `pyprocessor.utils.error_manager` module. This provides:

- Consistent error handling across the application
- Error categorization and severity levels
- Error recovery mechanisms
- Error reporting and logging
- Error history tracking
- Error metrics and aggregation
- Error notification capabilities
- Error serialization/deserialization

## Custom Exception Classes

The error handling system defines a hierarchy of custom exception classes:

- `PyProcessorError`: Base exception class for all PyProcessor errors
  - `ConfigurationError`: Configuration-related errors
  - `FileSystemError`: File system-related errors
  - `NetworkError`: Network-related errors
  - `EncodingError`: Encoding-related errors
  - `ProcessError`: Process-related errors
  - `ValidationError`: Validation-related errors
  - `ResourceError`: Resource-related errors
  - `PermissionError`: Permission-related errors
  - `SystemError`: System-related errors

Each exception includes:

- A message
- A severity level
- A category
- The original exception (if applicable)
- Additional details
- A unique error ID
- A timestamp
- Recovery status information

## Error Severity Levels

Errors are categorized by severity:

- `INFO`: Informational messages that don't indicate a problem
- `WARNING`: Potential issues that don't prevent operation
- `ERROR`: Issues that prevent a specific operation but allow the application to continue
- `CRITICAL`: Severe issues that may prevent the application from functioning

## Error Categories

Errors are categorized by type:

- `CONFIGURATION`: Configuration-related errors
- `FILE_SYSTEM`: File system-related errors
- `NETWORK`: Network-related errors
- `ENCODING`: Encoding-related errors
- `PROCESS`: Process-related errors
- `VALIDATION`: Validation-related errors
- `RESOURCE`: Resource-related errors
- `PERMISSION`: Permission-related errors
- `SYSTEM`: System-related errors
- `UNKNOWN`: Errors that don't fit into other categories

## Using the Error Manager

### Accessing the Error Manager

```python
from pyprocessor.utils.error_manager import get_error_manager

# Get the error manager
error_manager = get_error_manager()
```

### Handling Errors

```python
from pyprocessor.utils.error_manager import handle_error, convert_exception

try:
    # Some code that might raise an exception
    result = process_file(file_path)
except Exception as e:
    # Convert the exception to a PyProcessorError
    error = convert_exception(e, f"Error processing file {file_path}")

    # Handle the error
    handle_error(error)
```

### Safe Function Calls

```python
from pyprocessor.utils.error_manager import safe_call

# Call a function safely
success, result, error = safe_call(process_file, file_path)

if success:
    # Use the result
    print(f"Successfully processed file: {result}")
else:
    # Handle the error
    print(f"Failed to process file: {error}")
```

### Result Type

The error handling system provides a `Result` type for operations that might fail:

```python
from pyprocessor.utils.error_manager import Result, try_call

# Create a successful result
result = Result.ok(42)

# Create a failed result
result = Result.fail("Something went wrong")

# Check if the result is successful
if result:
    # Use the value
    value = result.value
else:
    # Handle the error
    error = result.error

# Unwrap the result (raises an error if unsuccessful)
try:
    value = result.unwrap()
except PyProcessorError as e:
    # Handle the error
    print(f"Error: {e}")

# Unwrap with a default value
value = result.unwrap_or(0)

# Map the result
result2 = result.map(lambda x: x * 2)

# Flat map the result
result3 = result.flat_map(lambda x: Result.ok(x * 2))

# Try to call a function and get a Result
result = try_call(connect_to_server)
```

### Error Handling Decorator

```python
from pyprocessor.utils.error_manager import with_error_handling, ErrorCategory

# Basic usage
@with_error_handling
def process_file(file_path):
    # This function will have automatic error handling
    # Any exceptions will be converted to PyProcessorError and handled
    with open(file_path, 'r') as f:
        return f.read()

# Advanced usage
@with_error_handling(
    category=ErrorCategory.FILE_SYSTEM,
    reraise=True,
    context={"operation": "file processing"}
)
def process_file(file_path):
    # Function code here
    pass

# Dynamic context
@with_error_handling(
    context=lambda file_path: {"file_path": file_path}
)
def process_file(file_path):
    # Function code here
    pass
```

### Error Context Manager

The system provides a context manager for error handling:

```python
from pyprocessor.utils.error_manager import ErrorContext, ErrorCategory

# Basic usage
with ErrorContext("Processing file"):
    process_file(file_path)

# Advanced usage
with ErrorContext(
    "Processing file",
    category=ErrorCategory.FILE_SYSTEM,
    reraise=True,
    details={"file_path": file_path}
) as ctx:
    # Add more context information
    ctx.set_context(start_time=time.time())
    process_file(file_path)
```

## Custom Error Handlers

You can register custom error handlers for specific error categories:

```python
from pyprocessor.utils.error_manager import get_error_manager, ErrorCategory

def custom_network_error_handler(error):
    # Custom handling for network errors
    print(f"Network error: {error}")

    # Attempt to reconnect
    try_reconnect()

    # Return True to indicate the error was handled
    return True

# Register the custom handler
error_manager = get_error_manager()
error_manager.register_error_handler(ErrorCategory.NETWORK, custom_network_error_handler)
```

## Error History and Metrics

The error manager keeps track of recent errors and provides metrics on error patterns:

```python
from pyprocessor.utils.error_manager import get_error_manager, get_error_history, get_filtered_error_history, get_error_metrics
from pyprocessor.utils.error_manager import ErrorCategory, ErrorSeverity
from datetime import datetime, timedelta

# Get the error manager
error_manager = get_error_manager()

# Get the error history
error_history = get_error_history()

# Get the last error
last_error = error_manager.get_last_error()

# Clear the error history
error_manager.clear_error_history()

# Get filtered errors
critical_errors = get_filtered_error_history(
    severity=ErrorSeverity.CRITICAL,
    start_time=datetime.now() - timedelta(days=1),
    max_results=10
)

# Get similar errors
similar_errors = get_similar_errors(last_error)

# Get error metrics
metrics = get_error_metrics()
print(f"Total errors: {metrics['total_errors']}")
print(f"Most common errors: {metrics['most_common_errors']}")
```

### Retry Mechanism

The system provides a retry mechanism for operations that might fail temporarily:

```python
from pyprocessor.utils.error_manager import retry, ErrorCategory

# Basic usage
@retry
def connect_to_server():
    # Function code here
    pass

# Advanced usage
@retry(
    max_attempts=5,
    retry_delay=1.0,
    backoff_factor=2.0,
    max_delay=60.0,
    retry_on=[ConnectionError, TimeoutError, ErrorCategory.NETWORK],
    retry_if=lambda e: isinstance(e, IOError) and e.errno == 11
)
def connect_to_server():
    # Function code here
    pass
```

## Best Practices

1. **Use Custom Exception Classes**: Use the appropriate custom exception class for each error type.
2. **Include Context**: Provide detailed error messages with context about what was happening when the error occurred.
3. **Handle Errors at the Appropriate Level**: Handle errors at the level where you have enough context to make a decision.
4. **Log Errors**: Always log errors with appropriate severity levels.
5. **Provide Recovery Mechanisms**: When possible, provide ways to recover from errors.
6. **Use the Error Handling Decorator**: Use the `with_error_handling` decorator for functions that should have automatic error handling.
7. **Use Safe Function Calls**: Use `safe_call` for functions that might raise exceptions when you want to handle the error locally.
8. **Use the Result Type**: Use the `Result` type for operations that might fail.
9. **Use the Error Context Manager**: Use the `ErrorContext` context manager for error handling in a specific scope.
10. **Use the Retry Mechanism**: Use the retry mechanism for operations that might fail temporarily.
11. **Register Recovery Handlers**: Register recovery handlers for common errors to automate recovery.
12. **Register Notification Handlers**: Register notification handlers for critical errors to ensure timely response.
13. **Monitor Error Metrics**: Use error metrics to identify patterns and recurring issues.
14. **Export Error History**: Export error history for long-term storage and analysis.
15. **Use Error Aggregation**: Use error aggregation to reduce noise from similar errors.

## Example: Complete Error Handling

```python
from pyprocessor.utils.error_manager import (
    get_error_manager,
    handle_error,
    convert_exception,
    safe_call,
    with_error_handling,
    ErrorContext,
    retry,
    Result,
    try_call,
    ErrorCategory,
    ErrorSeverity,
    EncodingError,
    FileSystemError,
    PyProcessorError
)

# Register a custom error handler
def custom_encoding_error_handler(error):
    # Try an alternative encoding method
    if "libx265" in str(error):
        try:
            # Try with libx264 instead
            result = encode_with_libx264(error.details.get("file_path"))
            return True
        except Exception as e:
            # If that also fails, log it and continue with normal handling
            logger.error(f"Alternative encoding also failed: {e}")

    # Return False to indicate the error wasn't fully handled
    # and should be processed by the default handler
    return False

# Get the error manager and register the custom handler
error_manager = get_error_manager()
error_manager.register_error_handler(ErrorCategory.ENCODING, custom_encoding_error_handler)

# Function with automatic error handling and retry
@with_error_handling(category=ErrorCategory.ENCODING)
@retry(max_attempts=3, retry_on=[IOError, ErrorCategory.NETWORK])
def encode_video(file_path, output_path):
    # This function will have automatic error handling and retry
    with ErrorContext("Encoding video", details={"file_path": file_path, "output_path": output_path}) as ctx:
        if not os.path.exists(file_path):
            # Raise a custom exception
            raise FileSystemError(
                f"Input file not found: {file_path}",
                severity=ErrorSeverity.ERROR,
                details={"file_path": file_path, "output_path": output_path}
            )

        # Add more context information
        ctx.set_context(file_size=os.path.getsize(file_path))

        # Attempt to encode the video
        result = ffmpeg.encode(file_path, output_path)

        if not result.success:
            # Raise a custom exception
            raise EncodingError(
                f"Failed to encode video: {result.error}",
                severity=ErrorSeverity.ERROR,
                details={"file_path": file_path, "output_path": output_path, "ffmpeg_result": result}
            )

        return result

# Function that returns a Result
def process_file(file_path):
    # Try to process the file and return a Result
    return try_call(encode_video, file_path, get_output_path(file_path))

# Main processing function
def process_videos(file_paths):
    results = []

    for file_path in file_paths:
        # Get a Result from the process_file function
        result = process_file(file_path)

        if result:
            # Success case
            results.append((file_path, True, result.value, None))
        else:
            # Error case
            error = result.error
            logger.error(f"Error processing {file_path}: {error}")
            results.append((file_path, False, None, str(error)))

    return results
```

## Error Recovery and Notification

The error manager provides mechanisms for recovering from errors and notifying users or administrators of critical errors:

```python
from pyprocessor.utils.error_manager import register_recovery_handler, register_notification_handler
from pyprocessor.utils.error_manager import ErrorCategory, PyProcessorError, ErrorSeverity
from datetime import timedelta

# Define a recovery handler
def file_system_recovery_handler(error: PyProcessorError) -> bool:
    """Try to recover from file system errors."""
    if "file_not_found" in error.details:
        try:
            with open(error.details["file_path"], "w") as f:
                f.write("")
            return True
        except Exception:
            return False
    return False

# Register the recovery handler
register_recovery_handler(ErrorCategory.FILE_SYSTEM, file_system_recovery_handler)

# Define a notification handler
def critical_error_notification_handler(error: PyProcessorError) -> None:
    """Send a notification for critical errors."""
    # Send an email, Slack message, etc.
    send_email(
        to="admin@example.com",
        subject=f"Critical Error: {error.message}",
        body=f"Error details: {error.to_dict()}"
    )

# Register the notification handler
register_notification_handler(ErrorCategory.SYSTEM, critical_error_notification_handler)

# Set the notification threshold
set_notification_threshold(ErrorSeverity.ERROR)

# Set the notification cooldown
set_notification_cooldown(timedelta(minutes=30))
```

## Error Serialization

The error manager provides mechanisms for serializing and deserializing errors:

```python
from pyprocessor.utils.error_manager import serialize_errors, deserialize_errors, export_error_history, import_error_history

# Serialize errors to JSON
errors = get_error_history()
json_str = serialize_errors(errors)

# Deserialize errors from JSON
errors = deserialize_errors(json_str)

# Export error history to a file
export_error_history("/path/to/error_history.json")

# Import error history from a file
import_error_history("/path/to/error_history.json")
```

## Error Handling Flow

1. **Exception Occurs**: An exception is raised during operation.
2. **Exception Conversion**: The exception is converted to a `PyProcessorError` with appropriate category and severity.
3. **Error Handling**: The error is passed to the error manager for handling.
4. **Custom Handler**: If a custom handler is registered for the error category, it's called first.
5. **Default Handler**: If no custom handler is registered or the custom handler returns False, the default handler is called.
6. **Logging**: The error is logged with the appropriate severity level.
7. **Error Metrics**: Error metrics are updated.
8. **Recovery**: If possible, recovery mechanisms are attempted.
9. **Error History**: The error is added to the error history and similar errors are aggregated.
10. **Notification**: If the error severity is above the notification threshold, notification handlers are called.
11. **Reporting**: The error is reported to the user if appropriate.
