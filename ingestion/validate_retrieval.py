"""
Retrieval validation script for Phase 3.

Queries each rulebook with known questions and verifies the top-1 result
contains the expected keywords. Useful after re-ingestion to confirm chunks
landed correctly.

Usage:
  python validate_retrieval.py              # all rulebooks
  python validate_retrieval.py --body OBR   # one rulebook
"""

import argparse
import sys
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

from embedder import embed_batch
from pinecone_store import _get_index
from sources import GOVERNING_BODY_DEPS

PASS_THRESHOLD = 0.90


@dataclass
class ValidationCase:
    question: str
    governing_body: str
    expected_keywords: list[str]
    description: str


@dataclass
class ValidationResult:
    case: ValidationCase
    passed: bool
    top_chunk: dict | None


CASES: list[ValidationCase] = [
    # OBR
    ValidationCase("What is the infield fly rule and when does it apply?", "OBR", ["infield fly"], "OBR — infield fly rule"),
    ValidationCase("What actions by a pitcher constitute a balk?", "OBR", ["balk"], "OBR — balk"),
    ValidationCase("What is the definition of obstruction?", "OBR", ["obstruction"], "OBR — obstruction"),
    ValidationCase("What is interference and when is it called?", "OBR", ["interference"], "OBR — interference"),
    ValidationCase("When is a batter touched by a pitched ball entitled to advance to first base?", "OBR", ["touched by"], "OBR — hit by pitch"),

    # DYB
    ValidationCase("When does the infield fly rule apply?", "DYB", ["infield fly"], "DYB — infield fly rule"),
    ValidationCase("What is a fielder's choice?", "DYB", ["fielder's choice"], "DYB — fielder's choice"),
    ValidationCase("What is obstruction?", "DYB", ["obstruction"], "DYB — obstruction"),
    ValidationCase("What is interference?", "DYB", ["interference"], "DYB — interference"),
    ValidationCase("What is the dropped third strike rule?", "DYB", ["third strike"], "DYB — dropped third strike"),

    # DYS (filter includes NFHS_SOFTBALL via dependency)
    ValidationCase("What constitutes an illegal pitch in softball?", "DYS", ["illegal"], "DYS — illegal pitch"),
    ValidationCase("When does the infield fly rule apply in softball?", "DYS", ["infield fly"], "DYS — infield fly rule"),
    ValidationCase("What is obstruction in softball?", "DYS", ["obstruction"], "DYS — obstruction"),
    ValidationCase("What is interference in softball?", "DYS", ["interference"], "DYS — interference"),
    ValidationCase("When does a pitched ball touching a batter award them first base?", "DYS", ["touches"], "DYS — hit by pitch"),

    # NFHS_SOFTBALL
    ValidationCase("What constitutes an illegal pitch?", "NFHS_SOFTBALL", ["illegal"], "NFHS — illegal pitch"),
    ValidationCase("When does the infield fly rule apply?", "NFHS_SOFTBALL", ["infield fly"], "NFHS — infield fly rule"),
    ValidationCase("What is obstruction?", "NFHS_SOFTBALL", ["obstruction"], "NFHS — obstruction"),
    ValidationCase("What is interference?", "NFHS_SOFTBALL", ["interference"], "NFHS — interference"),
    ValidationCase("When does a pitched ball touching a batter award them first base?", "NFHS_SOFTBALL", ["touches"], "NFHS — hit by pitch"),
]


def check_keywords(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    return all(kw.lower() in lower for kw in keywords)


def _build_filter(governing_body: str) -> dict:
    bodies = GOVERNING_BODY_DEPS.get(governing_body, [governing_body])
    if len(bodies) == 1:
        return {"governing_body": {"$eq": bodies[0]}}
    return {"governing_body": {"$in": bodies}}


def _retrieve(question: str, governing_body: str, top_k: int = 1) -> list[dict]:
    vector = embed_batch([question])[0]
    results = _get_index().query(
        vector=vector,
        top_k=top_k,
        include_metadata=True,
        filter=_build_filter(governing_body),
    )
    return [match.metadata for match in results.matches]


def run_case(case: ValidationCase, retrieve_fn=_retrieve) -> ValidationResult:
    chunks = retrieve_fn(case.question, case.governing_body, top_k=1)
    if not chunks:
        return ValidationResult(case=case, passed=False, top_chunk=None)
    top = chunks[0]
    passed = check_keywords(top.get("text", ""), case.expected_keywords)
    return ValidationResult(case=case, passed=passed, top_chunk=top)


def accuracy(results: list[ValidationResult]) -> float:
    if not results:
        return 0.0
    return sum(1 for r in results if r.passed) / len(results)


def _print_result(result: ValidationResult) -> None:
    status = "PASS" if result.passed else "FAIL"
    chunk = result.top_chunk
    rule = chunk.get("rule_number", "?") if chunk else "—"
    body = chunk.get("governing_body", "?") if chunk else "—"
    print(f"  [{status}] {result.case.description}")
    if not result.passed:
        preview = chunk.get("text", "")[:120].replace("\n", " ") if chunk else "no chunks returned"
        print(f"         retrieved: {body} rule {rule}")
        print(f"         text:      {preview}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--body", metavar="BODY", help="Validate only one governing body")
    args = parser.parse_args()

    cases = CASES
    if args.body:
        cases = [c for c in CASES if c.governing_body == args.body.upper()]
        if not cases:
            print(f"No cases for governing body '{args.body}'", file=sys.stderr)
            sys.exit(1)

    bodies = dict.fromkeys(c.governing_body for c in cases)
    all_results: list[ValidationResult] = []

    for body in bodies:
        body_cases = [c for c in cases if c.governing_body == body]
        print(f"\n{body} ({len(body_cases)} cases)")
        results = [run_case(c) for c in body_cases]
        for r in results:
            _print_result(r)
        pct = accuracy(results) * 100
        print(f"  → {sum(r.passed for r in results)}/{len(results)} passed ({pct:.0f}%)")
        all_results.extend(results)

    overall = accuracy(all_results)
    print(f"\nOverall: {sum(r.passed for r in all_results)}/{len(all_results)} passed ({overall * 100:.0f}%)")

    if overall < PASS_THRESHOLD:
        print(f"FAILED — below {PASS_THRESHOLD * 100:.0f}% threshold", file=sys.stderr)
        sys.exit(1)

    print("PASSED")


if __name__ == "__main__":
    main()
