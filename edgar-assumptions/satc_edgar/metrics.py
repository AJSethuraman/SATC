"""Per-company / per-fiscal-year financial extraction and metric computation.

Pipeline:
  1. ``extract_annual_financials`` parses a companyfacts payload into one
     record per fiscal year of raw line items (revenue, EBITDA components,
     debt, working-capital items, ...).
  2. ``compute_metrics`` derives the four metric families from those raw
     items, returning ``None`` (never an imputed value) for any metric whose
     inputs are missing or whose denominator is zero, and recording WHY.

EBITDA is not an XBRL tag and is reconstructed:
  * Method "oi+da"  : OperatingIncomeLoss + D&A      (preferred)
  * Method "ni+...":  NetIncomeLoss + InterestExpense + IncomeTax + D&A
A company-year with no usable EBITDA is kept for non-EBITDA metrics, and the
EBITDA-based metrics are recorded as missing with a reason.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import concepts

DAYS_IN_YEAR = 365.0


# --------------------------------------------------------------------------
# Raw extraction
# --------------------------------------------------------------------------
def _days_between(start: str, end: str) -> Optional[int]:
    try:
        s = _dt.date.fromisoformat(start)
        e = _dt.date.fromisoformat(end)
    except (TypeError, ValueError):
        return None
    return (e - s).days


def _annual_points(dps: List[Dict[str, Any]], duration: bool) -> Dict[int, float]:
    """Reduce a list of XBRL data points to one annual value per fiscal year.

    Keeps only annual (FY) figures from 10-K filings. For duration concepts the
    period must span ~one year (340-380 days) to exclude mislabeled quarters.
    When the same fiscal year appears in multiple filings (restatements), the
    latest-filed value wins; ties broken deterministically by accession.
    """
    chosen: Dict[int, tuple] = {}  # fy -> (filed, accn, val)
    for dp in dps:
        form = str(dp.get("form", ""))
        if not form.startswith("10-K"):
            continue
        if dp.get("fp") != "FY":
            continue
        fy = dp.get("fy")
        if fy is None:
            continue
        start = dp.get("start")
        end = dp.get("end")
        if duration:
            if not start or not end:
                continue
            d = _days_between(start, end)
            if d is None or d < 340 or d > 380:
                continue
        else:
            if start:  # instant concepts have no start
                continue
        val = dp.get("val")
        if val is None:
            continue
        try:
            fy_int = int(fy)
        except (TypeError, ValueError):
            continue
        filed = str(dp.get("filed", ""))
        accn = str(dp.get("accn", ""))
        cur = chosen.get(fy_int)
        if cur is None or (filed, accn) > (cur[0], cur[1]):
            chosen[fy_int] = (filed, accn, float(val))
    return {fy: v[2] for fy, v in chosen.items()}


def _get_concept(gaap: Dict[str, Any], tags: List[str], duration: bool) -> Dict[int, float]:
    """Resolve a line item across priority-ordered tags -> {fiscal_year: value}.

    For each fiscal year the highest-priority tag that has a value wins, so a
    company that switched tags over time still yields a continuous series.
    """
    out: Dict[int, float] = {}
    for tag in tags:  # high priority first
        node = gaap.get(tag)
        if not isinstance(node, dict):
            continue
        units = node.get("units", {})
        dps = units.get("USD")
        if not dps:
            continue
        for fy, val in _annual_points(dps, duration).items():
            out.setdefault(fy, val)  # earlier (higher-priority) tag wins
    return out


@dataclass
class CompanyYear:
    """Raw line items for one company in one fiscal year."""

    cik: int
    name: str
    ticker: str
    fiscal_year: int
    # raw line items (USD); None when not tagged
    revenue: Optional[float] = None
    cost_of_revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_income: Optional[float] = None
    net_income: Optional[float] = None
    interest_expense: Optional[float] = None
    income_tax: Optional[float] = None
    dep_amort: Optional[float] = None
    capex: Optional[float] = None
    assets: Optional[float] = None
    assets_current: Optional[float] = None
    liabilities_current: Optional[float] = None
    cash: Optional[float] = None
    inventory: Optional[float] = None
    receivables: Optional[float] = None
    payables: Optional[float] = None
    total_debt: Optional[float] = None
    # provenance / quality
    ebitda: Optional[float] = None
    ebitda_method: str = ""
    debt_method: str = ""
    notes: List[str] = field(default_factory=list)


def _combine_da(gaap: Dict[str, Any]) -> Dict[int, float]:
    """D&A per year: prefer a combined tag, else sum depreciation+amortization."""
    combined = _get_concept(gaap, concepts.DEP_AMORT, duration=True)
    dep = _get_concept(gaap, concepts.DEPRECIATION_ONLY, duration=True)
    amort = _get_concept(gaap, concepts.AMORTIZATION_ONLY, duration=True)
    out: Dict[int, float] = {}
    years = set(combined) | set(dep) | set(amort)
    for fy in years:
        if fy in combined:
            out[fy] = combined[fy]
        elif fy in dep or fy in amort:
            out[fy] = dep.get(fy, 0.0) + amort.get(fy, 0.0)
    return out


def _total_debt(gaap: Dict[str, Any]) -> Dict[int, tuple]:
    """Reconstruct total debt per year -> {fy: (value, method)}.

    Precedence (documented to avoid double-counting current maturities):
      1. LongTermDebtNoncurrent + LongTermDebtCurrent + short-term  ("components")
      2. LongTermDebt (treated as total LT incl. current) + short-term ("ltd_total")
      3. short-term only  ("short_only")
    """
    ltd_nc = _get_concept(gaap, concepts.LONG_TERM_DEBT_NONCURRENT, duration=False)
    ltd_c = _get_concept(gaap, concepts.LONG_TERM_DEBT_CURRENT, duration=False)
    ltd_total = _get_concept(gaap, concepts.LONG_TERM_DEBT_TOTAL, duration=False)
    st = _get_concept(gaap, concepts.SHORT_TERM_DEBT, duration=False)

    out: Dict[int, tuple] = {}
    years = set(ltd_nc) | set(ltd_c) | set(ltd_total) | set(st)
    for fy in years:
        if fy in ltd_nc:
            val = ltd_nc[fy] + ltd_c.get(fy, 0.0) + st.get(fy, 0.0)
            out[fy] = (val, "components")
        elif fy in ltd_total:
            val = ltd_total[fy] + st.get(fy, 0.0)
            out[fy] = (val, "ltd_total")
        elif fy in st:
            out[fy] = (st[fy], "short_only")
    return out


def extract_annual_financials(facts: Dict[str, Any], cik: int, name: str, ticker: str) -> List[CompanyYear]:
    """Build per-fiscal-year ``CompanyYear`` records from a companyfacts payload."""
    gaap = facts.get("facts", {}).get("us-gaap", {})
    if not gaap:
        return []

    revenue = _get_concept(gaap, concepts.REVENUE, True)
    cost = _get_concept(gaap, concepts.COST_OF_REVENUE, True)
    gross = _get_concept(gaap, concepts.GROSS_PROFIT, True)
    op = _get_concept(gaap, concepts.OPERATING_INCOME, True)
    ni = _get_concept(gaap, concepts.NET_INCOME, True)
    interest = _get_concept(gaap, concepts.INTEREST_EXPENSE, True)
    tax = _get_concept(gaap, concepts.INCOME_TAX, True)
    da = _combine_da(gaap)
    capex = _get_concept(gaap, concepts.CAPEX, True)
    assets = _get_concept(gaap, concepts.ASSETS, False)
    ca = _get_concept(gaap, concepts.ASSETS_CURRENT, False)
    cl = _get_concept(gaap, concepts.LIABILITIES_CURRENT, False)
    cash = _get_concept(gaap, concepts.CASH, False)
    inv = _get_concept(gaap, concepts.INVENTORY, False)
    recv = _get_concept(gaap, concepts.RECEIVABLES, False)
    pay = _get_concept(gaap, concepts.PAYABLES, False)
    debt = _total_debt(gaap)

    # A fiscal year is in scope if it has revenue OR total assets (the two
    # anchors for tiering and most metrics).
    years = sorted(set(revenue) | set(assets))
    records: List[CompanyYear] = []
    for fy in years:
        rec = CompanyYear(cik=cik, name=name, ticker=ticker, fiscal_year=fy)
        rec.revenue = revenue.get(fy)
        rec.cost_of_revenue = cost.get(fy)
        rec.gross_profit = gross.get(fy)
        rec.operating_income = op.get(fy)
        rec.net_income = ni.get(fy)
        rec.interest_expense = interest.get(fy)
        rec.income_tax = tax.get(fy)
        rec.dep_amort = da.get(fy)
        rec.capex = capex.get(fy)
        rec.assets = assets.get(fy)
        rec.assets_current = ca.get(fy)
        rec.liabilities_current = cl.get(fy)
        rec.cash = cash.get(fy)
        rec.inventory = inv.get(fy)
        rec.receivables = recv.get(fy)
        rec.payables = pay.get(fy)
        if fy in debt:
            rec.total_debt, rec.debt_method = debt[fy]

        # Gross profit fallback: revenue - cost of revenue.
        if rec.gross_profit is None and rec.revenue is not None and rec.cost_of_revenue is not None:
            rec.gross_profit = rec.revenue - rec.cost_of_revenue

        _reconstruct_ebitda(rec)
        records.append(rec)
    return records


def _reconstruct_ebitda(rec: CompanyYear) -> None:
    """Populate ``rec.ebitda`` / ``rec.ebitda_method`` or record why not."""
    if rec.dep_amort is None:
        rec.notes.append("ebitda:missing_D&A")
        return
    if rec.operating_income is not None:
        rec.ebitda = rec.operating_income + rec.dep_amort
        rec.ebitda_method = "oi+da"
        return
    if rec.net_income is not None and rec.interest_expense is not None and rec.income_tax is not None:
        rec.ebitda = rec.net_income + rec.interest_expense + rec.income_tax + rec.dep_amort
        rec.ebitda_method = "ni+int+tax+da"
        return
    rec.notes.append("ebitda:missing_OI_and_NI_components")


# --------------------------------------------------------------------------
# Metric computation
# --------------------------------------------------------------------------
# Canonical metric order used everywhere downstream (deterministic output).
METRIC_FAMILIES: Dict[str, List[str]] = {
    "Leverage & coverage": [
        "debt_to_ebitda",
        "debt_to_assets",
        "ebitda_to_interest",
        "ebitda_less_capex_to_interest",
    ],
    "Margins & profitability": [
        "gross_margin",
        "ebitda_margin",
        "operating_margin",
        "net_margin",
        "return_on_assets",
    ],
    "Working capital & liquidity": [
        "current_ratio",
        "quick_ratio",
        "days_sales_outstanding",
        "days_inventory",
        "days_payable",
        "cash_conversion_cycle",
    ],
}

ALL_METRICS: List[str] = [m for fam in METRIC_FAMILIES.values() for m in fam]


def _safe_div(num: Optional[float], den: Optional[float]) -> Optional[float]:
    if num is None or den is None or den == 0:
        return None
    return num / den


def compute_metrics(rec: CompanyYear) -> Dict[str, Optional[float]]:
    """Compute all metrics for one company-year (None where not computable)."""
    m: Dict[str, Optional[float]] = {k: None for k in ALL_METRICS}

    # Leverage & coverage
    m["debt_to_ebitda"] = _safe_div(rec.total_debt, rec.ebitda)
    m["debt_to_assets"] = _safe_div(rec.total_debt, rec.assets)
    m["ebitda_to_interest"] = _safe_div(rec.ebitda, rec.interest_expense)
    if rec.ebitda is not None and rec.capex is not None:
        m["ebitda_less_capex_to_interest"] = _safe_div(rec.ebitda - rec.capex, rec.interest_expense)

    # Margins & profitability
    m["gross_margin"] = _safe_div(rec.gross_profit, rec.revenue)
    m["ebitda_margin"] = _safe_div(rec.ebitda, rec.revenue)
    m["operating_margin"] = _safe_div(rec.operating_income, rec.revenue)
    m["net_margin"] = _safe_div(rec.net_income, rec.revenue)
    m["return_on_assets"] = _safe_div(rec.net_income, rec.assets)

    # Working capital & liquidity
    m["current_ratio"] = _safe_div(rec.assets_current, rec.liabilities_current)
    if rec.assets_current is not None and rec.inventory is not None and rec.liabilities_current:
        m["quick_ratio"] = (rec.assets_current - rec.inventory) / rec.liabilities_current
    dso = _safe_div(rec.receivables, rec.revenue)
    dio = _safe_div(rec.inventory, rec.cost_of_revenue)
    dpo = _safe_div(rec.payables, rec.cost_of_revenue)
    m["days_sales_outstanding"] = dso * DAYS_IN_YEAR if dso is not None else None
    m["days_inventory"] = dio * DAYS_IN_YEAR if dio is not None else None
    m["days_payable"] = dpo * DAYS_IN_YEAR if dpo is not None else None
    if m["days_sales_outstanding"] is not None and m["days_inventory"] is not None and m["days_payable"] is not None:
        m["cash_conversion_cycle"] = (
            m["days_sales_outstanding"] + m["days_inventory"] - m["days_payable"]
        )

    return m


# Pretty labels and units for output.
METRIC_LABELS: Dict[str, str] = {
    "debt_to_ebitda": "Total debt / EBITDA (x)",
    "debt_to_assets": "Total debt / total assets (x)",
    "ebitda_to_interest": "EBITDA / interest (x)",
    "ebitda_less_capex_to_interest": "(EBITDA - capex) / interest (x)",
    "gross_margin": "Gross margin (%)",
    "ebitda_margin": "EBITDA margin (%)",
    "operating_margin": "Operating margin (%)",
    "net_margin": "Net margin (%)",
    "return_on_assets": "Return on assets (%)",
    "current_ratio": "Current ratio (x)",
    "quick_ratio": "Quick ratio (x)",
    "days_sales_outstanding": "Days sales outstanding",
    "days_inventory": "Days inventory",
    "days_payable": "Days payable",
    "cash_conversion_cycle": "Cash conversion cycle (days)",
}

# Metrics expressed as ratios that read better as percentages in summaries.
PERCENT_METRICS = {
    "gross_margin",
    "ebitda_margin",
    "operating_margin",
    "net_margin",
    "return_on_assets",
}
