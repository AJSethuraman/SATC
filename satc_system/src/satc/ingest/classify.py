"""Content-based document classification — decide what a file *is* by reading it.

A filename sorter breaks the moment a client sends ``IMG_4471.pdf``. This reads the
document instead, preferring cheap and exact signals before any paid OCR:

    1. PDF form fields  — a fillable form's AcroForm field names are its
       fingerprint (``w2_box1_wages`` -> W-2). Free, exact.
    2. Embedded PDF text — most "PDFs" carry a real text layer; the form's printed
       title ("Wage and Tax Statement") names it. Free, no OCR.
    3. Filename hint     — weak; used only when the content is silent.
    4. Vision / OCR      — only true scans with no text layer reach here; needs an
       Anthropic API key and costs a little per document.

The result feeds the same intake/staging pipeline, so classification only picks
*which* extraction map to use — it never writes a value on its own.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from satc.config import load_classification, load_extraction_map

# Confidence ordering for any callers that want to compare.
CONF_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "UNCERTAIN": 0}

# Default scoring knobs for the text rung (overridable in classification.yaml).
DEFAULT_TEXT_THRESHOLD = 6      # minimum winning score to classify by text
DEFAULT_CLOSE_DELTA = 3         # winner within this of the runner-up => ambiguous (don't guess)

_DASHES = "‐‑‒–—−"
_QUOTES = "‘’ʼ`'"


def _normalize(text: str) -> str:
    return "".join(ch for ch in str(text).lower() if ch.isalnum())


def _normalize_text(text: str) -> str:
    """Lowercase, fold unicode dashes/quotes, and repair OCR-split form names.

    Scanners routinely drop the hyphen in form numbers ("1099 NEC", "W 2"); a
    keyword match would miss them otherwise. Keeps word boundaries (spaces) so
    multi-word phrases still match — unlike :func:`_normalize`.
    """
    t = str(text).lower()
    for d in _DASHES:
        t = t.replace(d, "-")
    for q in _QUOTES:
        t = t.replace(q, "")
    t = re.sub(r"\b1099\s+(nec|misc|int|div|r|b|g|k)\b", r"1099-\1", t)
    t = re.sub(r"\bw\s+2\b", "w-2", t)
    t = re.sub(r"\b1098\s+(t|e)\b", r"1098-\1", t)
    t = re.sub(r"\bssa\s+1099\b", "ssa-1099", t)
    return re.sub(r"\s+", " ", t).strip()


@dataclass(slots=True)
class DocType:
    """A known document type and the signals that identify it."""

    key: str | None                       # extraction-config key; None = filed-not-extracted
    label: str
    code: str
    filename_hints: list[str] = field(default_factory=list)
    keywords: list[tuple[str, int]] = field(default_factory=list)  # (normalized phrase, weight)
    threshold: int = 0                    # per-type override; 0 = use the classifier default
    field_markers: set[str] = field(default_factory=set)  # normalized AcroForm field names

    @property
    def extractable(self) -> bool:
        return self.key is not None


# Methods that are not an identification at all. Kept as a set rather than a
# chain of != so that adding a third non-verdict cannot silently pass for one.
_NOT_A_VERDICT = frozenset({"unclassified", "not downloaded"})

# Worst first, so `min(confidences, key=_CONFIDENCE_ORDER.index)` reads as what
# it is: several pages agreeing is only as good as the least sure of them.
_CONFIDENCE_ORDER = ["LOW", "MEDIUM", "HIGH"]

# HOW MANY DISTINCT KEYWORDS A TYPE MUST MATCH before it may be a verdict at
# all. The config's own header promises that "generic words are low so they
# can't classify on their own" -- and that was only ever true of GENERIC words.
# `["form w-2", 9]` against a threshold of 6 meant one occurrence of the literal
# string "Form W-2", anywhere, classified a document as a W-2 at HIGH.
#
# MEASURED on the fourteen real blanks, 31 Aug 2026, counting distinct keyword
# phrases matched by each file's winning type on its best page:
#
#     real forms      2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 4, 5, 6      (minimum 2)
#     Schedule C      1     -- "Form W-2", "Form 1065", "Form 1040" once each,
#                              which came back "Several forms: W-2, Schedule
#                              K-1 (1065), Prior-year 1040"
#
# A document that IS a form says so more than once and in more than one way; a
# document that MENTIONS one says it once. The two do not overlap.
#
# THE FAILURE DIRECTION IS DELIBERATE. A form that names itself only once now
# comes back Unclassified, and a preparer looks at it. That is the cheap
# mistake. Filing a Schedule C against a client's open W-2 request closes it,
# and nobody asks for the W-2 again.
MIN_SIGNALS = 2


@dataclass(slots=True)
class Classification:
    """The classifier's verdict for one file."""

    label: str
    key: str | None
    code: str
    confidence: str          # HIGH / MEDIUM / LOW / UNCERTAIN
    method: str              # "form fields" / "text" / "filename" / "vision" / "unclassified"
    evidence: str = ""
    # EVERY form this one document contains, primary first. Empty for the
    # ordinary case of one document, one form -- the composite label is not a
    # substitute, because a caller that has to parse a label to learn what it
    # found will eventually parse it wrong.
    forms: tuple[str, ...] = ()
    # The tax year printed on the document, or None for "could not read one".
    # None NEVER means the current year -- see document_year and wrong_year.
    tax_year: int | None = None

    @property
    def multi(self) -> bool:
        """True when this document is SEVERAL forms, not one.

        Distinct from a low confidence, and the distinction is the whole point.
        MEDIUM means *we are unsure which single form this is*. ``multi`` means
        *we are sure it is more than one* -- a consolidated brokerage 1099
        carrying DIV, INT and B summaries on one page, which is what every
        Schwab/Fidelity/Vanguard client sends. Answering that with the single
        highest-scoring label is not a near-miss, it is a wrong answer that
        closes a request: matching accepts "1099-INT" against a core-income
        bundle, reconcile marks it Received, and the 1099-B nobody has yet is
        never asked for again.
        """
        return len(self.forms) > 1

    @property
    def extractable(self) -> bool:
        # A multi-form page is already excluded here and needs no test of its
        # own: `classify_text` gives every "Several forms:" verdict `key=None`,
        # because there IS no single extraction map for a page of three forms --
        # reading it with one form's map would key another form's figures onto
        # the wrong lines, which is worse than not reading it, because the
        # result looks like data. A `not self.multi` clause was written here
        # first and removed: it could never fire, and a check that cannot fire
        # reads to the next person as if it were load-bearing.
        return self.key is not None

    @property
    def classified(self) -> bool:
        """True when we identified what this document IS.

        Both non-verdicts are excluded, and they are different non-verdicts:
        "unclassified" is *we read it and did not recognise it*, "not downloaded"
        is *we never saw it*. A comment here once claimed the second was already
        excluded because its method differed from the first -- it was not, and
        the test caught it: a placeholder counted as classified and would have
        been handed to reconcile.
        """
        return self.method not in _NOT_A_VERDICT


