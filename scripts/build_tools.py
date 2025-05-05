#!/usr/bin/env python3
"""
Unified build tools for PyProcessor.

This script provides a comprehensive set of build tools for PyProcessor:

Commands:
    ffmpeg      - Download and extract FFmpeg binaries
    build       - Build the PyProcessor executable
    package     - Package the PyProcessor executable for distribution

Usage:
    python scripts/build_tools.py ffmpeg
    python scripts/build_tools.py build [--skip-ffmpeg]
    python scripts/build_tools.py package [--skip-build] [--platform PLATFORM]

Options:
    build:
        --skip-ffmpeg      Skip downloading FFmpeg (use if already downloaded)

    package:
        --skip-build       Skip building the executable (use existing build)
        --platform         Target platform (windows, macos, linux, all)
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pyprocessor.utils.logging.log_manager import get_logger

# Import the FFmpegManager and log manager
from pyprocessor.utils.media.ffmpeg_manager import FFmpegManager

# Import path utilities if available
try:
    from pyprocessor.utils.file_system.path_manager import (
        copy_file,
        ensure_dir_exists,
        file_exists,
    )
except ImportError:
    # If the module is not installed yet, define simple versions
    def ensure_dir_exists(path):
        """Ensure a directory exists, creating it if necessary."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def file_exists(path):
        """Check if a file exists."""
        return Path(path).exists() and Path(path).is_file()

    def copy_file(src, dst):
        """Copy a file from source to destination."""
        return Path(shutil.copy2(src, dst))

    def normalize_path(path):
        """Normalize a path string to use the correct path separators."""
        return Path(path)


#
# FFmpeg Functions
#

# Get the logger
logger = get_logger(level="INFO")


# Create a logger function for the FFmpegManager
def logger_func(level, message):
    if level == "info":
        logger.info(message)
    elif level == "debug":
        logger.debug(message)
    elif level == "warning":
        logger.warning(message)
    elif level == "error":
        logger.error(message)


def download_ffmpeg():
    """Download and extract FFmpeg binaries for packaging."""
    print(
        f"Downloading FFmpeg binaries for {platform.system()} ({platform.machine()})..."
    )

    # Create directories if they don't exist
    temp_dir = ensure_dir_exists("ffmpeg_temp")
    bin_dir = ensure_dir_exists(os.path.join(temp_dir, "bin"))

    # Create an instance of FFmpegManager with our logger function
    ffmpeg_manager = FFmpegManager(logger_func)

    # Use the FFmpegManager to download FFmpeg
    success = ffmpeg_manager.download_ffmpeg(bin_dir)

    if success:
        print(
            "FFmpeg preparation complete. You can now run the build script to create the executable."
        )

    return success


#
# Build Functions
#


