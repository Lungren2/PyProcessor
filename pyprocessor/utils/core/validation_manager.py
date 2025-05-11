"""
Validation utilities for PyProcessor.

This module provides a centralized way to validate inputs, including:
- Common validation functions
- Custom validation rules
- Validation error handling
"""

import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from pyprocessor.utils.error_manager import (
    ErrorCategory,
    ErrorSeverity,
    PyProcessorError,
    with_error_handling,
)
from pyprocessor.utils.log_manager import get_logger


class ValidationError(PyProcessorError):
    """Error related to validation."""

    def __init__(self, message: str, field: str = None, **kwargs):
        """
        Initialize the validation error.

        Args:
            message: Error message
            field: Field that failed validation
            **kwargs: Additional error details
        """
        super().__init__(
            message=message,
            severity=kwargs.get("severity", ErrorSeverity.WARNING),
            category=ErrorCategory.VALIDATION,
            details={"field": field, **kwargs.get("details", {})},
            **{k: v for k, v in kwargs.items() if k != "details"},
        )
        self.field = field


class ValidationResult:
    """Result of a validation operation."""

    def __init__(
        self,
        valid: bool = True,
        errors: List[ValidationError] = None,
        warnings: List[ValidationError] = None,
    ):
        """
        Initialize the validation result.

        Args:
            valid: Whether the validation passed
            errors: List of validation errors
            warnings: List of validation warnings
        """
        self.valid = valid
        self.errors = errors or []
        self.warnings = warnings or []

    def add_error(self, message: str, field: str = None, **kwargs):
        """
        Add an error to the validation result.

        Args:
            message: Error message
            field: Field that failed validation
            **kwargs: Additional error details
        """
        self.errors.append(
            ValidationError(message, field, severity=ErrorSeverity.ERROR, **kwargs)
        )
        self.valid = False

    def add_warning(self, message: str, field: str = None, **kwargs):
        """
        Add a warning to the validation result.

        Args:
            message: Warning message
            field: Field that has a warning
            **kwargs: Additional warning details
        """
        self.warnings.append(
            ValidationError(message, field, severity=ErrorSeverity.WARNING, **kwargs)
        )

    def merge(self, other: "ValidationResult"):
        """
        Merge another validation result into this one.

        Args:
            other: Another validation result to merge
        """
        if not other.valid:
            self.valid = False
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)

    def __bool__(self):
        """Return whether the validation passed."""
        return self.valid


