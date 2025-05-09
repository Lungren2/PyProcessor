"""
Plugin management utilities for PyProcessor.

This module provides a centralized way to manage plugins, including:
- Plugin discovery and loading
- Plugin registration and configuration
- Plugin execution and lifecycle management
- Plugin dependency resolution
"""

import importlib
import inspect
import pkgutil
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from pyprocessor.utils.logging.error_manager import (
    PyProcessorError,
    with_error_handling,
)
from pyprocessor.utils.logging.log_manager import get_logger


class PluginError(PyProcessorError):
    """Error related to plugin management."""


class Plugin:
    """
    Base class for all plugins.

    All plugins must inherit from this class and implement the required methods.
    """

    # Plugin metadata
    name = "base_plugin"
    version = "0.1.0"
    description = "Base plugin class"
    author = "PyProcessor Team"
    dependencies = []  # List of plugin names this plugin depends on

    def __init__(self):
        """Initialize the plugin."""
        self.logger = get_logger()
        self.initialized = False
        self.enabled = False

    def initialize(self) -> bool:
        """
        Initialize the plugin.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        self.initialized = True
        return True

    def shutdown(self) -> bool:
        """
        Shutdown the plugin.

        Returns:
            bool: True if shutdown was successful, False otherwise
        """
        self.initialized = False
        return True

    def enable(self) -> bool:
        """
        Enable the plugin.

        Returns:
            bool: True if enabling was successful, False otherwise
        """
        if not self.initialized:
            self.initialize()
        self.enabled = True
        return True

    def disable(self) -> bool:
        """
        Disable the plugin.

        Returns:
            bool: True if disabling was successful, False otherwise
        """
        self.enabled = False
        return True

    def is_enabled(self) -> bool:
        """
        Check if the plugin is enabled.

        Returns:
            bool: True if the plugin is enabled, False otherwise
        """
        return self.enabled

    def is_initialized(self) -> bool:
        """
        Check if the plugin is initialized.

        Returns:
            bool: True if the plugin is initialized, False otherwise
        """
        return self.initialized

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get plugin metadata.

        Returns:
            Dict[str, Any]: Plugin metadata
        """
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "dependencies": self.dependencies,
            "initialized": self.initialized,
            "enabled": self.enabled,
        }


