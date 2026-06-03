#!/usr/bin/env python3
"""Shared PyMuPDF-based PDF operations.

The single home for the fitz-backed building blocks used across the suite -- merge,
split, and HTML-to-PDF -- so tools share one implementation instead of duplicating
it. Kept separate from core.py because these need PyMuPDF; fitz is imported lazily
inside each function so importing this module stays cheap.
"""

from __future__ import annotations

from pathlib import Path

PAGE_MARGIN = (54, 54, -54, -54)


def merge_pdfs(pdf_paths: list[Path], dest_path: Path) -> Path | None:
    """Concatenate PDFs into one file. Returns the output path, or None if no inputs."""

    import fitz  # PyMuPDF

    if not pdf_paths:
        return None
    merged = fitz.open()
    try:
        for path in pdf_paths:
            with fitz.open(path) as source:
                merged.insert_pdf(source)
        merged.save(str(dest_path))
    finally:
        merged.close()
    return dest_path


def split_pdf(source_pdf: Path, dest_dir: Path, prefix: str | None = None) -> list[Path]:
    """Split a PDF into one file per page in dest_dir. Returns the page file paths."""

    import fitz  # PyMuPDF

    outputs: list[Path] = []
    with fitz.open(source_pdf) as document:
        stem = prefix or source_pdf.stem
        width = max(len(str(document.page_count)), 2)
        for index in range(document.page_count):
            single = fitz.open()
            try:
                single.insert_pdf(document, from_page=index, to_page=index)
                dest = dest_dir / f"{stem}_p{str(index + 1).zfill(width)}.pdf"
                single.save(str(dest))
            finally:
                single.close()
            outputs.append(dest)
    return outputs


def html_to_pdf(html_text: str, dest_path: Path) -> Path:
    """Render an HTML string to a PDF (text stays selectable)."""

    import fitz  # PyMuPDF

    story = fitz.Story(html=html_text)
    writer = fitz.DocumentWriter(str(dest_path))
    rect = fitz.paper_rect("letter")
    area = rect + PAGE_MARGIN
    try:
        more = 1
        while more:
            device = writer.begin_page(rect)
            more, _ = story.place(area)
            story.draw(device)
            writer.end_page()
    finally:
        writer.close()
    return dest_path
