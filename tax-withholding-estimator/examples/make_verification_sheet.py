"""Generate tax_verify_2025.xlsx — a step-by-step Excel verification of the
tax withholding estimator against 2025 IRS tables.

Run:
    python examples/make_verification_sheet.py

Opens (or creates) tax_verify_2025.xlsx in the current directory.
All yellow cells are user inputs. All blue cells are computed by Excel
formulas so you can change the inputs and watch everything update.

Compare the green "TWE Output" column against what `twe estimate` or
the web UI actually reports — they should match within $1 (rounding).
"""

from openpyxl import Workbook
from openpyxl.styles import (
    Alignment, Border, Font, PatternFill, Side,
)
from openpyxl.utils import get_column_letter
import os

OUT = os.path.join(os.path.dirname(__file__), "tax_verify_2025.xlsx")

# ── palette ──────────────────────────────────────────────────────────────────
HDR   = PatternFill("solid", fgColor="0F766E")   # teal header
INP   = PatternFill("solid", fgColor="FFFDE7")   # yellow input
CALC  = PatternFill("solid", fgColor="E3F2FD")   # blue calculated
RES   = PatternFill("solid", fgColor="E8F5E9")   # green result
WARN  = PatternFill("solid", fgColor="FFF3E0")   # orange info
WHITE = PatternFill("solid", fgColor="FFFFFF")
NONE  = PatternFill("none")

HDR_F  = Font(bold=True, color="FFFFFF", size=10)
LBL_F  = Font(bold=True, size=9)
NORM_F = Font(size=9)
SMALL  = Font(size=8, italic=True, color="546E7A")
NOTE_F = Font(size=8, color="546E7A")

THIN = Side(style="thin", color="B0BEC5")
MED  = Side(style="medium", color="0F766E")
BOX  = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
MED_BOX = Border(left=MED, right=MED, top=MED, bottom=MED)

USD  = '#,##0.00'
PCT  = '0.00%'
INT_ = '#,##0'


def _hdr(ws, row, label, span=3):
    ws.cell(row, 1, label).font = HDR_F
    ws.cell(row, 1).fill = HDR
    ws.cell(row, 1).alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.cell(row, 1).border = MED_BOX
    for c in range(2, span + 1):
        ws.cell(row, c).fill = HDR
        ws.cell(row, c).border = MED_BOX
    ws.row_dimensions[row].height = 16


def _row(ws, row, label, value=None, formula=None, fmt=USD,
         fill=None, note="", bold_label=False):
    lc = ws.cell(row, 1, label)
    lc.font = Font(bold=bold_label, size=9)
    lc.alignment = Alignment(indent=1, vertical="center")
    lc.border = BOX

    vc = ws.cell(row, 2)
    if formula:
        vc.value = formula
        vc.fill = fill or CALC
    elif value is not None:
        vc.value = value
        vc.fill = fill or INP
    else:
        vc.fill = fill or NONE
    vc.number_format = fmt
    vc.alignment = Alignment(horizontal="right", vertical="center")
    vc.border = BOX
    vc.font = NORM_F

    nc = ws.cell(row, 3, note)
    nc.font = NOTE_F
    nc.alignment = Alignment(vertical="center", wrap_text=True)
    nc.border = BOX

    ws.row_dimensions[row].height = 15
    return vc


EMPTY_BORDER = Border()

def _blank(ws, row):
    for c in range(1, 4):
        ws.cell(row, c).fill = WHITE
        ws.cell(row, c).border = EMPTY_BORDER
    ws.row_dimensions[row].height = 6


# ── named-cell helpers ───────────────────────────────────────────────────────
# We track cell addresses for formula references by name.
REF = {}

def _addr(cell):
    return f"$B${cell.row}"

def _reg(name, cell):
    REF[name] = _addr(cell)
    return cell


