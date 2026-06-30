"""Canonical series-dictionary seed (BUILD SPEC sec 2).

This is the build-time source of the `_config` SERIES table. The runner never
imports it -- the runner reads the already-expanded dictionary out of the
workbook. Keeping the seed here (not hardcoded in the runner) preserves the
rule that the dictionary is the contract and the runner just reads it.

Columns (one row per series), matching SeriesSpec / the sheet header:
  series_id, title, category, lane, metric_type, frequency, sa_nsa, units,
  level_rate_index, geo_segment, dashboard_capable, watchlist_capable,
  transform, alert_rule, notes
"""
from __future__ import annotations

HEADER = [
    "series_id", "title", "category", "lane", "metric_type", "frequency",
    "sa_nsa", "units", "level_rate_index", "geo_segment", "dashboard_capable",
    "watchlist_capable", "transform", "alert_rule", "notes",
]


def row(series_id, title, category, lane, metric_type, frequency, sa_nsa, units,
        level_rate_index, geo_segment, dashboard_capable, watchlist_capable,
        transform, alert_rule, notes=""):
    return {
        "series_id": series_id, "title": title, "category": category, "lane": lane,
        "metric_type": metric_type, "frequency": frequency, "sa_nsa": sa_nsa,
        "units": units, "level_rate_index": level_rate_index, "geo_segment": geo_segment,
        "dashboard_capable": "TRUE" if dashboard_capable else "FALSE",
        "watchlist_capable": "TRUE" if watchlist_capable else "FALSE",
        "transform": transform, "alert_rule": alert_rule, "notes": notes,
    }


def _co_dr(sid, title, category, lane, geo="national"):
    """A quarterly charge-off / delinquency rate dashboard series."""
    return row(sid, title, category, lane, "charge_off" if sid.startswith("COR") else "delinquency",
               "quarterly", "SA", "percent", "rate", geo, True, False,
               "zscore_8q", "zscore",
               "Bank-tier delinquency/charge-off can lag a quarter; stale-check flags it.")


def _sloos(sid, title, lane, alert=True, demand=False):
    return row(sid, title, "sloos_diffusion", lane, "sloos_diffusion", "quarterly",
               "NSA", "net percent", "rate", "national", True, False, "level",
               "sloos_level" if (alert and not demand) else "none",
               "SLOOS demand series -- not a tightening signal." if demand else
               "Net % tightening; +band flags broad tightening.")


