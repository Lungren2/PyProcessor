"""
Notification utilities for PyProcessor.

This module provides a centralized way to manage notifications, including:
- In-app notifications
- System notifications
- Email notifications (planned)
- Webhook notifications (planned)
"""

import queue
import threading
import time
import uuid
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pyprocessor.utils.log_manager import get_logger


class NotificationType(Enum):
    """Types of notifications."""

    INFO = "info"
    SUCCESS = "success"  # Unused variable  # Unused variable
    WARNING = "warning"
    ERROR = "error"


class NotificationPriority(Enum):
    """Priority levels for notifications."""

    LOW = 0  # Unused variable  # Unused variable
    NORMAL = 1
    HIGH = 2  # Unused variable  # Unused variable
    URGENT = 3  # Unused variable  # Unused variable


class NotificationChannel(Enum):
    """Channels through which notifications can be delivered."""

    IN_APP = "in_app"
    SYSTEM = "system"
    # EMAIL = "email"  # Planned for future
    # WEBHOOK = "webhook"  # Planned for future


class Notification:
    """A notification with metadata."""

    def __init__(
        self,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        title: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        expiration: Optional[int] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Initialize a notification.

        Args:
            message: The notification message
            notification_type: Type of notification
            priority: Priority level
            channel: Delivery channel
            title: Optional title (defaults to type name if None)
            data: Optional additional data
            expiration: Optional expiration time in seconds
            actions: Optional list of actions that can be taken on the notification
        """
        self.id = str(uuid.uuid4())
        self.message = message
        self.notification_type = notification_type
        self.priority = priority
        self.channel = channel
        self.title = title or notification_type.name.capitalize()
        self.data = data or {}
        self.created_at = time.time()
        self.expiration = expiration
        self.actions = actions or []
        self.read = False
        self.dismissed = False

    def is_expired(self) -> bool:
        """
        Check if the notification is expired.

        Returns:
            bool: True if expired, False otherwise
        """
        if self.expiration is None:
            return False
        return (time.time() - self.created_at) > self.expiration

    def mark_as_read(self) -> None:
        """Mark the notification as read."""
        self.read = True

    def dismiss(self) -> None:
        """Dismiss the notification."""
        self.dismissed = True

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the notification to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the notification
        """
        return {
            "id": self.id,
            "message": self.message,
            "type": self.notification_type.value,
            "priority": self.priority.value,
            "channel": self.channel.value,
            "title": self.title,
            "data": self.data,
            "created_at": self.created_at,
            "expiration": self.expiration,
            "actions": self.actions,
            "read": self.read,
            "dismissed": self.dismissed,
        }


class NotificationManager:
    """
    Centralized manager for notification operations.

    This class provides:
    - In-app notification management
    - System notification delivery
    - Notification history
    - Notification callbacks
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(NotificationManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialize the notification manager."""
        # Only initialize once
        if getattr(self, "_initialized", False):
            return

        # Get logger
        self.logger = get_logger()

        # Initialize notification storage
        self._notifications: Dict[str, Notification] = {}

        # Initialize notification queue for async delivery
        self._notification_queue = queue.Queue()

        # Initialize callbacks
        self._callbacks: Dict[NotificationChannel, List[Callable]] = {
            channel: [] for channel in NotificationChannel
        }

        # Start notification worker thread
        self._stop_event = threading.Event()
        self._worker_thread = threading.Thread(
            target=self._notification_worker, daemon=True, name="NotificationWorker"
        )
        self._worker_thread.start()

        # Mark as initialized
        self._initialized = True
        self.logger.debug("Notification manager initialized")

    def _notification_worker(self) -> None:
        """Worker thread for processing notifications."""
        while not self._stop_event.is_set():
            try:
                # Get notification from queue with timeout
                notification = self._notification_queue.get(timeout=0.5)

                # Process the notification
                self._process_notification(notification)

                # Mark task as done
                self._notification_queue.task_done()

            except queue.Empty:
                # No notifications in queue, continue
                continue
            except Exception as e:
                self.logger.error(f"Error processing notification: {str(e)}")

    def _process_notification(self, notification: Notification) -> None:
        """
        Process a notification.

        Args:
            notification: The notification to process
        """
        # Store the notification
        self._notifications[notification.id] = notification

        # Call callbacks for the notification channel
        for callback in self._callbacks.get(notification.channel, []):
            try:
                callback(notification)
            except Exception as e:
                self.logger.error(f"Error in notification callback: {str(e)}")

        # Handle system notifications
        if notification.channel == NotificationChannel.SYSTEM:
            self._send_system_notification(notification)

    def _send_system_notification(self, notification: Notification) -> None:
        """
        Send a system notification.

        Args:
            notification: The notification to send
        """
        try:
            # Check platform and send appropriate system notification
            import platform

            system = platform.system()

            if system == "Windows":
                self._send_windows_notification(notification)
            elif system == "Darwin":  # macOS
                self._send_macos_notification(notification)
            elif system == "Linux":
                self._send_linux_notification(notification)
            else:
                self.logger.warning(f"System notifications not supported on {system}")

        except Exception as e:
            self.logger.error(f"Error sending system notification: {str(e)}")

    def _send_windows_notification(self, notification: Notification) -> None:
        """
        Send a Windows notification.

        Args:
            notification: The notification to send
        """
        try:
            # Try to use Windows 10 toast notifications
            from win10toast import ToastNotifier

            toaster = ToastNotifier()
            toaster.show_toast(
                notification.title, notification.message, duration=5, threaded=True
            )
        except ImportError:
            self.logger.warning(
                "win10toast not installed, cannot send Windows notification"
            )
        except Exception as e:
            self.logger.error(f"Error sending Windows notification: {str(e)}")

    def _send_macos_notification(self, notification: Notification) -> None:
        """
        Send a macOS notification.

        Args:
            notification: The notification to send
        """
        try:
            # Use osascript to send notification
            import subprocess

            script = f'display notification "{notification.message}" with title "{notification.title}"'
            subprocess.run(["osascript", "-e", script], check=True)

        except Exception as e:
            self.logger.error(f"Error sending macOS notification: {str(e)}")

    def _send_linux_notification(self, notification: Notification) -> None:
        """
        Send a Linux notification.

        Args:
            notification: The notification to send
        """
        try:
            # Try to use notify-send
            import subprocess

            subprocess.run(
                ["notify-send", notification.title, notification.message], check=True
            )

        except Exception as e:
            self.logger.error(f"Error sending Linux notification: {str(e)}")

    def add_notification(
        self,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        title: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        expiration: Optional[int] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
        async_delivery: bool = True,
    ) -> str:
        """
        Add a notification.

        Args:
            message: The notification message
            notification_type: Type of notification
            priority: Priority level
            channel: Delivery channel
            title: Optional title
            data: Optional additional data
            expiration: Optional expiration time in seconds
            actions: Optional list of actions
            async_delivery: Whether to deliver asynchronously

        Returns:
            str: Notification ID
        """
        # Create notification
        notification = Notification(
            message=message,
            notification_type=notification_type,
            priority=priority,
            channel=channel,
            title=title,
            data=data,
            expiration=expiration,
            actions=actions,
        )

        # Log the notification
        self.logger.debug(
            f"Added notification: {notification.id} - {notification.message}"
        )

        if async_delivery:
            # Add to queue for async processing
            self._notification_queue.put(notification)
        else:
            # Process immediately
            self._process_notification(notification)

        return notification.id

    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """
        Get a notification by ID.

        Args:
            notification_id: Notification ID

        Returns:
            Optional[Notification]: The notification or None if not found
        """
        notification = self._notifications.get(notification_id)

        # Check if expired
        if notification and notification.is_expired():
            return None

        return notification

    def get_all_notifications(
        self,
        include_read: bool = False,
        include_dismissed: bool = False,
        channel: Optional[NotificationChannel] = None,
        notification_type: Optional[NotificationType] = None,
        priority: Optional[NotificationPriority] = None,
        max_age: Optional[int] = None,
    ) -> List[Notification]:
        """
        Get all notifications matching the criteria.

        Args:
            include_read: Whether to include read notifications
            include_dismissed: Whether to include dismissed notifications
            channel: Filter by channel
            notification_type: Filter by type
            priority: Filter by priority
            max_age: Maximum age in seconds

        Returns:
            List[Notification]: List of matching notifications
        """
        result = []
        current_time = time.time()

        for notification in self._notifications.values():
            # Skip expired notifications
            if notification.is_expired():
                continue

            # Skip read notifications if not included
            if not include_read and notification.read:
                continue

            # Skip dismissed notifications if not included
            if not include_dismissed and notification.dismissed:
                continue

            # Filter by channel
            if channel is not None and notification.channel != channel:
                continue

            # Filter by type
            if (
                notification_type is not None
                and notification.notification_type != notification_type
            ):
                continue

            # Filter by priority
            if priority is not None and notification.priority != priority:
                continue

            # Filter by age
            if max_age is not None:
                age = current_time - notification.created_at
                if age > max_age:
                    continue

            result.append(notification)

        # Sort by priority (highest first) and then by creation time (newest first)
        result.sort(key=lambda n: (-n.priority.value, -n.created_at))

        return result

    def mark_as_read(self, notification_id: str) -> bool:
        """
        Mark a notification as read.

        Args:
            notification_id: Notification ID

        Returns:
            bool: True if successful, False otherwise
        """
        notification = self.get_notification(notification_id)
        if notification:
            notification.mark_as_read()
            return True
        return False

    def dismiss(self, notification_id: str) -> bool:
        """
        Dismiss a notification.

        Args:
            notification_id: Notification ID

        Returns:
            bool: True if successful, False otherwise
        """
        notification = self.get_notification(notification_id)
        if notification:
            notification.dismiss()
            return True
        return False

    def clear_all(
        self,
        channel: Optional[NotificationChannel] = None,
        notification_type: Optional[NotificationType] = None,
        older_than: Optional[int] = None,
    ) -> int:
        """
        Clear all notifications matching the criteria.

        Args:
            channel: Filter by channel
            notification_type: Filter by type
            older_than: Clear notifications older than this many seconds

        Returns:
            int: Number of notifications cleared
        """
        to_remove = []
        current_time = time.time()

        for notification_id, notification in self._notifications.items():
            # Filter by channel
            if channel is not None and notification.channel != channel:
                continue

            # Filter by type
            if (
                notification_type is not None
                and notification.notification_type != notification_type
            ):
                continue

            # Filter by age
            if older_than is not None:
                age = current_time - notification.created_at
                if age <= older_than:
                    continue

            to_remove.append(notification_id)

        # Remove the notifications
        for notification_id in to_remove:
            del self._notifications[notification_id]

        return len(to_remove)

    def register_callback(
        self,
        callback: Callable[[Notification], None],
        channel: NotificationChannel = NotificationChannel.IN_APP,
    ) -> None:
        """
        Register a callback for notifications.

        Args:
            callback: Callback function
            channel: Notification channel to register for
        """
        if channel not in self._callbacks:
            self._callbacks[channel] = []

        self._callbacks[channel].append(callback)
        self.logger.debug(f"Registered callback for {channel.value} notifications")

    def unregister_callback(
        self,
        callback: Callable[[Notification], None],
        channel: NotificationChannel = NotificationChannel.IN_APP,
    ) -> bool:
        """
        Unregister a callback for notifications.

        Args:
            callback: Callback function
            channel: Notification channel

        Returns:
            bool: True if successful, False otherwise
        """
        if channel not in self._callbacks:
            return False

        try:
            self._callbacks[channel].remove(callback)
            self.logger.debug(
                f"Unregistered callback for {channel.value} notifications"
            )
            return True
        except ValueError:
            return False

    def shutdown(self) -> None:
        """Shutdown the notification manager."""
        self._stop_event.set()
        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)
        self.logger.debug("Notification manager shutdown")


