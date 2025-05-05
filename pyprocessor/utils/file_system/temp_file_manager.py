"""
Temporary file management module for PyProcessor.

This module provides functionality for managing temporary files, including:
- Configurable temporary file locations
- Disk space monitoring
- Automatic cleanup of temporary files
- Scheduled cleanup of orphaned temporary files
- Disk space threshold warnings
- Emergency cleanup procedures
- Temporary file tracking and reporting
"""

import os
import shutil
import tempfile
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Optional, Union

# Import path manager for path handling
from pyprocessor.utils.file_system.path_manager import get_path_manager
from pyprocessor.utils.logging.log_manager import get_logger


# Import resource manager for disk space monitoring
# Use a deferred import to avoid circular imports
def get_resource_manager():
    from pyprocessor.utils.process.resource_manager import get_resource_manager

    return get_resource_manager()


def get_resource_types():
    from pyprocessor.utils.process.resource_manager import ResourceType

    return ResourceType


def get_resource_states():
    from pyprocessor.utils.process.resource_manager import ResourceState

    return ResourceState


# Placeholder for temporary file registry
# This will track all temporary files created by the application
_temp_file_registry = {}

# Placeholder for cleanup thread
_cleanup_thread = None
_stop_cleanup_event = threading.Event()

# Default thresholds
DEFAULT_WARNING_THRESHOLD = 0.8  # 80% disk usage
DEFAULT_CRITICAL_THRESHOLD = 0.95  # 95% disk usage


