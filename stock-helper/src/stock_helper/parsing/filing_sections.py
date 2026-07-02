"""Heuristic 10-K/10-Q section extraction (early Phase 2 slice).

Deliberately best-effort: EDGAR HTML formatting varies wildly across filers and
years. We convert HTML to text and locate "Item 1A" (Risk Factors) and
"Item 7" / "Item 2" (MD&A) headings by regex, taking the occurrence with the
most content after it (skips tables of contents). Everything extracted carries
PARSER_VERSION so results can be invalidated when the parser improves.
"""

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

PARSER_VERSION = "sections-0.1"

# Cap stored section size; MD&A in some filings is enormous.
_MAX_SECTION_CHARS = 150_000
_CHUNK_TARGET_CHARS = 2_000

# section key -> (start patterns, forms it applies to)
_SECTION_PATTERNS: dict[str, list[str]] = {
    "risk_factors": [
        r"item\s*1a\.?\s*[-–—:.]?\s*risk\s+factors",
    ],
    "mdna": [
        r"item\s*7\.?\s*[-–—:.]?\s*management'?s\s+discussion\s+and\s+analysis",
        r"item\s*2\.?\s*[-–—:.]?\s*management'?s\s+discussion\s+and\s+analysis",
    ],
}

# Any "Item N" style heading terminates the previous section.
_NEXT_ITEM = re.compile(r"\n\s*item\s+\d{1,2}[ab]?\.?\s", re.IGNORECASE)


@dataclass
class ExtractedSection:
    section_name: str
    text: str
    char_start: int
    char_end: int


@dataclass
class SectionChunk:
    section_name: str
    chunk_id: str
    chunk_index: int
    text: str
    char_start: int
    char_end: int


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text("\n")
    # Collapse aggressive whitespace but keep paragraph boundaries.
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text


def extract_sections(text: str) -> list[ExtractedSection]:
    """Best-effort extraction. Returns [] rather than guessing when headings
    can't be found — absence is reported honestly upstream."""
    lower = text.lower()
    sections: list[ExtractedSection] = []
    for name, patterns in _SECTION_PATTERNS.items():
        best: ExtractedSection | None = None
        for pattern in patterns:
            for match in re.finditer(pattern, lower):
                start = match.start()
                next_item = _NEXT_ITEM.search(lower, match.end())
                end = next_item.start() if next_item else min(len(text), start + _MAX_SECTION_CHARS)
                body = text[start:end].strip()
                # TOC entries have almost no content after the heading.
                if len(body) < 500:
                    continue
                if best is None or len(body) > len(best.text):
                    best = ExtractedSection(
                        section_name=name,
                        text=body[:_MAX_SECTION_CHARS],
                        char_start=start,
                        char_end=min(end, start + _MAX_SECTION_CHARS),
                    )
        if best:
            sections.append(best)
    return sections


def chunk_section(section: ExtractedSection, accession: str) -> list[SectionChunk]:
    """Split a section into ~2k-char chunks on paragraph boundaries, with stable
    chunk ids ({accession}:{section}:{n}) for future retrieval/citation use."""
    chunks: list[SectionChunk] = []
    paragraphs = section.text.split("\n\n")
    buffer: list[str] = []
    size = 0
    offset = section.char_start

    def flush() -> None:
        nonlocal buffer, size, offset
        if not buffer:
            return
        body = "\n\n".join(buffer)
        index = len(chunks)
        chunks.append(
            SectionChunk(
                section_name=section.section_name,
                chunk_id=f"{accession}:{section.section_name}:{index}",
                chunk_index=index,
                text=body,
                char_start=offset,
                char_end=offset + len(body),
            )
        )
        offset += len(body) + 2
        buffer, size = [], 0

    for paragraph in paragraphs:
        buffer.append(paragraph)
        size += len(paragraph)
        if size >= _CHUNK_TARGET_CHARS:
            flush()
    flush()
    return chunks
