"""Result containers shared by the metric engine and report writers.

Every metric computation returns a :class:`MetricResult`.  When a metric (or
a sub-dimension of a metric) cannot be computed because the tape lacks the
required fields, the engine records a structured :class:`DataGapFinding`.
The collected gap findings are themselves a client deliverable: a
data-maturity gap assessment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

STATUS_COMPUTED = "computed"
STATUS_PARTIAL = "partial"  # computed, but some sub-dimensions were blocked
STATUS_BLOCKED = "blocked"


@dataclass(frozen=True)
class DataGapFinding:
    """A metric (or metric dimension) that could not be computed.

    Attributes:
        metric: Metric name (matches ``MetricSpec.name``).
        scope: ``"metric"`` if the whole metric was blocked, otherwise the
            name of the blocked sub-dimension (e.g. ``"score_band"``).
        missing_fields: Tape fields (or the panel-structure marker) whose
            absence blocked the computation.
        tier_required: Lowest data tier at which the computation becomes
            available.
        description: Analyst-readable explanation of what is lost.
    """

    metric: str
    scope: str
    missing_fields: tuple[str, ...]
    tier_required: int
    description: str


@dataclass
class MetricResult:
    """Output of a single metric computation.

    Attributes:
        metric: Metric name (matches ``MetricSpec.name``).
        status: ``computed`` / ``partial`` / ``blocked``.
        summary: Headline scalar values keyed by stable summary-key names.
            These keys are what threshold checks reference.
        tables: Detail tables keyed by table name (exported to Excel).
        gaps: Data-gap findings raised by this metric (always populated when
            ``status`` is ``blocked``; may be populated when ``partial``).
    """

    metric: str
    status: str
    summary: dict[str, object] = field(default_factory=dict)
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    gaps: list[DataGapFinding] = field(default_factory=list)


@dataclass(frozen=True)
class ThresholdException:
    """A metric value that breached (or neared) its configured threshold.

    Attributes:
        metric: Metric name.
        check: Human-readable check label.
        summary_key: The ``MetricResult.summary`` key that was evaluated.
        observed: Observed value.
        limit: Configured limit.
        direction: ``"max"`` (observed must be <= limit) or ``"min"``.
        severity: ``"EXCEPTION"`` for a breach, ``"WATCH"`` for within 10%
            of the limit on the compliant side.
        message: Formatted one-line description.
    """

    metric: str
    check: str
    summary_key: str
    observed: float
    limit: float
    direction: str
    severity: str
    message: str
    format: str = "pct"  # "pct" or "num" -- how to render observed/limit


@dataclass
class ReviewResult:
    """Full output of one engine run over one tape."""

    product_type: str
    tier_detection: "object"  # ucpa.tier_detector.TierDetectionResult
    portfolio_summary: dict[str, object]
    metric_results: list[MetricResult]
    exceptions: list[ThresholdException]
    gaps: list[DataGapFinding]
    thresholds_used: dict[str, object]
    #: Deterministic rule-based observations (ucpa.observations.Observation),
    #: derived after all metrics and threshold checks have run.
    observations: list = field(default_factory=list)

    def result_for(self, metric: str) -> Optional[MetricResult]:
        """Return the result for ``metric``, or None if not present."""
        for r in self.metric_results:
            if r.metric == metric:
                return r
        return None
