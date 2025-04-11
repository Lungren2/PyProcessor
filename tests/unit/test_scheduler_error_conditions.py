"""
Unit tests for processing scheduler error conditions.
"""
import pytest
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from concurrent.futures import ProcessPoolExecutor, TimeoutError, CancelledError

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the modules to test
from video_processor.utils.config import Config
from video_processor.utils.logging import Logger
from video_processor.processing.file_manager import FileManager
from video_processor.processing.encoder import FFmpegEncoder
from video_processor.processing.scheduler import ProcessingScheduler

class TestSchedulerErrorConditions:
    """Test error conditions in the ProcessingScheduler class"""
    
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
            "Another_Movie_720p.mp4"
        ]
        
        for filename in self.test_files:
            with open(self.input_dir / filename, 'w') as f:
                f.write("Test content")
        
        # Create config
        self.config = Config()
        self.config.input_folder = self.input_dir
        self.config.output_folder = self.output_dir
        self.config.max_parallel_jobs = 2
        self.config.file_validation_pattern = r".+_\d+p\.mp4$"
        
        # Create logger
        self.logger = Logger(level="INFO")
        
        # Create mocked file manager and encoder
        self.file_manager = MagicMock(spec=FileManager)
        self.encoder = MagicMock(spec=FFmpegEncoder)
        
        # Configure mocks
        self.file_manager.validate_files.return_value = (
            [Path(self.input_dir / filename) for filename in self.test_files],
            []
        )
        
        # Create scheduler
        self.scheduler = ProcessingScheduler(self.config, self.logger, self.file_manager, self.encoder)
    
    def teardown_method(self):
        """Clean up after each test method"""
        self.temp_dir.cleanup()
    
    @patch('video_processor.processing.scheduler.ProcessPoolExecutor')
    def test_process_videos_with_no_valid_files(self, mock_executor_class):
        """Test processing videos with no valid files"""
        # Mock the file manager to return no valid files
        self.file_manager.validate_files.return_value = ([], [])
        
        # Process videos
        result = self.scheduler.process_videos()
        
        # Verify the result
        assert result is False
        
        # Verify that the executor was not used
        mock_executor_class.assert_not_called()
    
    @patch('video_processor.processing.scheduler.ProcessPoolExecutor')
    def test_process_videos_with_executor_exception(self, mock_executor_class):
        """Test processing videos with an executor exception"""
        # Mock the executor to raise an exception
        mock_executor_class.side_effect = Exception("Executor error")
        
        # Process videos
        result = self.scheduler.process_videos()
        
        # Verify the result
        assert result is False
    
    @patch('video_processor.processing.scheduler.ProcessPoolExecutor')
    def test_process_videos_with_submit_exception(self, mock_executor_class):
        """Test processing videos with a submit exception"""
        # Mock the executor's submit method to raise an exception
        mock_executor = MagicMock(spec=ProcessPoolExecutor)
        mock_executor.submit.side_effect = Exception("Submit error")
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        
        # Process videos
        result = self.scheduler.process_videos()
        
        # Verify the result
        assert result is False
    
    @patch('video_processor.processing.scheduler.ProcessPoolExecutor')
    def test_process_videos_with_future_exception(self, mock_executor_class):
        """Test processing videos with a future exception"""
        # Mock the executor's submit method to return a future that raises an exception
        mock_executor = MagicMock(spec=ProcessPoolExecutor)
        mock_future = MagicMock()
        mock_future.result.side_effect = Exception("Future error")
        mock_executor.submit.return_value = mock_future
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        
        # Process videos
        result = self.scheduler.process_videos()
        
        # Verify the result
        assert result is False
    
    @patch('video_processor.processing.scheduler.ProcessPoolExecutor')
    def test_process_videos_with_timeout_error(self, mock_executor_class):
        """Test processing videos with a timeout error"""
        # Mock the executor's submit method to return a future that raises a TimeoutError
        mock_executor = MagicMock(spec=ProcessPoolExecutor)
        mock_future = MagicMock()
        mock_future.result.side_effect = TimeoutError("Future timeout")
        mock_executor.submit.return_value = mock_future
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        
        # Process videos
        result = self.scheduler.process_videos()
        
        # Verify the result
        assert result is False
    
    @patch('video_processor.processing.scheduler.ProcessPoolExecutor')
    def test_process_videos_with_cancelled_error(self, mock_executor_class):
        """Test processing videos with a cancelled error"""
        # Mock the executor's submit method to return a future that raises a CancelledError
        mock_executor = MagicMock(spec=ProcessPoolExecutor)
        mock_future = MagicMock()
        mock_future.result.side_effect = CancelledError("Future cancelled")
        mock_executor.submit.return_value = mock_future
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        
        # Process videos
        result = self.scheduler.process_videos()
        
        # Verify the result
        assert result is False
    
    @patch('video_processor.processing.scheduler.ProcessPoolExecutor')
    def test_process_videos_with_mixed_results(self, mock_executor_class):
        """Test processing videos with mixed results (success and failure)"""
        # Mock the executor's submit method to return futures with mixed results
        mock_executor = MagicMock(spec=ProcessPoolExecutor)
        
        # Create mock futures
        mock_success_future = MagicMock()
        mock_success_future.result.return_value = (True, "success_file.mp4", "1080p")
        
        mock_failure_future = MagicMock()
        mock_failure_future.result.return_value = (False, "failure_file.mp4", None)
        
        # Set up the futures to be returned in sequence
        mock_executor.submit.side_effect = [mock_success_future, mock_failure_future]
        
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        
        # Process videos
        result = self.scheduler.process_videos()
        
        # Verify the result
        assert result is False  # Should return False if any file fails
    
    @patch('video_processor.processing.scheduler.ProcessPoolExecutor')
    def test_process_videos_with_all_failures(self, mock_executor_class):
        """Test processing videos with all failures"""
        # Mock the executor's submit method to return futures with all failures
        mock_executor = MagicMock(spec=ProcessPoolExecutor)
        
        # Create mock futures
        mock_failure_future = MagicMock()
        mock_failure_future.result.return_value = (False, "failure_file.mp4", None)
        
        # Set up the futures to be returned in sequence
        mock_executor.submit.side_effect = [mock_failure_future, mock_failure_future]
        
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        
        # Process videos
        result = self.scheduler.process_videos()
        
        # Verify the result
        assert result is False  # Should return False if all files fail
    
    @patch('video_processor.processing.scheduler.ProcessPoolExecutor')
    def test_process_videos_with_invalid_result_format(self, mock_executor_class):
        """Test processing videos with invalid result format"""
        # Mock the executor's submit method to return futures with invalid result format
        mock_executor = MagicMock(spec=ProcessPoolExecutor)
        
        # Create mock futures
        mock_invalid_future = MagicMock()
        mock_invalid_future.result.return_value = "Invalid result format"  # Not a tuple
        
        # Set up the futures to be returned in sequence
        mock_executor.submit.side_effect = [mock_invalid_future, mock_invalid_future]
        
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        
        # Process videos
        result = self.scheduler.process_videos()
        
        # Verify the result
        assert result is False  # Should return False if results are invalid
    
    def test_get_progress_with_no_files(self):
        """Test getting progress with no files"""
        # Set up with no files
        self.scheduler.processed_count = 0
        self.scheduler.total_files = 0
        
        # Get progress
        progress = self.scheduler.get_progress()
        
        # Verify the progress
        assert progress == 0.0  # No files = 0%
    
    def test_request_abort_when_not_running(self):
        """Test requesting abortion when not running"""
        # Ensure is_running is False
        self.scheduler.is_running = False
        
        # Request abort
        result = self.scheduler.request_abort()
        
        # Verify the result
        assert result is False
        assert self.scheduler.abort_requested is False
    
    def test_request_abort_when_running(self):
        """Test requesting abortion when running"""
        # Set is_running to True
        self.scheduler.is_running = True
        
        # Request abort
        result = self.scheduler.request_abort()
        
        # Verify the result
        assert result is True
        assert self.scheduler.abort_requested is True
    
    def test_set_progress_callback_with_invalid_callback(self):
        """Test setting an invalid progress callback"""
        # Set an invalid callback
        self.scheduler.set_progress_callback("not a function")
        
        # Verify that the callback was not set
        assert self.scheduler.progress_callback != "not a function"
    
    def test_set_output_file_callback_with_invalid_callback(self):
        """Test setting an invalid output file callback"""
        # Set an invalid callback
        self.scheduler.set_output_file_callback("not a function")
        
        # Verify that the callback was not set
        assert self.scheduler.output_file_callback != "not a function"
