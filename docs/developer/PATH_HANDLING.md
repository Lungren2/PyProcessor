# Path Handling in PyProcessor

This document describes how paths are handled in PyProcessor, including the use of environment variables and platform-agnostic paths.

## Platform-Agnostic Paths

PyProcessor uses platform-agnostic paths to ensure compatibility across different operating systems. This means:

- Forward slashes (`/`) are used in configuration files instead of backslashes (`\`)
- Environment variables are used to define base directories
- The `pathlib.Path` class is used for path manipulation, which automatically handles platform-specific path separators

## Environment Variables

The following environment variables can be used to customize paths in PyProcessor:

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `MEDIA_ROOT` | Base directory for media files | Platform-specific (see below) |
| `PYPROCESSOR_PROFILES_DIR` | Directory for profile files | `<app_dir>/profiles` |
| `PYPROCESSOR_LOG_DIR` | Directory for log files | `<app_dir>/logs` |

### Default Values

If the environment variables are not set, the following default values are used:

#### MEDIA_ROOT

- **Windows**: 
  - If IIS is installed: `C:/inetpub/wwwroot/media`
  - Otherwise: `%USERPROFILE%/Documents/PyProcessor/media`
- **Linux**: 
  - If web server directories exist: `/var/www/html/media` or `/srv/www/media`
  - Otherwise: `~/PyProcessor/media`
- **macOS**: `~/Library/Application Support/PyProcessor/media`

## Using Environment Variables in Configuration

Environment variables can be used in configuration files using the `${VAR}` syntax:

```json
{
  "input_folder": "${MEDIA_ROOT}/input",
  "output_folder": "${MEDIA_ROOT}/output"
}
```

This allows for flexible configuration across different environments without hardcoding paths.

## Path Utilities

The `pyprocessor.utils.path_utils` module provides utilities for working with paths:

- `normalize_path(path_str)`: Converts a string path to a `Path` object, expanding environment variables
- `expand_env_vars(path_str)`: Expands environment variables in a path string
- `get_default_media_root()`: Returns the default media root directory based on the platform
- `get_app_data_dir()`: Returns the application data directory based on the platform

## Examples

### Setting Environment Variables

#### Windows (PowerShell)

```powershell
$env:MEDIA_ROOT = "D:/media"
$env:PYPROCESSOR_PROFILES_DIR = "D:/pyprocessor/profiles"
```

#### Linux/macOS (Bash)

```bash
export MEDIA_ROOT="/mnt/data/media"
export PYPROCESSOR_PROFILES_DIR="/mnt/data/pyprocessor/profiles"
```

### Using Environment Variables in Code

```python
from pyprocessor.utils.path_utils import normalize_path

# Expand environment variables in a path
media_path = normalize_path("${MEDIA_ROOT}/videos")

# Use the path
with open(media_path / "video.mp4", "rb") as f:
    # Do something with the file
    pass
```

## Best Practices

1. Always use forward slashes (`/`) in path strings, even on Windows
2. Use environment variables for base directories to make configurations portable
3. Use the `normalize_path()` function when converting string paths to `Path` objects
4. Use relative paths when possible to improve portability
