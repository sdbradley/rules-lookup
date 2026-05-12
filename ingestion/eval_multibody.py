"""
Evaluation script for Phase 9: multi-rulebook disambiguation.

Runs ~20 questions through the query pipeline and prints the retrieved
governing bodies alongside the answer so the disambiguation behavior can
be reviewed manually.

Usage:
  python eval_multibody.py                  # all questions, no filter
  python eval_multibody.py --filter DYS     # restrict to DYS + its deps
  python eval_multibody.py --question 5     # run a single question by index
"""

import argparse
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

# Questions that span multiple governing bodies or probe disambiguation.
# Marked with expected bodies for reviewer orientation — not enforced by the script.
QUESTIONS = [
    # Multi-body: pitch distance differs between baseball and softball
    ("What is the distance from the pitcher's mound to home plate?", None),
    # Multi-body: base distances differ (DYB 60ft, DYS 60ft, OBR 90ft, NFHS_SOFTBALL 60ft)
    ("What are the base path distances?", None),
    # Multi-body: all rulebooks have batting-out-of-order but penalties may differ
    ("What happens when a batter bats out of order?", None),
    # Multi-body: obstruction rules exist in all but language differs OBR vs NFHS
    ("How does the obstruction rule work?", None),
    # Multi-body: infield fly across all
    ("When does the infield fly rule apply?", None),
    # Multi-body: dropped third strike — youth rules may differ
    ("What is the dropped third strike rule?", None),
    # Multi-body: balk rules differ between baseball and softball
    ("What pitching actions constitute a balk or illegal pitch?", None),
    # Multi-body: run limit / mercy rule may differ by rulebook
    ("Is there a run limit per inning or a mercy rule?", None),
    # Multi-body: walk rule is universal but good baseline
    ("How many balls does it take to walk a batter?", None),
    # DYS-specific: filter to DYS to verify NFHS_SOFTBALL dependency is included
    ("What are the pitching rules for softball?", "DYS"),
    # NFHS_SOFTBALL: legal delivery requirements
    ("What constitutes a legal pitch in softball?", "NFHS_SOFTBALL"),
    # DYB-specific: should pull from OBR as base
    ("Can a pitcher return to pitch after being removed from the mound?", "DYB"),
    # OBR: interference types
    ("What are the different types of interference?", "OBR"),
    # Multi-body: hit by pitch — all bodies have this but wording varies
    ("What happens when a batter is hit by a pitch?", None),
    # Multi-body: runner advancing on passed ball / wild pitch
    ("Can a runner advance on a wild pitch or passed ball?", None),
    # Multi-body: appeal plays
    ("What is an appeal play and when must it be made?", None),
    # Multi-body: time of pitch (when is the ball live vs dead)
    ("When is the ball considered live and when is it dead?", None),
    # DYS: courtesy runner or special runner rules in youth softball
    ("Are there any special runner substitution rules in youth softball?", "DYS"),
    # Multi-body: fielder's choice definition
    ("What is the definition of a fielder's choice?", None),
    # Multi-body: fair vs foul ball definition
    ("How is a fair ball distinguished from a foul ball?", None),
]


def build_filter(governing_body: str | None) -> dict | None:
    if governing_body is None:
        return None
    bodies = GOVERNING_BODY_DEPS.get(governing_body, [governing_body])
    if len(bodies) == 1:
        return {"governing_body": {"$eq": bodies[0]}}
    return {"governing_body": {"$in": bodies}}


def retrieve(question: str, governing_body: str | None, top_k: int = 5) -> list[dict]:
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


def run_question(index: int, question: str, governing_body: str | None) -> None:
    print(f"\n{'=' * 70}")
    print(f"[{index + 1}/{len(QUESTIONS)}] {question}")
    if governing_body:
        print(f"Filter: {governing_body}")

    chunks = retrieve(question, governing_body)
    bodies_retrieved = sorted({c.get("governing_body", "?") for c in chunks})
    print(f"Sources retrieved: {', '.join(bodies_retrieved)}")
    print()

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_prompt(question, chunks)}],
    )
    print(response.content[0].text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--filter", metavar="BODY", help="Governing body filter (DYB|DYS|OBR|NFHS_SOFTBALL)")
    parser.add_argument("--question", type=int, metavar="N", help="Run only question N (1-based)")
    args = parser.parse_args()

    if args.question is not None:
        idx = args.question - 1
        if idx < 0 or idx >= len(QUESTIONS):
            print(f"Question index must be between 1 and {len(QUESTIONS)}", file=sys.stderr)
            sys.exit(1)
        question, governing_body = QUESTIONS[idx]
        run_question(idx, question, args.filter or governing_body)
        return

    for i, (question, governing_body) in enumerate(QUESTIONS):
        run_question(i, question, args.filter or governing_body)

    print(f"\n{'=' * 70}")
    print(f"Evaluated {len(QUESTIONS)} questions.")


if __name__ == "__main__":
    main()
