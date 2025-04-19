"""
API key management for PyProcessor.

This module provides API key management functionality for programmatic access.
"""

import json
import os
import threading
import time
import uuid
import secrets
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from pyprocessor.utils.logging.log_manager import get_logger
from pyprocessor.utils.file_system.path_utils import (
    normalize_path, ensure_dir_exists, get_user_data_dir
)


class ApiKey:
    """API key model for programmatic access."""

    def __init__(self, id: str, key_hash: str, username: str, 
                description: str = None, created_at: float = None,
                expires_at: float = None, last_used: float = None,
                revoked: bool = False):
        """
        Initialize an API key.

        Args:
            id: API key ID
            key_hash: Hashed API key
            username: Username
            description: Description
            created_at: Creation timestamp
            expires_at: Expiration timestamp
            last_used: Last used timestamp
            revoked: Whether the key is revoked
        """
        self.id = id
        self.key_hash = key_hash
        self.username = username
        self.description = description
        self.created_at = created_at or time.time()
        self.expires_at = expires_at
        self.last_used = last_used
        self.revoked = revoked

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert API key to dictionary.

        Returns:
            Dict[str, Any]: API key data
        """
        return {
            "id": self.id,
            "key_hash": self.key_hash,
            "username": self.username,
            "description": self.description,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "last_used": self.last_used,
            "revoked": self.revoked
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApiKey':
        """
        Create API key from dictionary.

        Args:
            data: API key data

        Returns:
            ApiKey: API key object
        """
        return cls(
            id=data["id"],
            key_hash=data["key_hash"],
            username=data["username"],
            description=data.get("description"),
            created_at=data.get("created_at"),
            expires_at=data.get("expires_at"),
            last_used=data.get("last_used"),
            revoked=data.get("revoked", False)
        )

    def is_expired(self) -> bool:
        """
        Check if the API key is expired.

        Returns:
            bool: True if API key is expired, False otherwise
        """
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def is_valid(self) -> bool:
        """
        Check if the API key is valid.

        Returns:
            bool: True if API key is valid, False otherwise
        """
        return not self.revoked and not self.is_expired()

    def update_last_used(self):
        """Update the last used timestamp."""
        self.last_used = time.time()


class ApiKeyManager:
    """
    API key manager for programmatic access.

    This class provides API key creation, validation, and management.
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        """Create a new instance of ApiKeyManager or return the existing one."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ApiKeyManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the API key manager."""
        # Only initialize once
        if self._initialized:
            return

        # Get logger
        self.logger = get_logger()

        # Initialize data
        self.api_keys: Dict[str, ApiKey] = {}

        # Initialize default paths
        self.data_dir = Path(get_user_data_dir()) / "security"
        self.api_keys_file = self.data_dir / "api_keys.json"

        # Initialize configuration
        self.default_expiry = 365 * 24 * 60 * 60  # 1 year in seconds
        self.cleanup_interval = 24 * 60 * 60  # 1 day in seconds
        self.last_cleanup = time.time()

        # Mark as initialized
        self._initialized = True
        self.logger.debug("API key manager initialized")

    def initialize(self, config=None):
        """
        Initialize the API key manager with configuration.

        Args:
            config: Configuration object or dictionary
        """
        # Apply configuration if provided
        if config:
            if hasattr(config, "get"):
                # Config is a dictionary-like object
                self.default_expiry = config.get("security.api_key_expiry", self.default_expiry)
                self.cleanup_interval = config.get("security.api_key_cleanup_interval", self.cleanup_interval)
                
                # Get data directory from config if available
                data_dir = config.get("security.data_dir")
                if data_dir:
                    self.data_dir = Path(normalize_path(data_dir))
                    self.api_keys_file = self.data_dir / "api_keys.json"

        # Ensure data directory exists
        ensure_dir_exists(self.data_dir)

        # Load API keys
        self._load_api_keys()

        # Clean up expired API keys
        self._cleanup_api_keys()

        self.logger.info("API key manager initialized with configuration")

    def shutdown(self):
        """Shutdown the API key manager."""
        # Save API keys
        self._save_api_keys()

        self.logger.info("API key manager shutdown")

    def _load_api_keys(self):
        """Load API keys from file."""
        if not self.api_keys_file.exists():
            self.logger.info(f"API keys file not found: {self.api_keys_file}")
            return

        try:
            with open(self.api_keys_file, "r") as f:
                data = json.load(f)
                self.api_keys = {
                    key_id: ApiKey.from_dict(key_data)
                    for key_id, key_data in data.items()
                }
            self.logger.info(f"Loaded {len(self.api_keys)} API keys from {self.api_keys_file}")
        except Exception as e:
            self.logger.error(f"Failed to load API keys: {e}")

    def _save_api_keys(self):
        """Save API keys to file."""
        try:
            data = {
                key_id: api_key.to_dict()
                for key_id, api_key in self.api_keys.items()
            }
            with open(self.api_keys_file, "w") as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"Saved {len(self.api_keys)} API keys to {self.api_keys_file}")
        except Exception as e:
            self.logger.error(f"Failed to save API keys: {e}")

    def _cleanup_api_keys(self):
        """Clean up expired API keys."""
        # Check if cleanup is needed
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return

        # Clean up expired API keys
        expired_keys = [
            key_id for key_id, api_key in self.api_keys.items()
            if api_key.is_expired()
        ]

        for key_id in expired_keys:
            self.api_keys[key_id].revoked = True

        if expired_keys:
            self.logger.info(f"Marked {len(expired_keys)} expired API keys as revoked")

        # Update last cleanup time
        self.last_cleanup = now

        # Save API keys
        self._save_api_keys()

    def create_api_key(self, username: str, description: str = None,
                      expires_in: int = None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Create a new API key.

        Args:
            username: Username
            description: Description
            expires_in: Expiration time in seconds from now

        Returns:
            Tuple containing:
            - bool: True if API key was created, False otherwise
            - str: API key if creation was successful, error message otherwise
            - Dict[str, Any]: API key data if creation was successful, None otherwise
        """
        # Generate a unique ID
        key_id = str(uuid.uuid4())

        # Generate a secure API key
        api_key = f"pk_{secrets.token_urlsafe(32)}"

        # Hash the API key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Calculate expiry time
        expires_at = None
        if expires_in is not None:
            expires_at = time.time() + expires_in
        elif self.default_expiry is not None:
            expires_at = time.time() + self.default_expiry

        # Create API key
        api_key_obj = ApiKey(
            id=key_id,
            key_hash=key_hash,
            username=username,
            description=description,
            expires_at=expires_at
        )

        # Add API key
        self.api_keys[key_id] = api_key_obj

        # Clean up expired API keys
        self._cleanup_api_keys()

        # Save API keys
        self._save_api_keys()

        # Return API key data (without key hash)
        api_key_data = api_key_obj.to_dict()
        api_key_data.pop("key_hash", None)

        self.logger.info(f"API key created for user: {username}")
        return True, api_key, api_key_data

    def validate_api_key(self, api_key: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate an API key.

        Args:
            api_key: API key

        Returns:
            Tuple containing:
            - bool: True if API key is valid, False otherwise
            - Optional[Dict[str, Any]]: API key data if API key is valid, None otherwise
        """
        # Hash the API key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Find the API key
        for key_id, api_key_obj in self.api_keys.items():
            if api_key_obj.key_hash == key_hash:
                # Check if API key is valid
                if not api_key_obj.is_valid():
                    return False, None

                # Update last used
                api_key_obj.update_last_used()

                # Save API keys
                self._save_api_keys()

                # Return API key data (without key hash)
                api_key_data = api_key_obj.to_dict()
                api_key_data.pop("key_hash", None)

                return True, api_key_data

        return False, None

    def revoke_api_key(self, key_id: str) -> bool:
        """
        Revoke an API key.

        Args:
            key_id: API key ID

        Returns:
            bool: True if API key was revoked, False otherwise
        """
        # Check if API key exists
        if key_id not in self.api_keys:
            return False

        # Revoke API key
        self.api_keys[key_id].revoked = True

        # Save API keys
        self._save_api_keys()

        self.logger.info(f"API key revoked: {key_id}")
        return True

    def revoke_all_keys_for_user(self, username: str) -> int:
        """
        Revoke all API keys for a user.

        Args:
            username: Username

        Returns:
            int: Number of API keys revoked
        """
        # Find all API keys for the user
        keys_to_revoke = [
            key_id for key_id, api_key in self.api_keys.items()
            if api_key.username == username and not api_key.revoked
        ]

        # Revoke API keys
        for key_id in keys_to_revoke:
            self.api_keys[key_id].revoked = True

        # Save API keys if any were revoked
        if keys_to_revoke:
            self._save_api_keys()
            self.logger.info(f"Revoked {len(keys_to_revoke)} API keys for user: {username}")

        return len(keys_to_revoke)

    def get_api_key(self, key_id: str) -> Optional[Dict[str, Any]]:
        """
        Get API key data.

        Args:
            key_id: API key ID

        Returns:
            Optional[Dict[str, Any]]: API key data if API key exists, None otherwise
        """
        # Check if API key exists
        if key_id not in self.api_keys:
            return None

        api_key = self.api_keys[key_id]

        # Return API key data (without key hash)
        api_key_data = api_key.to_dict()
        api_key_data.pop("key_hash", None)

        return api_key_data

    def list_api_keys(self, username: str = None) -> List[Dict[str, Any]]:
        """
        List API keys.

        Args:
            username: Username to filter by

        Returns:
            List[Dict[str, Any]]: List of API key data
        """
        # Clean up expired API keys
        self._cleanup_api_keys()

        # Filter API keys by username if provided
        if username:
            return [
                {k: v for k, v in api_key.to_dict().items() if k != "key_hash"}
                for api_key in self.api_keys.values()
                if api_key.username == username
            ]

        # Return all API keys (without key hashes)
        return [
            {k: v for k, v in api_key.to_dict().items() if k != "key_hash"}
            for api_key in self.api_keys.values()
        ]


def get_api_key_manager() -> ApiKeyManager:
    """
    Get the API key manager instance.

    Returns:
        ApiKeyManager: API key manager instance
    """
    return ApiKeyManager()


def create_api_key(username: str, description: str = None,
                  expires_in: int = None) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Create a new API key.

    Args:
        username: Username
        description: Description
        expires_in: Expiration time in seconds from now

    Returns:
        Tuple containing:
        - bool: True if API key was created, False otherwise
        - str: API key if creation was successful, error message otherwise
        - Dict[str, Any]: API key data if creation was successful, None otherwise
    """
    return get_api_key_manager().create_api_key(username, description, expires_in)


def validate_api_key(api_key: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Validate an API key.

    Args:
        api_key: API key

    Returns:
        Tuple containing:
        - bool: True if API key is valid, False otherwise
        - Optional[Dict[str, Any]]: API key data if API key is valid, None otherwise
    """
    return get_api_key_manager().validate_api_key(api_key)


def revoke_api_key(key_id: str) -> bool:
    """
    Revoke an API key.

    Args:
        key_id: API key ID

    Returns:
        bool: True if API key was revoked, False otherwise
    """
    return get_api_key_manager().revoke_api_key(key_id)


def get_api_key(key_id: str) -> Optional[Dict[str, Any]]:
    """
    Get API key data.

    Args:
        key_id: API key ID

    Returns:
        Optional[Dict[str, Any]]: API key data if API key exists, None otherwise
    """
    return get_api_key_manager().get_api_key(key_id)


def list_api_keys(username: str = None) -> List[Dict[str, Any]]:
    """
    List API keys.

    Args:
        username: Username to filter by

    Returns:
        List[Dict[str, Any]]: List of API key data
    """
    return get_api_key_manager().list_api_keys(username)
