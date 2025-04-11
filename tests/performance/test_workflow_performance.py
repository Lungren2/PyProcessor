"""
Performance tests for end-to-end workflow processing.
"""
import os
import sys
import time
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from concurrent.futures import ProcessPoolExecutor
from typing import List, Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the modules to test
from video_processor.utils.config import Config
from video_processor.utils.logging import Logger
from video_processor.processing.file_manager import FileManager
from video_processor.processing.encoder import FFmpegEncoder
from video_processor.processing.scheduler import ProcessingScheduler

# Import performance test base
from tests.performance.test_performance_base import PerformanceTest, time_function, create_test_videos

class EndToEndWorkflowPerformanceTest(PerformanceTest):
    """Test the performance of the end-to-end workflow."""
    
    def __init__(self, file_count: int, iterations: int = 3):
        """
        Initialize the test.
        
        Args:
            file_count: Number of files to process
            iterations: Number of iterations to run
        """
        super().__init__(f"End-to-End Workflow ({file_count} files)", iterations)
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
        
        # Create test files with names that need renaming
        self.test_files = []
        for i in range(self.file_count):
            file_path = self.input_dir / f"movie_{i}_1080p.mp4"
            with open(file_path, 'wb') as f:
                f.write(os.urandom(1024 * 1024))  # 1MB file
            self.test_files.append(file_path)
        
        # Create config
        self.config = Config()
        self.config.input_folder = self.input_dir
        self.config.output_folder = self.output_dir
        self.config.auto_rename_files = True
        self.config.auto_organize_folders = True
        self.config.file_rename_pattern = r"(.+?)_\d+p"
        self.config.file_validation_pattern = r".+\.mp4$"
        self.config.folder_organization_pattern = r"(.+?)_"
        self.config.max_parallel_jobs = min(4, os.cpu_count() or 1)
        
        # Create logger
        self.logger = Logger(level="INFO")
        
        # Create file manager
        self.file_manager = FileManager(self.config, self.logger)
        
        # Create encoder
        self.encoder = FFmpegEncoder(self.config, self.logger)
        
        # Create scheduler
        self.scheduler = ProcessingScheduler(self.config, self.logger, self.file_manager, self.encoder)
    
    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.temp_dir:
            self.temp_dir.cleanup()
    
    @patch('video_processor.processing.scheduler.process_video_task')
    @patch('video_processor.processing.scheduler.ProcessPoolExecutor')
    def run_iteration(self, mock_executor_class, mock_process_video_task) -> float:
        """Run a single iteration of the test."""
        # Mock the ProcessPoolExecutor
        mock_executor = MagicMock(spec=ProcessPoolExecutor)
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        
        # Mock the process_video_task function
        mock_process_video_task.return_value = (True, "output_file.mp4", "1080p", None)
        
        # Mock the executor's submit method
        mock_future = MagicMock()
        mock_future.result.return_value = (True, "output_file.mp4", "1080p", None)
        mock_executor.submit.return_value = mock_future
        
        start_time = time.time()
        
        # Step 1: Rename files
        self.file_manager.rename_files()
        
        # Step 2: Process videos
        self.scheduler.process_videos()
        
        # Step 3: Organize folders
        self.file_manager.organize_folders()
        
        end_time = time.time()
        return end_time - start_time

class FileRenamingWorkflowPerformanceTest(PerformanceTest):
    """Test the performance of the file renaming workflow."""
    
    def __init__(self, file_count: int, iterations: int = 3):
        """
        Initialize the test.
        
        Args:
            file_count: Number of files to rename
            iterations: Number of iterations to run
        """
        super().__init__(f"File Renaming Workflow ({file_count} files)", iterations)
        self.file_count = file_count
        self.temp_dir = None
        self.input_dir = None
        self.config = None
        self.logger = None
        self.file_manager = None
        self.test_files = []
    
    def setup(self) -> None:
        """Set up the test environment."""
        # Create temporary directories
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_dir = Path(self.temp_dir.name) / "input"
        self.input_dir.mkdir(exist_ok=True)
        
        # Create test files with names that need renaming
        self.test_files = []
        for i in range(self.file_count):
            file_path = self.input_dir / f"movie_{i}_1080p.mp4"
            with open(file_path, 'wb') as f:
                f.write(os.urandom(1024 * 1024))  # 1MB file
            self.test_files.append(file_path)
        
        # Create config
        self.config = Config()
        self.config.input_folder = self.input_dir
        self.config.auto_rename_files = True
        self.config.file_rename_pattern = r"(.+?)_\d+p"
        
        # Create logger
        self.logger = Logger(level="INFO")
        
        # Create file manager
        self.file_manager = FileManager(self.config, self.logger)
    
    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.temp_dir:
            self.temp_dir.cleanup()
    
    def run_iteration(self) -> float:
        """Run a single iteration of the test."""
        # Reset the test files for each iteration
        for file_path in self.test_files:
            if file_path.exists():
                file_path.unlink()
        
        for i in range(self.file_count):
            file_path = self.input_dir / f"movie_{i}_1080p.mp4"
            with open(file_path, 'wb') as f:
                f.write(os.urandom(1024 * 1024))  # 1MB file
        
        # Time the renaming operation
        _, execution_time = time_function(self.file_manager.rename_files)
        return execution_time

