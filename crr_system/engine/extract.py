"""Extraction engine: pulls structured rows out of ingested documents.

Type A: regulatory/policy thresholds  -> metric, value, basis, citation,
        agency tag(s), effective/rescinded dates.
Type B: credit-memo assertions        -> borrower, facility, ratios, grade,
        repayment, guarantor, covenants, collateral, assumptions.

Design rules:
  * Every row carries the verbatim sentence it came from plus a page/section
    anchor. No span, no row.
  * Conservative: ambiguity lowers confidence and routes to staging for human
    resolution; the engine never guesses. Thresholds whose current status
    cannot be verified are recorded as Coverage Gap rows, not asserted.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from .ingest import IngestedDocument, detect_section
from .schema import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    ROW_TYPE_A,
    ROW_TYPE_B,
    STATUS_COVERAGE_GAP,
    ExtractedRow,
    SourceAnchor,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_SENT_SPLIT = re.compile(r"(?<=[.;])\s+(?=[A-Z(])|\n(?=[A-Z•\-])")

_MONTHS = (
    "January February March April May June July August September October "
    "November December".split()
)
_DATE_RE = re.compile(
    r"(" + "|".join(_MONTHS) + r")\s+(\d{1,2}),?\s+(\d{4})|"
    r"(" + "|".join(_MONTHS) + r")\s+(\d{4})|"
    r"(\d{4})-(\d{2})-(\d{2})"
)


def sentences_with_offsets(text: str) -> List[Tuple[int, str]]:
    """Split text into sentence-ish units, keeping each unit's char offset."""
    out, last = [], 0
    for m in _SENT_SPLIT.finditer(text):
        chunk = text[last : m.start()].strip()
        if chunk:
            out.append((last + (len(text[last : m.start()]) - len(text[last : m.start()].lstrip())), chunk))
        last = m.end()
    tail = text[last:].strip()
    if tail:
        out.append((last + (len(text[last:]) - len(text[last:].lstrip())), tail))
    return out


def parse_date(text: str) -> Optional[dt.date]:
    m = _DATE_RE.search(text)
    if not m:
        return None
    if m.group(1):
        return dt.date(int(m.group(3)), _MONTHS.index(m.group(1)) + 1, int(m.group(2)))
    if m.group(4):
        return dt.date(int(m.group(5)), _MONTHS.index(m.group(4)) + 1, 1)
    return dt.date(int(m.group(6)), int(m.group(7)), int(m.group(8)))


_AGENCY_PATTERNS = [
    ("OCC", re.compile(r"\bOCC\b|Office of the Comptroller", re.I)),
    ("FRB", re.compile(r"\bFRB\b|Federal Reserve|Board of Governors", re.I)),
    ("FDIC", re.compile(r"\bFDIC\b|Federal Deposit Insurance", re.I)),
    ("CFPB", re.compile(r"\bCFPB\b|Consumer Financial Protection", re.I)),
]


def detect_agencies(text: str) -> List[str]:
    flat = re.sub(r"\s+", " ", text)
    return [name for name, pat in _AGENCY_PATTERNS if pat.search(flat)]


# ---------------------------------------------------------------------------
# Type A: regulatory / policy thresholds
# ---------------------------------------------------------------------------

