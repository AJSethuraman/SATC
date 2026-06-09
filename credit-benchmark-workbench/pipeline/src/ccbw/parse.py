"""Parse EDGAR CompanyFacts JSON into clean, deduplicated annual facts.

The messy realities this module owns:

* **Duplicate facts.** CompanyFacts returns every amount from every filing,
  including amendments, so the same (tag, period) appears many times. We
  dedupe on the period identity and keep the most recently *filed* value,
  which makes restatements win over the originally filed number. The
  superseded values are retained on the record for audit.
* **Tag fragmentation.** Different filers tag the same concept differently.
  Tag selection happens per concept via the ordered chains in ``tags.py``;
  the chosen tag is recorded in provenance.
* **Fiscal-year misalignment.** A January-2024 fiscal year end is the same
  economic year as a December-2023 one. Facts are assigned a fiscal-year
  *label*: the calendar year the period ends in, unless it ends January-May,
  in which case the prior year. The raw period dates stay in provenance.
* **Units.** XBRL values are raw units (not thousands). We accept only the
  expected unit key for each concept and surface anything else as a gap
  instead of guessing a scale.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Iterable, Optional

from .tags import CONCEPTS, DURATION, INSTANT, ConceptSpec

ANNUAL_MIN_DAYS = 330
ANNUAL_MAX_DAYS = 400
ANNUAL_FORMS = ("10-K", "10-K/A", "20-F", "40-F")


@dataclass
class Fact:
    """One XBRL fact with full provenance."""
    cik: int
    entity: str
    taxonomy: str
    tag: str
    unit: str
    end: date
    val: float
    accn: str
    fy: Optional[int]          # filer's fiscal-year context (NOT the data period)
    fp: Optional[str]
    form: str
    filed: date
    start: Optional[date] = None
    frame: Optional[str] = None
    superseded: list["Fact"] = field(default_factory=list)

    @property
    def duration_days(self) -> Optional[int]:
        if self.start is None:
            return None
        return (self.end - self.start).days

    def provenance(self) -> dict:
        return {
            "cik": self.cik,
            "taxonomy": self.taxonomy,
            "tag": self.tag,
            "unit": self.unit,
            "start": self.start.isoformat() if self.start else None,
            "end": self.end.isoformat(),
            "accn": self.accn,
            "fy": self.fy,
            "fp": self.fp,
            "form": self.form,
            "filed": self.filed.isoformat(),
            "n_superseded": len(self.superseded),
        }


class MalformedFilingError(ValueError):
    """CompanyFacts JSON is structurally unusable."""


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d").date()


def fiscal_year_label(end: date) -> int:
    """Calendar year the period ends in; Jan-May ends label the prior year.

    A FYE of 2024-01-31 covers essentially calendar 2023 and is labeled
    FY2023, keeping off-calendar filers comparable with December filers.
    """
    return end.year if end.month >= 6 else end.year - 1


def extract_facts(companyfacts: dict, taxonomy: str = "us-gaap") -> list[Fact]:
    """Flatten a CompanyFacts payload into Fact records (no dedupe yet).

    Skips malformed unit entries (missing val/end) rather than failing the
    whole company; raises MalformedFilingError only when the payload has no
    usable structure at all.
    """
    if not isinstance(companyfacts, dict) or "facts" not in companyfacts:
        raise MalformedFilingError("payload has no 'facts' key")
    cik = companyfacts.get("cik")
    if cik is None:
        raise MalformedFilingError("payload has no 'cik'")
    entity = companyfacts.get("entityName", "")
    tax_facts = companyfacts.get("facts", {}).get(taxonomy, {})
    if not isinstance(tax_facts, dict):
        raise MalformedFilingError(f"'facts.{taxonomy}' is not an object")

    out: list[Fact] = []
    for tag, body in tax_facts.items():
        units = body.get("units") if isinstance(body, dict) else None
        if not isinstance(units, dict):
            continue
        for unit, entries in units.items():
            if not isinstance(entries, list):
                continue
            for e in entries:
                try:
                    val = float(e["val"])
                    end = _parse_date(e["end"])
                    filed = _parse_date(e.get("filed")) or date(1900, 1, 1)
                except (KeyError, TypeError, ValueError):
                    continue  # malformed entry: skip, don't poison the company
                if end is None:
                    continue
                out.append(Fact(
                    cik=int(cik),
                    entity=entity,
                    taxonomy=taxonomy,
                    tag=tag,
                    unit=unit,
                    start=_parse_date(e.get("start")),
                    end=end,
                    val=val,
                    accn=e.get("accn", ""),
                    fy=e.get("fy"),
                    fp=e.get("fp"),
                    form=e.get("form", ""),
                    filed=filed,
                    frame=e.get("frame"),
                ))
    return out


def dedupe_facts(facts: Iterable[Fact]) -> list[Fact]:
    """Collapse duplicate facts for the same (tag, unit, period).

    The API returns one row per filing that mentioned the amount, including
    amendments and the comparative columns of later filings. The most
    recently filed value wins (restatements supersede originals); earlier
    values are kept on ``superseded`` for audit. Ties on filed date prefer
    the amended form, then the lexically larger accession number (a stable,
    deterministic tie-break that correlates with later submission).
    """
    grouped: dict[tuple, list[Fact]] = {}
    for f in facts:
        key = (f.tag, f.unit, f.start, f.end)
        grouped.setdefault(key, []).append(f)

    out: list[Fact] = []
    for group in grouped.values():
        group.sort(key=lambda f: (f.filed, f.form.endswith("/A"), f.accn))
        winner = group[-1]
        winner.superseded = [g for g in group[:-1] if g.val != winner.val]
        out.append(winner)
    return out


def _annual_duration_facts(facts: list[Fact]) -> list[Fact]:
    annual = [
        f for f in facts
        if f.duration_days is not None
        and ANNUAL_MIN_DAYS <= f.duration_days <= ANNUAL_MAX_DAYS
    ]
    from_annual_forms = [f for f in annual if f.form in ANNUAL_FORMS]
    return from_annual_forms or annual


def select_annual(
    facts: list[Fact],
    concept: str,
    fiscal_year_ends: Optional[dict[int, date]] = None,
) -> tuple[dict[int, Fact], list[str]]:
    """Pick one fact per fiscal-year label for a concept.

    Walks the concept's tag chain in order and uses the first tag with any
    usable annual data, then fills remaining years from later tags in the
    chain (mixed-tag fills are noted). For INSTANT concepts, prefers facts
    dated at the company's known fiscal year ends when provided.

    Returns ({fy_label: Fact}, notes). Notes record fallback-tag usage and
    unit rejections -- the raw material for coverage-gap reporting.
    """
    spec: ConceptSpec = CONCEPTS[concept]
    notes: list[str] = []
    by_tag: dict[str, list[Fact]] = {}
    for f in facts:
        if f.tag in spec.tags:
            if f.unit != spec.unit:
                notes.append(
                    f"{concept}: rejected unit '{f.unit}' for tag {f.tag} "
                    f"(expected {spec.unit}); value not used"
                )
                continue
            by_tag.setdefault(f.tag, []).append(f)

    selected: dict[int, Fact] = {}
    used_tags: list[str] = []
    for tag in spec.tags:  # chain order, not dict order
        tag_facts = by_tag.get(tag, [])
        if not tag_facts:
            continue
        if spec.kind == DURATION:
            candidates = _annual_duration_facts(tag_facts)
        else:
            candidates = tag_facts
            if fiscal_year_ends:
                fye_dates = set(fiscal_year_ends.values())
                at_fye = [f for f in candidates if f.end in fye_dates]
                if at_fye:
                    candidates = at_fye
        added = False
        for f in sorted(candidates, key=lambda f: f.end):
            label = fiscal_year_label(f.end)
            if label not in selected:
                selected[label] = f
                added = True
        if added:
            used_tags.append(tag)

    if len(used_tags) > 1:
        notes.append(
            f"{concept}: filled from multiple tags {used_tags}; "
            "cross-tag basis may differ between years"
        )
    elif used_tags and used_tags[0] != spec.tags[0]:
        notes.append(
            f"{concept}: primary tag {spec.tags[0]} absent; "
            f"used fallback {used_tags[0]}"
        )
    return selected, notes


def annual_period_ends(facts: list[Fact]) -> dict[int, date]:
    """Infer the company's fiscal-year-end date per fiscal-year label,
    from annual-duration facts (any concept)."""
    ends: dict[int, date] = {}
    for f in _annual_duration_facts([f for f in facts if f.start is not None]):
        label = fiscal_year_label(f.end)
        # Prefer the latest end seen for the label (amended periods rare)
        if label not in ends or f.end > ends[label]:
            ends[label] = f.end
    return ends
