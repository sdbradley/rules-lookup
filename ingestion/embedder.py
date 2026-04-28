import os

import voyageai

_client: voyageai.Client | None = None


def _get_client() -> voyageai.Client:
    global _client
    if _client is None:
        _client = voyageai.Client(api_key=os.environ["VOYAGE_API_KEY"])
    return _client


def embed_batch(texts: list[str], model: str = "voyage-3") -> list[list[float]]:
    result = _get_client().embed(texts, model=model)
    return result.embeddings
