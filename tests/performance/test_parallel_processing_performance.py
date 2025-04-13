"""
Performance tests for parallel processing efficiency.
"""
import os
import sys
import time
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from concurrent.futures import ProcessPoolExecutor

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the modules to test
from pyprocessor.utils.config import Config
from pyprocessor.utils.logging import Logger
from pyprocessor.processing.file_manager import FileManager
from pyprocessor.processing.encoder import FFmpegEncoder
from pyprocessor.processing.scheduler import ProcessingScheduler

# Import performance test base
from tests.performance.test_performance_base import PerformanceTest, PerformanceResult, time_and_memory_function

class ParallelProcessingEfficiencyTest(PerformanceTest):
    """Test the efficiency of parallel processing with different numbers of workers."""
    
    def __init__(self, file_count: int, worker_count: int, iterations: int = 3):
        """
        Initialize the test.
        
        Args:
            file_count: Number of files to process
            worker_count: Number of parallel workers
            iterations: Number of iterations to run
        """
        super().__init__(f"Parallel Processing ({file_count} files, {worker_count} workers)", iterations)
        self.file_count = file_count
        self.worker_count = worker_count
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
        
        # Create test files
        self.test_files = []
        for i in range(self.file_count):
            file_path = self.input_dir / f"test_video_{i+1}.mp4"
            with open(file_path, 'wb') as f:
                f.write(os.urandom(1024 * 1024))  # 1MB file
            self.test_files.append(file_path)
        
        # Create config
        self.config = Config()
        self.config.input_folder = self.input_dir
        self.config.output_folder = self.output_dir
        self.config.max_parallel_jobs = self.worker_count
        self.config.file_validation_pattern = r".+\.mp4$"
        
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
    
    @patch('pyprocessor.processing.scheduler.process_video_task')
    @patch('pyprocessor.processing.scheduler.ProcessPoolExecutor')
    def run_iteration(self, mock_executor_class, mock_process_video_task) -> PerformanceResult:
        """Run a single iteration of the test."""
        # Mock the process_video_task function to simulate work
        def simulated_work(*args, **kwargs):
            # Simulate work that takes 0.1 seconds per file
            time.sleep(0.1)
            return (True, "output_file.mp4", "1080p", None)
        
        mock_process_video_task.side_effect = simulated_work
        
        # Create a real ProcessPoolExecutor with the specified number of workers
        real_executor = ProcessPoolExecutor(max_workers=self.worker_count)
        
        # Mock the executor's submit method to use the real executor
        def submit_to_real_executor(*args, **kwargs):
            future = real_executor.submit(*args, **kwargs)
            return future
        
        mock_executor = MagicMock(spec=ProcessPoolExecutor)
        mock_executor.submit.side_effect = submit_to_real_executor
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        
        # Mock the file manager's validate_files method
        valid_files = [Path(file) for file in self.test_files]
        invalid_files = []
        self.file_manager.validate_files = MagicMock(return_value=(valid_files, invalid_files))
        
        # Time and measure memory usage of the processing
        result, execution_time, memory_usage = time_and_memory_function(self.scheduler.process_videos)
        
        # Clean up the real executor
        real_executor.shutdown(wait=True)
        
        return PerformanceResult(execution_time, memory_usage)

class ProcessPoolScalingTest(PerformanceTest):
    """Test the scaling efficiency of ProcessPoolExecutor with different numbers of workers."""
    
    def __init__(self, task_count: int, worker_count: int, task_duration: float = 0.1, iterations: int = 3):
        """
        Initialize the test.
        
        Args:
            task_count: Number of tasks to process
            worker_count: Number of parallel workers
            task_duration: Duration of each task in seconds
            iterations: Number of iterations to run
        """
        super().__init__(f"ProcessPool Scaling ({task_count} tasks, {worker_count} workers)", iterations)
        self.task_count = task_count
        self.worker_count = worker_count
        self.task_duration = task_duration
    
    def setup(self) -> None:
        """Set up the test environment."""
    
    def teardown(self) -> None:
        """Clean up the test environment."""
    
    def run_iteration(self) -> PerformanceResult:
        """Run a single iteration of the test."""
        def simulated_task(task_id):
            """Simulated task that sleeps for a specified duration."""
            time.sleep(self.task_duration)
            return task_id
        
        # Time and measure memory usage of the processing
        def run_tasks():
            with ProcessPoolExecutor(max_workers=self.worker_count) as executor:
                futures = [executor.submit(simulated_task, i) for i in range(self.task_count)]
                results = [future.result() for future in futures]
                return results
        
        result, execution_time, memory_usage = time_and_memory_function(run_tasks)
        
        return PerformanceResult(execution_time, memory_usage)

@patch('pyprocessor.processing.scheduler.process_video_task')
@patch('pyprocessor.processing.scheduler.ProcessPoolExecutor')
def test_parallel_processing_efficiency(mock_executor_class, mock_process_video_task):
    """Test the efficiency of parallel processing with different numbers of workers."""
    # Define test parameters
    file_count = 20
    worker_counts = [1, 2, 4, 8]
    
    # Run tests for each worker count
    results = {}
    for worker_count in worker_counts:
        test = ParallelProcessingEfficiencyTest(file_count, worker_count)
        result = test.run()
        test.print_results(result)
        results[worker_count] = result["avg_time"]
    
    # Calculate speedup and efficiency
    print("\nParallel Processing Speedup and Efficiency:")
    print(f"{'Workers':<10} {'Time (s)':<10} {'Speedup':<10} {'Efficiency':<10}")
    
    base_time = results[1]  # Time with 1 worker
    for worker_count in worker_counts:
        time_taken = results[worker_count]
        speedup = base_time / time_taken
        efficiency = speedup / worker_count
        print(f"{worker_count:<10} {time_taken:<10.4f} {speedup:<10.4f} {efficiency:<10.4f}")
    
    # Assert that there is some speedup with more workers
    assert results[worker_counts[-1]] < results[1], "No speedup with more workers"

def test_process_pool_scaling():
    """Test the scaling efficiency of ProcessPoolExecutor with different numbers of workers."""
    # Define test parameters
    task_count = 100
    worker_counts = [1, 2, 4, 8, 16]
    task_duration = 0.1  # 100ms per task
    
    # Run tests for each worker count
    results = {}
    for worker_count in worker_counts:
        test = ProcessPoolScalingTest(task_count, worker_count, task_duration)
        result = test.run()
        test.print_results(result)
        results[worker_count] = result["avg_time"]
    
    # Calculate speedup and efficiency
    print("\nProcess Pool Scaling Speedup and Efficiency:")
    print(f"{'Workers':<10} {'Time (s)':<10} {'Speedup':<10} {'Efficiency':<10}")
    
    base_time = results[1]  # Time with 1 worker
    for worker_count in worker_counts:
        time_taken = results[worker_count]
        speedup = base_time / time_taken
        efficiency = speedup / worker_count
        print(f"{worker_count:<10} {time_taken:<10.4f} {speedup:<10.4f} {efficiency:<10.4f}")
    
    # Assert that there is some speedup with more workers
    assert results[worker_counts[-1]] < results[1], "No speedup with more workers"

if __name__ == "__main__":
    test_parallel_processing_efficiency()
    test_process_pool_scaling()
