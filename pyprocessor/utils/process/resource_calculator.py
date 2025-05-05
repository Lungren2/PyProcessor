"""
Resource calculator for determining optimal batch sizes.

This module provides utilities for calculating optimal batch sizes
based on system resources, file characteristics, and workload.
"""

import math
from pathlib import Path
from typing import Any, Dict, List

import psutil

from pyprocessor.utils.logging import get_logger
from pyprocessor.utils.process.gpu_manager import (
    GPUCapability,
    get_all_gpu_usage,
    get_gpus,
)


class ResourceCalculator:
    """
    Calculates optimal resource allocation based on system capabilities and workload.

    This class provides methods to determine the optimal batch size for processing
    multiple files based on available system resources and file characteristics.
    """

    def __init__(self, config=None, logger=None):
        """
        Initialize the resource calculator.

        Args:
            config: Configuration object (optional)
            logger: Logger instance (optional)
        """
        self.config = config
        self.logger = logger or get_logger()

    def calculate_optimal_batch_size(
        self, files: List[Path], max_parallel_jobs: int = None
    ) -> int:
        """
        Calculate the optimal batch size based on system resources and file characteristics.

        Args:
            files: List of files to process
            max_parallel_jobs: Maximum number of parallel jobs (if None, uses config or auto-detects)

        Returns:
            int: Optimal batch size
        """
        # Get system information
        total_files = len(files)
        if total_files == 0:
            return 1

        # Get CPU and memory information
        cpu_count = psutil.cpu_count(logical=True)
        memory_info = psutil.virtual_memory()
        total_memory_gb = memory_info.total / (1024**3)  # Convert to GB
        available_memory_gb = memory_info.available / (1024**3)  # Convert to GB

        # Get GPU information if available
        gpu_info = self._get_gpu_info()
        has_gpu = gpu_info.get("has_gpu", False)
        gpu_memory_available_gb = gpu_info.get("available_memory_gb", 0)
        gpu_utilization = gpu_info.get("utilization", 0.0)
        gpu_encoder_usage = gpu_info.get("encoder_usage", 0.0)

        # Determine max parallel jobs if not provided
        if max_parallel_jobs is None:
            if self.config and hasattr(self.config, "max_parallel_jobs"):
                max_parallel_jobs = self.config.max_parallel_jobs
            else:
                # Default to 75% of CPU cores
                max_parallel_jobs = max(1, int(cpu_count * 0.75))

        # Estimate average file size
        avg_file_size_gb = self._estimate_average_file_size(files)

        # Calculate memory requirements per file (estimated)
        # FFmpeg typically needs ~1.5-2x the file size in memory for processing
        memory_per_file_gb = avg_file_size_gb * 2

        # Calculate how many files we can process in parallel based on memory
        max_files_by_memory = max(
            1, int(available_memory_gb / memory_per_file_gb * 0.8)
        )  # Use 80% of available memory

        # If using GPU encoding, consider GPU memory as well
        if (
            has_gpu
            and self.config
            and hasattr(self.config, "ffmpeg_params")
            and self.config.ffmpeg_params.get("video_encoder", "").endswith("_nvenc")
        ):
            # GPU encoding typically needs ~1.5x the file size in GPU memory
            gpu_memory_per_file_gb = avg_file_size_gb * 1.5

            # Calculate how many files we can process in parallel based on GPU memory
            # Use 70% of available GPU memory to leave room for other operations
            max_files_by_gpu = max(
                1, int(gpu_memory_available_gb / gpu_memory_per_file_gb * 0.7)
            )

            # Log GPU constraints
            self.logger.info(
                f"GPU constraints: {gpu_memory_available_gb:.1f}GB available, "
                f"{gpu_memory_per_file_gb:.2f}GB per file, max {max_files_by_gpu} files"
            )

            # Adjust max files based on GPU memory (more constrained resource)
            max_files_by_memory = min(max_files_by_memory, max_files_by_gpu)

            # Also consider GPU utilization and encoder usage
            if gpu_utilization > 0.8 or gpu_encoder_usage > 0.8:
                # If GPU is already heavily utilized, reduce batch size further
                max_files_by_memory = max(1, int(max_files_by_memory * 0.7))
                self.logger.info(
                    f"Reducing batch size due to high GPU utilization: {gpu_utilization:.2%} util, "
                    f"{gpu_encoder_usage:.2%} encoder usage"
                )

        # Calculate optimal batch size
        if total_files <= max_parallel_jobs:
            # If we have fewer files than parallel jobs, process each file individually
            return 1

        # Calculate ideal batch size to distribute files evenly across processes
        ideal_batch_size = math.ceil(total_files / max_parallel_jobs)

        # Adjust batch size based on memory constraints
        memory_constrained_batch_size = max(
            1, int(max_files_by_memory / max_parallel_jobs)
        )

        # Take the minimum of ideal and memory-constrained batch sizes
        batch_size = min(ideal_batch_size, memory_constrained_batch_size)

        # Log the calculation
        self.logger.info(
            f"Resource calculation: {total_files} files, {max_parallel_jobs} parallel jobs"
        )
        self.logger.info(
            f"System: {cpu_count} CPUs, {total_memory_gb:.1f}GB total memory, {available_memory_gb:.1f}GB available"
        )

        # Log GPU information if available
        if has_gpu:
            gpu_name = gpu_info.get("gpu_name", "Unknown")
            gpu_count = gpu_info.get("gpu_count", 0)  # Unused variable  # Unused variable
            self.logger.info(
                f"GPU: {gpu_name}, {gpu_memory_available_gb:.1f}GB available, "
                f"utilization: {gpu_utilization:.2%}, encoder: {gpu_encoder_usage:.2%}"
            )
            if gpu_info.get("has_h264", False):
                self.logger.info("GPU supports H.264 hardware encoding")
            if gpu_info.get("has_hevc", False):
                self.logger.info("GPU supports HEVC hardware encoding")

        self.logger.info(
            f"Files: {avg_file_size_gb:.2f}GB average size, {memory_per_file_gb:.2f}GB estimated memory per file"
        )
        self.logger.info(
            f"Calculated batch size: {batch_size} (ideal: {ideal_batch_size}, memory-constrained: {memory_constrained_batch_size})"
        )

        return batch_size

    def _get_gpu_info(self) -> Dict[str, Any]:
        """
        Get GPU information for resource calculation.

        Returns:
            Dict[str, Any]: GPU information
        """
        try:
            # Get GPU usage from GPU manager
            gpu_usages = get_all_gpu_usage()

            if not gpu_usages:
                return {
                    "has_gpu": False,
                    "available_memory_gb": 0,
                    "utilization": 0.0,
                    "encoder_usage": 0.0,
                    "decoder_usage": 0.0,
                    "gpu_count": 0,
                }

            # Use the GPU with most available memory for encoding
            primary_gpu = max(
                gpu_usages, key=lambda x: (x.memory_total - x.memory_used)
            )

            # Calculate available memory in GB
            available_memory_gb = (
                primary_gpu.memory_total - primary_gpu.memory_used
            ) / (1024**3)

            # Check if GPU has encoding capability
            gpus = get_gpus()
            has_h264 = any(GPUCapability.H264 in gpu.capabilities for gpu in gpus)
            has_hevc = any(GPUCapability.HEVC in gpu.capabilities for gpu in gpus)

            return {
                "has_gpu": True,
                "available_memory_gb": available_memory_gb,
                "utilization": primary_gpu.utilization,
                "encoder_usage": (
                    primary_gpu.encoder_usage
                    if primary_gpu.encoder_usage is not None
                    else 0.0
                ),
                "decoder_usage": (
                    primary_gpu.decoder_usage
                    if primary_gpu.decoder_usage is not None
                    else 0.0
                ),
                "gpu_count": len(gpu_usages),
                "has_h264": has_h264,
                "has_hevc": has_hevc,
                "gpu_index": primary_gpu.index,
                "gpu_name": (
                    gpus[primary_gpu.index].name
                    if primary_gpu.index < len(gpus)
                    else "Unknown"
                ),
            }

        except Exception as e:
            self.logger.warning(f"Error getting GPU information: {str(e)}")
            return {
                "has_gpu": False,
                "available_memory_gb": 0,
                "utilization": 0.0,
                "encoder_usage": 0.0,
                "decoder_usage": 0.0,
                "gpu_count": 0,
            }

    def _estimate_average_file_size(self, files: List[Path]) -> float:
        """
        Estimate the average file size in GB.

        Args:
            files: List of files

        Returns:
            float: Average file size in GB
        """
        # Sample up to 10 files to estimate average size
        sample_size = min(10, len(files))
        sample_files = files[:sample_size]

        total_size = 0
        for file in sample_files:
            try:
                total_size += file.stat().st_size
            except (FileNotFoundError, PermissionError):
                # Skip files that can't be accessed
                pass

        if sample_size == 0:
            # Default to 500MB if we couldn't sample any files
            return 0.5

        avg_size_bytes = total_size / sample_size
        avg_size_gb = avg_size_bytes / (1024**3)  # Convert to GB

        # Ensure a minimum size to prevent division by zero
        return max(0.1, avg_size_gb)  # Minimum 100MB

    def calculate_memory_usage_per_batch(
        self, batch_size: int, avg_file_size_gb: float
    ) -> float:
        """
        Calculate estimated memory usage for a batch.

        Args:
            batch_size: Number of files in the batch
            avg_file_size_gb: Average file size in GB

        Returns:
            float: Estimated memory usage in GB
        """
        # Base memory usage for the process
        base_memory_gb = 0.2  # 200MB base overhead

        # Memory per file (estimated)
        memory_per_file_gb = avg_file_size_gb * 2

        # Total memory for the batch
        total_memory_gb = base_memory_gb + (memory_per_file_gb * batch_size)

        return total_memory_gb

    def adjust_batch_size_for_divisibility(
        self, total_files: int, batch_size: int, max_parallel_jobs: int
    ) -> int:
        """
        Adjust batch size to ensure even distribution across processes.

        Args:
            total_files: Total number of files
            batch_size: Initial batch size
            max_parallel_jobs: Maximum number of parallel jobs

        Returns:
            int: Adjusted batch size
        """
        # Calculate number of batches with current batch size
        num_batches = math.ceil(total_files / batch_size)

        # If number of batches is less than max parallel jobs, we're good
        if num_batches <= max_parallel_jobs:
            return batch_size

        # Try to find a batch size that divides the files evenly
        for adjusted_size in range(batch_size, batch_size + 3):
            if total_files % adjusted_size == 0:
                return adjusted_size

        # If we can't find a perfect divisor, return the original
        return batch_size


def get_optimal_batch_size(files: List[Path], config=None, logger=None) -> int:
    """
    Get the optimal batch size for the given files and system resources.

    Args:
        files: List of files to process
        config: Configuration object (optional)
        logger: Logger instance (optional)

    Returns:
        int: Optimal batch size
    """
    calculator = ResourceCalculator(config, logger)
    return calculator.calculate_optimal_batch_size(files)
