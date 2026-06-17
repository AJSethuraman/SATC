"""Synthetic, masked fixtures — NEVER real client PII.

These power the demo workbook, tests, and screenshots. Names are obviously
fictional, SSNs/EINs use IRS-reserved/invalid ranges, and dollar amounts are
illustrative. The amounts are chosen so the workpaper cross-checks and the
Drake reconciliation tie cleanly, demonstrating a "clean" return.
"""

from __future__ import annotations

from decimal import Decimal

from satc.ids import line_item_key, return_key
from satc.models.identity import IdentityRecord, VaultAddress, VaultContact
from satc.models.mart import (
    Carryforward,
    DataMart,
    DocumentRecord,
    EngagementRecord,
    EstimatePayment,
    LineItem,
    OwnerBasis,
    ReturnRecord,
)
from satc.models.provenance import Provenance, SourceRef

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


def synthetic_entity_values(return_type: str) -> dict[str, object]:
    """Confirmed line values for the entity returns (chosen to tie cleanly).

    Beginning basis/capital come from the data mart via carryforwards (0 here, as
    the demo starts a fresh basis history); reconciliation & M-1 differences
    resolve to 0.
    """
    if return_type == "1120S":
        v = {
            "shareholders_count": 2, "state_code": "MI",
            "gross_receipts": 900000, "cogs": 540000, "other_income": 0,
            "officer_comp": 90000, "salaries_wages": 120000, "repairs": 8000,
            "rents": 24000, "taxes_licenses": 12000, "depreciation": 20000,
            "sec179": 15000, "other_deductions": 16000,
            "k_rental": 0, "k_interest": 500, "k_dividends": 0, "k_charitable": 2000,
            "distributions_total": 50000,
            "k1_ordinary_sum": 70000, "k1_dist_sum": 50000,
            "basis_contrib": 0, "basis_income": 28200, "basis_distributions": 20000, "basis_losses": 0,
            "total_assets": 300000, "total_liabilities": 120000, "total_equity": 180000,
            "book_income": 68500, "m1_add_taxexempt_exp": 0,
            "m1_subtract_taxexempt_inc": 0, "m1_other": 0,
            "apportion_sales_state": 600000, "apportion_sales_total": 900000,
            "pte_tax_per_drake": 1983,
            "drake_ordinary": 70000, "drake_distributions": 50000,
        }
        return v
    if return_type == "1065":
        return {
            "partners_count": 2, "state_code": "MA",
            "gross_receipts": 1200000, "cogs": 700000, "other_income": 0,
            "guaranteed_payments": 120000, "salaries_wages": 150000, "rents": 36000,
            "taxes_licenses": 18000, "depreciation": 30000, "sec179": 20000,
            "other_deductions": 26000,
            "k_rental": 0, "k_interest": 800, "distributions_total": 90000,
            "k1_ordinary_sum": 120000, "k1_gp_sum": 120000,
            "cap_contrib": 0, "cap_income": 60400, "cap_withdrawals": 45000, "cap_losses": 0,
            "total_assets": 400000, "total_liabilities": 150000, "total_capital": 250000,
            "book_income": 120800, "m1_add": 0, "m1_subtract": 0, "m1_other": 0,
            "apportion_sales_state": 720000, "apportion_sales_total": 1200000,
            "pte_tax_per_drake": 6040,
            "drake_ordinary": 120000,
        }
    if return_type == "1120":
        return {
            "state_code": "OH",
            "gross_receipts": 2000000, "cogs": 1100000, "dividends_received": 10000,
            "interest_income": 5000, "other_income": 0,
            "officer_comp": 150000, "salaries_wages": 200000, "rents": 48000,
            "taxes_licenses": 30000, "depreciation": 40000, "other_deductions": 42000,
            "charitable_claimed": 30000,
            "corp_rate": 0.21, "tax_per_drake": 78750,
            "book_income": 296250, "m1_fed_tax": 78750, "m1_add": 0, "m1_subtract": 0, "m1_other": 0,
            "total_assets": 1500000, "total_liabilities": 600000, "total_equity": 900000,
            "apportion_sales_state": 1400000, "apportion_sales_total": 2000000,
            "state_tax_per_drake": 9187,
            "drake_taxable": 375000,
        }
    return {}


