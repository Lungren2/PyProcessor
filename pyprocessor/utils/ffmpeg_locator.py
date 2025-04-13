"""
FFmpeg locator module for finding and using bundled FFmpeg executables.
"""
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