class ValidationManager:
    """
    Centralized manager for validation operations.

    This class provides:
    - Common validation functions
    - Custom validation rules
    - Validation error handling
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ValidationManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the validation manager."""
        # Only initialize once
        if getattr(self, "_initialized", False):
            return

        # Get logger
        self.logger = get_logger()

        # Initialize validation rules
        self._custom_rules = {}

        # Mark as initialized
        self._initialized = True
        self.logger.debug("Validation manager initialized")

    # Basic validation functions

    @with_error_handling
    def validate_string(
        self,
        value: Any,
        field: str = None,
        min_length: int = None,
        max_length: int = None,
        pattern: str = None,
        required: bool = False,
    ) -> ValidationResult:
        """
        Validate a string value.

        Args:
            value: Value to validate
            field: Field name for error messages
            min_length: Minimum length
            max_length: Maximum length
            pattern: Regular expression pattern
            required: Whether the value is required

        Returns:
            ValidationResult: Result of the validation
        """
        result = ValidationResult()

        # Check if required
        if required and (value is None or value == ""):
            result.add_error("Value is required", field)
            return result

        # Skip further validation if value is None or empty
        if value is None or value == "":
            return result

        # Check type
        if not isinstance(value, str):
            result.add_error(
                f"Value must be a string, got {type(value).__name__}", field
            )
            return result

        # Check min length
        if min_length is not None and len(value) < min_length:
            result.add_error(f"Value must be at least {min_length} characters", field)

        # Check max length
        if max_length is not None and len(value) > max_length:
            result.add_error(f"Value must be at most {max_length} characters", field)

        # Check pattern
        if pattern is not None:
            try:
                if not re.match(pattern, value):
                    result.add_error(f"Value does not match pattern: {pattern}", field)
            except re.error as e:
                result.add_error(f"Invalid pattern: {str(e)}", field)

        return result

    @with_error_handling
    def validate_number(
        self,
        value: Any,
        field: str = None,
        min_value: Union[int, float] = None,
        max_value: Union[int, float] = None,
        integer_only: bool = False,
        required: bool = False,
    ) -> ValidationResult:
        """
        Validate a numeric value.

        Args:
            value: Value to validate
            field: Field name for error messages
            min_value: Minimum value
            max_value: Maximum value
            integer_only: Whether the value must be an integer
            required: Whether the value is required

        Returns:
            ValidationResult: Result of the validation
        """
        result = ValidationResult()

        # Check if required
        if required and value is None:
            result.add_error("Value is required", field)
            return result

        # Skip further validation if value is None
        if value is None:
            return result

        # Convert to number if string
        if isinstance(value, str):
            try:
                if integer_only:
                    value = int(value)
                else:
                    value = float(value)
            except ValueError:
                result.add_error("Value must be a valid number", field)
                return result

        # Check type
        if integer_only and not isinstance(value, int):
            result.add_error(
                f"Value must be an integer, got {type(value).__name__}", field
            )
            return result
        elif not isinstance(value, (int, float)):
            result.add_error(
                f"Value must be a number, got {type(value).__name__}", field
            )
            return result

        # Check min value
        if min_value is not None and value < min_value:
            result.add_error(f"Value must be at least {min_value}", field)

        # Check max value
        if max_value is not None and value > max_value:
            result.add_error(f"Value must be at most {max_value}", field)

        return result

    @with_error_handling
    def validate_boolean(
        self, value: Any, field: str = None, required: bool = False
    ) -> ValidationResult:
        """
        Validate a boolean value.

        Args:
            value: Value to validate
            field: Field name for error messages
            required: Whether the value is required

        Returns:
            ValidationResult: Result of the validation
        """
        result = ValidationResult()

        # Check if required
        if required and value is None:
            result.add_error("Value is required", field)
            return result

        # Skip further validation if value is None
        if value is None:
            return result

        # Convert string to boolean
        if isinstance(value, str):
            value = value.lower()
            if value in ("true", "yes", "1", "y", "t"):
                value = True
            elif value in ("false", "no", "0", "n", "f"):
                value = False
            else:
                result.add_error("Value must be a valid boolean", field)
                return result

        # Check type
        if not isinstance(value, bool):
            result.add_error(
                f"Value must be a boolean, got {type(value).__name__}", field
            )

        return result

    @with_error_handling
    def validate_path(
        self,
        value: Any,
        field: str = None,
        must_exist: bool = False,
        must_be_file: bool = False,
        must_be_dir: bool = False,
        required: bool = False,
    ) -> ValidationResult:
        """
        Validate a file path.

        Args:
            value: Value to validate
            field: Field name for error messages
            must_exist: Whether the path must exist
            must_be_file: Whether the path must be a file
            must_be_dir: Whether the path must be a directory
            required: Whether the value is required

        Returns:
            ValidationResult: Result of the validation
        """
        result = ValidationResult()

        # Check if required
        if required and (value is None or value == ""):
            result.add_error("Value is required", field)
            return result

        # Skip further validation if value is None or empty
        if value is None or value == "":
            return result

        # Convert to Path object
        try:
            path = Path(value)
        except Exception as e:
            result.add_error(f"Invalid path: {str(e)}", field)
            return result

        # Check if path exists
        if must_exist and not path.exists():
            result.add_error(f"Path does not exist: {path}", field)
            return result

        # Check if path is a file
        if must_be_file and not path.is_file():
            result.add_error(f"Path is not a file: {path}", field)
            return result

        # Check if path is a directory
        if must_be_dir and not path.is_dir():
            result.add_error(f"Path is not a directory: {path}", field)
            return result

        return result

    @with_error_handling
    def validate_list(
        self,
        value: Any,
        field: str = None,
        min_length: int = None,
        max_length: int = None,
        item_validator: Callable = None,
        required: bool = False,
    ) -> ValidationResult:
        """
        Validate a list value.

        Args:
            value: Value to validate
            field: Field name for error messages
            min_length: Minimum length
            max_length: Maximum length
            item_validator: Function to validate each item
            required: Whether the value is required

        Returns:
            ValidationResult: Result of the validation
        """
        result = ValidationResult()

        # Check if required
        if required and value is None:
            result.add_error("Value is required", field)
            return result

        # Skip further validation if value is None
        if value is None:
            return result

        # Check type
        if not isinstance(value, (list, tuple)):
            result.add_error(f"Value must be a list, got {type(value).__name__}", field)
            return result

        # Check min length
        if min_length is not None and len(value) < min_length:
            result.add_error(f"List must have at least {min_length} items", field)

        # Check max length
        if max_length is not None and len(value) > max_length:
            result.add_error(f"List must have at most {max_length} items", field)

        # Validate each item
        if item_validator is not None:
            for i, item in enumerate(value):
                item_result = item_validator(
                    item, f"{field}[{i}]" if field else f"[{i}]"
                )
                result.merge(item_result)

        return result

    @with_error_handling
    def validate_dict(
        self,
        value: Any,
        field: str = None,
        required_keys: List[str] = None,
        optional_keys: List[str] = None,
        key_validator: Callable = None,
        value_validator: Callable = None,
        required: bool = False,
    ) -> ValidationResult:
        """
        Validate a dictionary value.

        Args:
            value: Value to validate
            field: Field name for error messages
            required_keys: List of required keys
            optional_keys: List of optional keys
            key_validator: Function to validate each key
            value_validator: Function to validate each value
            required: Whether the value is required

        Returns:
            ValidationResult: Result of the validation
        """
        result = ValidationResult()

        # Check if required
        if required and value is None:
            result.add_error("Value is required", field)
            return result

        # Skip further validation if value is None
        if value is None:
            return result

        # Check type
        if not isinstance(value, dict):
            result.add_error(
                f"Value must be a dictionary, got {type(value).__name__}", field
            )
            return result

        # Check required keys
        if required_keys is not None:
            for key in required_keys:
                if key not in value:
                    result.add_error(f"Missing required key: {key}", field)

        # Check for unknown keys
        if required_keys is not None and optional_keys is not None:
            allowed_keys = set(required_keys) | set(optional_keys)
            for key in value.keys():
                if key not in allowed_keys:
                    result.add_warning(f"Unknown key: {key}", field)

        # Validate each key
        if key_validator is not None:
            for key in value.keys():
                key_result = key_validator(key, f"{field}.{key}" if field else key)
                result.merge(key_result)

        # Validate each value
        if value_validator is not None:
            for key, val in value.items():
                value_result = value_validator(val, f"{field}.{key}" if field else key)
                result.merge(value_result)

        return result

    @with_error_handling
    def validate_email(
        self, value: Any, field: str = None, required: bool = False
    ) -> ValidationResult:
        """
        Validate an email address.

        Args:
            value: Value to validate
            field: Field name for error messages
            required: Whether the value is required

        Returns:
            ValidationResult: Result of the validation
        """
        result = ValidationResult()

        # Check if required
        if required and (value is None or value == ""):
            result.add_error("Value is required", field)
            return result

        # Skip further validation if value is None or empty
        if value is None or value == "":
            return result

        # Check type
        if not isinstance(value, str):
            result.add_error(
                f"Value must be a string, got {type(value).__name__}", field
            )
            return result

        # Simple email pattern
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, value):
            result.add_error("Invalid email address", field)

        return result

    @with_error_handling
    def validate_url(
        self, value: Any, field: str = None, required: bool = False
    ) -> ValidationResult:
        """
        Validate a URL.

        Args:
            value: Value to validate
            field: Field name for error messages
            required: Whether the value is required

        Returns:
            ValidationResult: Result of the validation
        """
        result = ValidationResult()

        # Check if required
        if required and (value is None or value == ""):
            result.add_error("Value is required", field)
            return result

        # Skip further validation if value is None or empty
        if value is None or value == "":
            return result

        # Check type
        if not isinstance(value, str):
            result.add_error(
                f"Value must be a string, got {type(value).__name__}", field
            )
            return result

        # Simple URL pattern
        pattern = r"^(https?|ftp)://[^\s/$.?#].[^\s]*$"
        if not re.match(pattern, value):
            result.add_error("Invalid URL", field)

        return result

    @with_error_handling
    def validate_enum(
        self,
        value: Any,
        field: str = None,
        allowed_values: List[Any] = None,
        case_sensitive: bool = True,
        required: bool = False,
    ) -> ValidationResult:
        """
        Validate a value against an enumeration of allowed values.

        Args:
            value: Value to validate
            field: Field name for error messages
            allowed_values: List of allowed values
            case_sensitive: Whether string comparison is case-sensitive
            required: Whether the value is required

        Returns:
            ValidationResult: Result of the validation
        """
        result = ValidationResult()

        # Check if required
        if required and value is None:
            result.add_error("Value is required", field)
            return result

        # Skip further validation if value is None
        if value is None:
            return result

        # Check allowed values
        if allowed_values is not None:
            if isinstance(value, str) and not case_sensitive:
                if value.lower() not in [str(v).lower() for v in allowed_values]:
                    result.add_error(
                        f"Value must be one of: {', '.join(str(v) for v in allowed_values)}",
                        field,
                    )
            else:
                if value not in allowed_values:
                    result.add_error(
                        f"Value must be one of: {', '.join(str(v) for v in allowed_values)}",
                        field,
                    )

        return result

    @with_error_handling
    def validate_regex(
        self, value: Any, field: str = None, required: bool = False
    ) -> ValidationResult:
        """
        Validate a regular expression pattern.

        Args:
            value: Value to validate
            field: Field name for error messages
            required: Whether the value is required

        Returns:
            ValidationResult: Result of the validation
        """
        result = ValidationResult()

        # Check if required
        if required and (value is None or value == ""):
            result.add_error("Value is required", field)
            return result

        # Skip further validation if value is None or empty
        if value is None or value == "":
            return result

        # Check type
        if not isinstance(value, str):
            result.add_error(
                f"Value must be a string, got {type(value).__name__}", field
            )
            return result

        # Try to compile the regex
        try:
            re.compile(value)
        except re.error as e:
            result.add_error(f"Invalid regular expression: {str(e)}", field)

        return result

    # Custom validation rule management

    @with_error_handling
    def register_rule(self, name: str, validator: Callable) -> None:
        """
        Register a custom validation rule.

        Args:
            name: Name of the rule
            validator: Validation function
        """
        if not callable(validator):
            raise ValueError(
                f"Validator must be callable, got {type(validator).__name__}"
            )

        self._custom_rules[name] = validator
        self.logger.debug(f"Registered custom validation rule: {name}")

    @with_error_handling
    def unregister_rule(self, name: str) -> bool:
        """
        Unregister a custom validation rule.

        Args:
            name: Name of the rule

        Returns:
            bool: True if the rule was unregistered, False if it was not found
        """
        if name in self._custom_rules:
            del self._custom_rules[name]
            self.logger.debug(f"Unregistered custom validation rule: {name}")
            return True
        return False

    @with_error_handling
    def get_rule(self, name: str) -> Optional[Callable]:
        """
        Get a custom validation rule.

        Args:
            name: Name of the rule

        Returns:
            Optional[Callable]: The validation function or None if not found
        """
        return self._custom_rules.get(name)

    @with_error_handling
    def apply_rule(
        self, name: str, value: Any, field: str = None, **kwargs
    ) -> ValidationResult:
        """
        Apply a custom validation rule.

        Args:
            name: Name of the rule
            value: Value to validate
            field: Field name for error messages
            **kwargs: Additional arguments to pass to the validator

        Returns:
            ValidationResult: Result of the validation
        """
        validator = self.get_rule(name)
        if validator is None:
            result = ValidationResult()
            result.add_error(f"Unknown validation rule: {name}", field)
            return result

        return validator(value, field, **kwargs)

    # Object validation with schema

    @with_error_handling
    def validate_object(
        self, value: Any, schema: Dict[str, Dict[str, Any]], field: str = None
    ) -> ValidationResult:
        """
        Validate an object against a schema.

        Args:
            value: Object to validate
            schema: Validation schema
            field: Field name for error messages

        Returns:
            ValidationResult: Result of the validation
        """
        result = ValidationResult()

        # Check if value is None
        if value is None:
            if any(
                field_schema.get("required", False) for field_schema in schema.values()
            ):
                result.add_error("Object is required", field)
            return result

        # Check type
        if not isinstance(value, dict):
            result.add_error(
                f"Value must be an object, got {type(value).__name__}", field
            )
            return result

        # Validate each field
        for field_name, field_schema in schema.items():
            field_value = value.get(field_name)
            field_type = field_schema.get("type")
            field_required = field_schema.get("required", False)
            field_path = f"{field}.{field_name}" if field else field_name

            # Check if required
            if field_required and field_value is None:
                result.add_error("Field is required", field_path)
                continue

            # Skip further validation if value is None
            if field_value is None:
                continue

            # Validate based on type
            if field_type == "string":
                field_result = self.validate_string(
                    field_value,
                    field_path,
                    min_length=field_schema.get("min_length"),
                    max_length=field_schema.get("max_length"),
                    pattern=field_schema.get("pattern"),
                    required=field_required,
                )
            elif field_type == "number":
                field_result = self.validate_number(
                    field_value,
                    field_path,
                    min_value=field_schema.get("min_value"),
                    max_value=field_schema.get("max_value"),
                    integer_only=field_schema.get("integer_only", False),
                    required=field_required,
                )
            elif field_type == "boolean":
                field_result = self.validate_boolean(
                    field_value, field_path, required=field_required
                )
            elif field_type == "path":
                field_result = self.validate_path(
                    field_value,
                    field_path,
                    must_exist=field_schema.get("must_exist", False),
                    must_be_file=field_schema.get("must_be_file", False),
                    must_be_dir=field_schema.get("must_be_dir", False),
                    required=field_required,
                )
            elif field_type == "list":
                field_result = self.validate_list(
                    field_value,
                    field_path,
                    min_length=field_schema.get("min_length"),
                    max_length=field_schema.get("max_length"),
                    item_validator=field_schema.get("item_validator"),
                    required=field_required,
                )
            elif field_type == "dict":
                field_result = self.validate_dict(
                    field_value,
                    field_path,
                    required_keys=field_schema.get("required_keys"),
                    optional_keys=field_schema.get("optional_keys"),
                    key_validator=field_schema.get("key_validator"),
                    value_validator=field_schema.get("value_validator"),
                    required=field_required,
                )
            elif field_type == "email":
                field_result = self.validate_email(
                    field_value, field_path, required=field_required
                )
            elif field_type == "url":
                field_result = self.validate_url(
                    field_value, field_path, required=field_required
                )
            elif field_type == "enum":
                field_result = self.validate_enum(
                    field_value,
                    field_path,
                    allowed_values=field_schema.get("allowed_values"),
                    case_sensitive=field_schema.get("case_sensitive", True),
                    required=field_required,
                )
            elif field_type == "regex":
                field_result = self.validate_regex(
                    field_value, field_path, required=field_required
                )
            elif field_type == "object":
                field_result = self.validate_object(
                    field_value, field_schema.get("schema", {}), field_path
                )
            elif field_type == "custom":
                rule_name = field_schema.get("rule")
                if rule_name:
                    field_result = self.apply_rule(
                        rule_name,
                        field_value,
                        field_path,
                        **field_schema.get("params", {}),
                    )
                else:
                    field_result = ValidationResult()
                    field_result.add_error("Missing custom rule name", field_path)
            else:
                field_result = ValidationResult()
                field_result.add_error(f"Unknown field type: {field_type}", field_path)

            result.merge(field_result)

        return result


