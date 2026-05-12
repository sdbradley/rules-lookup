from unittest.mock import MagicMock, patch

import validate_retrieval
from validate_retrieval import ValidationCase, ValidationResult, check_keywords, run_case


def make_chunk(text: str = "The infield fly rule applies when...", **kwargs) -> dict:
    return {"text": text, "governing_body": "OBR", "rule_number": "2.00", **kwargs}


class TestCheckKeywords:
    def test_all_keywords_present(self):
        assert check_keywords("The infield fly rule applies here.", ["infield fly"]) is True

    def test_missing_keyword_returns_false(self):
        assert check_keywords("The batter is out.", ["infield fly"]) is False

    def test_all_of_multiple_keywords_must_match(self):
        assert check_keywords("obstruction was called on the fielder.", ["obstruction", "balk"]) is False

    def test_all_of_multiple_keywords_present(self):
        assert check_keywords("obstruction and balk rules differ.", ["obstruction", "balk"]) is True

    def test_case_insensitive(self):
        assert check_keywords("The Infield Fly Rule applies.", ["infield fly"]) is True

    def test_empty_keywords_returns_true(self):
        assert check_keywords("anything", []) is True


class TestRunCase:
    def test_pass_when_top_chunk_matches(self):
        case = ValidationCase(
            question="When does the infield fly rule apply?",
            governing_body="OBR",
            expected_keywords=["infield fly"],
            description="Infield fly rule",
        )
        retrieve_fn = MagicMock(return_value=[make_chunk("The infield fly rule applies when...")])
        result = run_case(case, retrieve_fn)
        assert result.passed is True
        assert result.case is case

    def test_fail_when_top_chunk_does_not_match(self):
        case = ValidationCase(
            question="When does the infield fly rule apply?",
            governing_body="OBR",
            expected_keywords=["infield fly"],
            description="Infield fly rule",
        )
        retrieve_fn = MagicMock(return_value=[make_chunk("The batter is awarded first base.")])
        result = run_case(case, retrieve_fn)
        assert result.passed is False

    def test_fail_when_no_chunks_returned(self):
        case = ValidationCase(
            question="What is a balk?",
            governing_body="OBR",
            expected_keywords=["balk"],
            description="Balk rule",
        )
        retrieve_fn = MagicMock(return_value=[])
        result = run_case(case, retrieve_fn)
        assert result.passed is False
        assert result.top_chunk is None

    def test_only_top_chunk_is_checked(self):
        case = ValidationCase(
            question="What is a balk?",
            governing_body="OBR",
            expected_keywords=["balk"],
            description="Balk rule",
        )
        chunks = [
            make_chunk("Obstruction was called."),         # top-1 — no "balk"
            make_chunk("A balk is an illegal motion."),    # top-2 — has "balk"
        ]
        retrieve_fn = MagicMock(return_value=chunks)
        result = run_case(case, retrieve_fn)
        assert result.passed is False

    def test_retrieve_called_with_top_k_1(self):
        case = ValidationCase(
            question="What is obstruction?",
            governing_body="OBR",
            expected_keywords=["obstruction"],
            description="Obstruction",
        )
        retrieve_fn = MagicMock(return_value=[make_chunk("obstruction")])
        run_case(case, retrieve_fn)
        retrieve_fn.assert_called_once_with("What is obstruction?", "OBR", top_k=1)

    def test_result_stores_top_chunk(self):
        case = ValidationCase(
            question="What is obstruction?",
            governing_body="OBR",
            expected_keywords=["obstruction"],
            description="Obstruction",
        )
        chunk = make_chunk("obstruction was called")
        retrieve_fn = MagicMock(return_value=[chunk])
        result = run_case(case, retrieve_fn)
        assert result.top_chunk is chunk


class TestAccuracy:
    def test_all_pass(self):
        results = [ValidationResult(case=MagicMock(), passed=True, top_chunk={}) for _ in range(5)]
        assert validate_retrieval.accuracy(results) == 1.0

    def test_partial_pass(self):
        results = [
            ValidationResult(case=MagicMock(), passed=True, top_chunk={}),
            ValidationResult(case=MagicMock(), passed=True, top_chunk={}),
            ValidationResult(case=MagicMock(), passed=False, top_chunk={}),
            ValidationResult(case=MagicMock(), passed=False, top_chunk={}),
            ValidationResult(case=MagicMock(), passed=False, top_chunk={}),
        ]
        assert validate_retrieval.accuracy(results) == pytest.approx(2 / 5)

    def test_empty_results(self):
        assert validate_retrieval.accuracy([]) == 0.0


import pytest