def synthetic_documents() -> list[dict]:
    """Synthetic source documents as labeled key/value pairs (as a parser hands off).

    Includes two W-2s (to exercise aggregation) and one deliberately malformed
    money field ("see stub") to prove the gate routes it to review instead of
    guessing. SSN/EIN use invalid/reserved ranges and are masked on staging.
    """
    return [
        {"document_id": "DOC-0001", "doc_key": "w2", "labeled": {
            "Box 1 - Wages, tips, other comp": "98,000.00",
            "Box 2 - Federal income tax withheld": "12,500.00",
            "Box 3 - Social Security wages": "98,000.00",
            "Box 17 - State income tax": "3,200.00",
            "Box 15 - State": "OH",
            "Employer name": "Buckeye Manufacturing LLC",
            "Employer EIN": "31-0009999",
            "Employee SSN": "400-55-1234"}},
        {"document_id": "DOC-0002", "doc_key": "w2", "labeled": {
            "Box 1 - Wages, tips, other comp": "47,000.00",
            "Box 2 - Federal income tax withheld": "5,500.00",
            "Box 17 - State income tax": "1,800.00",
            "Employer name": "Dublin Schools",
            "Employer EIN": "31-0007777"}},
        {"document_id": "DOC-0003", "doc_key": "1099int", "labeled": {
            "Box 1 - Interest income": "1,200.00",
            "Payer name": "Heartland Bank",
            "Payer TIN": "34-0001111"}},
        {"document_id": "DOC-0004", "doc_key": "1099div", "labeled": {
            "Box 1a - Total ordinary dividends": "3,400.00",
            "Box 1b - Qualified dividends": "see stub",  # malformed -> NEEDS_REVIEW
            "Payer name": "Vanguard"}},
        {"document_id": "DOC-0005", "doc_key": "k1_1120s", "labeled": {
            "Box 1 - Ordinary business income": "12,000.00",
            "Box 16 - Items affecting shareholder basis (distributions)": "9,000.00",
            "Box 17 - Code V QBI": "12,000.00",
            "Corporation EIN": "38-7654321",
            "Shareholder ownership %": "40"}},
        {"document_id": "DOC-0006", "doc_key": "prior_1040", "labeled": {
            "Line 11 - Adjusted gross income": "190,000.00",
            "Line 22 - Total tax": "24,000.00",
            "Capital loss carryover to next year": "0",
            "Filing status": "MFJ"}},
    ]


def _li(rk: str, schedule: str, line: str, label: str, amount, kind="SOURCE_DOC") -> LineItem:
    prov = Provenance(source_kind=kind, source_ref=SourceRef(citation="synthetic"))
    return LineItem(line_item_key=line_item_key(rk, schedule, line), return_key=rk,
                    schedule=schedule, line_code=line, label=label,
                    amount=Decimal(str(amount)), provenance=prov)


