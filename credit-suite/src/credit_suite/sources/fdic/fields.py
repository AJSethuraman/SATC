"""FDIC's field table, ratio table and metric registry -- data, not engine code.

Every name in here is a Call Report field or a metric defined over them, and
every one is verified against the FDIC's own documentation (see
`fdic-peer-monitor/COVERAGE_RESEARCH_FDIC.md` and `RESEARCH_COMPETITOR_PACK.md`).
They are extracted from the monitor this replaces, unchanged, because parity is
measured cell for cell and a "tidied" field name is a moved number.

Mixed units per record (trap F4): dollar fields are $ THOUSANDS, ratio fields
are PERCENT. `FIELD_UNITS` is what stops the two being averaged together.

`PACK_RATIOS` is the declarative table that drives BOTH the Python metric
functions and the Excel formulas, so the two definitions cannot drift (trap F5).
"""

from __future__ import annotations

from typing import Dict, Optional

from credit_suite.engine.metrics import build_registry, ratio, total

RAW_FIELDS = [
    "ASSET", "DEP", "LNLSGR", "LNLSNET", "BRO", "EQ",           # $000
    "NCLNLS", "LNATRES", "P3LNLS",                              # $000
    "LNRECONS", "LNRENRES", "LNREMULT",                         # $000
    "NCLNLSR", "NTLNLSQR", "LNATRESR", "LNRESNCR",              # pct
    "RBC1AAJ", "RBCRWAJ", "EQV", "ROAQ", "NIMY", "EEFFR",       # pct
    # --- v1.1 consumer track: the PD/NA dollar triples (Schedule RC-N) ---
    # The FDIC also publishes a ratio twin for each of these (P3CRCDR and so
    # on) -- over AVERAGE TOTAL ASSETS, not over the loan class. Landing the
    # dollars and computing over the book is the only way the classes compare
    # with each other and with the thresholds (#268, 5 Sep 2026).
    "P3CRCD", "P9CRCD", "NACRCD",                               # $000
    "P3AUTO", "P9AUTO", "NAAUTO",                               # $000
    "P3RERES", "P9RERES", "NARERES",                            # $000
    "P3RELOC", "P9RELOC", "NARELOC",                            # $000 (HELOC)
    "P3CONOTH", "P9CONOTH", "NACONOTH",                         # $000
    # consumer balances + quarterly NCO dollars (F1: never the YTD NT{c})
    "LNCRCD", "LNAUTO", "LNCONOTH", "LNRERES", "LNRELOC",       # $000
    "NTCRCDQ", "NTAUTOQ", "NTCONOTQ", "NTRERESQ",               # $000
    # --- v1.1 commercial floor ---
    "P3CI", "P9CI", "NACI",                                     # $000
    "P3RECONS", "P9RECONS", "NARECONS",                         # $000
    "P3RENRES", "P9RENRES", "NARENRES",                         # $000
    "P3REMULT", "P9REMULT", "NAREMULT",                         # $000
    "LNCI",                                                     # $000
    "NTRECONQ", "NTRENREQ", "NTREMULQ", "NTCIQ",                # $000
    # --- v1.1 SVB / funding-stress pack ---
    "DEPUNINS",                                                 # $000 (nullable)
    "SCHA", "SCHF", "SCAA", "SCAF",                             # $000 HTM/AFS
    "OTHBFHLB",                                                 # $000 FHLB adv
]
#: The only ratios still landed as ratios are whole-bank ones, and those are
#: over LOANS (or average loans), which is the denominator a reader expects.
#: The class ratios the FDIC publishes are over TOTAL ASSETS and are no longer
#: landed at all -- see #268.
PCT_FIELDS = {
    "NCLNLSR", "NTLNLSQR", "LNATRESR", "LNRESNCR",
    "RBC1AAJ", "RBCRWAJ", "EQV", "ROAQ", "NIMY", "EEFFR",
}
DOLLAR_FIELDS = {f for f in RAW_FIELDS if f not in PCT_FIELDS}
FIELD_UNITS = {f: ("USD_thousands" if f in DOLLAR_FIELDS else "pct")
               for f in RAW_FIELDS}

