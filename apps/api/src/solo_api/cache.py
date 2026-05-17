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


CURRENT_WEATHER_TTL_SECONDS = 60 * 60
AIR_QUALITY_TTL_SECONDS = 60 * 60 * 3
CLIMATE_TTL_SECONDS = 60 * 60 * 24 * 30
ATTRACTIONS_TTL_SECONDS = 60 * 60 * 24 * 30
HOTEL_PRICING_TTL_SECONDS = 60 * 60 * 24 * 7
CITY_CANDIDATE_TTL_SECONDS = 60 * 60 * 12


class RedisJsonCache:
    def __init__(self, redis_url: str | None):
        self.redis_url = redis_url

    def _client(self):
        if not self.redis_url:
            return None
        try:
            import redis
        except ImportError:
            return None
        return redis.Redis.from_url(self.redis_url, decode_responses=True)

    def get(self, key: str) -> str | None:
        client = self._client()
        if client is None:
            return None
        return client.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        client = self._client()
        if client is None:
            return
        client.setex(key, ttl_seconds, value)