def synthetic_mart() -> DataMart:
    """A small, multi-year normalized data mart for the proforma/comparison demos.

    SATC-001000 (1040, OH) has both 2023 and 2024 on file with deliberate
    variances: a wage swing, a 1099-INT that dropped, and a dropped dependent.
    Entity returns are on file for 2024, with carryforwards and basis to seed 2025.
    """
    mart = DataMart()
    mart.public_clients = [r.to_public() for r in synthetic_identities()]

    rk_23 = return_key("SATC-001000", 2023, "1040", "US")
    rk_24 = return_key("SATC-001000", 2024, "1040", "US")
    rk_24_oh = return_key("SATC-001000", 2024, "1040", "OH")

    mart.returns = [
        ReturnRecord(return_key=rk_23, client_id="SATC-001000", tax_year=2023,
                     return_type="1040", jurisdiction="US", status="Accepted",
                     residency="FULL_YEAR", refund_amount=Decimal("1500")),
        ReturnRecord(return_key=rk_24, client_id="SATC-001000", tax_year=2024,
                     return_type="1040", jurisdiction="US", status="In review",
                     residency="FULL_YEAR", balance_due_amount=Decimal("1767")),
        ReturnRecord(return_key=rk_24_oh, client_id="SATC-001000", tax_year=2024,
                     return_type="1040", jurisdiction="OH", status="In review",
                     residency="FULL_YEAR", refund_amount=Decimal("300")),
        ReturnRecord(return_key=return_key("SATC-002000", 2024, "1120S", "MI"),
                     client_id="SATC-002000", tax_year=2024, return_type="1120S",
                     jurisdiction="MI", status="Ready to file"),
        ReturnRecord(return_key=return_key("SATC-003000", 2024, "1065", "MA"),
                     client_id="SATC-003000", tax_year=2024, return_type="1065",
                     jurisdiction="MA", status="In prep"),
        ReturnRecord(return_key=return_key("SATC-004000", 2024, "1120", "OH"),
                     client_id="SATC-004000", tax_year=2024, return_type="1120",
                     jurisdiction="OH", status="Filed", is_extended=True),
    ]

    mart.line_items = [
        # 2023 (prior year)
        _li(rk_23, "1040", "wages", "Wages", 130000),
        _li(rk_23, "SCH_B", "interest", "Taxable interest", 2500),
        _li(rk_23, "SCH_B", "old_bank_int", "Interest — Old Bank 1099-INT", 1800),
        _li(rk_23, "1040", "agi", "Adjusted gross income", 180000, "DRAKE_OUTPUT"),
        _li(rk_23, "1040", "taxable_income", "Taxable income", 150000, "DRAKE_OUTPUT"),
        _li(rk_23, "1040", "total_tax", "Total tax", 24000, "DRAKE_OUTPUT"),
        _li(rk_23, "1040", "dependents", "Dependents", 3),
        # 2024 (current year)
        _li(rk_24, "1040", "wages", "Wages", 145000),
        _li(rk_24, "SCH_B", "interest", "Taxable interest", 1200),
        _li(rk_24, "SCH_B", "dividends_ord", "Ordinary dividends", 3400),
        _li(rk_24, "1040", "agi", "Adjusted gross income", 202236, "DRAKE_OUTPUT"),
        _li(rk_24, "1040", "taxable_income", "Taxable income", 164872, "DRAKE_OUTPUT"),
        _li(rk_24, "1040", "total_tax", "Total tax", 27767, "DRAKE_OUTPUT"),
        _li(rk_24, "1040", "dependents", "Dependents", 2),
    ]

    cf_prov = Provenance(source_kind="DRAKE_OUTPUT",
                         source_ref=SourceRef(worksheet_title="Carryover Worksheet"))
    mart.carryforwards = [
        Carryforward(cf_id="CF-1000-CAPLT-2023", client_id="SATC-001000", return_type="1040",
                     jurisdiction="US", kind="CAP_LOSS_LT", tax_year_generated=2023,
                     amount=Decimal("3000"), provenance=cf_prov),
        Carryforward(cf_id="CF-1000-CHAR-2023", client_id="SATC-001000", return_type="1040",
                     jurisdiction="US", kind="CHARITABLE", tax_year_generated=2023,
                     amount=Decimal("2000"), expires_after_year=2028, provenance=cf_prov),
        Carryforward(cf_id="CF-1000-STOVP-2024", client_id="SATC-001000", return_type="1040",
                     jurisdiction="OH", kind="STATE_OVERPAYMENT_APPLIED", tax_year_generated=2024,
                     amount=Decimal("300"), provenance=cf_prov),
        Carryforward(cf_id="CF-4000-NOL-2023", client_id="SATC-004000", return_type="1120",
                     jurisdiction="US", kind="NOL", tax_year_generated=2023,
                     amount=Decimal("100000"), provenance=cf_prov),
    ]

    rk_scorp = return_key("SATC-002000", 2024, "1120S", "MI")
    mart.owner_basis = [
        OwnerBasis(return_key=rk_scorp, client_id="SATC-002000", owner_id="OWNER-A",
                   tax_year=2024, beginning_balance=Decimal("0"), contributions=Decimal("0"),
                   income_items=Decimal("28200"), distributions=Decimal("20000"),
                   loss_items=Decimal("0"), ending_balance=Decimal("8200"),
                   ownership_pct=Decimal("0.40"), provenance=cf_prov),
    ]

    mart.estimate_payments = [
        EstimatePayment(payment_id=f"EP-1000-2024-Q{q}", client_id="SATC-001000",
                        tax_year=2024, jurisdiction="US", period=f"Q{q}", amount=Decimal("2000"))
        for q in range(1, 5)
    ]

    mart.engagements = [
        EngagementRecord(client_id="SATC-001000", tax_year=2024,
                         engagement_letter_status="Signed", fee_amount=Decimal("650"),
                         invoiced=True, paid=False),
        EngagementRecord(client_id="SATC-002000", tax_year=2024,
                         engagement_letter_status="Signed", fee_amount=Decimal("2400"),
                         invoiced=True, paid=True),
        EngagementRecord(client_id="SATC-003000", tax_year=2024,
                         engagement_letter_status="Sent", fee_amount=Decimal("3200")),
        EngagementRecord(client_id="SATC-004000", tax_year=2024,
                         engagement_letter_status="Signed", fee_amount=Decimal("5500"),
                         invoiced=True, paid=True),
    ]

    from datetime import date as _d
    sp = "https://sharepoint.example/SATC/{cid}/2024/{doc}"
    mart.documents = [
        DocumentRecord("DOC-0001", "SATC-001000", 2024, "W-2", "Received", _d(2025, 2, 3),
                       sp.format(cid="SATC-001000", doc="W2-1"), "preparer"),
        DocumentRecord("DOC-0002", "SATC-001000", 2024, "W-2", "Received", _d(2025, 2, 3),
                       sp.format(cid="SATC-001000", doc="W2-2"), "preparer"),
        DocumentRecord("DOC-0010", "SATC-001000", 2024, "1099-DIV", "Requested", _d(2025, 2, 1),
                       "", "preparer", note="Awaiting corrected 1099-DIV (Box 1b)"),
        DocumentRecord("DOC-0011", "SATC-001000", 2024, "Engagement letter", "Signed", _d(2025, 1, 15),
                       sp.format(cid="SATC-001000", doc="EL"), "client"),
        DocumentRecord("DOC-0012", "SATC-001000", 2024, "Form 8879", "Requested", _d(2025, 3, 1),
                       "", "preparer", note="E-file authorization not yet signed"),
        DocumentRecord("DOC-0013", "SATC-001000", 2024, "Delivery email", "Sent", _d(2025, 3, 10),
                       sp.format(cid="SATC-001000", doc="delivery"), "system"),
        DocumentRecord("DOC-0020", "SATC-002000", 2024, "K-1 (1120S)", "Received", _d(2025, 2, 20),
                       sp.format(cid="SATC-002000", doc="K1"), "preparer"),
        DocumentRecord("DOC-0021", "SATC-002000", 2024, "Trial balance", "Requested", _d(2025, 2, 10),
                       "", "preparer", note="Awaiting year-end trial balance"),
        DocumentRecord("DOC-0030", "SATC-003000", 2024, "Organizer", "Requested", _d(2025, 1, 20),
                       "", "preparer", note="Partnership organizer outstanding"),
        DocumentRecord("DOC-0040", "SATC-004000", 2024, "Signed 8879", "Signed", _d(2025, 3, 5),
                       sp.format(cid="SATC-004000", doc="8879"), "client"),
    ]
    return mart


