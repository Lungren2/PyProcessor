"""
Example application demonstrating how to integrate the resource management system with an application.

This script shows how to create a resource monitor application that displays resource usage
and takes actions based on resource states.
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
    set_thresholds,
    register_callback,
    get_usage_history,
    get_stats,
    shutdown_resource_manager,
    ResourceType,
    ResourceState,
    ResourceUsage,
)
from pyprocessor.utils.core.notification_manager import (
    add_notification,
    NotificationType,
    NotificationPriority,
    NotificationChannel,
)


class ResourceMonitorApp:
    """A simple resource monitor application."""

    def __init__(self):
        """Initialize the resource monitor application."""
        # Initialize system info
        self.system_info = get_system_info()

        # Initialize resource history
        self.cpu_history = []
        self.memory_history = []
        self.disk_history = []

        # Initialize resource thresholds
        set_thresholds(ResourceType.CPU, warning=0.7, critical=0.9)
        set_thresholds(ResourceType.MEMORY, warning=0.7, critical=0.9)
        set_thresholds(ResourceType.DISK, warning=0.8, critical=0.95)

        # Register resource callbacks
        register_callback(self.on_resource_warning, ResourceState.WARNING)
        register_callback(self.on_resource_critical, ResourceState.CRITICAL)

        # Track current process
        self.pid = os.getpid()
        track_process(self.pid)

        # Start resource monitoring
        start_monitoring(interval=2.0)

        # Initialize running flag
        self.running = True

        # Start update thread
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()

    def on_resource_warning(self, resource_usage: ResourceUsage):
        """
        Handle warning resource state.

        Args:
            resource_usage: Resource usage information
        """
        # Add a notification
        add_notification(
            f"{resource_usage.resource_type.value.upper()} usage at {resource_usage.utilization:.2%}",
            notification_type=NotificationType.WARNING,
            priority=NotificationPriority.HIGH,
            channel=NotificationChannel.IN_APP,
            title=f"{resource_usage.resource_type.value.capitalize()} Warning",
            data={
                "utilization": resource_usage.utilization,
                "available": resource_usage.available,
                "total": resource_usage.total,
            },
        )

        # Log the warning
        print(
            f"WARNING: {resource_usage.resource_type.value} usage at {resource_usage.utilization:.2%}"
        )

        # Take action based on resource type
        if resource_usage.resource_type == ResourceType.MEMORY:
            # Suggest memory optimization
            print("Memory optimization suggested")

    def on_resource_critical(self, resource_usage: ResourceUsage):
        """
        Handle critical resource state.

        Args:
            resource_usage: Resource usage information
        """
        # Add a notification
        add_notification(
            f"{resource_usage.resource_type.value.upper()} usage at {resource_usage.utilization:.2%}",
            notification_type=NotificationType.ERROR,
            priority=NotificationPriority.URGENT,
            channel=NotificationChannel.SYSTEM,
            title=f"{resource_usage.resource_type.value.capitalize()} Critical",
            data={
                "utilization": resource_usage.utilization,
                "available": resource_usage.available,
                "total": resource_usage.total,
            },
        )

        # Log the critical state
        print(
            f"CRITICAL: {resource_usage.resource_type.value} usage at {resource_usage.utilization:.2%}"
        )

        # Take action based on resource type
        if resource_usage.resource_type == ResourceType.MEMORY:
            # Perform memory cleanup
            self.cleanup_memory()
        elif resource_usage.resource_type == ResourceType.CPU:
            # Throttle CPU-intensive tasks
            self.throttle_cpu_tasks()

    def cleanup_memory(self):
        """Perform memory cleanup."""
        print("Performing memory cleanup...")
        # In a real application, this would free up memory
        # For example, clearing caches, releasing unused resources, etc.

        # Simulate memory cleanup
        import gc

        gc.collect()
        print("Memory cleanup completed")

    def throttle_cpu_tasks(self):
        """Throttle CPU-intensive tasks."""
        print("Throttling CPU-intensive tasks...")
        # In a real application, this would throttle CPU-intensive tasks
        # For example, reducing thread count, lowering process priority, etc.
        print("CPU throttling completed")

    def _update_loop(self):
        """Update loop for resource monitoring."""
        while self.running:
            try:
                # Get current resource usage
                cpu_usage = get_cpu_usage()
                memory_usage = get_memory_usage()
                disk_usage = get_disk_usage()

                # Update history
                self.cpu_history.append(cpu_usage)
                if len(self.cpu_history) > 30:
                    self.cpu_history.pop(0)

                self.memory_history.append(memory_usage)
                if len(self.memory_history) > 30:
                    self.memory_history.pop(0)

                self.disk_history.append(disk_usage)
                if len(self.disk_history) > 30:
                    self.disk_history.pop(0)

                # Update display
                self._update_display()

                # Sleep for a bit
                time.sleep(2.0)

            except Exception as e:
                print(f"Error in update loop: {str(e)}")
                time.sleep(1.0)

    def _update_display(self):
        """Update the display with current resource usage."""
        # Clear the screen
        os.system("cls" if os.name == "nt" else "clear")

        # Print header
        print("=== Resource Monitor ===")
        print(
            f"System: {self.system_info.get('platform', 'Unknown')} {self.system_info.get('platform_release', '')}"
        )
        print(
            f"CPU: {self.system_info.get('processor', 'Unknown')} ({self.system_info.get('cpu_count', 0)} cores)"
        )
        print(f"Memory: {self._format_bytes(self.system_info.get('memory_total', 0))}")
        print("========================")

        # Print current resource usage
        if self.cpu_history:
            cpu_usage = self.cpu_history[-1]
            print(f"\nCPU Usage: {cpu_usage.utilization:.2%} ({cpu_usage.state.value})")
            self._print_bar(cpu_usage.utilization)

        if self.memory_history:
            memory_usage = self.memory_history[-1]
            print(
                f"\nMemory Usage: {memory_usage.utilization:.2%} ({memory_usage.state.value})"
            )
            self._print_bar(memory_usage.utilization)
            print(
                f"Available: {self._format_bytes(memory_usage.available)} / {self._format_bytes(memory_usage.total)}"
            )

        if self.disk_history:
            disk_usage = self.disk_history[-1]
            print(
                f"\nDisk Usage: {disk_usage.utilization:.2%} ({disk_usage.state.value})"
            )
            self._print_bar(disk_usage.utilization)
            print(
                f"Available: {self._format_bytes(disk_usage.available)} / {self._format_bytes(disk_usage.total)}"
            )

        # Print resource statistics
        stats = get_stats()
        print("\nResource Statistics:")
        print(f"CPU Peak: {stats.get('cpu_peak', 0):.2%}")
        print(f"Memory Peak: {stats.get('memory_peak', 0):.2%}")
        print(f"Disk Peak: {stats.get('disk_peak', 0):.2%}")
        print(f"Warning Events: {stats.get('warning_events', 0)}")
        print(f"Critical Events: {stats.get('critical_events', 0)}")

        # Print instructions
        print("\nPress Ctrl+C to exit")

    def _print_bar(self, value, width=50):
        """
        Print a progress bar.

        Args:
            value: Value between 0 and 1
            width: Width of the bar
        """
        filled_width = int(value * width)
        empty_width = width - filled_width

        # Determine color based on value
        if value >= 0.9:
            color = "\033[91m"  # Red
        elif value >= 0.7:
            color = "\033[93m"  # Yellow
        else:
            color = "\033[92m"  # Green

        reset = "\033[0m"  # Reset color

        # Print the bar
        print(f"{color}[{'#' * filled_width}{' ' * empty_width}]{reset}")

    def _format_bytes(self, bytes_value):
        """
        Format bytes value to human-readable format.

        Args:
            bytes_value: Bytes value

        Returns:
            str: Formatted bytes value
        """
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

    def simulate_load(self):
        """Simulate system load."""
        print("Simulating system load...")

        # Simulate CPU load
        cpu_thread = threading.Thread(target=self._simulate_cpu_load, daemon=True)
        cpu_thread.start()

        # Simulate memory load
        memory_thread = threading.Thread(target=self._simulate_memory_load, daemon=True)
        memory_thread.start()

    def _simulate_cpu_load(self, duration=10):
        """
        Simulate CPU load.

        Args:
            duration: Duration in seconds
        """
        print(f"Simulating CPU load for {duration} seconds...")
        start_time = time.time()
        while time.time() - start_time < duration:
            # Perform CPU-intensive operations
            for _ in range(10000000):
                _ = 1 + 1

    def _simulate_memory_load(self, size_mb=500, duration=10):
        """
        Simulate memory load.

        Args:
            size_mb: Size in MB
            duration: Duration in seconds
        """
        print(f"Simulating memory load of {size_mb} MB for {duration} seconds...")
        # Allocate memory
        data = bytearray(size_mb * 1024 * 1024)
        # Hold for duration
        time.sleep(duration)
        # Release memory
        del data

    def shutdown(self):
        """Shutdown the resource monitor application."""
        print("Shutting down resource monitor...")
        self.running = False

        if self.update_thread.is_alive():
            self.update_thread.join(timeout=2.0)

        # Stop resource monitoring
        stop_monitoring()

        # Shutdown resource manager
        shutdown_resource_manager()

        print("Resource monitor shutdown completed")


def main():
    """Main function."""
    print("Resource Monitor Application")
    print("===========================")

    # Create resource monitor
    monitor = ResourceMonitorApp()

    try:
        # Run for a while
        time.sleep(5)

        # Simulate load
        monitor.simulate_load()

        # Run until interrupted
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        # Shutdown monitor
        monitor.shutdown()


if __name__ == "__main__":
    main()
