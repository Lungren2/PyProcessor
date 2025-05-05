"""
Example script demonstrating how to use the plugin system.

This script shows how to discover, load, and use plugins.
"""

import os
import sys
import json
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyprocessor.utils.core.plugin_manager import (
    get_plugin_manager,
    discover_plugins,
    load_plugin,
    enable_plugin,
    get_plugin,
    get_available_plugins,
    get_all_plugin_metadata,
)


def main():
    """Main function demonstrating plugin usage."""
    # Add the examples/plugins directory to the plugin search path
    plugin_dirs = [Path(__file__).parent / "plugins"]
    plugin_manager = get_plugin_manager(plugin_dirs)

    # Discover available plugins
    print("Discovering plugins...")
    discover_plugins()

    # Get available plugins
    available_plugins = get_available_plugins()
    print(f"Available plugins: {available_plugins}")

    # Get plugin metadata
    plugin_metadata = get_all_plugin_metadata()
    print("Plugin metadata:")
    for name, metadata in plugin_metadata.items():
        print(
            f"  {name}: {metadata['description']} (v{metadata['version']}) by {metadata['author']}"
        )

    # Load and use the FFmpeg encoder plugin
    print("\nLoading FFmpeg encoder plugin...")
    ffmpeg_plugin = load_plugin("ffmpeg_encoder")
    if ffmpeg_plugin:
        print("FFmpeg encoder plugin loaded successfully")

        # Enable the plugin
        enable_plugin("ffmpeg_encoder")
        print("FFmpeg encoder plugin enabled")

        # Get plugin information
        print(f"Supported formats: {ffmpeg_plugin.get_supported_formats()}")
        print(
            f"Supported codecs: {json.dumps(ffmpeg_plugin.get_supported_codecs(), indent=2)}"
        )
        print(
            f"Default options: {json.dumps(ffmpeg_plugin.get_default_options(), indent=2)}"
        )

        # Use the plugin
        input_file = "examples/data/sample.mp4"
        output_file = "examples/data/output.mp4"

        # Create the output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Check if the input file exists
        if not os.path.exists(input_file):
            print(f"Input file not found: {input_file}")
            print("Please create this file or update the path to an existing file")
        else:
            # Encode the file
            print(f"Encoding {input_file} to {output_file}...")
            success = ffmpeg_plugin.encode(
                input_file,
                output_file,
                {
                    "video_codec": "libx264",
                    "audio_codec": "aac",
                    "preset": "fast",
                    "crf": 23,
                },
            )

            if success:
                print("Encoding completed successfully")
            else:
                print("Encoding failed")
    else:
        print("Failed to load FFmpeg encoder plugin")

    # Load and use the simple analyzer plugin
    print("\nLoading simple analyzer plugin...")
    analyzer_plugin = load_plugin("simple_analyzer")
    if analyzer_plugin:
        print("Simple analyzer plugin loaded successfully")

        # Enable the plugin
        enable_plugin("simple_analyzer")
        print("Simple analyzer plugin enabled")

        # Get plugin information
        print(f"Supported formats: {analyzer_plugin.get_supported_formats()}")
        print(
            f"Default options: {json.dumps(analyzer_plugin.get_default_options(), indent=2)}"
        )

        # Use the plugin
        input_file = "examples/data/sample.mp4"

        # Check if the input file exists
        if not os.path.exists(input_file):
            print(f"Input file not found: {input_file}")
            print("Please create this file or update the path to an existing file")
        else:
            # Analyze the file
            print(f"Analyzing {input_file}...")
            results = analyzer_plugin.analyze(
                input_file,
                {
                    "include_timestamps": True,
                    "include_permissions": True,
                    "save_results": True,
                    "output_file": "examples/data/analysis.json",
                },
            )

            print("Analysis results:")
            print(json.dumps(results, indent=2))
    else:
        print("Failed to load simple analyzer plugin")


if __name__ == "__main__":
    main()
