import pytest
from unittest.mock import MagicMock

import usage


FREE_TIER_LIMIT = usage.FREE_TIER_LIMIT


def _mock_db(count: int | None):
    db = MagicMock()
    doc_ref = MagicMock()
    db.collection.return_value.document.return_value = doc_ref
    snap = MagicMock()
    snap.exists = count is not None
    snap.to_dict.return_value = {"count": count} if count is not None else {}
    doc_ref.get.return_value = snap
    return db, doc_ref


def test_get_monthly_count_no_doc():
    db, _ = _mock_db(None)
    assert usage.get_monthly_count(db, "uid-1") == 0


def test_get_monthly_count_existing():
    db, _ = _mock_db(7)
    assert usage.get_monthly_count(db, "uid-1") == 7


def test_increment_count_creates_doc():
    db, doc_ref = _mock_db(None)
    usage.increment_count(db, "uid-1")
    doc_ref.set.assert_called_once()
    call_args = doc_ref.set.call_args[0][0]
    assert call_args["count"] == 1


def test_increment_count_increments_existing():
    db, doc_ref = _mock_db(5)
    usage.increment_count(db, "uid-1")
    doc_ref.set.assert_called_once()
    call_args = doc_ref.set.call_args[0][0]
    assert call_args["count"] == 6


def test_is_over_limit_false():
    assert usage.is_over_limit(FREE_TIER_LIMIT - 1) is False


def test_is_over_limit_at_limit():
    assert usage.is_over_limit(FREE_TIER_LIMIT) is True


def test_is_over_limit_above_limit():
    assert usage.is_over_limit(FREE_TIER_LIMIT + 5) is True
