"""Seed Signal Dictionary (spec section 6).

These series ids are verified against FRED. Thresholds are deliberate rough
starting points to calibrate after 2-3 months of live observation. The
quarterly credit benchmarks anchor an industry-vs-our-book comparison rather
than month-to-month flags.

Materialised into the workbook's ``Signal Dictionary`` sheet on first run; the
owner then tunes thresholds there and the engine reads the sheet next time.
"""

from __future__ import annotations

from redflag_monitor.config import Signal

# (series_id, label, category, native_frequency, threshold_type,
#  threshold_value, direction, notes)
_SEED: list[tuple[str, str, str, str, str, float, str, str]] = [
    # --- Rates (daily; level and change both matter) ----------------------
    ("DFF", "Fed Funds Effective Rate", "Rate", "daily", "abs_change", 0.25, "both",
     "Policy rate; drives funding + card APRs"),
    ("DGS10", "10-Yr Treasury", "Rate", "daily", "abs_change", 0.50, "both",
     "Term funding / benchmark"),
    ("DGS2", "2-Yr Treasury", "Rate", "daily", "abs_change", 0.50, "both",
     "Short end"),
    ("T10Y2Y", "10Y-2Y Spread", "Rate", "daily", "level_below", 0.0, "down",
     "Inversion = recession signal"),
    ("SOFR", "Secured Overnight Financing Rate", "Rate", "daily", "abs_change", 0.25, "both",
     "Funding benchmark"),
    # --- Macro (monthly/quarterly; borrower-capacity stress) --------------
    ("UNRATE", "Unemployment Rate", "Macro", "monthly", "abs_change", 0.20, "up",
     "Labor deterioration -> consumer stress"),
    ("CPIAUCSL", "CPI (All Urban, SA)", "Macro", "monthly", "yoy_change", 1.0, "up",
     "Inflation squeezes repayment capacity"),
    ("UMCSENT", "Consumer Sentiment (UMich)", "Macro", "monthly", "pct_change", 10.0, "down",
     "Leading demand / stress signal"),
    ("PSAVERT", "Personal Saving Rate", "Macro", "monthly", "abs_change", 1.0, "down",
     "Thin savings buffer = repayment risk"),
    ("TDSP", "Household Debt Service Ratio", "Macro", "quarterly", "abs_change", 0.30, "up",
     "Household leverage / payment burden"),
    # --- Consumer-credit benchmarks (quarterly; the peer comparison) ------
    ("DRCCLACBS", "Delinquency Rate, Credit Card Loans, All Comm. Banks",
     "Credit-Benchmark", "quarterly", "abs_change", 0.20, "up",
     "Industry card DQ - compare to your book"),
    ("CORCCACBS", "Charge-Off Rate, Credit Card Loans, All Comm. Banks",
     "Credit-Benchmark", "quarterly", "abs_change", 0.30, "up",
     "Industry card losses"),
    ("DRCLACBS", "Delinquency Rate, Consumer Loans, All Comm. Banks",
     "Credit-Benchmark", "quarterly", "abs_change", 0.20, "up",
     "Broad consumer DQ"),
    ("TERMCBCCALLNS", "Comm. Bank Interest Rate on Credit Card Plans",
     "Credit-Benchmark", "monthly", "abs_change", 0.50, "both",
     "Industry card APR; pricing context. Labeled monthly but populates ~quarterly."),
]


def seed_signals() -> list[Signal]:
    """Return the seed signal set, all active."""
    return [
        Signal(
            series_id=series_id,
            label=label,
            category=category,
            source="FRED",
            native_frequency=frequency,
            threshold_type=threshold_type,
            threshold_value=threshold_value,
            direction_that_matters=direction,
            active=True,
            notes=notes,
        )
        for (series_id, label, category, frequency, threshold_type,
             threshold_value, direction, notes) in _SEED
    ]
