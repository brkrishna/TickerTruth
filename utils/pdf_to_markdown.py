#!/usr/bin/env python3
"""Convert a PDF file to Markdown using pdfminer for text extraction."""

import argparse
import re
import sys
from pathlib import Path

try:
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTChar, LTTextBox, LTTextLine
except ImportError:
    sys.exit("pdfminer.six is required. Run: pip install pdfminer.six")


def extract_text_from_pdf(pdf_path: Path) -> list[str]:
    pages = []
    for page_layout in extract_pages(str(pdf_path)):
        page_lines = []
        for element in page_layout:
            if isinstance(element, LTTextBox):
                for line in element:
                    if isinstance(line, LTTextLine):
                        text = line.get_text().rstrip("\n")
                        if not text.strip():
                            continue
                        font_sizes = [
                            char.size for char in line if isinstance(char, LTChar)
                        ]
                        avg_size = (
                            sum(font_sizes) / len(font_sizes) if font_sizes else 0
                        )
                        page_lines.append((text, avg_size))
        pages.append(page_lines)
    return pages


def infer_heading_level(font_size: float, size_map: dict[int, int]) -> int | None:
    """Map a font size bucket to a heading level (1–3), or None for body text."""
    rounded = round(font_size)
    return size_map.get(rounded)


def build_size_map(pages: list[list[tuple[str, float]]]) -> dict[int, int]:
    """Assign heading levels based on the top distinct font sizes in the doc."""
    from collections import Counter

    size_counter: Counter = Counter()
    for page in pages:
        for _, size in page:
            size_counter[round(size)] += 1

    # Body text is the most frequent size; pick up to 3 larger sizes as headings
    if not size_counter:
        return {}

    body_size = size_counter.most_common(1)[0][0]
    heading_sizes = sorted([s for s in size_counter if s > body_size], reverse=True)[:3]

    return {size: level + 1 for level, size in enumerate(heading_sizes)}


def lines_to_markdown(
    pages: list[list[tuple[str, float]]], size_map: dict[int, int]
) -> str:
    md_parts = []

    for page_num, page_lines in enumerate(pages, start=1):
        if page_num > 1:
            md_parts.append("\n---\n")  # page break marker

        paragraph_buffer: list[str] = []

        def flush_paragraph():
            if paragraph_buffer:
                md_parts.append(" ".join(paragraph_buffer))
                paragraph_buffer.clear()
                md_parts.append("")

        for text, size in page_lines:
            level = infer_heading_level(size, size_map)
            if level is not None:
                flush_paragraph()
                prefix = "#" * level
                md_parts.append(f"{prefix} {text.strip()}")
                md_parts.append("")
            else:
                stripped = text.strip()
                # Heuristic: short line ending without punctuation = likely a standalone line
                if len(stripped) < 60 and not stripped.endswith((",", ";", "-")):
                    flush_paragraph()
                    md_parts.append(stripped)
                    md_parts.append("")
                else:
                    paragraph_buffer.append(stripped)

        flush_paragraph()

    # Collapse more than two consecutive blank lines
    result = "\n".join(md_parts)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip() + "\n"


def convert(pdf_path: Path, output_path: Path | None = None) -> Path:
    if not pdf_path.exists():
        sys.exit(f"File not found: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        sys.exit(f"Expected a .pdf file, got: {pdf_path.suffix}")

    if output_path is None:
        output_path = pdf_path.with_suffix(".md")

    print(f"Reading {pdf_path} …")
    pages = extract_text_from_pdf(pdf_path)
    size_map = build_size_map(pages)
    markdown = lines_to_markdown(pages, size_map)

    output_path.write_text(markdown, encoding="utf-8")
    print(f"Written to {output_path}  ({len(markdown):,} chars, {len(pages)} pages)")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Convert a PDF to Markdown.")
    parser.add_argument("pdf", type=Path, help="Path to the input PDF file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output .md file path (default: same name as PDF, .md extension)",
    )
    args = parser.parse_args()
    convert(args.pdf, args.output)


if __name__ == "__main__":
    main()
