"""TTL-based in-memory caching for computed responses.

Keeps repeated dashboard reruns (re-selecting a team/season/player, or a
Streamlit script rerun on any widget interaction) from re-fetching upstream
data or re-fitting a trajectory model on every request, while still
expiring often enough to pick up newly posted game data.
"""
from __future__ import annotations

import functools
import threading
import time
from typing import Any, Callable


class TTLCache:
    def __init__(self, ttl_seconds: float):
        self.ttl_seconds = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.monotonic() >= expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (time.monotonic() + self.ttl_seconds, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


def cached(ttl_seconds: float = 60) -> Callable:
    """Decorator that memoizes a function's return value for ``ttl_seconds``.

    Keyed on the function's arguments, so different (team, season, player)
    combinations are cached independently. Call ``func.cache.clear()`` to
    force a refresh (e.g. from a manual "refresh now" control).
    """

    def decorator(func: Callable) -> Callable:
        cache = TTLCache(ttl_seconds)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = repr((args, tuple(sorted(kwargs.items()))))
            hit = cache.get(key)
            if hit is not None:
                return hit
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result

        wrapper.cache = cache
        return wrapper

    return decorator
