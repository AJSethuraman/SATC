"""Tiered data model for unsecured consumer loan tapes.

This module is the single source of truth for the field-level data model that
drives BOTH the synthetic generator and the tier detector.  A "tape" is a
pandas DataFrame with one row per account per as-of month (a longitudinal
panel) or, for low-maturity clients, one row per account (a snapshot).

Data tiers
----------
Tier 0 (required minimum)
    account ID, product type, origination date, as-of date, balance,
    current delinquency status, charge-off flag.
Tier 1 (standard monitoring)
    Tier 0 plus credit limit / original amount, risk grade or score band,
    payment status, and -- structurally -- a monthly longitudinal panel
    (multiple as-of months per account) rather than a single snapshot.
Tier 2 (advanced analytics)
    Tier 1 plus score at origination and refreshed score, utilization over
    time, line-change history (original credit limit alongside the monthly
    limit), recovery detail, and original/remaining term (installment
    products only; not applicable to revolving cards).

Tape conventions
----------------
* ``delinquency_bucket`` uses the ordered labels in :data:`BUCKET_ORDER`.
  ``DPD120`` means 120-179 days past due; accounts charge off (move to
  ``CO``) at roughly 180 days, per Regulation/FFIEC charge-off timing for
  open-end credit.
* In the month an account charges off, ``charge_off_flag`` flips to 1 and
  ``balance`` holds the amount written off.  Any later rows for that
  account carry ``balance == 0`` and, at Tier 2, ``recovery_amount`` for
  post-charge-off collections.
* Money fields are in dollars (floats, cents precision); ``utilization``
  is a fraction (1.0 = fully drawn).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Column names (use these constants, not string literals, in engine code)
# ---------------------------------------------------------------------------
F_ACCOUNT_ID = "account_id"
F_PRODUCT_TYPE = "product_type"
F_ORIGINATION_DATE = "origination_date"
F_AS_OF_DATE = "as_of_date"
F_BALANCE = "balance"
F_DELINQUENCY_BUCKET = "delinquency_bucket"
F_CHARGE_OFF_FLAG = "charge_off_flag"

F_CREDIT_LIMIT = "credit_limit"
F_SCORE_BAND = "score_band"
F_PAYMENT_STATUS = "payment_status"

F_ORIG_SCORE = "orig_score"
F_CURRENT_SCORE = "current_score"
F_UTILIZATION = "utilization"
F_ORIG_CREDIT_LIMIT = "orig_credit_limit"
F_RECOVERY_AMOUNT = "recovery_amount"
F_ORIGINAL_TERM_MONTHS = "original_term_months"
F_REMAINING_TERM_MONTHS = "remaining_term_months"

# ---------------------------------------------------------------------------
# Tier field sets (generic; product modules may exclude non-applicable fields)
# ---------------------------------------------------------------------------
TIER0_FIELDS: frozenset[str] = frozenset(
    {
        F_ACCOUNT_ID,
        F_PRODUCT_TYPE,
        F_ORIGINATION_DATE,
        F_AS_OF_DATE,
        F_BALANCE,
        F_DELINQUENCY_BUCKET,
        F_CHARGE_OFF_FLAG,
    }
)

TIER1_ONLY_FIELDS: frozenset[str] = frozenset(
    {
        F_CREDIT_LIMIT,
        F_SCORE_BAND,
        F_PAYMENT_STATUS,
    }
)

TIER2_ONLY_FIELDS: frozenset[str] = frozenset(
    {
        F_ORIG_SCORE,
        F_CURRENT_SCORE,
        F_UTILIZATION,
        F_ORIG_CREDIT_LIMIT,
        F_RECOVERY_AMOUNT,
        F_ORIGINAL_TERM_MONTHS,
        F_REMAINING_TERM_MONTHS,
    }
)

#: Structural (non-column) requirement marker used by the tier detector and
#: by metric specs: a monthly longitudinal panel, i.e. multiple as-of months
#: observed per account.
PANEL_REQUIREMENT = "monthly_panel (multiple as_of_date months per account)"

# ---------------------------------------------------------------------------
# Categorical vocabularies
# ---------------------------------------------------------------------------
BUCKET_CURRENT = "CURRENT"
BUCKET_DPD30 = "DPD30"
BUCKET_DPD60 = "DPD60"
BUCKET_DPD90 = "DPD90"
BUCKET_DPD120 = "DPD120"  # 120-179 DPD; charge-off occurs at ~180 DPD
BUCKET_CO = "CO"

#: Delinquency buckets in severity order. ``CO`` is absorbing.
BUCKET_ORDER: tuple[str, ...] = (
    BUCKET_CURRENT,
    BUCKET_DPD30,
    BUCKET_DPD60,
    BUCKET_DPD90,
    BUCKET_DPD120,
    BUCKET_CO,
)

#: Buckets that count as delinquent-but-not-charged-off.
DELINQUENT_BUCKETS: tuple[str, ...] = (
    BUCKET_DPD30,
    BUCKET_DPD60,
    BUCKET_DPD90,
    BUCKET_DPD120,
)

#: Score bands in best-to-worst order, with refreshed-score ranges.
SCORE_BANDS: tuple[str, ...] = ("SUPER_PRIME", "PRIME", "NEAR_PRIME", "SUBPRIME")
SCORE_BAND_RANGES: dict[str, tuple[int, int]] = {
    "SUPER_PRIME": (760, 850),
    "PRIME": (660, 759),
    "NEAR_PRIME": (600, 659),
    "SUBPRIME": (520, 599),
}

PAYMENT_STATUSES: tuple[str, ...] = ("FULL_PAY", "MIN_PAY", "PARTIAL_PAY", "NO_PAY")

#: Product type codes. Phase 1 implements CREDIT_CARD end to end; the other
#: two products only define the interface they will implement in Phase 2.
PRODUCT_CREDIT_CARD = "CREDIT_CARD"
PRODUCT_PERSONAL_LOAN = "PERSONAL_LOAN"
PRODUCT_STUDENT_LOAN = "STUDENT_LOAN"

#: Credit-limit ("line size") concentration buckets for cards.
LINE_SIZE_EDGES: tuple[float, ...] = (0.0, 2500.0, 5000.0, 10000.0, 20000.0, float("inf"))
LINE_SIZE_LABELS: tuple[str, ...] = ("<$2.5K", "$2.5K-5K", "$5K-10K", "$10K-20K", "$20K+")
