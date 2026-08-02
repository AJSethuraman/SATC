"""BILLING — value-based pricing, adjusted for means, shown honestly.

The practice bills for what the client received, at what they can reasonably
pay, and the invoice says both out loud:

    Your federal individual tax return .................. 450.00
    Rental property (x2) ................................ 370.00
                                         Full value      820.00
                                  Household rate  25%   -205.00
                                         YOU PAY         615.00

Three ideas hold it together:

* **Value and means are separate facts.** A service has a standard rate (what
  the work is worth); a client has a rate plan (what they can pay). Keeping
  them apart is what makes the discount visible rather than a smaller number
  nobody can interpret.
* **Every reduced rate records WHY.** A sliding scale with no basis is
  improvisation, and improvisation is what looks arbitrary when two clients
  compare notes. The engine refuses to issue without one.
* **Piecemeal.** An engagement produces several invoices as work happens, and
  ``billed_to_date`` answers what has already been charged.

And one thing the engine cannot express at all: a fee derived from the size of a
refund. A line is service × quantity, discounted by a percentage, with no access
to the outcome of the return — so the Circular 230 §10.27 prohibition on
contingent fees is structural rather than a rule someone has to remember.
"""

from __future__ import annotations

from satc.billing.catalogue import (
    RatePlan,
    Service,
    by_category,
    default_plan_key,
    load_plans,
    load_services,
    plan,
    plans,
    service,
    services,
)
from satc.billing.invoice import (
    BillingError,
    Invoice,
    InvoiceLine,
    billed_to_date,
    next_invoice_number,
)

__all__ = [
    "BillingError",
    "Invoice",
    "InvoiceLine",
    "RatePlan",
    "Service",
    "billed_to_date",
    "by_category",
    "default_plan_key",
    "load_plans",
    "load_services",
    "next_invoice_number",
    "plan",
    "plans",
    "service",
    "services",
]
