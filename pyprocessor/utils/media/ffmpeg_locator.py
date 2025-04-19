"""
FFmpeg locator module for finding and using FFmpeg executables across platforms.

This module provides functions to locate FFmpeg and FFprobe executables
on different platforms (Windows, macOS, Linux) in various locations.

NOTE: This module is deprecated and will be removed in a future version.
Please use the FFmpegManager class from pyprocessor.utils.ffmpeg_manager instead.
"""

import warnings

# Import the new FFmpegManager
from pyprocessor.utils.ffmpeg_manager import FFmpegManager

# Create a singleton instance of FFmpegManager for backward compatibility
_ffmpeg_manager = FFmpegManager()

# Show deprecation warning
warnings.warn(
    "The ffmpeg_locator module is deprecated and will be removed in a future version. "
    "Please use the FFmpegManager class from pyprocessor.utils.ffmpeg_manager instead.",
    DeprecationWarning,
    stacklevel=2
)


def get_base_dir():
    """Get the base directory for the application
    
    Deprecated: Use FFmpegManager.get_base_dir() instead.
    """
    return _ffmpeg_manager.get_base_dir()


def get_ffmpeg_path():
    """Get the path to the FFmpeg executable
    
    Deprecated: Use FFmpegManager.get_ffmpeg_path() instead.
    """
    return _ffmpeg_manager.get_ffmpeg_path()


def get_ffprobe_path():
    """Get the path to the FFprobe executable
    
    Deprecated: Use FFmpegManager.get_ffprobe_path() instead.
    """
    return _ffmpeg_manager.get_ffprobe_path()


def check_ffmpeg_installation():
    """Check if FFmpeg is installed and available
    
    Deprecated: Use FFmpegManager.get_ffmpeg_version() instead.
    
    Returns:
        tuple: (is_installed, version_string, error_message)
    """
    is_installed, version_string, error_message = _ffmpeg_manager.get_ffmpeg_version()
    return is_installed, version_string, error_message
