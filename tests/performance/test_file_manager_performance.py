"""
Performance tests for the file manager component.
"""
import os
import sys
import tempfile
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the modules to test
from pyprocessor.utils.config import Config
from pyprocessor.utils.logging import Logger
from pyprocessor.processing.file_manager import FileManager

# Import performance test base
from tests.performance.test_performance_base import PerformanceTest, PerformanceResult, time_and_memory_function, create_test_videos

class FileValidationPerformanceTest(PerformanceTest):
    """Test the performance of file validation."""

    def __init__(self, file_count: int, iterations: int = 5):
        """
        Initialize the test.

        Args:
            file_count: Number of files to validate
            iterations: Number of iterations to run
        """
        super().__init__(f"File Validation ({file_count} files)", iterations)
        self.file_count = file_count
        self.temp_dir = None
        self.input_dir = None
        self.output_dir = None
        self.config = None
        self.logger = None
        self.file_manager = None
        self.test_files = []

    def setup(self) -> None:
        """Set up the test environment."""
        # Create temporary directories
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_dir = Path(self.temp_dir.name) / "input"
        self.output_dir = Path(self.temp_dir.name) / "output"
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

        # Create test files
        self.test_files = create_test_videos(self.input_dir, self.file_count, size_mb=1)

        # Create config
        self.config = Config()
        self.config.input_folder = self.input_dir
        self.config.output_folder = self.output_dir
        self.config.file_validation_pattern = r".+_\d+p\.mp4$"

        # Create logger
        self.logger = Logger(level="INFO")

        # Create file manager
        self.file_manager = FileManager(self.config, self.logger)

    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.temp_dir:
            self.temp_dir.cleanup()

    def run_iteration(self) -> PerformanceResult:
        """Run a single iteration of the test."""
        _, execution_time, memory_usage = time_and_memory_function(self.file_manager.validate_files)
        return PerformanceResult(execution_time, memory_usage)

class FileRenamingPerformanceTest(PerformanceTest):
    """Test the performance of file renaming."""

    def __init__(self, file_count: int, iterations: int = 5):
        """
        Initialize the test.

        Args:
            file_count: Number of files to rename
            iterations: Number of iterations to run
        """
        super().__init__(f"File Renaming ({file_count} files)", iterations)
        self.file_count = file_count
        self.temp_dir = None
        self.input_dir = None
        self.output_dir = None
        self.config = None
        self.logger = None
        self.file_manager = None
        self.test_files = []

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
        self.config.auto_rename_files = True
        self.config.file_rename_pattern = r"(.+?)_\d+p"
        self.config.file_validation_pattern = r".+_\d+p\.mp4$"

        # Create logger
        self.logger = Logger(level="INFO")

        # Create file manager
        self.file_manager = FileManager(self.config, self.logger)

    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.temp_dir:
            self.temp_dir.cleanup()

    def run_iteration(self) -> PerformanceResult:
        """Run a single iteration of the test."""
        # Create new test files for each iteration
        self.test_files = create_test_videos(self.input_dir, self.file_count, size_mb=1)

        # Time the renaming operation
        _, execution_time, memory_usage = time_and_memory_function(self.file_manager.rename_files)
        return PerformanceResult(execution_time, memory_usage)

class FolderOrganizationPerformanceTest(PerformanceTest):
    """Test the performance of folder organization."""

    def __init__(self, file_count: int, iterations: int = 5):
        """
        Initialize the test.

        Args:
            file_count: Number of files to organize
            iterations: Number of iterations to run
        """
        super().__init__(f"Folder Organization ({file_count} files)", iterations)
        self.file_count = file_count
        self.temp_dir = None
        self.input_dir = None
        self.output_dir = None
        self.config = None
        self.logger = None
        self.file_manager = None
        self.test_files = []

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
        self.config.auto_organize_folders = True
        self.config.folder_organization_pattern = r"(.+?)_"

        # Create logger
        self.logger = Logger(level="INFO")

        # Create file manager
        self.file_manager = FileManager(self.config, self.logger)

    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.temp_dir:
            self.temp_dir.cleanup()

    def run_iteration(self) -> PerformanceResult:
        """Run a single iteration of the test."""
        # Create new test files in the output directory for each iteration
        self.test_files = create_test_videos(self.output_dir, self.file_count, size_mb=1)

        # Time the organization operation
        _, execution_time, memory_usage = time_and_memory_function(self.file_manager.organize_folders)
        return PerformanceResult(execution_time, memory_usage)

def test_file_validation_performance():
    """Test the performance of file validation with different file counts."""
    file_counts = [10, 100, 1000]

    for file_count in file_counts:
        test = FileValidationPerformanceTest(file_count)
        results = test.run()
        test.print_results(results)

        # Assert that the performance is reasonable
        # These thresholds should be adjusted based on your specific requirements
        if file_count == 10:
            assert results["avg_time"] < 0.1, f"File validation for {file_count} files is too slow"
        elif file_count == 100:
            assert results["avg_time"] < 1.0, f"File validation for {file_count} files is too slow"
        elif file_count == 1000:
            assert results["avg_time"] < 10.0, f"File validation for {file_count} files is too slow"

def test_file_renaming_performance():
    """Test the performance of file renaming with different file counts."""
    file_counts = [10, 100]

    for file_count in file_counts:
        test = FileRenamingPerformanceTest(file_count)
        results = test.run()
        test.print_results(results)

        # Assert that the performance is reasonable
        if file_count == 10:
            assert results["avg_time"] < 0.2, f"File renaming for {file_count} files is too slow"
        elif file_count == 100:
            assert results["avg_time"] < 2.0, f"File renaming for {file_count} files is too slow"

def test_folder_organization_performance():
    """Test the performance of folder organization with different file counts."""
    file_counts = [10, 100]

    for file_count in file_counts:
        test = FolderOrganizationPerformanceTest(file_count)
        results = test.run()
        test.print_results(results)

        # Assert that the performance is reasonable
        if file_count == 10:
            assert results["avg_time"] < 0.2, f"Folder organization for {file_count} files is too slow"
        elif file_count == 100:
            assert results["avg_time"] < 2.0, f"Folder organization for {file_count} files is too slow"

if __name__ == "__main__":
    test_file_validation_performance()
    test_file_renaming_performance()
    test_folder_organization_performance()
