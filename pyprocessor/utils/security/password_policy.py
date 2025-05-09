"""
Password policy for PyProcessor.

This module provides password policy enforcement and password generation.
"""

import secrets
import string
import threading
from typing import Optional, Tuple

from pyprocessor.utils.logging.log_manager import get_logger


class PasswordPolicy:
    """
    Password policy for user authentication.

    This class provides password policy enforcement and password generation.
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        """Create a new instance of PasswordPolicy or return the existing one."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PasswordPolicy, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the password policy."""
        # Only initialize once
        if self._initialized:
            return

        # Get logger
        self.logger = get_logger()

        # Initialize configuration
        self.min_length = 8
        self.max_length = 128
        self.require_uppercase = True
        self.require_lowercase = True
        self.require_digits = True
        self.require_special = True
        self.disallow_common = True
        self.disallow_username = True
        self.disallow_sequential = True
        self.disallow_repeated = True
        self.max_repeated_chars = 3
        self.common_passwords = set()

        # Mark as initialized
        self._initialized = True
        self.logger.debug("Password policy initialized")

    def initialize(self, config=None):
        """
        Initialize the password policy with configuration.

        Args:
            config: Configuration object or dictionary
        """
        # Apply configuration if provided
        if config:
            if hasattr(config, "get"):
                # Config is a dictionary-like object
                self.min_length = config.get(
                    "security.password_policy.min_length", self.min_length
                )
                self.max_length = config.get(
                    "security.password_policy.max_length", self.max_length
                )
                self.require_uppercase = config.get(
                    "security.password_policy.require_uppercase", self.require_uppercase
                )
                self.require_lowercase = config.get(
                    "security.password_policy.require_lowercase", self.require_lowercase
                )
                self.require_digits = config.get(
                    "security.password_policy.require_digits", self.require_digits
                )
                self.require_special = config.get(
                    "security.password_policy.require_special", self.require_special
                )
                self.disallow_common = config.get(
                    "security.password_policy.disallow_common", self.disallow_common
                )
                self.disallow_username = config.get(
                    "security.password_policy.disallow_username", self.disallow_username
                )
                self.disallow_sequential = config.get(
                    "security.password_policy.disallow_sequential",
                    self.disallow_sequential,
                )
                self.disallow_repeated = config.get(
                    "security.password_policy.disallow_repeated", self.disallow_repeated
                )
                self.max_repeated_chars = config.get(
                    "security.password_policy.max_repeated_chars",
                    self.max_repeated_chars,
                )

        # Load common passwords
        self._load_common_passwords()

        self.logger.info("Password policy initialized with configuration")

    def _load_common_passwords(self):
        """Load common passwords from built-in list."""
        # This is a small subset of common passwords for demonstration
        # In a production environment, you would load a more comprehensive list
        common_passwords = [
            "password",
            "123456",
            "12345678",
            "qwerty",
            "abc123",
            "monkey",
            "1234567",
            "letmein",
            "trustno1",
            "dragon",
            "baseball",
            "111111",
            "iloveyou",
            "master",
            "sunshine",
            "ashley",
            "bailey",
            "passw0rd",
            "shadow",
            "123123",
            "654321",
            "superman",
            "qazwsx",
            "michael",
            "football",
            "welcome",
            "jesus",
            "ninja",
            "mustang",
            "password1",
        ]

        self.common_passwords = set(common_passwords)
        self.logger.debug(f"Loaded {len(self.common_passwords)} common passwords")

    def validate_password(
        self, password: str, username: str = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a password against the password policy.

        Args:
            password: Password to validate
            username: Username (for username-based checks)

        Returns:
            Tuple containing:
            - bool: True if password is valid, False otherwise
            - Optional[str]: Error message if password is invalid, None otherwise
        """
        # Check password length
        if len(password) < self.min_length:
            return False, f"Password must be at least {self.min_length} characters long"

        if len(password) > self.max_length:
            return False, f"Password must be at most {self.max_length} characters long"

        # Check character requirements
        if self.require_uppercase and not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"

        if self.require_lowercase and not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"

        if self.require_digits and not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit"

        if self.require_special and not any(c in string.punctuation for c in password):
            return False, "Password must contain at least one special character"

        # Check for common passwords
        if self.disallow_common and password.lower() in self.common_passwords:
            return False, "Password is too common"

        # Check for username in password
        if self.disallow_username and username and username.lower() in password.lower():
            return False, "Password must not contain the username"

        # Check for sequential characters
        if self.disallow_sequential:
            # Check for sequential letters
            for i in range(len(password) - 2):
                if ord(password[i].lower()) + 1 == ord(password[i + 1].lower()) and ord(
                    password[i + 1].lower()
                ) + 1 == ord(password[i + 2].lower()):
                    return False, "Password must not contain sequential characters"

            # Check for sequential digits
            for i in range(len(password) - 2):
                if (
                    password[i].isdigit()
                    and password[i + 1].isdigit()
                    and password[i + 2].isdigit()
                    and int(password[i]) + 1 == int(password[i + 1])
                    and int(password[i + 1]) + 1 == int(password[i + 2])
                ):
                    return False, "Password must not contain sequential digits"

        # Check for repeated characters
        if self.disallow_repeated:
            for i in range(len(password) - (self.max_repeated_chars - 1)):
                if all(
                    password[i] == password[i + j]
                    for j in range(1, self.max_repeated_chars)
                ):
                    return (
                        False,
                        f"Password must not contain more than {self.max_repeated_chars - 1} repeated characters",
                    )

        return True, None

    def generate_password(self, length: int = None) -> str:
        """
        Generate a password that meets the password policy.

        Args:
            length: Password length (default: min_length + 4)

        Returns:
            str: Generated password
        """
        if length is None:
            length = self.min_length + 4

        # Ensure length is within bounds
        length = max(length, self.min_length)
        length = min(length, self.max_length)

        # Define character sets
        uppercase_chars = string.ascii_uppercase
        lowercase_chars = string.ascii_lowercase
        digit_chars = string.digits
        special_chars = "!@#$%^&*()-_=+[]{}|;:,.<>?"

        # Create a list of all allowed characters
        all_chars = ""
        if self.require_uppercase:
            all_chars += uppercase_chars
        if self.require_lowercase:
            all_chars += lowercase_chars
        if self.require_digits:
            all_chars += digit_chars
        if self.require_special:
            all_chars += special_chars

        # If no character sets are required, use a default set
        if not all_chars:
            all_chars = string.ascii_letters + string.digits

        # Generate password
        while True:
            # Start with one character from each required set
            password_chars = []

            if self.require_uppercase:
                password_chars.append(secrets.choice(uppercase_chars))

            if self.require_lowercase:
                password_chars.append(secrets.choice(lowercase_chars))

            if self.require_digits:
                password_chars.append(secrets.choice(digit_chars))

            if self.require_special:
                password_chars.append(secrets.choice(special_chars))

            # Fill the rest with random characters
            remaining_length = length - len(password_chars)
            password_chars.extend(
                secrets.choice(all_chars) for _ in range(remaining_length)
            )

            # Shuffle the characters
            secrets.SystemRandom().shuffle(password_chars)

            # Create the password
            password = "".join(password_chars)

            # Validate the password
            valid, _ = self.validate_password(password)

            if valid:
                return password


def get_password_policy() -> PasswordPolicy:
    """
    Get the password policy instance.

    Returns:
        PasswordPolicy: Password policy instance
    """
    return PasswordPolicy()


def validate_password(
    password: str, username: str = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate a password against the password policy.

    Args:
        password: Password to validate
        username: Username (for username-based checks)

    Returns:
        Tuple containing:
        - bool: True if password is valid, False otherwise
        - Optional[str]: Error message if password is invalid, None otherwise
    """
    return get_password_policy().validate_password(password, username)


def generate_password(length: int = None) -> str:
    """
    Generate a password that meets the password policy.

    Args:
        length: Password length (default: min_length + 4)

    Returns:
        str: Generated password
    """
    return get_password_policy().generate_password(length)