# A tax year printed on a form. Standalone only: an EIN (34-2026112), an account
# number or a ZIP+4 can all carry four digits that read like a year, so a run
# glued to more digits or to a dash is not one.
_YEAR = re.compile(r"(?<![\d-])(19[9]\d|20[0-4]\d)(?![\d-])")

# The window a tax document can plausibly belong to. Wide on purpose -- prior-year
# returns, amended filings and carryforward schedules are ordinary work -- but
# not so wide that a founding date in a letterhead ("Established 1887") counts.
YEAR_FLOOR = 1990
YEAR_CEILING = 2049


def document_year(text: str) -> int | None:
    """The tax year this document is for, or None when it cannot be read.

    NONE MEANS UNKNOWN AND UNKNOWN MEANS UNKNOWN. It never means "probably this
    year". Nothing downstream may treat a None as a match or as a mismatch --
    see :func:`wrong_year` for the asymmetry that depends on it.

    Real forms print their year more than once: in the header, in the footer
    rule, sometimes in a box. A stray reference to a different year ("corrected
    from your 2025 filing") appears once. So the most repeated year wins, and a
    genuine tie is unknown rather than whichever happened to be scanned first --
    picking one there would be a coin toss wearing a fact's clothes.

    Measured 30 Aug 2026: without this, a 2019 W-2 from a job the client left
    classified HIGH and filed as "W-2 (2).pdf" beside the current one, and could
    close this year's W-2 request.
    """
    if not text:
        return None
    counts: dict[int, int] = {}
    for m in _YEAR.finditer(text):
        year = int(m.group(1))
        if YEAR_FLOOR <= year <= YEAR_CEILING:
            counts[year] = counts.get(year, 0) + 1
    if not counts:
        return None
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return None            # a tie is not evidence
    return ranked[0][0]


