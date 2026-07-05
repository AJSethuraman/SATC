"""The canonical-field contract.

Messy real-world flat files carry the same concept under a hundred header
spellings and two or three unit conventions. This module is the single
declaration of *what a field means* to the bench: its canonical id, its data
type, whether it is load-bearing, the unit conventions it may arrive in, and
the header aliases used to auto-propose a mapping (Slice-1 mapping layer).

Roles (PRD R1):

- ``UNIVERSAL``      — the file will not load without it. These are the two
  truly load-bearing fields: the row identity and the balance every dollar
  weighting divides by.
- ``FEATURE_GATED``  — the file still loads, but a *specific* analysis refuses
  (with a named-missing-field message) when the field is absent. Delinquency
  and URCCP need the delinquency signal + product shape; a weighted average
  needs its own attribute; vintage needs the origination date; and so on.
- ``OPTIONAL_SLICE`` — a dimension that lights up group-bys/cohorts when
  present and is cleanly absent otherwise (including the open-ended ad-hoc
  tail).

Units are captured per mapped column at confirm time (Slice-1 mapping) so a
rate stored as ``7.25`` and a rate stored as ``0.0725`` both normalize to a
fraction before any weighting — the L8-class "silently 100x off" trap.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --- data types ------------------------------------------------------------
# dtype drives parsing/validation in the cleaning gate and formatting on output.
TEXT = "text"
USD = "usd"        # a dollar amount; weight/denominator material
NUM = "num"        # a plain number (score, months)
RATIO = "ratio"    # a proportion that may arrive as fraction OR percent
DATE = "date"

# --- unit conventions ------------------------------------------------------
# For RATIO fields the reviewer declares which convention the column arrived in;
# the cleaning gate rescales PERCENT -> FRACTION and records it.
UNIT_FRACTION = "fraction"   # 0.0725, 0.43
UNIT_PERCENT = "percent"     # 7.25, 43
RATIO_UNITS = (UNIT_FRACTION, UNIT_PERCENT)

# --- roles -----------------------------------------------------------------
UNIVERSAL = "universal"
FEATURE_GATED = "feature_gated"
OPTIONAL_SLICE = "optional_slice"


@dataclass(frozen=True)
class CanonicalField:
    """One declared field in the contract."""

    id: str
    label: str
    dtype: str
    role: str
    aliases: tuple[str, ...] = ()
    units: tuple[str, ...] = ()           # non-empty only for ambiguous-scale fields
    feature: str | None = None            # which analysis this field gates
    help: str = ""

    @property
    def ambiguous_units(self) -> bool:
        return bool(self.units)


def _norm(s: str) -> str:
    """Normalize a header/alias to its comparable core: lowercase alphanumerics."""
    return "".join(ch for ch in str(s).lower() if ch.isalnum())


# ---------------------------------------------------------------------------
# The contract. Slice 1 needs only identity + balance + one attribute (FICO)
# to demonstrate the full path; later slices extend this registry (delinquency,
# product shape, DTI/LTV, dates, charge-off, prior bucket). New fields are
# data, not code.
# ---------------------------------------------------------------------------
_FIELDS: tuple[CanonicalField, ...] = (
    CanonicalField(
        id="loan_id", label="Loan / account number", dtype=TEXT, role=UNIVERSAL,
        aliases=("loan_id", "loan_number", "loan_no", "account_number",
                 "account_no", "acct", "acct_no", "note_number", "id"),
        help="Row identity and the file-pull key for linesheet review.",
    ),
    CanonicalField(
        id="current_balance", label="Current balance (UPB)", dtype=USD, role=UNIVERSAL,
        aliases=("current_balance", "current_upb", "upb", "outstanding_balance",
                 "principal_balance", "curr_bal", "balance", "bal",
                 "current_principal", "ending_balance"),
        help="Unpaid principal balance; the default weight for every WA metric.",
    ),
    CanonicalField(
        id="orig_amount", label="Original loan amount", dtype=USD, role=OPTIONAL_SLICE,
        aliases=("orig_amount", "original_amount", "original_balance",
                 "orig_balance", "loan_amount", "amount_financed", "note_amount"),
        help="Origination amount; the denominator for vintage cohort curves.",
    ),
    CanonicalField(
        id="fico_orig", label="FICO at origination", dtype=NUM, role=FEATURE_GATED,
        feature="wa_fico_orig",
        aliases=("fico_orig", "orig_fico", "origination_fico", "fico_at_orig",
                 "fico", "credit_score", "score", "bureau_score", "fico_score"),
        help="Origination bureau score. Weighted by current UPB.",
    ),
    CanonicalField(
        id="fico_refresh", label="FICO refreshed", dtype=NUM, role=FEATURE_GATED,
        feature="wa_fico_refresh",
        aliases=("fico_refresh", "refreshed_fico", "current_fico", "fico_current",
                 "updated_score", "refresh_score"),
        help="Refreshed bureau score; a distinct axis from origination FICO.",
    ),
    CanonicalField(
        id="dti", label="Debt-to-income (back-end)", dtype=RATIO, role=FEATURE_GATED,
        feature="wa_dti", units=RATIO_UNITS,
        aliases=("dti", "back_end_dti", "dti_ratio", "debt_to_income",
                 "backend_dti", "dti_back"),
        help="Back-end DTI at origination. Weighted by current UPB.",
    ),
    CanonicalField(
        id="rate", label="Note rate / APR", dtype=RATIO, role=FEATURE_GATED,
        feature="wa_rate", units=RATIO_UNITS,
        aliases=("rate", "note_rate", "apr", "interest_rate", "coupon", "int_rate"),
        help="Note rate/coupon. Balance-weighted = WAC.",
    ),
    CanonicalField(
        id="ltv", label="Loan-to-value (or CLTV)", dtype=RATIO, role=FEATURE_GATED,
        feature="wa_ltv", units=RATIO_UNITS,
        aliases=("ltv", "cltv", "loan_to_value", "combined_ltv", "current_ltv"),
        help="Secured consumer only. Also the URCCP residential ≥90-DPD qualifier.",
    ),
    # --- delinquency signal: exactly one of the three forms must be mapped for
    #     any delinquency/URCCP analysis (feature "delinquency"). ---
    CanonicalField(
        id="dpd_days", label="Days past due (count)", dtype=NUM, role=FEATURE_GATED,
        feature="delinquency",
        aliases=("dpd", "dpd_days", "days_past_due", "days_delinquent",
                 "days_pastdue", "delinquency_days", "past_due_days"),
        help="Actual DPD day count. Bucketized to the canonical delinquency buckets.",
    ),
    CanonicalField(
        id="dpd_bucket", label="Delinquency bucket (label)", dtype=TEXT, role=FEATURE_GATED,
        feature="delinquency",
        aliases=("dpd_bucket", "delinquency_bucket", "aging_bucket",
                 "aging", "bucket", "delq_bucket"),
        help="A pre-bucketed aging label (e.g. '30-59', '90-119', '180+').",
    ),
    CanonicalField(
        id="dpd_status", label="Delinquency status (code)", dtype=TEXT, role=FEATURE_GATED,
        feature="delinquency",
        aliases=("dpd_status", "delinquency_status", "loan_status",
                 "performance_status", "delq_status"),
        help="A status code mapped to a canonical bucket via [DELQ_STATUS] config.",
    ),
    CanonicalField(
        id="structure", label="Open/closed-end structure", dtype=TEXT, role=FEATURE_GATED,
        feature="urccp",
        aliases=("structure", "classification_type", "open_closed",
                 "loan_structure", "end_type", "open_closed_end"),
        help="closed_end | open_end | residential_secured — the URCCP branch.",
    ),
    CanonicalField(
        id="product_type", label="Product type", dtype=TEXT, role=OPTIONAL_SLICE,
        aliases=("product", "product_type", "loan_type", "portfolio", "product_code"),
        help="card / auto / personal / HELOC / student ... a slice dimension.",
    ),
    CanonicalField(
        id="orig_date", label="Origination date", dtype=DATE, role=FEATURE_GATED,
        feature="vintage",
        aliases=("orig_date", "origination_date", "open_date", "note_date",
                 "funding_date", "booked_date", "opened_date"),
        help="Booking date; defines the vintage cohort and MOB.",
    ),
    CanonicalField(
        id="chargeoff_flag", label="Charged-off flag", dtype=TEXT, role=FEATURE_GATED,
        feature="loss",
        aliases=("chargeoff_flag", "charged_off", "co_flag", "is_chargeoff",
                 "writeoff_flag", "charge_off_flag"),
        help="Truthy where the loan was charged off in the period.",
    ),
    CanonicalField(
        id="chargeoff_date", label="Charge-off date", dtype=DATE, role=FEATURE_GATED,
        feature="loss",
        aliases=("chargeoff_date", "co_date", "charge_off_date", "writeoff_date"),
        help="Charge-off date; positions the loss on the vintage MOB triangle.",
    ),
    CanonicalField(
        id="chargeoff_balance", label="Charged-off balance", dtype=USD, role=FEATURE_GATED,
        feature="loss",
        aliases=("chargeoff_balance", "co_amount", "charged_off_amount",
                 "charge_off_amount", "writeoff_amount", "co_balance"),
        help="Balance at charge-off; the gross charge-off numerator (no recoveries).",
    ),
    CanonicalField(
        id="prior_dpd_bucket", label="Prior DPD bucket", dtype=TEXT, role=FEATURE_GATED,
        feature="roll",
        aliases=("prior_dpd_bucket", "prior_bucket", "prev_bucket",
                 "beginning_bucket", "prior_status", "prior_delq"),
        help="Prior-period delinquency bucket; enables the single-period roll matrix.",
    ),
)

_BY_ID = {f.id: f for f in _FIELDS}
# alias -> field id (normalized), plus the canonical id itself as an alias.
_ALIAS_INDEX: dict[str, str] = {}
for _f in _FIELDS:
    for _a in (_f.id, *_f.aliases):
        _ALIAS_INDEX[_norm(_a)] = _f.id


def all_fields() -> tuple[CanonicalField, ...]:
    return _FIELDS


def get(field_id: str) -> CanonicalField:
    return _BY_ID[field_id]


def universal_ids() -> tuple[str, ...]:
    return tuple(f.id for f in _FIELDS if f.role == UNIVERSAL)


def field_for_alias(header: str) -> str | None:
    """Exact (normalized) alias hit for a raw header, or None."""
    return _ALIAS_INDEX.get(_norm(header))


def normalize_header(header: str) -> str:
    return _norm(header)


# The three interchangeable delinquency-signal forms; exactly one is needed for
# any delinquency/URCCP analysis.
DELINQUENCY_FORMS = ("dpd_days", "dpd_bucket", "dpd_status")


def fields_for_feature(feature: str) -> tuple[str, ...]:
    return tuple(f.id for f in _FIELDS if f.feature == feature)