def build():
    wb = Workbook()
    ws = wb.active
    ws.title = "Verify 2025"

    ws.column_dimensions["A"].width = 36
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 48

    # freeze header rows
    ws.freeze_panes = "A5"

    # ── title ─────────────────────────────────────────────────────────────────
    ws.row_dimensions[1].height = 22
    t = ws.cell(1, 1, "Tax Withholding Estimator — 2025 Verification Sheet")
    t.font = Font(bold=True, size=13, color="0F766E")
    t.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.merge_cells("A1:C1")

    ws.row_dimensions[2].height = 13
    d = ws.cell(2, 1,
        "Yellow cells = user inputs.  Blue = Excel formula.  "
        "Green = final results.  Paste twe output in column D to compare.")
    d.font = Font(size=8, italic=True, color="546E7A")
    ws.merge_cells("A2:C2")

    ws.row_dimensions[3].height = 6

    # column D header
    ws.column_dimensions["D"].width = 16
    dh = ws.cell(4, 4, "TWE Output\n(paste here)")
    dh.font = Font(bold=True, size=9, color="0F766E")
    dh.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
    dh.fill = PatternFill("solid", fgColor="E0F7FA")
    ws.row_dimensions[4].height = 28

    r = 4  # current row counter

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1: INPUTS
    # ══════════════════════════════════════════════════════════════════════════
    r += 1; _hdr(ws, r, "① INPUTS  (pre-filled from examples/sample_input.json)", 4)

    r += 1; _hdr(ws, r, "  Filing & Year", 4)
    r += 1; _reg("filing",   _row(ws, r, "Filing status", "single",  fmt="@",
                                  note='single | married_jointly | married_separately | head_of_household'))
    r += 1; _reg("tax_year", _row(ws, r, "Tax year",      2025,       fmt=INT_))
    r += 1; _reg("std_ded",  _row(ws, r, "Standard deduction (2025 single)", 15000, fmt=USD,
                                  note="Update if using a different filing status or age-65/blind add-on"))

    r += 1; _blank(ws, r)
    r += 1; _hdr(ws, r, "  Paystub  (Job 1)", 4)
    r += 1; _reg("freq",      _row(ws, r, "Pay frequency",                   "biweekly", fmt="@",
                                   note="weekly=52  biweekly=26  semimonthly=24  monthly=12"))
    r += 1; _reg("ppy",       _row(ws, r, "Periods per year",                26,   fmt=INT_,
                                   note="biweekly = 26"))
    r += 1; _reg("taxable_pp",_row(ws, r, "Taxable wages this period ($)",   2950, fmt=USD,
                                   note="Box 1 equivalent on your stub"))
    r += 1; _reg("wh_pp",     _row(ws, r, "Federal tax withheld per period ($)", 410, fmt=USD))
    r += 1; _reg("remaining", _row(ws, r, "Pay periods remaining",           14,   fmt=INT_))
    r += 1; _reg("ytd_wages", _row(ws, r, "YTD taxable wages ($)",           35100,fmt=USD,
                                   note="Leave 0 to infer from per-period amount"))
    r += 1; _reg("ytd_wh",    _row(ws, r, "YTD federal tax withheld ($)",    4920, fmt=USD))

    r += 1; _blank(ws, r)
    r += 1; _hdr(ws, r, "  Other Income (annual)", 4)
    r += 1; _reg("interest",  _row(ws, r, "Interest income ($)",                  350,  fmt=USD))
    r += 1; _reg("ord_div",   _row(ws, r, "Ordinary dividends ($)",               800,  fmt=USD))
    r += 1; _reg("qual_div",  _row(ws, r, "Qualified dividends ($)",              600,  fmt=USD,
                                   note="Must be ≤ ordinary dividends; part of LTCG rate pool"))
    r += 1; _reg("ira_dist",  _row(ws, r, "Taxable IRA / retirement distributions ($)", 5000, fmt=USD))
    r += 1; _reg("ltcg",      _row(ws, r, "Long-term capital gains ($)",         2000,  fmt=USD))
    r += 1; _reg("stcg",      _row(ws, r, "Short-term capital gains ($)",        0,     fmt=USD))
    r += 1; _reg("se_net",    _row(ws, r, "Self-employment net income ($)",      0,     fmt=USD))
    r += 1; _reg("unemp",     _row(ws, r, "Unemployment compensation ($)",       0,     fmt=USD))
    r += 1; _reg("other_inc", _row(ws, r, "Other taxable income ($)",            0,     fmt=USD))
    r += 1; _reg("sp_wages",  _row(ws, r, "Spouse taxable wages ($)",           0,     fmt=USD))
    r += 1; _reg("sp_wh",     _row(ws, r, "Spouse federal tax withheld ($)",    0,     fmt=USD))

    r += 1; _blank(ws, r)
    r += 1; _hdr(ws, r, "  Adjustments (above-the-line)", 4)
    r += 1; _reg("ira_ded",   _row(ws, r, "Traditional IRA deduction ($)",  0,    fmt=USD))
    r += 1; _reg("hsa_ded",   _row(ws, r, "HSA deduction ($)",              2000, fmt=USD))
    r += 1; _reg("sl_int",    _row(ws, r, "Student loan interest ($)",      1200, fmt=USD))
    r += 1; _reg("other_adj", _row(ws, r, "Other adjustments ($)",          0,    fmt=USD))

    r += 1; _blank(ws, r)
    r += 1; _hdr(ws, r, "  Deductions & Credits", 4)
    r += 1; _reg("itemized",  _row(ws, r, "Itemized total ($, or 0 = use standard)", 0, fmt=USD,
                                   note="0 → uses standard deduction"))
    r += 1; _reg("ctc",       _row(ws, r, "Child Tax Credit ($)",           0, fmt=USD))
    r += 1; _reg("nr_cred",   _row(ws, r, "Other nonrefundable credits ($)",0, fmt=USD))
    r += 1; _reg("ref_cred",  _row(ws, r, "Refundable credits ($)",         0, fmt=USD))

    r += 1; _blank(ws, r)
    r += 1; _hdr(ws, r, "  Other Payments & Target", 4)
    r += 1; _reg("est_pay",   _row(ws, r, "Estimated tax payments ($)",     0, fmt=USD))
    r += 1; _reg("other_wh",  _row(ws, r, "Other withholding ($)",          0, fmt=USD))
    r += 1; _reg("target_ref",_row(ws, r, "Target refund ($, 0 = break even)", 0, fmt=USD))
    r += 1; _reg("py_tax",    _row(ws, r, "Prior-year tax ($)",           8200, fmt=USD,
                                   note="For safe-harbor calculation"))
    r += 1; _reg("py_agi",    _row(ws, r, "Prior-year AGI ($)",          71000, fmt=USD))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2: INCOME PROJECTION
    # ══════════════════════════════════════════════════════════════════════════
    r += 1; _blank(ws, r)
    r += 1; _hdr(ws, r, "② INCOME PROJECTION", 4)

    elapsed_formula = f"={REF['ppy']}-{REF['remaining']}"
    r += 1; _reg("elapsed", _row(ws, r, "Elapsed periods",
        formula=elapsed_formula, fmt=INT_, note="periods_per_year − remaining"))

    ytd_used = (f"=IF({REF['ytd_wages']}>0, {REF['ytd_wages']}, "
                f"{REF['taxable_pp']}*{REF['elapsed']})")
    r += 1; _reg("ytd_used", _row(ws, r, "YTD taxable wages used",
        formula=ytd_used, fmt=USD, note="From input if provided, else inferred"))

    proj_wages = f"={REF['ytd_used']}+{REF['taxable_pp']}*{REF['remaining']}"
    r += 1; _reg("proj_wages", _row(ws, r, "Projected taxable wages",
        formula=proj_wages, fmt=USD))

    ytd_wh_used = (f"=IF({REF['ytd_wh']}>0, {REF['ytd_wh']}, "
                   f"{REF['wh_pp']}*{REF['elapsed']})")
    r += 1; _reg("ytd_wh_used", _row(ws, r, "YTD withholding used",
        formula=ytd_wh_used, fmt=USD))

    proj_wh = f"={REF['ytd_wh_used']}+{REF['wh_pp']}*{REF['remaining']}"
    r += 1; _reg("proj_wh", _row(ws, r, "Projected total withholding (job 1)",
        formula=proj_wh, fmt=USD))

    total_income = (f"={REF['proj_wages']}+{REF['interest']}+{REF['ord_div']}"
                    f"+{REF['ira_dist']}+{REF['stcg']}+{REF['ltcg']}"
                    f"+{REF['se_net']}+{REF['unemp']}+{REF['other_inc']}"
                    f"+{REF['sp_wages']}")
    r += 1; _reg("total_income", _row(ws, r, "Total income",
        formula=total_income, fmt=USD))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3: AGI
    # ══════════════════════════════════════════════════════════════════════════
    r += 1; _blank(ws, r)
    r += 1; _hdr(ws, r, "③ ADJUSTMENTS → AGI", 4)

    # SE tax (simplified — full calc below)
    # half_se = se_net * 0.9235 * (0.124 + 0.029) / 2  (approx, ignores SS wage base)
    half_se_f = (f"=IF({REF['se_net']}<=0, 0, "
                 f"({REF['se_net']}*0.9235*(0.124+0.029))/2)")
    r += 1; _reg("half_se_approx", _row(ws, r, "One-half SE tax deduction",
        formula=half_se_f, fmt=USD,
        note="Approx — exact calc in SE Tax section below; use that value"))

    adj_total = (f"={REF['ira_ded']}+{REF['hsa_ded']}+{REF['sl_int']}"
                 f"+{REF['other_adj']}+{REF['half_se_approx']}")
    r += 1; _reg("adj_total", _row(ws, r, "Total adjustments",
        formula=adj_total, fmt=USD))

    agi_f = f"=MAX(0, {REF['total_income']}-{REF['adj_total']})"
    r += 1; _reg("agi", _row(ws, r, "Adjusted Gross Income (AGI)",
        formula=agi_f, fmt=USD, fill=RES, bold_label=True))
    ws.cell(r, 4).number_format = USD  # comparison column

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4: DEDUCTION → TAXABLE INCOME
    # ══════════════════════════════════════════════════════════════════════════
    r += 1; _blank(ws, r)
    r += 1; _hdr(ws, r, "④ DEDUCTION → TAXABLE INCOME", 4)

    deduction_f = (f"=IF({REF['itemized']}>{REF['std_ded']}, "
                   f"{REF['itemized']}, {REF['std_ded']})")
    r += 1; _reg("deduction", _row(ws, r, "Deduction used (larger of standard/itemized)",
        formula=deduction_f, fmt=USD,
        note="Standard = $15,000 for single 2025; update std_ded input for other status"))

    ti_f = f"=MAX(0, {REF['agi']}-{REF['deduction']})"
    r += 1; _reg("taxable_income", _row(ws, r, "Taxable Income",
        formula=ti_f, fmt=USD, fill=RES, bold_label=True))
    ws.cell(r, 4).number_format = USD

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 5: ORDINARY INCOME TAX (2025 Single brackets hardcoded)
    # ══════════════════════════════════════════════════════════════════════════
    r += 1; _blank(ws, r)
    r += 1; _hdr(ws, r, "⑤ ORDINARY INCOME TAX  (2025 Single brackets — update for other status)", 4)

    # Preferential income (LTCG + qualified dividends) is stacked on top.
    # Ordinary taxable income = taxable_income - min(ltcg+qual_div, taxable_income)
    pref_f = (f"=MIN(MAX(0,{REF['qual_div']}+{REF['ltcg']}), {REF['taxable_income']})")
    r += 1; _reg("preferential", _row(ws, r, "Preferential income (LTCG + qual. dividends)",
        formula=pref_f, fmt=USD, note="Taxed at 0/15/20% rates — subtracted from ordinary TI"))

    ord_ti_f = f"=MAX(0, {REF['taxable_income']}-{REF['preferential']})"
    r += 1; _reg("ord_ti", _row(ws, r, "Ordinary taxable income",
        formula=ord_ti_f, fmt=USD))

    # 2025 Single bracket tax using IFS
    # Cumulative tax at each threshold:
    #   11,925 → 1,192.50
    #   48,475 → 5,578.50
    #  103,350 → 17,651.00
    #  197,300 → 40,199.00
    #  250,525 → 57,231.00
    #  626,350 → 188,769.75
    oti = REF['ord_ti']
    bracket_tax = (
        f"=IFS("
        f"{oti}<=0, 0, "
        f"{oti}<=11925, {oti}*0.10, "
        f"{oti}<=48475, 1192.50+({oti}-11925)*0.12, "
        f"{oti}<=103350, 5578.50+({oti}-48475)*0.22, "
        f"{oti}<=197300, 17651.00+({oti}-103350)*0.24, "
        f"{oti}<=250525, 40199.00+({oti}-197300)*0.32, "
        f"{oti}<=626350, 57231.00+({oti}-250525)*0.35, "
        f"TRUE, 188769.75+({oti}-626350)*0.37)"
    )
    r += 1; _reg("ord_tax", _row(ws, r, "Ordinary income tax",
        formula=bracket_tax, fmt=USD,
        note="IFS brackets: 10/12/22/24/32/35/37%  (2025 single)"))

    # Marginal rate
    marg_f = (
        f"=IFS("
        f"{oti}<=0, 0.10, "
        f"{oti}<=11925, 0.10, "
        f"{oti}<=48475, 0.12, "
        f"{oti}<=103350, 0.22, "
        f"{oti}<=197300, 0.24, "
        f"{oti}<=250525, 0.32, "
        f"{oti}<=626350, 0.35, "
        f"TRUE, 0.37)"
    )
    r += 1; _reg("marginal", _row(ws, r, "Marginal rate", formula=marg_f, fmt=PCT))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 6: CAPITAL GAINS TAX  (2025 single: 0% ≤ 48,350 / 15% ≤ 533,400 / 20%)
    # ══════════════════════════════════════════════════════════════════════════
    r += 1; _blank(ws, r)
    r += 1; _hdr(ws, r, "⑥ CAPITAL GAINS TAX  (2025 Single — 0/15/20% stacked on ordinary TI)", 4)

    # zero_room = MAX(0, 48350 - ord_ti)
    zroom_f = f"=MAX(0, 48350-{REF['ord_ti']})"
    r += 1; _reg("zero_room", _row(ws, r, "Room in 0% bracket",
        formula=zroom_f, fmt=USD, note="2025 single 0% LTCG threshold: $48,350"))

    # zero_amount = MIN(preferential, zero_room)
    zamount_f = f"=MIN({REF['preferential']}, {REF['zero_room']})"
    r += 1; _reg("zero_amount", _row(ws, r, "Amount taxed at 0%",
        formula=zamount_f, fmt=USD))

    # remaining after 0%
    cg_rem1_f = f"=MAX(0, {REF['preferential']}-{REF['zero_amount']})"
    r += 1; _reg("cg_rem1", _row(ws, r, "Preferential income above 0% threshold",
        formula=cg_rem1_f, fmt=USD))

    # fifteen_start = MAX(ord_ti, 48350)
    # fifteen_room = MAX(0, 533400 - fifteen_start)
    froom_f = f"=MAX(0, 533400-MAX({REF['ord_ti']}, 48350))"
    r += 1; _reg("fifteen_room", _row(ws, r, "Room in 15% bracket",
        formula=froom_f, fmt=USD, note="2025 single 15% LTCG threshold: $533,400"))

    famount_f = f"=MIN({REF['cg_rem1']}, {REF['fifteen_room']})"
    r += 1; _reg("fifteen_amount", _row(ws, r, "Amount taxed at 15%",
        formula=famount_f, fmt=USD))

    twenty_f = f"=MAX(0, {REF['cg_rem1']}-{REF['fifteen_amount']})"
    r += 1; _reg("twenty_amount", _row(ws, r, "Amount taxed at 20%",
        formula=twenty_f, fmt=USD))

    cg_tax_f = f"={REF['fifteen_amount']}*0.15+{REF['twenty_amount']}*0.20"
    r += 1; _reg("cg_tax", _row(ws, r, "Capital gains tax",
        formula=cg_tax_f, fmt=USD))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 7: SELF-EMPLOYMENT TAX
    # ══════════════════════════════════════════════════════════════════════════
    r += 1; _blank(ws, r)
    r += 1; _hdr(ws, r, "⑦ SELF-EMPLOYMENT TAX  (if applicable)", 4)

    se_base_f = f"=IF({REF['se_net']}<=0, 0, {REF['se_net']}*0.9235)"
    r += 1; _reg("se_base", _row(ws, r, "SE net earnings (×0.9235)",
        formula=se_base_f, fmt=USD))

    # SS wage base 2025 = 176,100; subject to SS portion = wages + SE base, capped
    ss_room_f = f"=MAX(0, 176100-{REF['proj_wages']}-{REF['sp_wages']})"
    r += 1; _reg("ss_room", _row(ws, r, "SS wage base room (2025: $176,100)",
        formula=ss_room_f, fmt=USD))

    ss_taxable_f = f"=MIN({REF['se_base']}, {REF['ss_room']})"
    r += 1; _reg("ss_taxable_se", _row(ws, r, "SE income subject to SS",
        formula=ss_taxable_f, fmt=USD))

    se_tax_f = (f"=IF({REF['se_net']}<=0, 0, "
                f"{REF['ss_taxable_se']}*0.124 + {REF['se_base']}*0.029)")
    r += 1; _reg("se_tax", _row(ws, r, "Self-employment tax (SS 12.4% + Medicare 2.9%)",
        formula=se_tax_f, fmt=USD))

    half_se_exact_f = f"={REF['se_tax']}/2"
    r += 1; _reg("half_se_exact", _row(ws, r, "One-half SE tax (above-the-line deduction)",
        formula=half_se_exact_f, fmt=USD,
        note="This is the exact value; the approximation above in Section ③ is close but update AGI if SE income is large"))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 8: ADDITIONAL MEDICARE TAX & NIIT
    # ══════════════════════════════════════════════════════════════════════════
    r += 1; _blank(ws, r)
    r += 1; _hdr(ws, r, "⑧ ADDITIONAL MEDICARE TAX & NIIT", 4)

    # AMT 0.9% — single threshold $200,000
    amt_base_f = f"={REF['proj_wages']}+{REF['sp_wages']}+{REF['se_base']}"
    r += 1; _reg("amt_base", _row(ws, r, "Medicare wages (wages + spouse wages + SE base)",
        formula=amt_base_f, fmt=USD))

    amt_f = f"=MAX(0, {REF['amt_base']}-200000)*0.009"
    r += 1; _reg("add_medicare", _row(ws, r, "Additional Medicare Tax (0.9% over $200K single)",
        formula=amt_f, fmt=USD))

    # NIIT 3.8% — single threshold $200,000
    inv_income_f = (f"=MAX(0, {REF['interest']}+{REF['ord_div']}"
                    f"+{REF['stcg']}+{REF['ltcg']})")
    r += 1; _reg("inv_income", _row(ws, r, "Net investment income",
        formula=inv_income_f, fmt=USD))

    niit_f = f"=MIN({REF['inv_income']}, MAX(0,{REF['agi']}-200000))*0.038"
    r += 1; _reg("niit", _row(ws, r, "Net Investment Income Tax (3.8% over $200K single)",
        formula=niit_f, fmt=USD))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 9: TOTAL LIABILITY
    # ══════════════════════════════════════════════════════════════════════════
    r += 1; _blank(ws, r)
    r += 1; _hdr(ws, r, "⑨ TAX LIABILITY", 4)

    inc_tax_f = f"={REF['ord_tax']}+{REF['cg_tax']}"
    r += 1; _reg("inc_tax", _row(ws, r, "Income tax before credits",
        formula=inc_tax_f, fmt=USD))

    tax_bc_f = f"={REF['inc_tax']}+{REF['se_tax']}+{REF['add_medicare']}+{REF['niit']}"
    r += 1; _reg("tax_before_credits", _row(ws, r, "Tax before credits",
        formula=tax_bc_f, fmt=USD))

    nr_credits_f = f"=MIN({REF['ctc']}+{REF['nr_cred']}, {REF['tax_before_credits']})"
    r += 1; _reg("nr_credits", _row(ws, r, "Nonrefundable credits applied",
        formula=nr_credits_f, fmt=USD))

    total_liability_f = (f"=MAX(0, {REF['tax_before_credits']}"
                         f"-{REF['nr_credits']}-{REF['ref_cred']})")
    r += 1; _reg("total_liability", _row(ws, r, "TOTAL TAX LIABILITY",
        formula=total_liability_f, fmt=USD, fill=RES, bold_label=True))
    ws.cell(r, 4).number_format = USD

    eff_f = f"=IF({REF['agi']}>0, {REF['total_liability']}/{REF['agi']}, 0)"
    r += 1; _reg("eff_rate", _row(ws, r, "Effective rate", formula=eff_f, fmt=PCT))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 10: WITHHOLDING RECOMMENDATION
    # ══════════════════════════════════════════════════════════════════════════
    r += 1; _blank(ws, r)
    r += 1; _hdr(ws, r, "⑩ WITHHOLDING RECOMMENDATION", 4)

    other_pay_f = f"={REF['est_pay']}+{REF['other_wh']}+{REF['sp_wh']}"
    r += 1; _reg("other_pay", _row(ws, r, "Other payments (estimated tax + other withholding)",
        formula=other_pay_f, fmt=USD))

    already_secured_f = f"={REF['ytd_wh_used']}+{REF['other_pay']}"
    r += 1; _reg("already_secured", _row(ws, r, "Already secured (YTD withholding + other payments)",
        formula=already_secured_f, fmt=USD))

    others_future_f = "=0"  # single job scenario
    r += 1; _reg("others_future", _row(ws, r, "Future withholding from OTHER jobs",
        formula=others_future_f, fmt=USD, note="0 for single-job; add other jobs' remaining withholding here"))

    req_remaining_f = (f"=MAX(0, ({REF['total_liability']}+{REF['target_ref']})"
                       f"-{REF['already_secured']}-{REF['others_future']})")
    r += 1; _reg("req_remaining", _row(ws, r, "Required from remaining paychecks",
        formula=req_remaining_f, fmt=USD))

    rec_pp_f = (f"=IF({REF['remaining']}>0, "
                f"{REF['req_remaining']}/{REF['remaining']}, 0)")
    r += 1; _reg("rec_pp", _row(ws, r, "Recommended withholding per paycheck",
        formula=rec_pp_f, fmt=USD, fill=RES, bold_label=True))
    ws.cell(r, 4).number_format = USD

    add_pp_f = f"=MAX(0, {REF['rec_pp']}-{REF['wh_pp']})"
    r += 1; _reg("add_pp", _row(ws, r, "Additional withholding per paycheck (W-4 line 4c)",
        formula=add_pp_f, fmt=USD, fill=RES, bold_label=True))
    ws.cell(r, 4).number_format = USD

    proj_balance_f = (f"={REF['proj_wh']}+{REF['other_pay']}-{REF['total_liability']}")
    r += 1; _reg("proj_balance", _row(ws, r, "Projected refund (+) / owe (−) at current rate",
        formula=proj_balance_f, fmt=USD, fill=RES))
    ws.cell(r, 4).number_format = USD

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 11: SAFE HARBOR
    # ══════════════════════════════════════════════════════════════════════════
    r += 1; _blank(ws, r)
    r += 1; _hdr(ws, r, "⑪ SAFE HARBOR  (penalty avoidance)", 4)

    sh_current_f = f"={REF['total_liability']}*0.90"
    r += 1; _reg("sh_current", _row(ws, r, "90% of current-year liability",
        formula=sh_current_f, fmt=USD))

    # Prior-year: 100% if AGI ≤ 150K, else 110%
    sh_prior_f = (f"=IF({REF['py_agi']}>150000, "
                  f"{REF['py_tax']}*1.10, {REF['py_tax']}*1.00)")
    r += 1; _reg("sh_prior", _row(ws, r, "100% (or 110%) of prior-year tax",
        formula=sh_prior_f, fmt=USD, note="110% applies if prior-year AGI > $150,000"))

    sh_target_f = f"=MIN({REF['sh_current']}, {REF['sh_prior']})"
    r += 1; _reg("sh_target", _row(ws, r, "Safe-harbor target (lesser of the two)",
        formula=sh_target_f, fmt=USD))

    sh_add_pp_f = (f"=MAX(0, ({REF['sh_target']}-{REF['already_secured']}"
                   f"-{REF['others_future']})/{REF['remaining']})")
    r += 1; _reg("sh_add_pp", _row(ws, r, "Safe-harbor additional per paycheck",
        formula=sh_add_pp_f, fmt=USD, fill=RES))
    ws.cell(r, 4).number_format = USD

    # ══════════════════════════════════════════════════════════════════════════
    # Comparison column D header rows (already set above at row 4 header)
    # ══════════════════════════════════════════════════════════════════════════
    r += 1; _blank(ws, r)
    r += 1
    ws.row_dimensions[r].height = 40
    msg = ws.cell(r, 1,
        "COMPARISON: paste the values from `twe estimate` output (or the web UI) "
        "into column D on the matching rows above. Differences > $1 indicate a "
        "discrepancy to investigate.")
    msg.font = Font(size=9, italic=True, color="546E7A")
    msg.fill = WARN
    ws.merge_cells(f"A{r}:D{r}")
    msg.alignment = Alignment(wrap_text=True, vertical="center", indent=1)

    wb.save(OUT)
    print(f"Saved: {OUT}")


if __name__ == "__main__":
    build()