def synthetic_drake_intake() -> list:
    """A DEA-compatible intake (full synthetic PII) for SATC-001000.

    Used only to exercise the Drake input generator + drake-entry-assistant seam.
    Written to a transient, git-ignored location — never committed. Wages total
    $145,000, matching the 1040 demo.
    """
    from satc.drake.input_generator import IntakeClient, IntakeW2
    return [IntakeClient(
        client_id="SATC-001000", tax_year=2024, filing_status="MFJ",
        tp_first="Jordan", tp_last="Maplewood", tp_ssn="400-55-1234",
        tp_dob="1980-04-12", tp_occupation="Engineer",
        sp_first="Avery", sp_last="Maplewood", sp_ssn="400-55-9876",
        sp_dob="1982-08-03", sp_occupation="Teacher",
        address="118 Buckeye Lane", city="Dublin", state="OH", zip="43017",
        phone="614-555-0100", email="jordan@example.invalid",
        w2s=[
            IntakeW2(w2_id="W2-1", employee="taxpayer", employer_ein="31-0009999",
                     employer_name="Buckeye Manufacturing LLC", employer_address="900 Industrial Pkwy",
                     employer_city="Dublin", employer_state="OH", employer_zip="43017",
                     box1=98000, box2=12500, box3=98000, box4=6076, box5=98000, box6=1421,
                     box15_state="OH", box16=98000, box17=3200),
            IntakeW2(w2_id="W2-2", employee="spouse", employer_ein="31-0007777",
                     employer_name="Dublin City Schools", employer_address="7030 Coffman Rd",
                     employer_city="Dublin", employer_state="OH", employer_zip="43017",
                     box1=47000, box2=5500, box3=47000, box4=2914, box5=47000, box6=681,
                     box15_state="OH", box16=47000, box17=1800),
        ])]


