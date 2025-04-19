"""
PyProcessor plugin system.

This package contains the plugin system for PyProcessor, including:
- Plugin interfaces
- Built-in plugins
- Plugin discovery and loading
"""

# Import plugin interfaces
from pyprocessor.utils.plugin_manager import Plugin
from pyprocessor.plugins.interfaces import (
    EncoderPlugin,
    ProcessorPlugin,
    FilterPlugin,
    AnalyzerPlugin,
    OutputPlugin,
)

# Import built-in plugins
from pyprocessor.plugins.ffmpeg_encoder import FFmpegEncoderPlugin

# List of built-in plugins
BUILTIN_PLUGINS = [
    FFmpegEncoderPlugin,
]
