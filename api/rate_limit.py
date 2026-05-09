import time
from collections import defaultdict

from fastapi import HTTPException

_WINDOW_SECONDS = 60
_MAX_REQUESTS = 60

_store: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(uid: str) -> None:
    now = time.time()
    cutoff = now - _WINDOW_SECONDS
    timestamps = _store[uid]
    _store[uid] = [t for t in timestamps if t > cutoff]
    if len(_store[uid]) >= _MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
    _store[uid].append(now)
