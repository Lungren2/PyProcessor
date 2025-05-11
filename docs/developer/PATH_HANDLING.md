# Path Handling in PyProcessor

This document describes how paths are handled in PyProcessor, including the use of environment variables and platform-agnostic paths.

## Platform-Agnostic Paths

PyProcessor uses platform-agnostic paths to ensure compatibility across different operating systems. This means:

- Forward slashes (`/`) are used in configuration files instead of backslashes (`\`)
- Environment variables are used to define base directories
- The `pathlib.Path` class is used for path manipulation, which automatically handles platform-specific path separators

## Environment Variables

The following environment variables can be used to customize paths in PyProcessor:

| Variable                   | Description                    | Default Value                 |
| -------------------------- | ------------------------------ | ----------------------------- |
| `MEDIA_ROOT`               | Base directory for media files | Platform-specific (see below) |
| `PYPROCESSOR_PROFILES_DIR` | Directory for profile files    | `<app_dir>/profiles`          |
| `PYPROCESSOR_LOG_DIR`      | Directory for log files        | `<app_dir>/logs`              |

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

## Path Manager

The `pyprocessor.utils.path_manager` module provides a centralized path manager for working with paths:

- `get_path_manager()`: Returns the singleton path manager instance
- `normalize_path(path_str)`: Converts a string path to a `Path` object, expanding environment variables
- `expand_env_vars(path_str)`: Expands environment variables in a path string
- `get_default_media_root()`: Returns the default media root directory based on the platform
- `get_app_data_dir()`: Returns the application data directory based on the platform
- `get_profiles_dir()`: Returns the profiles directory based on the platform
- `get_logs_dir()`: Returns the logs directory based on the platform
- `get_user_data_dir()`: Returns the user data directory based on platform conventions
- `get_user_config_dir()`: Returns the user configuration directory based on platform conventions
- `get_user_cache_dir()`: Returns the user cache directory based on platform conventions
- `get_temp_dir()`: Creates and returns a temporary directory
- `get_temp_file()`: Creates and returns a temporary file
- `temp_dir_context()`: Context manager for a temporary directory
- `temp_file_context()`: Context manager for a temporary file
- `is_same_path()`: Checks if two paths refer to the same file or directory
- `is_subpath()`: Checks if a path is a subpath of another path
- `is_valid_path()`: Checks if a path is valid
- `is_absolute_path()`: Checks if a path is absolute
- `make_relative()`: Makes a path relative to a base path
- `make_absolute()`: Makes a path absolute

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

### Using the Path Manager in Code

```python
from pyprocessor.utils.path_manager import get_path_manager

# Get the path manager
path_manager = get_path_manager()

# Normalize a path
media_path = path_manager.normalize_path("${MEDIA_ROOT}/videos")

# Use the path
with open(media_path / "video.mp4", "rb") as f:
    # Do something with the file
    pass
```

### Using Path Utility Functions

```python
from pyprocessor.utils.path_manager import normalize_path, ensure_dir_exists

# Normalize a path
config_path = normalize_path("${PYPROCESSOR_DATA_DIR}/config.json")

# Ensure a directory exists
output_dir = ensure_dir_exists("${MEDIA_ROOT}/output")
```

### Working with Temporary Files and Directories

```python
from pyprocessor.utils.path_manager import get_temp_dir, get_temp_file, temp_dir_context, temp_file_context

# Create a temporary directory
temp_dir = get_temp_dir(prefix="my_prefix_")

# Create a temporary file
temp_file = get_temp_file(suffix=".json", prefix="my_prefix_")

# Use a temporary directory with automatic cleanup
with temp_dir_context() as temp_dir:
    # Do something with the temporary directory
    (temp_dir / "file.txt").write_text("Hello, world!")
    # Directory is automatically removed when the context exits

# Use a temporary file with automatic cleanup
with temp_file_context(suffix=".json") as temp_file:
    # Do something with the temporary file
    temp_file.write_text('{"key": "value"}')
    # File is automatically removed when the context exits
```

### Path Validation and Comparison

```python
from pyprocessor.utils.path_manager import is_same_path, is_subpath, is_valid_path, is_absolute_path, make_relative, make_absolute

# Check if two paths refer to the same file or directory
if is_same_path("path/to/file.txt", "./path/to/file.txt"):
    print("Paths refer to the same file")

# Check if a path is a subpath of another path
if is_subpath("/home/user", "/home/user/documents/file.txt"):
    print("File is in the user's home directory")

# Check if a path is valid
if is_valid_path("path/with/invalid/characters?*:"):
    print("Path is valid")
else:
    print("Path is invalid")

# Check if a path is absolute
if is_absolute_path("/absolute/path"):
    print("Path is absolute")
else:
    print("Path is relative")

# Make a path relative to a base path
relative_path = make_relative("/home/user/documents/file.txt", "/home/user")
# Result: "documents/file.txt"

# Make a path absolute
absolute_path = make_absolute("documents/file.txt", "/home/user")
# Result: "/home/user/documents/file.txt"
```

## Best Practices

1. Always use forward slashes (`/`) in path strings, even on Windows
2. Use environment variables for base directories to make configurations portable
3. Use the `normalize_path()` function when converting string paths to `Path` objects
4. Use relative paths when possible to improve portability
5. Use the path manager for all path operations to ensure consistent behavior
6. Use the `ensure_dir_exists()` function to create directories before writing files
7. Use the `get_*_dir()` functions to get standard directories instead of hardcoding paths
8. Use the `temp_dir_context()` and `temp_file_context()` context managers for temporary files and directories to ensure proper cleanup
9. Use the `is_same_path()` function to compare paths instead of string comparison
10. Use the `is_subpath()` function to check if a path is within a specific directory
11. Use the `make_relative()` and `make_absolute()` functions to convert between relative and absolute paths
12. Use the `is_valid_path()` function to validate user input before using it as a path

## Platform-Specific Directories

The path manager provides platform-specific directories based on standard conventions:

### Windows

- User Data: `%LOCALAPPDATA%\PyProcessor`
- User Config: `%APPDATA%\PyProcessor`
- User Cache: `%LOCALAPPDATA%\PyProcessor\Cache`
- Logs: `%LOCALAPPDATA%\PyProcessor\logs`

### macOS

- User Data: `~/Library/Application Support/PyProcessor`
- User Config: `~/Library/Preferences/PyProcessor`
- User Cache: `~/Library/Caches/PyProcessor`
- Logs: `~/Library/Logs/PyProcessor`

### Linux

- User Data: `~/.local/share/pyprocessor`
- User Config: `~/.config/pyprocessor`
- User Cache: `~/.cache/pyprocessor`
- Logs: `/var/log/pyprocessor` (if writable) or `~/.local/share/pyprocessor/logs`
