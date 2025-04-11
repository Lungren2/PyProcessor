# Makefile for PyProcessor

.PHONY: setup clean test perf-test lint format build package run all

# Default target
all: clean test build

# Setup development environment
setup:
	python scripts/dev_setup.py

# Clean up temporary files and build artifacts
clean:
	python scripts/cleanup.py --all

# Run tests
test:
	python scripts/run_tests.py --coverage

# Run performance tests
perf-test:
	python scripts/run_performance_tests.py

# Run linting
lint:
	flake8 video_processor

# Format code
format:
	black video_processor tests scripts

# Build executable
build:
	python scripts/build_package.py --skip-nsis

# Package executable with NSIS
package:
	python scripts/build_package.py --skip-ffmpeg --skip-pyinstaller

# Run the application
run:
	python -m video_processor
