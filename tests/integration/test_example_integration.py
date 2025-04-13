"""
Integration tests for PyProcessor's basic functionality.

This module tests the end-to-end workflow of the video processor,
including file renaming, video processing, and folder organization.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import the modules to test
from pyprocessor.utils.config import Config
from pyprocessor.utils.logging import Logger
from pyprocessor.processing.file_manager import FileManager
from pyprocessor.processing.encoder import FFmpegEncoder
from pyprocessor.processing.scheduler import ProcessingScheduler


def create_test_video(directory, filename, size_mb=1):
    """Create a test video file of the specified size."""
    file_path = directory / filename

    # Create a file with random data
    with open(file_path, "wb") as f:
        f.write(os.urandom(size_mb * 1024 * 1024))

    return file_path


def test_basic_processor_functionality():
    """Test that the basic processor functionality works end-to-end."""
    # Setup test environment with sample input files
    temp_dir = tempfile.TemporaryDirectory()
    base_dir = Path(temp_dir.name)
    input_dir = base_dir / "input"
    output_dir = base_dir / "output"
    logs_dir = base_dir / "logs"

    # Create directories
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)

    try:
        # Create test video files with naming pattern that matches the default pattern
        test_files = [
            "101-001.mp4",  # Already correctly named
            "movie_102-002_1080p.mp4",  # Needs renaming
            "tv_show_103-003_720p.mp4",  # Needs renaming
            "invalid_file.mp4",  # Invalid naming pattern
        ]

        for filename in test_files:
            create_test_video(input_dir, filename)

        # Configure the processor
        config = Config()
        config.input_folder = input_dir
        config.output_folder = output_dir
        config.max_parallel_jobs = 2
        config.auto_rename_files = True
        config.auto_organize_folders = True
        config.file_rename_pattern = r".*?(\d+-\d+).*?\.mp4$"
        # Update validation pattern to match both original and renamed files
        config.file_validation_pattern = r"(^\d+-\d+\.mp4$|.*?\d+-\d+.*?\.mp4$)"
        config.folder_organization_pattern = r"^(\d+)-\d+"

        # Create logger
        logger = Logger(log_dir=logs_dir, level="INFO")

        # Create components
        file_manager = FileManager(config, logger)
        encoder = FFmpegEncoder(config, logger)

        # Mock the encode_video method to avoid actual encoding
        with patch.object(FFmpegEncoder, "encode_video") as mock_encode:
            # Configure the mock to return success and create expected output files
            def mock_encode_side_effect(
                input_file, output_folder, progress_callback=None
            ):
                # Create mock output files
                output_path = Path(output_folder)
                output_path.mkdir(parents=True, exist_ok=True)

                # Create a master playlist file
                with open(output_path / "master.m3u8", "w") as f:
                    f.write("#EXTM3U\n")

                # Create variant playlist files
                for resolution in ["1080p", "720p", "480p", "360p"]:
                    with open(output_path / f"playlist_{resolution}.m3u8", "w") as f:
                        f.write(
                            f"#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION={resolution}\n"
                        )

                # Create segment files
                for i in range(3):
                    with open(output_path / f"segment_{i}.ts", "w") as f:
                        f.write(f"Segment {i} data")

                # Call progress callback if provided
                if progress_callback:
                    progress_callback(input_file.name, 100)

                return True

            # Set the mock to always return True
            mock_encode.return_value = True

            # Create scheduler
            scheduler = ProcessingScheduler(config, logger, file_manager, encoder)

            # Execute processor functionality

            # Step 1: Rename files
            renamed_count = file_manager.rename_files()

            # Step 2: Process videos
            success = scheduler.process_videos()

            # Step 3: Organize folders
            organized_count = file_manager.organize_folders()

            # Verify expected outputs were generated

            # Check that files were renamed correctly
            assert renamed_count == 2  # Two files should be renamed
            assert (input_dir / "101-001.mp4").exists()  # Already correct
            assert (input_dir / "102-002.mp4").exists()  # Renamed
            assert (input_dir / "103-003.mp4").exists()  # Renamed
            assert (input_dir / "invalid_file.mp4").exists()  # Not renamed (invalid)

            # Check that videos were processed
            assert success is True
            assert mock_encode.call_count == 3  # Three valid files should be processed

            # Check that output folders were created
            assert (output_dir / "101-001").exists()
            assert (output_dir / "102-002").exists()
            assert (output_dir / "103-003").exists()

            # Check that master playlists were created
            assert (output_dir / "101-001" / "master.m3u8").exists()
            assert (output_dir / "102-002" / "master.m3u8").exists()
            assert (output_dir / "103-003" / "master.m3u8").exists()

            # Check that folders were organized
            assert organized_count == 3  # Three folders should be organized
            assert (output_dir / "101" / "101-001").exists()
            assert (output_dir / "102" / "102-002").exists()
            assert (output_dir / "103" / "103-003").exists()

            # Check that log files were created
            log_files = list(logs_dir.glob("*.log"))
            assert len(log_files) > 0

            # Close logger to release file handles
            logger.close()

    finally:
        # Close any open loggers to release file handles
        try:
            # Find and close any loggers that might have been created
            import logging

            for handler in logging.root.handlers[:]:
                handler.close()
                logging.root.removeHandler(handler)
        except Exception as e:
            print(f"Error closing loggers: {e}")

        # Cleanup test artifacts
        temp_dir.cleanup()


def test_processor_with_disabled_options():
    """Test processor functionality with renaming and organization disabled."""
    # Setup test environment with sample input files
    temp_dir = tempfile.TemporaryDirectory()
    base_dir = Path(temp_dir.name)
    input_dir = base_dir / "input"
    output_dir = base_dir / "output"
    logs_dir = base_dir / "logs"

    # Create directories
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)

    try:
        # Create test video files
        test_files = [
            "101-001.mp4",
            "movie_102-002_1080p.mp4",
            "tv_show_103-003_720p.mp4",
        ]

        for filename in test_files:
            create_test_video(input_dir, filename)

        # Configure the processor with options disabled
        config = Config()
        config.input_folder = input_dir
        config.output_folder = output_dir
        config.max_parallel_jobs = 2
        config.auto_rename_files = False  # Disable renaming
        config.auto_organize_folders = False  # Disable organization
        config.file_validation_pattern = r".+\.mp4$"  # Accept any MP4 file

        # Create logger
        logger = Logger(log_dir=logs_dir, level="INFO")

        # Create components
        file_manager = FileManager(config, logger)
        encoder = FFmpegEncoder(config, logger)

        # Mock the encode_video method
        with patch.object(FFmpegEncoder, "encode_video") as mock_encode:
            # Configure the mock to return success and create expected output files
            def mock_encode_side_effect(
                input_file, output_folder, progress_callback=None
            ):
                # Create mock output files
                output_path = Path(output_folder)
                output_path.mkdir(parents=True, exist_ok=True)

                # Create a master playlist file
                with open(output_path / "master.m3u8", "w") as f:
                    f.write("#EXTM3U\n")

                return True

            # Set the mock to always return True
            mock_encode.return_value = True

            # Create scheduler
            scheduler = ProcessingScheduler(config, logger, file_manager, encoder)

            # Execute processor functionality

            # Step 1: Rename files (should be skipped)
            renamed_count = file_manager.rename_files()

            # Step 2: Process videos
            success = scheduler.process_videos()

            # Step 3: Organize folders (should be skipped)
            organized_count = file_manager.organize_folders()

            # Verify expected outputs

            # Check that files were not renamed
            assert renamed_count == 0  # No files should be renamed
            assert (
                input_dir / "movie_102-002_1080p.mp4"
            ).exists()  # Original name preserved
            assert (
                input_dir / "tv_show_103-003_720p.mp4"
            ).exists()  # Original name preserved

            # Check that videos were processed
            assert success is True
            assert mock_encode.call_count == 3  # All files should be processed

            # Check that output folders were created with original names
            assert (output_dir / "101-001").exists()
            assert (output_dir / "movie_102-002_1080p").exists()
            assert (output_dir / "tv_show_103-003_720p").exists()

            # Check that folders were not organized
            assert organized_count == 0  # No folders should be organized
            assert not (output_dir / "101").exists()
            assert not (output_dir / "102").exists()
            assert not (output_dir / "103").exists()

            # Close logger to release file handles
            logger.close()

    finally:
        # Close any open loggers to release file handles
        try:
            # Find and close any loggers that might have been created
            import logging

            for handler in logging.root.handlers[:]:
                handler.close()
                logging.root.removeHandler(handler)
        except Exception as e:
            print(f"Error closing loggers: {e}")

        # Cleanup test artifacts
        temp_dir.cleanup()


def test_error_handling():
    """Test that the processor handles errors gracefully."""
    # Setup test environment
    temp_dir = tempfile.TemporaryDirectory()
    base_dir = Path(temp_dir.name)
    input_dir = base_dir / "input"
    output_dir = base_dir / "output"
    logs_dir = base_dir / "logs"

    # Create directories
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)

    try:
        # Create test video file
        test_file = create_test_video(input_dir, "101-001.mp4")

        # Configure the processor
        config = Config()
        config.input_folder = input_dir
        config.output_folder = output_dir

        # Create logger
        logger = Logger(log_dir=logs_dir, level="INFO")

        # Create components
        file_manager = FileManager(config, logger)
        encoder = FFmpegEncoder(config, logger)

        # Mock the encode_video method to simulate an error
        with patch.object(FFmpegEncoder, "encode_video") as mock_encode:
            # Configure the mock to return failure
            mock_encode.return_value = False

            # Create scheduler
            scheduler = ProcessingScheduler(config, logger, file_manager, encoder)

            # Process videos
            success = scheduler.process_videos()

            # Verify that the process failed but didn't crash
            assert success is False
            assert mock_encode.call_count == 1

            # Check that error was logged
            log_files = list(logs_dir.glob("*.log"))
            assert len(log_files) > 0

            # Read the log file to check for error messages
            with open(log_files[0], "r") as f:
                log_content = f.read()
                assert "error" in log_content.lower() or "failed" in log_content.lower()

            # Close logger to release file handles
            logger.close()

    finally:
        # Close any open loggers to release file handles
        try:
            # Find and close any loggers that might have been created
            import logging

            for handler in logging.root.handlers[:]:
                handler.close()
                logging.root.removeHandler(handler)
        except Exception as e:
            print(f"Error closing loggers: {e}")

        # Cleanup test artifacts
        temp_dir.cleanup()
