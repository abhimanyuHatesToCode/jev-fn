"""Small process-local TTL cache with a maximum number of entries."""

from collections import OrderedDict
from hashlib import sha256
import json
from threading import RLock
from time import monotonic

_MAX_ENTRIES = 1024
_cache: OrderedDict[str, tuple[float, float]] = OrderedDict()
_lock = RLock()


def make_key(model: str | None, query: str, context: str | None) -> str:
    raw = json.dumps(
        [model, query.strip(), context.strip() if context is not None else None],
        ensure_ascii=False,
    )
    return sha256(raw.encode("utf-8")).hexdigest()


def get_cached(key: str) -> float | None:
    now = monotonic()
    with _lock:
        item = _cache.get(key)
        if item is None:
            return None
        expires_at, value = item
        if expires_at <= now:
            del _cache[key]
            return None
        _cache.move_to_end(key)
        return value


def set_cached(key: str, value: float, ttl: int) -> None:
    with _lock:
        _cache[key] = (monotonic() + ttl, value)
        _cache.move_to_end(key)
        while len(_cache) > _MAX_ENTRIES:
            _cache.popitem(last=False)


def clear_cache() -> None:
    """Clear the process-local cache (mainly useful in tests)."""
    with _lock:
        _cache.clear()
