"""
Unit tests for the file management system.
"""
import pytest
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the modules to test
from video_processor.utils.config import Config
from video_processor.utils.logging import Logger
from video_processor.processing.file_manager import FileManager

class TestFileManager:
    """Test the FileManager class functionality"""
    
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
            "invalid-filename.mp4"
        ]
        
        for filename in self.test_files:
            with open(self.input_dir / filename, 'w') as f:
                f.write("Test content")
        
        # Create config
        self.config = Config()
        self.config.input_folder = self.input_dir
        self.config.output_folder = self.output_dir
        self.config.auto_rename_files = True
        self.config.auto_organize_folders = True
        self.config.file_rename_pattern = r"(.+?)_\d+p"
        self.config.file_validation_pattern = r".+_\d+p\.mp4$"
        self.config.folder_organization_pattern = r"(.+?)_"
        
        # Create logger
        self.logger = Logger(level="INFO")
        
        # Create file manager
        self.file_manager = FileManager(self.config, self.logger)
    
    def teardown_method(self):
        """Clean up after each test method"""
        self.temp_dir.cleanup()
    
    def test_initialization(self):
        """Test that the FileManager initializes correctly"""
        assert self.file_manager.input_folder == self.input_dir
        assert self.file_manager.output_folder == self.output_dir
        assert self.file_manager.config == self.config
        assert self.file_manager.logger == self.logger
    
    def test_validate_files(self):
        """Test file validation based on patterns"""
        valid_files, invalid_files = self.file_manager.validate_files()
        
        # Check that valid files are correctly identified
        assert len(valid_files) == 4  # All except "invalid-filename.mp4"
        assert len(invalid_files) == 1
        assert "invalid-filename.mp4" in invalid_files
        
        # Check that all valid files are Path objects
        for file in valid_files:
            assert isinstance(file, Path)
    
    def test_rename_files(self):
        """Test file renaming functionality"""
        # Enable auto-rename
        self.config.auto_rename_files = True
        
        # Rename files
        renamed_count = self.file_manager.rename_files()
        
        # Check that files were renamed
        assert renamed_count == 4  # All valid files should be renamed
        
        # Check that renamed files exist
        expected_files = [
            "Movie_Title.mp4",
            "Another_Movie.mp4",
            "TV_Show_S01E01.mp4",
            "Documentary_2020.mp4"
        ]
        
        for filename in expected_files:
            assert (self.input_dir / filename).exists()
    
    def test_rename_files_disabled(self):
        """Test that file renaming is skipped when disabled"""
        # Disable auto-rename
        self.config.auto_rename_files = False
        
        # Attempt to rename files
        renamed_count = self.file_manager.rename_files()
        
        # Check that no files were renamed
        assert renamed_count == 0
        
        # Check that original files still exist
        for filename in self.test_files:
            assert (self.input_dir / filename).exists()
    
    def test_organize_folders(self):
        """Test folder organization functionality"""
        # Enable auto-organize
        self.config.auto_organize_folders = True
        
        # Create some output files to organize
        output_files = [
            "Movie_Title_1080p.mp4",
            "Another_Movie_720p.mp4",
            "TV_Show_S01E01_480p.mp4",
            "Documentary_2020_360p.mp4"
        ]
        
        for filename in output_files:
            with open(self.output_dir / filename, 'w') as f:
                f.write("Test content")
        
        # Organize folders
        organized_count = self.file_manager.organize_folders()
        
        # Check that folders were created and files moved
        expected_folders = [
            "Movie",
            "Another",
            "TV",
            "Documentary"
        ]
        
        for folder in expected_folders:
            assert (self.output_dir / folder).exists()
            assert (self.output_dir / folder).is_dir()
        
        # Check that files were moved to their respective folders
        assert (self.output_dir / "Movie" / "Movie_Title_1080p.mp4").exists()
        assert (self.output_dir / "Another" / "Another_Movie_720p.mp4").exists()
        assert (self.output_dir / "TV" / "TV_Show_S01E01_480p.mp4").exists()
        assert (self.output_dir / "Documentary" / "Documentary_2020_360p.mp4").exists()
    
    def test_organize_folders_disabled(self):
        """Test that folder organization is skipped when disabled"""
        # Disable auto-organize
        self.config.auto_organize_folders = False
        
        # Create some output files
        output_files = [
            "Movie_Title_1080p.mp4",
            "Another_Movie_720p.mp4"
        ]
        
        for filename in output_files:
            with open(self.output_dir / filename, 'w') as f:
                f.write("Test content")
        
        # Attempt to organize folders
        organized_count = self.file_manager.organize_folders()
        
        # Check that no folders were created
        assert organized_count == 0
        
        # Check that files remain in the output directory
        for filename in output_files:
            assert (self.output_dir / filename).exists()
            assert (self.output_dir / filename).is_file()
    
    def test_handle_existing_files(self):
        """Test handling of existing files during renaming"""
        # Create a file that would conflict with a renamed file
        with open(self.input_dir / "Movie_Title.mp4", 'w') as f:
            f.write("Existing file")
        
        # Rename files
        renamed_count = self.file_manager.rename_files()
        
        # Check that only non-conflicting files were renamed
        assert renamed_count == 3  # One less than before due to conflict
        
        # Check that both the original and existing files still exist
        assert (self.input_dir / "Movie_Title_1080p.mp4").exists()
        assert (self.input_dir / "Movie_Title.mp4").exists()
    
    def test_custom_rename_pattern(self):
        """Test renaming with a custom pattern"""
        # Set a custom rename pattern
        self.config.file_rename_pattern = r"(.+?)_S\d+E\d+"
        
        # Rename files
        renamed_count = self.file_manager.rename_files()
        
        # Only the TV show file should match this pattern
        assert renamed_count == 1
        assert (self.input_dir / "TV_Show.mp4").exists()
    
    def test_custom_validation_pattern(self):
        """Test validation with a custom pattern"""
        # Set a custom validation pattern that only matches TV shows
        self.config.file_validation_pattern = r".+_S\d+E\d+_\d+p\.mp4$"
        
        # Validate files
        valid_files, invalid_files = self.file_manager.validate_files()
        
        # Only the TV show file should be valid
        assert len(valid_files) == 1
        assert str(valid_files[0]).endswith("TV_Show_S01E01_480p.mp4")
        assert len(invalid_files) == 4
