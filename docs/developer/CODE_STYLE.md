# Code Style Guide

This document outlines the coding standards and style guidelines for the Video Processor project. Following these guidelines ensures consistency across the codebase and makes it easier for contributors to understand and modify the code.

## Python Style Guidelines

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with some specific adaptations.

### Formatting

- **Indentation**: Use 4 spaces for indentation (no tabs)
- **Line Length**: Maximum line length of 88 characters (as per Black formatter)
- **Line Breaks**: Use line breaks to enhance readability
- **Blank Lines**:
  - 2 blank lines before top-level classes and functions
  - 1 blank line before methods within a class
  - Use blank lines to separate logical sections within functions

### Naming Conventions

- **Packages and Modules**: Short, lowercase names (e.g., `utils`, `gui`)
- **Classes**: CamelCase (e.g., `FileManager`, `ConfigDialog`)
- **Functions and Methods**: lowercase_with_underscores (e.g., `process_video`, `save_config`)
- **Variables**: lowercase_with_underscores (e.g., `input_folder`, `max_parallel_jobs`)
- **Constants**: UPPERCASE_WITH_UNDERSCORES (e.g., `DEFAULT_BITRATE`, `MAX_THREADS`)

### Imports

- Group imports in the following order:
  1. Standard library imports
  2. Related third-party imports
  3. Local application/library specific imports
- Separate each group with a blank line
- Use absolute imports for clarity

Example:
```python
import os
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QMainWindow
import ffmpeg

from pyprocessor.utils.config import Config
from pyprocessor.processing.encoder import FFmpegEncoder
```

### Comments and Documentation

- Use docstrings for all modules, classes, and functions
- Follow the Google style for docstrings:

```python
def function_name(param1, param2):
    """Short description of the function.

    Longer description explaining the function in detail.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ExceptionType: When and why this exception is raised
    """
    # Function implementation
```

- Use inline comments sparingly and only to explain complex logic
- Keep comments up-to-date with code changes

### Type Hints

- Use type hints for function parameters and return values:

```python
def process_video(file_path: Path, output_dir: Path) -> bool:
    """Process a video file.

    Args:
        file_path: Path to the input video file
        output_dir: Directory to save processed files

    Returns:
        True if processing was successful, False otherwise
    """
    # Function implementation
```

## Code Organization

### File Structure

- Keep files focused on a single responsibility
- Limit file size (aim for under 500 lines)
- Use meaningful file names that reflect the content

### Class Structure

- Follow the single responsibility principle
- Order class methods as follows:
  1. `__init__` and other special methods
  2. Public methods
  3. Protected methods (prefixed with `_`)
  4. Private methods (prefixed with `__`)
  5. Static and class methods

### Function Structure

- Keep functions focused on a single task
- Limit function length (aim for under 50 lines)
- Use helper functions to break down complex logic

## Error Handling

- Use specific exception types rather than catching all exceptions
- Provide meaningful error messages
- Log exceptions with appropriate context
- Handle errors at the appropriate level of abstraction

Example:
```python
try:
    result = self.encoder.encode_video(file, output_folder)
except FFmpegError as e:
    self.logger.error(f"FFmpeg encoding error for {file.name}: {str(e)}")
    return False
except IOError as e:
    self.logger.error(f"I/O error processing {file.name}: {str(e)}")
    return False
except Exception as e:
    self.logger.error(f"Unexpected error processing {file.name}: {str(e)}")
    return False
```

## Logging

- Use the application's logger rather than print statements
- Choose the appropriate log level:
  - `DEBUG`: Detailed information for debugging
  - `INFO`: Confirmation that things are working as expected
  - `WARNING`: Something unexpected happened, but the application can continue
  - `ERROR`: A more serious problem that prevented an operation from completing
  - `CRITICAL`: A serious error that might prevent the application from continuing

Example:
```python
self.logger.debug(f"Starting to process file: {file.name}")
self.logger.info(f"Successfully processed {file.name}")
self.logger.warning(f"File {file.name} has an unusual format")
self.logger.error(f"Failed to process {file.name}: {str(e)}")
```

## Tools

We use the following tools to enforce code style:

- **Black**: For code formatting
- **Flake8**: For linting
- **isort**: For import sorting
- **mypy**: For type checking
- **autoflake**: For removing unused imports
- **vulture**: For detecting unused variables

Run these tools before submitting changes:

```bash
black pyprocessor
flake8 pyprocessor
isort pyprocessor
mypy pyprocessor
python scripts/clean_code.py
```

Alternatively, you can use the Makefile targets:

```bash
make format    # Run Black formatter
make lint      # Run Flake8 linter
make clean-code # Remove unused imports and comment unused variables
```

## Pre-commit Hooks

Consider setting up pre-commit hooks to automatically check code style before committing:

```bash
pip install pre-commit
pre-commit install
```

Our pre-commit configuration runs Black, Flake8, isort, and autoflake automatically to ensure code quality and remove unused imports.
