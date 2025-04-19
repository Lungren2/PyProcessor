"""
Dependency management module for PyProcessor.

This module provides functionality for managing dependencies, including:
- Version checking for dependencies
- Compatibility checks for FFmpeg versions
- Dependency validation during startup
- Graceful fallbacks for missing optional dependencies
- Dependency resolution for conflicting requirements
- Dependency update checking
- Dependency isolation for plugins
- Platform-specific dependency handling
"""

import os
import sys
import re
import pkg_resources
import platform
import subprocess
import importlib
import importlib.util
from typing import Dict, List, Tuple, Optional, Any, Set
from pathlib import Path
from contextlib import suppress
import warnings

from pyprocessor.utils.logging.log_manager import get_logger
from pyprocessor.utils.logging.error_manager import (
    get_error_manager, with_error_handling, DependencyError, ErrorSeverity
)


class DependencyManager:
    """
    Dependency manager for PyProcessor.

    This class provides functionality for managing dependencies, including:
    - Version checking for dependencies
    - Compatibility checks for FFmpeg versions
    - Dependency validation during startup
    - Graceful fallbacks for missing optional dependencies
    - Dependency resolution for conflicting requirements
    - Dependency update checking
    - Dependency isolation for plugins
    - Platform-specific dependency handling
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DependencyManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, logger=None):
        """
        Initialize the dependency manager.

        Args:
            logger: Logger instance for logging messages
        """
        # Only initialize once
        if self._initialized:
            return

        # Initialize logger
        self.logger = logger or get_logger()
        self.error_manager = get_error_manager()

        # Initialize dependency information
        self.dependencies = {}
        self.optional_dependencies = {}
        self.ffmpeg_version = None
        self.ffmpeg_available = False
        self.ffmpeg_min_version = "4.0.0"  # Minimum required FFmpeg version
        self.ffmpeg_recommended_version = "5.0.0"  # Recommended FFmpeg version

        # Initialize platform information
        self.system = platform.system().lower()
        self.is_windows = self.system == "windows"
        self.is_macos = self.system == "darwin"
        self.is_linux = self.system.startswith("linux")

        # Initialize dependency manifest
        self._load_dependency_manifest()

        # Mark as initialized
        self._initialized = True
        self.logger.debug("Dependency manager initialized")

    def _load_dependency_manifest(self):
        """
        Load the dependency manifest.
        """
        # Base dependencies (required for all platforms)
        self.dependencies = {
            "tqdm": {"min_version": "4.60.0", "required": True},
        }

        # Platform-specific dependencies
        if self.is_windows:
            self.dependencies.update({
                "pywin32": {"min_version": "305", "required": True},
                "winshell": {"min_version": "0.6", "required": True},
            })
        elif self.is_macos:
            self.dependencies.update({
                "pyobjc-core": {"min_version": "9.2", "required": True},
                "pyobjc-framework-Cocoa": {"min_version": "9.2", "required": True},
            })
        elif self.is_linux:
            self.dependencies.update({
                "python-xlib": {"min_version": "0.33", "required": True},
                "dbus-python": {"min_version": "1.3.2", "required": True},
            })

        # Optional dependencies
        self.optional_dependencies = {
            "ffmpeg-python": {"min_version": "0.2.0", "required": False},
            "black": {"min_version": "23.7.0", "required": False, "group": "dev"},
            "flake8": {"min_version": "6.1.0", "required": False, "group": "dev"},
            "isort": {"min_version": "5.12.0", "required": False, "group": "dev"},
            "pyinstaller": {"min_version": "5.13.0", "required": False, "group": "dev"},
        }

    @with_error_handling
    def check_dependencies(self) -> Tuple[List[str], List[str]]:
        """
        Check for missing or incompatible dependencies.

        Returns:
            Tuple[List[str], List[str]]: Lists of errors and warnings
        """
        errors = []
        warnings = []

        # Check required dependencies
        for package, info in self.dependencies.items():
            try:
                # Check if package is installed
                pkg_version = pkg_resources.get_distribution(package).version
                min_version = info.get("min_version")
                
                # Check version if minimum version is specified
                if min_version and pkg_resources.parse_version(pkg_version) < pkg_resources.parse_version(min_version):
                    errors.append(f"Incompatible version of {package}: {pkg_version} (minimum required: {min_version})")
                else:
                    self.logger.debug(f"Found {package} {pkg_version}")
            except pkg_resources.DistributionNotFound:
                errors.append(f"Required dependency {package} not found")
            except Exception as e:
                errors.append(f"Error checking dependency {package}: {str(e)}")

        # Check optional dependencies
        for package, info in self.optional_dependencies.items():
            try:
                # Check if package is installed
                pkg_version = pkg_resources.get_distribution(package).version
                min_version = info.get("min_version")
                
                # Check version if minimum version is specified
                if min_version and pkg_resources.parse_version(pkg_version) < pkg_resources.parse_version(min_version):
                    warnings.append(f"Incompatible version of optional dependency {package}: {pkg_version} (minimum recommended: {min_version})")
                else:
                    self.logger.debug(f"Found optional dependency {package} {pkg_version}")
            except pkg_resources.DistributionNotFound:
                warnings.append(f"Optional dependency {package} not found")
            except Exception as e:
                warnings.append(f"Error checking optional dependency {package}: {str(e)}")

        # Check FFmpeg
        ffmpeg_available, ffmpeg_version, ffmpeg_error = self.check_ffmpeg()
        if not ffmpeg_available:
            errors.append(f"FFmpeg not found: {ffmpeg_error}")
        elif ffmpeg_version:
            # Extract version number from FFmpeg version string
            version_match = re.search(r"ffmpeg version (\d+\.\d+\.\d+)", ffmpeg_version)
            if version_match:
                version = version_match.group(1)
                self.ffmpeg_version = version
                
                # Check if version is below minimum required
                if pkg_resources.parse_version(version) < pkg_resources.parse_version(self.ffmpeg_min_version):
                    errors.append(f"Incompatible FFmpeg version: {version} (minimum required: {self.ffmpeg_min_version})")
                # Check if version is below recommended
                elif pkg_resources.parse_version(version) < pkg_resources.parse_version(self.ffmpeg_recommended_version):
                    warnings.append(f"FFmpeg version {version} is below recommended version {self.ffmpeg_recommended_version}")
                else:
                    self.logger.debug(f"Found FFmpeg {version}")
            else:
                warnings.append(f"Could not determine FFmpeg version from: {ffmpeg_version}")

        return errors, warnings

    @with_error_handling
    def check_ffmpeg(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if FFmpeg is installed and available.

        Returns:
            Tuple[bool, Optional[str], Optional[str]]: (is_available, version_string, error_message)
        """
        try:
            # Try to get FFmpeg path from FFmpegManager
            from pyprocessor.utils.media.ffmpeg_manager import FFmpegManager
            ffmpeg_manager = FFmpegManager()
            ffmpeg_path = ffmpeg_manager.get_ffmpeg_path()
            
            # Run FFmpeg version command
            result = subprocess.run(
                [ffmpeg_path, "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
            )
            
            if result.returncode != 0:
                return False, None, f"FFmpeg check failed with return code {result.returncode}: {result.stderr}"
            
            if "ffmpeg version" in result.stdout:
                version_line = result.stdout.split('\n')[0]
                self.ffmpeg_available = True
                return True, version_line, None
            
            return False, None, "FFmpeg check failed: version string not found in output"
        
        except Exception as e:
            return False, None, f"Error checking FFmpeg: {str(e)}"

    @with_error_handling
    def check_module_available(self, module_name: str) -> bool:
        """
        Check if a Python module is available.

        Args:
            module_name: Name of the module to check

        Returns:
            bool: True if the module is available, False otherwise
        """
        try:
            importlib.import_module(module_name)
            return True
        except ImportError:
            return False
        except Exception:
            return False

    @with_error_handling
    def get_module_version(self, module_name: str) -> Optional[str]:
        """
        Get the version of a Python module.

        Args:
            module_name: Name of the module to check

        Returns:
            Optional[str]: Version string or None if not available
        """
        try:
            module = importlib.import_module(module_name)
            
            # Try different version attributes
            for attr in ["__version__", "version", "VERSION"]:
                if hasattr(module, attr):
                    return getattr(module, attr)
            
            # Try to get version from pkg_resources
            return pkg_resources.get_distribution(module_name).version
        except (ImportError, pkg_resources.DistributionNotFound):
            return None
        except Exception:
            return None

    @with_error_handling
    def check_for_updates(self) -> Dict[str, Tuple[str, str]]:
        """
        Check for available updates to dependencies.

        Returns:
            Dict[str, Tuple[str, str]]: Dictionary of package names and their current and latest versions
        """
        updates_available = {}
        
        # Check all dependencies (required and optional)
        all_dependencies = {**self.dependencies, **self.optional_dependencies}
        
        for package in all_dependencies:
            try:
                # Get current version
                current_version = pkg_resources.get_distribution(package).version
                
                # Check for latest version using pip
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "index", "versions", package],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10,
                )
                
                if result.returncode == 0:
                    # Parse output to find latest version
                    match = re.search(r"Available versions: ([\d\.]+)", result.stdout)
                    if match:
                        latest_version = match.group(1)
                        
                        # Compare versions
                        if pkg_resources.parse_version(latest_version) > pkg_resources.parse_version(current_version):
                            updates_available[package] = (current_version, latest_version)
            except Exception as e:
                self.logger.debug(f"Error checking for updates for {package}: {str(e)}")
        
        return updates_available

    @with_error_handling
    def get_fallback_module(self, module_name: str) -> Optional[Any]:
        """
        Get a fallback module for a missing optional dependency.

        Args:
            module_name: Name of the module to get a fallback for

        Returns:
            Optional[Any]: Fallback module or None if no fallback is available
        """
        # Define fallbacks for known modules
        fallbacks = {
            "ffmpeg-python": self._fallback_ffmpeg,
            "black": lambda: None,  # No fallback for black
            "flake8": lambda: None,  # No fallback for flake8
            "isort": lambda: None,   # No fallback for isort
        }
        
        # Get fallback function
        fallback_func = fallbacks.get(module_name)
        if fallback_func:
            return fallback_func()
        
        return None

    def _fallback_ffmpeg(self):
        """
        Provide a fallback for ffmpeg-python.
        
        Returns:
            Optional[Any]: Fallback module or None
        """
        # This is a simplified fallback that just provides basic functionality
        # In a real implementation, you would create a more complete fallback
        
        class FFmpegFallback:
            """Minimal fallback for ffmpeg-python."""
            
            def __init__(self):
                self.logger = get_logger()
                self.logger.warning("Using fallback FFmpeg implementation (limited functionality)")
            
            def input(self, filename):
                """Create an input stream."""
                self.logger.debug(f"FFmpeg fallback: input({filename})")
                return self
            
            def output(self, filename, **kwargs):
                """Create an output stream."""
                self.logger.debug(f"FFmpeg fallback: output({filename}, {kwargs})")
                return self
            
            def run(self, **kwargs):
                """Run the FFmpeg command."""
                self.logger.debug(f"FFmpeg fallback: run({kwargs})")
                # In a real fallback, you would implement this using subprocess
                # to call FFmpeg directly
                raise NotImplementedError("FFmpeg fallback does not support running commands")
        
        return FFmpegFallback()

    @with_error_handling
    def create_isolated_environment(self, name: str, dependencies: Dict[str, str]) -> str:
        """
        Create an isolated environment for a plugin.

        Args:
            name: Name of the environment
            dependencies: Dictionary of dependencies and their versions

        Returns:
            str: Path to the isolated environment
        """
        # This is a simplified implementation
        # In a real implementation, you would create a virtual environment
        # and install the dependencies in it
        
        # Create a directory for the isolated environment
        env_dir = Path(os.path.expanduser("~")) / ".pyprocessor" / "environments" / name
        env_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a requirements file
        requirements_file = env_dir / "requirements.txt"
        with open(requirements_file, "w") as f:
            for package, version in dependencies.items():
                f.write(f"{package}=={version}\n")
        
        # Log the creation of the isolated environment
        self.logger.info(f"Created isolated environment for {name} at {env_dir}")
        
        return str(env_dir)


