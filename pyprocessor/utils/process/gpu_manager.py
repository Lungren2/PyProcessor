"""
GPU resource management utilities for PyProcessor.

This module provides utilities for detecting and monitoring GPU resources,
particularly NVIDIA GPUs using the NVML library through pynvml.
"""

import os
import platform
import threading
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

# Import pynvml for NVIDIA GPU monitoring
try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False

from pyprocessor.utils.log_manager import get_logger


class GPUVendor(Enum):
    """GPU vendor types."""
    UNKNOWN = "unknown"
    NVIDIA = "nvidia"
    AMD = "amd"
    INTEL = "intel"


class GPUCapability(Enum):
    """GPU encoding capabilities."""
    NONE = "none"
    H264 = "h264"
    HEVC = "hevc"
    AV1 = "av1"


class GPUInfo:
    """Information about a GPU device."""
    
    def __init__(
        self,
        index: int,
        name: str,
        vendor: GPUVendor,
        total_memory: int,  # in bytes
        capabilities: List[GPUCapability] = None,
        driver_version: str = None,
        device_id: str = None,
    ):
        """
        Initialize GPU information.
        
        Args:
            index: GPU index
            name: GPU name
            vendor: GPU vendor
            total_memory: Total memory in bytes
            capabilities: List of encoding capabilities
            driver_version: Driver version
            device_id: Device ID
        """
        self.index = index
        self.name = name
        self.vendor = vendor
        self.total_memory = total_memory
        self.capabilities = capabilities or []
        self.driver_version = driver_version
        self.device_id = device_id
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert GPU information to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of GPU information
        """
        return {
            "index": self.index,
            "name": self.name,
            "vendor": self.vendor.value,
            "total_memory": self.total_memory,
            "capabilities": [cap.value for cap in self.capabilities],
            "driver_version": self.driver_version,
            "device_id": self.device_id,
        }


class GPUUsage:
    """GPU usage information."""
    
    def __init__(
        self,
        index: int,
        utilization: float,  # 0.0-1.0
        memory_used: int,  # in bytes
        memory_total: int,  # in bytes
        temperature: Optional[float] = None,  # in Celsius
        power_usage: Optional[float] = None,  # in Watts
        encoder_usage: Optional[float] = None,  # 0.0-1.0
        decoder_usage: Optional[float] = None,  # 0.0-1.0
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize GPU usage.
        
        Args:
            index: GPU index
            utilization: GPU utilization (0.0-1.0)
            memory_used: Memory used in bytes
            memory_total: Total memory in bytes
            temperature: GPU temperature in Celsius
            power_usage: Power usage in Watts
            encoder_usage: Encoder utilization (0.0-1.0)
            decoder_usage: Decoder utilization (0.0-1.0)
            details: Additional details
        """
        self.index = index
        self.utilization = utilization
        self.memory_used = memory_used
        self.memory_total = memory_total
        self.memory_utilization = memory_used / memory_total if memory_total > 0 else 0.0
        self.temperature = temperature
        self.power_usage = power_usage
        self.encoder_usage = encoder_usage
        self.decoder_usage = decoder_usage
        self.details = details or {}
        self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert GPU usage to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of GPU usage
        """
        return {
            "index": self.index,
            "utilization": self.utilization,
            "memory_used": self.memory_used,
            "memory_total": self.memory_total,
            "memory_utilization": self.memory_utilization,
            "temperature": self.temperature,
            "power_usage": self.power_usage,
            "encoder_usage": self.encoder_usage,
            "decoder_usage": self.decoder_usage,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class GPUManager:
    """
    Manager for GPU resources.
    
    This class provides:
    - GPU detection and information
    - GPU usage monitoring
    - GPU capability detection
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GPUManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """Initialize the GPU manager."""
        # Only initialize once
        if getattr(self, '_initialized', False):
            return
            
        # Get logger
        self.logger = get_logger()
        
        # Initialize GPU information
        self._gpus = []
        self._nvml_initialized = False
        
        # Initialize monitoring
        self._monitoring_enabled = False
        self._monitoring_interval = 5.0  # seconds
        self._monitoring_thread = None
        self._stop_event = threading.Event()
        
        # Initialize usage history
        self._usage_history = {}  # index -> List[GPUUsage]
        
        # Initialize statistics
        self._stats = {
            "peak_utilization": {},  # index -> float
            "peak_memory_usage": {},  # index -> float
            "peak_temperature": {},  # index -> float
            "peak_power_usage": {},  # index -> float
            "peak_encoder_usage": {},  # index -> float
            "peak_decoder_usage": {},  # index -> float
        }
        
        # Try to initialize NVML
        self._initialize_nvml()
        
        # Detect GPUs
        self._detect_gpus()
        
        # Mark as initialized
        self._initialized = True
        self.logger.debug("GPU manager initialized")
    
    def _initialize_nvml(self) -> bool:
        """
        Initialize NVIDIA Management Library.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not PYNVML_AVAILABLE:
            self.logger.debug("pynvml not available, NVIDIA GPU monitoring disabled")
            return False
            
        try:
            pynvml.nvmlInit()
            self._nvml_initialized = True
            self.logger.debug("NVML initialized successfully")
            return True
        except Exception as e:
            self.logger.warning(f"Failed to initialize NVML: {str(e)}")
            self._nvml_initialized = False
            return False
    
    def _detect_gpus(self) -> None:
        """Detect available GPUs."""
        self._gpus = []
        
        # Detect NVIDIA GPUs using NVML
        if self._nvml_initialized:
            try:
                device_count = pynvml.nvmlDeviceGetCount()
                self.logger.debug(f"Detected {device_count} NVIDIA GPUs")
                
                for i in range(device_count):
                    try:
                        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                        name = pynvml.nvmlDeviceGetName(handle)
                        memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                        driver_version = pynvml.nvmlSystemGetDriverVersion()
                        device_uuid = pynvml.nvmlDeviceGetUUID(handle)
                        
                        # Detect capabilities
                        capabilities = [GPUCapability.NONE]
                        
                        # Check for NVENC support (H.264 and HEVC)
                        try:
                            encoder_count = pynvml.nvmlDeviceGetEncoderCapacity(handle, pynvml.NVML_ENCODER_QUERY_H264)
                            if encoder_count > 0:
                                capabilities.append(GPUCapability.H264)
                                
                            encoder_count = pynvml.nvmlDeviceGetEncoderCapacity(handle, pynvml.NVML_ENCODER_QUERY_HEVC)
                            if encoder_count > 0:
                                capabilities.append(GPUCapability.HEVC)
                        except Exception:
                            # If we can't query encoder capabilities, assume basic support
                            capabilities.extend([GPUCapability.H264, GPUCapability.HEVC])
                        
                        # Create GPU info
                        gpu_info = GPUInfo(
                            index=i,
                            name=name,
                            vendor=GPUVendor.NVIDIA,
                            total_memory=memory_info.total,
                            capabilities=capabilities,
                            driver_version=driver_version,
                            device_id=device_uuid,
                        )
                        
                        self._gpus.append(gpu_info)
                        self._usage_history[i] = []
                        self._stats["peak_utilization"][i] = 0.0
                        self._stats["peak_memory_usage"][i] = 0.0
                        self._stats["peak_temperature"][i] = 0.0
                        self._stats["peak_power_usage"][i] = 0.0
                        self._stats["peak_encoder_usage"][i] = 0.0
                        self._stats["peak_decoder_usage"][i] = 0.0
                        
                        self.logger.info(f"GPU {i}: {name}, {memory_info.total / (1024**3):.2f} GB, capabilities: {[cap.value for cap in capabilities]}")
                        
                    except Exception as e:
                        self.logger.warning(f"Error detecting NVIDIA GPU {i}: {str(e)}")
                
            except Exception as e:
                self.logger.warning(f"Error detecting NVIDIA GPUs: {str(e)}")
        
        # TODO: Add detection for AMD and Intel GPUs
    
    def get_gpus(self) -> List[GPUInfo]:
        """
        Get list of available GPUs.
        
        Returns:
            List[GPUInfo]: List of GPU information
        """
        return self._gpus.copy()
    
    def get_gpu_count(self) -> int:
        """
        Get number of available GPUs.
        
        Returns:
            int: Number of GPUs
        """
        return len(self._gpus)
    
    def has_encoding_capability(self, capability: GPUCapability) -> bool:
        """
        Check if any GPU has the specified encoding capability.
        
        Args:
            capability: Encoding capability to check
            
        Returns:
            bool: True if any GPU has the capability, False otherwise
        """
        for gpu in self._gpus:
            if capability in gpu.capabilities:
                return True
        return False
    
    def get_gpu_usage(self, index: int) -> Optional[GPUUsage]:
        """
        Get current usage for a specific GPU.
        
        Args:
            index: GPU index
            
        Returns:
            Optional[GPUUsage]: GPU usage information or None if not available
        """
        if not self._nvml_initialized or index >= len(self._gpus):
            return None
            
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(index)
            
            # Get utilization
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpu_util = utilization.gpu / 100.0
            
            # Get memory usage
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            memory_used = memory_info.used
            memory_total = memory_info.total
            
            # Get temperature
            temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            
            # Get power usage
            try:
                power_usage = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # Convert from mW to W
            except Exception:
                power_usage = None
            
            # Get encoder/decoder usage
            try:
                encoder_stats = pynvml.nvmlDeviceGetEncoderUtilization(handle)
                encoder_usage = encoder_stats[0] / 100.0
            except Exception:
                encoder_usage = None
                
            try:
                decoder_stats = pynvml.nvmlDeviceGetDecoderUtilization(handle)
                decoder_usage = decoder_stats[0] / 100.0
            except Exception:
                decoder_usage = None
            
            # Create GPU usage object
            gpu_usage = GPUUsage(
                index=index,
                utilization=gpu_util,
                memory_used=memory_used,
                memory_total=memory_total,
                temperature=temperature,
                power_usage=power_usage,
                encoder_usage=encoder_usage,
                decoder_usage=decoder_usage,
                details={
                    "memory_free": memory_info.free,
                    "memory_used_percent": memory_used / memory_total if memory_total > 0 else 0.0,
                }
            )
            
            return gpu_usage
            
        except Exception as e:
            self.logger.error(f"Error getting GPU {index} usage: {str(e)}")
            return None
    
    def get_all_gpu_usage(self) -> List[GPUUsage]:
        """
        Get current usage for all GPUs.
        
        Returns:
            List[GPUUsage]: List of GPU usage information
        """
        usages = []
        for i in range(len(self._gpus)):
            usage = self.get_gpu_usage(i)
            if usage:
                usages.append(usage)
        return usages
    
    def start_monitoring(self, interval: float = 5.0) -> None:
        """
        Start GPU monitoring.
        
        Args:
            interval: Monitoring interval in seconds
        """
        if self._monitoring_enabled or not self._nvml_initialized:
            return
            
        self._monitoring_interval = interval
        self._monitoring_enabled = True
        self._stop_event.clear()
        
        # Start monitoring thread
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="GPUMonitor"
        )
        self._monitoring_thread.start()
        
        self.logger.debug(f"GPU monitoring started with interval {interval}s")
    
    def stop_monitoring(self) -> None:
        """Stop GPU monitoring."""
        if not self._monitoring_enabled:
            return
            
        self._monitoring_enabled = False
        self._stop_event.set()
        
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=2.0)
            
        self.logger.debug("GPU monitoring stopped")
    
    def _monitoring_loop(self) -> None:
        """GPU monitoring loop."""
        while not self._stop_event.is_set():
            try:
                # Get current GPU usage for all GPUs
                for i in range(len(self._gpus)):
                    usage = self.get_gpu_usage(i)
                    if not usage:
                        continue
                        
                    # Store in history (limit to last 100 entries)
                    self._usage_history[i].append(usage)
                    if len(self._usage_history[i]) > 100:
                        self._usage_history[i].pop(0)
                        
                    # Update statistics
                    self._stats["peak_utilization"][i] = max(
                        self._stats["peak_utilization"].get(i, 0.0),
                        usage.utilization
                    )
                    self._stats["peak_memory_usage"][i] = max(
                        self._stats["peak_memory_usage"].get(i, 0.0),
                        usage.memory_utilization
                    )
                    
                    if usage.temperature is not None:
                        self._stats["peak_temperature"][i] = max(
                            self._stats["peak_temperature"].get(i, 0.0),
                            usage.temperature
                        )
                        
                    if usage.power_usage is not None:
                        self._stats["peak_power_usage"][i] = max(
                            self._stats["peak_power_usage"].get(i, 0.0),
                            usage.power_usage
                        )
                        
                    if usage.encoder_usage is not None:
                        self._stats["peak_encoder_usage"][i] = max(
                            self._stats["peak_encoder_usage"].get(i, 0.0),
                            usage.encoder_usage
                        )
                        
                    if usage.decoder_usage is not None:
                        self._stats["peak_decoder_usage"][i] = max(
                            self._stats["peak_decoder_usage"].get(i, 0.0),
                            usage.decoder_usage
                        )
                
                # Sleep until next interval
                time.sleep(self._monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in GPU monitoring: {str(e)}")
                time.sleep(1.0)  # Sleep briefly before retrying
    
    def get_usage_history(self, index: int, count: int = None) -> List[GPUUsage]:
        """
        Get GPU usage history.
        
        Args:
            index: GPU index
            count: Number of entries to return (None for all)
            
        Returns:
            List[GPUUsage]: GPU usage history
        """
        history = self._usage_history.get(index, [])
        
        if count is not None:
            history = history[-count:]
            
        return history
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get GPU statistics.
        
        Returns:
            Dict[str, Any]: GPU statistics
        """
        return self._stats.copy()
    
    def reset_stats(self) -> None:
        """Reset GPU statistics."""
        for i in range(len(self._gpus)):
            self._stats["peak_utilization"][i] = 0.0
            self._stats["peak_memory_usage"][i] = 0.0
            self._stats["peak_temperature"][i] = 0.0
            self._stats["peak_power_usage"][i] = 0.0
            self._stats["peak_encoder_usage"][i] = 0.0
            self._stats["peak_decoder_usage"][i] = 0.0
            
        self.logger.debug("Reset GPU statistics")
    
    def shutdown(self) -> None:
        """Shutdown the GPU manager."""
        self.stop_monitoring()
        
        # Shutdown NVML
        if self._nvml_initialized:
            try:
                pynvml.nvmlShutdown()
                self._nvml_initialized = False
                self.logger.debug("NVML shutdown")
            except Exception as e:
                self.logger.warning(f"Error shutting down NVML: {str(e)}")
        
        self.logger.debug("GPU manager shutdown")