class PluginManager:
    """
    Centralized manager for plugin-related operations.

    This class handles:
    - Plugin discovery and loading
    - Plugin registration and configuration
    - Plugin execution and lifecycle management
    - Plugin dependency resolution
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PluginManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, plugin_dirs: Optional[List[Union[str, Path]]] = None):
        """
        Initialize the plugin manager.

        Args:
            plugin_dirs: List of directories to search for plugins
        """
        # Only initialize once
        if self._initialized:
            return

        # Get logger
        self.logger = get_logger()

        # Initialize plugin tracking
        self._plugins = {}  # Dict of loaded plugins
        self._plugin_classes = {}  # Dict of plugin classes

        # Set plugin directories
        self._plugin_dirs = []
        if plugin_dirs:
            for plugin_dir in plugin_dirs:
                self._plugin_dirs.append(Path(plugin_dir))

        # Add default plugin directory
        default_plugin_dir = Path(__file__).parent.parent / "plugins"
        if default_plugin_dir not in self._plugin_dirs:
            self._plugin_dirs.append(default_plugin_dir)

        # Initialize locks
        self._plugin_lock = threading.Lock()

        # Mark as initialized
        self._initialized = True
        self.logger.debug("Plugin manager initialized")

    @with_error_handling
    def discover_plugins(self) -> List[Type[Plugin]]:
        """
        Discover available plugins in the plugin directories.

        Returns:
            List[Type[Plugin]]: List of discovered plugin classes
        """
        discovered_plugins = []

        # Ensure plugin directories exist
        for plugin_dir in self._plugin_dirs:
            if not plugin_dir.exists():
                plugin_dir.mkdir(parents=True, exist_ok=True)

        # Add plugin directories to sys.path
        for plugin_dir in self._plugin_dirs:
            if str(plugin_dir) not in sys.path:
                sys.path.append(str(plugin_dir))

        # Discover plugins in each directory
        for plugin_dir in self._plugin_dirs:
            self.logger.debug(f"Discovering plugins in {plugin_dir}")

            # Skip if directory doesn't exist
            if not plugin_dir.exists():
                continue

            # Iterate through all Python files in the directory
            for _, name, is_pkg in pkgutil.iter_modules([str(plugin_dir)]):
                try:
                    # Import the module
                    module = importlib.import_module(name)

                    # Find all Plugin subclasses in the module
                    for item_name, item in inspect.getmembers(module, inspect.isclass):
                        if issubclass(item, Plugin) and item is not Plugin:
                            self.logger.debug(
                                f"Discovered plugin: {item.name} ({item.__module__}.{item.__name__})"
                            )
                            discovered_plugins.append(item)

                            # Register the plugin class
                            self._plugin_classes[item.name] = item
                except Exception as e:
                    self.logger.error(f"Error discovering plugin {name}: {str(e)}")

        return discovered_plugins

    @with_error_handling
    def load_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """
        Load a plugin by name.

        Args:
            plugin_name: Name of the plugin to load

        Returns:
            Optional[Plugin]: Loaded plugin instance or None if not found
        """
        with self._plugin_lock:
            # Check if plugin is already loaded
            if plugin_name in self._plugins:
                return self._plugins[plugin_name]

            # Check if plugin class is available
            if plugin_name not in self._plugin_classes:
                # Try to discover plugins
                self.discover_plugins()

                # Check again
                if plugin_name not in self._plugin_classes:
                    self.logger.error(f"Plugin not found: {plugin_name}")
                    return None

            # Get the plugin class
            plugin_class = self._plugin_classes[plugin_name]

            # Load dependencies first
            for dependency in plugin_class.dependencies:
                if dependency not in self._plugins:
                    dependency_plugin = self.load_plugin(dependency)
                    if dependency_plugin is None:
                        self.logger.error(
                            f"Failed to load dependency {dependency} for plugin {plugin_name}"
                        )
                        return None

            # Create plugin instance
            try:
                plugin = plugin_class()

                # Initialize the plugin
                if not plugin.initialize():
                    self.logger.error(f"Failed to initialize plugin {plugin_name}")
                    return None

                # Store the plugin
                self._plugins[plugin_name] = plugin

                self.logger.debug(f"Loaded plugin: {plugin_name}")
                return plugin
            except Exception as e:
                self.logger.error(f"Error loading plugin {plugin_name}: {str(e)}")
                return None

    @with_error_handling
    def load_all_plugins(self) -> Dict[str, Plugin]:
        """
        Load all available plugins.

        Returns:
            Dict[str, Plugin]: Dictionary of loaded plugins
        """
        # Discover plugins
        self.discover_plugins()

        # Load each plugin
        for plugin_name in self._plugin_classes:
            self.load_plugin(plugin_name)

        return self._plugins

    @with_error_handling
    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """
        Get a loaded plugin by name.

        Args:
            plugin_name: Name of the plugin to get

        Returns:
            Optional[Plugin]: Plugin instance or None if not found
        """
        with self._plugin_lock:
            # Check if plugin is loaded
            if plugin_name in self._plugins:
                return self._plugins[plugin_name]

            # Try to load the plugin
            return self.load_plugin(plugin_name)

    @with_error_handling
    def enable_plugin(self, plugin_name: str) -> bool:
        """
        Enable a plugin.

        Args:
            plugin_name: Name of the plugin to enable

        Returns:
            bool: True if the plugin was enabled, False otherwise
        """
        # Get the plugin
        plugin = self.get_plugin(plugin_name)
        if plugin is None:
            return False

        # Enable the plugin
        return plugin.enable()

    @with_error_handling
    def disable_plugin(self, plugin_name: str) -> bool:
        """
        Disable a plugin.

        Args:
            plugin_name: Name of the plugin to disable

        Returns:
            bool: True if the plugin was disabled, False otherwise
        """
        # Get the plugin
        plugin = self.get_plugin(plugin_name)
        if plugin is None:
            return False

        # Disable the plugin
        return plugin.disable()

    @with_error_handling
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin.

        Args:
            plugin_name: Name of the plugin to unload

        Returns:
            bool: True if the plugin was unloaded, False otherwise
        """
        with self._plugin_lock:
            # Check if plugin is loaded
            if plugin_name not in self._plugins:
                return False

            # Get the plugin
            plugin = self._plugins[plugin_name]

            # Shutdown the plugin
            if not plugin.shutdown():
                self.logger.error(f"Failed to shutdown plugin {plugin_name}")
                return False

            # Remove the plugin
            del self._plugins[plugin_name]

            self.logger.debug(f"Unloaded plugin: {plugin_name}")
            return True

    @with_error_handling
    def unload_all_plugins(self) -> bool:
        """
        Unload all plugins.

        Returns:
            bool: True if all plugins were unloaded, False otherwise
        """
        success = True

        # Get a copy of the plugin names
        plugin_names = list(self._plugins.keys())

        # Unload each plugin
        for plugin_name in plugin_names:
            if not self.unload_plugin(plugin_name):
                success = False

        return success

    @with_error_handling
    def get_loaded_plugins(self) -> Dict[str, Plugin]:
        """
        Get all loaded plugins.

        Returns:
            Dict[str, Plugin]: Dictionary of loaded plugins
        """
        return self._plugins.copy()

    @with_error_handling
    def get_available_plugins(self) -> List[str]:
        """
        Get names of all available plugins.

        Returns:
            List[str]: List of plugin names
        """
        # Discover plugins
        self.discover_plugins()

        return list(self._plugin_classes.keys())

    @with_error_handling
    def get_plugin_metadata(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Optional[Dict[str, Any]]: Plugin metadata or None if not found
        """
        # Get the plugin
        plugin = self.get_plugin(plugin_name)
        if plugin is None:
            return None

        # Get metadata
        return plugin.get_metadata()

    @with_error_handling
    def get_all_plugin_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        Get metadata for all available plugins.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of plugin metadata
        """
        # Discover plugins
        self.discover_plugins()

        result = {}

        # Get metadata for each plugin class
        for plugin_name, plugin_class in self._plugin_classes.items():
            # Check if plugin is loaded
            if plugin_name in self._plugins:
                # Get metadata from loaded plugin
                result[plugin_name] = self._plugins[plugin_name].get_metadata()
            else:
                # Get metadata from plugin class
                result[plugin_name] = {
                    "name": plugin_class.name,
                    "version": plugin_class.version,
                    "description": plugin_class.description,
                    "author": plugin_class.author,
                    "dependencies": plugin_class.dependencies,
                    "initialized": False,
                    "enabled": False,
                }

        return result


# Singleton instance
_plugin_manager = None


def get_plugin_manager(
    plugin_dirs: Optional[List[Union[str, Path]]] = None,
) -> PluginManager:
    """
    Get the singleton plugin manager instance.

    Args:
        plugin_dirs: List of directories to search for plugins

    Returns:
        PluginManager: The singleton plugin manager instance
    """
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager(plugin_dirs)
    return _plugin_manager


# Module-level functions for convenience


def discover_plugins() -> List[Type[Plugin]]:
    """
    Discover available plugins.

    Returns:
        List[Type[Plugin]]: List of discovered plugin classes
    """
    return get_plugin_manager().discover_plugins()


def load_plugin(plugin_name: str) -> Optional[Plugin]:
    """
    Load a plugin by name.

    Args:
        plugin_name: Name of the plugin to load

    Returns:
        Optional[Plugin]: Loaded plugin instance or None if not found
    """
    return get_plugin_manager().load_plugin(plugin_name)


def load_all_plugins() -> Dict[str, Plugin]:
    """
    Load all available plugins.

    Returns:
        Dict[str, Plugin]: Dictionary of loaded plugins
    """
    return get_plugin_manager().load_all_plugins()


def get_plugin(plugin_name: str) -> Optional[Plugin]:
    """
    Get a loaded plugin by name.

    Args:
        plugin_name: Name of the plugin to get

    Returns:
        Optional[Plugin]: Plugin instance or None if not found
    """
    return get_plugin_manager().get_plugin(plugin_name)


def enable_plugin(plugin_name: str) -> bool:
    """
    Enable a plugin.

    Args:
        plugin_name: Name of the plugin to enable

    Returns:
        bool: True if the plugin was enabled, False otherwise
    """
    return get_plugin_manager().enable_plugin(plugin_name)


def disable_plugin(plugin_name: str) -> bool:
    """
    Disable a plugin.

    Args:
        plugin_name: Name of the plugin to disable

    Returns:
        bool: True if the plugin was disabled, False otherwise
    """
    return get_plugin_manager().disable_plugin(plugin_name)


def unload_plugin(plugin_name: str) -> bool:
    """
    Unload a plugin.

    Args:
        plugin_name: Name of the plugin to unload

    Returns:
        bool: True if the plugin was unloaded, False otherwise
    """
    return get_plugin_manager().unload_plugin(plugin_name)


def unload_all_plugins() -> bool:
    """
    Unload all plugins.

    Returns:
        bool: True if all plugins were unloaded, False otherwise
    """
    return get_plugin_manager().unload_all_plugins()


def get_loaded_plugins() -> Dict[str, Plugin]:
    """
    Get all loaded plugins.

    Returns:
        Dict[str, Plugin]: Dictionary of loaded plugins
    """
    return get_plugin_manager().get_loaded_plugins()


def get_available_plugins() -> List[str]:
    """
    Get names of all available plugins.

    Returns:
        List[str]: List of plugin names
    """
    return get_plugin_manager().get_available_plugins()


def get_plugin_metadata(plugin_name: str) -> Optional[Dict[str, Any]]:
    """
    Get metadata for a plugin.

    Args:
        plugin_name: Name of the plugin

    Returns:
        Optional[Dict[str, Any]]: Plugin metadata or None if not found
    """
    return get_plugin_manager().get_plugin_metadata(plugin_name)


def get_all_plugin_metadata() -> Dict[str, Dict[str, Any]]:
    """
    Get metadata for all available plugins.

    Returns:
        Dict[str, Dict[str, Any]]: Dictionary of plugin metadata
    """
    return get_plugin_manager().get_all_plugin_metadata()
