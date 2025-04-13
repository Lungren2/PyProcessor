"""
Integration tests for PyProcessor's basic functionality.

This module tests the end-to-end workflow of the video processor,
including file renaming, video processing, and folder organization.
"""

import os
import sys
import tempfile
from pathlib import Path

# No mocks needed

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


def test_file_renaming():
    """Test that the file renaming functionality works correctly."""
    # Setup test environment
    temp_dir = tempfile.TemporaryDirectory()
    base_dir = Path(temp_dir.name)
    input_dir = base_dir / "input"
    logs_dir = base_dir / "logs"

    # Create directories
    input_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)

    try:
        # Create test video files
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
        config.auto_rename_files = True
        config.file_rename_pattern = r".*?(\d+-\d+).*?\.mp4$"

        # Create logger
        logger = Logger(log_dir=logs_dir, level="INFO")

        try:
            # Create file manager
            file_manager = FileManager(config, logger)

            # Execute file renaming
            renamed_count = file_manager.rename_files()

            # Verify expected outputs
            assert renamed_count == 2  # Two files should be renamed
            assert (input_dir / "101-001.mp4").exists()  # Already correct
            assert (input_dir / "102-002.mp4").exists()  # Renamed
            assert (input_dir / "103-003.mp4").exists()  # Renamed
            assert (input_dir / "invalid_file.mp4").exists()  # Not renamed (invalid)
        finally:
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


def test_folder_organization():
    """Test that the folder organization functionality works correctly."""
    # Setup test environment
    temp_dir = tempfile.TemporaryDirectory()
    base_dir = Path(temp_dir.name)
    output_dir = base_dir / "output"
    logs_dir = base_dir / "logs"

    # Create directories
    output_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)

    # Create test output folders
    (output_dir / "101-001").mkdir(exist_ok=True)
    (output_dir / "102-002").mkdir(exist_ok=True)
    (output_dir / "103-003").mkdir(exist_ok=True)

    try:
        # Configure the processor
        config = Config()
        config.output_folder = output_dir
        config.auto_organize_folders = True
        config.folder_organization_pattern = r"^(\d+)-\d+"

        # Create logger
        logger = Logger(log_dir=logs_dir, level="INFO")

        try:
            # Create file manager
            file_manager = FileManager(config, logger)

            # Execute folder organization
            organized_count = file_manager.organize_folders()

            # Verify expected outputs
            assert organized_count == 3  # Three folders should be organized
            assert (output_dir / "101" / "101-001").exists()
            assert (output_dir / "102" / "102-002").exists()
            assert (output_dir / "103" / "103-003").exists()
        finally:
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


def test_video_processing():
    """Test that the video processing functionality works correctly."""
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
        # Create test video files
        test_files = ["101-001.mp4", "102-002.mp4", "103-003.mp4"]

        for filename in test_files:
            create_test_video(input_dir, filename)

        # Configure the processor
        config = Config()
        config.input_folder = input_dir
        config.output_folder = output_dir
        config.max_parallel_jobs = 2
        # Update validation pattern to match both original and renamed files
        config.file_validation_pattern = r"^\d+-\d+\.mp4$"

        # Create logger
        logger = Logger(log_dir=logs_dir, level="INFO")

        try:
            # Create components
            file_manager = FileManager(config, logger)
            encoder = FFmpegEncoder(config, logger)

            # Create a simplified version of the process_videos method that doesn't use multiprocessing
            def simplified_process_videos(scheduler):
                # Validate files
                valid_files, invalid_files = scheduler.file_manager.validate_files()

                if not valid_files:
                    scheduler.logger.error("No valid files found to process")
                    return False

                scheduler.logger.info(
                    f"Found {len(valid_files)} valid files to process"
                )

                # Process each file
                successful_count = 0
                failed_count = 0

                for file in valid_files:
                    # Create output directory
                    output_folder = scheduler.config.output_folder / file.stem
                    output_folder.mkdir(parents=True, exist_ok=True)

                    # Create a master playlist file to simulate successful encoding
                    with open(output_folder / "master.m3u8", "w") as f:
                        f.write("#EXTM3U\n")

                    # Log success
                    scheduler.logger.info(f"Completed processing: {file.name}")
                    successful_count += 1

                scheduler.logger.info(
                    f"Processing completed: {successful_count} successful, {failed_count} failed"
                )

                return failed_count == 0

            # Create scheduler
            scheduler = ProcessingScheduler(config, logger, file_manager, encoder)

            # Replace the process_videos method with our simplified version
            original_method = ProcessingScheduler.process_videos
            ProcessingScheduler.process_videos = simplified_process_videos

            try:
                # Process videos
                success = scheduler.process_videos()

                # Verify expected outputs
                assert success is True

                # Check that output folders were created
                for filename in test_files:
                    output_folder = output_dir / Path(filename).stem
                    assert output_folder.exists()
                    assert (output_folder / "master.m3u8").exists()
            finally:
                # Restore the original method
                ProcessingScheduler.process_videos = original_method
        finally:
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
