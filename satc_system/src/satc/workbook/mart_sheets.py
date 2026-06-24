"""Workbook views of the client data mart, comparison, and proforma.

These render the normalized, de-identified tables as flat grids — the same shape
they take in SQL — so the workbook is a faithful, queryable mirror of the mart:
no PII, stable keys, one row per record.
"""

from __future__ import annotations

from decimal import Decimal

from openpyxl.worksheet.worksheet import Worksheet

from satc.models.mart import DataMart
from satc.proforma.comparison import VarianceRow
from satc.proforma.rollforward import ProformaSeed
from satc.workbook import components as X
from satc.workbook import styles as S
from satc.workbook.styles import NF


def _num(x) -> float | None:
    return float(x) if isinstance(x, (int, float, Decimal)) else None


def _table(ws: Worksheet, row: int, title: str, headers: list[str], rows: list[list],
           formats: list[str] | None = None, last_col_for_header: int = 12):
    """Render a flat table. Returns (next_row, first_data_row, last_data_row)."""
    row = X.section_header(ws, row, title, last_col_for_header, first_col=2)
    row = X.column_headers(ws, row, [""] + headers, start_col=1)
    first_data = row
    for data in rows:
        for i, val in enumerate(data):
            fmt = (formats[i] if formats and i < len(formats) else None)
            style = S.COMPUTED if fmt in (NF.USD, NF.NUM) else S.LABEL
            X.write(ws, row, 2 + i, val, style, number_format=fmt)
        row += 1
    last_data = row - 1
    return row + 1, first_data, last_data


def build_data_mart_sheet(ws: Worksheet, mart: DataMart) -> dict[str, dict]:
    """Build the data mart sheet. Returns table ranges for live dashboard formulas."""
    S.paper_canvas(ws, max_col=13, max_row=140)
    X.set_widths(ws, {"A": 2, "B": 26, "C": 12, "D": 8, "E": 9, "F": 14,
                      "G": 12, "H": 14, "I": 13, "J": 13, "K": 13, "L": 12})
    X.merge_text(ws, 1, 2, 12, "Client Data Mart — normalized, year over year", S.TITLE)
    X.merge_text(ws, 2, 2, 12,
                 "De-identified · keyed by client_id + tax_year + return_type + jurisdiction · "
                 "ports to SQL with no restructuring. No PII; documents referenced by id/link.",
                 S.SUBTITLE)
    row = 4
    ranges: dict[str, dict] = {}

    row, f, l = _table(ws, row, "Return register", [
        "client_id", "year", "type", "juris", "status", "residency", "refund", "balance due"],
        [[r.client_id, r.tax_year, r.return_type, r.jurisdiction, r.status, r.residency,
          _num(r.refund_amount), _num(r.balance_due_amount)] for r in mart.returns],
        formats=[NF.TEXT, NF.YEAR, NF.TEXT, NF.TEXT, NF.TEXT, NF.TEXT, NF.USD, NF.USD])
    # Columns: B=client C=year D=type E=juris F=status G=residency H=refund I=balance
    ranges["returns"] = {"first": f, "last": l,
                         "year": "C", "type": "D", "status": "F", "refund": "H", "balance": "I"}

    row, f, l = _table(ws, row, "Line items (record-level, every field queryable)", [
        "client/year", "schedule", "line", "label", "amount", "source"],
        [[li.return_key.split("|")[0] + " " + li.return_key.split("|")[1], li.schedule,
          li.line_code, li.label, _num(li.amount),
          li.provenance.short_source() if li.provenance else ""] for li in mart.line_items],
        formats=[NF.TEXT, NF.TEXT, NF.TEXT, NF.TEXT, NF.USD, NF.TEXT])

    row, f, l = _table(ws, row, "Carryforward register (carried year to year)", [
        "client_id", "kind", "yr gen", "juris", "amount", "expires after", "applied"],
        [[c.client_id, c.kind, c.tax_year_generated, c.jurisdiction, _num(c.amount),
          c.expires_after_year or "—", c.applied_to_year or "open"] for c in mart.carryforwards],
        formats=[NF.TEXT, NF.TEXT, NF.YEAR, NF.TEXT, NF.USD, NF.TEXT, NF.TEXT])

    row, f, l = _table(ws, row, "Per-owner basis / capital rollforward", [
        "client_id", "owner", "year", "begin", "+contrib", "+income", "-dist", "-loss", "ending"],
        [[b.client_id, b.owner_id, b.tax_year, _num(b.beginning_balance), _num(b.contributions),
          _num(b.income_items), _num(b.distributions), _num(b.loss_items), _num(b.ending_balance)]
         for b in mart.owner_basis],
        formats=[NF.TEXT, NF.TEXT, NF.YEAR, NF.USD, NF.USD, NF.USD, NF.USD, NF.USD, NF.USD])

    row, f, l = _table(ws, row, "Estimated-payment history", [
        "client_id", "year", "juris", "period", "amount"],
        [[p.client_id, p.tax_year, p.jurisdiction, p.period, _num(p.amount)]
         for p in mart.estimate_payments],
        formats=[NF.TEXT, NF.YEAR, NF.TEXT, NF.TEXT, NF.USD])

    row, f, l = _table(ws, row, "Engagement & fees", [
        "client_id", "year", "letter", "fee", "invoiced", "paid"],
        [[e.client_id, e.tax_year, e.engagement_letter_status, _num(e.fee_amount),
          "Yes" if e.invoiced else "No", "Yes" if e.paid else "No"] for e in mart.engagements],
        formats=[NF.TEXT, NF.YEAR, NF.TEXT, NF.USD, NF.TEXT, NF.TEXT])
    # Columns: B=client C=year D=letter E=fee F=invoiced G=paid
    ranges["engagements"] = {"first": f, "last": l,
                             "year": "C", "letter": "D", "fee": "E", "invoiced": "F", "paid": "G"}

    X.page_setup(ws, "Client Data Mart", orientation="landscape")
    X.freeze(ws, "A4")
    ranges["sheet"] = ws.title
    return ranges


