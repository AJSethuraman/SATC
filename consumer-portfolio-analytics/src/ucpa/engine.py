"""Deterministic metric engine.

Orchestrates one review run over one tape:

1. detect the tape's data tier (product-aware),
2. for each metric in the product's battery, either compute it (when the
   tape's fields, panel structure, and detected tier support it) or log a
   structured data-gap finding,
3. evaluate every computed metric against its configured thresholds.

The engine is product-agnostic and tape-source-agnostic: a real client
tape that conforms to the data model drops in for the synthetic generator
without any engine changes.
"""

from __future__ import annotations

from typing import Mapping, Optional

import pandas as pd

from ucpa.data_model import (
    F_ACCOUNT_ID,
    F_AS_OF_DATE,
    F_BALANCE,
    PANEL_REQUIREMENT,
)
from ucpa.metrics.common import active_rows
from ucpa.metrics.results import (
    STATUS_BLOCKED,
    DataGapFinding,
    MetricResult,
    ReviewResult,
    ThresholdException,
)
from ucpa.products.base import MetricSpec, ProductModule
from ucpa.thresholds import evaluate_checks, load_default_thresholds
from ucpa.tier_detector import TierDetectionResult, detect_tier, field_present


def _blocked_result(
    spec: MetricSpec, missing: list[str], detection: TierDetectionResult
) -> MetricResult:
    """Build the blocked MetricResult + data-gap finding for one spec."""
    if missing:
        description = (
            f"Cannot compute '{spec.name}': tape is missing {', '.join(missing)}."
        )
    else:
        next_tier_fields = ", ".join(detection.missing_for_next_tier) or "n/a"
        description = (
            f"Cannot compute '{spec.name}': requires Tier {spec.min_tier} data "
            f"maturity but the tape was detected at Tier {detection.detected_tier} "
            f"(missing for next tier: {next_tier_fields})."
        )
        missing = list(detection.missing_for_next_tier)
    gap = DataGapFinding(
        metric=spec.name,
        scope="metric",
        missing_fields=tuple(missing),
        tier_required=spec.min_tier,
        description=description,
    )
    return MetricResult(metric=spec.name, status=STATUS_BLOCKED, gaps=[gap])


def _portfolio_summary(tape: pd.DataFrame) -> dict[str, object]:
    """Headline tape facts for the dashboard, independent of any metric."""
    act = active_rows(tape)
    latest = act[act[F_AS_OF_DATE] == act[F_AS_OF_DATE].max()] if not act.empty else act
    return {
        "as_of": latest[F_AS_OF_DATE].max() if not latest.empty else None,
        "open_accounts": int(latest[F_ACCOUNT_ID].nunique()),
        "open_balance": float(latest[F_BALANCE].sum()),
        "panel_months": int(tape[F_AS_OF_DATE].nunique()),
        "rows": int(len(tape)),
    }


def run_review(
    tape: pd.DataFrame,
    module: ProductModule,
    thresholds: Optional[Mapping] = None,
) -> ReviewResult:
    """Run the full asset-quality review battery over ``tape``.

    Args:
        tape: Account-level tape (panel or snapshot) for one product.
        module: Product module supplying the data model and metric battery.
        thresholds: Thresholds config; defaults to the firm-standard config.

    Returns:
        A :class:`ReviewResult` with the tier detection, every metric result
        (computed, partial, or blocked), flagged threshold exceptions, and
        the consolidated data-gap findings (the data-maturity assessment).
    """
    config = dict(thresholds) if thresholds is not None else load_default_thresholds()
    detection = detect_tier(tape, module)

    results: list[MetricResult] = []
    exceptions: list[ThresholdException] = []
    gaps: list[DataGapFinding] = []

    for spec in module.metric_specs():
        missing = [f for f in spec.required_fields if not field_present(tape, f)]
        if spec.requires_panel and not detection.is_panel:
            missing.append(PANEL_REQUIREMENT)

        if missing or detection.detected_tier < spec.min_tier:
            result = _blocked_result(spec, missing, detection)
        else:
            result = spec.compute(tape)
            exceptions.extend(evaluate_checks(result, spec.checks, config))
        results.append(result)
        gaps.extend(result.gaps)

    review = ReviewResult(
        product_type=module.product_type,
        tier_detection=detection,
        portfolio_summary=_portfolio_summary(tape),
        metric_results=results,
        exceptions=exceptions,
        gaps=gaps,
        thresholds_used=config,
    )
    # Deterministic rule-based observations run last: they read the computed
    # summaries, tables, and threshold outcomes, never the raw tape.
    from ucpa.observations import derive_observations

    review.observations = derive_observations(review)
    return review
