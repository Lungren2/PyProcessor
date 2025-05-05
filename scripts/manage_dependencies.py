#!/usr/bin/env python3
"""
Cross-platform dependency management script for PyProcessor.

This script helps manage dependencies across different platforms:
1. Checks for required dependencies
2. Installs missing dependencies
3. Updates dependencies to the latest versions
4. Creates a virtual environment if needed
5. Validates compatibility of installed dependencies
6. Provides fallbacks for missing optional dependencies

Usage:
    python scripts/manage_dependencies.py [--check] [--install] [--update] [--venv] [--extras EXTRAS]

Options:
    --check         Check for missing dependencies
    --install       Install missing dependencies
    --update        Update dependencies to the latest versions
    --venv          Create a virtual environment
    --extras EXTRAS Install extra dependencies (dev, ffmpeg, all)
    --validate      Validate compatibility of installed dependencies
"""

import argparse
import os
import platform
import subprocess
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the dependency manager if available
try:
    from pyprocessor.utils.core.dependency_manager import (
        check_dependencies,
        check_for_updates,
    )

    DEPENDENCY_MANAGER_AVAILABLE = True
except ImportError:
    DEPENDENCY_MANAGER_AVAILABLE = False


def get_platform_requirements():
    """Get the appropriate requirements file for the current platform."""
    system = platform.system().lower()

    if system == "windows":
        return "requirements-windows.txt"
    elif system == "darwin":
        return "requirements-macos.txt"
    else:  # Linux and others
        return "requirements-linux.txt"


def check_dependencies(requirements_file):
    """Check for missing dependencies."""
    print(f"Checking dependencies from {requirements_file}...")

    try:
        # Get installed packages
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=freeze"],
            capture_output=True,
            text=True,
            check=True,
        )
        installed_packages = {
            line.split("==")[0].lower(): line.split("==")[1]
            for line in result.stdout.splitlines()
            if "==" in line
        }

        # Read requirements file
        with open(requirements_file, "r") as f:
            requirements = [
                line.strip()
                for line in f.readlines()
                if line.strip() and not line.strip().startswith("#") and ";" not in line
            ]

        # Check for missing dependencies
        missing_dependencies = []
        for req in requirements:
            package = req.split(">=")[0].split("==")[0].split("<")[0].strip().lower()
            if package not in installed_packages:
                missing_dependencies.append(req)

        if missing_dependencies:
            print(f"Missing dependencies: {', '.join(missing_dependencies)}")
            return missing_dependencies
        else:
            print("All dependencies are installed.")
            return []

    except Exception as e:
        print(f"Error checking dependencies: {e}")
        return []


def install_dependencies(requirements_file, extras=None):
    """Install dependencies from the requirements file."""
    print(f"Installing dependencies from {requirements_file}...")

    try:
        # Install base requirements
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", requirements_file],
            check=True,
        )
        print(f"✓ Installed dependencies from {requirements_file}")

        # Install extras if specified
        if extras:
            if extras == "dev" or extras == "all":
                print("Installing development dependencies...")
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", ".[dev]"],
                    check=True,
                )
                print("✓ Installed development dependencies")

            if extras == "ffmpeg" or extras == "all":
                print("Installing FFmpeg dependencies...")
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", ".[ffmpeg]"],
                    check=True,
                )
                print("✓ Installed FFmpeg dependencies")

        return True
    except Exception as e:
        print(f"Error installing dependencies: {e}")
        return False


def update_dependencies(requirements_file, extras=None):
    """Update dependencies to the latest versions."""
    print(f"Updating dependencies from {requirements_file}...")

    try:
        # Update base requirements
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-r",
                requirements_file,
                "--upgrade",
            ],
            check=True,
        )
        print(f"✓ Updated dependencies from {requirements_file}")

        # Update extras if specified
        if extras:
            if extras == "dev" or extras == "all":
                print("Updating development dependencies...")
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", ".[dev]", "--upgrade"],
                    check=True,
                )
                print("✓ Updated development dependencies")

            if extras == "ffmpeg" or extras == "all":
                print("Updating FFmpeg dependencies...")
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", ".[ffmpeg]", "--upgrade"],
                    check=True,
                )
                print("✓ Updated FFmpeg dependencies")

        return True
    except Exception as e:
        print(f"Error updating dependencies: {e}")
        return False


