"""What one filing says about one field. The single answer both checks use.

Tenet S3: two halves of one tool must make the same call, and the way to
guarantee it is for one to BE the other.

The tie-out that runs on every build was first written with its own copy of
this comparison, and reported 157 differences against a feed the full run calls
clean. Every one was the copy, not the data: it did not know the capital ratios
are filed as fractions and multiplied by a hundred, it picked the larger of the
consolidated and domestic columns instead of the one the citation names, and it
knew nothing about the two-column capital fields. A second implementation of a
comparison is a second opinion, and the cheaper one is always the one that is
wrong.

So there is one implementation, here, and every checker calls it.

The four kinds of field, which is the whole of the logic:

* **a capital ratio the bank files** (RBC1AAJ, RBCRWAJ) -- on Schedule RC-R as
  a FRACTION, in up to two regulatory frameworks. The lower one binds.
* **a two-column amount** -- filed under two frameworks; the column chosen by
  its ratio, before the amount is looked at, so the comparison can still fail.
* **a ratio the FDIC computes** -- not a filed line at all. There is nothing to
  compare it with and saying so is the answer.
* **an amount** -- an MDRM expression resolved against this filing.

Quarterly flows are NOT here. A quarter is the difference of two filings and,
across a merger, of more than two; that needs the previous filing and the
merger record, so it belongs to the caller that holds them.
"""
from __future__ import annotations

import re
from typing import Dict, Optional, Tuple

from . import feed_fields as FF
from . import filing as F
from . import provenance_seed as PS

#: The two capital ratios a bank files itself, and where. Filed as a fraction
#: (0.102357), published as a percent (10.2357).
CAPITAL: Dict[str, Tuple[str, str]] = {
    "RBC1AAJ": ("7204", "RC-R Part I line 31, Tier 1 leverage ratio"),
    "RBCRWAJ": ("7205", "RC-R Part I line 51, total capital ratio"),
}
#: An MDRM item is four characters; the prefix in front of it says which column
#: of which schedule. `RC[A-Z][AW]7204` matches the advanced-approaches pair.
_CAPITAL_COLUMN = "RC[A-Z][AW]%s"
PREFIXES = ("RCFD", "RCON", "RIAD", "RCFA", "RCOA", "RCFW", "RCFN")

#: field -> the MDRM expression the provenance map cites for it.
PROVENANCE = {row[0]: row[3] for row in PS.ALL_ROWS}

#: Verdicts this returns. `NOT_A_FILED_LINE` is a real answer, not a gap.
TIES = "TIES"
DIFFERS = "DIFFERS"
NOT_ON_FILING = "NOT ON THIS FILING"
NOT_A_FILED_LINE = "COMPUTED BY THE FDIC"
NO_CITATION = "NO USABLE CITATION"
IS_A_FLOW = "QUARTERLY FLOW"

#: A balance is filed in thousands and published in thousands, so anything
#: under half a thousand is the filing's own rounding. A ratio is published to
#: four decimals.
TOLERANCE_AMOUNT = 0.51
TOLERANCE_RATIO = 0.005


def items_by_code(facts: dict) -> Dict[str, list]:
    """{four-character item: [every value filed under it]} for one filing."""
    out: Dict[str, list] = {}
    for code, value in facts.items():
        if isinstance(value, (int, float)) and code[:4] in PREFIXES:
            out.setdefault(code[4:], []).append(float(value))
    return out


def evaluate(expression: str, items: Dict[str, list], facts: dict) -> Optional[float]:
    """Sum an MDRM expression over one filing, in the filing's own units.

    A term may be a full code (`RCONJ454` -- that column and no other) or a
    bare item (`3815` -- whichever column this bank files). Absent means the
    whole expression is unanswerable, not zero: a line nobody filed and a line
    filed as zero are different facts.
    """
    total, sign, buf, terms = 0.0, 1, "", []
    for char in expression:
        if char in "+-":
            terms.append((sign, buf.strip()))
            sign = 1 if char == "+" else -1
            buf = ""
        else:
            buf += char
    terms.append((sign, buf.strip()))
    for signum, code in terms:
        if not code:
            continue
        if code[:4] in PREFIXES:
            if facts.get(code) is None:
                return None
            total += signum * float(facts[code])
            continue
        if code not in items:
            return None
        total += signum * max(items[code], key=abs)
    return total


def filed_value(field: str, facts: dict, report_date: str):
    """What this filing says about this field.

    Returns ``(value, citation, kind)``. ``value`` is in the units the feed
    publishes -- thousands of dollars for an amount, percent for a ratio -- or
    None when the filing does not answer. ``kind`` is one of the verdict
    constants above and says WHY when it does not.
    """
    if field in FF.FEED_FLOW_FIELDS or field in _FLOW_FIELDS:
        return None, "", IS_A_FLOW

    if field in CAPITAL:
        item, where = CAPITAL[field]
        filed = [v for code, v in facts.items()
                 if re.fullmatch(_CAPITAL_COLUMN % item, code)]
        if not filed:
            return None, where, NOT_ON_FILING
        # The lower ratio is the binding one where a bank files two.
        return min(filed) * 100, where, TIES

    if field in FF.TWO_COLUMN_FIELDS:
        column = FF.binding_column(field, facts)
        if column is None:
            return None, "", NOT_ON_FILING
        return float(facts[column]) / 1000.0, column, TIES

    if field in FF.FEED_FIELDS:
        expression = FF.citation_for(field, report_date).split(" (")[0]
        if not expression:
            return None, "", NO_CITATION
        got = evaluate(expression, items_by_code(facts), facts)
        if got is None:
            return None, expression, NOT_ON_FILING
        return got / 1000.0, expression, TIES

    # NOT split on " (" -- on this path the parenthetical IS the citation.
    # `RCON2200 (+RCFN2200 031)` says to add the foreign-office column on form
    # 031; `1797 (domestic)` says which of two columns; `RCON1606 (031:
    # RCFD1251+1254)` gives the whole alternative for the other form. Stripping
    # it left 4,067 values compared against the wrong column and reported as
    # differences -- JPMorgan's deposits came out 2,226,790,000 against a
    # delivered 2,820,284,000, which is domestic against consolidated and
    # nothing to do with the data. `parse_mdrm` exists to read all of that.
    expression = PROVENANCE.get(field) or ""
    if not expression:
        return None, "", NO_CITATION
    if "/" in expression:
        return None, expression, NOT_A_FILED_LINE
    parsed = F.parse_mdrm(expression)
    if parsed is None:
        return None, expression, NO_CITATION
    value, used = F.filed_value(facts, parsed)
    if value is None:
        return None, used or expression, NOT_ON_FILING
    # `filed_value` already returns the figure in the field's own units.
    return float(value), used or expression, TIES


def compare(field: str, ours: float, facts: dict, report_date: str):
    """``(verdict, theirs, citation)`` for one delivered value."""
    theirs, citation, kind = filed_value(field, facts, report_date)
    if kind != TIES:
        return kind, theirs, citation
    tolerance = TOLERANCE_RATIO if field in CAPITAL else TOLERANCE_AMOUNT
    if abs(float(ours) - theirs) < tolerance:
        return TIES, theirs, citation
    return DIFFERS, theirs, citation


#: The quarterly flows among the ORIGINAL fields. Named here so `filed_value`
#: refuses them rather than answering with a year-to-date, which is the shape
#: of a wrong answer that looks right.
_FLOW_FIELDS = frozenset({
    "NTCRCDQ", "NTAUTOQ", "NTCIQ", "NTCONOTQ", "NTRERESQ", "NTRECONQ",
    "NTRENREQ", "NTREMULQ",
})