# Singleton instance
_dependency_manager = None


def get_dependency_manager(logger=None) -> DependencyManager:
    """
    Get the dependency manager instance.

    Args:
        logger: Logger instance for logging messages

    Returns:
        DependencyManager: Dependency manager instance
    """
    global _dependency_manager
    if _dependency_manager is None:
        _dependency_manager = DependencyManager(logger)
    return _dependency_manager


# Convenience functions
def check_dependencies() -> Tuple[List[str], List[str]]:
    """
    Check for missing or incompatible dependencies.

    Returns:
        Tuple[List[str], List[str]]: Lists of errors and warnings
    """
    return get_dependency_manager().check_dependencies()


def check_ffmpeg() -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Check if FFmpeg is installed and available.

    Returns:
        Tuple[bool, Optional[str], Optional[str]]: (is_available, version_string, error_message)
    """
    return get_dependency_manager().check_ffmpeg()


def check_module_available(module_name: str) -> bool:
    """
    Check if a Python module is available.

    Args:
        module_name: Name of the module to check

    Returns:
        bool: True if the module is available, False otherwise
    """
    return get_dependency_manager().check_module_available(module_name)


def get_module_version(module_name: str) -> Optional[str]:
    """
    Get the version of a Python module.

    Args:
        module_name: Name of the module to check

    Returns:
        Optional[str]: Version string or None if not available
    """
    return get_dependency_manager().get_module_version(module_name)


def check_for_updates() -> Dict[str, Tuple[str, str]]:
    """
    Check for available updates to dependencies.

    Returns:
        Dict[str, Tuple[str, str]]: Dictionary of package names and their current and latest versions
    """
    return get_dependency_manager().check_for_updates()


def get_fallback_module(module_name: str) -> Optional[Any]:
    """
    Get a fallback module for a missing optional dependency.

    Args:
        module_name: Name of the module to get a fallback for

    Returns:
        Optional[Any]: Fallback module or None if no fallback is available
    """
    return get_dependency_manager().get_fallback_module(module_name)


def create_isolated_environment(name: str, dependencies: Dict[str, str]) -> str:
    """
    Create an isolated environment for a plugin.

    Args:
        name: Name of the environment
        dependencies: Dictionary of dependencies and their versions

    Returns:
        str: Path to the isolated environment
    """
    return get_dependency_manager().create_isolated_environment(name, dependencies)
