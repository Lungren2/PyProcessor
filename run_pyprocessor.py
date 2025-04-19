#!/usr/bin/env python3
"""
Cross-platform launcher script for PyProcessor.

This script can be used to launch PyProcessor on any platform (Windows, macOS, Linux).
It will detect if PyProcessor is installed as a package or if it's being run from source.
"""

import os
import sys
import platform
import subprocess
from pathlib import Path


def find_executable():
    """Find the PyProcessor executable."""
    # Check if running from source
    if os.path.exists("pyprocessor"):
        print("Running PyProcessor from source...")
        return [sys.executable, "-m", "pyprocessor"]
    
    # Check if running from installed package
    try:
        import pyprocessor
        print(f"Running PyProcessor package version {pyprocessor.__version__}...")
        return [sys.executable, "-m", "pyprocessor"]
    except ImportError:
        pass
    
    # Check for executable in dist directory
    system = platform.system().lower()
    exe_ext = ".exe" if system == "windows" else ""
    
    executable_path = Path("dist/PyProcessor/PyProcessor" + exe_ext)
    if executable_path.exists():
        print(f"Running PyProcessor executable from {executable_path}...")
        return [str(executable_path)]
    
    # Check for macOS app bundle
    if system == "darwin":
        app_path = Path("dist/PyProcessor.app")
        if app_path.exists():
            print(f"Running PyProcessor app bundle from {app_path}...")
            return ["open", str(app_path)]
    
    print("Error: Could not find PyProcessor executable.")
    print("Please make sure PyProcessor is installed or built correctly.")
    sys.exit(1)


def main():
    """Main function to launch PyProcessor."""
    # Find the executable
    cmd = find_executable()
    
    # Pass any command line arguments
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])
    
    # Launch PyProcessor
    try:
        print(f"Launching PyProcessor: {' '.join(cmd)}")
        subprocess.run(cmd)
    except Exception as e:
        print(f"Error launching PyProcessor: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
