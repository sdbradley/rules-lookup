from pathlib import Path

import pytest

from chunker import chunk_markdown, chunk_pdf, _parse_nfhs_metadata, _extract_pdf_rule_number
from schema import ChunkMetadata, GoverningBody
from sources import SourceConfig

NFHS_TEST = Path("/app/pdfs/2026-NFHS-softball-rules.md")
DYB_PDF = Path("/app/pdfs/2026-DYB-Official-Playing-Rules.pdf")


# --- markdown chunker ---

class TestChunkMarkdown:
    def test_returns_chunk_metadata_list(self):
        chunks = chunk_markdown(SourceConfig(NFHS_TEST, GoverningBody.NFHS_SOFTBALL, 2026))
        assert chunks
        assert all(isinstance(c, ChunkMetadata) for c in chunks)

    def test_governing_body_set(self):
        chunks = chunk_markdown(SourceConfig(NFHS_TEST, GoverningBody.NFHS_SOFTBALL, 2026))
        assert all(c.governing_body == GoverningBody.NFHS_SOFTBALL for c in chunks)

    def test_year_set(self):
        chunks = chunk_markdown(SourceConfig(NFHS_TEST, GoverningBody.NFHS_SOFTBALL, 2026))
        assert all(c.year == 2026 for c in chunks)

    def test_orphan_nodes_filtered(self):
        chunks = chunk_markdown(SourceConfig(NFHS_TEST, GoverningBody.NFHS_SOFTBALL, 2026))
        assert all(len(c.text.strip()) > 50 for c in chunks)

    def test_page_number_is_none(self):
        chunks = chunk_markdown(SourceConfig(NFHS_TEST, GoverningBody.NFHS_SOFTBALL, 2026))
        assert all(c.page_number is None for c in chunks)

    def test_chunk_ids_are_unique(self):
        chunks = chunk_markdown(SourceConfig(NFHS_TEST, GoverningBody.NFHS_SOFTBALL, 2026))
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_no_oversized_chunks(self):
        # Secondary splitter targets 512 tokens; at ~5 chars/token the char ceiling is ~2500.
        # This threshold catches truly runaway chunks while allowing normal sentence-split variance.
        chunks = chunk_markdown(SourceConfig(NFHS_TEST, GoverningBody.NFHS_SOFTBALL, 2026))
        assert all(len(c.text) <= 3000 for c in chunks)

    def test_rule_number_extracted(self):
        chunks = chunk_markdown(SourceConfig(NFHS_TEST, GoverningBody.NFHS_SOFTBALL, 2026))
        # Rule 1, Section 1, Art. 1 → "1-1-1"
        assert any(c.rule_number == "1-1-1" for c in chunks)

    def test_section_title_extracted(self):
        chunks = chunk_markdown(SourceConfig(NFHS_TEST, GoverningBody.NFHS_SOFTBALL, 2026))
        assert any(c.section_title == "THE FIELD" for c in chunks)


# --- NFHS metadata parser ---

class TestParseNfhsMetadata:
    def test_full_hierarchy(self):
        rule_num, section_title = _parse_nfhs_metadata(
            "/Rule 1 – Field and Equipment/SECTION 1 THE FIELD/",
            "### ART. 2\nMandated field distances...",
        )
        assert rule_num == "1-1-2"
        assert section_title == "THE FIELD"

    def test_section_2(self):
        rule_num, section_title = _parse_nfhs_metadata(
            "/Rule 1 – Field and Equipment/SECTION 2 BASES, PLATES/",
            "### ART. 1\nFirst, second and third base...",
        )
        assert rule_num == "1-2-1"
        assert section_title == "BASES, PLATES"

    def test_no_article_returns_none_rule_number(self):
        rule_num, _ = _parse_nfhs_metadata(
            "/Rule 1 – Field and Equipment/",
            "Some introductory text with no article heading.",
        )
        assert rule_num is None

    def test_empty_header_path(self):
        rule_num, section_title = _parse_nfhs_metadata("", "Some text.")
        assert rule_num is None
        assert section_title is None


# --- PDF rule number extractor ---

class TestExtractPdfRuleNumber:
    def test_standard_rule(self):
        assert _extract_pdf_rule_number("1.01 - DYB baseball is a game") == "1.01"

    def test_rule_with_parens(self):
        assert _extract_pdf_rule_number("4.01(c) Upon the umpire's entry") == "4.01"

    def test_section_header(self):
        assert _extract_pdf_rule_number("1.00-OBJECTIVES OF THE GAME") == "1.00"

    def test_no_rule_number(self):
        assert _extract_pdf_rule_number("This text has no rule number.") is None

    def test_rule_mid_paragraph_not_matched(self):
        # Rule numbers in the middle of a sentence should not match
        text = "As stated in rule 1.01, the game is played between two teams."
        assert _extract_pdf_rule_number(text) is None


# --- PDF chunker ---

class TestChunkPdf:
    def test_returns_chunk_metadata_list(self):
        chunks = chunk_pdf(SourceConfig(DYB_PDF, GoverningBody.DYB, 2026))
        assert chunks
        assert all(isinstance(c, ChunkMetadata) for c in chunks)

    def test_governing_body_set(self):
        chunks = chunk_pdf(SourceConfig(DYB_PDF, GoverningBody.DYB, 2026))
        assert all(c.governing_body == GoverningBody.DYB for c in chunks)

    def test_page_numbers_set(self):
        chunks = chunk_pdf(SourceConfig(DYB_PDF, GoverningBody.DYB, 2026))
        assert all(c.page_number is not None for c in chunks)

    def test_chunk_ids_are_unique(self):
        chunks = chunk_pdf(SourceConfig(DYB_PDF, GoverningBody.DYB, 2026))
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_no_empty_chunks(self):
        chunks = chunk_pdf(SourceConfig(DYB_PDF, GoverningBody.DYB, 2026))
        assert all(len(c.text.strip()) > 50 for c in chunks)