# Singleton instance
_notification_manager = None


def get_notification_manager() -> NotificationManager:
    """
    Get the singleton notification manager instance.

    Returns:
        NotificationManager: The singleton notification manager instance
    """
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


# Module-level functions for convenience


def add_notification(
    message: str,
    notification_type: NotificationType = NotificationType.INFO,
    priority: NotificationPriority = NotificationPriority.NORMAL,
    channel: NotificationChannel = NotificationChannel.IN_APP,
    title: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    expiration: Optional[int] = None,
    actions: Optional[List[Dict[str, Any]]] = None,
    async_delivery: bool = True,
) -> str:
    """
    Add a notification.

    Args:
        message: The notification message
        notification_type: Type of notification
        priority: Priority level
        channel: Delivery channel
        title: Optional title
        data: Optional additional data
        expiration: Optional expiration time in seconds
        actions: Optional list of actions
        async_delivery: Whether to deliver asynchronously

    Returns:
        str: Notification ID
    """
    return get_notification_manager().add_notification(
        message,
        notification_type,
        priority,
        channel,
        title,
        data,
        expiration,
        actions,
        async_delivery,
    )


def get_notification(notification_id: str) -> Optional[Notification]:
    """
    Get a notification by ID.

    Args:
        notification_id: Notification ID

    Returns:
        Optional[Notification]: The notification or None if not found
    """
    return get_notification_manager().get_notification(notification_id)