# Singleton instance
_validation_manager = None


def get_validation_manager() -> ValidationManager:
    """
    Get the singleton validation manager instance.

    Returns:
        ValidationManager: The singleton validation manager instance
    """
    global _validation_manager
    if _validation_manager is None:
        _validation_manager = ValidationManager()
    return _validation_manager


# Module-level functions for convenience


def validate_string(
    value: Any,
    field: str = None,
    min_length: int = None,
    max_length: int = None,
    pattern: str = None,
    required: bool = False,
) -> ValidationResult:
    """
    Validate a string value.

    Args:
        value: Value to validate
        field: Field name for error messages
        min_length: Minimum length
        max_length: Maximum length
        pattern: Regular expression pattern
        required: Whether the value is required

    Returns:
        ValidationResult: Result of the validation
    """
    return get_validation_manager().validate_string(
        value, field, min_length, max_length, pattern, required
    )


def validate_number(
    value: Any,
    field: str = None,
    min_value: Union[int, float] = None,
    max_value: Union[int, float] = None,
    integer_only: bool = False,
    required: bool = False,
) -> ValidationResult:
    """
    Validate a numeric value.

    Args:
        value: Value to validate
        field: Field name for error messages
        min_value: Minimum value
        max_value: Maximum value
        integer_only: Whether the value must be an integer
        required: Whether the value is required

    Returns:
        ValidationResult: Result of the validation
    """
    return get_validation_manager().validate_number(
        value, field, min_value, max_value, integer_only, required
    )


