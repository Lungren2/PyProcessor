"""
Path utilities for platform-agnostic path handling.
"""

import os
import platform
from pathlib import Path


def expand_env_vars(path_str):
    """
    Expand environment variables in a path string.
    
    Supports both ${VAR} and %VAR% formats for compatibility with
    Unix/Linux/macOS and Windows.
    
    Args:
        path_str: Path string that may contain environment variables
        
    Returns:
        String with environment variables expanded
    """
    # First expand ${VAR} format (Unix/Linux/macOS style)
    if path_str and "${" in path_str:
        # Handle ${VAR} format
        import re
        env_vars = re.findall(r'\${([^}]+)}', path_str)
        for var in env_vars:
            if var in os.environ:
                path_str = path_str.replace(f"${{{var}}}", os.environ[var])
            else:
                # Keep the variable if it's not defined
                pass
    
    # Then expand %VAR% format (Windows style)
    if path_str and "%" in path_str:
        # Handle %VAR% format
        path_str = os.path.expandvars(path_str)
    
    return path_str


def normalize_path(path_str):
    """
    Normalize a path string to use the correct path separators for the current platform.
    
    Args:
        path_str: Path string that may use forward or backward slashes
        
    Returns:
        Path object with correct separators for the current platform
    """
    if not path_str:
        return None
    
    # Expand environment variables
    expanded_path = expand_env_vars(path_str)
    
    # Convert to Path object which handles platform-specific separators
    return Path(expanded_path)


def get_default_media_root():
    """
    Get the default media root directory based on the platform.
    
    Returns:
        Path object for the default media root
    """
    system = platform.system().lower()
    
    if system == "windows":
        # Check if IIS paths exist
        iis_path = Path("C:/inetpub/wwwroot/media")
        if iis_path.exists():
            return iis_path
        
        # Fall back to user's documents folder
        return Path(os.path.expanduser("~/Documents/PyProcessor/media"))
    
    elif system == "linux":
        # Common web server paths on Linux
        for path in ["/var/www/html/media", "/srv/www/media"]:
            if Path(path).exists():
                return Path(path)
        
        # Fall back to user's home directory
        return Path(os.path.expanduser("~/PyProcessor/media"))
    
    elif system == "darwin":  # macOS
        # Use standard macOS conventions
        return Path(os.path.expanduser("~/Library/Application Support/PyProcessor/media"))
    
    else:
        # Generic fallback
        return Path(os.path.expanduser("~/PyProcessor/media"))


def get_app_data_dir():
    """
    Get the application data directory based on the platform.
    
    Returns:
        Path object for the application data directory
    """
    system = platform.system().lower()
    
    if system == "windows":
        # Use %APPDATA% on Windows
        return Path(os.path.expandvars("%APPDATA%/PyProcessor"))
    
    elif system == "linux":
        # Use XDG_CONFIG_HOME or ~/.config on Linux
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            return Path(xdg_config) / "pyprocessor"
        return Path(os.path.expanduser("~/.config/pyprocessor"))
    
    elif system == "darwin":  # macOS
        # Use ~/Library/Application Support on macOS
        return Path(os.path.expanduser("~/Library/Application Support/PyProcessor"))
    
    else:
        # Generic fallback
        return Path(os.path.expanduser("~/.pyprocessor"))
