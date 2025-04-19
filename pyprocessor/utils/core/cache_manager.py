"""
Cache utilities for PyProcessor.

This module provides a centralized way to cache data, including:
- Memory caching
- Disk caching
- Cache invalidation strategies
- Cache statistics
"""

import os
import time
import json
import pickle
import hashlib
import threading
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, Callable

from pyprocessor.utils.log_manager import get_logger
from pyprocessor.utils.path_manager import get_user_cache_dir, ensure_dir_exists


class CacheBackend(Enum):
    """Cache backend types."""
    MEMORY = "memory"
    DISK = "disk"
    # TODO: Add more backends (Redis, etc.)


class CachePolicy(Enum):
    """Cache invalidation policies."""
    LRU = "lru"  # Least Recently Used
    TTL = "ttl"  # Time To Live
    # TODO: Add more policies


class CacheEntry:
    """A cache entry with metadata."""

    def __init__(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Initialize a cache entry.

        Args:
            key: Cache key
            value: Cached value
            ttl: Time to live in seconds (None for no expiration)
        """
        self.key = key
        self.value = value
        self.created_at = time.time()
        self.last_accessed = time.time()
        self.ttl = ttl
        self.access_count = 0

    def is_expired(self) -> bool:
        """
        Check if the cache entry is expired.

        Returns:
            bool: True if expired, False otherwise
        """
        if self.ttl is None:
            return False
        return (time.time() - self.created_at) > self.ttl

    def access(self) -> None:
        """Update the last accessed time and access count."""
        self.last_accessed = time.time()
        self.access_count += 1


class CacheManager:
    """
    Centralized manager for caching operations.

    This class provides:
    - Memory caching
    - Disk caching
    - Cache invalidation strategies
    - Cache statistics
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(CacheManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, max_memory_size: int = 1000, max_disk_size: int = 1024 * 1024 * 100):
        """
        Initialize the cache manager.

        Args:
            max_memory_size: Maximum number of items in memory cache
            max_disk_size: Maximum size of disk cache in bytes (default: 100MB)
        """
        # Only initialize once
        if getattr(self, '_initialized', False):
            return

        # Get logger
        self.logger = get_logger()

        # Initialize memory cache
        self._memory_cache: Dict[str, CacheEntry] = {}
        self.max_memory_size = max_memory_size

        # Initialize disk cache
        self.cache_dir = ensure_dir_exists(get_user_cache_dir() / "cache")
        self.max_disk_size = max_disk_size

        # Initialize statistics
        self._stats = {
            "memory_hits": 0,
            "memory_misses": 0,
            "disk_hits": 0,
            "disk_misses": 0,
            "memory_evictions": 0,
            "disk_evictions": 0,
        }

        # Mark as initialized
        self._initialized = True
        self.logger.debug("Cache manager initialized")

    def _get_disk_path(self, key: str) -> Path:
        """
        Get the disk path for a cache key.

        Args:
            key: Cache key

        Returns:
            Path: Path to the cache file
        """
        # Create a hash of the key to use as the filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    def _serialize(self, value: Any) -> bytes:
        """
        Serialize a value for disk storage.

        Args:
            value: Value to serialize

        Returns:
            bytes: Serialized value
        """
        return pickle.dumps(value)

    def _deserialize(self, data: bytes) -> Any:
        """
        Deserialize a value from disk storage.

        Args:
            data: Serialized data

        Returns:
            Any: Deserialized value
        """
        return pickle.loads(data)

    def get(self, key: str, default: Any = None, backend: CacheBackend = CacheBackend.MEMORY) -> Any:
        """
        Get a value from the cache.

        Args:
            key: Cache key
            default: Default value if key not found
            backend: Cache backend to use

        Returns:
            Any: Cached value or default
        """
        if backend == CacheBackend.MEMORY:
            # Check memory cache
            if key in self._memory_cache:
                entry = self._memory_cache[key]

                # Check if expired
                if entry.is_expired():
                    self.delete(key, backend)
                    self._stats["memory_misses"] += 1
                    return default

                # Update access metadata
                entry.access()
                self._stats["memory_hits"] += 1
                return entry.value

            self._stats["memory_misses"] += 1
            return default

        elif backend == CacheBackend.DISK:
            # Check disk cache
            cache_path = self._get_disk_path(key)
            if cache_path.exists():
                try:
                    # Read metadata and data
                    with open(cache_path, "rb") as f:
                        metadata_size = int.from_bytes(f.read(4), byteorder="little")
                        metadata_bytes = f.read(metadata_size)
                        metadata = json.loads(metadata_bytes.decode())
                        data = f.read()

                    # Check if expired
                    if metadata.get("ttl") is not None:
                        if (time.time() - metadata.get("created_at", 0)) > metadata["ttl"]:
                            self.delete(key, backend)
                            self._stats["disk_misses"] += 1
                            return default

                    # Update metadata
                    metadata["last_accessed"] = time.time()
                    metadata["access_count"] = metadata.get("access_count", 0) + 1

                    # Write updated metadata
                    metadata_bytes = json.dumps(metadata).encode()
                    with open(cache_path, "wb") as f:
                        f.write(len(metadata_bytes).to_bytes(4, byteorder="little"))
                        f.write(metadata_bytes)
                        f.write(data)

                    self._stats["disk_hits"] += 1
                    return self._deserialize(data)
                except Exception as e:
                    self.logger.error(f"Error reading from disk cache: {str(e)}")
                    self.delete(key, backend)

            self._stats["disk_misses"] += 1
            return default

        return default

    def set(self, key: str, value: Any, ttl: Optional[int] = None,
            backend: CacheBackend = CacheBackend.MEMORY) -> None:
        """
        Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None for no expiration)
            backend: Cache backend to use
        """
        if backend == CacheBackend.MEMORY:
            # Check if we need to evict
            if len(self._memory_cache) >= self.max_memory_size and key not in self._memory_cache:
                self._evict_memory_cache()

            # Set in memory cache
            self._memory_cache[key] = CacheEntry(key, value, ttl)

        elif backend == CacheBackend.DISK:
            # Set in disk cache
            cache_path = self._get_disk_path(key)

            try:
                # Create metadata
                metadata = {
                    "key": key,
                    "created_at": time.time(),
                    "last_accessed": time.time(),
                    "ttl": ttl,
                    "access_count": 0
                }

                # Serialize data
                data = self._serialize(value)

                # Write metadata and data
                metadata_bytes = json.dumps(metadata).encode()
                with open(cache_path, "wb") as f:
                    f.write(len(metadata_bytes).to_bytes(4, byteorder="little"))
                    f.write(metadata_bytes)
                    f.write(data)

                # Check disk cache size and evict if necessary
                self._check_disk_cache_size()

            except Exception as e:
                self.logger.error(f"Error writing to disk cache: {str(e)}")

    def delete(self, key: str, backend: CacheBackend = CacheBackend.MEMORY) -> bool:
        """
        Delete a value from the cache.

        Args:
            key: Cache key
            backend: Cache backend to use

        Returns:
            bool: True if deleted, False if not found
        """
        if backend == CacheBackend.MEMORY:
            # Delete from memory cache
            if key in self._memory_cache:
                del self._memory_cache[key]
                return True
            return False

        elif backend == CacheBackend.DISK:
            # Delete from disk cache
            cache_path = self._get_disk_path(key)
            if cache_path.exists():
                try:
                    cache_path.unlink()
                    return True
                except Exception as e:
                    self.logger.error(f"Error deleting from disk cache: {str(e)}")
            return False

        return False

    def clear(self, backend: Optional[CacheBackend] = None) -> None:
        """
        Clear the cache.

        Args:
            backend: Cache backend to clear (None for all)
        """
        if backend is None or backend == CacheBackend.MEMORY:
            # Clear memory cache
            self._memory_cache.clear()
            self.logger.debug("Memory cache cleared")

        if backend is None or backend == CacheBackend.DISK:
            # Clear disk cache
            try:
                for cache_file in self.cache_dir.glob("*.cache"):
                    cache_file.unlink()
                self.logger.debug("Disk cache cleared")
            except Exception as e:
                self.logger.error(f"Error clearing disk cache: {str(e)}")

    def _evict_memory_cache(self) -> None:
        """
        Evict items from the memory cache based on LRU policy.
        """
        if not self._memory_cache:
            return

        # Find the least recently used entry
        lru_key = min(self._memory_cache.items(),
                      key=lambda x: x[1].last_accessed)[0]

        # Remove it
        if lru_key in self._memory_cache:
            del self._memory_cache[lru_key]
            self._stats["memory_evictions"] += 1

    def _check_disk_cache_size(self) -> None:
        """
        Check disk cache size and evict if necessary.
        """
        try:
            # Get all cache files
            cache_files = list(self.cache_dir.glob("*.cache"))

            # Calculate total size
            total_size = sum(f.stat().st_size for f in cache_files)

            # If under limit, no need to evict
            if total_size <= self.max_disk_size:
                return

            # Need to evict - sort by last accessed time
            file_stats = []
            for cache_file in cache_files:
                try:
                    # Read metadata to get last accessed time
                    with open(cache_file, "rb") as f:
                        metadata_size = int.from_bytes(f.read(4), byteorder="little")
                        metadata_bytes = f.read(metadata_size)
                        metadata = json.loads(metadata_bytes.decode())

                    file_stats.append({
                        "path": cache_file,
                        "size": cache_file.stat().st_size,
                        "last_accessed": metadata.get("last_accessed", 0)
                    })
                except Exception:
                    # If we can't read metadata, assume old
                    file_stats.append({
                        "path": cache_file,
                        "size": cache_file.stat().st_size,
                        "last_accessed": 0
                    })

            # Sort by last accessed time (oldest first)
            file_stats.sort(key=lambda x: x["last_accessed"])

            # Remove files until we're under the limit
            removed_size = 0
            for stat in file_stats:
                if total_size - removed_size <= self.max_disk_size:
                    break

                # Remove the file
                try:
                    stat["path"].unlink()
                    removed_size += stat["size"]
                    self._stats["disk_evictions"] += 1
                except Exception as e:
                    self.logger.error(f"Error removing cache file: {str(e)}")

            self.logger.debug(f"Evicted {self._stats['disk_evictions']} files from disk cache")

        except Exception as e:
            self.logger.error(f"Error checking disk cache size: {str(e)}")

    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dict[str, int]: Cache statistics
        """
        return self._stats.copy()

    def reset_stats(self) -> None:
        """
        Reset cache statistics.
        """
        for key in self._stats:
            self._stats[key] = 0

    # TODO: Add more advanced caching features


# Singleton instance
_cache_manager = None


def get_cache_manager() -> CacheManager:
    """
    Get the singleton cache manager instance.

    Returns:
        CacheManager: The singleton cache manager instance
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


# Module-level functions for convenience

def cache_get(key: str, default: Any = None, backend: CacheBackend = CacheBackend.MEMORY) -> Any:
    """
    Get a value from the cache.

    Args:
        key: Cache key
        default: Default value if key not found
        backend: Cache backend to use

    Returns:
        Any: Cached value or default
    """
    return get_cache_manager().get(key, default, backend)


def cache_set(key: str, value: Any, ttl: Optional[int] = None,
             backend: CacheBackend = CacheBackend.MEMORY) -> None:
    """
    Set a value in the cache.

    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds (None for no expiration)
        backend: Cache backend to use
    """
    return get_cache_manager().set(key, value, ttl, backend)


def cache_delete(key: str, backend: CacheBackend = CacheBackend.MEMORY) -> bool:
    """
    Delete a value from the cache.

    Args:
        key: Cache key
        backend: Cache backend to use

    Returns:
        bool: True if deleted, False if not found
    """
    return get_cache_manager().delete(key, backend)


def cache_clear(backend: Optional[CacheBackend] = None) -> None:
    """
    Clear the cache.

    Args:
        backend: Cache backend to clear (None for all)
    """
    return get_cache_manager().clear(backend)


def get_cache_stats() -> Dict[str, int]:
    """
    Get cache statistics.

    Returns:
        Dict[str, int]: Cache statistics
    """
    return get_cache_manager().get_stats()


def reset_cache_stats() -> None:
    """
    Reset cache statistics.
    """
    return get_cache_manager().reset_stats()


# Decorator for caching function results
def cached(ttl: Optional[int] = None, key_prefix: str = "",
          backend: CacheBackend = CacheBackend.MEMORY):
    """
    Decorator for caching function results.

    Args:
        ttl: Time to live in seconds (None for no expiration)
        key_prefix: Prefix for cache keys
        backend: Cache backend to use

    Returns:
        Callable: Decorated function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Create a cache key from the function name and arguments
            key_parts = [key_prefix or func.__name__]

            # Add positional arguments
            for arg in args:
                key_parts.append(str(arg))

            # Add keyword arguments (sorted for consistency)
            for k in sorted(kwargs.keys()):
                key_parts.append(f"{k}={kwargs[k]}")

            cache_key = ":".join(key_parts)

            # Try to get from cache
            cached_value = cache_get(cache_key, backend=backend)
            if cached_value is not None:
                return cached_value

            # Call the function
            result = func(*args, **kwargs)

            # Cache the result
            cache_set(cache_key, result, ttl, backend)

            return result
        return wrapper
    return decorator
