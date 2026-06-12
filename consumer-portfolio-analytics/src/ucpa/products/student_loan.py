"""Student loan product module -- Phase 2.

Interface definition only, per the Phase 1 build order (see
:mod:`ucpa.products.personal_loan` for rationale).
"""

from __future__ import annotations

from ucpa.data_model import PRODUCT_STUDENT_LOAN
from ucpa.products.base import MetricSpec, ProductModule


class StudentLoanModule(ProductModule):
    """Interface stub: implemented in Phase 2 following the card template."""

    product_type = PRODUCT_STUDENT_LOAN

    def metric_specs(self) -> tuple[MetricSpec, ...]:
        raise NotImplementedError(
            "Student loan metric battery is a Phase 2 deliverable; "
            "implement following ucpa.products.credit_card.CreditCardModule."
        )