def wrong_year(document: int | None, engagement: int | None) -> bool:
    """True only when BOTH years are known and they differ.

    The asymmetry is the whole design. A year we could not read blocks nothing:
    most documents read fine, and a pipeline that refused everything it was
    unsure of would hand the whole packet back to the preparer, which is the job
    it exists to remove. A year we DID read, which differs, is the one case
    where we know enough to be sure something is wrong -- and there it refuses.
    """
    return (document is not None and engagement is not None
            and document != engagement)


# A neutral verdict for files nothing matched.
UNCLASSIFIED = Classification(
    label="Unclassified", key=None, code="DOC",
    confidence="UNCERTAIN", method="unclassified",
    evidence="no form fields, text, filename hint, or vision match",
)


# How much of the winner's score a second form must reach before the document is
# read as several forms rather than one. Chosen from measurement, not taste --
# see the note at its use. Genuine multi-form documents cluster near 0.9; a
# passing mention of another form clusters near 0.3.
MULTI_SHARE = 0.6


# A file whose bytes are not on this disk. DISTINCT FROM UNCLASSIFIED ON PURPOSE.
#
# OneDrive's Files On-Demand leaves PLACEHOLDERS: entries that appear in the
# folder listing, report a size in Explorer, and have no bytes locally. Measured
# 30 Aug 2026, and predicted in the collection design before that: a zero-byte
# PDF came back "Unclassified", silently, and was filed. A document that arrived,
# was processed, and vanished into a folder nobody reads.
#
# "We looked and could not identify it" and "we never saw it" are different facts
# with different remedies -- the first wants a new keyword, the second wants you
# to right-click and choose Always keep on this device. In a folder listing they
# are the same grey word unless we make them different here.
#
# `method` is not "unclassified", so `classified` is False and nothing downstream
# counts this as a document that arrived. That is the property reconcile keys on.
NOT_DOWNLOADED = Classification(
    label="Not downloaded", key=None, code="DOC",
    confidence="UNCERTAIN", method="not downloaded",
    evidence="the file has no bytes on this disk -- it is a placeholder, not a "
             "document. Download it (right-click, Always keep on this device) "
             "and run this again.",
)


def _has_bytes(path: Path) -> bool:
    """True when this file's contents are actually on this disk.

    Zero bytes ONLY. A small real PDF is a real PDF, and a size threshold here
    would start refusing documents on a guess about how big a form ought to be.

    ON WINDOWS a placeholder can also be a nonzero-size file with
    FILE_ATTRIBUTE_OFFLINE or FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS set, which
    this does not yet check -- st_file_attributes exists only on Windows and
    there is no Windows machine in the build environment to prove it against.
    NOT CLAIMED AS COVERED (S28). What is proven is the zero-byte case, which is
    the one that was actually measured.
    """
    try:
        return path.stat().st_size > 0
    except OSError:
        return False        # gone mid-sync is the same situation as never pulled


