import pytest
from unittest.mock import MagicMock, patch

import webhook


def _mock_db():
    db = MagicMock()
    doc_ref = MagicMock()
    db.collection.return_value.document.return_value = doc_ref
    return db, doc_ref


def test_verify_webhook_secret_no_secret_configured():
    with patch.dict("os.environ", {}, clear=False):
        import os
        os.environ.pop("REVENUECAT_WEBHOOK_SECRET", None)
        assert webhook.verify_webhook_secret("anything") is True


def test_verify_webhook_secret_matches():
    with patch.dict("os.environ", {"REVENUECAT_WEBHOOK_SECRET": "mysecret"}):
        assert webhook.verify_webhook_secret("mysecret") is True


def test_verify_webhook_secret_wrong():
    with patch.dict("os.environ", {"REVENUECAT_WEBHOOK_SECRET": "mysecret"}):
        assert webhook.verify_webhook_secret("wrong") is False


def test_handle_event_initial_purchase():
    db, doc_ref = _mock_db()
    webhook.handle_event(db, {"type": "INITIAL_PURCHASE", "app_user_id": "uid-1"})
    doc_ref.set.assert_called_once()
    args = doc_ref.set.call_args[0][0]
    assert args["is_subscriber"] is True


def test_handle_event_cancellation():
    db, doc_ref = _mock_db()
    webhook.handle_event(db, {"type": "CANCELLATION", "app_user_id": "uid-1"})
    doc_ref.set.assert_called_once()
    args = doc_ref.set.call_args[0][0]
    assert args["is_subscriber"] is False


def test_handle_event_unknown_type():
    db, doc_ref = _mock_db()
    webhook.handle_event(db, {"type": "UNKNOWN_EVENT", "app_user_id": "uid-1"})
    doc_ref.set.assert_not_called()


def test_handle_event_missing_uid():
    db, doc_ref = _mock_db()
    webhook.handle_event(db, {"type": "INITIAL_PURCHASE"})
    doc_ref.set.assert_not_called()
