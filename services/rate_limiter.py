"""Sliding window rate limiter — in-memory, per session key."""
import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int = 20, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._windows: dict[str, deque] = defaultdict(deque)

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        dq = self._windows[key]
        while dq and dq[0] < now - self.window:
            dq.popleft()
        if len(dq) >= self.max_requests:
            return False
        dq.append(now)
        return True

    def remaining(self, key: str) -> int:
        now = time.monotonic()
        dq = self._windows[key]
        while dq and dq[0] < now - self.window:
            dq.popleft()
        return max(0, self.max_requests - len(dq))


rate_limiter = SlidingWindowRateLimiter()
