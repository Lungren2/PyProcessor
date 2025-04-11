"""
Base framework for performance testing in PyProcessor.
"""
import os
import sys
import time
import tempfile
import statistics
import pytest
import psutil
import gc
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional, Tuple, NamedTuple

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

class MemoryUsage(NamedTuple):
    """Memory usage information."""
    before: int  # Memory usage before function execution (bytes)
    after: int   # Memory usage after function execution (bytes)
    diff: int    # Difference in memory usage (bytes)

class PerformanceResult(NamedTuple):
    """Result of a performance test iteration."""
    execution_time: float      # Execution time in seconds
    memory_usage: MemoryUsage  # Memory usage information

class PerformanceTest:
    """Base class for performance tests."""

    def __init__(self, name: str, iterations: int = 5, warmup_iterations: int = 1, track_memory: bool = True):
        """
        Initialize the performance test.

        Args:
            name: Name of the test
            iterations: Number of iterations to run
            warmup_iterations: Number of warmup iterations to run (not included in results)
            track_memory: Whether to track memory usage
        """
        self.name = name
        self.iterations = iterations
        self.warmup_iterations = warmup_iterations
        self.track_memory = track_memory
        self.results: List[PerformanceResult] = []

    def setup(self) -> None:
        """Set up the test environment. Override in subclasses."""
        pass

    def teardown(self) -> None:
        """Clean up the test environment. Override in subclasses."""
        pass

    def run_iteration(self) -> PerformanceResult:
        """
        Run a single iteration of the test.

        Returns:
            PerformanceResult with execution time and memory usage
        """
        raise NotImplementedError("Subclasses must implement run_iteration")

    def run(self) -> Dict[str, Any]:
        """
        Run the performance test.

        Returns:
            Dictionary with test results
        """
        self.setup()

        try:
            # Run warmup iterations
            for _ in range(self.warmup_iterations):
                self.run_iteration()

            # Run actual iterations
            self.results = []
            for _ in range(self.iterations):
                result = self.run_iteration()
                self.results.append(result)

        finally:
            self.teardown()

        # Calculate statistics
        if self.results:
            # Time statistics
            times = [result.execution_time for result in self.results]
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            median_time = statistics.median(times)
            stdev_time = statistics.stdev(times) if len(times) > 1 else 0

            # Memory statistics
            if self.track_memory:
                memory_diffs = [result.memory_usage.diff for result in self.results]
                avg_memory = statistics.mean(memory_diffs)
                min_memory = min(memory_diffs)
                max_memory = max(memory_diffs)
                median_memory = statistics.median(memory_diffs)
                stdev_memory = statistics.stdev(memory_diffs) if len(memory_diffs) > 1 else 0
            else:
                avg_memory = min_memory = max_memory = median_memory = stdev_memory = 0
        else:
            avg_time = min_time = max_time = median_time = stdev_time = 0
            avg_memory = min_memory = max_memory = median_memory = stdev_memory = 0

        return {
            "name": self.name,
            "iterations": self.iterations,
            "results": self.results,
            "avg_time": avg_time,
            "min_time": min_time,
            "max_time": max_time,
            "median_time": median_time,
            "stdev_time": stdev_time,
            "avg_memory": avg_memory,
            "min_memory": min_memory,
            "max_memory": max_memory,
            "median_memory": median_memory,
            "stdev_memory": stdev_memory,
            "track_memory": self.track_memory
        }

    def print_results(self, results: Dict[str, Any]) -> None:
        """
        Print the test results.

        Args:
            results: Dictionary with test results
        """
        print(f"\nPerformance Test: {results['name']}")
        print(f"Iterations: {results['iterations']}")

        # Time results
        print("\nTime Results:")
        print(f"  Average Time: {results['avg_time']:.4f} seconds")
        print(f"  Minimum Time: {results['min_time']:.4f} seconds")
        print(f"  Maximum Time: {results['max_time']:.4f} seconds")
        print(f"  Median Time: {results['median_time']:.4f} seconds")
        print(f"  Standard Deviation: {results['stdev_time']:.4f} seconds")

        # Memory results
        if results['track_memory']:
            print("\nMemory Results:")
            print(f"  Average Memory: {format_bytes(results['avg_memory'])}")
            print(f"  Minimum Memory: {format_bytes(results['min_memory'])}")
            print(f"  Maximum Memory: {format_bytes(results['max_memory'])}")
            print(f"  Median Memory: {format_bytes(results['median_memory'])}")
            print(f"  Standard Deviation: {format_bytes(results['stdev_memory'])}")

        print("\nIndividual Results:")
        for i, result in enumerate(results['results'], 1):
            if results['track_memory']:
                print(f"  Iteration {i}: {result.execution_time:.4f} seconds, Memory: {format_bytes(result.memory_usage.diff)}")
            else:
                print(f"  Iteration {i}: {result.execution_time:.4f} seconds")

def format_bytes(bytes_value: int) -> str:
    """
    Format bytes value to human-readable string.

    Args:
        bytes_value: Value in bytes

    Returns:
        Formatted string
    """
    if bytes_value < 0:
        return f"-{format_bytes(-bytes_value)}"

    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024 or unit == 'TB':
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024

def get_memory_usage() -> int:
    """
    Get current memory usage of the process.

    Returns:
        Memory usage in bytes
    """
    process = psutil.Process(os.getpid())
    return process.memory_info().rss

def time_function(func: Callable, *args, **kwargs) -> Tuple[Any, float]:
    """
    Time the execution of a function.

    Args:
        func: Function to time
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        Tuple of (function result, execution time in seconds)
    """
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    return result, end_time - start_time

def time_and_memory_function(func: Callable, *args, **kwargs) -> Tuple[Any, float, MemoryUsage]:
    """
    Time the execution of a function and measure memory usage.

    Args:
        func: Function to time
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        Tuple of (function result, execution time in seconds, memory usage)
    """
    # Force garbage collection before measuring memory
    gc.collect()

    # Measure memory before execution
    memory_before = get_memory_usage()

    # Time the function
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()

    # Force garbage collection after execution
    gc.collect()

    # Measure memory after execution
    memory_after = get_memory_usage()

    # Calculate memory difference
    memory_diff = memory_after - memory_before

    return result, end_time - start_time, MemoryUsage(memory_before, memory_after, memory_diff)

def create_test_video(directory: Path, filename: str, size_mb: int = 10) -> Path:
    """
    Create a test video file of the specified size.

    Args:
        directory: Directory to create the file in
        filename: Name of the file
        size_mb: Size of the file in megabytes

    Returns:
        Path to the created file
    """
    file_path = directory / filename

    # Create a file with random data
    with open(file_path, 'wb') as f:
        f.write(os.urandom(size_mb * 1024 * 1024))

    return file_path

def create_test_videos(directory: Path, count: int, size_mb: int = 10) -> List[Path]:
    """
    Create multiple test video files.

    Args:
        directory: Directory to create the files in
        count: Number of files to create
        size_mb: Size of each file in megabytes

    Returns:
        List of paths to the created files
    """
    files = []
    for i in range(count):
        filename = f"test_video_{i+1}_1080p.mp4"
        file_path = create_test_video(directory, filename, size_mb)
        files.append(file_path)
    return files
