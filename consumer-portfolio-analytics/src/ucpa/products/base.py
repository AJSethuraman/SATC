"""Product-module interface.

Each unsecured consumer product (credit card, personal/installment loan,
student loan) is implemented as a *product module*: a class that declares

* which tape fields each data tier requires **for that product** (e.g.
  original/remaining term is a Tier 2 field for installment products but is
  not applicable to revolving cards), and
* the product's metric battery, as a list of :class:`MetricSpec` entries that
  pair a deterministic compute function with its field requirements and its
  configurable threshold checks.

The metric engine (:mod:`ucpa.engine`) is product-agnostic: it walks the
module's specs, computes what the tape supports, and logs a structured
data-gap finding for everything it cannot compute.  Phase 1 implements
:class:`ucpa.products.credit_card.CreditCardModule` end to end; personal and
student loans implement this same interface in a later phase.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

from ucpa.data_model import TIER0_FIELDS, TIER1_ONLY_FIELDS, TIER2_ONLY_FIELDS
from ucpa.metrics.results import MetricResult


@dataclass(frozen=True)
class ThresholdCheck:
    """Binds one summary value of a metric to one configurable limit.

    Attributes:
        config_key: Dotted path into the thresholds config, e.g.
            ``"delinquency.max_dpd30plus_balance_rate"``.
        summary_key: Key in ``MetricResult.summary`` to evaluate.
        direction: ``"max"`` (breach when observed > limit) or ``"min"``.
        label: Human-readable check name for reports.
        format: ``"pct"`` or ``"num"`` -- how to render values in reports.
    """

    config_key: str
    summary_key: str
    direction: str
    label: str
    format: str = "pct"


@dataclass(frozen=True)
class MetricSpec:
    """One metric in a product's battery.

    Attributes:
        name: Stable metric identifier.
        description: One-line definition (also used in the findings doc).
        min_tier: Lowest data tier at which the metric is computable.
        required_fields: Tape columns the compute function needs.
        requires_panel: Whether a monthly longitudinal panel is required.
        compute: Deterministic function ``(tape) -> MetricResult``.
        checks: Threshold checks evaluated against the result's summary.
    """

    name: str
    description: str
    min_tier: int
    required_fields: tuple[str, ...]
    requires_panel: bool
    compute: Callable[[pd.DataFrame], MetricResult]
    checks: tuple[ThresholdCheck, ...] = field(default_factory=tuple)


class ProductModule(ABC):
    """Interface every product module implements."""

    #: Product type code as it appears in the tape's ``product_type`` column.
    product_type: str

    def tier_fields(self) -> dict[int, frozenset[str]]:
        """Fields required at each tier for this product.

        Default: the generic tiered data model.  Products override
        :meth:`not_applicable_fields` to drop fields that do not apply
        (they may still appear in a tape, but never gate tier detection).
        """
        na = self.not_applicable_fields()
        return {
            0: TIER0_FIELDS - na,
            1: TIER1_ONLY_FIELDS - na,
            2: TIER2_ONLY_FIELDS - na,
        }

    def not_applicable_fields(self) -> frozenset[str]:
        """Fields from the generic model that do not apply to this product."""
        return frozenset()

    @abstractmethod
    def metric_specs(self) -> tuple[MetricSpec, ...]:
        """The product's asset-quality metric battery, in report order."""
        raise NotImplementedError
