# Caching System in PyProcessor

This document describes the caching system in PyProcessor, including the centralized `CacheManager` class, caching strategies, and cache backends.

## Overview

PyProcessor provides a centralized caching system through the `CacheManager` class in the `pyprocessor.utils.cache_manager` module. This class provides a consistent interface for caching data across the application.

The caching system is designed to:

- Provide a consistent way to cache data
- Support different cache backends (memory, disk)
- Implement cache invalidation strategies
- Track cache statistics
- Optimize performance for frequently accessed data

## CacheManager

The `CacheManager` class is a singleton that provides the following features:

- Memory caching
- Disk caching
- Cache invalidation strategies
- Cache statistics

### Getting the Cache Manager

```python
from pyprocessor.utils.cache_manager import get_cache_manager

# Get the cache manager
cache_manager = get_cache_manager()
```

## Basic Caching Operations

### Setting Values

```python
from pyprocessor.utils.cache_manager import cache_set, CacheBackend

# Cache in memory (default)
cache_set("my_key", "my_value")

# Cache in memory with TTL (time to live)
cache_set("my_key", "my_value", ttl=60)  # 60 seconds

# Cache on disk
cache_set("my_key", "my_value", backend=CacheBackend.DISK)

# Cache on disk with TTL
cache_set("my_key", "my_value", ttl=3600, backend=CacheBackend.DISK)  # 1 hour
```

### Getting Values

```python
from pyprocessor.utils.cache_manager import cache_get, CacheBackend

# Get from memory (default)
value = cache_get("my_key")

# Get from memory with default value
value = cache_get("my_key", default="default_value")

# Get from disk
value = cache_get("my_key", backend=CacheBackend.DISK)

# Get from disk with default value
value = cache_get("my_key", default="default_value", backend=CacheBackend.DISK)
```

### Deleting Values

```python
from pyprocessor.utils.cache_manager import cache_delete, CacheBackend

# Delete from memory (default)
cache_delete("my_key")

# Delete from disk
cache_delete("my_key", backend=CacheBackend.DISK)
```

### Clearing the Cache

```python
from pyprocessor.utils.cache_manager import cache_clear, CacheBackend

# Clear memory cache
cache_clear(backend=CacheBackend.MEMORY)

# Clear disk cache
cache_clear(backend=CacheBackend.DISK)

# Clear all caches
cache_clear()
```

## Caching Decorator

The caching system provides a decorator for caching function results:

```python
from pyprocessor.utils.cache_manager import cached, CacheBackend

# Cache in memory for 60 seconds
@cached(ttl=60)
def get_data(param1, param2):
    # Expensive operation
    return result

# Cache on disk for 1 hour with custom key prefix
@cached(ttl=3600, key_prefix="my_prefix", backend=CacheBackend.DISK)
def get_data(param1, param2):
    # Expensive operation
    return result
```

## Cache Statistics

The caching system tracks statistics for monitoring and debugging:

```python
from pyprocessor.utils.cache_manager import get_cache_stats, reset_cache_stats

# Get cache statistics
stats = get_cache_stats()
print(f"Memory hits: {stats['memory_hits']}")
print(f"Memory misses: {stats['memory_misses']}")
print(f"Disk hits: {stats['disk_hits']}")
print(f"Disk misses: {stats['disk_misses']}")

# Reset cache statistics
reset_cache_stats()
```

## Cache Backends

The caching system supports different backends for storing cached data:

- `CacheBackend.MEMORY`: In-memory cache (fast, but limited by available memory)
- `CacheBackend.DISK`: Disk-based cache (slower, but persistent and larger capacity)

## Cache Invalidation Strategies

The caching system implements different strategies for cache invalidation:

- Time-based expiration (TTL)
- Least Recently Used (LRU) eviction

## Best Practices

1. **Use Memory Cache for Small, Frequently Accessed Data**: Memory cache is faster but has limited capacity.
2. **Use Disk Cache for Larger, Less Frequently Accessed Data**: Disk cache is slower but has larger capacity and is persistent.
3. **Set Appropriate TTL Values**: Set TTL values based on how frequently the data changes.
4. **Use the Caching Decorator for Function Results**: The `@cached` decorator is a convenient way to cache function results.
5. **Monitor Cache Statistics**: Use cache statistics to monitor cache performance and adjust caching strategies.
6. **Clear Caches When Appropriate**: Clear caches when data changes or when memory usage is high.
7. **Use Key Prefixes to Avoid Collisions**: Use key prefixes to avoid key collisions between different parts of the application.
8. **Cache Immutable Data**: Cache data that doesn't change frequently to maximize cache hits.
9. **Don't Cache Sensitive Data**: Avoid caching sensitive data, especially on disk.
10. **Handle Cache Misses Gracefully**: Always handle cache misses gracefully and have a fallback mechanism.

## Example: Caching File Contents

Here's an example of using the caching system to cache file contents:

```python
from pyprocessor.utils.cache_manager import cache_get, cache_set, CacheBackend

def read_file_with_cache(file_path, ttl=3600):
    """
    Read a file with caching.
    
    Args:
        file_path: Path to the file
        ttl: Time to live in seconds (default: 1 hour)
        
    Returns:
        str: File contents
    """
    # Create a cache key from the file path and modification time
    file_path = Path(file_path)
    if not file_path.exists():
        return None
        
    mtime = file_path.stat().st_mtime
    cache_key = f"file:{file_path}:{mtime}"
    
    # Try to get from cache
    cached_content = cache_get(cache_key, backend=CacheBackend.MEMORY)
    if cached_content is not None:
        return cached_content
        
    # Read the file
    with open(file_path, "r") as f:
        content = f.read()
        
    # Cache the content
    cache_set(cache_key, content, ttl=ttl, backend=CacheBackend.MEMORY)
    
    return content
```

## Example: Caching API Responses

Here's an example of using the caching system to cache API responses:

```python
import requests
from pyprocessor.utils.cache_manager import cached, CacheBackend

@cached(ttl=300, key_prefix="api", backend=CacheBackend.DISK)
def get_api_data(url, params=None):
    """
    Get data from an API with caching.
    
    Args:
        url: API URL
        params: Query parameters
        
    Returns:
        dict: API response
    """
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()
```

## Troubleshooting

If you encounter issues with the caching system, try the following:

1. **Check Cache Statistics**: Use `get_cache_stats()` to check cache hits and misses.
2. **Clear the Cache**: Use `cache_clear()` to clear the cache and start fresh.
3. **Check Disk Cache Directory**: Make sure the disk cache directory exists and is writable.
4. **Check TTL Values**: Make sure TTL values are appropriate for your data.
5. **Check Cache Keys**: Make sure cache keys are unique and consistent.
6. **Check Serialization**: Make sure cached values can be serialized and deserialized.
7. **Check Memory Usage**: Make sure memory usage is not too high.
8. **Check Disk Space**: Make sure there's enough disk space for the disk cache.
9. **Check Permissions**: Make sure the application has permission to write to the disk cache directory.
10. **Check for Errors**: Look for error messages in the application logs.