def create_virtual_environment():
    """Create a virtual environment."""
    print("Creating virtual environment...")

    # Check if venv module is available
    try:
        import venv  # noqa: F401 - imported but unused, needed for check
    except ImportError:
        print("Error: venv module not available. Please install Python 3.6 or later.")
        return False

    # Create venv directory
    venv_dir = "venv"
    if os.path.exists(venv_dir):
        print(f"Virtual environment already exists at {venv_dir}")
        return True

    try:
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
        print(f"Created virtual environment at {venv_dir}")

        # Get the path to pip executable
        system = platform.system().lower()
        if system == "windows":
            pip_path = os.path.abspath(os.path.join(venv_dir, "Scripts", "pip.exe"))
        else:
            pip_path = os.path.abspath(os.path.join(venv_dir, "bin", "pip"))

        # Upgrade pip
        subprocess.run([pip_path, "install", "--upgrade", "pip"], check=True)
        print("Upgraded pip to the latest version")

        # Print activation instructions
        if system == "windows":
            print("\nTo activate the virtual environment, run:")
            print(f"{venv_dir}\\Scripts\\activate.bat")
        else:
            print("\nTo activate the virtual environment, run:")
            print(f"source {venv_dir}/bin/activate")

        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating virtual environment: {e}")
        return False


def validate_dependencies():
    """Validate compatibility of installed dependencies."""
    if not DEPENDENCY_MANAGER_AVAILABLE:
        print("Dependency manager not available. Cannot validate dependencies.")
        return True

    print("Validating dependencies...")
    errors, warnings = check_dependencies()

    if errors:
        print("\nDependency errors:")
        for error in errors:
            print(f"  ✗ {error}")

    if warnings:
        print("\nDependency warnings:")
        for warning in warnings:
            print(f"  ! {warning}")

    if not errors and not warnings:
        print("All dependencies are compatible.")

    return len(errors) == 0


def check_for_dependency_updates():
    """Check for available updates to dependencies."""
    if not DEPENDENCY_MANAGER_AVAILABLE:
        print("Dependency manager not available. Cannot check for updates.")
        return {}

    print("Checking for dependency updates...")
    updates = check_for_updates()

    if updates:
        print("\nUpdates available:")
        for package, (current, latest) in updates.items():
            print(f"  {package}: {current} → {latest}")
    else:
        print("All dependencies are up to date.")

    return updates


def main():
    """Main function to run the dependency management process."""
    parser = argparse.ArgumentParser(description="Manage dependencies for PyProcessor")
    parser.add_argument(
        "--check", action="store_true", help="Check for missing dependencies"
    )
    parser.add_argument(
        "--install", action="store_true", help="Install missing dependencies"
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update dependencies to the latest versions",
    )
    parser.add_argument(
        "--venv", action="store_true", help="Create a virtual environment"
    )
    parser.add_argument(
        "--extras",
        choices=["dev", "ffmpeg", "all"],
        help="Install extra dependencies (dev, ffmpeg, all)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate compatibility of installed dependencies",
    )
    args = parser.parse_args()

    # If no arguments are provided, show help
    if not (args.check or args.install or args.update or args.venv or args.validate):
        parser.print_help()
        return True

    # Get the appropriate requirements file
    requirements_file = get_platform_requirements()

    # Create virtual environment if requested
    if args.venv:
        if not create_virtual_environment():
            return False

    # Check for missing dependencies
    if args.check:
        missing_dependencies = check_dependencies(requirements_file)
        if missing_dependencies and args.install:
            print("Installing missing dependencies...")
            if not install_dependencies(requirements_file, args.extras):
                return False

    # Install dependencies if requested
    elif args.install:
        if not install_dependencies(requirements_file, args.extras):
            return False

    # Update dependencies if requested
    if args.update:
        if not update_dependencies(requirements_file, args.extras):
            return False

    # Validate dependencies if requested
    if args.validate:
        if not validate_dependencies():
            print("\nWarning: Some dependencies have compatibility issues.")
            print("You may want to run with --update to fix these issues.")

    print("\n✓ Dependency management completed successfully!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