# (metric label, unit, sentence-must-match pattern, value-capture pattern)
_THRESHOLD_PATTERNS = [
    (
        "Total Debt / EBITDA",
        "x",
        re.compile(r"total\s+debt[\s/]+(to\s+)?EBITDA|total\s+leverage", re.I),
        re.compile(r"(\d+(?:\.\d+)?)\s*(?:x|times|X)\b"),
    ),
    (
        "Senior Debt / EBITDA",
        "x",
        re.compile(r"senior\s+debt[\s/]+(to\s+)?EBITDA|senior\s+secured\s+leverage", re.I),
        re.compile(r"(\d+(?:\.\d+)?)\s*(?:x|times|X)\b"),
    ),
    (
        "Repayment Capacity (base-case de-lever)",
        "%/yrs",
        re.compile(r"repay(?:ment)?\b.{0,160}(?:five|5)\D{0,5}(?:to|-)\D{0,5}(?:seven|7)\s*years", re.I | re.S),
        re.compile(r"(\d{1,3})\s*(?:percent|%)"),
    ),
    (
        "CLD Concentration / Total Risk-Based Capital",
        "%",
        re.compile(r"(construction|land\s+development|CLD)\b.{0,200}capital", re.I | re.S),
        re.compile(r"(\d{2,3})\s*(?:percent|%)"),
    ),
    (
        "Total CRE / Total Risk-Based Capital",
        "%",
        re.compile(r"total\s+(?:non[- ]owner[- ]occupied\s+)?(?:commercial\s+real\s+estate|CRE)\b.{0,200}capital", re.I | re.S),
        re.compile(r"(\d{3})\s*(?:percent|%)"),
    ),
    (
        "CRE 36-Month Growth Trigger",
        "%",
        re.compile(r"(?:36\s*months?|thirty[- ]six\s*months?|prior\s+three\s+years)", re.I),
        re.compile(r"(\d{2,3})\s*(?:percent|%)"),
    ),
    (
        "Minimum DSCR",
        "x",
        re.compile(r"(?:minimum\s+)?debt\s+service\s+coverage|(?<![A-Za-z])DSCR", re.I),
        re.compile(r"(\d\.\d{1,2})\s*x?\b"),
    ),
    (
        "Maximum LTV",
        "%",
        re.compile(r"loan[- ]to[- ]value|(?<![A-Za-z])LTV", re.I),
        re.compile(r"(\d{2,3})\s*(?:percent|%)"),
    ),
    (
        "Maximum Advance Rate (Eligible AR)",
        "%",
        re.compile(r"advance\s+rate.{0,80}(?:accounts\s+receivable|receivables|AR)\b", re.I | re.S),
        re.compile(r"(\d{2})\s*(?:percent|%)"),
    ),
    (
        "Maximum Advance Rate (Eligible Inventory)",
        "%",
        re.compile(r"advance\s+rate.{0,80}inventory", re.I | re.S),
        re.compile(r"(\d{2})\s*(?:percent|%)"),
    ),
]

_HEDGE_RE = re.compile(r"raises?\s+concern|may\s+be|generally|critici[sz]ed|heightened", re.I)


def extract_thresholds(
    doc: IngestedDocument,
    *,
    citation: str = "",
    agencies: Optional[List[str]] = None,
    effective_date: Optional[dt.date] = None,
    status_verified: bool = True,
) -> List[ExtractedRow]:
    """Extract Type A threshold rows from a regulatory/policy document.

    If the document is interagency, one row is emitted per issuing agency so
    that later rescissions can apply to one agency without touching another.
    If status_verified is False, rows are marked Coverage Gap instead of
    asserting current applicability.
    """
    full = doc.full_text()
    doc_agencies = agencies or detect_agencies(full[:4000]) or ["Internal"]
    doc_effective = effective_date or parse_date(full[:1500])

    rows: List[ExtractedRow] = []
    seen = set()  # (metric, value, page) dedupe
    for page in doc.pages:
        for offset, sent in sentences_with_offsets(page.text):
            flat = re.sub(r"\s+", " ", sent)
            for metric, unit, must, valpat in _THRESHOLD_PATTERNS:
                kw = must.search(flat)
                if not kw:
                    continue
                # Prefer the value nearest AFTER the metric phrase ("DSCR of
                # 1.25x"); fall back to the nearest value before it ("in
                # excess of 6.0x Total Debt to EBITDA"). A second distinct
                # candidate inside the proximity window means the sentence is
                # ambiguous -> low confidence, reviewer resolves in staging.
                inside = [m for m in valpat.finditer(flat, kw.start(), kw.end())]
                after = [m for m in valpat.finditer(flat, kw.end())]
                before = [m for m in valpat.finditer(flat[: kw.start()])]
                if inside:
                    value = inside[0].group(1)
                    window = [m.group(1) for m in inside]
                elif after:
                    value = after[0].group(1)
                    window = [m.group(1) for m in after if m.start() - kw.end() <= 40]
                elif before:
                    value = before[-1].group(1)
                    window = [m.group(1) for m in before if kw.start() - m.end() <= 40]
                else:
                    continue
                key = (metric, value, page.number)
                if key in seen:
                    continue
                seen.add(key)
                ambiguous = len(set(window)) > 1
                confidence = (
                    CONFIDENCE_LOW
                    if ambiguous
                    else (CONFIDENCE_HIGH if _HEDGE_RE.search(flat) or unit in ("%", "x") else CONFIDENCE_MEDIUM)
                )
                basis = "Supervisory expectation" if _HEDGE_RE.search(flat) else "Stated threshold"
                note = (
                    f"Multiple candidate values {sorted(set(values))} in source sentence; "
                    "reviewer must select." if ambiguous else ""
                )
                for agency in doc_agencies:
                    rows.append(
                        ExtractedRow(
                            row_type=ROW_TYPE_A,
                            metric=metric,
                            proposed_value=value,
                            unit=unit,
                            basis=basis,
                            source_span=sent[:500],
                            anchor=SourceAnchor(
                                document=doc.name,
                                page=page.number,
                                section=detect_section(page.text, offset),
                                char_start=offset,
                                char_end=offset + len(sent),
                            ),
                            confidence=confidence if status_verified else CONFIDENCE_LOW,
                            status="Staged" if status_verified else STATUS_COVERAGE_GAP,
                            agency=agency,
                            citation=citation or doc.name,
                            effective_date=doc_effective,
                            notes=note
                            if status_verified
                            else (note + " Current status unverified - coverage gap.").strip(),
                        )
                    )
    return rows


