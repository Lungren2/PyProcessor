# PyProcessor User Guide

This guide provides instructions for using the PyProcessor library and CLI tool for video processing and HLS encoding.

## Installation

### Using the Installer

1. Download the latest PyProcessorInstaller.exe from the releases page
2. Run the installer and follow the on-screen instructions
3. Launch PyProcessor from the command line

### From Source

If you prefer to run from source:

```bash
git clone https://github.com/Lungren2/PyProcessor.git
cd PyProcessor
pip install -e .
python -m pyprocessor
```

## Getting Started

### Command Line Interface

PyProcessor is primarily used through the command line interface:

```bash
pyprocessor --input /path/to/input --output /path/to/output [options]
```

### Basic Workflow

1. **Specify Input**: Provide the input directory containing video files
2. **Specify Output**: Provide the output directory for processed files
3. **Configure Settings**: Set encoding options via command line arguments or a profile
4. **Start Processing**: Run the command to begin processing
5. **Monitor Progress**: Watch the progress indicators in the console

## Configuration Options

### Video Encoding

- **Encoder**: Choose between libx265, h264_nvenc, or libx264
- **Preset**: Select an encoding speed preset (ultrafast, veryfast, medium, etc.)
- **Tune**: Optimize for specific content types (film, animation, etc.)
- **FPS**: Set the frames per second for output videos

### HLS Packaging

- **Quality Levels**: Configure multiple quality levels for adaptive streaming
- **Segment Duration**: Set the duration of HLS segments
- **Playlist Type**: Choose between VOD or EVENT playlist types

### Advanced Settings

- **Parallel Processing**: Set the number of files to process simultaneously
- **File Organization**: Configure automatic file organization options
- **Custom Patterns**: Set custom regex patterns for file processing

## File Processing and Pattern Usage

PyProcessor uses regular expression patterns to handle file naming and organization. These patterns are controlled by configuration flags that determine when they are applied.

### Auto Rename Files

When the `auto_rename_files` option is enabled, input files are renamed according to the `file_rename_pattern` before processing.

- **Flag**: `auto_rename_files` (true/false)
- **Pattern**: `file_rename_pattern`
- **Example**: With the default pattern `(\d+-\d+)(?:[_-].*?)?\.mp4$`, a file named `video-123-456.mp4` or `123-456_720p.mp4` will be renamed to `123-456.mp4`

### Auto Organize Folders

When the `auto_organize_folders` option is enabled, output folders are organized according to the `folder_organization_pattern` after processing.

- **Flag**: `auto_organize_folders` (true/false)
- **Pattern**: `folder_organization_pattern`
- **Example**: With the default pattern `^(\d+)-\d+`, a folder named `123-456` will be moved into a parent folder named `123`, creating a structure like `123/123-456`

### File Validation

All files are validated against the `file_validation_pattern` before processing. Files that don't match this pattern are considered invalid and will be skipped.

- **Pattern**: `file_validation_pattern`
- **Example**: With the default pattern `^\d+-\d+\.mp4$`, only files named like `123-456.mp4` will be processed

You can customize these patterns in the configuration file or via command line arguments to match your specific naming conventions.

## Using Profiles

Profiles allow you to save and reuse configurations for different encoding scenarios.

### Using a Profile

```bash
pyprocessor --profile high_quality --input /path/to/input --output /path/to/output
```

### Available Profiles

The following profiles are included by default:

- `default`: Standard encoding settings
- `high_quality`: High quality encoding settings
- `fast`: Fast encoding with lower quality

## Server Optimization

PyProcessor includes tools to optimize your web server for HLS content delivery.

### Optimizing IIS Server

```bash
pyprocessor optimize-server --server-type iis --site-name "Default Web Site" --video-path "C:\inetpub\wwwroot\media"
```

### Optimizing Nginx Server

```bash
pyprocessor optimize-server --server-type nginx --server-name "example.com" --output-path "/etc/nginx/sites-available/media.conf"
```

## Troubleshooting

### Common Issues

1. **FFmpeg Not Found**: Ensure FFmpeg is installed and available in your system PATH
2. **Permission Errors**: Make sure the application has write permissions for the output directory
3. **Encoding Errors**: Check the logs for detailed error messages

### Viewing Logs

You can examine the log files in the `pyprocessor/logs/` directory or use the log command:

```bash
pyprocessor logs --level error --last 50
```

## Getting Help

If you encounter issues not covered in this guide, please:

1. Check the [GitHub Issues](https://github.com/Lungren2/PyProcessor/issues) for similar problems
2. Create a new issue with detailed information about your problem
3. Include log files and steps to reproduce the issue
