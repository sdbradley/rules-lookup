import os
import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()

from embedder import embed_batch
from pinecone_store import _get_index
from sources import GOVERNING_BODY_DEPS

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are a knowledgeable baseball and softball rules assistant.
Answer questions using only the provided rule excerpts — do not rely on general knowledge.

Guidelines:
- Attribute each statement to its governing body (DYB, DYS, OBR, or NFHS_SOFTBALL)
- If excerpts from multiple governing bodies address the topic differently, note the differences explicitly
- If the excerpts do not contain enough information to answer, say so clearly rather than guessing
- Lead with a direct answer, then provide supporting citations
- Use plain language unless quoting directly from the rules"""


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


def build_prompt(question: str, chunks: list[dict]) -> str:
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


def format_sources(chunks: list[dict]) -> str:
    lines = []
    for chunk in chunks:
        governing_body = chunk.get("governing_body", "Unknown")
        rule_number = chunk.get("rule_number")
        section_title = chunk.get("section_title")
        source_doc = chunk.get("source_doc", "")
        page = chunk.get("page_number")

        citation = f"  • {governing_body}"
        if rule_number:
            citation += f" Rule {rule_number}"
        if section_title:
            citation += f" — {section_title}"
        if page:
            citation += f" (p.{page})"
        citation += f" [{source_doc}]"
        lines.append(citation)
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python query.py "your question" [GOVERNING_BODY]')
        print("       GOVERNING_BODY: DYB | DYS | OBR | NFHS_SOFTBALL")
        sys.exit(1)

    question = sys.argv[1]
    governing_body = sys.argv[2].upper() if len(sys.argv) > 2 else None

    print(f"\nQuestion: {question}")
    if governing_body:
        print(f"Filter:   {governing_body}")
    print()

    print("Retrieving relevant rules...")
    chunks = retrieve(question, governing_body)
    print(f"Found {len(chunks)} excerpts. Generating answer...\n")

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_prompt(question, chunks)}],
    )

    print("Answer:")
    print("-" * 60)
    print(response.content[0].text)
    print("-" * 60)
    print("\nSources:")
    print(format_sources(chunks))
    print()


if __name__ == "__main__":
    main()