def synthetic_preparer_set_text() -> str:
    """A synthetic Drake 'preparer copy' as text (the shape of pdftotext output).

    Demonstrates multi-state aggregation (Federal + OH + MI) and the paper-file
    branch (Michigan is paper-filed with a mail-to address). Titles match Drake's
    stable worksheet titles so the parser keys off titles, not coordinates.
    """
    return (
        "FILING INSTRUCTIONS - FEDERAL\n"
        "Form: 1040\n"
        "Filing method: Electronically filed\n"
        "Due date: 04/15/2025\n"
        "Balance due: $1,767\n"
        "Mail to: N/A (e-filed)\n"
        "\f"
        "FILING INSTRUCTIONS - OHIO\n"
        "Form: IT 1040\n"
        "Filing method: Electronically filed\n"
        "Due date: 04/15/2025\n"
        "Refund: $300\n"
        "\f"
        "FILING INSTRUCTIONS - MICHIGAN\n"
        "Form: MI-1040\n"
        "Filing method: Paper filed\n"
        "Due date: 04/15/2025\n"
        "Balance due: $245\n"
        "Mail to: Michigan Department of Treasury, Lansing MI 48956\n"
        "\f"
        "TAX RETURN COMPARISON\n"
        "                          2022        2023        2024\n"
        "Wages                  120,000     130,000     145,000\n"
        "Total income           175,000     190,000     213,420\n"
        "Adjusted gross income  168,000     180,000     202,236\n"
        "Taxable income         140,000     150,000     164,872\n"
        "Total tax               22,000      24,000      27,767\n"
        "Withholding             20,000      21,000      18,000\n"
        "\f"
        "CARRYOVER WORKSHEET\n"
        "Item                         To 2025\n"
        "Long-term capital loss        3,000\n"
        "Charitable contribution       2,000\n"
        "State overpayment applied       300\n"
        "\f"
        "EF STATUS / FORM 9325\n"
        "Federal: Accepted 03/12/2025\n"
        "Ohio: Accepted 03/12/2025\n"
    )


def synthetic_carryforwards() -> list[dict]:
    """A few prior-year carryforwards for the data mart / proforma demo."""
    return [
        {"client_id": "SATC-001000", "kind": "CAP_LOSS_LT", "tax_year_generated": 2023,
         "amount": Decimal("0"), "jurisdiction": "US", "return_type": "1040"},
        {"client_id": "SATC-001000", "kind": "CHARITABLE", "tax_year_generated": 2023,
         "amount": Decimal("0"), "jurisdiction": "US", "return_type": "1040"},
    ]
