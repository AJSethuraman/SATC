"""Canonical seed for the Bank Counterparty & Peer Monitor (BUILD_SPEC_FDIC.md sec 2).

Build-time source of the `_config` tables. The runner never imports this
module -- it reads the already-expanded dictionary out of the workbook, so the
workbook stays the source of truth (BUILD SPEC 0.4).

THE INVERSION (what makes this template different): rows are BANKS, not series
types. [SERIES] is a bank-agnostic METRIC dictionary (53 verified metrics:
15 core + the 38-metric v1.1 competitor pack; geo_segment="entity"); the hand-picked [PEERS] list IS the watchlist, keyed by
FDIC CERT. The runner expands active peers x metrics at run time into units
s{slot:02d}_{METRIC} -- adding/removing a bank is a [PEERS] line edit + re-run,
never a rebuild (the flexible-peers USER REQUIREMENT).

DESIGN INVARIANTS:
  * Every metric row uses ONLY fields verified in COVERAGE_RESEARCH_FDIC.md
    / RESEARCH_COMPETITOR_PACK.md (93/93 pack fields). v1.1 brings uninsured
    deposits + HTM/AFS fair-value fields IN (verified); still-UNVERIFIED
    fields (ORE, INTAN, AOCI stock) stay OUT -- the
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
# THE METRIC DICTIONARY (BUILD_SPEC_FDIC.md sec 2 + SPEC_COMPETITOR_PACK.md
# sec 1 -- 53 verified metrics: 15 core + 38 pack).
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

# --------------------------------------------------------------------------
# v1.1 COMPETITOR PACK (SPEC_COMPETITOR_PACK.md secs 1-2, fields verified in
# RESEARCH_COMPETITOR_PACK.md). Two-track design (USER, binding): CONSUMER
# classes get the DQ/NCO track (retail classification is DPD-formula-driven
# under the Uniform Retail Credit Classification policy -- DQ IS the story);
# COMMERCIAL classes get Call-Report DQ as the public FLOOR (criticized/
# classified arrives via the EDGAR template #6).
# Naming: R-suffix ratio twins are consumed DIRECTLY only where the twin name
# fits the 8-char field limit (P3CRCD_BOOK yes, P3CONOTH_BOOK no); all other rates
# are computed from the verified dollar triple/flow + balance. Quarterly NCO
# rates are ANNUALIZED x4 (the FDIC's own NTLNLSQR convention) and use the
# Q flow fields ONLY (trap F1) -- note the 8-char truncation (NTRECONQ).
# --------------------------------------------------------------------------
_pack = metric        # pack rows use the same 19-column row constructor

CONSUMER_TRACK = [
    # credit card (verified R twins; NCOq computed)
    _pack("P3CRCD_BOOK", "Card 30-89 PD %", "consumer_credit",
          "P3CRCD/LNCRCD*100", "derived",
          "Computed over the BOOK. The FDIC publishes a twin (P3CRCDR) over TOTAL ASSETS -- a different ratio, which is why this one is named _BOOK (#268, verified live 5 Sep 2026)."),
    _pack("P9CRCD_BOOK", "Card 90+ PD %", "consumer_credit",
          "P9CRCD/LNCRCD*100", "derived",
          "Computed over the BOOK. The FDIC publishes a twin (P9CRCDR) over TOTAL ASSETS -- a different ratio, which is why this one is named _BOOK (#268, verified live 5 Sep 2026)."),
    _pack("NACRCD_BOOK", "Card nonaccrual %", "consumer_credit",
          "NACRCD/LNCRCD*100", "derived",
          "Computed over the BOOK. The FDIC publishes a twin (NACRCDR) over TOTAL ASSETS -- a different ratio, which is why this one is named _BOOK (#268, verified live 5 Sep 2026)."),
    _pack("NTCRCDQ_BOOK", "Card NCO % (q, ann.)", "consumer_credit",
          "NTCRCDQ/LNCRCD*400", "derived",
          "QUARTERLY flow (F1; 8-char name NTCRCDQ), annualized x4 like "
          "NTLNLSQR. Card runs structurally high -- QBP context in the "
          "subtitle."),
    # auto (verified twins; *AUTO fields exist only from 2011 -- F-trap)
    _pack("P3AUTO_BOOK", "Auto 30-89 PD %", "consumer_credit",
          "P3AUTO/LNAUTO*100", "derived",
          "Computed over the BOOK. The FDIC publishes a twin (P3AUTOR) over TOTAL ASSETS -- a different ratio, which is why this one is named _BOOK (#268, verified live 5 Sep 2026)."),
    _pack("P9AUTO_BOOK", "Auto 90+ PD %", "consumer_credit",
          "P9AUTO/LNAUTO*100", "derived",
          "Computed over the BOOK. The FDIC publishes a twin (P9AUTOR) over TOTAL ASSETS -- a different ratio, which is why this one is named _BOOK (#268, verified live 5 Sep 2026)."),
    _pack("NAAUTO_BOOK", "Auto nonaccrual %", "consumer_credit",
          "NAAUTO/LNAUTO*100", "derived",
          "Computed over the BOOK. The FDIC publishes a twin (NAAUTOR) over TOTAL ASSETS -- a different ratio, which is why this one is named _BOOK (#268, verified live 5 Sep 2026)."),
    _pack("NTAUTOQ_BOOK", "Auto NCO % (q, ann.)", "consumer_credit",
          "NTAUTOQ/LNAUTO*400", "derived",
          "Quarterly flow annualized x4; NEVER the YTD NTAUTO (F1)."),
    # other consumer (twin names exceed 8 chars -- computed from the triple)
    _pack("P3CONOTH_BOOK", "Other-cons 30-89 PD %", "consumer_credit",
          "P3CONOTH/LNCONOTH*100", "derived",
          "Computed over the BOOK. The FDIC does publish P3CONOTHR -- over "
          "TOTAL ASSETS (verified live 5 Sep 2026), which is a different "
          "ratio; ours is named P3CONOTH_BOOK so the two cannot be "
          "confused."),
    _pack("P9CONOTH_BOOK", "Other-cons 90+ PD %", "consumer_credit",
          "P9CONOTH/LNCONOTH*100", "derived", "Computed; still accruing."),
    _pack("NACONOTH_BOOK", "Other-cons nonaccrual %", "consumer_credit",
          "NACONOTH/LNCONOTH*100", "derived", "Computed."),
    _pack("NTCONOTQ_BOOK", "Other-cons NCO % (q, ann.)", "consumer_credit",
          "NTCONOTQ/LNCONOTH*400", "derived",
          "Quarterly flow annualized x4 (8-char truncated NTCONOTQ)."),
    # 1-4 family residential (verified twins) + HELOC drill-in
    _pack("P3RERES_BOOK", "Resi 30-89 PD %", "consumer_credit",
          "P3RERES/LNRERES*100", "derived",
          "Computed over the BOOK. The FDIC publishes a twin (P3RERESR) over TOTAL ASSETS -- a different ratio, which is why this one is named _BOOK (#268, verified live 5 Sep 2026)."),
    _pack("P9RERES_BOOK", "Resi 90+ PD %", "consumer_credit",
          "P9RERES/LNRERES*100", "derived",
          "Computed over the BOOK. The FDIC publishes a twin (P9RERESR) over TOTAL ASSETS -- a different ratio, which is why this one is named _BOOK (#268, verified live 5 Sep 2026)."),
    _pack("NARERES_BOOK", "Resi nonaccrual %", "consumer_credit",
          "NARERES/LNRERES*100", "derived",
          "Computed over the BOOK. The FDIC publishes a twin (NARERESR) over TOTAL ASSETS -- a different ratio, which is why this one is named _BOOK (#268, verified live 5 Sep 2026)."),
    _pack("NTRERESQ_BOOK", "Resi NCO % (q, ann.)", "consumer_credit",
          "NTRERESQ/LNRERES*400", "derived",
          "Quarterly flow annualized x4."),
    _pack("P3RELOC_BOOK", "HELOC 30-89 PD %", "consumer_credit",
          "P3RELOC/LNRELOC*100", "derived",
          "Computed over the BOOK. The FDIC publishes a twin (P3RELOCR) over TOTAL ASSETS -- a different ratio, which is why this one is named _BOOK (#268, verified live 5 Sep 2026)."),
    _pack("P9RELOC_BOOK", "HELOC 90+ PD %", "consumer_credit",
          "P9RELOC/LNRELOC*100", "derived",
          "Computed over the BOOK. The FDIC publishes a twin (P9RELOCR) over TOTAL ASSETS -- a different ratio, which is why this one is named _BOOK (#268, verified live 5 Sep 2026)."),
    _pack("NARELOC_BOOK", "HELOC nonaccrual %", "consumer_credit",
          "NARELOC/LNRELOC*100", "derived",
          "Computed over the BOOK. The FDIC publishes a twin (NARELOCR) over TOTAL ASSETS -- a different ratio, which is why this one is named _BOOK (#268, verified live 5 Sep 2026)."),
]

COMMERCIAL_FLOOR = [
    # construction
    _pack("P3RECONS_BOOK", "Constr 30-89 PD %", "commercial_credit",
          "P3RECONS/LNRECONS*100", "derived",
          "Computed over the BOOK (the FDIC publishes this twin over "
          "TOTAL ASSETS). PUBLIC FLOOR: commercial "
          "risk ratings lead delinquency; criticized/classified via EDGAR "
          "template. Splits exist from ~2007-08 (null-tolerant)."),
    _pack("P9RECONS_BOOK", "Constr 90+ PD %", "commercial_credit",
          "P9RECONS/LNRECONS*100", "derived", "Computed; still accruing."),
    _pack("NARECONS_BOOK", "Constr nonaccrual %", "commercial_credit",
          "NARECONS/LNRECONS*100", "derived", "Computed."),
    _pack("NTRECONQ_BOOK", "Constr NCO % (q, ann.)", "commercial_credit",
          "NTRECONQ/LNRECONS*400", "derived",
          "Quarterly flow annualized x4; 8-char truncation is VERIFIED here "
          "(NTRECONQ, never NTRECONSQ)."),
    # nonfarm nonresidential CRE
    _pack("P3RENRES_BOOK", "CRE-NFN 30-89 PD %", "commercial_credit",
          "P3RENRES/LNRENRES*100", "derived", "Computed (twin >8 chars)."),
    _pack("P9RENRES_BOOK", "CRE-NFN 90+ PD %", "commercial_credit",
          "P9RENRES/LNRENRES*100", "derived", "Computed; still accruing."),
    _pack("NARENRES_BOOK", "CRE-NFN nonaccrual %", "commercial_credit",
          "NARENRES/LNRENRES*100", "derived",
          "Computed. The office-stress headline metric."),
    _pack("NTRENREQ_BOOK", "CRE-NFN NCO % (q, ann.)", "commercial_credit",
          "NTRENREQ/LNRENRES*400", "derived",
          "Quarterly flow annualized x4 (8-char truncated NTRENREQ)."),
    # multifamily
    _pack("P3REMULT_BOOK", "Multifam 30-89 PD %", "commercial_credit",
          "P3REMULT/LNREMULT*100", "derived", "Computed (twin >8 chars)."),
    _pack("P9REMULT_BOOK", "Multifam 90+ PD %", "commercial_credit",
          "P9REMULT/LNREMULT*100", "derived", "Computed; still accruing."),
    _pack("NAREMULT_BOOK", "Multifam nonaccrual %", "commercial_credit",
          "NAREMULT/LNREMULT*100", "derived", "Computed."),
    _pack("NTREMULQ_BOOK", "Multifam NCO % (q, ann.)", "commercial_credit",
          "NTREMULQ/LNREMULT*400", "derived",
          "Quarterly flow annualized x4 (8-char truncated NTREMULQ)."),
    # C&I (verified twins for PD/NA; NCOq computed)
    _pack("P3CI_BOOK", "C&I 30-89 PD %", "commercial_credit",
          "P3CI/LNCI*100", "derived",
          "Computed over the BOOK. The FDIC publishes a twin (P3CIR) over TOTAL ASSETS -- a different ratio, which is why this one is named _BOOK (#268, verified live 5 Sep 2026)."),
    _pack("P9CI_BOOK", "C&I 90+ PD %", "commercial_credit",
          "P9CI/LNCI*100", "derived",
          "Computed over the BOOK. The FDIC publishes a twin (P9CIR) over TOTAL ASSETS -- a different ratio, which is why this one is named _BOOK (#268, verified live 5 Sep 2026)."),
    _pack("NACI_BOOK", "C&I nonaccrual %", "commercial_credit",
          "NACI/LNCI*100", "derived",
          "Computed over the BOOK. The FDIC publishes a twin (NACIR) over TOTAL ASSETS -- a different ratio, which is why this one is named _BOOK (#268, verified live 5 Sep 2026)."),
    _pack("NTCIQ_BOOK", "C&I NCO % (q, ann.)", "commercial_credit",
          "NTCIQ/LNCI*400", "derived", "Quarterly flow annualized x4."),
]

SVB_PACK = [
    _pack("UNINSDEPR", "Uninsured deposit share %", "funding_stress",
          "DEPUNINS/DEP*100", "derived",
          "SVB metric. DEPUNINS (RC-O Mem 2) is FILED by $1B+ reporters "
          "only -- null renders BLANK + a digest note, NEVER 0 (F3). 2023 "
          "failures context: SVB ~94 pct uninsured."),
    _pack("UNRLZCAPR", "Unrealized sec loss / capital %", "funding_stress",
          "((SCHA-SCHF)+(SCAA-SCAF))/(EQ+LNATRES)*100", "derived",
          "SVB metric, BOTH legs COMPUTED (no named unrealized field "
          "exists): HTM (SCHA-SCHF) + AFS (SCAA-SCAF) over the EQ+LNATRES "
          "cushion. Positive = unrealized LOSS. EQCCOMPI is the YTD OCI "
          "FLOW, not the AOCI stock -- deliberately NOT used. SVB ran "
          ">100 pct."),
    _pack("FHLBASSR", "FHLB advances / assets %", "funding_stress",
          "OTHBFHLB/ASSET*100", "derived",
          "SVB metric: wholesale-funding reliance; FHLB advances are the "
          "classic stressed-liquidity backfill."),
]

METRIC_ROWS = (ASSET_QUALITY + CAPITAL_EARNINGS + FUNDING_CONCENTRATION
               + CONSUMER_TRACK + COMMERCIAL_FLOOR + SVB_PACK)


# --------------------------------------------------------------------------
# [THRESHOLDS] -- metric-keyed, direction-aware, authority-labeled
# (BUILD_SPEC_FDIC.md sec 2). watch/alert land as NUMERIC cells (the macro
# template's text-"0.5" lesson: Excel's number>=text is silently FALSE).
# --------------------------------------------------------------------------
THRESHOLDS = [
    # id, watch, alert, direction, authority
    # CALIBRATED against live 2026Q1 data (JPMorgan cert 628 and peers): the
    # original heuristic bands fired on ~11/12 healthy megabanks because normal
    # values (46% uninsured, 3.3% card NCO, 2% CRE nonaccrual) sat inside them.
    # Bands moved to where genuine distress lives, anchored to real pristine-bank
    # readings + supervisory norms. The user (credit review) tunes these directly
    # in the _config [THRESHOLDS] tab -- data, not code.
    ("NCLNLSR", 1.5, 3.0, "above", "noncurrent rate; healthy <1 (JPM 0.85)"),
    ("NTLNLSQR", 1.0, 2.0, "above", "total NCO; QBP Q1'26 industry 0.59"),
    ("PD3089R", 1.5, 3.0, "above", "early-delinquency pipeline"),
    ("LNATRESR", 1.0, 0.75, "below", "thin allowance / loans"),
    ("LNRESNCR", 100.0, 50.0, "below", "coverage: reserves < noncurrents"),
    ("TEXAS", 25.0, 50.0, "above",
     "Cassidy/RBC; <25 healthy, 50-100 significant stress, >100 historic "
     "failure signal (v1 VARIANT numerator/denominator; JPM 3.56)"),
    ("RBC1AAJ", 6.0, 5.0, "below",
     "PCA well-cap leverage 5; CBLR floor 8 eff 7/1/2026"),
    ("RBCRWAJ", 11.0, 10.5, "below",
     "PCA well-cap total RBC 10; null for CBLR electors"),
    ("EQV", 7.0, 5.0, "below", "equity/assets (leverage-parallel)"),
    ("ROAQ", 0.5, 0.0, "below", "QBP Q1'26 industry ROA 1.26"),
    ("NIMY", 2.0, 1.5, "below", "weak core margin; QBP Q1'26 NIM 3.31"),
    ("EEFFR", 70.0, 85.0, "above", "expense discipline"),
    ("LNDEPR", 100.0, 110.0, "above", "loans/deposits funding reliance"),
    ("BRODEPR", 15.0, 30.0, "above",
     "brokered reliance; FDI Act s29 / 12 CFR 337.6 salience"),
    ("CRECONR", 250.0, 300.0, "above",
     "2006 interagency CRE guidance 300 at ALERT (PROXY denominator); WATCH "
     "= approach band (JPM 49)"),
    # ---- v1.1 pack: per-loan-class ratios, loosened to real-world normal so a
    # bank trips only on genuinely elevated category performance. All numeric (L8).
    ("P3CRCD_BOOK", 2.5, 4.0, "above", "card 30-89 pipeline"),
    ("P9CRCD_BOOK", 2.0, 3.5, "above", "card 90+ accruing"),
    ("NACRCD_BOOK", 1.0, 2.0, "above", "cards charge off, rarely NA"),
    ("NTCRCDQ_BOOK", 6.0, 8.0, "above",
     "card NCO runs structurally high; normal 3-4% (JPM 3.28)"),
    ("P3AUTO_BOOK", 4.0, 6.0, "above", "auto early DQ runs elevated"),
    ("P9AUTO_BOOK", 1.0, 2.0, "above", "auto 90+ accruing"),
    ("NAAUTO_BOOK", 1.5, 3.0, "above", "auto nonaccrual"),
    ("NTAUTOQ_BOOK", 2.5, 4.0, "above", "auto NCO; normal 0.5-2%"),
    ("P3CONOTH_BOOK", 3.0, 5.0, "above", "other consumer early DQ"),
    ("P9CONOTH_BOOK", 1.5, 3.0, "above", "other consumer 90+"),
    ("NACONOTH_BOOK", 2.5, 4.0, "above", "other consumer nonaccrual"),
    ("NTCONOTQ_BOOK", 2.0, 4.0, "above", "other consumer NCO"),
    ("P3RERES_BOOK", 2.0, 4.0, "above", "resi 1-4 early DQ"),
    ("P9RERES_BOOK", 1.5, 3.0, "above", "resi 90+"),
    ("NARERES_BOOK", 1.5, 3.0, "above", "resi nonaccrual"),
    ("NTRERESQ_BOOK", 0.75, 1.5, "above", "resi NCO runs near zero"),
    ("P3RELOC_BOOK", 2.0, 4.0, "above", "HELOC early DQ"),
    ("P9RELOC_BOOK", 1.5, 3.0, "above", "HELOC 90+"),
    ("NARELOC_BOOK", 1.5, 3.0, "above", "HELOC nonaccrual"),
    ("P3RECONS_BOOK", 2.0, 4.0, "above", "construction 30-89"),
    ("P9RECONS_BOOK", 1.5, 3.0, "above", "construction 90+"),
    ("NARECONS_BOOK", 4.0, 7.0, "above", "constr NA runs above CRE (JPM 2.55)"),
    ("NTRECONQ_BOOK", 1.5, 3.0, "above", "construction NCO"),
    ("P3RENRES_BOOK", 2.0, 4.0, "above", "CRE nonfarm early DQ"),
    ("P9RENRES_BOOK", 1.5, 3.0, "above", "CRE nonfarm 90+"),
    ("NARENRES_BOOK", 4.0, 7.0, "above", "CRE nonaccrual elevated in 2026 (JPM 2.10)"),
    ("NTRENREQ_BOOK", 1.5, 3.0, "above", "CRE nonfarm NCO"),
    ("P3REMULT_BOOK", 2.0, 4.0, "above", "multifamily early DQ"),
    ("P9REMULT_BOOK", 1.5, 3.0, "above", "multifamily 90+"),
    ("NAREMULT_BOOK", 3.0, 5.0, "above", "multifamily nonaccrual"),
    ("NTREMULQ_BOOK", 1.5, 3.0, "above", "multifamily NCO"),
    ("P3CI_BOOK", 1.5, 3.0, "above", "C&I early DQ"),
    ("P9CI_BOOK", 1.0, 2.0, "above", "C&I 90+"),
    ("NACI_BOOK", 1.5, 3.0, "above", "C&I nonaccrual"),
    ("NTCIQ_BOOK", 1.5, 3.0, "above", "C&I quarterly NCO; normal 0.2-1% (JPM 0.78)"),
    ("UNINSDEPR", 60.0, 75.0, "above",
     "uninsured share; megabanks normally 40-55 (JPM 46), SVB was 94; "
     "null DEPUNINS renders blank, never 0"),
    ("UNRLZCAPR", 25.0, 50.0, "above",
     "unrealized loss / capital cushion; SVB ran >100 (JPM 5.76)"),
    ("FHLBASSR", 10.0, 20.0, "above", "wholesale FHLB reliance screen"),
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
    assert len(rows) == 53, len(rows)     # 15 core + 38 pack (v1.1)
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
