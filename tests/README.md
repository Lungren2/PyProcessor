# PyProcessor Tests

This directory contains tests for the PyProcessor application.

## Testing Strategy

PyProcessor follows a comprehensive testing strategy that includes several types of tests to ensure code quality, functionality, and performance. Our testing approach is designed to catch issues at different levels of the application, from individual components to end-to-end workflows.

### Testing Objectives

- **Functionality Verification**: Ensure all features work as expected
- **Regression Prevention**: Prevent new changes from breaking existing functionality
- **Edge Case Handling**: Verify the application handles unexpected inputs and error conditions
- **Performance Monitoring**: Ensure the application meets performance requirements
- **Memory Usage Control**: Monitor and control memory consumption

## Test Structure

The tests are organized into three main categories:

- **Unit Tests**: Tests for individual components and functions
- **Integration Tests**: Tests for interactions between components
- **Performance Tests**: Tests for execution time and memory usage

## Running Tests

### Functional Tests

You can run the functional tests (unit and integration) using the provided test runner script:

```bash
python scripts/run_tests.py
```

#### Running Specific Test Types

To run only unit tests:

```bash
python scripts/run_tests.py --unit
```

To run only integration tests:

```bash
python scripts/run_tests.py --integration
```

#### Running Specific Test Modules

To run tests for a specific module:

```bash
python scripts/run_tests.py --module config
```

To run tests for a specific class:

```bash
python scripts/run_tests.py --class Config
```

#### Running with Coverage

To run tests with coverage reporting:

```bash
python scripts/run_tests.py --coverage
```

To generate an HTML coverage report:

```bash
python scripts/run_tests.py --coverage --html
```

### Performance Tests

You can run the performance tests using the dedicated performance test runner script:

```bash
python scripts/run_performance_tests.py
```

#### Running Specific Performance Test Modules

To run only specific performance test modules:

```bash
python scripts/run_performance_tests.py --module encoder
python scripts/run_performance_tests.py --module ui
python scripts/run_performance_tests.py --module workflow
```

#### Disabling Memory Tracking

Memory tracking can be disabled if you only want to measure execution time:

```bash
python scripts/run_performance_tests.py --no-memory
```

#### Generating HTML Reports

You can generate HTML reports for the performance tests:

```bash
python scripts/run_performance_tests.py --html
```

### Using the Makefile

On Linux/macOS, you can use the Makefile targets:

```bash
make test        # Run functional tests
make perf-test   # Run performance tests
```

## Writing Tests

### Unit Tests

Unit tests should be placed in the `tests/unit/` directory and follow these naming conventions:

- Test files should be named `test_*.py`
- Test classes should be named `Test*`
- Test methods should be named `test_*`

Example:

```python
# tests/unit/test_encoder.py
import unittest
from pyprocessor.processing.encoder import FFmpegEncoder

class TestFFmpegEncoder(unittest.TestCase):
    def test_initialization(self):
        encoder = FFmpegEncoder(
            input_path="test.mp4",
            output_path="output.mp4",
            encoder="libx264"
        )
        self.assertEqual(encoder.input_path, "test.mp4")
        self.assertEqual(encoder.output_path, "output.mp4")
        self.assertEqual(encoder.encoder, "libx264")

    def test_encode(self):
        # Test encoding functionality
        pass
```

### Integration Tests

Integration tests should be placed in the `tests/integration/` directory and follow the same naming conventions as unit tests.

Example:

```python
# tests/integration/test_basic_functionality.py
import os
import sys
import tempfile
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the modules to test
from pyprocessor.utils.config import Config
from pyprocessor.utils.logging import Logger
from pyprocessor.processing.file_manager import FileManager

def create_test_video(directory, filename, size_mb=1):
    """Create a test video file of the specified size."""
    file_path = directory / filename

    # Create a file with random data
    with open(file_path, 'wb') as f:
        f.write(os.urandom(size_mb * 1024 * 1024))

    return file_path

def test_file_renaming():
    """Test that the file renaming functionality works correctly."""
    # Setup test environment
    temp_dir = tempfile.TemporaryDirectory()
    base_dir = Path(temp_dir.name)
    input_dir = base_dir / "input"
    logs_dir = base_dir / "logs"

    # Create directories
    input_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)

    try:
        # Create test video files
        test_files = [
            "101-001.mp4",  # Already correctly named
            "movie_102-002_1080p.mp4",  # Needs renaming
            "tv_show_103-003_720p.mp4",  # Needs renaming
            "invalid_file.mp4"  # Invalid naming pattern
        ]

        for filename in test_files:
            create_test_video(input_dir, filename)

        # Configure the processor
        config = Config()
        config.input_folder = input_dir
        config.auto_rename_files = True
        config.file_rename_pattern = r".*?(\d+-\d+).*?\.mp4$"

        # Create logger
        logger = Logger(log_dir=logs_dir, level="INFO")

        try:
            # Create file manager
            file_manager = FileManager(config, logger)

            # Execute file renaming
            renamed_count = file_manager.rename_files()

            # Verify expected outputs
            assert renamed_count == 2  # Two files should be renamed
            assert (input_dir / "101-001.mp4").exists()  # Already correct
            assert (input_dir / "102-002.mp4").exists()  # Renamed
            assert (input_dir / "103-003.mp4").exists()  # Renamed
            assert (input_dir / "invalid_file.mp4").exists()  # Not renamed (invalid)
        finally:
            # Close logger to release file handles
            logger.close()
    finally:
        # Cleanup test artifacts
        temp_dir.cleanup()
```