# Singleton instance
_gpu_manager = None


def get_gpu_manager() -> GPUManager:
    """
    Get the singleton GPU manager instance.
    
    Returns:
        GPUManager: The singleton GPU manager instance
    """
    global _gpu_manager
    if _gpu_manager is None:
        _gpu_manager = GPUManager()
    return _gpu_manager


# Module-level functions for convenience

def get_gpus() -> List[GPUInfo]:
    """
    Get list of available GPUs.
    
    Returns:
        List[GPUInfo]: List of GPU information
    """
    return get_gpu_manager().get_gpus()


def get_gpu_count() -> int:
    """
    Get number of available GPUs.
    
    Returns:
        int: Number of GPUs
    """
    return get_gpu_manager().get_gpu_count()


def has_encoding_capability(capability: GPUCapability) -> bool:
    """
    Check if any GPU has the specified encoding capability.
    
    Args:
        capability: Encoding capability to check
        
    Returns:
        bool: True if any GPU has the capability, False otherwise
    """
    return get_gpu_manager().has_encoding_capability(capability)


def get_gpu_usage(index: int) -> Optional[GPUUsage]:
    """
    Get current usage for a specific GPU.
    
    Args:
        index: GPU index
        
    Returns:
        Optional[GPUUsage]: GPU usage information or None if not available
    """
    return get_gpu_manager().get_gpu_usage(index)


