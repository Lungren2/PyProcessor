# Logging System

This document provides a detailed overview of the Video Processor logging system, explaining how it works and how to use it effectively.

## Overview

The Video Processor application uses a comprehensive logging system that provides detailed information about application operations. Logs are essential for:

- Debugging issues
- Monitoring application performance
- Tracking processing operations
- Auditing application usage

## Log Location

Logs are stored in the `pyprocessor/logs/` directory. Each log file is named with a descriptive pattern that includes:

- Date and time
- Log level
- Username
- System information

Example log filename:
```
vp_2023-04-09_14-30-25_INFO_username_windows.log
```

## Log Format

Log entries follow a consistent format:

```
[YYYY-MM-DD HH:MM:SS][LEVEL] Message
```

Example:
```
[2023-04-09 14:30:25][INFO] Starting video processing
[2023-04-09 14:30:26][DEBUG] Found 5 valid files to process
[2023-04-09 14:30:30][WARNING] File example.mp4 has an unusual format
[2023-04-09 14:31:15][ERROR] Failed to process file: permission denied
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

The logger is initialized in the main application and passed to components that need it:

```python
from pyprocessor.utils.logging import Logger

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
logger.critical("Unable to access output directory, application cannot continue")
```

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

## Log Rotation

The logging system implements automatic log rotation to prevent logs from consuming too much disk space:

- By default, the system keeps the 10 most recent log files
- Older log files are automatically deleted
- The maximum number of logs can be configured when initializing the Logger

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
logger = Logger(level=logging.DEBUG)

# Change the log level later
logger.set_level(logging.INFO)
```

### Changing the Maximum Number of Logs

```python
# Keep 20 log files instead of the default 10
logger = Logger(max_logs=20)
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

For advanced log analysis:

1. **Filtering**:
   - Use grep or similar tools to filter logs by level or content
   - Example: `grep "\[ERROR\]" logs/vp_*.log`

2. **Aggregation**:
   - Combine logs from multiple runs for comprehensive analysis
   - Example: `cat logs/vp_*.log > combined_logs.txt`

3. **Visualization**:
   - Consider using log visualization tools for complex analysis
   - Tools like Kibana or Grafana can be used with exported logs
