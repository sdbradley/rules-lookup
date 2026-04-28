from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GoverningBody(str, Enum):
    DYB = "DYB"
    DYS = "DYS"
    NFHS_BASEBALL = "NFHS_BASEBALL"
    NFHS_SOFTBALL = "NFHS_SOFTBALL"


# Pinecone index config — kept here so ingestion and query layers stay in sync
PINECONE_INDEX_DIMENSION = 1024  # voyage-3 output dimension
PINECONE_INDEX_METRIC = "cosine"


@dataclass
class ChunkMetadata:
    id: str
    text: str
    source_doc: str
    governing_body: GoverningBody
    year: int
    rule_number: str | None = None
    section_title: str | None = None
    page_number: int | None = None
    chunk_index: int = 0

    def to_pinecone_metadata(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "source_doc": self.source_doc,
            "governing_body": self.governing_body.value,
            "year": self.year,
            "rule_number": self.rule_number,
            "section_title": self.section_title,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
        }
