"""Canonical seed for the Bank Counterparty & Peer Monitor (BUILD_SPEC_FDIC.md sec 2).

Build-time source of the `_config` tables. The runner never imports this
module -- it reads the already-expanded dictionary out of the workbook, so the
workbook stays the source of truth (BUILD SPEC 0.4).

THE INVERSION (what makes this template different): rows are BANKS, not series
types. [SERIES] is a bank-agnostic METRIC dictionary (15 verified metrics,
geo_segment="entity"); the hand-picked [PEERS] list IS the watchlist, keyed by
FDIC CERT. The runner expands active peers x metrics at run time into units
s{slot:02d}_{METRIC} -- adding/removing a bank is a [PEERS] line edit + re-run,
never a rebuild (the flexible-peers USER REQUIREMENT).

DESIGN INVARIANTS:
  * Every metric row uses ONLY fields verified in COVERAGE_RESEARCH_FDIC.md
    (risview_properties.yaml + a captured response). UNVERIFIED fields (ORE,
    INTAN, uninsured deposits, AOCI, HTM fair value) are OUT of v1 -- the
    Texas ratio is a documented VARIANT and CRECONR uses a documented PROXY
    denominator until those field ids are confirmed live.
  * Quarterly-clean fields only where variants exist (trap F1): ROAQ and
    NTLNLSQR, never the YTD ROA/NTLNLSR-as-annualized variants.
  * Derived metrics are pure functions of landed fields, defined identically
    in runner.py (Python) and build_workbook.py (Excel formulas) -- trap F5.
Pure ASCII (L3).
"""
from __future__ import annotations

# The 19-column contract header (TEMPLATE_CONTRACT.md sec 3) -- identical to
# the bureau/macro templates so control_center + the parser stay generic.
HEADER = [
    "id", "title", "category", "lane", "metric_type", "frequency", "sa_nsa",
    "units", "level_rate_index", "geo_segment", "source_class",
    "dashboard_capable", "watchlist_capable", "source_url", "table_id", "sheet",
    "series_label", "transform", "notes",
]

FDIC_DOCS = "https://api.fdic.gov/banks/docs"


def metric(id, title, category, series_label, transform, notes=""):
    """One [SERIES] row = one bank-agnostic METRIC. geo_segment='entity' is
    the placeholder the runner expands to cert:NNN per active peer; every
    metric is both dashboard-rendered and watchlist-counted."""
    return {
        "id": id, "title": title, "category": category, "lane": "dashboard",
        "metric_type": category, "frequency": "quarterly", "sa_nsa": "NSA",
        "units": "pct", "level_rate_index": "rate",
        "geo_segment": "entity", "source_class": "A",
        "dashboard_capable": "TRUE", "watchlist_capable": "TRUE",
        "source_url": FDIC_DOCS, "table_id": "risview", "sheet": "",
        "series_label": series_label, "transform": transform, "notes": notes,
    }


# --------------------------------------------------------------------------
# THE METRIC DICTIONARY (BUILD_SPEC_FDIC.md sec 2 -- 15 verified metrics).
# series_label documents the exact API fields consumed; transform "direct"
# means value = the single field, "derived" means the runner/Excel compute a
# named pure function of the fields (registry keyed by metric id).
# --------------------------------------------------------------------------
ASSET_QUALITY = [
    metric("NCLNLSR", "Noncurrent loans / loans", "asset_quality",
           "NCLNLSR", "direct",
           "Direct API ratio (pct). Heuristic bands vs QBP context."),
    metric("NTLNLSQR", "Net charge-offs / loans (quarterly)", "asset_quality",
           "NTLNLSQR", "direct",
           "QUARTERLY variant (trap F1: NTLNLSR is YTD-annualized). Q4 is "
           "seasonally heavy (cleanup) -- compare YoY, not just QoQ (F7). "
           "QBP Q1'26 industry NCO 0.59pct."),
    metric("PD3089R", "30-89 day past due / loans", "asset_quality",
           "P3LNLS/LNLSGR", "derived",
           "No API ratio field exists -- computed P3LNLS/LNLSGR*100 (both $000). "
           "The early-delinquency pipeline ahead of noncurrent."),
    metric("LNATRESR", "Loss allowance / loans", "asset_quality",
           "LNATRESR", "direct",
           "Direct API ratio (pct); ALLL/ACL coverage of the book."),
    metric("LNRESNCR", "Allowance / noncurrent (coverage)", "asset_quality",
           "LNRESNCR", "direct",
           "Direct API ratio (pct); below-is-bad -- thin coverage of "
           "noncurrents is the stress signal."),
    metric("TEXAS", "Texas ratio (VARIANT)", "composite",
           "NCLNLS/(EQ+LNATRES)", "derived",
           "Documented VARIANT: NCLNLS/(EQ+LNATRES)*100 from verified fields "
           "only. Canonical adds OREO to the numerator and nets intangibles "
           "from equity -- ORE/INTAN field ids UNVERIFIED, pending first live "
           "run (Open Q). Authority: Cassidy/RBC; StL Fed 2025."),
]