# The FDIC bulk endpoint caps fields= at 250; the ONE bulk request must stay
# far under it (spec sec 3). Guarded here AND at request build time.
MAX_REQUEST_FIELDS = 250
assert len(RAW_FIELDS) + 2 < MAX_REQUEST_FIELDS, "fields= list over the cap"


def d_pd3089r(f):
    """30-89 day past due %: P3LNLS/LNLSGR*100 (no API ratio field exists)."""
    return ratio(f.get("P3LNLS"), f.get("LNLSGR"))


def d_texas(f):
    """Texas ratio VARIANT: NCLNLS/(EQ+LNATRES)*100. Canonical adds OREO and
    nets intangibles -- ORE/INTAN field ids are UNVERIFIED (Open Q), so v1
    computes the documented variant from verified fields only."""
    return ratio(f.get("NCLNLS"), total(f.get("EQ"), f.get("LNATRES")))


def d_lndepr(f):
    """Loans/deposits %: LNLSNET/DEP*100."""
    return ratio(f.get("LNLSNET"), f.get("DEP"))


def d_brodepr(f):
    """Brokered deposit share %: BRO/DEP*100 (BRO null -> blank, never 0)."""
    return ratio(f.get("BRO"), f.get("DEP"))


def d_creconr(f):
    """CRE concentration PROXY: (LNRECONS+LNRENRES+LNREMULT)/(EQ+LNATRES)*100.
    Guidance uses total risk-based capital; CBLR electors lack it, so the
    documented proxy denominator stands until the tier-1 dollar field is
    verified live."""
    return ratio(total(f.get("LNRECONS"), f.get("LNRENRES"), f.get("LNREMULT")),
                  total(f.get("EQ"), f.get("LNATRES")))


