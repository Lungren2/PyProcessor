"""
Unit tests for file manager edge cases and error handling.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import the modules to test
from pyprocessor.utils.config import Config
from pyprocessor.utils.logging import Logger
from pyprocessor.processing.file_manager import FileManager


class TestFileManagerEdgeCases:
    """Test edge cases and error handling in the FileManager class"""

    def setup_method(self):
        """Set up test environment before each test method"""
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

    def test_empty_input_directory(self):
        """Test with an empty input directory"""
        # Input directory is already empty

        # Validate files
        valid_files, invalid_files = self.file_manager.validate_files()

        # Check that no files were found
        assert len(valid_files) == 0
        assert len(invalid_files) == 0

        # Rename files
        renamed_count = self.file_manager.rename_files()

        # Check that no files were renamed
        assert renamed_count == 0

    def test_nonexistent_input_directory(self):
        """Test with a nonexistent input directory"""
        # Set a nonexistent input directory
        nonexistent_dir = Path(self.temp_dir.name) / "nonexistent"
        self.config.input_folder = nonexistent_dir

        # Validate files
        valid_files, invalid_files = self.file_manager.validate_files()

        # Check that no files were found
        assert len(valid_files) == 0
        assert len(invalid_files) == 0

        # Rename files
        renamed_count = self.file_manager.rename_files()

        # Check that no files were renamed
        assert renamed_count == 0

    def test_nonexistent_output_directory(self):
        """Test with a nonexistent output directory"""
        # Set a nonexistent output directory
        nonexistent_dir = Path(self.temp_dir.name) / "nonexistent"
        self.config.output_folder = nonexistent_dir

        # Create some test files
        test_files = ["Movie_Title_1080p.mp4", "Another_Movie_720p.mp4"]
        for filename in test_files:
            with open(self.input_dir / filename, "w") as f:
                f.write("Test content")

        # Organize folders
        organized_count = self.file_manager.organize_folders()

        # Check that no folders were organized
        assert organized_count == 0

    def test_readonly_input_directory(self):
        """Test with a read-only input directory"""
        # Create some test files
        test_files = ["Movie_Title_1080p.mp4", "Another_Movie_720p.mp4"]
        for filename in test_files:
            with open(self.input_dir / filename, "w") as f:
                f.write("Test content")

        # Make the input directory read-only
        os.chmod(self.input_dir, 0o500)  # r-x------

        try:
            # Rename files
            renamed_count = self.file_manager.rename_files()

            # Check that no files were renamed
            assert renamed_count == 0
        finally:
            # Restore permissions for cleanup
            os.chmod(self.input_dir, 0o700)  # rwx------

    def test_readonly_output_directory(self):
        """Test with a read-only output directory"""
        # Create some test files in the output directory
        test_files = ["Movie_Title_1080p.mp4", "Another_Movie_720p.mp4"]
        for filename in test_files:
            with open(self.output_dir / filename, "w") as f:
                f.write("Test content")

        # Make the output directory read-only
        os.chmod(self.output_dir, 0o500)  # r-x------

        try:
            # Organize folders
            organized_count = self.file_manager.organize_folders()

            # Check that no folders were organized
            assert organized_count == 0
        finally:
            # Restore permissions for cleanup
            os.chmod(self.output_dir, 0o700)  # rwx------

    def test_invalid_rename_pattern(self):
        """Test with an invalid rename pattern"""
        # Set an invalid rename pattern
        self.config.file_rename_pattern = "["  # Invalid regex

        # Create some test files
        test_files = ["Movie_Title_1080p.mp4", "Another_Movie_720p.mp4"]
        for filename in test_files:
            with open(self.input_dir / filename, "w") as f:
                f.write("Test content")

        # Rename files
        renamed_count = self.file_manager.rename_files()

        # Check that no files were renamed
        assert renamed_count == 0

    def test_invalid_validation_pattern(self):
        """Test with an invalid validation pattern"""
        # Set an invalid validation pattern
        self.config.file_validation_pattern = "["  # Invalid regex

        # Create some test files
        test_files = ["Movie_Title_1080p.mp4", "Another_Movie_720p.mp4"]
        for filename in test_files:
            with open(self.input_dir / filename, "w") as f:
                f.write("Test content")

        # Validate files
        valid_files, invalid_files = self.file_manager.validate_files()

        # Check that no files were validated
        assert len(valid_files) == 0
        assert len(invalid_files) == 0

    def test_invalid_organization_pattern(self):
        """Test with an invalid organization pattern"""
        # Set an invalid organization pattern
        self.config.folder_organization_pattern = "["  # Invalid regex

        # Create some test files in the output directory
        test_files = ["Movie_Title_1080p.mp4", "Another_Movie_720p.mp4"]
        for filename in test_files:
            with open(self.output_dir / filename, "w") as f:
                f.write("Test content")

        # Organize folders
        organized_count = self.file_manager.organize_folders()

        # Check that no folders were organized
        assert organized_count == 0

    def test_rename_with_permission_error(self):
        """Test renaming with permission errors"""
        # Create a test file
        test_file = self.input_dir / "Movie_Title_1080p.mp4"
        with open(test_file, "w") as f:
            f.write("Test content")

        # Make the file read-only
        os.chmod(test_file, 0o400)  # r--------

        try:
            # Rename files
            renamed_count = self.file_manager.rename_files()

            # Check that no files were renamed
            assert renamed_count == 0
        finally:
            # Restore permissions for cleanup
            os.chmod(test_file, 0o600)  # rw-------

    def test_organize_with_permission_error(self):
        """Test organizing with permission errors"""
        # Create a test file in the output directory
        test_file = self.output_dir / "Movie_Title_1080p.mp4"
        with open(test_file, "w") as f:
            f.write("Test content")

        # Make the file read-only
        os.chmod(test_file, 0o400)  # r--------

        try:
            # Organize folders
            organized_count = self.file_manager.organize_folders()

            # Check that no folders were organized
            assert organized_count == 0
        finally:
            # Restore permissions for cleanup
            os.chmod(test_file, 0o600)  # rw-------

    def test_rename_with_existing_destination(self):
        """Test renaming when destination already exists"""
        # Create test files
        with open(self.input_dir / "Movie_Title_1080p.mp4", "w") as f:
            f.write("Original file")

        # Create a file that would conflict with the renamed file
        with open(self.input_dir / "Movie_Title.mp4", "w") as f:
            f.write("Existing file")

        # Rename files
        renamed_count = self.file_manager.rename_files()

        # Check that no files were renamed
        assert renamed_count == 0

        # Check that both files still exist
        assert (self.input_dir / "Movie_Title_1080p.mp4").exists()
        assert (self.input_dir / "Movie_Title.mp4").exists()

    def test_organize_with_existing_destination(self):
        """Test organizing when destination already exists"""
        # Create a folder that would conflict with the organized folder
        movie_dir = self.output_dir / "Movie"
        movie_dir.mkdir(exist_ok=True)

        # Create a file in the folder
        with open(movie_dir / "existing_file.mp4", "w") as f:
            f.write("Existing file")

        # Create a test file in the output directory
        with open(self.output_dir / "Movie_Title_1080p.mp4", "w") as f:
            f.write("Test content")

        # Organize folders
        organized_count = self.file_manager.organize_folders()

        # Check that the file was organized
        assert organized_count == 1

        # Check that the file was moved to the existing folder
        assert (movie_dir / "Movie_Title_1080p.mp4").exists()
        assert (movie_dir / "existing_file.mp4").exists()

    def test_organize_with_nested_folders(self):
        """Test organizing with nested folders"""
        # Create a nested folder structure
        nested_dir = self.output_dir / "Nested" / "Folder"
        nested_dir.mkdir(parents=True, exist_ok=True)

        # Create a test file in the nested folder
        with open(nested_dir / "Nested_Folder_1080p.mp4", "w") as f:
            f.write("Test content")

        # Organize folders
        organized_count = self.file_manager.organize_folders()

        # Check that the file was organized
        assert organized_count == 1

        # Check that the file was moved to a new folder
        assert (self.output_dir / "Nested" / "Nested_Folder_1080p.mp4").exists()

    def test_rename_with_special_characters(self):
        """Test renaming files with special characters"""
        # Create test files with special characters
        special_files = [
            "Movie-With-Dashes_1080p.mp4",
            "Movie With Spaces_1080p.mp4",
            "Movie.With.Dots_1080p.mp4",
            "Movie_With_Underscores_1080p.mp4",
            "Movie(With)Parentheses_1080p.mp4",
            "Movie[With]Brackets_1080p.mp4",
        ]

        for filename in special_files:
            with open(self.input_dir / filename, "w") as f:
                f.write("Test content")

        # Rename files
        renamed_count = self.file_manager.rename_files()

        # Check that all files were renamed
        assert renamed_count == 6

        # Check that renamed files exist
        assert (self.input_dir / "Movie-With-Dashes.mp4").exists()
        assert (self.input_dir / "Movie With Spaces.mp4").exists()
        assert (self.input_dir / "Movie.With.Dots.mp4").exists()
        assert (self.input_dir / "Movie_With_Underscores.mp4").exists()
        assert (self.input_dir / "Movie(With)Parentheses.mp4").exists()
        assert (self.input_dir / "Movie[With]Brackets.mp4").exists()
