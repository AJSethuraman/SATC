"""Turn SEC companyfacts JSON into clean canonical annual series.

Two stages, deliberately separated:

1. **Extraction** (`extract_annual_points`): pull every annual fact for every
   candidate tag in xbrl_mapping.py — *including superseded values* (the same
   fiscal year re-reported in later filings). This is what ingestion stores.
2. **Selection** (`select_annual_series`): given fact points (from extraction
   or from the database), optionally apply an ``as_of`` cutoff, dedupe each
   period to one value, and pick the winning tag per metric by coverage.

Point-in-time notes:
- Every point keeps the accession and the filed date of the filing it came from.
- Without ``as_of``, the **latest-filed** value per period_end wins — the
  restated/most recent view, right for a research tear sheet.
- With ``as_of``, facts filed after that date are excluded and the latest value
  *filed on or before* ``as_of`` wins per period: the series as it was knowable
  on that date. This is the foundation for Phase 7 backtesting/calibration.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime

from stock_helper.normalization.xbrl_mapping import CANONICAL_METRICS, FLOW, MetricSpec

NORMALIZER_VERSION = "facts-0.2"

# Annual duration window, generous enough for 52/53-week fiscal years.
_ANNUAL_MIN_DAYS = 300
_ANNUAL_MAX_DAYS = 400

_ANNUAL_FORMS = ("10-K", "10-K/A")


@dataclass(frozen=True)
class FactPoint:
    metric_key: str
    taxonomy: str
    tag: str
    unit: str
    value: float
    period_start: date | None
    period_end: date
    fiscal_year: int | None
    fiscal_period: str | None
    form: str
    accession: str
    filed: date | None


@dataclass
class MetricSeries:
    metric_key: str
    tag: str
    unit: str
    points: list[FactPoint]  # ascending by period_end

    @property
    def latest(self) -> FactPoint:
        return self.points[-1]

    def values(self) -> list[tuple[date, float]]:
        return [(p.period_end, p.value) for p in self.points]

    def accessions(self) -> list[str]:
        return sorted({p.accession for p in self.points if p.accession})


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _is_annual(entry: dict, kind: str) -> bool:
    form = entry.get("form", "")
    if not any(form.startswith(f) for f in _ANNUAL_FORMS):
        return False
    if entry.get("fp") not in (None, "FY"):
        return False
    if kind == FLOW:
        start, end = _parse_date(entry.get("start")), _parse_date(entry.get("end"))
        if not start or not end:
            return False
        return _ANNUAL_MIN_DAYS <= (end - start).days <= _ANNUAL_MAX_DAYS
    return entry.get("end") is not None


def _extract_tag_points(
    facts_json: dict, spec: MetricSpec, taxonomy: str, tag: str
) -> list[FactPoint]:
    """All annual facts for one tag — superseded values included, no dedupe."""
    tag_data = facts_json.get("facts", {}).get(taxonomy, {}).get(tag)
    if not tag_data:
        return []
    # Units appear as e.g. "USD" or "shares"; pick the matching one.
    unit_entries = tag_data.get("units", {}).get(spec.unit)
    if unit_entries is None:
        return []

    points: list[FactPoint] = []
    for entry in unit_entries:
        if not _is_annual(entry, spec.kind):
            continue
        end = _parse_date(entry.get("end"))
        if end is None or entry.get("val") is None:
            continue
        points.append(
            FactPoint(
                metric_key=spec.key,
                taxonomy=taxonomy,
                tag=tag,
                unit=spec.unit,
                value=float(entry["val"]),
                period_start=_parse_date(entry.get("start")),
                period_end=end,
                fiscal_year=entry.get("fy"),
                fiscal_period=entry.get("fp"),
                form=entry.get("form", ""),
                accession=entry.get("accn", ""),
                filed=_parse_date(entry.get("filed")),
            )
        )
    return points


def extract_annual_points(facts_json: dict) -> list[FactPoint]:
    """Every annual FactPoint for every candidate tag of every canonical metric.

    This is the storage-layer view: nothing is deduped, so later as-of replay
    can still see originally-filed values that were superseded by restatements.
    """
    points: list[FactPoint] = []
    for spec in CANONICAL_METRICS.values():
        for taxonomy, tag in spec.candidates:
            points.extend(_extract_tag_points(facts_json, spec, taxonomy, tag))
    return points


def select_annual_series(
    points: Iterable[FactPoint], as_of: date | None = None
) -> dict[str, MetricSeries]:
    """Canonical metric key -> annual MetricSeries.

    ``as_of`` replays the series as knowable on that date: facts filed later
    are excluded (facts with no filed date cannot be placed in time and are
    also excluded), and the latest value filed on or before ``as_of`` wins per
    period. Default None = current restated view (latest filed wins).
    """
    deduped: dict[tuple[str, str], dict[date, FactPoint]] = {}
    for point in points:
        if as_of is not None and (point.filed is None or point.filed > as_of):
            continue
        per_period = deduped.setdefault((point.metric_key, point.tag), {})
        current = per_period.get(point.period_end)
        if current is None or (point.filed or date.min) >= (current.filed or date.min):
            per_period[point.period_end] = point

    series: dict[str, MetricSeries] = {}
    for key, spec in CANONICAL_METRICS.items():
        best: list[FactPoint] | None = None
        # Candidates iterate in preference order; strict '>' keeps the earlier
        # (preferred) tag on coverage ties.
        for _taxonomy, tag in spec.candidates:
            per_period = deduped.get((key, tag))
            if per_period and (best is None or len(per_period) > len(best)):
                best = sorted(per_period.values(), key=lambda p: p.period_end)
        if best:
            series[key] = MetricSeries(
                metric_key=key, tag=best[0].tag, unit=spec.unit, points=best
            )
    return series


def build_annual_series(
    facts_json: dict, as_of: date | None = None
) -> dict[str, MetricSeries]:
    """Extraction + selection in one step (used on fresh companyfacts JSON)."""
    return select_annual_series(extract_annual_points(facts_json), as_of=as_of)
