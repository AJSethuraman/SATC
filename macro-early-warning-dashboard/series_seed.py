"""Canonical series-dictionary seed (BUILD_SPEC_MACRO.md sec 2).

Build-time source of the `_config` SERIES table. The runner never imports this
module -- it reads the already-expanded dictionary out of the workbook, so the
dictionary stays the contract and the runner just reads it (BUILD SPEC 0.4).

One row per series. Columns match runner.SERIES_HEADER exactly:
  id, title, category, lane, metric_type, frequency, sa_nsa, units,
  level_rate_index, geo_segment, source_class, dashboard_capable,
  watchlist_capable, source_url, table_id, sheet, series_label, transform, notes

DESIGN INVARIANTS (BUILD SPEC 0.1 / sec 2):
  * Every national row is lane="dashboard", geo_segment="national",
    watchlist_capable=FALSE -- national aggregates can never localize a
    portfolio footprint and the default-deny validator refuses them.
  * The watchlist rows are GENERATED (never hand-typed) from STATES: {ST}UR
    for all 50 states + DC, {ST}ICLAIMS and {ST}PHCI for the 50 states (both
    families verified absent for DC). All lane="watchlist",
    watchlist_capable=TRUE, source_class="A", geo_segment="state:XX".
  * EXCLUDED (verified dead/absent -- must never appear as fetchable rows):
    TEDRATE, CFSI, {ST}SLIND / USSLIND (frozen at Feb 2020 -- the staleness
    lesson), Conference Board LEI. Pure ASCII (L3).
"""
from __future__ import annotations

HEADER = [
    "id", "title", "category", "lane", "metric_type", "frequency", "sa_nsa",
    "units", "level_rate_index", "geo_segment", "source_class",
    "dashboard_capable", "watchlist_capable", "source_url", "table_id", "sheet",
    "series_label", "transform", "notes",
]

FRED = "https://fred.stlouisfed.org/series/"

# Binding licensing notes (COVERAGE_RESEARCH_MACRO.md; ASCII rendering of the
# research text -- the (c)/-- substitutions keep the embedded code pure ASCII, L3).
ICE_NOTE = ("(c) Ice Data Indices -- display-only; FRED serves ~3yr window "
            "from Apr 2026; thresholds are static references, not computed "
            "percentiles")
UMICH_NOTE = ("source-mandated 1-month delay -- as of prior month; "
              "(c) University of Michigan")


def row(id, title, category, lane, metric_type, frequency, sa_nsa, units,
        level_rate_index, geo_segment, transform, notes="",
        source_class="A", dashboard_capable=True, watchlist_capable=False,
        source_url=None, table_id="", sheet="", series_label=""):
    return {
        "id": id, "title": title, "category": category, "lane": lane,
        "metric_type": metric_type, "frequency": frequency, "sa_nsa": sa_nsa,
        "units": units, "level_rate_index": level_rate_index,
        "geo_segment": geo_segment, "source_class": source_class,
        "dashboard_capable": "TRUE" if dashboard_capable else "FALSE",
        "watchlist_capable": "TRUE" if watchlist_capable else "FALSE",
        "source_url": source_url if source_url is not None else FRED + id,
        "table_id": table_id, "sheet": sheet,
        "series_label": series_label, "transform": transform, "notes": notes,
    }


# --------------------------------------------------------------------------
# NATIONAL LANES (~20 rows, all lane="dashboard", geo="national",
# watchlist_capable=FALSE). Thresholds live in build_workbook.THRESHOLDS.
# --------------------------------------------------------------------------
CURVE = [
    row("T10Y3M", "10Y-3M Treasury spread", "curve", "dashboard",
        "curve_spread", "daily", "NSA", "pct_pts", "level", "national", "level",
        "The headline inversion signal (H.15). Threshold direction=below: "
        "watch 0.0 / alert -0.5."),
    row("T10Y2Y", "10Y-2Y Treasury spread", "curve", "dashboard",
        "curve_spread", "daily", "NSA", "pct_pts", "level", "national", "level"),
    row("T10Y3MM", "10Y-3M spread (monthly)", "curve", "dashboard",
        "curve_spread", "monthly", "NSA", "pct_pts", "level", "national",
        "level", "Monthly counterpart for composite math."),
]

