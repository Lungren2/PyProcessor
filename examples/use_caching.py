"""
Example script demonstrating how to use the caching system.

This script shows how to cache data in memory and on disk, and how to use the caching decorator.
"""

import os
import sys
import time
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyprocessor.utils.core.cache_manager import (
    cache_get,
    cache_set,
    cache_delete,
    cache_clear,
    get_cache_stats,
    reset_cache_stats,
    cached,
    CacheBackend
)


def expensive_operation(n):
    """Simulate an expensive operation."""
    print(f"Performing expensive operation for n={n}...")
    time.sleep(2)  # Simulate work
    return n * n


@cached(ttl=10)
def cached_operation(n):
    """Cached version of the expensive operation."""
    print(f"Performing cached operation for n={n}...")
    time.sleep(2)  # Simulate work
    return n * n


@cached(ttl=10, backend=CacheBackend.DISK)
def disk_cached_operation(n):
    """Disk-cached version of the expensive operation."""
    print(f"Performing disk-cached operation for n={n}...")
    time.sleep(2)  # Simulate work
    return n * n


def print_stats():
    """Print cache statistics."""
    stats = get_cache_stats()
    print("\nCache Statistics:")
    print(f"Memory hits: {stats['memory_hits']}")
    print(f"Memory misses: {stats['memory_misses']}")
    print(f"Disk hits: {stats['disk_hits']}")
    print(f"Disk misses: {stats['disk_misses']}")
    print(f"Memory evictions: {stats['memory_evictions']}")
    print(f"Disk evictions: {stats['disk_evictions']}")


def main():
    """Main function demonstrating caching usage."""
    print("Caching System Example")
    print("=====================")

    # Clear the cache to start fresh
    cache_clear()
    reset_cache_stats()

    # Basic memory caching
    print("\n1. Basic Memory Caching")

    # First call (cache miss)
    start = time.time()
    result1 = expensive_operation(5)
    duration1 = time.time() - start
    print(f"Result: {result1}, Duration: {duration1:.2f}s")

    # Cache the result
    cache_set("expensive_operation:5", result1)

    # Second call (cache hit)
    start = time.time()
    result2 = cache_get("expensive_operation:5")
    duration2 = time.time() - start
    print(f"Result: {result2}, Duration: {duration2:.2f}s")

    print(f"Speedup: {duration1 / duration2:.2f}x")

    # Caching decorator
    print("\n2. Caching Decorator")

    # First call (cache miss)
    start = time.time()
    result1 = cached_operation(10)
    duration1 = time.time() - start
    print(f"Result: {result1}, Duration: {duration1:.2f}s")

    # Second call (cache hit)
    start = time.time()
    result2 = cached_operation(10)
    duration2 = time.time() - start
    print(f"Result: {result2}, Duration: {duration2:.2f}s")

    print(f"Speedup: {duration1 / duration2:.2f}x")

    # Disk caching
    print("\n3. Disk Caching")

    # First call (cache miss)
    start = time.time()
    result1 = disk_cached_operation(15)
    duration1 = time.time() - start
    print(f"Result: {result1}, Duration: {duration1:.2f}s")

    # Second call (cache hit)
    start = time.time()
    result2 = disk_cached_operation(15)
    duration2 = time.time() - start
    print(f"Result: {result2}, Duration: {duration2:.2f}s")

    print(f"Speedup: {duration1 / duration2:.2f}x")

    # Cache invalidation
    print("\n4. Cache Invalidation")

    # Cache with TTL
    cache_set("short_lived", "I will expire soon", ttl=5)
    print("Cached 'short_lived' with TTL=5 seconds")

    # Check immediately
    print(f"Immediate value: {cache_get('short_lived')}")

    # Wait for expiration
    print("Waiting for expiration...")
    time.sleep(6)

    # Check after expiration
    print(f"After expiration: {cache_get('short_lived')}")

    # Manual invalidation
    cache_set("manual_delete", "Delete me")
    print(f"Before delete: {cache_get('manual_delete')}")
    cache_delete("manual_delete")
    print(f"After delete: {cache_get('manual_delete')}")

    # Cache statistics
    print_stats()

    # Clear cache
    print("\n5. Clearing Cache")
    cache_clear(backend=CacheBackend.MEMORY)
    print("Memory cache cleared")
    cache_clear(backend=CacheBackend.DISK)
    print("Disk cache cleared")

    print("\nCaching example completed")


if __name__ == "__main__":
    main()
