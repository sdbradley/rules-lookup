"""
Phase 1: PDF extraction quality check.

Reads each PDF from /app/pdfs, extracts text via pdfplumber,
and writes output to /app/output/<filename>.txt for manual inspection.
"""

import sys
from pathlib import Path

import pdfplumber

PDFS_DIR = Path("/app/pdfs")
OUTPUT_DIR = Path("/app/output")


def extract(pdf_path: Path) -> None:
    output_path = OUTPUT_DIR / f"{pdf_path.stem}.txt"
    print(f"Extracting {pdf_path.name} → {output_path.name}")

    pages_extracted = 0
    suspect_pages = []

    with pdfplumber.open(pdf_path) as pdf, output_path.open("w") as out:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            out.write(f"\n--- Page {i} ---\n")
            out.write(text)

            if len(text.strip()) < 50:
                suspect_pages.append(i)
            pages_extracted += 1

    print(f"  {pages_extracted} pages extracted")
    if suspect_pages:
        print(f"  WARNING: {len(suspect_pages)} suspect pages (very short text): {suspect_pages}")


def main() -> None:
    pdf_files = sorted(PDFS_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {PDFS_DIR}")
        sys.exit(1)

    for pdf_path in pdf_files:
        extract(pdf_path)

    print("\nDone. Inspect output/ to evaluate extraction quality.")


if __name__ == "__main__":
    main()
