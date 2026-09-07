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
    # --- v1.1 consumer track: verified R ratio twins (pct) ---
    "P3CRCDR", "P9CRCDR", "NACRCDR",                            # pct
    "P3AUTOR", "P9AUTOR", "NAAUTOR",                            # pct
    "P3RERESR", "P9RERESR", "NARERESR",                         # pct
    "P3RELOCR", "P9RELOCR", "NARELOCR",                         # pct (HELOC)
    # other-consumer PD/NA dollar triple (twin name would exceed 8 chars)
    "P3CONOTH", "P9CONOTH", "NACONOTH",                         # $000
    # consumer balances + quarterly NCO dollars (F1: never the YTD NT{c})
    "LNCRCD", "LNAUTO", "LNCONOTH", "LNRERES",                  # $000
    "NTCRCDQ", "NTAUTOQ", "NTCONOTQ", "NTRERESQ",               # $000
    # --- v1.1 commercial floor ---
    "P3CIR", "P9CIR", "NACIR",                                  # pct twins
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
PCT_FIELDS = {
    "NCLNLSR", "NTLNLSQR", "LNATRESR", "LNRESNCR",
    "RBC1AAJ", "RBCRWAJ", "EQV", "ROAQ", "NIMY", "EEFFR",
    "P3CRCDR", "P9CRCDR", "NACRCDR", "P3AUTOR", "P9AUTOR", "NAAUTOR",
    "P3RERESR", "P9RERESR", "NARERESR", "P3RELOCR", "P9RELOCR", "NARELOCR",
    "P3CIR", "P9CIR", "NACIR",
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
    # consumer PD/NA rates computed from the verified dollar triple + balance
    # (the R-twin name would exceed the 8-char field-name limit -- unverified)
    "P3CONOTHR": ("P3CONOTH", "LNCONOTH", 100),
    "P9CONOTHR": ("P9CONOTH", "LNCONOTH", 100),
    "NACONOTHR": ("NACONOTH", "LNCONOTH", 100),
    # consumer quarterly NCO rates (F1: the Q dollar flow, never YTD NT{c})
    "NTCRCDQR": ("NTCRCDQ", "LNCRCD", 400),
    "NTAUTOQR": ("NTAUTOQ", "LNAUTO", 400),
    "NTCONOTQR": ("NTCONOTQ", "LNCONOTH", 400),
    "NTRERESQR": ("NTRERESQ", "LNRERES", 400),
    # commercial-floor PD/NA rates (twin names exceed 8 chars -- computed)
    "P3RECONSR": ("P3RECONS", "LNRECONS", 100),
    "P9RECONSR": ("P9RECONS", "LNRECONS", 100),
    "NARECONSR": ("NARECONS", "LNRECONS", 100),
    "P3RENRESR": ("P3RENRES", "LNRENRES", 100),
    "P9RENRESR": ("P9RENRES", "LNRENRES", 100),
    "NARENRESR": ("NARENRES", "LNRENRES", 100),
    "P3REMULTR": ("P3REMULT", "LNREMULT", 100),
    "P9REMULTR": ("P9REMULT", "LNREMULT", 100),
    "NAREMULTR": ("NAREMULT", "LNREMULT", 100),
    # commercial quarterly NCO rates (8-char truncation: NTRECONQ etc.)
    "NTRECONQR": ("NTRECONQ", "LNRECONS", 400),
    "NTRENREQR": ("NTRENREQ", "LNRENRES", 400),
    "NTREMULQR": ("NTREMULQ", "LNREMULT", 400),
    "NTCIQR": ("NTCIQ", "LNCI", 400),
    # SVB pack simple ratios
    "UNINSDEPR": ("DEPUNINS", "DEP", 100),   # null -> BLANK + digest note
    "FHLBASSR": ("OTHBFHLB", "ASSET", 100),
}

# verified R-twin ratio fields consumed DIRECTLY (metric id IS the field)
PACK_DIRECT = [
    "P3CRCDR", "P9CRCDR", "NACRCDR",
    "P3AUTOR", "P9AUTOR", "NAAUTOR",
    "P3RERESR", "P9RERESR", "NARERESR",
    "P3RELOCR", "P9RELOCR", "NARELOCR",
    "P3CIR", "P9CIR", "NACIR",
]


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
        (("P3CRCDR", "P9CRCDR", "NACRCDR", "NTCRCDQR"), "credit card"),
        (("P3AUTOR", "P9AUTOR", "NAAUTOR", "NTAUTOQR"), "auto"),
        (("P3CONOTHR", "P9CONOTHR", "NACONOTHR", "NTCONOTQR"),
         "other consumer"),
        (("P3RERESR", "P9RERESR", "NARERESR", "NTRERESQR"), "resi 1-4 fam"),
        (("P3RELOCR", "P9RELOCR", "NARELOCR"), "HELOC"),
        (("P3RECONSR", "P9RECONSR", "NARECONSR", "NTRECONQR"),
         "construction"),
        (("P3RENRESR", "P9RENRESR", "NARENRESR", "NTRENREQR"),
         "CRE nonfarm"),
        (("P3REMULTR", "P9REMULTR", "NAREMULTR", "NTREMULQR"),
         "multifamily"),
        (("P3CIR", "P9CIR", "NACIR", "NTCIQR"), "C&I")):
    for _m in _mid:
        LOANBOOK_CLASS[_m] = _cls

CONSUMER_CLASSES = ("credit card", "auto", "other consumer", "resi 1-4 fam",
                    "HELOC")
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

REGISTRY = build_registry(direct=DIRECT, ratios=PACK_RATIOS, derived=DERIVED)
