# Makefile for PyProcessor

.PHONY: setup clean lint format clean-code build package run all

# Default target
all: clean build

# Setup development environment
setup:
	python scripts/dev_setup.py

# Clean up temporary files and build artifacts
clean:
	python scripts/cleanup.py --all



# Run linting
lint:
	flake8 pyprocessor

# Format code
format:
	black pyprocessor scripts

# Clean code (remove unused imports and comment unused variables)
clean-code:
	python scripts/clean_code.py

# Build executable
build:
	python scripts/build_package.py --skip-nsis

# Package executable with NSIS
package:
	python scripts/build_package.py --skip-ffmpeg --skip-pyinstaller

# Run the application
run:
	python -m pyprocessor
