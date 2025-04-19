#!/usr/bin/env python3
"""
Unified development tools for PyProcessor.

This script provides a comprehensive set of development tools for PyProcessor:

Commands:
    setup       - Set up the development environment
    clean       - Clean up temporary files and build artifacts
    lint        - Run linting tools (black, flake8, isort)
    deps        - Manage dependencies

Usage:
    python scripts/dev_tools.py setup [--no-venv] [--no-ffmpeg] [--no-hooks] [--platform PLATFORM]
    python scripts/dev_tools.py clean [--all] [--ffmpeg] [--logs]
    python scripts/dev_tools.py lint [--check]
    python scripts/dev_tools.py deps [--check] [--install] [--update] [--extras EXTRAS]

Options:
    setup:
        --no-venv     Skip virtual environment creation
        --no-ffmpeg   Skip FFmpeg download
        --no-hooks    Skip pre-commit hooks setup
        --platform    Target platform (windows, macos, linux, all)

    clean:
        --all         Remove all temporary files and build artifacts
        --ffmpeg      Remove FFmpeg temporary files
        --logs        Clean up log files

    lint:
        --check       Check code style without making changes

    deps:
        --check       Check for missing dependencies
        --install     Install missing dependencies
        --update      Update dependencies to the latest versions
        --extras      Install extra dependencies (dev, ffmpeg, all)
"""

import os
import sys
import subprocess
import argparse
import platform
import shutil
import venv
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import path utilities if available
try:
    from pyprocessor.utils.file_system.path_utils import ensure_dir_exists
except ImportError:
    # If the module is not installed yet, define a simple version
    def ensure_dir_exists(path):
        """Ensure a directory exists, creating it if necessary."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path


#
# Setup Environment Functions
#

def create_virtual_environment():
    """Create a virtual environment for development."""
    venv_dir = "venv"

    if os.path.exists(venv_dir):
        print(f"✓ Virtual environment already exists at {venv_dir}")
        return True

    print(f"Creating virtual environment at {venv_dir}...")
    try:
        venv.create(venv_dir, with_pip=True)
        print(f"✓ Virtual environment created at {venv_dir}")

        # Determine the pip executable path
        if platform.system() == "Windows":
            pip_path = os.path.join(venv_dir, "Scripts", "pip")
        else:
            pip_path = os.path.join(venv_dir, "bin", "pip")

        # Upgrade pip
        subprocess.run([pip_path, "install", "--upgrade", "pip"], check=True)
        print("✓ Pip upgraded to latest version")

        return pip_path
    except Exception as e:
        print(f"✗ Failed to create virtual environment: {e}")
        return False


def get_platform_requirements(target_platform=None):
    """Get the appropriate requirements file for the specified platform."""
    if target_platform:
        if target_platform == "windows":
            return "requirements-windows.txt"
        elif target_platform == "macos":
            return "requirements-macos.txt"
        elif target_platform == "linux":
            return "requirements-linux.txt"
        elif target_platform == "all":
            return "requirements.txt"

    # If no platform specified, use the current platform
    system = platform.system().lower()
    if system == "windows":
        return "requirements-windows.txt"
    elif system == "darwin":
        return "requirements-macos.txt"
    else:  # Linux and others
        return "requirements-linux.txt"


def get_pip_path():
    """Get the path to pip executable."""
    system = platform.system().lower()

    if os.path.exists("venv"):
        # Virtual environment exists
        if system == "windows":
            return os.path.abspath("venv/Scripts/pip.exe")
        else:
            return os.path.abspath("venv/bin/pip")
    else:
        # No virtual environment, use system pip
        return "pip"


def install_dependencies(pip_path=None, target_platform=None, extras=None):
    """Install development dependencies."""
    if pip_path is None:
        pip_path = get_pip_path()

    print("Installing dependencies...")
    try:
        # Get the appropriate requirements file
        requirements_file = get_platform_requirements(target_platform)

        # Install regular dependencies
        subprocess.run([pip_path, "install", "-r", requirements_file], check=True)
        print(f"✓ Installed project dependencies from {requirements_file}")

        # Install development dependencies
        dev_dependencies = [
            "black",
            "flake8",
            "mypy",
            "pre-commit",
            "pyinstaller",
            "autoflake",
            "vulture",
            "isort",
        ]

        if extras == "dev" or extras == "all":
            subprocess.run([pip_path, "install"] + dev_dependencies, check=True)
            print("✓ Installed development dependencies")

        # Install the package in development mode
        install_cmd = [pip_path, "install", "-e", "."]
        if extras:
            if extras == "all":
                install_cmd = [pip_path, "install", "-e", ".[dev,ffmpeg]"]
            else:
                install_cmd = [pip_path, "install", "-e", f".[{extras}]"]

        subprocess.run(install_cmd, check=True)
        print("✓ Installed package in development mode")

        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install dependencies: {e}")
        return False


def download_ffmpeg():
    """Download FFmpeg binaries."""
    try:
        # Import the FFmpegManager
        from pyprocessor.utils.media.ffmpeg_manager import FFmpegManager

        print("Downloading FFmpeg binaries...")

        # Create directories if they don't exist
        temp_dir = ensure_dir_exists("ffmpeg_temp")
        bin_dir = ensure_dir_exists(os.path.join(temp_dir, "bin"))

        # Create a simple logger function
        def logger_func(level, message):
            print(f"[{level.upper()}] {message}")

        # Create an instance of FFmpegManager with our logger function
        ffmpeg_manager = FFmpegManager(logger_func)

        # Use the FFmpegManager to download FFmpeg
        success = ffmpeg_manager.download_ffmpeg(bin_dir)

        if success:
            print("✓ FFmpeg downloaded and extracted successfully")
            return True
        else:
            print("✗ Failed to download FFmpeg")
            return False
    except Exception as e:
        print(f"✗ Error downloading FFmpeg: {e}")
        return False


def setup_pre_commit_hooks():
    """Set up pre-commit hooks."""
    if not os.path.exists(".git"):
        print("✗ Not a git repository. Skipping pre-commit hooks setup.")
        return False

    print("Setting up pre-commit hooks...")

    # Create pre-commit config if it doesn't exist
    pre_commit_config = ".pre-commit-config.yaml"
    if not os.path.exists(pre_commit_config):
        config_content = """repos:
