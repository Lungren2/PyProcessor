# Video Processor Architecture

This document provides a detailed overview of the Video Processor application architecture, explaining the key components and their interactions.

## Overview

The Video Processor application follows a modular architecture with clear separation of concerns. The application is divided into several key components:

1. **GUI Module**: User interface components
2. **Processing Module**: Core video processing logic
3. **Utils Module**: Configuration and logging utilities

## Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Main Application                       │
└───────────────────────────┬─────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
┌───────────▼───────┐ ┌─────▼──────┐ ┌──────▼─────┐
│     GUI Module    │ │ Processing │ │    Utils   │
│                   │ │   Module   │ │   Module   │
└───────────┬───────┘ └─────┬──────┘ └──────┬─────┘
            │               │               │
  ┌─────────┴───────┐ ┌─────┴──────┐ ┌──────┴─────┐
  │  Main Window    │ │  Encoder   │ │   Config   │
  │  Config Dialog  │ │FileManager │ │   Logger   │
  │  Progress Widget│ │ Scheduler  │ │            │
  │  Log Viewer     │ │            │ │            │
  └─────────────────┘ └────────────┘ └────────────┘
```

## Key Components

### 1. GUI Module (`video_processor/gui/`)

The GUI module provides the graphical user interface for the application.

#### Components:

- **Main Window** (`main_window.py`): The primary application window that integrates all GUI components and provides the main user interface.
  
- **Configuration Dialog** (`config_dialog.py`): Dialog for configuring encoding and processing options.
  
- **Progress Widget** (`progress_widget.py`): Widget for displaying processing progress, including file-specific and overall progress.
  
- **Log Viewer** (`log_viewer.py`): Dialog for viewing application logs with filtering and refresh options.

#### Responsibilities:

- Provide user interface for configuring and controlling the application
- Display processing progress and status
- Allow viewing of logs and configuration settings
- Handle user interactions and trigger appropriate actions

### 2. Processing Module (`video_processor/processing/`)

The processing module contains the core logic for video processing.

#### Components:

- **Encoder** (`encoder.py`): Wrapper for FFmpeg that handles video encoding operations.
  
- **File Manager** (`file_manager.py`): Manages file operations, including renaming, validation, and organization.
  
- **Scheduler** (`scheduler.py`): Orchestrates parallel processing of video files.

#### Responsibilities:

- Execute FFmpeg commands for video encoding
- Manage file operations and organization
- Schedule and coordinate parallel processing tasks
- Track processing progress and handle errors

### 3. Utils Module (`video_processor/utils/`)

The utils module provides utility functions and services used throughout the application.

#### Components:

- **Config** (`config.py`): Manages application configuration, including loading, saving, and validating settings.
  
- **Logger** (`logging.py`): Provides logging functionality with different levels and output options.

#### Responsibilities:

- Manage application configuration
- Provide logging services
- Handle utility functions used across the application

## Data Flow

1. **Configuration Flow**:
   - User configures settings via GUI or command line
   - Configuration is validated and saved
   - Components access configuration as needed

2. **Processing Flow**:
   - User initiates processing
   - Scheduler identifies files to process
   - File Manager handles file operations
   - Encoder processes files in parallel
   - Progress is reported back to GUI or CLI
   - Results are logged

3. **Logging Flow**:
   - Components log events and errors
   - Logs are written to files
   - Log Viewer displays logs to user

## Threading Model

The application uses a combination of threading approaches:

- **GUI Thread**: Handles user interface operations
- **Processing Thread**: Manages the overall processing workflow
- **Process Pool**: Executes encoding tasks in parallel

This separation ensures the GUI remains responsive during processing operations.

## Configuration Management

Configuration is managed through a hierarchical approach:

1. **Default Configuration**: Built-in defaults
2. **User Configuration**: Saved in JSON format
3. **Profiles**: Named configurations for different scenarios
4. **Command-line Overrides**: Options specified via command line

## Error Handling

The application implements comprehensive error handling:

- **Component-level Error Handling**: Each component handles its specific errors
- **Centralized Logging**: All errors are logged with appropriate context
- **User Feedback**: Errors are reported to the user through the GUI or CLI
- **Graceful Degradation**: The application attempts to continue operation when possible

## Extension Points

The architecture is designed to be extensible in several ways:

1. **Additional Encoders**: Support for new encoding options can be added to the Encoder class
2. **New File Operations**: The File Manager can be extended with new file handling capabilities
3. **UI Customization**: The GUI components can be modified or extended
4. **Configuration Options**: New configuration options can be added to the Config class

## Future Considerations

Areas for potential architectural enhancement:

1. **Plugin System**: A formal plugin architecture for extending functionality
2. **Remote Processing**: Support for distributing processing across multiple machines
3. **Advanced Queue Management**: More sophisticated job queuing and prioritization
4. **Web Interface**: Alternative web-based user interface