LABOR = [
    row("SAHMREALTIME", "Sahm rule (real-time)", "labor", "dashboard",
        "sahm", "monthly", "SA", "pct_pts", "level", "national", "level",
        "The canonical trigger: 3m-avg U-3 rising >= 0.50pp above its "
        "12-month low, built from real-time vintages."),
    row("SAHMCURRENT", "Sahm rule (current data)", "labor", "dashboard",
        "sahm", "monthly", "SA", "pct_pts", "level", "national", "level",
        "Context only: history mutates with BLS revisions."),
    row("ICSA", "Initial claims", "labor", "dashboard", "claims", "weekly",
        "SA", "count", "level", "national", "yoy_ma4",
        "Thursday release; alert on the YoY of the 4-week MA, never raw "
        "weekly deltas."),
    row("IC4WSA", "Initial claims, 4-week MA", "labor", "dashboard", "claims",
        "weekly", "SA", "count", "level", "national", "level",
        "Already a 4-week MA -- shown as the smoothed level."),
    row("CCSA", "Continued claims", "labor", "dashboard", "claims", "weekly",
        "SA", "count", "level", "national", "yoy_ma4",
        "One week behind ICSA."),
    row("AWHMAN", "Mfg avg weekly hours", "labor", "dashboard", "hours",
        "monthly", "SA", "hours", "level", "national", "level",
        "Classic leading composite input (hours cut before heads)."),
]

CREDIT_CONDITIONS = [
    row("BAMLH0A0HYM2", "HY OAS (ICE BofA)", "spreads", "dashboard", "oas",
        "daily", "NSA", "pct", "level", "national", "level", ICE_NOTE),
    row("BAMLC0A0CM", "IG OAS (ICE BofA)", "spreads", "dashboard", "oas",
        "daily", "NSA", "pct", "level", "national", "level", ICE_NOTE),
    row("NFCI", "Chicago Fed NFCI", "conditions", "dashboard",
        "fin_conditions", "weekly", "NSA", "index", "index", "national",
        "level", "Mean-0/sd-1 back to 1971; positive = tighter than average."),
    row("ANFCI", "Chicago Fed adjusted NFCI", "conditions", "dashboard",
        "fin_conditions", "weekly", "NSA", "index", "index", "national",
        "level"),
    row("STLFSI4", "St. Louis Fed stress index", "conditions", "dashboard",
        "fin_conditions", "weekly", "NSA", "index", "index", "national",
        "level", "4th vintage -- STLFSI/2/3 all carry (DISCONTINUED)."),
    row("KCFSI", "Kansas City Fed stress index", "conditions", "dashboard",
        "fin_conditions", "monthly", "NSA", "index", "index", "national",
        "level", "Monthly complement to the weekly stress gauges."),
    row("DRTSCILM", "SLOOS: C&I tightening (large/mid)", "sloos", "dashboard",
        "sloos", "quarterly", "NSA", "pct", "rate", "national", "level",
        "Net pct of banks tightening -- the underwriting cycle."),
]

HOUSING_SENTIMENT = [
    row("PERMIT", "Building permits", "housing", "dashboard", "housing",
        "monthly", "SA", "thous_saar", "level", "national", "yoy_ma3",
        "Latest 1-2 prints are preliminary -- alert on the 3m-smoothed YoY."),
    row("HOUST", "Housing starts", "housing", "dashboard", "housing",
        "monthly", "SA", "thous_saar", "level", "national", "yoy_ma3",
        "Preliminary prints; 3m-smoothed YoY."),
    row("UMCSENT", "UMich consumer sentiment", "sentiment", "dashboard",
        "sentiment", "monthly", "NSA", "index", "index", "national",
        "yoy_pct", UMICH_NOTE),
    row("NEWORDER", "Core capex orders", "sentiment", "dashboard",
        "orders", "monthly", "SA", "USD_mn", "level", "national", "yoy_pct",
        "Nominal, not deflated (LEI deflates it; the FRED copy is not)."),
    row("RECPROUSM156N", "Recession probability (smoothed)", "confirm",
        "dashboard", "recession_prob", "monthly", "NSA", "pct", "rate",
        "national", "level",
        "Publishes 2-3 months behind -- confirmatory only, never early-warning."),
]

