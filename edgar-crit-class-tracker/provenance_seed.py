"""Provenance seed -- the tie-out map rendered as workbook data
(TEMPLATE_CONTRACT.md sec 12).

Build-time source of the `_provenance` tab: one row per canonical METRIC and
per raw INPUT, mapping each workbook value to where it appears in the bank's
actual FILED 10-Q/10-K -- the "Credit Quality Indicators" note required by
ASC 326-20-50-5 (amortized cost by credit quality indicator, BY CLASS,
quarterly), tagged in XBRL on the FinancingReceivableBeforeAllowanceFor-
CreditLoss line items dimensioned by InternalCreditAssessmentAxis x the
class axis. The ACCESSION of the filing each fact came from is recorded PER
FACT in the Raw_EDGAR fact blocks and PER QUARTER in the canonical metric
blocks; `--tieout CIK [quarter]` prints value + tag + member breakdown +
accession + the EDGAR viewer URL.

This tab also QUOTES the uniform interagency criticized/classified
definitions (with citations) so a reviewer can check the composition rules
against the official record without leaving the workbook.

The runner does NOT import this module -- `--tieout` reads the rendered
_provenance tab out of the workbook (the workbook is the source of truth).
Pure ASCII (L3).
"""
from __future__ import annotations

FILING_DIR_PATTERN = ("https://www.sec.gov/Archives/edgar/data/"
                      "{CIK}/{ACCESSION-NODASH}/")
BROWSE_PATTERN = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
                  "&CIK={CIK}&type=10-Q&dateb=&owner=include&count=40")
SUBMISSIONS_PATTERN = "https://data.sec.gov/submissions/CIK{CIK-10-DIGIT}.json"

