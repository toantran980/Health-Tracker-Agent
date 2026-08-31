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
        self.lock = threading.Lock()
        self.hits: dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, client_id: str) -> bool:
        """Return True if the call is allowed, False if rate-limited."""
        now = time.monotonic()
        with self.lock:
            timestamps = self.hits[client_id]
            cutoff = now - self.window_seconds
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) >= self.max_requests:
                return False

            timestamps.append(now)
            return True

    def status(self, client_id: str) -> dict:
        """Return {remaining, reset, limit, window} for a client (after pruning).

        `reset` is seconds until the current window fully resets (relative, so
        it works for both monotonic and wall-clock backends).
        """
        now = time.monotonic()
        with self.lock:
            timestamps = self.hits.get(client_id)
            cutoff = now - self.window_seconds
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if not timestamps:
                count = 0
                reset = self.window_seconds
            else:
                count = len(timestamps)
                reset = (timestamps[-1] + self.window_seconds) - now
        return {
            "limit": self.max_requests,
            "remaining": max(0, self.max_requests - count),
            "reset": max(0.0, reset),
            "window": self.window_seconds,
        }

    def reset(self, client_id: str | None = None) -> None:
        """Clear recorded hits (optionally for a single client)."""
        with self.lock:
            if client_id is None:
                self.hits.clear()
            else:
                self.hits.pop(client_id, None)


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
        self.redis = redis_client

    def key(self, client_id: str) -> str:
        return f"{self.prefix}:{client_id}"

    def allow(self, client_id: str) -> bool:
        """Atomically record a hit and enforce the window."""
        key = self.key(client_id)
        now = time.time()
        cutoff = now - self.window_seconds
        pipe = self.redis.pipeline(transaction=True)
        pipe.zremrangebyscore(key, "-inf", cutoff)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, int(self.window_seconds) + 1)
        results = pipe.execute()
        count = results[2]
        if count > self.max_requests:
            return False
        return True

    def status(self, client_id: str) -> dict:
        """Return {remaining, reset, limit, window} for a client.

        `reset` is seconds until the current window fully resets (relative).
        """
        key = self.key(client_id)
        now = time.time()
        cutoff = now - self.window_seconds
        pipe = self.redis.pipeline(transaction=True)
        pipe.zremrangebyscore(key, "-inf", cutoff)
        pipe.zcard(key)
        pipe.zrange(key, 0, -1, withscores=True)
        _, count, members = pipe.execute()
        if members and members[-1] is not None:
            latest = members[-1][1]
            reset = (latest + self.window_seconds) - now
        else:
            reset = self.window_seconds
        return {
            "limit": self.max_requests,
            "remaining": max(0, self.max_requests - count),
            "reset": max(0.0, reset),
            "window": self.window_seconds,
        }


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
def build_default():
    import config
    return build_limiter(
        max_requests=config.EXTERNAL_API_RATE_LIMIT,
        window_seconds=config.EXTERNAL_API_RATE_WINDOW_SECONDS,
        backend=config.RATE_LIMIT_BACKEND,
        redis_url=config.REDIS_URL,
    )


default_limiter = build_default()