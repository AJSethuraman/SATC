"""Practice-management dashboards (live formulas over the data mart & repository).

Pipeline, deadlines & extensions, missing documents, engagement & fees,
year-over-year, and reconciliation status. Counts are Excel COUNTIFS/SUMIFS
against the Data Mart and Document Repository ranges, so the dashboard updates
when the underlying records change — nothing is hardcoded.
"""

from __future__ import annotations

from openpyxl.worksheet.worksheet import Worksheet

from satc.workbook import components as X
from satc.workbook import styles as S
from satc.workbook.styles import NF

_STATUSES = ["Awaiting docs", "In prep", "In review", "Ready to file", "Filed", "Accepted"]
_TYPES = ["1040", "1120S", "1065", "1120"]
# Original / extended federal due dates by return type (month, day).
_DUE = {"1040": (4, 15), "1120": (4, 15), "1120S": (3, 15), "1065": (3, 15)}
_EXT = {"1040": (10, 15), "1120": (10, 15), "1120S": (9, 15), "1065": (9, 15)}


def _rng(sheet: str, col: str, first: int, last: int) -> str:
    return f"'{sheet}'!${col}${first}:${col}${last}"


def build_dashboards_sheet(ws: Worksheet, *, mart_ranges: dict, repo_ranges: dict,
                           tax_year: int) -> None:
    S.paper_canvas(ws, max_col=10, max_row=90)
    X.set_widths(ws, {"A": 2, "B": 24, "C": 12, "D": 12, "E": 12, "F": 12, "G": 12, "H": 14})
    X.merge_text(ws, 1, 2, 9, "Practice Dashboards", S.TITLE)
    X.merge_text(ws, 2, 2, 9,
                 f"Live counts over the data mart & repository · filing season TY{tax_year} · "
                 "deadlines for the following calendar year.", S.SUBTITLE)

    rr = mart_ranges["returns"]
    ms = mart_ranges["sheet"]
    eng = mart_ranges["engagements"]
    type_r = _rng(ms, rr["type"], rr["first"], rr["last"])
    status_r = _rng(ms, rr["status"], rr["first"], rr["last"])
    year_r = _rng(ms, rr["year"], rr["first"], rr["last"])
    fee_r = _rng(ms, eng["fee"], eng["first"], eng["last"])
    paid_r = _rng(ms, eng["paid"], eng["first"], eng["last"])
    inv_r = _rng(ms, eng["invoiced"], eng["first"], eng["last"])
    letter_r = _rng(ms, eng["letter"], eng["first"], eng["last"])
    repo_status_r = _rng(repo_ranges["sheet"], repo_ranges["status"],
                         repo_ranges["first"], repo_ranges["last"])

    row = 4
    # -- Pipeline matrix: status x return type ----------------------------
    row = X.section_header(ws, row, "Pipeline — returns by status × type", 9, first_col=2)
    row = X.column_headers(ws, row, ["", "status"] + _TYPES + ["Total"], start_col=1)
    for status in _STATUSES:
        X.write(ws, row, 2, status, S.LABEL)
        for i, rt in enumerate(_TYPES):
            X.write(ws, row, 3 + i,
                    f'=COUNTIFS({type_r},"{rt}",{status_r},"{status}")', S.COMPUTED, number_format=NF.NUM)
        X.write(ws, row, 3 + len(_TYPES), f'=COUNTIF({status_r},"{status}")',
                S.COMPUTED_BOLD, number_format=NF.NUM)
        row += 1
    X.write(ws, row, 2, "Total", S.LABEL)
    for i, rt in enumerate(_TYPES):
        X.write(ws, row, 3 + i, f'=COUNTIF({type_r},"{rt}")', S.COMPUTED_BOLD, number_format=NF.NUM)
    X.write(ws, row, 3 + len(_TYPES),
            f'=COUNTA({_rng(ms, rr["type"], rr["first"], rr["last"])})', S.COMPUTED_BOLD, number_format=NF.NUM)
    row += 2

    # -- Deadlines & extensions -------------------------------------------
    row = X.section_header(ws, row, "Deadlines & extensions (aging)", 9, first_col=2)
    row = X.column_headers(ws, row, ["", "return type", "original due", "extended due",
                                     "days to due", "open (not filed)"], start_col=1)
    for rt in _TYPES:
        m, d = _DUE[rt]
        em, ed = _EXT[rt]
        X.write(ws, row, 2, rt, S.LABEL)
        X.write(ws, row, 3, f"=DATE({tax_year + 1},{m},{d})", S.COMPUTED, number_format=NF.DATE)
        X.write(ws, row, 4, f"=DATE({tax_year + 1},{em},{ed})", S.COMPUTED, number_format=NF.DATE)
        X.write(ws, row, 5, f"=DATE({tax_year + 1},{m},{d})-TODAY()", S.COMPUTED, number_format=NF.NUM)
        X.write(ws, row, 6,
                f'=COUNTIFS({type_r},"{rt}",{status_r},"<>Filed",{status_r},"<>Accepted")',
                S.COMPUTED, number_format=NF.NUM)
        row += 1
    row += 1

    # -- Missing documents & reconciliation -------------------------------
    row = X.section_header(ws, row, "Open items", 9, first_col=2)
    pairs = [
        ("Outstanding document requests", f'=COUNTIF({repo_status_r},"Requested")', NF.NUM),
        ("Returns in review / in prep (recon outstanding)",
         f'=COUNTIF({status_r},"In review")+COUNTIF({status_r},"In prep")', NF.NUM),
        ("Returns filed or accepted", f'=COUNTIF({status_r},"Filed")+COUNTIF({status_r},"Accepted")', NF.NUM),
    ]
    for label, formula, fmt in pairs:
        X.write(ws, row, 2, label, S.LABEL)
        X.write(ws, row, 5, formula, S.COMPUTED, number_format=fmt)
        row += 1
    row += 1

    # -- Engagement & fees ------------------------------------------------
    row = X.section_header(ws, row, "Engagement & fees", 9, first_col=2)
    fee_pairs = [
        ("Total fees (book)", f"=SUM({fee_r})", NF.USD),
        ("Engagement letters signed", f'=COUNTIF({letter_r},"Signed")', NF.NUM),
        ("Invoiced", f'=COUNTIF({inv_r},"Yes")', NF.NUM),
        ("Paid", f'=COUNTIF({paid_r},"Yes")', NF.NUM),
        ("Unpaid fees ($)", f'=SUMIFS({fee_r},{paid_r},"No")', NF.USD),
    ]
    for label, formula, fmt in fee_pairs:
        X.write(ws, row, 2, label, S.LABEL)
        X.write(ws, row, 5, formula, S.COMPUTED, number_format=fmt)
        row += 1
    row += 1

    # -- Year over year ---------------------------------------------------
    row = X.section_header(ws, row, "Year over year", 9, first_col=2)
    row = X.column_headers(ws, row, ["", "metric", str(tax_year - 1), str(tax_year)], start_col=1)
    X.write(ws, row, 2, "Returns on file", S.LABEL)
    X.write(ws, row, 3, f"=COUNTIF({year_r},{tax_year - 1})", S.COMPUTED, number_format=NF.NUM)
    X.write(ws, row, 4, f"=COUNTIF({year_r},{tax_year})", S.COMPUTED, number_format=NF.NUM)
    row += 1

    X.page_setup(ws, "Dashboards", orientation="portrait")