class FileValidationWorkflowPerformanceTest(PerformanceTest):
    """Test the performance of the file validation workflow."""
    
    def __init__(self, file_count: int, iterations: int = 3):
        """
        Initialize the test.
        
        Args:
            file_count: Number of files to validate
            iterations: Number of iterations to run
        """
        super().__init__(f"File Validation Workflow ({file_count} files)", iterations)
        self.file_count = file_count
        self.temp_dir = None
        self.input_dir = None
        self.config = None
        self.logger = None
        self.file_manager = None
        self.test_files = []
    
    def setup(self) -> None:
        """Set up the test environment."""
        # Create temporary directories
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_dir = Path(self.temp_dir.name) / "input"
        self.input_dir.mkdir(exist_ok=True)
        
        # Create test files
        self.test_files = []
        for i in range(self.file_count):
            # Create a mix of valid and invalid files
            if i % 5 == 0:  # 20% invalid
                file_path = self.input_dir / f"invalid_file_{i}.mp4"
            else:
                file_path = self.input_dir / f"movie_{i}.mp4"
            
            with open(file_path, 'wb') as f:
                f.write(os.urandom(1024 * 1024))  # 1MB file
            self.test_files.append(file_path)
        
        # Create config
        self.config = Config()
        self.config.input_folder = self.input_dir
        self.config.file_validation_pattern = r"movie_\d+\.mp4$"
        
        # Create logger
        self.logger = Logger(level="INFO")
        
        # Create file manager
        self.file_manager = FileManager(self.config, self.logger)
    
    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.temp_dir:
            self.temp_dir.cleanup()
    
    def run_iteration(self) -> float:
        """Run a single iteration of the test."""
        # Time the validation operation
        _, execution_time = time_function(self.file_manager.validate_files)
        return execution_time

class FolderOrganizationWorkflowPerformanceTest(PerformanceTest):
    """Test the performance of the folder organization workflow."""
    
    def __init__(self, folder_count: int, iterations: int = 3):
        """
        Initialize the test.
        
        Args:
            folder_count: Number of folders to organize
            iterations: Number of iterations to run
        """
        super().__init__(f"Folder Organization Workflow ({folder_count} folders)", iterations)
        self.folder_count = folder_count
        self.temp_dir = None
        self.output_dir = None
        self.config = None
        self.logger = None
        self.file_manager = None
        self.test_folders = []
    
    def setup(self) -> None:
        """Set up the test environment."""
        # Create temporary directories
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name) / "output"
        self.output_dir.mkdir(exist_ok=True)
        
        # Create test folders
        self.test_folders = []
        for i in range(self.folder_count):
            # Create folders that match the organization pattern
            folder_path = self.output_dir / f"movie_{i}"
            folder_path.mkdir(exist_ok=True)
            
            # Create a few files in each folder
            for j in range(3):
                file_path = folder_path / f"file_{j}.mp4"
                with open(file_path, 'wb') as f:
                    f.write(os.urandom(1024 * 1024))  # 1MB file
            
            self.test_folders.append(folder_path)
        
        # Create config
        self.config = Config()
        self.config.output_folder = self.output_dir
        self.config.auto_organize_folders = True
        self.config.folder_organization_pattern = r"(.+?)_\d+"
        
        # Create logger
        self.logger = Logger(level="INFO")
        
        # Create file manager
        self.file_manager = FileManager(self.config, self.logger)
    
    def teardown(self) -> None:
        """Clean up the test environment."""
        if self.temp_dir:
            self.temp_dir.cleanup()
    
    def run_iteration(self) -> float:
        """Run a single iteration of the test."""
        # Reset the test folders for each iteration
        for folder_path in self.test_folders:
            if folder_path.exists():
                import shutil
                shutil.rmtree(folder_path)
        
        for i in range(self.folder_count):
            folder_path = self.output_dir / f"movie_{i}"
            folder_path.mkdir(exist_ok=True)
            
            # Create a few files in each folder
            for j in range(3):
                file_path = folder_path / f"file_{j}.mp4"
                with open(file_path, 'wb') as f:
                    f.write(os.urandom(1024 * 1024))  # 1MB file
        
        # Time the organization operation
        _, execution_time = time_function(self.file_manager.organize_folders)
        return execution_time

