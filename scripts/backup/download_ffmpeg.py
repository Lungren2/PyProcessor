"""
Script to download and extract FFmpeg binaries for packaging PyProcessor.

This script supports downloading FFmpeg binaries for Windows, macOS, and Linux.
"""

import os
import sys
import platform

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the FFmpegManager, path utilities, and log manager
from pyprocessor.utils.ffmpeg_manager import FFmpegManager
from pyprocessor.utils.path_utils import ensure_dir_exists
from pyprocessor.utils.log_manager import get_logger


# Get the logger
logger = get_logger(level="INFO")

# Create a logger function for the FFmpegManager
def logger_func(level, message):
    if level == "info":
        logger.info(message)
    elif level == "debug":
        logger.debug(message)
    elif level == "warning":
        logger.warning(message)
    elif level == "error":
        logger.error(message)


def download_ffmpeg():
    """Download and extract FFmpeg binaries for packaging."""
    print(f"Downloading FFmpeg binaries for {platform.system()} ({platform.machine()})...")

    # Create directories if they don't exist
    temp_dir = ensure_dir_exists("ffmpeg_temp")
    bin_dir = ensure_dir_exists(temp_dir / "bin")

    # Create an instance of FFmpegManager with our logger function
    ffmpeg_manager = FFmpegManager(logger_func)

    # Use the FFmpegManager to download FFmpeg
    success = ffmpeg_manager.download_ffmpeg(bin_dir)

    if success:
        print("FFmpeg preparation complete. You can now run the build script to create the executable.")

    return success


if __name__ == "__main__":
    result = download_ffmpeg()
    sys.exit(0 if result else 1)
