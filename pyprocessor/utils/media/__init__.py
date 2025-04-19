"""
Media processing utilities for PyProcessor.

This module provides utilities for media processing, particularly FFmpeg.
"""

from pyprocessor.utils.media.ffmpeg_manager import (
    FFmpegManager, get_ffmpeg_manager, get_ffmpeg_path, get_ffprobe_path,
    check_ffmpeg_available, download_ffmpeg, run_ffmpeg_command
)
# Import from ffmpeg_locator for backward compatibility
from pyprocessor.utils.media.ffmpeg_locator import (
    get_base_dir, get_ffmpeg_path, get_ffprobe_path
)
