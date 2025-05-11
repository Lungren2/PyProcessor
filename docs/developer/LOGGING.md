# Logging System

This document provides a detailed overview of the PyProcessor logging system, explaining how it works and how to use it effectively.

## Overview

The PyProcessor application uses a comprehensive logging system that provides detailed information about application operations. Logs are essential for:

- Debugging issues
- Monitoring application performance
- Tracking processing operations
- Auditing application usage
- Analyzing application behavior
- Correlating events across components
- Measuring performance metrics

## Log Location

Logs are stored in the platform-specific logs directory:

- Windows: `%LOCALAPPDATA%\PyProcessor\logs`
- macOS: `~/Library/Logs/PyProcessor`
- Linux: `/var/log/pyprocessor` (if writable) or `~/.local/share/pyprocessor/logs`

Each log file is named with a descriptive pattern that includes:

- Application name
- Date and time
- Log level
- Username
- System information

Example log filename:

```text
pyprocessor_2023-04-09_14-30-25_info_username_windows.log
```

## Log Format

The logging system uses two different formats:

**Detailed Format (File)**: `[TIMESTAMP][LEVEL][MODULE.FUNCTION:LINE] MESSAGE`

```text
[2023-04-09 14:30:25][INFO][encoder.encode_video:123] Starting to encode video.mp4
```

**Simple Format (Console)**: `[LEVEL][MODULE] MESSAGE`

```text
[INFO][encoder] Starting to encode video.mp4
```

## Log Levels

The logging system uses standard Python logging levels:

| Level    | Value | Description                                                                           |
| -------- | ----- | ------------------------------------------------------------------------------------- |
| DEBUG    | 10    | Detailed information, typically of interest only when diagnosing problems             |
| INFO     | 20    | Confirmation that things are working as expected                                      |
| WARNING  | 30    | An indication that something unexpected happened, or may happen in the near future    |
| ERROR    | 40    | Due to a more serious problem, the software has not been able to perform a function   |
| CRITICAL | 50    | A serious error, indicating that the program itself may be unable to continue running |

## Using the Logger

### Accessing the Logger

The logger is a singleton that can be accessed from anywhere in the application:

```python
from pyprocessor.utils.log_manager import get_logger

# Get the logger
logger = get_logger()

# Configure the logger (optional)
logger = get_logger(
    log_dir="/custom/log/path",
    max_logs=20,
    max_size_mb=20,
    max_days=60,
    level="DEBUG",
    app_name="custom_app",
    compress_logs=True,
    encrypt_sensitive=False,
    log_metrics=True
)

# For backward compatibility
from pyprocessor.utils.log_manager import Logger

# Initialize logger
logger = Logger()

# Pass to components
file_manager = FileManager(config, logger)
encoder = FFmpegEncoder(config, logger)
scheduler = ProcessingScheduler(config, logger, file_manager, encoder)
```

### Logging Messages

To log messages at different levels:

```python
# Debug information
logger.debug("Starting to process file: example.mp4")

# General information
logger.info("Successfully processed 5 files")

# Warning
logger.warning("File has unusual format, processing may take longer")

# Error
logger.error(f"Failed to process file: {str(e)}")

# Critical error
logger.critical("Application cannot continue due to critical error")
```

### Structured Logging

The logger supports structured logging with additional context:

```python
# Log with structured data
logger.info("Processing file", file_name="example.mp4", file_size=1024, duration=120)

# Log with exception information
try:
    process_file("example.mp4")
except Exception as e:
    logger.error("Failed to process file", file_name="example.mp4", exception=e)
```

### Context Information

You can set context information that will be included in all subsequent log messages from the same thread:

```python
# Set context information
logger.set_context(user_id="user123", session_id="abc123")

# Log messages (context will be included automatically)
logger.info("User logged in")
logger.info("User performed action")

# Clear context when done
logger.clear_context()
```

### Correlation IDs

Correlation IDs are useful for tracking related events across different components or services:

```python
from pyprocessor.utils.log_manager import get_logger, set_correlation_id, get_correlation_id

# Set a correlation ID (generates a UUID if none provided)
correlation_id = set_correlation_id()
# or
correlation_id = set_correlation_id("abc-123-xyz")

# Get the current correlation ID
current_id = get_correlation_id()

# The correlation ID is automatically included in all log messages
logger.info("Processing request")
```

### Logging Decorator

The logging system provides a decorator for automatic function logging:

```python
from pyprocessor.utils.log_manager import with_logging

# Basic usage
@with_logging
def process_file(file_path):
    # Function code here
    pass

# Advanced usage
@with_logging(level=logging.INFO, log_args=True, log_result=True)
def calculate_result(a, b):
    return a + b
```

The decorator will automatically log:

- Function entry and exit
- Function arguments (if `log_args=True`)
- Function result (if `log_result=True`)
- Any exceptions that occur

### Best Practices for Logging

1. **Choose the Appropriate Level**:
   - Use DEBUG for detailed diagnostic information
   - Use INFO for general operational information
   - Use WARNING for unexpected but non-critical issues
   - Use ERROR for failures that prevent an operation from completing
   - Use CRITICAL for application-breaking errors

2. **Include Contextual Information**:
   - Log file names, user actions, and other relevant context
   - For errors, include exception details

3. **Be Concise but Complete**:
   - Log messages should be clear and to the point
   - Include all necessary information for understanding the event

4. **Avoid Sensitive Information**:
   - Never log passwords, API keys, or personal data
   - Be cautious with file paths that might contain username information
   - Use the `encrypt_sensitive` option to automatically redact sensitive data

5. **Use Correlation IDs**:
   - Set correlation IDs for tracking related events
   - Include correlation IDs in logs across different components

6. **Collect Metrics**:
   - Include performance metrics in logs
   - Use the metrics analysis tools to track performance trends

7. **Use Structured Logging**:
   - Include relevant context as structured data
   - Use consistent field names across the application

8. **Enable Log Compression**:
   - Enable log compression for long-term storage
   - Use the built-in tools to analyze compressed logs

9. **Analyze Logs Regularly**:
   - Use the analysis tools to identify patterns and trends
   - Monitor error rates and performance metrics

## Log Rotation and Compression

The logging system automatically rotates log files based on:

- **Count**: Maximum number of log files to keep (default: 10)
- **Size**: Maximum size of log files in MB (default: 10MB)
- **Age**: Maximum age of log files in days (default: 30 days)

Additionally, the system can automatically compress older log files to save disk space:

```python
# Enable log compression
logger = get_logger(compress_logs=True)
```

Compressed log files have a `.gz` extension and can still be analyzed using the log filtering and searching tools.

## Viewing Logs

Logs can be viewed in several ways:

1. **Through the GUI**:
   - Use the "View Logs" option in the application menu
   - The Log Viewer dialog allows filtering and refreshing logs

2. **Directly from Files**:
   - Open log files in any text editor
   - Log files are plain text and can be analyzed with standard text tools

3. **Programmatically**:
   - Use the `get_log_content()` method of the Logger class
   - This method returns the most recent log entries

## Customizing Logging

The logging system can be customized in several ways:

### Setting the Log Level

```python
# Set the log level when initializing
logger = get_logger(level=logging.DEBUG)
# or
logger = get_logger(level="DEBUG")

# Change the log level later
logger.set_level(logging.INFO)
# or
logger.set_level("INFO")
```

### Changing Log Rotation Settings

```python
# Customize log rotation
logger = get_logger(
    max_logs=20,      # Keep 20 log files
    max_size_mb=20,   # Maximum size of 20MB per file
    max_days=60       # Keep logs for 60 days
)
```

### Accessing Log Content

```python
# Get the last 50 lines of the log
log_content = logger.get_log_content(lines=50)
print(log_content)
```

### Closing the Logger

```python
# Close the logger to release file locks
logger.close()
```

## Troubleshooting

If you encounter issues with logging:

1. **Check Permissions**:
   - Ensure the application has write permissions to the logs directory

2. **Check Disk Space**:
   - Insufficient disk space can prevent log creation

