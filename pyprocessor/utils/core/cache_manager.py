"""
Cache utilities for PyProcessor.

This module provides a centralized way to cache data, including:
- Memory caching
- Disk caching
- Cache invalidation strategies
- Cache statistics
"""

import hashlib
import json
import pickle
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pyprocessor.utils.log_manager import get_logger
from pyprocessor.utils.path_manager import ensure_dir_exists, get_user_cache_dir


class CacheBackend(Enum):
    """Cache backend types."""

    MEMORY = "memory"
    DISK = "disk"
    MULTI = "multi"  # Multi-level cache (memory + disk)
    # TODO: Add more backends (Redis, etc.)


# This class is replaced by the more comprehensive CachePolicy class below


class CachePolicy(Enum):
    """Cache eviction policy types."""

    LRU = "lru"  # Least Recently Used
    MRU = "mru"  # Most Recently Used
    FIFO = "fifo"  # First In First Out
    LFU = "lfu"  # Least Frequently Used


class TTLStrategy(Enum):
    """TTL strategy types."""

    FIXED = "fixed"  # Fixed TTL from creation time
    SLIDING = "sliding"  # TTL resets on each access


class CacheEntry:
    """A cache entry with metadata."""

    def __init__(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        ttl_strategy: TTLStrategy = TTLStrategy.FIXED,
    ):
        """
        Initialize a cache entry.

        Args:
            key: Cache key
            value: Cached value
            ttl: Time to live in seconds (None for no expiration)
            ttl_strategy: TTL strategy to use
        """
        self.key = key
        self.value = value
        self.created_at = time.time()
        self.last_accessed = time.time()
        self.ttl = ttl
        self.ttl_strategy = ttl_strategy
        self.access_count = 0
        self.size = self._estimate_size(value)

    def _estimate_size(self, value: Any) -> int:
        """Estimate the size of a value in bytes."""
        try:
            # Try to get the size using sys.getsizeof
            import sys

            return sys.getsizeof(value)
        except (ImportError, TypeError):
            # Fallback to a rough estimate based on pickle size
            try:
                return len(pickle.dumps(value))
            except:
                # If all else fails, return a default size
                return 1024  # 1KB default

    def is_expired(self) -> bool:
        """
        Check if the cache entry is expired.

        Returns:
            bool: True if expired, False otherwise
        """
        if self.ttl is None:
            return False

        if self.ttl_strategy == TTLStrategy.FIXED:
            return (time.time() - self.created_at) > self.ttl
        elif self.ttl_strategy == TTLStrategy.SLIDING:
            return (time.time() - self.last_accessed) > self.ttl

        # Default to fixed TTL if strategy is unknown
        return (time.time() - self.created_at) > self.ttl

    def access(self) -> None:
        """Update the last accessed time and access count."""
        self.last_accessed = time.time()
        self.access_count += 1

    def get_priority_score(self, policy: CachePolicy) -> float:
        """Get the priority score for this entry based on the eviction policy."""
        now = time.time()

        if policy == CachePolicy.LRU:
            # Lower score = higher priority for eviction
            return now - self.last_accessed
        elif policy == CachePolicy.MRU:
            # Higher score = higher priority for eviction
            return self.last_accessed
        elif policy == CachePolicy.FIFO:
            # Lower score = higher priority for eviction
            return now - self.created_at
        elif policy == CachePolicy.LFU:
            # Lower score = higher priority for eviction
            return 1.0 / (self.access_count + 1)

        # Default to LRU
        return now - self.last_accessed


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

    def __init__(
        self,
        max_memory_size: int = 1000,
        max_disk_size: int = 1024 * 1024 * 100,
        eviction_policy: CachePolicy = CachePolicy.LRU,
        default_ttl_strategy: TTLStrategy = TTLStrategy.FIXED,
        auto_adjust_sizes: bool = True,
    ):
        """
        Initialize the cache manager.

        Args:
            max_memory_size: Maximum number of items in memory cache
            max_disk_size: Maximum size of disk cache in bytes (default: 100MB)
            eviction_policy: Cache eviction policy to use
            default_ttl_strategy: Default TTL strategy to use
            auto_adjust_sizes: Whether to automatically adjust cache sizes based on system resources
        """
        # Only initialize once
        if getattr(self, "_initialized", False):
            return

        # Get logger
        self.logger = get_logger()

        # Initialize memory cache
        self._memory_cache: Dict[str, CacheEntry] = {}
        self.max_memory_size = max_memory_size
        self.current_memory_size = 0

        # Initialize disk cache
        self.cache_dir = ensure_dir_exists(get_user_cache_dir() / "cache")
        self.max_disk_size = max_disk_size
        self.current_disk_size = self._calculate_disk_cache_size()

        # Set eviction policy and TTL strategy
        self.eviction_policy = eviction_policy
        self.default_ttl_strategy = default_ttl_strategy

        # Auto-adjust settings
        self.auto_adjust_sizes = auto_adjust_sizes
        if auto_adjust_sizes:
            self._adjust_cache_sizes()

        # Initialize statistics
        self._stats = {
            "memory_hits": 0,
            "memory_misses": 0,
            "disk_hits": 0,
            "disk_misses": 0,
            "memory_evictions": 0,
            "disk_evictions": 0,
            "multi_hits_memory": 0,
            "multi_hits_disk": 0,
            "multi_misses": 0,
            "preloads": 0,
            "invalidations": 0,
        }

        # Initialize file watchers for cache invalidation
        self._file_watchers: Dict[str, float] = {}
        self._file_watcher_thread = None
        self._file_watcher_running = False

        # Initialize frequently accessed items tracking
        self._access_frequency: Dict[str, int] = {}
        self._preloaded_keys: List[str] = []

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

    def get(
        self, key: str, default: Any = None, backend: CacheBackend = CacheBackend.MEMORY
    ) -> Any:
        """
        Get a value from the cache.

        Args:
            key: Cache key
            default: Default value if key not found
            backend: Cache backend to use

        Returns:
            Any: Cached value or default
        """
        # Track access frequency for preloading
        self._access_frequency[key] = self._access_frequency.get(key, 0) + 1

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
                        if (time.time() - metadata.get("created_at", 0)) > metadata[
                            "ttl"
                        ]:
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

        elif backend == CacheBackend.MULTI:
            # Try memory cache first, then disk cache
            memory_value = self.get(key, None, CacheBackend.MEMORY)
            if memory_value is not None:
                self._stats["multi_hits_memory"] += 1
                return memory_value

            # Try disk cache
            disk_value = self.get(key, None, CacheBackend.DISK)
            if disk_value is not None:
                # Promote to memory cache for faster future access
                self.set(key, disk_value, backend=CacheBackend.MEMORY)
                self._stats["multi_hits_disk"] += 1
                return disk_value

            self._stats["multi_misses"] += 1
            return default

        return default

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        backend: CacheBackend = CacheBackend.MEMORY,
        ttl_strategy: Optional[TTLStrategy] = None,
    ) -> None:
        """
        Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None for no expiration)
            backend: Cache backend to use
            ttl_strategy: TTL strategy to use (None for default)
        """
        # Use default TTL strategy if not specified
        if ttl_strategy is None:
            ttl_strategy = self.default_ttl_strategy

        if backend == CacheBackend.MEMORY:
            # Check if we need to evict
            if (
                len(self._memory_cache) >= self.max_memory_size
                and key not in self._memory_cache
            ):
                self._evict_memory_cache()

            # Set in memory cache
            entry = CacheEntry(key, value, ttl, ttl_strategy)
            self._memory_cache[key] = entry

            # Update memory size tracking
            self.current_memory_size += entry.size

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
                    "ttl_strategy": ttl_strategy.value if ttl_strategy else None,
                    "access_count": 0,
                }

                # Serialize data
                data = self._serialize(value)

                # Write metadata and data
                metadata_bytes = json.dumps(metadata).encode()
                with open(cache_path, "wb") as f:
                    f.write(len(metadata_bytes).to_bytes(4, byteorder="little"))
                    f.write(metadata_bytes)
                    f.write(data)

                # Update disk size tracking
                self.current_disk_size += cache_path.stat().st_size

                # Check disk cache size and evict if necessary
                self._check_disk_cache_size()

            except Exception as e:
                self.logger.error(f"Error writing to disk cache: {str(e)}")

        elif backend == CacheBackend.MULTI:
            # Set in both memory and disk cache
            self.set(key, value, ttl, CacheBackend.MEMORY, ttl_strategy)
            self.set(key, value, ttl, CacheBackend.DISK, ttl_strategy)

    def delete(self, key: str, backend: CacheBackend = CacheBackend.MEMORY) -> bool:
        """
        Delete a value from the cache.

        Args:
            key: Cache key
            backend: Cache backend to use

        Returns:
            bool: True if deleted, False if not found
        """
        result = False

        if backend == CacheBackend.MEMORY:
            # Delete from memory cache
            if key in self._memory_cache:
                # Update memory size tracking
                self.current_memory_size -= self._memory_cache[key].size
                del self._memory_cache[key]
                result = True

        elif backend == CacheBackend.DISK:
            # Delete from disk cache
            cache_path = self._get_disk_path(key)
            if cache_path.exists():
                try:
                    # Update disk size tracking
                    self.current_disk_size -= cache_path.stat().st_size
                    cache_path.unlink()
                    result = True
                except Exception as e:
                    self.logger.error(f"Error deleting from disk cache: {str(e)}")

        elif backend == CacheBackend.MULTI:
            # Delete from both memory and disk cache
            memory_result = self.delete(key, CacheBackend.MEMORY)
            disk_result = self.delete(key, CacheBackend.DISK)
            result = memory_result or disk_result

        # Remove from access frequency tracking
        if key in self._access_frequency:
            del self._access_frequency[key]

        # Remove from preloaded keys
        if key in self._preloaded_keys:
            self._preloaded_keys.remove(key)

        # Update stats
        if result:
            self._stats["invalidations"] += 1

        return result

    def clear(self, backend: Optional[CacheBackend] = None) -> None:
        """
        Clear the cache.

        Args:
            backend: Cache backend to clear (None for all)
        """
        if (
            backend is None
            or backend == CacheBackend.MEMORY
            or backend == CacheBackend.MULTI
        ):
            # Clear memory cache
            self._memory_cache.clear()
            self.current_memory_size = 0
            self.logger.debug("Memory cache cleared")

        if (
            backend is None
            or backend == CacheBackend.DISK
            or backend == CacheBackend.MULTI
        ):
            # Clear disk cache
            try:
                for cache_file in self.cache_dir.glob("*.cache"):
                    cache_file.unlink()
                self.current_disk_size = 0
                self.logger.debug("Disk cache cleared")
            except Exception as e:
                self.logger.error(f"Error clearing disk cache: {str(e)}")

        # Clear tracking data
        if backend is None:
            self._access_frequency.clear()
            self._preloaded_keys.clear()
            self._file_watchers.clear()

    def _evict_memory_cache(self) -> None:
        """
        Evict items from the memory cache based on the configured eviction policy.
        """
        if not self._memory_cache:
            return

        # Find the entry to evict based on the policy
        entries = [(key, entry) for key, entry in self._memory_cache.items()]

        if self.eviction_policy == CachePolicy.LRU:
            # Sort by last accessed time (oldest first)
            entries.sort(key=lambda x: x[1].last_accessed)
        elif self.eviction_policy == CachePolicy.MRU:
            # Sort by last accessed time (newest first)
            entries.sort(key=lambda x: x[1].last_accessed, reverse=True)
        elif self.eviction_policy == CachePolicy.FIFO:
            # Sort by creation time (oldest first)
            entries.sort(key=lambda x: x[1].created_at)
        elif self.eviction_policy == CachePolicy.LFU:
            # Sort by access count (least first)
            entries.sort(key=lambda x: x[1].access_count)
        else:
            # Default to LRU
            entries.sort(key=lambda x: x[1].last_accessed)

        # Get the key to evict
        key_to_evict = entries[0][0]

        # Remove it
        if key_to_evict in self._memory_cache:
            # Update memory size tracking
            self.current_memory_size -= self._memory_cache[key_to_evict].size
            del self._memory_cache[key_to_evict]
            self._stats["memory_evictions"] += 1

    def _check_disk_cache_size(self) -> None:
        """
        Check disk cache size and evict if necessary based on the configured eviction policy.
        """
        try:
            # Get all cache files
            cache_files = list(self.cache_dir.glob("*.cache"))

            # Calculate total size
            total_size = sum(f.stat().st_size for f in cache_files)
            self.current_disk_size = total_size

            # If under limit, no need to evict
            if total_size <= self.max_disk_size:
                return

            # Need to evict - get metadata for all files
            file_stats = []
            for cache_file in cache_files:
                try:
                    # Read metadata
                    with open(cache_file, "rb") as f:
                        metadata_size = int.from_bytes(f.read(4), byteorder="little")
                        metadata_bytes = f.read(metadata_size)
                        metadata = json.loads(metadata_bytes.decode())

                    file_stats.append(
                        {
                            "path": cache_file,
                            "size": cache_file.stat().st_size,
                            "last_accessed": metadata.get("last_accessed", 0),
                            "created_at": metadata.get("created_at", 0),
                            "access_count": metadata.get("access_count", 0),
                        }
                    )
                except Exception:
                    # If we can't read metadata, assume old
                    file_stats.append(
                        {
                            "path": cache_file,
                            "size": cache_file.stat().st_size,
                            "last_accessed": 0,
                            "created_at": 0,
                            "access_count": 0,
                        }
                    )

            # Sort based on eviction policy
            if self.eviction_policy == CachePolicy.LRU:
                # Sort by last accessed time (oldest first)
                file_stats.sort(key=lambda x: x["last_accessed"])
            elif self.eviction_policy == CachePolicy.MRU:
                # Sort by last accessed time (newest first)
                file_stats.sort(key=lambda x: x["last_accessed"], reverse=True)
            elif self.eviction_policy == CachePolicy.FIFO:
                # Sort by creation time (oldest first)
                file_stats.sort(key=lambda x: x["created_at"])
            elif self.eviction_policy == CachePolicy.LFU:
                # Sort by access count (least first)
                file_stats.sort(key=lambda x: x["access_count"])
            else:
                # Default to LRU
                file_stats.sort(key=lambda x: x["last_accessed"])

            # Remove files until we're under the limit
            removed_size = 0
            eviction_count = 0
            for stat in file_stats:
                if total_size - removed_size <= self.max_disk_size:
                    break

                # Remove the file
                try:
                    stat["path"].unlink()
                    removed_size += stat["size"]
                    eviction_count += 1
                    self.current_disk_size -= stat["size"]
                except Exception as e:
                    self.logger.error(f"Error removing cache file: {str(e)}")

            self._stats["disk_evictions"] += eviction_count
            self.logger.debug(f"Evicted {eviction_count} files from disk cache")

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

    def _calculate_disk_cache_size(self) -> int:
        """
        Calculate the current size of the disk cache.

        Returns:
            int: Size in bytes
        """
        try:
            cache_files = list(self.cache_dir.glob("*.cache"))
            return sum(f.stat().st_size for f in cache_files)
        except Exception as e:
            self.logger.error(f"Error calculating disk cache size: {str(e)}")
            return 0

    def _adjust_cache_sizes(self) -> None:
        """
        Adjust cache sizes based on available system resources.
        """
        try:
            import psutil

            # Get system memory info
            mem = psutil.virtual_memory()
            total_memory = mem.total
            available_memory = mem.available

            # Adjust memory cache size (use up to 5% of available memory)
            max_memory_items = int(
                (available_memory * 0.05) / 1024
            )  # Rough estimate: 1KB per item
            self.max_memory_size = max(
                1000, min(max_memory_items, 100000)
            )  # Between 1K and 100K items

            # Adjust disk cache size (use up to 1% of free disk space)
            disk = psutil.disk_usage(self.cache_dir)
            free_disk = disk.free
            self.max_disk_size = max(
                100 * 1024 * 1024, min(free_disk * 0.01, 10 * 1024 * 1024 * 1024)
            )  # Between 100MB and 10GB

            self.logger.debug(
                f"Adjusted cache sizes: memory={self.max_memory_size} items, disk={self.max_disk_size/1024/1024:.1f}MB"
            )
        except ImportError:
            self.logger.warning("psutil not available, using default cache sizes")
        except Exception as e:
            self.logger.error(f"Error adjusting cache sizes: {str(e)}")

    def preload_frequently_accessed(
        self, min_access_count: int = 5, max_items: int = 100
    ) -> int:
        """
        Preload frequently accessed items into memory cache.

        Args:
            min_access_count: Minimum access count to consider an item frequently accessed
            max_items: Maximum number of items to preload

        Returns:
            int: Number of items preloaded
        """
        # Get frequently accessed items
        frequent_items = [
            (k, v) for k, v in self._access_frequency.items() if v >= min_access_count
        ]
        frequent_items.sort(
            key=lambda x: x[1], reverse=True
        )  # Sort by access count (highest first)
        frequent_items = frequent_items[:max_items]  # Limit to max_items

        # Preload items
        preloaded = 0
        for key, _ in frequent_items:
            # Skip if already in memory
            if key in self._memory_cache:
                continue

            # Try to get from disk
            value = self.get(key, None, CacheBackend.DISK)
            if value is not None:
                # Add to memory cache
                self.set(key, value, backend=CacheBackend.MEMORY)
                self._preloaded_keys.append(key)
                preloaded += 1
                self._stats["preloads"] += 1

        return preloaded

    def watch_file(self, file_path: Union[str, Path], key_prefix: str = "") -> None:
        """
        Watch a file for changes and invalidate related cache entries when it changes.

        Args:
            file_path: Path to the file to watch
            key_prefix: Prefix for cache keys to invalidate
        """
        file_path = Path(file_path)
        if not file_path.exists():
            self.logger.warning(f"Cannot watch non-existent file: {file_path}")
            return

        # Store the file's last modification time
        self._file_watchers[str(file_path)] = file_path.stat().st_mtime

        # Start the file watcher thread if not already running
        self._start_file_watcher()

    def _start_file_watcher(self) -> None:
        """
        Start the file watcher thread if not already running.
        """
        if self._file_watcher_thread is not None and self._file_watcher_running:
            return

        self._file_watcher_running = True
        self._file_watcher_thread = threading.Thread(
            target=self._file_watcher_loop, daemon=True
        )
        self._file_watcher_thread.start()

    def _file_watcher_loop(self) -> None:
        """
        Loop that checks for file changes and invalidates cache entries.
        """
        while self._file_watcher_running:
            try:
                # Check each watched file
                for file_path_str, last_mtime in list(self._file_watchers.items()):
                    file_path = Path(file_path_str)
                    if not file_path.exists():
                        # File was deleted, remove from watchers
                        del self._file_watchers[file_path_str]
                        continue

                    # Check if file was modified
                    current_mtime = file_path.stat().st_mtime
                    if current_mtime > last_mtime:
                        # File was modified, invalidate related cache entries
                        self._invalidate_for_file(file_path_str)
                        # Update last modification time
                        self._file_watchers[file_path_str] = current_mtime
            except Exception as e:
                self.logger.error(f"Error in file watcher: {str(e)}")

            # Sleep for a bit
            time.sleep(5)  # Check every 5 seconds

    def _invalidate_for_file(self, file_path: str) -> None:
        """
        Invalidate cache entries related to a file.

        Args:
            file_path: Path to the file
        """
        # Find cache keys that contain the file path
        keys_to_invalidate = []

        # Check memory cache
        for key in list(self._memory_cache.keys()):
            if file_path in key:
                keys_to_invalidate.append(key)

        # Invalidate found keys
        for key in keys_to_invalidate:
            self.delete(key, CacheBackend.MULTI)

        self.logger.debug(
            f"Invalidated {len(keys_to_invalidate)} cache entries for file: {file_path}"
        )

    def stop_file_watcher(self) -> None:
        """
        Stop the file watcher thread.
        """
        self._file_watcher_running = False
        if self._file_watcher_thread is not None:
            self._file_watcher_thread.join(timeout=1)
            self._file_watcher_thread = None


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


