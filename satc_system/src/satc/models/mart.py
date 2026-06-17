"""WORKING DATA MART — normalized, year-over-year, de-identified.

One record per client per tax year per return/jurisdiction, plus normalized
child tables for line items, carryforwards, per-owner basis/capital, estimated
payments, and engagement/fee data. No PII: clients are referenced by
``client_id`` (resolved only in the vault). Documents are referenced by id/link.

Every dataclass here maps 1:1 to a SQL table; the field that would be the SQL
primary key is named explicitly. There is no data in merged cells and no nesting
that cannot be flattened — the model ports to a relational database unchanged.
Stable composite keys are built by :mod:`satc.ids`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Literal

from satc.models.provenance import Provenance

# ---------------------------------------------------------------------------
# Controlled vocabularies (port to SQL lookup tables / enums)
# ---------------------------------------------------------------------------

# Pipeline status drives the practice dashboards.
PipelineStatus = Literal[
    "Awaiting docs", "In prep", "In review", "Ready to file", "Filed", "Accepted", "Rejected",
]

# Carryforward kinds the mart stores and rolls forward. Drake computes these; the
# mart STORES and CARRIES them so we always hold each client's record-level data
# year to year and can seed next year (proforma).
CarryforwardKind = Literal[
    "NOL",                      # net operating loss (federal/state)
    "CAP_LOSS_ST",              # short-term capital loss carryover
    "CAP_LOSS_LT",              # long-term capital loss carryover
    "SEC179_DISALLOWED",        # §179 expense disallowed (income limit) carryover
    "PASSIVE_LOSS",             # suspended passive activity loss
    "CHARITABLE",               # charitable contribution carryover
    "AMT_CREDIT",               # minimum tax credit carryforward
    "QBI_LOSS",                 # §199A qualified business loss carryforward
    "QBI_REIT_PTP",             # §199A REIT/PTP loss carryforward
    "STATE_OVERPAYMENT_APPLIED",# state overpayment applied to next year
    "FEDERAL_OVERPAYMENT_APPLIED",
    "FOREIGN_TAX_CREDIT",       # FTC carryover
    "OTHER",
]

ResidencyStatus = Literal["FULL_YEAR", "PART_YEAR", "NONRESIDENT", "NA"]


# ---------------------------------------------------------------------------
# Core tables
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ReturnRecord:
    """Return register — the spine of the mart. PK = ``return_key``."""

    return_key: str             # ids.return_key(client_id, tax_year, return_type, jurisdiction)
    client_id: str
    tax_year: int
    return_type: str            # "1040" | "1120S" | "1065" | "1120"
    jurisdiction: str           # "US" | "OH" | "MI" | "MA" | ...
    status: PipelineStatus = "Awaiting docs"
    preparer_id: str = ""       # seam for multiple preparers; "" = solo default
    residency: ResidencyStatus = "NA"
    is_extended: bool = False
    filed_date: date | None = None
    accepted_date: date | None = None
    # Headline results stored at the return level for fast dashboards / comparison.
    refund_amount: Decimal | None = None
    balance_due_amount: Decimal | None = None
    note: str = ""


@dataclass(slots=True)
class LineItem:
    """Normalized line-level fact table. PK = (line_item_key)."""

    line_item_key: str          # ids.line_item_key(return_key, schedule, line)
    return_key: str
    schedule: str               # e.g. "1040", "SCH_C", "SCH_E", "K1", "M1", "SCH_L"
    line_code: str              # e.g. "1a", "8b", "QBI", "APPORTION_FACTOR"
    label: str
    amount: Decimal | None = None
    text_value: str = ""        # for non-numeric facts (codes, flags)
    provenance: Provenance | None = None


@dataclass(slots=True)
class Carryforward:
    """Carryforward register — drives roll-forward / proforma. PK = ``cf_id``."""

    cf_id: str
    client_id: str
    return_type: str
    jurisdiction: str
    kind: CarryforwardKind
    tax_year_generated: int     # year the carryforward arose
    amount: Decimal
    applied_to_year: int | None = None   # year it was consumed (None = still open)
    expires_after_year: int | None = None
    note: str = ""
    provenance: Provenance | None = None


@dataclass(slots=True)
class OwnerBasis:
    """Per-owner basis & capital-account rollforward for 1120-S / 1065.

    PK = (return_key, owner_id, tax_year). For 1120-S ``stock_basis`` /
    ``debt_basis`` apply; for 1065 ``capital_account`` (tax basis) applies. The
    rollforward columns mirror the K-1 basis worksheet so the ending balance of
    year Y becomes the beginning balance of year Y+1.
    """

    return_key: str
    client_id: str
    owner_id: str               # opaque per-owner handle (vault resolves identity)
    tax_year: int
    beginning_balance: Decimal = Decimal("0")
    contributions: Decimal = Decimal("0")
    income_items: Decimal = Decimal("0")     # K-1 income increasing basis
    loss_items: Decimal = Decimal("0")       # K-1 loss/deductions decreasing basis
    distributions: Decimal = Decimal("0")
    ending_balance: Decimal = Decimal("0")
    # 1120-S only: debt basis tracked separately from stock basis.
    debt_basis_beginning: Decimal = Decimal("0")
    debt_basis_ending: Decimal = Decimal("0")
    ownership_pct: Decimal | None = None
    provenance: Provenance | None = None


@dataclass(slots=True)
class EstimatePayment:
    """Estimated-payment history. PK = ``payment_id``."""

    payment_id: str
    client_id: str
    tax_year: int
    jurisdiction: str
    period: str                 # "Q1" | "Q2" | "Q3" | "Q4" | "EXT" | "APPLIED_PRIOR"
    amount: Decimal
    paid_date: date | None = None
    provenance: Provenance | None = None


@dataclass(slots=True)
class EngagementRecord:
    """Engagement & fee data (lightweight). PK = (client_id, tax_year)."""

    client_id: str
    tax_year: int
    engagement_letter_status: str = "Not sent"   # Not sent / Sent / Signed
    fee_amount: Decimal | None = None
    invoiced: bool = False
    paid: bool = False
    preparer_id: str = ""
    note: str = ""


@dataclass(slots=True)
class DataMart:
    """In-memory container for the normalized tables (one per SQL table)."""

    public_clients: list = field(default_factory=list)        # PublicClient
    returns: list[ReturnRecord] = field(default_factory=list)
    line_items: list[LineItem] = field(default_factory=list)
    carryforwards: list[Carryforward] = field(default_factory=list)
    owner_basis: list[OwnerBasis] = field(default_factory=list)
    estimate_payments: list[EstimatePayment] = field(default_factory=list)
    engagements: list[EngagementRecord] = field(default_factory=list)
