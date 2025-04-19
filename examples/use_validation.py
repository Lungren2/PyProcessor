"""
Example script demonstrating how to use the validation system.

This script shows how to validate different types of inputs and handle validation errors.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyprocessor.utils.core.validation_manager import (
    validate_string,
    validate_number,
    validate_boolean,
    validate_path,
    validate_list,
    validate_dict,
    validate_email,
    validate_url,
    validate_enum,
    validate_regex,
    validate_object,
    register_rule,
    apply_rule,
    ValidationResult
)


def print_validation_result(result, field_name=None):
    """Print a validation result."""
    if result:
        print(f"✅ Validation passed for {field_name or 'value'}")
    else:
        print(f"❌ Validation failed for {field_name or 'value'}")
        for error in result.errors:
            print(f"  Error: {error.message}")
        for warning in result.warnings:
            print(f"  Warning: {warning.message}")
    print()


def main():
    """Main function demonstrating validation usage."""
    print("Validation System Example")
    print("========================")

    # String validation
    print("\n1. String Validation")
    result = validate_string(
        "hello",
        field="name",
        min_length=3,
        max_length=10,
        pattern=r"^[a-zA-Z]+$",
        required=True
    )
    print_validation_result(result, "name")

    # Invalid string
    result = validate_string(
        "hi",
        field="name",
        min_length=3,
        max_length=10,
        pattern=r"^[a-zA-Z]+$",
        required=True
    )
    print_validation_result(result, "name")

    # Number validation
    print("\n2. Number Validation")
    result = validate_number(
        42,
        field="age",
        min_value=18,
        max_value=100,
        integer_only=True,
        required=True
    )
    print_validation_result(result, "age")

    # Invalid number
    result = validate_number(
        15,
        field="age",
        min_value=18,
        max_value=100,
        integer_only=True,
        required=True
    )
    print_validation_result(result, "age")

    # Boolean validation
    print("\n3. Boolean Validation")
    result = validate_boolean(
        True,
        field="active",
        required=True
    )
    print_validation_result(result, "active")

    # Invalid boolean
    result = validate_boolean(
        "not a boolean",
        field="active",
        required=True
    )
    print_validation_result(result, "active")

    # Path validation
    print("\n4. Path Validation")
    # Create a temporary file for testing
    temp_file = Path(__file__).parent / "temp_test_file.txt"
    with open(temp_file, "w") as f:
        f.write("Test file")

    result = validate_path(
        str(temp_file),
        field="config_file",
        must_exist=True,
        must_be_file=True,
        required=True
    )
    print_validation_result(result, "config_file")

    # Invalid path
    result = validate_path(
        "nonexistent_file.txt",
        field="config_file",
        must_exist=True,
        must_be_file=True,
        required=True
    )
    print_validation_result(result, "config_file")

    # Clean up the temporary file
    os.remove(temp_file)

    # List validation
    print("\n5. List Validation")
    result = validate_list(
        ["apple", "banana", "cherry"],
        field="fruits",
        min_length=1,
        max_length=5,
        item_validator=lambda item, field: validate_string(item, field, min_length=3),
        required=True
    )
    print_validation_result(result, "fruits")

    # Invalid list
    result = validate_list(
        ["apple", "b", "cherry"],
        field="fruits",
        min_length=1,
        max_length=5,
        item_validator=lambda item, field: validate_string(item, field, min_length=3),
        required=True
    )
    print_validation_result(result, "fruits")

    # Dictionary validation
    print("\n6. Dictionary Validation")
    result = validate_dict(
        {"name": "John", "age": 30},
        field="user",
        required_keys=["name", "age"],
        optional_keys=["email"],
        key_validator=lambda key, field: validate_string(key, field),
        value_validator=lambda value, field: (
            validate_string(value, field) if field.endswith("name") else
            validate_number(value, field) if field.endswith("age") else
            None
        ),
        required=True
    )
    print_validation_result(result, "user")

    # Invalid dictionary
    result = validate_dict(
        {"name": "John"},
        field="user",
        required_keys=["name", "age"],
        optional_keys=["email"],
        key_validator=lambda key, field: validate_string(key, field),
        value_validator=lambda value, field: (
            validate_string(value, field) if field.endswith("name") else
            validate_number(value, field) if field.endswith("age") else
            None
        ),
        required=True
    )
    print_validation_result(result, "user")

    # Email validation
    print("\n7. Email Validation")
    result = validate_email(
        "user@example.com",
        field="email",
        required=True
    )
    print_validation_result(result, "email")

    # Invalid email
    result = validate_email(
        "not_an_email",
        field="email",
        required=True
    )
    print_validation_result(result, "email")

    # URL validation
    print("\n8. URL Validation")
    result = validate_url(
        "https://example.com",
        field="website",
        required=True
    )
    print_validation_result(result, "website")

    # Invalid URL
    result = validate_url(
        "not_a_url",
        field="website",
        required=True
    )
    print_validation_result(result, "website")

    # Enum validation
    print("\n9. Enum Validation")
    result = validate_enum(
        "apple",
        field="fruit",
        allowed_values=["apple", "banana", "cherry"],
        case_sensitive=False,
        required=True
    )
    print_validation_result(result, "fruit")

    # Invalid enum
    result = validate_enum(
        "orange",
        field="fruit",
        allowed_values=["apple", "banana", "cherry"],
        case_sensitive=False,
        required=True
    )
    print_validation_result(result, "fruit")

    # Regex validation
    print("\n10. Regex Validation")
    result = validate_regex(
        r"^[a-zA-Z0-9]+$",
        field="pattern",
        required=True
    )
    print_validation_result(result, "pattern")

    # Invalid regex
    result = validate_regex(
        r"^[a-zA-Z0-9+$",
        field="pattern",
        required=True
    )
    print_validation_result(result, "pattern")

    # Custom validation rule
    print("\n11. Custom Validation Rule")

    # Define a custom validation rule
    def validate_even_number(value, field=None, **kwargs):
        result = ValidationResult()

        if value is None:
            if kwargs.get("required", False):
                result.add_error("Value is required", field)
            return result

        if not isinstance(value, int):
            result.add_error("Value must be an integer", field)
            return result

        if value % 2 != 0:
            result.add_error("Value must be an even number", field)

        return result

    # Register the rule
    register_rule("even_number", validate_even_number)

    # Apply the rule
    result = apply_rule("even_number", 42, field="value")
    print_validation_result(result, "value")

    # Invalid value for custom rule
    result = apply_rule("even_number", 43, field="value")
    print_validation_result(result, "value")

    # Schema-based validation
    print("\n12. Schema-Based Validation")

    # Define a schema
    user_schema = {
        "name": {
            "type": "string",
            "min_length": 3,
            "max_length": 50,
            "required": True
        },
        "age": {
            "type": "number",
            "min_value": 18,
            "integer_only": True,
            "required": True
        },
        "email": {
            "type": "email",
            "required": False
        },
        "active": {
            "type": "boolean",
            "required": False
        },
        "roles": {
            "type": "list",
            "min_length": 1,
            "item_validator": lambda item, field: validate_enum(
                item, field, allowed_values=["admin", "user", "guest"]
            ),
            "required": False
        },
        "settings": {
            "type": "object",
            "schema": {
                "theme": {
                    "type": "enum",
                    "allowed_values": ["light", "dark"],
                    "required": False
                },
                "notifications": {
                    "type": "boolean",
                    "required": False
                }
            },
            "required": False
        }
    }

    # Valid user
    user = {
        "name": "John Doe",
        "age": 30,
        "email": "john@example.com",
        "active": True,
        "roles": ["admin", "user"],
        "settings": {
            "theme": "dark",
            "notifications": True
        }
    }

    result = validate_object(user, user_schema, field="user")
    print_validation_result(result, "user")

    # Invalid user
    invalid_user = {
        "name": "Jo",
        "age": 15,
        "email": "not_an_email",
        "active": "not_a_boolean",
        "roles": ["admin", "invalid_role"],
        "settings": {
            "theme": "invalid_theme",
            "notifications": "not_a_boolean"
        }
    }

    result = validate_object(invalid_user, user_schema, field="user")
    print_validation_result(result, "user")

    print("\nValidation example completed")


if __name__ == "__main__":
    main()
