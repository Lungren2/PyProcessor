#!/usr/bin/env python3
"""
Cross-platform installation script for PyProcessor.

This script installs PyProcessor on the current system:
1. Installs dependencies
2. Creates necessary directories
3. Copies files to the installation directory
4. Creates shortcuts or symlinks

Usage:
    python scripts/install.py [--prefix PREFIX] [--user]

Options:
    --prefix PREFIX    Installation prefix (default: /usr/local on Unix, C:\\Program Files on Windows)
    --user             Install for the current user only
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

# Import path utilities if available
try:
    from pyprocessor.utils.path_utils import ensure_dir_exists
except ImportError:
    # If the module is not installed yet, define a simple version
    def ensure_dir_exists(path):
        """Ensure a directory exists, creating it if necessary."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path


def get_default_prefix(user_install):
    """Get the default installation prefix."""
    system = platform.system().lower()
    
    if user_install:
        # User installation
        if system == "windows":
            return Path(os.path.expandvars("%LOCALAPPDATA%")) / "Programs" / "PyProcessor"
        elif system == "darwin":
            return Path(os.path.expanduser("~/Applications/PyProcessor"))
        else:
            return Path(os.path.expanduser("~/.local"))
    else:
        # System-wide installation
        if system == "windows":
            return Path(os.path.expandvars("%ProgramFiles%")) / "PyProcessor"
        elif system == "darwin":
            return Path("/Applications/PyProcessor")
        else:
            return Path("/usr/local")


def check_dependencies():
    """Check if dependencies are installed."""
    print("Checking dependencies...")
    
    # Check for FFmpeg
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
        
        if result.returncode == 0 and "ffmpeg version" in result.stdout:
            print(f"✓ FFmpeg found: {result.stdout.split(chr(10))[0]}")
        else:
            print("✗ FFmpeg not found or not working properly")
            return False
    except (subprocess.SubprocessError, FileNotFoundError):
        print("✗ FFmpeg not found. Please install FFmpeg before continuing.")
        return False
    
    return True


def install_files(prefix, user_install):
    """Install files to the specified prefix."""
    print(f"Installing PyProcessor to {prefix}...")
    
    system = platform.system().lower()
    
    # Determine source directory
    if os.path.exists("dist/PyProcessor"):
        # Use built executable
        source_dir = Path("dist/PyProcessor")
    elif os.path.exists("pyprocessor"):
        # Use source code
        source_dir = Path(".")
    else:
        print("✗ PyProcessor source or build not found")
        return False
    
    try:
        # Create installation directories
        bin_dir = ensure_dir_exists(prefix / "bin" if system != "windows" else prefix)
        
        if os.path.exists("dist/PyProcessor"):
            # Install built executable
            if system == "windows":
                # Copy all files from dist/PyProcessor to prefix
                for item in source_dir.glob("*"):
                    if item.is_dir():
                        shutil.copytree(item, prefix / item.name, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, prefix / item.name)
                
                # Create shortcut
                create_windows_shortcut(prefix)
            elif system == "darwin":
                # Check if we have a .app bundle
                if os.path.exists("dist/PyProcessor.app"):
                    # Copy the .app bundle to /Applications or ~/Applications
                    app_dir = Path("/Applications") if not user_install else Path(os.path.expanduser("~/Applications"))
                    ensure_dir_exists(app_dir)
                    
                    app_path = app_dir / "PyProcessor.app"
                    if app_path.exists():
                        shutil.rmtree(app_path)
                    
                    shutil.copytree("dist/PyProcessor.app", app_path)
                    print(f"✓ Installed PyProcessor.app to {app_path}")
                    
                    # Create symlink in bin_dir
                    symlink_path = bin_dir / "pyprocessor"
                    if symlink_path.exists():
                        symlink_path.unlink()
                    
                    os.symlink("/usr/bin/open", symlink_path)
                    print(f"✓ Created symlink in {symlink_path}")
                else:
                    # Copy executable to bin_dir
                    for item in source_dir.glob("*"):
                        if item.is_file() and item.name == "PyProcessor":
                            shutil.copy2(item, bin_dir / "pyprocessor")
                            os.chmod(bin_dir / "pyprocessor", 0o755)
                        elif item.is_dir():
                            shutil.copytree(item, prefix / item.name, dirs_exist_ok=True)
                    
                    print(f"✓ Installed PyProcessor to {bin_dir}")
            else:
                # Linux installation
                # Copy executable to bin_dir
                for item in source_dir.glob("*"):
                    if item.is_file() and item.name == "PyProcessor":
                        shutil.copy2(item, bin_dir / "pyprocessor")
                        os.chmod(bin_dir / "pyprocessor", 0o755)
                    elif item.is_dir():
                        shutil.copytree(item, prefix / "share" / "pyprocessor" / item.name, dirs_exist_ok=True)
                
                # Create desktop entry
                create_linux_desktop_entry(prefix, user_install)
                
                print(f"✓ Installed PyProcessor to {bin_dir}")
        else:
            # Install from source
            # Create a Python package installation
            subprocess.run(
                [sys.executable, "-m", "pip", "install", ".", "--prefix", str(prefix)],
                check=True
            )
            
            print(f"✓ Installed PyProcessor Python package to {prefix}")
        
        return True
    except Exception as e:
        print(f"✗ Installation failed: {e}")
        return False