# --------------------------------------------------------------------------
# CONSUMER LANE
# --------------------------------------------------------------------------
CONSUMER = [
    # Credit cards (all / top-100 / not-top-100)
    _co_dr("CORCCACBS", "Charge-Off Rate on Credit Card Loans, All Commercial Banks", "credit_card", "consumer"),
    _co_dr("DRCCLACBS", "Delinquency Rate on Credit Card Loans, All Commercial Banks", "credit_card", "consumer"),
    _co_dr("CORCCT100S", "Charge-Off Rate on Credit Card Loans, Top 100 Banks", "credit_card", "consumer"),
    _co_dr("CORCCOBS", "Charge-Off Rate on Credit Card Loans, Banks Not Among 100 Largest", "credit_card", "consumer"),
    _co_dr("DRCCLT100S", "Delinquency Rate on Credit Card Loans, Top 100 Banks", "credit_card", "consumer"),
    _co_dr("DRCCLOBS", "Delinquency Rate on Credit Card Loans, Other Banks", "credit_card", "consumer"),
    # Consumer loans
    _co_dr("CORCACBS", "Charge-Off Rate on Consumer Loans, All Commercial Banks", "consumer_loans", "consumer"),
    _co_dr("DRCLACBS", "Delinquency Rate on Consumer Loans, All Commercial Banks", "consumer_loans", "consumer"),
    _co_dr("DRCLT100S", "Delinquency Rate on Consumer Loans, Top 100 Banks", "consumer_loans", "consumer"),
    _co_dr("DRCLOBS", "Delinquency Rate on Consumer Loans, Other Banks", "consumer_loans", "consumer"),
    _co_dr("CORCOBS", "Charge-Off Rate on Consumer Loans, Other Banks", "consumer_loans", "consumer"),
    # Other consumer (auto / personal ex-card)
    _co_dr("DROCLT100S", "Delinquency Rate on Other Consumer Loans, Top 100 Banks", "other_consumer", "consumer"),
    _co_dr("DROCLOBS", "Delinquency Rate on Other Consumer Loans, Other Banks", "other_consumer", "consumer"),
    _co_dr("DROCLACBS", "Delinquency Rate on Other Consumer Loans, All Commercial Banks", "other_consumer", "consumer"),
    # Single-family residential mortgage
    _co_dr("CORSFRMACBS", "Charge-Off Rate on Single-Family Residential Mortgages, All Banks", "sf_mortgage", "consumer"),
    _co_dr("DRSFRMACBS", "Delinquency Rate on Single-Family Residential Mortgages, All Banks", "sf_mortgage", "consumer"),
    _co_dr("DRSFRMT100S", "Delinquency Rate on Single-Family Residential Mortgages, Top 100 Banks", "sf_mortgage", "consumer"),
    _co_dr("DRSFRMOBS", "Delinquency Rate on Single-Family Residential Mortgages, Other Banks", "sf_mortgage", "consumer"),
    # Leases
    _co_dr("DRLFRACBS", "Delinquency Rate on Leases, All Commercial Banks", "leases", "consumer"),
    # G.19 consumer credit (monthly, dollar levels / flow)
    row("TOTALSL", "Total Consumer Credit Owned and Securitized (SA)", "g19", "consumer", "level",
        "monthly", "SA", "billions $", "level", "national", True, False, "yoy_pct", "none",
        "G.19 dropped the nonfinancial-business sector from the May 2025 release; do not read as a break."),
    row("TOTALNS", "Total Consumer Credit Owned and Securitized (NSA)", "g19", "consumer", "level",
        "monthly", "NSA", "billions $", "level", "national", True, False, "yoy_pct", "none"),
    row("REVOLSL", "Revolving Consumer Credit Owned and Securitized (SA)", "g19", "consumer", "level",
        "monthly", "SA", "billions $", "level", "national", True, False, "yoy_pct", "none"),
    row("NONREVSL", "Nonrevolving Consumer Credit Owned and Securitized (SA)", "g19", "consumer", "level",
        "monthly", "SA", "billions $", "level", "national", True, False, "yoy_pct", "none"),
    row("TOTALSLAR", "Total Consumer Credit, Percent Change at Annual Rate", "g19", "consumer", "flow",
        "monthly", "SA", "percent (annual rate)", "rate", "national", True, False, "level", "none",
        "Already a rate of change -- passthrough, do not re-difference."),
    # Debt service ratios (quarterly)
    row("TDSP", "Household Debt Service Payments as % of Disposable Income", "dsr", "consumer", "ratio",
        "quarterly", "SA", "percent", "ratio", "national", True, False, "level", "none",
        "DSR switched to a credit-bureau methodology in 2024:Q2; watch for a level shift."),
    row("MDSP", "Mortgage Debt Service Payments as % of Disposable Income", "dsr", "consumer", "ratio",
        "quarterly", "SA", "percent", "ratio", "national", True, False, "level", "none",
        "Methodology break 2024:Q2 (credit-bureau)."),
    row("CDSP", "Consumer Debt Service Payments as % of Disposable Income", "dsr", "consumer", "ratio",
        "quarterly", "SA", "percent", "ratio", "national", True, False, "level", "none",
        "Methodology break 2024:Q2 (credit-bureau)."),
    row("FODSP", "Financial Obligations Ratio (discontinued)", "dsr", "consumer", "ratio",
        "quarterly", "SA", "percent", "ratio", "national", False, False, "level", "none",
        "DISCONTINUED after 2023:Q3 -- documented-dead, do not pull live."),
    # SLOOS consumer diffusion
    _sloos("DRTSCLCC", "Net % Banks Tightening Standards for Credit Card Loans", "consumer"),
    _sloos("STDSAUTO", "Net % Banks Tightening Standards for Auto Loans", "consumer"),
    _sloos("STDSOTHCONS", "Net % Banks Tightening Standards for Other Consumer Loans", "consumer"),
    _sloos("DRTSSP", "Net % Banks Tightening Standards for Consumer Loans (subprime)", "consumer"),
    _sloos("SUBLPDHMSENQ", "Net % Banks Reporting Stronger Demand for Consumer Loans", "consumer", demand=True),
]

