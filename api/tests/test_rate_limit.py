import pytest
from fastapi import HTTPException

import rate_limit


def setup_function():
    rate_limit._store.clear()


def test_allows_requests_under_limit():
    for _ in range(rate_limit._MAX_REQUESTS - 1):
        rate_limit.check_rate_limit("uid-1")


def test_blocks_at_limit():
    for _ in range(rate_limit._MAX_REQUESTS):
        rate_limit.check_rate_limit("uid-1")
    with pytest.raises(HTTPException) as exc_info:
        rate_limit.check_rate_limit("uid-1")
    assert exc_info.value.status_code == 429


def test_different_users_are_independent():
    for _ in range(rate_limit._MAX_REQUESTS):
        rate_limit.check_rate_limit("uid-1")
    rate_limit.check_rate_limit("uid-2")


def test_old_requests_expire():
    import time
    now = time.time()
    uid = "uid-expiry"
    rate_limit._store[uid] = [now - rate_limit._WINDOW_SECONDS - 1] * rate_limit._MAX_REQUESTS
    rate_limit.check_rate_limit(uid)
