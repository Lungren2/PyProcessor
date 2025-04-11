# PyProcessor

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
- Dark/light theme that follows system settings
- Server optimization for IIS, Nginx, and Linux systems with HTTP/3 support

## Requirements

- Python 3.6 or higher
- FFmpeg installed and available in PATH
- PyQt5 for the graphical interface
- tqdm for progress display in CLI mode

### Optional Dependencies

- darkdetect for system theme detection
- pyqtdarktheme for high-quality dark/light themes

## Installation

### From Source

```bash
git clone https://github.com/Lungren2/PyProcessor.git
cd video_processor
pip install -e .
```

This will install the package in development mode, making the `video_processor` command available in your environment.

### Standalone Installer

A standalone installer is available that includes all dependencies, including FFmpeg. To build the installer:

```bash
python scripts/build_package.py
```

This will create a `PyProcessorInstaller.exe` file that can be distributed to users. See [Packaging](docs/PACKAGING.md) for more details.

## Project Architecture

The project is organized into the following structure:

```text
PyProcessor/
├── docs/                      # Documentation
│   ├── user/                  # User documentation
│   ├── developer/             # Developer documentation
│   └── api/                   # API documentation
├── scripts/                   # Utility scripts
│   ├── build_package.py       # Build script
│   ├── cleanup.py             # Cleanup script
│   ├── dev_setup.py           # Development environment setup
│   ├── download_ffmpeg.py     # FFmpeg downloader
│   └── run_tests.py           # Test runner
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests
│   └── integration/           # Integration tests
├── video_processor/           # Main package
│   ├── gui/                   # GUI components
│   ├── processing/            # Processing logic
│   ├── utils/                 # Utility functions
│   ├── profiles/              # Profile storage
│   └── logs/                  # Log storage
├── optimization-utils/        # Server optimization utilities
├── .github/                   # GitHub workflows and templates
│   └── workflows/             # CI/CD workflows
├── .gitignore                 # Git ignore file
├── LICENSE                    # License file
├── Makefile                   # Makefile for common tasks
├── README.md                  # Main README
├── dev_tools.bat              # Windows development tools
├── requirements.txt           # Dependencies
├── setup.py                   # Package setup
└── run_pyprocessor.bat        # Launcher script
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

# Server Optimization Options
--optimize-server    Server type to optimize (iis, nginx, linux)
--site-name          IIS site name (for IIS optimization)
--video-path         Path to video content directory (for IIS)
--enable-http2       Enable HTTP/2 protocol (for IIS)
--enable-http3       Enable HTTP/3 with Alt-Svc headers (for IIS or Nginx)
--enable-cors        Enable CORS headers (for IIS)
--cors-origin        CORS origin value (for IIS)
--output-config      Output path for server configuration (for Nginx)
--server-name        Server name for configuration (for Nginx)
--apply-changes      Apply changes directly (for Linux)
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
- **Server Optimization**:
  - Server type (IIS, Nginx, Linux)
  - HTTP/3 support with Alt-Svc headers for auto-upgrading
  - Server-specific configuration options
  - Network and performance optimizations

### Configuration Files

Configuration files are stored as JSON in the `video_processor/profiles/` directory. You can create multiple profiles for different encoding scenarios.

## Logging

The application maintains detailed logs in the `video_processor/logs/` directory. Log files include timestamps, log levels, and detailed information about the processing operations.

## Development

For detailed information about development, please refer to the documentation in the `docs/` directory:

- [User Guide](docs/user/USER_GUIDE.md) - Comprehensive guide for using PyProcessor
- [Contributing Guide](docs/developer/CONTRIBUTING.md) - How to contribute to the project
- [Architecture Overview](docs/developer/ARCHITECTURE.md) - Detailed explanation of the project architecture
- [Code Style Guide](docs/developer/CODE_STYLE.md) - Coding standards and style guidelines
- [Development Workflow](docs/developer/DEVELOPMENT_WORKFLOW.md) - Recommended development process
- [Logging System](docs/developer/LOGGING.md) - Details about the logging system
- [FFmpeg Integration](docs/developer/FFMPEG_INTEGRATION.md) - How the application integrates with FFmpeg
- [Packaging](docs/developer/PACKAGING.md) - How to package the application into an executable with bundled FFmpeg
- [NSIS Packaging](docs/developer/NSIS_PACKAGING.md) - Detailed guide for creating an installer with NSIS
- [Server Optimization](docs/developer/SERVER_OPTIMIZATION.md) - Prerequisites and details for server optimization
- [API Reference](docs/api/API_REFERENCE.md) - Reference for the PyProcessor API

### Development Setup

We provide several utility scripts to make development easier:

#### Using the Development Setup Script

```bash
python scripts/dev_setup.py
```

This script will:

1. Create a virtual environment
2. Install development dependencies
3. Download FFmpeg binaries
4. Set up pre-commit hooks
5. Create necessary directories

#### Using the Makefile (Linux/macOS) or Batch File (Windows)

On Linux/macOS:

```bash
make setup  # Set up development environment
make clean  # Clean up temporary files
make test   # Run tests
make build  # Build executable
make run    # Run the application
```

On Windows:

```batch
dev_tools.bat setup   # Set up development environment
dev_tools.bat clean   # Clean up temporary files
dev_tools.bat test    # Run tests
dev_tools.bat build   # Build executable
dev_tools.bat run     # Run the application
```

### Running Tests

```bash
python scripts/run_tests.py --coverage
```

Or for specific test types:

```bash
python scripts/run_tests.py --unit      # Run only unit tests
python scripts/run_tests.py --integration # Run only integration tests
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
