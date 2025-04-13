# Testing and CI/CD in PyProcessor

This document provides comprehensive information about the testing strategy and continuous integration/continuous deployment (CI/CD) setup for the PyProcessor project.

## Table of Contents

- [Testing Strategy](#testing-strategy)
  - [Unit Tests](#unit-tests)
  - [Integration Tests](#integration-tests)
  - [Performance Tests](#performance-tests)
  - [Edge Cases and Error Conditions](#edge-cases-and-error-conditions)
  - [Running Tests](#running-tests)
- [CI/CD Setup](#cicd-setup)
  - [GitHub Actions Workflows](#github-actions-workflows)
  - [Automated Testing](#automated-testing)
  - [Code Quality Checks](#code-quality-checks)
  - [Building and Packaging](#building-and-packaging)
  - [Dependency Updates](#dependency-updates)
- [Best Practices](#best-practices)
  - [Writing Effective Tests](#writing-effective-tests)
  - [Handling Edge Cases](#handling-edge-cases)
  - [Mocking External Dependencies](#mocking-external-dependencies)

## Testing Strategy

PyProcessor uses a comprehensive testing strategy that includes unit tests, integration tests, and specific tests for edge cases and error conditions.

### Unit Tests

Unit tests focus on testing individual components in isolation. Each major component of PyProcessor has its own set of unit tests:

- **Configuration Tests** (`test_config.py`): Tests for loading, saving, and validating configuration settings and profiles.
- **File Manager Tests** (`test_file_manager.py`): Tests for file validation, renaming, and folder organization.
- **FFmpeg Encoder Tests** (`test_encoder.py`): Tests for video encoding, progress tracking, and command building.
- **Processing Scheduler Tests** (`test_scheduler.py`): Tests for parallel processing, progress tracking, and error handling.
- **Logger Tests** (`test_logger.py`): Tests for logging functionality and log file management.
- **Theme Manager Tests** (`test_theme_manager.py`): Tests for theme detection, switching, and error handling.
- **Server Optimizer Tests** (`test_server_optimizer.py`): Tests for IIS, Nginx, and Linux server optimization.
- **GUI Component Tests** (`test_gui_components.py`): Tests for main window, settings widgets, and progress display.

### Integration Tests

Integration tests verify that different components work together correctly:

- **Processing Workflow Tests** (`test_processing_workflow.py`): Tests for the end-to-end video processing workflow.
- **CLI Interface Tests** (`test_cli_interface.py`): Tests for command-line argument parsing and execution.

### Performance Tests

Performance tests measure execution time and memory usage to ensure the application meets performance requirements:

- **Encoder Performance Tests** (`test_encoder_performance.py`): Tests for the performance of encoding operations.
- **File Manager Performance Tests** (`test_file_manager_performance.py`): Tests for the performance of file operations.
- **Scheduler Performance Tests** (`test_scheduler_performance.py`): Tests for the performance of task scheduling.
- **UI Performance Tests** (`test_ui_performance.py`): Tests for the performance of GUI components.
- **Config Performance Tests** (`test_config_performance.py`): Tests for the performance of configuration operations.
- **Server Optimizer Performance Tests** (`test_server_optimizer_performance.py`): Tests for the performance of server optimization.
- **Workflow Performance Tests** (`test_workflow_performance.py`): Tests for the performance of end-to-end workflows.
- **Parallel Processing Tests** (`test_parallel_processing_performance.py`): Tests for the efficiency of parallel processing.

### Edge Cases and Error Conditions

Specific tests for edge cases and error conditions ensure that the application handles unexpected situations gracefully:

- **Config Edge Cases** (`test_config_edge_cases.py`): Tests for handling invalid configuration files, missing fields, and validation errors.
- **File Manager Edge Cases** (`test_file_manager_edge_cases.py`): Tests for handling permission errors, invalid patterns, and special characters.
- **Encoder Error Conditions** (`test_encoder_error_conditions.py`): Tests for handling FFmpeg errors, process crashes, and invalid parameters.
- **Scheduler Error Conditions** (`test_scheduler_error_conditions.py`): Tests for handling process pool errors, task failures, and cancellation.

### Running Tests

You can run the tests using the provided test runner script:

```bash
# Run all tests
python scripts/run_tests.py

# Run only unit tests
python scripts/run_tests.py --unit

# Run only integration tests
python scripts/run_tests.py --integration

# Run with code coverage
python scripts/run_tests.py --coverage

# Generate HTML coverage report
python scripts/run_tests.py --coverage --html

# Run tests for a specific module
python scripts/run_tests.py --module config

# Run tests for a specific class
python scripts/run_tests.py --class Config

# Run with increased verbosity
python scripts/run_tests.py --verbose

# Stop on first failure
python scripts/run_tests.py --fail-fast

# Run performance tests
python scripts/run_performance_tests.py

# Run specific performance test module
python scripts/run_performance_tests.py --module encoder

# Run performance tests without memory tracking
python scripts/run_performance_tests.py --no-memory

# Generate HTML performance report
python scripts/run_performance_tests.py --html
```

## CI/CD Setup

PyProcessor uses GitHub Actions for continuous integration and continuous deployment.

### GitHub Actions Workflows

The following workflows are configured:

1. **Tests Workflow** (`.github/workflows/tests.yml`): Runs tests on every push and pull request.
2. **Build Workflow** (`.github/workflows/build.yml`): Builds and packages the application on tags and main branch.
3. **Code Quality Workflow** (`.github/workflows/code-quality.yml`): Checks code quality on every push and pull request.
4. **Dependencies Workflow** (`.github/workflows/dependencies.yml`): Updates dependencies weekly.

### Automated Testing

The tests workflow:

- Runs on Windows with multiple Python versions (3.8, 3.9, 3.10)
- Installs dependencies
- Runs linting with flake8
- Checks formatting with black
- Runs unit tests with coverage
- Runs integration tests
- Runs performance tests (on scheduled runs only)
- Uploads coverage reports to Codecov

### Code Quality Checks

The code quality workflow:

- Runs on Ubuntu
- Checks code formatting with black
- Checks import sorting with isort
- Runs linting with flake8
- Checks types with mypy
- Checks security issues with bandit

### Building and Packaging

The build workflow:

- Runs on Windows
- Installs dependencies
- Downloads FFmpeg
- Builds the application with PyInstaller
- Uploads build artifacts
- Creates an installer (if triggered by a tag)
- Creates a GitHub release (if triggered by a tag)

### Dependency Updates

The dependencies workflow:

- Runs weekly on Sunday
- Updates dependencies using pip-tools
- Creates a pull request with the updates

## Best Practices

### Writing Effective Tests

1. **Test One Thing at a Time**: Each test should focus on testing a single functionality or behavior.
2. **Use Descriptive Test Names**: Test names should clearly describe what is being tested.
3. **Arrange-Act-Assert**: Structure tests with setup, action, and verification phases.
4. **Keep Tests Independent**: Tests should not depend on each other or on external state.
5. **Use Fixtures for Common Setup**: Use pytest fixtures for common setup code.

### Handling Edge Cases

1. **Identify Edge Cases**: Consider boundary conditions, invalid inputs, and error scenarios.
2. **Test Error Handling**: Verify that errors are handled gracefully and appropriate error messages are provided.
3. **Test Resource Cleanup**: Ensure resources are properly cleaned up, even in error cases.
4. **Test Concurrency Issues**: Verify that parallel processing works correctly and handles race conditions.

### Mocking External Dependencies

1. **Mock External Services**: Use mocks for external services like FFmpeg.
2. **Mock File System Operations**: Use temporary directories and mock file operations for testing.
3. **Mock User Interface**: Use mock objects for testing UI components without a display server.
4. **Control Time**: Mock time-dependent operations to make tests deterministic.

### Performance Testing

1. **Measure Baseline**: Establish a baseline for performance before making changes.
2. **Test with Realistic Data**: Use realistic data sizes and operation counts.
3. **Test Scaling**: Test with different data sizes to understand scaling behavior.
4. **Monitor Memory Usage**: Track memory usage to identify memory leaks and excessive consumption.
5. **Test Parallel Processing**: Test the efficiency of parallel processing with different numbers of workers.
6. **Set Reasonable Thresholds**: Set reasonable performance thresholds that scale with workload size.
7. **Isolate Tests**: Create isolated test environments to ensure consistent results.

By following these practices and using the provided testing infrastructure, you can ensure that PyProcessor remains robust, reliable, maintainable, and performant.