def check_pyinstaller():
    """Check if PyInstaller is installed."""
    try:
        # Check if PyInstaller is installed without importing it
        subprocess.run(
            [sys.executable, "-c", "import PyInstaller"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        logger.info("PyInstaller is installed.")
        return True
    except subprocess.CalledProcessError:
        logger.warning("PyInstaller is not installed.")
        return False


def install_pyinstaller():
    """Install PyInstaller using pip."""
    logger.info("Installing PyInstaller...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "PyInstaller"], check=True
        )
        logger.info("PyInstaller installed successfully.")
        return True
    except subprocess.CalledProcessError:
        logger.error("Failed to install PyInstaller.")
        return False


def create_spec_file():
    """Create a PyInstaller spec file for the current platform."""
    system = platform.system().lower()
    spec_file = Path("pyprocessor.spec")

    if file_exists(spec_file):
        logger.info("PyInstaller spec file already exists.")
        return True

    logger.info("Creating PyInstaller spec file...")

    # Common spec file content
    spec_content = """# -*- mode: python ; coding: utf-8 -*-

import sys
import os
import platform
from pathlib import Path

block_cipher = None

# Define the base directory
base_dir = Path.cwd().absolute()

# Define paths for data files
profiles_dir = base_dir / 'pyprocessor' / 'profiles'
logs_dir = base_dir / 'pyprocessor' / 'logs'

# Create directories if they don't exist
profiles_dir.mkdir(parents=True, exist_ok=True)
logs_dir.mkdir(parents=True, exist_ok=True)

# Find the FFmpeg directory
ffmpeg_dir = base_dir / 'ffmpeg_temp' / 'bin'
if not ffmpeg_dir.exists():
    raise FileNotFoundError("FFmpeg binaries not found. Please run download_ffmpeg.py first.")

# Platform-specific settings
system = platform.system().lower()
exe_ext = '.exe' if system == 'windows' else ''

# Define data files to include
added_files = [
    # Include profiles directory
    (str(profiles_dir), 'pyprocessor/profiles'),
    # Include logs directory
    (str(logs_dir), 'pyprocessor/logs'),
    # Include FFmpeg binaries
    (str(ffmpeg_dir / f'ffmpeg{exe_ext}'), f'ffmpeg/ffmpeg{exe_ext}'),
    (str(ffmpeg_dir / f'ffprobe{exe_ext}'), f'ffmpeg/ffprobe{exe_ext}'),
    ('ffmpeg_temp/README.txt', 'ffmpeg/README.txt'),
]

a = Analysis(
    ['pyprocessor/__main__.py'],  # Entry point
    pathex=[base_dir],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'tqdm',
        'multiprocessing',
        'multiprocessing.pool',
        'multiprocessing.managers',
        'multiprocessing.Queue',
        'multiprocessing.Manager',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PyProcessor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Set to True for CLI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PyProcessor',
)
"""

    # Platform-specific additions
    if system == "darwin":  # macOS
        spec_content += """
# macOS specific: Create a .app bundle
app = BUNDLE(
    coll,
    name='PyProcessor.app',
    icon=None,
    bundle_identifier='com.lungren2.pyprocessor',
    info_plist={
        'CFBundleShortVersionString': '0.1.0',
        'CFBundleVersion': '0.1.0',
        'NSHighResolutionCapable': 'True',
        'LSBackgroundOnly': 'False',
    },
)
"""

    try:
        with open(spec_file, "w") as f:
            f.write(spec_content)
        logger.info("Created PyInstaller spec file.")
        return True
    except Exception as e:
        logger.error(f"Failed to create spec file: {e}")
        return False


def build_executable(skip_ffmpeg=False):
    """Build the PyProcessor executable."""
    # Print platform information
    system = platform.system()
    machine = platform.machine()
    logger.info(f"Building PyProcessor for {system} {machine}")

    # Check for PyInstaller
    if not check_pyinstaller():
        if not install_pyinstaller():
            logger.error("Please install PyInstaller manually: pip install pyinstaller")
            return False

    # Download FFmpeg if not skipping
    if not skip_ffmpeg:
        if not download_ffmpeg():
            logger.error(
                "Failed to download FFmpeg. Please try again or download manually."
            )
            return False

    # Create spec file if it doesn't exist
    if not create_spec_file():
        return False

    logger.info("Building executable with PyInstaller...")
    try:
        # Run PyInstaller
        subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--clean", "pyprocessor.spec"],
            check=True,
        )
        logger.info("PyInstaller build completed successfully.")

        # Show output location
        dist_path = Path("dist/PyProcessor").absolute()
        if dist_path.exists():
            logger.info(f"Executable created at: {dist_path}")

            # Platform-specific instructions
            if system == "Windows":
                logger.info(f"To run the application: {dist_path}\\PyProcessor.exe")
            elif system == "Darwin":  # macOS
                app_path = Path("dist/PyProcessor.app").absolute()
                if app_path.exists():
                    logger.info(f"Application bundle created at: {app_path}")
                    logger.info(f"To run the application: open {app_path}")
                else:
                    logger.info(f"To run the application: {dist_path}/PyProcessor")
            else:  # Linux
                logger.info(f"To run the application: {dist_path}/PyProcessor")

        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"PyInstaller build failed: {e}")
        return False


#
# Package Functions
#


def find_nsis():
    """Find the NSIS executable."""
    if platform.system() != "Windows":
        return None

    try:
        # Try to find NSIS in the registry
        import winreg

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\NSIS") as key:
            nsis_path = winreg.QueryValueEx(key, "")[0]
            makensis_path = Path(nsis_path) / "makensis.exe"

            if file_exists(makensis_path):
                return makensis_path
    except:
        pass

    # Try common installation paths
    common_paths = [
        r"C:\Program Files\NSIS\makensis.exe",
        r"C:\Program Files (x86)\NSIS\makensis.exe",
    ]

    for path in common_paths:
        if file_exists(path):
            return path

    return None


