# PyProcessor User Guide

This guide provides instructions for using the PyProcessor application for video processing and HLS encoding.

## Installation

### Using the Installer

1. Download the latest PyProcessorInstaller.exe from the releases page
2. Run the installer and follow the on-screen instructions
3. Launch PyProcessor from the Start menu or desktop shortcut

### From Source

If you prefer to run from source:

```bash
git clone https://github.com/Lungren2/PyProcessor.git
cd PyProcessor
pip install -e .
python -m pyprocessor
```

## Getting Started

### Main Interface

When you launch PyProcessor, you'll see the main interface with the following components:

- Input path selection
- Output path selection
- Encoding settings tabs
- Progress indicators
- Start/Stop buttons

### Basic Workflow

1. **Select Input**: Click the "Browse" button next to the input field to select a directory containing video files
2. **Select Output**: Click the "Browse" button next to the output field to select a directory for processed files
3. **Configure Settings**: Adjust encoding settings in the tabs as needed
4. **Start Processing**: Click the "Start" button to begin processing
5. **Monitor Progress**: Watch the progress indicators for real-time updates

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

You can customize these patterns in the Advanced Settings tab to match your specific naming conventions.

## Using Profiles

Profiles allow you to save and reuse configurations for different encoding scenarios.

### Saving a Profile

1. Configure your settings as desired
2. Click "Save Profile" in the File menu
3. Enter a name for the profile
4. Click "Save"

### Loading a Profile

1. Click "Load Profile" in the File menu
2. Select a profile from the list
3. Click "Load"

## Server Optimization

PyProcessor includes tools to optimize your web server for HLS content delivery.

### Optimizing IIS Server

1. Go to the "Server Optimization" tab
2. Select "IIS" as the server type
3. Enter your site name and video path
4. Select optimization options
5. Click "Optimize Server"

### Optimizing Nginx Server

1. Go to the "Server Optimization" tab
2. Select "Nginx" as the server type
3. Enter your server name and output configuration path
4. Select optimization options
5. Click "Optimize Server"

## Troubleshooting

### Common Issues

1. **FFmpeg Not Found**: Ensure FFmpeg is installed and available in your system PATH
2. **Permission Errors**: Make sure the application has write permissions for the output directory
3. **Encoding Errors**: Check the logs for detailed error messages

### Viewing Logs

You can view logs either through the GUI (Tools > View Logs) or by examining the log files in the `pyprocessor/logs/` directory.

## Getting Help

If you encounter issues not covered in this guide, please:

1. Check the [GitHub Issues](https://github.com/Lungren2/PyProcessor/issues) for similar problems
2. Create a new issue with detailed information about your problem
3. Include log files and steps to reproduce the issue
