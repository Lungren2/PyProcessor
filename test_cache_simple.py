"""
Simple test script for the enhanced caching system.
"""

import os
import sys
import time
import json
import pickle
import hashlib
import threading
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, Callable

# Define the necessary classes for testing
class CacheBackend(Enum):
    """Cache backend types."""
    MEMORY = "memory"
    DISK = "disk"
    MULTI = "multi"  # Multi-level cache (memory + disk)


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

    def __init__(self, key: str, value: Any, ttl: Optional[int] = None,
                 ttl_strategy: TTLStrategy = TTLStrategy.FIXED):
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


class SimpleCacheManager:
    """A simplified version of the CacheManager for testing."""

    def __init__(self, max_memory_size: int = 100, max_disk_size: int = 1024 * 1024,
                 eviction_policy: CachePolicy = CachePolicy.LRU,
                 default_ttl_strategy: TTLStrategy = TTLStrategy.FIXED):
        """Initialize the cache manager."""
        # Initialize memory cache
        self._memory_cache: Dict[str, CacheEntry] = {}
        self.max_memory_size = max_memory_size
        self.current_memory_size = 0

        # Initialize disk cache
        self.cache_dir = Path("./cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.max_disk_size = max_disk_size
        self.current_disk_size = self._calculate_disk_cache_size()

        # Set eviction policy and TTL strategy
        self.eviction_policy = eviction_policy
        self.default_ttl_strategy = default_ttl_strategy

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

        # Initialize access frequency tracking
        self._access_frequency: Dict[str, int] = {}
        self._preloaded_keys: List[str] = []

    def _calculate_disk_cache_size(self) -> int:
        """Calculate the current size of the disk cache."""
        try:
            cache_files = list(self.cache_dir.glob("*.cache"))
            return sum(f.stat().st_size for f in cache_files)
        except Exception as e:
            print(f"Error calculating disk cache size: {str(e)}")
            return 0

    def _get_disk_path(self, key: str) -> Path:
        """Get the disk path for a cache key."""
        # Create a hash of the key to use as the filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    def _serialize(self, value: Any) -> bytes:
        """Serialize a value for disk storage."""
        return pickle.dumps(value)

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize a value from disk storage."""
        return pickle.loads(data)

    def get(self, key: str, default: Any = None, backend: CacheBackend = CacheBackend.MEMORY) -> Any:
        """Get a value from the cache."""
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
                    print(f"Error reading from disk cache: {str(e)}")
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

    def set(self, key: str, value: Any, ttl: Optional[int] = None,
            backend: CacheBackend = CacheBackend.MEMORY,
            ttl_strategy: Optional[TTLStrategy] = None) -> None:
        """Set a value in the cache."""
        # Use default TTL strategy if not specified
        if ttl_strategy is None:
            ttl_strategy = self.default_ttl_strategy

        if backend == CacheBackend.MEMORY:
            # Check if we need to evict
            if len(self._memory_cache) >= self.max_memory_size and key not in self._memory_cache:
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

                # Update disk size tracking
                self.current_disk_size += cache_path.stat().st_size

                # Check disk cache size and evict if necessary
                self._check_disk_cache_size()

            except Exception as e:
                print(f"Error writing to disk cache: {str(e)}")

        elif backend == CacheBackend.MULTI:
            # Set in both memory and disk cache
            self.set(key, value, ttl, CacheBackend.MEMORY, ttl_strategy)
            self.set(key, value, ttl, CacheBackend.DISK, ttl_strategy)

    def delete(self, key: str, backend: CacheBackend = CacheBackend.MEMORY) -> bool:
        """Delete a value from the cache."""
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
                    print(f"Error deleting from disk cache: {str(e)}")

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
        """Clear the cache."""
        if backend is None or backend == CacheBackend.MEMORY or backend == CacheBackend.MULTI:
            # Clear memory cache
            self._memory_cache.clear()
            self.current_memory_size = 0
            print("Memory cache cleared")

        if backend is None or backend == CacheBackend.DISK or backend == CacheBackend.MULTI:
            # Clear disk cache
            try:
                for cache_file in self.cache_dir.glob("*.cache"):
                    cache_file.unlink()
                self.current_disk_size = 0
                print("Disk cache cleared")
            except Exception as e:
                print(f"Error clearing disk cache: {str(e)}")

        # Clear tracking data
        if backend is None:
            self._access_frequency.clear()
            self._preloaded_keys.clear()

    def _evict_memory_cache(self) -> None:
        """Evict items from the memory cache based on the configured eviction policy."""
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
        """Check disk cache size and evict if necessary based on the configured eviction policy."""
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

                    file_stats.append({
                        "path": cache_file,
                        "size": cache_file.stat().st_size,
                        "last_accessed": metadata.get("last_accessed", 0),
                        "created_at": metadata.get("created_at", 0),
                        "access_count": metadata.get("access_count", 0)
                    })
                except Exception:
                    # If we can't read metadata, assume old
                    file_stats.append({
                        "path": cache_file,
                        "size": cache_file.stat().st_size,
                        "last_accessed": 0,
                        "created_at": 0,
                        "access_count": 0
                    })

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
                    print(f"Error removing cache file: {str(e)}")

            self._stats["disk_evictions"] += eviction_count
            print(f"Evicted {eviction_count} files from disk cache")

        except Exception as e:
            print(f"Error checking disk cache size: {str(e)}")

    def preload_frequently_accessed(self, min_access_count: int = 5, max_items: int = 100) -> int:
        """Preload frequently accessed items into memory cache."""
        # Get frequently accessed items
        frequent_items = [(k, v) for k, v in self._access_frequency.items() if v >= min_access_count]
        frequent_items.sort(key=lambda x: x[1], reverse=True)  # Sort by access count (highest first)
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

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return self._stats.copy()


def test_cache():
    """Test the enhanced caching system."""
    print("Testing Enhanced Caching System")
    print("==============================")
    
    # Create a cache manager instance
    cache_manager = SimpleCacheManager(
        max_memory_size=100,
        max_disk_size=1024 * 1024,  # 1MB
        eviction_policy=CachePolicy.LRU,
        default_ttl_strategy=TTLStrategy.FIXED
    )
    
    # Test memory caching
    print("\n1. Memory Caching")
    cache_manager.set("test_key", "test_value", backend=CacheBackend.MEMORY)
    value = cache_manager.get("test_key", backend=CacheBackend.MEMORY)
    print(f"Memory cache test: {'PASS' if value == 'test_value' else 'FAIL'}")
    
    # Test disk caching
    print("\n2. Disk Caching")
    cache_manager.set("test_key_disk", "test_value_disk", backend=CacheBackend.DISK)
    value = cache_manager.get("test_key_disk", backend=CacheBackend.DISK)
    print(f"Disk cache test: {'PASS' if value == 'test_value_disk' else 'FAIL'}")
    
    # Test multi-level caching
    print("\n3. Multi-level Caching")
    cache_manager.set("test_key_multi", "test_value_multi", backend=CacheBackend.MULTI)
    
    # Clear memory cache to test fallback
    cache_manager._memory_cache.clear()
    
    # Should get from disk and promote to memory
    value = cache_manager.get("test_key_multi", backend=CacheBackend.MULTI)
    print(f"Multi-level cache test: {'PASS' if value == 'test_value_multi' else 'FAIL'}")
    
    # Should now be in memory
    in_memory = "test_key_multi" in cache_manager._memory_cache
    print(f"Promotion to memory test: {'PASS' if in_memory else 'FAIL'}")
    
    # Test TTL
    print("\n4. TTL Test")
    cache_manager.set("test_key_ttl", "test_value_ttl", ttl=2, backend=CacheBackend.MEMORY)
    value1 = cache_manager.get("test_key_ttl", backend=CacheBackend.MEMORY)
    print(f"Initial TTL test: {'PASS' if value1 == 'test_value_ttl' else 'FAIL'}")
    
    print("Waiting for TTL expiration...")
    time.sleep(3)
    
    value2 = cache_manager.get("test_key_ttl", backend=CacheBackend.MEMORY)
    print(f"After TTL test: {'PASS' if value2 is None else 'FAIL'}")
    
    # Test sliding TTL
    print("\n5. Sliding TTL Test")
    cache_manager.set("test_key_sliding", "test_value_sliding", ttl=3, 
                     ttl_strategy=TTLStrategy.SLIDING, backend=CacheBackend.MEMORY)
    
    # Access to reset the TTL
    for i in range(2):
        print(f"Access {i+1}...")
        value = cache_manager.get("test_key_sliding", backend=CacheBackend.MEMORY)
        print(f"Value: {value}")
        time.sleep(2)  # Wait 2 seconds (TTL is 3 seconds)
    
    # Should still be valid because of sliding TTL
    value = cache_manager.get("test_key_sliding", backend=CacheBackend.MEMORY)
    print(f"Sliding TTL test: {'PASS' if value == 'test_value_sliding' else 'FAIL'}")
    
    # Test eviction policy
    print("\n6. Eviction Policy Test")
    # Fill the cache to trigger eviction
    for i in range(110):  # Cache size is 100
        cache_manager.set(f"eviction_test_{i}", f"value_{i}", backend=CacheBackend.MEMORY)
    
    # Check if eviction happened
    cache_size = len(cache_manager._memory_cache)
    print(f"Cache size after filling: {cache_size}")
    print(f"Eviction test: {'PASS' if cache_size <= 100 else 'FAIL'}")
    
    # Test preloading
    print("\n7. Preloading Test")
    # Cache items to disk
    for i in range(10):
        cache_manager.set(f"preload_test_{i}", f"value_{i}", backend=CacheBackend.DISK)
    
    # Access some items multiple times
    for _ in range(5):
        for i in [2, 5, 8]:
            cache_manager._access_frequency[f"preload_test_{i}"] = 5
    
    # Clear memory cache
    cache_manager._memory_cache.clear()
    
    # Preload
    preloaded = cache_manager.preload_frequently_accessed(min_access_count=5, max_items=3)
    print(f"Preloaded {preloaded} items")
    
    # Check which items were preloaded
    preloaded_keys = [key for key in cache_manager._memory_cache.keys() if key.startswith("preload_test_")]
    print(f"Preloaded keys: {preloaded_keys}")
    print(f"Preloading test: {'PASS' if len(preloaded_keys) == 3 else 'FAIL'}")
    
    # Print statistics
    stats = cache_manager.get_stats()
    print("\nCache Statistics:")
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # Clean up
    cache_manager.clear()
    try:
        os.rmdir("./cache")
    except:
        pass
    
    print("\nAll tests completed")

if __name__ == "__main__":
    test_cache()
