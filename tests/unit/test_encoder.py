"""
Unit tests for the FFmpeg encoder.
"""

import pytest
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import the modules to test
from pyprocessor.utils.config import Config
from pyprocessor.utils.logging import Logger
from pyprocessor.processing.encoder import FFmpegEncoder


class TestFFmpegEncoder:
    """Test the FFmpegEncoder class functionality"""

    def setup_method(self):
        """Set up test environment before each test method"""
        # Create temporary directories
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_dir = Path(self.temp_dir.name) / "input"
        self.output_dir = Path(self.temp_dir.name) / "output"
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

        # Create a mock video file (not a real video, just for testing)
        self.test_video = self.input_dir / "test_video.mp4"
        with open(self.test_video, "w") as f:
            f.write("Mock video content")

        # Create config with test settings
        self.config = Config()
        self.config.input_folder = self.input_dir
        self.config.output_folder = self.output_dir
        self.config.ffmpeg_params = {
            "video_encoder": "libx264",
            "preset": "medium",
            "tune": "film",
            "fps": 30,
            "include_audio": True,
            "bitrates": {
                "1080p": "5000k",
                "720p": "3000k",
                "480p": "1500k",
                "360p": "800k",
            },
        }

        # Create logger
        self.logger = Logger(level="INFO")

        # Create encoder
        self.encoder = FFmpegEncoder(self.config, self.logger)

    def teardown_method(self):
        """Clean up after each test method"""
        # Stop any running process
        if self.encoder.process:
            from contextlib import suppress

            with suppress(Exception):
                self.encoder.process.terminate()

        self.temp_dir.cleanup()

    @patch("pyprocessor.processing.encoder.subprocess.run")
    def test_check_ffmpeg(self, mock_run):
        """Test FFmpeg availability check"""
        # Mock successful FFmpeg check
        mock_process = MagicMock()
        mock_process.stdout = (
            "ffmpeg version 4.4 Copyright (c) 2000-2021 the FFmpeg developers"
        )
        mock_run.return_value = mock_process

        # Check FFmpeg
        result = self.encoder.check_ffmpeg()

        # Verify the result
        assert result is True
        mock_run.assert_called_once()

    @patch("pyprocessor.processing.encoder.subprocess.run")
    def test_check_ffmpeg_not_found(self, mock_run):
        """Test FFmpeg check when FFmpeg is not found"""
        # Mock FFmpeg not found
        mock_run.side_effect = FileNotFoundError("FFmpeg not found")

        # Check FFmpeg
        result = self.encoder.check_ffmpeg()

        # Verify the result
        assert result is False
        mock_run.assert_called_once()

    def test_build_command(self):
        """Test building FFmpeg command"""
        # Build command
        cmd = self.encoder.build_command(self.test_video, self.output_dir)

        # Check that the command is a list
        assert isinstance(cmd, list)

        # Check that the command contains the expected elements
        assert "ffmpeg" in cmd[0] or "ffmpeg.exe" in cmd[0]
        assert "-i" in cmd
        assert self.test_video.name in " ".join(cmd)
        assert self.config.ffmpeg_params["video_encoder"] in " ".join(cmd)
        assert self.config.ffmpeg_params["preset"] in " ".join(cmd)
        assert self.config.ffmpeg_params["tune"] in " ".join(cmd)

    def test_build_command_no_audio(self):
        """Test building FFmpeg command with audio disabled"""
        # Disable audio
        self.config.ffmpeg_params["include_audio"] = False

        # Build command
        cmd = self.encoder.build_command(self.test_video, self.output_dir)

        # Check that the command contains -an (no audio)
        assert "-an" in cmd

    @patch("pyprocessor.processing.encoder.subprocess.Popen")
    def test_encode_video(self, mock_popen):
        """Test video encoding process"""
        # Mock the FFmpeg process
        mock_process = MagicMock()
        mock_process.stderr = iter(
            [
                "Duration: 00:10:00.00, start: 0.000000, bitrate: 5000 kb/s",
                "frame=  100 fps=25 q=28.0 size=    500kB time=00:00:04.00 bitrate=1024.0kbits/s speed=1x",
                "frame=  200 fps=25 q=28.0 size=   1000kB time=00:00:08.00 bitrate=1024.0kbits/s speed=1x",
                "frame=  300 fps=25 q=28.0 size=   1500kB time=00:00:12.00 bitrate=1024.0kbits/s speed=1x",
                "video:1500kB audio:500kB subtitle:0kB other streams:0kB global headers:0kB muxing overhead: 1.000000%",
            ]
        )
        mock_process.poll.side_effect = [None, None, None, None, 0]
        mock_popen.return_value = mock_process

        # Create a progress callback
        progress_callback = MagicMock()

        # Encode video
        result = self.encoder.encode_video(
            self.test_video, self.output_dir, progress_callback
        )

        # Verify the result
        assert result is True
        mock_popen.assert_called_once()

        # Check that the progress callback was called
        assert progress_callback.call_count > 0

    @patch("pyprocessor.processing.encoder.subprocess.Popen")
    def test_encode_video_error(self, mock_popen):
        """Test video encoding process with an error"""
        # Mock the FFmpeg process with an error
        mock_process = MagicMock()
        mock_process.stderr = iter(
            [
                "Duration: 00:10:00.00, start: 0.000000, bitrate: 5000 kb/s",
                "frame=  100 fps=25 q=28.0 size=    500kB time=00:00:04.00 bitrate=1024.0kbits/s speed=1x",
                "Error: Invalid data found when processing input",
            ]
        )
        mock_process.poll.side_effect = [None, None, 1]
        mock_popen.return_value = mock_process

        # Encode video
        result = self.encoder.encode_video(self.test_video, self.output_dir)

        # Verify the result
        assert result is False
        mock_popen.assert_called_once()

    @patch("pyprocessor.processing.encoder.subprocess.Popen")
    def test_stop_encoding(self, mock_popen):
        """Test stopping the encoding process"""
        # Mock the FFmpeg process
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        # Start encoding in a way that doesn't block
        self.encoder.process = mock_process

        # Stop encoding
        self.encoder.stop()

        # Verify that the process was terminated
        mock_process.terminate.assert_called_once()

    def test_parse_progress(self):
        """Test parsing progress from FFmpeg output"""
        # Test with a valid time output
        time_line = "frame=  100 fps=25 q=28.0 size=    500kB time=00:00:04.00 bitrate=1024.0kbits/s speed=1x"
        duration_seconds = 10 * 60  # 10 minutes in seconds

        progress = self.encoder._parse_progress(time_line, duration_seconds)

        # Progress should be 4 seconds out of 10 minutes = 4 / 600 = 0.0067 = 0.67%
        assert progress == pytest.approx(0.0067, abs=0.001)

    def test_parse_progress_invalid(self):
        """Test parsing progress with invalid input"""
        # Test with an invalid time output
        time_line = (
            "frame=  100 fps=25 q=28.0 size=    500kB bitrate=1024.0kbits/s speed=1x"
        )
        duration_seconds = 10 * 60  # 10 minutes in seconds

        progress = self.encoder._parse_progress(time_line, duration_seconds)

        # Progress should be 0 if time cannot be parsed
        assert progress == 0

    def test_parse_duration(self):
        """Test parsing duration from FFmpeg output"""
        # Test with a valid duration output
        duration_line = "Duration: 00:10:00.00, start: 0.000000, bitrate: 5000 kb/s"

        duration_seconds = self.encoder._parse_duration(duration_line)

        # Duration should be 10 minutes = 600 seconds
        assert duration_seconds == 600

    def test_parse_duration_invalid(self):
        """Test parsing duration with invalid input"""
        # Test with an invalid duration output
        duration_line = "Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'test_video.mp4':"

        duration_seconds = self.encoder._parse_duration(duration_line)

        # Duration should be 0 if it cannot be parsed
        assert duration_seconds == 0
