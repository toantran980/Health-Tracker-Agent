"""Sliding-window rate limiters for proxied external API endpoints.

Backends:
  - "memory" (default): per-process state, thread-safe, no extra dependency.
    Fine for a single process.
  - "redis": shared, atomic counters across workers/processes. Requires the
    `redis` package and a reachable REDIS_URL
    (config.RATE_LIMIT_BACKEND="redis", config.REDIS_URL).

The active backend is selected by `build_limiter()` when the module loads;
`default_limiter` is the configured instance used by the external blueprint.
"""

import time
import threading
from collections import defaultdict, deque
from typing import Deque


class RateLimiter:
    """Sliding-window counter with a lock (in-process backend)."""

    def __init__(self, max_requests: int, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._hits: dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, client_id: str) -> bool:
        """Return True if the call is allowed, False if rate-limited."""
        now = time.monotonic()
        with self._lock:
            timestamps = self._hits[client_id]
            cutoff = now - self.window_seconds
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) >= self.max_requests:
                return False

            timestamps.append(now)
            return True

    def reset(self, client_id: str | None = None) -> None:
        """Clear recorded hits (optionally for a single client)."""
        with self._lock:
            if client_id is None:
                self._hits.clear()
            else:
                self._hits.pop(client_id, None)


class RedisRateLimiter:
    """Sliding-window counter backed by Redis (shared across processes).

    Uses a sorted set of hit timestamps per client; old hits are pruned on
    each call. Timestamps use `time.time()` (Unix seconds).
    """

    def __init__(self, max_requests: int, window_seconds: float = 60.0,
                 redis_client=None, prefix: str = "ratelimit"):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.prefix = prefix
        if redis_client is None:
            import redis  # imported lazily so "redis" is not required by default
            redis_client = redis.Redis.from_url("redis://localhost:6379/0")
        self._redis = redis_client

    def _key(self, client_id: str) -> str:
        return f"{self.prefix}:{client_id}"

    def allow(self, client_id: str) -> bool:
        """Atomically record a hit and enforce the window."""
        key = self._key(client_id)
        now = time.time()
        cutoff = now - self.window_seconds
        pipe = self._redis.pipeline(transaction=True)
        pipe.zremrangebyscore(key, "-inf", cutoff)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, int(self.window_seconds) + 1)
        results = pipe.execute()
        count = results[2]
        if count > self.max_requests:
            return False
        return True


def build_limiter(max_requests: int, window_seconds: float, backend: str,
                  redis_url: str):
    """Construct the limiter matching the configured backend."""
    backend = (backend or "memory").strip().lower()
    if backend == "memory":
        return RateLimiter(max_requests, window_seconds)
    if backend == "redis":
        try:
            import redis  # imported lazily so the default install needs nothing extra
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise RuntimeError(
                "RATE_LIMIT_BACKEND=redis requires the 'redis' package. "
                "Install it (e.g. pip install redis) or use the default 'memory' backend."
            ) from exc
        client = redis.Redis.from_url(redis_url)
        return RedisRateLimiter(max_requests, window_seconds, redis_client=client)
    raise ValueError(
        f"Unknown RATE_LIMIT_BACKEND: {backend!r} (expected 'memory' or 'redis')"
    )


# Default external-API limiter, configured from environment.
def _build_default():
    import config
    return build_limiter(
        max_requests=config.EXTERNAL_API_RATE_LIMIT,
        window_seconds=config.EXTERNAL_API_RATE_WINDOW_SECONDS,
        backend=config.RATE_LIMIT_BACKEND,
        redis_url=config.REDIS_URL,
    )


default_limiter = _build_default()