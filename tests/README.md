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
from video_processor.processing.encoder import FFmpegEncoder

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
# tests/integration/test_processing_workflow.py
import unittest
import os
import tempfile
from video_processor.processing.scheduler import ProcessingScheduler

class TestProcessingWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_dir = os.path.join(self.temp_dir.name, "input")
        self.output_dir = os.path.join(self.temp_dir.name, "output")
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        # Create test files
        with open(os.path.join(self.input_dir, "test.mp4"), "wb") as f:
            f.write(b"test")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_scheduler_workflow(self):
        # Test the entire processing workflow
        pass
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

### Integration Test Categories

Integration tests focus on testing interactions between components. Key integration test categories include:

- **Processing Workflow Tests**: Test the end-to-end video processing workflow
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

For more details on the CI/CD setup, see the [TESTING_AND_CICD.md](../docs/developer/TESTING_AND_CICD.md) document.