def validate_boolean(
    value: Any, field: str = None, required: bool = False
) -> ValidationResult:
    """
    Validate a boolean value.

    Args:
        value: Value to validate
        field: Field name for error messages
        required: Whether the value is required

    Returns:
        ValidationResult: Result of the validation
    """
    return get_validation_manager().validate_boolean(value, field, required)


def validate_path(
    value: Any,
    field: str = None,
    must_exist: bool = False,
    must_be_file: bool = False,
    must_be_dir: bool = False,
    required: bool = False,
) -> ValidationResult:
    """
    Validate a file path.

    Args:
        value: Value to validate
        field: Field name for error messages
        must_exist: Whether the path must exist
        must_be_file: Whether the path must be a file
        must_be_dir: Whether the path must be a directory
        required: Whether the value is required

    Returns:
        ValidationResult: Result of the validation
    """
    return get_validation_manager().validate_path(
        value, field, must_exist, must_be_file, must_be_dir, required
    )


def validate_list(
    value: Any,
    field: str = None,
    min_length: int = None,
    max_length: int = None,
    item_validator: Callable = None,
    required: bool = False,
) -> ValidationResult:
    """
    Validate a list value.

    Args:
        value: Value to validate
        field: Field name for error messages
        min_length: Minimum length
        max_length: Maximum length
        item_validator: Function to validate each item
        required: Whether the value is required

    Returns:
        ValidationResult: Result of the validation
    """
    return get_validation_manager().validate_list(
        value, field, min_length, max_length, item_validator, required
    )


