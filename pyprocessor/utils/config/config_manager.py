"""
Centralized configuration manager for PyProcessor.

This module provides a singleton configuration manager that can be used throughout the application.
It ensures consistent configuration handling and format across all modules.
"""

import datetime
import json
import multiprocessing
import os
import re
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from pyprocessor.utils.config_schema import ConfigSchema, ConfigValueType
from pyprocessor.utils.core.validation_manager import (
    validate_object,
    validate_path,
)
from pyprocessor.utils.file_system.path_manager import (
    ensure_dir_exists,
    expand_env_vars,
    get_logs_dir,
    get_profiles_dir,
    normalize_path,
)
from pyprocessor.utils.logging.error_manager import (
    with_error_handling,
)
from pyprocessor.utils.logging.log_manager import get_logger


class ConfigManager:
    """
    Singleton configuration manager for PyProcessor.

    This class provides a centralized configuration system with the following features:
    - Singleton pattern to ensure only one configuration instance exists
    - Dictionary-like access to configuration values
    - Environment variable expansion in configuration values
    - Type conversion for configuration values
    - Validation of configuration values
    - Profile management for saving and loading configurations
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConfigManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialize the configuration manager."""
        # Only initialize once
        if self._initialized:
            return

        # Get logger
        self.logger = get_logger()

        # Initialize configuration dictionary
        self._config = {}

        # Initialize version tracking
        self._version = 1
        self._history = []
        self._max_history = 10

        # Initialize change callbacks
        self._change_callbacks = []

        # Set default configuration
        self._set_defaults()

        # Create required directories
        self._ensure_directories()

        # Mark as initialized
        self._initialized = True

        self.logger.debug("Configuration manager initialized")

    def _set_defaults(self):
        """Set default configuration values from schema."""
        # Get default configuration from schema
        self._config = ConfigSchema.get_default_config()

        # Apply environment variables
        self._apply_env_vars()

    def _calculate_parallel_jobs(self) -> int:
        """
        Calculate optimal number of parallel jobs based on CPU cores.

        Returns:
            int: Optimal number of parallel jobs
        """
        cores = multiprocessing.cpu_count()
        return max(1, int(cores * 0.75))

    def _ensure_directories(self) -> bool:
        """
        Create required directories if they don't exist.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure input and output folders exist
            ensure_dir_exists(self.get_path("input_folder"))
            ensure_dir_exists(self.get_path("output_folder"))

            # Ensure profiles directory exists
            profiles_dir = get_profiles_dir()
            ensure_dir_exists(profiles_dir)

            # Ensure logs directory exists
            logs_dir = get_logs_dir()
            ensure_dir_exists(logs_dir)

            return True
        except Exception as e:
            self.logger.error(f"Error creating directories: {str(e)}")
            return False

    def _expand_env_vars(self, value: Any) -> Any:
        """
        Expand environment variables in a value.

        Args:
            value: Value to expand environment variables in

        Returns:
            Value with environment variables expanded
        """
        if isinstance(value, str):
            # Expand environment variables in the string
            return expand_env_vars(value)
        elif isinstance(value, dict):
            # Recursively expand environment variables in dictionary values
            return {k: self._expand_env_vars(v) for k, v in value.items()}
        elif isinstance(value, list):
            # Recursively expand environment variables in list items
            return [self._expand_env_vars(item) for item in value]
        else:
            # Return other types as-is
            return value

    def _apply_env_vars(self):
        """
        Apply environment variables to configuration values based on schema.
        """
        schema = ConfigSchema.get_schema()
        self._apply_env_vars_recursive(schema, "")

    def _apply_env_vars_recursive(self, schema: Dict[str, Any], prefix: str):
        """
        Recursively apply environment variables to configuration values based on schema.

        Args:
            schema: Schema to apply environment variables from
            prefix: Prefix for nested keys (e.g., "parent.")
        """
        for key, value in schema.items():
            full_key = f"{prefix}{key}" if prefix else key

            # Skip if not a schema definition
            if not isinstance(value, dict):
                continue

            # Check if this schema has an environment variable
            if "env_var" in value and value["env_var"] in os.environ:
                env_value = os.environ[value["env_var"]]

                # Convert value based on type
                if value["type"] == ConfigValueType.INTEGER:
                    try:
                        env_value = int(env_value)
                    except ValueError:
                        self.logger.warning(
                            f"Cannot convert environment variable {value['env_var']}={env_value} to int"
                        )
                        continue
                elif value["type"] == ConfigValueType.FLOAT:
                    try:
                        env_value = float(env_value)
                    except ValueError:
                        self.logger.warning(
                            f"Cannot convert environment variable {value['env_var']}={env_value} to float"
                        )
                        continue
                elif value["type"] == ConfigValueType.BOOLEAN:
                    if env_value.lower() in ("true", "yes", "1", "on"):
                        env_value = True
                    elif env_value.lower() in ("false", "no", "0", "off"):
                        env_value = False
                    else:
                        self.logger.warning(
                            f"Cannot convert environment variable {value['env_var']}={env_value} to bool"
                        )
                        continue
                elif value["type"] == ConfigValueType.ARRAY:
                    try:
                        # Try to parse as JSON
                        env_value = json.loads(env_value)
                        if not isinstance(env_value, list):
                            # Try to split by comma
                            env_value = [item.strip() for item in env_value.split(",")]
                    except json.JSONDecodeError:
                        # Try to split by comma
                        env_value = [item.strip() for item in env_value.split(",")]
                elif value["type"] == ConfigValueType.OBJECT:
                    try:
                        env_value = json.loads(env_value)
                        if not isinstance(env_value, dict):
                            self.logger.warning(
                                f"Environment variable {value['env_var']}={env_value} is not a valid JSON object"
                            )
                            continue
                    except json.JSONDecodeError:
                        self.logger.warning(
                            f"Environment variable {value['env_var']}={env_value} is not a valid JSON object"
                        )
                        continue

                # Set the value
                self.set(full_key, env_value)

            # Recursively process nested properties
            if value["type"] == ConfigValueType.OBJECT and "properties" in value:
                self._apply_env_vars_recursive(value["properties"], f"{full_key}.")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key (supports dot notation for nested values)
            default: Default value if key is not found

        Returns:
            Configuration value or default if key is not found
        """
        # Handle nested keys with dot notation
        if "." in key:
            parts = key.split(".")
            value = self._config
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
            return value

        # Handle simple keys
        return self._config.get(key, default)

    def get_path(self, key: str, default: Optional[str] = None) -> Path:
        """
        Get a configuration value as a Path object.

        Args:
            key: Configuration key (supports dot notation for nested values)
            default: Default value if key is not found

        Returns:
            Path object for the configuration value
        """
        value = self.get(key, default)
        if value is None:
            return None

        # Expand environment variables
        value = self._expand_env_vars(value)

        # Convert to Path object
        return normalize_path(value)

    def get_int(self, key: str, default: Optional[int] = None) -> Optional[int]:
        """
        Get a configuration value as an integer.

        Args:
            key: Configuration key (supports dot notation for nested values)
            default: Default value if key is not found or not convertible

        Returns:
            Integer value or default if key is not found or not convertible
        """
        value = self.get(key, default)
        if value is None:
            return default

        try:
            return int(value)
        except (ValueError, TypeError):
            self.logger.warning(
                f"Cannot convert {key}={value} to int, using default {default}"
            )
            return default

    def get_float(self, key: str, default: Optional[float] = None) -> Optional[float]:
        """
        Get a configuration value as a float.

        Args:
            key: Configuration key (supports dot notation for nested values)
            default: Default value if key is not found or not convertible

        Returns:
            Float value or default if key is not found or not convertible
        """
        value = self.get(key, default)
        if value is None:
            return default

        try:
            return float(value)
        except (ValueError, TypeError):
            self.logger.warning(
                f"Cannot convert {key}={value} to float, using default {default}"
            )
            return default

    def get_bool(self, key: str, default: Optional[bool] = None) -> Optional[bool]:
        """
        Get a configuration value as a boolean.

        Args:
            key: Configuration key (supports dot notation for nested values)
            default: Default value if key is not found or not convertible

        Returns:
            Boolean value or default if key is not found or not convertible
        """
        value = self.get(key, default)
        if value is None:
            return default

        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            if value.lower() in ("true", "yes", "1", "on"):
                return True
            elif value.lower() in ("false", "no", "0", "off"):
                return False
        elif isinstance(value, int):
            return bool(value)

        self.logger.warning(
            f"Cannot convert {key}={value} to bool, using default {default}"
        )
        return default

    def get_list(self, key: str, default: Optional[List] = None) -> Optional[List]:
        """
        Get a configuration value as a list.

        Args:
            key: Configuration key (supports dot notation for nested values)
            default: Default value if key is not found or not convertible

        Returns:
            List value or default if key is not found or not convertible
        """
        value = self.get(key, default)
        if value is None:
            return default

        if isinstance(value, list):
            return value
        elif isinstance(value, str):
            # Try to parse as JSON
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                # Try to split by comma
                return [item.strip() for item in value.split(",")]

        self.logger.warning(
            f"Cannot convert {key}={value} to list, using default {default}"
        )
        return default

    def get_dict(self, key: str, default: Optional[Dict] = None) -> Optional[Dict]:
        """
        Get a configuration value as a dictionary.

        Args:
            key: Configuration key (supports dot notation for nested values)
            default: Default value if key is not found or not convertible

        Returns:
            Dictionary value or default if key is not found or not convertible
        """
        value = self.get(key, default)
        if value is None:
            return default

        if isinstance(value, dict):
            return value
        elif isinstance(value, str):
            # Try to parse as JSON
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        self.logger.warning(
            f"Cannot convert {key}={value} to dict, using default {default}"
        )
        return default

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key (supports dot notation for nested values)
            value: Value to set
        """
        # Get the old value for change tracking
        old_value = self.get(key)

        # Handle nested keys with dot notation
        if "." in key:
            parts = key.split(".")
            config = self._config
            for part in parts[:-1]:
                if part not in config:
                    config[part] = {}
                elif not isinstance(config[part], dict):
                    config[part] = {}
                config = config[part]
            config[parts[-1]] = value
        else:
            # Handle simple keys
            self._config[key] = value

        # Track changes if the value has changed
        if old_value != value:
            self._track_change(key, old_value, value)

    def _track_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """
        Track a configuration change.

        Args:
            key: Configuration key
            old_value: Old value
            new_value: New value
        """
        # Increment version
        self._version += 1

        # Add to history
        change = {
            "version": self._version,
            "timestamp": datetime.datetime.now().isoformat(),
            "key": key,
            "old_value": old_value,
            "new_value": new_value,
        }
        self._history.append(change)

        # Trim history if it's too long
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        # Notify change callbacks
        for callback in self._change_callbacks:
            try:
                callback(key, old_value, new_value)
            except Exception as e:
                self.logger.error(f"Error in change callback: {str(e)}")

    def register_change_callback(
        self, callback: Callable[[str, Any, Any], None]
    ) -> None:
        """
        Register a callback to be called when a configuration value changes.

        Args:
            callback: Function that takes (key, old_value, new_value)
        """
        if callback not in self._change_callbacks:
            self._change_callbacks.append(callback)

    def unregister_change_callback(
        self, callback: Callable[[str, Any, Any], None]
    ) -> None:
        """
        Unregister a change callback.

        Args:
            callback: Function to unregister
        """
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)

    def update(self, config_dict: Dict) -> None:
        """
        Update configuration with values from a dictionary.

        Args:
            config_dict: Dictionary with configuration values
        """
        for key, value in config_dict.items():
            self.set(key, value)

    def load(
        self,
        filepath: Optional[Union[str, Path]] = None,
        profile_name: Optional[str] = None,
    ) -> bool:
        """
        Load configuration from file.

        Args:
            filepath: Optional custom path for loading
            profile_name: Optional profile name to load

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get profiles directory
            profiles_dir = get_profiles_dir()

            # If profile name is provided, load from profiles directory
            if profile_name:
                filepath = profiles_dir / f"{profile_name}.json"
                self.set("last_used_profile", profile_name)

            # If no filepath is specified, use default
            if not filepath:
                filepath = self.get_path("output_folder") / "config.json"

            filepath = Path(filepath)
            if not filepath.exists():
                self.logger.warning(f"Configuration file not found: {filepath}")
                return False

            with open(filepath, "r") as f:
                config_dict = json.load(f)

                # Update configuration
                self.update(config_dict)

                # Ensure directories exist
                self._ensure_directories()

            self.logger.info(f"Configuration loaded from {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Error loading configuration: {str(e)}")
            return False

    def save(
        self,
        filepath: Optional[Union[str, Path]] = None,
        profile_name: Optional[str] = None,
    ) -> bool:
        """
        Save configuration to file.

        Args:
            filepath: Optional custom path for saving
            profile_name: Optional profile name to save as

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Add timestamp
            self.set("saved_at", datetime.datetime.now().isoformat())

            # Get profiles directory
            profiles_dir = get_profiles_dir()

            # If profile name is provided, save as a profile
            if profile_name:
                filepath = profiles_dir / f"{profile_name}.json"
                self.set("last_used_profile", profile_name)

            # If no filepath is specified, use default
            if not filepath:
                filepath = self.get_path("output_folder") / "config.json"

            # Ensure directory exists
            ensure_dir_exists(Path(filepath).parent)

            # Save the configuration
            with open(filepath, "w") as f:
                json.dump(self._config, f, indent=2)

            self.logger.info(f"Configuration saved to {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving configuration: {str(e)}")
            return False

    def get_available_profiles(self) -> List[str]:
        """
        Get a list of available configuration profiles.

        Returns:
            List of profile names
        """
        # Get profiles directory
        profiles_dir = get_profiles_dir()

        # Ensure the directory exists
        ensure_dir_exists(profiles_dir)

        # Get all JSON files in the profiles directory
        profile_files = list(profiles_dir.glob("*.json"))
        profiles = [file.stem for file in profile_files]
        return profiles

    @with_error_handling
    def validate(self) -> Tuple[List[str], List[str]]:
        """
        Validate the configuration against the schema.

        Returns:
            Tuple of (errors, warnings)

        Raises:
            ConfigurationError: If there's an error validating the configuration
        """
        # Create a validation schema based on the config schema
        schema = self._create_validation_schema()

        # Validate the configuration against the schema
        result = validate_object(self._config, schema)

        # Extract errors and warnings
        errors = [error.message for error in result.errors]
        warnings = [warning.message for warning in result.warnings]

        # Check directories
        try:
            input_folder = self.get_path("input_folder")
            path_result = validate_path(
                input_folder, "input_folder", must_exist=True, must_be_dir=True
            )
            if not path_result:
                for error in path_result.errors:
                    errors.append(error.message)
        except Exception as e:
            errors.append(f"Invalid input folder path: {str(e)}")

        try:
            output_folder = self.get_path("output_folder")
            path_result = validate_path(
                output_folder, "output_folder", must_exist=True, must_be_dir=True
            )
            if not path_result:
                for error in path_result.errors:
                    errors.append(error.message)
        except Exception as e:
            errors.append(f"Invalid output folder path: {str(e)}")

        return errors, warnings

    def _create_validation_schema(self) -> Dict[str, Dict[str, Any]]:
        """
        Create a validation schema from the configuration schema.

        Returns:
            Dict[str, Dict[str, Any]]: Validation schema
        """
        schema = ConfigSchema.get_schema()
        validation_schema = {}

        for key, value in schema.items():
            if not isinstance(value, dict):
                continue

            field_schema = {}

            # Map ConfigValueType to validation type
            if value["type"] == ConfigValueType.INTEGER:
                field_schema["type"] = "number"
                field_schema["integer_only"] = True
                if "min" in value:
                    field_schema["min_value"] = value["min"]
                if "max" in value:
                    field_schema["max_value"] = value["max"]
            elif value["type"] == ConfigValueType.FLOAT:
                field_schema["type"] = "number"
                if "min" in value:
                    field_schema["min_value"] = value["min"]
                if "max" in value:
                    field_schema["max_value"] = value["max"]
            elif value["type"] == ConfigValueType.BOOLEAN:
                field_schema["type"] = "boolean"
            elif value["type"] == ConfigValueType.STRING:
                field_schema["type"] = "string"
                if "pattern" in value:
                    field_schema["pattern"] = value["pattern"]
            elif value["type"] == ConfigValueType.ENUM:
                field_schema["type"] = "enum"
                if "enum" in value:
                    field_schema["allowed_values"] = value["enum"]
            elif value["type"] == ConfigValueType.ARRAY:
                field_schema["type"] = "list"
                # TODO: Add item validation based on schema
            elif value["type"] == ConfigValueType.OBJECT:
                field_schema["type"] = "dict"
                if "properties" in value:
                    field_schema["schema"] = self._create_validation_schema_recursive(
                        value["properties"]
                    )
            elif value["type"] == ConfigValueType.PATH:
                field_schema["type"] = "path"
            elif value["type"] == ConfigValueType.REGEX:
                field_schema["type"] = "regex"

            # Add common properties
            field_schema["required"] = value.get("required", False)
            if "default" in value:
                field_schema["default"] = value["default"]

            validation_schema[key] = field_schema

        return validation_schema

    def _create_validation_schema_recursive(
        self, schema: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Recursively create a validation schema from the configuration schema.

        Args:
            schema: Configuration schema

        Returns:
            Dict[str, Dict[str, Any]]: Validation schema
        """
        validation_schema = {}

        for key, value in schema.items():
            if not isinstance(value, dict):
                continue

            field_schema = {}

            # Map ConfigValueType to validation type
            if value["type"] == ConfigValueType.INTEGER:
                field_schema["type"] = "number"
                field_schema["integer_only"] = True
                if "min" in value:
                    field_schema["min_value"] = value["min"]
                if "max" in value:
                    field_schema["max_value"] = value["max"]
            elif value["type"] == ConfigValueType.FLOAT:
                field_schema["type"] = "number"
                if "min" in value:
                    field_schema["min_value"] = value["min"]
                if "max" in value:
                    field_schema["max_value"] = value["max"]
            elif value["type"] == ConfigValueType.BOOLEAN:
                field_schema["type"] = "boolean"
            elif value["type"] == ConfigValueType.STRING:
                field_schema["type"] = "string"
                if "pattern" in value:
                    field_schema["pattern"] = value["pattern"]
            elif value["type"] == ConfigValueType.ENUM:
                field_schema["type"] = "enum"
                if "enum" in value:
                    field_schema["allowed_values"] = value["enum"]
            elif value["type"] == ConfigValueType.ARRAY:
                field_schema["type"] = "list"
                # TODO: Add item validation based on schema
            elif value["type"] == ConfigValueType.OBJECT:
                field_schema["type"] = "dict"
                if "properties" in value:
                    field_schema["schema"] = self._create_validation_schema_recursive(
                        value["properties"]
                    )
            elif value["type"] == ConfigValueType.PATH:
                field_schema["type"] = "path"
            elif value["type"] == ConfigValueType.REGEX:
                field_schema["type"] = "regex"

            # Add common properties
            field_schema["required"] = value.get("required", False)
            if "default" in value:
                field_schema["default"] = value["default"]

            validation_schema[key] = field_schema

        return validation_schema

    def _validate_recursive(
        self,
        schema: Dict[str, Any],
        prefix: str,
        errors: List[str],
        warnings: List[str],
    ):
        """
        Recursively validate configuration against schema.

        Args:
            schema: Schema to validate against
            prefix: Prefix for nested keys (e.g., "parent.")
            errors: List to add errors to
            warnings: List to add warnings to
        """
        for key, value in schema.items():
            full_key = f"{prefix}{key}" if prefix else key

            # Skip if not a schema definition
            if not isinstance(value, dict):
                continue

            # Get configuration value
            config_value = self.get(full_key)

            # Check if required
            if value.get("required", False) and config_value is None:
                errors.append(f"Missing required configuration value: {full_key}")
                # Set default value if available
                if "default" in value:
                    self.set(full_key, value["default"])
                continue

            # Skip validation if value is None and not required
            if config_value is None:
                # Set default value if available
                if "default" in value:
                    self.set(full_key, value["default"])
                continue

            # Validate value based on type
            if value["type"] == ConfigValueType.INTEGER:
                try:
                    int_value = int(config_value)
                    # Check min/max
                    if "min" in value and int_value < value["min"]:
                        warnings.append(
                            f"Value for {full_key} is below minimum: {int_value} < {value['min']}. Using minimum."
                        )
                        self.set(full_key, value["min"])
                    elif "max" in value and int_value > value["max"]:
                        warnings.append(
                            f"Value for {full_key} is above maximum: {int_value} > {value['max']}. Using maximum."
                        )
                        self.set(full_key, value["max"])
                except (ValueError, TypeError):
                    warnings.append(
                        f"Invalid integer value for {full_key}: {config_value}. Using default."
                    )
                    if "default" in value:
                        self.set(full_key, value["default"])
            elif value["type"] == ConfigValueType.FLOAT:
                try:
                    float_value = float(config_value)
                    # Check min/max
                    if "min" in value and float_value < value["min"]:
                        warnings.append(
                            f"Value for {full_key} is below minimum: {float_value} < {value['min']}. Using minimum."
                        )
                        self.set(full_key, value["min"])
                    elif "max" in value and float_value > value["max"]:
                        warnings.append(
                            f"Value for {full_key} is above maximum: {float_value} > {value['max']}. Using maximum."
                        )
                        self.set(full_key, value["max"])
                except (ValueError, TypeError):
                    warnings.append(
                        f"Invalid float value for {full_key}: {config_value}. Using default."
                    )
                    if "default" in value:
                        self.set(full_key, value["default"])
            elif value["type"] == ConfigValueType.BOOLEAN:
                if not isinstance(config_value, bool):
                    warnings.append(
                        f"Invalid boolean value for {full_key}: {config_value}. Using default."
                    )
                    if "default" in value:
                        self.set(full_key, value["default"])
            elif value["type"] == ConfigValueType.STRING:
                if not isinstance(config_value, str):
                    warnings.append(
                        f"Invalid string value for {full_key}: {config_value}. Using default."
                    )
                    if "default" in value:
                        self.set(full_key, value["default"])
                elif "pattern" in value:
                    try:
                        if not re.match(value["pattern"], config_value):
                            warnings.append(
                                f"Value for {full_key} does not match pattern: {value['pattern']}. Using default."
                            )
                            if "default" in value:
                                self.set(full_key, value["default"])
                    except re.error:
                        warnings.append(
                            f"Invalid pattern for {full_key}: {value['pattern']}. Skipping pattern validation."
                        )
            elif value["type"] == ConfigValueType.ENUM:
                if "enum" in value and config_value not in value["enum"]:
                    warnings.append(
                        f"Invalid enum value for {full_key}: {config_value}. Valid options: {', '.join(value['enum'])}. Using default."
                    )
                    if "default" in value:
                        self.set(full_key, value["default"])
            elif value["type"] == ConfigValueType.ARRAY:
                if not isinstance(config_value, list):
                    warnings.append(
                        f"Invalid array value for {full_key}: {config_value}. Using default."
                    )
                    if "default" in value:
                        self.set(full_key, value["default"])
                elif "items" in value and isinstance(value["items"], dict):
                    # Validate array items
                    for i, item in enumerate(config_value):
                        if "type" in value["items"]:
                            if value["items"]["type"] == ConfigValueType.INTEGER:
                                try:
                                    int(item)
                                except (ValueError, TypeError):
                                    warnings.append(
                                        f"Invalid integer item in {full_key}[{i}]: {item}. Removing item."
                                    )
                                    config_value.pop(i)
                            elif value["items"]["type"] == ConfigValueType.FLOAT:
                                try:
                                    float(item)
                                except (ValueError, TypeError):
                                    warnings.append(
                                        f"Invalid float item in {full_key}[{i}]: {item}. Removing item."
                                    )
                                    config_value.pop(i)
                            elif value["items"][
                                "type"
                            ] == ConfigValueType.BOOLEAN and not isinstance(item, bool):
                                warnings.append(
                                    f"Invalid boolean item in {full_key}[{i}]: {item}. Removing item."
                                )
                                config_value.pop(i)
                            elif value["items"][
                                "type"
                            ] == ConfigValueType.STRING and not isinstance(item, str):
                                warnings.append(
                                    f"Invalid string item in {full_key}[{i}]: {item}. Removing item."
                                )
                                config_value.pop(i)
                    # Update array value
                    self.set(full_key, config_value)
            elif value["type"] == ConfigValueType.OBJECT:
                if not isinstance(config_value, dict):
                    warnings.append(
                        f"Invalid object value for {full_key}: {config_value}. Using default."
                    )
                    if "default" in value:
                        self.set(full_key, value["default"])
                elif "properties" in value:
                    # Recursively validate object properties
                    self._validate_recursive(
                        value["properties"],
                        f"{full_key}." if full_key else "",
                        errors,
                        warnings,
                    )
            elif value["type"] == ConfigValueType.PATH:
                try:
                    # Try to convert to Path object
                    path_value = self.get_path(full_key)
                    if path_value is None:
                        warnings.append(
                            f"Invalid path value for {full_key}: {config_value}. Using default."
                        )
                        if "default" in value:
                            self.set(full_key, value["default"])
                except Exception as e:
                    warnings.append(
                        f"Invalid path value for {full_key}: {config_value}. Error: {str(e)}. Using default."
                    )
                    if "default" in value:
                        self.set(full_key, value["default"])
            elif value["type"] == ConfigValueType.REGEX:
                try:
                    # Try to compile regex
                    re.compile(config_value)
                except re.error as e:
                    warnings.append(
                        f"Invalid regex value for {full_key}: {config_value}. Error: {str(e)}. Using default."
                    )
                    if "default" in value:
                        self.set(full_key, value["default"])

    def apply_args(self, args) -> None:
        """
        Apply command line arguments to configuration.

        Args:
            args: Command line arguments object
        """
        if hasattr(args, "input") and args.input:
            self.set("input_folder", str(normalize_path(args.input)))

        if hasattr(args, "output") and args.output:
            self.set("output_folder", str(normalize_path(args.output)))

        if hasattr(args, "encoder") and args.encoder:
            self.set("ffmpeg_params.video_encoder", args.encoder)

        if hasattr(args, "preset") and args.preset:
            self.set("ffmpeg_params.preset", args.preset)

        if hasattr(args, "tune") and args.tune:
            self.set("ffmpeg_params.tune", args.tune)

        if hasattr(args, "fps") and args.fps is not None:
            self.set("ffmpeg_params.fps", args.fps)

        if hasattr(args, "no_audio") and args.no_audio:
            self.set("ffmpeg_params.include_audio", False)

        if hasattr(args, "parallel") and args.parallel is not None:
            self.set("max_parallel_jobs", args.parallel)

        if hasattr(args, "rename") and args.rename is not None:
            self.set("auto_rename_files", args.rename)

        if hasattr(args, "organize") and args.organize is not None:
            self.set("auto_organize_folders", args.organize)

    def __getitem__(self, key: str) -> Any:
        """
        Get a configuration value using dictionary-like access.

        Args:
            key: Configuration key

        Returns:
            Configuration value

        Raises:
            KeyError: If key is not found
        """
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key: str, value: Any) -> None:
        """
        Set a configuration value using dictionary-like access.

        Args:
            key: Configuration key
            value: Value to set
        """
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        """
        Check if a configuration key exists.

        Args:
            key: Configuration key

        Returns:
            bool: True if key exists, False otherwise
        """
        return self.get(key) is not None

    def __str__(self) -> str:
        """
        Get a string representation of the configuration.

        Returns:
            String representation of the configuration
        """
        return json.dumps(self._config, indent=2)

    def __repr__(self) -> str:
        """
        Get a string representation of the configuration.

        Returns:
            String representation of the configuration
        """
        return f"ConfigManager({self._config})"

    # Version Management Methods

    def get_version(self) -> int:
        """
        Get the current configuration version.

        Returns:
            int: Current version number
        """
        return self._version

    def get_change_history(self) -> List[Dict[str, Any]]:
        """
        Get the configuration change history.

        Returns:
            List[Dict[str, Any]]: List of change records
        """
        return self._history.copy()

    def set_max_history(self, max_history: int) -> None:
        """
        Set the maximum number of changes to keep in history.

        Args:
            max_history: Maximum number of changes to keep
        """
        self._max_history = max_history

        # Trim history if it's too long
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

    def clear_history(self) -> None:
        """
        Clear the configuration change history.
        """
        self._history = []

    def revert_to_version(self, version: int) -> bool:
        """
        Revert configuration to a specific version.

        Args:
            version: Version number to revert to

        Returns:
            bool: True if successful, False otherwise
        """
        if version < 1 or version > self._version:
            self.logger.error(f"Invalid version number: {version}")
            return False

        # Find all changes after the specified version
        changes_to_revert = [
            change for change in self._history if change["version"] > version
        ]

        # Sort changes in reverse order (newest first)
        changes_to_revert.sort(key=lambda x: x["version"], reverse=True)

        # Revert each change
        for change in changes_to_revert:
            # Disable change tracking temporarily
            callbacks = self._change_callbacks
            self._change_callbacks = []

            # Revert the change
            self.set(change["key"], change["old_value"])

            # Restore change tracking
            self._change_callbacks = callbacks

        # Update version
        self._version = version

        # Update history
        self._history = [
            change for change in self._history if change["version"] <= version
        ]

        self.logger.info(f"Configuration reverted to version {version}")
        return True

    # Configuration Merging Methods

    def merge(self, config_dict: Dict[str, Any], overwrite: bool = True) -> None:
        """
        Merge configuration with values from a dictionary.

        Args:
            config_dict: Dictionary with configuration values
            overwrite: Whether to overwrite existing values (default: True)
        """
        self._merge_recursive(self._config, config_dict, "", overwrite)

    def _merge_recursive(
        self,
        target: Dict[str, Any],
        source: Dict[str, Any],
        prefix: str,
        overwrite: bool,
    ) -> None:
        """
        Recursively merge configuration dictionaries.

        Args:
            target: Target dictionary to merge into
            source: Source dictionary to merge from
            prefix: Prefix for nested keys (e.g., "parent.")
            overwrite: Whether to overwrite existing values
        """
        for key, value in source.items():
            full_key = f"{prefix}{key}" if prefix else key

            if (
                isinstance(value, dict)
                and key in target
                and isinstance(target[key], dict)
            ):
                # Recursively merge dictionaries
                self._merge_recursive(target[key], value, f"{full_key}.", overwrite)
            elif key not in target or overwrite:
                # Set the value using the set method to track changes
                self.set(full_key, value)

    def merge_from_file(
        self, filepath: Union[str, Path], overwrite: bool = True
    ) -> bool:
        """
        Merge configuration with values from a file.

        Args:
            filepath: Path to the file
            overwrite: Whether to overwrite existing values (default: True)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            filepath = Path(filepath)

            if not filepath.exists():
                self.logger.warning(f"Configuration file not found: {filepath}")
                return False

            with open(filepath, "r") as f:
                config_dict = json.load(f)

            self.merge(config_dict, overwrite)

            self.logger.info(f"Configuration merged from {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Error merging configuration from file: {str(e)}")
            return False

    # Configuration Diffing Methods

    def diff(self, other_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare configuration with another configuration dictionary.

        Args:
            other_config: Configuration dictionary to compare with

        Returns:
            Dict[str, Any]: Dictionary with added, removed, and changed keys
        """
        return self._diff_recursive(self._config, other_config)

    def _diff_recursive(
        self, config1: Dict[str, Any], config2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recursively compare configuration dictionaries.

        Args:
            config1: First configuration dictionary
            config2: Second configuration dictionary

        Returns:
            Dict[str, Any]: Dictionary with added, removed, and changed keys
        """
        result = {"added": {}, "removed": {}, "changed": {}}

        # Find added and changed keys
        for key, value in config2.items():
            if key not in config1:
                result["added"][key] = value
            elif isinstance(value, dict) and isinstance(config1[key], dict):
                # Recursively compare dictionaries
                nested_diff = self._diff_recursive(config1[key], value)

                # Add nested differences to result
                if nested_diff["added"]:
                    result["added"][key] = nested_diff["added"]
                if nested_diff["removed"]:
                    result["removed"][key] = nested_diff["removed"]
                if nested_diff["changed"]:
                    result["changed"][key] = nested_diff["changed"]
            elif config1[key] != value:
                result["changed"][key] = {"old": config1[key], "new": value}

        # Find removed keys
        for key in config1:
            if key not in config2:
                result["removed"][key] = config1[key]

        return result

    def diff_with_file(self, filepath: Union[str, Path]) -> Dict[str, Any]:
        """
        Compare configuration with a configuration file.

        Args:
            filepath: Path to the file

        Returns:
            Dict[str, Any]: Dictionary with added, removed, and changed keys
        """
        try:
            filepath = Path(filepath)

            if not filepath.exists():
                self.logger.warning(f"Configuration file not found: {filepath}")
                return {"added": {}, "removed": {}, "changed": {}}

            with open(filepath, "r") as f:
                config_dict = json.load(f)

            return self.diff(config_dict)
        except Exception as e:
            self.logger.error(f"Error comparing configuration with file: {str(e)}")
            return {"added": {}, "removed": {}, "changed": {}}

    # Configuration Export/Import Methods

    def export_to_json(self, filepath: Union[str, Path], pretty: bool = True) -> bool:
        """
        Export configuration to a JSON file.

        Args:
            filepath: Path to the file
            pretty: Whether to format the JSON for readability (default: True)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            filepath = Path(filepath)

            # Ensure directory exists
            ensure_dir_exists(filepath.parent)

            with open(filepath, "w") as f:
                if pretty:
                    json.dump(self._config, f, indent=2)
                else:
                    json.dump(self._config, f)

            self.logger.info(f"Configuration exported to {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Error exporting configuration to JSON: {str(e)}")
            return False

    def export_to_yaml(self, filepath: Union[str, Path]) -> bool:
        """
        Export configuration to a YAML file.

        Args:
            filepath: Path to the file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import yaml

            filepath = Path(filepath)

            # Ensure directory exists
            ensure_dir_exists(filepath.parent)

            with open(filepath, "w") as f:
                yaml.dump(self._config, f, default_flow_style=False)

            self.logger.info(f"Configuration exported to {filepath}")
            return True
        except ImportError:
            self.logger.error(
                "PyYAML is not installed. Install it with 'pip install pyyaml'"
            )
            return False
        except Exception as e:
            self.logger.error(f"Error exporting configuration to YAML: {str(e)}")
            return False

    def export_to_csv(self, filepath: Union[str, Path]) -> bool:
        """
        Export configuration to a CSV file.

        Args:
            filepath: Path to the file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import csv

            filepath = Path(filepath)

            # Ensure directory exists
            ensure_dir_exists(filepath.parent)

            # Flatten the configuration
            flat_config = self._flatten_config(self._config)

            with open(filepath, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Key", "Value"])
                for key, value in flat_config.items():
                    writer.writerow([key, value])

            self.logger.info(f"Configuration exported to {filepath}")
            return True
        except ImportError:
            self.logger.error("CSV module is not available")
            return False
        except Exception as e:
            self.logger.error(f"Error exporting configuration to CSV: {str(e)}")
            return False

    def _flatten_config(
        self, config: Dict[str, Any], prefix: str = ""
    ) -> Dict[str, Any]:
        """
        Flatten a nested configuration dictionary.

        Args:
            config: Configuration dictionary to flatten
            prefix: Prefix for nested keys (e.g., "parent.")

        Returns:
            Dict[str, Any]: Flattened configuration dictionary
        """
        result = {}

        for key, value in config.items():
            full_key = f"{prefix}{key}" if prefix else key

            if isinstance(value, dict):
                # Recursively flatten dictionaries
                nested_result = self._flatten_config(value, f"{full_key}.")
                result.update(nested_result)
            else:
                result[full_key] = value

        return result

    def import_from_json(
        self, filepath: Union[str, Path], overwrite: bool = True
    ) -> bool:
        """
        Import configuration from a JSON file.

        Args:
            filepath: Path to the file
            overwrite: Whether to overwrite existing values (default: True)

        Returns:
            bool: True if successful, False otherwise
        """
        return self.merge_from_file(filepath, overwrite)

    def import_from_yaml(
        self, filepath: Union[str, Path], overwrite: bool = True
    ) -> bool:
        """
        Import configuration from a YAML file.

        Args:
            filepath: Path to the file
            overwrite: Whether to overwrite existing values (default: True)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import yaml

            filepath = Path(filepath)

            if not filepath.exists():
                self.logger.warning(f"Configuration file not found: {filepath}")
                return False

            with open(filepath, "r") as f:
                config_dict = yaml.safe_load(f)

            self.merge(config_dict, overwrite)

            self.logger.info(f"Configuration imported from {filepath}")
            return True
        except ImportError:
            self.logger.error(
                "PyYAML is not installed. Install it with 'pip install pyyaml'"
            )
            return False
        except Exception as e:
            self.logger.error(f"Error importing configuration from YAML: {str(e)}")
            return False

    def import_from_csv(
        self, filepath: Union[str, Path], overwrite: bool = True
    ) -> bool:
        """
        Import configuration from a CSV file.

        Args:
            filepath: Path to the file
            overwrite: Whether to overwrite existing values (default: True)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import csv

            filepath = Path(filepath)

            if not filepath.exists():
                self.logger.warning(f"Configuration file not found: {filepath}")
                return False

            with open(filepath, "r", newline="") as f:
                reader = csv.reader(f)
                next(reader)  # Skip header row

                for row in reader:
                    if len(row) >= 2:
                        key, value = row[0], row[1]

                        # Try to convert value to appropriate type
                        try:
                            # Try as int
                            value = int(value)
                        except ValueError:
                            try:
                                # Try as float
                                value = float(value)
                            except ValueError:
                                # Try as bool
                                if value.lower() in ("true", "yes", "1", "on"):
                                    value = True
                                elif value.lower() in ("false", "no", "0", "off"):
                                    value = False
                                # Otherwise, keep as string

                        # Set the value
                        if overwrite or not self.get(key):
                            self.set(key, value)

            self.logger.info(f"Configuration imported from {filepath}")
            return True
        except ImportError:
            self.logger.error("CSV module is not available")
            return False
        except Exception as e:
            self.logger.error(f"Error importing configuration from CSV: {str(e)}")
            return False

    # Configuration Documentation Methods

    def generate_documentation(self, filepath: Union[str, Path] = None) -> str:
        """
        Generate documentation from the configuration schema.

        Args:
            filepath: Optional path to save the documentation

        Returns:
            str: Documentation string
        """
        schema = ConfigSchema.get_schema()
        doc = self._generate_documentation_recursive(schema, "")

        if filepath:
            try:
                filepath = Path(filepath)

                # Ensure directory exists
                ensure_dir_exists(filepath.parent)

                with open(filepath, "w") as f:
                    f.write(doc)

                self.logger.info(f"Documentation saved to {filepath}")
            except Exception as e:
                self.logger.error(f"Error saving documentation: {str(e)}")

        return doc

    def _generate_documentation_recursive(
        self, schema: Dict[str, Any], prefix: str, level: int = 0
    ) -> str:
        """
        Recursively generate documentation from the configuration schema.

        Args:
            schema: Schema to generate documentation from
            prefix: Prefix for nested keys (e.g., "parent.")
            level: Current heading level

        Returns:
            str: Documentation string
        """
        doc = ""

        for key, value in schema.items():
            full_key = f"{prefix}{key}" if prefix else key

            # Skip if not a schema definition
            if not isinstance(value, dict):
                continue

            # Add heading
            doc += f"{'#' * (level + 2)} {full_key}\n\n"

            # Add description
            if "description" in value:
                doc += f"{value['description']}\n\n"

            # Add type
            if "type" in value:
                doc += f"**Type**: {value['type'].value}\n\n"

            # Add default value
            if "default" in value:
                doc += f"**Default**: `{value['default']}`\n\n"

            # Add required flag
            if "required" in value and value["required"]:
                doc += f"**Required**: Yes\n\n"

            # Add environment variable
            if "env_var" in value:
                doc += f"**Environment Variable**: `{value['env_var']}`\n\n"

            # Add enum values
            if "enum" in value:
                doc += f"**Allowed Values**: {', '.join([f'`{v}`' for v in value['enum']])}\n\n"

            # Add min/max values
            if "min" in value:
                doc += f"**Minimum**: {value['min']}\n\n"
            if "max" in value:
                doc += f"**Maximum**: {value['max']}\n\n"

            # Add pattern
            if "pattern" in value:
                doc += f"**Pattern**: `{value['pattern']}`\n\n"

            # Add nested properties
            if "properties" in value and isinstance(value["properties"], dict):
                doc += self._generate_documentation_recursive(
                    value["properties"], f"{full_key}.", level + 1
                )

        return doc


# Create a singleton instance
_config_manager = None


def get_config() -> ConfigManager:
    """
    Get the singleton configuration manager instance.

    Returns:
        ConfigManager: The singleton configuration manager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


# Module-level functions for the new methods


def get_version() -> int:
    """
    Get the current configuration version.

    Returns:
        int: Current version number
    """
    return get_config().get_version()


def get_change_history() -> List[Dict[str, Any]]:
    """
    Get the configuration change history.

    Returns:
        List[Dict[str, Any]]: List of change records
    """
    return get_config().get_change_history()


def revert_to_version(version: int) -> bool:
    """
    Revert configuration to a specific version.

    Args:
        version: Version number to revert to

    Returns:
        bool: True if successful, False otherwise
    """
    return get_config().revert_to_version(version)


def merge(config_dict: Dict[str, Any], overwrite: bool = True) -> None:
    """
    Merge configuration with values from a dictionary.

    Args:
        config_dict: Dictionary with configuration values
        overwrite: Whether to overwrite existing values (default: True)
    """
    get_config().merge(config_dict, overwrite)


def merge_from_file(filepath: Union[str, Path], overwrite: bool = True) -> bool:
    """
    Merge configuration with values from a file.

    Args:
        filepath: Path to the file
        overwrite: Whether to overwrite existing values (default: True)

    Returns:
        bool: True if successful, False otherwise
    """
    return get_config().merge_from_file(filepath, overwrite)


def diff(other_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare configuration with another configuration dictionary.

    Args:
        other_config: Configuration dictionary to compare with

    Returns:
        Dict[str, Any]: Dictionary with added, removed, and changed keys
    """
    return get_config().diff(other_config)


def diff_with_file(filepath: Union[str, Path]) -> Dict[str, Any]:
    """
    Compare configuration with a configuration file.

    Args:
        filepath: Path to the file

    Returns:
        Dict[str, Any]: Dictionary with added, removed, and changed keys
    """
    return get_config().diff_with_file(filepath)


def export_to_json(filepath: Union[str, Path], pretty: bool = True) -> bool:
    """
    Export configuration to a JSON file.

    Args:
        filepath: Path to the file
        pretty: Whether to format the JSON for readability (default: True)

    Returns:
        bool: True if successful, False otherwise
    """
    return get_config().export_to_json(filepath, pretty)


def export_to_yaml(filepath: Union[str, Path]) -> bool:
    """
    Export configuration to a YAML file.

    Args:
        filepath: Path to the file

    Returns:
        bool: True if successful, False otherwise
    """
    return get_config().export_to_yaml(filepath)


def export_to_csv(filepath: Union[str, Path]) -> bool:
    """
    Export configuration to a CSV file.

    Args:
        filepath: Path to the file

    Returns:
        bool: True if successful, False otherwise
    """
    return get_config().export_to_csv(filepath)


def import_from_json(filepath: Union[str, Path], overwrite: bool = True) -> bool:
    """
    Import configuration from a JSON file.

    Args:
        filepath: Path to the file
        overwrite: Whether to overwrite existing values (default: True)

    Returns:
        bool: True if successful, False otherwise
    """
    return get_config().import_from_json(filepath, overwrite)


def import_from_yaml(filepath: Union[str, Path], overwrite: bool = True) -> bool:
    """
    Import configuration from a YAML file.

    Args:
        filepath: Path to the file
        overwrite: Whether to overwrite existing values (default: True)

    Returns:
        bool: True if successful, False otherwise
    """
    return get_config().import_from_yaml(filepath, overwrite)


def import_from_csv(filepath: Union[str, Path], overwrite: bool = True) -> bool:
    """
    Import configuration from a CSV file.

    Args:
        filepath: Path to the file
        overwrite: Whether to overwrite existing values (default: True)

    Returns:
        bool: True if successful, False otherwise
    """
    return get_config().import_from_csv(filepath, overwrite)


def generate_documentation(filepath: Union[str, Path] = None) -> str:
    """
    Generate documentation from the configuration schema.

    Args:
        filepath: Optional path to save the documentation

    Returns:
        str: Documentation string
    """
    return get_config().generate_documentation(filepath)


def register_change_callback(callback: Callable[[str, Any, Any], None]) -> None:
    """
    Register a callback to be called when a configuration value changes.

    Args:
        callback: Function that takes (key, old_value, new_value)
    """
    get_config().register_change_callback(callback)


def unregister_change_callback(callback: Callable[[str, Any, Any], None]) -> None:
    """
    Unregister a change callback.

    Args:
        callback: Function to unregister
    """
    get_config().unregister_change_callback(callback)


# Compatibility with old Config class
class Config:
    """
    Compatibility class for the old Config interface.

    This class provides the same interface as the old Config class,
    but uses the new ConfigManager internally.
    """

    def __init__(self):
        """Initialize the configuration."""
        self.config_manager = get_config()

    def __getattr__(self, name):
        """
        Get a configuration value using attribute access.

        Args:
            name: Configuration key

        Returns:
            Configuration value

        Raises:
            AttributeError: If key is not found
        """
        try:
            value = self.config_manager.get(name)
            if value is None and name not in self.config_manager:
                raise AttributeError(name)

            # Handle special cases for Path objects
            if name in ["input_folder", "output_folder"]:
                return self.config_manager.get_path(name)

            return value
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        """
        Set a configuration value using attribute access.

        Args:
            name: Configuration key
            value: Value to set
        """
        if name == "config_manager":
            super().__setattr__(name, value)
        else:
            self.config_manager.set(name, value)

    def save(self, filepath=None, profile_name=None):
        """
        Save configuration to file.

        Args:
            filepath: Optional custom path for saving
            profile_name: Optional profile name to save as

        Returns:
            bool: True if successful, False otherwise
        """
        return self.config_manager.save(filepath, profile_name)

    def load(self, filepath=None, profile_name=None):
        """
        Load configuration from file.

        Args:
            filepath: Optional custom path for loading
            profile_name: Optional profile name to load

        Returns:
            bool: True if successful, False otherwise
        """
        return self.config_manager.load(filepath, profile_name)

    def get_available_profiles(self):
        """
        Get a list of available configuration profiles.

        Returns:
            List of profile names
        """
        return self.config_manager.get_available_profiles()

    def validate(self):
        """
        Validate configuration and return any errors or warnings.

        Returns:
            Tuple of (errors, warnings)
        """
        return self.config_manager.validate()

    def apply_args(self, args):
        """
        Apply command line arguments to configuration.

        Args:
            args: Command line arguments object
        """
        return self.config_manager.apply_args(args)

    def _calculate_parallel_jobs(self):
        """
        Calculate optimal number of parallel jobs based on CPU cores.

        Returns:
            int: Optimal number of parallel jobs
        """
        return self.config_manager._calculate_parallel_jobs()

    def _ensure_directories(self):
        """
        Create required directories if they don't exist.

        Returns:
            bool: True if successful, False otherwise
        """
        return self.config_manager._ensure_directories()
