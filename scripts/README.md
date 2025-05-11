# PyProcessor Scripts

This directory contains utility scripts for development, building, and packaging PyProcessor.

## Available Scripts

### Development Tools

- **dev_tools.py**: Unified development tools for PyProcessor

  ```bash
  # Set up the development environment
  python scripts/dev_tools.py setup [--no-venv] [--no-ffmpeg] [--no-hooks] [--platform PLATFORM]

  # Clean up temporary files and build artifacts
  python scripts/dev_tools.py clean [--all] [--ffmpeg] [--logs]

  # Run linting tools
  python scripts/dev_tools.py lint [--check]

  # Manage dependencies
  python scripts/dev_tools.py deps [--check] [--install] [--update] [--extras EXTRAS]
  ```

### Building and Packaging Tools

- **build_tools.py**: Unified build tools for PyProcessor

  ```bash
  # Download and extract FFmpeg binaries
  python scripts/build_tools.py ffmpeg

  # Build the PyProcessor executable
  python scripts/build_tools.py build [--skip-ffmpeg]

  # Package the PyProcessor executable for distribution
  python scripts/build_tools.py package [--skip-build] [--platform PLATFORM]
  ```

### Dependency Management

- **manage_dependencies.py**: Advanced dependency management tools

  ```bash
  # Check and manage project dependencies
  python scripts/manage_dependencies.py [options]
  ```

## Script Details

### dev_tools.py

This script provides a comprehensive set of development tools for PyProcessor:

#### Setup Command

Sets up the development environment for PyProcessor:

1. Creates a virtual environment
2. Installs development dependencies
3. Downloads FFmpeg binaries
4. Sets up pre-commit hooks
5. Creates necessary directories

Options:

- `--no-venv`: Skip virtual environment creation
- `--no-ffmpeg`: Skip FFmpeg download
- `--no-hooks`: Skip pre-commit hooks setup
- `--platform`: Target platform for dependencies (windows, macos, linux, all)

#### Clean Command

Cleans up temporary files and build artifacts:

1. Removes `__pycache__` directories and .pyc files
2. Removes build artifacts (build/, dist/, *.egg-info/)
3. Removes FFmpeg temporary files (optional)
4. Cleans up log files (optional)

Options:

- `--all`: Remove all temporary files and build artifacts
- `--ffmpeg`: Remove FFmpeg temporary files
- `--logs`: Clean up log files

#### Lint Command

Runs linting tools on the codebase:

1. Runs black code formatter
2. Runs isort to sort imports
3. Runs flake8 linter
4. Removes unused imports
5. Comments unused variables

Options:

- `--check`: Check code style without making changes

#### Deps Command

Manages dependencies:

1. Checks for missing dependencies
2. Installs missing dependencies
3. Updates dependencies to the latest versions

Options:

- `--check`: Check for missing dependencies
- `--install`: Install missing dependencies
- `--update`: Update dependencies to the latest versions
- `--extras`: Install extra dependencies (dev, ffmpeg, all)

### build_tools.py

This script provides a comprehensive set of build tools for PyProcessor:

#### FFmpeg Command

Downloads and extracts FFmpeg binaries for packaging PyProcessor.

#### Build Command

Builds the PyProcessor executable:

1. Checks for PyInstaller
2. Downloads FFmpeg binaries (if not skipped)
3. Creates a PyInstaller spec file
4. Builds the executable using PyInstaller

Options:

- `--skip-ffmpeg`: Skip downloading FFmpeg (use if already downloaded)

#### Package Command

Packages the PyProcessor executable for distribution:

1. Builds the executable (if not skipped)
2. Creates platform-specific packages:
   - Windows: NSIS installer
   - macOS: DMG file
   - Linux: DEB and RPM packages

Options:

- `--skip-build`: Skip building the executable (use existing build)
- `--platform`: Target platform for packaging (windows, macos, linux, all)

### manage_dependencies.py

This script provides advanced dependency management for PyProcessor:

1. Analyzes project dependencies
2. Checks for outdated packages
3. Manages virtual environments
4. Handles platform-specific dependencies

This script complements the basic dependency management provided by `dev_tools.py` with more advanced features for complex dependency scenarios.
