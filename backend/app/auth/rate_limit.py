"""Small in-memory limiter for failed logins.

Failures are counted per (client address, email) for a sliding window. Once the
limit is reached, further login attempts get 429 until the window passes. A
successful login clears the count.

This lives in process memory, so each server worker keeps its own counts and a
restart resets them. That is enough to slow down password guessing on a single
instance; if you run several workers or servers, move the counts to Redis.
"""

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, status

MAX_FAILURES = 5
WINDOW_SECONDS = 15 * 60

_failures: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()


def _key(client_host: str | None, email: str) -> str:
    return f"{client_host or 'unknown'}|{email.strip().lower()}"


def _prune(attempts: deque[float], now: float) -> None:
    while attempts and now - attempts[0] > WINDOW_SECONDS:
        attempts.popleft()


def ensure_not_locked(client_host: str | None, email: str) -> None:
    key = _key(client_host, email)
    now = time.monotonic()
    with _lock:
        attempts = _failures.get(key)
        if attempts is None:
            return
        _prune(attempts, now)
        if not attempts:
            del _failures[key]
            return
        if len(attempts) >= MAX_FAILURES:
            retry_after = int(WINDOW_SECONDS - (now - attempts[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Try again later.",
                headers={"Retry-After": str(retry_after)},
            )


def record_failure(client_host: str | None, email: str) -> None:
    key = _key(client_host, email)
    now = time.monotonic()
    with _lock:
        attempts = _failures[key]
        _prune(attempts, now)
        attempts.append(now)


def clear_failures(client_host: str | None, email: str) -> None:
    with _lock:
        _failures.pop(_key(client_host, email), None)


def reset_all() -> None:
    """Forget every count. Used by tests."""
    with _lock:
        _failures.clear()
