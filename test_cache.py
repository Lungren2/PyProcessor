"""
Simple test script for the enhanced caching system.
"""

import sys
import time
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import only the cache_manager module
from pyprocessor.utils.core.cache_manager import (
    CacheBackend,
    CachePolicy,
    TTLStrategy,
    CacheManager,
)


def test_cache():
    """Test the enhanced caching system."""
    print("Testing Enhanced Caching System")
    print("==============================")

    # Create a cache manager instance
    cache_manager = CacheManager(
        max_memory_size=100,
        max_disk_size=1024 * 1024,  # 1MB
        eviction_policy=CachePolicy.LRU,
        default_ttl_strategy=TTLStrategy.FIXED,
        auto_adjust_sizes=False,
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
    print(
        f"Multi-level cache test: {'PASS' if value == 'test_value_multi' else 'FAIL'}"
    )

    # Should now be in memory
    in_memory = "test_key_multi" in cache_manager._memory_cache
    print(f"Promotion to memory test: {'PASS' if in_memory else 'FAIL'}")

    # Test TTL
    print("\n4. TTL Test")
    cache_manager.set(
        "test_key_ttl", "test_value_ttl", ttl=2, backend=CacheBackend.MEMORY
    )
    value1 = cache_manager.get("test_key_ttl", backend=CacheBackend.MEMORY)
    print(f"Initial TTL test: {'PASS' if value1 == 'test_value_ttl' else 'FAIL'}")

    print("Waiting for TTL expiration...")
    time.sleep(3)

    value2 = cache_manager.get("test_key_ttl", backend=CacheBackend.MEMORY)
    print(f"After TTL test: {'PASS' if value2 is None else 'FAIL'}")

    # Test sliding TTL
    print("\n5. Sliding TTL Test")
    cache_manager.set(
        "test_key_sliding",
        "test_value_sliding",
        ttl=3,
        ttl_strategy=TTLStrategy.SLIDING,
        backend=CacheBackend.MEMORY,
    )

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
        cache_manager.set(
            f"eviction_test_{i}", f"value_{i}", backend=CacheBackend.MEMORY
        )

    # Check if eviction happened
    cache_size = len(cache_manager._memory_cache)
    print(f"Cache size after filling: {cache_size}")
    print(f"Eviction test: {'PASS' if cache_size <= 100 else 'FAIL'}")

    # Test file watching
    print("\n7. File Watching Test")
    test_file = Path("test_watch_file.txt")
    with open(test_file, "w") as f:
        f.write("Initial content")

    # Cache a value with the file path in the key
    cache_key = f"file:{test_file}:content"
    cache_manager.set(cache_key, "Cached content", backend=CacheBackend.MEMORY)
    cache_manager.watch_file(test_file)

    print(f"Initial cached value: {cache_manager.get(cache_key)}")

    # Modify the file
    time.sleep(1)
    with open(test_file, "w") as f:
        f.write("Modified content")

    # Wait for the file watcher to detect the change
    print("Waiting for file watcher...")
    time.sleep(6)

    # Check if the cache was invalidated
    value = cache_manager.get(cache_key)
    print(f"Cached value after modification: {value}")
    print(f"File watching test: {'PASS' if value is None else 'FAIL'}")

    # Clean up
    cache_manager.stop_file_watcher()
    test_file.unlink()

    # Test preloading
    print("\n8. Preloading Test")
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
    preloaded = cache_manager.preload_frequently_accessed(
        min_access_count=5, max_items=3
    )
    print(f"Preloaded {preloaded} items")

    # Check which items were preloaded
    preloaded_keys = [
        key
        for key in cache_manager._memory_cache.keys()
        if key.startswith("preload_test_")
    ]
    print(f"Preloaded keys: {preloaded_keys}")
    print(f"Preloading test: {'PASS' if len(preloaded_keys) == 3 else 'FAIL'}")

    print("\nAll tests completed")


if __name__ == "__main__":
    test_cache()
