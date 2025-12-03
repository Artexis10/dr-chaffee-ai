"""
Simple TTL Cache Utility

Provides time-based caching for expensive operations.
Thread-safe and suitable for FastAPI async handlers.
"""

import time
import threading
from typing import Any, Callable, Dict, Optional, TypeVar
from functools import wraps

T = TypeVar('T')


class TTLCache:
    """
    Simple time-to-live cache for single values.
    
    Thread-safe and suitable for caching expensive computations
    that should be refreshed periodically.
    
    Usage:
        cache = TTLCache(ttl_seconds=5.0)
        
        def get_expensive_data():
            return cache.get_or_compute("key", lambda: compute_data())
    """
    
    def __init__(self, ttl_seconds: float = 5.0):
        """
        Initialize cache with TTL.
        
        Args:
            ttl_seconds: Time-to-live in seconds (default: 5.0)
        """
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)
        self._lock = threading.Lock()
        self._ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if expired/missing
        """
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if time.time() < expiry:
                    return value
                # Expired - remove it
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """
        Set cached value with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            self._cache[key] = (value, time.time() + self._ttl)
    
    def get_or_compute(self, key: str, compute_fn: Callable[[], Any]) -> Any:
        """
        Get cached value or compute and cache it.
        
        Args:
            key: Cache key
            compute_fn: Function to compute value if not cached
            
        Returns:
            Cached or freshly computed value
        """
        # Check cache first (without lock for read)
        cached = self.get(key)
        if cached is not None:
            return cached
        
        # Compute and cache
        value = compute_fn()
        self.set(key, value)
        return value
    
    def invalidate(self, key: str) -> None:
        """Remove a specific key from cache."""
        with self._lock:
            self._cache.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()


def ttl_cache(ttl_seconds: float = 5.0, key_fn: Optional[Callable] = None):
    """
    Decorator for caching function results with TTL.
    
    Args:
        ttl_seconds: Time-to-live in seconds
        key_fn: Optional function to generate cache key from args.
                If None, uses function name as key (suitable for no-arg functions).
    
    Usage:
        @ttl_cache(ttl_seconds=5.0)
        def get_models():
            return load_models_from_db()
            
        # With custom key:
        @ttl_cache(ttl_seconds=5.0, key_fn=lambda x: f"user_{x}")
        def get_user_data(user_id):
            return fetch_user(user_id)
    """
    cache = TTLCache(ttl_seconds=ttl_seconds)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_fn is not None:
                cache_key = key_fn(*args, **kwargs)
            else:
                cache_key = func.__name__
            
            return cache.get_or_compute(cache_key, lambda: func(*args, **kwargs))
        
        # Expose cache for manual invalidation
        wrapper.cache = cache
        wrapper.invalidate = lambda: cache.invalidate(func.__name__)
        
        return wrapper
    
    return decorator


# Global caches for common use cases
_endpoint_cache = TTLCache(ttl_seconds=5.0)


def get_endpoint_cache() -> TTLCache:
    """Get the shared endpoint cache (5 second TTL)."""
    return _endpoint_cache
