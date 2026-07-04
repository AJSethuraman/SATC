"""Canonical seed for the County Mortgage Delinquency Monitor
(BUILD_SPEC_CFPB.md sec 2).

Build-time source of the `_config` tables. The runner never imports this
module -- it reads the already-expanded dictionary out of the workbook, so
the workbook stays the source of truth (BUILD SPEC 0.4).

THE SLOT MECHANISM (carried wholesale from the FDIC template's [PEERS]):
the hand-picked `[FOOTPRINT]` list IS the watchlist, keyed by 5-digit county
FIPS. `[SERIES]` holds the national rows, the state dashboard rows (derived
from the seed footprint's distinct states at BUILD time, slot-provisioned to
15 state slots) and the 2-measure county TEMPLATE rows the runner expands at
run time into units co_{slot:02d}_{measure}. Adding/removing a county is a
[FOOTPRINT] line edit + re-run, never a rebuild (within built capacity).

DESIGN INVARIANTS:
  * Every FIPS below is real: 01003 (Baldwin AL) and 01073 (Jefferson AL)
    are quoted verbatim in the inspected CFPB county file
    (COVERAGE_RESEARCH_CFPB.md); the remaining ten are well-known large
    counties. All are illustrative -- the in-sheet comment says "replace
    with your footprint; --lookup finds FIPS".
  * FIPS stay TEXT everywhere (trap C1: the CFPB file quote-wraps them so
    Excel cannot strip leading zeros; this seed must not undo that care).
  * Thresholds are heuristic and labeled so (spec sec 3).
Pure ASCII (L3).
"""
from __future__ import annotations

# The 19-column contract header (TEMPLATE_CONTRACT.md sec 3) -- identical to
# the bureau/macro/FDIC templates so control_center + the parser stay generic.
HEADER = [
    "id", "title", "category", "lane", "metric_type", "frequency", "sa_nsa",
    "units", "level_rate_index", "geo_segment", "source_class",
    "dashboard_capable", "watchlist_capable", "source_url", "table_id", "sheet",
    "series_label", "transform", "notes",
]

CFPB_PAGE = ("https://www.consumerfinance.gov/data-research/"
             "mortgage-performance-trends/download-the-data/")

# USPS state abbreviation -> 2-digit state FIPS (text). Full map so a user
# can extend the footprint to any state and the build/runner can derive the
# matching st_{FIPS2} dashboard rows.
STATE_FIPS2 = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08",
    "CT": "09", "DE": "10", "DC": "11", "FL": "12", "GA": "13", "HI": "15",
    "ID": "16", "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21",
    "LA": "22", "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27",
    "MS": "28", "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
    "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46",
    "TN": "47", "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53",
    "WV": "54", "WI": "55", "WY": "56",
}
FIPS2_STATE = {v: k for k, v in STATE_FIPS2.items()}

MEASURES = ("d3089", "d90")
MEASURE_TITLE = {"d3089": "30-89 days delinquent (%)",
                 "d90": "90+ days delinquent (%)"}
MEASURE_FILE = {"d3089": "30-89", "d90": "90-plus"}


# --------------------------------------------------------------------------
# [FOOTPRINT] seed -- 12 illustrative large counties (spec sec 2 order).
# 01003/01073 are verified verbatim from the inspected file; the rest are
# well-known large-county FIPS. slot | fips | name | state | active.
# --------------------------------------------------------------------------
FOOTPRINT = [
    (1, "01003", "Baldwin County", "AL", "TRUE"),      # VERIFIED in file
    (2, "01073", "Jefferson County", "AL", "TRUE"),    # VERIFIED in file
    (3, "06037", "Los Angeles County", "CA", "TRUE"),
    (4, "17031", "Cook County", "IL", "TRUE"),
    (5, "48201", "Harris County", "TX", "TRUE"),
    (6, "04013", "Maricopa County", "AZ", "TRUE"),
    (7, "06073", "San Diego County", "CA", "TRUE"),
    (8, "12086", "Miami-Dade County", "FL", "TRUE"),
    (9, "36047", "Kings County", "NY", "TRUE"),
    (10, "39035", "Cuyahoga County", "OH", "TRUE"),
    (11, "42101", "Philadelphia County", "PA", "TRUE"),
    (12, "53033", "King County", "WA", "TRUE"),
]

FOOTPRINT_HEADER = ["slot", "fips", "name", "state", "active"]


def footprint_rows(footprint_slots):
    """The [FOOTPRINT] table at BUILT capacity: seed counties fill the low
    slots, the remaining rows are EMPTY placeholders (slot number only) the
    user fills by hand -- add a county = type fips/name/state/active on a
    free slot row and re-run; no rebuild within capacity."""
    filled = {f[0]: f for f in FOOTPRINT}
    rows = []
    for slot in range(1, footprint_slots + 1):
        if slot in filled:
            rows.append(list(filled[slot]))
        else:
            rows.append([slot, "", "", "", ""])
    return rows


