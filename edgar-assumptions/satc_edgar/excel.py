"""Build a clean, analyst-friendly .xlsx workbook from the pipeline results.

Sheets:
  * ReadMe      — run metadata + the standing caveats block.
  * Summary     — tidy/long percentile table (SIC x Tier x View x Metric), with
                  proper per-cell number formats (%, x, days), filterable.
  * Roster      — the constituent companies of each tier.
  * 2020 Shock  — median 2019->2020 change per metric, per tier.
  * Raw Data    — the auditable per-company-per-year feed (mirrors the CSV).

All numeric cells carry real numbers (not strings) with a number format, so the
workbook is ready to pivot/chart. Output is deterministic (see xlsx.py).
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from . import xlsx
from .metrics import (
    ALL_METRICS,
    METRIC_FAMILIES,
    METRIC_LABELS,
    PERCENT_METRICS,
)
from .output import CAVEATS, _CSV_FIELDS

HEADER_FILL = "1F4E79"     # dark blue
HEADER_TEXT_FILL = None
SUBHEAD_FILL = "D9E1F2"    # light blue
LOWCONF_FILL = "FCE4D6"    # light orange

_DAYS_METRICS = {
    "days_sales_outstanding",
    "days_inventory",
    "days_payable",
    "cash_conversion_cycle",
}
# Raw financial line items (USD) in the audit feed.
_USD_FIELDS = {
    "revenue", "cost_of_revenue", "gross_profit", "operating_income",
    "net_income", "interest_expense", "income_tax", "dep_amort", "capex",
    "assets", "assets_current", "liabilities_current", "cash", "inventory",
    "receivables", "payables", "total_debt", "ebitda",
}


def metric_format(metric: str) -> str:
    if metric in PERCENT_METRICS:
        return xlsx.FMT_PCT1
    if metric in _DAYS_METRICS:
        return xlsx.FMT_DAYS
    return xlsx.FMT_RATIO


def metric_unit(metric: str) -> str:
    if metric in PERCENT_METRICS:
        return "%"
    if metric in _DAYS_METRICS:
        return "days"
    return "x"


def _hdr(text: str) -> xlsx.Cell:
    return xlsx.txt(text, bold=True, fill=SUBHEAD_FILL)


def _coerce_number(s) -> Optional[float]:
    if s is None or s == "":
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def build_workbook(runs, years: int, vintage: str, min_sample: int) -> "xlsx.Workbook":
    wb = xlsx.Workbook()
    _readme_sheet(wb, runs, years, vintage, min_sample)
    _summary_sheet(wb, runs)
    _roster_sheet(wb, runs)
    _shock_sheet(wb, runs)
    _raw_sheet(wb, runs)
    return wb


# --------------------------------------------------------------------------
def _readme_sheet(wb, runs, years, vintage, min_sample) -> None:
    sh = wb.add_sheet("ReadMe")
    sh.set_widths({0: 100})
    sh.add_row([xlsx.txt("EDGAR Industry Assumption Set", bold=True)])
    sh.add_row([xlsx.txt("")])
    sh.add_row([xlsx.txt(f"SIC codes: {', '.join(r.sic for r in runs)}")])
    sh.add_row([xlsx.txt(f"EDGAR data vintage (date pulled): {vintage}")])
    sh.add_row([xlsx.txt(f"Lookback window: {years} fiscal years")])
    sh.add_row([xlsx.txt(f"Minimum sample per tier: {min_sample} companies")])
    sh.add_row([xlsx.txt("")])
    for line in CAVEATS.splitlines():
        sh.add_row([xlsx.txt(line, bold=line.startswith("##"), wrap=True)])
    sh.add_row([xlsx.txt("")])
    sh.add_row([xlsx.txt("Sheets in this workbook:", bold=True)])
    for name, desc in (
        ("Summary", "Percentile ranges per SIC x revenue tier x view x metric (filterable)."),
        ("Roster", "The public companies that make up each tier."),
        ("2020 Shock", "Median 2019->2020 change per metric, per tier."),
        ("Raw Data", "Auditable per-company-per-year figures and computed metrics."),
    ):
        sh.add_row([xlsx.txt(f"  - {name}: {desc}", wrap=True)])


# --------------------------------------------------------------------------
def _summary_sheet(wb, runs) -> None:
    sh = wb.add_sheet("Summary")
    headers = [
        "SIC", "SIC description", "Revenue tier", "View", "Metric family",
        "Metric", "Unit", "p10", "p25", "p50 (median)", "p75", "p90",
        "# companies", "# company-years", "Median CV", "Low confidence",
    ]
    sh.add_row([_hdr(h) for h in headers])
    sh.freeze_rows = 1
    sh.freeze_cols = 6
    sh.autofilter = True
    sh.set_widths({0: 8, 1: 26, 2: 13, 3: 15, 4: 24, 5: 30, 6: 6,
                   7: 9, 8: 9, 9: 12, 10: 9, 11: 9, 12: 12, 13: 15, 14: 10, 15: 14})

    for run in sorted(runs, key=lambda r: r.sic):
        for tr in run.tier_results:
            if tr.n_companies == 0:
                continue
            lowconf = tr.low_confidence
            fill = LOWCONF_FILL if lowconf else None
            for view_key, view_label, dists in (
                ("current", "Current norms", tr.current),
                ("through_cycle", "Through-cycle", tr.through_cycle),
            ):
                for family, metrics in METRIC_FAMILIES.items():
                    for metric in metrics:
                        d = dists[metric]
                        fmt = metric_format(metric)
                        row = [
                            xlsx.txt(run.sic, fill=fill),
                            xlsx.txt(run.sic_description, fill=fill),
                            xlsx.txt(tr.tier.label, fill=fill),
                            xlsx.txt(view_label, fill=fill),
                            xlsx.txt(family, fill=fill),
                            xlsx.txt(METRIC_LABELS.get(metric, metric), fill=fill),
                            xlsx.txt(metric_unit(metric), fill=fill),
                            xlsx.num(d.p10, fmt, fill=fill),
                            xlsx.num(d.p25, fmt, fill=fill),
                            xlsx.num(d.p50, fmt, fill=fill),
                            xlsx.num(d.p75, fmt, fill=fill),
                            xlsx.num(d.p90, fmt, fill=fill),
                            xlsx.num(d.n_companies, xlsx.FMT_INT, fill=fill),
                            xlsx.num(d.n_company_years, xlsx.FMT_INT, fill=fill),
                            xlsx.num(d.median_cv, "0.00", fill=fill),
                            xlsx.txt("YES" if lowconf else "", fill=fill),
                        ]
                        sh.add_row(row)


# --------------------------------------------------------------------------
def _roster_sheet(wb, runs) -> None:
    sh = wb.add_sheet("Roster")
    headers = ["SIC", "Revenue tier", "Ticker", "Company", "CIK",
               "Latest revenue (USD)", "First FY", "Last FY", "# years", "Low confidence"]
    sh.add_row([_hdr(h) for h in headers])
    sh.freeze_rows = 1
    sh.autofilter = True
    sh.set_widths({0: 8, 1: 13, 2: 10, 3: 34, 4: 12, 5: 20, 6: 9, 7: 9, 8: 8, 9: 14})

    for run in sorted(runs, key=lambda r: r.sic):
        for tr in run.tier_results:
            fill = LOWCONF_FILL if tr.low_confidence else None
            for e in tr.roster:
                sh.add_row([
                    xlsx.txt(run.sic, fill=fill),
                    xlsx.txt(tr.tier.label, fill=fill),
                    xlsx.txt(e.ticker, fill=fill),
                    xlsx.txt(e.name, fill=fill),
                    xlsx.num(e.cik, "0", fill=fill),
                    xlsx.num(e.latest_revenue, xlsx.FMT_USD, fill=fill),
                    xlsx.num(e.first_year, "0", fill=fill),
                    xlsx.num(e.last_year, "0", fill=fill),
                    xlsx.num(e.n_years, xlsx.FMT_INT, fill=fill),
                    xlsx.txt("YES" if tr.low_confidence else "", fill=fill),
                ])


# --------------------------------------------------------------------------
def _shock_sheet(wb, runs) -> None:
    sh = wb.add_sheet("2020 Shock")
    headers = ["SIC", "Revenue tier", "Metric", "Change", "Unit", "# companies"]
    sh.add_row([_hdr(h) for h in headers])
    sh.freeze_rows = 1
    sh.autofilter = True
    sh.set_widths({0: 8, 1: 13, 2: 30, 3: 12, 4: 12, 5: 12})

    for run in sorted(runs, key=lambda r: r.sic):
        for tr in run.tier_results:
            shock = tr.shock_2020 or {}
            n = int(shock.get("_n", 0.0))
            if n < 2:
                continue
            fill = LOWCONF_FILL if tr.low_confidence else None
            for metric in ALL_METRICS:
                val = shock.get(metric)
                if val is None:
                    continue
                if metric in PERCENT_METRICS:
                    # stored as a fractional pp difference; show as pp.
                    disp, fmt, unit = val * 100.0, xlsx.FMT_DAYS, "pp"
                else:
                    disp, fmt, unit = val, xlsx.FMT_PCT1, "% change"
                sh.add_row([
                    xlsx.txt(run.sic, fill=fill),
                    xlsx.txt(tr.tier.label, fill=fill),
                    xlsx.txt(METRIC_LABELS.get(metric, metric), fill=fill),
                    xlsx.num(disp, fmt, fill=fill),
                    xlsx.txt(unit, fill=fill),
                    xlsx.num(n, xlsx.FMT_INT, fill=fill),
                ])


# --------------------------------------------------------------------------
def _raw_sheet(wb, runs) -> None:
    sh = wb.add_sheet("Raw Data")
    sh.add_row([_hdr(f) for f in _CSV_FIELDS])
    sh.freeze_rows = 1
    sh.freeze_cols = 5
    sh.autofilter = True
    # sensible widths for the identity columns
    sh.set_widths({0: 8, 1: 11, 2: 32, 3: 9, 4: 11, 5: 12})

    all_rows: List[dict] = []
    for run in sorted(runs, key=lambda r: r.sic):
        all_rows.extend(run.raw_rows)

    for row in all_rows:
        cells: List[xlsx.Cell] = []
        for field in _CSV_FIELDS:
            raw = row.get(field, "")
            if field in ("cik", "fiscal_year"):
                cells.append(xlsx.num(_coerce_number(raw), "0"))
            elif field in _USD_FIELDS:
                cells.append(xlsx.num(_coerce_number(raw), xlsx.FMT_USD))
            elif field in ALL_METRICS:
                cells.append(xlsx.num(_coerce_number(raw), metric_format(field)))
            else:
                cells.append(xlsx.txt(str(raw)))
        sh.add_row(cells)


def write_workbook(path: str, runs, years: int, vintage: str, min_sample: int) -> None:
    build_workbook(runs, years, vintage, min_sample).save(path)
