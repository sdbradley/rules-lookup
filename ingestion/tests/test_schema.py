import pytest
from schema import ChunkMetadata, GoverningBody


def test_governing_body_values_are_stable():
    assert GoverningBody.DYB.value == "DYB"
    assert GoverningBody.DYS.value == "DYS"
    assert GoverningBody.NFHS_BASEBALL.value == "NFHS_BASEBALL"
    assert GoverningBody.NFHS_SOFTBALL.value == "NFHS_SOFTBALL"


def test_chunk_metadata_to_pinecone_roundtrip():
    chunk = ChunkMetadata(
        id="dyb-2026-1.01-0",
        text="DYB baseball is a game between two teams of nine players each.",
        source_doc="2026-DYB-Official-Playing-Rules",
        governing_body=GoverningBody.DYB,
        year=2026,
        rule_number="1.01",
        section_title="Objectives of the Game",
        page_number=16,
        chunk_index=0,
    )
    pinecone_meta = chunk.to_pinecone_metadata()

    assert pinecone_meta["text"] == chunk.text
    assert pinecone_meta["governing_body"] == "DYB"
    assert pinecone_meta["year"] == 2026
    assert pinecone_meta["rule_number"] == "1.01"
    assert pinecone_meta["section_title"] == "Objectives of the Game"
    assert pinecone_meta["page_number"] == 16
    assert pinecone_meta["chunk_index"] == 0


def test_chunk_metadata_optional_fields_default_to_none():
    chunk = ChunkMetadata(
        id="nfhs-baseball-2026-unknown-0",
        text="Some rule text.",
        source_doc="2026-NFHS-Baseball",
        governing_body=GoverningBody.NFHS_BASEBALL,
        year=2026,
    )
    pinecone_meta = chunk.to_pinecone_metadata()

    assert pinecone_meta["rule_number"] is None
    assert pinecone_meta["section_title"] is None
    assert pinecone_meta["page_number"] is None
    assert pinecone_meta["chunk_index"] == 0


def test_pinecone_metadata_has_no_extra_keys():
    chunk = ChunkMetadata(
        id="dys-2026-2.04-0",
        text="Players shall be considered property of the league.",
        source_doc="2026-DYS-Official-Playing-Rules",
        governing_body=GoverningBody.DYS,
        year=2026,
        rule_number="2.04",
    )
    expected_keys = {
        "text", "source_doc", "governing_body", "year",
        "rule_number", "section_title", "page_number", "chunk_index",
    }
    assert set(chunk.to_pinecone_metadata().keys()) == expected_keys


def test_chunk_id_format():
    chunk = ChunkMetadata(
        id="dyb-2026-1.01-0",
        text="Some text.",
        source_doc="2026-DYB-Official-Playing-Rules",
        governing_body=GoverningBody.DYB,
        year=2026,
    )
    assert chunk.id == "dyb-2026-1.01-0"