@patch('video_processor.processing.scheduler.process_video_task')
@patch('video_processor.processing.scheduler.ProcessPoolExecutor')
def test_end_to_end_workflow_performance(mock_executor_class, mock_process_video_task):
    """Test the performance of the end-to-end workflow with different file counts."""
    # Mock the process_video_task function
    mock_process_video_task.return_value = (True, "output_file.mp4", "1080p", None)
    
    # Mock the executor's submit method
    mock_future = MagicMock()
    mock_future.result.return_value = (True, "output_file.mp4", "1080p", None)
    mock_executor = MagicMock(spec=ProcessPoolExecutor)
    mock_executor.submit.return_value = mock_future
    mock_executor_class.return_value.__enter__.return_value = mock_executor
    
    file_counts = [10, 50, 100]
    
    for file_count in file_counts:
        test = EndToEndWorkflowPerformanceTest(file_count)
        results = test.run()
        test.print_results(results)
        
        # Assert that the performance is reasonable
        if file_count == 10:
            assert results["avg_time"] < 1.0, f"End-to-end workflow for {file_count} files is too slow"
        elif file_count == 50:
            assert results["avg_time"] < 5.0, f"End-to-end workflow for {file_count} files is too slow"
        elif file_count == 100:
            assert results["avg_time"] < 10.0, f"End-to-end workflow for {file_count} files is too slow"

def test_file_renaming_workflow_performance():
    """Test the performance of the file renaming workflow with different file counts."""
    file_counts = [10, 100, 1000]
    
    for file_count in file_counts:
        test = FileRenamingWorkflowPerformanceTest(file_count)
        results = test.run()
        test.print_results(results)
        
        # Assert that the performance is reasonable
        if file_count == 10:
            assert results["avg_time"] < 0.1, f"File renaming workflow for {file_count} files is too slow"
        elif file_count == 100:
            assert results["avg_time"] < 1.0, f"File renaming workflow for {file_count} files is too slow"
        elif file_count == 1000:
            assert results["avg_time"] < 10.0, f"File renaming workflow for {file_count} files is too slow"

def test_file_validation_workflow_performance():
    """Test the performance of the file validation workflow with different file counts."""
    file_counts = [10, 100, 1000]
    
    for file_count in file_counts:
        test = FileValidationWorkflowPerformanceTest(file_count)
        results = test.run()
        test.print_results(results)
        
        # Assert that the performance is reasonable
        if file_count == 10:
            assert results["avg_time"] < 0.1, f"File validation workflow for {file_count} files is too slow"
        elif file_count == 100:
            assert results["avg_time"] < 1.0, f"File validation workflow for {file_count} files is too slow"
        elif file_count == 1000:
            assert results["avg_time"] < 10.0, f"File validation workflow for {file_count} files is too slow"

def test_folder_organization_workflow_performance():
    """Test the performance of the folder organization workflow with different folder counts."""
    folder_counts = [10, 50, 100]
    
    for folder_count in folder_counts:
        test = FolderOrganizationWorkflowPerformanceTest(folder_count)
        results = test.run()
        test.print_results(results)
        
        # Assert that the performance is reasonable
        if folder_count == 10:
            assert results["avg_time"] < 1.0, f"Folder organization workflow for {folder_count} folders is too slow"
        elif folder_count == 50:
            assert results["avg_time"] < 5.0, f"Folder organization workflow for {folder_count} folders is too slow"
        elif folder_count == 100:
            assert results["avg_time"] < 10.0, f"Folder organization workflow for {folder_count} folders is too slow"

if __name__ == "__main__":
    test_end_to_end_workflow_performance()
    test_file_renaming_workflow_performance()
    test_file_validation_workflow_performance()
    test_folder_organization_workflow_performance()
