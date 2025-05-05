"""
Example script demonstrating how to use the resource management system.

This script shows how to monitor system resources, set thresholds, and handle resource events.
"""

import os
import sys
import time
import threading
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyprocessor.utils.process.resource_manager import (
    start_monitoring,
    stop_monitoring,
    get_cpu_usage,
    get_memory_usage,
    get_disk_usage,
    get_system_info,
    track_process,
    untrack_process,
    set_resource_limits,
    set_thresholds,
    register_callback,
    unregister_callback,
    get_usage_history,
    get_stats,
    reset_stats,
    shutdown_resource_manager,
    ResourceType,
    ResourceState,
    ResourceUsage,
)


def print_resource_usage(resource_usage):
    """Print resource usage information."""
    print(f"Resource: {resource_usage.resource_type.value}")
    print(f"Utilization: {resource_usage.utilization:.2%}")
    print(f"Available: {format_bytes(resource_usage.available)}")
    print(f"Total: {format_bytes(resource_usage.total)}")
    print(f"State: {resource_usage.state.value}")
    print(
        f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(resource_usage.timestamp))}"
    )

    if resource_usage.details:
        print("Details:")
        for key, value in resource_usage.details.items():
            if key in [
                "used",
                "free",
                "cached",
                "buffers",
                "read_bytes",
                "write_bytes",
            ]:
                print(f"  {key}: {format_bytes(value) if value is not None else 'N/A'}")
            else:
                print(f"  {key}: {value}")
    print()


def format_bytes(bytes_value):
    """Format bytes value to human-readable format."""
    if bytes_value is None:
        return "N/A"

    # Convert to bytes if not already
    bytes_value = float(bytes_value)

    # Define units and thresholds
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    threshold = 1024.0

    # Find the appropriate unit
    unit_index = 0
    while bytes_value >= threshold and unit_index < len(units) - 1:
        bytes_value /= threshold
        unit_index += 1

    # Format the value
    return f"{bytes_value:.2f} {units[unit_index]}"


def warning_callback(resource_usage):
    """Callback function for warning resource state."""
    print(
        f"WARNING: {resource_usage.resource_type.value} usage at {resource_usage.utilization:.2%}"
    )


def critical_callback(resource_usage):
    """Callback function for critical resource state."""
    print(
        f"CRITICAL: {resource_usage.resource_type.value} usage at {resource_usage.utilization:.2%}"
    )


def simulate_cpu_load(duration=5):
    """Simulate CPU load for a specified duration."""
    print(f"Simulating CPU load for {duration} seconds...")
    start_time = time.time()
    while time.time() - start_time < duration:
        # Perform CPU-intensive operations
        for _ in range(1000000):
            _ = 1 + 1


def simulate_memory_load(size_mb=100, duration=5):
    """Simulate memory load for a specified duration."""
    print(f"Simulating memory load of {size_mb} MB for {duration} seconds...")
    # Allocate memory
    data = bytearray(size_mb * 1024 * 1024)
    # Hold for duration
    time.sleep(duration)
    # Release memory
    del data


def main():
    """Main function demonstrating resource management."""
    print("Resource Management Example")
    print("==========================")

    # Get system information
    print("\n1. System Information")
    system_info = get_system_info()
    print(
        f"Platform: {system_info.get('platform', 'Unknown')} {system_info.get('platform_release', '')}"
    )
    print(f"Version: {system_info.get('platform_version', 'Unknown')}")
    print(f"Architecture: {system_info.get('architecture', 'Unknown')}")
    print(f"Processor: {system_info.get('processor', 'Unknown')}")
    print(f"CPU Count: {system_info.get('cpu_count', 'Unknown')}")
    print(f"Physical CPU Count: {system_info.get('physical_cpu_count', 'Unknown')}")
    print(f"Total Memory: {format_bytes(system_info.get('memory_total', 0))}")
    print(f"Hostname: {system_info.get('hostname', 'Unknown')}")
    print(f"Python Version: {system_info.get('python_version', 'Unknown')}")
    print(
        f"Boot Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(system_info.get('boot_time', 0)))}"
    )

    # Start resource monitoring
    print("\n2. Starting Resource Monitoring")
    start_monitoring(interval=1.0)
    print("Resource monitoring started with 1-second interval")

    # Get current resource usage
    print("\n3. Current Resource Usage")

    # CPU usage
    print("\nCPU Usage:")
    cpu_usage = get_cpu_usage()
    print_resource_usage(cpu_usage)

    # Memory usage
    print("Memory Usage:")
    memory_usage = get_memory_usage()
    print_resource_usage(memory_usage)

    # Disk usage
    print("Disk Usage:")
    disk_usage = get_disk_usage()
    print_resource_usage(disk_usage)

    # Set resource thresholds
    print("\n4. Setting Resource Thresholds")
    set_thresholds(ResourceType.CPU, warning=0.5, critical=0.8)
    set_thresholds(ResourceType.MEMORY, warning=0.6, critical=0.8)
    set_thresholds(ResourceType.DISK, warning=0.7, critical=0.9)
    print("Resource thresholds set")

    # Register callbacks
    print("\n5. Registering Resource Callbacks")
    register_callback(warning_callback, ResourceState.WARNING)
    register_callback(critical_callback, ResourceState.CRITICAL)
    print("Resource callbacks registered")

    # Track current process
    print("\n6. Tracking Current Process")
    current_pid = os.getpid()
    track_process(current_pid)
    print(f"Tracking process {current_pid}")

    # Set resource limits
    print("\n7. Setting Resource Limits")
    set_resource_limits(cpu_limit=80.0, memory_limit=1024 * 1024 * 1024)
    print("Resource limits set")

    # Simulate CPU load
    print("\n8. Simulating CPU Load")
    simulate_cpu_load(duration=5)

    # Simulate memory load
    print("\n9. Simulating Memory Load")
    simulate_memory_load(size_mb=100, duration=5)

    # Get resource usage history
    print("\n10. Resource Usage History")
    cpu_history = get_usage_history(ResourceType.CPU, count=5)
    print(f"CPU History (last {len(cpu_history)} entries):")
    for i, usage in enumerate(cpu_history):
        print(
            f"Entry {i+1}: {usage.utilization:.2%} at {time.strftime('%H:%M:%S', time.localtime(usage.timestamp))}"
        )

    # Get resource statistics
    print("\n11. Resource Statistics")
    stats = get_stats()
    print(f"CPU Peak: {stats.get('cpu_peak', 0):.2%}")
    print(f"Memory Peak: {stats.get('memory_peak', 0):.2%}")
    print(f"Disk Peak: {stats.get('disk_peak', 0):.2%}")
    print(f"Warning Events: {stats.get('warning_events', 0)}")
    print(f"Critical Events: {stats.get('critical_events', 0)}")

    # Reset statistics
    print("\n12. Resetting Statistics")
    reset_stats()
    print("Statistics reset")

    # Untrack process
    print("\n13. Untracking Process")
    untrack_process(current_pid)
    print(f"Untracked process {current_pid}")

    # Unregister callbacks
    print("\n14. Unregistering Callbacks")
    unregister_callback(warning_callback, ResourceState.WARNING)
    unregister_callback(critical_callback, ResourceState.CRITICAL)
    print("Callbacks unregistered")

    # Stop monitoring
    print("\n15. Stopping Resource Monitoring")
    stop_monitoring()
    print("Resource monitoring stopped")

    # Shutdown resource manager
    print("\n16. Shutting Down Resource Manager")
    shutdown_resource_manager()
    print("Resource manager shutdown")

    print("\nResource management example completed")


if __name__ == "__main__":
    main()
