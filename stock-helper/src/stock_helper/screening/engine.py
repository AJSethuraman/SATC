"""Cross-sectional standardization, composites, and outlier flags (pure).

The engine takes a list of :class:`UniverseRow` and turns each raw figure into a
robust cross-sectional z-score (median / scaled-MAD, from ``valuation.stats``)
and a percentile — computed WITHIN the company's industry bucket when the bucket
is large enough (``min_sector_n``), otherwise against the whole universe. Every
metric is oriented so that ``+`` always means "better / cheaper": lower-is-better
metrics (EV/EBIT, P/B, Beneish, accruals) have their z (and percentile) sign
flipped.

Composites (value / quality) are the plain mean of the oriented z-scores of
their component metrics, computed only when enough components are present. Flags
are cross-sectional OUTLIER screens — deliberately loose, and never a verdict.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlmodel import Session

from stock_helper.screening.metrics import (
    QUALITY_METRICS,
    STANDARDIZABLE,
    VALUE_METRICS,
    UniverseRow,
    build_universe_rows,
)
from stock_helper.valuation.stats import mad, median, percentile_of, robust_zscore

# Metric polarity: +1 = higher raw value is better, -1 = lower raw value is
# better. The engine multiplies each z-score by this so a positive oriented z
# always reads as "better / cheaper".
HIGHER_IS_BETTER = frozenset({
    "fair_value_gap", "earnings_yield", "fcf_yield",
    "piotroski_f", "gross_profitability", "roic", "roe",
    "altman_z",  # a higher Altman Z is safer
})
LOWER_IS_BETTER = frozenset({"ev_ebit", "p_b", "beneish_m", "accruals"})

POLARITY: dict[str, int] = (
    {m: 1 for m in HIGHER_IS_BETTER} | {m: -1 for m in LOWER_IS_BETTER}
)

# Altman raw distress cutoff (Altman 1968 original-Z distress zone floor). Used
# by the outlier flags directly on the RAW value, not the z-score.
_ALTMAN_DISTRESS = 1.81


@dataclass
class CrossSection:
    """A standardized universe: per-metric oriented z-scores and percentiles,
    plus composites and outlier flags. Pandas-free — the per-metric maps are
    plain ``{ticker: value}`` dicts.

    ``z[metric][ticker]`` and ``percentile[metric][ticker]`` are only populated
    for rows whose raw metric was present. ``value_score`` / ``quality_score`` /
    ``combined_score`` and ``flags`` are filled by :func:`compute_composites` and
    :func:`flag_outliers` respectively."""

    rows: list[UniverseRow]
    z: dict[str, dict[str, float | None]] = field(default_factory=dict)
    percentile: dict[str, dict[str, float]] = field(default_factory=dict)
    value_score: dict[str, float | None] = field(default_factory=dict)
    quality_score: dict[str, float | None] = field(default_factory=dict)
    combined_score: dict[str, float | None] = field(default_factory=dict)
    flags: dict[str, list[str]] = field(default_factory=dict)
    by_sector: bool = True

    def row_by_ticker(self, ticker: str) -> UniverseRow | None:
        return next((r for r in self.rows if r.ticker == ticker), None)


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def standardize(
    rows: list[UniverseRow],
    *,
    by_sector: bool = True,
    min_sector_n: int = 5,
) -> CrossSection:
    """Robust-standardize every metric across ``rows``.

    For each metric and each row, the peer set is the company's bucket when that
    bucket has ``>= min_sector_n`` rows with the metric present (and
    ``by_sector`` is on), otherwise the whole universe. The z-score is
    ``robust_zscore`` (median / scaled MAD, clipped to ±3) and is sign-flipped
    for lower-is-better metrics so ``+`` always means better/cheaper; the
    percentile is likewise oriented (100 = best). Rows missing the raw metric are
    left out of that metric's maps (they never become a 0)."""
    cs = CrossSection(rows=list(rows), by_sector=by_sector)

    for metric in STANDARDIZABLE:
        polarity = POLARITY[metric]
        universe_vals = [
            r.metrics.get(metric) for r in rows if r.metrics.get(metric) is not None
        ]
        z_map: dict[str, float | None] = {}
        pct_map: dict[str, float] = {}

        for row in rows:
            value = row.metrics.get(metric)
            if value is None:
                continue  # missing -> excluded, never a fabricated 0

            peers: list[float | None] | None = None
            if by_sector:
                same = [
                    r.metrics.get(metric)
                    for r in rows
                    if r.bucket == row.bucket and r.metrics.get(metric) is not None
                ]
                if len(same) >= min_sector_n:
                    peers = same
            if peers is None:
                peers = list(universe_vals)

            center = median(peers)
            spread = mad(peers)
            z = robust_zscore(value, center, spread)
            if z is not None:
                z *= polarity
            pct_raw = percentile_of(value, peers)
            pct = pct_raw if polarity > 0 else 100.0 - pct_raw

            z_map[row.ticker] = z
            pct_map[row.ticker] = pct

        cs.z[metric] = z_map
        cs.percentile[metric] = pct_map

    return cs


