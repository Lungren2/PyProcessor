"""
Unit tests for FFmpeg encoder error conditions.
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import the modules to test
from pyprocessor.utils.config import Config
from pyprocessor.utils.logging import Logger
from pyprocessor.processing.encoder import FFmpegEncoder


class TestEncoderErrorConditions:
    """Test error conditions in the FFmpegEncoder class"""

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
            "encoder": "libx264",
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
            try:
                self.encoder.process.terminate()
            except:
                pass

        self.temp_dir.cleanup()

    @patch("pyprocessor.processing.encoder.subprocess.run")
    def test_ffmpeg_not_installed(self, mock_run):
        """Test when FFmpeg is not installed"""
        # Mock subprocess.run to raise FileNotFoundError
        mock_run.side_effect = FileNotFoundError("FFmpeg not found")

        # Check FFmpeg
        result = self.encoder.check_ffmpeg()

        # Verify the result
        assert result is False

    @patch("pyprocessor.processing.encoder.subprocess.run")
    def test_ffmpeg_timeout(self, mock_run):
        """Test when FFmpeg check times out"""
        # Mock subprocess.run to raise TimeoutExpired
        mock_run.side_effect = subprocess.TimeoutExpired("ffmpeg", 5)

        # Check FFmpeg
        result = self.encoder.check_ffmpeg()

        # Verify the result
        assert result is False

    @patch("pyprocessor.processing.encoder.subprocess.run")
    def test_ffmpeg_error_output(self, mock_run):
        """Test when FFmpeg returns error output"""
        # Mock subprocess.run to return error output
        mock_process = MagicMock()
        mock_process.stdout = ""
        mock_process.stderr = "ffmpeg: error: some error message"
        mock_process.returncode = 1
        mock_run.return_value = mock_process

        # Check FFmpeg
        result = self.encoder.check_ffmpeg()

        # Verify the result
        assert result is False

    def test_nonexistent_input_file(self):
        """Test encoding a nonexistent input file"""
        # Set a nonexistent input file
        nonexistent_file = self.input_dir / "nonexistent.mp4"

        # Encode video
        result = self.encoder.encode_video(nonexistent_file, self.output_dir)

        # Verify the result
        assert result is False

    def test_readonly_output_directory(self):
        """Test encoding to a read-only output directory"""
        # Make the output directory read-only
        os.chmod(self.output_dir, 0o500)  # r-x------

        try:
            # Encode video
            result = self.encoder.encode_video(self.test_video, self.output_dir)

            # Verify the result
            assert result is False
        finally:
            # Restore permissions for cleanup
            os.chmod(self.output_dir, 0o700)  # rwx------

    @patch("pyprocessor.processing.encoder.subprocess.Popen")
    def test_ffmpeg_process_error(self, mock_popen):
        """Test when FFmpeg process returns an error"""
        # Mock the FFmpeg process to return an error
        mock_process = MagicMock()
        mock_process.stderr = iter(
            [
                "Duration: 00:10:00.00, start: 0.000000, bitrate: 5000 kb/s",
                "Error: Invalid data found when processing input",
            ]
        )
        mock_process.poll.side_effect = [None, 1]
        mock_popen.return_value = mock_process

        # Encode video
        result = self.encoder.encode_video(self.test_video, self.output_dir)

        # Verify the result
        assert result is False

    @patch("pyprocessor.processing.encoder.subprocess.Popen")
    def test_ffmpeg_process_crash(self, mock_popen):
        """Test when FFmpeg process crashes"""
        # Mock the FFmpeg process to crash
        mock_process = MagicMock()
        mock_process.stderr = iter(
            [
                "Duration: 00:10:00.00, start: 0.000000, bitrate: 5000 kb/s",
                "frame=  100 fps=25 q=28.0 size=    500kB time=00:00:04.00 bitrate=1024.0kbits/s speed=1x",
            ]
        )
        mock_process.poll.side_effect = [None, None]
        mock_process.communicate.side_effect = subprocess.SubprocessError(
            "Process crashed"
        )
        mock_popen.return_value = mock_process

        # Encode video
        result = self.encoder.encode_video(self.test_video, self.output_dir)

        # Verify the result
        assert result is False

    @patch("pyprocessor.processing.encoder.subprocess.Popen")
    def test_ffmpeg_invalid_duration(self, mock_popen):
        """Test when FFmpeg returns invalid duration"""
        # Mock the FFmpeg process with invalid duration
        mock_process = MagicMock()
        mock_process.stderr = iter(
            [
                "Invalid duration: N/A, start: 0.000000, bitrate: N/A",
                "frame=  100 fps=25 q=28.0 size=    500kB time=00:00:04.00 bitrate=1024.0kbits/s speed=1x",
            ]
        )
        mock_process.poll.side_effect = [None, None, 0]
        mock_popen.return_value = mock_process

        # Encode video
        result = self.encoder.encode_video(self.test_video, self.output_dir)

        # Verify the result
        assert result is True  # Should still succeed even with invalid duration

    @patch("pyprocessor.processing.encoder.subprocess.Popen")
    def test_ffmpeg_invalid_time(self, mock_popen):
        """Test when FFmpeg returns invalid time"""
        # Mock the FFmpeg process with invalid time
        mock_process = MagicMock()
        mock_process.stderr = iter(
            [
                "Duration: 00:10:00.00, start: 0.000000, bitrate: 5000 kb/s",
                "frame=  100 fps=25 q=28.0 size=    500kB time=N/A bitrate=1024.0kbits/s speed=1x",
            ]
        )
        mock_process.poll.side_effect = [None, None, 0]
        mock_popen.return_value = mock_process

        # Encode video
        result = self.encoder.encode_video(self.test_video, self.output_dir)

        # Verify the result
        assert result is True  # Should still succeed even with invalid time

    @patch("pyprocessor.processing.encoder.subprocess.Popen")
    def test_stop_nonexistent_process(self, mock_popen):
        """Test stopping a nonexistent process"""
        # Ensure no process is running
        self.encoder.process = None

        # Stop encoding
        self.encoder.stop()

        # Verify that no exception was raised
        assert self.encoder.process is None

    @patch("pyprocessor.processing.encoder.subprocess.Popen")
    def test_stop_terminated_process(self, mock_popen):
        """Test stopping an already terminated process"""
        # Mock a terminated process
        mock_process = MagicMock()
        mock_process.poll.return_value = 0  # Process has already terminated
        self.encoder.process = mock_process

        # Stop encoding
        self.encoder.stop()

        # Verify that terminate was not called
        mock_process.terminate.assert_not_called()

    @patch("pyprocessor.processing.encoder.subprocess.Popen")
    def test_stop_with_exception(self, mock_popen):
        """Test stopping a process that raises an exception"""
        # Mock a process that raises an exception when terminated
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is still running
        mock_process.terminate.side_effect = Exception("Termination error")
        self.encoder.process = mock_process

        # Stop encoding
        self.encoder.stop()

        # Verify that terminate was called
        mock_process.terminate.assert_called_once()

        # Verify that the exception was handled
        assert (
            self.encoder.process is mock_process
        )  # Process reference should still be there

    @patch("pyprocessor.processing.encoder.get_ffmpeg_path")
    def test_invalid_ffmpeg_path(self, mock_get_ffmpeg_path):
        """Test with an invalid FFmpeg path"""
        # Mock get_ffmpeg_path to return a nonexistent path
        mock_get_ffmpeg_path.return_value = "/nonexistent/ffmpeg"

        # Build command
        cmd = self.encoder.build_command(self.test_video, self.output_dir)

        # Verify that the command uses the invalid path
        assert cmd[0] == "/nonexistent/ffmpeg"

        # Encode video (should fail)
        result = self.encoder.encode_video(self.test_video, self.output_dir)

        # Verify the result
        assert result is False

    def test_invalid_encoder(self):
        """Test with an invalid encoder"""
        # Set an invalid encoder
        self.config.ffmpeg_params["encoder"] = "invalid_encoder"

        # Build command
        cmd = self.encoder.build_command(self.test_video, self.output_dir)

        # Verify that the command includes the invalid encoder
        assert "-c:v" in cmd
        assert "invalid_encoder" in cmd

        # Encode video (would fail in a real environment)
        # We can't test this directly without running FFmpeg

    def test_invalid_preset(self):
        """Test with an invalid preset"""
        # Set an invalid preset
        self.config.ffmpeg_params["preset"] = "invalid_preset"

        # Build command
        cmd = self.encoder.build_command(self.test_video, self.output_dir)

        # Verify that the command includes the invalid preset
        assert "-preset" in cmd
        assert "invalid_preset" in cmd

        # Encode video (would fail in a real environment)
        # We can't test this directly without running FFmpeg

    def test_invalid_tune(self):
        """Test with an invalid tune"""
        # Set an invalid tune
        self.config.ffmpeg_params["tune"] = "invalid_tune"

        # Build command
        cmd = self.encoder.build_command(self.test_video, self.output_dir)

        # Verify that the command includes the invalid tune
        assert "-tune" in cmd
        assert "invalid_tune" in cmd

        # Encode video (would fail in a real environment)
        # We can't test this directly without running FFmpeg

    def test_invalid_fps(self):
        """Test with an invalid FPS"""
        # Set an invalid FPS
        self.config.ffmpeg_params["fps"] = -10

        # Build command
        cmd = self.encoder.build_command(self.test_video, self.output_dir)

        # Verify that the command includes the invalid FPS
        assert "-r" in cmd
        assert "-10" in cmd

        # Encode video (would fail in a real environment)
        # We can't test this directly without running FFmpeg