class TempFileManager:
    """
    Manager for temporary files with disk space monitoring.

    This class provides functionality for:
    - Creating and tracking temporary files
    - Monitoring disk space usage
    - Automatic cleanup of temporary files
    - Emergency cleanup when disk space is critically low
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Ensure singleton pattern."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TempFileManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, logger=None):
        """Initialize the temporary file manager."""
        # Only initialize once
        if getattr(self, "_initialized", False):
            return

        # Get logger
        self.logger = logger or get_logger()

        # Get path manager
        self.path_manager = get_path_manager()

        # Initialize registry for temporary files
        self._temp_files = {}

        # Initialize configuration
        self._temp_dir = None
        self._warning_threshold = DEFAULT_WARNING_THRESHOLD
        self._critical_threshold = DEFAULT_CRITICAL_THRESHOLD

        # Initialize monitoring
        self._monitoring_enabled = False
        self._monitoring_interval = 60  # seconds
        self._cleanup_interval = 3600  # seconds (1 hour)

        # Initialize callbacks
        self._warning_callbacks = []
        self._critical_callbacks = []

        # Mark as initialized
        self._initialized = True
        self.logger.debug("Temporary file manager initialized")

    def configure_temp_dir(
        self, temp_dir: Union[str, Path] = None, create_if_missing: bool = True
    ) -> Path:
        """
        Configure the temporary file directory.

        Args:
            temp_dir: Path to the temporary file directory (default: system temp directory)
            create_if_missing: Whether to create the directory if it doesn't exist

        Returns:
            Path: The configured temporary directory
        """
        if temp_dir is None:
            # Use system temp directory with a PyProcessor subdirectory
            temp_dir = Path(tempfile.gettempdir()) / "PyProcessor"
        else:
            temp_dir = self.path_manager.normalize_path(temp_dir)

        # Create directory if it doesn't exist and create_if_missing is True
        if create_if_missing and not temp_dir.exists():
            temp_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Created temporary directory: {temp_dir}")

        self._temp_dir = temp_dir
        self.logger.debug(f"Configured temporary directory: {temp_dir}")
        return temp_dir

    def get_temp_dir(self) -> Path:
        """
        Get the configured temporary directory.

        Returns:
            Path: The configured temporary directory
        """
        if self._temp_dir is None:
            return self.configure_temp_dir()
        return self._temp_dir

    def create_temp_file(
        self,
        prefix: str = "pyprocessor_",
        suffix: str = "",
        parent_dir: Optional[Union[str, Path]] = None,
    ) -> Path:
        """
        Create a temporary file and register it for tracking.

        Args:
            prefix: Prefix for the temporary file name
            suffix: Suffix for the temporary file name
            parent_dir: Parent directory for the temporary file (default: configured temp directory)

        Returns:
            Path: Path to the created temporary file
        """
        # Use configured temp directory if parent_dir is not specified
        if parent_dir is None:
            parent_dir = self.get_temp_dir()
        else:
            parent_dir = self.path_manager.normalize_path(parent_dir)
            if not parent_dir.exists():
                parent_dir.mkdir(parents=True, exist_ok=True)

        # Create temporary file
        fd, temp_file_path = tempfile.mkstemp(
            suffix=suffix, prefix=prefix, dir=str(parent_dir)
        )
        os.close(fd)  # Close the file descriptor
        temp_file = Path(temp_file_path)

        # Register the temporary file
        file_id = str(uuid.uuid4())
        self._temp_files[file_id] = {
            "path": temp_file,
            "created": datetime.now(),
            "type": "file",
            "size": 0,  # Initial size
            "last_accessed": datetime.now(),
            "in_use": True,
        }

        self.logger.debug(f"Created temporary file: {temp_file}")
        return temp_file

    def create_temp_dir(
        self,
        prefix: str = "pyprocessor_",
        parent_dir: Optional[Union[str, Path]] = None,
    ) -> Path:
        """
        Create a temporary directory and register it for tracking.

        Args:
            prefix: Prefix for the temporary directory name
            parent_dir: Parent directory for the temporary directory (default: configured temp directory)

        Returns:
            Path: Path to the created temporary directory
        """
        # Use configured temp directory if parent_dir is not specified
        if parent_dir is None:
            parent_dir = self.get_temp_dir()
        else:
            parent_dir = self.path_manager.normalize_path(parent_dir)
            if not parent_dir.exists():
                parent_dir.mkdir(parents=True, exist_ok=True)

        # Create temporary directory
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix, dir=str(parent_dir)))

        # Register the temporary directory
        dir_id = str(uuid.uuid4())
        self._temp_files[dir_id] = {
            "path": temp_dir,
            "created": datetime.now(),
            "type": "directory",
            "size": 0,  # Initial size
            "last_accessed": datetime.now(),
            "in_use": True,
        }

        self.logger.debug(f"Created temporary directory: {temp_dir}")
        return temp_dir

    def mark_temp_file_in_use(
        self, file_path: Union[str, Path], in_use: bool = True
    ) -> bool:
        """
        Mark a temporary file as in use or not in use.

        Args:
            file_path: Path to the temporary file
            in_use: Whether the file is in use

        Returns:
            bool: True if successful, False otherwise
        """
        file_path = self.path_manager.normalize_path(file_path)

        # Find the file in the registry
        for file_id, file_info in self._temp_files.items():
            if self.path_manager.is_same_path(file_info["path"], file_path):
                file_info["in_use"] = in_use
                file_info["last_accessed"] = datetime.now()
                return True

        return False

    def update_temp_file_size(self, file_path: Union[str, Path]) -> int:
        """
        Update the size of a temporary file in the registry.

        Args:
            file_path: Path to the temporary file

        Returns:
            int: The updated size in bytes, or -1 if the file is not found
        """
        file_path = self.path_manager.normalize_path(file_path)

        # Find the file in the registry
        for file_id, file_info in self._temp_files.items():
            if self.path_manager.is_same_path(file_info["path"], file_path):
                try:
                    if file_info["type"] == "file":
                        size = file_path.stat().st_size
                    else:  # directory
                        size = sum(
                            f.stat().st_size
                            for f in file_path.glob("**/*")
                            if f.is_file()
                        )

                    file_info["size"] = size
                    file_info["last_accessed"] = datetime.now()
                    return size
                except (FileNotFoundError, PermissionError):
                    return -1

        return -1

    def get_disk_space_info(self, path: Optional[Union[str, Path]] = None) -> Dict:
        """
        Get disk space information for a path.

        Args:
            path: Path to check disk space for (default: temp directory)

        Returns:
            Dict: Disk space information
        """
        if path is None:
            path = self.get_temp_dir()
        else:
            path = self.path_manager.normalize_path(path)

        try:
            # Get disk usage from psutil
            usage = shutil.disk_usage(str(path))

            # Calculate utilization
            utilization = usage.used / usage.total

            # Determine state based on thresholds
            if utilization >= self._critical_threshold:
                state = "critical"
            elif utilization >= self._warning_threshold:
                state = "warning"
            else:
                state = "normal"

            return {
                "path": str(path),
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "utilization": utilization,
                "state": state,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Error getting disk space info for {path}: {str(e)}")
            return {
                "path": str(path),
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def cleanup_temp_file(self, file_path: Union[str, Path]) -> bool:
        """
        Clean up a specific temporary file.

        Args:
            file_path: Path to the temporary file to clean up

        Returns:
            bool: True if successful, False otherwise
        """
        file_path = self.path_manager.normalize_path(file_path)

        # Find the file in the registry
        file_id_to_remove = None
        for file_id, file_info in self._temp_files.items():
            if self.path_manager.is_same_path(file_info["path"], file_path):
                file_id_to_remove = file_id
                break

        if file_id_to_remove is None:
            self.logger.warning(f"Temporary file not found in registry: {file_path}")
            return False

        # Check if the file is in use
        if self._temp_files[file_id_to_remove]["in_use"]:
            self.logger.warning(
                f"Cannot clean up temporary file that is in use: {file_path}"
            )
            return False

        try:
            # Remove the file or directory
            if self._temp_files[file_id_to_remove]["type"] == "file":
                if file_path.exists():
                    file_path.unlink()
            else:  # directory
                if file_path.exists():
                    shutil.rmtree(file_path)

            # Remove from registry
            del self._temp_files[file_id_to_remove]

            self.logger.debug(
                f"Cleaned up temporary {self._temp_files[file_id_to_remove]['type']}: {file_path}"
            )
            return True
        except Exception as e:
            self.logger.error(f"Error cleaning up temporary file {file_path}: {str(e)}")
            return False

    def cleanup_all_temp_files(self, older_than: Optional[int] = None) -> int:
        """
        Clean up all registered temporary files.

        Args:
            older_than: Only clean up files older than this many seconds

        Returns:
            int: Number of files cleaned up
        """
        files_to_remove = []

        # Find files to remove
        now = datetime.now()
        for file_id, file_info in self._temp_files.items():
            # Skip files that are in use
            if file_info["in_use"]:
                continue

            # Check age if older_than is specified
            if older_than is not None:
                age = (now - file_info["last_accessed"]).total_seconds()
                if age < older_than:
                    continue

            files_to_remove.append(file_id)

        # Remove files
        count = 0
        for file_id in files_to_remove:
            file_info = self._temp_files[file_id]
            try:
                if file_info["type"] == "file":
                    if file_info["path"].exists():
                        file_info["path"].unlink()
                else:  # directory
                    if file_info["path"].exists():
                        shutil.rmtree(file_info["path"])

                del self._temp_files[file_id]
                count += 1
                self.logger.debug(
                    f"Cleaned up temporary {file_info['type']}: {file_info['path']}"
                )
            except Exception as e:
                self.logger.error(
                    f"Error cleaning up temporary file {file_info['path']}: {str(e)}"
                )

        return count

    def emergency_cleanup(self) -> int:
        """
        Perform emergency cleanup when disk space is critically low.

        Returns:
            int: Number of files cleaned up
        """
        # First, clean up all unused temporary files regardless of age
        count = self.cleanup_all_temp_files()

        # If disk space is still critical, clean up older in-use files
        disk_info = self.get_disk_space_info()
        if disk_info.get("state") == "critical":
            self.logger.warning(
                "Disk space still critical after cleaning unused files. Cleaning older in-use files."
            )

            # Find older in-use files (older than 1 hour)
            files_to_remove = []
            now = datetime.now()
            for file_id, file_info in self._temp_files.items():
                age = (now - file_info["created"]).total_seconds()
                if age > 3600:  # 1 hour
                    files_to_remove.append(file_id)

            # Remove files
            for file_id in files_to_remove:
                file_info = self._temp_files[file_id]
                try:
                    if file_info["type"] == "file":
                        if file_info["path"].exists():
                            file_info["path"].unlink()
                    else:  # directory
                        if file_info["path"].exists():
                            shutil.rmtree(file_info["path"])

                    del self._temp_files[file_id]
                    count += 1
                    self.logger.warning(
                        f"Emergency cleanup of in-use temporary {file_info['type']}: {file_info['path']}"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Error in emergency cleanup of {file_info['path']}: {str(e)}"
                    )

        return count

    def register_warning_callback(self, callback: Callable[[Dict], None]) -> None:
        """
        Register a callback for disk space warning.

        Args:
            callback: Callback function that takes disk space info as argument
        """
        if callback not in self._warning_callbacks:
            self._warning_callbacks.append(callback)

    def register_critical_callback(self, callback: Callable[[Dict], None]) -> None:
        """
        Register a callback for critical disk space.

        Args:
            callback: Callback function that takes disk space info as argument
        """
        if callback not in self._critical_callbacks:
            self._critical_callbacks.append(callback)

    def start_monitoring(
        self, interval: int = 60, cleanup_interval: int = 3600
    ) -> None:
        """
        Start monitoring disk space and scheduled cleanup.

        Args:
            interval: Monitoring interval in seconds
            cleanup_interval: Cleanup interval in seconds
        """
        if self._monitoring_enabled:
            return

        self._monitoring_enabled = True
        self._monitoring_interval = interval
        self._cleanup_interval = cleanup_interval

        # Start monitoring thread
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True, name="TempFileMonitor"
        )
        self._monitoring_thread.start()

        self.logger.debug(
            f"Started temporary file monitoring with interval {interval}s"
        )

    def stop_monitoring(self) -> None:
        """
        Stop monitoring disk space and scheduled cleanup.
        """
        if not self._monitoring_enabled:
            return

        self._monitoring_enabled = False

        # Wait for monitoring thread to stop
        if hasattr(self, "_monitoring_thread") and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=2.0)

        self.logger.debug("Stopped temporary file monitoring")

    def _monitoring_loop(self) -> None:
        """
        Monitoring loop for disk space and scheduled cleanup.
        """
        last_cleanup_time = time.time()

        while self._monitoring_enabled:
            try:
                # Check disk space
                disk_info = self.get_disk_space_info()

                # Call callbacks based on state
                if disk_info.get("state") == "warning":
                    for callback in self._warning_callbacks:
                        try:
                            callback(disk_info)
                        except Exception as e:
                            self.logger.error(f"Error in warning callback: {str(e)}")

                elif disk_info.get("state") == "critical":
                    # Call critical callbacks
                    for callback in self._critical_callbacks:
                        try:
                            callback(disk_info)
                        except Exception as e:
                            self.logger.error(f"Error in critical callback: {str(e)}")

                    # Perform emergency cleanup
                    self.emergency_cleanup()

                # Check if it's time for scheduled cleanup
                current_time = time.time()
                if current_time - last_cleanup_time >= self._cleanup_interval:
                    # Clean up files older than 24 hours
                    count = self.cleanup_all_temp_files(older_than=86400)  # 24 hours
                    if count > 0:
                        self.logger.info(
                            f"Scheduled cleanup removed {count} temporary files"
                        )

                    last_cleanup_time = current_time

                # Sleep until next check
                time.sleep(self._monitoring_interval)

            except Exception as e:
                self.logger.error(f"Error in temporary file monitoring: {str(e)}")
                time.sleep(10)  # Sleep briefly before retrying

    def get_temp_file_stats(self) -> Dict:
        """
        Get statistics about temporary files.

        Returns:
            Dict: Statistics about temporary files
        """
        total_size = 0
        file_count = 0
        dir_count = 0
        in_use_count = 0
        oldest_file = None
        newest_file = None

        # Calculate statistics
        for file_id, file_info in self._temp_files.items():
            # Update file size
            if file_info["path"].exists():
                self.update_temp_file_size(file_info["path"])

            total_size += file_info["size"]

            if file_info["type"] == "file":
                file_count += 1
            else:  # directory
                dir_count += 1

            if file_info["in_use"]:
                in_use_count += 1

            # Track oldest and newest files
            if (
                oldest_file is None
                or file_info["created"] < self._temp_files[oldest_file]["created"]
            ):
                oldest_file = file_id

            if (
                newest_file is None
                or file_info["created"] > self._temp_files[newest_file]["created"]
            ):
                newest_file = file_id

        # Get disk space info
        disk_info = self.get_disk_space_info()

        return {
            "total_files": file_count,
            "total_directories": dir_count,
            "in_use_count": in_use_count,
            "total_size": total_size,
            "oldest_file": (
                str(self._temp_files[oldest_file]["path"]) if oldest_file else None
            ),
            "oldest_file_age": (
                (
                    datetime.now() - self._temp_files[oldest_file]["created"]
                ).total_seconds()
                if oldest_file
                else None
            ),
            "newest_file": (
                str(self._temp_files[newest_file]["path"]) if newest_file else None
            ),
            "newest_file_age": (
                (
                    datetime.now() - self._temp_files[newest_file]["created"]
                ).total_seconds()
                if newest_file
                else None
            ),
            "disk_space": disk_info,
            "temp_dir": str(self.get_temp_dir()),
            "monitoring_enabled": self._monitoring_enabled,
            "monitoring_interval": self._monitoring_interval,
            "cleanup_interval": self._cleanup_interval,
            "warning_threshold": self._warning_threshold,
            "critical_threshold": self._critical_threshold,
        }


# Singleton instance
_temp_file_manager = None


def get_temp_file_manager(logger=None) -> TempFileManager:
    """
    Get the singleton temporary file manager instance.

    Args:
        logger: Optional logger object

    Returns:
        TempFileManager: The singleton temporary file manager instance
    """
    global _temp_file_manager
    if _temp_file_manager is None:
        _temp_file_manager = TempFileManager(logger)
    return _temp_file_manager


# Module-level functions for convenience


def configure_temp_dir(
    temp_dir: Union[str, Path], create_if_missing: bool = True
) -> Path:
    """
    Configure the temporary file directory.

    Args:
        temp_dir: Path to the temporary file directory
        create_if_missing: Whether to create the directory if it doesn't exist

    Returns:
        Path: The configured temporary directory
    """
    return get_temp_file_manager().configure_temp_dir(temp_dir, create_if_missing)


def get_temp_dir() -> Path:
    """
    Get the configured temporary directory.

    Returns:
        Path: The configured temporary directory
    """
    return get_temp_file_manager().get_temp_dir()


def create_temp_file(
    prefix: str = "pyprocessor_",
    suffix: str = "",
    parent_dir: Optional[Union[str, Path]] = None,
) -> Path:
    """
    Create a temporary file and register it for tracking.

    Args:
        prefix: Prefix for the temporary file name
        suffix: Suffix for the temporary file name
        parent_dir: Parent directory for the temporary file

    Returns:
        Path: Path to the created temporary file
    """
    return get_temp_file_manager().create_temp_file(prefix, suffix, parent_dir)


def create_temp_dir(
    prefix: str = "pyprocessor_", parent_dir: Optional[Union[str, Path]] = None
) -> Path:
    """
    Create a temporary directory and register it for tracking.

    Args:
        prefix: Prefix for the temporary directory name
        parent_dir: Parent directory for the temporary directory

    Returns:
        Path: Path to the created temporary directory
    """
    return get_temp_file_manager().create_temp_dir(prefix, parent_dir)


def mark_temp_file_in_use(file_path: Union[str, Path], in_use: bool = True) -> bool:
    """
    Mark a temporary file as in use or not in use.

    Args:
        file_path: Path to the temporary file
        in_use: Whether the file is in use

    Returns:
        bool: True if successful, False otherwise
    """
    return get_temp_file_manager().mark_temp_file_in_use(file_path, in_use)


def cleanup_temp_file(file_path: Union[str, Path]) -> bool:
    """
    Clean up a specific temporary file.

    Args:
        file_path: Path to the temporary file to clean up

    Returns:
        bool: True if successful, False otherwise
    """
    return get_temp_file_manager().cleanup_temp_file(file_path)


def cleanup_all_temp_files(older_than: Optional[int] = None) -> int:
    """
    Clean up all registered temporary files.

    Args:
        older_than: Only clean up files older than this many seconds

    Returns:
        int: Number of files cleaned up
    """
    return get_temp_file_manager().cleanup_all_temp_files(older_than)


def emergency_cleanup() -> int:
    """
    Perform emergency cleanup when disk space is critically low.

    Returns:
        int: Number of files cleaned up
    """
    return get_temp_file_manager().emergency_cleanup()


def start_monitoring(interval: int = 60, cleanup_interval: int = 3600) -> None:
    """
    Start monitoring disk space and scheduled cleanup.

    Args:
        interval: Monitoring interval in seconds
        cleanup_interval: Cleanup interval in seconds
    """
    return get_temp_file_manager().start_monitoring(interval, cleanup_interval)


def stop_monitoring() -> None:
    """Stop monitoring disk space and scheduled cleanup."""
    return get_temp_file_manager().stop_monitoring()


def get_disk_space_info(path: Optional[Union[str, Path]] = None) -> Dict:
    """
    Get disk space information for a path.

    Args:
        path: Path to check disk space for (default: temp directory)

    Returns:
        Dict: Disk space information
    """
    return get_temp_file_manager().get_disk_space_info(path)


def register_warning_callback(callback: Callable[[Dict], None]) -> None:
    """
    Register a callback for disk space warning.

    Args:
        callback: Callback function that takes disk space info as argument
    """
    return get_temp_file_manager().register_warning_callback(callback)


def register_critical_callback(callback: Callable[[Dict], None]) -> None:
    """
    Register a callback for critical disk space.

    Args:
        callback: Callback function that takes disk space info as argument
    """
    return get_temp_file_manager().register_critical_callback(callback)


def get_temp_file_stats() -> Dict:
    """
    Get statistics about temporary files.

    Returns:
        Dict: Statistics about temporary files
    """
    return get_temp_file_manager().get_temp_file_stats()


def set_thresholds(
    warning_threshold: float = DEFAULT_WARNING_THRESHOLD,
    critical_threshold: float = DEFAULT_CRITICAL_THRESHOLD,
) -> None:
    """
    Set disk space thresholds for warnings and critical alerts.

    Args:
        warning_threshold: Warning threshold (0.0-1.0)
        critical_threshold: Critical threshold (0.0-1.0)
    """
    manager = get_temp_file_manager()
    manager._warning_threshold = warning_threshold
    manager._critical_threshold = critical_threshold
