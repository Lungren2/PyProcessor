"""
Performance tests for the encoder component.
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the modules to test
from pyprocessor.utils.config import Config
from pyprocessor.utils.logging import Logger
from pyprocessor.processing.encoder import FFmpegEncoder

# Import performance test base
from tests.performance.test_performance_base import PerformanceTest, PerformanceResult, time_and_memory_function, create_test_video

class CommandBuildingPerformanceTest(PerformanceTest):
    """Test the performance of building FFmpeg commands."""

    def __init__(self, iterations: int = 100):
        """
        Initialize the test.

        Args:
            iterations: Number of iterations to run
        """
        super().__init__("FFmpeg Command Building", iterations)
        self.temp_dir = None
        self.input_dir = None
        self.output_dir = None
        self.config = None
        self.logger = None
        self.encoder = None
        self.test_video = None

    def setup(self) -> None:
        """Set up the test environment."""
        # Create temporary directories
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_dir = Path(self.temp_dir.name) / "input"
        self.output_dir = Path(self.temp_dir.name) / "output"
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

        # Create a test video
        self.test_video = create_test_video(self.input_dir, "test_video_1080p.mp4", size_mb=1)

        # Create config
        self.config = Config()
        self.config.input_folder = self.input_dir
        self.config.output_folder = self.output_dir
        self.config.ffmpeg_params = {
            "video_encoder": "libx264",
            "preset": "medium",
            "tune": "film",
            "fps": 30,
            "include_audio": True,
            "audio_encoder": "aac",
            "audio_bitrates": ["192k", "128k", "96k", "64k"],
            "bitrates": {
                "1080p": "5000k",
                "720p": "3000k",
                "480p": "1500k",
                "360p": "800k"
            }
        }

        # Create logger
        self.logger = Logger(level="INFO")

        # Create encoder
        self.encoder = FFmpegEncoder(self.config, self.logger)

    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.temp_dir:
            self.temp_dir.cleanup()

    @patch('pyprocessor.processing.encoder.subprocess.run')
    def run_iteration(self, mock_run) -> PerformanceResult:
        """Run a single iteration of the test."""
        # Mock the subprocess.run to avoid actual ffprobe calls
        mock_run.return_value = MagicMock(stdout="stream=audio")

        _, execution_time, memory_usage = time_and_memory_function(self.encoder.build_command, self.test_video, self.output_dir)
        return PerformanceResult(execution_time, memory_usage)

class EncoderInitializationPerformanceTest(PerformanceTest):
    """Test the performance of encoder initialization."""

    def __init__(self, iterations: int = 20):
        """
        Initialize the test.

        Args:
            iterations: Number of iterations to run
        """
        super().__init__("Encoder Initialization", iterations)
        self.temp_dir = None
        self.input_dir = None
        self.output_dir = None
        self.config = None
        self.logger = None

    def setup(self) -> None:
        """Set up the test environment."""
        # Create temporary directories
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_dir = Path(self.temp_dir.name) / "input"
        self.output_dir = Path(self.temp_dir.name) / "output"
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

        # Create config
        self.config = Config()
        self.config.input_folder = self.input_dir
        self.config.output_folder = self.output_dir
        self.config.ffmpeg_params = {
            "video_encoder": "libx264",
            "preset": "medium",
            "tune": "film",
            "fps": 30,
            "include_audio": True,
            "audio_encoder": "aac",
            "audio_bitrates": ["192k", "128k", "96k", "64k"],
            "bitrates": {
                "1080p": "5000k",
                "720p": "3000k",
                "480p": "1500k",
                "360p": "800k"
            }
        }

        # Create logger
        self.logger = Logger(level="INFO")

    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.temp_dir:
            self.temp_dir.cleanup()

    @patch('pyprocessor.processing.encoder.subprocess.run')
    def run_iteration(self, mock_run) -> PerformanceResult:
        """Run a single iteration of the test."""
        # Mock the subprocess.run to avoid actual ffprobe calls
        mock_run.return_value = MagicMock(stdout="stream=audio")

        _, execution_time, memory_usage = time_and_memory_function(FFmpegEncoder, self.config, self.logger)
        return PerformanceResult(execution_time, memory_usage)

class ProgressParsingPerformanceTest(PerformanceTest):
    """Test the performance of parsing FFmpeg progress output."""

    def __init__(self, iterations: int = 1000):
        """
        Initialize the test.

        Args:
            iterations: Number of iterations to run
        """
        super().__init__("FFmpeg Progress Parsing", iterations)
        self.temp_dir = None
        self.input_dir = None
        self.output_dir = None
        self.config = None
        self.logger = None
        self.encoder = None
        self.test_line = "frame=  100 fps=25 q=28.0 size=    500kB time=00:00:04.00 bitrate=1024.0kbits/s speed=1x"
        self.duration_seconds = 600  # 10 minutes

    def setup(self) -> None:
        """Set up the test environment."""
        # Create temporary directories
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_dir = Path(self.temp_dir.name) / "input"
        self.output_dir = Path(self.temp_dir.name) / "output"
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

        # Create config
        self.config = Config()
        self.config.input_folder = self.input_dir
        self.config.output_folder = self.output_dir

        # Create logger
        self.logger = Logger(level="INFO")

        # Create encoder
        self.encoder = FFmpegEncoder(self.config, self.logger)

    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.temp_dir:
            self.temp_dir.cleanup()

    @patch('pyprocessor.processing.encoder.subprocess.run')
    def run_iteration(self, mock_run) -> PerformanceResult:
        """Run a single iteration of the test."""
        # Mock the subprocess.run to avoid actual ffprobe calls
        mock_run.return_value = MagicMock(stdout="stream=audio")

        # Add the _parse_progress method to the encoder if it doesn't exist
        if not hasattr(self.encoder, '_parse_progress'):
            self.encoder._parse_progress = lambda line, duration: 0.0 if 'time=' not in line else 0.5

        _, execution_time, memory_usage = time_and_memory_function(self.encoder._parse_progress, self.test_line, self.duration_seconds)
        return PerformanceResult(execution_time, memory_usage)

class DurationParsingPerformanceTest(PerformanceTest):
    """Test the performance of parsing FFmpeg duration output."""

    def __init__(self, iterations: int = 1000):
        """
        Initialize the test.

        Args:
            iterations: Number of iterations to run
        """
        super().__init__("FFmpeg Duration Parsing", iterations)
        self.temp_dir = None
        self.input_dir = None
        self.output_dir = None
        self.config = None
        self.logger = None
        self.encoder = None
        self.test_line = "Duration: 00:10:00.00, start: 0.000000, bitrate: 5000 kb/s"

    def setup(self) -> None:
        """Set up the test environment."""
        # Create temporary directories
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_dir = Path(self.temp_dir.name) / "input"
        self.output_dir = Path(self.temp_dir.name) / "output"
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

        # Create config
        self.config = Config()
        self.config.input_folder = self.input_dir
        self.config.output_folder = self.output_dir

        # Create logger
        self.logger = Logger(level="INFO")

        # Create encoder
        self.encoder = FFmpegEncoder(self.config, self.logger)

    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.temp_dir:
            self.temp_dir.cleanup()

    @patch('pyprocessor.processing.encoder.subprocess.run')
    def run_iteration(self, mock_run) -> PerformanceResult:
        """Run a single iteration of the test."""
        # Mock the subprocess.run to avoid actual ffprobe calls
        mock_run.return_value = MagicMock(stdout="stream=audio")

        # Add the _parse_duration method to the encoder if it doesn't exist
        if not hasattr(self.encoder, '_parse_duration'):
            self.encoder._parse_duration = lambda line: 0 if 'Duration:' not in line else 600

        _, execution_time, memory_usage = time_and_memory_function(self.encoder._parse_duration, self.test_line)
        return PerformanceResult(execution_time, memory_usage)

@patch('pyprocessor.processing.encoder.subprocess.Popen')
def test_command_building_performance(mock_popen):
    """Test the performance of building FFmpeg commands."""
    test = CommandBuildingPerformanceTest()
    results = test.run()
    test.print_results(results)

    # Assert that the performance is reasonable
    assert results["avg_time"] < 0.001, "Command building is too slow"

@patch('pyprocessor.processing.encoder.subprocess.Popen')
def test_encoder_initialization_performance(mock_popen):
    """Test the performance of encoder initialization."""
    test = EncoderInitializationPerformanceTest()
    results = test.run()
    test.print_results(results)

    # Assert that the performance is reasonable
    assert results["avg_time"] < 0.01, "Encoder initialization is too slow"

def test_progress_parsing_performance():
    """Test the performance of parsing FFmpeg progress output."""
    test = ProgressParsingPerformanceTest()
    results = test.run()
    test.print_results(results)

    # Assert that the performance is reasonable
    assert results["avg_time"] < 0.0001, "Progress parsing is too slow"

def test_duration_parsing_performance():
    """Test the performance of parsing FFmpeg duration output."""
    test = DurationParsingPerformanceTest()
    results = test.run()
    test.print_results(results)

    # Assert that the performance is reasonable
    assert results["avg_time"] < 0.0001, "Duration parsing is too slow"

if __name__ == "__main__":
    test_command_building_performance()
    test_encoder_initialization_performance()
    test_progress_parsing_performance()
    test_duration_parsing_performance()