# --------------------------------------------------------------------------
# COMMERCIAL LANE
# --------------------------------------------------------------------------
COMMERCIAL = [
    # C&I / business
    _co_dr("CORBLACBS", "Charge-Off Rate on Commercial & Industrial Loans, All Banks", "ci", "commercial"),
    _co_dr("DRBLACBS", "Delinquency Rate on Commercial & Industrial Loans, All Banks", "ci", "commercial"),
    _co_dr("DRBLT100S", "Delinquency Rate on C&I Loans, Top 100 Banks", "ci", "commercial"),
    _co_dr("DRBLOBS", "Delinquency Rate on C&I Loans, Other Banks", "ci", "commercial"),
    # CRE (excl. farmland)
    _co_dr("CORCREXFACBS", "Charge-Off Rate on CRE Loans (excl. Farmland), All Banks", "cre", "commercial"),
    _co_dr("DRCRELEXFACBS", "Delinquency Rate on CRE Loans (excl. Farmland), All Banks", "cre", "commercial"),
    _co_dr("DRCRELEXFT100S", "Delinquency Rate on CRE Loans (excl. Farmland), Top 100 Banks", "cre", "commercial"),
    _co_dr("DRCRELEXFOBS", "Delinquency Rate on CRE Loans (excl. Farmland), Other Banks", "cre", "commercial"),
    # All-loans aggregate
    _co_dr("CORALACBS", "Charge-Off Rate on All Loans & Leases, All Banks", "all_loans", "commercial"),
    _co_dr("DRALACBS", "Delinquency Rate on All Loans & Leases, All Banks", "all_loans", "commercial"),
    # SLOOS commercial diffusion
    _sloos("DRTSCILM", "Net % Tightening Standards for C&I Loans to Large/Medium Firms", "commercial"),
    _sloos("DRTSCIS", "Net % Tightening Standards for C&I Loans to Small Firms", "commercial"),
    _sloos("DRSDCILM", "Net % Reporting Stronger Demand for C&I Loans, Large/Medium Firms", "commercial", demand=True),
    _sloos("DRSDCIS", "Net % Reporting Stronger Demand for C&I Loans, Small Firms", "commercial", demand=True),
    _sloos("SUBLPDRCSN", "Net % Tightening Standards for CRE Construction & Land Loans", "commercial"),
    _sloos("SUBLPDRCSM", "Net % Tightening Standards for CRE Multifamily Loans", "commercial"),
    _sloos("SUBLPDRCSC", "Net % Tightening Standards for CRE Nonfarm Nonresidential Loans", "commercial"),
    _sloos("SUBLPDCILSLGNQ", "Net % Increasing Spreads on C&I Loans to Large/Medium Firms", "commercial"),
]

# --------------------------------------------------------------------------
# PRICE LANE -- national dashboard context
# --------------------------------------------------------------------------
PRICE_NATIONAL = [
    row("USSTHPI", "FHFA All-Transactions House Price Index, United States", "hpi_national", "price",
        "index", "quarterly", "SA", "index 1980Q1=100", "index", "national", True, False,
        "index_to_pct", "none", "National HPI -- dashboard only, cannot localize a portfolio."),
    row("HPIPONM226S", "FHFA Purchase-Only House Price Index, United States (Monthly, SA)", "hpi_national",
        "price", "index", "monthly", "SA", "index 1991-01=100", "index", "national", True, False,
        "index_to_pct", "none"),
    row("CSUSHPINSA", "S&P CoreLogic Case-Shiller U.S. National HPI (NSA)", "hpi_national", "price", "index",
        "monthly", "NSA", "index 2000-01=100", "index", "national", True, False, "index_to_pct", "none",
        "Case-Shiller is copyrighted -- internal monitoring only, not for redistribution."),
    row("CSUSHPISA", "S&P CoreLogic Case-Shiller U.S. National HPI (SA)", "hpi_national", "price", "index",
        "monthly", "SA", "index 2000-01=100", "index", "national", True, False, "index_to_pct", "none",
        "Case-Shiller is copyrighted -- internal monitoring only, not for redistribution."),
    row("BOGZ1FL075035503Q", "Z.1 Commercial Real Estate Value (Nonfinancial Corporate), Level", "cre_price",
        "price", "level", "quarterly", "NSA", "millions $", "level", "national", True, False, "level", "none",
        "DOLLAR LEVEL, not a 2000=100 index -- never apply index_to_pct."),
    row("COMREPUSQ159N", "Commercial Real Estate Prices for United States (YoY %)", "cre_price", "price",
        "rate", "quarterly", "NSA", "percent (YoY)", "rate", "national", True, False, "level", "none",
        "Already expressed as YoY % -- passthrough, do not re-difference."),
    row("BOGZ1FL075035403Q", "Z.1 Multifamily Residential Real Estate Value, Level", "cre_price", "price",
        "level", "quarterly", "NSA", "millions $", "level", "national", True, False, "level", "none",
        "DOLLAR LEVEL, not an index -- never apply index_to_pct."),
]

