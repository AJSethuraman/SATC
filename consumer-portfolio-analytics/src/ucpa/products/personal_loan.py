"""Personal/installment loan product module -- Phase 2.

Interface definition only, per the Phase 1 build order: the module exists
so the engine's product registry and tier detector have a stable contract
to code against, but the installment metric battery (term-based
amortization curves, payment-progress delinquency, etc.) is deliberately
not implemented yet.
"""

from __future__ import annotations

from ucpa.data_model import PRODUCT_PERSONAL_LOAN
from ucpa.products.base import MetricSpec, ProductModule


class PersonalLoanModule(ProductModule):
    """Interface stub: implemented in Phase 2 following the card template."""

    product_type = PRODUCT_PERSONAL_LOAN

    def metric_specs(self) -> tuple[MetricSpec, ...]:
        raise NotImplementedError(
            "Personal/installment loan metric battery is a Phase 2 deliverable; "
            "implement following ucpa.products.credit_card.CreditCardModule."
        )