CAPITAL_EARNINGS = [
    metric("RBC1AAJ", "Tier 1 leverage ratio", "capital",
           "RBC1AAJ", "direct",
           "Universal (CBLR electors included). CBLR floor 9pct -> 8pct "
           "effective 7/1/2026 (F8); PCA well-cap leverage 5pct."),
    metric("RBCRWAJ", "Total risk-based capital ratio", "capital",
           "RBCRWAJ", "direct",
           "JSON null for CBLR electors (trap F3: null is NOT zero) -- cell "
           "renders blank, never 0. PCA well-cap 10pct."),
    metric("EQV", "Equity / assets", "capital", "EQV", "direct",
           "Direct API ratio (pct); GAAP equity, includes AOCI where "
           "applicable."),
    metric("ROAQ", "Return on assets (quarterly)", "earnings",
           "ROAQ", "direct",
           "QUARTERLY variant (trap F1: ROA is YTD-annualized). QBP Q1'26 "
           "industry ROA 1.26pct."),
    metric("NIMY", "Net interest margin", "earnings", "NIMY", "direct",
           "QBP Q1'26 industry NIM 3.31pct."),
    metric("EEFFR", "Efficiency ratio", "earnings", "EEFFR", "direct",
           "Above-is-bad: expense per dollar of revenue."),
]

FUNDING_CONCENTRATION = [
    metric("LNDEPR", "Loans / deposits", "funding",
           "LNLSNET/DEP", "derived",
           "Computed LNLSNET/DEP*100 (both $000). Heuristic bands."),
    metric("BRODEPR", "Brokered deposits / deposits", "funding",
           "BRO/DEP", "derived",
           "Computed BRO/DEP*100 (both $000; BRO may be null -- blank, never "
           "0). Regulatory salience: FDI Act s29 / 12 CFR 337.6 restricts "
           "brokered deposits below well-capitalized; healthy-bank bands are "
           "heuristic."),
    metric("CRECONR", "CRE concentration (PROXY)", "concentration",
           "(LNRECONS+LNRENRES+LNREMULT)/(EQ+LNATRES)", "derived",
           "2006 interagency guidance screens total CRE vs total RBC "
           "(300pct); CBLR electors report no risk-based capital, so v1 uses "
           "the documented PROXY denominator EQ+LNATRES until the tier-1 "
           "dollar field is verified. 36-month growth leg omitted (merger-"
           "distorted, F6)."),
]

METRIC_ROWS = ASSET_QUALITY + CAPITAL_EARNINGS + FUNDING_CONCENTRATION


