# [PyProcessor](https://pyprocessor.netlify.app/) &middot; [![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/Lungren2/PyProcessor/blob/main/LICENSE) [![(Runtime) Build and Test](https://github.com/Lungren2/PyProcessor/actions/workflows/build.yml/badge.svg)](https://github.com/Lungren2/PyProcessor/actions/workflows/build.yml) [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/Lungren2/PyProcessor/blob/main/docs/developer/CONTRIBUTING.md)

A cross-platform Python application for media processing and HLS encoding based on FFmpeg. PyProcessor supports processing video files with various encoding options, utilizing parallel processing for improved performance, and works seamlessly on Windows, macOS, and Linux.

## Overview

PyProcessor is designed to be a powerful yet flexible media processing engine that can handle everything from simple video encoding to complex adaptive streaming package creation. It features intelligent resource management, batch processing capabilities, and a plugin system for extensibility.

The application is built with a focus on:

- **Performance**: Optimized for speed with parallel processing and GPU acceleration
- **Flexibility**: Configurable for various use cases through profiles and command-line options
- **Extensibility**: Plugin system allows adding custom functionality
- **Security**: Content encryption for protecting sensitive media files
- **Cross-Platform**: Works consistently across Windows, macOS, and Linux

## Features

### Core Features

- **Cross-Platform Compatibility**: Works on Windows, macOS, and Linux
- **Command-line Interface**: For automation and scripting
- **Fast Parallel Processing**: Process multiple video files simultaneously
- **Multiple Encoder Support**: libx265, h264_nvenc, libx264, and more
- **HLS Packaging**: Create adaptive streaming packages with multiple quality levels
- **Automatic Organization**: File renaming and folder organization
- **Configuration Profiles**: Save and reuse encoding settings
- **Detailed Logging**: Comprehensive logging system

### Advanced Features

- **Intelligent Batch Processing**: Dynamically adjusts batch sizes based on system resources
- **Resource Monitoring**: Monitors CPU, memory, and GPU usage during processing
- **Plugin System**: Extend functionality through custom plugins
- **Server Optimization**: Tools for IIS (Windows), Nginx (Linux/macOS), and Apache
- **HTTP/3 Support**: Modern protocol support with Alt-Svc headers for auto-upgrading
- **Content Encryption**: AES-256 encryption for protecting sensitive media files

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

### Basic Usage

To use the application:

```bash
pyprocessor [options]
```

or

```bash
python -m pyprocessor [options]
```

### Quick Start Examples

#### Basic Video Processing

```bash
# Process all videos in input directory with default settings
pyprocessor --input /path/to/videos --output /path/to/output

# Use a specific encoder and preset
pyprocessor --input /path/to/videos --output /path/to/output --encoder libx265 --preset medium

# Process videos with a saved profile
pyprocessor --input /path/to/videos --output /path/to/output --profile high_quality
```

#### Batch Processing

```bash
# Enable batch processing with automatic batch sizing
pyprocessor --input /path/to/videos --output /path/to/output --batch-mode enabled

# Specify a fixed batch size
pyprocessor --input /path/to/videos --output /path/to/output --batch-mode enabled --batch-size 10

# Limit memory usage for batch processing
pyprocessor --input /path/to/videos --output /path/to/output --batch-mode enabled --max-memory 70
```

#### Server Optimization

```bash
# Optimize IIS server
pyprocessor --optimize-server iis --site-name "My Video Site" --video-path "C:\inetpub\wwwroot\videos" --enable-http3

# Generate Nginx configuration
pyprocessor --optimize-server nginx --server-name example.com --output-config /etc/nginx/sites-available/videos.conf

# Apply Linux system optimizations
pyprocessor --optimize-server linux --apply-changes
```

#### Content Encryption

```bash
# Enable encryption for output files
pyprocessor --input /path/to/videos --output /path/to/output --enable-encryption --encrypt-output

# Use a specific encryption key
pyprocessor --input /path/to/videos --output /path/to/output --enable-encryption --encrypt-output --encryption-key KEY_ID
```

### Available Command-Line Options

#### Core Options

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
```

#### Batch Processing Options

```text
--batch-mode         Enable or disable batch processing mode (enabled, disabled)
--batch-size         Number of videos to process in a single batch
--max-memory         Maximum memory usage percentage before throttling batches
```

#### Server Optimization Options

```text
--optimize-server    Server type to optimize (iis, nginx, apache, linux)
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

#### Security Options

```text
--enable-encryption  Enable content encryption
--encrypt-output     Encrypt output files
--encryption-key     Encryption key ID to use
```

## Configuration

PyProcessor uses a flexible, hierarchical configuration system that allows you to customize every aspect of the application's behavior.

### Configuration Hierarchy

The configuration system follows this hierarchy (from lowest to highest precedence):

1. **Default Configuration**: Built-in defaults for all settings
2. **User Configuration**: Saved in JSON format in the user's configuration directory
3. **Profiles**: Named configurations for different scenarios
4. **Environment Variables**: Settings specified via environment variables
5. **Command-line Overrides**: Options specified via command line take precedence over all other settings

### Configuration Profiles

Profiles allow you to save and reuse configurations for different encoding scenarios. They are stored as JSON files in the `pyprocessor/profiles/` directory.

#### Default Profile

The default profile (`default.json`) includes sensible defaults for most settings:

```json
{
  "input_folder": "${MEDIA_ROOT}/input",
  "output_folder": "${MEDIA_ROOT}/output",
  "ffmpeg_params": {
    "video_encoder": "libx265",
    "preset": "ultrafast",
    "tune": "zerolatency",
    "fps": 60,
    "include_audio": true,
    "bitrates": {
      "1080p": "11000k",
      "720p": "6500k",
      "480p": "4000k",
      "360p": "1500k"
    },
    "audio_bitrates": ["192k", "128k", "96k", "64k"]
  },
  "max_parallel_jobs": 4,
  "batch_processing": {
    "enabled": true,
    "batch_size": null,
    "max_memory_percent": 80
  },
  "auto_rename_files": true,
  "auto_organize_folders": true
}
```

#### Creating Custom Profiles

To create a custom profile:

1. Create a new JSON file in the `pyprocessor/profiles/` directory (e.g., `high_quality.json`)
2. Add your custom settings (you only need to specify settings that differ from the defaults)
3. Use the profile with the `--profile` command-line option

### Configuration Categories

#### Core Settings

- **Input/Output Folders**: Directories for source and processed files
- **FFmpeg Parameters**:
  - Video encoder (libx265, h264_nvenc, libx264)
  - Encoding preset (ultrafast, veryfast, medium, etc.)
  - Tune options (zerolatency, film, animation)
  - FPS setting
  - Audio inclusion/exclusion
  - Bitrates for different resolutions (1080p, 720p, 480p, 360p)
  - Audio bitrates

#### Processing Options

- **Parallel Processing**: Maximum number of parallel jobs
- **Batch Processing**: Batch size and memory usage limits
- **File Organization**: Auto-rename files and auto-organize folders
- **Pattern Matching**: Regular expressions for file validation, renaming, and organization

#### Advanced Configuration Options

- **Server Optimization**:
  - Server type (IIS, Nginx, Apache, Linux)
  - HTTP/3 support with Alt-Svc headers for auto-upgrading
  - Server-specific configuration options
  - Network and performance optimizations
- **Security**:
  - Content encryption with AES-256
  - Key management and rotation
  - Password-based encryption

### File Processing Patterns

PyProcessor uses regular expression patterns to handle file naming and organization. These patterns are controlled by configuration flags:

- `auto_rename_files`: When enabled, input files are renamed according to the `file_rename_pattern`
- `auto_organize_folders`: When enabled, output folders are organized according to the `folder_organization_pattern`
- `file_validation_pattern`: Files that don't match this pattern are considered invalid and will be skipped

### Environment Variables

You can use environment variables in configuration files and on the command line. For example:

- `${MEDIA_ROOT}`: Root directory for media files
- `${PYPROCESSOR_DATA_DIR}`: PyProcessor data directory

For detailed information about configuration options and flag-pattern relationships, see the [Configuration Documentation](docs/developer/CONFIGURATION.md) and [Regex Patterns Documentation](docs/regex_patterns.md).

## Logging

The application maintains detailed logs in the `pyprocessor/logs/` directory. Log files include timestamps, log levels, and detailed information about the processing operations.

## Documentation

PyProcessor includes comprehensive documentation for both users and developers.

### User Documentation

- [User Guide](docs/user/USER_GUIDE.md) - Comprehensive guide for using PyProcessor
- [Batch Processing](docs/user/BATCH_PROCESSING.md) - How to use the batch processing system
- [Server Optimization](docs/user/SERVER_OPTIMIZATION.md) - How to optimize servers for video streaming
- [Content Encryption](docs/user/CONTENT_ENCRYPTION.md) - How to use content encryption features

### Developer Documentation

- [Contributing Guide](docs/developer/CONTRIBUTING.md) - How to contribute to the project
- [Architecture Overview](docs/developer/ARCHITECTURE.md) - Detailed explanation of the project architecture
- [Code Style Guide](docs/developer/CODE_STYLE.md) - Coding standards and style guidelines
- [Development Workflow](docs/developer/DEVELOPMENT_WORKFLOW.md) - Recommended development process
- [Plugin System](docs/developer/PLUGIN_SYSTEM.md) - How to create and use plugins
- [Logging System](docs/developer/LOGGING.md) - Details about the logging system
- [FFmpeg Integration](docs/developer/FFMPEG_INTEGRATION.md) - How the application integrates with FFmpeg
- [Packaging](docs/developer/PACKAGING.md) - How to package the application into an executable
- [NSIS Packaging](docs/developer/NSIS_PACKAGING.md) - Creating an installer with NSIS
- [Dependencies](docs/developer/DEPENDENCIES.md) - Managing dependencies across platforms
- [Path Handling](docs/developer/PATH_HANDLING.md) - How paths and environment variables are handled
- [Application Context](docs/developer/APPLICATION_CONTEXT.md) - How application state and lifecycle are managed

### API Documentation

- [API Reference](docs/api/API_REFERENCE.md) - Reference for the PyProcessor API

### Security Documentation

- [Content Encryption](docs/security/CONTENT_ENCRYPTION.md) - Technical details of content encryption
- [Security Best Practices](docs/security/SECURITY_BEST_PRACTICES.md) - Security recommendations

## Development

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
- ✅ Implement AES-256 content encryption for protecting sensitive media files

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
