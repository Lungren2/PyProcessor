"""
Centralized path handling module for PyProcessor.

This module provides a singleton path manager that can be used throughout the application.
It ensures consistent path handling and resolution across all modules.
"""

import os
import re
import sys
import platform
import shutil
import tempfile
import uuid
from pathlib import Path
import threading
from typing import Dict, List, Optional, Union, Callable, Tuple, Any
from contextlib import contextmanager

from pyprocessor.utils.logging.log_manager import get_logger

# Avoid circular import with cache_manager
# Define simple versions of the functions we need
def cache_get(key, default=None):
    """Simple cache get function to avoid circular imports."""
    return default

def cache_set(key, value, ttl=None):
    """Simple cache set function to avoid circular imports."""
    pass

def cache_delete(key):
    """Simple cache delete function to avoid circular imports."""
    pass

class CacheBackend:
    """Simple enum to avoid circular imports."""
    MEMORY = "memory"
    DISK = "disk"


class PathManager:
    """
    Singleton path manager for PyProcessor.

    This class provides a centralized path handling system with the following features:
    - Singleton pattern to ensure only one path manager instance exists
    - Consistent path normalization and resolution
    - Environment variable expansion in paths
    - Platform-specific path handling
    - Path caching for improved performance
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PathManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, logger=None):
        """
        Initialize the path manager.

        Args:
            logger: Optional logger object
        """
        # Only initialize once
        if self._initialized:
            return

        # Get logger
        self.logger = logger or get_logger()

        # Initialize path cache
        self._path_cache = {}

        # Initialize system information
        self.system = platform.system().lower()
        self.is_windows = self.system == "windows"
        self.is_macos = self.system == "darwin"
        self.is_linux = self.system == "linux"
        self.is_frozen = getattr(sys, "frozen", False)

        # Initialize executable extensions
        self.exe_ext = ".exe" if self.is_windows else ""

        # Mark as initialized
        self._initialized = True

        self.logger.debug("Path manager initialized")

    def expand_env_vars(self, path_str: str) -> str:
        """
        Expand environment variables in a path string.

        Supports both ${VAR} and %VAR% formats for compatibility with
        Unix/Linux/macOS and Windows.

        Args:
            path_str: Path string that may contain environment variables

        Returns:
            String with environment variables expanded
        """
        if not path_str:
            return path_str

        # First expand ${VAR} format (Unix/Linux/macOS style)
        if "${" in path_str:
            env_vars = re.findall(r'\${([^}]+)}', path_str)
            for var in env_vars:
                if var in os.environ:
                    path_str = path_str.replace(f"${{{var}}}", os.environ[var])

        # Then expand %VAR% format (Windows style)
        if "%" in path_str:
            path_str = os.path.expandvars(path_str)

        return path_str

    def normalize_path(self, path_str: Union[str, Path]) -> Path:
        """
        Normalize a path string to use the correct path separators for the current platform.

        Args:
            path_str: Path string that may use forward or backward slashes

        Returns:
            Path object with correct separators for the current platform
        """
        if not path_str:
            return None

        # Handle string or Path objects
        if isinstance(path_str, Path):
            return path_str

        # Expand environment variables and user home directory
        expanded_path = self.expand_env_vars(str(path_str))
        expanded_path = os.path.expanduser(expanded_path)

        # Convert to Path object which handles platform-specific separators
        return Path(expanded_path)

    def ensure_dir_exists(self, path: Union[str, Path]) -> Path:
        """
        Ensure a directory exists, creating it if necessary.

        Args:
            path: Path to the directory

        Returns:
            Path object for the directory
        """
        path = self.normalize_path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_base_dir(self) -> Path:
        """
        Get the base directory for the application.

        Returns:
            Path object for the base directory
        """
        # Check cache first
        cache_key = "path_manager:base_dir"
        cached_path = cache_get(cache_key)
        if cached_path is not None:
            return cached_path

        if self.is_frozen:
            # Running as a bundled executable
            base_dir = Path(sys._MEIPASS)
        else:
            # Running in a normal Python environment
            base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Cache the result (this path won't change during runtime)
        cache_set(cache_key, base_dir)

        # Also store in the internal cache for backward compatibility
        self._path_cache["base_dir"] = base_dir

        return base_dir

    def get_user_home_dir(self) -> Path:
        """
        Get the user's home directory.

        Returns:
            Path object for the user's home directory
        """
        # Check cache first
        cache_key = "path_manager:user_home_dir"
        cached_path = cache_get(cache_key)
        if cached_path is not None:
            return cached_path

        # Get the user's home directory
        home_dir = Path.home()

        # Cache the result (this path won't change during runtime)
        cache_set(cache_key, home_dir)

        # Also store in the internal cache for backward compatibility
        self._path_cache["user_home_dir"] = home_dir

        return home_dir

    def get_user_data_dir(self, app_name: str = "PyProcessor") -> Path:
        """
        Get the user data directory based on platform conventions.

        Args:
            app_name: Name of the application

        Returns:
            Path object for the user data directory
        """
        # Check cache first
        cache_key = f"user_data_dir_{app_name}"
        if cache_key in self._path_cache:
            return self._path_cache[cache_key]

        if self.is_windows:
            # Windows: Use %LOCALAPPDATA%
            base_dir = os.environ.get("LOCALAPPDATA")
            if not base_dir:
                base_dir = os.path.expandvars("%USERPROFILE%\\AppData\\Local")
            data_dir = Path(base_dir) / app_name
        elif self.is_macos:
            # macOS: Use ~/Library/Application Support
            data_dir = Path(os.path.expanduser(f"~/Library/Application Support/{app_name}"))
        else:
            # Linux: Use ~/.local/share
            data_dir = Path(os.path.expanduser(f"~/.local/share/{app_name}"))

        # Cache the result
        self._path_cache[cache_key] = data_dir

        return data_dir

    def get_user_config_dir(self, app_name: str = "PyProcessor") -> Path:
        """
        Get the user configuration directory based on platform conventions.

        Args:
            app_name: Name of the application

        Returns:
            Path object for the user configuration directory
        """
        # Check cache first
        cache_key = f"user_config_dir_{app_name}"
        if cache_key in self._path_cache:
            return self._path_cache[cache_key]

        if self.is_windows:
            # Windows: Use %APPDATA% (Roaming)
            base_dir = os.environ.get("APPDATA")
            if not base_dir:
                base_dir = os.path.expandvars("%USERPROFILE%\\AppData\\Roaming")
            config_dir = Path(base_dir) / app_name
        elif self.is_macos:
            # macOS: Use ~/Library/Preferences
            config_dir = Path(os.path.expanduser(f"~/Library/Preferences/{app_name}"))
        else:
            # Linux: Use ~/.config
            config_dir = Path(os.path.expanduser(f"~/.config/{app_name}"))

        # Cache the result
        self._path_cache[cache_key] = config_dir

        return config_dir

    def get_user_cache_dir(self, app_name: str = "PyProcessor") -> Path:
        """
        Get the user cache directory based on platform conventions.

        Args:
            app_name: Name of the application

        Returns:
            Path object for the user cache directory
        """
        # Check cache first
        cache_key = f"user_cache_dir_{app_name}"
        if cache_key in self._path_cache:
            return self._path_cache[cache_key]

        if self.is_windows:
            # Windows: Use %LOCALAPPDATA%\Cache
            base_dir = os.environ.get("LOCALAPPDATA")
            if not base_dir:
                base_dir = os.path.expandvars("%USERPROFILE%\\AppData\\Local")
            cache_dir = Path(base_dir) / app_name / "Cache"
        elif self.is_macos:
            # macOS: Use ~/Library/Caches
            cache_dir = Path(os.path.expanduser(f"~/Library/Caches/{app_name}"))
        else:
            # Linux: Use ~/.cache
            cache_dir = Path(os.path.expanduser(f"~/.cache/{app_name}"))

        # Cache the result
        self._path_cache[cache_key] = cache_dir

        return cache_dir

    def get_default_media_root(self) -> Path:
        """
        Get the default media root directory based on the platform.

        Returns:
            Path object for the default media root
        """
        # Check cache first
        if "default_media_root" in self._path_cache:
            return self._path_cache["default_media_root"]

        # Check for environment variable first (highest priority)
        if "MEDIA_ROOT" in os.environ:
            media_root = self.normalize_path(os.environ["MEDIA_ROOT"])
            self._path_cache["default_media_root"] = media_root
            return media_root

        # Get the user's home directory
        home_dir = self.get_user_home_dir()

        # Create a platform-specific media directory
        if self.is_windows:
            # On Windows, use Documents folder
            media_root = home_dir / "Documents" / "PyProcessor"
        else:
            # On Unix-like systems, use home directory
            media_root = home_dir / "PyProcessor"

        # Cache the result
        self._path_cache["default_media_root"] = media_root

        return media_root

    def get_app_data_dir(self) -> Path:
        """
        Get the application data directory based on the platform.

        Returns:
            Path object for the application data directory
        """
        # Check cache first
        if "app_data_dir" in self._path_cache:
            return self._path_cache["app_data_dir"]

        # Check for environment variable first (highest priority)
        if "PYPROCESSOR_DATA_DIR" in os.environ:
            app_data_dir = self.normalize_path(os.environ["PYPROCESSOR_DATA_DIR"])
            self._path_cache["app_data_dir"] = app_data_dir
            return app_data_dir

        # Fall back to user data directory
        app_data_dir = self.get_user_data_dir()

        # Cache the result
        self._path_cache["app_data_dir"] = app_data_dir

        return app_data_dir

    def get_profiles_dir(self) -> Path:
        """
        Get the profiles directory based on the platform.

        Returns:
            Path object for the profiles directory
        """
        # Check cache first
        if "profiles_dir" in self._path_cache:
            return self._path_cache["profiles_dir"]

        # Check for environment variable first (highest priority)
        if "PYPROCESSOR_PROFILES_DIR" in os.environ:
            profiles_dir = self.normalize_path(os.environ["PYPROCESSOR_PROFILES_DIR"])
            self._path_cache["profiles_dir"] = profiles_dir
            return profiles_dir

        # Fall back to user config directory
        profiles_dir = self.get_user_config_dir() / "profiles"

        # Cache the result
        self._path_cache["profiles_dir"] = profiles_dir

        return profiles_dir

    def get_logs_dir(self) -> Path:
        """
        Get the logs directory based on the platform.

        Returns:
            Path object for the logs directory
        """
        # Check cache first
        if "logs_dir" in self._path_cache:
            return self._path_cache["logs_dir"]

        # Check for environment variable first (highest priority)
        if "PYPROCESSOR_LOG_DIR" in os.environ:
            logs_dir = self.normalize_path(os.environ["PYPROCESSOR_LOG_DIR"])
            self._path_cache["logs_dir"] = logs_dir
            return logs_dir

        if self.is_windows:
            logs_dir = self.get_user_data_dir() / "logs"
        elif self.is_macos:
            logs_dir = Path(os.path.expanduser("~/Library/Logs/PyProcessor"))
        else:
            # Linux: Use /var/log if possible, otherwise use user's home
            if os.path.exists("/var/log") and os.access("/var/log", os.W_OK):
                logs_dir = Path("/var/log/pyprocessor")
            else:
                logs_dir = self.get_user_data_dir() / "logs"

        # Cache the result
        self._path_cache["logs_dir"] = logs_dir

        return logs_dir

    def find_executable(self, name: str) -> Optional[str]:
        """
        Find an executable in the system PATH.

        Args:
            name: Name of the executable without extension

        Returns:
            Path to the executable or None if not found
        """
        return shutil.which(name)

    def get_executable_extension(self) -> str:
        """
        Get the executable extension for the current platform.

        Returns:
            str: Executable extension (e.g., '.exe' on Windows, '' on Unix/Linux/macOS)
        """
        return self.exe_ext

    def join_path(self, *args) -> Path:
        """
        Join path components in a platform-agnostic way.

        Args:
            *args: Path components to join

        Returns:
            Path object for the joined path
        """
        return Path(os.path.join(*args))

    def get_file_extension(self, path: Union[str, Path]) -> str:
        """
        Get the file extension from a path.

        Args:
            path: Path to the file

        Returns:
            str: File extension (lowercase, including the dot)
        """
        path = self.normalize_path(path)
        return path.suffix.lower()

    def get_filename(self, path: Union[str, Path], with_extension: bool = True) -> str:
        """
        Get the filename from a path.

        Args:
            path: Path to the file
            with_extension: Whether to include the extension

        Returns:
            str: Filename
        """
        path = self.normalize_path(path)
        if with_extension:
            return path.name
        else:
            return path.stem

    def list_files(self, directory: Union[str, Path], pattern: str = "*", recursive: bool = False) -> List[Path]:
        """
        List files in a directory matching a pattern.

        Args:
            directory: Directory to search in
            pattern: Glob pattern to match (default: "*")
            recursive: Whether to search recursively (default: False)

        Returns:
            list: List of Path objects for matching files
        """
        directory = self.normalize_path(directory)
        if not directory.exists():
            return []

        if recursive:
            return list(directory.glob(f"**/{pattern}"))
        else:
            return list(directory.glob(pattern))

    def file_exists(self, path: Union[str, Path]) -> bool:
        """
        Check if a file exists.

        Args:
            path: Path to the file

        Returns:
            bool: True if the file exists, False otherwise
        """
        path = self.normalize_path(path)
        return path.exists() and path.is_file()

    def dir_exists(self, path: Union[str, Path]) -> bool:
        """
        Check if a directory exists.

        Args:
            path: Path to the directory

        Returns:
            bool: True if the directory exists, False otherwise
        """
        path = self.normalize_path(path)
        return path.exists() and path.is_dir()

    def copy_file(self, src: Union[str, Path], dst: Union[str, Path], overwrite: bool = True) -> Optional[Path]:
        """
        Copy a file from source to destination.

        Args:
            src: Source file path
            dst: Destination file path
            overwrite: Whether to overwrite existing files (default: True)

        Returns:
            Path object for the destination file or None if copy failed
        """
        src = self.normalize_path(src)
        dst = self.normalize_path(dst)

        # Check if source exists
        if not src.exists() or not src.is_file():
            self.logger.error(f"Source file does not exist: {src}")
            return None

        # Check if destination exists
        if dst.exists() and not overwrite:
            self.logger.warning(f"Destination file exists and overwrite is False: {dst}")
            return None

        # Ensure destination directory exists
        dst.parent.mkdir(parents=True, exist_ok=True)

        # Copy the file
        return Path(shutil.copy2(src, dst))

    def move_file(self, src: Union[str, Path], dst: Union[str, Path], overwrite: bool = True) -> Optional[Path]:
        """
        Move a file from source to destination.

        Args:
            src: Source file path
            dst: Destination file path
            overwrite: Whether to overwrite existing files (default: True)

        Returns:
            Path object for the destination file or None if move failed
        """
        src = self.normalize_path(src)
        dst = self.normalize_path(dst)

        # Check if source exists
        if not src.exists() or not src.is_file():
            self.logger.error(f"Source file does not exist: {src}")
            return None

        # Check if destination exists
        if dst.exists():
            if not overwrite:
                self.logger.warning(f"Destination file exists and overwrite is False: {dst}")
                return None
            else:
                # Remove destination file
                dst.unlink()

        # Ensure destination directory exists
        dst.parent.mkdir(parents=True, exist_ok=True)

        # Move the file
        shutil.move(str(src), str(dst))
        return dst

    def remove_file(self, path: Union[str, Path]) -> bool:
        """
        Remove a file.

        Args:
            path: Path to the file to remove

        Returns:
            bool: True if the file was removed, False otherwise
        """
        path = self.normalize_path(path)

        if not path.exists() or not path.is_file():
            return False

        try:
            path.unlink()
            return True
        except OSError:
            return False

    def remove_dir(self, path: Union[str, Path], recursive: bool = False) -> bool:
        """
        Remove a directory.

        Args:
            path: Path to the directory to remove
            recursive: Whether to remove recursively (default: False)

        Returns:
            bool: True if the directory was removed, False otherwise
        """
        path = self.normalize_path(path)

        if not path.exists() or not path.is_dir():
            return False

        try:
            if recursive:
                shutil.rmtree(path)
            else:
                path.rmdir()
            return True
        except OSError:
            return False

    def is_same_path(self, path1: Union[str, Path], path2: Union[str, Path]) -> bool:
        """
        Check if two paths refer to the same file or directory.

        Args:
            path1: First path
            path2: Second path

        Returns:
            bool: True if the paths refer to the same file or directory, False otherwise
        """
        path1 = self.normalize_path(path1)
        path2 = self.normalize_path(path2)

        try:
            # Resolve symlinks and get absolute paths
            path1 = path1.resolve()
            path2 = path2.resolve()

            # Compare the resolved paths
            return path1 == path2
        except Exception:
            return False

    def is_subpath(self, parent: Union[str, Path], child: Union[str, Path]) -> bool:
        """
        Check if a path is a subpath of another path.

        Args:
            parent: Parent path
            child: Child path

        Returns:
            bool: True if child is a subpath of parent, False otherwise
        """
        parent = self.normalize_path(parent)
        child = self.normalize_path(child)

        try:
            # Resolve symlinks and get absolute paths
            parent = parent.resolve()
            child = child.resolve()

            # Check if child is a subpath of parent
            return str(child).startswith(str(parent))
        except Exception:
            return False

    def is_valid_path(self, path: Union[str, Path]) -> bool:
        """
        Check if a path is valid and safe.

        Validates that a path:
        1. Can be normalized
        2. Doesn't contain invalid characters
        3. Isn't a potential path traversal attack

        Args:
            path: Path to check

        Returns:
            bool: True if the path is valid and safe, False otherwise
        """
        try:
            # Try to normalize the path
            path = self.normalize_path(path)
            path_str = str(path)

            # Check for null bytes (potential security issue)
            if '\0' in path_str:
                self.logger.warning(f"Path contains null bytes: {path}")
                return False

            # Check for suspicious path traversal patterns
            if self._contains_path_traversal(path_str):
                self.logger.warning(f"Path contains suspicious traversal patterns: {path}")
                return False

            # Additional platform-specific checks
            if self.is_windows:
                # Check for reserved Windows device names
                parts = path.parts
                if parts and parts[0].upper() in (
                    "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
                    "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2",
                    "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
                ):
                    self.logger.warning(f"Path contains reserved Windows device name: {path}")
                    return False

            return True
        except Exception as e:
            self.logger.debug(f"Invalid path: {path}, error: {str(e)}")
            return False

    def _contains_path_traversal(self, path_str: str) -> bool:
        """
        Check if a path contains suspicious path traversal patterns.

        Args:
            path_str: Path string to check

        Returns:
            bool: True if suspicious patterns are found, False otherwise
        """
        # Check for suspicious patterns that might indicate path traversal attacks
        suspicious_patterns = [
            "../", "..\\", "/..", "\\..",  # Parent directory traversal
            "/.\\.", "\\./."  # Current directory with obfuscation
        ]

        # Normalize path separators for consistent checking
        normalized = path_str.replace("\\", "/")

        # Check for suspicious patterns
        for pattern in suspicious_patterns:
            pattern = pattern.replace("\\", "/")
            if pattern in normalized:
                return True

        return False

    def is_safe_path(self, base_path: Union[str, Path], path: Union[str, Path]) -> bool:
        """
        Check if a path is safe (doesn't escape the base path).

        This is useful for preventing path traversal attacks when working with
        user-supplied paths that should be confined to a specific directory.

        Args:
            base_path: The base path that should contain the path
            path: The path to check

        Returns:
            bool: True if the path is safe, False otherwise
        """
        try:
            base_path = self.normalize_path(base_path).resolve()
            path = self.normalize_path(path)

            # First check if the path is valid
            if not self.is_valid_path(path):
                return False

            # Try to resolve the path (this will follow symlinks)
            # If it fails, the path might not exist yet
            try:
                resolved_path = path.resolve()
                # Check if the resolved path starts with the base path
                return str(resolved_path).startswith(str(base_path))
            except Exception:
                # If we can't resolve, use a different approach
                # Normalize both paths and check if the normalized path is within the base path
                normalized_path = os.path.normpath(str(path))
                normalized_base = os.path.normpath(str(base_path))

                # Check if the normalized path starts with the normalized base path
                # and that there's either an exact match or a directory separator after the base path
                return (normalized_path == normalized_base or
                        normalized_path.startswith(normalized_base + os.sep))

        except Exception as e:
            self.logger.error(f"Error checking if path is safe: {str(e)}")
            return False

    def is_absolute_path(self, path: Union[str, Path]) -> bool:
        """
        Check if a path is absolute.

        Args:
            path: Path to check

        Returns:
            bool: True if the path is absolute, False otherwise
        """
        try:
            # Try to normalize the path
            path = self.normalize_path(path)

            # Check if the path is absolute
            return path.is_absolute()
        except Exception:
            return False

    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a filename to remove invalid characters.

        Args:
            filename: Filename to sanitize

        Returns:
            str: Sanitized filename
        """
        if not filename:
            return ""

        # Replace invalid characters with underscores
        # This covers Windows, macOS, and Linux invalid characters
        invalid_chars = r'[<>:"/\\|?*\x00-\x1F]'
        sanitized = re.sub(invalid_chars, '_', filename)

        # Remove leading/trailing whitespace and periods
        # (Windows doesn't allow filenames ending with periods)
        sanitized = sanitized.strip('. ')

        # Ensure the filename isn't empty after sanitization
        if not sanitized:
            sanitized = "unnamed_file"

        # Ensure the filename isn't a reserved name on Windows
        if self.is_windows and sanitized.upper() in (
            "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
            "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2",
            "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
        ):
            sanitized = f"_{sanitized}"

        return sanitized

    def sanitize_path(self, path: Union[str, Path]) -> Path:
        """
        Sanitize a path to remove invalid characters and make it safe.

        Args:
            path: Path to sanitize

        Returns:
            Path: Sanitized path
        """
        try:
            path = self.normalize_path(path)
            parts = list(path.parts)

            # Sanitize each part of the path
            for i in range(len(parts)):
                if i == 0 and path.is_absolute():
                    # Don't sanitize the drive letter or root
                    continue
                parts[i] = self.sanitize_filename(parts[i])

            # Reconstruct the path
            if path.is_absolute():
                sanitized_path = Path(*parts)
            else:
                sanitized_path = Path(*parts)

            # Resolve the path to eliminate any remaining path traversal issues
            # Only if the path exists or we're creating a new path
            if sanitized_path.exists() or sanitized_path.parent.exists():
                try:
                    sanitized_path = sanitized_path.resolve()
                except Exception:
                    # If resolution fails, keep the sanitized path
                    pass

            return sanitized_path
        except Exception as e:
            self.logger.error(f"Error sanitizing path {path}: {str(e)}")
            # Return a safe default path if sanitization fails
            return Path(self.get_temp_dir() / "sanitized_path")

    def make_relative(self, path: Union[str, Path], base: Union[str, Path]) -> Path:
        """
        Make a path relative to a base path.

        Args:
            path: Path to make relative
            base: Base path

        Returns:
            Path object for the relative path
        """
        path = self.normalize_path(path)
        base = self.normalize_path(base)

        try:
            # Resolve symlinks and get absolute paths
            path = path.resolve()
            base = base.resolve()

            # Make the path relative to the base
            return path.relative_to(base)
        except ValueError:
            # If the path is not relative to the base, return the original path
            return path

    def make_absolute(self, path: Union[str, Path], base: Optional[Union[str, Path]] = None) -> Path:
        """
        Make a path absolute.

        Args:
            path: Path to make absolute
            base: Base path (default: current working directory)

        Returns:
            Path object for the absolute path
        """
        path = self.normalize_path(path)

        if path.is_absolute():
            return path

        if base is None:
            base = Path.cwd()
        else:
            base = self.normalize_path(base)

        return (base / path).resolve()

    def clear_cache(self):
        """
        Clear the path cache.
        """
        # Clear internal cache
        self._path_cache.clear()

        # Clear external cache
        for key in [
            "path_manager:base_dir",
            "path_manager:user_home_dir",
            "path_manager:user_data_dir_PyProcessor",
            "path_manager:user_config_dir_PyProcessor",
            "path_manager:user_cache_dir_PyProcessor",
            "path_manager:default_media_root",
            "path_manager:app_data_dir",
            "path_manager:profiles_dir",
            "path_manager:logs_dir"
        ]:
            cache_delete(key)

        self.logger.debug("Path cache cleared")

    def get_temp_dir(self, prefix: str = "pyprocessor_", parent_dir: Optional[Union[str, Path]] = None) -> Path:
        """
        Get a temporary directory.

        Args:
            prefix: Prefix for the temporary directory name
            parent_dir: Parent directory for the temporary directory (default: system temp directory)

        Returns:
            Path object for the temporary directory
        """
        if parent_dir is None:
            temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
        else:
            parent_dir = self.normalize_path(parent_dir)
            self.ensure_dir_exists(parent_dir)
            temp_dir = Path(tempfile.mkdtemp(prefix=prefix, dir=str(parent_dir)))

        self.logger.debug(f"Created temporary directory: {temp_dir}")
        return temp_dir

    def get_temp_file(self, suffix: str = "", prefix: str = "pyprocessor_", parent_dir: Optional[Union[str, Path]] = None) -> Path:
        """
        Get a temporary file.

        Args:
            suffix: Suffix for the temporary file name
            prefix: Prefix for the temporary file name
            parent_dir: Parent directory for the temporary file (default: system temp directory)

        Returns:
            Path object for the temporary file
        """
        if parent_dir is None:
            fd, temp_file = tempfile.mkstemp(suffix=suffix, prefix=prefix)
        else:
            parent_dir = self.normalize_path(parent_dir)
            self.ensure_dir_exists(parent_dir)
            fd, temp_file = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=str(parent_dir))

        os.close(fd)  # Close the file descriptor
        self.logger.debug(f"Created temporary file: {temp_file}")
        return Path(temp_file)

    @contextmanager
    def temp_dir_context(self, prefix: str = "pyprocessor_", parent_dir: Optional[Union[str, Path]] = None, cleanup: bool = True):
        """
        Context manager for a temporary directory.

        Args:
            prefix: Prefix for the temporary directory name
            parent_dir: Parent directory for the temporary directory (default: system temp directory)
            cleanup: Whether to clean up the directory when the context exits (default: True)

        Yields:
            Path object for the temporary directory
        """
        temp_dir = self.get_temp_dir(prefix, parent_dir)
        try:
            yield temp_dir
        finally:
            if cleanup:
                self.remove_dir(temp_dir, recursive=True)
                self.logger.debug(f"Removed temporary directory: {temp_dir}")

    @contextmanager
    def temp_file_context(self, suffix: str = "", prefix: str = "pyprocessor_", parent_dir: Optional[Union[str, Path]] = None, cleanup: bool = True):
        """
        Context manager for a temporary file.

        Args:
            suffix: Suffix for the temporary file name
            prefix: Prefix for the temporary file name
            parent_dir: Parent directory for the temporary file (default: system temp directory)
            cleanup: Whether to clean up the file when the context exits (default: True)

        Yields:
            Path object for the temporary file
        """
        temp_file = self.get_temp_file(suffix, prefix, parent_dir)
        try:
            yield temp_file
        finally:
            if cleanup:
                self.remove_file(temp_file)
                self.logger.debug(f"Removed temporary file: {temp_file}")


