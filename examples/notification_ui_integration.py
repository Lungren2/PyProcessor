"""
Example script demonstrating how to integrate the notification system with a UI.

This script shows how to create a simple notification center using the notification system.
"""

import os
import sys
import time
import threading
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyprocessor.utils.core.notification_manager import (
    add_notification,
    get_notification,
    get_all_notifications,
    mark_as_read,
    dismiss,
    clear_all,
    register_callback,
    unregister_callback,
    shutdown_notifications,
    NotificationType,
    NotificationPriority,
    NotificationChannel,
    Notification
)


class NotificationCenter:
    """A simple notification center."""

    def __init__(self):
        """Initialize the notification center."""
        # Register callback for new notifications
        register_callback(self.on_new_notification, NotificationChannel.IN_APP)

        # Initialize notification list
        self.notifications = []

        # Initialize notification count
        self.unread_count = 0

        # Update notifications
        self.update_notifications()

    def on_new_notification(self, notification):
        """
        Handle new notification.

        Args:
            notification: The new notification
        """
        print(f"New notification received: {notification.message}")

        # Update notifications
        self.update_notifications()

        # Display notification
        self.display_notification(notification)

    def update_notifications(self):
        """Update the notification list."""
        # Get all notifications
        self.notifications = get_all_notifications(include_read=True)

        # Update unread count
        self.unread_count = len([n for n in self.notifications if not n.read])

        # Update UI
        self.update_ui()

    def update_ui(self):
        """Update the UI with the current notifications."""
        print("\n=== Notification Center ===")
        print(f"Unread notifications: {self.unread_count}")
        print(f"Total notifications: {len(self.notifications)}")
        print("===========================\n")

    def display_notification(self, notification):
        """
        Display a notification.

        Args:
            notification: The notification to display
        """
        # Get icon based on notification type
        icon = self._get_icon(notification.notification_type)

        # Print notification
        print(f"\n{icon} {notification.title}")
        print(f"{notification.message}")
        if notification.data:
            print(f"Data: {notification.data}")
        if notification.actions:
            print("Actions:")
            for action in notification.actions:
                print(f"- {action['label']}")
        print()

    def _get_icon(self, notification_type):
        """
        Get an icon for a notification type.

        Args:
            notification_type: The notification type

        Returns:
            str: Icon for the notification type
        """
        if notification_type == NotificationType.INFO:
            return "ℹ️"
        elif notification_type == NotificationType.SUCCESS:
            return "✅"
        elif notification_type == NotificationType.WARNING:
            return "⚠️"
        elif notification_type == NotificationType.ERROR:
            return "❌"
        else:
            return "📢"

    def mark_all_as_read(self):
        """Mark all notifications as read."""
        for notification in self.notifications:
            if not notification.read:
                mark_as_read(notification.id)

        # Update notifications
        self.update_notifications()

    def dismiss_all(self):
        """Dismiss all notifications."""
        for notification in self.notifications:
            if not notification.dismissed:
                dismiss(notification.id)

        # Update notifications
        self.update_notifications()

    def clear_old_notifications(self, hours=24):
        """
        Clear notifications older than the specified hours.

        Args:
            hours: Number of hours
        """
        # Clear old notifications
        count = clear_all(older_than=hours * 3600)
        print(f"Cleared {count} old notifications")

        # Update notifications
        self.update_notifications()

    def shutdown(self):
        """Shutdown the notification center."""
        # Unregister callback
        unregister_callback(self.on_new_notification, NotificationChannel.IN_APP)


def generate_notifications():
    """Generate some sample notifications."""
    # Add info notification
    add_notification(
        "Welcome to PyProcessor",
        notification_type=NotificationType.INFO,
        title="Welcome",
        data={"version": "1.0.0"}
    )

    # Wait a bit
    time.sleep(1)

    # Add success notification
    add_notification(
        "Your file has been processed successfully",
        notification_type=NotificationType.SUCCESS,
        title="Processing Complete",
        data={"file": "video.mp4", "duration": "00:05:30"}
    )

    # Wait a bit
    time.sleep(1)

    # Add warning notification
    add_notification(
        "Your disk space is running low",
        notification_type=NotificationType.WARNING,
        title="Low Disk Space",
        data={"free_space": "1.2 GB", "threshold": "2.0 GB"}
    )

    # Wait a bit
    time.sleep(1)

    # Add error notification
    add_notification(
        "Failed to process file due to invalid format",
        notification_type=NotificationType.ERROR,
        title="Processing Error",
        data={"file": "invalid.xyz", "error": "Unsupported format"}
    )

    # Wait a bit
    time.sleep(1)

    # Add notification with actions
    add_notification(
        "A new version of PyProcessor is available",
        notification_type=NotificationType.INFO,
        title="Update Available",
        data={"current_version": "1.0.0", "new_version": "1.1.0"},
        actions=[
            {"id": "update", "label": "Update Now"},
            {"id": "later", "label": "Remind Me Later"},
            {"id": "ignore", "label": "Ignore"}
        ]
    )


def main():
    """Main function demonstrating notification UI integration."""
    print("Notification UI Integration Example")
    print("==================================")

    # Create notification center
    notification_center = NotificationCenter()

    # Generate notifications in a separate thread
    threading.Thread(target=generate_notifications, daemon=True).start()

    # Wait for notifications to be generated
    time.sleep(6)

    # Display menu
    while True:
        print("\nMenu:")
        print("1. Show all notifications")
        print("2. Mark all as read")
        print("3. Dismiss all notifications")
        print("4. Clear old notifications")
        print("5. Add a new notification")
        print("6. Exit")

        choice = input("Enter your choice (1-6): ")

        if choice == "1":
            # Show all notifications
            print("\nAll Notifications:")
            for notification in notification_center.notifications:
                notification_center.display_notification(notification)

        elif choice == "2":
            # Mark all as read
            notification_center.mark_all_as_read()
            print("All notifications marked as read")

        elif choice == "3":
            # Dismiss all notifications
            notification_center.dismiss_all()
            print("All notifications dismissed")

        elif choice == "4":
            # Clear old notifications
            hours = input("Enter hours (default 24): ")
            try:
                hours = int(hours) if hours else 24
                notification_center.clear_old_notifications(hours)
            except ValueError:
                print("Invalid input, using default 24 hours")
                notification_center.clear_old_notifications(24)

        elif choice == "5":
            # Add a new notification
            message = input("Enter notification message: ")
            if message:
                add_notification(message)
                print("Notification added")
            else:
                print("Message cannot be empty")

        elif choice == "6":
            # Exit
            break

        else:
            print("Invalid choice, please try again")

    # Shutdown notification center
    notification_center.shutdown()

    # Shutdown notification system
    shutdown_notifications()

    print("\nNotification UI integration example completed")


if __name__ == "__main__":
    main()
