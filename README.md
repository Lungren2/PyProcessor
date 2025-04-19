# PyProcessor

A cross-platform Python application for media processing and HLS encoding based on FFmpeg. This tool supports processing video files with various encoding options, utilizing parallel processing for improved performance, and works seamlessly on Windows, macOS, and Linux.

## Features

- **Cross-Platform Compatibility**: Works on Windows, macOS, and Linux
- **Command-line Interface**: For automation and scripting
- **Fast Parallel Processing**: Process multiple video files simultaneously
- **Multiple Encoder Support**: libx265, h264_nvenc, libx264, and more
- **HLS Packaging**: Create adaptive streaming packages with multiple quality levels
- **Automatic Organization**: File renaming and folder organization
- **Configuration Profiles**: Save and reuse encoding settings
- **Detailed Logging**: Comprehensive logging system
- **Server Optimization**: Tools for IIS (Windows), Nginx (Linux/macOS), and other systems
- **HTTP/3 Support**: Modern protocol support with Alt-Svc headers for auto-upgrading

## Requirements

- Python 3.6 or higher
- FFmpeg installed and available in PATH
- Platform-specific dependencies (automatically installed)
  - Windows: pywin32, winshell
  - macOS: pyobjc-core, pyobjc-framework-Cocoa
  - Linux: python-xlib, dbus-python
- Base dependencies (automatically installed)
  - tqdm for progress display

## Installation

### From Source

```bash
git clone https://github.com/Lungren2/PyProcessor.git
cd PyProcessor

# Install with base dependencies
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"

# Or install with FFmpeg Python bindings
pip install -e ".[ffmpeg]"

# Or install with all extras
pip install -e ".[dev,ffmpeg]"
```

This will install the package in development mode, making the `pyprocessor` command available in your environment.

### Using the Dependency Management Script

For more control over dependencies, you can use the dependency management script:

```bash
# Check for missing dependencies
python scripts/manage_dependencies.py --check

# Install dependencies for your platform
python scripts/manage_dependencies.py --install

# Install dependencies with extras
python scripts/manage_dependencies.py --install --extras dev

# Update dependencies
python scripts/manage_dependencies.py --update
```

### Standalone Packages

Standalone packages are available for all supported platforms. To build the package for your platform:

```bash
python scripts/build.py
```

This will create an executable in the `dist` directory. To create an installer package:

```bash
python scripts/package.py
```

This will create platform-specific packages in the `packages` directory:

- Windows: NSIS installer (.exe)
- macOS: Application bundle (.app) and disk image (.dmg)
- Linux: Debian package (.deb) and RPM package (.rpm)

See [Packaging](docs/PACKAGING.md) for more details.

## Project Architecture

The project is organized into the following structure:

```text
PyProcessor/
├── docs/                      # Documentation
│   ├── user/                  # User documentation
│   ├── developer/             # Developer documentation
│   └── api/                   # API documentation
├── scripts/                   # Utility scripts
│   ├── build.py               # Cross-platform build script
│   ├── package.py             # Cross-platform packaging script
│   ├── setup.py               # Cross-platform setup script
│   ├── install.py             # Cross-platform installation script
│   ├── cleanup.py             # Cleanup script
│   └── download_ffmpeg.py     # Cross-platform FFmpeg downloader
├── pyprocessor/           # Main package
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
├── MANIFEST.in                # Package manifest
├── requirements.txt           # Dependencies
├── setup.py                   # Package setup
└── run_pyprocessor.py         # Cross-platform launcher script
```

## Usage

To use the application:

```bash
pyprocessor [options]
```

or

```bash
python -m pyprocessor [options]
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

Configuration files are stored as JSON in the `pyprocessor/profiles/` directory. You can create multiple profiles for different encoding scenarios. The configuration includes flags that control file processing behavior:

- `auto_rename_files`: When enabled, input files are renamed according to the `file_rename_pattern`
- `auto_organize_folders`: When enabled, output folders are organized according to the `folder_organization_pattern`

For detailed information about configuration options and flag-pattern relationships, see the [Configuration Documentation](docs/developer/CONFIGURATION.md) and [Regex Patterns Documentation](docs/regex_patterns.md).

## Logging

The application maintains detailed logs in the `pyprocessor/logs/` directory. Log files include timestamps, log levels, and detailed information about the processing operations.

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
- [Dependencies](docs/developer/DEPENDENCIES.md) - Managing dependencies across platforms
- [API Reference](docs/api/API_REFERENCE.md) - Reference for the PyProcessor API
- [Path Handling](docs/developer/PATH_HANDLING.md) - How paths and environment variables are handled
- [Application Context](docs/developer/APPLICATION_CONTEXT.md) - How application state and lifecycle are managed

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

#### Using Cross-Platform Scripts

On any platform (Windows, macOS, Linux):

```bash
python scripts/setup.py       # Set up development environment
python scripts/cleanup.py     # Clean up temporary files
python scripts/build.py       # Build executable
python run_pyprocessor.py     # Run the application
```

#### Using the Makefile (Linux/macOS)

```bash
make setup  # Set up development environment
make clean  # Clean up temporary files
make build  # Build executable
make run    # Run the application
```

## TODO

The project has several ongoing development tasks organized by category. Each task has its own detailed markdown file in the `docs/todo/` directory.

When a task is completed, simply remove its corresponding file from the `docs/todo/` directory.

### Recently Completed

- ✅ Implement intelligent batch processing with dynamic sizing based on system resources
- ✅ Create a resource monitoring and allocation system for optimal hardware utilization

### In Progress

See the individual task files in the [docs/todo](docs/todo/) directory for detailed information on each task.

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: If you encounter `ModuleNotFoundError: No module named 'pyprocessor'`, make sure you've installed the package with `pip install -e .`

2. **FFmpeg Not Found**: Ensure FFmpeg is installed and available in your system PATH

3. **Permission Errors**: Make sure the application has write permissions for the output directory

4. **Path Issues**: If you encounter path-related issues, check the [Path Handling](docs/developer/PATH_HANDLING.md) documentation for information on using environment variables and platform-agnostic paths

### Viewing Logs

You can view logs by examining the log files in the `pyprocessor/logs/` directory.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
