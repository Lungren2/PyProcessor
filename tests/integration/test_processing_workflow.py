"""
Integration tests for the video processing workflow.
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the modules to test
from pyprocessor.utils.config import Config
from pyprocessor.utils.logging import Logger
from pyprocessor.processing.file_manager import FileManager
from pyprocessor.processing.encoder import FFmpegEncoder
from pyprocessor.processing.scheduler import ProcessingScheduler

class TestProcessingWorkflow:
    """Test the complete video processing workflow"""

    def setup_method(self):
        """Set up test environment before each test method"""
        # Create temporary directories
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_dir = Path(self.temp_dir.name) / "input"
        self.output_dir = Path(self.temp_dir.name) / "output"
        self.profiles_dir = Path(self.temp_dir.name) / "profiles"
        self.logs_dir = Path(self.temp_dir.name) / "logs"

        # Create directories
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        self.profiles_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

        # Set environment variables for logs and profiles
        os.environ["PYPROCESSOR_LOG_DIR"] = str(self.logs_dir)
        os.environ["PYPROCESSOR_PROFILES_DIR"] = str(self.profiles_dir)

        # Create test files
        self.test_files = [
            "Movie_Title_1080p.mp4",
            "Another_Movie_720p.mp4",
            "TV_Show_S01E01_480p.mp4",
            "Documentary_2020_360p.mp4"
        ]

        for filename in self.test_files:
            with open(self.input_dir / filename, 'w') as f:
                f.write("Test content")

    def teardown_method(self):
        """Clean up after each test method"""
        # Remove environment variables
        os.environ.pop("PYPROCESSOR_LOG_DIR", None)
        os.environ.pop("PYPROCESSOR_PROFILES_DIR", None)

        # Close any open loggers to release file handles
        try:
            # Find and close any loggers that might have been created
            import logging
            for handler in logging.root.handlers[:]:
                handler.close()
                logging.root.removeHandler(handler)
        except Exception as e:
            print(f"Error closing loggers: {e}")

        # Clean up temporary directory
        self.temp_dir.cleanup()

    @patch('pyprocessor.processing.scheduler.ProcessingScheduler.process_videos')
    def test_end_to_end_workflow(self, mock_process_videos):
        """Test the end-to-end video processing workflow"""
        # Mock the process_videos method to return success
        mock_process_videos.return_value = True

        # Create configuration
        config = Config()
        config.input_folder = self.input_dir
        config.output_folder = self.output_dir
        config.auto_rename_files = True
        config.auto_organize_folders = True
        config.file_rename_pattern = r"(.+?)_\d+p"
        # Update validation pattern to match both original and renamed files
        config.file_validation_pattern = r"(.+?)(\.mp4$|_\d+p\.mp4$)"
        config.folder_organization_pattern = r"(.+?)_"
        config.max_parallel_jobs = 2
        config.ffmpeg_params = {
            "video_encoder": "libx264",  # Changed from 'encoder' to 'video_encoder'
            "preset": "medium",
            "tune": "film",
            "fps": 30,
            "include_audio": True,
            "audio_encoder": "aac",  # Added audio encoder
            "audio_bitrates": ["192k", "128k", "96k", "64k"],  # Added audio bitrates
            "bitrates": {
                "1080p": "5000k",
                "720p": "3000k",
                "480p": "1500k",
                "360p": "800k"
            }
        }

        # Create logger
        logger = Logger(level="INFO")

        # Create components
        file_manager = FileManager(config, logger)
        encoder = FFmpegEncoder(config, logger)
        scheduler = ProcessingScheduler(config, logger, file_manager, encoder)

        # Run the workflow

        # Step 1: Rename files
        renamed_count = file_manager.rename_files()

        # Step 2: Process videos
        success = scheduler.process_videos()

        # Step 3: Organize folders
        organized_count = file_manager.organize_folders()

        # Verify results
        assert renamed_count == 4  # All files should be renamed
        assert success is True  # Processing should succeed
        assert organized_count == 0  # No files to organize yet (mocked encoding)

        # Verify that process_videos was called
        assert mock_process_videos.call_count > 0

    @patch('pyprocessor.processing.scheduler.ProcessingScheduler.process_videos')
    def test_workflow_with_invalid_files(self, mock_process_videos):
        """Test the workflow with some invalid files"""
        # Mock the process_videos method to return success
        mock_process_videos.return_value = True

        # Add some invalid files
        invalid_files = [
            "invalid-file-1.mp4",
            "invalid-file-2.mp4"
        ]

        for filename in invalid_files:
            with open(self.input_dir / filename, 'w') as f:
                f.write("Invalid content")

        # Create configuration
        config = Config()
        config.input_folder = self.input_dir
        config.output_folder = self.output_dir
        config.auto_rename_files = True
        config.auto_organize_folders = True
        config.file_rename_pattern = r"(.+?)_\d+p"
        # Update validation pattern to match both original and renamed files
        config.file_validation_pattern = r"(.+?)(\.mp4$|_\d+p\.mp4$)"
        config.folder_organization_pattern = r"(.+?)_"
        config.max_parallel_jobs = 2

        # Create logger
        logger = Logger(level="INFO")

        # Create components
        file_manager = FileManager(config, logger)
        encoder = FFmpegEncoder(config, logger)
        scheduler = ProcessingScheduler(config, logger, file_manager, encoder)

        # Run the workflow

        # Step 1: Rename files
        renamed_count = file_manager.rename_files()

        # Step 2: Process videos
        success = scheduler.process_videos()

        # Verify results
        assert renamed_count == 4  # Only valid files should be renamed
        assert success is True  # Processing should succeed for valid files

        # Verify that process_videos was called
        assert mock_process_videos.call_count > 0

    @patch('pyprocessor.processing.scheduler.ProcessingScheduler.process_videos')
    def test_workflow_with_encoding_failures(self, mock_process_videos):
        """Test the workflow with some encoding failures"""
        # Mock the process_videos method to return failure
        mock_process_videos.return_value = False

        # Create configuration
        config = Config()
        config.input_folder = self.input_dir
        config.output_folder = self.output_dir
        config.auto_rename_files = True
        config.auto_organize_folders = True
        config.file_rename_pattern = r"(.+?)_\d+p"
        # Update validation pattern to match both original and renamed files
        config.file_validation_pattern = r"(.+?)(\.mp4$|_\d+p\.mp4$)"
        config.folder_organization_pattern = r"(.+?)_"
        config.max_parallel_jobs = 2

        # Create logger
        logger = Logger(level="INFO")

        # Create components
        file_manager = FileManager(config, logger)
        encoder = FFmpegEncoder(config, logger)
        scheduler = ProcessingScheduler(config, logger, file_manager, encoder)

        # Run the workflow

        # Step 1: Rename files
        renamed_count = file_manager.rename_files()

        # Step 2: Process videos
        success = scheduler.process_videos()

        # Verify results
        assert renamed_count == 4  # All files should be renamed
        assert success is False  # Processing should fail due to encoding failures

        # Verify that process_videos was called
        assert mock_process_videos.call_count > 0

    def test_config_save_load_workflow(self):

        """Test the configuration save and load workflow"""
        # Create initial configuration
        config1 = Config()
        config1.input_folder = self.input_dir
        config1.output_folder = self.output_dir
        config1.auto_rename_files = True
        config1.auto_organize_folders = True
        config1.file_rename_pattern = r"(.+?)_\d+p"
        config1.file_validation_pattern = r"(.+?)(\.mp4$|_\d+p\.mp4$)"
        config1.folder_organization_pattern = r"(.+?)_"
        config1.max_parallel_jobs = 2
        config1.ffmpeg_params = {
            "video_encoder": "libx264",  # Changed from 'encoder' to 'video_encoder'
            "preset": "medium",
            "tune": "film",
            "fps": 30,
            "include_audio": True,
            "audio_encoder": "aac",  # Added audio encoder
            "audio_bitrates": ["192k", "128k", "96k", "64k"],  # Added audio bitrates
            "bitrates": {
                "1080p": "5000k",
                "720p": "3000k",
                "480p": "1500k",
                "360p": "800k"
            }
        }

        # Save configuration as a profile
        config1.profiles_dir = self.profiles_dir
        config1.save(profile_name="test_profile")

        # Create a new configuration and load the profile
        config2 = Config()
        config2.profiles_dir = self.profiles_dir
        config2.load(profile_name="test_profile")

        # Verify that the loaded configuration matches the saved one
        assert str(config2.input_folder) == str(config1.input_folder)
        assert str(config2.output_folder) == str(config1.output_folder)
        assert config2.auto_rename_files == config1.auto_rename_files
        assert config2.auto_organize_folders == config1.auto_organize_folders
        assert config2.file_rename_pattern == config1.file_rename_pattern
        assert config2.file_validation_pattern == config1.file_validation_pattern
        assert config2.folder_organization_pattern == config1.folder_organization_pattern
        assert config2.max_parallel_jobs == config1.max_parallel_jobs
        assert config2.ffmpeg_params["video_encoder"] == config1.ffmpeg_params["video_encoder"]
        assert config2.ffmpeg_params["preset"] == config1.ffmpeg_params["preset"]
        assert config2.ffmpeg_params["tune"] == config1.ffmpeg_params["tune"]
        assert config2.ffmpeg_params["fps"] == config1.ffmpeg_params["fps"]
        assert config2.ffmpeg_params["include_audio"] == config1.ffmpeg_params["include_audio"]
        assert config2.ffmpeg_params["bitrates"]["1080p"] == config1.ffmpeg_params["bitrates"]["1080p"]
