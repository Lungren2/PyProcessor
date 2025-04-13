# PyProcessor Configuration

This document explains the PyProcessor configuration format, with a focus on the flag-pattern relationships that control file processing behavior.

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

The configuration is managed by the `Config` class in `pyprocessor/utils/config.py`. This class provides methods for loading, saving, and validating configuration settings.

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

## Best Practices

1. **Use Consistent Patterns**: Ensure that your `file_rename_pattern`, `file_validation_pattern`, and `folder_organization_pattern` work together consistently.

2. **Test Patterns**: Before using custom patterns in production, test them with sample filenames to ensure they work as expected.

3. **Document Custom Patterns**: If you create custom patterns, document their purpose and expected behavior for future reference.

4. **Validate Configuration**: Always validate configuration settings before using them to ensure they are valid and consistent.

5. **Use Profiles**: Create different profiles for different encoding scenarios to avoid having to reconfigure settings each time.
