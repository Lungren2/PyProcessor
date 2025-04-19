# Notification System in PyProcessor

This document describes the notification system in PyProcessor, including the centralized `NotificationManager` class, notification types, and notification channels.

## Overview

PyProcessor provides a centralized notification system through the `NotificationManager` class in the `pyprocessor.utils.notification_manager` module. This class provides a consistent interface for managing notifications across the application.

The notification system is designed to:

- Provide a consistent way to display notifications to users
- Support different types of notifications (info, success, warning, error)
- Support different notification channels (in-app, system)
- Track notification history
- Allow for notification callbacks

## NotificationManager

The `NotificationManager` class is a singleton that provides the following features:

- In-app notification management
- System notification delivery
- Notification history
- Notification callbacks

### Getting the Notification Manager

```python
from pyprocessor.utils.notification_manager import get_notification_manager

# Get the notification manager
notification_manager = get_notification_manager()
```

## Notification Types

The notification system supports different types of notifications:

- `NotificationType.INFO`: Informational notifications
- `NotificationType.SUCCESS`: Success notifications
- `NotificationType.WARNING`: Warning notifications
- `NotificationType.ERROR`: Error notifications

## Notification Priorities

Notifications can have different priority levels:

- `NotificationPriority.LOW`: Low priority
- `NotificationPriority.NORMAL`: Normal priority
- `NotificationPriority.HIGH`: High priority
- `NotificationPriority.URGENT`: Urgent priority

## Notification Channels

Notifications can be delivered through different channels:

- `NotificationChannel.IN_APP`: In-app notifications
- `NotificationChannel.SYSTEM`: System notifications

## Basic Notification Operations

### Adding Notifications

```python
from pyprocessor.utils.notification_manager import (
    add_notification,
    NotificationType,
    NotificationPriority,
    NotificationChannel
)

# Add a simple in-app notification
notification_id = add_notification("This is a simple notification")

# Add a success notification
notification_id = add_notification(
    "Operation completed successfully",
    notification_type=NotificationType.SUCCESS
)

# Add a high-priority warning notification
notification_id = add_notification(
    "Disk space is running low",
    notification_type=NotificationType.WARNING,
    priority=NotificationPriority.HIGH
)

# Add a system notification
notification_id = add_notification(
    "Download completed",
    notification_type=NotificationType.SUCCESS,
    channel=NotificationChannel.SYSTEM
)

# Add a notification with additional data
notification_id = add_notification(
    "File processed",
    data={"file_path": "/path/to/file.mp4", "duration": 120}
)

# Add a notification with actions
notification_id = add_notification(
    "New update available",
    actions=[
        {"id": "update", "label": "Update Now"},
        {"id": "later", "label": "Remind Me Later"}
    ]
)

# Add a notification with expiration
notification_id = add_notification(
    "This notification will expire in 60 seconds",
    expiration=60
)
```

### Getting Notifications

```python
from pyprocessor.utils.notification_manager import (
    get_notification,
    get_all_notifications,
    NotificationType,
    NotificationChannel
)

# Get a specific notification
notification = get_notification(notification_id)
if notification:
    print(f"Notification: {notification.message}")

# Get all unread notifications
notifications = get_all_notifications()

# Get all notifications including read ones
notifications = get_all_notifications(include_read=True)

# Get all error notifications
notifications = get_all_notifications(
    notification_type=NotificationType.ERROR
)

# Get all system notifications
notifications = get_all_notifications(
    channel=NotificationChannel.SYSTEM
)

# Get all high-priority notifications
notifications = get_all_notifications(
    priority=NotificationPriority.HIGH
)

# Get all notifications from the last hour
notifications = get_all_notifications(
    max_age=3600  # 1 hour in seconds
)
```

### Managing Notifications

```python
from pyprocessor.utils.notification_manager import (
    mark_as_read,
    dismiss,
    clear_all,
    NotificationType,
    NotificationChannel
)

# Mark a notification as read
mark_as_read(notification_id)

# Dismiss a notification
dismiss(notification_id)

# Clear all notifications
clear_all()

# Clear all error notifications
clear_all(notification_type=NotificationType.ERROR)

# Clear all in-app notifications
clear_all(channel=NotificationChannel.IN_APP)

# Clear all notifications older than 24 hours
clear_all(older_than=86400)  # 24 hours in seconds
```

## Notification Callbacks

You can register callbacks to be notified when new notifications are added:

```python
from pyprocessor.utils.notification_manager import (
    register_callback,
    unregister_callback,
    NotificationChannel,
    Notification
)

# Define a callback function
def notification_callback(notification: Notification):
    print(f"New notification: {notification.message}")

# Register the callback for in-app notifications
register_callback(notification_callback, NotificationChannel.IN_APP)

# Register the callback for system notifications
register_callback(notification_callback, NotificationChannel.SYSTEM)

# Unregister the callback
unregister_callback(notification_callback, NotificationChannel.IN_APP)
```

## System Notifications

The notification system can send system notifications on different platforms:

- **Windows**: Uses the `win10toast` library to send toast notifications
- **macOS**: Uses `osascript` to send notifications
- **Linux**: Uses `notify-send` to send notifications

```python
from pyprocessor.utils.notification_manager import (
    add_notification,
    NotificationType,
    NotificationChannel
)

# Send a system notification
add_notification(
    "Download completed",
    notification_type=NotificationType.SUCCESS,
    channel=NotificationChannel.SYSTEM,
    title="PyProcessor"
)
```

## Integration with UI

To integrate the notification system with a UI, you can register callbacks to update the UI when notifications are added:

```python
from pyprocessor.utils.notification_manager import (
    register_callback,
    NotificationChannel,
    Notification
)

class NotificationUI:
    def __init__(self):
        # Register callback for in-app notifications
        register_callback(self.update_ui, NotificationChannel.IN_APP)
        
    def update_ui(self, notification: Notification):
        # Update the UI with the new notification
        # This will depend on your UI framework
        pass
```

## Best Practices

1. **Use Appropriate Types**: Use the appropriate notification type (info, success, warning, error) for each notification.
2. **Set Appropriate Priorities**: Use the appropriate priority level for each notification.
3. **Use In-App Notifications for Most Cases**: Use in-app notifications for most cases, and system notifications only for important events.
4. **Set Expirations**: Set expiration times for notifications that are only relevant for a short time.
5. **Include Relevant Data**: Include relevant data in notifications to provide context.
6. **Add Actions When Appropriate**: Add actions to notifications when the user can take action.
7. **Clear Old Notifications**: Regularly clear old notifications to avoid clutter.
8. **Handle Callbacks Safely**: Handle exceptions in notification callbacks to avoid crashing the application.
9. **Use Async Delivery**: Use async delivery for notifications to avoid blocking the main thread.
10. **Shutdown Properly**: Call `shutdown_notifications()` when shutting down the application to clean up resources.

## Example: Notification Center

Here's an example of implementing a simple notification center using the notification system:

```python
from pyprocessor.utils.notification_manager import (
    get_all_notifications,
    mark_as_read,
    dismiss,
    clear_all,
    register_callback,
    Notification,
    NotificationChannel
)

class NotificationCenter:
    def __init__(self):
        # Register callback for new notifications
        register_callback(self.on_new_notification, NotificationChannel.IN_APP)
        
    def on_new_notification(self, notification: Notification):
        # Handle new notification
        print(f"New notification: {notification.message}")
        
    def get_unread_count(self):
        # Get count of unread notifications
        return len(get_all_notifications())
        
    def get_notifications(self, include_read=False):
        # Get all notifications
        return get_all_notifications(include_read=include_read)
        
    def mark_all_as_read(self):
        # Mark all notifications as read
        for notification in get_all_notifications():
            mark_as_read(notification.id)
            
    def dismiss_all(self):
        # Dismiss all notifications
        for notification in get_all_notifications(include_read=True):
            dismiss(notification.id)
            
    def clear_old_notifications(self, hours=24):
        # Clear notifications older than the specified hours
        clear_all(older_than=hours * 3600)
```

## Troubleshooting

If you encounter issues with the notification system, try the following:

1. **Check System Requirements**: Make sure your system meets the requirements for system notifications.
2. **Check Dependencies**: Make sure you have the required dependencies installed for system notifications.
3. **Check Permissions**: Make sure your application has the required permissions to send system notifications.
4. **Check Callbacks**: Make sure your notification callbacks are not throwing exceptions.
5. **Check Notification Queue**: Make sure the notification queue is not full.
6. **Check Worker Thread**: Make sure the notification worker thread is running.
7. **Check Logs**: Look for error messages in the application logs.
8. **Restart the Application**: Try restarting the application.
9. **Reinstall Dependencies**: Try reinstalling the required dependencies.
10. **Update the Application**: Make sure you are using the latest version of the application.
