from collections import defaultdict
from datetime import UTC, datetime, timedelta
from threading import Lock

from fastapi import HTTPException, status


class InMemoryRateLimiter:
    """
    Thread-safe sliding-window in-memory rate limiter.

    Suitable for single-process deployments. For multi-process/multi-instance
    setups, replace with a Redis-backed implementation (e.g. slowapi + Redis).
    """

    def __init__(self) -> None:
        self._store: dict[str, list[datetime]] = defaultdict(list)
        self._lock = Lock()

    def check(self, key: str, max_requests: int, window_seconds: int) -> None:
        """
        Raise HTTP 429 if ``key`` has exceeded ``max_requests`` within the
        last ``window_seconds`` seconds, then record the current attempt.
        """
        now = datetime.now(UTC)
        window_start = now - timedelta(seconds=window_seconds)

        with self._lock:
            # Prune attempts outside the sliding window
            self._store[key] = [t for t in self._store[key] if t > window_start]

            if len(self._store[key]) >= max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                    headers={"Retry-After": str(window_seconds)},
                )

            self._store[key].append(now)

    def reset(self, key: str) -> None:
        """Remove all recorded attempts for a key (useful in tests)."""
        with self._lock:
            self._store.pop(key, None)


rate_limiter = InMemoryRateLimiter()