def build_comparison_sheet(ws: Worksheet, rows: list[VarianceRow], *, title: str) -> None:
    S.paper_canvas(ws, max_col=9, max_row=max(50, len(rows) + 15))
    X.set_widths(ws, {"A": 2, "B": 14, "C": 12, "D": 30, "E": 13, "F": 13, "G": 13, "H": 9, "I": 34})
    X.merge_text(ws, 1, 2, 9, "Prior-vs-Current Comparison", S.TITLE)
    X.merge_text(ws, 2, 2, 9, title, S.SUBTITLE)
    row = 4
    row = X.column_headers(ws, row, [
        "", "schedule", "line", "label", "prior", "current", "Δ", "Δ%", "flag"], start_col=1)
    X.freeze(ws, "A" + str(row))
    for r in rows:
        X.write(ws, row, 2, r.schedule, S.LABEL_MUTED)
        X.write(ws, row, 3, r.line_code, S.LABEL_MUTED)
        X.write(ws, row, 4, r.label, S.LABEL)
        X.write(ws, row, 5, _num(r.prior), S.COMPUTED, number_format=NF.NUM)
        X.write(ws, row, 6, _num(r.current), S.COMPUTED, number_format=NF.NUM)
        X.write(ws, row, 7, _num(r.delta), S.COMPUTED, number_format=NF.NUM)
        X.write(ws, row, 8, r.pct, S.COMPUTED, number_format=NF.PCT1)
        X.write(ws, row, 9, r.flag or "—", S.EXCEPTION if r.severity == "flag" else S.NOTE)
        row += 1
    X.page_setup(ws, "Prior-vs-Current", orientation="landscape")


def build_proforma_sheet(ws: Worksheet, seeds: dict[str, ProformaSeed], *, to_year: int) -> None:
    S.paper_canvas(ws, max_col=9, max_row=80)
    X.set_widths(ws, {"A": 2, "B": 16, "C": 26, "D": 12, "E": 9, "F": 13, "G": 13, "H": 13})
    X.merge_text(ws, 1, 2, 8, f"Proforma — seed for tax year {to_year}", S.TITLE)
    X.merge_text(ws, 2, 2, 8,
                 "Standing data and open carryforwards carried from the data mart into next year. "
                 "Drake recomputes; the mart seeds so nothing is re-keyed.", S.SUBTITLE)
    row = 4
    row = X.section_header(ws, row, "Carryforwards carried into next year", 8, first_col=2)
    row = X.column_headers(ws, row, ["", "client_id", "kind", "yr gen", "juris", "amount"], start_col=1)
    for seed in seeds.values():
        for cf in seed.carryforwards:
            X.write(ws, row, 2, cf.client_id, S.LABEL)
            X.write(ws, row, 3, cf.kind, S.CARRYFORWARD)
            X.write(ws, row, 4, cf.tax_year_generated, S.LABEL_MUTED, number_format=NF.YEAR)
            X.write(ws, row, 5, cf.jurisdiction, S.LABEL_MUTED)
            X.write(ws, row, 6, _num(cf.amount), S.CARRYFORWARD, number_format=NF.USD)
            row += 1
    row += 1
    row = X.section_header(ws, row, "Per-owner basis / capital opening balances", 8, first_col=2)
    row = X.column_headers(ws, row, ["", "client_id", "owner", "year", "beginning basis"], start_col=1)
    for seed in seeds.values():
        for ob in seed.owner_basis_beginning:
            X.write(ws, row, 2, ob.client_id, S.LABEL)
            X.write(ws, row, 3, ob.owner_id, S.LABEL_MUTED)
            X.write(ws, row, 4, ob.tax_year, S.LABEL_MUTED, number_format=NF.YEAR)
            X.write(ws, row, 5, _num(ob.beginning_balance), S.CARRYFORWARD, number_format=NF.USD)
            row += 1
    X.page_setup(ws, "Proforma", orientation="landscape")
