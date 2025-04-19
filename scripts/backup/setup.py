#!/usr/bin/env python3
"""
Cross-platform setup script for PyProcessor.

This script sets up the development environment for PyProcessor on any platform:
1. Creates a virtual environment (if requested)
2. Installs dependencies
3. Downloads FFmpeg binaries
4. Creates necessary directories

Usage:
    python scripts/setup.py [--no-venv] [--no-ffmpeg]

Options:
    --no-venv       Skip virtual environment creation
    --no-ffmpeg     Skip FFmpeg download
"""

import os
import sys
import platform
import subprocess
import argparse
import shutil
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import path utilities
try:
    from pyprocessor.utils.path_utils import ensure_dir_exists
except ImportError:
    # If the module is not installed yet, define a simple version
    def ensure_dir_exists(path):
        """Ensure a directory exists, creating it if necessary."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path


def create_virtual_environment():
    """Create a virtual environment."""
    print("Creating virtual environment...")
    
    # Check if venv module is available
    try:
        import venv
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
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating virtual environment: {e}")
        return False


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


def install_dependencies():
    """Install dependencies."""
    print("Installing dependencies...")
    
    pip_path = get_pip_path()
    
    try:
        # Install regular dependencies
        subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
        print("✓ Installed project dependencies")
        
        # Install development dependencies
        dev_dependencies = [
            "pytest",
            "black",
            "flake8",
            "pyinstaller",
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
    print("Downloading FFmpeg binaries...")
    
    try:
        # Import the download_ffmpeg function
        sys.path.insert(0, os.path.abspath("scripts"))
        from download_ffmpeg import download_ffmpeg as dl_ffmpeg
        
        success = dl_ffmpeg()
        if success:
            print("✓ Downloaded FFmpeg binaries")
            return True
        else:
            print("✗ Failed to download FFmpeg binaries")
            return False
    except Exception as e:
        print(f"✗ Error downloading FFmpeg: {e}")
        return False


def create_directories():
    """Create necessary directories."""
    print("Creating necessary directories...")
    
    try:
        # Create profiles directory
        ensure_dir_exists("pyprocessor/profiles")
        
        # Create logs directory
        ensure_dir_exists("pyprocessor/logs")
        
        # Create ffmpeg_temp directory
        ensure_dir_exists("ffmpeg_temp")
        
        print("✓ Created necessary directories")
        return True
    except Exception as e:
        print(f"✗ Error creating directories: {e}")
        return False


def main():
    """Main function to run the setup process."""
    parser = argparse.ArgumentParser(description="Set up PyProcessor development environment")
    parser.add_argument("--no-venv", action="store_true", help="Skip virtual environment creation")
    parser.add_argument("--no-ffmpeg", action="store_true", help="Skip FFmpeg download")
    args = parser.parse_args()
    
    # Print platform information
    system = platform.system()
    machine = platform.machine()
    python_version = platform.python_version()
    print(f"Setting up PyProcessor on {system} {machine} with Python {python_version}")
    
    # Create virtual environment if not skipped
    if not args.no_venv:
        if not create_virtual_environment():
            print("Failed to create virtual environment. Continuing with setup...")
    
    # Install dependencies
    if not install_dependencies():
        print("Failed to install dependencies. Please check the errors and try again.")
        return False
    
    # Create necessary directories
    if not create_directories():
        print("Failed to create necessary directories. Please check the errors and try again.")
        return False
    
    # Download FFmpeg if not skipped
    if not args.no_ffmpeg:
        if not download_ffmpeg():
            print("Failed to download FFmpeg. Please try again or download manually.")
            return False
    
    print("\n✓ Setup completed successfully!")
    
    # Print next steps
    print("\nNext steps:")
    if os.path.exists("venv"):
        if system == "windows":
            print("1. Activate the virtual environment: .\\venv\\Scripts\\activate")
        else:
            print("1. Activate the virtual environment: source venv/bin/activate")
    print("2. Run PyProcessor: python run_pyprocessor.py")
    print("3. Build PyProcessor: python scripts/build.py")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
