"""
Core application utilities for PyProcessor.

This module provides core utilities for application management.
"""

from pyprocessor.utils.core.application_context import ApplicationContext
from pyprocessor.utils.core.plugin_manager import (
    PluginManager, get_plugin_manager, Plugin, PluginError,
    discover_plugins, load_plugin, load_all_plugins
)
from pyprocessor.utils.core.cache_manager import (
    CacheManager, get_cache_manager, CacheBackend, CachePolicy
)
from pyprocessor.utils.core.notification_manager import (
    NotificationManager, get_notification_manager, Notification,
    NotificationChannel, NotificationPriority, NotificationStatus
)
from pyprocessor.utils.core.validation_manager import (
    ValidationManager, get_validation_manager, ValidationRule,
    ValidationResult, validate
)
