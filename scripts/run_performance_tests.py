#!/usr/bin/env python
"""
Script to run performance tests for PyProcessor.

This script runs the performance test suite for PyProcessor with various options:
- All performance tests
- Specific performance test modules
- With or without memory tracking
- With or without HTML report generation

Usage:
    python scripts/run_performance_tests.py [--module MODULE] [--no-memory] [--html] [--verbose]

Options:
    --module       Run tests in a specific module (e.g., encoder, scheduler)
    --no-memory    Disable memory tracking
    --html         Generate HTML report
    --verbose      Show more detailed output
"""

import os
import sys
import subprocess
import argparse
import time
import json
from pathlib import Path
from datetime import datetime

def ensure_dependencies():
    """Ensure that all required dependencies are installed."""
    try:
        pass
    except ImportError:
        print("Installing required dependencies...")
        subprocess.check_call([sys.executable, "scripts/install_performance_deps.py"])

def run_performance_tests(module=None, track_memory=True, html_report=False, verbose=False):
    """Run the performance test suite with the specified options."""
    # Ensure the performance tests directory exists
    tests_dir = Path("tests/performance")
    if not tests_dir.exists():
        print("Performance tests directory not found.")
        return False

    # Determine which tests to run
    if module:
        test_path = tests_dir / f"test_{module}_performance.py"
        if not test_path.exists():
            print(f"Performance test module not found: {test_path}")
            return False
    else:
        test_path = tests_dir

    # Build the command
    cmd = [sys.executable, "-m", "pytest"]

    # Add verbosity
    if verbose:
        cmd.append("-vv")
    else:
        cmd.append("-v")

    # Add HTML report option if requested
    if html_report:
        cmd.append("--html=performance_report.html")
        cmd.append("--self-contained-html")

    # Add the test path
    cmd.append(str(test_path))

    # Set environment variable for memory tracking
    env = os.environ.copy()
    env["PYPROCESSOR_TRACK_MEMORY"] = "1" if track_memory else "0"

    print(f"Running command: {' '.join(cmd)}")

    try:
        # Run the tests
        start_time = time.time()
        result = subprocess.run(cmd, check=False, env=env)
        end_time = time.time()

        # Calculate execution time
        execution_time = end_time - start_time

        if result.returncode == 0:
            print(f"\n✓ All performance tests passed in {execution_time:.2f} seconds!")

            if html_report:
                print("\nHTML report generated in performance_report.html")

            # Save results to JSON file
            save_results(module, track_memory, execution_time)

            return True
        else:
            print(f"\n✗ Some performance tests failed after {execution_time:.2f} seconds.")
            return False
    except Exception as e:
        print(f"\n✗ Error running performance tests: {e}")
        return False

def save_results(module, track_memory, execution_time):
    """Save test results to a JSON file."""

    # Ensure psutil is available
    try:
        import psutil
    except ImportError:
        ensure_dependencies()

    # Create results directory if it doesn't exist
    results_dir = Path("performance_results")
    results_dir.mkdir(exist_ok=True)

    # Create a timestamp for the filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create the results file
    results_file = results_dir / f"performance_results_{timestamp}.json"
    
    # Create the results data
    results_data = {
        "timestamp": timestamp,
        "module": module if module else "all",
        "track_memory": track_memory,
        "execution_time": execution_time,
        "system_info": get_system_info()
    }
    
    # Write the results to the file
    with open(results_file, 'w') as f:
        json.dump(results_data, f, indent=4)
    
    print(f"\nResults saved to {results_file}")

def get_system_info():
    """Get system information for the results."""
    import platform
    import psutil
    
    return {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "processor": platform.processor(),
        "cpu_count": psutil.cpu_count(logical=False),
        "logical_cpu_count": psutil.cpu_count(logical=True),
        "memory_total": psutil.virtual_memory().total,
        "memory_available": psutil.virtual_memory().available
    }

def main():
    """Parse arguments and run performance tests."""
    parser = argparse.ArgumentParser(description="Run PyProcessor performance tests")
    parser.add_argument("--module", help="Run tests in a specific module (e.g., encoder, scheduler)")
    parser.add_argument("--no-memory", action="store_true", help="Disable memory tracking")
    parser.add_argument("--html", action="store_true", help="Generate HTML report")
    parser.add_argument("--verbose", action="store_true", help="Show more detailed output")
    args = parser.parse_args()

    # Ensure dependencies are installed
    ensure_dependencies()

    # Run the tests
    success = run_performance_tests(
        module=args.module,
        track_memory=not args.no_memory,
        html_report=args.html,
        verbose=args.verbose
    )

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
