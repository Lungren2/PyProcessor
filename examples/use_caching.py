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
    preload_cache,
    watch_file,
    stop_file_watcher,
    CacheBackend,
    CachePolicy,
    TTLStrategy
)


def expensive_operation(n):
    """Simulate an expensive operation."""
    print(f"Performing expensive operation for n={n}...")
    time.sleep(2)  # Simulate work
    return n * n


@cached(ttl=10, ttl_strategy=TTLStrategy.FIXED)
def cached_operation(n):
    """Cached version of the expensive operation with fixed TTL."""
    print(f"Performing cached operation for n={n}...")
    time.sleep(2)  # Simulate work
    return n * n


@cached(ttl=10, ttl_strategy=TTLStrategy.SLIDING)
def sliding_cached_operation(n):
    """Cached version of the expensive operation with sliding TTL."""
    print(f"Performing sliding cached operation for n={n}...")
    time.sleep(2)  # Simulate work
    return n * n


@cached(ttl=10, backend=CacheBackend.DISK)
def disk_cached_operation(n):
    """Disk-cached version of the expensive operation."""
    print(f"Performing disk-cached operation for n={n}...")
    time.sleep(2)  # Simulate work
    return n * n


@cached(ttl=10, backend=CacheBackend.MULTI)
def multi_cached_operation(n):
    """Multi-level cached version of the expensive operation."""
    print(f"Performing multi-level cached operation for n={n}...")
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
    print(f"Multi-level hits (memory): {stats['multi_hits_memory']}")
    print(f"Multi-level hits (disk): {stats['multi_hits_disk']}")
    print(f"Multi-level misses: {stats['multi_misses']}")
    print(f"Memory evictions: {stats['memory_evictions']}")
    print(f"Disk evictions: {stats['disk_evictions']}")
    print(f"Preloads: {stats['preloads']}")
    print(f"Invalidations: {stats['invalidations']}")


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

    # Multi-level caching
    print("\n5. Multi-level Caching")

    # First call (cache miss)
    start = time.time()
    result1 = multi_cached_operation(20)
    duration1 = time.time() - start
    print(f"Result: {result1}, Duration: {duration1:.2f}s")

    # Second call (cache hit from memory)
    start = time.time()
    result2 = multi_cached_operation(20)
    duration2 = time.time() - start
    print(f"Result: {result2}, Duration: {duration2:.2f}s")

    print(f"Speedup: {duration1 / duration2:.2f}x")

    # Clear memory cache to test disk fallback
    cache_clear(backend=CacheBackend.MEMORY)
    print("Memory cache cleared, testing disk fallback...")

    # Third call (cache hit from disk, promoted to memory)
    start = time.time()
    result3 = multi_cached_operation(20)
    duration3 = time.time() - start
    print(f"Result: {result3}, Duration: {duration3:.2f}s")

    # Sliding TTL
    print("\n6. Sliding TTL")

    # First call (cache miss)
    start = time.time()
    result1 = sliding_cached_operation(25)
    duration1 = time.time() - start
    print(f"Result: {result1}, Duration: {duration1:.2f}s")

    # Second call (cache hit)
    start = time.time()
    result2 = sliding_cached_operation(25)
    duration2 = time.time() - start
    print(f"Result: {result2}, Duration: {duration2:.2f}s")

    print("Waiting 6 seconds (TTL is 10 seconds)...")
    time.sleep(6)  # Wait 6 seconds (TTL is 10 seconds)

    # Third call (still a cache hit because of sliding TTL)
    start = time.time()
    result3 = sliding_cached_operation(25)
    duration3 = time.time() - start
    print(f"Result: {result3}, Duration: {duration3:.2f}s")

    print("Waiting 11 seconds (should expire now)...")
    time.sleep(11)  # Wait 11 seconds (should expire now)

    # Fourth call (cache miss because TTL expired)
    start = time.time()
    result4 = sliding_cached_operation(25)
    duration4 = time.time() - start
    print(f"Result: {result4}, Duration: {duration4:.2f}s")

    # File watching
    print("\n7. File Watching")

    # Create a test file
    test_file = Path("test_cache_file.txt")
    with open(test_file, "w") as f:
        f.write("Initial content")

    # Cache a value with the file path in the key
    cache_key = f"file:{test_file}:content"
    cache_set(cache_key, "Cached content")
    print(f"Cached value: {cache_get(cache_key)}")

    # Watch the file
    watch_file(test_file)
    print(f"Watching file: {test_file}")

    # Modify the file
    time.sleep(1)  # Wait a bit
    with open(test_file, "w") as f:
        f.write("Modified content")
    print("File modified")

    # Wait for the file watcher to detect the change
    time.sleep(6)

    # Check if the cache was invalidated
    print(f"Cached value after modification: {cache_get(cache_key)}")

    # Clean up
    stop_file_watcher()
    test_file.unlink()

    # Preloading
    print("\n8. Cache Preloading")

    # Cache several items
    for i in range(10):
        cache_key = f"preload_test:{i}"
        cache_set(cache_key, f"Value {i}", backend=CacheBackend.DISK)

    # Access some items multiple times to increase their frequency
    for _ in range(5):
        for i in [2, 5, 8]:
            cache_key = f"preload_test:{i}"
            cache_get(cache_key, backend=CacheBackend.DISK)

    # Clear memory cache
    cache_clear(backend=CacheBackend.MEMORY)

    # Preload frequently accessed items
    num_preloaded = preload_cache(min_access_count=3, max_items=5)
    print(f"Preloaded {num_preloaded} items")

    # Check which items were preloaded
    for i in range(10):
        cache_key = f"preload_test:{i}"
        in_memory = cache_get(cache_key, None, CacheBackend.MEMORY) is not None
        print(f"Item {i}: {'in memory' if in_memory else 'not in memory'}")

    # Clear cache
    print("\n9. Clearing Cache")
    cache_clear()
    print("All caches cleared")

    print("\nCaching example completed")


if __name__ == "__main__":
    main()
