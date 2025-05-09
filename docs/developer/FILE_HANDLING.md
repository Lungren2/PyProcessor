# File Handling in PyProcessor

This document describes the file handling system in PyProcessor, including the centralized `FileManager` class and best practices for working with files.

## Overview

PyProcessor provides a centralized file management system through the `FileManager` class in the `pyprocessor.utils.file_manager` module. This class provides a consistent interface for file operations, error handling, and file organization.

The file management system is designed to work closely with the path management system (see [PATH_HANDLING.md](PATH_HANDLING.md)) to provide a comprehensive solution for working with files and paths.

## File Manager

The `FileManager` class is a singleton that provides the following features:

- Consistent error handling for file operations
- Progress reporting for long-running operations
- File validation and pattern matching
- File and folder organization
- File content operations (read/write)
- File compression operations (ZIP/TAR)
- File metadata operations
- File streaming operations

### Getting the File Manager

```python
from pyprocessor.utils.file_manager import get_file_manager

# Get the file manager
file_manager = get_file_manager()

# Get the file manager with a configuration object
from pyprocessor.utils.config_manager import get_config_manager
config = get_config_manager()
file_manager = get_file_manager(config)
```

## Basic File Operations

### Listing Files

```python
from pyprocessor.utils.file_manager import get_file_manager

file_manager = get_file_manager()

# List all files in a directory
files = file_manager.list_files("/path/to/directory")

# List files with a specific pattern
mp4_files = file_manager.list_files("/path/to/directory", pattern="*.mp4")

# List files recursively
all_files = file_manager.list_files("/path/to/directory", recursive=True)
```

### Copying and Moving Files

```python
from pyprocessor.utils.file_manager import get_file_manager

file_manager = get_file_manager()

# Copy a file
file_manager.copy_file("/path/to/source.txt", "/path/to/destination.txt")

# Move a file
file_manager.move_file("/path/to/source.txt", "/path/to/destination.txt")

# Rename a file
file_manager.rename_file("/path/to/file.txt", "new_name.txt")
```

### Removing Files and Directories

```python
from pyprocessor.utils.file_manager import get_file_manager

file_manager = get_file_manager()

# Remove a file
file_manager.remove_file("/path/to/file.txt")

# Remove a directory
file_manager.remove_directory("/path/to/directory")

# Remove a directory recursively
file_manager.remove_directory("/path/to/directory", recursive=True)
```

## File Content Operations

### Reading and Writing Text

```python
from pyprocessor.utils.file_manager import get_file_manager

file_manager = get_file_manager()

# Read text from a file
content = file_manager.read_text("/path/to/file.txt")

# Write text to a file
file_manager.write_text("/path/to/file.txt", "Hello, world!")

# Append text to a file
file_manager.write_text("/path/to/file.txt", "More content", append=True)

# Read lines from a file
lines = file_manager.read_lines("/path/to/file.txt")

# Write lines to a file
file_manager.write_lines("/path/to/file.txt", ["Line 1", "Line 2", "Line 3"])
```

### Reading and Writing Binary Data

```python
from pyprocessor.utils.file_manager import get_file_manager

file_manager = get_file_manager()

# Read binary data from a file
data = file_manager.read_binary("/path/to/file.bin")

# Write binary data to a file
file_manager.write_binary("/path/to/file.bin", b"Binary data")
```

### Working with JSON and CSV

```python
from pyprocessor.utils.file_manager import get_file_manager

file_manager = get_file_manager()

# Read JSON from a file
data = file_manager.read_json("/path/to/file.json")

# Write JSON to a file
file_manager.write_json("/path/to/file.json", {"key": "value"})

# Read CSV from a file
data = file_manager.read_csv("/path/to/file.csv")

# Write CSV to a file
file_manager.write_csv("/path/to/file.csv", [
    {"name": "John", "age": 30},
    {"name": "Jane", "age": 25}
])
```

## File Compression Operations

### Working with ZIP Files

```python
from pyprocessor.utils.file_manager import get_file_manager

file_manager = get_file_manager()

# Create a ZIP file
file_manager.create_zip("/path/to/archive.zip", [
    "/path/to/file1.txt",
    "/path/to/file2.txt"
])

# Extract a ZIP file
file_manager.extract_zip("/path/to/archive.zip", "/path/to/extract")
```

### Working with TAR Files

```python
from pyprocessor.utils.file_manager import get_file_manager

file_manager = get_file_manager()

# Create a TAR file
file_manager.create_tar("/path/to/archive.tar.gz", [
    "/path/to/file1.txt",
    "/path/to/file2.txt"
], compression="gz")

# Extract a TAR file
file_manager.extract_tar("/path/to/archive.tar.gz", "/path/to/extract")
```

