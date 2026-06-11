"""Product modules and registry."""

from __future__ import annotations

from ucpa.products.base import MetricSpec, ProductModule, ThresholdCheck
from ucpa.products.credit_card import CreditCardModule
from ucpa.products.personal_loan import PersonalLoanModule
from ucpa.products.student_loan import StudentLoanModule

#: Registry of product modules by product_type code.
PRODUCT_REGISTRY: dict[str, type[ProductModule]] = {
    CreditCardModule.product_type: CreditCardModule,
    PersonalLoanModule.product_type: PersonalLoanModule,
    StudentLoanModule.product_type: StudentLoanModule,
}


def get_product_module(product_type: str) -> ProductModule:
    """Instantiate the module registered for ``product_type``."""
    try:
        return PRODUCT_REGISTRY[product_type]()
    except KeyError as exc:
        raise KeyError(
            f"No product module registered for {product_type!r}; "
            f"known products: {sorted(PRODUCT_REGISTRY)}"
        ) from exc


__all__ = [
    "MetricSpec",
    "ProductModule",
    "ThresholdCheck",
    "CreditCardModule",
    "PersonalLoanModule",
    "StudentLoanModule",
    "PRODUCT_REGISTRY",
    "get_product_module",
]
