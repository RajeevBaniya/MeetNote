import asyncio
import time
from collections import deque
from typing import Deque, Dict


class WsMessageRateLimiter:
    def __init__(self, max_messages: int, window_seconds: float) -> None:
        self._max_messages = max(1, int(max_messages))
        self._window_seconds = max(0.1, float(window_seconds))
        self._lock = asyncio.Lock()
        # Sliding window: list of timestamps (monotonic seconds) per key.
        self._timestamps: Dict[str, Deque[float]] = {}

    def _make_key(self, user_id: object | None, client_ip: str | None) -> str:
        if user_id is not None:
            return f"user:{user_id}"
        return f"ip:{client_ip or 'unknown'}"

    async def allow(self, user_id: object | None, client_ip: str | None) -> bool:
        key = self._make_key(user_id, client_ip)
        now = time.monotonic()
        cutoff = now - self._window_seconds

        async with self._lock:
            dq = self._timestamps.get(key)
            if dq is None:
                dq = deque()
                self._timestamps[key] = dq

            while dq and dq[0] < cutoff:
                dq.popleft()

            if len(dq) >= self._max_messages:
                return False

            dq.append(now)
            return True


_ws_message_limiter = WsMessageRateLimiter(max_messages=5, window_seconds=1.0)


async def allow_ws_message(user_id: object | None, client_ip: str | None) -> bool:
    return await _ws_message_limiter.allow(user_id, client_ip)

