import pytest
from unittest.mock import MagicMock, patch

import query_handler
from models import QueryRequest, Source


SAMPLE_CHUNK = {
    "governing_body": "OBR",
    "rule_number": "6.01",
    "section_title": "Interference",
    "source_doc": "2026-official-baseball-rules",
    "page_number": 42,
    "text": "A batter is out when...",
}


def test_build_filter_none():
    assert query_handler.build_filter(None) is None


def test_build_filter_single():
    f = query_handler.build_filter("OBR")
    assert f == {"governing_body": {"$eq": "OBR"}}


def test_build_filter_dys_includes_nfhs():
    f = query_handler.build_filter("DYS")
    assert f == {"governing_body": {"$in": ["DYS", "NFHS_SOFTBALL"]}}


def test_chunk_to_source():
    source = query_handler.chunk_to_source(SAMPLE_CHUNK)
    assert isinstance(source, Source)
    assert source.governing_body == "OBR"
    assert source.rule_number == "6.01"
    assert source.page_number == 42


def test_chunk_to_source_optional_fields_missing():
    chunk = {"governing_body": "DYB", "source_doc": "2026-DYB", "text": "some text"}
    source = query_handler.chunk_to_source(chunk)
    assert source.rule_number is None
    assert source.section_title is None
    assert source.page_number is None


@patch("query_handler._get_index")
@patch("query_handler.embed_batch")
def test_retrieve(mock_embed, mock_get_index):
    mock_embed.return_value = [[0.1] * 1024]
    match = MagicMock()
    match.metadata = SAMPLE_CHUNK
    mock_get_index.return_value.query.return_value.matches = [match]

    chunks = query_handler.retrieve("what is interference?", "OBR")
    assert len(chunks) == 1
    assert chunks[0]["governing_body"] == "OBR"
    mock_get_index.return_value.query.assert_called_once()


@patch("query_handler.anthropic.Anthropic")
def test_generate(mock_anthropic_cls):
    client = MagicMock()
    mock_anthropic_cls.return_value = client
    response = MagicMock()
    response.content = [MagicMock(text="The answer is yes.")]
    response.usage = MagicMock(input_tokens=100, output_tokens=50)
    client.messages.create.return_value = response

    answer, input_tokens, output_tokens = query_handler.generate("What is interference?", [SAMPLE_CHUNK])
    assert answer == "The answer is yes."
    assert input_tokens == 100
    assert output_tokens == 50
    client.messages.create.assert_called_once()


@patch("query_handler.generate", return_value=("Here is the answer.", 100, 50))
@patch("query_handler.retrieve", return_value=[SAMPLE_CHUNK])
def test_handle_query(mock_retrieve, mock_generate):
    req = QueryRequest(question="What is interference?", governing_body="OBR")
    response = query_handler.handle_query(req)
    assert response.answer == "Here is the answer."
    assert len(response.sources) == 1
    assert response.sources[0].governing_body == "OBR"
    mock_retrieve.assert_called_once_with("What is interference?", "OBR")
    mock_generate.assert_called_once_with("What is interference?", [SAMPLE_CHUNK])


@patch("query_handler._get_index")
@patch("query_handler.embed_batch")
def test_retrieve_includes_vector_id(mock_embed, mock_get_index):
    mock_embed.return_value = [[0.1] * 1024]
    match = MagicMock()
    match.id = "vec_abc123"
    match.metadata = SAMPLE_CHUNK
    mock_get_index.return_value.query.return_value.matches = [match]

    chunks = query_handler.retrieve("what is interference?", "OBR")
    assert chunks[0]["_id"] == "vec_abc123"
    assert chunks[0]["governing_body"] == "OBR"


def test_log_query_to_firestore():
    db = MagicMock()
    req = QueryRequest(question="What is interference?", governing_body="OBR")
    chunks = [dict(SAMPLE_CHUNK, _id="vec_abc")]

    query_handler._log_query_to_firestore(db, "uid-123", req, chunks, "The answer.", 450)

    db.collection.assert_called_once_with("query_logs")
    written = db.collection.return_value.add.call_args[0][0]
    assert written["uid"] == "uid-123"
    assert written["question"] == "What is interference?"
    assert written["governing_body"] == "OBR"
    assert written["chunk_ids"] == ["vec_abc"]
    assert written["answer"] == "The answer."
    assert written["latency_ms"] == 450
    assert "created_at" in written


def test_log_query_to_firestore_omits_chunks_without_id():
    db = MagicMock()
    req = QueryRequest(question="What is a balk?", governing_body=None)
    chunks = [SAMPLE_CHUNK]  # no _id field

    query_handler._log_query_to_firestore(db, "uid-123", req, chunks, "A balk is...", 300)

    written = db.collection.return_value.add.call_args[0][0]
    assert written["chunk_ids"] == []


@patch("query_handler._log_query_to_firestore")
@patch("query_handler.generate", return_value=("Here is the answer.", 100, 50))
@patch("query_handler.retrieve", return_value=[SAMPLE_CHUNK])
def test_handle_query_logs_to_firestore_when_db_provided(mock_retrieve, mock_generate, mock_log_fs):
    db = MagicMock()
    req = QueryRequest(question="What is interference?", governing_body="OBR")
    query_handler.handle_query(req, uid="uid-abc", db=db)
    mock_log_fs.assert_called_once()
    call_args = mock_log_fs.call_args[0]
    assert call_args[0] is db
    assert call_args[1] == "uid-abc"


@patch("query_handler._log_query_to_firestore")
@patch("query_handler.generate", return_value=("Here is the answer.", 100, 50))
@patch("query_handler.retrieve", return_value=[SAMPLE_CHUNK])
def test_handle_query_no_firestore_when_db_none(mock_retrieve, mock_generate, mock_log_fs):
    req = QueryRequest(question="What is interference?", governing_body="OBR")
    query_handler.handle_query(req, uid="uid-abc", db=None)
    mock_log_fs.assert_not_called()


@patch("query_handler.anthropic.Anthropic")
@patch("query_handler.retrieve", return_value=[SAMPLE_CHUNK])
def test_stream_query_calls_on_complete(mock_retrieve, mock_anthropic_cls):
    client = MagicMock()
    mock_anthropic_cls.return_value = client
    stream_ctx = MagicMock()
    stream_ctx.__enter__ = MagicMock(return_value=stream_ctx)
    stream_ctx.__exit__ = MagicMock(return_value=False)
    stream_ctx.text_stream = iter(["The answer ", "is yes."])
    final_msg = MagicMock()
    final_msg.usage = MagicMock(input_tokens=100, output_tokens=20)
    stream_ctx.get_final_message.return_value = final_msg
    client.messages.stream.return_value = stream_ctx

    on_complete = MagicMock()
    req = QueryRequest(question="What is interference?", governing_body="OBR")
    _, gen = query_handler.stream_query(req, uid="uid-abc", on_complete=on_complete)

    # exhaust the generator to trigger on_complete
    list(gen)

    on_complete.assert_called_once()
    answer, sources = on_complete.call_args[0]
    assert answer == "The answer is yes."
    assert isinstance(sources, list)
