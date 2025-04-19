# PyProcessor Configuration

This document explains the PyProcessor configuration system, including the configuration format, schema-based validation, and programmatic access.

## Configuration Format

PyProcessor uses JSON files for configuration, stored in the `pyprocessor/profiles/` directory. Each profile is a separate JSON file that contains settings for encoding, file processing, and server optimization.

## Flag-Pattern Relationships

The configuration includes several flags that control whether certain patterns are applied during processing:

### Auto Rename Files

The `auto_rename_files` flag controls whether input files are renamed according to the `file_rename_pattern` before processing.

```json
{
  "auto_rename_files": true,
  "file_rename_pattern": "(\\d+-\\d+)(?:[_-].*?)?\\.mp4$"
}
```

When `auto_rename_files` is `true`:

- The `file_rename_pattern` is used to extract parts of filenames for renaming
- Files that match the pattern are renamed to the format specified by the capture group
- For example, with the default pattern, a file named `video-123-456.mp4` will be renamed to `123-456.mp4`

When `auto_rename_files` is `false`:

- Files are not renamed
- The `file_rename_pattern` is ignored

### Auto Organize Folders

The `auto_organize_folders` flag controls whether output folders are organized according to the `folder_organization_pattern` after processing.

```json
{
  "auto_organize_folders": true,
  "folder_organization_pattern": "^(\\d+)-\\d+"
}
```

When `auto_organize_folders` is `true`:

- The `folder_organization_pattern` is used to organize folders into a hierarchical structure
- Folders that match the pattern are moved into parent folders based on the capture group
- For example, with the default pattern, a folder named `123-456` will be moved into a parent folder named `123`

When `auto_organize_folders` is `false`:

- Folders are not organized
- The `folder_organization_pattern` is ignored

### File Validation

The `file_validation_pattern` is always used to validate files before processing, regardless of the flag settings.

```json
{
  "file_validation_pattern": "^\\d+-\\d+\\.mp4$"
}
```

- Files that match the pattern are considered valid and will be processed
- Files that don't match the pattern are considered invalid and will be skipped
- For example, with the default pattern, only files named like `123-456.mp4` will be processed

## Example Configuration

Here's an example of a complete configuration with explanations:

```jsonc
{
  // Input and output directories
  "input_folder": "C:\\inetpub\\wwwroot\\media\\input",
  "output_folder": "C:\\inetpub\\wwwroot\\media\\output",

  // FFmpeg encoding parameters
  "ffmpeg_params": {
    "video_encoder": "libx265",
    "preset": "medium",
    "tune": "film",
    "fps": 60,
    "include_audio": true,
    "bitrates": {
      "1080p": "15000k",
      "720p": "8500k",
      "480p": "5000k",
      "360p": "2500k"
    },
    "audio_bitrates": ["256k", "192k", "128k", "96k"]
  },

  // Parallel processing
  "max_parallel_jobs": 2,

  // File processing flags
  "auto_rename_files": true,      // Controls whether file_rename_pattern is applied
  "auto_organize_folders": true,  // Controls whether folder_organization_pattern is applied

  // Regex patterns for file processing
  "file_rename_pattern": "(\\d+-\\d+)(?:[_-].*?)?\\.mp4$",  // Used when auto_rename_files is true
  "file_validation_pattern": "^\\d+-\\d+\\.mp4$",           // Always used for validation
  "folder_organization_pattern": "^(\\d+)-\\d+",            // Used when auto_organize_folders is true

  // Profile information
  "last_used_profile": "high_quality",
  "saved_at": "2023-07-15T12:30:00.000000"
}
```

## Configuration Schema

For a complete reference of all configuration options, see the [Configuration Schema](../config_schema.json) document.

## Programmatic Access

PyProcessor provides two ways to access configuration:

### Legacy Config Class

The legacy configuration is managed by the `Config` class in `pyprocessor/utils/config.py`. This class provides methods for loading, saving, and validating configuration settings.

```python
from pyprocessor.utils.config import Config

# Create a new configuration
config = Config()

# Load a profile
config.load(profile_name="high_quality")

# Access configuration values
input_folder = config.input_folder
auto_rename_files = config.auto_rename_files
file_rename_pattern = config.file_rename_pattern

# Modify configuration values
config.auto_rename_files = True
config.file_rename_pattern = r"(\\d+-\\d+)(?:[_-].*?)?\\.mp4$"

# Save configuration
config.save(profile_name="custom_profile")
```

