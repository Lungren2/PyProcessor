# PyProcessor API Reference

This document provides a reference for the PyProcessor API, which can be used to integrate video processing functionality into your own applications.

## Core Modules

### pyprocessor.processing.encoder

The encoder module provides a wrapper around FFmpeg for video encoding operations.

#### Classes

##### `FFmpegEncoder`

Main encoder class that handles video encoding operations.

```python
from pyprocessor.processing.encoder import FFmpegEncoder

encoder = FFmpegEncoder(
    input_path="input.mp4",
    output_path="output.mp4",
    encoder="libx264",
    preset="medium",
    tune="film",
    fps=30,
    include_audio=True
)

# Start encoding
encoder.encode()

# Get progress
progress = encoder.get_progress()

# Stop encoding
encoder.stop()
```

##### `HLSEncoder`

Specialized encoder for HLS packaging.

```python
from pyprocessor.processing.encoder import HLSEncoder

encoder = HLSEncoder(
    input_path="input.mp4",
    output_path="output",
    quality_levels=[
        {"resolution": "1920x1080", "bitrate": "5000k"},
        {"resolution": "1280x720", "bitrate": "3000k"},
        {"resolution": "854x480", "bitrate": "1500k"},
        {"resolution": "640x360", "bitrate": "800k"}
    ],
    segment_duration=6,
    playlist_type="vod"
)

# Start encoding
encoder.encode()
```

### pyprocessor.processing.scheduler

The scheduler module handles parallel processing of multiple files.

#### Classes

##### `ProcessingScheduler`

Manages parallel processing of multiple files.

```python
from pyprocessor.processing.scheduler import ProcessingScheduler

scheduler = ProcessingScheduler(
    input_dir="input_directory",
    output_dir="output_directory",
    max_workers=4,
    encoder_settings={
        "encoder": "libx264",
        "preset": "medium",
        "tune": "film",
        "fps": 30,
        "include_audio": True
    }
)

# Start processing
scheduler.start()

# Get overall progress
progress = scheduler.get_progress()

# Stop processing
scheduler.stop()
```

### pyprocessor.utils.config

The config module handles configuration management.

#### Classes

##### `ConfigManager`

Manages application configuration.

```python
from pyprocessor.utils.config import ConfigManager

# Load configuration
config = ConfigManager()
config.load()

# Get a configuration value
encoder = config.get("encoder", "libx264")  # Default to libx264

# Set a configuration value
config.set("encoder", "libx265")

# Save configuration
config.save()

# Load a profile
config.load_profile("high_quality")

# Save a profile
config.save_profile("high_quality")
```

### pyprocessor.utils.logging

The logging module provides logging functionality.

#### Functions

##### `setup_logger`

Sets up the application logger.

```python
from pyprocessor.utils.logging import setup_logger

logger = setup_logger(
    name="my_logger",
    log_file="my_log.log",
    level="INFO"
)

logger.info("This is an info message")
logger.error("This is an error message")
```

### pyprocessor.utils.server_optimizer

The server_optimizer module provides server optimization functionality.

#### Classes

##### `ServerOptimizer`

Base class for server optimization.

##### `IISOptimizer`

Optimizes IIS servers for HLS content delivery.

```python
from pyprocessor.utils.server_optimizer import IISOptimizer

optimizer = IISOptimizer(
    site_name="MyVideoSite",
    video_path="C:\\inetpub\\wwwroot\\videos",
    enable_http2=True,
    enable_http3=True,
    enable_cors=True,
    cors_origin="*"
)

optimizer.optimize()
```

##### `NginxOptimizer`

Optimizes Nginx servers for HLS content delivery.

```python
from pyprocessor.utils.server_optimizer import NginxOptimizer

optimizer = NginxOptimizer(
    server_name="example.com",
    output_config="/etc/nginx/sites-available/hls",
    enable_http2=True,
    enable_http3=True,
    enable_cors=True,
    cors_origin="*"
)

optimizer.optimize()
```

## Command Line Interface

PyProcessor provides a command-line interface for automation and scripting.

```bash
python -m pyprocessor --no-gui [options]
```

Available command-line options:

```text
--input PATH         Input directory path
--output PATH        Output directory path
--config PATH        Configuration file path
--profile NAME       Configuration profile name
--encoder NAME       Video encoder (libx265, h264_nvenc, libx264)
--preset NAME        Encoding preset (ultrafast, veryfast, medium, etc.)
--tune NAME          Encoding tune (zerolatency, film, animation, etc.)
--fps NUMBER         Frames per second
--no-audio           Disable audio in output
--jobs NUMBER        Number of parallel encoding jobs
--no-gui             Run without GUI
--verbose            Enable verbose logging

# Server Optimization Options
--optimize-server    Server type to optimize (iis, nginx, linux)
--site-name          IIS site name (for IIS optimization)
--video-path         Path to video content directory (for IIS)
--enable-http2       Enable HTTP/2 protocol (for IIS)
--enable-http3       Enable HTTP/3 with Alt-Svc headers (for IIS or Nginx)
--enable-cors        Enable CORS headers (for IIS)
--cors-origin        CORS origin value (for IIS)
--output-config      Output path for server configuration (for Nginx)
--server-name        Server name for configuration (for Nginx)
--apply-changes      Apply changes directly (for Linux)
```
