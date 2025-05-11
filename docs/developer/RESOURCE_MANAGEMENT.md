# Resource Management in PyProcessor

This document describes the resource management system in PyProcessor, including the centralized `ResourceManager` class, resource monitoring, and resource limits.

## Overview

PyProcessor provides a centralized resource management system through the `ResourceManager` class in the `pyprocessor.utils.resource_manager` module. This class provides a consistent interface for monitoring and managing system resources across the application.

The resource management system is designed to:

- Monitor system resource usage (CPU, memory, disk)
- Set resource usage thresholds and limits
- Track resource usage of specific processes
- Provide resource usage history and statistics
- Notify when resource usage exceeds thresholds

## ResourceManager

The `ResourceManager` class is a singleton that provides the following features:

- Resource usage monitoring
- Resource allocation and limits
- Resource usage statistics
- Resource usage callbacks

### Getting the Resource Manager

```python
from pyprocessor.utils.resource_manager import get_resource_manager

# Get the resource manager
resource_manager = get_resource_manager()
```

## Resource Types

The resource management system supports different types of resources:

- `ResourceType.CPU`: CPU resources
- `ResourceType.MEMORY`: Memory resources
- `ResourceType.DISK`: Disk resources

## Resource States

Resources can be in different states based on their utilization:

- `ResourceState.NORMAL`: Normal utilization
- `ResourceState.WARNING`: Warning level utilization
- `ResourceState.CRITICAL`: Critical level utilization

## Basic Resource Operations

### Monitoring Resources

```python
from pyprocessor.utils.resource_manager import start_monitoring, stop_monitoring

# Start resource monitoring with a 5-second interval
start_monitoring(interval=5.0)

# Stop resource monitoring
stop_monitoring()
```

### Getting Resource Usage

```python
from pyprocessor.utils.resource_manager import (
    get_cpu_usage,
    get_memory_usage,
    get_disk_usage
)

# Get CPU usage
cpu_usage = get_cpu_usage()
print(f"CPU utilization: {cpu_usage.utilization:.2%}")
print(f"CPU state: {cpu_usage.state.value}")

# Get memory usage
memory_usage = get_memory_usage()
print(f"Memory utilization: {memory_usage.utilization:.2%}")
print(f"Available memory: {memory_usage.available / (1024 * 1024):.2f} MB")
print(f"Total memory: {memory_usage.total / (1024 * 1024):.2f} MB")

# Get disk usage
disk_usage = get_disk_usage()
print(f"Disk utilization: {disk_usage.utilization:.2%}")
print(f"Available disk space: {disk_usage.available / (1024 * 1024 * 1024):.2f} GB")
print(f"Total disk space: {disk_usage.total / (1024 * 1024 * 1024):.2f} GB")

# Get disk usage for a specific path
disk_usage = get_disk_usage("/path/to/directory")
```

### Getting System Information

```python
from pyprocessor.utils.resource_manager import get_system_info

# Get system information
system_info = get_system_info()
print(f"Platform: {system_info['platform']} {system_info['platform_release']}")
print(f"CPU: {system_info['processor']}")
print(f"CPU count: {system_info['cpu_count']}")
print(f"Memory: {system_info['memory_total'] / (1024 * 1024 * 1024):.2f} GB")
```

## Resource Thresholds and Limits

### Setting Resource Thresholds

```python
from pyprocessor.utils.resource_manager import set_thresholds, ResourceType

# Set CPU thresholds
set_thresholds(ResourceType.CPU, warning=0.7, critical=0.9)  # 70% and 90%

# Set memory thresholds
set_thresholds(ResourceType.MEMORY, warning=0.8, critical=0.95)  # 80% and 95%

# Set disk thresholds
set_thresholds(ResourceType.DISK, warning=0.85, critical=0.95)  # 85% and 95%
```

### Setting Resource Limits

