# PyProcessor Scripts

This directory contains utility scripts for development, building, and packaging PyProcessor.

## Available Scripts

### Development Scripts

- **dev_setup.py**: Sets up the development environment
  ```bash
  python scripts/dev_setup.py [--no-venv] [--no-ffmpeg] [--no-hooks]
  ```

- **run_tests.py**: Runs the test suite
  ```bash
  python scripts/run_tests.py [--unit] [--integration] [--coverage] [--html]
  ```

- **cleanup.py**: Cleans up temporary files and build artifacts
  ```bash
  python scripts/cleanup.py [--all] [--ffmpeg] [--logs]
  ```

### Building and Packaging Scripts

- **download_ffmpeg.py**: Downloads and extracts FFmpeg binaries
  ```bash
  python scripts/download_ffmpeg.py
  ```

- **build_package.py**: Builds and packages PyProcessor
  ```bash
  python scripts/build_package.py [--skip-ffmpeg] [--skip-pyinstaller] [--skip-nsis]
  ```

## Script Details

### dev_setup.py

This script sets up the development environment for PyProcessor:

1. Creates a virtual environment
2. Installs development dependencies
3. Downloads FFmpeg binaries
4. Sets up pre-commit hooks
5. Creates necessary directories

Options:
- `--no-venv`: Skip virtual environment creation
- `--no-ffmpeg`: Skip FFmpeg download
- `--no-hooks`: Skip pre-commit hooks setup

### run_tests.py

This script runs the test suite for PyProcessor:

1. Runs unit tests and/or integration tests
2. Generates coverage reports

Options:
- `--unit`: Run only unit tests
- `--integration`: Run only integration tests
- `--coverage`: Generate coverage report
- `--html`: Generate HTML coverage report

### cleanup.py

This script cleans up temporary files and build artifacts:

1. Removes __pycache__ directories and .pyc files
2. Removes build artifacts (build/, dist/, *.egg-info/)
3. Removes FFmpeg temporary files (optional)
4. Cleans up log files (optional)

Options:
- `--all`: Remove all temporary files and build artifacts
- `--ffmpeg`: Remove FFmpeg temporary files
- `--logs`: Clean up log files

### download_ffmpeg.py

This script downloads and extracts FFmpeg binaries for packaging PyProcessor.

### build_package.py

This script automates the entire build and packaging process for PyProcessor:

1. Checks for required dependencies (PyInstaller, NSIS)
2. Downloads and extracts FFmpeg binaries
3. Creates the PyInstaller executable
4. Packages the executable using NSIS

Options:
- `--skip-ffmpeg`: Skip downloading FFmpeg (use if already downloaded)
- `--skip-pyinstaller`: Skip PyInstaller build (use if already built)
- `--skip-nsis`: Skip NSIS packaging (use if only executable is needed)
