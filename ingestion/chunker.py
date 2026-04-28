import re
from pathlib import Path

import pdfplumber
from llama_index.core import Document
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter

from schema import ChunkMetadata, GoverningBody
from sources import SourceConfig

_SENTENCE_SPLITTER = SentenceSplitter(chunk_size=512, chunk_overlap=50)
_MARKDOWN_PARSER = MarkdownNodeParser()

MIN_CHUNK_CHARS = 50
MAX_CHUNK_CHARS = 2048  # ~512 tokens; triggers secondary split above this


def chunk_source(config: SourceConfig) -> list[ChunkMetadata]:
    if config.path.suffix == ".md":
        return chunk_markdown(config)
    return chunk_pdf(config)


def chunk_markdown(config: SourceConfig) -> list[ChunkMetadata]:
    with open(config.path) as f:
        content = f.read()

    raw_nodes = _MARKDOWN_PARSER.get_nodes_from_documents([Document(text=content)])

    # Filter bare section-heading nodes (orphans with no article content)
    nodes = [n for n in raw_nodes if len(n.text.strip()) > MIN_CHUNK_CHARS]

    # Secondary split for any article that exceeds the token target
    expanded = []
    for node in nodes:
        if len(node.text) > MAX_CHUNK_CHARS:
            sub_nodes = _SENTENCE_SPLITTER.get_nodes_from_documents([Document(text=node.text)])
            for sub in sub_nodes:
                sub.metadata.update(node.metadata)
            expanded.extend(sub_nodes)
        else:
            expanded.append(node)

    chunks = []
    for i, node in enumerate(expanded):
        rule_number, section_title = _parse_nfhs_metadata(
            node.metadata.get("header_path", ""), node.text
        )
        chunks.append(ChunkMetadata(
            id=f"{config.governing_body.value.lower()}-{config.year}-{i:04d}",
            text=node.text,
            source_doc=config.path.stem,
            governing_body=config.governing_body,
            year=config.year,
            rule_number=rule_number,
            section_title=section_title,
            page_number=None,
            chunk_index=i,
        ))

    return chunks


def chunk_pdf(config: SourceConfig) -> list[ChunkMetadata]:
    chunks = []
    chunk_index = 0

    with pdfplumber.open(config.path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            if len(text) < MIN_CHUNK_CHARS:
                continue

            nodes = _SENTENCE_SPLITTER.get_nodes_from_documents([Document(text=text)])

            for node in nodes:
                if len(node.text.strip()) < MIN_CHUNK_CHARS:
                    continue
                chunks.append(ChunkMetadata(
                    id=f"{config.governing_body.value.lower()}-{config.year}-{chunk_index:04d}",
                    text=node.text,
                    source_doc=config.path.stem,
                    governing_body=config.governing_body,
                    year=config.year,
                    rule_number=_extract_pdf_rule_number(node.text),
                    section_title=None,
                    page_number=page_num,
                    chunk_index=chunk_index,
                ))
                chunk_index += 1

    return chunks


def _parse_nfhs_metadata(header_path: str, text: str) -> tuple[str | None, str | None]:
    parts = [p for p in header_path.split("/") if p]

    rule_base = section_num = section_title = art_num = None

    if parts:
        m = re.match(r"Rule (\d+)", parts[0])
        if m:
            rule_base = m.group(1)

    if len(parts) >= 2:
        m = re.match(r"SECTION (\d+)\s+(.*)", parts[1])
        if m:
            section_num = m.group(1)
            section_title = m.group(2).strip()

    m = re.match(r"###\s+ART\.\s+(\d+)", text)
    if m:
        art_num = m.group(1)

    rule_number = None
    if rule_base and section_num and art_num:
        rule_number = f"{rule_base}-{section_num}-{art_num}"

    return rule_number, section_title


def _extract_pdf_rule_number(text: str) -> str | None:
    # Match rule numbers at the start of a line: 1.01, 4.01, 1.00, etc.
    m = re.search(r"^(\d+\.\d+)\s*[-–(]", text, re.MULTILINE)
    return m.group(1) if m else None
