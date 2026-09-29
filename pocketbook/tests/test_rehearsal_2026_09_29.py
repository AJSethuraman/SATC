"""Defects found running PocketBook on public loan data (docs/rehearsal-public-data-2026-09.md), each held here on a
tiny synthetic book: no public row is read.

1. A category limit the launcher's list doesn't offer (Choices(many_values=60): State has 51 values and a blank, one
   over the usual 50) was written into Control's pick cell, where only a listed option is read. The Run then
   refused "60 is not an option" on a row the analyst can't edit (it is the launcher's), after Set up had already
   used 60; and reading the block back (Set up again, the launcher) quietly took the usual 50 instead.
"""

from openpyxl import load_workbook

from pocketbook import book, choices as ch, control, synth
from test_book import PICK


def _limits_book(tmp_path, **limits):
    extract = synth.write_extract(tmp_path, n=2000)
    c = ch.Choices(run_kind=ch.BLEED, bands=("FICO",), segments=("CHANNEL",), **limits)
    out = book.set_up(extract, choices=c)
    assert out.ok, out.lines
    return out.book


def _answer(b):
    wb = load_workbook(b)
    for r in wb[control.SHEET].iter_rows(min_row=control.FIRST_ROW):
        k = r[control.KEY_COL - 1].value
        if k in PICK:
            r[control.CHOOSE_COL - 1].value = PICK[k]
    wb["Columns"][book.CONFIRM_CELL] = "Yes"
    wb.save(b)


def test_a_limit_off_the_launchers_list_is_read_back_as_chosen(tmp_path):
    b = _limits_book(tmp_path, few_values=3, many_values=60)
    got, _ = control.read_choices(load_workbook(b)[control.SHEET])
    assert (got.few_values, got.many_values) == (3, 60)


def test_a_limit_off_the_launchers_list_runs(tmp_path):
    b = _limits_book(tmp_path, many_values=60)
    _answer(b)
    _, problems, _ = book.read_book(b)
    assert not [p for p in problems if "not an option" in p], problems
    ran = book.run(b)
    assert ran.ok, ran.lines


def test_a_listed_limit_is_still_picked_from_the_list(tmp_path):
    b = _limits_book(tmp_path, few_values=24, many_values=100)
    ws = load_workbook(b)[control.SHEET]
    row = {k: control.row_of(ws, k) for k in ("few_values", "many_values")}
    assert ws.cell(row=row["few_values"], column=control.CHOOSE_COL).value == "24 values"
    assert ws.cell(row=row["many_values"], column=control.CHOOSE_COL).value == "100 values"
    assert ws.cell(row=row["many_values"], column=control.OWN_COL).value is None
