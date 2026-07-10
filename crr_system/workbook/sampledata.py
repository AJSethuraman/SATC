"""Deterministic sample credits for demonstration/validation.

Generates 4 credits per segment with per-question answers following the
shared Yes/No/N/A/Obs convention (No = exception with rationale note,
Obs = pass with required note, N/A excluded from rates). Review dates span
four quarters so trend views have shape. Seeded so builds are reproducible.
"""

from __future__ import annotations

import datetime as dt
import random

from .content import SEGMENTS, question_rows

_RNG = random.Random(20260610)

_BORROWERS = {
    "CI": ["Meridian Fabrication Holdings, LLC", "Cascade Food Distributors, Inc.",
           "Brightline Logistics Group", "Harbor Tool & Die Co."],
    "CRE": ["Lakeview Office Partners LP", "Stonebridge Multifamily I LLC",
            "Pinecrest Retail Center LLC", "Gateway Industrial Park LLC"],
    "LL": ["Apex Packaging Buyout Co.", "Summit HealthTech Acquisition",
           "Ironwood Components Holdings", "Bluepeak Software Group"],
    "ABL": ["Royal Textile Mills, Inc.", "Northgate Auto Parts Supply",
            "Crestline Paper Converters", "Delta Steel Service Center"],
    "ARG": ["Fairmont Hospitality LLC (Workout)", "Quarry Ridge Homes, Inc. (Workout)",
            "Westbrook Printing Co. (Workout)", "Sablewood Furniture Mfg. (Workout)"],
    "COMP": ["Compliance Sweep - Alder Mfg.", "Compliance Sweep - Birchway Clinics",
             "Compliance Sweep - Cobalt Foods", "Compliance Sweep - Dunmore Plastics"],
    "IA": ["Wire Transfer Operations Audit", "Vendor Management Program Audit",
           "Loan Servicing Controls Audit", "Model Risk Governance Audit"],
}

_REVIEWERS = ["A. Chen", "R. Ortiz", "M. Kowalski", "D. Whitaker"]

_REVIEW_DATES = [dt.date(2025, 8, 14), dt.date(2025, 11, 6),
                 dt.date(2026, 2, 19), dt.date(2026, 5, 7)]

_NO_NOTES = [
    "Financial statements stale beyond policy window; no waiver in file.",
    "Approval signature exceeds officer's delegated authority; no co-approval.",
    "UCC continuation lapsed; lien perfection not verified at review date.",
    "Covenant test for Q4 not evidenced; compliance certificate missing.",
    "Projection growth assumption unsupported versus 3-year actuals.",
    "Guarantor PFS older than 12 months; reliance not currently supported.",
]
_OBS_NOTES = [
    "Spread mislabels FY2024 column as FY2025; values correct.",
    "Annual review completed 10 days before deadline two cycles running - timing risk.",
    "Site-visit memo informative but not filed in imaging system.",
    "Borrowing-base certificate delivered by email rather than portal per agreement.",
    "Rate-reset sensitivity shown only at +100bp; broader stress would aid analysis.",
]

# Per-segment plausible (leverage x, DSCR x, LTV %) ranges; None = not applicable.
_RATIO_RANGES = {
    "CI": ((2.0, 4.5), (1.15, 2.2), None),
    "CRE": (None, (1.10, 1.65), (0.55, 0.82)),
    "LL": ((3.8, 6.6), (1.05, 1.6), None),
    "ABL": ((2.5, 5.0), (1.1, 1.8), None),
    "ARG": ((5.0, 9.0), (0.4, 1.0), None),
    "COMP": (None, None, None),
    "IA": (None, None, None),
}


def _answer(profile_bad: float):
    r = _RNG.random()
    if r < profile_bad:
        return "No", _RNG.choice(_NO_NOTES)
    if r < profile_bad + 0.07:
        return "Obs", _RNG.choice(_OBS_NOTES)
    if r < profile_bad + 0.15:
        return "N/A", ""
    return "Yes", ""


