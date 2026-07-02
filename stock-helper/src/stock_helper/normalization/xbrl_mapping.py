"""Canonical metric registry: which XBRL tags map to which canonical metric.

Candidates are ordered by preference; normalization picks the candidate with the
best annual coverage and records the winning tag on every stored fact, so the
mapping decision is always auditable. Values are as-filed — companies using
custom extension tags simply yield an UNAVAILABLE metric (never a guess).
"""

from dataclasses import dataclass, field

FLOW = "flow"  # duration facts (income statement / cash flow)
INSTANT = "instant"  # balance-sheet facts


@dataclass(frozen=True)
class MetricSpec:
    key: str
    kind: str  # FLOW | INSTANT
    unit: str  # "USD" | "shares"
    label: str
    candidates: tuple[tuple[str, str], ...]  # (taxonomy, tag), in preference order
    notes: str = field(default="")


def _usgaap(*tags: str) -> tuple[tuple[str, str], ...]:
    return tuple(("us-gaap", tag) for tag in tags)


CANONICAL_METRICS: dict[str, MetricSpec] = {
    spec.key: spec
    for spec in [
        MetricSpec(
            "revenue", FLOW, "USD", "Revenue",
            _usgaap(
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "Revenues",
                "RevenueFromContractWithCustomerIncludingAssessedTax",
                "SalesRevenueNet",
            ),
            "Generic revenue tags; unreliable for banks (see banking notes).",
        ),
        MetricSpec(
            "cost_of_revenue", FLOW, "USD", "Cost of revenue",
            _usgaap("CostOfGoodsAndServicesSold", "CostOfRevenue", "CostOfGoodsSold"),
        ),
        MetricSpec("operating_income", FLOW, "USD", "Operating income",
                   _usgaap("OperatingIncomeLoss")),
        MetricSpec("net_income", FLOW, "USD", "Net income", _usgaap("NetIncomeLoss")),
        MetricSpec(
            "operating_cash_flow", FLOW, "USD", "Operating cash flow",
            _usgaap(
                "NetCashProvidedByUsedInOperatingActivities",
                "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
            ),
        ),
        MetricSpec(
            "capex", FLOW, "USD", "Capital expenditures",
            _usgaap(
                "PaymentsToAcquirePropertyPlantAndEquipment",
                "PaymentsToAcquireProductiveAssets",
            ),
            "Purchases of PP&E only; excludes acquisitions.",
        ),
        MetricSpec("interest_expense", FLOW, "USD", "Interest expense",
                   _usgaap("InterestExpense", "InterestAndDebtExpense")),
        MetricSpec(
            "buybacks", FLOW, "USD", "Share repurchases",
            _usgaap("PaymentsForRepurchaseOfCommonStock"),
            "Gross repurchases from the cash flow statement.",
        ),
        MetricSpec("dividends_paid", FLOW, "USD", "Dividends paid",
                   _usgaap("PaymentsOfDividendsCommonStock", "PaymentsOfDividends")),
        MetricSpec(
            "diluted_shares", FLOW, "shares", "Diluted shares (wtd avg)",
            _usgaap(
                "WeightedAverageNumberOfDilutedSharesOutstanding",
                "WeightedAverageNumberOfSharesOutstandingBasic",
            ),
        ),
        MetricSpec("total_assets", INSTANT, "USD", "Total assets", _usgaap("Assets")),
        MetricSpec("total_liabilities", INSTANT, "USD", "Total liabilities",
                   _usgaap("Liabilities")),
        MetricSpec(
            "equity", INSTANT, "USD", "Stockholders' equity",
            _usgaap(
                "StockholdersEquity",
                "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
            ),
        ),
        MetricSpec(
            "cash", INSTANT, "USD", "Cash & equivalents",
            _usgaap(
                "CashAndCashEquivalentsAtCarryingValue",
                "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
            ),
        ),
        MetricSpec("current_assets", INSTANT, "USD", "Current assets",
                   _usgaap("AssetsCurrent"),
                   "Absent for filers without classified balance sheets (incl. banks)."),
        MetricSpec("current_liabilities", INSTANT, "USD", "Current liabilities",
                   _usgaap("LiabilitiesCurrent")),
        MetricSpec("long_term_debt", INSTANT, "USD", "Long-term debt",
                   _usgaap("LongTermDebtNoncurrent", "LongTermDebt")),
        MetricSpec("short_term_debt", INSTANT, "USD", "Short-term debt",
                   _usgaap("DebtCurrent", "LongTermDebtCurrent")),
        # Banking-specific (face XBRL where available)
        MetricSpec("deposits", INSTANT, "USD", "Total deposits", _usgaap("Deposits"),
                   "Banking only. Mix of interest/non-interest-bearing not visible here."),
        MetricSpec(
            "credit_loss_allowance", INSTANT, "USD", "Allowance for credit losses",
            _usgaap(
                "FinancingReceivableAllowanceForCreditLossExcludingAccruedInterest",
                "FinancingReceivableAllowanceForCreditLosses",
                "LoansAndLeasesReceivableAllowance",
            ),
            "Banking only. CECL adoption (~2020) breaks tag comparability across years.",
        ),
    ]
}