# --------------------------------------------------------------------------
# v1.1 COMPETITOR PACK ratios -- ONE declarative table drives BOTH the Python
# functions (below) and the Excel formulas (build_workbook reads this table),
# so the two definitions cannot drift (trap F5).
#   metric id -> (numerator field, denominator field, multiplier)
# Multiplier 100 = plain percent; 400 = QUARTERLY flow ANNUALIZED (x4), the
# same convention as the FDIC's own NTLNLSQR (PROVENANCE_MAP_FDIC.md sec F).
# All None-tolerant: null numerator OR denominator -> blank, never 0 (F3) --
# DEPUNINS especially is genuinely null below the $1B reporting threshold.
# --------------------------------------------------------------------------
PACK_RATIOS = {
    # every consumer PD/NA rate, over its own book (#268). The FDIC publishes
    # a twin for most of these over TOTAL ASSETS; ours carry _BOOK so the two
    # can never be read as the same number.
    "P3CRCD_BOOK": ("P3CRCD", "LNCRCD", 100),
    "P9CRCD_BOOK": ("P9CRCD", "LNCRCD", 100),
    "NACRCD_BOOK": ("NACRCD", "LNCRCD", 100),
    "P3AUTO_BOOK": ("P3AUTO", "LNAUTO", 100),
    "P9AUTO_BOOK": ("P9AUTO", "LNAUTO", 100),
    "NAAUTO_BOOK": ("NAAUTO", "LNAUTO", 100),
    "P3RERES_BOOK": ("P3RERES", "LNRERES", 100),
    "P9RERES_BOOK": ("P9RERES", "LNRERES", 100),
    "NARERES_BOOK": ("NARERES", "LNRERES", 100),
    "P3RELOC_BOOK": ("P3RELOC", "LNRELOC", 100),
    "P9RELOC_BOOK": ("P9RELOC", "LNRELOC", 100),
    "NARELOC_BOOK": ("NARELOC", "LNRELOC", 100),
    "P3CI_BOOK": ("P3CI", "LNCI", 100),
    "P9CI_BOOK": ("P9CI", "LNCI", 100),
    "NACI_BOOK": ("NACI", "LNCI", 100),
    "P3CONOTH_BOOK": ("P3CONOTH", "LNCONOTH", 100),
    "P9CONOTH_BOOK": ("P9CONOTH", "LNCONOTH", 100),
    "NACONOTH_BOOK": ("NACONOTH", "LNCONOTH", 100),
    # consumer quarterly NCO rates (F1: the Q dollar flow, never YTD NT{c})
    "NTCRCDQ_BOOK": ("NTCRCDQ", "LNCRCD", 400),
    "NTAUTOQ_BOOK": ("NTAUTOQ", "LNAUTO", 400),
    "NTCONOTQ_BOOK": ("NTCONOTQ", "LNCONOTH", 400),
    "NTRERESQ_BOOK": ("NTRERESQ", "LNRERES", 400),
    # commercial-floor PD/NA rates (twin names exceed 8 chars -- computed)
    "P3RECONS_BOOK": ("P3RECONS", "LNRECONS", 100),
    "P9RECONS_BOOK": ("P9RECONS", "LNRECONS", 100),
    "NARECONS_BOOK": ("NARECONS", "LNRECONS", 100),
    "P3RENRES_BOOK": ("P3RENRES", "LNRENRES", 100),
    "P9RENRES_BOOK": ("P9RENRES", "LNRENRES", 100),
    "NARENRES_BOOK": ("NARENRES", "LNRENRES", 100),
    "P3REMULT_BOOK": ("P3REMULT", "LNREMULT", 100),
    "P9REMULT_BOOK": ("P9REMULT", "LNREMULT", 100),
    "NAREMULT_BOOK": ("NAREMULT", "LNREMULT", 100),
    # commercial quarterly NCO rates (8-char truncation: NTRECONQ etc.)
    "NTRECONQ_BOOK": ("NTRECONQ", "LNRECONS", 400),
    "NTRENREQ_BOOK": ("NTRENREQ", "LNRENRES", 400),
    "NTREMULQ_BOOK": ("NTREMULQ", "LNREMULT", 400),
    "NTCIQ_BOOK": ("NTCIQ", "LNCI", 400),
    # SVB pack simple ratios
    "UNINSDEPR": ("DEPUNINS", "DEP", 100),   # null -> BLANK + digest note
    "FHLBASSR": ("OTHBFHLB", "ASSET", 100),
}

# verified R-twin ratio fields consumed DIRECTLY (metric id IS the field)
#: Nothing. Every class rate is computed over its book (#268); the FDIC's own
#: twins are over total assets and are not landed. Kept as an empty list so
#: the three-kinds-of-metric assembly below still reads as three kinds.
PACK_DIRECT: list = []


def d_unrlzcapr(f):
    """Unrealized securities loss / capital cushion (SVB metric):
    ((SCHA-SCHF)+(SCAA-SCAF))/(EQ+LNATRES)*100. BOTH legs COMPUTED from the
    verified fair/amortized pairs -- no named unrealized field exists, and
    EQCCOMPI is the YTD OCI FLOW, not the AOCI stock (never used). Positive =
    unrealized LOSS eroding the cushion. Any null leg blanks the metric."""
    vals = [f.get(k) for k in ("SCHA", "SCHF", "SCAA", "SCAF")]
    if any(v is None for v in vals):
        return None
    scha, schf, scaa, scaf = vals
    return ratio((scha - schf) + (scaa - scaf),
                  total(f.get("EQ"), f.get("LNATRES")))


