# PyProcessor Architecture

This document provides a detailed overview of the PyProcessor architecture, explaining the key components and their interactions.

## Overview

PyProcessor follows a modular architecture with clear separation of concerns. The library is divided into several key components:

1. **Processing Module**: Core video processing logic
2. **Utils Module**: Configuration, logging, and utility functions

## Component Diagram

```ascii
┌─────────────────────────────────────────────────────────────┐
│                      Main Application                       │
└───────────────────────────┬─────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
┌───────────▼───────┐ ┌─────▼──────┐ ┌──────▼─────┐
│      CLI Module   │ │ Processing │ │    Utils   │
│                   │ │   Module   │ │   Module   │
└───────────────────┘ └─────┬──────┘ └──────┬─────┘
                            │               │
                      ┌─────┴──────┐ ┌──────┴─────┐
                      │  Encoder   │ │   Config   │
                      │FileManager │ │   Logger   │
                      │ Scheduler  │ │            │
                      │            │ │            │
                      └────────────┘ └────────────┘
```

## Key Components

### 1. CLI Module (`pyprocessor/cli/`)

The CLI module provides the command-line interface for the application.

#### Components

- **Command Parser**: Parses command-line arguments and options
- **Progress Reporter**: Reports processing progress to the console
- **Interactive Mode**: Provides an interactive command-line interface

#### Responsibilities

- Parse command-line arguments
- Display processing progress and status
- Provide interactive command-line interface
- Handle user interactions and trigger appropriate actions

### 2. Processing Module (`pyprocessor/processing/`)

The processing module contains the core logic for video processing.

#### Components

- **Encoder** (`encoder.py`): Wrapper for FFmpeg that handles video encoding operations.

- **File Manager** (`file_manager.py`): Manages file operations, including renaming, validation, and organization.

- **Scheduler** (`scheduler.py`): Orchestrates parallel processing of video files.

#### Processing Responsibilities

- Execute FFmpeg commands for video encoding
- Manage file operations and organization
- Schedule and coordinate parallel processing tasks
- Track processing progress and handle errors

### 3. Utils Module (`pyprocessor/utils/`)

The utils module provides utility functions and services used throughout the application.

#### Utility Components

- **Config** (`config.py`): Manages application configuration, including loading, saving, and validating settings.

- **Logger** (`logging.py`): Provides logging functionality with different levels and output options.

#### Utility Responsibilities

- Manage application configuration
- Provide logging services
- Handle utility functions used across the application

## Data Flow

1. **Configuration Flow**:
   - User configures settings via command line or configuration files
   - Configuration is validated and saved
   - Components access configuration as needed

2. **Processing Flow**:
   - User initiates processing
   - Scheduler identifies files to process
   - File Manager handles file operations
   - Encoder processes files in parallel
   - Progress is reported back to CLI
   - Results are logged

3. **Logging Flow**:
   - Components log events and errors
   - Logs are written to files
   - Logs can be accessed for review

## Threading Model

The application uses a combination of threading approaches:

- **Main Thread**: Handles command-line interface and overall control
- **Processing Thread**: Manages the overall processing workflow
- **Process Pool**: Executes encoding tasks in parallel

This separation ensures the application remains responsive during processing operations.

## Configuration Management

Configuration is managed through a hierarchical approach:

1. **Default Configuration**: Built-in defaults
2. **User Configuration**: Saved in JSON format
3. **Profiles**: Named configurations for different scenarios
4. **Command-line Overrides**: Options specified via command line

### Flag-Pattern Relationships

The configuration includes several flags that control whether certain patterns are applied during processing:

- **auto_rename_files**: When enabled, the `file_rename_pattern` is used to extract parts of filenames for renaming before processing
- **auto_organize_folders**: When enabled, the `folder_organization_pattern` is used to organize output folders into a hierarchical structure after processing

The `file_validation_pattern` is always used to validate files before processing, regardless of the flag settings.

For detailed information about these relationships, see the [Configuration Documentation](CONFIGURATION.md) and [Regex Patterns Documentation](../regex_patterns.md).

## Error Handling

The application implements comprehensive error handling:

- **Component-level Error Handling**: Each component handles its specific errors
- **Centralized Logging**: All errors are logged with appropriate context
- **User Feedback**: Errors are reported to the user through the CLI
- **Graceful Degradation**: The application attempts to continue operation when possible

## Extension Points

The architecture is designed to be extensible in several ways:

1. **Additional Encoders**: Support for new encoding options can be added to the Encoder class
2. **New File Operations**: The File Manager can be extended with new file handling capabilities
3. **CLI Extensions**: The command-line interface can be extended with new commands
4. **Configuration Options**: New configuration options can be added to the Config class

## Future Considerations

Areas for potential architectural enhancement:

1. **Plugin System**: A formal plugin architecture for extending functionality
2. **Remote Processing**: Support for distributing processing across multiple machines
3. **Advanced Queue Management**: More sophisticated job queuing and prioritization
4. **API Interface**: REST API for remote control and integration
