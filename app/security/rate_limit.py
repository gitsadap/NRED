from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional


@dataclass(frozen=True)
class RateLimitStatus:
    blocked: bool
    retry_after_seconds: Optional[int] = None


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter suitable for single-instance deployments.
    For multi-worker/multi-instance production, prefer a shared store (e.g., Redis).
    """

    def __init__(self, max_attempts: int, window_seconds: int, block_seconds: int):
        self._max_attempts = max(1, int(max_attempts))
        self._window_seconds = max(1, int(window_seconds))
        self._block_seconds = max(1, int(block_seconds))

        self._attempts: Dict[str, Deque[float]] = {}
        self._blocked_until: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def check_blocked(self, key: str) -> RateLimitStatus:
        now = time.monotonic()
        async with self._lock:
            blocked_until = self._blocked_until.get(key)
            if not blocked_until:
                return RateLimitStatus(blocked=False)
            if blocked_until <= now:
                self._blocked_until.pop(key, None)
                return RateLimitStatus(blocked=False)
            retry_after = int(blocked_until - now) + 1
            return RateLimitStatus(blocked=True, retry_after_seconds=retry_after)

    async def register_failure(self, key: str) -> RateLimitStatus:
        now = time.monotonic()
        async with self._lock:
            attempts = self._attempts.setdefault(key, deque())
            while attempts and (now - attempts[0]) > self._window_seconds:
                attempts.popleft()
            attempts.append(now)

            if len(attempts) >= self._max_attempts:
                self._blocked_until[key] = now + self._block_seconds
                self._attempts.pop(key, None)
                return RateLimitStatus(blocked=True, retry_after_seconds=self._block_seconds)

            return RateLimitStatus(blocked=False)

    async def reset(self, key: str) -> None:
        async with self._lock:
            self._attempts.pop(key, None)
            self._blocked_until.pop(key, None)

