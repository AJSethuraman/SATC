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
    """Classify every page of a PDF by its text layer (OCR'ing pages that lack one)."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    use_ocr = getattr(classifier, "ocr_text_provider", None) is not None
    out: list[Classification] = []
    from satc.ingest.pages import is_guidance

    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if not text.strip() and use_ocr:          # scanned page: OCR it locally
            try:
                from satc.ingest.ocr import ocr_pdf_page_text

                text = ocr_pdf_page_text(path, i)
            except Exception:  # noqa: BLE001
                text = ""
        # A PAGE OF INSTRUCTIONS IS NOT A DOCUMENT. This is the path production
        # runs -- `sort_folder`, `intake` and `collect` all split before they
        # classify -- and without this it made a whole document out of every
        # notice and instruction page inside a form. Measured on the real
        # blanks, 31 Aug 2026: one eleven-page W-2 became SIX "documents", one
        # of them a HIGH-confidence `Prior-year 1040` cut from a W-2
        # instruction page; and `f1099g.pdf` led with a HIGH `1099-NEC` made
        # out of its notice page, which `reconcile_received` would have used to
        # close the client's open 1099-NEC request.
        #
        # UNCLASSIFIED rather than dropped: `segment_pages` attaches a
        # non-verdict page to the run around it, so the instructions stay with
        # the form they belong to and no page is lost.
        if is_guidance(text):
            out.append(UNCLASSIFIED)
            continue
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

    # A DOCUMENT THAT OPENS WITH A NON-VERDICT. The loop attaches an
    # unclassified page to the form BEFORE it, and at the top of a file there is
    # no form before it -- so a leading notice page became a document of its own
    # and every real IRS blank "split" into two. The same reasoning applies at
    # either end: a page we could not name belongs with the document it is bound
    # to, and the only document it can be bound to here is the one that follows.
    if len(segments) > 1 and _category(segments[0].classification) is None:
        segments[1].start = segments[0].start
        segments.pop(0)
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
