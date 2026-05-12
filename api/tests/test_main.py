import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

# Patch Firebase init before importing app
with patch("firebase_admin.initialize_app"), patch("firebase_admin.credentials.Certificate"):
    from main import app

from models import QueryResponse, Source

client = TestClient(app, raise_server_exceptions=False)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("main.verify_token", return_value="uid-abc")
@patch("main.is_subscriber", return_value=False)
@patch("main.get_monthly_count", return_value=0)
@patch("main.increment_count")
@patch("main.write_cache")
@patch("main.get_cached", return_value=None)
@patch("main.handle_query")
def test_query_success(mock_handle, mock_get_cached, mock_write, mock_inc, mock_count, mock_sub, mock_verify):
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
def test_query_over_limit(mock_count, mock_sub, mock_verify):
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
@patch("main.handle_query", side_effect=Exception("Pinecone unavailable"))
def test_query_internal_error(mock_handle, mock_get_cached, mock_inc, mock_count, mock_sub, mock_verify):
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
@patch("main.get_cached", return_value={"answer": "Cached answer.", "sources": []})
def test_query_returns_cached_answer(mock_cached, mock_inc, mock_count, mock_sub, mock_verify):
    response = client.post(
        "/query",
        json={"question": "What is the infield fly rule?", "governing_body": "OBR"},
        headers={"Authorization": "Bearer valid-token"},
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "Cached answer."


@patch("main.verify_token", return_value="uid-abc")
@patch("main.is_subscriber", return_value=False)
@patch("main.get_monthly_count", return_value=0)
@patch("main.increment_count")
@patch("main.write_cache")
@patch("main.get_cached", return_value=None)
@patch("main.handle_query")
def test_query_writes_to_cache_on_miss(mock_handle, mock_get_cached, mock_write, mock_inc, mock_count, mock_sub, mock_verify):
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
@patch("main.handle_query")
@patch("main.get_cached", return_value=None)
def test_query_does_not_call_handle_query_on_cache_hit(mock_get_cached, mock_handle, mock_inc, mock_count, mock_sub, mock_verify):
    mock_get_cached.return_value = {"answer": "Cached.", "sources": []}
    client.post(
        "/query",
        json={"question": "What is the infield fly rule?"},
        headers={"Authorization": "Bearer valid-token"},
    )
    mock_handle.assert_not_called()