### Writing Performance Tests

Performance tests should be placed in the `tests/performance/` directory and follow these guidelines:

- Test files should be named `test_*_performance.py`
- Test classes should inherit from `PerformanceTest`
- Test classes should implement `setup()`, `teardown()`, and `run_iteration()` methods

Example:

```python
# tests/performance/test_component_performance.py
from tests.performance.test_performance_base import PerformanceTest, PerformanceResult, MemoryUsage, time_and_memory_function

class ComponentPerformanceTest(PerformanceTest):
    def __init__(self, iterations: int = 5):
        super().__init__("Component Test", iterations)

    def setup(self) -> None:
        # Set up test environment
        pass

    def teardown(self) -> None:
        # Clean up test environment
        pass

    def run_iteration(self) -> PerformanceResult:
        # Run a single iteration of the test
        _, execution_time, memory_usage = time_and_memory_function(my_function)
        return PerformanceResult(execution_time, memory_usage)

def test_component_performance():
    test = ComponentPerformanceTest()
    results = test.run()
    test.print_results(results)

    # Assert that the performance is reasonable
    assert results["avg_time"] < 0.1, "Component is too slow"
```

## Test Categories and Coverage

### Unit Test Categories

Unit tests focus on testing individual components in isolation. Key unit test categories include:

- **Config Tests**: Test configuration loading, saving, and validation
- **Encoder Tests**: Test FFmpeg command building and encoding functionality
- **File Manager Tests**: Test file validation, renaming, and organization
- **Scheduler Tests**: Test task scheduling and progress tracking
- **GUI Component Tests**: Test individual GUI components
- **Server Optimizer Tests**: Test server optimization functionality
- **Logger Tests**: Test logging functionality and log rotation
- **Error Handling Tests**: Test error handling and recovery mechanisms

### Integration Test Categories

Integration tests focus on testing interactions between components. Key integration test categories include:

- **Processing Workflow Tests**: Test the end-to-end video processing workflow
- **File Management Tests**: Test file renaming, validation, and folder organization
- **Video Processing Tests**: Test the video encoding and processing pipeline
- **CLI Interface Tests**: Test command-line argument parsing and execution
- **GUI Workflow Tests**: Test user interactions with the GUI

### Performance Test Categories

Performance tests focus on measuring execution time and memory usage. Key performance test categories include:

- **Encoder Performance Tests**: Test the performance of encoding operations
- **File Manager Performance Tests**: Test the performance of file operations
- **Scheduler Performance Tests**: Test the performance of task scheduling
- **UI Performance Tests**: Test the performance of GUI components
- **Config Performance Tests**: Test the performance of configuration operations
- **Server Optimizer Performance Tests**: Test the performance of server optimization
- **Workflow Performance Tests**: Test the performance of end-to-end workflows
- **Parallel Processing Tests**: Test the efficiency of parallel processing

## Test Dependencies

### Functional Test Dependencies

The functional tests require the following dependencies:

- pytest
- pytest-cov (for coverage reporting)

### Performance Test Dependencies

The performance tests require the following additional dependencies:

- psutil (for memory usage monitoring)
- pytest-html (for HTML reports)

### Installing Dependencies

These dependencies are automatically installed when you run the development setup script:

```bash
python scripts/dev_setup.py
```

You can also install the performance test dependencies separately:

```bash
python scripts/install_performance_deps.py
```

## Test Results

### Functional Test Results

Functional test results are displayed in the console and, if enabled, in an HTML coverage report.

### Performance Test Results

Performance test results are displayed in the console and saved in the `performance_results` directory. Each test run generates a JSON file with the following information:

- Timestamp
- Module tested
- Memory tracking status
- Execution time
- System information

## Continuous Integration

PyProcessor uses GitHub Actions for continuous integration. The CI pipeline runs all functional tests on each pull request and push to the main branches.

### CI/CD Pipeline

The CI/CD pipeline includes the following steps:

1. **Setup**: Install Python and dependencies
2. **Linting**: Run linting checks with flake8
3. **Unit Tests**: Run unit tests with pytest
4. **Integration Tests**: Run integration tests with pytest
5. **Coverage**: Generate coverage reports
6. **Performance Tests**: Run performance tests on scheduled runs
7. **Build**: Build the application package
8. **Deploy**: Deploy the application (on release branches only)

For more details on the CI/CD setup, see the [TESTING_AND_CICD.md](../docs/developer/TESTING_AND_CICD.md) document.
