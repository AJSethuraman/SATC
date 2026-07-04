"""Prior-year vs current-year comparison with variance flags.

Operates on the normalized data mart line items, so it works for any return type
and jurisdiction. Flags the cases the kickoff calls out: large income swings, an
item that appeared last year but is missing this year (e.g. a 1099 that dropped),
a new item, and new/dropped dependents.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from satc.ids import return_key
from satc.models.mart import DataMart, LineItem

# Default swing threshold (fraction) above which a year-over-year change is flagged.
DEFAULT_SWING = Decimal("0.10")
# Lines small enough that a percentage swing is noise rather than signal.
_MATERIALITY = Decimal("500")

Severity = str  # "" | "info" | "flag"


@dataclass(slots=True)
class VarianceRow:
    schedule: str
    line_code: str
    label: str
    prior: Decimal | None
    current: Decimal | None
    delta: Decimal
    pct: float | None
    flag: str
    severity: Severity


def _index(mart: DataMart, rk: str) -> dict[tuple[str, str], LineItem]:
    return {(li.schedule, li.line_code): li for li in mart.line_items if li.return_key == rk}


def compare_years(mart: DataMart, *, client_id: str, return_type: str, jurisdiction: str,
                  prior_year: int, current_year: int,
                  swing: Decimal = DEFAULT_SWING) -> list[VarianceRow]:
    """Return one :class:`VarianceRow` per line present in either year, flagged."""
    prior_rk = return_key(client_id, prior_year, return_type, jurisdiction)
    current_rk = return_key(client_id, current_year, return_type, jurisdiction)
    prior = _index(mart, prior_rk)
    current = _index(mart, current_rk)

    rows: list[VarianceRow] = []
    for key in sorted(set(prior) | set(current)):
        p = prior.get(key)
        c = current.get(key)
        label = (c or p).label
        pv = p.amount if p and p.amount is not None else None
        cv = c.amount if c and c.amount is not None else None
        delta = (cv or Decimal("0")) - (pv or Decimal("0"))
        pct: float | None = float(delta / abs(pv)) if pv not in (None, Decimal("0")) else None

        flag, severity = "", ""
        if p is not None and c is None and pv not in (None, Decimal("0")):
            flag, severity = "DROPPED — present last year, missing this year", "flag"
        elif c is not None and p is None and cv not in (None, Decimal("0")):
            flag, severity = "NEW — not present last year", "info"
        elif pv is not None and pct is not None and abs(delta) >= _MATERIALITY and abs(Decimal(str(pct))) >= swing:
            flag, severity = f"SWING {pct:+.0%}", "flag"

        # Dependent count changes are always surfaced.
        if key[0] == "1040" and key[1] in ("dependents", "ctc_children") and delta != 0:
            flag = flag or f"DEPENDENTS changed {pv}→{cv}"
            severity = "flag"

        rows.append(VarianceRow(
            schedule=key[0], line_code=key[1], label=label, prior=pv, current=cv,
            delta=delta, pct=pct, flag=flag, severity=severity))
    return rows


def flagged(rows: list[VarianceRow]) -> list[VarianceRow]:
    return [r for r in rows if r.severity == "flag"]