def cache_get(
    key: str, default: Any = None, backend: CacheBackend = CacheBackend.MEMORY
) -> Any:
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


def cache_set(
    key: str,
    value: Any,
    ttl: Optional[int] = None,
    backend: CacheBackend = CacheBackend.MEMORY,
    ttl_strategy: Optional[TTLStrategy] = None,
) -> None:
    """
    Set a value in the cache.

    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds (None for no expiration)
        backend: Cache backend to use
        ttl_strategy: TTL strategy to use (None for default)
    """
    return get_cache_manager().set(key, value, ttl, backend, ttl_strategy)


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


def preload_cache(min_access_count: int = 5, max_items: int = 100) -> int:
    """
    Preload frequently accessed items into memory cache.

    Args:
        min_access_count: Minimum access count to consider an item frequently accessed
        max_items: Maximum number of items to preload

    Returns:
        int: Number of items preloaded
    """
    return get_cache_manager().preload_frequently_accessed(min_access_count, max_items)


def watch_file(file_path: Union[str, Path], key_prefix: str = "") -> None:
    """
    Watch a file for changes and invalidate related cache entries when it changes.

    Args:
        file_path: Path to the file to watch
        key_prefix: Prefix for cache keys to invalidate
    """
    return get_cache_manager().watch_file(file_path, key_prefix)


def stop_file_watcher() -> None:
    """
    Stop the file watcher thread.
    """
    return get_cache_manager().stop_file_watcher()


# Decorator for caching function results
def cached(
    ttl: Optional[int] = None,
    key_prefix: str = "",
    backend: CacheBackend = CacheBackend.MEMORY,
    ttl_strategy: Optional[TTLStrategy] = None,
):
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
            cache_set(cache_key, result, ttl, backend, ttl_strategy)

            return result

        return wrapper

    return decorator
