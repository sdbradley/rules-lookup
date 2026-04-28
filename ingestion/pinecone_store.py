import os

from pinecone import Pinecone

from schema import ChunkMetadata

BATCH_SIZE = 100

_index = None


def _get_index():
    global _index
    if _index is None:
        pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
        _index = pc.Index(os.environ["PINECONE_INDEX_NAME"])
    return _index


def upsert_chunks(chunks: list[ChunkMetadata], vectors: list[list[float]]) -> None:
    index = _get_index()
    records = [
        {"id": chunk.id, "values": vector, "metadata": chunk.to_pinecone_metadata()}
        for chunk, vector in zip(chunks, vectors)
    ]
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        index.upsert(vectors=batch)
        print(f"  upserted {min(i + BATCH_SIZE, len(records))}/{len(records)}")
