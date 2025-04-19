#!/usr/bin/env python3
"""
Cross-platform packaging script for PyProcessor.

This script creates installation packages for different platforms:
1. Windows: Creates an NSIS installer
2. macOS: Creates a DMG file
3. Linux: Creates DEB and RPM packages

Usage:
    python scripts/package.py [--platform PLATFORM] [--skip-build]

Options:
    --platform PLATFORM    Target platform (windows, macos, linux, all)
    --skip-build           Skip building the executable (use existing build)
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


def build_executable():
    """Build the executable using the build script."""
    print("Building executable...")
    
    try:
        # Run the build script
        build_script = os.path.join("scripts", "build.py")
        subprocess.run([sys.executable, build_script], check=True)
        print("✓ Built executable successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to build executable: {e}")
        return False


def create_windows_installer():
    """Create a Windows installer using NSIS."""
    print("Creating Windows installer...")
    
    # Check if NSIS is installed
    nsis_path = find_nsis()
    if not nsis_path:
        print("✗ NSIS not found. Please install NSIS to create a Windows installer.")
        return False
    
    # Create license file if it doesn't exist
    if not create_license_file():
        return False
    
    try:
        # Run NSIS
        subprocess.run([nsis_path, "installer.nsi"], check=True)
        
        # Check if installer was created
        installer_path = Path("PyProcessorInstaller.exe")
        if installer_path.exists():
            print(f"✓ Created Windows installer: {installer_path.absolute()}")
            
            # Create packages directory
            packages_dir = ensure_dir_exists("packages")
            
            # Copy installer to packages directory
            target_path = packages_dir / f"PyProcessor-{get_version()}-setup.exe"
            shutil.copy2(installer_path, target_path)
            print(f"✓ Copied installer to: {target_path}")
            
            return True
        else:
            print("✗ Failed to create Windows installer")
            return False
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to create Windows installer: {e}")
        return False


def create_macos_package():
    """Create a macOS package (DMG file)."""
    print("Creating macOS package...")
    
    if platform.system() != "Darwin":
        print("✗ macOS packaging can only be done on macOS")
        return False
    
    try:
        # Check if the app bundle exists
        app_path = Path("dist/PyProcessor.app")
        if not app_path.exists():
            print("✗ App bundle not found. Please build the executable first.")
            return False
        
        # Create packages directory
        packages_dir = ensure_dir_exists("packages")
        
        # Create DMG file
        dmg_path = packages_dir / f"PyProcessor-{get_version()}.dmg"
        
        # Use hdiutil to create DMG
        subprocess.run([
            "hdiutil", "create",
            "-volname", "PyProcessor",
            "-srcfolder", str(app_path),
            "-ov", "-format", "UDZO",
            str(dmg_path)
        ], check=True)
        
        print(f"✓ Created macOS package: {dmg_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to create macOS package: {e}")
        return False
    except Exception as e:
        print(f"✗ Error creating macOS package: {e}")
        return False


def create_linux_packages():
    """Create Linux packages (DEB and RPM)."""
    print("Creating Linux packages...")
    
    if platform.system() != "Linux":
        print("✗ Linux packaging can only be done on Linux")
        return False
    
    try:
        # Check if the executable exists
        executable_path = Path("dist/PyProcessor/PyProcessor")
        if not executable_path.exists():
            print("✗ Executable not found. Please build the executable first.")
            return False
        
        # Create packages directory
        packages_dir = ensure_dir_exists("packages")
        
        # Check if fpm is installed
        if not shutil.which("fpm"):
            print("✗ fpm not found. Please install fpm to create Linux packages.")
            print("  You can install fpm with: gem install fpm")
            return False
        
        # Create DEB package
        deb_path = packages_dir / f"pyprocessor_{get_version()}_amd64.deb"
        subprocess.run([
            "fpm",
            "-s", "dir",
            "-t", "deb",
            "-n", "pyprocessor",
            "-v", get_version(),
            "--description", "Cross-platform media processing engine",
            "--url", "https://github.com/Lungren2/PyProcessor",
            "--license", "MIT",
            "--vendor", "Lungren2",
            "--architecture", "amd64",
            "--depends", "ffmpeg",
            "-C", "dist/PyProcessor",
            "--prefix", "/opt/pyprocessor",
            "."
        ], check=True)
        
        # Create RPM package
        rpm_path = packages_dir / f"pyprocessor-{get_version()}.x86_64.rpm"
        subprocess.run([
            "fpm",
            "-s", "dir",
            "-t", "rpm",
            "-n", "pyprocessor",
            "-v", get_version(),
            "--description", "Cross-platform media processing engine",
            "--url", "https://github.com/Lungren2/PyProcessor",
            "--license", "MIT",
            "--vendor", "Lungren2",
            "--architecture", "x86_64",
            "--depends", "ffmpeg",
            "-C", "dist/PyProcessor",
            "--prefix", "/opt/pyprocessor",
            "."
        ], check=True)
        
        print(f"✓ Created Linux packages: {deb_path} and {rpm_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to create Linux packages: {e}")
        return False
    except Exception as e:
        print(f"✗ Error creating Linux packages: {e}")
        return False


def find_nsis():
    """Find the NSIS executable."""
    if platform.system() != "Windows":
        return None
    
    try:
        # Try to find NSIS in the registry
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\NSIS") as key:
            nsis_path = winreg.QueryValueEx(key, "")[0]
            makensis_path = os.path.join(nsis_path, "makensis.exe")
            
            if os.path.exists(makensis_path):
                return makensis_path
    except:
        pass
    
    # Try common installation paths
    common_paths = [
        r"C:\Program Files\NSIS\makensis.exe",
        r"C:\Program Files (x86)\NSIS\makensis.exe",
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    return None


def create_license_file():
    """Create a license file if it doesn't exist."""
    license_path = Path("license.txt")
    
    if license_path.exists():
        return True
    
    print("Creating license file...")
    
    license_content = """PyProcessor License

Copyright (c) 2023-2024 Lungren2

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
    
    try:
        with open(license_path, "w") as f:
            f.write(license_content)
        print("✓ Created license file")
        return True
    except Exception as e:
        print(f"✗ Failed to create license file: {e}")
        return False


def get_version():
    """Get the version from setup.py."""
    try:
        with open("setup.py", "r") as f:
            for line in f:
                if "version=" in line:
                    # Extract version from version="x.y.z"
                    version = line.split('version="')[1].split('"')[0]
                    return version
    except:
        pass
    
    # Default version if not found
    return "0.1.0"


def main():
    """Main function to run the packaging process."""
    parser = argparse.ArgumentParser(description="Package PyProcessor for different platforms")
    parser.add_argument(
        "--platform",
        choices=["windows", "macos", "linux", "all"],
        default=platform.system().lower(),
        help="Target platform (windows, macos, linux, all)"
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip building the executable (use existing build)"
    )
    args = parser.parse_args()
    
    # Print platform information
    system = platform.system()
    machine = platform.machine()
    print(f"Packaging PyProcessor v{get_version()} on {system} {machine}")
    
    # Create packages directory
    ensure_dir_exists("packages")
    
    # Build executable if not skipped
    if not args.skip_build:
        if not build_executable():
            print("Failed to build executable. Please check the errors and try again.")
            return False
    
    # Package for the specified platform
    if args.platform == "all":
        # Package for all platforms
        if system == "Windows":
            create_windows_installer()
        elif system == "Darwin":
            create_macos_package()
        elif system == "Linux":
            create_linux_packages()
        
        print("\nNote: You can only create packages for the current platform.")
        print("To create packages for all platforms, you need to run this script on each platform.")
    elif args.platform == "windows":
        if system != "Windows":
            print("Windows packaging can only be done on Windows")
            return False
        if not create_windows_installer():
            return False
    elif args.platform == "macos":
        if system != "Darwin":
            print("macOS packaging can only be done on macOS")
            return False
        if not create_macos_package():
            return False
    elif args.platform == "linux":
        if system != "Linux":
            print("Linux packaging can only be done on Linux")
            return False
        if not create_linux_packages():
            return False
    
    print("\n✓ Packaging completed successfully!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
