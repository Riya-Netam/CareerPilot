"""Simple in-memory sliding-window rate limiter.

Good enough for a single server process. With several instances (or restarts) limits are per
process; use Redis-backed limiting if you scale out. Documented in docs/SECURITY.md.
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.core.config import get_settings

_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def client_ip(request: Request) -> str:
    if get_settings().TRUST_PROXY:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def reset_rate_limits() -> None:
    with _lock:
        _hits.clear()


def rate_limit(name: str, limit: int, window_seconds: int):
    def dep(request: Request) -> None:
        if not get_settings().RATE_LIMIT_ENABLED:
            return
        key = f"{name}:{client_ip(request)}"
        now = time.monotonic()
        with _lock:
            q = _hits[key]
            while q and now - q[0] > window_seconds:
                q.popleft()
            if len(q) >= limit:
                retry = int(window_seconds - (now - q[0])) + 1
                raise HTTPException(429, detail={"code": "rate_limited", "message": "Too many attempts. Please wait and try again."},
                                    headers={"Retry-After": str(retry)})
            q.append(now)
    return dep