NATIONAL = CURVE + LABOR + CREDIT_CONDITIONS + HOUSING_SENTIMENT


# --------------------------------------------------------------------------
# GEOGRAPHIC WATCHLIST -- GENERATED from the state list (never hand-typed).
# 50 states + DC; ICLAIMS and PHCI are verified absent for DC.
# --------------------------------------------------------------------------
STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut",
    "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida",
    "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky",
    "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}

# Families verified absent for DC (COVERAGE_RESEARCH_MACRO.md): claims are
# unverified for DC (omit), PHCI has a verified DC gap.
NO_ICLAIMS = {"DC"}
NO_PHCI = {"DC"}


def _state_row(st, name, family, title_fmt, metric_type, frequency, sa_nsa,
               units, lri, transform, notes=""):
    return row(f"{st}{family}", title_fmt.format(name=name), "state",
               "watchlist", metric_type, frequency, sa_nsa, units, lri,
               f"state:{st}", transform, notes,
               dashboard_capable=False, watchlist_capable=True)


def state_rows():
    rows = []
    for st, name in sorted(STATES.items()):
        rows.append(_state_row(
            st, name, "UR", "{name} unemployment rate", "unemp_rate",
            "monthly", "SA", "pct", "rate", "sahm_gap",
            "Sahm-STYLE state gap: mean(latest 3) - min(12 before). "
            "Oct-2025 observation missing (survey never collected)."))
    for st, name in sorted(STATES.items()):
        if st in NO_ICLAIMS:
            continue
        rows.append(_state_row(
            st, name, "ICLAIMS", "{name} initial claims", "claims",
            "weekly", "NSA", "count", "level", "yoy_ma4",
            "NSA-only -- alert on YoY of the 4-week MA, never raw deltas."))
    for st, name in sorted(STATES.items()):
        if st in NO_PHCI:
            continue
        rows.append(_state_row(
            st, name, "PHCI", "{name} coincident index", "coincident",
            "monthly", "SA", "index", "index", "chg_3p",
            "Annual benchmark re-estimation revises full history; no "
            "Oct-2025 observation (survey never collected)."))
    return rows


def all_series():
    return NATIONAL + state_rows()


if __name__ == "__main__":
    rows = all_series()
    print(f"{len(rows)} series seeded")
    lanes = {}
    for r in rows:
        lanes[r["lane"]] = lanes.get(r["lane"], 0) + 1
    print("by lane:", lanes)
    import re
    wl = [r for r in rows if r["lane"] == "watchlist"]
    assert len(wl) == 151, len(wl)                       # 51 UR + 50 ICLAIMS + 50 PHCI
    for r in wl:
        assert re.match(r"^state:[A-Z]{2}$", r["geo_segment"]), r["id"]
        assert r["watchlist_capable"] == "TRUE" and r["source_class"] == "A", r["id"]
    nat = [r for r in rows if r["lane"] == "dashboard"]
    for r in nat:
        assert r["geo_segment"] == "national" and r["watchlist_capable"] == "FALSE", r["id"]
    ids = {r["id"] for r in rows}
    for dead in ("TEDRATE", "CFSI", "USSLIND"):
        assert dead not in ids, dead
    assert not any("SLIND" in i for i in ids)            # the frozen family
    assert len(HEADER) == 19
    for r in rows:
        assert set(r.keys()) == set(HEADER), f"row {r['id']} key mismatch"
    print(f"watchlist rows: {len(wl)} | national rows: {len(nat)} | OK")
