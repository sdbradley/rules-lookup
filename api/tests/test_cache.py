from unittest.mock import MagicMock, patch

import cache
from cache import get_cached, normalize_key, write_cache


class TestNormalizeKey:
    def test_lowercases_question(self):
        key = normalize_key("What Is A Balk?", None)
        assert key.startswith("what is a balk")

    def test_strips_punctuation(self):
        key = normalize_key("What is a balk?", None)
        assert "?" not in key

    def test_collapses_whitespace(self):
        key = normalize_key("what  is   a  balk", None)
        assert "  " not in key

    def test_includes_governing_body(self):
        key = normalize_key("What is a balk?", "OBR")
        assert key.endswith("|OBR")

    def test_none_governing_body_produces_empty_suffix(self):
        key = normalize_key("What is a balk?", None)
        assert key.endswith("|")

    def test_same_question_different_body_produces_different_keys(self):
        k1 = normalize_key("What is a balk?", "OBR")
        k2 = normalize_key("What is a balk?", "DYB")
        assert k1 != k2

    def test_same_question_case_insensitive(self):
        k1 = normalize_key("What is a balk?", "OBR")
        k2 = normalize_key("WHAT IS A BALK?", "OBR")
        assert k1 == k2

    def test_punctuation_variants_produce_same_key(self):
        k1 = normalize_key("What is a balk?", "OBR")
        k2 = normalize_key("What is a balk", "OBR")
        assert k1 == k2


class TestGetCached:
    def test_returns_none_on_miss(self):
        db = MagicMock()
        db.collection.return_value.document.return_value.get.return_value.exists = False
        result = get_cached(db, "some-key")
        assert result is None

    def test_returns_data_on_hit(self):
        db = MagicMock()
        snap = MagicMock()
        snap.exists = True
        snap.to_dict.return_value = {"answer": "A balk is...", "sources": []}
        db.collection.return_value.document.return_value.get.return_value = snap
        result = get_cached(db, "some-key")
        assert result["answer"] == "A balk is..."

    def test_queries_correct_collection_and_document(self):
        db = MagicMock()
        db.collection.return_value.document.return_value.get.return_value.exists = False
        get_cached(db, "my-cache-key")
        db.collection.assert_called_once_with("question_cache")
        db.collection.return_value.document.assert_called_once_with("my-cache-key")


class TestWriteCache:
    def test_writes_to_correct_collection_and_document(self):
        db = MagicMock()
        write_cache(db, "my-key", "What is a balk?", "OBR", "A balk is...", [])
        db.collection.assert_called_once_with("question_cache")
        db.collection.return_value.document.assert_called_once_with("my-key")
        db.collection.return_value.document.return_value.set.assert_called_once()

    def test_writes_correct_fields(self):
        db = MagicMock()
        sources = [{"rule_number": "6.02", "source_doc": "obr"}]
        write_cache(db, "key", "What is a balk?", "OBR", "A balk is...", sources)
        written = db.collection.return_value.document.return_value.set.call_args[0][0]
        assert written["question"] == "What is a balk?"
        assert written["governing_body"] == "OBR"
        assert written["answer"] == "A balk is..."
        assert written["sources"] == sources
        assert written["hit_count"] == 0
        assert "created_at" in written
        assert "last_hit_at" in written

    def test_handles_none_governing_body(self):
        db = MagicMock()
        write_cache(db, "key", "What is a balk?", None, "A balk is...", [])
        written = db.collection.return_value.document.return_value.set.call_args[0][0]
        assert written["governing_body"] is None
