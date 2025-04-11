#!/usr/bin/env python
"""
Test runner script for PyProcessor.

This script runs the test suite for PyProcessor with various options:
- Unit tests only
- Integration tests only
- All tests
- With or without coverage reports
- Specific test modules or classes

Usage:
    python scripts/run_tests.py [--unit] [--integration] [--coverage] [--html] [--module MODULE] [--class CLASS] [--verbose] [--fail-fast]

Options:
    --unit         Run only unit tests
    --integration  Run only integration tests
    --coverage     Generate coverage report
    --html         Generate HTML coverage report
    --module       Run tests in a specific module (e.g., test_config)
    --class        Run tests in a specific class (e.g., TestConfig)
    --verbose      Show more detailed output
    --fail-fast    Stop on first failure
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def run_tests(unit_only=False, integration_only=False, coverage=False, html_report=False,
            module=None, test_class=None, verbose=False, fail_fast=False):
    """Run the test suite with the specified options."""
    # Ensure the tests directory exists
    tests_dir = Path("tests")
    if not tests_dir.exists():
        print("Tests directory not found. Creating it...")
        os.makedirs("tests/unit", exist_ok=True)
        os.makedirs("tests/integration", exist_ok=True)

        # Create __init__.py files
        Path("tests/__init__.py").touch()
        Path("tests/unit/__init__.py").touch()
        Path("tests/integration/__init__.py").touch()

        print("Created tests directory structure.")
        print("Please add tests before running this script again.")
        return False

    # Determine which tests to run
    if module or test_class:
        # If a specific module or class is specified, use that
        if module and test_class:
            test_path = f"tests/unit/test_{module}.py::Test{test_class}"
        elif module:
            test_path = f"tests/unit/test_{module}.py"
        else:  # test_class only
            # Search for the class in all test files
            test_path = f"tests/unit/::Test{test_class}"
    elif unit_only and integration_only:
        print("Cannot specify both --unit and --integration. Running all tests.")
        test_path = "tests"
    elif unit_only:
        test_path = "tests/unit"
    elif integration_only:
        test_path = "tests/integration"
    else:
        test_path = "tests"

    # Build the command
    cmd = ["pytest"]

    # Add verbosity
    if verbose:
        cmd.append("-vv")
    else:
        cmd.append("-v")

    # Add fail-fast option
    if fail_fast:
        cmd.append("-x")

    # Add coverage options if requested
    if coverage:
        cmd.extend(["--cov=video_processor", "--cov-report=term"])
        if html_report:
            cmd.append("--cov-report=html")

    # Add the test path
    cmd.append(test_path)

    print(f"Running command: {' '.join(cmd)}")

    try:
        # Run the tests
        result = subprocess.run(cmd, check=False)

        if result.returncode == 0:
            print("\n✓ All tests passed!")

            if coverage and html_report:
                print("\nHTML coverage report generated in htmlcov/index.html")

            return True
        else:
            print("\n✗ Some tests failed.")
            return False
    except Exception as e:
        print(f"\n✗ Error running tests: {e}")
        return False

def main():
    """Parse arguments and run tests."""
    parser = argparse.ArgumentParser(description="Run PyProcessor tests")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--html", action="store_true", help="Generate HTML coverage report")
    parser.add_argument("--module", help="Run tests in a specific module (e.g., config)")
    parser.add_argument("--class", dest="test_class", help="Run tests in a specific class (e.g., Config)")
    parser.add_argument("--verbose", action="store_true", help="Show more detailed output")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failure")
    args = parser.parse_args()

    success = run_tests(
        unit_only=args.unit,
        integration_only=args.integration,
        coverage=args.coverage,
        html_report=args.html,
        module=args.module,
        test_class=args.test_class,
        verbose=args.verbose,
        fail_fast=args.fail_fast
    )

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
