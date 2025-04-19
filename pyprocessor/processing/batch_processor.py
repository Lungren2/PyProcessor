"""
Batch processing module for PyProcessor.

This module provides functionality for processing videos in batches,
allowing multiple videos to be processed within a single process.
"""

import os
import time
import threading
import queue
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional, Tuple

from pyprocessor.utils.logging import get_logger
from pyprocessor.utils.process.resource_manager import get_resource_manager


class BatchProcessor:
    """
    Batch processor for handling multiple videos within a single process.

    This class processes multiple videos in a single process using threads,
    which provides a balance between process isolation and resource usage.
    """

    def __init__(self, config, logger=None):
        """
        Initialize the batch processor.

        Args:
            config: Configuration object
            logger: Logger instance (optional)
        """
        self.config = config
        self.logger = logger or get_logger()
        self.resource_manager = get_resource_manager()

        # Get batch processing settings
        self.batch_enabled = config.get("batch_processing.enabled", True)
        self.batch_size = config.get("batch_processing.batch_size", 10)
        self.max_memory_percent = config.get("batch_processing.max_memory_percent", 80)

        # Internal state
        self.processing_queue = queue.Queue()
        self.results_queue = queue.Queue()
        self.worker_threads = []
        self.is_running = False
        self.abort_requested = False

    def process_batch(self, files: List[Path], output_folder: Path,
                     ffmpeg_params: Dict[str, Any],
                     progress_callback: Optional[Callable] = None,
                     output_file_callback: Optional[Callable] = None,
                     encrypt_output: bool = False,
                     encryption_key_id: Optional[str] = None) -> List[Tuple[str, bool, float, str]]:
        """
        Process a batch of video files.

        Args:
            files: List of video files to process
            output_folder: Output folder for processed videos
            ffmpeg_params: FFmpeg parameters
            progress_callback: Callback for progress updates
            output_file_callback: Callback for output file updates

        Returns:
            List of tuples (filename, success, duration, error_message)
        """
        self.logger.info(f"Processing batch of {len(files)} files")
        self.is_running = True
        self.abort_requested = False

        # Clear queues
        while not self.processing_queue.empty():
            self.processing_queue.get()
        while not self.results_queue.empty():
            self.results_queue.get()

        # Add files to processing queue
        for file in files:
            self.processing_queue.put((file, output_folder, ffmpeg_params, encrypt_output, encryption_key_id))

        # Start worker threads
        num_threads = min(len(files), self.batch_size)
        self.worker_threads = []

        for i in range(num_threads):
            thread = threading.Thread(
                target=self._worker_thread,
                args=(i, progress_callback, output_file_callback),
                daemon=True,
                name=f"BatchWorker-{i}"
            )
            thread.start()
            self.worker_threads.append(thread)

        # Wait for all threads to complete
        results = []
        try:
            # Wait for all files to be processed
            while len(results) < len(files) and not self.abort_requested:
                try:
                    # Get result with timeout to allow checking abort flag
                    result = self.results_queue.get(timeout=0.5)
                    results.append(result)
                    self.results_queue.task_done()
                except queue.Empty:
                    # Check if all threads are done
                    if all(not thread.is_alive() for thread in self.worker_threads):
                        break

            # If abort was requested, wait for threads to finish current file
            if self.abort_requested:
                self.logger.warning("Batch processing aborted, waiting for threads to finish current files")
                for thread in self.worker_threads:
                    if thread.is_alive():
                        thread.join(timeout=5.0)
        finally:
            self.is_running = False

        return results

    def _worker_thread(self, thread_id: int,
                      progress_callback: Optional[Callable],
                      output_file_callback: Optional[Callable]):
        """
        Worker thread for processing videos.

        Args:
            thread_id: Thread ID
            progress_callback: Callback for progress updates
            output_file_callback: Callback for output file updates
        """
        self.logger.debug(f"Worker thread {thread_id} started")

        while not self.abort_requested:
            try:
                # Get next file from queue with timeout to allow checking abort flag
                try:
                    file, output_folder, ffmpeg_params, encrypt_output, encryption_key_id = self.processing_queue.get(timeout=0.5)
                except queue.Empty:
                    break

                # Process the file
                try:
                    self.logger.info(f"Thread {thread_id} processing {file.name}")
                    start_time = time.time()

                    # Import here to avoid circular imports
                    from pyprocessor.processing.encoder import process_video_task

                    # Process the video
                    result = process_video_task(
                        str(file),
                        str(output_folder),
                        ffmpeg_params,
                        thread_id,
                        progress_callback=progress_callback,
                        output_file_callback=output_file_callback,
                        encrypt_output=encrypt_output,
                        encryption_key_id=encryption_key_id
                    )

                    # Add result to results queue
                    self.results_queue.put(result)

                    # Mark task as done
                    self.processing_queue.task_done()

                    # Log completion
                    duration = time.time() - start_time
                    self.logger.info(f"Thread {thread_id} completed {file.name} in {duration:.2f}s")

                except Exception as e:
                    self.logger.error(f"Error processing {file.name}: {str(e)}")
                    self.results_queue.put((str(file), False, 0.0, str(e)))
                    self.processing_queue.task_done()

            except Exception as e:
                self.logger.error(f"Error in worker thread {thread_id}: {str(e)}")

        self.logger.debug(f"Worker thread {thread_id} stopped")

    def request_abort(self):
        """Request abortion of the batch processing."""
        if not self.is_running:
            return False

        self.logger.warning("Batch processing abort requested")
        self.abort_requested = True
        return True


def create_batches(files: List[Path], batch_size: int = None, config=None, logger=None) -> List[List[Path]]:
    """
    Create batches of files for processing.

    Args:
        files: List of files to batch
        batch_size: Maximum size of each batch (if None, calculates optimal size)
        config: Configuration object (optional)
        logger: Logger instance (optional)

    Returns:
        List of file batches
    """
    # If batch size is not specified, calculate the optimal size
    if batch_size is None:
        from pyprocessor.utils.process.resource_calculator import get_optimal_batch_size
        batch_size = get_optimal_batch_size(files, config, logger)

    # Create batches
    batches = []
    for i in range(0, len(files), batch_size):
        batch = files[i:i + batch_size]
        batches.append(batch)

    return batches