-   repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
    -   id: trailing-whitespace
    -   id: end-of-file-fixer
    -   id: check-yaml
    -   id: check-added-large-files
    -   id: check-ast
    -   id: check-json
    -   id: check-merge-conflict
    -   id: detect-private-key

-   repo: https://github.com/psf/black
    rev: 24.2.0
    hooks:
    -   id: black
        language_version: python3

-   repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
    -   id: isort
        args: ["--profile", "black"]

-   repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
    -   id: flake8
        additional_dependencies: [flake8-docstrings]

-   repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
    -   id: mypy
        additional_dependencies: [types-requests]

-   repo: https://github.com/PyCQA/autoflake
    rev: v2.2.1
    hooks:
    -   id: autoflake
        args: [
            "--remove-all-unused-imports",
            "--remove-unused-variables",
            "--in-place",
            "--recursive"
        ]
"""
        try:
            with open(pre_commit_config, "w") as f:
                f.write(config_content)
            print(f"✓ Created {pre_commit_config}")
        except Exception as e:
            print(f"✗ Failed to create pre-commit config: {e}")
            return False

    try:
        # Install the pre-commit hooks
        subprocess.run(["pre-commit", "install"], check=True)
        print("✓ Pre-commit hooks installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install pre-commit hooks: {e}")
        return False
    except FileNotFoundError:
        print(
            "✗ pre-commit not found. Make sure it's installed in your virtual environment."
        )
        return False


def create_directories():
    """Create necessary directories for development."""
    directories = [
        "pyprocessor/logs",
        "pyprocessor/profiles",
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)

        # Create .gitkeep files for empty directories
        gitkeep_path = os.path.join(directory, ".gitkeep")
        if not os.path.exists(gitkeep_path):
            open(gitkeep_path, "w").close()

    print("✓ Created necessary directories")
    return True


def setup_environment(args):
    """Set up the development environment."""
    print(f"Setting up PyProcessor development environment on {platform.system()} {platform.machine()}")

    # Create virtual environment
    pip_path = True
    if not args.no_venv:
        pip_path = create_virtual_environment()
        if not pip_path:
            print("Failed to create virtual environment. Continuing with other setup steps...")

    # Install dependencies
    if pip_path and pip_path is not True:
        if not install_dependencies(pip_path, args.platform):
            print("Failed to install dependencies. Continuing with other setup steps...")

    # Download FFmpeg
    if not args.no_ffmpeg:
        if not download_ffmpeg():
            print("Failed to download FFmpeg. Continuing with other setup steps...")

    # Set up pre-commit hooks
    if not args.no_hooks and pip_path:
        if not setup_pre_commit_hooks():
            print("Failed to set up pre-commit hooks. Continuing with other setup steps...")

    # Create necessary directories
    create_directories()

    print("\n✓ Development environment setup completed!")

    # Print activation instructions
    if pip_path and pip_path is not True:
        if platform.system() == "Windows":
            print("\nTo activate the virtual environment, run:")
            print("    venv\\Scripts\\activate")
        else:
            print("\nTo activate the virtual environment, run:")
            print("    source venv/bin/activate")

    return True


#
# Cleanup Functions
#

def remove_pycache():
    """Remove __pycache__ directories and .pyc files."""
    print("Removing __pycache__ directories and .pyc files...")

    # Remove __pycache__ directories
    pycache_count = 0
    for root, dirs, files in os.walk("."):
        if "__pycache__" in dirs:
            pycache_path = os.path.join(root, "__pycache__")
            try:
                shutil.rmtree(pycache_path)
                pycache_count += 1
            except Exception as e:
                print(f"Error removing {pycache_path}: {e}")

    # Remove .pyc files
    pyc_count = 0
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".pyc"):
                pyc_path = os.path.join(root, file)
                try:
                    os.remove(pyc_path)
                    pyc_count += 1
                except Exception as e:
                    print(f"Error removing {pyc_path}: {e}")

    print(f"✓ Removed {pycache_count} __pycache__ directories and {pyc_count} .pyc files")
    return True


def remove_build_artifacts():
    """Remove build artifacts."""
    print("Removing build artifacts...")

    # Directories to remove
    build_dirs = ["build", "dist", "*.egg-info"]

    # Remove directories
    removed_count = 0
    for pattern in build_dirs:
        if "*" in pattern:
            # Handle wildcard patterns
            for item in Path(".").glob(pattern):
                if item.is_dir():
                    try:
                        shutil.rmtree(item)
                        print(f"Removed {item}")
                        removed_count += 1
                    except Exception as e:
                        print(f"Error removing {item}: {e}")
        else:
            # Handle exact directory names
            if os.path.exists(pattern) and os.path.isdir(pattern):
                try:
                    shutil.rmtree(pattern)
                    print(f"Removed {pattern}")
                    removed_count += 1
                except Exception as e:
                    print(f"Error removing {pattern}: {e}")

    print(f"✓ Removed {removed_count} build artifact directories")
    return True


def remove_ffmpeg_temp():
    """Remove FFmpeg temporary files."""
    print("Removing FFmpeg temporary files...")

    ffmpeg_temp = "ffmpeg_temp"
    if os.path.exists(ffmpeg_temp) and os.path.isdir(ffmpeg_temp):
        try:
            shutil.rmtree(ffmpeg_temp)
            print(f"✓ Removed {ffmpeg_temp} directory")
            return True
        except Exception as e:
            print(f"Error removing {ffmpeg_temp}: {e}")
            return False
    else:
        print(f"✓ No {ffmpeg_temp} directory found")
        return True


def clean_logs():
    """Clean up log files."""
    print("Cleaning up log files...")

    logs_dir = "pyprocessor/logs"
    if os.path.exists(logs_dir) and os.path.isdir(logs_dir):
        log_count = 0
        for item in os.listdir(logs_dir):
            if item != ".gitkeep":  # Preserve .gitkeep
                log_path = os.path.join(logs_dir, item)
                try:
                    if os.path.isfile(log_path):
                        os.remove(log_path)
                        log_count += 1
                except Exception as e:
                    print(f"Error removing {log_path}: {e}")

        print(f"✓ Removed {log_count} log files")
        return True
    else:
        print(f"✓ No {logs_dir} directory found")
        return True


def cleanup(args):
    """Clean up temporary files and build artifacts."""
    success = True

    # If no specific options are provided, just remove pycache and build artifacts
    if not (args.all or args.ffmpeg or args.logs):
        remove_pycache()
        remove_build_artifacts()
        return True

    # Otherwise, perform the requested cleanup operations
    if args.all or args.ffmpeg:
        if not remove_ffmpeg_temp():
            success = False

    if args.all:
        if not remove_pycache():
            success = False
        if not remove_build_artifacts():
            success = False

    if args.all or args.logs:
        if not clean_logs():
            success = False

    return success


#
# Linting Functions
#

def install_linting_tools():
    """Install linting tools if not already installed."""
    print("Checking for linting tools...")

    tools = ["black", "flake8", "isort", "autoflake", "vulture"]
    missing_tools = []

    for tool in tools:
        try:
            subprocess.run([sys.executable, "-m", tool, "--version"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing_tools.append(tool)

    if missing_tools:
        print(f"Installing missing linting tools: {', '.join(missing_tools)}")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install"] + missing_tools, check=True)
            print("✓ Installed linting tools")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install linting tools: {e}")
            return False
    else:
        print("✓ All linting tools are installed")
        return True


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

    cmd.extend(["pyprocessor", "scripts"])

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
    """Identify and comment out unused variables using vulture."""
    print("Checking for unused variables...")

    # Run vulture to find unused variables
    result = subprocess.run(
        [sys.executable, "-m", "vulture", "pyprocessor", "scripts"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0 and not result.stdout:
        print(f"✗ Error checking for unused variables: {result.stderr}")
        return False

    # Parse vulture output to find unused variables
    unused_vars = []
    for line in result.stdout.splitlines():
        if "unused variable" in line:
            parts = line.split(":")
            if len(parts) >= 3:
                file_path = parts[0]
                line_num = int(parts[1])
                var_name = parts[2].split("'")[1]
                unused_vars.append((file_path, line_num, var_name))

    if check_only:
        if unused_vars:
            print("Found unused variables that would be commented out:")
            for file_path, line_num, var_name in unused_vars:
                print(f"{file_path}:{line_num}: {var_name}")
            return False
        else:
            print("✓ No unused variables found")
            return True

    # Comment out unused variables
    if not unused_vars:
        print("✓ No unused variables found")
        return True

    modified_files = set()
    for file_path, line_num, var_name in unused_vars:
        try:
            with open(file_path, "r") as f:
                lines = f.readlines()

            if line_num <= len(lines):
                line = lines[line_num - 1]
                # Only comment out the variable if it's a simple assignment
                if re.match(r"^\s*" + var_name + r"\s*=", line):
                    lines[line_num - 1] = line.rstrip() + "  # Unused variable\n"
                    modified_files.add(file_path)

            with open(file_path, "w") as f:
                f.writelines(lines)
        except Exception as e:
            print(f"✗ Error modifying {file_path}: {e}")

    if modified_files:
        print(f"✓ Commented out unused variables in {len(modified_files)} files")
    else:
        print("✓ No variables were commented out")

    return True


def run_black(check_only=False):
    """Run black code formatter."""
    print("Running black code formatter...")

    cmd = [sys.executable, "-m", "black"]
    if check_only:
        cmd.append("--check")

    cmd.extend(["pyprocessor", "scripts"])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0 and check_only:
        print("✗ Code formatting issues found:")
        print(result.stdout)
        return False
    elif result.returncode != 0:
        print(f"✗ Error formatting code: {result.stderr}")
        return False
    else:
        print("✓ Code formatting completed")
        return True


def run_isort(check_only=False):
    """Run isort to sort imports."""
    print("Sorting imports with isort...")

    cmd = [sys.executable, "-m", "isort", "--profile", "black"]
    if check_only:
        cmd.append("--check")

    cmd.extend(["pyprocessor", "scripts"])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0 and check_only:
        print("✗ Import sorting issues found:")
        print(result.stdout)
        return False
    elif result.returncode != 0:
        print(f"✗ Error sorting imports: {result.stderr}")
        return False
    else:
        print("✓ Import sorting completed")
        return True


def run_flake8():
    """Run flake8 linter."""
    print("Running flake8 linter...")

    cmd = [sys.executable, "-m", "flake8", "pyprocessor", "scripts"]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("✗ Linting issues found:")
        print(result.stdout)
        return False
    else:
        print("✓ No linting issues found")
        return True


def lint_code(args):
    """Run linting tools on the codebase."""
    # Install linting tools if needed
    if not install_linting_tools():
        return False

    success = True

    # Run black
    if not run_black(args.check):
        success = False

    # Run isort
    if not run_isort(args.check):
        success = False

    # Run flake8 (check only)
    if not run_flake8():
        success = False

    # Remove unused imports
    if not remove_unused_imports(args.check):
        success = False

    # Comment unused variables
    if not comment_unused_variables(args.check):
        success = False

    return success


#
# Dependency Management Functions
#

def check_dependencies(extras=None):
    """Check for missing dependencies."""
    print("Checking for missing dependencies...")

    # Get the appropriate requirements file
    requirements_file = get_platform_requirements()

    # Check regular dependencies
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "check"],
            capture_output=True,
            text=True,
        )

        if "No broken requirements found" in result.stdout:
            print("✓ All dependencies are satisfied")
            return True
        else:
            print("✗ Dependency issues found:")
            print(result.stdout)
            return False
    except subprocess.CalledProcessError as e:
        print(f"✗ Error checking dependencies: {e}")
        return False


def update_dependencies(extras=None):
    """Update dependencies to the latest versions."""
    print("Updating dependencies to the latest versions...")

    pip_path = get_pip_path()

    # Get the appropriate requirements file
    requirements_file = get_platform_requirements()

    try:
        # Update regular dependencies
        subprocess.run([pip_path, "install", "--upgrade", "-r", requirements_file], check=True)
        print(f"✓ Updated project dependencies from {requirements_file}")

        # Update development dependencies if requested
        if extras == "dev" or extras == "all":
            dev_dependencies = [
                "black",
                "flake8",
                "mypy",
                "pre-commit",
                "pyinstaller",
                "autoflake",
                "vulture",
                "isort",
            ]
            subprocess.run([pip_path, "install", "--upgrade"] + dev_dependencies, check=True)
            print("✓ Updated development dependencies")

        # Update FFmpeg dependencies if requested
        if extras == "ffmpeg" or extras == "all":
            subprocess.run([pip_path, "install", "--upgrade", "ffmpeg-python"], check=True)
            print("✓ Updated FFmpeg dependencies")

        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to update dependencies: {e}")
        return False


def manage_dependencies(args):
    """Manage dependencies."""
    success = True

    # Check dependencies
    if args.check:
        if not check_dependencies(args.extras):
            success = False

    # Install dependencies
    if args.install:
        if not install_dependencies(extras=args.extras):
            success = False

    # Update dependencies
    if args.update:
        if not update_dependencies(args.extras):
            success = False

    return success


#
# Main Function
#

def main():
    """Main function to parse arguments and run the appropriate command."""
    parser = argparse.ArgumentParser(description="PyProcessor Development Tools")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Set up the development environment")
    setup_parser.add_argument("--no-venv", action="store_true", help="Skip virtual environment creation")
    setup_parser.add_argument("--no-ffmpeg", action="store_true", help="Skip FFmpeg download")
    setup_parser.add_argument("--no-hooks", action="store_true", help="Skip pre-commit hooks setup")
    setup_parser.add_argument(
        "--platform",
        choices=["windows", "macos", "linux", "all"],
        help="Target platform for dependencies"
    )

    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean up temporary files and build artifacts")
    clean_parser.add_argument("--all", action="store_true", help="Remove all temporary files and build artifacts")
    clean_parser.add_argument("--ffmpeg", action="store_true", help="Remove FFmpeg temporary files")
    clean_parser.add_argument("--logs", action="store_true", help="Clean up log files")

    # Lint command
    lint_parser = subparsers.add_parser("lint", help="Run linting tools")
    lint_parser.add_argument("--check", action="store_true", help="Check code style without making changes")

    # Dependencies command
    deps_parser = subparsers.add_parser("deps", help="Manage dependencies")
    deps_parser.add_argument("--check", action="store_true", help="Check for missing dependencies")
    deps_parser.add_argument("--install", action="store_true", help="Install missing dependencies")
    deps_parser.add_argument("--update", action="store_true", help="Update dependencies to the latest versions")
    deps_parser.add_argument(
        "--extras",
        choices=["dev", "ffmpeg", "all"],
        help="Extra dependencies to install or update"
    )

    args = parser.parse_args()

    # Run the appropriate command
    if args.command == "setup":
        success = setup_environment(args)
    elif args.command == "clean":
        success = cleanup(args)
    elif args.command == "lint":
        success = lint_code(args)
    elif args.command == "deps":
        success = manage_dependencies(args)
    else:
        parser.print_help()
        return True

    return success


if __name__ == "__main__":
    import re  # Import here for comment_unused_variables function
    success = main()
    sys.exit(0 if success else 1)
