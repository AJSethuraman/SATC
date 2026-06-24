"""Bridge: confirmed paystub-reader fields -> an estimator :class:`Paystub`.

The :class:`~satc.ingest.readers.paystub.PaystubReader` emits labeled source
values that the preparer confirms against the document. Once confirmed, this turns
those labels into the estimator's per-paycheck input, including two derivations:

* taxable wages per period = gross - pre-tax retirement (a Box 1 proxy), and
* pay periods remaining, inferred from how many periods the YTD gross implies have
  already elapsed (so a mid-year stub projects the rest of the year, not a full
  extra year on top of YTD).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from satc.ingest.readers.paystub import (
    LABEL_EMPLOYER,
    LABEL_FED_WH_CURRENT,
    LABEL_FED_WH_YTD,
    LABEL_GROSS_CURRENT,
    LABEL_GROSS_YTD,
    LABEL_PAY_FREQUENCY,
    LABEL_RETIREMENT_CURRENT,
)
from satc.withholding.models import PERIODS_PER_YEAR, ZERO, Paystub

_DEFAULT_FREQUENCY = "biweekly"


def _money(value: str | None) -> Decimal | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return Decimal(str(value).replace(",", "").replace("$", "").strip())
    except InvalidOperation:
        return None


def paystub_from_fields(labeled: dict[str, str], *, name: str = "",
                        adjust_withholding: bool = False) -> Paystub:
    """Build an estimator :class:`Paystub` from confirmed reader labels."""
    freq = (labeled.get(LABEL_PAY_FREQUENCY) or _DEFAULT_FREQUENCY).lower()
    if freq not in PERIODS_PER_YEAR:
        freq = _DEFAULT_FREQUENCY
    ppy = PERIODS_PER_YEAR[freq]

    gross = _money(labeled.get(LABEL_GROSS_CURRENT))
    retire = _money(labeled.get(LABEL_RETIREMENT_CURRENT)) or ZERO
    fed = _money(labeled.get(LABEL_FED_WH_CURRENT)) or ZERO
    ytd_gross = _money(labeled.get(LABEL_GROSS_YTD))
    ytd_fed = _money(labeled.get(LABEL_FED_WH_YTD))

    taxable = (gross - retire) if gross is not None else None

    # Infer elapsed/remaining periods from the YTD gross vs the current gross.
    remaining: int | None = None
    ytd_taxable: Decimal | None = ytd_gross
    if ytd_gross is not None and gross is not None and gross > ZERO:
        elapsed = int((ytd_gross / gross).to_integral_value(rounding=ROUND_HALF_UP))
        elapsed = max(0, min(elapsed, ppy))
        remaining = ppy - elapsed
        # Keep the YTD taxable proxy consistent with the per-period netting.
        ytd_taxable = ytd_gross - retire * elapsed
        if ytd_taxable < ZERO:
            ytd_taxable = ZERO

    return Paystub(
        pay_frequency=freq,
        taxable_wages_per_period=taxable,
        gross_pay_per_period=gross or ZERO,
        federal_tax_withheld_per_period=fed,
        retirement_pretax_per_period=retire,
        ytd_taxable_wages=ytd_taxable,
        ytd_federal_tax_withheld=ytd_fed,
        pay_periods_remaining=remaining,
        name=name or labeled.get(LABEL_EMPLOYER, ""),
        adjust_withholding=adjust_withholding,
    )
