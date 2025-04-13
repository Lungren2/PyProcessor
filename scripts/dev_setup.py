#!/usr/bin/env python
"""
Development environment setup script for PyProcessor.

This script:
1. Creates a virtual environment
2. Installs development dependencies
3. Downloads FFmpeg binaries
4. Sets up pre-commit hooks (optional)
5. Creates necessary directories

Usage:
    python scripts/dev_setup.py [--no-venv] [--no-ffmpeg] [--no-hooks]

Options:
    --no-venv     Skip virtual environment creation
    --no-ffmpeg   Skip FFmpeg download
    --no-hooks    Skip pre-commit hooks setup
"""

import os
import sys
import subprocess
import argparse
import platform
import venv

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


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


def install_dependencies(pip_path):
    """Install development dependencies."""
    if not pip_path:
        return False

    print("Installing development dependencies...")
    try:
        # Install regular dependencies
        subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
        print("✓ Installed project dependencies")

        # Install development dependencies
        dev_dependencies = [
            "pytest",
            "pytest-cov",
            "black",
            "flake8",
            "mypy",
            "pre-commit",
            "pyinstaller",
            "autoflake",
            "vulture",
            "isort",
        ]

        subprocess.run([pip_path, "install"] + dev_dependencies, check=True)
        print("✓ Installed development dependencies")

        # Install the package in development mode
        subprocess.run([pip_path, "install", "-e", "."], check=True)
        print("✓ Installed package in development mode")

        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install dependencies: {e}")
        return False


def download_ffmpeg():
    """Download FFmpeg binaries."""
    try:
        from scripts.download_ffmpeg import download_ffmpeg as dl_ffmpeg

        print("Downloading FFmpeg binaries...")
        success = dl_ffmpeg()

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
        "tests/unit",
        "tests/integration",
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)

        # Create .gitkeep files for empty directories
        gitkeep_path = os.path.join(directory, ".gitkeep")
        if not os.path.exists(gitkeep_path):
            with open(gitkeep_path, "w") as f:
                pass

    print("✓ Created necessary directories")
    return True


def main():
    """Main function to set up the development environment."""
    parser = argparse.ArgumentParser(
        description="Set up development environment for PyProcessor"
    )
    parser.add_argument(
        "--no-venv", action="store_true", help="Skip virtual environment creation"
    )
    parser.add_argument("--no-ffmpeg", action="store_true", help="Skip FFmpeg download")
    parser.add_argument(
        "--no-hooks", action="store_true", help="Skip pre-commit hooks setup"
    )
    args = parser.parse_args()

    # Create virtual environment
    pip_path = True
    if not args.no_venv:
        pip_path = create_virtual_environment()
        if not pip_path:
            print(
                "Failed to create virtual environment. Continuing with other setup steps..."
            )

    # Install dependencies
    if pip_path and pip_path is not True:
        if not install_dependencies(pip_path):
            print(
                "Failed to install dependencies. Continuing with other setup steps..."
            )

    # Download FFmpeg
    if not args.no_ffmpeg:
        if not download_ffmpeg():
            print("Failed to download FFmpeg. Continuing with other setup steps...")

    # Set up pre-commit hooks
    if not args.no_hooks and pip_path:
        if not setup_pre_commit_hooks():
            print(
                "Failed to set up pre-commit hooks. Continuing with other setup steps..."
            )

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


if __name__ == "__main__":
    main()
