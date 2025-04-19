"""
Configuration management utilities for PyProcessor.

This module provides utilities for managing application configuration.
"""

from pyprocessor.utils.config.config_manager import (
    ConfigManager, get_config, get_version, get_change_history,
    save, load, reset, update, merge_from_file, diff
)
from pyprocessor.utils.config.config import Config
from pyprocessor.utils.config.config_schema import validate_config, get_config_schema