def get_all_notifications(
    include_read: bool = False,
    include_dismissed: bool = False,
    channel: Optional[NotificationChannel] = None,
    notification_type: Optional[NotificationType] = None,
    priority: Optional[NotificationPriority] = None,
    max_age: Optional[int] = None,
) -> List[Notification]:
    """
    Get all notifications matching the criteria.

    Args:
        include_read: Whether to include read notifications
        include_dismissed: Whether to include dismissed notifications
        channel: Filter by channel
        notification_type: Filter by type
        priority: Filter by priority
        max_age: Maximum age in seconds

    Returns:
        List[Notification]: List of matching notifications
    """
    return get_notification_manager().get_all_notifications(
        include_read, include_dismissed, channel, notification_type, priority, max_age
    )


def mark_as_read(notification_id: str) -> bool:
    """
    Mark a notification as read.

    Args:
        notification_id: Notification ID

    Returns:
        bool: True if successful, False otherwise
    """
    return get_notification_manager().mark_as_read(notification_id)


def dismiss(notification_id: str) -> bool:
    """
    Dismiss a notification.

    Args:
        notification_id: Notification ID

    Returns:
        bool: True if successful, False otherwise
    """
    return get_notification_manager().dismiss(notification_id)


def clear_all(
    channel: Optional[NotificationChannel] = None,
    notification_type: Optional[NotificationType] = None,
    older_than: Optional[int] = None,
) -> int:
    """
    Clear all notifications matching the criteria.

    Args:
        channel: Filter by channel
        notification_type: Filter by type
        older_than: Clear notifications older than this many seconds

    Returns:
        int: Number of notifications cleared
    """
    return get_notification_manager().clear_all(channel, notification_type, older_than)


def register_callback(
    callback: Callable[[Notification], None],
    channel: NotificationChannel = NotificationChannel.IN_APP,
) -> None:
    """
    Register a callback for notifications.

    Args:
        callback: Callback function
        channel: Notification channel to register for
    """
    return get_notification_manager().register_callback(callback, channel)


def unregister_callback(
    callback: Callable[[Notification], None],
    channel: NotificationChannel = NotificationChannel.IN_APP,
) -> bool:
    """
    Unregister a callback for notifications.

    Args:
        callback: Callback function
        channel: Notification channel

    Returns:
        bool: True if successful, False otherwise
    """
    return get_notification_manager().unregister_callback(callback, channel)


def shutdown_notifications() -> None:
    """Shutdown the notification manager."""
    if _notification_manager is not None:
        _notification_manager.shutdown()
