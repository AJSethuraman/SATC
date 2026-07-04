"""Canonical config seed for the EDGAR Criticized/Classified Tracker
(BUILD_SPEC_EDGAR.md sec 2).

Build-time source of the `_config` tables. The runner never imports this
module -- it reads the already-expanded tables out of the workbook, so the
workbook stays the source of truth (BUILD SPEC 0.4), INCLUDING the [PEERS]
watchlist and the per-bank [MEMBER_MAP]/[CLASS_MAP] disclosure dialects
(contract sec 13: entity sets AND per-entity dialects are config, not code).

Seed provenance (COVERAGE_RESEARCH_EDGAR.md):
  * The 10 [PEERS] CIKs and their disclosure FAMILIES are research-verified
    against actual 10-Q filings (grades_full / criticized_only / ig_nig).
  * STANDARD us-gaap members (PassMember, SpecialMentionMember,
    SubstandardMember, DoubtfulMember,
    UnlikelyToBeCollectedFinancingReceivableMember, CriticizedMember,
    InternalInvestmentGradeMember, InternalNoninvestmentGradeMember) are
    verified by grepping the official us-gaap taxonomy linkbases.
  * EXTENSION member qnames (key:/mtb:/hban: rows) are ILLUSTRATIVE
    placeholders for the researched disclosure shapes -- the exact qnames
    are resolved empirically by the first live fetch: unknown members
    bootstrap into [MEMBER_MAP] as grade="unmapped" and are flagged for
    manual mapping (never guessed).
  * us-gaap:CriticizedMember PARENTS SpecialMention/Substandard/Doubtful/
    Loss in the taxonomy -- a filer tagging BOTH the subtotal and its leaves
    would double-count, so the subtotal is seeded grade="ignore" (excluded
    from numerators AND denominators) for every grades_full bank.

Pure ASCII (L3).
"""
from __future__ import annotations

PEER_HEADER = ["slot", "cik", "name", "ticker", "active"]
MEMBER_MAP_HEADER = ["cik", "family", "member_qname", "grade"]
CLASS_MAP_HEADER = ["cik", "class_member_qname", "class"]

# Provisioned BLANK bootstrap rows inside each map section: the runner
# appends newly observed members here (grade/class = "unmapped") WITHOUT
# inserting rows -- inserting would shift every threshold/peer cell the
# dashboard formulas reference.
MEMBER_MAP_SPARE_ROWS = 40
CLASS_MAP_SPARE_ROWS = 24

# --------------------------------------------------------------------------
# The 10 research-verified seed banks (BUILD_SPEC_EDGAR.md sec 2), with
# their disclosure families per COVERAGE_RESEARCH_EDGAR.md.
# --------------------------------------------------------------------------
SEED_BANKS = [
    # slot, cik, name, ticker, family
    (1, "35527", "Fifth Third Bancorp", "FITB", "grades_full"),
    (2, "1281761", "Regions Financial Corp", "RF", "grades_full"),
    (3, "109380", "Zions Bancorporation NA", "ZION", "grades_full"),
    (4, "28412", "Comerica Inc", "CMA", "grades_full"),
    (5, "49196", "Huntington Bancshares Inc", "HBAN", "grades_full"),
    (6, "92230", "Truist Financial Corp", "TFC", "grades_full"),
    (7, "91576", "KeyCorp", "KEY", "criticized_only"),
    (8, "36270", "M&T Bank Corp", "MTB", "criticized_only"),
    (9, "36104", "US Bancorp", "USB", "ig_nig"),
    (10, "875357", "BOK Financial Corp", "BOKF", "grades_full"),
]

SEED_FAMILY = {cik: fam for _s, cik, _n, _t, fam in SEED_BANKS}


def peer_rows(peer_slots: int):
    """[PEERS] rows: the 10 seeds + provisioned empty slots to capacity."""
    rows = []
    by_slot = {s: (cik, name, tkr) for s, cik, name, tkr, _f in SEED_BANKS}
    for slot in range(1, peer_slots + 1):
        if slot in by_slot:
            cik, name, tkr = by_slot[slot]
            rows.append([slot, int(cik), name, tkr, "TRUE"])
        else:
            rows.append([slot, "", "", "", ""])
    return rows