PREAMBLE = [
    "PROVENANCE / TIE-OUT MAP -- where every workbook value appears in the "
    "bank's actual filed 10-Q/10-K.",
    "",
    "SOURCE DOCUMENT: the quarterly 'Credit Quality Indicators' note "
    "(ASC 326-20-50-5: amortized cost by credit quality indicator, by class "
    "of financing receivable, by vintage for PBEs -- this tracker uses the "
    "GRADE TOTALS and IGNORES vintage line items, which would double-count).",
    "XBRL LOCATION: facts on FinancingReceivableBeforeAllowanceForCreditLoss "
    "(or the ...ExcludingAccruedInterest... twin -- per-bank preference "
    "recorded in the TAG column of every landed quarter), dimensioned by "
    "us-gaap:InternalCreditAssessmentAxis x the class axis "
    "(FinancingReceivableRecordedInvestmentByClassOfFinancingReceivableAxis "
    "or FinancingReceivablePortfolioSegmentAxis). Parsed from the "
    "EDGAR-generated extracted XBRL instance (*_htm.xml) in each filing "
    "directory -- the convenience JSON APIs are structurally non-dimensional "
    "and CANNOT carry these tables (research-verified).",
    "ACCESSION: recorded per fact (Raw_EDGAR fact blocks) and per quarter "
    "(canonical metric blocks + block header).",
    "",
    "OPEN THE FILED DOCUMENT (keyed by CIK + accession, which this template "
    "already records):",
    "  Filing directory:  " + FILING_DIR_PATTERN,
    "  Company filings:   " + BROWSE_PATTERN,
    "  Submissions JSON:  " + SUBMISSIONS_PATTERN,
    "  (CIK is 10-digit zero-padded on data.sec.gov, UNPADDED in /Archives "
    "-- trap E8.)",
    "",
    "TIE-OUT (minutes, from PowerShell): python runner.py -w <book>.xlsm "
    "--tieout <CIK> [quarter] prints each metric's value + tag + the "
    "member-level breakdown + accession + the filing-directory URL; open "
    "the 10-Q's Credit Quality Indicators note and match the amounts. "
    "--demo prints LOUDLY-LABELED deterministic fiction with the same "
    "provenance columns.",
    "",
    "[UNIFORM INTERAGENCY DEFINITIONS -- QUOTED]",
    "Lineage: interagency classification agreements 1938/1949/1979; the "
    "2004 'Uniform Agreement on the Classification of Assets and Appraisal "
    "of Securities Held by Banks and Thrifts' (OCC/FRB/FDIC/OTS, June 15, "
    "2004); Special Mention adopted interagency 1993 (FRB SR 93-30). "
    "Definitions as published in the OCC Comptroller's Handbook, 'Rating "
    "Credit Risk':",
    "",
    "SPECIAL MENTION: \"A special mention asset has potential weaknesses "
    "that deserve management's close attention. If left uncorrected, these "
    "potential weaknesses may result in deterioration of the repayment "
    "prospects for the asset or in the institution's credit position at "
    "some future date. Special mention assets are not adversely classified "
    "and do not expose an institution to sufficient risk to warrant adverse "
    "classification.\" (OCC Rating Credit Risk handbook; SR 93-30)",
    "",
    "SUBSTANDARD: \"A substandard asset is inadequately protected by the "
    "current sound worth and paying capacity of the obligor or of the "
    "collateral pledged, if any. Assets so classified must have a "
    "well-defined weakness or weaknesses that jeopardize the liquidation "
    "of the debt. They are characterized by the distinct possibility that "
    "the bank will sustain some loss if the deficiencies are not "
    "corrected.\" (2004 Uniform Agreement)",
    "",
    "DOUBTFUL: \"An asset classified doubtful has all the weaknesses "
    "inherent in one classified substandard with the added characteristic "
    "that the weaknesses make collection or liquidation in full, on the "
    "basis of currently existing facts, conditions, and values, highly "
    "questionable and improbable.\" (2004 Uniform Agreement)",
    "",
    "LOSS: \"Assets classified loss are considered uncollectible and of "
    "such little value that their continuance as bankable assets is not "
    "warranted. This classification does not mean that the asset has "
    "absolutely no recovery or salvage value, but rather that it is not "
    "practical or desirable to defer writing off this basically worthless "
    "asset even though partial recovery may be effected in the future.\" "
    "(2004 Uniform Agreement)",
    "",
    "COMPOSITIONS (Shared National Credit program usage): CLASSIFIED = "
    "Substandard + Doubtful + Loss.  CRITICIZED = Special Mention + "
    "Classified.  There is NO standard us-gaap ClassifiedMember; "
    "us-gaap:CriticizedMember exists and PARENTS the SM/Substandard/"
    "Doubtful/Loss members (taxonomy-verified) -- filer-tagged subtotals "
    "are mapped grade='ignore' so they never double-count.",
    "",
    "APPLICATION-TIMING CAVEAT (trap E9): the DEFINITIONS are uniform; the "
    "TIMING of downgrades is bank judgment and exam-cycle driven -- "
    "quarter-over-quarter moves partly reflect when each bank's review "
    "cycle runs, not only when credit deteriorated.",
    "",
    "FLAGS: [V] = taxonomy/mechanics verified in COVERAGE_RESEARCH_EDGAR.md "
    "| [~] = derived/composed from [V] inputs | SEEDED = illustrative seed, "
    "resolved empirically by the first live fetch (member bootstrap).",
]

HEADER = ["metric", "source document / note", "tag / axis", "accession",
          "flag", "notes"]

_NOTE = ("10-Q/10-K note: Credit Quality Indicators (ASC 326-20-50-5)")
_TAG = ("FinancingReceivableBeforeAllowanceForCreditLoss or "
        "...ExcludingAccruedInterest... twin (per-bank preference, "
        "recorded in the TAG column) x InternalCreditAssessmentAxis "
        "x class axis")
_ACC = "accession recorded per fact (Raw_EDGAR fact block + metric block)"

