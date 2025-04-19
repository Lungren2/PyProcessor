"""
Authentication manager for PyProcessor.

This module provides user authentication and authorization functionality.
"""

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set

import bcrypt

from pyprocessor.utils.logging.log_manager import get_logger
from pyprocessor.utils.file_system.path_utils import (
    normalize_path, ensure_dir_exists, get_user_data_dir
)


class User:
    """User model for authentication and authorization."""

    def __init__(self, username: str, password_hash: str, email: str = None,
                full_name: str = None, roles: List[str] = None, 
                created_at: float = None, updated_at: float = None,
                last_login: float = None, failed_attempts: int = 0,
                locked_until: float = None, active: bool = True):
        """
        Initialize a user.

        Args:
            username: Username
            password_hash: Hashed password
            email: Email address
            full_name: Full name
            roles: List of role names
            created_at: Creation timestamp
            updated_at: Last update timestamp
            last_login: Last login timestamp
            failed_attempts: Number of failed login attempts
            locked_until: Timestamp until which the account is locked
            active: Whether the user is active
        """
        self.username = username
        self.password_hash = password_hash
        self.email = email
        self.full_name = full_name
        self.roles = roles or ["user"]
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or time.time()
        self.last_login = last_login
        self.failed_attempts = failed_attempts
        self.locked_until = locked_until
        self.active = active

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert user to dictionary.

        Returns:
            Dict[str, Any]: User data
        """
        return {
            "username": self.username,
            "password_hash": self.password_hash,
            "email": self.email,
            "full_name": self.full_name,
            "roles": self.roles,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_login": self.last_login,
            "failed_attempts": self.failed_attempts,
            "locked_until": self.locked_until,
            "active": self.active
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """
        Create user from dictionary.

        Args:
            data: User data

        Returns:
            User: User object
        """
        return cls(
            username=data["username"],
            password_hash=data["password_hash"],
            email=data.get("email"),
            full_name=data.get("full_name"),
            roles=data.get("roles", ["user"]),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            last_login=data.get("last_login"),
            failed_attempts=data.get("failed_attempts", 0),
            locked_until=data.get("locked_until"),
            active=data.get("active", True)
        )


class Role:
    """Role model for authorization."""

    def __init__(self, name: str, description: str = None, 
                permissions: List[str] = None):
        """
        Initialize a role.

        Args:
            name: Role name
            description: Role description
            permissions: List of permission names
        """
        self.name = name
        self.description = description
        self.permissions = permissions or []

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert role to dictionary.

        Returns:
            Dict[str, Any]: Role data
        """
        return {
            "name": self.name,
            "description": self.description,
            "permissions": self.permissions
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Role':
        """
        Create role from dictionary.

        Args:
            data: Role data

        Returns:
            Role: Role object
        """
        return cls(
            name=data["name"],
            description=data.get("description"),
            permissions=data.get("permissions", [])
        )


class Permission:
    """Permission model for authorization."""

    def __init__(self, name: str, description: str = None):
        """
        Initialize a permission.

        Args:
            name: Permission name
            description: Permission description
        """
        self.name = name
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert permission to dictionary.

        Returns:
            Dict[str, Any]: Permission data
        """
        return {
            "name": self.name,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Permission':
        """
        Create permission from dictionary.

        Args:
            data: Permission data

        Returns:
            Permission: Permission object
        """
        return cls(
            name=data["name"],
            description=data.get("description")
        )


class AuthManager:
    """
    Authentication and authorization manager.

    This class provides user authentication, role-based access control,
    and permission management.
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        """Create a new instance of AuthManager or return the existing one."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AuthManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the authentication manager."""
        # Only initialize once
        if self._initialized:
            return

        # Get logger
        self.logger = get_logger()

        # Initialize data
        self.users: Dict[str, User] = {}
        self.roles: Dict[str, Role] = {}
        self.permissions: Dict[str, Permission] = {}

        # Initialize default paths
        self.data_dir = Path(get_user_data_dir()) / "security"
        self.users_file = self.data_dir / "users.json"
        self.roles_file = self.data_dir / "roles.json"
        self.permissions_file = self.data_dir / "permissions.json"

        # Initialize configuration
        self.max_failed_attempts = 5
        self.lockout_duration = 15 * 60  # 15 minutes in seconds
        self.password_hash_rounds = 12

        # Mark as initialized
        self._initialized = True
        self.logger.debug("Authentication manager initialized")

    def initialize(self, config=None):
        """
        Initialize the authentication manager with configuration.

        Args:
            config: Configuration object or dictionary
        """
        # Apply configuration if provided
        if config:
            if hasattr(config, "get"):
                # Config is a dictionary-like object
                self.max_failed_attempts = config.get("security.max_failed_attempts", self.max_failed_attempts)
                self.lockout_duration = config.get("security.lockout_duration", self.lockout_duration)
                self.password_hash_rounds = config.get("security.password_hash_rounds", self.password_hash_rounds)
                
                # Get data directory from config if available
                data_dir = config.get("security.data_dir")
                if data_dir:
                    self.data_dir = Path(normalize_path(data_dir))
                    self.users_file = self.data_dir / "users.json"
                    self.roles_file = self.data_dir / "roles.json"
                    self.permissions_file = self.data_dir / "permissions.json"

        # Ensure data directory exists
        ensure_dir_exists(self.data_dir)

        # Load data
        self._load_permissions()
        self._load_roles()
        self._load_users()

        # Create default data if not exists
        self._create_default_permissions()
        self._create_default_roles()
        self._create_default_admin()

        self.logger.info("Authentication manager initialized with configuration")

    def shutdown(self):
        """Shutdown the authentication manager."""
        # Save data
        self._save_users()
        self._save_roles()
        self._save_permissions()

        self.logger.info("Authentication manager shutdown")

    def _load_users(self):
        """Load users from file."""
        if not self.users_file.exists():
            self.logger.info(f"Users file not found: {self.users_file}")
            return

        try:
            with open(self.users_file, "r") as f:
                data = json.load(f)
                self.users = {
                    username: User.from_dict(user_data)
                    for username, user_data in data.items()
                }
            self.logger.info(f"Loaded {len(self.users)} users from {self.users_file}")
        except Exception as e:
            self.logger.error(f"Failed to load users: {e}")

    def _save_users(self):
        """Save users to file."""
        try:
            data = {
                username: user.to_dict()
                for username, user in self.users.items()
            }
            with open(self.users_file, "w") as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"Saved {len(self.users)} users to {self.users_file}")
        except Exception as e:
            self.logger.error(f"Failed to save users: {e}")

    def _load_roles(self):
        """Load roles from file."""
        if not self.roles_file.exists():
            self.logger.info(f"Roles file not found: {self.roles_file}")
            return

        try:
            with open(self.roles_file, "r") as f:
                data = json.load(f)
                self.roles = {
                    name: Role.from_dict(role_data)
                    for name, role_data in data.items()
                }
            self.logger.info(f"Loaded {len(self.roles)} roles from {self.roles_file}")
        except Exception as e:
            self.logger.error(f"Failed to load roles: {e}")

    def _save_roles(self):
        """Save roles to file."""
        try:
            data = {
                name: role.to_dict()
                for name, role in self.roles.items()
            }
            with open(self.roles_file, "w") as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"Saved {len(self.roles)} roles to {self.roles_file}")
        except Exception as e:
            self.logger.error(f"Failed to save roles: {e}")

    def _load_permissions(self):
        """Load permissions from file."""
        if not self.permissions_file.exists():
            self.logger.info(f"Permissions file not found: {self.permissions_file}")
            return

        try:
            with open(self.permissions_file, "r") as f:
                data = json.load(f)
                self.permissions = {
                    name: Permission.from_dict(permission_data)
                    for name, permission_data in data.items()
                }
            self.logger.info(f"Loaded {len(self.permissions)} permissions from {self.permissions_file}")
        except Exception as e:
            self.logger.error(f"Failed to load permissions: {e}")

    def _save_permissions(self):
        """Save permissions to file."""
        try:
            data = {
                name: permission.to_dict()
                for name, permission in self.permissions.items()
            }
            with open(self.permissions_file, "w") as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"Saved {len(self.permissions)} permissions to {self.permissions_file}")
        except Exception as e:
            self.logger.error(f"Failed to save permissions: {e}")

    def _create_default_permissions(self):
        """Create default permissions if they don't exist."""
        default_permissions = [
            Permission("user.view", "View user information"),
            Permission("user.create", "Create users"),
            Permission("user.update", "Update users"),
            Permission("user.delete", "Delete users"),
            Permission("role.view", "View roles"),
            Permission("role.create", "Create roles"),
            Permission("role.update", "Update roles"),
            Permission("role.delete", "Delete roles"),
            Permission("permission.view", "View permissions"),
            Permission("permission.create", "Create permissions"),
            Permission("permission.update", "Update permissions"),
            Permission("permission.delete", "Delete permissions"),
            Permission("api_key.view", "View API keys"),
            Permission("api_key.create", "Create API keys"),
            Permission("api_key.delete", "Delete API keys"),
            Permission("session.view", "View sessions"),
            Permission("session.delete", "Delete sessions"),
            Permission("audit_log.view", "View audit logs"),
            Permission("config.view", "View configuration"),
            Permission("config.update", "Update configuration"),
            Permission("media.process", "Process media files"),
            Permission("media.view", "View media files"),
            Permission("media.upload", "Upload media files"),
            Permission("media.download", "Download media files"),
            Permission("media.delete", "Delete media files"),
            Permission("plugin.view", "View plugins"),
            Permission("plugin.enable", "Enable plugins"),
            Permission("plugin.disable", "Disable plugins"),
            Permission("plugin.install", "Install plugins"),
            Permission("plugin.uninstall", "Uninstall plugins"),
            Permission("system.view", "View system information"),
            Permission("system.update", "Update system"),
            Permission("system.restart", "Restart system"),
            Permission("system.shutdown", "Shutdown system"),
        ]

        for permission in default_permissions:
            if permission.name not in self.permissions:
                self.permissions[permission.name] = permission
                self.logger.debug(f"Created default permission: {permission.name}")

        # Save permissions
        self._save_permissions()

    def _create_default_roles(self):
        """Create default roles if they don't exist."""
        default_roles = [
            Role("admin", "Administrator with full access", [
                # All permissions
                permission.name for permission in self.permissions.values()
            ]),
            Role("user", "Regular user", [
                "media.process",
                "media.view",
                "media.upload",
                "media.download",
                "media.delete",
                "config.view",
                "plugin.view",
                "system.view",
            ]),
            Role("guest", "Guest user with limited access", [
                "media.view",
                "media.download",
                "config.view",
                "plugin.view",
                "system.view",
            ]),
        ]

        for role in default_roles:
            if role.name not in self.roles:
                self.roles[role.name] = role
                self.logger.debug(f"Created default role: {role.name}")

        # Save roles
        self._save_roles()

    def _create_default_admin(self):
        """Create default admin user if no users exist."""
        if not self.users:
            # Generate a random password for the admin user
            import random
            import string
            password = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
            
            # Create admin user
            self.create_user(
                username="admin",
                password=password,
                email=None,
                full_name="Administrator",
                roles=["admin"]
            )
            
            self.logger.warning(f"Created default admin user with username 'admin' and password '{password}'")
            self.logger.warning("Please change the admin password immediately!")

    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Authenticate a user with username and password.

        Args:
            username: Username
            password: Password

        Returns:
            Tuple containing:
            - bool: True if authentication was successful, False otherwise
            - Optional[Dict[str, Any]]: User data if authentication was successful, None otherwise
        """
        # Check if user exists
        if username not in self.users:
            self.logger.warning(f"Authentication failed: User not found: {username}")
            return False, None

        user = self.users[username]

        # Check if user is active
        if not user.active:
            self.logger.warning(f"Authentication failed: User is not active: {username}")
            return False, None

        # Check if account is locked
        if user.locked_until and user.locked_until > time.time():
            self.logger.warning(f"Authentication failed: Account is locked: {username}")
            return False, None

        # Verify password
        if not verify_password(password, user.password_hash):
            # Increment failed attempts
            user.failed_attempts += 1
            user.updated_at = time.time()

            # Lock account if too many failed attempts
            if user.failed_attempts >= self.max_failed_attempts:
                user.locked_until = time.time() + self.lockout_duration
                self.logger.warning(f"Account locked due to too many failed attempts: {username}")

            # Save users
            self._save_users()

            self.logger.warning(f"Authentication failed: Invalid password for user: {username}")
            return False, None

        # Authentication successful
        # Reset failed attempts and update last login
        user.failed_attempts = 0
        user.last_login = time.time()
        user.updated_at = time.time()

        # Save users
        self._save_users()

        # Return user data (without password hash)
        user_data = user.to_dict()
        user_data.pop("password_hash", None)

        self.logger.info(f"Authentication successful: {username}")
        return True, user_data

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
        # Check if username is valid
        if not username or not isinstance(username, str) or len(username) < 3:
            return False, "Username must be at least 3 characters", None

        # Check if username already exists
        if username in self.users:
            return False, f"Username already exists: {username}", None

        # Validate roles
        if roles:
            for role_name in roles:
                if role_name not in self.roles:
                    return False, f"Role does not exist: {role_name}", None
        else:
            # Default role
            roles = ["user"]

        # Hash password
        password_hash = hash_password(password)

        # Create user
        user = User(
            username=username,
            password_hash=password_hash,
            email=email,
            full_name=full_name,
            roles=roles
        )

        # Add user
        self.users[username] = user

        # Save users
        self._save_users()

        # Return user data (without password hash)
        user_data = user.to_dict()
        user_data.pop("password_hash", None)

        self.logger.info(f"User created: {username}")
        return True, None, user_data

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
        # Check if user exists
        if username not in self.users:
            return False, f"User not found: {username}"

        user = self.users[username]

        # Update password if provided
        if password:
            user.password_hash = hash_password(password)

        # Update email if provided
        if email is not None:
            user.email = email

        # Update full name if provided
        if full_name is not None:
            user.full_name = full_name

        # Update roles if provided
        if roles is not None:
            # Validate roles
            for role_name in roles:
                if role_name not in self.roles:
                    return False, f"Role does not exist: {role_name}"
            user.roles = roles

        # Update active status if provided
        if active is not None:
            user.active = active

        # Update timestamp
        user.updated_at = time.time()

        # Save users
        self._save_users()

        self.logger.info(f"User updated: {username}")
        return True, None

    def delete_user(self, username: str) -> bool:
        """
        Delete a user.

        Args:
            username: Username

        Returns:
            bool: True if user was deleted, False otherwise
        """
        # Check if user exists
        if username not in self.users:
            return False

        # Delete user
        del self.users[username]

        # Save users
        self._save_users()

        self.logger.info(f"User deleted: {username}")
        return True

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user data.

        Args:
            username: Username

        Returns:
            Optional[Dict[str, Any]]: User data if user exists, None otherwise
        """
        # Check if user exists
        if username not in self.users:
            return None

        user = self.users[username]

        # Return user data (without password hash)
        user_data = user.to_dict()
        user_data.pop("password_hash", None)

        return user_data

    def list_users(self) -> List[Dict[str, Any]]:
        """
        List all users.

        Returns:
            List[Dict[str, Any]]: List of user data
        """
        # Return user data (without password hashes)
        return [
            {k: v for k, v in user.to_dict().items() if k != "password_hash"}
            for user in self.users.values()
        ]

    def check_permission(self, username: str, permission: str) -> bool:
        """
        Check if a user has a permission.

        Args:
            username: Username
            permission: Permission name

        Returns:
            bool: True if user has permission, False otherwise
        """
        # Check if user exists
        if username not in self.users:
            return False

        user = self.users[username]

        # Check if user is active
        if not user.active:
            return False

        # Check if user has admin role (admin has all permissions)
        if "admin" in user.roles:
            return True

        # Get all permissions for user's roles
        user_permissions: Set[str] = set()
        for role_name in user.roles:
            if role_name in self.roles:
                role = self.roles[role_name]
                user_permissions.update(role.permissions)

        # Check if user has the permission
        return permission in user_permissions

    def assign_role(self, username: str, role_name: str) -> bool:
        """
        Assign a role to a user.

        Args:
            username: Username
            role_name: Role name

        Returns:
            bool: True if role was assigned, False otherwise
        """
        # Check if user exists
        if username not in self.users:
            return False

        # Check if role exists
        if role_name not in self.roles:
            return False

        user = self.users[username]

        # Check if user already has the role
        if role_name in user.roles:
            return True

        # Assign role
        user.roles.append(role_name)
        user.updated_at = time.time()

        # Save users
        self._save_users()

        self.logger.info(f"Role assigned to user: {role_name} -> {username}")
        return True

    def revoke_role(self, username: str, role_name: str) -> bool:
        """
        Revoke a role from a user.

        Args:
            username: Username
            role_name: Role name

        Returns:
            bool: True if role was revoked, False otherwise
        """
        # Check if user exists
        if username not in self.users:
            return False

        user = self.users[username]

        # Check if user has the role
        if role_name not in user.roles:
            return True

        # Revoke role
        user.roles.remove(role_name)
        user.updated_at = time.time()

        # Save users
        self._save_users()

        self.logger.info(f"Role revoked from user: {role_name} -> {username}")
        return True


