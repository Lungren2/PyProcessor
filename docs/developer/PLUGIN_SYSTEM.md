# Plugin System in PyProcessor

This document describes the plugin system in PyProcessor, including the plugin architecture, plugin interfaces, and how to create and use plugins.

## Overview

PyProcessor provides a flexible plugin system that allows extending the application with custom functionality. The plugin system is designed to be:

- **Modular**: Plugins can be added and removed without affecting the core application
- **Extensible**: New plugin types can be added as needed
- **Discoverable**: Plugins are automatically discovered and loaded
- **Configurable**: Plugins can be configured through the application
- **Dependency-aware**: Plugins can depend on other plugins

## Plugin Architecture

The plugin system consists of the following components:

- **Plugin Manager**: Manages plugin discovery, loading, and lifecycle
- **Plugin Base Class**: Base class for all plugins
- **Plugin Interfaces**: Interfaces for different types of plugins
- **Built-in Plugins**: Plugins that come with PyProcessor
- **Custom Plugins**: Plugins created by users

### Plugin Manager

The `PluginManager` class in `pyprocessor.utils.plugin_manager` is responsible for:

- Discovering available plugins
- Loading and unloading plugins
- Managing plugin lifecycle (initialization, enabling, disabling)
- Resolving plugin dependencies

```python
from pyprocessor.utils.plugin_manager import get_plugin_manager

# Get the plugin manager
plugin_manager = get_plugin_manager()

# Discover available plugins
plugin_manager.discover_plugins()

# Load a plugin
plugin = plugin_manager.load_plugin("ffmpeg_encoder")

# Enable a plugin
plugin_manager.enable_plugin("ffmpeg_encoder")

# Get a loaded plugin
plugin = plugin_manager.get_plugin("ffmpeg_encoder")

# Unload a plugin
plugin_manager.unload_plugin("ffmpeg_encoder")
```

### Plugin Base Class

The `Plugin` class in `pyprocessor.utils.plugin_manager` is the base class for all plugins. It provides:

- Plugin metadata (name, version, description, author)
- Plugin lifecycle methods (initialize, shutdown, enable, disable)
- Plugin dependency management

```python
from pyprocessor.utils.plugin_manager import Plugin

class MyPlugin(Plugin):
    name = "my_plugin"
    version = "0.1.0"
    description = "My custom plugin"
    author = "My Name"
    dependencies = ["other_plugin"]
    
    def initialize(self):
        # Initialize the plugin
        return super().initialize()
    
    def shutdown(self):
        # Shutdown the plugin
        return super().shutdown()
    
    def enable(self):
        # Enable the plugin
        return super().enable()
    
    def disable(self):
        # Disable the plugin
        return super().disable()
```

### Plugin Interfaces

PyProcessor provides several plugin interfaces for different types of functionality:

- **EncoderPlugin**: Provides encoding functionality
- **ProcessorPlugin**: Provides processing functionality
- **FilterPlugin**: Provides filtering functionality
- **AnalyzerPlugin**: Provides analysis functionality
- **OutputPlugin**: Provides output functionality

These interfaces define the methods that plugins of each type must implement.

```python
from pyprocessor.plugins.interfaces import EncoderPlugin

class MyEncoderPlugin(EncoderPlugin):
    name = "my_encoder"
    version = "0.1.0"
    description = "My custom encoder plugin"
    author = "My Name"
    
    def encode(self, input_file, output_file, options=None):
        # Encode the file
        return True
    
    def get_supported_formats(self):
        return ["mp4", "mkv"]
    
    def get_supported_codecs(self):
        return {
            "video": ["libx264", "libx265"],
            "audio": ["aac", "mp3"],
        }
    
    def get_default_options(self):
        return {
            "video_codec": "libx264",
            "audio_codec": "aac",
        }
```

## Creating Plugins

To create a custom plugin, follow these steps:

1. Choose the appropriate plugin interface for your functionality
2. Create a new class that inherits from the chosen interface
3. Implement the required methods
4. Add your plugin to a directory in the plugin search path

