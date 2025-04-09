# FFmpeg Integration

This document explains how the Video Processor application integrates with FFmpeg for video encoding and provides guidance on extending or customizing the FFmpeg functionality.

## Overview

The Video Processor uses FFmpeg as its core engine for video encoding and processing. FFmpeg is a powerful, open-source tool for handling multimedia data, capable of encoding, decoding, transcoding, muxing, demuxing, streaming, filtering, and playing various formats.

## FFmpeg Requirements

- FFmpeg must be installed on the system and available in the PATH
- Minimum recommended version: FFmpeg 4.0 or higher
- For hardware acceleration, appropriate drivers must be installed

## FFmpeg Wrapper

The application interacts with FFmpeg through a wrapper class (`FFmpegEncoder`) that:

1. Constructs FFmpeg commands based on user configuration
2. Executes FFmpeg processes
3. Monitors progress and captures output
4. Handles errors and exceptions

## Key Features

### Supported Encoders

The application supports multiple video encoders:

- **libx265**: High-efficiency video coding (HEVC) software encoder
- **h264_nvenc**: NVIDIA GPU-accelerated H.264 encoder
- **libx264**: Standard H.264 software encoder

### Encoding Presets

For software encoders (libx265, libx264), the application supports various presets:

- **ultrafast**: Fastest encoding, largest file size
- **veryfast**: Fast encoding with reasonable compression
- **medium**: Balanced encoding speed and compression

### Tune Options

For software encoders, tune options optimize encoding for specific content types:

- **zerolatency**: Minimizes latency
- **film**: Optimized for film content
- **animation**: Optimized for animated content

### HLS Packaging

The application creates HTTP Live Streaming (HLS) packages with:

- Multiple quality levels (1080p, 720p, 480p, 360p)
- Adaptive bitrates
- Master playlist
- Segment files

## Implementation Details

### Command Construction

The `build_command` method in the `FFmpegEncoder` class constructs the FFmpeg command:

```python
def build_command(self, input_file, output_folder):
    """Build FFmpeg command for HLS encoding with audio option"""
    # Check for audio streams and respect the include_audio setting
    has_audio = self.has_audio(input_file) and self.config.ffmpeg_params.get("include_audio", True)
    
    # Calculate buffer sizes
    bitrates = self.config.ffmpeg_params["bitrates"]
    bufsizes = {}
    for res, bitrate in bitrates.items():
        bufsize_value = int(bitrate.rstrip('k')) * 2
        bufsizes[res] = f"{bufsize_value}k"
    
    # Build filter complex string
    filter_complex = "[0:v]split=4[v1][v2][v3][v4];[v1]scale=1920:1080[v1out];[v2]scale=1280:720[v2out];[v3]scale=854:480[v3out];[v4]scale=640:360[v4out]"
    
    # Build FFmpeg command
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "info", "-stats", 
           "-i", str(input_file), "-filter_complex", filter_complex]
    
    # Add video and audio mapping
    # ...
```

### Process Execution

The `encode_video` method executes the FFmpeg process:

```python
def encode_video(self, input_file, output_folder):
    """Encode a video file to HLS format"""
    try:
        # Create output directory structure
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)
        
        # Build command
        cmd = self.build_command(input_file, output_folder)
        self.logger.debug(f"Executing: {' '.join(cmd)}")
        
        # Execute FFmpeg
        self.process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            universal_newlines=True
        )
        
        # Process stdout and stderr
        stdout, stderr = self.process.communicate()
        
        # Check for errors
        if self.process.returncode != 0:
            error_message = stderr.strip()
            self.logger.error(f"FFmpeg error encoding {input_file.name}: {error_message}")
            return False
        
        # Verify output
        # ...
```

## Customizing FFmpeg Options

### Adding a New Encoder

To add support for a new encoder:

1. Update the `valid_encoders` list in the `Config.validate` method:
   ```python
   valid_encoders = ["libx265", "h264_nvenc", "libx264", "new_encoder"]
   ```

2. Modify the `build_command` method in `FFmpegEncoder` to handle the new encoder's specific options

3. Update the GUI in `config_dialog.py` to include the new encoder option

### Modifying Bitrates

To change the default bitrates:

1. Update the bitrate dictionary in the `Config.__init__` method:
   ```python
   self.ffmpeg_params = {
       # ...
       "bitrates": {
           "1080p": "11000k",
           "720p": "6500k",
           "480p": "4000k",
           "360p": "1500k"
       },
       # ...
   }
   ```

2. Consider adding GUI controls to allow users to customize bitrates

### Adding New Output Formats

To support additional output formats beyond HLS:

1. Add a format selection option to the configuration
2. Implement a new method in `FFmpegEncoder` for the new format
3. Modify the `encode_video` method to call the appropriate format-specific method

Example for adding DASH support:
```python
def build_dash_command(self, input_file, output_folder):
    """Build FFmpeg command for DASH encoding"""
    # Implementation
    
def encode_video(self, input_file, output_folder):
    """Encode a video file to the selected format"""
    if self.config.ffmpeg_params.get("format") == "dash":
        cmd = self.build_dash_command(input_file, output_folder)
    else:  # Default to HLS
        cmd = self.build_command(input_file, output_folder)
    # Continue with execution
```

## Troubleshooting FFmpeg Issues

### Common Problems

1. **FFmpeg Not Found**:
   - Ensure FFmpeg is installed and in the system PATH
   - The application checks for FFmpeg availability with `check_ffmpeg()`

2. **Encoding Errors**:
   - Check FFmpeg error output in the logs
   - Verify input file is valid and not corrupted
   - Ensure sufficient disk space for output

3. **Performance Issues**:
   - For slow encoding, consider using hardware acceleration if available
   - Adjust preset settings (faster presets sacrifice quality for speed)
   - Reduce the number of parallel jobs if system resources are limited

### Debugging FFmpeg Commands

To debug FFmpeg commands:

1. Set the logger level to DEBUG to see the full FFmpeg command:
   ```python
   logger.set_level(logging.DEBUG)
   ```

2. Copy the command from the logs and run it manually to see detailed output

3. Use FFmpeg's own debugging options for more information:
   ```
   ffmpeg -v debug -i input.mp4 ...
   ```

## Advanced FFmpeg Usage

### Hardware Acceleration

The application supports NVIDIA hardware acceleration through h264_nvenc. To use other hardware acceleration methods:

1. Add the encoder to the valid encoders list
2. Implement the necessary command-line options in `build_command`
3. Update the GUI to include the new option

### Custom Filters

To add custom FFmpeg filters:

1. Modify the filter_complex string in `build_command`
2. Add configuration options for the new filters
3. Update the GUI to allow users to configure the filters

### Progress Monitoring

The application currently monitors FFmpeg progress through process output. To implement more detailed progress monitoring:

1. Parse the FFmpeg stats output to extract frame count and time information
2. Calculate progress percentage based on duration and current time
3. Update the progress callback with more granular information

## Resources

- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [FFmpeg Wiki](https://trac.ffmpeg.org/wiki)
- [FFmpeg Filters Documentation](https://ffmpeg.org/ffmpeg-filters.html)
- [HLS Specification](https://tools.ietf.org/html/rfc8216)