def validate_dict(
    value: Any,
    field: str = None,
    required_keys: List[str] = None,
    optional_keys: List[str] = None,
    key_validator: Callable = None,
    value_validator: Callable = None,
    required: bool = False,
) -> ValidationResult:
    """
    Validate a dictionary value.

    Args:
        value: Value to validate
        field: Field name for error messages
        required_keys: List of required keys
        optional_keys: List of optional keys
        key_validator: Function to validate each key
        value_validator: Function to validate each value
        required: Whether the value is required

    Returns:
        ValidationResult: Result of the validation
    """
    return get_validation_manager().validate_dict(
        value,
        field,
        required_keys,
        optional_keys,
        key_validator,
        value_validator,
        required,
    )


def validate_email(
    value: Any, field: str = None, required: bool = False
) -> ValidationResult:
    """
    Validate an email address.

    Args:
        value: Value to validate
        field: Field name for error messages
        required: Whether the value is required

    Returns:
        ValidationResult: Result of the validation
    """
    return get_validation_manager().validate_email(value, field, required)


def validate_url(
    value: Any, field: str = None, required: bool = False
) -> ValidationResult:
    """
    Validate a URL.

    Args:
        value: Value to validate
        field: Field name for error messages
        required: Whether the value is required

    Returns:
        ValidationResult: Result of the validation
    """
    return get_validation_manager().validate_url(value, field, required)


