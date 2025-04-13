"""
Unit tests for the processing scheduler.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from concurrent.futures import ProcessPoolExecutor

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import the modules to test
from pyprocessor.utils.config import Config
from pyprocessor.utils.logging import Logger
from pyprocessor.processing.file_manager import FileManager
from pyprocessor.processing.encoder import FFmpegEncoder
from pyprocessor.processing.scheduler import ProcessingScheduler


class TestProcessingScheduler:
    """Test the ProcessingScheduler class functionality"""

    def setup_method(self):
        """Set up test environment before each test method"""
        # Create temporary directories
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_dir = Path(self.temp_dir.name) / "input"
        self.output_dir = Path(self.temp_dir.name) / "output"
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

        # Create test files
        self.test_files = [
            "Movie_Title_1080p.mp4",
            "Another_Movie_720p.mp4",
            "TV_Show_S01E01_480p.mp4",
            "Documentary_2020_360p.mp4",
        ]

        for filename in self.test_files:
            with open(self.input_dir / filename, "w") as f:
                f.write("Test content")

        # Create config
        self.config = Config()
        self.config.input_folder = self.input_dir
        self.config.output_folder = self.output_dir
        self.config.max_parallel_jobs = 2
        self.config.file_validation_pattern = r".+_\d+p\.mp4$"
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

        # Create mocked file manager and encoder
        self.file_manager = FileManager(self.config, self.logger)
        self.encoder = MagicMock(spec=FFmpegEncoder)

        # Create scheduler
        self.scheduler = ProcessingScheduler(
            self.config, self.logger, self.file_manager, self.encoder
        )

    def teardown_method(self):
        """Clean up after each test method"""
        self.temp_dir.cleanup()

    def test_initialization(self):
        """Test that the ProcessingScheduler initializes correctly"""
        assert self.scheduler.config == self.config
        assert self.scheduler.logger == self.logger
        assert self.scheduler.file_manager == self.file_manager
        assert self.scheduler.encoder == self.encoder
        assert self.scheduler.is_running is False
        assert self.scheduler.abort_requested is False

    def test_set_progress_callback(self):
        """Test setting a progress callback"""
        # Create a mock callback
        callback = MagicMock()

        # Set the callback
        self.scheduler.set_progress_callback(callback)

        # Verify that the callback was set
        assert self.scheduler.progress_callback == callback

    def test_set_output_file_callback(self):
        """Test setting an output file callback"""
        # Create a mock callback
        callback = MagicMock()

        # Set the callback
        self.scheduler.set_output_file_callback(callback)

        # Verify that the callback was set
        assert self.scheduler.output_file_callback == callback

    def test_request_abort(self):
        """Test requesting abortion of processing"""
        # Set is_running to True
        self.scheduler.is_running = True

        # Request abort
        result = self.scheduler.request_abort()

        # Verify the result
        assert result is True
        assert self.scheduler.abort_requested is True

    def test_request_abort_not_running(self):
        """Test requesting abortion when not running"""
        # Ensure is_running is False
        self.scheduler.is_running = False

        # Request abort
        result = self.scheduler.request_abort()

        # Verify the result
        assert result is False
        assert self.scheduler.abort_requested is False

    @patch("pyprocessor.processing.scheduler.ProcessPoolExecutor")
    def test_process_videos(self, mock_executor_class):
        """Test processing videos"""
        # Mock the ProcessPoolExecutor
        mock_executor = MagicMock(spec=ProcessPoolExecutor)
        mock_executor_class.return_value.__enter__.return_value = mock_executor

        # Mock the file manager's validate_files method
        valid_files = [Path(self.input_dir / filename) for filename in self.test_files]
        invalid_files = []
        self.file_manager.validate_files = MagicMock(
            return_value=(valid_files, invalid_files)
        )

        # Mock the executor's submit method
        mock_future = MagicMock()
        mock_future.result.return_value = ("output_file.mp4", True, 8.33, None)
        mock_executor.submit.return_value = mock_future

        # Process videos
        result = self.scheduler.process_videos()

        # Verify the result
        assert result is True
        assert self.scheduler.is_running is False

        # Verify that submit was called for each file
        assert mock_executor.submit.call_count == len(self.test_files)

    @patch("pyprocessor.processing.scheduler.ProcessPoolExecutor")
    def test_process_videos_no_valid_files(self, mock_executor_class):
        """Test processing videos with no valid files"""
        # Mock the file manager's validate_files method to return no valid files
        self.file_manager.validate_files = MagicMock(return_value=([], ["invalid.mp4"]))

        # Process videos
        result = self.scheduler.process_videos()

        # Verify the result
        assert result is False
        assert self.scheduler.is_running is False

        # Verify that the executor was not used
        mock_executor_class.assert_not_called()

    @patch("pyprocessor.processing.scheduler.ProcessPoolExecutor")
    def test_process_videos_with_abort(self, mock_executor_class):
        """Test aborting video processing"""
        # Mock the ProcessPoolExecutor
        mock_executor = MagicMock(spec=ProcessPoolExecutor)
        mock_executor_class.return_value.__enter__.return_value = mock_executor

        # Mock the file manager's validate_files method
        valid_files = [Path(self.input_dir / filename) for filename in self.test_files]
        invalid_files = []
        self.file_manager.validate_files = MagicMock(
            return_value=(valid_files, invalid_files)
        )

        # Mock the executor's submit method
        mock_future = MagicMock()
        mock_future.result.return_value = ("output_file.mp4", True, 8.33, None)
        mock_executor.submit.return_value = mock_future

        # Set up the scheduler to abort after processing starts
        def set_abort(*args, **kwargs):
            self.scheduler.abort_requested = True
            return mock_future

        mock_executor.submit.side_effect = set_abort

        # Process videos
        result = self.scheduler.process_videos()

        # Verify the result
        assert result is False  # Should return False when aborted
        assert self.scheduler.is_running is False

        # Verify that submit was called at least once
        assert mock_executor.submit.call_count > 0

        # Verify that the executor was shut down
        mock_executor.shutdown.assert_called_once_with(wait=False)

    @patch("pyprocessor.processing.scheduler.ProcessPoolExecutor")
    def test_process_videos_with_errors(self, mock_executor_class):
        """Test processing videos with errors"""
        # Mock the ProcessPoolExecutor
        mock_executor = MagicMock(spec=ProcessPoolExecutor)
        mock_executor_class.return_value.__enter__.return_value = mock_executor

        # Mock the file manager's validate_files method
        valid_files = [Path(self.input_dir / filename) for filename in self.test_files]
        invalid_files = []
        self.file_manager.validate_files = MagicMock(
            return_value=(valid_files, invalid_files)
        )

        # Mock the executor's submit method to return a mix of success and failure
        mock_success_future = MagicMock()
        mock_success_future.result.return_value = ("success_file.mp4", True, 5.20, None)

        mock_failure_future = MagicMock()
        mock_failure_future.result.return_value = (
            "failure_file.mp4",
            False,
            0.0,
            "Simulated error",
        )

        # Alternate between success and failure
        mock_executor.submit.side_effect = [
            mock_success_future,
            mock_failure_future,
        ] * 2

        # Process videos
        result = self.scheduler.process_videos()

        # Verify the result
        assert result is False  # Should return False if any file fails
        assert self.scheduler.is_running is False

        # Verify that submit was called for each file
        assert mock_executor.submit.call_count == len(self.test_files)

    def test_get_progress(self):
        """Test getting progress information"""
        # Set up some progress data
        self.scheduler.processed_count = 2
        self.scheduler.total_files = 4

        # Get progress
        progress = self.scheduler.get_progress()

        # Verify the progress
        assert progress == 0.5  # 2/4 = 50%

    def test_get_progress_no_files(self):
        """Test getting progress with no files"""
        # Set up with no files
        self.scheduler.processed_count = 0
        self.scheduler.total_files = 0

        # Get progress
        progress = self.scheduler.get_progress()

        # Verify the progress
        assert progress == 0.0  # No files = 0%