# ---------------------------------------------------------------------------
# Type A supplement: rescission notices
# ---------------------------------------------------------------------------

@dataclass
class RescissionNotice:
    target_keywords: str        # text identifying the guidance being rescinded
    agencies: List[str]
    rescinded_date: Optional[dt.date]
    source_span: str
    anchor: SourceAnchor


_RESCIND_RE = re.compile(r"rescind(?:s|ed|ing)?", re.I)


def extract_rescissions(doc: IngestedDocument) -> List[RescissionNotice]:
    """Find sentences announcing a rescission, with agency tags and dates."""
    notices = []
    for page in doc.pages:
        for offset, sent in sentences_with_offsets(page.text):
            if not _RESCIND_RE.search(sent):
                continue
            agencies = detect_agencies(sent)
            if not agencies:
                continue
            quoted = re.findall(r"[“\"]([^”\"]{8,120})[”\"]", sent)
            target = quoted[0] if quoted else sent
            notices.append(
                RescissionNotice(
                    target_keywords=target,
                    agencies=agencies,
                    rescinded_date=parse_date(sent) or parse_date(page.text[:600]),
                    source_span=sent[:500],
                    anchor=SourceAnchor(
                        document=doc.name,
                        page=page.number,
                        section=detect_section(page.text, offset),
                        char_start=offset,
                        char_end=offset + len(sent),
                    ),
                )
            )
    return notices


# ---------------------------------------------------------------------------
# Type B: credit-memo / underwriting assertions
# ---------------------------------------------------------------------------

_LABELED_FIELDS = [
    ("Borrower", "borrower", re.compile(r"^Borrower\s*[:\-]\s*(.+)$", re.I | re.M)),
    ("Facility", "facility", re.compile(r"^Facilit(?:y|ies)\s*[:\-]\s*(.+)$", re.I | re.M)),
    ("Assigned Risk Grade", "grade", re.compile(r"^(?:Assigned\s+)?Risk\s+(?:Grade|Rating)\s*[:\-]\s*(.+)$", re.I | re.M)),
    ("Guarantor", "guarantor", re.compile(r"^Guarantors?\s*[:\-]\s*(.+)$", re.I | re.M)),
    ("Collateral", "collateral", re.compile(r"^Collateral\s*[:\-]\s*(.+)$", re.I | re.M)),
]

_RATIO_ASSERTIONS = [
    ("Total Debt / EBITDA (asserted)", "x", re.compile(r"total\s+(?:debt|leverage)\s*(?:/|to)?\s*EBITDA[^.\n]{0,60}?(\d+(?:\.\d+)?)\s*x", re.I)),
    ("Senior Debt / EBITDA (asserted)", "x", re.compile(r"senior\s+(?:debt|leverage)\s*(?:/|to)?\s*EBITDA[^.\n]{0,60}?(\d+(?:\.\d+)?)\s*x", re.I)),
    ("DSCR (asserted)", "x", re.compile(r"(?:DSCR|debt\s+service\s+coverage(?:\s+ratio)?)[^.\n]{0,60}?(\d+(?:\.\d+)?)\s*x", re.I)),
    ("Fixed Charge Coverage (asserted)", "x", re.compile(r"fixed[- ]charge\s+coverage[^.\n]{0,60}?(\d+(?:\.\d+)?)\s*x", re.I)),
    ("Interest Coverage (asserted)", "x", re.compile(r"interest\s+coverage[^.\n]{0,60}?(\d+(?:\.\d+)?)\s*x", re.I)),
    ("LTV (asserted)", "%", re.compile(r"(?:LTV|loan[- ]to[- ]value)[^.\n]{0,60}?(\d{1,3}(?:\.\d+)?)\s*%", re.I)),
    ("Debt Yield (asserted)", "%", re.compile(r"debt\s+yield[^.\n]{0,60}?(\d{1,2}(?:\.\d+)?)\s*%", re.I)),
    ("Current Ratio (asserted)", "x", re.compile(r"current\s+ratio[^.\n]{0,60}?(\d+(?:\.\d+)?)\s*x?", re.I)),
    ("Global DSCR (asserted)", "x", re.compile(r"global\s+(?:cash\s+flow|DSCR)[^.\n]{0,80}?(\d+(?:\.\d+)?)\s*x", re.I)),
]