def get_auth_manager() -> AuthManager:
    """
    Get the authentication manager instance.

    Returns:
        AuthManager: Authentication manager instance
    """
    return AuthManager()


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Password to hash

    Returns:
        str: Hashed password
    """
    # Generate a salt and hash the password
    salt = bcrypt.gensalt(rounds=get_auth_manager().password_hash_rounds)
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        password: Password to verify
        password_hash: Hashed password

    Returns:
        bool: True if password matches hash, False otherwise
    """
    try:
        # Verify the password
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except Exception:
        return False


def authenticate(username: str, password: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Authenticate a user with username and password.

    Args:
        username: Username
        password: Password

    Returns:
        Tuple containing:
        - bool: True if authentication was successful, False otherwise
        - Optional[Dict[str, Any]]: User data if authentication was successful, None otherwise
    """
    return get_auth_manager().authenticate(username, password)


def create_user(username: str, password: str, email: str = None,
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
    return get_auth_manager().create_user(username, password, email, full_name, roles)


def update_user(username: str, password: str = None, email: str = None,
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
    return get_auth_manager().update_user(username, password, email, full_name, roles, active)


def delete_user(username: str) -> bool:
    """
    Delete a user.

    Args:
        username: Username

    Returns:
        bool: True if user was deleted, False otherwise
    """
    return get_auth_manager().delete_user(username)


def get_user(username: str) -> Optional[Dict[str, Any]]:
    """
    Get user data.

    Args:
        username: Username

    Returns:
        Optional[Dict[str, Any]]: User data if user exists, None otherwise
    """
    return get_auth_manager().get_user(username)


def list_users() -> List[Dict[str, Any]]:
    """
    List all users.

    Returns:
        List[Dict[str, Any]]: List of user data
    """
    return get_auth_manager().list_users()


def check_permission(username: str, permission: str) -> bool:
    """
    Check if a user has a permission.

    Args:
        username: Username
        permission: Permission name

    Returns:
        bool: True if user has permission, False otherwise
    """
    return get_auth_manager().check_permission(username, permission)


def assign_role(username: str, role_name: str) -> bool:
    """
    Assign a role to a user.

    Args:
        username: Username
        role_name: Role name

    Returns:
        bool: True if role was assigned, False otherwise
    """
    return get_auth_manager().assign_role(username, role_name)


def revoke_role(username: str, role_name: str) -> bool:
    """
    Revoke a role from a user.

    Args:
        username: Username
        role_name: Role name

    Returns:
        bool: True if role was revoked, False otherwise
    """
    return get_auth_manager().revoke_role(username, role_name)