### Example: Creating an Encoder Plugin

```python
from pyprocessor.plugins.interfaces import EncoderPlugin

class MyEncoderPlugin(EncoderPlugin):
    name = "my_encoder"
    version = "0.1.0"
    description = "My custom encoder plugin"
    author = "My Name"
    
    def encode(self, input_file, output_file, options=None):
        # Encode the file using your custom logic
        return True
    
    def get_supported_formats(self):
        return ["mp4", "mkv"]
    
    def get_supported_codecs(self):
        return {
            "video": ["libx264", "libx265"],
            "audio": ["aac", "mp3"],
        }
    
    def get_default_options(self):
        return {
            "video_codec": "libx264",
            "audio_codec": "aac",
        }
```

### Plugin Directory Structure

Plugins can be placed in the following directories:

- `pyprocessor/plugins`: Built-in plugins
- `~/.pyprocessor/plugins`: User plugins
- Custom directories specified when creating the plugin manager

Each plugin should be in its own Python module (file) or package (directory with `__init__.py`).

## Using Plugins

To use plugins in your code, follow these steps:

1. Get the plugin manager
2. Load the plugin
3. Enable the plugin
4. Use the plugin

```python
from pyprocessor.utils.plugin_manager import get_plugin_manager

# Get the plugin manager
plugin_manager = get_plugin_manager()

# Load the plugin
plugin = plugin_manager.load_plugin("ffmpeg_encoder")

# Enable the plugin
plugin_manager.enable_plugin("ffmpeg_encoder")

# Use the plugin
plugin.encode("input.mp4", "output.mp4", {
    "video_codec": "libx265",
    "audio_codec": "aac",
})
```

## Plugin Configuration

Plugins can be configured through the application configuration system:

```python
from pyprocessor.utils.config_manager import get_config_manager

# Get the configuration manager
config_manager = get_config_manager()

# Configure a plugin
config_manager.set("plugins.ffmpeg_encoder.video_codec", "libx265")
config_manager.set("plugins.ffmpeg_encoder.audio_codec", "aac")

# Save the configuration
config_manager.save()
```

## Plugin Events

Plugins can emit and listen for events using the event system:

```python
from pyprocessor.utils.event_manager import get_event_manager

# Get the event manager
event_manager = get_event_manager()

# Listen for an event
event_manager.subscribe("encoding_started", my_callback)

# Emit an event
event_manager.emit("encoding_started", {"file": "input.mp4"})
```

## Best Practices

1. **Use the appropriate interface**: Choose the plugin interface that best matches your functionality
2. **Implement all required methods**: Make sure to implement all methods required by the interface
3. **Handle errors gracefully**: Catch and log exceptions, and return appropriate error codes
4. **Document your plugin**: Include clear documentation for your plugin
5. **Test your plugin**: Write tests for your plugin to ensure it works correctly
6. **Respect dependencies**: If your plugin depends on other plugins, list them in the `dependencies` attribute
7. **Clean up resources**: Make sure to clean up resources in the `shutdown` method
8. **Use the logger**: Use the logger provided by the plugin base class for logging
9. **Follow naming conventions**: Use descriptive names for your plugins and methods
10. **Version your plugins**: Use semantic versioning for your plugins

## Troubleshooting

If you encounter issues with plugins, try the following:

1. **Check the logs**: Look for error messages in the application logs
2. **Verify dependencies**: Make sure all dependencies are installed and loaded
3. **Check plugin paths**: Make sure your plugin is in a directory in the plugin search path
4. **Verify plugin structure**: Make sure your plugin follows the required structure
5. **Test in isolation**: Try loading and using your plugin in isolation
6. **Debug initialization**: Add debug logging to your plugin's initialization method
7. **Check for conflicts**: Make sure there are no conflicts with other plugins
8. **Verify compatibility**: Make sure your plugin is compatible with the current version of PyProcessor
