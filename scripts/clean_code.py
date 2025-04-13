#!/usr/bin/env python
"""
Code cleaning script for PyProcessor.

This script:
1. Removes unused imports using autoflake
2. Identifies and comments out unused variables using vulture

Usage:
    python scripts/clean_code.py [--imports-only] [--variables-only] [--check]

Options:
    --imports-only    Only remove unused imports
    --variables-only  Only comment unused variables
    --check           Check for unused imports and variables without making changes
"""

import sys
import subprocess
import argparse
import re


def install_dependencies():
    """Install required dependencies if not already installed."""
    try:
        # Check if autoflake is installed
        subprocess.run(
            [sys.executable, "-m", "pip", "show", "autoflake"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print("✓ autoflake is already installed")
    except subprocess.CalledProcessError:
        print("Installing autoflake...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "autoflake"],
            check=True,
        )
        print("✓ Installed autoflake")

    try:
        # Check if vulture is installed
        subprocess.run(
            [sys.executable, "-m", "pip", "show", "vulture"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print("✓ vulture is already installed")
    except subprocess.CalledProcessError:
        print("Installing vulture...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "vulture"],
            check=True,
        )
        print("✓ Installed vulture")


def remove_unused_imports(check_only=False):
    """Remove unused imports using autoflake."""
    print("Removing unused imports...")

    # Build the command
    cmd = [
        sys.executable,
        "-m",
        "autoflake",
        "--remove-all-unused-imports",
        "--recursive",
    ]

    if not check_only:
        cmd.append("--in-place")

    cmd.extend(["pyprocessor", "tests", "scripts"])

    # Run autoflake
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"✗ Error removing unused imports: {result.stderr}")
        return False

    if check_only:
        if result.stdout:
            print("Found unused imports that would be removed:")
            print(result.stdout)
            return False
        else:
            print("✓ No unused imports found")
            return True
    else:
        print("✓ Removed unused imports")
        return True


def comment_unused_variables(check_only=False):
    """Identify and comment out unused variables using vulture.

    Args:
        check_only: If True, only check for unused variables without modifying files

    Returns:
        bool: True if successful, False otherwise
    """
    print("Identifying unused variables...")

    # Run vulture to find unused variables
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "vulture",
            "pyprocessor",
            "tests",
            "scripts",
            "--min-confidence",
            "90",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0 and not result.stdout:
        print(f"✗ Error identifying unused variables: {result.stderr}")
        return False

    # Parse vulture output to find unused variables
    unused_vars = []
    for line in result.stdout.splitlines():
        # Look for unused variable patterns
        match = re.search(r"(.+?):(\d+): unused variable \'(.+?)\'", line)
        if match:
            file_path, line_num, var_name = match.groups()
            unused_vars.append((file_path, int(line_num), var_name))

    if not unused_vars:
        print("✓ No unused variables found")
        return True

    if check_only:
        print(f"Found {len(unused_vars)} unused variables that would be commented:")
        for file_path, line_num, var_name in unused_vars:
            print(f"  {file_path}:{line_num}: {var_name}")
        return False

    # Comment out unused variables
    files_modified = set()
    for file_path, line_num, var_name in unused_vars:
        try:
            with open(file_path, "r") as f:
                lines = f.readlines()

            # Only modify the line if it's within range
            if 0 <= line_num - 1 < len(lines):
                line = lines[line_num - 1]

                # Skip function parameters to avoid breaking function signatures
                if re.search(
                    r"^\s*def\s+.*?\(.*?" + re.escape(var_name) + r".*?\):", line
                ):
                    continue

                # Check if the variable is part of an assignment
                if re.search(rf"\b{var_name}\b\s*=", line):
                    # Don't comment out class attributes or function parameters
                    if re.search(r"(self|cls)\." + re.escape(var_name), line):
                        continue

                    # Comment out the entire line instead of just the variable
                    modified_line = f"# {line.rstrip()} # Unused variable\n"
                    lines[line_num - 1] = modified_line
                    files_modified.add(file_path)

            # Write the modified content back to the file
            with open(file_path, "w") as f:
                f.writelines(lines)

        except Exception as e:
            print(f"✗ Error modifying {file_path}: {str(e)}")

    if files_modified:
        print(f"✓ Commented out unused variables in {len(files_modified)} files")
    else:
        print("No files were modified")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Clean code by removing unused imports and commenting unused variables"
    )
    parser.add_argument(
        "--imports-only", action="store_true", help="Only remove unused imports"
    )
    parser.add_argument(
        "--variables-only", action="store_true", help="Only comment unused variables"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check for unused imports and variables without making changes",
    )

    args = parser.parse_args()

    # Install dependencies
    install_dependencies()

    success = True

    # Remove unused imports
    if not args.variables_only:
        if not remove_unused_imports(args.check):
            success = False

    # Comment unused variables
    if not args.imports_only:
        if not comment_unused_variables(args.check):
            success = False

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
