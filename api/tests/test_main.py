import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

# Patch Firebase init before importing app
with patch("firebase_admin.initialize_app"), patch("firebase_admin.credentials.Certificate"):
    from main import app

from models import QueryResponse, Source

client = TestClient(app, raise_server_exceptions=False)

FAKE_CONV_ID = "conv-test-uuid"


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("main.verify_token", return_value="uid-abc")
@patch("main.is_subscriber", return_value=False)
@patch("main.get_monthly_count", return_value=0)
@patch("main.increment_count")
@patch("main._write_history")
@patch("main.write_cache")
@patch("main.get_cached", return_value=None)
@patch("main.create_conversation", return_value=FAKE_CONV_ID)
@patch("main.handle_query")
def test_query_success(mock_handle, mock_create_conv, mock_get_cached, mock_write, mock_hist, mock_inc, mock_count, mock_sub, mock_verify):
    mock_handle.return_value = QueryResponse(
        answer="The infield fly rule applies when...",
        sources=[],
    )
    response = client.post(
        "/query",
        json={"question": "What is the infield fly rule?", "governing_body": "OBR"},
        headers={"Authorization": "Bearer valid-token"},
    )
    assert response.status_code == 200
    mock_verify.assert_called_once_with("Bearer valid-token")
    mock_inc.assert_called_once()
    assert response.json()["conversation_id"] == FAKE_CONV_ID


@patch("main.verify_token", side_effect=__import__("fastapi").HTTPException(status_code=401, detail="Invalid token"))
def test_query_unauthorized(mock_verify):
    response = client.post(
        "/query",
        json={"question": "What is the infield fly rule?"},
        headers={"Authorization": "Bearer bad-token"},
    )
    assert response.status_code == 401


@patch("main.verify_token", return_value="uid-abc")
@patch("main.is_subscriber", return_value=False)
@patch("main.get_monthly_count", return_value=20)
@patch("main.create_conversation", return_value=FAKE_CONV_ID)
def test_query_over_limit(mock_create_conv, mock_count, mock_sub, mock_verify):
    response = client.post(
        "/query",
        json={"question": "What is the infield fly rule?"},
        headers={"Authorization": "Bearer valid-token"},
    )
    assert response.status_code == 429


@patch("main.verify_token", return_value="uid-abc")
@patch("main.is_subscriber", return_value=False)
@patch("main.get_monthly_count", return_value=0)
@patch("main.increment_count")
@patch("main.get_cached", return_value=None)
@patch("main.create_conversation", return_value=FAKE_CONV_ID)
@patch("main.handle_query", side_effect=Exception("Pinecone unavailable"))
def test_query_internal_error(mock_handle, mock_create_conv, mock_get_cached, mock_inc, mock_count, mock_sub, mock_verify):
    response = client.post(
        "/query",
        json={"question": "What is the infield fly rule?"},
        headers={"Authorization": "Bearer valid-token"},
    )
    assert response.status_code == 500


