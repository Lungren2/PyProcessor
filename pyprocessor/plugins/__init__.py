"""
PyProcessor plugin system.

This package contains the plugin system for PyProcessor, including:
- Plugin interfaces
- Built-in plugins
- Plugin discovery and loading
"""

# Import built-in plugins
from pyprocessor.plugins.ffmpeg_encoder import FFmpegEncoderPlugin

# Import plugin interfaces

# List of built-in plugins
BUILTIN_PLUGINS = [  # Unused variable  # Unused variable  # Unused variable
    FFmpegEncoderPlugin,
]
