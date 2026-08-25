import time

from macroservice.caching import TTLCache, cached


def test_ttl_cache_returns_none_before_any_set():
    cache = TTLCache(ttl_seconds=60)
    assert cache.get("missing") is None


def test_ttl_cache_returns_value_before_expiry():
    cache = TTLCache(ttl_seconds=60)
    cache.set("key", "value")
    assert cache.get("key") == "value"


def test_ttl_cache_expires_after_ttl():
    cache = TTLCache(ttl_seconds=0.01)
    cache.set("key", "value")
    time.sleep(0.02)
    assert cache.get("key") is None


def test_ttl_cache_clear_removes_all_entries():
    cache = TTLCache(ttl_seconds=60)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.clear()
    assert cache.get("a") is None
    assert cache.get("b") is None


def test_cached_decorator_memoizes_by_args():
    calls = []

    @cached(ttl_seconds=60)
    def add(a, b):
        calls.append((a, b))
        return a + b

    assert add(1, 2) == 3
    assert add(1, 2) == 3
    assert len(calls) == 1

    assert add(2, 3) == 5
    assert len(calls) == 2


def test_cached_decorator_exposes_cache_for_manual_clear():
    @cached(ttl_seconds=60)
    def identity(x):
        return x

    identity(1)
    assert identity.cache.get(repr(((1,), ()))) == 1
    identity.cache.clear()
    assert identity.cache.get(repr(((1,), ()))) is None
