# Packaging PyProcessor

This document explains how to package the PyProcessor application into a standalone executable, including bundling FFmpeg to eliminate the external dependency.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Automated Build Process](#automated-build-process)
- [Manual Build Process](#manual-build-process)
  - [Bundling FFmpeg](#bundling-ffmpeg)
  - [Creating the Executable](#creating-the-executable)
  - [Creating an Installer](#creating-an-installer)
- [Distribution](#distribution)
- [Troubleshooting](#troubleshooting)

## Overview

PyProcessor can be packaged into a standalone executable using PyInstaller. This process bundles all necessary Python dependencies and includes FFmpeg binaries, eliminating the need for users to install FFmpeg separately. The packaged application can then be distributed as a standalone executable or as an installer created with NSIS (Nullsoft Scriptable Install System).

## Prerequisites

Before packaging the application, ensure you have:

- Python 3.6 or higher installed
- All required dependencies installed (`pip install -e .`)
- PyInstaller installed (`pip install pyinstaller`)
- NSIS installed (for creating the installer) - Download from [nsis.sourceforge.io/Download](https://nsis.sourceforge.io/Download)
- Internet connection to download FFmpeg binaries (if not already downloaded)

## Automated Build Process

The easiest way to build and package PyProcessor is to use the provided build script, which automates the entire process:

```bash
python scripts/build_package.py
```

This script will:

1. Check for required dependencies (PyInstaller, NSIS)
2. Download and extract FFmpeg binaries
3. Create the PyInstaller executable
4. Package the executable using NSIS

You can customize the build process with the following options:

```bash
python scripts/build_package.py --skip-ffmpeg     # Skip downloading FFmpeg
python scripts/build_package.py --skip-pyinstaller # Skip PyInstaller build
python scripts/build_package.py --skip-nsis        # Skip NSIS packaging
```

## Manual Build Process

## Bundling FFmpeg

### 1. Download and Extract FFmpeg Binaries

You can download and extract the FFmpeg binaries manually or use the provided helper script.

#### Option 1: Using the Helper Script

Run the provided helper script to automatically download and extract FFmpeg:

```bash
python scripts/download_ffmpeg.py
```

This script will:

- Download the FFmpeg essentials build for Windows
- Extract it to the `ffmpeg_temp` directory
- Create a README file with licensing information

#### Option 2: Manual Download and Extraction

If you prefer to download and extract FFmpeg manually:

```powershell
# Using PowerShell to download
Invoke-WebRequest -Uri "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile "ffmpeg.zip"

# Extract the downloaded zip file
Expand-Archive -Path ffmpeg.zip -DestinationPath ffmpeg_temp
```

### 3. Create FFmpeg Locator Module

Create a utility module to help the application find the bundled FFmpeg executables:

```python
# pyprocessor/utils/ffmpeg_locator.py
import os
import sys
from pathlib import Path

def get_base_dir():
    """Get the base directory for the application"""
    if getattr(sys, 'frozen', False):
        # Running as a bundled executable
        return Path(sys._MEIPASS)
    else:
        # Running in a normal Python environment
        return Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_ffmpeg_path():
    """Get the path to the FFmpeg executable"""
    base_dir = get_base_dir()

    # Check for bundled FFmpeg first
    if getattr(sys, 'frozen', False):
        # When running as a bundled executable
        ffmpeg_path = base_dir / "ffmpeg" / "ffmpeg.exe"
        if ffmpeg_path.exists():
            return str(ffmpeg_path)
    else:
        # When running in development mode, check relative path
        ffmpeg_path = base_dir.parent / "ffmpeg" / "ffmpeg.exe"
        if ffmpeg_path.exists():
            return str(ffmpeg_path)

    # Fall back to system FFmpeg
    return "ffmpeg"

def get_ffprobe_path():
    """Get the path to the FFprobe executable"""
    base_dir = get_base_dir()

    # Check for bundled FFprobe first
    if getattr(sys, 'frozen', False):
        # When running as a bundled executable
        ffprobe_path = base_dir / "ffmpeg" / "ffprobe.exe"
        if ffprobe_path.exists():
            return str(ffprobe_path)
    else:
        # When running in development mode, check relative path
        ffprobe_path = base_dir.parent / "ffmpeg" / "ffprobe.exe"
        if ffprobe_path.exists():
            return str(ffprobe_path)

    # Fall back to system FFprobe
    return "ffprobe"
```

### 4. Modify Encoder and Scheduler to Use Bundled FFmpeg

Update the encoder.py file to use the FFmpeg locator:

```python
# Add import at the top of the file
from pyprocessor.utils.ffmpeg_locator import get_ffmpeg_path, get_ffprobe_path

# Replace FFmpeg calls in check_ffmpeg method
def check_ffmpeg(self):
    """Check if FFmpeg is installed and available"""
    try:
        ffmpeg_path = get_ffmpeg_path()
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        # Rest of the method remains the same
```

Similarly, update the has_audio method and build_command method in encoder.py, and the check_for_audio function in scheduler.py.

## Creating the Executable

### 1. Create a PyInstaller Spec File

Create a custom spec file (pyprocessor.spec) to include FFmpeg binaries:

```python
# -*- mode: python ; coding: utf-8 -*-

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

# Define data files to include
added_files = [
    # Include profiles directory
    (profiles_dir, 'pyprocessor/profiles'),
    # Include logs directory
    (logs_dir, 'pyprocessor/logs'),
    # Include FFmpeg binaries
    ('ffmpeg_temp/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe', 'ffmpeg/ffmpeg.exe'),
    ('ffmpeg_temp/ffmpeg-7.1.1-essentials_build/bin/ffprobe.exe', 'ffmpeg/ffprobe.exe'),
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
```

### 2. Create a README for the FFmpeg Directory

Create a README file to document the bundled FFmpeg:

```text
FFmpeg Binaries for PyProcessor
==============================

These FFmpeg binaries are bundled with PyProcessor to enable video processing functionality without requiring a separate FFmpeg installation.

Source: https://www.gyan.dev/ffmpeg/builds/
Version: 7.1.1 (essentials build)

FFmpeg is licensed under the GNU Lesser General Public License (LGPL) version 2.1 or later.
For more information, visit: https://ffmpeg.org/legal.html

These binaries are included for convenience and are not modified in any way from their original distribution.
```

### 3. Build the Executable

Run PyInstaller with the spec file:

```powershell
python -m PyInstaller --clean pyprocessor.spec
```

The executable will be created in the `dist/PyProcessor` directory.

## Creating an Installer

After creating the executable with PyInstaller, you can create an installer using NSIS (Nullsoft Scriptable Install System).

### 1. Install NSIS

Download and install NSIS from [nsis.sourceforge.io/Download](https://nsis.sourceforge.io/Download).

### 2. Create a License File

Create a `license.txt` file in the project root directory. This file will be displayed during the installation process.

### 3. Build the Installer

Run the NSIS compiler with the provided installer script:

```powershell
"C:\Program Files (x86)\NSIS\makensis.exe" installer.nsi
```

This will create a `PyProcessorInstaller.exe` file in the project root directory.

For more details on the NSIS installer script and customization options, see [NSIS_PACKAGING.md](NSIS_PACKAGING.md).

## Distribution

### 1. Create a Batch File for Easy Launching (Optional)

If distributing without an installer, create a batch file (run_pyprocessor.bat) to help users launch the application:

```batch
@echo off
echo Starting PyProcessor...
start "" "%~dp0PyProcessor\PyProcessor.exe"
```

### 2. Package the Application

Options for distribution include:

- NSIS Installer (recommended) - Created using the process described above
- ZIP archive - Compress the entire `dist` folder
- Self-extracting archive - Create using tools like 7-Zip SFX

### 3. Documentation

Include a README file with the distribution that explains:

- How to run the application
- That FFmpeg is bundled and no separate installation is required
- System requirements
- Troubleshooting tips

## Troubleshooting

### Common Issues

1. **Missing DLLs**: If users encounter missing DLL errors, ensure that the Visual C++ Redistributable is installed on their system.

2. **FFmpeg Not Found**: If the application cannot find the bundled FFmpeg, check that the FFmpeg binaries are correctly included in the package and that the ffmpeg_locator.py module is working correctly.

3. **Permission Issues**: If users encounter permission issues when running the application, suggest running it as an administrator or installing it in a location where they have write permissions.

4. **Antivirus Blocking**: Some antivirus software may block the application. Users may need to add an exception for the application.

### Debugging

For debugging packaging issues:

1. Set `console=True` in the EXE section of the spec file to see console output
2. Add print statements to the ffmpeg_locator.py module to debug path issues
3. Test the packaged application on a clean system to ensure all dependencies are included

## Conclusion

By following this guide, you can create a standalone executable of PyProcessor with bundled FFmpeg, making it easier for users to install and use the application without worrying about external dependencies. The automated build script simplifies this process, handling all the necessary steps to create both the executable and the installer.
