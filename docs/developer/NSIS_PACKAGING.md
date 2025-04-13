# NSIS Packaging for PyProcessor

This document explains how to use the NSIS (Nullsoft Scriptable Install System) script to create an installer for PyProcessor.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Creating the License File](#creating-the-license-file)
- [NSIS Script Explanation](#nsis-script-explanation)
- [Building the Installer](#building-the-installer)
- [Customizing the Installer](#customizing-the-installer)
- [Troubleshooting](#troubleshooting)

## Overview

NSIS is a professional open-source system to create Windows installers. The PyProcessor project uses NSIS to create a user-friendly installer that:

- Installs the application to the user's Program Files directory
- Creates a desktop shortcut (optional)
- Adds the application to the Windows Add/Remove Programs list
- Provides an uninstaller

## Prerequisites

Before you can build the NSIS installer, you need:

1. **NSIS Installed**: Download and install NSIS from [nsis.sourceforge.io/Download](https://nsis.sourceforge.io/Download)
2. **PyInstaller Build**: Complete the PyInstaller build process to create the executable (see [PACKAGING.md](PACKAGING.md))
3. **License File**: Create a `license.txt` file in the project root (or use the automated build script)

## Creating the License File

The NSIS installer requires a `license.txt` file that will be displayed during installation. This file should contain the software license agreement that users must accept before installing PyProcessor.

### License File Requirements

- Create a plain text file named `license.txt` in the project root directory
- Use UTF-8 encoding to ensure proper display of special characters
- Keep line length reasonable (under 80 characters) for better readability in the installer

### License File Template

Here's a basic template you can use for your license file:

```text
PyProcessor License Agreement
===========================

Copyright (c) [Year] [Your Name/Organization]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

[Add your license conditions here]

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

You can use standard licenses like MIT, GPL, Apache, etc., or create a custom license for your project. Make sure to replace the placeholders with your actual information.

### Automated License File Creation

If you're using the automated build script (`scripts/build_package.py`), it will automatically generate a basic MIT license file for you if one doesn't exist. The generated license includes:

- Copyright attribution to Lungren2
- Standard MIT license terms
- Current year in the copyright notice

While this automatic generation is convenient, it's recommended to review and customize the license file to ensure it accurately represents your project's licensing terms.

## NSIS Script Explanation

The `installer.nsi` script in the project root contains the NSIS instructions for building the installer. Here's an explanation of its key components:

### General Settings

```nsis
Name "PyProcessor"
OutFile "PyProcessorInstaller.exe"
InstallDir "$PROGRAMFILES\PyProcessor"
InstallDirRegKey HKCU "Software\PyProcessor" ""
RequestExecutionLevel admin
```

- `Name`: The name of the application
- `OutFile`: The filename of the installer
- `InstallDir`: The default installation directory
- `InstallDirRegKey`: Registry key to store the installation directory
- `RequestExecutionLevel`: Requests administrator privileges for the installer

### Interface and Pages

```nsis
!include "MUI2.nsh"
!define MUI_ABORTWARNING

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "license.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
```

- `MUI2.nsh`: Includes the Modern UI 2 for a better-looking installer
- `MUI_ABORTWARNING`: Shows a warning when the user tries to abort the installation
- Various pages: Welcome, License, Directory selection, Components selection, Installation, and Finish

### Installation Sections

```nsis
Section "Main Application" SecMain
  SectionIn RO  ; Read-only, always installed

  SetOutPath "$INSTDIR"

  ; Extract files from your zip
  File /r "dist\*.*"

  ; Store installation folder
  WriteRegStr HKCU "Software\PyProcessor" "" $INSTDIR

  ; Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Add uninstaller information to Add/Remove Programs
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PyProcessor" "DisplayName" "PyProcessor"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PyProcessor" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PyProcessor" "QuietUninstallString" "$\"$INSTDIR\Uninstall.exe$\" /S"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PyProcessor" "InstallLocation" "$\"$INSTDIR$\""
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PyProcessor" "Publisher" "Lungren2"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PyProcessor" "DisplayIcon" "$\"$INSTDIR\PyProcessor.exe$\""
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PyProcessor" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PyProcessor" "NoRepair" 1
SectionEnd
```

- `SecMain`: The main installation section (required)
- `SectionIn RO`: Makes this section read-only (always installed)
- `File /r "dist\*.*"`: Copies all files from the `dist` directory to the installation directory
- Registry entries: Stores installation information and adds the application to Add/Remove Programs

### Optional Components

```nsis
Section "Desktop Shortcut" SecDesktopShortcut
  CreateShortCut "$DESKTOP\PyProcessor.lnk" "$INSTDIR\PyProcessor.exe"
SectionEnd
```

- `SecDesktopShortcut`: Optional section to create a desktop shortcut
- Users can choose whether to install this component

### Uninstaller

```nsis
Section "Uninstall"
  ; Remove application files
  RMDir /r "$INSTDIR"

  ; Remove desktop shortcut
  Delete "$DESKTOP\PyProcessor.lnk"

  ; Remove registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PyProcessor"
  DeleteRegKey HKCU "Software\PyProcessor"
SectionEnd
```

- Removes all installed files
- Removes the desktop shortcut
- Removes registry entries

## Building the Installer

### Automated Build

The easiest way to build the installer is to use the provided build script:

```bash
python scripts/build_package.py
```

This script will:

1. Check for required dependencies (PyInstaller, NSIS)
2. Download and extract FFmpeg binaries (if needed)
3. Create the PyInstaller executable
4. Package the executable using NSIS

### Manual Build

If you prefer to build the installer manually:

1. Ensure you have completed the PyInstaller build process
2. Create a `license.txt` file in the project root
3. Open a command prompt and navigate to the project directory
4. Run the NSIS compiler:

```bash
"C:\Program Files (x86)\NSIS\makensis.exe" installer.nsi
```

The installer will be created as `PyProcessorInstaller.exe` in the project root.

## Customizing the Installer

### Changing the Installer Appearance

To customize the installer appearance, you can modify the `installer.nsi` file:

- Change the installer name: Modify the `Name` directive
- Change the output filename: Modify the `OutFile` directive
- Add a custom icon: Add `!define MUI_ICON "path\to\icon.ico"`
- Change the installation directory: Modify the `InstallDir` directive

### Adding Additional Files

To include additional files in the installer:

1. Add the files to the PyInstaller build process first
2. The NSIS script will automatically include all files in the `dist` directory

### Adding Start Menu Shortcuts

To add Start Menu shortcuts, add the following to the main section:

```nsis
CreateDirectory "$SMPROGRAMS\PyProcessor"
CreateShortCut "$SMPROGRAMS\PyProcessor\PyProcessor.lnk" "$INSTDIR\PyProcessor.exe"
CreateShortCut "$SMPROGRAMS\PyProcessor\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
```

And add this to the uninstaller section:

```nsis
Delete "$SMPROGRAMS\PyProcessor\PyProcessor.lnk"
Delete "$SMPROGRAMS\PyProcessor\Uninstall.lnk"
RMDir "$SMPROGRAMS\PyProcessor"
```

## Troubleshooting

### Common Issues

1. **NSIS Not Found**: Ensure NSIS is installed and added to your PATH, or use the full path to `makensis.exe`
2. **Missing Files**: Make sure the PyInstaller build completed successfully and all files are in the `dist` directory
3. **License File Not Found**: Create a `license.txt` file in the project root or remove the license page from the NSIS script
4. **Permission Issues**: Run the NSIS compiler with administrator privileges if needed

### Testing the Installer

Always test the installer on a clean system to ensure it works correctly:

1. Install the application on a test machine
2. Verify all files are installed correctly
3. Test the application functionality
4. Test the uninstaller to ensure it removes all files and registry entries

## Conclusion

By using NSIS, you can create a professional installer for PyProcessor that provides a smooth installation experience for users. The installer handles all the necessary steps to install the application, create shortcuts, and add the application to the Windows Add/Remove Programs list.
