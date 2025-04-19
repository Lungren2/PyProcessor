"""
Path utilities for platform-agnostic path handling.

This module provides utilities for working with paths in a platform-agnostic way,
ensuring consistent behavior across Windows, macOS, and Linux.
"""

import warnings

from pyprocessor.utils.path_manager import (
    expand_env_vars,
    normalize_path,
    ensure_dir_exists,
    get_base_dir,
    get_user_data_dir,
    get_user_config_dir,
    get_user_cache_dir,
    get_default_media_root,
    get_app_data_dir,
    get_profiles_dir,
    get_logs_dir,
    find_executable,
    get_executable_extension,
    join_path,
    get_file_extension,
    get_filename,
    list_files,
    file_exists,
    dir_exists,
    copy_file,
    move_file,
    remove_file,
    remove_dir,
    get_temp_dir,
    get_temp_file,
    temp_dir_context,
    temp_file_context,
    is_same_path,
    is_subpath,
    is_valid_path,
    is_absolute_path,
    make_relative,
    make_absolute
)


# Show deprecation warning
warnings.warn(
    "The path_utils module is deprecated and will be removed in a future version. "
    "Please use the path_manager module instead.",
    DeprecationWarning,
    stacklevel=2
)


# All functions are imported from path_manager
