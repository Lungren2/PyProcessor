# Validation System in PyProcessor

This document describes the validation system in PyProcessor, including the centralized `ValidationManager` class, validation functions, and custom validation rules.

## Overview

PyProcessor provides a centralized validation system through the `ValidationManager` class in the `pyprocessor.utils.validation_manager` module. This class provides a consistent interface for validating inputs across the application.

The validation system is designed to:

- Provide a consistent way to validate inputs
- Support a wide range of validation types
- Allow for custom validation rules
- Provide detailed error messages
- Support schema-based validation

## ValidationManager

The `ValidationManager` class is a singleton that provides the following features:

- Basic validation functions for common types
- Custom validation rule management
- Schema-based object validation
- Validation error handling

### Getting the Validation Manager

```python
from pyprocessor.utils.validation_manager import get_validation_manager

# Get the validation manager
validation_manager = get_validation_manager()
```

## Validation Results

All validation functions return a `ValidationResult` object, which contains:

- A boolean `valid` flag indicating whether the validation passed
- A list of `errors` that caused the validation to fail
- A list of `warnings` that didn't cause the validation to fail but should be noted

```python
from pyprocessor.utils.validation_manager import validate_string

# Validate a string
result = validate_string("hello", min_length=10)

# Check if validation passed
if result:
    print("Validation passed")
else:
    print("Validation failed")
    for error in result.errors:
        print(f"Error: {error.message}")
    for warning in result.warnings:
        print(f"Warning: {warning.message}")
```

## Basic Validation Functions

### String Validation

```python
from pyprocessor.utils.validation_manager import validate_string

# Validate a string
result = validate_string(
    "hello",
    field="name",
    min_length=3,
    max_length=10,
    pattern=r"^[a-zA-Z]+$",
    required=True
)
```

### Number Validation

```python
from pyprocessor.utils.validation_manager import validate_number

# Validate a number
result = validate_number(
    42,
    field="age",
    min_value=18,
    max_value=100,
    integer_only=True,
    required=True
)
```

### Boolean Validation

```python
from pyprocessor.utils.validation_manager import validate_boolean

# Validate a boolean
result = validate_boolean(
    True,
    field="active",
    required=True
)
```

### Path Validation

```python
from pyprocessor.utils.validation_manager import validate_path

# Validate a path
result = validate_path(
    "/path/to/file.txt",
    field="config_file",
    must_exist=True,
    must_be_file=True,
    required=True
)
```

### List Validation

```python
from pyprocessor.utils.validation_manager import validate_list, validate_string

# Validate a list
result = validate_list(
    ["apple", "banana", "cherry"],
    field="fruits",
    min_length=1,
    max_length=5,
    item_validator=lambda item, field: validate_string(item, field, min_length=3),
    required=True
)
```

### Dictionary Validation

```python
from pyprocessor.utils.validation_manager import validate_dict, validate_string, validate_number

# Validate a dictionary
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
```

### Email Validation

```python
from pyprocessor.utils.validation_manager import validate_email

# Validate an email
result = validate_email(
    "user@example.com",
    field="email",
    required=True
)
```

### URL Validation

```python
from pyprocessor.utils.validation_manager import validate_url

# Validate a URL
result = validate_url(
    "https://example.com",
    field="website",
    required=True
)
```

### Enum Validation

```python
from pyprocessor.utils.validation_manager import validate_enum

# Validate an enum
result = validate_enum(
    "apple",
    field="fruit",
    allowed_values=["apple", "banana", "cherry"],
    case_sensitive=False,
    required=True
)
```

### Regex Validation

```python
from pyprocessor.utils.validation_manager import validate_regex

# Validate a regex pattern
result = validate_regex(
    r"^[a-zA-Z0-9]+$",
    field="pattern",
    required=True
)
```

## Custom Validation Rules

You can create and register custom validation rules:

```python
from pyprocessor.utils.validation_manager import register_rule, apply_rule, ValidationResult

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
```

## Schema-Based Validation

You can validate complex objects against a schema:

```python
from pyprocessor.utils.validation_manager import validate_object

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

# Validate an object against the schema
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
```

## Integration with Other Systems

The validation system works closely with other systems in PyProcessor:

- **Error Handling**: Validation errors are handled by the error handling system.
- **Logging**: Validation operations are logged using the logging system.
- **Configuration**: The validation system is used to validate configuration values.

```python
from pyprocessor.utils.config_manager import Config
from pyprocessor.utils.validation_manager import validate_object

# Define a schema for the configuration
config_schema = {
    "output_folder": {
        "type": "path",
        "must_exist": True,
        "must_be_dir": True,
        "required": True
    },
    "max_parallel_jobs": {
        "type": "number",
        "min_value": 1,
        "max_value": 16,
        "integer_only": True,
        "required": True
    },
    "ffmpeg_params": {
        "type": "dict",
        "required": True
    }
}

# Validate the configuration
config = Config()
result = validate_object(config.to_dict(), config_schema, field="config")
```

## Best Practices

1. **Use Field Names**: Always provide field names to validation functions to get more descriptive error messages.
2. **Use Schema Validation**: Use schema validation for complex objects to ensure all fields are properly validated.
3. **Handle Validation Errors**: Always check the validation result and handle errors appropriately.
4. **Use Custom Rules**: Create custom validation rules for domain-specific validation.
5. **Validate Early**: Validate inputs as early as possible to catch errors before they cause problems.
6. **Validate Thoroughly**: Validate all inputs, even those that come from trusted sources.
7. **Use Required Flag**: Use the `required` flag to indicate whether a value is required.
8. **Use Appropriate Validation**: Use the appropriate validation function for each type of input.
9. **Combine Validations**: Use the `merge` method to combine validation results from multiple validations.
10. **Log Validation Errors**: Log validation errors to help with debugging.

## Example: Form Validation

Here's an example of using the validation system to validate a form:

```python
from pyprocessor.utils.validation_manager import (
    validate_string,
    validate_number,
    validate_email,
    validate_boolean,
    ValidationResult
)

def validate_form(form_data):
    """Validate a form."""
    result = ValidationResult()
    
    # Validate name
    name_result = validate_string(
        form_data.get("name"),
        field="name",
        min_length=3,
        max_length=50,
        required=True
    )
    result.merge(name_result)
    
    # Validate age
    age_result = validate_number(
        form_data.get("age"),
        field="age",
        min_value=18,
        integer_only=True,
        required=True
    )
    result.merge(age_result)
    
    # Validate email
    email_result = validate_email(
        form_data.get("email"),
        field="email",
        required=True
    )
    result.merge(email_result)
    
    # Validate terms
    terms_result = validate_boolean(
        form_data.get("terms"),
        field="terms",
        required=True
    )
    result.merge(terms_result)
    
    # If terms is False, add an error
    if form_data.get("terms") is False:
        result.add_error("You must accept the terms and conditions", "terms")
    
    return result

# Example usage
form_data = {
    "name": "John Doe",
    "age": 30,
    "email": "john@example.com",
    "terms": True
}

result = validate_form(form_data)

if result:
    print("Form is valid")
else:
    print("Form is invalid")
    for error in result.errors:
        print(f"Error in {error.field}: {error.message}")
```

## Troubleshooting

If you encounter issues with the validation system, try the following:

1. **Check Input Types**: Make sure you're passing the correct types to validation functions.
2. **Check Field Names**: Make sure you're using consistent field names.
3. **Check Validation Rules**: Make sure your custom validation rules are working correctly.
4. **Check Schema**: Make sure your schema is correctly defined.
5. **Check Required Fields**: Make sure you're setting the `required` flag correctly.
6. **Check Error Messages**: Look at the error messages to understand what's wrong.
7. **Check Logs**: Look for error messages in the application logs.
8. **Simplify Validation**: Try simplifying your validation to isolate the issue.
9. **Test Individually**: Test each validation function individually to isolate the issue.
10. **Update Validation Rules**: Update your validation rules if they're not working as expected.
