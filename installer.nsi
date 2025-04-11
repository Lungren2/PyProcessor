; Basic NSIS installer script with uninstaller and desktop shortcut option

!include "MUI2.nsh"

; General settings
Name "PyProcessor"
OutFile "PyProcessorInstaller.exe"
InstallDir "$PROGRAMFILES\PyProcessor"
InstallDirRegKey HKCU "Software\PyProcessor" ""

; Request application privileges
RequestExecutionLevel admin

; Interface settings
!define MUI_ABORTWARNING

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "license.txt"  ; Replace with your license file or remove
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Language
!insertmacro MUI_LANGUAGE "English"

; Installer sections
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

; Optional desktop shortcut section
Section "Desktop Shortcut" SecDesktopShortcut
  CreateShortCut "$DESKTOP\PyProcessor.lnk" "$INSTDIR\PyProcessor.exe"
SectionEnd

; Section descriptions
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} "Install the main application files."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktopShortcut} "Create a shortcut on your desktop."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; Uninstaller section
Section "Uninstall"
  ; Remove application files
  RMDir /r "$INSTDIR"
  
  ; Remove desktop shortcut
  Delete "$DESKTOP\PyProcessor.lnk"
  
  ; Remove registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\PyProcessor"
  DeleteRegKey HKCU "Software\PyProcessor"
SectionEnd