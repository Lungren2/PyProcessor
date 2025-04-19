"""
Security manager for PyProcessor.

This module provides a central manager for all security-related functionality.
"""

import threading
from typing import Dict, List, Optional, Any, Tuple

from pyprocessor.utils.logging.log_manager import get_logger
from pyprocessor.utils.security.auth_manager import AuthManager, get_auth_manager
from pyprocessor.utils.security.session_manager import SessionManager, get_session_manager
from pyprocessor.utils.security.api_key_manager import ApiKeyManager, get_api_key_manager
from pyprocessor.utils.security.audit_logger import AuditLogger, get_audit_logger
from pyprocessor.utils.security.password_policy import PasswordPolicy, get_password_policy
from pyprocessor.utils.security.encryption_manager import EncryptionManager, get_encryption_manager
from pyprocessor.utils.security.process_sandbox import ProcessSandbox, get_process_sandbox


class SecurityManager:
    """
    Central manager for all security-related functionality.

    This class provides a unified interface for authentication, authorization,
    session management, API key management, audit logging, and password policy
    enforcement.
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        """Create a new instance of SecurityManager or return the existing one."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SecurityManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the security manager."""
        # Only initialize once
        if self._initialized:
            return

        # Get logger
        self.logger = get_logger()

        # Initialize components
        self.auth_manager = get_auth_manager()
        self.session_manager = get_session_manager()
        self.api_key_manager = get_api_key_manager()
        self.audit_logger = get_audit_logger()
        self.password_policy = get_password_policy()
        self.encryption_manager = get_encryption_manager()
        self.process_sandbox = get_process_sandbox()

        # Mark as initialized
        self._initialized = True
        self.logger.debug("Security manager initialized")

    def initialize(self, config=None):
        """
        Initialize the security manager with configuration.

        Args:
            config: Configuration object or dictionary
        """
        # Initialize components with configuration
        self.auth_manager.initialize(config)
        self.session_manager.initialize(config)
        self.api_key_manager.initialize(config)
        self.audit_logger.initialize(config)
        self.password_policy.initialize(config)
        self.encryption_manager.initialize(config)
        # Process sandbox doesn't have an initialize method, but we can configure it here if needed

        self.logger.info("Security manager initialized with configuration")

    def shutdown(self):
        """Shutdown the security manager."""
        # Shutdown components
        self.auth_manager.shutdown()
        self.session_manager.shutdown()
        self.api_key_manager.shutdown()
        self.audit_logger.shutdown()
        # No shutdown needed for encryption manager
        # Shutdown process sandbox
        from pyprocessor.utils.security.process_sandbox import shutdown_process_sandbox
        shutdown_process_sandbox()

        self.logger.info("Security manager shutdown")

    # Authentication methods
    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Authenticate a user with username and password.

        Args:
            username: Username
            password: Password

        Returns:
            Tuple containing:
            - bool: True if authentication was successful, False otherwise
            - Optional[str]: Session token if authentication was successful, None otherwise
            - Optional[Dict[str, Any]]: User data if authentication was successful, None otherwise
        """
        # Authenticate user
        success, user_data = self.auth_manager.authenticate(username, password)

        if not success:
            # Log failed authentication
            self.audit_logger.log_auth_event(
                "authentication_failed",
                username=username,
                success=False,
                reason="Invalid credentials"
            )
            return False, None, None

        # Create session
        session_token = self.session_manager.create_session(username, user_data)

        # Log successful authentication
        self.audit_logger.log_auth_event(
            "authentication_succeeded",
            username=username,
            success=True
        )

        return True, session_token, user_data

    def authenticate_api_key(self, api_key: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Authenticate with an API key.

        Args:
            api_key: API key

        Returns:
            Tuple containing:
            - bool: True if authentication was successful, False otherwise
            - Optional[Dict[str, Any]]: User data if authentication was successful, None otherwise
        """
        # Validate API key
        success, key_data = self.api_key_manager.validate_api_key(api_key)

        if not success:
            # Log failed authentication
            self.audit_logger.log_auth_event(
                "api_key_authentication_failed",
                api_key_id=api_key[:8] + "...",
                success=False,
                reason="Invalid API key"
            )
            return False, None

        # Get user data
        user_data = self.auth_manager.get_user(key_data["username"])

        # Log successful authentication
        self.audit_logger.log_auth_event(
            "api_key_authentication_succeeded",
            username=key_data["username"],
            api_key_id=key_data["id"],
            success=True
        )

        return True, user_data

    def validate_session(self, session_token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate a session token.

        Args:
            session_token: Session token

        Returns:
            Tuple containing:
            - bool: True if session is valid, False otherwise
            - Optional[Dict[str, Any]]: Session data if session is valid, None otherwise
        """
        return self.session_manager.validate_session(session_token)

    def invalidate_session(self, session_token: str) -> bool:
        """
        Invalidate a session token.

        Args:
            session_token: Session token

        Returns:
            bool: True if session was invalidated, False otherwise
        """
        success = self.session_manager.invalidate_session(session_token)

        if success:
            # Log session invalidation
            self.audit_logger.log_auth_event(
                "session_invalidated",
                session_id=session_token[:8] + "...",
                success=True
            )

        return success

    # User management methods
    def create_user(self, username: str, password: str, email: str = None,
                   full_name: str = None, roles: List[str] = None) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Create a new user.

        Args:
            username: Username
            password: Password
            email: Email address
            full_name: Full name
            roles: List of role names

        Returns:
            Tuple containing:
            - bool: True if user was created, False otherwise
            - Optional[str]: Error message if user creation failed, None otherwise
            - Optional[Dict[str, Any]]: User data if user was created, None otherwise
        """
        # Validate password against policy
        if not self.password_policy.validate_password(password):
            return False, "Password does not meet policy requirements", None

        # Create user
        success, error, user_data = self.auth_manager.create_user(
            username, password, email, full_name, roles
        )

        if success:
            # Log user creation
            self.audit_logger.log_admin_event(
                "user_created",
                username=username,
                success=True
            )

        return success, error, user_data

    def update_user(self, username: str, password: str = None, email: str = None,
                   full_name: str = None, roles: List[str] = None,
                   active: bool = None) -> Tuple[bool, Optional[str]]:
        """
        Update a user.

        Args:
            username: Username
            password: New password (if changing)
            email: New email address
            full_name: New full name
            roles: New list of role names
            active: New active status

        Returns:
            Tuple containing:
            - bool: True if user was updated, False otherwise
            - Optional[str]: Error message if user update failed, None otherwise
        """
        # Validate password against policy if provided
        if password is not None and not self.password_policy.validate_password(password):
            return False, "Password does not meet policy requirements"

        # Update user
        success, error = self.auth_manager.update_user(
            username, password, email, full_name, roles, active
        )

        if success:
            # Log user update
            self.audit_logger.log_admin_event(
                "user_updated",
                username=username,
                success=True
            )

            # Invalidate all sessions for this user if password was changed or user was deactivated
            if password is not None or (active is not None and not active):
                self.session_manager.invalidate_all_sessions_for_user(username)

        return success, error

    def delete_user(self, username: str) -> bool:
        """
        Delete a user.

        Args:
            username: Username

        Returns:
            bool: True if user was deleted, False otherwise
        """
        # Delete user
        success = self.auth_manager.delete_user(username)

        if success:
            # Log user deletion
            self.audit_logger.log_admin_event(
                "user_deleted",
                username=username,
                success=True
            )

            # Invalidate all sessions for this user
            self.session_manager.invalidate_all_sessions_for_user(username)

            # Revoke all API keys for this user
            self.api_key_manager.revoke_all_keys_for_user(username)

        return success

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user data.

        Args:
            username: Username

        Returns:
            Optional[Dict[str, Any]]: User data if user exists, None otherwise
        """
        return self.auth_manager.get_user(username)

    def list_users(self) -> List[Dict[str, Any]]:
        """
        List all users.

        Returns:
            List[Dict[str, Any]]: List of user data
        """
        return self.auth_manager.list_users()

    # Role and permission methods
    def check_permission(self, username: str, permission: str) -> bool:
        """
        Check if a user has a permission.

        Args:
            username: Username
            permission: Permission name

        Returns:
            bool: True if user has permission, False otherwise
        """
        return self.auth_manager.check_permission(username, permission)

    def assign_role(self, username: str, role_name: str) -> bool:
        """
        Assign a role to a user.

        Args:
            username: Username
            role_name: Role name

        Returns:
            bool: True if role was assigned, False otherwise
        """
        success = self.auth_manager.assign_role(username, role_name)

        if success:
            # Log role assignment
            self.audit_logger.log_admin_event(
                "role_assigned",
                username=username,
                role=role_name,
                success=True
            )

        return success

    def revoke_role(self, username: str, role_name: str) -> bool:
        """
        Revoke a role from a user.

        Args:
            username: Username
            role_name: Role name

        Returns:
            bool: True if role was revoked, False otherwise
        """
        success = self.auth_manager.revoke_role(username, role_name)

        if success:
            # Log role revocation
            self.audit_logger.log_admin_event(
                "role_revoked",
                username=username,
                role=role_name,
                success=True
            )

        return success

    # API key methods
    def create_api_key(self, username: str, description: str = None,
                      expires_in: int = None) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Create an API key for a user.

        Args:
            username: Username
            description: Description of the API key
            expires_in: Expiration time in seconds from now

        Returns:
            Tuple containing:
            - bool: True if API key was created, False otherwise
            - Optional[str]: API key if creation was successful, error message otherwise
            - Optional[Dict[str, Any]]: API key data if creation was successful, None otherwise
        """
        # Check if user exists
        if not self.auth_manager.get_user(username):
            return False, "User does not exist", None

        # Create API key
        success, result, key_data = self.api_key_manager.create_api_key(
            username, description, expires_in
        )

        if success:
            # Log API key creation
            self.audit_logger.log_admin_event(
                "api_key_created",
                username=username,
                api_key_id=key_data["id"],
                success=True
            )

        return success, result, key_data

    def revoke_api_key(self, api_key_id: str) -> bool:
        """
        Revoke an API key.

        Args:
            api_key_id: API key ID

        Returns:
            bool: True if API key was revoked, False otherwise
        """
        # Get API key data
        key_data = self.api_key_manager.get_api_key(api_key_id)
        if not key_data:
            return False

        # Revoke API key
        success = self.api_key_manager.revoke_api_key(api_key_id)

        if success:
            # Log API key revocation
            self.audit_logger.log_admin_event(
                "api_key_revoked",
                username=key_data["username"],
                api_key_id=api_key_id,
                success=True
            )

        return success

    def list_api_keys(self, username: str = None) -> List[Dict[str, Any]]:
        """
        List API keys.

        Args:
            username: Username to filter by

        Returns:
            List[Dict[str, Any]]: List of API key data
        """
        return self.api_key_manager.list_api_keys(username)

    # Password policy methods
    def validate_password(self, password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a password against the password policy.

        Args:
            password: Password to validate

        Returns:
            Tuple containing:
            - bool: True if password is valid, False otherwise
            - Optional[str]: Error message if password is invalid, None otherwise
        """
        return self.password_policy.validate_password(password)

    def generate_password(self) -> str:
        """
        Generate a password that meets the password policy.

        Returns:
            str: Generated password
        """
        return self.password_policy.generate_password()


def get_security_manager() -> SecurityManager:
    """
    Get the security manager instance.

    Returns:
        SecurityManager: Security manager instance
    """
    return SecurityManager()