@patch("main.verify_token", return_value="uid-abc")
@patch("main.is_subscriber", return_value=False)
@patch("main.get_monthly_count", return_value=0)
@patch("main.increment_count")
@patch("main._write_history")
@patch("main.get_cached", return_value={"answer": "Cached answer.", "sources": []})
@patch("main.create_conversation", return_value=FAKE_CONV_ID)
def test_query_returns_cached_answer(mock_create_conv, mock_cached, mock_hist, mock_inc, mock_count, mock_sub, mock_verify):
    response = client.post(
        "/query",
        json={"question": "What is the infield fly rule?", "governing_body": "OBR"},
        headers={"Authorization": "Bearer valid-token"},
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "Cached answer."
    assert response.json()["conversation_id"] == FAKE_CONV_ID


@patch("main.verify_token", return_value="uid-abc")
@patch("main.is_subscriber", return_value=False)
@patch("main.get_monthly_count", return_value=0)
@patch("main.increment_count")
@patch("main._write_history")
@patch("main.write_cache")
@patch("main.get_cached", return_value=None)
@patch("main.create_conversation", return_value=FAKE_CONV_ID)
@patch("main.handle_query")
def test_query_writes_to_cache_on_miss(mock_handle, mock_create_conv, mock_get_cached, mock_write, mock_hist, mock_inc, mock_count, mock_sub, mock_verify):
    mock_handle.return_value = QueryResponse(answer="Fresh answer.", sources=[])
    response = client.post(
        "/query",
        json={"question": "What is the infield fly rule?", "governing_body": "OBR"},
        headers={"Authorization": "Bearer valid-token"},
    )
    assert response.status_code == 200
    # write_cache is called in a background thread; give it a moment
    import time; time.sleep(0.05)
    mock_write.assert_called_once()
    args = mock_write.call_args[0]
    assert args[2] == "What is the infield fly rule?"
    assert args[4] == "Fresh answer."


@patch("main.verify_token", return_value="uid-abc")
@patch("main.is_subscriber", return_value=False)
@patch("main.get_monthly_count", return_value=0)
@patch("main.increment_count")
@patch("main._write_history")
@patch("main.handle_query")
@patch("main.get_cached", return_value=None)
@patch("main.create_conversation", return_value=FAKE_CONV_ID)
def test_query_does_not_call_handle_query_on_cache_hit(mock_create_conv, mock_get_cached, mock_handle, mock_hist, mock_inc, mock_count, mock_sub, mock_verify):
    mock_get_cached.return_value = {"answer": "Cached.", "sources": []}
    client.post(
        "/query",
        json={"question": "What is the infield fly rule?"},
        headers={"Authorization": "Bearer valid-token"},
    )
    mock_handle.assert_not_called()


@patch("main.verify_token", return_value="uid-abc")
@patch("main.is_subscriber", return_value=False)
@patch("main.get_monthly_count", return_value=0)
@patch("main.create_conversation", return_value=FAKE_CONV_ID)
@patch("main.list_conversations")
def test_get_conversations(mock_list_convs, mock_create_conv, mock_count, mock_sub, mock_verify):
    from datetime import datetime, timezone
    mock_list_convs.return_value = [
        {
            "id": "conv-1",
            "preview": "What is the infield fly rule?",
            "governing_body": "OBR",
            "created_at": datetime(2026, 5, 13, tzinfo=timezone.utc),
        }
    ]
    response = client.get(
        "/conversations",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "conv-1"
    assert data[0]["preview"] == "What is the infield fly rule?"


@patch("main.verify_token", return_value="uid-abc")
@patch("main.list_conversations")
@patch("main.get_messages")
def test_get_conversation_detail(mock_get_msgs, mock_list_convs, mock_verify):
    from datetime import datetime, timezone
    mock_list_convs.return_value = [
        {
            "id": "conv-1",
            "preview": "What is the infield fly rule?",
            "governing_body": "OBR",
            "created_at": datetime(2026, 5, 13, tzinfo=timezone.utc),
        }
    ]
    mock_get_msgs.return_value = [
        {"id": "msg-1", "role": "user", "content": "What is the infield fly rule?",
         "created_at": datetime(2026, 5, 13, tzinfo=timezone.utc)},
        {"id": "msg-2", "role": "assistant", "content": "The infield fly rule...",
         "created_at": datetime(2026, 5, 13, tzinfo=timezone.utc), "sources": []},
    ]
    response = client.get(
        "/conversations/conv-1",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "conv-1"
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"


@patch("main.verify_token", return_value="uid-abc")
@patch("main.list_conversations", return_value=[])
def test_get_conversation_detail_not_found(mock_list_convs, mock_verify):
    response = client.get(
        "/conversations/nonexistent-id",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert response.status_code == 404


@patch("main.verify_token", return_value="uid-abc")
@patch("main.is_subscriber", return_value=False)
@patch("main.get_monthly_count", return_value=0)
@patch("main.increment_count")
@patch("main._write_history")
@patch("main.write_cache")
@patch("main.get_cached", return_value=None)
@patch("main.create_conversation", return_value=FAKE_CONV_ID)
@patch("main.handle_query")
def test_query_uses_provided_conversation_id(mock_handle, mock_create_conv, mock_get_cached, mock_write, mock_hist, mock_inc, mock_count, mock_sub, mock_verify):
    mock_handle.return_value = QueryResponse(answer="Answer.", sources=[])
    response = client.post(
        "/query",
        json={"question": "Follow-up question", "conversation_id": "existing-conv-id"},
        headers={"Authorization": "Bearer valid-token"},
    )
    assert response.status_code == 200
    mock_create_conv.assert_not_called()
    assert response.json()["conversation_id"] == "existing-conv-id"
