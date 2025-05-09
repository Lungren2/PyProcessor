"""
Example script demonstrating how to use the notification system.

This script shows how to create and manage notifications of different types and channels.
"""

import os
import sys
import time
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
    Notification,
)


def print_notification(notification):
    """Print a notification."""
    print(
        f"[{notification.notification_type.value.upper()}] {notification.title}: {notification.message}"
    )
    if notification.data:
        print(f"  Data: {notification.data}")
    if notification.actions:
        print(
            f"  Actions: {', '.join(action['label'] for action in notification.actions)}"
        )
    print(
        f"  Created: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(notification.created_at))}"
    )
    print(
        f"  Status: {'Read' if notification.read else 'Unread'}, {'Dismissed' if notification.dismissed else 'Active'}"
    )
    print()


def notification_callback(notification):
    """Callback function for notifications."""
    print(f"Callback received notification: {notification.message}")


def main():
    """Main function demonstrating notification usage."""
    print("Notification System Example")
    print("==========================")

    # Register a callback for in-app notifications
    print("\n1. Registering notification callback")
    register_callback(notification_callback, NotificationChannel.IN_APP)

    # Add a simple notification
    print("\n2. Adding a simple notification")
    notification_id = add_notification(
        "This is a simple notification",
        async_delivery=False,  # For demonstration purposes
    )
    print(f"Added notification with ID: {notification_id}")

    # Get the notification
    notification = get_notification(notification_id)
    print_notification(notification)

    # Add notifications of different types
    print("\n3. Adding notifications of different types")

    info_id = add_notification(
        "This is an informational message",
        notification_type=NotificationType.INFO,
        async_delivery=False,
    )

    success_id = add_notification(
        "Operation completed successfully",
        notification_type=NotificationType.SUCCESS,
        async_delivery=False,
    )

    warning_id = add_notification(
        "Disk space is running low",
        notification_type=NotificationType.WARNING,
        async_delivery=False,
    )

    error_id = add_notification(
        "An error occurred during processing",
        notification_type=NotificationType.ERROR,
        async_delivery=False,
    )

    # Get all notifications
    print("\n4. Getting all notifications")
    notifications = get_all_notifications()
    print(f"Found {len(notifications)} notifications:")
    for notification in notifications:
        print_notification(notification)

    # Add notifications with different priorities
    print("\n5. Adding notifications with different priorities")

    low_id = add_notification(
        "Low priority notification",
        priority=NotificationPriority.LOW,
        async_delivery=False,
    )

    normal_id = add_notification(
        "Normal priority notification",
        priority=NotificationPriority.NORMAL,
        async_delivery=False,
    )

    high_id = add_notification(
        "High priority notification",
        priority=NotificationPriority.HIGH,
        async_delivery=False,
    )

    urgent_id = add_notification(
        "Urgent priority notification",
        priority=NotificationPriority.URGENT,
        async_delivery=False,
    )

    # Get notifications sorted by priority
    print("\n6. Getting notifications sorted by priority")
    notifications = get_all_notifications()
    print(f"Found {len(notifications)} notifications (sorted by priority):")
    for notification in notifications:
        print_notification(notification)

    # Add a notification with additional data
    print("\n7. Adding a notification with additional data")
    data_id = add_notification(
        "File processed successfully",
        notification_type=NotificationType.SUCCESS,
        data={"file_path": "/path/to/file.mp4", "duration": 120, "size": "1.2 GB"},
        async_delivery=False,
    )

    # Get the notification with data
    notification = get_notification(data_id)
    print_notification(notification)

    # Add a notification with actions
    print("\n8. Adding a notification with actions")
    actions_id = add_notification(
        "New update available",
        notification_type=NotificationType.INFO,
        actions=[
            {"id": "update", "label": "Update Now"},
            {"id": "later", "label": "Remind Me Later"},
            {"id": "ignore", "label": "Ignore"},
        ],
        async_delivery=False,
    )

    # Get the notification with actions
    notification = get_notification(actions_id)
    print_notification(notification)

    # Mark a notification as read
    print("\n9. Marking a notification as read")
    mark_as_read(info_id)
    print(f"Marked notification {info_id} as read")

    # Get the notification after marking as read
    notification = get_notification(info_id)
    print_notification(notification)

    # Dismiss a notification
    print("\n10. Dismissing a notification")
    dismiss(warning_id)
    print(f"Dismissed notification {warning_id}")

    # Get the notification after dismissing
    notification = get_notification(warning_id)
    print_notification(notification)

    # Get unread notifications
    print("\n11. Getting unread notifications")
    unread = get_all_notifications(include_read=False)
    print(f"Found {len(unread)} unread notifications:")
    for notification in unread:
        print_notification(notification)

    # Get all notifications including read and dismissed
    print("\n12. Getting all notifications including read and dismissed")
    all_notifications = get_all_notifications(include_read=True, include_dismissed=True)
    print(
        f"Found {len(all_notifications)} notifications (including read and dismissed):"
    )
    for notification in all_notifications:
        print_notification(notification)

    # Add a notification with expiration
    print("\n13. Adding a notification with expiration")
    expiring_id = add_notification(
        "This notification will expire in 5 seconds", expiration=5, async_delivery=False
    )

    # Get the notification before expiration
    notification = get_notification(expiring_id)
    print("Before expiration:")
    print_notification(notification)

    # Wait for expiration
    print("Waiting for expiration...")
    time.sleep(6)

    # Get the notification after expiration
    notification = get_notification(expiring_id)
    print("After expiration:")
    if notification:
        print_notification(notification)
    else:
        print("Notification has expired and is no longer available")

    # Clear all notifications
    print("\n14. Clearing all notifications")
    count = clear_all()
    print(f"Cleared {count} notifications")

    # Verify that all notifications are cleared
    notifications = get_all_notifications(include_read=True, include_dismissed=True)
    print(f"Remaining notifications: {len(notifications)}")

    # Try to send a system notification
    print("\n15. Sending a system notification")
    try:
        system_id = add_notification(
            "This is a system notification",
            notification_type=NotificationType.INFO,
            channel=NotificationChannel.SYSTEM,
            title="PyProcessor Example",
            async_delivery=False,
        )
        print(f"Sent system notification with ID: {system_id}")
    except Exception as e:
        print(f"Error sending system notification: {str(e)}")

    # Unregister the callback
    print("\n16. Unregistering notification callback")
    unregister_callback(notification_callback, NotificationChannel.IN_APP)

    # Add a notification after unregistering callback
    print("\n17. Adding a notification after unregistering callback")
    final_id = add_notification(
        "This notification should not trigger the callback", async_delivery=False
    )
    print(f"Added notification with ID: {final_id}")

    # Shutdown the notification system
    print("\n18. Shutting down notification system")
    shutdown_notifications()

    print("\nNotification example completed")


if __name__ == "__main__":
    main()
