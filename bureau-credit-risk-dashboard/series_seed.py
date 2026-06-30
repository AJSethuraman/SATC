"""Canonical series-dictionary seed (BUILD_SPEC_BUREAU.md sec 2).

Build-time source of the `_config` SERIES table. The runner never imports this
module -- it reads the already-expanded dictionary out of the workbook, so the
dictionary stays the contract and the runner just reads it (BUILD SPEC 0.4).

One row per series. Columns match runner.SERIES_HEADER exactly:
  id, title, category, lane, metric_type, frequency, sa_nsa, units,
  level_rate_index, geo_segment, source_class, dashboard_capable,
  watchlist_capable, source_url, table_id, sheet, series_label, transform, notes

DESIGN INVARIANT (BUILD SPEC 0.1 / sec 2): every seeded row is source_class="A",
dashboard_capable=TRUE, watchlist_capable=FALSE. The lone lane="watchlist" row
(WATCHLIST_MSA_PLACEHOLDER) documents the gated lane and stays unpopulated under
the public stand-in; the default-deny validator (runner sec 3) refuses it on the
source_class="A" gate even if someone flips its capability flag. Pure ASCII (L3).

SOURCE LOCATORS (Open Question #5): the literal NY Fed HHDC published-table
column schema was NOT established by the coverage research, so table_id / sheet /
series_label are conceptual locators that MUST be bound to the real published
layout before any live pull. HhdcProvider._parse_table refuses until they are.
"""
from __future__ import annotations

HEADER = [
    "id", "title", "category", "lane", "metric_type", "frequency", "sa_nsa",
    "units", "level_rate_index", "geo_segment", "source_class",
    "dashboard_capable", "watchlist_capable", "source_url", "table_id", "sheet",
    "series_label", "transform", "notes",
]

# The NY Fed Household Debt & Credit (HHDC) quarterly report + data page. The
# underlying workbook filename carries the vintage (e.g. ...2026q1.xlsx) and is
# resolved at bind time; this is the stable landing page (BUILD SPEC sec 1).
HHDC_URL = "https://www.newyorkfed.org/microeconomics/hhdc"


def row(id, title, category, lane, metric_type, frequency, sa_nsa, units,
        level_rate_index, geo_segment, transform, notes="",
        source_class="A", dashboard_capable=True, watchlist_capable=False,
        source_url=HHDC_URL, table_id="", sheet="", series_label=""):
    return {
        "id": id, "title": title, "category": category, "lane": lane,
        "metric_type": metric_type, "frequency": frequency, "sa_nsa": sa_nsa,
        "units": units, "level_rate_index": level_rate_index,
        "geo_segment": geo_segment, "source_class": source_class,
        "dashboard_capable": "TRUE" if dashboard_capable else "FALSE",
        "watchlist_capable": "TRUE" if watchlist_capable else "FALSE",
        "source_url": source_url, "table_id": table_id, "sheet": sheet,
        "series_label": series_label, "transform": transform, "notes": notes,
    }


# --------------------------------------------------------------------------
# BALANCES -- household debt balances by product (HHDC, 5% Equifax sample)
# --------------------------------------------------------------------------
BALANCES = [
    row("hhdc_total_balance", "Total household debt balance", "aggregate",
        "dashboard", "balance", "quarterly", "NSA", "USD_tn", "level", "national",
        "yoy_pct", "5% anonymized Equifax sample, not a census.",
        table_id="total_debt_balance", sheet="Page 3 Data", series_label="Total Debt"),
    row("hhdc_mortgage_balance", "Mortgage balance", "mortgage", "dashboard",
        "balance", "quarterly", "NSA", "USD_tn", "level", "national", "yoy_pct", "",
        table_id="total_debt_balance", sheet="Page 3 Data", series_label="Mortgage"),
    row("hhdc_heloc_balance", "HELOC balance", "heloc", "dashboard", "balance",
        "quarterly", "NSA", "USD_bn", "level", "national", "yoy_pct", "",
        table_id="total_debt_balance", sheet="Page 3 Data", series_label="HE Revolving"),
    row("hhdc_auto_balance", "Auto loan balance", "auto", "dashboard", "balance",
        "quarterly", "NSA", "USD_tn", "level", "national", "yoy_pct", "",
        table_id="total_debt_balance", sheet="Page 3 Data", series_label="Auto Loan"),
    row("hhdc_card_balance", "Credit card balance", "card", "dashboard", "balance",
        "quarterly", "NSA", "USD_tn", "level", "national", "yoy_pct",
        "CIIR Q1'26 ref: bankcard $1.12tn (+4.6% YoY).",
        table_id="total_debt_balance", sheet="Page 3 Data", series_label="Credit Card"),
    row("hhdc_student_balance", "Student loan balance", "student", "dashboard",
        "balance", "quarterly", "NSA", "USD_tn", "level", "national", "yoy_pct", "",
        table_id="total_debt_balance", sheet="Page 3 Data", series_label="Student Loan"),
    row("hhdc_personal_balance", "Personal/unsecured balance", "personal",
        "dashboard", "balance", "quarterly", "NSA", "USD_bn", "level", "national",
        "yoy_pct", "", table_id="total_debt_balance", sheet="Page 3 Data",
        series_label="Other"),
]

