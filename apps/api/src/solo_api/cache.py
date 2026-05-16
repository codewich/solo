import time
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    expires_at: float
    value: T


class TtlCache(Generic[T]):
    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds
        self._values: dict[str, CacheEntry[T]] = {}

    def get(self, key: str) -> T | None:
        entry = self._values.get(key)
        if entry is None:
            return None
        if entry.expires_at <= time.monotonic():
            self._values.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: T) -> None:
        self._values[key] = CacheEntry(
            expires_at=time.monotonic() + self.ttl_seconds,
            value=value,
        )
