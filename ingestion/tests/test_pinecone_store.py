import pytest
from unittest.mock import MagicMock, patch

import pinecone_store as _store_module
from pinecone_store import upsert_chunks
from schema import ChunkMetadata, GoverningBody


@pytest.fixture(autouse=True)
def reset_index():
    _store_module._index = None
    yield
    _store_module._index = None


def make_chunk(i: int) -> ChunkMetadata:
    return ChunkMetadata(
        id=f"dyb-2026-{i:04d}",
        text=f"Rule text {i}.",
        source_doc="2026-DYB-Official-Playing-Rules",
        governing_body=GoverningBody.DYB,
        year=2026,
        chunk_index=i,
    )


class TestUpsertChunks:
    def test_upserts_all_chunks(self):
        chunks = [make_chunk(i) for i in range(3)]
        vectors = [[float(i)] * 1024 for i in range(3)]

        with patch("pinecone_store.Pinecone") as mock_pc_cls:
            mock_index = mock_pc_cls.return_value.Index.return_value
            upsert_chunks(chunks, vectors)

        all_upserted = [
            record
            for call_args in mock_index.upsert.call_args_list
            for record in call_args[1]["vectors"]
        ]
        assert len(all_upserted) == 3

    def test_upsert_record_shape(self):
        chunk = make_chunk(0)
        vector = [0.1] * 1024

        with patch("pinecone_store.Pinecone") as mock_pc_cls:
            mock_index = mock_pc_cls.return_value.Index.return_value
            upsert_chunks([chunk], [vector])

        record = mock_index.upsert.call_args[1]["vectors"][0]
        assert record["id"] == chunk.id
        assert record["values"] == vector
        assert record["metadata"]["governing_body"] == "DYB"

    def test_batches_large_uploads(self):
        chunks = [make_chunk(i) for i in range(250)]
        vectors = [[0.1] * 1024 for _ in range(250)]

        with patch("pinecone_store.Pinecone") as mock_pc_cls:
            mock_index = mock_pc_cls.return_value.Index.return_value
            upsert_chunks(chunks, vectors)

        # BATCH_SIZE=100 → 3 calls for 250 chunks
        assert mock_index.upsert.call_count == 3
