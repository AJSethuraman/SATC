"""Rule-based signal engine: applies the registry to one company's metrics.

Guarantees the scorecard makes honest claims:
- Signals that don't apply to the industry bucket → NOT_APPLICABLE (never a bad ratio).
- Declared-but-unbuilt signals → PLACEHOLDER with the reason.
- Missing canonical metrics → UNAVAILABLE, naming the missing inputs.
- Too little history for a rule → INSUFFICIENT_DATA.
"""

from dataclasses import dataclass, field
from datetime import date

from stock_helper.features.metrics import DerivedMetric
from stock_helper.normalization.xbrl_mapping import CANONICAL_METRICS
from stock_helper.signals.base import (
    INSUFFICIENT_DATA,
    NOT_APPLICABLE,
    PLACEHOLDER,
    UNAVAILABLE,
    Evidence,
    SignalContext,
    SignalDef,
    SignalOutcome,
)
from stock_helper.signals.definitions import REGISTRY


@dataclass
class EvaluatedSignal:
    definition: SignalDef
    outcome: SignalOutcome


@dataclass
class DataConfidence:
    """Company-level data-quality summary shown on every scorecard."""

    metrics_mapped: int
    metrics_total: int
    annual_periods: int
    latest_filing: date | None
    notes: list[str] = field(default_factory=list)

    @property
    def coverage(self) -> float:
        return self.metrics_mapped / self.metrics_total if self.metrics_total else 0.0

    @property
    def level(self) -> str:
        if self.coverage >= 0.6 and self.annual_periods >= 3:
            return "high"
        if self.coverage >= 0.35 and self.annual_periods >= 2:
            return "medium"
        return "low"


def evaluate_signals(
    bucket: str,
    derived: dict[str, DerivedMetric],
    extras: dict[str, object] | None = None,
) -> list[EvaluatedSignal]:
    ctx = SignalContext(bucket=bucket, derived=derived, extras=extras or {})
    results: list[EvaluatedSignal] = []
    for definition in REGISTRY:
        results.append(EvaluatedSignal(definition, _evaluate_one(definition, ctx)))
    return results


def _evaluate_one(definition: SignalDef, ctx: SignalContext) -> SignalOutcome:
    if not definition.applies_to(ctx.bucket):
        return SignalOutcome(
            status=NOT_APPLICABLE,
            interpretation=(
                f"Not applicable to the '{ctx.bucket}' industry bucket by design "
                "(see SIGNAL_DEFINITIONS.md)."
            ),
        )
    if not definition.implemented:
        return SignalOutcome(
            status=PLACEHOLDER,
            interpretation=f"Planned signal, not yet implemented. {definition.placeholder_reason}",
        )
    missing = [m for m in definition.required_metrics if m not in ctx.derived]
    if missing:
        return SignalOutcome(
            status=UNAVAILABLE,
            interpretation=(
                f"Required metric(s) not mapped from XBRL for this filer: {', '.join(missing)}. "
                + (definition.unavailable_hint
                   or "The filer may use custom tags this version does not map.")
            ),
        )
    missing_extras = [e for e in definition.required_extras if ctx.extras.get(e) is None]
    if missing_extras:
        return SignalOutcome(
            status=UNAVAILABLE,
            interpretation=(
                f"Required context not available: {', '.join(missing_extras)}. "
                + definition.unavailable_hint
            ),
        )
    outcome = definition.evaluator(ctx) if definition.evaluator else None
    if outcome is None:
        return SignalOutcome(
            status=INSUFFICIENT_DATA,
            interpretation="Not enough annual periods available to apply this rule.",
        )
    return outcome


def assess_data_confidence(
    bucket: str,
    canonical_series: dict,  # canonical metric key -> object with .points
    latest_filing: date | None,
) -> DataConfidence:
    # Only count metrics that could plausibly apply to this bucket: a bank is
    # not penalized for missing cost_of_revenue, nor an industrial for deposits.
    bank_only = {
        "deposits", "credit_loss_allowance", "net_interest_income",
        "nonperforming_loans", "charge_offs",
    }
    not_for_banks = bank_only | {"cost_of_revenue", "current_assets", "current_liabilities"}
    if bucket == "banking":
        relevant = [k for k in CANONICAL_METRICS if k in bank_only or k not in not_for_banks]
    else:
        relevant = [k for k in CANONICAL_METRICS if k not in bank_only]
    periods = max((len(m.points) for m in canonical_series.values()), default=0)
    mapped = sum(1 for key in relevant if key in canonical_series)
    notes = []
    if mapped < len(relevant) * 0.5:
        notes.append(
            "Less than half of canonical metrics mapped — interpret every signal cautiously."
        )
    if periods < 3:
        notes.append("Fewer than 3 annual periods — trend signals are weak or missing.")
    return DataConfidence(
        metrics_mapped=mapped,
        metrics_total=len(relevant),
        annual_periods=periods,
        latest_filing=latest_filing,
        notes=notes,
    )


def evidence_for(outcome: SignalOutcome) -> list[Evidence]:
    return outcome.evidence
