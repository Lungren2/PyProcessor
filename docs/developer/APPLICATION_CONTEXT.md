# Application Context

This document describes the ApplicationContext pattern used in PyProcessor to manage application state and lifecycle.

## Overview

The ApplicationContext pattern encapsulates the application's state and lifecycle management in a single class. This approach:

1. Eliminates the need for module-level globals
2. Improves encapsulation of application state
3. Makes signal handling more maintainable
4. Improves testability

## Implementation

The ApplicationContext class is implemented in `pyprocessor/utils/application_context.py`. It manages:

- Configuration (Config)
- Logging (Logger)
- File management (FileManager)
- Encoding (FFmpegEncoder)
- Processing scheduling (ProcessingScheduler)
- Theme management (ThemeManager)
- Signal handling
- Application lifecycle (initialization, running, shutdown)

## Usage

### Initialization

```python
from pyprocessor.utils.application_context import ApplicationContext

# Create application context
app_context = ApplicationContext()

# Initialize with command line arguments
app_context.initialize(args)
```

### Running the Application

```python
# Run in CLI mode
exit_code = app_context.run_cli_mode()

# Or run in GUI mode
exit_code = app_context.run_gui_mode()
```

### Accessing Components

```python
# Access configuration
config = app_context.config

# Access logger
logger = app_context.logger

# Access file manager
file_manager = app_context.file_manager

# Access encoder
encoder = app_context.encoder

# Access scheduler
scheduler = app_context.scheduler
```

### Shutdown

```python
# Perform cleanup operations
app_context.shutdown()
```

## Signal Handling

The ApplicationContext registers signal handlers for SIGINT (Ctrl+C) and SIGTERM (termination signal) to ensure clean shutdown:

```python
def _register_signal_handlers(self):
    """Register signal handlers for clean shutdown."""
    signal.signal(signal.SIGINT, self._signal_handler)
    signal.signal(signal.SIGTERM, self._signal_handler)

def _signal_handler(self, sig, frame):
    """Handle termination signals for clean shutdown."""
    if self.logger:
        self.logger.info("Termination signal received. Shutting down...")

    # Stop any active FFmpeg process
    if self.encoder:
        self.encoder.terminate()

    # Request abort for scheduler
    if self.scheduler and self.scheduler.is_running:
        self.scheduler.request_abort()

    if self.logger:
        self.logger.info("Shutdown complete")

    sys.exit(0)
```

## Benefits

### Improved Encapsulation

The ApplicationContext encapsulates all application state in a single object, making it easier to reason about the application's state and lifecycle.

### Elimination of Global Variables

By encapsulating application state in a class, we eliminate the need for module-level globals, which can lead to tight coupling and side effects.

### Improved Testability

The ApplicationContext pattern makes testing easier by:

1. Providing a single point of control for application state
2. Making it easy to mock or stub components
3. Allowing for isolated testing of components

### Cleaner Shutdown

The ApplicationContext provides a centralized place for handling application shutdown, ensuring that all resources are properly released.

## Example: Main Application Entry Point

```python
def main():
    """Main application entry point"""
    # Parse command line arguments
    args = parse_args()
    
    # Create and initialize application context
    app_context = ApplicationContext()
    if not app_context.initialize(args):
        return 1
    
    # Run in CLI or GUI mode
    if args.no_gui:
        return run_cli_mode(app_context)
    else:
        return app_context.run_gui_mode()
```
