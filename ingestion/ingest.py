from dotenv import load_dotenv
load_dotenv()

from chunker import chunk_source
from embedder import embed_batch
from pinecone_store import upsert_chunks
from sources import SOURCES

EMBED_BATCH_SIZE = 50


def ingest_source(config) -> None:
    print(f"\n{config.governing_body.value} — {config.path.name}")
    chunks = chunk_source(config)
    print(f"  {len(chunks)} chunks")

    for i in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[i : i + EMBED_BATCH_SIZE]
        vectors = embed_batch([c.text for c in batch])
        upsert_chunks(batch, vectors)

    print(f"  done")


if __name__ == "__main__":
    for config in SOURCES:
        ingest_source(config)
    print("\nAll sources ingested.")
