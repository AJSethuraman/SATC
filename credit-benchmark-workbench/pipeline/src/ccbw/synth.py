"""Synthetic EDGAR corpus generator.

Purpose: (1) fixture factory for pipeline tests, and (2) source for the
demonstration benchmark snapshot when live EDGAR access is unavailable
(this build environment cannot reach data.sec.gov). Output is shaped
exactly like CompanyFacts JSON and is ingested through the SAME
parse -> panel -> benchmark path as live data, so swapping in real EDGAR is
a data refresh, not a code change.

The generator deliberately reproduces EDGAR's messy realities:

* tag fragmentation (filers split across revenue-tag variants),
* duplicate facts (each year's value re-reported as the comparative column
  of the next year's filing, with later filed dates and new accessions),
* restatements (10-K/A amendments with corrected values that must win),
* missing line items (D&A, interest, COGS dropped for some filers),
* off-calendar fiscal year ends (June/September/January),
* a non-USD unit trap (values under 'EUR' that must be rejected),
* a survivor-biased size distribution (the lower-middle-market band is
  deliberately thin, as it is in the real public universe),
* a deterioration cohort (~15%) with multi-year decline paths into distress,
  giving the Stage 5 backtest real events to measure.

Every number is deterministic given the seed. THE FINANCIAL LEVELS ARE
ILLUSTRATIVE: parameter centers are round, segment-plausible values chosen
for machinery demonstration, not sourced market statistics -- the snapshot
metadata and GUI banner carry this caveat.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

FY_FIRST, FY_LAST = 2012, 2024

REVENUE_TAGS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
]

# (segment, sic, weight) -- SICs chosen inside each segment's ranges
SEGMENT_SICS = {
    "cni": [3559, 3089, 5065, 7363, 3441, 5122],
    "cre_opco": [6512, 6798, 6531],
    "healthcare": [8062, 8011, 8082, 8071],
    "agribusiness": [200, 2041, 2086, 5153],
    # dedicated leveraged distributors (also inside C&I SIC space)
    "leveraged_seed": [5045, 5093, 5171],
}

# EBITDA size targets (USD): the public universe skews large, lmm thinnest
SIZE_MIX = [
    ("lmm", 8e6, 22e6, 2),
    ("cmm", 30e6, 90e6, 8),
    ("umm", 110e6, 280e6, 12),
    ("large", 350e6, 1800e6, 14),
]


@dataclass
class SegmentParams:
    margin_lo: float
    margin_hi: float
    gross_lo: float
    gross_hi: float
    lev_lo: float           # target debt/EBITDA
    lev_hi: float
    dso: tuple[float, float]
    dio: tuple[float, float]
    dpo: tuple[float, float]
    da_rate: tuple[float, float]      # D&A as % of revenue
    capex_rate: tuple[float, float]
    growth: tuple[float, float]
    cycle_amp: float                  # revenue cycle amplitude
    cycle_period: float
    noise: float
    has_inventory: bool = True
    rent_share: float = 0.0           # fraction of names with rent expense


SEG_PARAMS: dict[str, SegmentParams] = {
    "cni": SegmentParams(0.10, 0.20, 0.22, 0.40, 1.5, 3.5,
                         (35, 65), (45, 90), (30, 55), (0.030, 0.055),
                         (0.025, 0.05), (0.02, 0.06), 0.04, 7.0, 0.04),
    "cre_opco": SegmentParams(0.50, 0.65, 0.55, 0.75, 5.0, 8.0,
                              (15, 35), (0, 0), (15, 30), (0.18, 0.30),
                              (0.08, 0.15), (0.01, 0.04), 0.03, 10.0, 0.025,
                              has_inventory=False),
    "healthcare": SegmentParams(0.08, 0.18, 0.25, 0.45, 2.0, 4.5,
                                (45, 75), (8, 20), (25, 45), (0.030, 0.06),
                                (0.025, 0.05), (0.03, 0.07), 0.02, 8.0, 0.03,
                                rent_share=0.6),
    "agribusiness": SegmentParams(0.05, 0.12, 0.10, 0.22, 1.5, 3.5,
                                  (20, 45), (60, 120), (20, 40), (0.025, 0.05),
                                  (0.02, 0.045), (0.00, 0.05), 0.12, 4.0, 0.05),
    "leveraged_seed": SegmentParams(0.06, 0.12, 0.15, 0.28, 4.5, 6.5,
                                    (40, 60), (55, 95), (35, 55), (0.015, 0.03),
                                    (0.01, 0.025), (0.02, 0.05), 0.05, 7.0, 0.045),
}

FYE_CHOICES = [(12, 31)] * 17 + [(6, 30), (9, 30), (1, 31)]


@dataclass
class SynthCompany:
    cik: int
    name: str
    sic: int
    segment_hint: str
    fye_month: int
    fye_day: int
    revenue_tag: str
    ebitda0: float
    margin: float
    gross_margin: float
    leverage: float
    rate: float
    dso: float
    dio: float
    dpo: float
    da_rate: float
    capex_rate: float
    growth: float
    cycle_amp: float
    cycle_period: float
    cycle_phase: float
    noise: float
    has_inventory: bool
    has_rent: bool
    missing: set = field(default_factory=set)
    restates: bool = False
    decline_start: Optional[int] = None
    unit_trap_fy: Optional[int] = None


def make_universe(seed: int = 20260609) -> list[SynthCompany]:
    rng = random.Random(seed)
    companies: list[SynthCompany] = []
    cik = 900000
    for seg, sics in SEGMENT_SICS.items():
        p = SEG_PARAMS[seg]
        for bucket, lo, hi, count in SIZE_MIX:
            n = count
            if seg == "leveraged_seed":
                n = max(1, count // 2)
            if seg == "cre_opco" and bucket == "lmm":
                n = 1  # tiny public CRE opcos barely exist
            for i in range(n):
                cik += 7
                margin = rng.uniform(p.margin_lo, p.margin_hi)
                ebitda0 = rng.uniform(lo, hi)
                missing = set()
                if rng.random() < 0.08:
                    missing.add("depreciation_amortization")
                if rng.random() < 0.05:
                    missing.add("interest_expense")
                if rng.random() < 0.10:
                    missing.add("cogs")
                if rng.random() < 0.06:
                    missing.add("retained_earnings")
                fye = rng.choice(FYE_CHOICES)
                companies.append(SynthCompany(
                    cik=cik,
                    name=f"{seg.upper().replace('_SEED','')}-{bucket.upper()}-{i+1:02d} Corp",
                    sic=rng.choice(sics),
                    segment_hint=seg,
                    fye_month=fye[0], fye_day=fye[1],
                    revenue_tag=rng.choice(REVENUE_TAGS),
                    ebitda0=ebitda0,
                    margin=margin,
                    gross_margin=rng.uniform(p.gross_lo, p.gross_hi),
                    leverage=rng.uniform(p.lev_lo, p.lev_hi),
                    rate=rng.uniform(0.045, 0.075),
                    dso=rng.uniform(*p.dso),
                    dio=rng.uniform(*p.dio) if p.has_inventory else 0.0,
                    dpo=rng.uniform(*p.dpo),
                    da_rate=rng.uniform(*p.da_rate),
                    capex_rate=rng.uniform(*p.capex_rate),
                    growth=rng.uniform(*p.growth),
                    cycle_amp=p.cycle_amp,
                    cycle_period=p.cycle_period,
                    cycle_phase=rng.uniform(0, p.cycle_period),
                    noise=p.noise,
                    has_inventory=p.has_inventory,
                    has_rent=rng.random() < p.rent_share,
                    missing=missing,
                    restates=rng.random() < 0.10,
                    decline_start=(rng.choice([2017, 2018, 2019, 2020, 2021])
                                   if rng.random() < 0.16 else None),
                    unit_trap_fy=(2019 if rng.random() < 0.03 else None),
                ))
    return companies


def simulate_financials(c: SynthCompany, seed: int = 7) -> dict[int, dict]:
    """Simulate FY2012-FY2024 statements for one company. Returns
    {fy: {concept: value}} in USD raw units."""
    rng = random.Random(seed * 1_000_003 + c.cik)
    out: dict[int, dict] = {}
    revenue = c.ebitda0 / c.margin
    debt = c.leverage * c.ebitda0
    retained = 0.30 * revenue
    equity_base = 0.25 * revenue
    cash_rate = rng.uniform(0.04, 0.12)

    for fy in range(FY_FIRST, FY_LAST + 1):
        t = fy - FY_FIRST
        cyc = math.sin(2 * math.pi * (t + c.cycle_phase) / c.cycle_period)
        g = c.growth + c.cycle_amp * cyc + rng.gauss(0, c.noise)
        # margin cycles proportionally with the revenue cycle, bounded below
        margin = max(0.005, c.margin * (1 + 0.6 * cyc * (c.cycle_amp / 0.06) * 0.15
                                        + rng.gauss(0, 0.05)))
        if c.decline_start and fy >= c.decline_start:
            k = fy - c.decline_start + 1
            g -= 0.05 * k                    # compounding revenue slide
            margin *= max(0.15, 1 - 0.13 * k)  # margin compression
            debt *= 1.06                       # revolver creep
        if fy > FY_FIRST:
            revenue *= max(0.4, 1 + g)
        ebitda = revenue * margin
        da = revenue * c.da_rate
        op_income = ebitda - da
        rate = c.rate + (0.022 if fy >= 2023 else 0.012 if fy == 2022 else 0.0)
        if not c.decline_start:
            # drift debt toward target leverage on current EBITDA
            target = c.leverage * max(ebitda, 0.3 * c.ebitda0)
            debt += 0.35 * (target - debt)
        interest = debt * rate
        cogs = revenue * (1 - c.gross_margin)
        ar = c.dso / 365 * revenue
        inv = (c.dio / 365 * cogs) if c.has_inventory else 0.0
        ap = c.dpo / 365 * cogs
        cash = cash_rate * revenue
        if c.decline_start and fy >= c.decline_start:
            cash *= max(0.2, 1 - 0.25 * (fy - c.decline_start + 1))
            ar *= 1 + 0.06 * (fy - c.decline_start + 1)  # collections slow
        tax = 0.25 * max(0.0, op_income - interest)
        ni = op_income - interest - tax
        dividends = 0.2 * ni if ni > 0 else 0.0
        retained += ni - dividends
        equity = equity_base + retained
        accrued = 0.05 * revenue
        other_lt_liab = 0.06 * revenue
        debt_current = 0.10 * debt
        debt_noncurrent = 0.90 * debt
        total_liabilities = debt + ap + accrued + other_lt_liab
        total_assets = total_liabilities + max(equity, 0.05 * revenue)
        current_assets = cash + ar + inv + 0.02 * revenue
        current_liabilities = ap + accrued + debt_current
        capex = c.capex_rate * revenue
        cfo = ni + da - (0.1 * (ar + inv - ap)) * (0.3 if fy > FY_FIRST else 0)
        rent = 0.04 * revenue if c.has_rent else None

        row = {
            "revenue": revenue,
            "cogs": cogs,
            "operating_income": op_income,
            "depreciation_amortization": da,
            "interest_expense": interest,
            "net_income": ni,
            "capex": capex,
            "operating_cash_flow": cfo,
            "total_assets": total_assets,
            "current_assets": current_assets,
            "current_liabilities": current_liabilities,
            "total_liabilities": total_liabilities,
            "cash": cash,
            "receivables": ar,
            "inventory": inv if c.has_inventory else None,
            "payables": ap,
            "lt_debt_noncurrent": debt_noncurrent,
            "lt_debt_current": debt_current,
            "equity": equity,
            "retained_earnings": retained,
            "rent_expense": rent,
        }
        out[fy] = {k: v for k, v in row.items() if v is not None}
    return out


# ------------------------------------------------------------------ #
# CompanyFacts JSON emission (with messiness)
# ------------------------------------------------------------------ #

CONCEPT_TAG = {
    "cogs": "CostOfRevenue",
    "operating_income": "OperatingIncomeLoss",
    "depreciation_amortization": "DepreciationDepletionAndAmortization",
    "interest_expense": "InterestExpense",
    "net_income": "NetIncomeLoss",
    "capex": "PaymentsToAcquirePropertyPlantAndEquipment",
    "operating_cash_flow": "NetCashProvidedByUsedInOperatingActivities",
    "rent_expense": "OperatingLeaseExpense",
    "total_assets": "Assets",
    "current_assets": "AssetsCurrent",
    "current_liabilities": "LiabilitiesCurrent",
    "total_liabilities": "Liabilities",
    "cash": "CashAndCashEquivalentsAtCarryingValue",
    "receivables": "AccountsReceivableNetCurrent",
    "inventory": "InventoryNet",
    "payables": "AccountsPayableCurrent",
    "lt_debt_noncurrent": "LongTermDebtNoncurrent",
    "lt_debt_current": "LongTermDebtCurrent",
    "equity": "StockholdersEquity",
    "retained_earnings": "RetainedEarningsAccumulatedDeficit",
}

DURATION_CONCEPTS = {
    "revenue", "cogs", "operating_income", "depreciation_amortization",
    "interest_expense", "net_income", "capex", "operating_cash_flow",
    "rent_expense",
}


def _fye_date(c: SynthCompany, fy: int) -> date:
    # A January FYE belongs to the *following* calendar year (covers fy).
    if c.fye_month <= 5:
        return date(fy + 1, c.fye_month, c.fye_day)
    return date(fy, c.fye_month, c.fye_day)


def _accn(cik: int, year: int, seq: int) -> str:
    return f"{cik:010d}-{year % 100:02d}-{seq:06d}"


def company_facts_json(c: SynthCompany, seed: int = 7) -> dict:
    """Emit CompanyFacts-shaped JSON with duplicates, comparative re-reports,
    amendments/restatements, missing tags and the unit trap."""
    rng = random.Random(seed * 7_000_003 + c.cik)
    fin = simulate_financials(c, seed)
    facts: dict[str, dict] = {}

    def add(tag: str, unit: str, entry: dict) -> None:
        facts.setdefault(tag, {"units": {}})["units"].setdefault(unit, []).append(entry)

    for fy, row in fin.items():
        end = _fye_date(c, fy)
        start = end - timedelta(days=364)
        filed = end + timedelta(days=75)
        accn = _accn(c.cik, filed.year, fy * 10 + 1)
        next_filed = _fye_date(c, fy + 1) + timedelta(days=75)
        next_accn = _accn(c.cik, next_filed.year, (fy + 1) * 10 + 1)

        for concept, val in row.items():
            if concept in c.missing:
                continue
            tag = c.revenue_tag if concept == "revenue" else CONCEPT_TAG[concept]
            is_dur = concept in DURATION_CONCEPTS
            base = {
                "val": round(val, 0),
                "end": end.isoformat(),
                "accn": accn,
                "fy": end.year,
                "fp": "FY",
                "form": "10-K",
                "filed": filed.isoformat(),
            }
            if is_dur:
                base["start"] = start.isoformat()
            add(tag, "USD", dict(base))

            # duplicate: re-reported as next year's comparative column
            if fy < FY_LAST:
                dup = dict(base)
                dup["accn"] = next_accn
                dup["filed"] = next_filed.isoformat()
                dup["fy"] = next_filed.year
                # occasional restatement in the comparative column
                if c.restates and concept == "revenue" and fy == 2019:
                    dup["val"] = round(val * 1.03, 0)
                add(tag, "USD", dup)

            # 10-K/A amendment correcting interest expense
            if (c.restates and concept == "interest_expense" and fy == 2020):
                amend = dict(base)
                amend["form"] = "10-K/A"
                amend["accn"] = _accn(c.cik, filed.year, fy * 10 + 2)
                amend["filed"] = (filed + timedelta(days=120)).isoformat()
                amend["val"] = round(val * 1.10, 0)
                add(tag, "USD", amend)

        # unit trap: a stray EUR-denominated revenue entry
        if c.unit_trap_fy == fy:
            add(c.revenue_tag, "EUR", {
                "val": round(row["revenue"] * 0.9, 0),
                "start": start.isoformat(), "end": end.isoformat(),
                "accn": _accn(c.cik, filed.year, fy * 10 + 3),
                "fy": end.year, "fp": "FY", "form": "10-K",
                "filed": filed.isoformat(),
            })

    return {
        "cik": c.cik,
        "entityName": c.name,
        "facts": {"us-gaap": facts},
    }
