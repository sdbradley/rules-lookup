import pytest
from schema import ChunkMetadata, GoverningBody


def test_governing_body_values_are_stable():
    assert GoverningBody.DYB.value == "DYB"
    assert GoverningBody.DYS.value == "DYS"
    assert GoverningBody.OBR.value == "OBR"
    assert GoverningBody.NFHS_SOFTBALL.value == "NFHS_SOFTBALL"


def test_governing_body_has_no_nfhs_baseball():
    assert not hasattr(GoverningBody, "NFHS_BASEBALL")


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


def test_chunk_metadata_optional_fields_omitted_when_none():
    chunk = ChunkMetadata(
        id="nfhs-softball-2026-unknown-0",
        text="Some rule text.",
        source_doc="2026-NFHS-Softball",
        governing_body=GoverningBody.NFHS_SOFTBALL,
        year=2026,
    )
    pinecone_meta = chunk.to_pinecone_metadata()

    assert "rule_number" not in pinecone_meta
    assert "section_title" not in pinecone_meta
    assert "page_number" not in pinecone_meta
    assert pinecone_meta["chunk_index"] == 0


def test_pinecone_metadata_includes_optional_fields_when_set():
    chunk = ChunkMetadata(
        id="dys-2026-2.04-0",
        text="Players shall be considered property of the league.",
        source_doc="2026-DYS-Official-Playing-Rules",
        governing_body=GoverningBody.DYS,
        year=2026,
        rule_number="2.04",
        section_title="Player Eligibility",
        page_number=10,
    )
    meta = chunk.to_pinecone_metadata()
    assert meta["rule_number"] == "2.04"
    assert meta["section_title"] == "Player Eligibility"
    assert meta["page_number"] == 10


def test_chunk_id_format():
    chunk = ChunkMetadata(
        id="dyb-2026-1.01-0",
        text="Some text.",
        source_doc="2026-DYB-Official-Playing-Rules",
        governing_body=GoverningBody.DYB,
        year=2026,
    )
    assert chunk.id == "dyb-2026-1.01-0"
