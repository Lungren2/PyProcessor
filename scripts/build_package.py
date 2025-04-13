"""
Build and packaging script for PyProcessor.

This script automates the entire build and packaging process for PyProcessor:
1. Checks for required dependencies (PyInstaller, NSIS)
2. Downloads and extracts FFmpeg binaries
3. Creates the PyInstaller executable
4. Packages the executable using NSIS

Usage:
    python scripts/build_package.py [--skip-ffmpeg] [--skip-pyinstaller] [--skip-nsis]

Options:
    --skip-ffmpeg      Skip downloading FFmpeg (use if already downloaded)
    --skip-pyinstaller Skip PyInstaller build (use if already built)
    --skip-nsis        Skip NSIS packaging (use if only executable is needed)
"""

import os
import sys
import subprocess
import argparse
import platform
import winreg
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def check_pyinstaller():
    """Check if PyInstaller is installed."""
    try:
        print("✓ PyInstaller is installed.")
        return True
    except ImportError:
        print("✗ PyInstaller is not installed.")
        return False

def install_pyinstaller():
    """Install PyInstaller using pip."""
    print("Installing PyInstaller...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "PyInstaller"], check=True)
        print("✓ PyInstaller installed successfully.")
        return True
    except subprocess.CalledProcessError:
        print("✗ Failed to install PyInstaller.")
        return False

def check_nsis():
    """Check if NSIS is installed on Windows."""
    if platform.system() != "Windows":
        print("✗ NSIS check is only supported on Windows.")
        return False
    
    try:
        # Try to find NSIS in the registry
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\NSIS") as key:
            nsis_path = winreg.QueryValueEx(key, "")[0]
            makensis_path = os.path.join(nsis_path, "makensis.exe")
            
            if os.path.exists(makensis_path):
                print(f"✓ NSIS found at: {nsis_path}")
                return makensis_path
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"Error checking NSIS registry: {e}")
    
    # Try common installation paths
    common_paths = [
        r"C:\Program Files\NSIS\makensis.exe",
        r"C:\Program Files (x86)\NSIS\makensis.exe",
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            print(f"✓ NSIS found at: {os.path.dirname(path)}")
            return path
    
    print("✗ NSIS not found. Please install NSIS from https://nsis.sourceforge.io/Download")
    return False

def download_ffmpeg():
    """Download and extract FFmpeg binaries."""
    try:
        # Import the download_ffmpeg function from the existing script
        from scripts.download_ffmpeg import download_ffmpeg as dl_ffmpeg
        
        print("Downloading and extracting FFmpeg...")
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

def create_license_file():
    """Create a license file if it doesn't exist."""
    license_path = Path("license.txt")
    
    if license_path.exists():
        print("✓ License file already exists.")
        return True
    
    print("Creating a basic license file...")
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
        with open(license_path, 'w') as f:
            f.write(license_content)
        print("✓ Created license.txt file.")
        return True
    except Exception as e:
        print(f"✗ Failed to create license file: {e}")
        return False

def build_executable():
    """Build the executable using PyInstaller."""
    print("Building executable with PyInstaller...")
    
    # Check if spec file exists
    spec_file = Path("pyprocessor.spec")
    if not spec_file.exists():
        print("Creating PyInstaller spec file...")
        
        # Create a basic spec file
        spec_content = """# -*- mode: python ; coding: utf-8 -*-

import sys
import os
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
ffmpeg_dir = None
for root, dirs, files in os.walk('ffmpeg_temp'):
    for file in files:
        if file == 'ffmpeg.exe':
            ffmpeg_dir = os.path.dirname(os.path.join(root, file))
            break
    if ffmpeg_dir:
        break

if not ffmpeg_dir:
    raise FileNotFoundError("FFmpeg binaries not found. Please run download_ffmpeg.py first.")

# Define data files to include
added_files = [
    # Include profiles directory
    (profiles_dir, 'pyprocessor/profiles'),
    # Include logs directory
    (logs_dir, 'pyprocessor/logs'),
    # Include FFmpeg binaries
    (os.path.join(ffmpeg_dir, 'ffmpeg.exe'), 'ffmpeg/ffmpeg.exe'),
    (os.path.join(ffmpeg_dir, 'ffprobe.exe'), 'ffmpeg/ffprobe.exe'),
    ('ffmpeg_temp/README.txt', 'ffmpeg/README.txt'),
]

a = Analysis(
    ['pyprocessor/__main__.py'],  # Entry point
    pathex=[base_dir],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'darkdetect',
        'pyqtdarktheme',
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
    console=False,  # Set to False for GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if available
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
        
        try:
            with open(spec_file, 'w') as f:
                f.write(spec_content)
            print("✓ Created PyInstaller spec file.")
        except Exception as e:
            print(f"✗ Failed to create spec file: {e}")
            return False
    
    try:
        # Run PyInstaller
        subprocess.run([sys.executable, "-m", "PyInstaller", "--clean", "pyprocessor.spec"], check=True)
        print("✓ PyInstaller build completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ PyInstaller build failed: {e}")
        return False

def create_nsis_installer(makensis_path):
    """Create the NSIS installer."""
    print("Creating NSIS installer...")
    
    try:
        # Run makensis
        subprocess.run([makensis_path, "installer.nsi"], check=True)
        print("✓ NSIS installer created successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ NSIS installer creation failed: {e}")
        return False

def main():
    """Main function to run the build and packaging process."""
    parser = argparse.ArgumentParser(description="Build and package PyProcessor")
    parser.add_argument("--skip-ffmpeg", action="store_true", help="Skip downloading FFmpeg")
    parser.add_argument("--skip-pyinstaller", action="store_true", help="Skip PyInstaller build")
    parser.add_argument("--skip-nsis", action="store_true", help="Skip NSIS packaging")
    args = parser.parse_args()
    
    # Check for PyInstaller
    if not check_pyinstaller():
        if not install_pyinstaller():
            print("Please install PyInstaller manually: pip install pyinstaller")
            return False
    
    # Check for NSIS if not skipping NSIS packaging
    makensis_path = None
    if not args.skip_nsis:
        makensis_path = check_nsis()
        if not makensis_path:
            print("\nNSIS is required for packaging. Please install NSIS from https://nsis.sourceforge.io/Download")
            print("After installing NSIS, run this script again.")
            print("Alternatively, run with --skip-nsis to skip the packaging step.")
            return False
    
    # Download FFmpeg if not skipping
    if not args.skip_ffmpeg:
        if not download_ffmpeg():
            print("Failed to download FFmpeg. Please try again or download manually.")
            return False
    
    # Create license file for NSIS installer
    if not args.skip_nsis:
        if not create_license_file():
            print("Failed to create license file. Please create license.txt manually.")
            return False
    
    # Build executable if not skipping
    if not args.skip_pyinstaller:
        if not build_executable():
            print("Failed to build executable. Please check the errors and try again.")
            return False
    
    # Create NSIS installer if not skipping
    if not args.skip_nsis and makensis_path:
        if not create_nsis_installer(makensis_path):
            print("Failed to create NSIS installer. Please check the errors and try again.")
            return False
    
    print("\n✓ Build and packaging process completed successfully!")
    
    if not args.skip_nsis:
        installer_path = os.path.abspath("PyProcessorInstaller.exe")
        if os.path.exists(installer_path):
            print(f"\nInstaller created at: {installer_path}")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