class DocumentClassifier:
    """Classifies a file by reading it, cheapest-and-most-exact signal first."""

    def __init__(self, doc_types: list[DocType], *, has_key: bool | None = None,
                 text_threshold: int = DEFAULT_TEXT_THRESHOLD,
                 close_delta: int = DEFAULT_CLOSE_DELTA) -> None:
        self.doc_types = doc_types
        self.text_threshold = text_threshold
        self.close_delta = close_delta
        # "has_key" gates the cloud vision rung; default to the opt-in posture so a
        # stray API key in the environment never silently enables cloud calls.
        if has_key is None:
            from satc.settings import cloud_vision_enabled
            has_key = cloud_vision_enabled()
        self.has_key = has_key
        # Optional local-OCR text provider (path -> text); set by load_classifier
        # when Tesseract is available, so scans can be classified locally.
        self.ocr_text_provider: Any = None
        # PAGE BY PAGE where the file has pages. The whole-file provider above
        # stays for images and for tests that hand over plain text; this one is
        # what lets a scan be judged by the same page rule as a text PDF.
        self.ocr_page_text_provider: Any = None

    # -- construction -----------------------------------------------------
    @classmethod
    def from_config(cls, config_root: Path | None = None, *, has_key: bool | None = None
                    ) -> DocumentClassifier:
        registry = load_classification(config_root)
        doc_types: list[DocType] = []
        cache: dict[str, set[str]] = {}
        for entry in registry.get("doc_types", []):
            key = entry.get("key")
            markers = cls._field_markers_for(key, config_root, cache) if key else set()
            doc_types.append(DocType(
                key=key,
                label=entry["label"],
                code=entry.get("code", entry["label"]),
                filename_hints=[h.lower() for h in entry.get("filename_hints", [])],
                keywords=cls._parse_keywords(entry),
                threshold=int(entry.get("threshold", 0)),
                field_markers=markers,
            ))
        return cls(doc_types, has_key=has_key,
                   text_threshold=int(registry.get("text_threshold", DEFAULT_TEXT_THRESHOLD)),
                   close_delta=int(registry.get("close_delta", DEFAULT_CLOSE_DELTA)))

    @staticmethod
    def _parse_keywords(entry: dict[str, Any]) -> list[tuple[str, int]]:
        """Read weighted ``keywords`` ([phrase, weight] or {phrase: weight}).

        Falls back to legacy ``title_markers`` at a default weight so a type that
        only lists markers still classifies (each marker alone clears threshold).
        """
        out: list[tuple[str, int]] = []
        raw = entry.get("keywords")
        if isinstance(raw, dict):
            raw = list(raw.items())
        for item in raw or []:
            phrase, weight = (item[0], item[1]) if isinstance(item, (list, tuple)) else (item, DEFAULT_TEXT_THRESHOLD)
            out.append((_normalize_text(phrase), int(weight)))
        for marker in entry.get("title_markers", []):
            out.append((_normalize_text(marker), DEFAULT_TEXT_THRESHOLD))
        return out

    @staticmethod
    def _field_markers_for(key: str, config_root: Path | None,
                           cache: dict[str, set[str]]) -> set[str]:
        """Normalized AcroForm fingerprints from an extraction config's field paths."""
        if key in cache:
            return cache[key]
        markers: set[str] = set()
        try:
            cfg = load_extraction_map(key, config_root)
            for spec in cfg.get("fields", []):
                for candidate in (spec.get("field_path"), spec.get("pdf_field")):
                    if candidate:
                        markers.add(_normalize(candidate))
        except Exception:  # noqa: BLE001 - a missing map just means no field signal
            markers = set()
        cache[key] = markers
        return markers

    # -- classify ---------------------------------------------------------
    def classify_path(self, source: str | Path) -> Classification:
        path = Path(source)
        # BEFORE ANY RUNG. Every reader below would "succeed" on a placeholder by
        # finding nothing in it, and the verdict would be indistinguishable from
        # a document we read and did not recognise.
        if not _has_bytes(path):
            return NOT_DOWNLOADED
        is_pdf = path.suffix.lower() == ".pdf"

        if is_pdf:
            by_fields = self._by_form_fields(path)
            if by_fields is not None:
                return by_fields
            by_text = self._by_text(path)
            if by_text is not None:
                return by_text

        by_ocr = self._by_ocr(path)          # scans / images / text-less PDFs (local OCR)
        if by_ocr is not None:
            return by_ocr

        by_name = self._by_filename(path.name)
        if by_name is not None:
            return by_name

        if self.has_key:
            by_vision = self._by_vision(path)
            if by_vision is not None:
                return by_vision

        return UNCLASSIFIED

    def _by_ocr(self, path: Path) -> Classification | None:
        """OCR, page by page where we can, judged by the same rule as the text.

        THE PROVIDER WAS POINTED AT PAGE 1 (`ocr_document_text(p, 1)`, with the
        comment "first page is enough for typing"). On a scanned IRS document
        page 1 is the notice, so this rung reproduced the very wrong answer the
        text rung had just been fixed for -- and did it on TRUE SCANS, where no
        cheaper rung is left to catch it.
        """
        if self.ocr_page_text_provider is not None and path.suffix.lower() == ".pdf":
            try:
                from pypdf import PdfReader

                count = len(PdfReader(str(path)).pages)
            except Exception:  # noqa: BLE001 - unreadable => try the whole-file rung
                count = 0
            if count:
                from satc.ingest.pages import OCR_PAGE_LIMIT, is_guidance

                def scanned() -> Iterator[tuple[int, str]]:
                    for number in range(1, min(count, OCR_PAGE_LIMIT) + 1):
                        try:
                            text = self.ocr_page_text_provider(str(path), number)
                        except Exception:  # noqa: BLE001 - a bad page is not the file
                            continue
                        if not is_guidance(text):
                            yield number, text

                # STOP AT THE FIRST PAGE THAT NAMES THE FORM, which the text
                # rung does not do. Rasterising a page at 300 dpi and running
                # Tesseract over it is thousands of times the cost of reading a
                # text layer, and reading every page turned the test suite from
                # minutes into hours.
                #
                # WHAT THIS GIVES UP, said plainly: a SCANNED consolidated
                # statement that puts each form on its own page is identified by
                # the first of them. The text rung still reads all of it, and a
                # real consolidated 1099 is a generated PDF with a text layer,
                # not a scan -- so this is the cheap end of a document class
                # that barely exists. The failure it leaves is an unclosed
                # request, not a wrongly closed one.
                return self._verdict_over(scanned(), "ocr", stop_when_found=True)

        if self.ocr_text_provider is None:
            return None
        try:
            text = self.ocr_text_provider(str(path))
        except Exception:  # noqa: BLE001 - OCR unavailable / failed => fall through
            return None
        return self.classify_text(text, method="ocr")

    # -- individual signals ----------------------------------------------
    def _by_form_fields(self, path: Path) -> Classification | None:
        names = self._acroform_names(path)
        if not names:
            return None
        best, best_score = None, 0
        for dt in self.doc_types:
            if not dt.field_markers:
                continue
            score = len(names & dt.field_markers)
            if score > best_score:
                best, best_score = dt, score
        if best is not None and best_score >= 2:
            # A fillable form is identified by its field NAMES, which carry no
            # year -- so read the year off the printed page as every other rung
            # does. Cheap (the text layer is already there on a fillable PDF)
            # and it keeps the year available on the free, exact path rather
            # than only on the text one.
            return Classification(best.label, best.key, best.code, "HIGH", "form fields",
                                  f"matched {best_score} fillable form fields",
                                  tax_year=document_year(self._page_text(path)))
        return None

    def _by_text(self, path: Path) -> Classification | None:
        """Every form page judged on its own, and the verdicts unioned.

        NOT one score over the concatenation, and NOT the best-scoring page.
        Both were tried and measured on 31 Aug 2026:

        * **Concatenating** the pages adds up evidence a page at a time, so a
          form that merely REFERS to others collects their keywords across the
          document and comes back as several forms.
        * **The best-scoring page** compares scores that are not on one scale --
          the per-type ceilings run from 17 to 38 against a shared threshold of
          6 -- so it favours high-ceiling types; and it silently answers a
          consolidated 1099 with whichever single form scored highest, which is
          the partial answer :attr:`Classification.multi` exists to prevent.

        Judging each page against its own thresholds has neither problem, and it
        catches the consolidated statement that puts each form on its OWN page,
        which no single-text rung could ever see.
        """
        from satc.ingest.pages import CLASSIFY_PAGE_LIMIT, form_pages

        return self._verdict_over(form_pages(path)[:CLASSIFY_PAGE_LIMIT], "text")

    def _verdict_over(self, pages: Iterable[tuple[int, str]], method: str,
                      *, stop_when_found: bool = False) -> Classification | None:
        """One verdict from many pages, each judged on its own.

        ``stop_when_found`` is for the OCR rung, where reading one more page
        costs seconds rather than milliseconds -- see :meth:`_by_ocr`.
        """
        labels: list[str] = []
        confidences: list[str] = []
        years: list[int] = []
        evidence: list[str] = []
        for number, text in pages:
            verdict = self.classify_text(text, method=method)
            if verdict is None:
                continue
            for label in (verdict.forms or (verdict.label,)):
                if label not in labels:
                    labels.append(label)
            confidences.append(verdict.confidence)
            if verdict.tax_year:
                years.append(verdict.tax_year)
            evidence.append(f"p{number}: {verdict.evidence}")
            if stop_when_found:
                break

        if not labels:
            return None

        # THE YEAR IS A VOTE, not the first answer. A guidance page is already
        # gone, but a form page may print a neighbouring revision date; the year
        # the document repeats is the document's.
        year = max(set(years), key=years.count) if years else None

        if len(labels) == 1:
            best = next(dt for dt in self.doc_types if dt.label == labels[0])
            worst = min(confidences, key=_CONFIDENCE_ORDER.index)
            return Classification(best.label, best.key, best.code, worst, method,
                                  "; ".join(evidence), tax_year=year)

        return Classification(
            label="Several forms: " + ", ".join(labels), key=None, code="MULTI",
            confidence="HIGH", method=method,
            evidence="; ".join(evidence), forms=tuple(labels), tax_year=year)

    def classify_text(self, text: str, *, method: str = "text") -> Classification | None:
        """Weighted-keyword scoring over document text (shared by text + OCR rungs).

        Each type's keywords carry weights (strong identifiers high, generic words
        low) so no single weak word can classify alone. The winner must clear its
        threshold; if a runner-up is also strong or within ``close_delta``, the
        result is downgraded to MEDIUM — the pipeline feeds a human, so when it is
        unsure it says so rather than guessing.
        """
        if not text or not text.strip():
            return None
        norm = _normalize_text(text)
        year = document_year(text)      # RAW text: _normalize_text folds the
                                        # punctuation the standalone-run rule needs
        scored: list[tuple[int, int, DocType]] = []
        for dt in self.doc_types:
            hits = [w for phrase, w in dt.keywords if phrase and phrase in norm]
            if len(hits) >= MIN_SIGNALS:
                scored.append((sum(hits), dt.threshold or self.text_threshold, dt))
        qualified = [(s, dt) for s, thr, dt in scored if s >= thr]
        if not qualified:
            return None
        qualified.sort(key=lambda x: x[0], reverse=True)
        best_score, best = qualified[0]
        # A runner-up that resolves to the *same* extraction key (e.g. the generic
        # "Schedule K-1" vs the specific 1120-S entry) agrees with the winner — it is
        # not a competing interpretation, so it never makes the result ambiguous.
        # Every OTHER type that cleared its own threshold on its own evidence.
        # Types that resolve to the same extraction key (the generic "Schedule
        # K-1" beside the specific 1120-S entry) agree with the winner rather
        # than competing, so they never count as a second form.
        # A RUNNER-UP AGREES WITH THE WINNER when it is the same form under
        # another entry (the generic "Schedule K-1" beside the specific 1120-S
        # one), and that is what this filter is for. It compared `key`, and
        # `key` is ALSO the flag for "filed, not extracted" -- so all fourteen
        # non-extractable types shared `key=None` and were read as agreeing with
        # each other. A document that is genuinely a 1099-B *and* a 1099-MISC
        # could never be reported as several forms. Compare on identity.
        others = [(s, dt) for s, dt in qualified[1:] if dt.label != best.label
                  and not (dt.key is not None and dt.key == best.key)]
        # A second form must clear its own threshold AND score a real SHARE of
        # the winner's. Clearing the floor alone is not enough: measured on the
        # real keyword weights, 30 Aug 2026 --
        #
        #   consolidated 1099 (DIV + INT + B)   1099-INT 16 vs 1099-DIV 15   0.94
        #   terse "1099-INT ... 1099-DIV"       1099-DIV 18 vs 1099-INT 16   0.89
        #   a W-2 that MENTIONS 1099-R          W-2      27 vs 1099-R   9    0.33
        #
        # -- so the floor-only rule called that last one "Several forms: W-2,
        # 1099-R", which is a plain W-2 and one of the commonest documents there
        # is. A form the document is ABOUT scores comparably to the winner; a
        # form it merely refers to does not. MULTI_SHARE sits between the two
        # clusters with margin on both sides.
        strong = [dt.label for s, dt in others
                  if s >= (dt.threshold or self.text_threshold)
                  and s >= best_score * MULTI_SHARE]

        if strong:
            # SEVERAL FORMS, NOT AN UNSURE ONE. Each of these cleared the bar
            # this classifier sets for "this document is a <form>" -- so the
            # honest reading is that the page carries all of them. See
            # Classification.multi for why answering with just the best one is
            # a money bug rather than an imprecision.
            names = [best.label, *strong]
            return Classification(
                label="Several forms: " + ", ".join(names),
                key=None, code="MULTI", confidence="HIGH", method=method,
                evidence=f"{len(names)} forms each cleared their threshold "
                         f"(best {best_score})",
                forms=tuple(names), tax_year=year,
            )

        runner = others[0][0] if others else 0
        ambiguous = runner > 0 and best_score - runner <= self.close_delta
        conf = "MEDIUM" if ambiguous else "HIGH"
        ev = f"text score {best_score}" + (f" (runner-up {runner})" if runner else "")
        return Classification(best.label, best.key, best.code, conf, method, ev,
                              tax_year=year)

    def _by_filename(self, name: str) -> Classification | None:
        low = name.lower()
        for dt in self.doc_types:
            for hint in dt.filename_hints:
                if hint in low:
                    return Classification(dt.label, dt.key, dt.code, "LOW", "filename",
                                          f"file name contains “{hint}”")
        return None

    def _by_vision(self, path: Path) -> Classification | None:  # pragma: no cover - needs a key
        """Last resort: ask the vision model to name the form (true scans only)."""
        try:
            from satc.ingest.readers.vision import VisionDocumentReader

            labels = [dt.label for dt in self.doc_types]
            choice = VisionDocumentReader.classify_form(str(path), labels)
        except Exception:  # noqa: BLE001 - never let a model error crash sorting
            return None
        for dt in self.doc_types:
            if dt.label == choice:
                return Classification(dt.label, dt.key, dt.code, "MEDIUM", "vision",
                                      "identified by vision model")
        return None

    # -- low-level readers (guarded; never raise) ------------------------
    @staticmethod
    def _acroform_names(path: Path) -> set[str]:
        try:
            from pypdf import PdfReader

            fields = PdfReader(str(path)).get_fields() or {}
            return {_normalize(name) for name in fields}
        except Exception:  # noqa: BLE001 - not a fillable PDF / pypdf unavailable
            return set()

    @staticmethod
    def _page_text(path: Path) -> str:
        """The document's OWN text -- guidance pages dropped, several pages deep.

        THIS READ PAGE 1 AND NOTHING ELSE, and page 1 of a real IRS blank is a
        notice about which revision to use whose worked example is 1099-NEC. A
        1098-T, a 1099-G, a 1099-MISC and a 1099-R all came back "1099-NEC" at
        HIGH confidence off that one page. See :mod:`satc.ingest.pages`.
        """
        from satc.ingest.pages import form_text

        return form_text(path)


def load_classifier(config_root: Path | None = None, *, has_key: bool | None = None
                    ) -> DocumentClassifier:
    """Convenience builder used by intake and the sorter.

    Wires in the local-OCR text providers when Tesseract is available, so scanned
    documents can be classified on-machine.

    IT USED TO PASS `page=1` HERE, with the comment "first page is enough for
    typing". That was the whole classifier bug in one argument: page 1 of a real
    IRS document is a notice, and this rung is the one that runs on true scans,
    where nothing cheaper is left to disagree with it.
    """
    clf = DocumentClassifier.from_config(config_root, has_key=has_key)
    from satc.settings import ocr_enabled

    if ocr_enabled():
        from satc.ingest.ocr import ocr_document_text, ocr_pdf_page_text

        clf.ocr_text_provider = ocr_document_text          # every page, not the first
        clf.ocr_page_text_provider = ocr_pdf_page_text
    return clf
