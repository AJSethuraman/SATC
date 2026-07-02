"""Shared datatypes for the rule-based signal engine.

Scores are small integers in [-2, +2] used only for ordering and badges.
They are NOT expected returns and imply no predictive accuracy (nothing here
is backtested — see DISCLAIMER.md).
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from stock_helper.features.metrics import DerivedMetric

SIGNALS_VERSION = "signals-0.1"

# Statuses
OK = "OK"
NOT_APPLICABLE = "NOT_APPLICABLE"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
UNAVAILABLE = "UNAVAILABLE"
PLACEHOLDER = "PLACEHOLDER"


@dataclass
class Evidence:
    kind: str  # fact | filing | section | url
    reference: str  # accessions / chunk id / url
    description: str
    source_url: str | None = None


@dataclass
class SignalOutcome:
    status: str = OK
    value_text: str = ""
    numeric_value: float | None = None
    direction: str = ""  # improving | deteriorating | stable | mixed
    score: int | None = None
    interpretation: str = ""
    confidence: str = ""  # high | medium | low
    caveat: str = ""
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class SignalContext:
    bucket: str
    derived: dict[str, DerivedMetric]
    # Optional context computed outside the engine (text metrics, market data,
    # peer stats). Keys: "risk_language", "market", "peers". Signals requiring
    # extras report UNAVAILABLE (with the definition's hint) when absent —
    # e.g. in point-in-time history replay, where extras are not reconstructed.
    extras: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class SignalDef:
    key: str
    name: str
    category: str
    description: str
    formula: str = ""
    # None = applies to every bucket; otherwise the exact set it applies to.
    applicable_buckets: frozenset[str] | None = None
    excluded_buckets: frozenset[str] = frozenset()
    required_metrics: tuple[str, ...] = ()
    required_extras: tuple[str, ...] = ()
    unavailable_hint: str = ""  # shown when required metrics/extras are missing
    evaluator: Callable[[SignalContext], SignalOutcome | None] | None = None
    implemented: bool = True
    placeholder_reason: str = ""

    def applies_to(self, bucket: str) -> bool:
        if bucket in self.excluded_buckets:
            return False
        return self.applicable_buckets is None or bucket in self.applicable_buckets


def metric_evidence(metric: DerivedMetric, max_accessions: int = 3) -> Evidence:
    accessions = metric.input_accessions[-max_accessions:]
    return Evidence(
        kind="fact",
        reference=", ".join(accessions),
        description=f"{metric.label}: us-gaap {', '.join(metric.input_tags)} "
        f"({metric.formula})",
    )