```python
from pyprocessor.utils.resource_manager import set_resource_limits

# Set CPU limit to 50%
set_resource_limits(cpu_limit=50.0)

# Set memory limit to 1 GB
set_resource_limits(memory_limit=1024 * 1024 * 1024)

# Set disk limit to 10 GB
set_resource_limits(disk_limit=10 * 1024 * 1024 * 1024)

# Set multiple limits
set_resource_limits(
    cpu_limit=50.0,
    memory_limit=1024 * 1024 * 1024,
    disk_limit=10 * 1024 * 1024 * 1024
)
```

## Process Tracking

```python
from pyprocessor.utils.resource_manager import track_process, untrack_process
import os

# Track the current process
current_pid = os.getpid()
track_process(current_pid)

# Track another process
track_process(12345)

# Stop tracking a process
untrack_process(12345)
```

## Resource Callbacks

You can register callbacks to be notified when resource usage exceeds thresholds:

```python
from pyprocessor.utils.resource_manager import (
    register_callback,
    unregister_callback,
    ResourceState,
    ResourceUsage
)

# Define callback functions
def warning_callback(resource_usage: ResourceUsage):
    print(f"WARNING: {resource_usage.resource_type.value} usage at {resource_usage.utilization:.2%}")

def critical_callback(resource_usage: ResourceUsage):
    print(f"CRITICAL: {resource_usage.resource_type.value} usage at {resource_usage.utilization:.2%}")

# Register callbacks
register_callback(warning_callback, ResourceState.WARNING)
register_callback(critical_callback, ResourceState.CRITICAL)

# Unregister callbacks
unregister_callback(warning_callback, ResourceState.WARNING)
```

## Resource History and Statistics

### Getting Resource Usage History

```python
from pyprocessor.utils.resource_manager import get_usage_history, ResourceType

# Get CPU usage history
cpu_history = get_usage_history(ResourceType.CPU)
for usage in cpu_history:
    print(f"CPU: {usage.utilization:.2%} at {usage.timestamp}")

# Get the last 10 memory usage entries
memory_history = get_usage_history(ResourceType.MEMORY, count=10)
```

### Getting Resource Statistics

```python
from pyprocessor.utils.resource_manager import get_stats, reset_stats

# Get resource statistics
stats = get_stats()
print(f"CPU peak: {stats['cpu_peak']:.2%}")
print(f"Memory peak: {stats['memory_peak']:.2%}")
print(f"Disk peak: {stats['disk_peak']:.2%}")
print(f"Warning events: {stats['warning_events']}")
print(f"Critical events: {stats['critical_events']}")

# Reset statistics
reset_stats()
```

## Integration with Application

### Resource Monitoring in Application Context

```python
from pyprocessor.utils.resource_manager import (
    start_monitoring,
    stop_monitoring,
    register_callback,
    ResourceState,
    ResourceUsage
)
from pyprocessor.utils.notification_manager import add_notification, NotificationType

class Application:
    def __init__(self):
        # Start resource monitoring
        start_monitoring(interval=10.0)
        
        # Register resource callbacks
        register_callback(self.on_resource_warning, ResourceState.WARNING)
        register_callback(self.on_resource_critical, ResourceState.CRITICAL)
        
    def on_resource_warning(self, resource_usage: ResourceUsage):
        # Add a notification for warning
        add_notification(
            f"{resource_usage.resource_type.value.upper()} usage at {resource_usage.utilization:.2%}",
            notification_type=NotificationType.WARNING
        )
        
    def on_resource_critical(self, resource_usage: ResourceUsage):
        # Add a notification for critical
        add_notification(
            f"{resource_usage.resource_type.value.upper()} usage at {resource_usage.utilization:.2%}",
            notification_type=NotificationType.ERROR
        )
        
        # Take action based on resource type
        if resource_usage.resource_type == ResourceType.MEMORY:
            # Free up memory
            self.free_memory()
        
    def free_memory(self):
        # Implementation to free up memory
        pass
        
    def shutdown(self):
        # Stop resource monitoring
        stop_monitoring()
```

## Best Practices

