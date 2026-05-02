import json
import os
from collections.abc import Generator

import anthropic
from pinecone import Pinecone
import voyageai

from models import QueryRequest, QueryResponse, Source

_voyage_client = None
_pinecone_index = None

GOVERNING_BODY_DEPS: dict[str, list[str]] = {
    "DYB": ["DYB"],
    "DYS": ["DYS", "NFHS_SOFTBALL"],
    "OBR": ["OBR"],
    "NFHS_SOFTBALL": ["NFHS_SOFTBALL"],
}

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are a knowledgeable baseball and softball rules assistant.
Answer questions using only the provided rule excerpts — do not rely on general knowledge.

Guidelines:
- Attribute each statement to its governing body (DYB, DYS, OBR, or NFHS_SOFTBALL)
- If excerpts from multiple governing bodies address the topic differently, note the differences explicitly
- If the excerpts do not contain enough information to answer, say so clearly rather than guessing
- Lead with a direct answer, then provide supporting citations
- Use plain language unless quoting directly from the rules"""


def _get_voyage() -> voyageai.Client:
    global _voyage_client
    if _voyage_client is None:
        _voyage_client = voyageai.Client(api_key=os.environ["VOYAGE_API_KEY"])
    return _voyage_client


def _get_index():
    global _pinecone_index
    if _pinecone_index is None:
        pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
        _pinecone_index = pc.Index(os.environ["PINECONE_INDEX_NAME"])
    return _pinecone_index


def embed_batch(texts: list[str]) -> list[list[float]]:
    result = _get_voyage().embed(texts, model="voyage-3")
    return result.embeddings


def build_filter(governing_body: str | None) -> dict | None:
    if governing_body is None:
        return None
    bodies = GOVERNING_BODY_DEPS.get(governing_body, [governing_body])
    if len(bodies) == 1:
        return {"governing_body": {"$eq": bodies[0]}}
    return {"governing_body": {"$in": bodies}}


def retrieve(question: str, governing_body: str | None = None, top_k: int = 5) -> list[dict]:
    vector = embed_batch([question])[0]
    results = _get_index().query(
        vector=vector,
        top_k=top_k,
        include_metadata=True,
        filter=build_filter(governing_body),
    )
    return [match.metadata for match in results.matches]


def _build_prompt(question: str, chunks: list[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        governing_body = chunk.get("governing_body", "Unknown")
        rule_number = chunk.get("rule_number")
        section_title = chunk.get("section_title")
        source_doc = chunk.get("source_doc", "")
        page = chunk.get("page_number")

        header = f"[Source {i}: {governing_body}"
        if rule_number:
            header += f", Rule {rule_number}"
        if section_title:
            header += f" — {section_title}"
        if page:
            header += f", p.{page}"
        header += f" ({source_doc})]"

        parts.append(f"{header}\n{chunk.get('text', '')}")

    context = "\n\n".join(parts)
    return f"Rule excerpts:\n\n{context}\n\nQuestion: {question}"


def generate(question: str, chunks: list[dict]) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_prompt(question, chunks)}],
    )
    return response.content[0].text


def chunk_to_source(chunk: dict) -> Source:
    return Source(
        governing_body=chunk.get("governing_body", "Unknown"),
        rule_number=chunk.get("rule_number"),
        section_title=chunk.get("section_title"),
        source_doc=chunk.get("source_doc", ""),
        page_number=chunk.get("page_number"),
    )


def handle_query(req: QueryRequest) -> QueryResponse:
    chunks = retrieve(req.question, req.governing_body)
    answer = generate(req.question, chunks)
    return QueryResponse(
        answer=answer,
        sources=[chunk_to_source(c) for c in chunks],
    )


def stream_query(req: QueryRequest) -> tuple[list[dict], Generator[str, None, None]]:
    chunks = retrieve(req.question, req.governing_body)

    def _generate() -> Generator[str, None, None]:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        with client.messages.stream(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_prompt(req.question, chunks)}],
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps({'type': 'text', 'text': text})}\n\n"

        sources = [chunk_to_source(c).model_dump() for c in chunks]
        yield f"data: {json.dumps({'type': 'done', 'sources': sources})}\n\n"

    return chunks, _generate()