3. **Check for Log Corruption**:
   - If a log file is corrupted, rename or delete it and restart the application

## Log Analysis

PyProcessor provides built-in tools for advanced log analysis:

### Filtering and Searching

```python
from pyprocessor.utils.log_manager import filter_logs, search_logs
from datetime import datetime, timedelta

# Filter logs by various criteria
filtered_logs = filter_logs(
    level="error",  # Only ERROR and CRITICAL logs
    start_time=datetime.now() - timedelta(days=1),  # Last 24 hours
    pattern="database",  # Contains "database"
    correlation_id="abc-123",  # With specific correlation ID
    limit=100  # Maximum 100 results
)

# Search logs with a query
search_results = search_logs(
    query="connection failed",
    case_sensitive=False,
    whole_word=False,
    regex=False,
    limit=50
)
```

### Aggregation

```python
from pyprocessor.utils.log_manager import aggregate_logs

# Aggregate logs by level
level_counts = aggregate_logs(
    group_by="level",
    time_window="1d",  # Last 24 hours
    count_only=True
)
print(f"Error count: {level_counts.get('ERROR', 0)}")

# Aggregate logs by module
module_logs = aggregate_logs(
    group_by="module",
    time_window="6h"  # Last 6 hours
)
for module, data in module_logs.items():
    print(f"{module}: {data['count']} logs")
```

### Analysis

```python
from pyprocessor.utils.log_manager import analyze_logs

# Analyze error distribution
error_analysis = analyze_logs(
    analysis_type="error_distribution",
    time_window="1d"  # Last 24 hours
)
print(f"Total errors: {error_analysis['total_errors']}")

# Analyze log volume
volume_analysis = analyze_logs(
    analysis_type="log_volume",
    time_window="1d"  # Last 24 hours
)
print(f"Total logs: {volume_analysis['total_logs']}")

# Analyze performance
perf_analysis = analyze_logs(analysis_type="performance")
for op, stats in perf_analysis['operation_stats'].items():
    print(f"{op}: avg={stats['avg']:.2f}ms, max={stats['max']:.2f}ms")
```

### Metrics

```python
from pyprocessor.utils.log_manager import get_metrics, reset_metrics

# Get log metrics
metrics = get_metrics()
print(f"Uptime: {metrics['uptime']['formatted']}")
print(f"Total logs: {metrics['total_logs']}")
print(f"Logs per second: {metrics['logs_per_second']}")

# Reset metrics
previous_metrics = reset_metrics()
```

### External Tools

You can also use external tools for log analysis:

1. **Filtering**:
   - Use grep or similar tools to filter logs by level or content
   - Example: `grep "\[ERROR\]" logs/vp_*.log`

2. **Aggregation**:
   - Combine logs from multiple runs for comprehensive analysis
   - Example: `cat logs/vp_*.log > combined_logs.txt`

3. **Visualization**:
   - Consider using log visualization tools for complex analysis
   - Tools like Kibana or Grafana can be used with exported logs

## Complete Example

Here's a complete example of using the logging system:

```python
from pyprocessor.utils.log_manager import get_logger, with_logging
import logging

# Get the logger
logger = get_logger(level="DEBUG")

# Set context for the current thread
logger.set_context(user_id="user123", session_id="abc123")

# Log with structured data
logger.info("Starting application", version="1.0.0", environment="production")

# Use the logging decorator
@with_logging(level=logging.INFO, log_args=True, log_result=True)
def process_file(file_path, options=None):
    logger.debug(f"Processing file with options", options=options)

    try:
        # Process the file
        result = {"status": "success", "file_path": file_path}
        logger.info("File processed successfully", file_path=file_path)
        return result
    except Exception as e:
        logger.error("Failed to process file", file_path=file_path, exception=e)
        raise

# Call the function
try:
    result = process_file("example.mp4", options={"quality": "high"})
    logger.info("Process completed", result=result)
except Exception as e:
    logger.critical("Process failed", exception=e)

# Clear context when done
logger.clear_context()

# Close the logger when the application is shutting down
logger.close()
```