# "Sentence body" that does not stop at decimal points (1.20x, $4.5 million).
_BODY = r"(?:[^.\n]|\.(?=\d))*\."

_NARRATIVE_PATTERNS = [
    ("Primary Repayment Source", "repayment", re.compile(r"primary\s+(?:source\s+of\s+)?repayment" + _BODY, re.I)),
    ("Secondary Repayment Source", "repayment", re.compile(r"secondary\s+(?:source\s+of\s+)?repayment" + _BODY, re.I)),
    ("Guarantor Support", "guarantor", re.compile(r"(?:personally\s+)?guarant(?:eed|y|ee)" + _BODY, re.I)),
    ("Collateral Description", "collateral", re.compile(r"secured\s+by" + _BODY, re.I)),
    ("Key Assumption / Projection", "assumption", re.compile(
        r"projections?\s+(?:assume|reflect|incorporate)" + _BODY
        + r"|assum(?:es|ing|ption)(?:[^.\n]|\.(?=\d))*?\d+(?:\.\d+)?\s*%" + _BODY, re.I)),
]

_COVENANT_RE = re.compile(
    r"(?:maximum|minimum|max\.?|min\.?)\s+[A-Za-z /]{3,40}\s+of\s+\d+(?:\.\d+)?\s*[x%]|"
    r"covenants?\s+(?:include|require)" + _BODY,
    re.I,
)


def _find_anchor(doc: IngestedDocument, needle: str) -> Optional[SourceAnchor]:
    for page in doc.pages:
        pos = page.text.find(needle[:80])
        if pos >= 0:
            return SourceAnchor(
                document=doc.name,
                page=page.number,
                section=detect_section(page.text, pos),
                char_start=pos,
                char_end=pos + len(needle),
            )
    return None


def extract_assertions(doc: IngestedDocument, *, borrower_hint: str = "") -> List[ExtractedRow]:
    """Extract Type B rows: what the credit memo asserts, for independent check."""
    rows: List[ExtractedRow] = []
    full = doc.full_text()

    borrower = borrower_hint
    m = _LABELED_FIELDS[0][2].search(full)
    if m:
        borrower = m.group(1).strip()

    def add(metric, category, value, unit, span, confidence=CONFIDENCE_HIGH, note=""):
        anchor = _find_anchor(doc, span)
        if anchor is None:
            return
        rows.append(
            ExtractedRow(
                row_type=ROW_TYPE_B,
                metric=metric,
                proposed_value=value.strip()[:300],
                unit=unit,
                basis="Asserted in credit file",
                source_span=span.strip()[:500],
                anchor=anchor,
                confidence=confidence,
                borrower=borrower,
                category=category,
                notes=note,
            )
        )

    for label, category, pat in _LABELED_FIELDS:
        m = pat.search(full)
        if m:
            add(label, category, m.group(1), "text", m.group(0))

    seen_vals = set()
    for metric, unit, pat in _RATIO_ASSERTIONS:
        matches = list(pat.finditer(full))
        if not matches:
            continue
        distinct = {m.group(1) for m in matches}
        m = matches[0]
        conf = CONFIDENCE_HIGH if len(distinct) == 1 else CONFIDENCE_LOW
        note = (
            f"Document states conflicting values {sorted(distinct)}; reviewer must resolve."
            if len(distinct) > 1
            else ""
        )
        if (metric, m.group(1)) in seen_vals:
            continue
        seen_vals.add((metric, m.group(1)))
        span = full[max(0, m.start() - 40) : m.end() + 40].replace("\n", " ")
        add(metric, "ratio", m.group(1), unit, full[m.start() : m.end()], conf, note)

    for metric, category, pat in _NARRATIVE_PATTERNS:
        for m in list(pat.finditer(full))[:3]:
            span = m.group(0).replace("\n", " ").strip()
            if len(span) < 15:
                continue
            add(metric, category, span, "text", m.group(0), CONFIDENCE_MEDIUM)

    for m in list(_COVENANT_RE.finditer(full))[:8]:
        span = m.group(0).replace("\n", " ").strip()
        add("Covenant Term", "covenant", span, "text", m.group(0),
            CONFIDENCE_HIGH if re.search(r"\d", span) else CONFIDENCE_MEDIUM)

    return rows
