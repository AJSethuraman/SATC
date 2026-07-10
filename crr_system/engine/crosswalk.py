"""Crosswalk versioning: agency-tagged, as-of-date threshold status.

A threshold row is Active for agency X as of date D when:
    effective_date <= D  and  (rescinded_date is null or D < rescinded_date)

Because Type A rows are emitted one-per-agency, a rescission by the OCC and
FDIC stamps only those agencies' rows; an FRB row for the same metric stays
Active. This is exactly the leveraged-lending Dec-2025 fixture scenario.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Iterable, List, Optional

from .extract import RescissionNotice
from .schema import ROW_TYPE_A, ExtractedRow

STATUS_ACTIVE = "Active"
STATUS_RESCINDED = "Rescinded"
STATUS_NOT_YET_EFFECTIVE = "Not Yet Effective"
STATUS_UNKNOWN = "Unknown (Coverage Gap)"


def status_as_of(row: ExtractedRow, as_of: dt.date) -> str:
    if row.row_type != ROW_TYPE_A:
        raise ValueError("status_as_of applies to Type A threshold rows only")
    if row.status == "Coverage Gap" or row.effective_date is None:
        return STATUS_UNKNOWN
    if as_of < row.effective_date:
        return STATUS_NOT_YET_EFFECTIVE
    if row.rescinded_date is not None and as_of >= row.rescinded_date:
        return STATUS_RESCINDED
    return STATUS_ACTIVE


def _keywords(text: str) -> set:
    stop = {"the", "and", "for", "of", "on", "in", "to", "a", "an", "guidance"}
    return {w for w in re.findall(r"[a-z]{3,}", text.lower()) if w not in stop}


def apply_rescissions(
    rows: Iterable[ExtractedRow],
    notices: Iterable[RescissionNotice],
    *,
    min_overlap: int = 2,
) -> List[ExtractedRow]:
    """Stamp rescinded_date onto threshold rows matched by agency + citation.

    Matching is keyword overlap between the rescission notice's target text
    and the row's citation/source document name. Conservative: a notice that
    matches nothing changes nothing; agencies not named in the notice keep
    their rows untouched.
    """
    rows = list(rows)
    for notice in notices:
        target_kw = _keywords(notice.target_keywords)
        for row in rows:
            if row.row_type != ROW_TYPE_A or row.agency not in notice.agencies:
                continue
            row_kw = _keywords(row.citation + " " + row.anchor.document)
            if len(target_kw & row_kw) >= min_overlap:
                if row.rescinded_date is None or (
                    notice.rescinded_date and notice.rescinded_date < row.rescinded_date
                ):
                    row.rescinded_date = notice.rescinded_date
                    row.notes = (
                        (row.notes + " " if row.notes else "")
                        + f"Rescinded for {row.agency} per {notice.anchor.document} "
                        f"({notice.anchor.locator()})."
                    ).strip()
    return rows


def applicable_thresholds(
    rows: Iterable[ExtractedRow],
    *,
    as_of: dt.date,
    agency: Optional[str] = None,
    metric: Optional[str] = None,
) -> List[ExtractedRow]:
    """Thresholds in force for a review dated `as_of` (optionally by agency/metric)."""
    out = []
    for row in rows:
        if row.row_type != ROW_TYPE_A:
            continue
        if agency and row.agency != agency:
            continue
        if metric and row.metric != metric:
            continue
        if status_as_of(row, as_of) == STATUS_ACTIVE:
            out.append(row)
    return out
