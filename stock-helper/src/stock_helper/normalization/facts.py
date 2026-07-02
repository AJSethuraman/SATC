"""Turn SEC companyfacts JSON into clean canonical annual series.

Approach: for each canonical metric we look at the candidate tags in
xbrl_mapping.py, extract annual facts (FY, 10-K family), and pick the candidate
tag with the most annual periods. Ties go to the earlier (preferred) candidate.

Point-in-time notes:
- Every point keeps the accession and the filed date of the filing it came from.
- The same fiscal year usually appears in several filings (comparatives). We
  keep the **latest-filed** value per period_end — i.e. the restated/most
  recent view — which is right for a research tear sheet.
- ``build_annual_series(..., as_of=date)`` replays what was knowable on a past
  date: facts filed after ``as_of`` are excluded, and the latest value *filed
  on or before* ``as_of`` wins per period. This is the foundation for Phase 7
  backtesting/calibration (outcome labels and walk-forward validation are not
  built yet — see ROADMAP.md).
"""

from dataclasses import dataclass
from datetime import date, datetime

from stock_helper.normalization.xbrl_mapping import CANONICAL_METRICS, FLOW, MetricSpec

NORMALIZER_VERSION = "facts-0.1"

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
    facts_json: dict,
    spec: MetricSpec,
    taxonomy: str,
    tag: str,
    as_of: date | None = None,
) -> list[FactPoint]:
    tag_data = facts_json.get("facts", {}).get(taxonomy, {}).get(tag)
    if not tag_data:
        return []
    # Units appear as e.g. "USD" or "shares"; pick the matching one.
    unit_entries = tag_data.get("units", {}).get(spec.unit)
    if unit_entries is None:
        return []

    # Latest-filed value wins per period_end (restated view; see module docstring).
    best: dict[date, FactPoint] = {}
    for entry in unit_entries:
        if not _is_annual(entry, spec.kind):
            continue
        end = _parse_date(entry.get("end"))
        if end is None or entry.get("val") is None:
            continue
        filed = _parse_date(entry.get("filed"))
        # Point-in-time replay: a fact "exists" only once filed. Facts with no
        # filed date cannot be placed in time, so they are excluded under as_of.
        if as_of is not None and (filed is None or filed > as_of):
            continue
        point = FactPoint(
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
            filed=filed,
        )
        current = best.get(end)
        if current is None or (point.filed or date.min) >= (current.filed or date.min):
            best[end] = point
    return sorted(best.values(), key=lambda p: p.period_end)


def build_annual_series(
    facts_json: dict, as_of: date | None = None
) -> dict[str, MetricSeries]:
    """Canonical metric key -> annual MetricSeries (metrics with no data omitted).

    ``as_of`` replays the series as it was knowable on that date (facts filed
    later are excluded). Default None = current restated view.
    """
    series: dict[str, MetricSeries] = {}
    for key, spec in CANONICAL_METRICS.items():
        candidates: list[list[FactPoint]] = []
        for taxonomy, tag in spec.candidates:
            points = _extract_tag_points(facts_json, spec, taxonomy, tag, as_of=as_of)
            if points:
                candidates.append(points)
        if not candidates:
            continue
        # Most annual coverage wins; ties resolved by candidate preference order
        # because sort is stable.
        winner = max(candidates, key=len)
        series[key] = MetricSeries(
            metric_key=key, tag=winner[0].tag, unit=spec.unit, points=winner
        )
    return series