# --------------------------------------------------------------------------
# [THRESHOLDS] -- metric-keyed, direction-aware, authority-labeled
# (BUILD_SPEC_FDIC.md sec 2). watch/alert land as NUMERIC cells (the macro
# template's text-"0.5" lesson: Excel's number>=text is silently FALSE).
# --------------------------------------------------------------------------
THRESHOLDS = [
    # id, watch, alert, direction, authority
    ("NCLNLSR", 2.0, 4.0, "above", "heuristic vs QBP industry context"),
    ("NTLNLSQR", 1.0, 2.0, "above", "heuristic; QBP Q1'26 industry NCO 0.59"),
    ("PD3089R", 1.5, 3.0, "above", "heuristic (early-delinquency pipeline)"),
    ("LNATRESR", 1.0, 0.75, "below", "heuristic (thin allowance)"),
    ("LNRESNCR", 100.0, 60.0, "below", "heuristic (coverage of noncurrents)"),
    ("TEXAS", 50.0, 100.0, "above",
     "Cassidy/RBC; StL Fed 2025: 50-100 significant stress, >100 historic "
     "failure signal (v1 VARIANT numerator/denominator)"),
    ("RBC1AAJ", 8.0, 5.0, "below",
     "CBLR floor 8 eff 7/1/2026; PCA well-cap leverage 5"),
    ("RBCRWAJ", 12.0, 10.0, "below",
     "PCA well-cap total RBC 10 (12 = approach band); null for CBLR electors"),
    ("EQV", 8.0, 5.0, "below", "heuristic (leverage-parallel)"),
    ("ROAQ", 0.5, 0.0, "below", "heuristic; QBP Q1'26 industry ROA 1.26"),
    ("NIMY", 2.5, 2.0, "below", "heuristic; QBP Q1'26 industry NIM 3.31"),
    ("EEFFR", 70.0, 85.0, "above", "heuristic (expense discipline)"),
    ("LNDEPR", 90.0, 105.0, "above", "heuristic (funding reliance)"),
    ("BRODEPR", 10.0, 25.0, "above",
     "heuristic bands; FDI Act s29 / 12 CFR 337.6 salience"),
    ("CRECONR", 250.0, 300.0, "above",
     "2006 interagency CRE guidance 300 at ALERT (PROXY denominator); WATCH "
     "= approach band"),
]


# --------------------------------------------------------------------------
# [PEERS] seed -- ~12 illustrative large banks. CERT provenance: 628, 3511
# and 639 are VERIFIED in COVERAGE_RESEARCH_FDIC.md (captured API response /
# spec examples). Every other CERT is illustrative from public sources and
# must be re-verified with `python runner.py --lookup "<name>"` before a live
# run (the _config comment line below the table says so in-sheet).
# group: peer | counterparty | self.
# --------------------------------------------------------------------------
PEERS = [
    # slot, cert, name, group, active
    (1, 628, "JPMorgan Chase Bank NA", "peer", "TRUE"),          # VERIFIED
    (2, 3511, "Wells Fargo Bank NA", "peer", "TRUE"),            # VERIFIED
    (3, 3510, "Bank of America NA", "peer", "TRUE"),
    (4, 7213, "Citibank NA", "peer", "TRUE"),
    (5, 6548, "US Bank NA", "peer", "TRUE"),
    (6, 6384, "PNC Bank NA", "peer", "TRUE"),
    (7, 9846, "Truist Bank", "peer", "TRUE"),
    (8, 4297, "Capital One NA", "peer", "TRUE"),
    (9, 17534, "KeyBank NA", "self", "TRUE"),
    (10, 639, "Bank of New York Mellon", "counterparty", "TRUE"),  # VERIFIED
    (11, 33124, "Goldman Sachs Bank USA", "counterparty", "TRUE"),
    (12, 32992, "Morgan Stanley Bank NA", "counterparty", "TRUE"),
]

PEER_HEADER = ["slot", "cert", "name", "group", "active"]


def peer_rows(peer_slots):
    """The [PEERS] table at BUILT capacity: seed banks fill the low slots,
    the remaining rows are EMPTY placeholders (slot number only) the user
    fills by hand -- add a bank = type cert/name/group/active on a free slot
    row and re-run; no rebuild within capacity."""
    filled = {p[0]: p for p in PEERS}
    rows = []
    for slot in range(1, peer_slots + 1):
        if slot in filled:
            rows.append(list(filled[slot]))
        else:
            rows.append([slot, "", "", "", ""])
    return rows


def all_series():
    return list(METRIC_ROWS)


if __name__ == "__main__":
    rows = all_series()
    assert len(rows) == 15, len(rows)
    assert len(HEADER) == 19
    for r in rows:
        assert set(r.keys()) == set(HEADER), f"row {r['id']} key mismatch"
        assert r["geo_segment"] == "entity" and r["source_class"] == "A"
        assert r["transform"] in ("direct", "derived")
    tids = {t[0] for t in THRESHOLDS}
    assert tids == {r["id"] for r in rows}, "every metric is thresholded"
    certs = [p[1] for p in PEERS]
    assert len(set(certs)) == len(certs), "duplicate CERT in seed"
    print(f"{len(rows)} metrics, {len(PEERS)} seed peers, "
          f"{len(THRESHOLDS)} thresholds -- OK")