# --------------------------------------------------------------------------
# DELINQUENCY -- 90+ DPD rates and transition flows by product
# --------------------------------------------------------------------------
DELINQUENCY = [
    row("hhdc_card_90plus", "Credit card 90+ DPD rate", "card", "dashboard",
        "delinq_rate", "quarterly", "NSA", "pct", "rate", "national", "level",
        "CIIR Q1'26 ref: bankcard 90+ DPD 2.53% (+10bps YoY).",
        table_id="pct_balance_90plus", sheet="Page 12 Data", series_label="Credit Card"),
    row("hhdc_auto_90plus", "Auto 90+ DPD rate", "auto", "dashboard", "delinq_rate",
        "quarterly", "NSA", "pct", "rate", "national", "level", "",
        table_id="pct_balance_90plus", sheet="Page 12 Data", series_label="Auto Loan"),
    row("hhdc_mortgage_90plus", "Mortgage 90+ DPD rate", "mortgage", "dashboard",
        "delinq_rate", "quarterly", "NSA", "pct", "rate", "national", "level", "",
        table_id="pct_balance_90plus", sheet="Page 12 Data", series_label="Mortgage"),
    row("hhdc_flow_to_30", "Flow into 30+ DPD (all products)", "aggregate",
        "dashboard", "delinq_flow", "quarterly", "NSA", "pct", "rate", "national",
        "level", "Transition flow into early delinquency.",
        table_id="flow_into_delinquency", sheet="Page 13 Data", series_label="30+ Flow"),
    row("hhdc_flow_to_90", "Flow into 90+ DPD (all products)", "aggregate",
        "dashboard", "delinq_flow", "quarterly", "NSA", "pct", "rate", "national",
        "level", "Transition flow into serious delinquency.",
        table_id="flow_into_delinquency", sheet="Page 13 Data", series_label="90+ Flow"),
]

# --------------------------------------------------------------------------
# ORIGINATIONS -- new originations by product (one-quarter lag)
# --------------------------------------------------------------------------
ORIGINATIONS = [
    row("hhdc_card_orig", "Bankcard originations", "card", "dashboard",
        "origination", "quarterly", "NSA", "count_m", "level", "national", "yoy_pct",
        "One-quarter lag; CIIR ref 21.9M (+13% YoY, Q4'25).",
        table_id="card_originations", sheet="Page 9 Data", series_label="New Cards"),
    row("hhdc_personal_orig", "Personal-loan originations", "personal", "dashboard",
        "origination", "quarterly", "NSA", "count_m", "level", "national", "yoy_pct",
        "CIIR ref record 7.6M (+21.7% YoY).",
        table_id="loan_originations", sheet="Page 7 Data", series_label="Personal"),
    row("hhdc_auto_orig", "Auto originations", "auto", "dashboard", "origination",
        "quarterly", "NSA", "count_m", "level", "national", "yoy_pct",
        "One-quarter lag.",
        table_id="auto_originations", sheet="Page 8 Data", series_label="Auto"),
    row("hhdc_mortgage_orig", "Mortgage originations", "mortgage", "dashboard",
        "origination", "quarterly", "NSA", "USD_bn", "level", "national", "yoy_pct",
        "One-quarter lag.",
        table_id="mortgage_originations", sheet="Page 6 Data", series_label="Mortgage"),
]

# --------------------------------------------------------------------------
# STATE (annual Q4 only) -- deliberately NOT a watchlist geo key
# --------------------------------------------------------------------------
STATE = [
    row("hhdc_state_balance_annual", "State total balance (annual Q4)", "aggregate",
        "dashboard", "balance", "annual", "NSA", "USD_bn", "level", "state_annual",
        "yoy_pct",
        "Annual Q4 only; NOT a watchlist geo key -- quarterly all-state withheld "
        "by Equifax contract.",
        table_id="state_level_debt", sheet="State Data", series_label="Total"),
]

# --------------------------------------------------------------------------
# WATCHLIST LANE -- gated placeholder (licensed Class C feed required)
# --------------------------------------------------------------------------
# Seeded source_class="A", watchlist_capable=FALSE: documents the lane's
# existence and its licensed requirement. The default-deny validator refuses it
# on the source_class="A" gate even if watchlist_capable is flipped TRUE
# (defense in depth -- BUILD SPEC sec 2 / 3).
WATCHLIST = [
    row("WATCHLIST_MSA_PLACEHOLDER", "MSA watchlist (LICENSED req'd)", "aggregate",
        "watchlist", "delinq_rate", "monthly", "NSA", "pct", "rate", "msa", "level",
        "GATED: requires Class C Prama MSA feed; refused under public stand-in "
        "(source_class=A).",
        table_id="", sheet="", series_label=""),
]


def all_series():
    return BALANCES + DELINQUENCY + ORIGINATIONS + STATE + WATCHLIST


if __name__ == "__main__":
    rows = all_series()
    print(f"{len(rows)} series seeded")
    lanes = {}
    for r in rows:
        lanes[r["lane"]] = lanes.get(r["lane"], 0) + 1
    print("by lane:", lanes)
    classes = {}
    for r in rows:
        classes[r["source_class"]] = classes.get(r["source_class"], 0) + 1
    print("by source_class:", classes)
    wl = [r for r in rows if r["watchlist_capable"] == "TRUE"]
    print(f"watchlist_capable: {len(wl)} (must be 0 under public stand-in)")
    assert len(HEADER) == 19
    for r in rows:
        assert set(r.keys()) == set(HEADER), f"row {r['id']} key mismatch"
