"""
Resource management utilities for PyProcessor.

This module provides a centralized way to manage system resources, including:
- CPU usage monitoring and management
- Memory usage monitoring and management
- Disk usage monitoring and management
- Resource allocation and limits
- Resource usage statistics
"""

import os
import platform
import threading
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import psutil

from pyprocessor.utils.log_manager import get_logger
from pyprocessor.utils.process.gpu_manager import (
    get_all_gpu_usage,
    start_gpu_monitoring,
    stop_gpu_monitoring,
)


# Import temp file manager for disk space monitoring
# Use a deferred import to avoid circular imports
def get_temp_file_manager():
    from pyprocessor.utils.file_system.temp_file_manager import get_temp_file_manager

    return get_temp_file_manager()


class ResourceType(Enum):
    """Types of system resources."""

    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    GPU = "gpu"  # Planned for future


class ResourceState(Enum):
    """Resource utilization states."""

    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


class ResourceThresholds:
    """Thresholds for resource utilization states."""

    def __init__(
        self,
        warning_threshold: float = 0.7,  # 70%
        critical_threshold: float = 0.9,  # 90%
    ):
        """
        Initialize resource thresholds.

        Args:
            warning_threshold: Threshold for warning state (0.0-1.0)
            critical_threshold: Threshold for critical state (0.0-1.0)
        """
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    def get_state(self, utilization: float) -> ResourceState:
        """
        Get the resource state based on utilization.

        Args:
            utilization: Resource utilization (0.0-1.0)

        Returns:
            ResourceState: The resource state
        """
        if utilization >= self.critical_threshold:
            return ResourceState.CRITICAL
        elif utilization >= self.warning_threshold:
            return ResourceState.WARNING
        else:
            return ResourceState.NORMAL


