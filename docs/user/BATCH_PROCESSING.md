# Batch Processing in PyProcessor

PyProcessor includes a sophisticated batch processing system that intelligently manages system resources while processing multiple video files. This document explains how batch processing works and how to configure it for optimal performance.

## Overview

Traditional video processing approaches often use one process per file, which can lead to excessive resource consumption when processing many files. PyProcessor's batch processing system addresses this by:

1. Grouping files into batches
2. Processing each batch in a separate process
3. Dynamically adjusting batch sizes based on system resources
4. Monitoring resource usage during processing

## Benefits of Batch Processing

- **Reduced Memory Usage**: Fewer processes means less overhead
- **Better Resource Utilization**: More efficient use of CPU, memory, and I/O
- **Improved Stability**: Less likely to overwhelm system resources
- **Scalability**: Handles large workloads (hundreds of files) efficiently

## How Batch Processing Works

1. **File Collection**: PyProcessor scans the input directory for valid video files
2. **Batch Creation**: Files are grouped into batches based on:
   - Available system resources (CPU, memory)
   - File sizes and count
   - Configuration settings
3. **Batch Processing**: Each batch is processed in a separate process
4. **Resource Monitoring**: System resources are monitored during processing
5. **Dynamic Adjustment**: Batch sizes are adjusted based on resource usage

## Configuration Options

### Command-Line Options

```bash
# Enable batch processing with automatic batch sizing
pyprocessor --input /path/to/videos --output /path/to/output --batch-mode enabled

# Specify a fixed batch size
pyprocessor --input /path/to/videos --output /path/to/output --batch-mode enabled --batch-size 10

# Limit memory usage for batch processing
pyprocessor --input /path/to/videos --output /path/to/output --batch-mode enabled --max-memory 70
```

### Configuration File Options

In your configuration file or profile:

```json
{
  "batch_processing": {
    "enabled": true,
    "batch_size": null,  // null for automatic sizing, or a number for fixed size
    "max_memory_percent": 80  // Maximum memory usage percentage
  }
}
```

## Automatic Batch Sizing

When `batch_size` is set to `null` (the default), PyProcessor will automatically determine the optimal batch size based on:

1. **Available CPU Cores**: More cores allow for larger batches
2. **Available Memory**: More memory allows for larger batches
3. **File Sizes**: Larger files result in smaller batches
4. **File Count**: More files result in smaller batches per process

The automatic sizing algorithm follows these steps:

1. Calculate available system resources
2. Estimate resource requirements per file
3. Determine the maximum number of files that can be processed simultaneously
4. Divide files into batches accordingly

## Manual Batch Sizing

If you prefer to set a fixed batch size, you can specify the `batch_size` parameter. This is useful when:

- You know the optimal batch size for your specific hardware
- You want consistent behavior across different runs
- You're processing files with similar characteristics

## Resource Monitoring

During processing, PyProcessor monitors:

- CPU usage
- Memory usage
- Disk I/O
- Process health

If resource usage exceeds configured thresholds (e.g., `max_memory_percent`), PyProcessor will:

1. Pause processing of new batches
2. Wait for current batches to complete
3. Reduce batch size for subsequent batches
4. Resume processing with the adjusted batch size

## Best Practices

- **Start with Automatic Sizing**: Let PyProcessor determine the optimal batch size for your system
- **Monitor Performance**: Check the logs to see how batch processing is performing
- **Adjust as Needed**: If you notice issues, adjust the `batch_size` or `max_memory_percent` parameters
- **Consider File Characteristics**: Larger files may benefit from smaller batch sizes
- **Balance with Parallel Jobs**: The `--jobs` parameter controls how many batches are processed in parallel

## Troubleshooting

### High Memory Usage

If you're experiencing high memory usage:

1. Reduce the `max_memory_percent` parameter (e.g., from 80% to 60%)
2. Set a fixed `batch_size` that's smaller than the automatic size
3. Reduce the number of parallel jobs with the `--jobs` parameter

### Slow Processing

If processing is slower than expected:

1. Increase the `batch_size` parameter
2. Increase the number of parallel jobs with the `--jobs` parameter
3. Check if disk I/O is the bottleneck (consider using an SSD)

### Process Crashes

If processes are crashing:

1. Reduce the `batch_size` parameter
2. Reduce the `max_memory_percent` parameter
3. Check the logs for specific error messages

## Advanced Configuration

For advanced users, additional configuration options are available in the `pyprocessor/processing/batch_processor.py` file. These include:

- Resource estimation parameters
- Throttling thresholds
- Monitoring intervals
- Error handling strategies

Consult the [API Reference](../api/API_REFERENCE.md) for detailed information about these options.
