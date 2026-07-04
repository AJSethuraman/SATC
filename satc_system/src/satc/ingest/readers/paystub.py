"""Deterministic reader for text-layer paystubs.

Paystubs are the natural input to the withholding estimator: they carry the
per-paycheck figures (gross, federal tax withheld, pre-tax retirement), their
year-to-date columns, and the pay frequency. Like every other reader this emits a
:class:`ReadResult` of labeled source values that flow through the same
staging/confirmation gate, so each figure is reviewed against the source document
before it ever drives an estimate.

The one structural wrinkle versus a W-2/1099 is the **two-column layout**: a line
like ``Federal Income Tax   250.00   3,000.00`` shows the current-period amount
first and the year-to-date amount second. The reader captures both.

Heuristic by nature, so it stays conservative: a money value is taken only when a
strict dollar pattern (comma groups or explicit cents) matches on the label's
line. Free-text (employer) and any inferred pay frequency are flagged uncertain
(staged LOW) so they never auto-confirm — the preparer still confirms.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from satc.ingest.readers.base import ReadResult
from satc.ingest.readers.text_anchor import MONEY

# Canonical source labels this reader emits (what the preparer confirms against
# the document, and what the estimator bridge reads back).
LABEL_PAY_FREQUENCY = "Paystub — Pay frequency"
LABEL_GROSS_CURRENT = "Paystub — Gross pay (current period)"
LABEL_GROSS_YTD = "Paystub — Gross pay (YTD)"
LABEL_FED_WH_CURRENT = "Paystub — Federal income tax withheld (current period)"
LABEL_FED_WH_YTD = "Paystub — Federal income tax withheld (YTD)"
LABEL_RETIREMENT_CURRENT = "Paystub — Pre-tax retirement 401(k)/403(b) (current period)"
LABEL_EMPLOYER = "Paystub — Employer name"


@dataclass(slots=True)
class _MoneySpec:
    anchors: tuple[str, ...]      # label phrases, matched case-insensitively
    current_label: str
    ytd_label: str | None = None  # second money on the line, when the field has a YTD column


_MONEY_SPECS: tuple[_MoneySpec, ...] = (
    _MoneySpec(("gross pay", "gross earnings", "gross wages", "total gross"),
               LABEL_GROSS_CURRENT, LABEL_GROSS_YTD),
    _MoneySpec(("federal income tax", "fed income tax", "federal withholding",
                "fed withholding", "federal tax withheld", "fed w/h", "federal w/h"),
               LABEL_FED_WH_CURRENT, LABEL_FED_WH_YTD),
    _MoneySpec(("401(k)", "401k", "403(b)", "403b", "pre-tax 401",
                "retirement plan", "pretax retirement"),
               LABEL_RETIREMENT_CURRENT, None),
)

# Frequency keywords, most specific first so "semi-monthly" wins over "monthly"
# and "bi-weekly" over "weekly".
_FREQ_WORDS: tuple[tuple[str, str], ...] = (
    ("semi-monthly", "semimonthly"), ("semimonthly", "semimonthly"), ("semi monthly", "semimonthly"),
    ("bi-weekly", "biweekly"), ("biweekly", "biweekly"), ("bi weekly", "biweekly"),
    ("weekly", "weekly"), ("monthly", "monthly"),
)
_FREQ_CONTEXT = ("frequency", "pay period", "pay type", "pay cycle", "period ending")


def _clean_amount(text: str) -> str:
    return text.replace(",", "").replace("$", "").strip()


def _anchor_end(low: str, anchors: tuple[str, ...]) -> int | None:
    """End offset just past the earliest-occurring anchor in ``low``, else None."""
    best: int | None = None
    for anchor in anchors:
        i = low.find(anchor)
        if i >= 0:
            end = i + len(anchor)
            if best is None or end < best:
                best = end
    return best


def _match_freq(text: str) -> str:
    for needle, norm in _FREQ_WORDS:
        if needle in text:
            return norm
    return ""


def _pay_frequency(text: str) -> tuple[str, bool]:
    """Return ``(normalized_frequency, confident)``.

    Confident when the keyword sits on a line that names the frequency (e.g.
    "Pay Frequency: Bi-Weekly"); a bare keyword elsewhere is returned uncertain.
    """
    low = text.lower()
    for line in low.splitlines():
        if any(ctx in line for ctx in _FREQ_CONTEXT):
            found = _match_freq(line)
            if found:
                return found, True
    found = _match_freq(low)
    return (found, False) if found else ("", False)


def _employer(lines: list[str]) -> str:
    """Employer name from an explicitly labeled line (never the EIN line)."""
    for raw in lines:
        if "identification" in raw.lower():
            continue  # avoid "Employer Identification Number: NN-NNNNNNN"
        m = re.search(r"(?:employer(?:\s*name)?|company)\s*[:\-]\s*(.+)", raw, re.IGNORECASE)
        if m:
            return re.split(r"\s{2,}|\t", m.group(1).strip())[0].strip()
    return ""


def _page_text(path: Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:  # noqa: BLE001 - no text layer / unreadable => empty
        return ""


class PaystubReader:
    """Reads per-period and YTD figures from a text-layer paystub."""

    def read(self, source: str) -> ReadResult:
        return self.read_text(_page_text(Path(source)))

    def read_text(self, text: str) -> ReadResult:
        """Core extraction over already-read text (unit-testable, no PDF)."""
        labeled: dict[str, str] = {}
        uncertain: set[str] = set()
        lines = (text or "").splitlines()

        for raw in lines:
            low = raw.lower()
            for spec in _MONEY_SPECS:
                if spec.current_label in labeled:
                    continue  # first occurrence of each field wins
                end = _anchor_end(low, spec.anchors)
                if end is None:
                    continue
                monies = [m.group(1) for m in MONEY.finditer(raw[end:])]
                if not monies:
                    continue
                labeled[spec.current_label] = _clean_amount(monies[0])
                if spec.ytd_label and len(monies) >= 2:
                    labeled[spec.ytd_label] = _clean_amount(monies[1])

        employer = _employer(lines)
        if employer:
            labeled[LABEL_EMPLOYER] = employer
            uncertain.add(LABEL_EMPLOYER)  # free text => review

        freq, confident = _pay_frequency(text or "")
        if freq:
            labeled[LABEL_PAY_FREQUENCY] = freq
            if not confident:
                uncertain.add(LABEL_PAY_FREQUENCY)

        return ReadResult(labeled_fields=labeled, uncertain_labels=uncertain,
                          backend="PaystubReader")
