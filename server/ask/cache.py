"""Bounded per-process Ask cache with one loader for concurrent identical keys."""

from __future__ import annotations

import copy
import weakref
from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar

from server.utils.ttl_cache import TTLCache

T = TypeVar("T")
_CACHES: weakref.WeakSet[AskCache] = weakref.WeakSet()


@dataclass(frozen=True)
class CacheValue(Generic[T]):
    value: T
    ttl_seconds: float


@dataclass(frozen=True)
class CacheResult(Generic[T]):
    value: T
    hit: bool


class AskCache:
    def __init__(self, max_entries: int = 256, version: str = "1"):
        self.version = version
        self._cache: TTLCache[tuple[str, str, Any], CacheValue] = TTLCache(
            max_entries, copy=copy.deepcopy,
        )
        _CACHES.add(self)

    def get_or_load(self, namespace: str, key: Any, loader: Callable[[], CacheValue[T]],
                    *, wait_timeout: float | None = None) -> CacheResult[T]:
        ran_loader = False

        def load() -> CacheValue[T]:
            nonlocal ran_loader
            ran_loader = True
            value = loader()
            if not isinstance(value, CacheValue):
                raise TypeError("Ask cache loader must return CacheValue")
            return value

        result = self._cache.get_or_load(
            (self.version, namespace, key), load, lambda value: value.ttl_seconds,
            wait_timeout=wait_timeout,
        )
        return CacheResult(result.value, hit=not ran_loader)

    def clear(self) -> None:
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)


def invalidate_ask_caches() -> None:
    for cache in tuple(_CACHES):
        cache.clear()
