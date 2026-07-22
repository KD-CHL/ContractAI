"""Small in-process sliding-window limiter for local authentication endpoints."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import RLock


class SlidingWindowRateLimiter:
    def __init__(self, *, limit: int = 10, window_seconds: int = 300) -> None:
        if limit <= 0 or window_seconds <= 0:
            raise ValueError("rate limit settings must be positive")
        self.limit = limit
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = RLock()

    def retry_after(self, key: str) -> int:
        now = time.monotonic()
        with self._lock:
            attempts = self._attempts[key]
            self._prune(attempts, now)
            if len(attempts) < self.limit:
                if not attempts:
                    self._attempts.pop(key, None)
                return 0
            return max(1, int(self.window_seconds - (now - attempts[0])))

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            attempts = self._attempts[key]
            self._prune(attempts, now)
            attempts.append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)

    def _prune(self, attempts: deque[float], now: float) -> None:
        cutoff = now - self.window_seconds
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()


__all__ = ["SlidingWindowRateLimiter"]