def _composite(
    cs: CrossSection, ticker: str, metrics: tuple[str, ...], min_components: int
) -> float | None:
    """Mean of the oriented z-scores present for ``ticker`` across ``metrics``;
    None if fewer than ``min_components`` are available."""
    zs = [
        z
        for m in metrics
        if (z := cs.z.get(m, {}).get(ticker)) is not None
    ]
    if len(zs) < min_components:
        return None
    return _mean(zs)


def compute_composites(
    cs: CrossSection,
    *,
    min_value_components: int = 3,
    min_quality_components: int = 3,
) -> CrossSection:
    """Fill value / quality / combined composite scores on ``cs`` (in place).

    ``value_score`` averages the oriented z of {fair_value_gap, earnings_yield,
    fcf_yield, ev_ebit, p_b}; ``quality_score`` averages {piotroski_f,
    gross_profitability, roic, roe}. Both require a minimum number of present
    components (a company with too few standardizable inputs scores ``None`` — it
    is NOT ranked 0). ``combined_score`` is the mean of the two, only when BOTH
    exist. A rough research ordering, not a rating."""
    for row in cs.rows:
        t = row.ticker
        vs = _composite(cs, t, VALUE_METRICS, min_value_components)
        qs = _composite(cs, t, QUALITY_METRICS, min_quality_components)
        cs.value_score[t] = vs
        cs.quality_score[t] = qs
        both = [s for s in (vs, qs) if s is not None]
        cs.combined_score[t] = _mean(both) if len(both) == 2 else None
    return cs


def flag_outliers(cs: CrossSection, *, z: float = 2.0) -> CrossSection:
    """Raise cross-sectional OUTLIER flags on ``cs`` (in place). Screens, not
    verdicts:

    - ``deep_value``: value composite z > ``z``.
    - ``quality_compounder``: quality composite z > ``z``.
    - ``distress``: distress models agree (Altman/Ohlson/Zmijewski) OR raw
      Altman Z < 1.81 (original-Z distress floor).
    - ``manipulation_risk``: the Beneish manipulation flag fired.
    - ``value_trap``: cheap on value (value z > ``z``) but weak on quality
      (quality z < -1) — a caution overlay on the deep-value flag.
    """
    for row in cs.rows:
        t = row.ticker
        fl: list[str] = []
        vz = cs.value_score.get(t)
        qz = cs.quality_score.get(t)

        if vz is not None and vz > z:
            fl.append("deep_value")
        if qz is not None and qz > z:
            fl.append("quality_compounder")

        altman = row.metrics.get("altman_z")
        if "distress_models_agree" in row.flags or (
            altman is not None and altman < _ALTMAN_DISTRESS
        ):
            fl.append("distress")

        if "beneish_manipulation_flag" in row.flags:
            fl.append("manipulation_risk")

        if vz is not None and qz is not None and vz > z and qz < -1.0:
            fl.append("value_trap")

        cs.flags[t] = fl
    return cs


def build_cross_section(
    session: Session,
    *,
    by_sector: bool = True,
    tickers: list[str] | None = None,
    settings=None,
    as_of: date | None = None,
) -> CrossSection:
    """End-to-end: build universe rows, standardize, compose, and flag. The one
    DB-touching entry point; the standardize/compose/flag steps are pure and
    independently testable."""
    rows = build_universe_rows(
        session, tickers=tickers, settings=settings, as_of=as_of
    )
    cs = standardize(rows, by_sector=by_sector)
    compute_composites(cs)
    flag_outliers(cs)
    return cs
