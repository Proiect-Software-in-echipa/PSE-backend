import time
from typing import Any, Optional
from functools import wraps


class TTLCache:
    """Cache simplu în memorie cu suport TTL (Time-To-Live)."""

    def __init__(self, default_ttl: int = 60):
        self._store: dict[str, tuple[Any, float]] = {}
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            return None
        value, expires_at = self._store[key]
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl = ttl if ttl is not None else self.default_ttl
        self._store[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    def invalidate_prefix(self, prefix: str) -> int:
        keys_to_delete = [k for k in self._store if k.startswith(prefix)]
        for k in keys_to_delete:
            del self._store[k]
        return len(keys_to_delete)

    def stats(self) -> dict:
        now = time.time()
        active = sum(1 for _, (_, exp) in self._store.items() if exp > now)
        return {"total_keys": len(self._store), "active_keys": active}


# Instanță globală
cache = TTLCache(default_ttl=120)


def cached(key_fn, ttl: int = 120):
    """Decorator pentru caching automat al rezultatelor unei funcții."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = key_fn(*args, **kwargs)
            result = cache.get(cache_key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)
            return result
        return wrapper
    return decorator
