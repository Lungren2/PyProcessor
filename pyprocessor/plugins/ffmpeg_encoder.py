"""
FFmpeg encoder plugin for PyProcessor.

This plugin provides encoding functionality using FFmpeg.
"""

import subprocess
from typing import Any, Dict, List

from pyprocessor.plugins.interfaces import EncoderPlugin
from pyprocessor.utils.ffmpeg_locator import get_ffmpeg_path


class FFmpegEncoderPlugin(EncoderPlugin):
    """
    FFmpeg encoder plugin.

    This plugin provides encoding functionality using FFmpeg.
    """

    name = "ffmpeg_encoder"
    version = "0.1.0"
    description = "FFmpeg encoder plugin"
    author = "PyProcessor Team"

    def __init__(self):
        """Initialize the plugin."""
        super().__init__()
        self.ffmpeg_path = None

    def initialize(self) -> bool:
        """
        Initialize the plugin.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Get FFmpeg path
            self.ffmpeg_path = get_ffmpeg_path()
            if not self.ffmpeg_path:
                self.logger.error("FFmpeg not found")
                return False

            self.logger.debug(f"FFmpeg found at {self.ffmpeg_path}")
            return super().initialize()
        except Exception as e:
            self.logger.error(f"Error initializing FFmpeg encoder plugin: {str(e)}")
            return False

    def encode(
        self, input_file: str, output_file: str, options: Dict[str, Any] = None
    ) -> bool:
        """
        Encode a file using FFmpeg.

        Args:
            input_file: Path to the input file
            output_file: Path to the output file
            options: Encoding options

        Returns:
            bool: True if encoding was successful, False otherwise
        """
        if not self.is_initialized():
            self.logger.error("Plugin not initialized")
            return False

        if not self.is_enabled():
            self.logger.error("Plugin not enabled")
            return False

        # Get encoding options
        options = options or self.get_default_options()

        # Build FFmpeg command
        cmd = [self.ffmpeg_path, "-i", input_file]

        # Add encoding options
        if "video_codec" in options:
            cmd.extend(["-c:v", options["video_codec"]])

        if "audio_codec" in options:
            cmd.extend(["-c:a", options["audio_codec"]])

        if "video_bitrate" in options:
            cmd.extend(["-b:v", options["video_bitrate"]])

        if "audio_bitrate" in options:
            cmd.extend(["-b:a", options["audio_bitrate"]])

        if "preset" in options:
            cmd.extend(["-preset", options["preset"]])

        if "crf" in options:
            cmd.extend(["-crf", str(options["crf"])])

        # Add output file
        cmd.append(output_file)

        # Run FFmpeg
        try:
            self.logger.debug(f"Running FFmpeg: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            self.logger.debug(f"FFmpeg output: {result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"FFmpeg error: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Error encoding file: {str(e)}")
            return False

    def get_supported_formats(self) -> List[str]:
        """
        Get supported input and output formats.

        Returns:
            List[str]: List of supported formats
        """
        return ["mp4", "mkv", "avi", "mov", "webm", "flv", "wmv", "m4v"]

    def get_supported_codecs(self) -> Dict[str, List[str]]:
        """
        Get supported codecs for each format.

        Returns:
            Dict[str, List[str]]: Dictionary mapping formats to supported codecs
        """
        return {
            "video": ["libx264", "libx265", "vp9", "av1", "h264_nvenc", "hevc_nvenc"],
            "audio": ["aac", "mp3", "opus", "flac", "vorbis"],
        }

    def get_default_options(self) -> Dict[str, Any]:
        """
        Get default encoding options.

        Returns:
            Dict[str, Any]: Default encoding options
        """
        return {
            "video_codec": "libx264",
            "audio_codec": "aac",
            "video_bitrate": "1M",
            "audio_bitrate": "128k",
            "preset": "medium",
            "crf": 23,
        }
