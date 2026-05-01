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
    client.messages.create.return_value = response

    answer = query_handler.generate("What is interference?", [SAMPLE_CHUNK])
    assert answer == "The answer is yes."
    client.messages.create.assert_called_once()


@patch("query_handler.generate", return_value="Here is the answer.")
@patch("query_handler.retrieve", return_value=[SAMPLE_CHUNK])
def test_handle_query(mock_retrieve, mock_generate):
    req = QueryRequest(question="What is interference?", governing_body="OBR")
    response = query_handler.handle_query(req)
    assert response.answer == "Here is the answer."
    assert len(response.sources) == 1
    assert response.sources[0].governing_body == "OBR"
    mock_retrieve.assert_called_once_with("What is interference?", "OBR")
    mock_generate.assert_called_once_with("What is interference?", [SAMPLE_CHUNK])
