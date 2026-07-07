"""Saved screens: named ranking recipes over a standardized CrossSection.

A screen is a candidate-generation recipe, NOT a buy list. Each ScreenSpec picks
a ranking value (a composite score, a raw metric, or the Magic Formula z-sum),
an optional set of required outlier flags, and a sort direction. ``run_screen``
applies it and returns a ranked list. Nothing here is scored for performance or
backtested — the output is a reading list, and distress/manipulation screens are
never verdicts.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from stock_helper.screening.engine import CrossSection

_DEFAULT_CAVEAT = (
    "Candidate screen, NOT a buy list — unscored and NOT backtested. "
    "Distress/manipulation screens flag names to READ, never verdicts."
)

# Ranking sources a ScreenSpec can draw its sort key from.
SOURCE_SCORE = "score"  # a composite score map (value/quality/combined)
SOURCE_METRIC = "metric"  # a raw metric on the UniverseRow
SOURCE_MAGIC = "magic"  # Greenblatt-style z(earnings_yield) + z(roic)


@dataclass(frozen=True)
class ScreenSpec:
    """One named screen recipe.

    ``rank_source`` selects where the sort key comes from; ``rank_by`` names the
    score/metric within that source (ignored for the Magic Formula). ``ascending``
    ranks smallest-first (used by distress, where a low Altman Z is worst).
    ``require_flags`` restricts the candidate set to rows carrying every listed
    outlier flag."""

    key: str
    label: str
    description: str
    rank_source: str
    rank_by: str = ""
    ascending: bool = False
    require_flags: tuple[str, ...] = ()
    caveat: str = _DEFAULT_CAVEAT


@dataclass
class ScreenRun:
    """One ranked candidate produced by a screen."""

    rank: int
    ticker: str
    name: str
    bucket: str
    rank_value: float
    fair_value_gap: float | None
    value_score: float | None
    quality_score: float | None
    combined_score: float | None
    flags: list[str] = field(default_factory=list)


SAVED_SCREENS: dict[str, ScreenSpec] = {
    "deep_value": ScreenSpec(
        key="deep_value",
        label="Deep value",
        description="Cheapest on the value composite (fair-value gap, yields, EV/EBIT, P/B).",
        rank_source=SOURCE_SCORE,
        rank_by="value_score",
    ),
    "quality_compounders": ScreenSpec(
        key="quality_compounders",
        label="Quality compounders",
        description="Strongest on the quality composite (Piotroski, gross profitability, ROIC, ROE).",
        rank_source=SOURCE_SCORE,
        rank_by="quality_score",
    ),
    "magic_formula_top": ScreenSpec(
        key="magic_formula_top",
        label="Magic Formula (top)",
        description="Greenblatt-style rank: earnings yield + ROIC (cross-sectional z-sum).",
        rank_source=SOURCE_MAGIC,
    ),
    "distress_watch": ScreenSpec(
        key="distress_watch",
        label="Distress watch",
        description="Names flagged distressed, most distressed first (lowest Altman Z).",
        rank_source=SOURCE_METRIC,
        rank_by="altman_z",
        ascending=True,
        require_flags=("distress",),
    ),
    "manipulation_watch": ScreenSpec(
        key="manipulation_watch",
        label="Manipulation watch",
        description="Names flagged by the Beneish screen, highest M-score first.",
        rank_source=SOURCE_METRIC,
        rank_by="beneish_m",
        require_flags=("manipulation_risk",),
    ),
}


def _rank_value(cs: CrossSection, spec: ScreenSpec, ticker: str) -> float | None:
    if spec.rank_source == SOURCE_SCORE:
        table = {
            "value_score": cs.value_score,
            "quality_score": cs.quality_score,
            "combined_score": cs.combined_score,
        }[spec.rank_by]
        return table.get(ticker)
    if spec.rank_source == SOURCE_METRIC:
        row = cs.row_by_ticker(ticker)
        return row.metrics.get(spec.rank_by) if row is not None else None
    if spec.rank_source == SOURCE_MAGIC:
        ey = cs.z.get("earnings_yield", {}).get(ticker)
        roic = cs.z.get("roic", {}).get(ticker)
        if ey is None or roic is None:
            return None
        return ey + roic
    raise ValueError(f"unknown rank_source {spec.rank_source!r}")


def run_screen(cs: CrossSection, spec: ScreenSpec) -> list[ScreenRun]:
    """Rank ``cs`` under ``spec`` and return the ranked candidates.

    Rows are dropped when they lack a required flag or have no ranking value
    (a missing metric is never treated as 0). Ties keep universe order (a stable
    sort); ranks are 1-based."""
    entries: list[ScreenRun] = []
    for row in cs.rows:
        t = row.ticker
        if spec.require_flags and not all(
            f in cs.flags.get(t, []) for f in spec.require_flags
        ):
            continue
        rv = _rank_value(cs, spec, t)
        if rv is None:
            continue
        entries.append(
            ScreenRun(
                rank=0,
                ticker=t,
                name=row.name,
                bucket=row.bucket,
                rank_value=rv,
                fair_value_gap=row.metrics.get("fair_value_gap"),
                value_score=cs.value_score.get(t),
                quality_score=cs.quality_score.get(t),
                combined_score=cs.combined_score.get(t),
                flags=list(cs.flags.get(t, [])),
            )
        )

    entries.sort(key=lambda e: e.rank_value, reverse=not spec.ascending)
    for i, entry in enumerate(entries, start=1):
        entry.rank = i
    return entries
