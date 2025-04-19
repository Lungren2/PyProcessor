"""
Session management for PyProcessor.

This module provides session management functionality for user authentication.
"""

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from pyprocessor.utils.logging.log_manager import get_logger
from pyprocessor.utils.file_system.path_utils import (
    normalize_path, ensure_dir_exists, get_user_data_dir
)


class Session:
    """Session model for user authentication."""

    def __init__(self, token: str, username: str, user_data: Dict[str, Any],
                created_at: float = None, expires_at: float = None,
                last_activity: float = None, ip_address: str = None,
                user_agent: str = None):
        """
        Initialize a session.

        Args:
            token: Session token
            username: Username
            user_data: User data
            created_at: Creation timestamp
            expires_at: Expiration timestamp
            last_activity: Last activity timestamp
            ip_address: IP address
            user_agent: User agent
        """
        self.token = token
        self.username = username
        self.user_data = user_data
        self.created_at = created_at or time.time()
        self.expires_at = expires_at
        self.last_activity = last_activity or time.time()
        self.ip_address = ip_address
        self.user_agent = user_agent

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert session to dictionary.

        Returns:
            Dict[str, Any]: Session data
        """
        return {
            "token": self.token,
            "username": self.username,
            "user_data": self.user_data,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "last_activity": self.last_activity,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """
        Create session from dictionary.

        Args:
            data: Session data

        Returns:
            Session: Session object
        """
        return cls(
            token=data["token"],
            username=data["username"],
            user_data=data["user_data"],
            created_at=data.get("created_at"),
            expires_at=data.get("expires_at"),
            last_activity=data.get("last_activity"),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent")
        )

    def is_expired(self) -> bool:
        """
        Check if the session is expired.

        Returns:
            bool: True if session is expired, False otherwise
        """
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def update_activity(self):
        """Update the last activity timestamp."""
        self.last_activity = time.time()


class SessionManager:
    """
    Session manager for user authentication.

    This class provides session creation, validation, and management.
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        """Create a new instance of SessionManager or return the existing one."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SessionManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the session manager."""
        # Only initialize once
        if self._initialized:
            return

        # Get logger
        self.logger = get_logger()

        # Initialize data
        self.sessions: Dict[str, Session] = {}

        # Initialize default paths
        self.data_dir = Path(get_user_data_dir()) / "security"
        self.sessions_file = self.data_dir / "sessions.json"

        # Initialize configuration
        self.session_expiry = 24 * 60 * 60  # 24 hours in seconds
        self.cleanup_interval = 60 * 60  # 1 hour in seconds
        self.last_cleanup = time.time()

        # Mark as initialized
        self._initialized = True
        self.logger.debug("Session manager initialized")

    def initialize(self, config=None):
        """
        Initialize the session manager with configuration.

        Args:
            config: Configuration object or dictionary
        """
        # Apply configuration if provided
        if config:
            if hasattr(config, "get"):
                # Config is a dictionary-like object
                self.session_expiry = config.get("security.session_expiry", self.session_expiry)
                self.cleanup_interval = config.get("security.session_cleanup_interval", self.cleanup_interval)
                
                # Get data directory from config if available
                data_dir = config.get("security.data_dir")
                if data_dir:
                    self.data_dir = Path(normalize_path(data_dir))
                    self.sessions_file = self.data_dir / "sessions.json"

        # Ensure data directory exists
        ensure_dir_exists(self.data_dir)

        # Load sessions
        self._load_sessions()

        # Clean up expired sessions
        self._cleanup_sessions()

        self.logger.info("Session manager initialized with configuration")

    def shutdown(self):
        """Shutdown the session manager."""
        # Save sessions
        self._save_sessions()

        self.logger.info("Session manager shutdown")

    def _load_sessions(self):
        """Load sessions from file."""
        if not self.sessions_file.exists():
            self.logger.info(f"Sessions file not found: {self.sessions_file}")
            return

        try:
            with open(self.sessions_file, "r") as f:
                data = json.load(f)
                self.sessions = {
                    token: Session.from_dict(session_data)
                    for token, session_data in data.items()
                }
            self.logger.info(f"Loaded {len(self.sessions)} sessions from {self.sessions_file}")
        except Exception as e:
            self.logger.error(f"Failed to load sessions: {e}")

    def _save_sessions(self):
        """Save sessions to file."""
        try:
            data = {
                token: session.to_dict()
                for token, session in self.sessions.items()
            }
            with open(self.sessions_file, "w") as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"Saved {len(self.sessions)} sessions to {self.sessions_file}")
        except Exception as e:
            self.logger.error(f"Failed to save sessions: {e}")

    def _cleanup_sessions(self):
        """Clean up expired sessions."""
        # Check if cleanup is needed
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return

        # Clean up expired sessions
        expired_tokens = [
            token for token, session in self.sessions.items()
            if session.is_expired()
        ]

        for token in expired_tokens:
            del self.sessions[token]

        if expired_tokens:
            self.logger.info(f"Cleaned up {len(expired_tokens)} expired sessions")

        # Update last cleanup time
        self.last_cleanup = now

        # Save sessions
        self._save_sessions()

    def create_session(self, username: str, user_data: Dict[str, Any],
                      expires_in: int = None, ip_address: str = None,
                      user_agent: str = None) -> str:
        """
        Create a new session.

        Args:
            username: Username
            user_data: User data
            expires_in: Session expiry time in seconds
            ip_address: IP address
            user_agent: User agent

        Returns:
            str: Session token
        """
        # Generate a unique token
        token = str(uuid.uuid4())

        # Calculate expiry time
        expires_at = None
        if expires_in is not None:
            expires_at = time.time() + expires_in
        elif self.session_expiry is not None:
            expires_at = time.time() + self.session_expiry

        # Create session
        session = Session(
            token=token,
            username=username,
            user_data=user_data,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Add session
        self.sessions[token] = session

        # Clean up expired sessions
        self._cleanup_sessions()

        # Save sessions
        self._save_sessions()

        self.logger.info(f"Session created for user: {username}")
        return token

    def validate_session(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate a session token.

        Args:
            token: Session token

        Returns:
            Tuple containing:
            - bool: True if session is valid, False otherwise
            - Optional[Dict[str, Any]]: Session data if session is valid, None otherwise
        """
        # Check if token exists
        if token not in self.sessions:
            return False, None

        session = self.sessions[token]

        # Check if session is expired
        if session.is_expired():
            # Remove expired session
            del self.sessions[token]
            self._save_sessions()
            return False, None

        # Update last activity
        session.update_activity()

        # Return session data
        return True, session.to_dict()

    def invalidate_session(self, token: str) -> bool:
        """
        Invalidate a session token.

        Args:
            token: Session token

        Returns:
            bool: True if session was invalidated, False otherwise
        """
        # Check if token exists
        if token not in self.sessions:
            return False

        # Remove session
        del self.sessions[token]

        # Save sessions
        self._save_sessions()

        self.logger.info(f"Session invalidated: {token[:8]}...")
        return True

    def invalidate_all_sessions_for_user(self, username: str) -> int:
        """
        Invalidate all sessions for a user.

        Args:
            username: Username

        Returns:
            int: Number of sessions invalidated
        """
        # Find all sessions for the user
        tokens_to_remove = [
            token for token, session in self.sessions.items()
            if session.username == username
        ]

        # Remove sessions
        for token in tokens_to_remove:
            del self.sessions[token]

        # Save sessions if any were removed
        if tokens_to_remove:
            self._save_sessions()
            self.logger.info(f"Invalidated {len(tokens_to_remove)} sessions for user: {username}")

        return len(tokens_to_remove)

    def get_session(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get session data.

        Args:
            token: Session token

        Returns:
            Optional[Dict[str, Any]]: Session data if session exists, None otherwise
        """
        # Check if token exists
        if token not in self.sessions:
            return None

        session = self.sessions[token]

        # Check if session is expired
        if session.is_expired():
            # Remove expired session
            del self.sessions[token]
            self._save_sessions()
            return None

        # Return session data
        return session.to_dict()

    def list_sessions(self, username: str = None) -> List[Dict[str, Any]]:
        """
        List sessions.

        Args:
            username: Username to filter by

        Returns:
            List[Dict[str, Any]]: List of session data
        """
        # Clean up expired sessions
        self._cleanup_sessions()

        # Filter sessions by username if provided
        if username:
            return [
                session.to_dict()
                for session in self.sessions.values()
                if session.username == username
            ]

        # Return all sessions
        return [session.to_dict() for session in self.sessions.values()]


def get_session_manager() -> SessionManager:
    """
    Get the session manager instance.

    Returns:
        SessionManager: Session manager instance
    """
    return SessionManager()


def create_session(username: str, user_data: Dict[str, Any],
                  expires_in: int = None, ip_address: str = None,
                  user_agent: str = None) -> str:
    """
    Create a new session.

    Args:
        username: Username
        user_data: User data
        expires_in: Session expiry time in seconds
        ip_address: IP address
        user_agent: User agent

    Returns:
        str: Session token
    """
    return get_session_manager().create_session(
        username, user_data, expires_in, ip_address, user_agent
    )


def validate_session(token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Validate a session token.

    Args:
        token: Session token

    Returns:
        Tuple containing:
        - bool: True if session is valid, False otherwise
        - Optional[Dict[str, Any]]: Session data if session is valid, None otherwise
    """
    return get_session_manager().validate_session(token)


def invalidate_session(token: str) -> bool:
    """
    Invalidate a session token.

    Args:
        token: Session token

    Returns:
        bool: True if session was invalidated, False otherwise
    """
    return get_session_manager().invalidate_session(token)


def get_session(token: str) -> Optional[Dict[str, Any]]:
    """
    Get session data.

    Args:
        token: Session token

    Returns:
        Optional[Dict[str, Any]]: Session data if session exists, None otherwise
    """
    return get_session_manager().get_session(token)


def list_sessions(username: str = None) -> List[Dict[str, Any]]:
    """
    List sessions.

    Args:
        username: Username to filter by

    Returns:
        List[Dict[str, Any]]: List of session data
    """
    return get_session_manager().list_sessions(username)