class ResourceUsage:
    """Resource usage information."""

    def __init__(
        self,
        resource_type: ResourceType,
        utilization: float,
        available: float,
        total: float,
        state: ResourceState,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize resource usage.

        Args:
            resource_type: Type of resource
            utilization: Resource utilization (0.0-1.0)
            available: Available resource amount
            total: Total resource amount
            state: Resource state
            details: Additional details
        """
        self.resource_type = resource_type
        self.utilization = utilization
        self.available = available
        self.total = total
        self.state = state
        self.details = details or {}
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert resource usage to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of resource usage
        """
        return {
            "resource_type": self.resource_type.value,
            "utilization": self.utilization,
            "available": self.available,
            "total": self.total,
            "state": self.state.value,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class ResourceLimits:
    """Resource limits for processes."""

    def __init__(
        self,
        cpu_limit: Optional[float] = None,  # Percentage (0-100)
        memory_limit: Optional[int] = None,  # Bytes
        disk_limit: Optional[int] = None,  # Bytes
        gpu_limit: Optional[float] = None,  # Percentage (0-100)
        gpu_memory_limit: Optional[int] = None,  # Bytes
    ):
        """
        Initialize resource limits.

        Args:
            cpu_limit: CPU usage limit in percentage (0-100)
            memory_limit: Memory usage limit in bytes
            disk_limit: Disk usage limit in bytes
            gpu_limit: GPU usage limit in percentage (0-100)
            gpu_memory_limit: GPU memory usage limit in bytes
        """
        self.cpu_limit = cpu_limit
        self.memory_limit = memory_limit
        self.disk_limit = disk_limit
        self.gpu_limit = gpu_limit
        self.gpu_memory_limit = gpu_memory_limit

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert resource limits to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of resource limits
        """
        return {
            "cpu_limit": self.cpu_limit,
            "memory_limit": self.memory_limit,
            "disk_limit": self.disk_limit,
            "gpu_limit": self.gpu_limit,
            "gpu_memory_limit": self.gpu_memory_limit,
        }


class ResourceManager:
    """
    Centralized manager for system resources.

    This class provides:
    - Resource usage monitoring
    - Resource allocation and limits
    - Resource usage statistics
    - Resource usage callbacks
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ResourceManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialize the resource manager."""
        # Only initialize once
        if getattr(self, "_initialized", False):
            return

        # Get logger
        self.logger = get_logger()

        # Initialize resource thresholds
        self._thresholds = {
            ResourceType.CPU: ResourceThresholds(0.7, 0.9),
            ResourceType.MEMORY: ResourceThresholds(0.7, 0.9),
            ResourceType.DISK: ResourceThresholds(0.8, 0.95),
            ResourceType.GPU: ResourceThresholds(0.7, 0.9),
        }

        # Initialize resource usage history
        self._usage_history = {
            ResourceType.CPU: [],
            ResourceType.MEMORY: [],
            ResourceType.DISK: [],
            ResourceType.GPU: [],
        }

        # Initialize resource limits
        self._resource_limits = ResourceLimits()

        # Initialize resource callbacks
        self._callbacks = {
            ResourceState.WARNING: [],
            ResourceState.CRITICAL: [],
        }

        # Initialize monitoring
        self._monitoring_interval = 5.0  # seconds
        self._monitoring_enabled = False
        self._monitoring_thread = None
        self._stop_event = threading.Event()

        # Initialize process tracking
        self._tracked_processes = {}  # pid -> psutil.Process

        # Initialize statistics
        self._stats = {
            "cpu_peak": 0.0,
            "memory_peak": 0.0,
            "disk_peak": 0.0,
            "gpu_peak": 0.0,
            "gpu_memory_peak": 0.0,
            "warning_events": 0,
            "critical_events": 0,
        }

        # Mark as initialized
        self._initialized = True
        self.logger.debug("Resource manager initialized")

    def start_monitoring(self, interval: float = 5.0) -> None:
        """
        Start resource monitoring.

        Args:
            interval: Monitoring interval in seconds
        """
        if self._monitoring_enabled:
            return

        self._monitoring_interval = interval
        self._monitoring_enabled = True
        self._stop_event.clear()

        # Start monitoring thread
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True, name="ResourceMonitor"
        )
        self._monitoring_thread.start()

        # Start GPU monitoring if available
        try:
            start_gpu_monitoring(interval)
        except Exception as e:
            self.logger.warning(f"Failed to start GPU monitoring: {str(e)}")

        self.logger.debug(f"Resource monitoring started with interval {interval}s")

    def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        if not self._monitoring_enabled:
            return

        self._monitoring_enabled = False
        self._stop_event.set()

        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=2.0)

        # Stop GPU monitoring
        try:
            stop_gpu_monitoring()
        except Exception as e:
            self.logger.warning(f"Failed to stop GPU monitoring: {str(e)}")

        self.logger.debug("Resource monitoring stopped")

    def _monitoring_loop(self) -> None:
        """Resource monitoring loop."""
        while not self._stop_event.is_set():
            try:
                # Get current resource usage
                cpu_usage = self.get_cpu_usage()
                memory_usage = self.get_memory_usage()
                disk_usage = self.get_disk_usage()
                gpu_usage = self.get_gpu_usage()

                # Store in history (limit to last 100 entries)
                self._usage_history[ResourceType.CPU].append(cpu_usage)
                if len(self._usage_history[ResourceType.CPU]) > 100:
                    self._usage_history[ResourceType.CPU].pop(0)

                self._usage_history[ResourceType.MEMORY].append(memory_usage)
                if len(self._usage_history[ResourceType.MEMORY]) > 100:
                    self._usage_history[ResourceType.MEMORY].pop(0)

                self._usage_history[ResourceType.DISK].append(disk_usage)
                if len(self._usage_history[ResourceType.DISK]) > 100:
                    self._usage_history[ResourceType.DISK].pop(0)

                if gpu_usage:
                    self._usage_history[ResourceType.GPU].append(gpu_usage)
                    if len(self._usage_history[ResourceType.GPU]) > 100:
                        self._usage_history[ResourceType.GPU].pop(0)

                # Update statistics
                self._stats["cpu_peak"] = max(
                    self._stats["cpu_peak"], cpu_usage.utilization
                )
                self._stats["memory_peak"] = max(
                    self._stats["memory_peak"], memory_usage.utilization
                )
                self._stats["disk_peak"] = max(
                    self._stats["disk_peak"], disk_usage.utilization
                )

                if gpu_usage:
                    self._stats["gpu_peak"] = max(
                        self._stats["gpu_peak"], gpu_usage.utilization
                    )
                    self._stats["gpu_memory_peak"] = max(
                        self._stats["gpu_memory_peak"],
                        gpu_usage.details.get("memory_utilization", 0.0),
                    )

                # Check for warning/critical states and call callbacks
                resources_to_check = [cpu_usage, memory_usage, disk_usage]
                if gpu_usage:
                    resources_to_check.append(gpu_usage)

                for usage in resources_to_check:
                    if usage.state == ResourceState.WARNING:
                        self._stats["warning_events"] += 1
                        for callback in self._callbacks[ResourceState.WARNING]:
                            try:
                                callback(usage)
                            except Exception as e:
                                self.logger.error(
                                    f"Error in resource warning callback: {str(e)}"
                                )
                    elif usage.state == ResourceState.CRITICAL:
                        self._stats["critical_events"] += 1
                        for callback in self._callbacks[ResourceState.CRITICAL]:
                            try:
                                callback(usage)
                            except Exception as e:
                                self.logger.error(
                                    f"Error in resource critical callback: {str(e)}"
                                )

                # Check tracked processes
                self._check_tracked_processes()

                # Sleep until next interval
                time.sleep(self._monitoring_interval)

            except Exception as e:
                self.logger.error(f"Error in resource monitoring: {str(e)}")
                time.sleep(1.0)  # Sleep briefly before retrying

    def _check_tracked_processes(self) -> None:
        """Check resource usage of tracked processes."""
        pids_to_remove = []

        for pid, process in self._tracked_processes.items():
            try:
                # Check if process is still running
                if not process.is_running():
                    pids_to_remove.append(pid)
                    continue

                # Get process resource usage
                cpu_percent = process.cpu_percent() / 100.0
                memory_percent = process.memory_percent() / 100.0

                # Check against limits
                if self._resource_limits.cpu_limit is not None:
                    cpu_limit = self._resource_limits.cpu_limit / 100.0
                    if cpu_percent > cpu_limit:
                        self.logger.warning(
                            f"Process {pid} exceeded CPU limit: {cpu_percent:.2%} > {cpu_limit:.2%}"
                        )
                        # TODO: Implement resource limiting actions

                if self._resource_limits.memory_limit is not None:
                    memory_info = process.memory_info()
                    if memory_info.rss > self._resource_limits.memory_limit:
                        self.logger.warning(
                            f"Process {pid} exceeded memory limit: {memory_info.rss} > {self._resource_limits.memory_limit}"
                        )
                        # TODO: Implement resource limiting actions

            except psutil.NoSuchProcess:
                pids_to_remove.append(pid)
            except Exception as e:
                self.logger.error(f"Error checking process {pid}: {str(e)}")
                pids_to_remove.append(pid)

        # Remove processes that are no longer running
        for pid in pids_to_remove:
            del self._tracked_processes[pid]

    def get_cpu_usage(self) -> ResourceUsage:
        """
        Get current CPU usage.

        Returns:
            ResourceUsage: CPU usage information
        """
        try:
            # Get CPU usage percentage
            cpu_percent = psutil.cpu_percent(interval=0.1) / 100.0

            # Get CPU count
            cpu_count = psutil.cpu_count(logical=True)

            # Get CPU frequency
            cpu_freq = psutil.cpu_freq()
            current_freq = cpu_freq.current if cpu_freq else None

            # Get CPU state
            state = self._thresholds[ResourceType.CPU].get_state(cpu_percent)

            # Create CPU usage object
            cpu_usage = ResourceUsage(
                resource_type=ResourceType.CPU,
                utilization=cpu_percent,
                available=cpu_count * (1.0 - cpu_percent),
                total=cpu_count,
                state=state,
                details={
                    "count": cpu_count,
                    "frequency": current_freq,
                    "per_cpu": psutil.cpu_percent(interval=0.1, percpu=True),
                },
            )

            return cpu_usage

        except Exception as e:
            self.logger.error(f"Error getting CPU usage: {str(e)}")
            # Return default CPU usage
            return ResourceUsage(
                resource_type=ResourceType.CPU,
                utilization=0.0,
                available=1.0,
                total=1.0,
                state=ResourceState.NORMAL,
            )

    def get_memory_usage(self) -> ResourceUsage:
        """
        Get current memory usage.

        Returns:
            ResourceUsage: Memory usage information
        """
        try:
            # Get memory usage
            memory = psutil.virtual_memory()

            # Calculate utilization
            memory_percent = memory.percent / 100.0

            # Get memory state
            state = self._thresholds[ResourceType.MEMORY].get_state(memory_percent)

            # Create memory usage object
            memory_usage = ResourceUsage(
                resource_type=ResourceType.MEMORY,
                utilization=memory_percent,
                available=memory.available,
                total=memory.total,
                state=state,
                details={
                    "used": memory.used,
                    "free": memory.free,
                    "cached": getattr(memory, "cached", None),
                    "buffers": getattr(memory, "buffers", None),
                },
            )

            return memory_usage

        except Exception as e:
            self.logger.error(f"Error getting memory usage: {str(e)}")
            # Return default memory usage
            return ResourceUsage(
                resource_type=ResourceType.MEMORY,
                utilization=0.0,
                available=1.0,
                total=1.0,
                state=ResourceState.NORMAL,
            )

    def get_disk_usage(self, path: str = None) -> ResourceUsage:
        """
        Get current disk usage.

        Args:
            path: Path to check disk usage (default: current working directory)

        Returns:
            ResourceUsage: Disk usage information
        """
        try:
            # Use current working directory if path is not specified
            if path is None:
                path = os.getcwd()

            # Try to use temp_file_manager's disk space info if available
            try:
                temp_file_manager = get_temp_file_manager()
                disk_info = temp_file_manager.get_disk_space_info(path)

                # Map state from temp_file_manager to ResourceState
                if disk_info.get("state") == "critical":
                    state = ResourceState.CRITICAL
                elif disk_info.get("state") == "warning":
                    state = ResourceState.WARNING
                else:
                    state = ResourceState.NORMAL

                # Create disk usage object from temp_file_manager's info
                disk_usage = ResourceUsage(
                    resource_type=ResourceType.DISK,
                    utilization=disk_info.get("utilization", 0.0),
                    available=disk_info.get("free", 0),
                    total=disk_info.get("total", 1),
                    state=state,
                    details={
                        "used": disk_info.get("used", 0),
                        "free": disk_info.get("free", 0),
                        "path": path,
                        # Add I/O stats if available
                        "timestamp": disk_info.get("timestamp"),
                    },
                )

                # Try to add I/O stats
                try:
                    disk_io = psutil.disk_io_counters()
                    disk_usage.details.update(
                        {
                            "read_count": getattr(disk_io, "read_count", None),
                            "write_count": getattr(disk_io, "write_count", None),
                            "read_bytes": getattr(disk_io, "read_bytes", None),
                            "write_bytes": getattr(disk_io, "write_bytes", None),
                        }
                    )
                except Exception:
                    pass  # Ignore errors getting I/O stats

                return disk_usage

            except Exception:
                # Fall back to psutil if temp_file_manager is not available
                # Get disk usage
                disk = psutil.disk_usage(path)

                # Calculate utilization
                disk_percent = disk.percent / 100.0

                # Get disk state
                state = self._thresholds[ResourceType.DISK].get_state(disk_percent)

                # Get disk I/O statistics
                disk_io = psutil.disk_io_counters()

                # Create disk usage object
                disk_usage = ResourceUsage(
                    resource_type=ResourceType.DISK,
                    utilization=disk_percent,
                    available=disk.free,
                    total=disk.total,
                    state=state,
                    details={
                        "used": disk.used,
                        "free": disk.free,
                        "path": path,
                        "read_count": getattr(disk_io, "read_count", None),
                        "write_count": getattr(disk_io, "write_count", None),
                        "read_bytes": getattr(disk_io, "read_bytes", None),
                        "write_bytes": getattr(disk_io, "write_bytes", None),
                    },
                )

                return disk_usage

        except Exception as e:
            self.logger.error(f"Error getting disk usage: {str(e)}")
            # Return default disk usage
            return ResourceUsage(
                resource_type=ResourceType.DISK,
                utilization=0.0,
                available=1.0,
                total=1.0,
                state=ResourceState.NORMAL,
            )

    def get_gpu_usage(self) -> Optional[ResourceUsage]:
        """
        Get current GPU usage.

        Returns:
            Optional[ResourceUsage]: GPU usage information or None if not available
        """
        try:
            # Get GPU usage from GPU manager
            gpu_usages = get_all_gpu_usage()

            if not gpu_usages:
                return None

            # Use the GPU with highest utilization
            primary_gpu = max(gpu_usages, key=lambda x: x.utilization)

            # Calculate overall utilization
            utilization = primary_gpu.utilization

            # Get GPU state
            state = self._thresholds[ResourceType.GPU].get_state(utilization)

            # Create GPU usage object
            gpu_usage = ResourceUsage(
                resource_type=ResourceType.GPU,
                utilization=utilization,
                available=primary_gpu.memory_total - primary_gpu.memory_used,
                total=primary_gpu.memory_total,
                state=state,
                details={
                    "memory_used": primary_gpu.memory_used,
                    "memory_free": primary_gpu.memory_total - primary_gpu.memory_used,
                    "memory_utilization": primary_gpu.memory_utilization,
                    "temperature": primary_gpu.temperature,
                    "power_usage": primary_gpu.power_usage,
                    "encoder_usage": primary_gpu.encoder_usage,
                    "decoder_usage": primary_gpu.decoder_usage,
                    "gpu_index": primary_gpu.index,
                    "all_gpus": [gpu.to_dict() for gpu in gpu_usages],
                },
            )

            return gpu_usage

        except Exception as e:
            self.logger.error(f"Error getting GPU usage: {str(e)}")
            return None

    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information.

        Returns:
            Dict[str, Any]: System information
        """
        try:
            # Get system information
            system_info = {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "hostname": platform.node(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(logical=True),
                "physical_cpu_count": psutil.cpu_count(logical=False),
                "memory_total": psutil.virtual_memory().total,
                "boot_time": psutil.boot_time(),
            }

            return system_info

        except Exception as e:
            self.logger.error(f"Error getting system information: {str(e)}")
            return {}

    def track_process(self, pid: int) -> bool:
        """
        Track a process for resource usage.

        Args:
            pid: Process ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if process exists
            process = psutil.Process(pid)

            # Add to tracked processes
            self._tracked_processes[pid] = process

            self.logger.debug(f"Tracking process {pid}")
            return True

        except psutil.NoSuchProcess:
            self.logger.warning(f"Process {pid} not found")
            return False
        except Exception as e:
            self.logger.error(f"Error tracking process {pid}: {str(e)}")
            return False

    def untrack_process(self, pid: int) -> bool:
        """
        Stop tracking a process.

        Args:
            pid: Process ID

        Returns:
            bool: True if successful, False otherwise
        """
        if pid in self._tracked_processes:
            del self._tracked_processes[pid]
            self.logger.debug(f"Stopped tracking process {pid}")
            return True
        return False

    def set_resource_limits(self, resource_limits: ResourceLimits) -> None:
        """
        Set resource limits.

        Args:
            resource_limits: Resource limits
        """
        self._resource_limits = resource_limits
        self.logger.debug(f"Set resource limits: {resource_limits.to_dict()}")

    def set_thresholds(
        self, resource_type: ResourceType, warning: float, critical: float
    ) -> None:
        """
        Set resource thresholds.

        Args:
            resource_type: Resource type
            warning: Warning threshold (0.0-1.0)
            critical: Critical threshold (0.0-1.0)
        """
        self._thresholds[resource_type] = ResourceThresholds(warning, critical)
        self.logger.debug(
            f"Set {resource_type.value} thresholds: warning={warning:.2f}, critical={critical:.2f}"
        )

    def register_callback(
        self, callback: Callable[[ResourceUsage], None], state: ResourceState
    ) -> None:
        """
        Register a callback for resource state.

        Args:
            callback: Callback function
            state: Resource state to trigger callback
        """
        if state not in self._callbacks:
            self._callbacks[state] = []

        self._callbacks[state].append(callback)
        self.logger.debug(f"Registered callback for {state.value} resource state")

    def unregister_callback(
        self, callback: Callable[[ResourceUsage], None], state: ResourceState
    ) -> bool:
        """
        Unregister a callback for resource state.

        Args:
            callback: Callback function
            state: Resource state

        Returns:
            bool: True if successful, False otherwise
        """
        if state not in self._callbacks:
            return False

        try:
            self._callbacks[state].remove(callback)
            self.logger.debug(f"Unregistered callback for {state.value} resource state")
            return True
        except ValueError:
            return False

    def get_usage_history(
        self, resource_type: ResourceType, count: int = None
    ) -> List[ResourceUsage]:
        """
        Get resource usage history.

        Args:
            resource_type: Resource type
            count: Number of entries to return (None for all)

        Returns:
            List[ResourceUsage]: Resource usage history
        """
        history = self._usage_history.get(resource_type, [])

        if count is not None:
            history = history[-count:]

        return history

    def get_stats(self) -> Dict[str, Any]:
        """
        Get resource statistics.

        Returns:
            Dict[str, Any]: Resource statistics
        """
        return self._stats.copy()

    def reset_stats(self) -> None:
        """Reset resource statistics."""
        self._stats = {
            "cpu_peak": 0.0,
            "memory_peak": 0.0,
            "disk_peak": 0.0,
            "gpu_peak": 0.0,
            "gpu_memory_peak": 0.0,
            "warning_events": 0,
            "critical_events": 0,
        }
        self.logger.debug("Reset resource statistics")

    def shutdown(self) -> None:
        """Shutdown the resource manager."""
        self.stop_monitoring()
        self.logger.debug("Resource manager shutdown")


# Singleton instance
_resource_manager = None


def get_resource_manager() -> ResourceManager:
    """
    Get the singleton resource manager instance.

    Returns:
        ResourceManager: The singleton resource manager instance
    """
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager


# Module-level functions for convenience


def start_monitoring(interval: float = 5.0) -> None:
    """
    Start resource monitoring.

    Args:
        interval: Monitoring interval in seconds
    """
    return get_resource_manager().start_monitoring(interval)


def stop_monitoring() -> None:
    """Stop resource monitoring."""
    return get_resource_manager().stop_monitoring()


def get_cpu_usage() -> ResourceUsage:
    """
    Get current CPU usage.

    Returns:
        ResourceUsage: CPU usage information
    """
    return get_resource_manager().get_cpu_usage()


def get_memory_usage() -> ResourceUsage:
    """
    Get current memory usage.

    Returns:
        ResourceUsage: Memory usage information
    """
    return get_resource_manager().get_memory_usage()


def get_disk_usage(path: str = None) -> ResourceUsage:
    """
    Get current disk usage.

    Args:
        path: Path to check disk usage (default: current working directory)

    Returns:
        ResourceUsage: Disk usage information
    """
    return get_resource_manager().get_disk_usage(path)


def get_gpu_usage() -> Optional[ResourceUsage]:
    """
    Get current GPU usage.

    Returns:
        Optional[ResourceUsage]: GPU usage information or None if not available
    """
    return get_resource_manager().get_gpu_usage()


def get_system_info() -> Dict[str, Any]:
    """
    Get system information.

    Returns:
        Dict[str, Any]: System information
    """
    return get_resource_manager().get_system_info()


def track_process(pid: int) -> bool:
    """
    Track a process for resource usage.

    Args:
        pid: Process ID

    Returns:
        bool: True if successful, False otherwise
    """
    return get_resource_manager().track_process(pid)


def untrack_process(pid: int) -> bool:
    """
    Stop tracking a process.

    Args:
        pid: Process ID

    Returns:
        bool: True if successful, False otherwise
    """
    return get_resource_manager().untrack_process(pid)


def set_resource_limits(
    cpu_limit: Optional[float] = None,
    memory_limit: Optional[int] = None,
    disk_limit: Optional[int] = None,
    gpu_limit: Optional[float] = None,
    gpu_memory_limit: Optional[int] = None,
) -> None:
    """
    Set resource limits.

    Args:
        cpu_limit: CPU usage limit in percentage (0-100)
        memory_limit: Memory usage limit in bytes
        disk_limit: Disk usage limit in bytes
        gpu_limit: GPU usage limit in percentage (0-100)
        gpu_memory_limit: GPU memory usage limit in bytes
    """
    resource_limits = ResourceLimits(
        cpu_limit, memory_limit, disk_limit, gpu_limit, gpu_memory_limit
    )
    return get_resource_manager().set_resource_limits(resource_limits)


def set_thresholds(
    resource_type: ResourceType, warning: float, critical: float
) -> None:
    """
    Set resource thresholds.

    Args:
        resource_type: Resource type
        warning: Warning threshold (0.0-1.0)
        critical: Critical threshold (0.0-1.0)
    """
    return get_resource_manager().set_thresholds(resource_type, warning, critical)


def register_callback(
    callback: Callable[[ResourceUsage], None], state: ResourceState
) -> None:
    """
    Register a callback for resource state.

    Args:
        callback: Callback function
        state: Resource state to trigger callback
    """
    return get_resource_manager().register_callback(callback, state)


def unregister_callback(
    callback: Callable[[ResourceUsage], None], state: ResourceState
) -> bool:
    """
    Unregister a callback for resource state.

    Args:
        callback: Callback function
        state: Resource state

    Returns:
        bool: True if successful, False otherwise
    """
    return get_resource_manager().unregister_callback(callback, state)


def get_usage_history(
    resource_type: ResourceType, count: int = None
) -> List[ResourceUsage]:
    """
    Get resource usage history.

    Args:
        resource_type: Resource type
        count: Number of entries to return (None for all)

    Returns:
        List[ResourceUsage]: Resource usage history
    """
    return get_resource_manager().get_usage_history(resource_type, count)


def get_stats() -> Dict[str, Any]:
    """
    Get resource statistics.

    Returns:
        Dict[str, Any]: Resource statistics
    """
    return get_resource_manager().get_stats()


def reset_stats() -> None:
    """Reset resource statistics."""
    return get_resource_manager().reset_stats()


def shutdown_resource_manager() -> None:
    """Shutdown the resource manager."""
    if _resource_manager is not None:
        _resource_manager.shutdown()

    # Also shutdown GPU manager
    from pyprocessor.utils.process.gpu_manager import shutdown_gpu_manager

    shutdown_gpu_manager()