INPUT_ROWS = [
    ("FinancingReceivableBeforeAllowanceForCreditLoss", _NOTE,
     "line item; USD amortized cost", _ACC, "[V]",
     "the pre-ASU-2022-02 disclosure style"),
    ("FinancingReceivableExcludingAccruedInterestBeforeAllowanceFor"
     "CreditLoss", _NOTE, "line item; USD amortized cost excl. accrued "
     "interest", _ACC, "[V]",
     "the accrued-interest twin (trap E2) -- per-bank preference"),
    ("InternalCreditAssessmentAxis", _NOTE,
     "axis; members = grade (Pass/SM/Substandard/Doubtful/Loss or "
     "bank dialect)", _ACC, "[V]",
     "member qnames kept namespace-qualified; extensions bootstrap into "
     "[MEMBER_MAP] as unmapped (trap E4)"),
    ("class axis", _NOTE,
     "FinancingReceivableRecordedInvestmentByClassOfFinancingReceivableAxis "
     "(legacy name) or FinancingReceivablePortfolioSegmentAxis", _ACC, "[V]",
     "coarse-mapped to ci/cre/construction/other_commercial via "
     "[CLASS_MAP] (trap E5); consumer classes excluded"),
    ("vintage line items", _NOTE, "IGNORED by exact-tag matching",
     "n/a", "[V]",
     "vintage is LINE ITEMS not an axis; grade totals are single facts -- "
     "summing vintages double-counts (trap E3)"),
    ("8-K items array", "SEC form 8-K item numbers",
     "data.sec.gov/submissions CIK{10d}.json filings.recent.items[]",
     "accession recorded per event (Raw_EDGAR event block)", "[V]",
     "harvested from the SAME submissions response -- zero extra requests"),
]

METRIC_ROWS = [
    ("criticized_ratio", _NOTE, _TAG, _ACC, "[~]",
     "(SM + Substandard + Doubtful + Loss | native criticized rows) / "
     "total commercial amortized cost x100; Tier 1 -- N/A for ig_nig/"
     "unmapped families"),
    ("classified_ratio", _NOTE, _TAG, _ACC, "[~]",
     "(Substandard + Doubtful + Loss) / total commercial x100; Tier 2 -- "
     "grades_full families only (no standard ClassifiedMember exists)"),
    ("sm_ratio", _NOTE, _TAG, _ACC, "[~]",
     "Special Mention / total commercial x100; Tier 2 -- grades_full only "
     "(SR 93-30 definition quoted above)"),
    ("crit_qoq_delta", _NOTE, _TAG, _ACC, "[~]",
     "criticized_ratio[q] - criticized_ratio[q-1], percentage points; "
     "application-timing caveat E9 applies"),
    ("crit_yoy_delta", _NOTE, _TAG, _ACC, "[~]",
     "criticized_ratio[q] - criticized_ratio[q-4], percentage points"),
    ("crit_growth", _NOTE, _TAG, _ACC, "[~]",
     "criticized USD QoQ growth %"),
    ("mix_ci", _NOTE, _TAG, _ACC, "[~]",
     "criticized USD share mapped [CLASS_MAP]=ci"),
    ("mix_cre", _NOTE, _TAG, _ACC, "[~]",
     "criticized USD share mapped [CLASS_MAP]=cre"),
    ("mix_construction", _NOTE, _TAG, _ACC, "[~]",
     "criticized USD share mapped [CLASS_MAP]=construction"),
    ("mix_other", _NOTE, _TAG, _ACC, "[~]",
     "criticized USD share mapped [CLASS_MAP]=other_commercial"),
    ("events_8k", "Form 8-K items 1.03 / 2.04 / 2.06 / 4.02 (+2.02 "
     "informational)",
     "submissions JSON items[] (columnar arrays)",
     "accession + filing-directory URL per event row", "[V]",
     "any 2.04/4.02/1.03 = automatic WATCH flag on the bank"),
]

ALL_ROWS = INPUT_ROWS + METRIC_ROWS


if __name__ == "__main__":
    import runner as R
    ids = {r[0] for r in ALL_ROWS}
    missing = [m for m in R.METRICS if m not in ids]
    assert not missing, f"metrics without provenance: {missing}"
    for r in ALL_ROWS:
        assert len(r) == 6, r
        assert all(ord(c) < 128 for c in "".join(map(str, r))), r[0]
    print(f"{len(INPUT_ROWS)} input rows + {len(METRIC_ROWS)} metric rows "
          f"-- every metric covered, ASCII clean")