### Modern ConfigManager Class

The modern configuration system is managed by the `ConfigManager` class in `pyprocessor/utils/config_manager.py`. This class provides a more robust and feature-rich interface for configuration management.

```python
from pyprocessor.utils.config_manager import get_config

# Get the configuration manager
config = get_config()

# Access configuration values
input_folder = config.get("input_folder")
auto_rename_files = config.get_bool("auto_rename_files")
file_rename_pattern = config.get("file_rename_pattern")

# Modify configuration values
config.set("auto_rename_files", True)
config.set("file_rename_pattern", r"(\\d+-\\d+)(?:[_-].*?)?\\.mp4$")

# Save configuration
config.save_to_file("custom_profile.json")
```

### Module-Level Functions

The `config_manager` module also provides module-level functions for common operations:

```python
from pyprocessor.utils.config_manager import get, set, save_to_file, load_from_file

# Access configuration values
input_folder = get("input_folder")
auto_rename_files = get("auto_rename_files", default=False)

# Modify configuration values
set("auto_rename_files", True)

# Save and load configuration
save_to_file("custom_profile.json")
load_from_file("custom_profile.json")
```

## Advanced Configuration Features

### Configuration Versioning

The `ConfigManager` tracks configuration changes and provides versioning capabilities:

```python
from pyprocessor.utils.config_manager import get_config, get_version, get_change_history, revert_to_version

# Get the current version
version = get_version()

# Get the change history
history = get_change_history()

# Revert to a previous version
revert_to_version(1)
```

### Configuration Change Callbacks

You can register callbacks to be notified when configuration values change:

```python
from pyprocessor.utils.config_manager import register_change_callback

# Define a callback function
def on_config_change(key, old_value, new_value):
    print(f"Configuration changed: {key} = {new_value} (was {old_value})")

# Register the callback
register_change_callback(on_config_change)
```

### Configuration Merging and Diffing

You can merge configurations and compare them:

```python
from pyprocessor.utils.config_manager import merge, merge_from_file, diff, diff_with_file

# Merge with a dictionary
merge({
    "auto_rename_files": True,
    "file_rename_pattern": r"(\\d+-\\d+)(?:[_-].*?)?\\.mp4$"
})

# Merge with a file
merge_from_file("custom_profile.json")

# Compare with a dictionary
diff_result = diff({
    "auto_rename_files": True,
    "file_rename_pattern": r"(\\d+-\\d+)(?:[_-].*?)?\\.mp4$"
})

# Compare with a file
diff_result = diff_with_file("custom_profile.json")
```

### Configuration Export/Import

You can export and import configurations in various formats:

```python
from pyprocessor.utils.config_manager import export_to_json, export_to_yaml, export_to_csv
from pyprocessor.utils.config_manager import import_from_json, import_from_yaml, import_from_csv

# Export to different formats
export_to_json("config.json")
export_to_yaml("config.yaml")
export_to_csv("config.csv")

# Import from different formats
import_from_json("config.json")
import_from_yaml("config.yaml")
import_from_csv("config.csv")
```

### Configuration Documentation

You can generate documentation from the configuration schema:

```python
from pyprocessor.utils.config_manager import generate_documentation

# Generate documentation
doc = generate_documentation()

# Save documentation to a file
generate_documentation("config.md")
```

## Best Practices

1. **Use Consistent Patterns**: Ensure that your `file_rename_pattern`, `file_validation_pattern`, and `folder_organization_pattern` work together consistently.

2. **Test Patterns**: Before using custom patterns in production, test them with sample filenames to ensure they work as expected.

3. **Document Custom Patterns**: If you create custom patterns, document their purpose and expected behavior for future reference.

4. **Validate Configuration**: Always validate configuration settings before using them to ensure they are valid and consistent.

5. **Use Profiles**: Create different profiles for different encoding scenarios to avoid having to reconfigure settings each time.

6. **Use the Schema**: Define configuration options in the schema with appropriate types, defaults, and validation rules.

7. **Use Environment Variables**: Use environment variables for sensitive configuration values.

8. **Use Versioning**: Track configuration changes using the versioning system.

9. **Use Diffing**: Compare configurations to identify differences.

10. **Use Documentation Generation**: Generate documentation from the schema to document configuration options.