def validate_enum(
    value: Any,
    field: str = None,
    allowed_values: List[Any] = None,
    case_sensitive: bool = True,
    required: bool = False,
) -> ValidationResult:
    """
    Validate a value against an enumeration of allowed values.

    Args:
        value: Value to validate
        field: Field name for error messages
        allowed_values: List of allowed values
        case_sensitive: Whether string comparison is case-sensitive
        required: Whether the value is required

    Returns:
        ValidationResult: Result of the validation
    """
    return get_validation_manager().validate_enum(
        value, field, allowed_values, case_sensitive, required
    )


def validate_regex(
    value: Any, field: str = None, required: bool = False
) -> ValidationResult:
    """
    Validate a regular expression pattern.

    Args:
        value: Value to validate
        field: Field name for error messages
        required: Whether the value is required

    Returns:
        ValidationResult: Result of the validation
    """
    return get_validation_manager().validate_regex(value, field, required)


def validate_object(
    value: Any, schema: Dict[str, Dict[str, Any]], field: str = None
) -> ValidationResult:
    """
    Validate an object against a schema.

    Args:
        value: Object to validate
        schema: Validation schema
        field: Field name for error messages

    Returns:
        ValidationResult: Result of the validation
    """
    return get_validation_manager().validate_object(value, schema, field)


def register_rule(name: str, validator: Callable) -> None:
    """
    Register a custom validation rule.

    Args:
        name: Name of the rule
        validator: Validation function
    """
    return get_validation_manager().register_rule(name, validator)


def unregister_rule(name: str) -> bool:
    """
    Unregister a custom validation rule.

    Args:
        name: Name of the rule

    Returns:
        bool: True if the rule was unregistered, False if it was not found
    """
    return get_validation_manager().unregister_rule(name)


def apply_rule(name: str, value: Any, field: str = None, **kwargs) -> ValidationResult:
    """
    Apply a custom validation rule.

    Args:
        name: Name of the rule
        value: Value to validate
        field: Field name for error messages
        **kwargs: Additional arguments to pass to the validator

    Returns:
        ValidationResult: Result of the validation
    """
    return get_validation_manager().apply_rule(name, value, field, **kwargs)
