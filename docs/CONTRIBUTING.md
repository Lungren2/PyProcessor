# Contributing to Video Processor

Thank you for your interest in contributing to the Video Processor project! This guide will help you understand the project structure, development workflow, and how to make contributions.

## Table of Contents

- [Project Overview](#project-overview)
- [Development Environment Setup](#development-environment-setup)
- [Project Architecture](#project-architecture)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)

## Project Overview

Video Processor is a Python application for video processing and HLS encoding based on FFmpeg. It provides both a graphical user interface and command-line interface for processing video files with various encoding options, supporting parallel processing for improved performance.

The project aims to provide a user-friendly, cross-platform solution for video encoding tasks, with a focus on:

- Ease of use through a well-designed GUI
- Flexibility through command-line options
- Performance through parallel processing
- Reliability through robust error handling and logging

## Development Environment Setup

### Prerequisites

- Python 3.6 or higher
- FFmpeg installed and available in PATH
- Git for version control

### Setting Up Your Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/Lungren2/PyProcessor.git
   cd PyProcessor
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the package in development mode:
   ```bash
   pip install -e .
   ```

4. Install development dependencies:
   ```bash
   pip install pytest pytest-cov flake8 black
   ```

## Project Architecture

The project follows a modular architecture with clear separation of concerns:

- **GUI Module**: Handles user interface components
- **Processing Module**: Contains core processing logic
- **Utils Module**: Provides utility functions and configuration management

For a detailed overview of the architecture, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Development Workflow

1. **Create a Feature Branch**: Always create a new branch for your changes
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**: Implement your changes following the coding standards

3. **Write Tests**: Add tests for your changes to ensure they work as expected

4. **Run Tests**: Ensure all tests pass
   ```bash
   python -m pytest
   ```

5. **Format Code**: Ensure your code follows the project's style guidelines
   ```bash
   black video_processor
   ```

6. **Submit a Pull Request**: Push your changes and create a pull request

## Coding Standards

We follow PEP 8 style guidelines for Python code. Some key points:

- Use 4 spaces for indentation
- Maximum line length of 88 characters (as per Black formatter)
- Use descriptive variable and function names
- Include docstrings for all modules, classes, and functions
- Add type hints where appropriate

We use Black for code formatting and flake8 for linting.

## Testing

We use pytest for testing. All new features should include tests, and all tests should pass before submitting a pull request.

To run tests:
```bash
python -m pytest
```

To run tests with coverage:
```bash
python -m pytest --cov=video_processor
```

## Documentation

Documentation is a crucial part of the project. Please update or add documentation for any changes you make:

- Update docstrings for any modified code
- Update relevant markdown files in the `docs/` directory
- For significant changes, consider updating the README.md

## Submitting Changes

1. Push your changes to your fork of the repository
2. Submit a pull request to the main repository
3. Describe your changes in detail in the pull request description
4. Reference any related issues in your pull request

Thank you for contributing to Video Processor!
