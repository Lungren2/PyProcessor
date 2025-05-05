"""
Encryption manager for PyProcessor.

This module provides encryption and decryption functionality for media files
and other sensitive data using AES-256 encryption.
"""

import base64
import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from pyprocessor.utils.file_system.path_utils import (
    ensure_dir_exists,
    get_user_data_dir,
    normalize_path,
)
from pyprocessor.utils.logging.log_manager import get_logger


class EncryptionKey:
    """Encryption key model."""

    def __init__(
        self,
        key_id: str,
        key_data: bytes,
        created_at: float,
        expires_at: Optional[float] = None,
        description: str = None,
        metadata: Dict[str, Any] = None,
    ):
        """
        Initialize an encryption key.

        Args:
            key_id: Unique identifier for the key
            key_data: Raw key data
            created_at: Creation timestamp
            expires_at: Expiration timestamp (optional)
            description: Key description (optional)
            metadata: Additional metadata (optional)
        """
        self.id = key_id
        self.key_data = key_data
        self.created_at = created_at
        self.expires_at = expires_at
        self.description = description
        self.metadata = metadata or {}


class EncryptionManager:
    """
    Singleton encryption manager for PyProcessor.

    This class provides encryption and decryption functionality for media files
    and other sensitive data using AES-256 encryption.
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        """Create a new instance of EncryptionManager or return the existing one."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EncryptionManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the encryption manager."""
        # Only initialize once
        if self._initialized:
            return

        # Get logger
        self.logger = get_logger()

        # Initialize data
        self.keys = {}
        self.default_key_id = None

        # Initialize default paths
        self.data_dir = Path(get_user_data_dir()) / "security" / "keys"
        self.keys_file = self.data_dir / "keys.json"

        # Initialize configuration
        self.key_rotation_interval = 90 * 24 * 60 * 60  # 90 days in seconds
        self.pbkdf2_iterations = 100000  # Number of iterations for PBKDF2

        # Mark as initialized
        self._initialized = True
        self.logger.debug("Encryption manager initialized")

    def initialize(self, config=None):
        """
        Initialize the encryption manager with configuration.

        Args:
            config: Configuration object or dictionary
        """
        if not config:
            return

        # Update configuration from config object
        if hasattr(config, "encryption"):
            encryption_config = config.encryption

            # Update key rotation interval
            if hasattr(encryption_config, "key_rotation_interval_days"):
                days = encryption_config.key_rotation_interval_days
                self.key_rotation_interval = days * 24 * 60 * 60

            # Update PBKDF2 iterations
            if hasattr(encryption_config, "pbkdf2_iterations"):
                self.pbkdf2_iterations = encryption_config.pbkdf2_iterations

            # Update data directory
            if hasattr(encryption_config, "keys_dir"):
                self.data_dir = normalize_path(encryption_config.keys_dir)
                self.keys_file = self.data_dir / "keys.json"

        # Ensure data directory exists
        ensure_dir_exists(self.data_dir)

        # Load existing keys
        self._load_keys()

        # Generate default key if none exists
        if not self.keys:
            self.logger.info("No encryption keys found, generating default key")
            success, key_id, _ = self.generate_key(description="Default encryption key")
            if success:
                self.default_key_id = key_id
                self.logger.info(f"Generated default encryption key: {key_id}")
            else:
                self.logger.error("Failed to generate default encryption key")

        self.logger.info("Encryption manager initialized with configuration")

    # Key management methods
    def generate_key(
        self, description: str = None, expires_in: int = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Generate a new encryption key.

        Args:
            description: Description of the key
            expires_in: Expiration time in seconds from now

        Returns:
            Tuple containing:
            - bool: True if key was generated, False otherwise
            - str: Key ID if generation was successful, error message otherwise
            - Dict[str, Any]: Key metadata if generation was successful, None otherwise
        """
        try:
            # Generate a unique ID
            key_id = str(uuid.uuid4())

            # Generate a secure random key (32 bytes = 256 bits for AES-256)
            key_data = os.urandom(32)

            # Calculate expiry time
            expires_at = None
            if expires_in is not None:
                expires_at = time.time() + expires_in

            # Create key object
            key = EncryptionKey(
                key_id=key_id,
                key_data=key_data,
                created_at=time.time(),
                expires_at=expires_at,
                description=description,
                metadata={},
            )

            # Store the key
            if not self.store_key(key):
                return False, "Failed to store key", None

            # If this is the first key, set it as default
            if len(self.keys) == 1:
                self.default_key_id = key_id
                self._save_keys()

            # Create metadata for return
            metadata = {
                "id": key_id,
                "created_at": key.created_at,
                "expires_at": key.expires_at,
                "description": key.description,
                "is_default": key_id == self.default_key_id,
            }

            return True, key_id, metadata

        except Exception as e:
            self.logger.error(f"Error generating key: {str(e)}")
            return False, f"Error: {str(e)}", None

    def derive_key_from_password(
        self, password: str, salt: Optional[bytes] = None
    ) -> Tuple[bytes, bytes]:
        """
        Derive an encryption key from a password.

        Args:
            password: Password to derive key from
            salt: Salt for key derivation (generated if not provided)

        Returns:
            Tuple containing:
            - bytes: Derived key
            - bytes: Salt used for derivation
        """
        try:
            # Generate salt if not provided
            if salt is None:
                salt = os.urandom(16)

            # Create PBKDF2HMAC instance
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,  # 32 bytes = 256 bits for AES-256
                salt=salt,
                iterations=self.pbkdf2_iterations,
                backend=default_backend(),
            )

            # Derive key
            key = kdf.derive(password.encode("utf-8"))

            return key, salt

        except Exception as e:
            self.logger.error(f"Error deriving key from password: {str(e)}")
            # Return empty values on error
            return b"", b""

    def store_key(self, key: EncryptionKey) -> bool:
        """
        Store an encryption key securely.

        Args:
            key: Encryption key to store

        Returns:
            bool: True if key was stored, False otherwise
        """
        try:
            # Add key to dictionary
            self.keys[key.id] = key

            # Save keys to disk
            self._save_keys()

            self.logger.debug(f"Stored encryption key: {key.id}")
            return True

        except Exception as e:
            self.logger.error(f"Error storing encryption key: {str(e)}")
            return False

    def get_key(self, key_id: str) -> Optional[EncryptionKey]:
        """
        Get an encryption key by ID.

        Args:
            key_id: Key ID

        Returns:
            Optional[EncryptionKey]: Encryption key if found, None otherwise
        """
        try:
            # Check if key exists
            if key_id not in self.keys:
                self.logger.warning(f"Key not found: {key_id}")
                return None

            # Check if key is expired
            key = self.keys[key_id]
            if key.expires_at is not None and key.expires_at < time.time():
                self.logger.warning(f"Key expired: {key_id}")
                return None

            return key

        except Exception as e:
            self.logger.error(f"Error retrieving key {key_id}: {str(e)}")
            return None

    def list_keys(self) -> List[Dict[str, Any]]:
        """
        List all encryption keys.

        Returns:
            List[Dict[str, Any]]: List of key metadata
        """
        try:
            result = []

            for key_id, key in self.keys.items():
                # Skip expired keys
                if key.expires_at is not None and key.expires_at < time.time():
                    continue

                # Create metadata
                metadata = {
                    "id": key_id,
                    "created_at": key.created_at,
                    "expires_at": key.expires_at,
                    "description": key.description,
                    "is_default": key_id == self.default_key_id,
                }

                result.append(metadata)

            return result

        except Exception as e:
            self.logger.error(f"Error listing keys: {str(e)}")
            return []

    def rotate_key(
        self, old_key_id: str
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Rotate an encryption key.

        Args:
            old_key_id: ID of the key to rotate

        Returns:
            Tuple containing:
            - bool: True if key was rotated, False otherwise
            - Optional[str]: New key ID if rotation was successful, error message otherwise
            - Optional[Dict[str, Any]]: New key metadata if rotation was successful, None otherwise
        """
        try:
            # Get the old key
            old_key = self.get_key(old_key_id)
            if old_key is None:
                return False, f"Key not found: {old_key_id}", None

            # Generate a new key with the same description
            success, new_key_id, metadata = self.generate_key(
                description=f"Rotated from {old_key_id}: {old_key.description}",
                expires_in=None,  # No expiration for rotated keys
            )

            if not success:
                return False, f"Failed to generate new key: {new_key_id}", None

            # If the old key was the default, make the new key the default
            if old_key_id == self.default_key_id:
                self.default_key_id = new_key_id
                self._save_keys()

            # Mark the old key as rotated in its metadata
            old_key.metadata["rotated_to"] = new_key_id
            old_key.metadata["rotated_at"] = time.time()

            # If we want to keep the old key for a while (for decryption of existing data)
            # we can set an expiration time
            if old_key.expires_at is None:
                # Set expiration to 30 days from now
                old_key.expires_at = time.time() + (30 * 24 * 60 * 60)

            self._save_keys()

            return True, new_key_id, metadata

        except Exception as e:
            self.logger.error(f"Error rotating key {old_key_id}: {str(e)}")
            return False, f"Error: {str(e)}", None

    def revoke_key(self, key_id: str) -> bool:
        """
        Revoke an encryption key.

        Args:
            key_id: Key ID

        Returns:
            bool: True if key was revoked, False otherwise
        """
        try:
            # Check if key exists
            if key_id not in self.keys:
                self.logger.warning(f"Cannot revoke non-existent key: {key_id}")
                return False

            # Check if it's the default key
            if key_id == self.default_key_id:
                self.logger.warning(f"Cannot revoke default key: {key_id}")
                return False

            # Remove the key
            del self.keys[key_id]

            # Save changes
            self._save_keys()

            self.logger.info(f"Revoked key: {key_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error revoking key {key_id}: {str(e)}")
            return False

    # Encryption/decryption methods
    def encrypt_data(
        self, data: bytes, key_id: Optional[str] = None
    ) -> Tuple[bool, bytes, Dict[str, Any]]:
        """
        Encrypt data using AES-256.

        Args:
            data: Data to encrypt
            key_id: Key ID to use for encryption (uses default key if not provided)

        Returns:
            Tuple containing:
            - bool: True if encryption was successful, False otherwise
            - bytes: Encrypted data if successful, empty bytes otherwise
            - Dict[str, Any]: Encryption metadata
        """
        try:
            # Use default key if not specified
            if key_id is None:
                if self.default_key_id is None:
                    self.logger.error("No default encryption key available")
                    return False, b"", {}
                key_id = self.default_key_id

            # Get the key
            key = self.get_key(key_id)
            if key is None:
                self.logger.error(f"Encryption key not found: {key_id}")
                return False, b"", {}

            # Generate a random IV (Initialization Vector)
            iv = os.urandom(16)  # 16 bytes = 128 bits for AES

            # Create AES cipher
            cipher = Cipher(
                algorithms.AES(key.key_data), modes.CBC(iv), backend=default_backend()
            )

            # Create encryptor
            encryptor = cipher.encryptor()

            # Create padder
            padder = padding.PKCS7(algorithms.AES.block_size).padder()

            # Pad the data
            padded_data = padder.update(data) + padder.finalize()

            # Encrypt the data
            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

            # Create metadata
            metadata = {
                "key_id": key_id,
                "algorithm": "AES-256-CBC",
                "iv": base64.b64encode(iv).decode("utf-8"),
                "created_at": time.time(),
            }

            return True, encrypted_data, metadata

        except Exception as e:
            self.logger.error(f"Error encrypting data: {str(e)}")
            return False, b"", {}

    def decrypt_data(
        self, encrypted_data: bytes, metadata: Dict[str, Any]
    ) -> Tuple[bool, bytes]:
        """
        Decrypt data using AES-256.

        Args:
            encrypted_data: Encrypted data
            metadata: Encryption metadata

        Returns:
            Tuple containing:
            - bool: True if decryption was successful, False otherwise
            - bytes: Decrypted data if successful, empty bytes otherwise
        """
        try:
            # Get required metadata
            key_id = metadata.get("key_id")
            algorithm = metadata.get("algorithm")
            iv_base64 = metadata.get("iv")

            # Validate metadata
            if not all([key_id, algorithm, iv_base64]):
                self.logger.error("Missing required metadata for decryption")
                return False, b""

            # Check algorithm
            if algorithm != "AES-256-CBC":
                self.logger.error(f"Unsupported encryption algorithm: {algorithm}")
                return False, b""

            # Get the key
            key = self.get_key(key_id)
            if key is None:
                self.logger.error(f"Decryption key not found: {key_id}")
                return False, b""

            # Decode IV
            iv = base64.b64decode(iv_base64)

            # Create AES cipher
            cipher = Cipher(
                algorithms.AES(key.key_data), modes.CBC(iv), backend=default_backend()
            )

            # Create decryptor
            decryptor = cipher.decryptor()

            # Decrypt the data
            padded_data = decryptor.update(encrypted_data) + decryptor.finalize()

            # Create unpadder
            unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()

            # Unpad the data
            data = unpadder.update(padded_data) + unpadder.finalize()

            return True, data

        except Exception as e:
            self.logger.error(f"Error decrypting data: {str(e)}")
            return False, b""

    def encrypt_file(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        key_id: Optional[str] = None,
        chunk_size: int = 1024 * 1024,
    ) -> Tuple[bool, Optional[Path], Dict[str, Any]]:
        """
        Encrypt a file using AES-256.

        Args:
            input_path: Path to the file to encrypt
            output_path: Path to save the encrypted file (defaults to input_path + '.enc')
            key_id: Key ID to use for encryption (uses default key if not provided)
            chunk_size: Size of chunks to process at a time (default: 1MB)

        Returns:
            Tuple containing:
            - bool: True if encryption was successful, False otherwise
            - Optional[Path]: Path to the encrypted file if successful, None otherwise
            - Dict[str, Any]: Encryption metadata
        """
        try:
            # Normalize paths
            input_path = normalize_path(input_path)

            # Check if input file exists
            if not input_path.exists():
                self.logger.error(f"Input file does not exist: {input_path}")
                return False, None, {}

            # Set default output path if not provided
            if output_path is None:
                output_path = input_path.with_suffix(input_path.suffix + ".enc")
            else:
                output_path = normalize_path(output_path)

            # Ensure output directory exists
            ensure_dir_exists(output_path.parent)

            # Use default key if not specified
            if key_id is None:
                if self.default_key_id is None:
                    self.logger.error("No default encryption key available")
                    return False, None, {}
                key_id = self.default_key_id

            # Get the key
            key = self.get_key(key_id)
            if key is None:
                self.logger.error(f"Encryption key not found: {key_id}")
                return False, None, {}

            # Generate a random IV (Initialization Vector)
            iv = os.urandom(16)  # 16 bytes = 128 bits for AES

            # Create AES cipher
            cipher = Cipher(
                algorithms.AES(key.key_data), modes.CBC(iv), backend=default_backend()
            )

            # Create encryptor
            encryptor = cipher.encryptor()

            # Create padder
            padder = padding.PKCS7(algorithms.AES.block_size).padder()

            # Create metadata
            metadata = {
                "key_id": key_id,
                "algorithm": "AES-256-CBC",
                "iv": base64.b64encode(iv).decode("utf-8"),
                "created_at": time.time(),
                "original_filename": input_path.name,
                "original_size": input_path.stat().st_size,
            }

            # Write metadata and encrypted data to output file
            with open(input_path, "rb") as in_file, open(output_path, "wb") as out_file:
                # Write metadata as JSON header (with size prefix)
                metadata_json = json.dumps(metadata).encode("utf-8")
                metadata_size = len(metadata_json)
                out_file.write(metadata_size.to_bytes(4, byteorder="big"))
                out_file.write(metadata_json)

                # Process file in chunks
                while True:
                    chunk = in_file.read(chunk_size)
                    if not chunk:
                        break

                    # For the last chunk, we need to pad
                    if len(chunk) < chunk_size:
                        padded_chunk = padder.update(chunk) + padder.finalize()
                    else:
                        padded_chunk = padder.update(chunk)

                    # Encrypt and write chunk
                    encrypted_chunk = encryptor.update(padded_chunk)
                    out_file.write(encrypted_chunk)

                # Write final block if needed
                final_block = encryptor.finalize()
                if final_block:
                    out_file.write(final_block)

            self.logger.info(f"Encrypted file {input_path} to {output_path}")
            return True, output_path, metadata

        except Exception as e:
            self.logger.error(f"Error encrypting file {input_path}: {str(e)}")
            return False, None, {}

    def decrypt_file(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 1024 * 1024,
    ) -> Tuple[bool, Optional[Path]]:
        """
        Decrypt a file using AES-256.

        Args:
            input_path: Path to the encrypted file
            output_path: Path to save the decrypted file
            metadata: Encryption metadata (read from file if not provided)
            chunk_size: Size of chunks to process at a time (default: 1MB)

        Returns:
            Tuple containing:
            - bool: True if decryption was successful, False otherwise
            - Optional[Path]: Path to the decrypted file if successful, None otherwise
        """
        try:
            # Normalize paths
            input_path = normalize_path(input_path)

            # Check if input file exists
            if not input_path.exists():
                self.logger.error(f"Input file does not exist: {input_path}")
                return False, None

            # Read metadata from file if not provided
            if metadata is None:
                with open(input_path, "rb") as in_file:
                    # Read metadata size (4 bytes)
                    metadata_size_bytes = in_file.read(4)
                    if len(metadata_size_bytes) != 4:
                        self.logger.error(
                            f"Invalid encrypted file format: {input_path}"
                        )
                        return False, None

                    metadata_size = int.from_bytes(metadata_size_bytes, byteorder="big")

                    # Read metadata JSON
                    metadata_json = in_file.read(metadata_size)
                    if len(metadata_json) != metadata_size:
                        self.logger.error(
                            f"Invalid encrypted file format: {input_path}"
                        )
                        return False, None

                    metadata = json.loads(metadata_json.decode("utf-8"))

            # Set default output path if not provided
            if output_path is None:
                # Use original filename from metadata if available
                original_filename = metadata.get("original_filename")
                if original_filename:
                    output_path = input_path.parent / original_filename
                else:
                    # Remove .enc suffix if present
                    if input_path.suffix == ".enc":
                        output_path = input_path.with_suffix("")
                    else:
                        output_path = input_path.with_suffix(input_path.suffix + ".dec")
            else:
                output_path = normalize_path(output_path)

            # Ensure output directory exists
            ensure_dir_exists(output_path.parent)

            # Get required metadata
            key_id = metadata.get("key_id")
            algorithm = metadata.get("algorithm")
            iv_base64 = metadata.get("iv")

            # Validate metadata
            if not all([key_id, algorithm, iv_base64]):
                self.logger.error("Missing required metadata for decryption")
                return False, None

            # Check algorithm
            if algorithm != "AES-256-CBC":
                self.logger.error(f"Unsupported encryption algorithm: {algorithm}")
                return False, None

            # Get the key
            key = self.get_key(key_id)
            if key is None:
                self.logger.error(f"Decryption key not found: {key_id}")
                return False, None

            # Decode IV
            iv = base64.b64decode(iv_base64)

            # Create AES cipher
            cipher = Cipher(
                algorithms.AES(key.key_data), modes.CBC(iv), backend=default_backend()
            )

            # Create decryptor
            decryptor = cipher.decryptor()

            # Create unpadder
            unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()

            # Decrypt file
            with open(input_path, "rb") as in_file, open(output_path, "wb") as out_file:
                # Skip metadata
                metadata_size_bytes = in_file.read(4)
                metadata_size = int.from_bytes(metadata_size_bytes, byteorder="big")
                in_file.read(metadata_size)  # Skip metadata JSON

                # Process file in chunks
                while True:
                    chunk = in_file.read(chunk_size)
                    if not chunk:
                        break

                    # Decrypt chunk
                    decrypted_chunk = decryptor.update(chunk)

                    # For the last chunk, we need to unpad
                    if len(chunk) < chunk_size:
                        try:
                            unpadded_chunk = (
                                unpadder.update(decrypted_chunk) + unpadder.finalize()
                            )
                        except Exception as e:
                            self.logger.error(f"Error unpadding data: {str(e)}")
                            return False, None
                    else:
                        try:
                            unpadded_chunk = unpadder.update(decrypted_chunk)
                        except Exception as e:
                            self.logger.error(f"Error unpadding data: {str(e)}")
                            return False, None

                    # Write chunk
                    out_file.write(unpadded_chunk)

                # Write final block if needed
                try:
                    final_block = decryptor.finalize()
                    if final_block:
                        out_file.write(final_block)
                except Exception as e:
                    self.logger.error(f"Error finalizing decryption: {str(e)}")
                    return False, None

            self.logger.info(f"Decrypted file {input_path} to {output_path}")
            return True, output_path

        except Exception as e:
            self.logger.error(f"Error decrypting file {input_path}: {str(e)}")
            return False, None

    def encrypt_stream(
        self,
        input_stream: BinaryIO,
        output_stream: BinaryIO,
        key_id: Optional[str] = None,
        chunk_size: int = 1024 * 1024,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Encrypt a stream using AES-256.

        Args:
            input_stream: Input binary stream
            output_stream: Output binary stream
            key_id: Key ID to use for encryption (uses default key if not provided)
            chunk_size: Size of chunks to process at a time (default: 1MB)

        Returns:
            Tuple containing:
            - bool: True if encryption was successful, False otherwise
            - Dict[str, Any]: Encryption metadata
        """
        try:
            # Use default key if not specified
            if key_id is None:
                if self.default_key_id is None:
                    self.logger.error("No default encryption key available")
                    return False, {}
                key_id = self.default_key_id

            # Get the key
            key = self.get_key(key_id)
            if key is None:
                self.logger.error(f"Encryption key not found: {key_id}")
                return False, {}

            # Generate a random IV (Initialization Vector)
            iv = os.urandom(16)  # 16 bytes = 128 bits for AES

            # Create AES cipher
            cipher = Cipher(
                algorithms.AES(key.key_data), modes.CBC(iv), backend=default_backend()
            )

            # Create encryptor
            encryptor = cipher.encryptor()

            # Create padder
            padder = padding.PKCS7(algorithms.AES.block_size).padder()

            # Create metadata
            metadata = {
                "key_id": key_id,
                "algorithm": "AES-256-CBC",
                "iv": base64.b64encode(iv).decode("utf-8"),
                "created_at": time.time(),
            }

            # Process stream in chunks
            while True:
                chunk = input_stream.read(chunk_size)
                if not chunk:
                    break

                # For the last chunk, we need to pad
                if len(chunk) < chunk_size:
                    padded_chunk = padder.update(chunk) + padder.finalize()
                else:
                    padded_chunk = padder.update(chunk)

                # Encrypt and write chunk
                encrypted_chunk = encryptor.update(padded_chunk)
                output_stream.write(encrypted_chunk)

            # Write final block if needed
            final_block = encryptor.finalize()
            if final_block:
                output_stream.write(final_block)

            self.logger.info("Stream encrypted successfully")
            return True, metadata

        except Exception as e:
            self.logger.error(f"Error encrypting stream: {str(e)}")
            return False, {}

    def decrypt_stream(
        self,
        input_stream: BinaryIO,
        output_stream: BinaryIO,
        metadata: Dict[str, Any],
        chunk_size: int = 1024 * 1024,
    ) -> bool:
        """
        Decrypt a stream using AES-256.

        Args:
            input_stream: Input binary stream
            output_stream: Output binary stream
            metadata: Encryption metadata
            chunk_size: Size of chunks to process at a time (default: 1MB)

        Returns:
            bool: True if decryption was successful, False otherwise
        """
        try:
            # Get required metadata
            key_id = metadata.get("key_id")
            algorithm = metadata.get("algorithm")
            iv_base64 = metadata.get("iv")

            # Validate metadata
            if not all([key_id, algorithm, iv_base64]):
                self.logger.error("Missing required metadata for decryption")
                return False

            # Check algorithm
            if algorithm != "AES-256-CBC":
                self.logger.error(f"Unsupported encryption algorithm: {algorithm}")
                return False

            # Get the key
            key = self.get_key(key_id)
            if key is None:
                self.logger.error(f"Decryption key not found: {key_id}")
                return False

            # Decode IV
            iv = base64.b64decode(iv_base64)

            # Create AES cipher
            cipher = Cipher(
                algorithms.AES(key.key_data), modes.CBC(iv), backend=default_backend()
            )

            # Create decryptor
            decryptor = cipher.decryptor()

            # Create unpadder
            unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()

            # Process stream in chunks
            buffer = b""
            while True:
                chunk = input_stream.read(chunk_size)
                if not chunk and not buffer:
                    break

                # Process the buffer and the new chunk
                if not chunk:  # Last chunk
                    # Process the remaining buffer with finalization
                    decrypted_chunk = decryptor.update(buffer) + decryptor.finalize()
                    unpadded_chunk = unpadder.update(decrypted_chunk) + unpadder.finalize()
                    output_stream.write(unpadded_chunk)
                    break
                elif not buffer:  # First chunk
                    buffer = chunk
                else:  # Middle chunks
                    # Process the buffer, keep the current chunk for next iteration
                    decrypted_chunk = decryptor.update(buffer)
                    try:
                        unpadded_chunk = unpadder.update(decrypted_chunk)
                        output_stream.write(unpadded_chunk)
                    except Exception as e:
                        self.logger.error(f"Error unpadding data: {str(e)}")
                        return False
                    buffer = chunk

            self.logger.info("Stream decrypted successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error decrypting stream: {str(e)}")
            return False

    # Key exchange methods
    def export_key(self, key_id: str, passphrase: str) -> Tuple[bool, Optional[str]]:
        """
        Export an encryption key securely.

        Args:
            key_id: Key ID
            passphrase: Passphrase to protect the exported key

        Returns:
            Tuple containing:
            - bool: True if key was exported, False otherwise
            - Optional[str]: Exported key data if successful, error message otherwise
        """
        try:
            # Get the key
            key = self.get_key(key_id)
            if key is None:
                return False, f"Key not found: {key_id}"

            # Derive encryption key from passphrase
            salt = os.urandom(16)
            derived_key, _ = self.derive_key_from_password(passphrase, salt)

            # Create export data
            export_data = {
                "id": key.id,
                "created_at": key.created_at,
                "expires_at": key.expires_at,
                "description": key.description,
                "metadata": key.metadata,
                "salt": base64.b64encode(salt).decode("utf-8"),
            }

            # Encrypt the key data
            iv = os.urandom(16)
            cipher = Cipher(
                algorithms.AES(derived_key), modes.CBC(iv), backend=default_backend()
            )
            encryptor = cipher.encryptor()

            # Pad the key data
            padder = padding.PKCS7(algorithms.AES.block_size).padder()
            padded_data = padder.update(key.key_data) + padder.finalize()

            # Encrypt the key data
            encrypted_key_data = encryptor.update(padded_data) + encryptor.finalize()

            # Add encrypted key data and IV to export data
            export_data["key_data"] = base64.b64encode(encrypted_key_data).decode(
                "utf-8"
            )
            export_data["iv"] = base64.b64encode(iv).decode("utf-8")

            # Serialize to JSON and encode in base64
            json_data = json.dumps(export_data)
            encoded_data = base64.b64encode(json_data.encode("utf-8")).decode("utf-8")

            # Format as a portable string
            portable_key = f"PYPROC_KEY_{encoded_data}"

            return True, portable_key

        except Exception as e:
            self.logger.error(f"Error exporting key {key_id}: {str(e)}")
            return False, f"Error: {str(e)}"

    def import_key(
        self, key_data: str, passphrase: str
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Import an encryption key.

        Args:
            key_data: Exported key data
            passphrase: Passphrase to decrypt the key

        Returns:
            Tuple containing:
            - bool: True if key was imported, False otherwise
            - Optional[str]: Key ID if import was successful, error message otherwise
            - Optional[Dict[str, Any]]: Key metadata if import was successful, None otherwise
        """
        try:
            # Check format
            if not key_data.startswith("PYPROC_KEY_"):
                return False, "Invalid key format", None

            # Decode the data
            encoded_data = key_data[len("PYPROC_KEY_") :]
            json_data = base64.b64decode(encoded_data).decode("utf-8")
            export_data = json.loads(json_data)

            # Extract data
            key_id = export_data["id"]
            created_at = export_data["created_at"]
            expires_at = export_data.get("expires_at")
            description = export_data.get("description")
            metadata = export_data.get("metadata", {})
            salt_base64 = export_data["salt"]
            encrypted_key_data_base64 = export_data["key_data"]
            iv_base64 = export_data["iv"]

            # Decode binary data
            salt = base64.b64decode(salt_base64)
            encrypted_key_data = base64.b64decode(encrypted_key_data_base64)
            iv = base64.b64decode(iv_base64)

            # Derive key from passphrase
            derived_key, _ = self.derive_key_from_password(passphrase, salt)

            # Decrypt the key data
            cipher = Cipher(
                algorithms.AES(derived_key), modes.CBC(iv), backend=default_backend()
            )
            decryptor = cipher.decryptor()

            # Decrypt and unpad
            padded_key_data = (
                decryptor.update(encrypted_key_data) + decryptor.finalize()
            )
            unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
            key_data_bytes = unpadder.update(padded_key_data) + unpadder.finalize()

            # Create key object
            key = EncryptionKey(
                key_id=key_id,
                key_data=key_data_bytes,
                created_at=created_at,
                expires_at=expires_at,
                description=description,
                metadata=metadata,
            )

            # Store the key
            if not self.store_key(key):
                return False, "Failed to store imported key", None

            # Create metadata for return
            return_metadata = {
                "id": key_id,
                "created_at": created_at,
                "expires_at": expires_at,
                "description": description,
                "is_default": key_id == self.default_key_id,
            }

            return True, key_id, return_metadata

        except Exception as e:
            self.logger.error(f"Error importing key: {str(e)}")
            return False, f"Error: {str(e)}", None

    def _load_keys(self):
        """
        Load encryption keys from storage.
        """
        try:
            if not self.keys_file.exists():
                self.logger.debug("Keys file does not exist, no keys to load")
                return

            with open(self.keys_file, "r") as f:
                keys_data = json.load(f)

            # Process each key
            for key_id, key_data in keys_data.items():
                try:
                    # Decode key data
                    raw_key = base64.b64decode(key_data["key_data"])

                    # Create key object
                    key = EncryptionKey(
                        key_id=key_id,
                        key_data=raw_key,
                        created_at=key_data["created_at"],
                        expires_at=key_data.get("expires_at"),
                        description=key_data.get("description"),
                        metadata=key_data.get("metadata", {}),
                    )

                    # Add to keys dictionary
                    self.keys[key_id] = key

                    # Set as default if marked
                    if key_data.get("is_default", False):
                        self.default_key_id = key_id

                except Exception as e:
                    self.logger.error(f"Error loading key {key_id}: {str(e)}")

            self.logger.info(f"Loaded {len(self.keys)} encryption keys")

        except Exception as e:
            self.logger.error(f"Error loading encryption keys: {str(e)}")

    def _save_keys(self):
        """
        Save encryption keys to storage.
        """
        try:
            # Prepare keys data for serialization
            keys_data = {}

            for key_id, key in self.keys.items():
                # Encode key data
                encoded_key = base64.b64encode(key.key_data).decode("utf-8")

                # Create serializable key data
                key_data = {
                    "key_data": encoded_key,
                    "created_at": key.created_at,
                    "is_default": key_id == self.default_key_id,
                }

                # Add optional fields
                if key.expires_at is not None:
                    key_data["expires_at"] = key.expires_at

                if key.description is not None:
                    key_data["description"] = key.description

                if key.metadata:
                    key_data["metadata"] = key.metadata

                keys_data[key_id] = key_data

            # Ensure directory exists
            ensure_dir_exists(self.data_dir)

            # Write to file
            with open(self.keys_file, "w") as f:
                json.dump(keys_data, f, indent=2)

            self.logger.debug(f"Saved {len(self.keys)} encryption keys")

        except Exception as e:
            self.logger.error(f"Error saving encryption keys: {str(e)}")


def get_encryption_manager() -> EncryptionManager:
    """
    Get the encryption manager instance.

    Returns:
        EncryptionManager: Encryption manager instance
    """
    return EncryptionManager()