## File Metadata Operations

### Getting File Metadata

```python
from pyprocessor.utils.file_manager import get_file_manager

file_manager = get_file_manager()

# Get file metadata
metadata = file_manager.get_file_metadata("/path/to/file.txt")
print(metadata["size"])
print(metadata["modified"])
print(metadata["mime_type"])

# Get directory size
size = file_manager.get_directory_size("/path/to/directory")

# Get file hash
hash_value = file_manager.get_file_hash("/path/to/file.txt", algorithm="sha256")

# Get MIME type
mime_type = file_manager.get_mime_type("/path/to/file.txt")
```

### Setting File Times

```python
from pyprocessor.utils.file_manager import get_file_manager
from datetime import datetime

file_manager = get_file_manager()

# Set file times
file_manager.set_file_times("/path/to/file.txt", 
                           accessed=datetime.now(),
                           modified=datetime.now())
```

## File Streaming Operations

### Streaming File Content

```python
from pyprocessor.utils.file_manager import get_file_manager

file_manager = get_file_manager()

# Stream lines from a text file
for line in file_manager.stream_read_lines("/path/to/file.txt"):
    print(line)

# Stream chunks from a binary file
for chunk in file_manager.stream_read_chunks("/path/to/file.bin"):
    process_chunk(chunk)
```

### Using File Context Managers

```python
from pyprocessor.utils.file_manager import get_file_manager

file_manager = get_file_manager()

# Open a text file
with file_manager.open_text("/path/to/file.txt", "r") as f:
    content = f.read()

# Open a binary file
with file_manager.open_binary("/path/to/file.bin", "rb") as f:
    data = f.read()
```

## File Organization

### Renaming Files Based on Patterns

```python
from pyprocessor.utils.file_manager import get_file_manager

file_manager = get_file_manager()

# Rename files based on a pattern
file_manager.rename_files("/path/to/directory", pattern=r"(\d+)_.*\.mp4")
```

### Validating Files

```python
from pyprocessor.utils.file_manager import get_file_manager

file_manager = get_file_manager()

# Validate files based on a pattern
valid_files, invalid_files = file_manager.validate_files("/path/to/directory", 
                                                       pattern=r"^\d+_.*\.mp4$")
```

### Organizing Folders

```python
from pyprocessor.utils.file_manager import get_file_manager

file_manager = get_file_manager()

# Organize folders based on a pattern
file_manager.organize_folders("/path/to/directory", pattern=r"^(\d+)_.*$")
```

## Temporary Files and Directories

### Creating Temporary Files and Directories

```python
from pyprocessor.utils.file_manager import get_file_manager

file_manager = get_file_manager()

# Create a temporary directory
temp_dir = file_manager.create_temp_directory()

# Clean up temporary directories
file_manager.clean_temp_directories()
```

## Best Practices

1. Always use the `FileManager` for file operations to ensure consistent error handling and logging
2. Use the context managers (`open_text`, `open_binary`) for file I/O to ensure proper resource cleanup
3. Use the streaming functions (`stream_read_lines`, `stream_read_chunks`) for large files to minimize memory usage
4. Use the file validation functions to ensure files meet expected patterns
5. Use the file organization functions to keep files and folders organized
6. Use the temporary file and directory functions for temporary storage
7. Use the file metadata functions to get information about files
8. Use the file compression functions for working with archives
9. Always handle errors gracefully and provide meaningful error messages
10. Use the `get_file_manager()` function to get the singleton instance instead of creating a new instance

## Error Handling

The `FileManager` class provides consistent error handling for all file operations. Most methods return `None`, `False`, or an empty collection on failure, and log the error using the logger.

```python
from pyprocessor.utils.file_manager import get_file_manager

file_manager = get_file_manager()

# Example of error handling
result = file_manager.read_text("/path/to/nonexistent/file.txt")
if result is None:
    print("Failed to read file")
else:
    print(result)
```

For more information on error handling in PyProcessor, see [ERROR_HANDLING.md](ERROR_HANDLING.md).

## Integration with Path Management

The file management system works closely with the path management system. For more information on path handling, see [PATH_HANDLING.md](PATH_HANDLING.md).

```python
from pyprocessor.utils.file_manager import get_file_manager
from pyprocessor.utils.path_manager import normalize_path

file_manager = get_file_manager()
path = normalize_path("${MEDIA_ROOT}/videos/video.mp4")

# Use the normalized path with the file manager
content = file_manager.read_binary(path)
```