def create_windows_shortcut(prefix):
    """Create a Windows shortcut."""
    try:
        # Create Start Menu shortcut
        start_menu_dir = Path(os.path.expandvars("%APPDATA%")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "PyProcessor"
        ensure_dir_exists(start_menu_dir)
        
        # Create shortcut using PowerShell
        ps_script = f"""
        $WshShell = New-Object -comObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut("{start_menu_dir}\\PyProcessor.lnk")
        $Shortcut.TargetPath = "{prefix}\\PyProcessor.exe"
        $Shortcut.WorkingDirectory = "{prefix}"
        $Shortcut.Description = "PyProcessor - Cross-platform media processing engine"
        $Shortcut.Save()
        """
        
        with open("create_shortcut.ps1", "w") as f:
            f.write(ps_script)
        
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", "create_shortcut.ps1"], check=True)
        
        # Clean up
        os.remove("create_shortcut.ps1")
        
        print(f"✓ Created Start Menu shortcut in {start_menu_dir}")
        return True
    except Exception as e:
        print(f"✗ Failed to create shortcut: {e}")
        return False


def create_linux_desktop_entry(prefix, user_install):
    """Create a Linux desktop entry."""
    try:
        # Determine desktop entry location
        if user_install:
            desktop_dir = Path(os.path.expanduser("~/.local/share/applications"))
        else:
            desktop_dir = Path("/usr/share/applications")
        
        ensure_dir_exists(desktop_dir)
        
        # Create desktop entry
        desktop_entry = f"""[Desktop Entry]
Type=Application
Name=PyProcessor
Comment=Cross-platform media processing engine
Exec={prefix}/bin/pyprocessor
Icon={prefix}/share/pyprocessor/icon.png
Terminal=false
Categories=AudioVideo;Video;
"""
        
        with open(desktop_dir / "pyprocessor.desktop", "w") as f:
            f.write(desktop_entry)
        
        # Make sure the desktop entry is executable
        os.chmod(desktop_dir / "pyprocessor.desktop", 0o755)
        
        print(f"✓ Created desktop entry in {desktop_dir}")
        return True
    except Exception as e:
        print(f"✗ Failed to create desktop entry: {e}")
        return False


def main():
    """Main function to run the installation process."""
    parser = argparse.ArgumentParser(description="Install PyProcessor")
    parser.add_argument(
        "--prefix",
        help="Installation prefix"
    )
    parser.add_argument(
        "--user",
        action="store_true",
        help="Install for the current user only"
    )
    args = parser.parse_args()
    
    # Get installation prefix
    prefix = args.prefix
    if prefix:
        prefix = Path(prefix)
    else:
        prefix = get_default_prefix(args.user)
    
    # Print platform information
    system = platform.system()
    machine = platform.machine()
    print(f"Installing PyProcessor on {system} {machine}")
    print(f"Installation prefix: {prefix}")
    
    # Check if running as root/administrator
    is_admin = False
    if system == "Windows":
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            is_admin = False
    else:
        is_admin = os.geteuid() == 0
    
    # Check if we need admin privileges
    if not args.user and not is_admin and system != "Darwin":
        print("Warning: Installing system-wide requires administrator privileges.")
        print("Please run this script as administrator/root or use --user for a user installation.")
        return False
    
    # Check dependencies
    if not check_dependencies():
        print("Please install the required dependencies and try again.")
        return False
    
    # Install files
    if not install_files(prefix, args.user):
        return False
    
    print("\n✓ Installation completed successfully!")
    
    # Print next steps
    if system == "Windows":
        print("\nYou can now run PyProcessor from the Start Menu or by running:")
        print(f"{prefix}\\PyProcessor.exe")
    elif system == "Darwin":
        if os.path.exists("dist/PyProcessor.app"):
            print("\nYou can now run PyProcessor from the Applications folder or by running:")
            print("open -a PyProcessor")
        else:
            print("\nYou can now run PyProcessor by running:")
            print("pyprocessor")
    else:
        print("\nYou can now run PyProcessor by running:")
        print("pyprocessor")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
