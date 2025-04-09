# Video Processor

A Python application for video processing and HLS encoding based on FFmpeg. This tool provides both a graphical user interface and command-line interface for processing video files with various encoding options, supporting parallel processing for improved performance.

## Features

- Graphical user interface for easy configuration and monitoring
- Command-line interface for automation and scripting
- Fast parallel processing of multiple video files
- Support for multiple encoders (libx265, h264_nvenc, libx264)
- HLS packaging with multiple quality levels
- Automatic file organization and renaming
- Configuration profiles for different encoding scenarios
- Detailed logging system

## Requirements

- Python 3.6 or higher
- FFmpeg installed and available in PATH
- PyQt5 for the graphical interface
- tqdm for progress display in CLI mode

## Installation

### From Source

```bash
git clone https://github.com/Lungren2/PyProcessor.git
cd video_processor
pip install -e .
```

This will install the package in development mode, making the `video_processor` command available in your environment.

## Project Architecture

The project is organized into several modules:

```text
video_processor/
├── main.py                 # Entry point
├── __main__.py             # Package entry point
├── gui/                    # GUI components
│   ├── main_window.py      # Main application window
│   ├── config_dialog.py    # Configuration dialog
│   ├── log_viewer.py       # Log viewing dialog
│   └── progress_widget.py  # Progress visualization
├── processing/             # Core processing logic
│   ├── encoder.py          # FFmpeg wrapper
│   ├── file_manager.py     # File operations
│   └── scheduler.py        # Parallelism management
├── utils/                  # Utility functions
│   ├── config.py           # Configuration handling
│   └── logging.py          # Logging system
├── resources/              # Application resources
│   └── defaults.json       # Default configuration values
└── logs/                   # Log files directory
```

## Usage

### Graphical Interface

To start the application with the graphical interface:

```bash
video_processor
```

or

```bash
python -m video_processor
```

### Command Line Interface

To use the command-line interface:

```bash
video_processor --no-gui [options]
```

Available command-line options:

```text
--input PATH         Input directory path
--output PATH        Output directory path
--config PATH        Configuration file path
--profile NAME       Configuration profile name
--encoder NAME       Video encoder (libx265, h264_nvenc, libx264)
--preset NAME        Encoding preset (ultrafast, veryfast, medium, etc.)
--tune NAME          Encoding tune (zerolatency, film, animation, etc.)
--fps NUMBER         Frames per second
--no-audio           Disable audio in output
--jobs NUMBER        Number of parallel encoding jobs
--no-gui             Run without GUI
--verbose            Enable verbose logging
```

## Configuration

The application uses a configuration system that supports:

1. **Default Configuration**: Built-in defaults for all settings
2. **User Configuration**: Saved in JSON format
3. **Profiles**: Multiple named configurations for different scenarios
4. **Command-line Overrides**: Options specified via command line take precedence

### Configuration Options

- **Input/Output Folders**: Directories for source and processed files
- **FFmpeg Parameters**:
  - Video encoder (libx265, h264_nvenc, libx264)
  - Encoding preset (ultrafast, veryfast, medium, etc.)
  - Tune options (zerolatency, film, animation)
  - FPS setting
  - Audio inclusion/exclusion
  - Bitrates for different resolutions (1080p, 720p, 480p, 360p)
  - Audio bitrates
- **Processing Options**:
  - Maximum parallel jobs
  - Auto-rename files
  - Auto-organize folders

### Configuration Files

Configuration files are stored as JSON in the `output_folder/profiles/` directory. You can create multiple profiles for different encoding scenarios.

## Logging

The application maintains detailed logs in the `video_processor/logs/` directory. Log files include timestamps, log levels, and detailed information about the processing operations.

## Development

For detailed information about development, please refer to the documentation in the `docs/` directory:

- [Contributing Guide](docs/CONTRIBUTING.md) - How to contribute to the project
- [Architecture Overview](docs/ARCHITECTURE.md) - Detailed explanation of the project architecture
- [Code Style Guide](docs/CODE_STYLE.md) - Coding standards and style guidelines
- [Development Workflow](docs/DEVELOPMENT_WORKFLOW.md) - Recommended development process
- [Logging System](docs/LOGGING.md) - Details about the logging system
- [FFmpeg Integration](docs/FFMPEG_INTEGRATION.md) - How the application integrates with FFmpeg

### Running Tests

```bash
python -m unittest discover tests
```

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: If you encounter `ModuleNotFoundError: No module named 'video_processor'`, make sure you've installed the package with `pip install -e .`

2. **FFmpeg Not Found**: Ensure FFmpeg is installed and available in your system PATH

3. **Permission Errors**: Make sure the application has write permissions for the output directory

### Viewing Logs

You can view logs either through the GUI (Tools > View Logs) or by examining the log files in the `video_processor/logs/` directory.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
