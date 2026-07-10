"""Helpers to build synthetic EDGAR payloads for deterministic offline tests."""

from __future__ import annotations

from typing import Dict, List, Optional


def _duration_dp(fy: int, val: float) -> dict:
    return {
        "start": f"{fy}-01-01",
        "end": f"{fy}-12-31",
        "val": val,
        "fy": fy,
        "fp": "FY",
        "form": "10-K",
        "filed": f"{fy + 1}-02-15",
        "accn": f"acc-{fy}",
    }


def _instant_dp(fy: int, val: float) -> dict:
    return {
        "end": f"{fy}-12-31",
        "val": val,
        "fy": fy,
        "fp": "FY",
        "form": "10-K",
        "filed": f"{fy + 1}-02-15",
        "accn": f"acc-{fy}",
    }


def make_companyfacts(
    cik: int,
    name: str,
    years: List[int],
    *,
    revenue: float,
    growth: float = 1.0,
    gross_margin: float = 0.18,
    op_margin: float = 0.05,
    da_frac: float = 0.02,
    interest: float = 20.0,
    tax_frac: float = 0.25,
    capex_frac: float = 0.02,
    debt: float = 1500.0,
    assets_mult: float = 0.6,
    extra: Optional[Dict[str, Dict[int, float]]] = None,
    drop_da: bool = False,
) -> dict:
    """Build a companyfacts-shaped dict spanning ``years`` (values in $M-ish)."""
    gaap: Dict[str, dict] = {}

    def add(tag: str, kind: str, series: Dict[int, float]) -> None:
        unit = "USD"
        dps = []
        for fy, val in series.items():
            dps.append(_duration_dp(fy, val) if kind == "d" else _instant_dp(fy, val))
        gaap[tag] = {"label": tag, "units": {unit: dps}}

    rev = {}
    for i, fy in enumerate(sorted(years)):
        rev[fy] = revenue * (growth ** i)
    cor = {fy: v * (1 - gross_margin) for fy, v in rev.items()}
    op = {fy: v * op_margin for fy, v in rev.items()}
    da = {fy: v * da_frac for fy, v in rev.items()}
    ni = {fy: (op[fy] - interest) * (1 - tax_frac) for fy in rev}
    tax = {fy: (op[fy] - interest) * tax_frac for fy in rev}
    capex = {fy: v * capex_frac for fy, v in rev.items()}
    assets = {fy: v * assets_mult for fy, v in rev.items()}

    add("Revenues", "d", rev)
    add("CostOfGoodsAndServicesSold", "d", cor)
    add("OperatingIncomeLoss", "d", op)
    add("NetIncomeLoss", "d", ni)
    add("IncomeTaxExpenseBenefit", "d", tax)
    add("InterestExpense", "d", {fy: interest for fy in rev})
    if not drop_da:
        add("DepreciationDepletionAndAmortization", "d", da)
    add("PaymentsToAcquirePropertyPlantAndEquipment", "d", capex)
    add("Assets", "i", assets)
    add("AssetsCurrent", "i", {fy: v * 0.4 for fy, v in rev.items()})
    add("LiabilitiesCurrent", "i", {fy: v * 0.25 for fy, v in rev.items()})
    add("CashAndCashEquivalentsAtCarryingValue", "i", {fy: v * 0.05 for fy, v in rev.items()})
    add("InventoryNet", "i", {fy: v * 0.12 for fy, v in rev.items()})
    add("AccountsReceivableNetCurrent", "i", {fy: v * 0.10 for fy, v in rev.items()})
    add("AccountsPayableCurrent", "i", {fy: v * 0.08 for fy, v in rev.items()})
    add("LongTermDebtNoncurrent", "i", {fy: debt for fy in rev})
    add("LongTermDebtCurrent", "i", {fy: debt * 0.1 for fy in rev})

    if extra:
        for tag, series in extra.items():
            kind = "i" if tag in ("Assets",) else "d"
            add(tag, kind, series)

    return {"cik": cik, "entityName": name, "facts": {"us-gaap": gaap}}
