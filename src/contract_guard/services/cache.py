"""Fingerprint-based review result caching."""

from __future__ import annotations

import hashlib
import inspect
import json
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from threading import RLock
from typing import Any, Protocol


def review_cache_key(
    *,
    org_id: str,
    session_id: str,
    fingerprint: str,
    variant: str = "default",
) -> str:
    """Build a tenant-safe cache key centered on the document fingerprint."""

    scope = hashlib.sha256(f"{org_id}\0{session_id}".encode()).hexdigest()[:24]
    option = hashlib.sha256(variant.encode("utf-8")).hexdigest()[:16]
    return f"contractguard:review:{scope}:{fingerprint}:{option}"


class ReviewCache(Protocol):
    """Async cache boundary used by the API orchestration layer."""

    async def get(
        self,
        *,
        org_id: str,
        session_id: str,
        fingerprint: str,
        variant: str = "default",
    ) -> Mapping[str, Any] | None: ...

    async def set(
        self,
        value: Mapping[str, Any],
        *,
        org_id: str,
        session_id: str,
        fingerprint: str,
        variant: str = "default",
        ttl_seconds: int | None = None,
    ) -> None: ...

    async def delete(
        self,
        *,
        org_id: str,
        session_id: str,
        fingerprint: str,
        variant: str = "default",
    ) -> None: ...


@dataclass(slots=True)
class _CacheEntry:
    value: dict[str, Any]
    expires_at: float | None


def _copy_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    """Detach cached JSON-compatible data from mutable caller state."""

    return json.loads(json.dumps(dict(value), ensure_ascii=False))


class InMemoryReviewCache:
    """Thread-safe local cache suitable for a single-process deployment."""

    def __init__(
        self,
        *,
        default_ttl_seconds: int = 3600,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if default_ttl_seconds <= 0:
            raise ValueError("default_ttl_seconds must be greater than zero")
        self.default_ttl_seconds = default_ttl_seconds
        self._clock = clock
        self._entries: dict[str, _CacheEntry] = {}
        self._lock = RLock()

    async def get(
        self,
        *,
        org_id: str,
        session_id: str,
        fingerprint: str,
        variant: str = "default",
    ) -> Mapping[str, Any] | None:
        key = review_cache_key(
            org_id=org_id,
            session_id=session_id,
            fingerprint=fingerprint,
            variant=variant,
        )
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at is not None and entry.expires_at <= self._clock():
                self._entries.pop(key, None)
                return None
            return _copy_mapping(entry.value)

    async def set(
        self,
        value: Mapping[str, Any],
        *,
        org_id: str,
        session_id: str,
        fingerprint: str,
        variant: str = "default",
        ttl_seconds: int | None = None,
    ) -> None:
        ttl = self.default_ttl_seconds if ttl_seconds is None else ttl_seconds
        if ttl <= 0:
            raise ValueError("ttl_seconds must be greater than zero")
        key = review_cache_key(
            org_id=org_id,
            session_id=session_id,
            fingerprint=fingerprint,
            variant=variant,
        )
        entry = _CacheEntry(value=_copy_mapping(value), expires_at=self._clock() + ttl)
        with self._lock:
            self._entries[key] = entry

    async def delete(
        self,
        *,
        org_id: str,
        session_id: str,
        fingerprint: str,
        variant: str = "default",
    ) -> None:
        key = review_cache_key(
            org_id=org_id,
            session_id=session_id,
            fingerprint=fingerprint,
            variant=variant,
        )
        with self._lock:
            self._entries.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


class RedisClient(Protocol):
    """Minimal subset supported by redis-py and compatible clients."""

    def get(self, key: str) -> Any | Awaitable[Any]: ...

    def set(self, key: str, value: str, *, ex: int | None = None) -> Any | Awaitable[Any]: ...

    def delete(self, key: str) -> Any | Awaitable[Any]: ...


async def _resolve(value: Any | Awaitable[Any]) -> Any:
    return await value if inspect.isawaitable(value) else value


class RedisReviewCache:
    """Optional Redis adapter; the Redis client is supplied by the application."""

    def __init__(self, client: RedisClient, *, default_ttl_seconds: int = 3600) -> None:
        if default_ttl_seconds <= 0:
            raise ValueError("default_ttl_seconds must be greater than zero")
        self.client = client
        self.default_ttl_seconds = default_ttl_seconds

    async def get(
        self,
        *,
        org_id: str,
        session_id: str,
        fingerprint: str,
        variant: str = "default",
    ) -> Mapping[str, Any] | None:
        key = review_cache_key(
            org_id=org_id,
            session_id=session_id,
            fingerprint=fingerprint,
            variant=variant,
        )
        value = await _resolve(self.client.get(key))
        if value is None:
            return None
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        decoded = json.loads(value)
        if not isinstance(decoded, dict):
            return None
        return decoded

    async def set(
        self,
        value: Mapping[str, Any],
        *,
        org_id: str,
        session_id: str,
        fingerprint: str,
        variant: str = "default",
        ttl_seconds: int | None = None,
    ) -> None:
        ttl = self.default_ttl_seconds if ttl_seconds is None else ttl_seconds
        if ttl <= 0:
            raise ValueError("ttl_seconds must be greater than zero")
        key = review_cache_key(
            org_id=org_id,
            session_id=session_id,
            fingerprint=fingerprint,
            variant=variant,
        )
        encoded = json.dumps(dict(value), ensure_ascii=False, separators=(",", ":"))
        await _resolve(self.client.set(key, encoded, ex=ttl))

    async def delete(
        self,
        *,
        org_id: str,
        session_id: str,
        fingerprint: str,
        variant: str = "default",
    ) -> None:
        key = review_cache_key(
            org_id=org_id,
            session_id=session_id,
            fingerprint=fingerprint,
            variant=variant,
        )
        await _resolve(self.client.delete(key))


# Concise aliases for callers that do not need the implementation detail in the name.
MemoryCache = InMemoryReviewCache
RedisCacheAdapter = RedisReviewCache
