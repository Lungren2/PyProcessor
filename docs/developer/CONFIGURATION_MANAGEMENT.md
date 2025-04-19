# Configuration Management in PyProcessor

This document describes the configuration management system in PyProcessor, including the configuration schema, environment variables, and validation.

## Configuration Manager

PyProcessor uses a centralized configuration management system through the `ConfigManager` class in the `pyprocessor.utils.config_manager` module. This provides:

- Consistent configuration handling across the application
- Schema-based configuration validation
- Environment variable expansion in configuration values
- Type conversion for configuration values
- Profile management for saving and loading configurations

## Configuration Schema

The configuration schema is defined in the `pyprocessor.utils.config_schema` module. It provides:

- Default values for all configuration options
- Type information for validation
- Environment variable mappings
- Validation rules (min/max values, patterns, etc.)
- Documentation for each configuration option

## Configuration Value Types

The following configuration value types are supported:

- `STRING`: String values
- `INTEGER`: Integer values
- `FLOAT`: Floating-point values
- `BOOLEAN`: Boolean values
- `ARRAY`: Array/list values
- `OBJECT`: Object/dictionary values
- `PATH`: File system path values
- `ENUM`: Enumerated values (from a predefined set)
- `REGEX`: Regular expression patterns

## Environment Variables

Configuration values can be overridden using environment variables. The mapping between configuration keys and environment variables is defined in the schema.

For example:

| Configuration Key | Environment Variable |
|-------------------|----------------------|
| `input_folder` | `PYPROCESSOR_INPUT_FOLDER` |
| `output_folder` | `PYPROCESSOR_OUTPUT_FOLDER` |
| `ffmpeg_params.video_encoder` | `PYPROCESSOR_VIDEO_ENCODER` |
| `max_parallel_jobs` | `PYPROCESSOR_MAX_PARALLEL_JOBS` |

## Using the Configuration Manager

### Accessing the Configuration Manager

```python
from pyprocessor.utils.config_manager import get_config

# Get the configuration manager
config = get_config()
```

### Getting Configuration Values

```python
# Get a simple value
input_folder = config.get("input_folder")

# Get a nested value using dot notation
encoder = config.get("ffmpeg_params.video_encoder")

# Get a value with a default
preset = config.get("ffmpeg_params.preset", "ultrafast")

# Get a value with type conversion
fps = config.get_int("ffmpeg_params.fps", 60)
include_audio = config.get_bool("ffmpeg_params.include_audio", True)
bitrates = config.get_dict("ffmpeg_params.bitrates")
audio_bitrates = config.get_list("ffmpeg_params.audio_bitrates")

# Get a path value (returns a Path object)
input_path = config.get_path("input_folder")
```

### Setting Configuration Values

```python
# Set a simple value
config.set("input_folder", "/path/to/input")

# Set a nested value using dot notation
config.set("ffmpeg_params.video_encoder", "libx265")

# Set a complex value
config.set("ffmpeg_params.bitrates", {
    "1080p": "11000k",
    "720p": "6500k",
    "480p": "4000k",
    "360p": "1500k",
})
```

### Loading and Saving Configuration

```python
# Load configuration from a file
config.load("/path/to/config.json")

# Load a configuration profile
config.load(profile_name="high_quality")

# Save configuration to a file
config.save("/path/to/config.json")

# Save a configuration profile
config.save(profile_name="high_quality")

# Get available profiles
profiles = config.get_available_profiles()
```

### Validating Configuration

```python
# Validate configuration
errors, warnings = config.validate()

if errors:
    print("Configuration errors:")
    for error in errors:
        print(f"- {error}")

if warnings:
    print("Configuration warnings:")
    for warning in warnings:
        print(f"- {warning}")
```

## Configuration Profiles

Configuration profiles allow users to save and load different configurations for different use cases. Profiles are stored as JSON files in the profiles directory.

The profiles directory is determined by the platform:

- Windows: `%APPDATA%\PyProcessor\profiles`
- macOS: `~/Library/Preferences/PyProcessor/profiles`
- Linux: `~/.config/pyprocessor/profiles`

## Default Configuration

The default configuration is defined in the schema and includes:

- Input and output folders in the user's media directory
- FFmpeg parameters for high-quality encoding
- Default file patterns for renaming and organizing files
- Server optimization settings

## Environment Variable Expansion

Environment variables in configuration values are automatically expanded. Both `${VAR}` and `%VAR%` formats are supported for compatibility with Unix/Linux/macOS and Windows.

```python
# Configuration with environment variables
config.set("input_folder", "${HOME}/videos")
config.set("output_folder", "%USERPROFILE%\\videos")

# Get expanded values
input_folder = config.get_path("input_folder")  # Returns Path object with expanded path
```

## Compatibility with Old Config Class

For backward compatibility, the old `Config` class is still available. It provides the same interface as before but uses the new `ConfigManager` internally.

```python
from pyprocessor.utils.config import Config

# Create a new configuration
config = Config()

# Access configuration values using attribute access
input_folder = config.input_folder
auto_rename_files = config.auto_rename_files
```

## Best Practices

1. **Use the ConfigManager**: Always use the `ConfigManager` for accessing and modifying configuration values.
2. **Use Environment Variables**: Use environment variables for configuration values that might change between environments.
3. **Validate Configuration**: Always validate configuration before using it.
4. **Use Type-Specific Getters**: Use the type-specific getters (`get_int`, `get_bool`, etc.) to ensure correct types.
5. **Use Dot Notation**: Use dot notation for accessing nested configuration values.
6. **Use Profiles**: Use configuration profiles for different use cases.
7. **Expand Environment Variables**: Use environment variables in configuration values for portability.

## Example: Complete Configuration Management

```python
from pyprocessor.utils.config_manager import get_config
from pyprocessor.utils.path_manager import get_profiles_dir

# Get the configuration manager
config = get_config()

# Load a profile
config.load(profile_name="high_quality")

# Validate configuration
errors, warnings = config.validate()

if errors:
    print("Configuration errors:")
    for error in errors:
        print(f"- {error}")
    # Handle errors (e.g., exit the application)
    exit(1)

if warnings:
    print("Configuration warnings:")
    for warning in warnings:
        print(f"- {warning}")

# Get configuration values
input_folder = config.get_path("input_folder")
output_folder = config.get_path("output_folder")
encoder = config.get("ffmpeg_params.video_encoder")
preset = config.get("ffmpeg_params.preset")
fps = config.get_int("ffmpeg_params.fps")
include_audio = config.get_bool("ffmpeg_params.include_audio")

# Use configuration values
print(f"Input folder: {input_folder}")
print(f"Output folder: {output_folder}")
print(f"Encoder: {encoder}")
print(f"Preset: {preset}")
print(f"FPS: {fps}")
print(f"Include audio: {include_audio}")

# Modify configuration
config.set("ffmpeg_params.video_encoder", "libx264")
config.set("ffmpeg_params.preset", "medium")

# Save modified configuration as a new profile
config.save(profile_name="custom_profile")

# Get available profiles
profiles = config.get_available_profiles()
print(f"Available profiles: {', '.join(profiles)}")
```
