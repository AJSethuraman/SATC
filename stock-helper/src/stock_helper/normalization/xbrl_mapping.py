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
    unit: str  # "USD" | "shares" | "USD/shares" (per-share; matches SEC unit key)
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
        MetricSpec(
            "net_interest_income", FLOW, "USD", "Net interest income",
            _usgaap(
                "InterestIncomeExpenseNet",
                "InterestIncomeExpenseAfterProvisionForLoanLoss",
            ),
            "Banking only. Second candidate is after provision — noted in signal caveat.",
        ),
        MetricSpec(
            "nonperforming_loans", INSTANT, "USD", "Nonaccrual / nonperforming loans",
            _usgaap(
                "FinancingReceivableNonaccrualStatus",  # post-CECL (2020+)
                "FinancingReceivableRecordedInvestmentNonaccrualStatus",  # pre-CECL
            ),
            "Banking only. Tag transition at CECL adoption; often disclosed only in tables.",
        ),
        MetricSpec(
            "charge_offs", FLOW, "USD", "Gross charge-offs",
            _usgaap(
                "FinancingReceivableAllowanceForCreditLossesWriteOffs",
                "AllowanceForLoanAndLeaseLossesWriteOffsNet",
            ),
            "Banking only. Gross vs net differs by tag; many filers disclose only in tables.",
        ),
        # --- Valuation / quality inputs (added for the valuation engine) -------
        # Point-in-time share count for market cap + per-share fair value. The
        # dei cover fact is dated ~weeks after fiscal year-end, so it is used ONLY
        # as a latest scalar (never joined to a fiscal period_end).
        MetricSpec(
            "shares_outstanding", INSTANT, "shares", "Shares outstanding",
            (
                ("dei", "EntityCommonStockSharesOutstanding"),
                ("us-gaap", "CommonStockSharesOutstanding"),
                ("us-gaap", "CommonStockSharesIssued"),
            ),
            "Latest scalar only; cover-date fact does not align to fiscal year-ends.",
        ),
        MetricSpec("gross_profit", FLOW, "USD", "Gross profit", _usgaap("GrossProfit"),
                   "Else derived as revenue - cost_of_revenue."),
        MetricSpec(
            "depreciation_amortization", FLOW, "USD", "Depreciation & amortization",
            _usgaap(
                "DepreciationDepletionAndAmortization",
                "DepreciationAmortizationAndAccretionNet",
                "DepreciationAndAmortization",
            ),
            "Cash-flow-statement D&A; may exceed income-statement D&A.",
        ),
        MetricSpec(
            "pretax_income", FLOW, "USD", "Pre-tax income",
            _usgaap(
                "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
            ),
        ),
        MetricSpec("tax_expense", FLOW, "USD", "Income tax expense",
                   _usgaap("IncomeTaxExpenseBenefit")),
        MetricSpec(
            "stock_based_comp", FLOW, "USD", "Stock-based compensation",
            _usgaap("ShareBasedCompensation", "ShareBasedCompensationExpense"),
            "Owner-earnings add-back; ignores future dilution (upper bound).",
        ),
        MetricSpec(
            "dividends_per_share", FLOW, "USD/shares", "Dividends per share",
            _usgaap(
                "CommonStockDividendsPerShareDeclared",
                "CommonStockDividendsPerShareCashPaid",
            ),
        ),
        MetricSpec("eps_diluted", FLOW, "USD/shares", "Diluted EPS",
                   _usgaap("EarningsPerShareDiluted")),
        MetricSpec("retained_earnings", INSTANT, "USD", "Retained earnings",
                   _usgaap("RetainedEarningsAccumulatedDeficit"),
                   "Altman X2."),
        MetricSpec("ppe_net", INSTANT, "USD", "Property, plant & equipment (net)",
                   _usgaap("PropertyPlantAndEquipmentNet"),
                   "Greenblatt tangible capital."),
        MetricSpec("goodwill", INSTANT, "USD", "Goodwill", _usgaap("Goodwill")),
        MetricSpec(
            "intangible_assets", INSTANT, "USD", "Intangible assets (ex-goodwill)",
            _usgaap("IntangibleAssetsNetExcludingGoodwill", "FiniteLivedIntangibleAssetsNet"),
        ),
        MetricSpec("inventory", INSTANT, "USD", "Inventory", _usgaap("InventoryNet")),
        MetricSpec(
            "accounts_receivable", INSTANT, "USD", "Accounts receivable",
            _usgaap("AccountsReceivableNetCurrent", "ReceivablesNetCurrent"),
        ),
        MetricSpec(
            "preferred_equity", INSTANT, "USD", "Preferred equity",
            _usgaap(
                "PreferredStockLiquidationPreferenceValue",
                "PreferredStockRedemptionAmount",
                "PreferredStockValue",
            ),
            "Liquidation/redemption value preferred; par (last candidate) is a weak fallback.",
        ),
        MetricSpec("minority_interest", INSTANT, "USD", "Minority interest",
                   _usgaap("MinorityInterest")),
        MetricSpec(
            "short_term_borrowings", INSTANT, "USD", "Short-term borrowings",
            _usgaap("ShortTermBorrowings", "CommercialPaper"),
            "Adds to total debt beyond current portion of long-term debt.",
        ),
        MetricSpec(
            "sga_expense", FLOW, "USD", "Selling, general & administrative",
            _usgaap(
                "SellingGeneralAndAdministrativeExpense",
                "GeneralAndAdministrativeExpense",
            ),
            "Beneish SGAI input.",
        ),
    ]
}
