"""XBRL (us-gaap) concept tag mappings.

Companies tag inconsistently and tags evolve over time, so each financial
line item is resolved from a PRIORITY-ORDERED list of candidate tags: the
highest-priority tag that has a value for a given fiscal year wins. This is
documented and auditable rather than silently guessed.

``DURATION`` concepts are income-statement / cash-flow flows reported over a
period (have a ``start`` and ``end``). ``INSTANT`` concepts are balance-sheet
stocks reported at a point in time (``end`` only).
"""

from __future__ import annotations

# --- Income statement (duration) -------------------------------------------
REVENUE = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
    "SalesRevenueGoodsNet",
]

COST_OF_REVENUE = [
    "CostOfGoodsAndServicesSold",
    "CostOfRevenue",
    "CostOfGoodsSold",
]

GROSS_PROFIT = ["GrossProfit"]

OPERATING_INCOME = ["OperatingIncomeLoss"]

NET_INCOME = [
    "NetIncomeLoss",
    "ProfitLoss",
    "NetIncomeLossAvailableToCommonStockholdersBasic",
]

INTEREST_EXPENSE = [
    "InterestExpense",
    "InterestExpenseDebt",
    "InterestAndDebtExpense",
    "InterestExpenseNonoperating",
]

INCOME_TAX = ["IncomeTaxExpenseBenefit"]

DEP_AMORT = [
    "DepreciationDepletionAndAmortization",
    "DepreciationAmortizationAndAccretionNet",
    "DepreciationAndAmortization",
]
# Components used only when a combined D&A tag is absent.
DEPRECIATION_ONLY = ["Depreciation", "DepreciationNonproduction"]
AMORTIZATION_ONLY = [
    "AmortizationOfIntangibleAssets",
    "AmortizationOfFinancingCostsAndDiscounts",
]

CAPEX = [
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsToAcquireProductiveAssets",
    "PaymentsForCapitalImprovements",
]

# --- Balance sheet (instant) -----------------------------------------------
ASSETS = ["Assets"]
ASSETS_CURRENT = ["AssetsCurrent"]
LIABILITIES_CURRENT = ["LiabilitiesCurrent"]

CASH = [
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    "CashAndCashEquivalentsAtCarryingValueIncludingDiscontinuedOperations",
]

INVENTORY = ["InventoryNet"]

RECEIVABLES = [
    "AccountsReceivableNetCurrent",
    "ReceivablesNetCurrent",
]

PAYABLES = [
    "AccountsPayableCurrent",
    "AccountsPayableTradeCurrent",
    "AccountsPayableAndAccruedLiabilitiesCurrent",
]

# Debt components (instant). Total debt is reconstructed in metrics.py from
# these with a documented precedence to avoid double-counting current
# maturities.
LONG_TERM_DEBT_NONCURRENT = ["LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations"]
LONG_TERM_DEBT_CURRENT = ["LongTermDebtCurrent", "LongTermDebtAndCapitalLeaseObligationsCurrent"]
LONG_TERM_DEBT_TOTAL = ["LongTermDebt"]
SHORT_TERM_DEBT = ["ShortTermBorrowings", "DebtCurrent"]
