"""Quick validation: shows how LlamaIndex chunks a markdown file."""

import sys
from pathlib import Path

from llama_index.core import Document
from llama_index.core.node_parser import MarkdownNodeParser

path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app/pdfs/nfhs-test.md")

with open(path) as f:
    content = f.read()

doc = Document(text=content)
nodes = MarkdownNodeParser().get_nodes_from_documents([doc])

print(f"File: {path.name}")
print(f"Total nodes: {len(nodes)}\n")

for i, node in enumerate(nodes):
    text_preview = node.text[:120].replace("\n", " ")
    print(f"[{i+1:02d}] metadata: {node.metadata}")
    print(f"      chars: {len(node.text)} | preview: {text_preview}")
    print()