1. **Start Monitoring Early**: Start resource monitoring early in the application lifecycle.
2. **Set Appropriate Thresholds**: Set appropriate thresholds based on your application's requirements.
3. **Use Callbacks for Critical Events**: Register callbacks for critical resource events to take immediate action.
4. **Track Important Processes**: Track important processes to monitor their resource usage.
5. **Check Resource Usage Before Heavy Operations**: Check resource usage before starting heavy operations.
6. **Free Resources When Not Needed**: Free up resources when they are no longer needed.
7. **Monitor Resource Trends**: Monitor resource usage trends to identify potential issues.
8. **Adjust Resource Limits Based on System**: Adjust resource limits based on the system's capabilities.
9. **Handle Resource Exhaustion Gracefully**: Handle resource exhaustion gracefully to prevent crashes.
10. **Shutdown Resource Manager Properly**: Call `shutdown_resource_manager()` when shutting down the application.

## Example: Resource Monitor

Here's an example of implementing a simple resource monitor using the resource management system:

```python
from pyprocessor.utils.resource_manager import (
    start_monitoring,
    stop_monitoring,
    get_cpu_usage,
    get_memory_usage,
    get_disk_usage,
    get_usage_history,
    ResourceType
)
import time
import matplotlib.pyplot as plt

class ResourceMonitor:
    def __init__(self):
        # Start resource monitoring
        start_monitoring(interval=1.0)
        
    def print_current_usage(self):
        # Get current resource usage
        cpu_usage = get_cpu_usage()
        memory_usage = get_memory_usage()
        disk_usage = get_disk_usage()
        
        # Print resource usage
        print(f"CPU: {cpu_usage.utilization:.2%} ({cpu_usage.state.value})")
        print(f"Memory: {memory_usage.utilization:.2%} ({memory_usage.state.value})")
        print(f"Disk: {disk_usage.utilization:.2%} ({disk_usage.state.value})")
        
    def plot_usage_history(self):
        # Get resource usage history
        cpu_history = get_usage_history(ResourceType.CPU)
        memory_history = get_usage_history(ResourceType.MEMORY)
        
        # Extract timestamps and utilization
        timestamps = [usage.timestamp for usage in cpu_history]
        cpu_utilization = [usage.utilization for usage in cpu_history]
        memory_utilization = [usage.utilization for usage in memory_history]
        
        # Plot resource usage
        plt.figure(figsize=(10, 6))
        plt.plot(timestamps, cpu_utilization, label="CPU")
        plt.plot(timestamps, memory_utilization, label="Memory")
        plt.xlabel("Time")
        plt.ylabel("Utilization")
        plt.title("Resource Usage History")
        plt.legend()
        plt.grid(True)
        plt.show()
        
    def run(self, duration=60):
        # Run for the specified duration
        start_time = time.time()
        while time.time() - start_time < duration:
            self.print_current_usage()
            time.sleep(5)
            
        # Plot usage history
        self.plot_usage_history()
        
    def shutdown(self):
        # Stop resource monitoring
        stop_monitoring()

# Usage
monitor = ResourceMonitor()
try:
    monitor.run(duration=60)
finally:
    monitor.shutdown()
```

## Troubleshooting

If you encounter issues with the resource management system, try the following:

1. **Check Dependencies**: Make sure you have the required dependencies installed (psutil).
2. **Check Permissions**: Make sure your application has the required permissions to access system resources.
3. **Check Monitoring Interval**: Adjust the monitoring interval to reduce overhead.
4. **Check Thresholds**: Make sure your thresholds are appropriate for your system.
5. **Check Callbacks**: Make sure your resource callbacks are not throwing exceptions.
6. **Check Process Tracking**: Make sure the processes you are tracking exist.
7. **Check Resource Limits**: Make sure your resource limits are appropriate for your system.
8. **Check System Load**: Check if your system is under heavy load from other applications.
9. **Restart Monitoring**: Try stopping and starting resource monitoring.
10. **Update Dependencies**: Make sure you are using the latest version of psutil.
