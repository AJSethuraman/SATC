"""Split a combined multi-form PDF into one document per form.

Real client uploads are often a single scanned stack: a W-2, then two 1099s, then
an engagement letter. This classifies each page by its text, groups consecutive
pages of the same form, and writes each run to its own PDF.

The non-obvious rule (from the standalone sorter): a page that doesn't classify —
an instruction page, a continuation, an illegible scan — **attaches to the form
that precedes it** rather than starting a new document. A new document begins only
when a page classifies as a *different* form.

Non-destructive: the original is never moved or modified; segments are copies.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from satc.ingest.classify import UNCLASSIFIED, Classification, DocumentClassifier, load_classifier


@dataclass(slots=True)
class Segment:
    """A run of consecutive pages that form one document. 0-based, inclusive."""

    classification: Classification
    start: int
    end: int

    @property
    def page_count(self) -> int:
        return self.end - self.start + 1


def _category(c: Classification | None) -> str | None:
    return c.label if (c is not None and c.classified) else None


def classify_pages(path: str | Path, classifier: DocumentClassifier) -> list[Classification]:
    """Classify every page of a PDF by its text layer."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    out: list[Classification] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        out.append(classifier.classify_text(text, method="text") or UNCLASSIFIED)
    return out


def segment_pages(classes: list[Classification]) -> list[Segment]:
    """Group consecutive pages; unclassified pages attach to the preceding form."""
    segments: list[Segment] = []
    for i, c in enumerate(classes):
        if not segments:
            segments.append(Segment(c, i, i))
            continue
        current = segments[-1]
        if _category(c) is None or _category(c) == _category(current.classification):
            current.end = i                      # continuation / same form
        else:
            segments.append(Segment(c, i, i))    # a different form starts here
    return segments


def plan_split(path: str | Path, classifier: DocumentClassifier | None = None) -> list[Segment]:
    """Return the page segments for a PDF (empty if it can't/needn't be split)."""
    classifier = classifier or load_classifier()
    try:
        classes = classify_pages(path, classifier)
    except Exception:  # noqa: BLE001 - unreadable / not a PDF
        return []
    if len(classes) < 2:
        return []
    return segment_pages(classes)


def is_combined(path: str | Path, classifier: DocumentClassifier | None = None) -> bool:
    """True if the PDF holds 2+ distinct forms and should be split."""
    return len(plan_split(path, classifier)) >= 2


def write_pages(src: str | Path, start: int, end: int, target: str | Path) -> None:
    """Write pages [start, end] (0-based, inclusive) of ``src`` to ``target``."""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(src))
    writer = PdfWriter()
    for p in range(start, end + 1):
        writer.add_page(reader.pages[p])
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "wb") as handle:
        writer.write(handle)


def split_to_dir(path: str | Path, out_dir: str | Path,
                 classifier: DocumentClassifier | None = None) -> list[tuple[Classification, Path]]:
    """Split a combined PDF into ``out_dir`` and return (classification, file) per part.

    Returns ``[]`` when the file is a single form (caller should read it whole).
    """
    segs = plan_split(path, classifier)
    if len(segs) < 2:
        return []
    src = Path(path)
    results: list[tuple[Classification, Path]] = []
    for i, seg in enumerate(segs, start=1):
        code = seg.classification.code if seg.classification.classified else "DOC"
        target = Path(out_dir) / f"{src.stem}__{i:02d}_{code}_p{seg.start + 1}-{seg.end + 1}.pdf"
        write_pages(src, seg.start, seg.end, target)
        results.append((seg.classification, target))
    return results
