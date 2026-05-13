from datetime import datetime, timezone
from unittest.mock import MagicMock, call

import pytest

import conversation


@pytest.fixture
def db():
    return MagicMock()


class TestCreateConversation:
    def test_returns_uuid_string(self, db):
        conv_id = conversation.create_conversation(db, "uid-1", "OBR", "What is the infield fly rule?")
        assert isinstance(conv_id, str)
        assert len(conv_id) == 36

    def test_writes_to_users_conversations_subcollection(self, db):
        conversation.create_conversation(db, "uid-1", "OBR", "What is the infield fly rule?")
        db.collection.assert_called_with("users")
        db.collection().document.assert_called_with("uid-1")
        db.collection().document().collection.assert_called_with("conversations")

    def test_written_data_contains_required_fields(self, db):
        conversation.create_conversation(db, "uid-1", "OBR", "What is the infield fly rule?")
        set_call = db.collection().document().collection().document().set
        set_call.assert_called_once()
        data = set_call.call_args[0][0]
        assert data["governing_body"] == "OBR"
        assert data["preview"] == "What is the infield fly rule?"
        assert "created_at" in data

    def test_none_governing_body_stored_as_none(self, db):
        conversation.create_conversation(db, "uid-1", None, "Any question")
        data = db.collection().document().collection().document().set.call_args[0][0]
        assert data["governing_body"] is None

    def test_preview_truncated_to_100_chars(self, db):
        long_question = "x" * 200
        conversation.create_conversation(db, "uid-1", None, long_question)
        data = db.collection().document().collection().document().set.call_args[0][0]
        assert len(data["preview"]) <= 100


class TestAppendMessage:
    def test_user_message_written_to_messages_subcollection(self, db):
        conversation.append_message(db, "uid-1", "conv-1", "user", "What is a balk?")
        db.collection().document().collection().document().collection.assert_called_with("messages")
        db.collection().document().collection().document().collection().add.assert_called_once()

    def test_user_message_has_no_sources_field(self, db):
        conversation.append_message(db, "uid-1", "conv-1", "user", "What is a balk?")
        data = db.collection().document().collection().document().collection().add.call_args[0][0]
        assert "sources" not in data

    def test_assistant_message_includes_sources(self, db):
        sources = [{"rule_number": "6.02", "governing_body": "OBR"}]
        conversation.append_message(db, "uid-1", "conv-1", "assistant", "A balk is...", sources=sources)
        data = db.collection().document().collection().document().collection().add.call_args[0][0]
        assert data["sources"] == sources

    def test_message_data_has_required_fields(self, db):
        conversation.append_message(db, "uid-1", "conv-1", "user", "What is a balk?")
        data = db.collection().document().collection().document().collection().add.call_args[0][0]
        assert data["role"] == "user"
        assert data["content"] == "What is a balk?"
        assert "created_at" in data


class TestListConversations:
    def test_returns_list_with_id_field(self, db):
        mock_doc = MagicMock()
        mock_doc.id = "conv-abc"
        mock_doc.to_dict.return_value = {
            "created_at": datetime(2026, 5, 13, tzinfo=timezone.utc),
            "governing_body": "OBR",
            "preview": "What is the infield fly rule?",
        }
        db.collection().document().collection().order_by().limit().stream.return_value = [mock_doc]
        result = conversation.list_conversations(db, "uid-1")
        assert len(result) == 1
        assert result[0]["id"] == "conv-abc"

    def test_returns_all_fields_from_firestore(self, db):
        mock_doc = MagicMock()
        mock_doc.id = "conv-abc"
        mock_doc.to_dict.return_value = {
            "created_at": datetime(2026, 5, 13, tzinfo=timezone.utc),
            "governing_body": "DYB",
            "preview": "Is there a balk rule?",
        }
        db.collection().document().collection().order_by().limit().stream.return_value = [mock_doc]
        result = conversation.list_conversations(db, "uid-1")
        assert result[0]["governing_body"] == "DYB"
        assert result[0]["preview"] == "Is there a balk rule?"

    def test_empty_returns_empty_list(self, db):
        db.collection().document().collection().order_by().limit().stream.return_value = []
        result = conversation.list_conversations(db, "uid-1")
        assert result == []


class TestGetMessages:
    def test_returns_messages_with_id_field(self, db):
        mock_msg = MagicMock()
        mock_msg.id = "msg-1"
        mock_msg.to_dict.return_value = {
            "role": "user",
            "content": "What is a balk?",
            "created_at": datetime(2026, 5, 13, tzinfo=timezone.utc),
        }
        db.collection().document().collection().document().collection().order_by().stream.return_value = [mock_msg]
        result = conversation.get_messages(db, "uid-1", "conv-1")
        assert len(result) == 1
        assert result[0]["id"] == "msg-1"

    def test_returns_role_and_content(self, db):
        mock_msg = MagicMock()
        mock_msg.id = "msg-1"
        mock_msg.to_dict.return_value = {
            "role": "assistant",
            "content": "A balk is...",
            "created_at": datetime(2026, 5, 13, tzinfo=timezone.utc),
            "sources": [],
        }
        db.collection().document().collection().document().collection().order_by().stream.return_value = [mock_msg]
        result = conversation.get_messages(db, "uid-1", "conv-1")
        assert result[0]["role"] == "assistant"
        assert result[0]["content"] == "A balk is..."

    def test_empty_conversation_returns_empty_list(self, db):
        db.collection().document().collection().document().collection().order_by().stream.return_value = []
        result = conversation.get_messages(db, "uid-1", "conv-1")
        assert result == []
