"""Excel "audit tape" for a withholding estimate.

Renders an :class:`~satc.withholding.models.EstimateResult` as a branded,
preparer-reviewable workpaper on the SATC workbook styling: the inputs, the full
Form 1040 projection walk, the per-paycheck recommendation, and — because this is
a tax workpaper — the **cited tax-law basis** pulled straight from the crosswalk
year that produced the numbers. One sheet, print-ready.
"""

from __future__ import annotations

from decimal import Decimal

from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from satc.crosswalk import CrosswalkLibrary
from satc.withholding.models import EstimateResult, EstimatorInput
from satc.workbook import components as K
from satc.workbook import styles as S
from satc.workbook.styles import NF

_LAST_COL = 5
_FILING_LABEL = {
    "single": "Single",
    "married_jointly": "Married filing jointly",
    "married_separately": "Married filing separately",
    "head_of_household": "Head of household",
}


def _f(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def _money_row(ws: Worksheet, row: int, label: str, value: Decimal | None,
               *, style: S.CellStyle = S.COMPUTED, basis: str = "",
               fmt: str = NF.USD_CENTS) -> int:
    K.write(ws, row, 1, label, S.LABEL)
    if value is not None:
        K.write(ws, row, 3, _f(value), style, number_format=fmt)
    if basis:
        K.write(ws, row, 5, basis, S.LABEL_MUTED)
    return row + 1


def _text_row(ws: Worksheet, row: int, label: str, value: str, basis: str = "") -> int:
    K.write(ws, row, 1, label, S.LABEL)
    K.write(ws, row, 3, value, S.INPUT_TEXT)
    if basis:
        K.write(ws, row, 5, basis, S.LABEL_MUTED)
    return row + 1


def build_audit_tape(result: EstimateResult, inp: EstimatorInput) -> Workbook:
    """Build the audit-tape workbook for one estimate."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Withholding Estimate"
    S.paper_canvas(ws, max_col=_LAST_COL, max_row=120)
    K.set_widths(ws, {"A": 44, "B": 2, "C": 16, "D": 2, "E": 56})
    K.page_setup(ws, "Withholding Estimate", orientation="portrait")

    b = result.breakdown
    rec = result.recommendation

    # -- title ------------------------------------------------------------
    K.write(ws, 1, 1, "SETHURAMAN", S.WORDMARK)
    K.merge_text(ws, 2, 1, _LAST_COL,
                 f"Withholding Estimate — Tax Year {result.tax_year_used}", S.TITLE)
    K.write(ws, 3, 1, _FILING_LABEL.get(result.filing_status, result.filing_status),
            S.SUBTITLE)
    row = 5

    # -- inputs -----------------------------------------------------------
    row = K.section_header(ws, row, "Inputs", _LAST_COL)
    oi = inp.other_income
    primary = inp.paystub
    row = _text_row(ws, row, "Pay frequency", primary.pay_frequency)
    row = _money_row(ws, row, "Gross pay per period", primary.gross_pay_per_period,
                     style=S.INPUT)
    row = _money_row(ws, row, "Federal tax withheld per period",
                     primary.federal_tax_withheld_per_period, style=S.INPUT)
    if primary.retirement_pretax_per_period:
        row = _money_row(ws, row, "Pre-tax retirement per period",
                         primary.retirement_pretax_per_period, style=S.INPUT)
    if primary.ytd_taxable_wages is not None:
        row = _money_row(ws, row, "YTD taxable wages", primary.ytd_taxable_wages, style=S.INPUT)
    if primary.ytd_federal_tax_withheld is not None:
        row = _money_row(ws, row, "YTD federal tax withheld",
                         primary.ytd_federal_tax_withheld, style=S.INPUT)
    for label, value in (
        ("Interest income", oi.interest),
        ("Ordinary dividends", oi.ordinary_dividends),
        ("Qualified dividends", oi.qualified_dividends),
        ("Long-term capital gains", oi.long_term_capital_gains),
        ("Short-term capital gains", oi.short_term_capital_gains),
        ("Self-employment net", oi.self_employment_net),
    ):
        if value:
            row = _money_row(ws, row, label, value, style=S.INPUT)
    if inp.deductions.itemized_total is not None:
        row = _money_row(ws, row, "Itemized deductions (entered)",
                         inp.deductions.itemized_total, style=S.INPUT)
    if inp.target_refund:
        row = _money_row(ws, row, "Target refund", inp.target_refund, style=S.INPUT)

    # -- projection (the 1040 walk) --------------------------------------
    row += 1
    row = K.section_header(ws, row, "Projection — Form 1040 walk", _LAST_COL)
    row = _money_row(ws, row, "Projected taxable wages", b.projected_taxable_wages)
    row = _money_row(ws, row, "Total income", b.total_income)
    row = _money_row(ws, row, "Adjustments to income", b.adjustments_total)
    row = _money_row(ws, row, "Adjusted gross income", b.adjusted_gross_income,
                     style=S.COMPUTED_BOLD)
    row = _money_row(ws, row, "Deduction used", b.deduction_used,
                     basis=f"{b.deduction_kind} deduction")
    row = _money_row(ws, row, "Taxable income", b.taxable_income, style=S.COMPUTED_BOLD)
    row = _money_row(ws, row, "Ordinary income tax", b.ordinary_income_tax)
    row = _money_row(ws, row, "Capital-gains / qualified-dividend tax", b.capital_gains_tax)
    row = _money_row(ws, row, "Income tax before credits", b.income_tax_before_credits,
                     style=S.COMPUTED_BOLD)
    row = _money_row(ws, row, "Self-employment tax", b.self_employment_tax)
    row = _money_row(ws, row, "Additional Medicare tax", b.additional_medicare_tax)
    row = _money_row(ws, row, "Net investment income tax", b.net_investment_income_tax)
    row = _money_row(ws, row, "Nonrefundable credits", b.nonrefundable_credits)
    row = _money_row(ws, row, "Refundable credits", b.refundable_credits)
    row = _money_row(ws, row, "Total tax liability", b.total_tax_liability,
                     style=S.COMPUTED_BOLD)
    row = _money_row(ws, row, "Marginal rate", b.marginal_rate, fmt=NF.PCT2)
    row = _money_row(ws, row, "Effective rate", b.effective_rate, fmt=NF.PCT2)

    # -- recommendation ---------------------------------------------------
    row += 1
    row = K.section_header(ws, row, "Withholding recommendation", _LAST_COL)
    row = _money_row(ws, row, "Withholding to date (all jobs)", rec.ytd_withholding)
    row = _money_row(ws, row, "Projected withholding at current rate",
                     rec.projected_withholding_current_rate)
    row = _money_row(ws, row, "Other payments", rec.other_payments_total)
    row = _money_row(ws, row, "Projected total payments", rec.projected_total_payments)
    row = _money_row(ws, row, "Projected balance (+refund / -due)", rec.projected_balance,
                     style=S.COMPUTED_BOLD)
    row = _money_row(ws, row, "Target refund", rec.target_refund)
    row = _money_row(ws, row, "Recommended withholding per period",
                     rec.recommended_withholding_per_period, style=S.COMPUTED_BOLD)
    row = _money_row(ws, row, "Additional per period (W-4 line 4c)",
                     rec.additional_withholding_per_period, style=S.COMPUTED_BOLD,
                     basis=f"on {rec.adjusted_job_name or 'primary job'}, "
                           f"{rec.periods_remaining} periods left")
    if rec.safe_harbor_target is not None:
        row = _money_row(ws, row, "Estimated-tax safe-harbor target", rec.safe_harbor_target)
    if rec.safe_harbor_additional_per_period is not None:
        row = _money_row(ws, row, "Safe-harbor additional per period",
                         rec.safe_harbor_additional_per_period)
    row = _text_row(ws, row, "Over-withholding vs. target?",
                    "Yes — reduce" if rec.is_over_withholding else "No — on/under target")

    # -- cited tax-law basis ---------------------------------------------
    row += 1
    row = K.section_header(ws, row, "Tax-law basis (from the SATC crosswalk)", _LAST_COL)
    cw = CrosswalkLibrary().resolve(result.tax_year_used, "US")
    K.write(ws, row, 1, "Source", S.LABEL)
    K.write(ws, row, 3, cw.source_label or f"US {result.tax_year_used}", S.LABEL_MUTED)
    row += 1
    for label, param in (
        ("Standard deduction", "standard_deduction"),
        ("Ordinary brackets", "brackets_single"),
        ("Capital-gains thresholds", "ltcg_0_pct_max"),
        ("Net investment income tax", "niit_rate"),
        ("Self-employment tax", "se_social_security_rate"),
        ("Additional Medicare tax", "addl_medicare_rate"),
        ("Estimated-tax safe harbor", "est_tax_safe_harbor_pct_current"),
    ):
        citation = cw.param(param).citation
        if citation:
            K.write(ws, row, 1, label, S.LABEL)
            K.write(ws, row, 3, citation, S.LABEL_MUTED)
            row += 1

    # -- notes ------------------------------------------------------------
    if result.notes:
        row += 1
        row = K.section_header(ws, row, "Notes", _LAST_COL)
        for note in result.notes:
            row = K.note_row(ws, row, note, _LAST_COL)

    return wb
