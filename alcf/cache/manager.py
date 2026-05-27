import hashlib
import json
import inspect
from typing import Callable, Any
from functools import wraps

from alcf.cache.backends import RedisCache, MemoryCache


class CacheManager:
    """Class to manage and streamline caching with dual options."""

    def __init__(self, redis_backend=None, memory_backend=None):
        """Initialize the two cache strategies."""
        self.redis = redis_backend
        self.memory = memory_backend


    def _make_key(self, func: Callable, args: tuple, kwargs: dict) -> str:
        """Generate unique keys based on function and its arguments."""

        # Build payload from input
        payload = {
            "module": func.__module__,
            "qualname": func.__qualname__,
            "file": func.__code__.co_filename,
            "line": func.__code__.co_firstlineno,
            "args": args,
            "kwargs": kwargs,
        }

        # Convert payload to a serialized string
        serialized = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )

        # Create and return hashed key from serialized string
        return hashlib.sha256(serialized.encode()).hexdigest()


    def get(self, key: str):
        """Get cached value from key."""

        # Try Redis first
        if self.redis:
            value = self.redis.get(key)
            if value is not None:
                return json.loads(value)
            
        # Try memory cache if Redis failed
        if self.memory:
            value = self.memory.get(key)
            if value is not None:
                return value

        # None if nothing cached for the given key
        return None


    def set(self, key: str, value: Any, ttl: int = 60):

        # Try Redis first
        if self.redis:
            try:
                self.redis.set(key, json.dumps(value), ttl)
                return # Skip memory cache
            except Exception:
                pass # Try memory cache

        # Fallback to memory if Redis failed
        if self.memory:
            self.memory.set(key, value, ttl)


    def cached(self, ttl: int = 60):
        def decorator(func: Callable):
            """Decorator for caching async and sync functions."""
            
            # For asynchronous function
            if inspect.iscoroutinefunction(func):
                @wraps(func)
                async def async_wrapper(*args, **kwargs):

                    # Get cached value if available
                    key = self._make_key(func, args, kwargs)
                    cached_value = self.get(key)
                    if cached_value is not None:
                        return cached_value
                    
                    # Execute async function and wait for result
                    result = await func(*args, **kwargs)

                    # Cache and return result 
                    self.set(key, result, ttl)
                    return result
                return async_wrapper
            
            # For synchronous function
            else:
                @wraps(func)
                def sync_wrapper(*args, **kwargs):

                    # Get cached value if available
                    key = self._make_key(func, args, kwargs)
                    cached_value = self.get(key)
                    if cached_value is not None:
                        return cached_value
                    
                    # Execute function and get result
                    result = func(*args, **kwargs)

                    # Cache and return result 
                    self.set(key, result, ttl)
                    return result
                return sync_wrapper
            
        return decorator


# Cache Manager
cache_manager = CacheManager(
    redis_backend=RedisCache(),
    memory_backend=MemoryCache()
)