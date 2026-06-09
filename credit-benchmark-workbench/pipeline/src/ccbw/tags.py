"""XBRL concept registry with tag-fallback chains.

Filers do not use a single canonical tag per concept: revenue alone appears
as ``Revenues``, ``RevenueFromContractWithCustomerExcludingAssessedTax``,
``SalesRevenueNet`` and others depending on filer and adoption year of
ASC 606. Each concept here carries an *ordered* chain of acceptable tags;
the parser walks the chain and records which tag actually supplied each
datapoint so provenance survives the fallback.
"""

from __future__ import annotations

from dataclasses import dataclass, field

DURATION = "duration"   # income statement / cash flow: has start + end
INSTANT = "instant"     # balance sheet: end only


@dataclass(frozen=True)
class ConceptSpec:
    name: str
    tags: tuple[str, ...]
    kind: str                  # DURATION or INSTANT
    unit: str = "USD"
    description: str = ""
    # Concepts whose absence should be surfaced as a coverage gap rather
    # than silently dropping the company-year.
    core: bool = False


CONCEPTS: dict[str, ConceptSpec] = {}


def _c(name: str, tags: list[str], kind: str, description: str, core: bool = False,
       unit: str = "USD") -> None:
    CONCEPTS[name] = ConceptSpec(
        name=name, tags=tuple(tags), kind=kind, description=description,
        core=core, unit=unit,
    )


# ---------------------------------------------------------------------- #
# Income statement / cash flow (duration)
# ---------------------------------------------------------------------- #

_c("revenue", [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "SalesRevenueNet",
    "SalesRevenueGoodsNet",
    "SalesRevenueServicesNet",
], DURATION, "Total revenue", core=True)

_c("cogs", [
    "CostOfRevenue",
    "CostOfGoodsAndServicesSold",
    "CostOfGoodsSold",
    "CostOfServices",
], DURATION, "Cost of revenue / goods sold")

_c("operating_income", [
    "OperatingIncomeLoss",
], DURATION, "Operating income (EBIT proxy)", core=True)

_c("depreciation_amortization", [
    "DepreciationDepletionAndAmortization",
    "DepreciationAmortizationAndAccretionNet",
    "DepreciationAndAmortization",
    "Depreciation",
], DURATION, "Depreciation & amortization (cash-flow statement presentation)",
   core=True)

_c("interest_expense", [
    "InterestExpense",
    "InterestExpenseDebt",
    "InterestAndDebtExpense",
    "InterestExpenseNonoperating",
], DURATION, "Interest expense", core=True)

_c("net_income", [
    "NetIncomeLoss",
    "ProfitLoss",
], DURATION, "Net income (ProfitLoss includes noncontrolling interests; "
             "comparability-noted when used)")

_c("capex", [
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsToAcquireProductiveAssets",
], DURATION, "Capital expenditure")

_c("operating_cash_flow", [
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
], DURATION, "Cash flow from operations")

_c("rent_expense", [
    "OperatingLeaseExpense",
    "OperatingLeasesRentExpenseNet",
    "OperatingLeasesRentExpenseMinimumRentals",
], DURATION, "Operating lease / rent expense (EBITDAR adjustments)")

# ---------------------------------------------------------------------- #
# Balance sheet (instant)
# ---------------------------------------------------------------------- #

_c("total_assets", ["Assets"], INSTANT, "Total assets", core=True)

_c("current_assets", ["AssetsCurrent"], INSTANT, "Total current assets")

_c("current_liabilities", ["LiabilitiesCurrent"], INSTANT,
   "Total current liabilities")

_c("total_liabilities", ["Liabilities"], INSTANT, "Total liabilities")

_c("cash", [
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
], INSTANT, "Cash and equivalents (second tag includes restricted cash; "
            "comparability-noted when used)")

_c("receivables", [
    "AccountsReceivableNetCurrent",
    "ReceivablesNetCurrent",
], INSTANT, "Trade receivables, net, current")

_c("inventory", ["InventoryNet"], INSTANT, "Inventory, net")

_c("payables", ["AccountsPayableCurrent"], INSTANT, "Trade payables, current")

_c("lt_debt_noncurrent", [
    "LongTermDebtNoncurrent",
    "LongTermDebtAndCapitalLeaseObligations",
], INSTANT, "Long-term debt, noncurrent portion", core=True)

_c("lt_debt_current", [
    "LongTermDebtCurrent",
    "LongTermDebtAndCapitalLeaseObligationsCurrent",
], INSTANT, "Current portion of long-term debt")

_c("debt_current_total", [
    "DebtCurrent",
], INSTANT, "All current debt (preferred over summing components when present)")

_c("short_term_borrowings", [
    "ShortTermBorrowings",
    "OtherShortTermBorrowings",
    "ShorttermDebtWeightedAverageInterestRate",  # never USD; kept as a known trap
], INSTANT, "Short-term borrowings / revolver draws")

_c("lt_debt_combined", [
    "LongTermDebt",
], INSTANT, "Long-term debt combined tag -- some filers report ONLY this; it "
            "may include the current portion (basis ambiguity is flagged "
            "when this fallback is used)")

_c("equity", [
    "StockholdersEquity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
], INSTANT, "Book equity")

_c("retained_earnings", [
    "RetainedEarningsAccumulatedDeficit",
], INSTANT, "Retained earnings (Altman Z-score input)")


# Tags acceptable per concept, as a quick lookup
ALL_TAGS: dict[str, str] = {
    tag: spec.name for spec in CONCEPTS.values() for tag in spec.tags
}
