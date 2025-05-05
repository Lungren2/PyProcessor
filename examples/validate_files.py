"""
Example script demonstrating how to use the validation system with the file manager.

This script shows how to validate files using the file manager and the validation system.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyprocessor.utils.file_system.file_manager import FileManager
from pyprocessor.utils.core.validation_manager import (
    validate_path,
    validate_string,
    validate_regex,
    ValidationResult,
)


def print_validation_result(result, field_name=None):
    """Print a validation result."""
    if result:
        print(f"✅ Validation passed for {field_name or 'value'}")
    else:
        print(f"❌ Validation failed for {field_name or 'value'}")
        for error in result.errors:
            print(f"  Error: {error.message}")
        for warning in result.warnings:
            print(f"  Warning: {warning.message}")
    print()


def main():
    """Main function demonstrating file validation."""
    print("File Validation Example")
    print("======================")

    # Create a temporary directory for testing
    temp_dir = Path(__file__).parent / "temp_validation"
    temp_dir.mkdir(exist_ok=True)

    # Create some test files
    valid_files = ["123-456.mp4", "789-012.mp4"]
    invalid_files = ["invalid.mp4", "123_456.mp4", "abc-def.mp4"]

    for filename in valid_files + invalid_files:
        with open(temp_dir / filename, "w") as f:
            f.write("Test file")

    # Create a file manager
    file_manager = FileManager()

    # Set the input folder
    file_manager.input_folder = temp_dir

    # Define a validation pattern
    pattern = r"^\d+-\d+\.mp4$"

    print("\n1. Validate the pattern")
    pattern_result = validate_regex(pattern, "pattern")
    print_validation_result(pattern_result, "pattern")

    print("\n2. Validate the directory")
    dir_result = validate_path(temp_dir, "directory", must_exist=True, must_be_dir=True)
    print_validation_result(dir_result, "directory")

    print("\n3. Validate files using the file manager")
    valid_files, invalid_files = file_manager.validate_files(temp_dir, pattern)

    print(f"Valid files ({len(valid_files)}):")
    for file in valid_files:
        print(f"  - {file.name}")

    print(f"\nInvalid files ({len(invalid_files)}):")
    for file in invalid_files:
        print(f"  - {file}")

    print("\n4. Validate individual files")
    for filename in valid_files + invalid_files:
        result = validate_string(filename, "file_name", pattern=pattern)
        print_validation_result(result, filename)

    # Clean up
    for file in temp_dir.glob("*.mp4"):
        file.unlink()
    temp_dir.rmdir()

    print("\nFile validation example completed")


if __name__ == "__main__":
    main()