def seed_states():
    """Distinct footprint states in first-appearance (slot) order -- the
    BUILD-time derivation of the state dashboard rows (spec sec 2)."""
    seen = []
    for _slot, _fips, _name, st, _active in FOOTPRINT:
        if st not in seen:
            seen.append(st)
    return seen


# --------------------------------------------------------------------------
# [THRESHOLDS] -- measure/transform-keyed, direction-aware, honestly labeled
# heuristics (spec sec 3). watch/alert land as NUMERIC cells (L8: Excel's
# number>=text comparison is silently FALSE).
# --------------------------------------------------------------------------
THRESHOLDS = [
    # id, watch, alert, direction, authority
    ("d3089_dev12m", 0.3, 0.6, "above",
     "heuristic: pp deviation of the 30-89 share above its own trailing-12 "
     "average (early-stage pipeline turning)"),
    ("d90_streak3", 2, 3, "above",
     "heuristic: consecutive monthly rises in the 90+ share, capped at 3 "
     "(persistence beats level for a slow-moving serious-delinquency rate)"),
    ("d90_level", 1.5, 3.0, "above",
     "heuristic: long-run non-crisis 90+ share is under ~1 pct; GFC county "
     "peaks ran far higher -- 1.5 = elevated, 3.0 = crisis-adjacent"),
]


def _series(id, title, geo_segment, series_label, watchlist, notes=""):
    """One [SERIES] row in the 19-column contract shape. frequency is
    monthly; values are percent shares (level/rate); everything is Class A
    (public CFPB files, keyless)."""
    return {
        "id": id, "title": title, "category": "mortgage_performance",
        "lane": "dashboard", "metric_type": "delinquency_rate",
        "frequency": "monthly", "sa_nsa": "NSA", "units": "pct",
        "level_rate_index": "rate", "geo_segment": geo_segment,
        "source_class": "A",
        "dashboard_capable": "TRUE",
        "watchlist_capable": "TRUE" if watchlist else "FALSE",
        "source_url": CFPB_PAGE, "table_id": "mortgage-performance",
        "sheet": "", "series_label": series_label, "transform": "level",
        "notes": notes,
    }


def national_rows():
    return [
        _series(f"nat_{m}", f"National {MEASURE_TITLE[m]}", "national",
                MEASURE_FILE[m], watchlist=False,
                notes="RegionType=National row (FIPSCode '-----') -- "
                      "benchmark context, never watchlist (trap C7).")
        for m in MEASURES
    ]


def state_rows(states=None):
    """State dashboard rows derived from the seed footprint's distinct
    states at BUILD time (spec sec 2). Dashboard context only -- the
    watchlist is county-FIPS-keyed by design."""
    states = states if states is not None else seed_states()
    rows = []
    for st in states:
        fips2 = STATE_FIPS2[st]
        for m in MEASURES:
            rows.append(_series(
                f"st_{fips2}_{m}", f"{st} {MEASURE_TITLE[m]}",
                f"state:{fips2}", MEASURE_FILE[m], watchlist=False,
                notes=f"State file row (2-digit FIPS {fips2}) -- the "
                      "fallback lane for suppressed footprint counties."))
    return rows


def county_template_rows():
    """The 2-measure county TEMPLATE rows: geo_segment='county' is the
    placeholder the runner expands to county:NNNNN per active footprint
    slot as units co_{slot:02d}_{measure} -- slot-keyed so footprint edits
    never move raw anchors."""
    return [
        _series(f"co_{m}", f"Footprint county {MEASURE_TITLE[m]}", "county",
                MEASURE_FILE[m], watchlist=True,
                notes="TEMPLATE row expanded per active [FOOTPRINT] slot at "
                      "run time; suppressed counties are ABSENT from the "
                      "file, never zero (trap C4).")
        for m in MEASURES
    ]


def all_series():
    return national_rows() + state_rows() + county_template_rows()


if __name__ == "__main__":
    rows = all_series()
    assert len(HEADER) == 19
    states = seed_states()
    assert len(states) == 10, states
    assert len(rows) == 2 + 20 + 2, len(rows)
    for r in rows:
        assert set(r.keys()) == set(HEADER), f"row {r['id']} key mismatch"
        assert r["source_class"] == "A"
    # only the county template rows are watchlist-capable (BUILD SPEC 0.1)
    wl = [r["id"] for r in rows if r["watchlist_capable"] == "TRUE"]
    assert wl == ["co_d3089", "co_d90"], wl
    fips = [f[1] for f in FOOTPRINT]
    assert len(set(fips)) == len(fips), "duplicate FIPS in seed"
    assert all(len(f) == 5 and f.isdigit() for f in fips)
    assert {t[0] for t in THRESHOLDS} == \
        {"d3089_dev12m", "d90_streak3", "d90_level"}
    print(f"{len(rows)} series rows ({len(states)} states), "
          f"{len(FOOTPRINT)} seed counties, {len(THRESHOLDS)} thresholds -- OK")
