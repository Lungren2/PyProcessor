#!/usr/bin/env python
"""
Script to install dependencies required for performance testing.
"""
import subprocess
import sys

def install_dependencies():
    """Install dependencies required for performance testing."""
    dependencies = [
        "psutil",
        "pytest",
        "pytest-cov"
    ]
    
    print("Installing performance testing dependencies...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + dependencies)
        print("Dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return False

if __name__ == "__main__":
    install_dependencies()
