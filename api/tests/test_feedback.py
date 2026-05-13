from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

import feedback


@pytest.fixture
def db():
    return MagicMock()


def _make_doc(uid="uid-1", has_feedback=False):
    doc = MagicMock()
    doc.exists = True
    data = {"uid": uid, "question": "What is a balk?", "answer": "A balk is..."}
    if has_feedback:
        data["feedback"] = {"rating": "up"}
    doc.to_dict.return_value = data
    return doc


class TestWriteFeedback:
    def test_writes_rating_to_log_document(self, db):
        db.collection().document().get.return_value = _make_doc()
        feedback.write_feedback(db, "uid-1", "log-abc", "up")
        db.collection().document().update.assert_called_once()
        written = db.collection().document().update.call_args[0][0]
        assert written["feedback"]["rating"] == "up"

    def test_writes_created_at_timestamp(self, db):
        db.collection().document().get.return_value = _make_doc()
        feedback.write_feedback(db, "uid-1", "log-abc", "down")
        written = db.collection().document().update.call_args[0][0]
        assert "created_at" in written["feedback"]

    def test_raises_if_log_not_found(self, db):
        missing = MagicMock()
        missing.exists = False
        db.collection().document().get.return_value = missing
        with pytest.raises(ValueError, match="not found"):
            feedback.write_feedback(db, "uid-1", "log-abc", "up")

    def test_raises_if_uid_does_not_match(self, db):
        db.collection().document().get.return_value = _make_doc(uid="uid-other")
        with pytest.raises(PermissionError):
            feedback.write_feedback(db, "uid-1", "log-abc", "up")

    def test_queries_query_logs_collection(self, db):
        db.collection().document().get.return_value = _make_doc()
        feedback.write_feedback(db, "uid-1", "log-abc", "up")
        db.collection.assert_called_with("query_logs")
        db.collection().document.assert_called_with("log-abc")

    def test_accepts_down_rating(self, db):
        db.collection().document().get.return_value = _make_doc()
        feedback.write_feedback(db, "uid-1", "log-abc", "down")
        written = db.collection().document().update.call_args[0][0]
        assert written["feedback"]["rating"] == "down"