# --------------------------------------------------------------------------
# PRICE LANE -- geographic (the ONLY watchlist-capable series)
# --------------------------------------------------------------------------
STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
    "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}

# FHFA metro convention ATNHPIUS[CBSA]Q -- starter set of major CBSAs (extensible
# via the _config CBSA_EXTENSIONS table).
CBSAS = {
    "35620": "New York-Newark-Jersey City, NY-NJ-PA",
    "31080": "Los Angeles-Long Beach-Anaheim, CA",
    "16980": "Chicago-Naperville-Elgin, IL-IN-WI",
    "19100": "Dallas-Fort Worth-Arlington, TX",
    "26420": "Houston-The Woodlands-Sugar Land, TX",
    "47900": "Washington-Arlington-Alexandria, DC-VA-MD-WV",
    "33100": "Miami-Fort Lauderdale-Pompano Beach, FL",
    "37980": "Philadelphia-Camden-Wilmington, PA-NJ-DE-MD",
    "12060": "Atlanta-Sandy Springs-Alpharetta, GA",
    "38060": "Phoenix-Mesa-Chandler, AZ",
    "14460": "Boston-Cambridge-Newton, MA-NH",
    "41860": "San Francisco-Oakland-Berkeley, CA",
    "42660": "Seattle-Tacoma-Bellevue, WA",
    "33460": "Minneapolis-St. Paul-Bloomington, MN-WI",
    "19820": "Detroit-Warren-Dearborn, MI",
    "12420": "Austin-Round Rock-Georgetown, TX",
    "40140": "Riverside-San Bernardino-Ontario, CA",
    "45300": "Tampa-St. Petersburg-Clearwater, FL",
}

# Case-Shiller 20-city components (seasonally adjusted, *XRSA).
CASE_SHILLER = {
    "ATXRSA": "Atlanta, GA", "BOXRSA": "Boston, MA", "CRXRSA": "Charlotte, NC",
    "CHXRSA": "Chicago, IL", "CEXRSA": "Cleveland, OH", "DAXRSA": "Dallas, TX",
    "DNXRSA": "Denver, CO", "DEXRSA": "Detroit, MI", "LVXRSA": "Las Vegas, NV",
    "LXXRSA": "Los Angeles, CA", "MIXRSA": "Miami, FL", "MNXRSA": "Minneapolis, MN",
    "NYXRSA": "New York, NY", "PHXRSA": "Phoenix, AZ", "POXRSA": "Portland, OR",
    "SDXRSA": "San Diego, CA", "SFXRSA": "San Francisco, CA", "SEXRSA": "Seattle, WA",
    "TPXRSA": "Tampa, FL", "WDXRSA": "Washington, DC",
}


def _geo_rows():
    out = []
    for code, name in STATES.items():
        out.append(row(f"{code}STHPI", f"FHFA All-Transactions HPI -- {name}", "hpi_state", "price",
                       "price", "quarterly", "NSA", "index 1980Q1=100", "index", f"state:{code}",
                       False, True, "yoy_pct", "none",
                       "FHFA state HPI -- geographically keyed; watchlist-capable."))
    for cbsa, name in CBSAS.items():
        out.append(row(f"ATNHPIUS{cbsa}Q", f"FHFA HPI -- {name}", "hpi_metro", "price", "price",
                       "quarterly", "NSA", "index 1995Q1=100", "index", f"cbsa:{cbsa}", False, True,
                       "yoy_pct", "none", "FHFA metro HPI (CBSA) -- watchlist-capable."))
    for sid, name in CASE_SHILLER.items():
        out.append(row(sid, f"Case-Shiller HPI -- {name}", "hpi_caseshiller", "price", "price",
                       "monthly", "SA", "index 2000-01=100", "index", f"metro:{name}", False, True,
                       "yoy_pct", "none",
                       "Case-Shiller metro -- copyrighted, internal only, higher-frequency confirmation."))
    return out


def all_series():
    return CONSUMER + COMMERCIAL + PRICE_NATIONAL + _geo_rows()


def cbsa_extension_rows():
    return [{"cbsa": k, "name": v, "series_id": f"ATNHPIUS{k}Q"} for k, v in CBSAS.items()]


if __name__ == "__main__":
    rows = all_series()
    print(f"{len(rows)} series seeded")
    lanes = {}
    for r in rows:
        lanes[r["lane"]] = lanes.get(r["lane"], 0) + 1
    print("by lane:", lanes)
    wl = [r for r in rows if r["watchlist_capable"] == "TRUE"]
    print(f"watchlist-capable: {len(wl)}")
