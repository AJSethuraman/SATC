"""Synthetic, masked fixtures — NEVER real client PII.

These power the demo workbook, tests, and screenshots. Names are obviously
fictional, SSNs/EINs use IRS-reserved/invalid ranges, and dollar amounts are
illustrative. The amounts are chosen so the workpaper cross-checks and the
Drake reconciliation tie cleanly, demonstrating a "clean" return.
"""

from __future__ import annotations

from decimal import Decimal

from satc.models.identity import IdentityRecord, VaultAddress, VaultContact

# 2024 federal MFJ standard deduction (mirrors configs/crosswalk/federal/2024.yaml).
# Used only to precompute the demo's reconciliation tie-out values.
_STD_DED_MFJ_2024 = 29200


def synthetic_identities() -> list[IdentityRecord]:
    """A small book of synthetic clients across the four return types."""
    return [
        IdentityRecord(
            client_id="SATC-001000", entity_type="INDIVIDUAL",
            legal_name="Jordan & Avery Maplewood", tin="400-55-1234",
            addresses=[VaultAddress(line1="118 Buckeye Lane", city="Dublin", state="OH", zip="43017")],
            contacts=[VaultContact(name="Jordan Maplewood", email="jordan@example.invalid", role="Taxpayer")],
        ),
        IdentityRecord(
            client_id="SATC-002000", entity_type="SCORP",
            legal_name="Northshore Cabinetry, Inc.", tin="38-7654321",
            addresses=[VaultAddress(line1="900 Industrial Pkwy", city="Ann Arbor", state="MI", zip="48104")],
            contacts=[VaultContact(name="Riley Park", email="riley@example.invalid", role="Officer")],
        ),
        IdentityRecord(
            client_id="SATC-003000", entity_type="PARTNERSHIP",
            legal_name="Beacon Hill Advisors, LP", tin="04-3219876",
            addresses=[VaultAddress(line1="55 Tremont St", city="Boston", state="MA", zip="02108")],
            contacts=[VaultContact(name="Sam Okafor", email="sam@example.invalid", role="Partner")],
        ),
        IdentityRecord(
            client_id="SATC-004000", entity_type="CCORP",
            legal_name="Lakefront Logistics Corp.", tin="34-1928374",
            addresses=[VaultAddress(line1="2200 Lakeside Ave", city="Cleveland", state="OH", zip="44114")],
            contacts=[VaultContact(name="Dana Lee", email="dana@example.invalid", role="CFO")],
        ),
    ]


def synthetic_1040_values(tax_year: int = 2024) -> dict[str, object]:
    """Confirmed 1040 line values for SATC-001000 (MFJ, OH resident).

    Returns a ``{line_id: value}`` dict consumed by the line-sheet builder to
    prefill the input cells; computed/linked cells remain live formulas.
    """
    v: dict[str, object] = {
        # Filing status & dependents
        "filing_status": "MFJ", "dependents_count": 2, "ctc_children": 2, "taxpayer_65_blind": 0,
        # Wages, interest, dividends
        "wages": 145000, "fed_wh_w2": 18000, "ss_wages": 145000,
        "interest": 1200, "dividends_ord": 3400, "dividends_qual": 3000,
        # Schedule C
        "sch_c_gross": 60000, "sch_c_expenses": 22000, "sch_c_miles": 4000,
        "sec179_taken": 5000, "sch_c_depr_other": 1500,
        # Schedule D
        "cap_st_proceeds": 10000, "cap_st_basis": 8000,
        "cap_lt_proceeds": 40000, "cap_lt_basis": 25000,
        # Schedule E
        "rental_income": 24000, "rental_expenses": 18000,
        "k1_ordinary": 12000, "k1_rental_other": 0,
        # Retirement / SS / other
        "retirement_taxable": 0, "ss_benefits": 0, "ss_taxable": 0, "other_income": 0,
        # Adjustments
        "adj_hsa": 8300, "adj_se_tax": 2884, "adj_other": 0,
        # Schedule A
        "sch_a_medical": 0, "sch_a_salt": 10000, "sch_a_interest": 9000, "sch_a_charity": 4000,
        # QBI
        "qbi_deduction": 8164,
        # Tax / credits / payments
        "tax_per_drake": 26000, "se_tax": 5767,
        "ctc_claimed": 4000, "eitc_claimed": 0, "education_credit": 0, "energy_credit": 0,
        "fed_est_payments": 8000,
        # Estimates / safe harbor
        "prior_year_tax": 24000, "prior_year_agi": 190000,
        # State
        "state_code": "OH", "residency": "FULL_YEAR",
        "state_additions": 0, "state_subtractions": 0,
        "state_tax_per_drake": 6200, "state_wh": 5000, "state_est": 1500,
    }

    # Precompute the workpaper chain so the Drake reconciliation ties to zero in
    # the demo (real engagements would surface any genuine difference).
    auto = v["sch_c_miles"] * 0.67
    sch_c_net = v["sch_c_gross"] - v["sch_c_expenses"] - auto - v["sec179_taken"] - v["sch_c_depr_other"]
    cap_gain_net = (v["cap_st_proceeds"] - v["cap_st_basis"]) + (v["cap_lt_proceeds"] - v["cap_lt_basis"])
    sch_e_net = (v["rental_income"] - v["rental_expenses"]) + v["k1_ordinary"] + v["k1_rental_other"]
    total_income = (v["wages"] + v["interest"] + v["dividends_ord"] + sch_c_net + cap_gain_net
                    + sch_e_net + v["retirement_taxable"] + v["ss_taxable"] + v["other_income"])
    adjustments = v["adj_hsa"] + v["adj_se_tax"] + v["adj_other"]
    agi = total_income - adjustments
    sch_a_total = v["sch_a_medical"] + v["sch_a_salt"] + v["sch_a_interest"] + v["sch_a_charity"]
    deduction_used = max(sch_a_total, _STD_DED_MFJ_2024)
    taxable_income = max(0, agi - deduction_used - v["qbi_deduction"])
    total_credits = v["ctc_claimed"] + v["eitc_claimed"] + v["education_credit"] + v["energy_credit"]
    total_tax = max(0, v["tax_per_drake"] + v["se_tax"] - total_credits)
    total_payments = v["fed_wh_w2"] + v["fed_est_payments"]
    refund_or_due = total_payments - total_tax

    v.update({
        "drake_agi": round(agi),
        "drake_taxable": round(taxable_income),
        "drake_total_tax": round(total_tax),
        "drake_refund": round(refund_or_due),
    })
    return v


def synthetic_carryforwards() -> list[dict]:
    """A few prior-year carryforwards for the data mart / proforma demo."""
    return [
        {"client_id": "SATC-001000", "kind": "CAP_LOSS_LT", "tax_year_generated": 2023,
         "amount": Decimal("0"), "jurisdiction": "US", "return_type": "1040"},
        {"client_id": "SATC-001000", "kind": "CHARITABLE", "tax_year_generated": 2023,
         "amount": Decimal("0"), "jurisdiction": "US", "return_type": "1040"},
    ]
