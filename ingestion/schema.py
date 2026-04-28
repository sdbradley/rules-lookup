from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GoverningBody(str, Enum):
    DYB = "DYB"                      # Diamond Youth Baseball (OBR-based)
    DYS = "DYS"                      # Diamond Youth Softball (NFHS Softball-based)
    OBR = "OBR"                      # Official Baseball Rules (MLB / base for DYB)
    NFHS_SOFTBALL = "NFHS_SOFTBALL"  # NFHS Softball (base rules for DYS)


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
        meta: dict[str, Any] = {
            "text": self.text,
            "source_doc": self.source_doc,
            "governing_body": self.governing_body.value,
            "year": self.year,
            "chunk_index": self.chunk_index,
        }
        if self.rule_number is not None:
            meta["rule_number"] = self.rule_number
        if self.section_title is not None:
            meta["section_title"] = self.section_title
        if self.page_number is not None:
            meta["page_number"] = self.page_number
        return meta
