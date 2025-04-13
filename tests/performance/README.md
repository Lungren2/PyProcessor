# PyProcessor Performance Tests

This directory contains performance tests for the PyProcessor application. These tests measure the execution time and memory usage of various components and workflows.

## Test Structure

The performance tests are organized into several modules:

- **test_performance_base.py**: Base framework for performance testing
- **test_encoder_performance.py**: Tests for the encoder component
- **test_file_manager_performance.py**: Tests for the file manager component
- **test_scheduler_performance.py**: Tests for the scheduler component
- **test_ui_performance.py**: Tests for the GUI components
- **test_config_performance.py**: Tests for configuration and profile management
- **test_server_optimizer_performance.py**: Tests for server optimization functionality
- **test_workflow_performance.py**: Tests for end-to-end workflows
- **test_parallel_processing_performance.py**: Tests for parallel processing efficiency

## Running Performance Tests

You can run the performance tests using the provided script:

```bash
python scripts/run_performance_tests.py
```

### Running Specific Test Modules

To run only specific performance test modules:

```bash
python scripts/run_performance_tests.py --module encoder
python scripts/run_performance_tests.py --module ui
python scripts/run_performance_tests.py --module workflow
```

### Disabling Memory Tracking

Memory tracking can be disabled if you only want to measure execution time:

```bash
python scripts/run_performance_tests.py --no-memory
```

### Generating HTML Reports

You can generate HTML reports for the performance tests:

```bash
python scripts/run_performance_tests.py --html
```

### Using the Makefile

On Linux/macOS:

```bash
make perf-test
```

## Test Results

Performance test results are saved in the `performance_results` directory. Each test run generates a JSON file with the following information:

- Timestamp
- Module tested
- Memory tracking status
- Execution time
- System information

## Writing Performance Tests

To write a new performance test:

1. Create a new file in the `tests/performance` directory named `test_<component>_performance.py`
2. Import the base classes from `test_performance_base.py`
3. Create a test class that inherits from `PerformanceTest`
4. Implement the `setup()`, `teardown()`, and `run_iteration()` methods
5. Create test functions that instantiate your test class and run it

Example:

```python
from tests.performance.test_performance_base import PerformanceTest, PerformanceResult, MemoryUsage, time_and_memory_function

class MyComponentPerformanceTest(PerformanceTest):
    def __init__(self, iterations: int = 5):
        super().__init__("My Component Test", iterations)
        
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

def test_my_component_performance():
    test = MyComponentPerformanceTest()
    results = test.run()
    test.print_results(results)
    
    # Assert that the performance is reasonable
    assert results["avg_time"] < 0.1, "My component is too slow"
```

## Dependencies

The performance tests require the following dependencies:

- psutil
- pytest
- pytest-cov
- pytest-html (for HTML reports)

These dependencies can be installed using the provided script:

```bash
python scripts/install_performance_deps.py
```