def get_all_gpu_usage() -> List[GPUUsage]:
    """
    Get current usage for all GPUs.
    
    Returns:
        List[GPUUsage]: List of GPU usage information
    """
    return get_gpu_manager().get_all_gpu_usage()


def start_gpu_monitoring(interval: float = 5.0) -> None:
    """
    Start GPU monitoring.
    
    Args:
        interval: Monitoring interval in seconds
    """
    return get_gpu_manager().start_monitoring(interval)


def stop_gpu_monitoring() -> None:
    """Stop GPU monitoring."""
    return get_gpu_manager().stop_monitoring()


def get_gpu_usage_history(index: int, count: int = None) -> List[GPUUsage]:
    """
    Get GPU usage history.
    
    Args:
        index: GPU index
        count: Number of entries to return (None for all)
        
    Returns:
        List[GPUUsage]: GPU usage history
    """
    return get_gpu_manager().get_usage_history(index, count)


def get_gpu_stats() -> Dict[str, Any]:
    """
    Get GPU statistics.
    
    Returns:
        Dict[str, Any]: GPU statistics
    """
    return get_gpu_manager().get_stats()


def reset_gpu_stats() -> None:
    """Reset GPU statistics."""
    return get_gpu_manager().reset_stats()


def shutdown_gpu_manager() -> None:
    """Shutdown the GPU manager."""
    global _gpu_manager
    if _gpu_manager is not None:
        _gpu_manager.shutdown()
        _gpu_manager = None