# Loan class per LoanBook metric (drives the email per-class alert section
# and the tieout grouping). Consumer classes are the DQ/NCO track; commercial
# classes are the public Call-Report FLOOR (criticized/classified via EDGAR).
LOANBOOK_CLASS = {}
for _mid, _cls in (
        (("P3CRCD_BOOK", "P9CRCD_BOOK", "NACRCD_BOOK", "NTCRCDQ_BOOK"),
         "credit card"),
        (("P3AUTO_BOOK", "P9AUTO_BOOK", "NAAUTO_BOOK", "NTAUTOQ_BOOK"),
         "auto"),
        (("P3CONOTH_BOOK", "P9CONOTH_BOOK", "NACONOTH_BOOK", "NTCONOTQ_BOOK"),
         "other consumer"),
        (("P3RERES_BOOK", "P9RERES_BOOK", "NARERES_BOOK", "NTRERESQ_BOOK"),
         "resi 1-4 fam"),
        (("P3RELOC_BOOK", "P9RELOC_BOOK", "NARELOC_BOOK"), "HELOC"),
        (("P3RECONS_BOOK", "P9RECONS_BOOK", "NARECONS_BOOK", "NTRECONQ_BOOK"),
         "construction"),
        (("P3RENRES_BOOK", "P9RENRES_BOOK", "NARENRES_BOOK", "NTRENREQ_BOOK"),
         "CRE nonfarm"),
        (("P3REMULT_BOOK", "P9REMULT_BOOK", "NAREMULT_BOOK", "NTREMULQ_BOOK"),
         "multifamily"),
        (("P3CI_BOOK", "P9CI_BOOK", "NACI_BOOK", "NTCIQ_BOOK"), "C&I")):
    for _m in _mid:
        LOANBOOK_CLASS[_m] = _cls

CONSUMER_CLASSES = ("credit card", "auto", "other consumer", "resi 1-4 fam",
                    "HELOC")

#: The landed balance each loan class stands on. Every class now has one --
#: LNRELOC was landed with the rest for #268, so HELOC is no longer the
#: exception it was.
CLASS_BALANCE = {
    "credit card": "LNCRCD", "auto": "LNAUTO", "other consumer": "LNCONOTH",
    "resi 1-4 fam": "LNRERES", "HELOC": "LNRELOC", "construction": "LNRECONS",
    "CRE nonfarm": "LNRENRES", "multifamily": "LNREMULT", "C&I": "LNCI",
}
COMMERCIAL_CLASSES = ("construction", "CRE nonfarm", "multifamily", "C&I")


# The three kinds of metric, assembled by the engine. `direct` means the metric
# id IS a landed field; `ratios` is the declarative table above, which also
# drives the Excel formulas; `derived` is the handful needing real code.
DERIVED = {
    "PD3089R": (("P3LNLS", "LNLSGR"), d_pd3089r),
    "TEXAS": (("NCLNLS", "EQ", "LNATRES"), d_texas),
    "LNDEPR": (("LNLSNET", "DEP"), d_lndepr),
    "BRODEPR": (("BRO", "DEP"), d_brodepr),
    "CRECONR": (("LNRECONS", "LNRENRES", "LNREMULT", "EQ", "LNATRES"), d_creconr),
    "UNRLZCAPR": (("SCHA", "SCHF", "SCAA", "SCAF", "EQ", "LNATRES"), d_unrlzcapr),
}

#: Metrics whose id is itself a landed field, passed through unchanged.
DIRECT = [
    "NCLNLSR", "NTLNLSQR", "LNATRESR", "LNRESNCR",
    "RBC1AAJ", "RBCRWAJ", "EQV", "ROAQ", "NIMY", "EEFFR",
    *PACK_DIRECT,
]

#: Metrics built from a QUARTERLY FLOW, which the FDIC derives by subtracting
#: the previous quarter's year-to-date total. Across a merger that subtraction
#: spans two banks, so the "quarter" is not a quarter of anything and the
#: value is uncomparable -- see sources/fdic/mergers.py for the incident.
#: NTLNLSQR is the FDIC's own published quarterly rate and is derived the same
#: way, so it belongs here even though this template lands it directly.
QUARTERLY_FLOW_METRICS = frozenset(
    [m for m, (_num, _den, mult) in PACK_RATIOS.items() if mult == 400]
    + ["NTLNLSQR"])

REGISTRY = build_registry(direct=DIRECT, ratios=PACK_RATIOS, derived=DERIVED)