def generate():
    """Return (credits, responses).

    credits:   list of dicts (one per credit-review)
    responses: list of dicts (one per question per credit)
    """
    credits, responses = [], []
    for seg_code, seg in SEGMENTS.items():
        questions = list(question_rows(seg_code))
        for i, borrower in enumerate(_BORROWERS[seg_code]):
            credit_id = f"{seg_code}-{2026}{i+1:03d}"
            review_date = _REVIEW_DATES[i]
            reviewer = _REVIEWERS[i % len(_REVIEWERS)]
            base_grade = {"ARG": _RNG.choice([5, 6, 6, 7])}.get(
                seg_code, _RNG.choice([2, 3, 3, 4, 4, 5])
            )
            downgrade = _RNG.random() < 0.25 and base_grade < 8
            crr_grade = base_grade + (1 if downgrade else 0)
            profile_bad = 0.05 + (0.05 if downgrade else 0) + (0.04 if seg_code == "ARG" else 0)

            lev_r, dscr_r, ltv_r = _RATIO_RANGES[seg_code]
            lev = round(_RNG.uniform(*lev_r), 1) if lev_r else None
            dscr = round(_RNG.uniform(*dscr_r), 2) if dscr_r else None
            ltv = round(_RNG.uniform(*ltv_r), 3) if ltv_r else None

            credits.append({
                "credit_id": credit_id, "segment": seg_code,
                "segment_name": seg["name"], "borrower": borrower,
                "commitment": _RNG.randrange(5_000, 80_000, 2_500),
                "review_date": review_date, "reviewer": reviewer,
                "lob_grade": base_grade, "crr_grade": crr_grade,
                "leverage": lev, "dscr": dscr, "ltv": ltv,
                "status": "Complete" if i < 3 else "In Progress",
            })
            for qid, section, question, severity in questions:
                ans, note = _answer(profile_bad)
                responses.append({
                    "credit_id": credit_id, "segment": seg_code, "qid": qid,
                    "section": section, "question": question,
                    "severity": severity, "answer": ans, "note": note,
                    "review_date": review_date, "reviewer": reviewer,
                })
    return credits, responses


# Hand-built C&I demo credit: matches the sample CAM fixture (Meridian) so the
# form's asserted column ties to the Assertions sheet and the ratio engine
# reproduces / challenges the memo's stated ratios.
MERIDIAN_INPUTS = {
    "Revenue ($000)": 96_400,
    "EBITDA ($000)": 17_100,
    "Interest Expense ($000)": 3_400,
    "CPLTD ($000)": 4_980,
    "Cash Taxes ($000)": 2_400,
    "Maintenance Capex ($000)": 1_800,
    "Distributions ($000)": 1_000,
    "Total Debt ($000)": 65_000,
    "Senior Debt ($000)": 49_590,
    "Current Assets ($000)": 31_200,
    "Current Liabilities ($000)": 18_350,
    "Accounts Receivable ($000)": 14_800,
    "Inventory ($000)": 9_650,
    "Accounts Payable ($000)": 7_900,
    "COGS ($000)": 66_500,
    "Tangible Net Worth ($000)": 28_900,
    "Guarantor Cash Flow ($000)": 1_200,
    "Guarantor Debt Service ($000)": 600,
}

# Asserted (per CAM) values for the C&I ratio block, from the fixture memo.
MERIDIAN_ASSERTED = {
    "CI-R1": 3.8, "CI-R2": 2.9, "CI-R3": 1.42, "CI-R4": 1.25,
    "CI-R5": 3.6, "CI-R6": 1.7, "CI-R9": 1.55,
}

# Demo inputs for the other segment forms (first sample credit of each).
FORM_INPUTS = {
    "CRE": {
        "Net Operating Income ($000)": 4_150, "Annual Debt Service ($000)": 3_120,
        "Loan Commitment ($000)": 42_000, "Appraised Value ($000)": 58_500,
        "Current Occupancy (%)": 0.88, "Leases Rolling 24 Mo (%)": 0.31,
        "In-Place Cap Rate (%)": 0.071, "Stressed Cap Rate (%)": 0.085,
    },
    "LL": {
        "Reported EBITDA ($000)": 22_400, "EBITDA Add-Backs ($000)": 4_300,
        "Total Debt ($000)": 152_000, "Senior Debt ($000)": 98_000,
        "Base-Case Annual FCF ($000)": 11_500, "Enterprise Value ($000)": 240_000,
        "Interest Expense ($000)": 13_900,
    },
    "ABL": {
        "Gross Accounts Receivable ($000)": 38_500, "Ineligible AR ($000)": 6_200,
        "AR Advance Rate (%)": 0.85, "Gross Inventory ($000)": 27_400,
        "Ineligible Inventory ($000)": 8_100, "Inventory Advance Rate (%)": 0.60,
        "Reserves ($000)": 2_500, "Outstanding Balance ($000)": 31_750,
        "Dilution (%)": 0.043,
    },
    "ARG": {
        "Loan Balance ($000)": 18_600, "Specific Reserve ($000)": 3_100,
        "Prior Charge-Offs ($000)": 2_400, "Recoveries to Date ($000)": 350,
        "Collateral Value - Gross ($000)": 21_000, "Liquidation Discount (%)": 0.25,
        "Estimated Costs to Sell (%)": 0.08,
    },
    "COMP": {},
    "IA": {
        "Population Size (items)": 1240, "Sample Size (items)": 60,
        "Items Tested (items)": 60, "Exceptions Found (items)": 4,
        "Tolerable Exception Rate (%)": 0.05,
    },
}

FORM_ASSERTED = {
    "CRE": {"CRE-R1": 1.33, "CRE-R2": 0.718, "CRE-R3": 0.099},
    "LL": {"LL-R3": 5.7, "LL-R4": 3.7, "LL-R6": 6.6},
    "ABL": {"ABL-R3": 36_000, "ABL-R5": 1.13},
    "ARG": {"ARG-R2": 0.78},
    "COMP": {},
    "IA": {"IA-R3": 0.033},
}
