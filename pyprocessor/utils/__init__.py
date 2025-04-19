"""
Utility modules for PyProcessor.

This package contains various utility modules used throughout the application.
"""

# Import from config module
from pyprocessor.utils.config import (
    Config, ConfigManager, get_config, get_version, get_change_history,
    save, load, reset, update, merge_from_file, diff,
    validate_config, get_config_schema
)

# Import from file_system module
from pyprocessor.utils.file_system import (
    FileManager, get_file_manager, PathManager, get_path_manager,
    expand_env_vars, normalize_path, ensure_dir_exists, get_base_dir,
    get_user_data_dir, get_user_config_dir, get_user_cache_dir,
    get_default_media_root, get_app_data_dir, get_profiles_dir, get_logs_dir,
    find_executable, get_executable_extension, join_path, get_file_extension,
    get_filename, list_files, file_exists, dir_exists, copy_file, move_file,
    remove_file, remove_dir, get_temp_dir, get_temp_file, temp_dir_context,
    temp_file_context, is_same_path, is_subpath, is_valid_path,
    is_absolute_path, make_relative, make_absolute
)

# Import from process module
from pyprocessor.utils.process import (
    ProcessManager, get_process_manager, run_process, run_async_process,
    run_in_thread, run_in_process, create_process_pool, create_thread_pool,
    ResourceManager, get_resource_manager, ResourceType, ResourceLimit,
    ResourceUsage, ResourceStatus, SchedulerManager, get_scheduler_manager,
    ScheduleType, ScheduleStatus, ScheduleTask
)

# Import from logging module
from pyprocessor.utils.logging import (
    LogManager, get_logger, set_context, get_context, clear_context,
    analyze_logs, get_metrics, reset_metrics, ErrorManager, get_error_manager,
    ErrorSeverity, ErrorCategory, PyProcessorError, with_error_handling,
    handle_error, register_error_handler
)

# Import from media module
from pyprocessor.utils.media import (
    FFmpegManager, get_ffmpeg_manager, get_ffmpeg_path, get_ffprobe_path,
    check_ffmpeg_available, download_ffmpeg, run_ffmpeg_command
)

# Import from core module
from pyprocessor.utils.core import (
    ApplicationContext, PluginManager, get_plugin_manager, Plugin, PluginError,
    discover_plugins, load_plugin, load_all_plugins, CacheManager,
    get_cache_manager, CacheBackend, CachePolicy, NotificationManager,
    get_notification_manager, Notification, NotificationChannel,
    NotificationPriority, NotificationStatus, ValidationManager,
    get_validation_manager, ValidationRule, ValidationResult, validate
)

# Import from server module
from pyprocessor.utils.server import (
    ServerOptimizer, get_server_optimizer, ServerType, OptimizationLevel,
    optimize_server, check_server_configuration
)