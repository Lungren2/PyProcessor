"""
Cross-platform build script for PyProcessor.

This script automates the build process for PyProcessor on Windows, macOS, and Linux:
1. Checks for required dependencies (PyInstaller)
2. Downloads and extracts FFmpeg binaries for the current platform
3. Creates the PyInstaller executable

Usage:
    python scripts/build.py [--skip-ffmpeg] [--skip-pyinstaller]

Options:
    --skip-ffmpeg      Skip downloading FFmpeg (use if already downloaded)
    --skip-pyinstaller Skip PyInstaller build (use if already built)
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
from pyprocessor.utils.path_utils import ensure_dir_exists


def check_pyinstaller():
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller
        print("✓ PyInstaller is installed.")
        return True
    except ImportError:
        print("✗ PyInstaller is not installed.")
        return False


def install_pyinstaller():
    """Install PyInstaller using pip."""
    print("Installing PyInstaller...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "PyInstaller"],
            check=True
        )
        print("✓ PyInstaller installed successfully.")
        return True
    except subprocess.CalledProcessError:
        print("✗ Failed to install PyInstaller.")
        return False


def download_ffmpeg():
    """Download and extract FFmpeg binaries."""
    try:
        # Import the download_ffmpeg function from the existing script
        from scripts.download_ffmpeg import download_ffmpeg as dl_ffmpeg

        print(f"Downloading and extracting FFmpeg for {platform.system()}...")
        success = dl_ffmpeg()

        if success:
            print("✓ FFmpeg downloaded and extracted successfully.")
            return True
        else:
            print("✗ Failed to download or extract FFmpeg.")
            return False
    except Exception as e:
        print(f"✗ Error downloading FFmpeg: {e}")
        return False


def create_spec_file():
    """Create a PyInstaller spec file for the current platform."""
    system = platform.system().lower()
    spec_file = Path("pyprocessor.spec")
    
    if spec_file.exists():
        print("✓ PyInstaller spec file already exists.")
        return True
    
    print("Creating PyInstaller spec file...")
    
    # Common spec file content
    spec_content = """# -*- mode: python ; coding: utf-8 -*-

import sys
import os
import platform
from pathlib import Path

block_cipher = None

# Define the base directory
base_dir = os.path.abspath(os.getcwd())

# Define paths for data files
profiles_dir = os.path.join(base_dir, 'pyprocessor', 'profiles')
logs_dir = os.path.join(base_dir, 'pyprocessor', 'logs')

# Create directories if they don't exist
Path(profiles_dir).mkdir(parents=True, exist_ok=True)
Path(logs_dir).mkdir(parents=True, exist_ok=True)

# Find the FFmpeg directory
ffmpeg_dir = os.path.join(base_dir, 'ffmpeg_temp', 'bin')
if not os.path.exists(ffmpeg_dir):
    raise FileNotFoundError("FFmpeg binaries not found. Please run download_ffmpeg.py first.")

# Platform-specific settings
system = platform.system().lower()
exe_ext = '.exe' if system == 'windows' else ''

# Define data files to include
added_files = [
    # Include profiles directory
    (profiles_dir, 'pyprocessor/profiles'),
    # Include logs directory
    (logs_dir, 'pyprocessor/logs'),
    # Include FFmpeg binaries
    (os.path.join(ffmpeg_dir, f'ffmpeg{exe_ext}'), f'ffmpeg/ffmpeg{exe_ext}'),
    (os.path.join(ffmpeg_dir, f'ffprobe{exe_ext}'), f'ffmpeg/ffprobe{exe_ext}'),
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
        print("✓ Created PyInstaller spec file.")
        return True
    except Exception as e:
        print(f"✗ Failed to create spec file: {e}")
        return False


def build_executable():
    """Build the executable using PyInstaller."""
    print("Building executable with PyInstaller...")
    
    # Create spec file if it doesn't exist
    if not create_spec_file():
        return False
    
    try:
        # Run PyInstaller
        subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--clean", "pyprocessor.spec"],
            check=True,
        )
        print("✓ PyInstaller build completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ PyInstaller build failed: {e}")
        return False


def main():
    """Main function to run the build process."""
    parser = argparse.ArgumentParser(description="Build PyProcessor for multiple platforms")
    parser.add_argument(
        "--skip-ffmpeg", action="store_true", help="Skip downloading FFmpeg"
    )
    parser.add_argument(
        "--skip-pyinstaller", action="store_true", help="Skip PyInstaller build"
    )
    args = parser.parse_args()

    # Print platform information
    system = platform.system()
    machine = platform.machine()
    print(f"Building PyProcessor for {system} {machine}")

    # Check for PyInstaller
    if not check_pyinstaller():
        if not install_pyinstaller():
            print("Please install PyInstaller manually: pip install pyinstaller")
            return False

    # Download FFmpeg if not skipping
    if not args.skip_ffmpeg:
        if not download_ffmpeg():
            print("Failed to download FFmpeg. Please try again or download manually.")
            return False

    # Build executable if not skipping
    if not args.skip_pyinstaller:
        if not build_executable():
            print("Failed to build executable. Please check the errors and try again.")
            return False

    print("\n✓ Build process completed successfully!")
    
    # Show output location
    dist_path = os.path.abspath("dist/PyProcessor")
    if os.path.exists(dist_path):
        print(f"\nExecutable created at: {dist_path}")
        
        # Platform-specific instructions
        if system == "Windows":
            print(f"\nTo run the application: {dist_path}\\PyProcessor.exe")
        elif system == "Darwin":  # macOS
            app_path = os.path.abspath("dist/PyProcessor.app")
            if os.path.exists(app_path):
                print(f"\nApplication bundle created at: {app_path}")
                print(f"To run the application: open {app_path}")
            else:
                print(f"\nTo run the application: {dist_path}/PyProcessor")
        else:  # Linux
            print(f"\nTo run the application: {dist_path}/PyProcessor")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