# Create a singleton instance
_path_manager = None


def get_path_manager(logger=None) -> PathManager:
    """
    Get the singleton path manager instance.

    Args:
        logger: Optional logger object

    Returns:
        PathManager: The singleton path manager instance
    """
    global _path_manager
    if _path_manager is None:
        _path_manager = PathManager(logger)
    return _path_manager


# Compatibility functions for backward compatibility
def expand_env_vars(path_str):
    """
    Expand environment variables in a path string.

    Args:
        path_str: Path string that may contain environment variables

    Returns:
        String with environment variables expanded
    """
    return get_path_manager().expand_env_vars(path_str)


def normalize_path(path_str):
    """
    Normalize a path string to use the correct path separators for the current platform.

    Args:
        path_str: Path string that may use forward or backward slashes

    Returns:
        Path object with correct separators for the current platform
    """
    return get_path_manager().normalize_path(path_str)


def ensure_dir_exists(path):
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Path to the directory

    Returns:
        Path object for the directory
    """
    return get_path_manager().ensure_dir_exists(path)


def get_base_dir():
    """
    Get the base directory for the application.

    Returns:
        Path object for the base directory
    """
    return get_path_manager().get_base_dir()


def get_user_data_dir(app_name="PyProcessor"):
    """
    Get the user data directory based on platform conventions.

    Args:
        app_name: Name of the application

    Returns:
        Path object for the user data directory
    """
    return get_path_manager().get_user_data_dir(app_name)


def get_user_config_dir(app_name="PyProcessor"):
    """
    Get the user configuration directory based on platform conventions.

    Args:
        app_name: Name of the application

    Returns:
        Path object for the user configuration directory
    """
    return get_path_manager().get_user_config_dir(app_name)


def get_user_cache_dir(app_name="PyProcessor"):
    """
    Get the user cache directory based on platform conventions.

    Args:
        app_name: Name of the application

    Returns:
        Path object for the user cache directory
    """
    return get_path_manager().get_user_cache_dir(app_name)


def get_default_media_root():
    """
    Get the default media root directory based on the platform.

    Returns:
        Path object for the default media root
    """
    return get_path_manager().get_default_media_root()


def get_app_data_dir():
    """
    Get the application data directory based on the platform.

    Returns:
        Path object for the application data directory
    """
    return get_path_manager().get_app_data_dir()


def get_profiles_dir():
    """
    Get the profiles directory based on the platform.

    Returns:
        Path object for the profiles directory
    """
    return get_path_manager().get_profiles_dir()


def get_logs_dir():
    """
    Get the logs directory based on the platform.

    Returns:
        Path object for the logs directory
    """
    return get_path_manager().get_logs_dir()


def find_executable(name):
    """
    Find an executable in the system PATH.

    Args:
        name: Name of the executable without extension

    Returns:
        Path to the executable or None if not found
    """
    return get_path_manager().find_executable(name)


def get_executable_extension():
    """
    Get the executable extension for the current platform.

    Returns:
        str: Executable extension (e.g., '.exe' on Windows, '' on Unix/Linux/macOS)
    """
    return get_path_manager().get_executable_extension()


def join_path(*args):
    """
    Join path components in a platform-agnostic way.

    Args:
        *args: Path components to join

    Returns:
        Path object for the joined path
    """
    return get_path_manager().join_path(*args)


def get_file_extension(path):
    """
    Get the file extension from a path.

    Args:
        path: Path to the file

    Returns:
        str: File extension (lowercase, including the dot)
    """
    return get_path_manager().get_file_extension(path)


def get_filename(path, with_extension=True):
    """
    Get the filename from a path.

    Args:
        path: Path to the file
        with_extension: Whether to include the extension

    Returns:
        str: Filename
    """
    return get_path_manager().get_filename(path, with_extension)


def list_files(directory, pattern="*", recursive=False):
    """
    List files in a directory matching a pattern.

    Args:
        directory: Directory to search in
        pattern: Glob pattern to match (default: "*")
        recursive: Whether to search recursively (default: False)

    Returns:
        list: List of Path objects for matching files
    """
    return get_path_manager().list_files(directory, pattern, recursive)


def file_exists(path):
    """
    Check if a file exists.

    Args:
        path: Path to the file

    Returns:
        bool: True if the file exists, False otherwise
    """
    return get_path_manager().file_exists(path)


def dir_exists(path):
    """
    Check if a directory exists.

    Args:
        path: Path to the directory

    Returns:
        bool: True if the directory exists, False otherwise
    """
    return get_path_manager().dir_exists(path)


def copy_file(src, dst, overwrite=True):
    """
    Copy a file from source to destination.

    Args:
        src: Source file path
        dst: Destination file path
        overwrite: Whether to overwrite existing files (default: True)

    Returns:
        Path object for the destination file or None if copy failed
    """
    return get_path_manager().copy_file(src, dst, overwrite)


def move_file(src, dst, overwrite=True):
    """
    Move a file from source to destination.

    Args:
        src: Source file path
        dst: Destination file path
        overwrite: Whether to overwrite existing files (default: True)

    Returns:
        Path object for the destination file or None if move failed
    """
    return get_path_manager().move_file(src, dst, overwrite)


def remove_file(path):
    """
    Remove a file.

    Args:
        path: Path to the file to remove

    Returns:
        bool: True if the file was removed, False otherwise
    """
    return get_path_manager().remove_file(path)


def remove_dir(path, recursive=False):
    """
    Remove a directory.

    Args:
        path: Path to the directory to remove
        recursive: Whether to remove recursively (default: False)

    Returns:
        bool: True if the directory was removed, False otherwise
    """
    return get_path_manager().remove_dir(path, recursive)


def get_temp_dir(prefix="pyprocessor_", parent_dir=None):
    """
    Get a temporary directory.

    Args:
        prefix: Prefix for the temporary directory name
        parent_dir: Parent directory for the temporary directory (default: system temp directory)

    Returns:
        Path object for the temporary directory
    """
    return get_path_manager().get_temp_dir(prefix, parent_dir)


def get_temp_file(suffix="", prefix="pyprocessor_", parent_dir=None):
    """
    Get a temporary file.

    Args:
        suffix: Suffix for the temporary file name
        prefix: Prefix for the temporary file name
        parent_dir: Parent directory for the temporary file (default: system temp directory)

    Returns:
        Path object for the temporary file
    """
    return get_path_manager().get_temp_file(suffix, prefix, parent_dir)


@contextmanager
def temp_dir_context(prefix="pyprocessor_", parent_dir=None, cleanup=True):
    """
    Context manager for a temporary directory.

    Args:
        prefix: Prefix for the temporary directory name
        parent_dir: Parent directory for the temporary directory (default: system temp directory)
        cleanup: Whether to clean up the directory when the context exits (default: True)

    Yields:
        Path object for the temporary directory
    """
    with get_path_manager().temp_dir_context(prefix, parent_dir, cleanup) as temp_dir:
        yield temp_dir


@contextmanager
def temp_file_context(suffix="", prefix="pyprocessor_", parent_dir=None, cleanup=True):
    """
    Context manager for a temporary file.

    Args:
        suffix: Suffix for the temporary file name
        prefix: Prefix for the temporary file name
        parent_dir: Parent directory for the temporary file (default: system temp directory)
        cleanup: Whether to clean up the file when the context exits (default: True)

    Yields:
        Path object for the temporary file
    """
    with get_path_manager().temp_file_context(suffix, prefix, parent_dir, cleanup) as temp_file:
        yield temp_file


def is_same_path(path1, path2):
    """
    Check if two paths refer to the same file or directory.

    Args:
        path1: First path
        path2: Second path

    Returns:
        bool: True if the paths refer to the same file or directory, False otherwise
    """
    return get_path_manager().is_same_path(path1, path2)


def is_subpath(parent, child):
    """
    Check if a path is a subpath of another path.

    Args:
        parent: Parent path
        child: Child path

    Returns:
        bool: True if child is a subpath of parent, False otherwise
    """
    return get_path_manager().is_subpath(parent, child)


def is_valid_path(path):
    """
    Check if a path is valid.

    Args:
        path: Path to check

    Returns:
        bool: True if the path is valid, False otherwise
    """
    return get_path_manager().is_valid_path(path)


def is_absolute_path(path):
    """
    Check if a path is absolute.

    Args:
        path: Path to check

    Returns:
        bool: True if the path is absolute, False otherwise
    """
    return get_path_manager().is_absolute_path(path)


def sanitize_filename(filename):
    """
    Sanitize a filename to remove invalid characters.

    Args:
        filename: Filename to sanitize

    Returns:
        str: Sanitized filename
    """
    return get_path_manager().sanitize_filename(filename)


def sanitize_path(path):
    """
    Sanitize a path to remove invalid characters and make it safe.

    Args:
        path: Path to sanitize

    Returns:
        Path: Sanitized path
    """
    return get_path_manager().sanitize_path(path)


def is_safe_path(base_path, path):
    """
    Check if a path is safe (doesn't escape the base path).

    Args:
        base_path: The base path that should contain the path
        path: The path to check

    Returns:
        bool: True if the path is safe, False otherwise
    """
    return get_path_manager().is_safe_path(base_path, path)


def make_relative(path, base):
    """
    Make a path relative to a base path.

    Args:
        path: Path to make relative
        base: Base path

    Returns:
        Path object for the relative path
    """
    return get_path_manager().make_relative(path, base)


def make_absolute(path, base=None):
    """
    Make a path absolute.

    Args:
        path: Path to make absolute
        base: Base path (default: current working directory)

    Returns:
        Path object for the absolute path
    """
    return get_path_manager().make_absolute(path, base)


def clear_path_cache():
    """
    Clear the path cache.
    """
    return get_path_manager().clear_cache()
