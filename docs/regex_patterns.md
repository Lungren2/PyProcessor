# Regex Patterns in PyProcessor

This document explains the regex patterns used in PyProcessor profiles for file renaming, validation, and folder organization, and how they relate to the configuration flags.

## Flag-Pattern Relationships

The PyProcessor configuration includes several flags that control whether certain patterns are applied:

| Flag                    | Pattern                       | Description                                                                                                                                                         |
| ----------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `auto_rename_files`     | `file_rename_pattern`         | When `auto_rename_files` is set to `true`, the `file_rename_pattern` is used to extract parts of filenames for renaming before processing.                          |
| `auto_organize_folders` | `folder_organization_pattern` | When `auto_organize_folders` is set to `true`, the `folder_organization_pattern` is used to organize output folders into a hierarchical structure after processing. |

The `file_validation_pattern` is always used to validate files before processing, regardless of the flag settings.

## File Rename Pattern

The `file_rename_pattern` is used to extract a specific part of a filename for renaming purposes. It's designed to capture a pattern like "123-456" from various filename formats.

Current pattern: `(\\d+-\\d+)(?:[_-].*?)?\\.mp4$`

### Explanation:

- `(\\d+-\\d+)` - Captures one or more digits, followed by a hyphen, followed by one or more digits. This is the main capture group that will be used as the new filename.
- `(?:[_-].*?)?` - Optional non-capturing group that matches either an underscore or hyphen followed by any characters (non-greedy). This allows for filenames with additional content after the digit pattern.
- `\\.mp4$` - Matches the file extension ".mp4" at the end of the string.

### Examples:

- `123-456.mp4` → Captures "123-456"
- `video-123-456.mp4` → Captures "123-456"
- `prefix_123-456_suffix.mp4` → Captures "123-456"
- `123-456_720p.mp4` → Captures "123-456"
- `movie_123-456_1080p.mp4` → Captures "123-456"
- `tv_show_123-456_season01.mp4` → Captures "123-456"
- `123-456-extra.mp4` → Captures "123-456"

## File Validation Pattern

The `file_validation_pattern` is used to validate filenames before processing. Files that don't match this pattern are considered invalid.

Current pattern: `^\\d+-\\d+\\.mp4$`

### Explanation:

- `^` - Matches the start of the string.
- `\\d+-\\d+` - Matches one or more digits, followed by a hyphen, followed by one or more digits.
- `\\.mp4$` - Matches the file extension ".mp4" at the end of the string.

This pattern ensures that files are named in the format "123-456.mp4" before processing.

## Folder Organization Pattern

The `folder_organization_pattern` is used to organize folders after processing. It extracts a part of the folder name to use as the parent folder name.

Current pattern: `^(\\d+)-\\d+`

### Explanation:

- `^` - Matches the start of the string.
- `(\\d+)` - Captures one or more digits. This is the main capture group that will be used as the parent folder name.
- `-\\d+` - Matches a hyphen followed by one or more digits.

This pattern extracts the first number group from a folder name like "123-456" to use as the parent folder name (e.g., "123").

## Notes for Maintenance

- The double backslashes (`\\`) are necessary for JSON string escaping. In actual regex, these would be single backslashes.
- The patterns are designed to work together: files are renamed according to `file_rename_pattern`, validated according to `file_validation_pattern`, and organized according to `folder_organization_pattern`.
- When modifying these patterns, be sure to test them thoroughly with various filename formats to ensure they work as expected.
- Consider the impact on existing files and folders when changing these patterns.