def create_license_file():
    """Create a license file if it doesn't exist."""
    license_path = Path("license.txt")

    if file_exists(license_path):
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

    # Check if installer script exists
    installer_script = Path("installer.nsi")
    if not installer_script.exists():
        print("✗ NSIS installer script not found. Please create installer.nsi first.")
        return False

    try:
        # Run NSIS
        subprocess.run([nsis_path, str(installer_script)], check=True)

        # Check if installer was created
        installer_path = Path("PyProcessorInstaller.exe")
        if file_exists(installer_path):
            print(f"✓ Created Windows installer: {installer_path.absolute()}")

            # Create packages directory
            packages_dir = ensure_dir_exists("packages")

            # Copy installer to packages directory
            target_path = packages_dir / f"PyProcessor-{get_version()}-setup.exe"
            copy_file(installer_path, target_path)
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
        if not file_exists(app_path):
            print("✗ App bundle not found. Please build the executable first.")
            return False

        # Create packages directory
        packages_dir = ensure_dir_exists("packages")

        # Create DMG file
        dmg_path = packages_dir / f"PyProcessor-{get_version()}.dmg"

        # Use hdiutil to create DMG
        subprocess.run(
            [
                "hdiutil",
                "create",
                "-volname",
                "PyProcessor",
                "-srcfolder",
                str(app_path),
                "-ov",
                "-format",
                "UDZO",
                str(dmg_path),
            ],
            check=True,
        )

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
        if not file_exists(executable_path):
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
        subprocess.run(
            [
                "fpm",
                "-s",
                "dir",
                "-t",
                "deb",
                "-n",
                "pyprocessor",
                "-v",
                get_version(),
                "--description",
                "Cross-platform media processing engine",
                "--url",
                "https://github.com/Lungren2/PyProcessor",
                "--license",
                "MIT",
                "--vendor",
                "Lungren2",
                "--architecture",
                "amd64",
                "--depends",
                "ffmpeg",
                "-C",
                "dist/PyProcessor",
                "--prefix",
                "/opt/pyprocessor",
                ".",
            ],
            check=True,
        )

        # Create RPM package
        rpm_path = packages_dir / f"pyprocessor-{get_version()}.x86_64.rpm"
        subprocess.run(
            [
                "fpm",
                "-s",
                "dir",
                "-t",
                "rpm",
                "-n",
                "pyprocessor",
                "-v",
                get_version(),
                "--description",
                "Cross-platform media processing engine",
                "--url",
                "https://github.com/Lungren2/PyProcessor",
                "--license",
                "MIT",
                "--vendor",
                "Lungren2",
                "--architecture",
                "x86_64",
                "--depends",
                "ffmpeg",
                "-C",
                "dist/PyProcessor",
                "--prefix",
                "/opt/pyprocessor",
                ".",
            ],
            check=True,
        )

        print(f"✓ Created Linux packages: {deb_path} and {rpm_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to create Linux packages: {e}")
        return False
    except Exception as e:
        print(f"✗ Error creating Linux packages: {e}")
        return False


def package_executable(skip_build=False, target_platform=None):
    """Package the PyProcessor executable for distribution."""
    # Print platform information
    system = platform.system()
    machine = platform.machine()
    print(f"Packaging PyProcessor v{get_version()} on {system} {machine}")

    # Create packages directory
    ensure_dir_exists("packages")

    # Build executable if not skipped
    if not skip_build:
        if not build_executable(skip_ffmpeg=True):  # Skip FFmpeg download during build
            print("Failed to build executable. Please check the errors and try again.")
            return False

    # Determine target platform if not specified
    if not target_platform:
        target_platform = system.lower()
        if target_platform == "darwin":
            target_platform = "macos"

    # Package for the specified platform
    if target_platform == "all":
        # Package for all platforms
        if system == "Windows":
            create_windows_installer()
        elif system == "Darwin":
            create_macos_package()
        elif system == "Linux":
            create_linux_packages()

        print("\nNote: You can only create packages for the current platform.")
        print(
            "To create packages for all platforms, you need to run this script on each platform."
        )
    elif target_platform == "windows":
        if system != "Windows":
            print("Windows packaging can only be done on Windows")
            return False
        if not create_windows_installer():
            return False
    elif target_platform == "macos":
        if system != "Darwin":
            print("macOS packaging can only be done on macOS")
            return False
        if not create_macos_package():
            return False
    elif target_platform == "linux":
        if system != "Linux":
            print("Linux packaging can only be done on Linux")
            return False
        if not create_linux_packages():
            return False

    print("\n✓ Packaging completed successfully!")
    return True


#
# Main Function
#


def main():
    """Main function to parse arguments and run the appropriate command."""
    parser = argparse.ArgumentParser(description="PyProcessor Build Tools")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # FFmpeg command
    subparsers.add_parser("ffmpeg", help="Download and extract FFmpeg binaries")

    # Build command
    build_parser = subparsers.add_parser(
        "build", help="Build the PyProcessor executable"
    )
    build_parser.add_argument(
        "--skip-ffmpeg", action="store_true", help="Skip downloading FFmpeg"
    )

    # Package command
    package_parser = subparsers.add_parser(
        "package", help="Package the PyProcessor executable"
    )
    package_parser.add_argument(
        "--skip-build", action="store_true", help="Skip building the executable"
    )
    package_parser.add_argument(
        "--platform",
        choices=["windows", "macos", "linux", "all"],
        help="Target platform for packaging",
    )

    args = parser.parse_args()

    # Run the appropriate command
    if args.command == "ffmpeg":
        success = download_ffmpeg()
    elif args.command == "build":
        success = build_executable(args.skip_ffmpeg)
    elif args.command == "package":
        success = package_executable(args.skip_build, args.platform)
    else:
        parser.print_help()
        return True

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