# --------------------------------------------------------------------------
# [MEMBER_MAP] seeds -- per research family. Standard us-gaap set for every
# grades_full bank; Huntington adds its OLEM extension label; criticized_only
# banks carry pass + the two criticized buckets; USB carries IG/NIG only.
# --------------------------------------------------------------------------
_STD_GRADES_FULL = [
    ("us-gaap:PassMember", "pass"),
    ("us-gaap:SpecialMentionMember", "special_mention"),
    ("us-gaap:SubstandardMember", "substandard"),
    ("us-gaap:DoubtfulMember", "doubtful"),
    ("us-gaap:UnlikelyToBeCollectedFinancingReceivableMember", "loss"),
    # subtotal member: parents the four adverse leaves -- NEVER summed
    ("us-gaap:CriticizedMember", "ignore"),
]

_EXT_MEMBERS = {
    # Huntington labels special mention "OLEM" (research) -- illustrative
    # extension qname; the standard member stays seeded alongside.
    "49196": [("hban:OlemMember", "special_mention")],
}

_CO_MEMBERS = {
    "91576": [("us-gaap:PassMember", "pass"),
              ("key:CriticizedAccruingMember", "criticized_accruing"),
              ("key:CriticizedNonaccrualMember", "criticized_nonaccruing")],
    "36270": [("us-gaap:PassMember", "pass"),
              ("mtb:CriticizedAccruingMember", "criticized_accruing"),
              ("mtb:CriticizedNonaccrualMember", "criticized_nonaccruing")],
}

_IG_MEMBERS = [
    ("us-gaap:InternalInvestmentGradeMember", "investment_grade"),
    ("us-gaap:InternalNoninvestmentGradeMember", "noninvestment_grade"),
]


def member_map_rows():
    rows = []
    for _slot, cik, _name, _tkr, fam in SEED_BANKS:
        if fam == "grades_full":
            pairs = list(_STD_GRADES_FULL) + _EXT_MEMBERS.get(cik, [])
        elif fam == "criticized_only":
            pairs = _CO_MEMBERS[cik]
        else:                               # ig_nig
            pairs = _IG_MEMBERS
        for qname, grade in pairs:
            rows.append([int(cik), fam, qname, grade])
    return rows


# --------------------------------------------------------------------------
# [CLASS_MAP] seeds -- coarse normalization of class-axis members to
# {ci, cre, construction, other_commercial}; consumer/residential books map
# to "excluded" (the denominators are COMMERCIAL amortized cost only).
# cik="*" rows are STANDARD us-gaap members that apply to every bank;
# per-bank extension class members bootstrap in below them as "unmapped".
# --------------------------------------------------------------------------
CLASS_MAP_SEEDS = [
    ("*", "us-gaap:CommercialPortfolioSegmentMember", "ci"),
    ("*", "us-gaap:CommercialRealEstatePortfolioSegmentMember", "cre"),
    ("*", "us-gaap:ConstructionLoansMember", "construction"),
    ("*", "us-gaap:CommercialLoanMember", "other_commercial"),
    ("*", "us-gaap:ResidentialPortfolioSegmentMember", "excluded"),
    ("*", "us-gaap:ConsumerPortfolioSegmentMember", "excluded"),
    ("*", "us-gaap:ResidentialMortgageMember", "excluded"),
    ("*", "us-gaap:HomeEquityLoanMember", "excluded"),
    ("*", "us-gaap:AutomobileLoanMember", "excluded"),
    ("*", "us-gaap:CreditCardReceivablesMember", "excluded"),
]


def class_map_rows():
    return [[c, q, k] for c, q, k in CLASS_MAP_SEEDS]


# --------------------------------------------------------------------------
# [THRESHOLDS] -- numeric cells (L8), HEURISTIC and labeled so
# (BUILD_SPEC_EDGAR.md sec 3). Only the banded metrics carry rows; the 8-K
# lane's automatic WATCH (any 2.04/4.02/1.03) is rule-based, not banded.
# --------------------------------------------------------------------------
THRESHOLDS = [
    # id, watch, alert, direction, authority
    ("criticized_ratio", 4.0, 6.0, "above",
     "HEURISTIC bands (labeled): mid-single-digit criticized share is "
     "elevated for a regional commercial book; calibrate to your house "
     "view. Definitions: 2004 Uniform Agreement / OCC Rating Credit Risk."),
    ("crit_qoq_delta", 0.5, 1.0, "above",
     "HEURISTIC: +0.5pp in one quarter = migration WATCH, +1.0pp = ALERT. "
     "Application timing is bank judgment (exam-cycle artifacts -- E9)."),
    ("sm_ratio", 2.0, 3.0, "above",
     "HEURISTIC: special mention is the leading edge (SR 93-30 definition); "
     "grades_full banks only -- other families render N/A."),
]
