#!/usr/bin/env python3
"""Generate ILLUSTRATIVE example outputs (CSV + markdown) for the README/PR.

This uses SYNTHETIC, deterministically-constructed companies — NOT real SEC
data — purely to demonstrate the tool's output format and how the cross-tier
trend, 2020 shock, roster, and LOW CONFIDENCE flagging render. The numbers are
made up but plausible. Run:  python examples/generate_examples.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from satc_edgar.aggregate import parse_tiers  # noqa: E402
from satc_edgar.pipeline import run_for_sic, write_outputs  # noqa: E402

YEARS = list(range(2018, 2025))  # 2018..2024, 7 fiscal years
DA_FRAC = 0.018
CAPEX_FRAC = 0.015
TAX_RATE = 0.24
INT_RATE = 0.06  # interest as a % of debt


def _dur(fy, val):
    return {"start": f"{fy}-01-01", "end": f"{fy}-12-31", "val": round(val, 2),
            "fy": fy, "fp": "FY", "form": "10-K", "filed": f"{fy + 1}-02-20", "accn": f"a{fy}"}


def _inst(fy, val):
    return {"end": f"{fy}-12-31", "val": round(val, 2), "fy": fy, "fp": "FY",
            "form": "10-K", "filed": f"{fy + 1}-02-20", "accn": f"a{fy}"}


def build_company(cik, name, ticker, *, base_rev, growth, gross_margin,
                  op_margin, target_leverage, shock_2020):
    """Construct a companyfacts-shaped dict with a realistic 7-year series."""
    def add(g, tag, kind, series):
        dps = [(_dur(fy, v) if kind == "d" else _inst(fy, v)) for fy, v in series.items()]
        g[tag] = {"label": tag, "units": {"USD": dps}}

    # Revenue path with a 2020 dip and recovery.
    rev = {}
    for i, fy in enumerate(YEARS):
        r = base_rev * (growth ** i)
        if fy == 2020:
            r *= (1.0 - shock_2020)
        rev[fy] = r

    # Margins compress in 2020 (operating leverage), recover after.
    op = {fy: rev[fy] * (op_margin * (0.55 if fy == 2020 else 1.0)) for fy in YEARS}
    gm = {fy: gross_margin * (0.92 if fy == 2020 else 1.0) for fy in YEARS}
    cor = {fy: rev[fy] * (1.0 - gm[fy]) for fy in YEARS}
    da = {fy: rev[fy] * DA_FRAC for fy in YEARS}
    capex = {fy: rev[fy] * CAPEX_FRAC for fy in YEARS}

    # Size debt to hit a target through-cycle leverage on latest-year EBITDA.
    ebitda_latest = rev[YEARS[-1]] * (op_margin + DA_FRAC)
    debt_total = target_leverage * ebitda_latest
    interest = {fy: debt_total * INT_RATE for fy in YEARS}
    tax = {fy: max(0.0, op[fy] - interest[fy]) * TAX_RATE for fy in YEARS}
    ni = {fy: (op[fy] - interest[fy]) - tax[fy] for fy in YEARS}

    assets = {fy: rev[fy] * 0.62 for fy in YEARS}
    cl = {fy: rev[fy] * 0.20 for fy in YEARS}
    ca = {fy: cl[fy] * 1.45 for fy in YEARS}          # current ratio ~1.45
    inv = {fy: rev[fy] * 0.11 for fy in YEARS}
    recv = {fy: rev[fy] * 0.095 for fy in YEARS}
    pay = {fy: rev[fy] * 0.075 for fy in YEARS}
    cash = {fy: rev[fy] * 0.04 for fy in YEARS}

    g = {}
    add(g, "Revenues", "d", rev)
    add(g, "CostOfGoodsAndServicesSold", "d", cor)
    add(g, "OperatingIncomeLoss", "d", op)
    add(g, "NetIncomeLoss", "d", ni)
    add(g, "IncomeTaxExpenseBenefit", "d", tax)
    add(g, "InterestExpense", "d", interest)
    add(g, "DepreciationDepletionAndAmortization", "d", da)
    add(g, "PaymentsToAcquirePropertyPlantAndEquipment", "d", capex)
    add(g, "Assets", "i", assets)
    add(g, "AssetsCurrent", "i", ca)
    add(g, "LiabilitiesCurrent", "i", cl)
    add(g, "InventoryNet", "i", inv)
    add(g, "AccountsReceivableNetCurrent", "i", recv)
    add(g, "AccountsPayableCurrent", "i", pay)
    add(g, "CashAndCashEquivalentsAtCarryingValue", "i", cash)
    add(g, "LongTermDebtNoncurrent", "i", {fy: debt_total for fy in YEARS})
    add(g, "LongTermDebtCurrent", "i", {fy: debt_total * 0.08 for fy in YEARS})
    return {"cik": cik, "entityName": name, "facts": {"us-gaap": g}}


# Illustrative roster: (name, ticker, base_rev, growth, gross_margin, op_margin,
# target_leverage, 2020_shock). Smaller names carry thinner margins, higher
# leverage, and a deeper 2020 dip — so the cross-tier trend is visible.
COMPANIES = [
    # Large (5B+) — 11 names: healthy tier
    ("US BROADLINE FOODS CORP", "USBF", 62e9, 1.05, 0.185, 0.041, 2.6, 0.06),
    ("CONTINENTAL PROVISIONS INC", "CPRV", 41e9, 1.045, 0.178, 0.038, 2.9, 0.07),
    ("MERIDIAN FOOD DISTRIBUTORS", "MFDX", 33e9, 1.06, 0.192, 0.044, 2.4, 0.05),
    ("GREATLAKES GROCERY SUPPLY", "GLGS", 28e9, 1.04, 0.175, 0.036, 3.1, 0.08),
    ("PACIFIC PANTRY HOLDINGS", "PPNT", 22e9, 1.055, 0.188, 0.043, 2.7, 0.06),
    ("ATLANTIC PROVISION CO", "ATPV", 18e9, 1.05, 0.181, 0.040, 2.8, 0.07),
    ("HEARTLAND FOODSERVICE", "HLFS", 14e9, 1.035, 0.170, 0.034, 3.3, 0.09),
    ("SUMMIT WHOLESALE FOODS", "SMWF", 11e9, 1.06, 0.195, 0.046, 2.3, 0.05),
    ("KEYSTONE DISTRIBUTION GROUP", "KSDG", 9.2e9, 1.045, 0.179, 0.039, 2.9, 0.07),
    ("NORTHSTAR FOOD PARTNERS", "NSFP", 7.4e9, 1.05, 0.184, 0.041, 2.7, 0.06),
    ("EVERGREEN PROVISIONS", "EVGP", 5.6e9, 1.04, 0.176, 0.037, 3.0, 0.08),
    # Mid (1B-5B) — 8 names: healthy tier
    ("REGIONAL LARDER INC", "RGLR", 4.3e9, 1.05, 0.172, 0.035, 3.4, 0.09),
    ("MIDWEST PANTRY SUPPLY", "MWPS", 3.5e9, 1.045, 0.168, 0.033, 3.6, 0.10),
    ("COASTAL FOODS WHOLESALE", "CFWS", 2.9e9, 1.06, 0.180, 0.038, 3.1, 0.08),
    ("VALLEY PROVISIONS CORP", "VLYP", 2.3e9, 1.04, 0.165, 0.031, 3.8, 0.11),
    ("PRAIRIE DISTRIBUTORS", "PRDB", 1.9e9, 1.05, 0.170, 0.034, 3.5, 0.10),
    ("HARBORVIEW FOODSERVICE", "HRBV", 1.6e9, 1.035, 0.162, 0.030, 4.0, 0.12),
    ("CEDARTON SUPPLY CO", "CDTN", 1.35e9, 1.05, 0.174, 0.036, 3.3, 0.09),
    ("LAKERIDGE PANTRY GROUP", "LKRP", 1.1e9, 1.04, 0.166, 0.032, 3.7, 0.11),
    # Small (250M-1B) — 3 names: THIN -> LOW CONFIDENCE
    ("TRISTATE FOOD SUPPLY", "TSFS", 820e6, 1.04, 0.158, 0.028, 4.3, 0.13),
    ("HILLCREST PROVISIONS", "HLCP", 560e6, 1.05, 0.160, 0.029, 4.1, 0.12),
    ("BROOKFIELD WHOLESALE", "BKFW", 330e6, 1.03, 0.152, 0.025, 4.6, 0.15),
]


class _FakeClient:
    def __init__(self, facts, desc):
        self._facts = facts
        self._desc = desc

    def get_companyfacts(self, cik):
        return self._facts.get(int(cik))

    def get_submissions(self, cik):
        return {"sicDescription": self._desc, "sic": "5140", "name": f"CIK{cik}"}


def main():
    facts = {}
    companies = []
    for idx, (name, ticker, *params) in enumerate(COMPANIES):
        cik = 900000 + idx
        base_rev, growth, gm, opm, lev, shock = params
        facts[cik] = build_company(
            cik, name, ticker, base_rev=base_rev, growth=growth,
            gross_margin=gm, op_margin=opm, target_leverage=lev, shock_2020=shock,
        )
        companies.append((cik, name, ticker))

    client = _FakeClient(facts, "GROCERIES, GENERAL LINE")
    tiers = parse_tiers("0-250M,250M-1B,1B-5B,5B+")
    run = run_for_sic(client, "5140", companies, tiers, years=7, min_sample=8,
                      log=lambda m: None)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    base = os.path.join(out_dir, "sample_food_dist")
    # Fixed vintage so the committed example is stable.
    write_outputs([run], base, 7, "2026-06-09 (SYNTHETIC EXAMPLE — not real EDGAR data)",
                  8, log=lambda m: None)
    print("Wrote example CSV + summary to", out_dir)


if __name__ == "__main__":
    main()
