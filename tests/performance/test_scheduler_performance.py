"""
Performance tests for the processing scheduler component.
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

# Import performance test base
from tests.performance.test_performance_base import (
    PerformanceTest,
    PerformanceResult,
    time_and_memory_function,
    create_test_videos,
)


class SchedulerInitializationPerformanceTest(PerformanceTest):
    """Test the performance of scheduler initialization."""

    def __init__(self, iterations: int = 20):
        """
        Initialize the test.

        Args:
            iterations: Number of iterations to run
        """
        super().__init__("Scheduler Initialization", iterations)
        self.temp_dir = None
        self.input_dir = None
        self.output_dir = None
        self.config = None
        self.logger = None
        self.file_manager = None
        self.encoder = None

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
        self.config.max_parallel_jobs = 4

        # Create logger
        self.logger = Logger(level="INFO")

        # Create mocked file manager and encoder
        self.file_manager = MagicMock(spec=FileManager)
        self.encoder = MagicMock(spec=FFmpegEncoder)

    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.temp_dir:
            self.temp_dir.cleanup()

    def run_iteration(self) -> PerformanceResult:
        """Run a single iteration of the test."""
        _, execution_time, memory_usage = time_and_memory_function(
            ProcessingScheduler,
            self.config,
            self.logger,
            self.file_manager,
            self.encoder,
        )
        return PerformanceResult(execution_time, memory_usage)


class TaskSubmissionPerformanceTest(PerformanceTest):
    """Test the performance of task submission in the scheduler."""

    def __init__(self, file_count: int, iterations: int = 3):
        """
        Initialize the test.

        Args:
            file_count: Number of files to process
            iterations: Number of iterations to run
        """
        super().__init__(f"Task Submission ({file_count} files)", iterations)
        self.file_count = file_count
        self.temp_dir = None
        self.input_dir = None
        self.output_dir = None
        self.config = None
        self.logger = None
        self.file_manager = None
        self.encoder = None
        self.scheduler = None
        self.test_files = []

    def setup(self) -> None:
        """Set up the test environment."""
        # Create temporary directories
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_dir = Path(self.temp_dir.name) / "input"
        self.output_dir = Path(self.temp_dir.name) / "output"
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

        # Create minimal test files (don't actually create large files)
        # Just create a few small placeholder files
        for i in range(min(10, self.file_count)):
            file_path = self.input_dir / f"test_video_{i+1}_1080p.mp4"
            with open(file_path, "wb") as f:
                f.write(b"test")
            self.test_files.append(file_path)

        # Create config
        self.config = Config()
        self.config.input_folder = self.input_dir
        self.config.output_folder = self.output_dir
        self.config.max_parallel_jobs = 4
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
            "audio_bitrates": ["192k", "128k", "96k", "64k"],
        }

        # Create logger
        self.logger = Logger(level="INFO")

        # Create mocked file manager and encoder
        self.file_manager = MagicMock(spec=FileManager)
        self.encoder = MagicMock(spec=FFmpegEncoder)

        # Configure mocks
        self.file_manager.validate_files.return_value = (
            [
                Path(self.input_dir / f"test_video_{i+1}_1080p.mp4")
                for i in range(self.file_count)
            ],
            [],
        )

        # Create scheduler
        self.scheduler = ProcessingScheduler(
            self.config, self.logger, self.file_manager, self.encoder
        )

    def teardown(self) -> None:
        """Clean up the test environment."""
        if hasattr(self.scheduler, "is_running"):
            self.scheduler.is_running = False
        if self.temp_dir:
            self.temp_dir.cleanup()

    @patch("pyprocessor.processing.scheduler.ProcessPoolExecutor")
    @patch("pyprocessor.processing.scheduler.Manager")
    def run_iteration(
        self, mock_manager_class, mock_executor_class
    ) -> PerformanceResult:
        """Run a single iteration of the test."""
        # Mock the manager and queues
        mock_manager = MagicMock()
        mock_queue = MagicMock()
        mock_queue.get.side_effect = Exception("Empty queue")
        mock_manager.Queue.return_value = mock_queue
        mock_manager_class.return_value = mock_manager

        # Mock the executor
        mock_executor = MagicMock(spec=ProcessPoolExecutor)
        mock_future = MagicMock()
        mock_future.result.return_value = (
            "output_file.mp4",
            True,
            8.33,
            None,
        )  # Updated to match expected format
        mock_executor.submit.return_value = mock_future
        mock_executor_class.return_value.__enter__.return_value = mock_executor

        # Time the task submission
        _, execution_time, memory_usage = time_and_memory_function(
            self.scheduler.process_videos
        )
        return PerformanceResult(execution_time, memory_usage)


class ProgressTrackingPerformanceTest(PerformanceTest):
    """Test the performance of progress tracking in the scheduler."""

    def __init__(self, file_count: int, iterations: int = 1000):
        """
        Initialize the test.

        Args:
            file_count: Number of files to track
            iterations: Number of iterations to run
        """
        super().__init__(f"Progress Tracking ({file_count} files)", iterations)
        self.file_count = file_count
        self.temp_dir = None
        self.input_dir = None
        self.output_dir = None
        self.config = None
        self.logger = None
        self.file_manager = None
        self.encoder = None
        self.scheduler = None

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
        self.config.max_parallel_jobs = 4

        # Create logger
        self.logger = Logger(level="INFO")

        # Create mocked file manager and encoder
        self.file_manager = MagicMock(spec=FileManager)
        self.encoder = MagicMock(spec=FFmpegEncoder)

        # Create scheduler
        self.scheduler = ProcessingScheduler(
            self.config, self.logger, self.file_manager, self.encoder
        )

        # Set up progress tracking state
        self.scheduler.total_files = self.file_count
        self.scheduler.processed_count = self.file_count // 2  # Half processed

    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.temp_dir:
            self.temp_dir.cleanup()

    def run_iteration(self) -> PerformanceResult:
        """Run a single iteration of the test."""
        _, execution_time, memory_usage = time_and_memory_function(
            self.scheduler.get_progress
        )
        return PerformanceResult(execution_time, memory_usage)


@patch("pyprocessor.processing.scheduler.ProcessPoolExecutor")
def test_scheduler_initialization_performance(mock_executor_class):
    """Test the performance of scheduler initialization."""
    test = SchedulerInitializationPerformanceTest()
    results = test.run()
    test.print_results(results)

    # Assert that the performance is reasonable
    assert results["avg_time"] < 0.01, "Scheduler initialization is too slow"


@patch("pyprocessor.processing.scheduler.ProcessPoolExecutor")
@patch("pyprocessor.processing.scheduler.Manager")
def test_task_submission_performance(mock_manager_class, mock_executor_class):
    """Test the performance of task submission with different file counts."""
    # Use smaller file counts to avoid excessive test duration
    file_counts = [10, 50]

    # Mock the manager and queues
    mock_manager = MagicMock()
    mock_queue = MagicMock()
    mock_manager.Queue.return_value = mock_queue
    mock_manager_class.return_value = mock_manager

    for file_count in file_counts:
        test = TaskSubmissionPerformanceTest(file_count)
        results = test.run()
        test.print_results(results)

        # Assert that the performance is reasonable
        if file_count == 10:
            assert (
                results["avg_time"] < 0.1
            ), f"Task submission for {file_count} files is too slow"
        elif file_count == 50:
            assert (
                results["avg_time"] < 0.5
            ), f"Task submission for {file_count} files is too slow"


def test_progress_tracking_performance():
    """Test the performance of progress tracking with different file counts."""
    # Use smaller file counts to avoid excessive test duration
    file_counts = [10, 100, 1000]

    for file_count in file_counts:
        test = ProgressTrackingPerformanceTest(file_count)
        results = test.run()
        test.print_results(results)

        # Assert that the performance is reasonable
        assert (
            results["avg_time"] < 0.001
        ), f"Progress tracking for {file_count} files is too slow"


if __name__ == "__main__":
    test_scheduler_initialization_performance()
    test_task_submission_performance()
    test_progress_tracking_performance()
