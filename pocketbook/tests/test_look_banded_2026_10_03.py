"""Look draws the band columns and the split only, and a Run draws it again when they change.

The firm, 3 Oct 2026, shown the Look tab of a 47-column book at 40 blocks on 22 pages against 4 blocks on 4 pages,
chose "Banded + split, redraw on Run": Look has a block for each band column chosen in the launcher and for the
split column, and when the band columns change on Control the next Run draws Look again to match. A Run that
changes nothing draws nothing. Columns still lists every column, and nothing in the workbook or in what Set up says
points at a block Look no longer has. None of these needs a display or LibreOffice.
"""

import re

import pytest
from openpyxl import load_workbook
from openpyxl.chart import ScatterChart

from pocketbook import book, choices as ch, launcher, look, perm, synth
from pocketbook.ingest import read_table
from test_book import _answer
from test_book_dates import _choose, _control

#: the synthetic extract's columns, and those Set up finds are numbers (each could have a block)
NUMBERS = ["FICO", "ORIG_BAL", "GCO_AMT", "RANR_AMT", "REV_DEBT"]
MARK = "AA1"                       # a cell no block uses: a Look drawn again has it blank


@pytest.fixture(autouse=True)
def _quiet(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher, "open_file", lambda p: None)
    monkeypatch.setenv("POCKETBOOK_MEMORY", str(tmp_path / "memory.yaml"))
    monkeypatch.setattr(perm, "SHUFFLES", 200)


def _set_up(tmp_path, n=2000, **chosen):
    x = synth.write_extract(tmp_path, n=n)
    got = dict(run_kind=ch.BLEED, segments=("CHANNEL",))
    got.update(chosen)
    return x, book.set_up(x, choices=ch.Choices(**got))


def _block_names(ws) -> list[str]:
    """The columns Look has a block for, read off the tab: each block's heading in B, in order."""
    out, r = [], look.FIRST
    while ws.cell(row=r + look.R_LOANS, column=look.STATS_COL).value == "Loans":
        out.append(ws.cell(row=r, column=look.STATS_COL).value)
        r += look.BLOCK
    return out


def _lines(ws, name) -> dict:
    r = look.FIRST + look.BLOCK * _block_names(ws).index(name)
    return {ws.cell(row=r + k, column=look.STATS_COL).value: ws.cell(row=r + k, column=look.VALUE_COL).value
            for k in range(1, look.R_MAX + 1)}


def test_look_banded_set_up_draws_only_the_band_columns_and_the_split(tmp_path):
    _, out = _set_up(tmp_path, bands=("FICO",), split="ORIG_BAL")
    assert out.ok, out.lines
    wb = load_workbook(out.book)
    assert look.drawn_columns(wb) == ["FICO", "ORIG_BAL"] == _block_names(wb[look.LOOK])
    assert look.eligible_columns(wb) == NUMBERS                     # recorded, for the Run's redraw
    titles = [c.title.tx.rich.p[0].r[0].t for c in wb[look.LOOK]._charts if isinstance(c, ScatterChart)]
    assert titles == ["ORIG_BAL against FICO"]
    # REV_DEBT, a band column not chosen, and the two outcomes are named nowhere on Look
    named = [c.coordinate for row in wb[look.LOOK].iter_rows() for c in row
             if isinstance(c.value, str) and any(o in c.value for o in ("REV_DEBT", "GCO_AMT", "RANR_AMT"))]
    assert named == []


def test_look_banded_set_up_with_nothing_narrowed_draws_every_band_column(tmp_path):
    x = synth.write_extract(tmp_path, n=2000)
    wb = load_workbook(book.set_up(x).book)
    assert look.drawn_columns(wb) == ["FICO", "ORIG_BAL", "REV_DEBT"]


def test_look_banded_split_number_column_gets_a_block_though_it_is_not_cut(tmp_path):
    _, out = _set_up(tmp_path, bands=("FICO", "ORIG_BAL"), split="REV_DEBT")
    wb = load_workbook(out.book)
    assert look.drawn_columns(wb) == ["FICO", "ORIG_BAL", "REV_DEBT"]
    titles = sorted(c.title.tx.rich.p[0].r[0].t for c in wb[look.LOOK]._charts if isinstance(c, ScatterChart))
    assert titles == ["REV_DEBT against FICO", "REV_DEBT against ORIG_BAL"]


def test_look_banded_run_redraws_look_when_the_band_columns_change_on_control(tmp_path):
    x, out = _set_up(tmp_path, bands=("FICO",))
    b = out.book
    _answer(b)
    assert book.run(b).ok
    assert look.drawn_columns(load_workbook(b)) == ["FICO"]
    _choose(b, bands=("FICO", "REV_DEBT"))
    ran = book.run(b)
    assert ran.ok, ran.lines
    wb = load_workbook(b)
    assert look.drawn_columns(wb) == ["FICO", "REV_DEBT"] == _block_names(wb[look.LOOK])
    # the new block counted from the loans, not left empty
    nums = []
    for r in read_table(x).rows:
        try:
            nums.append(float(r["REV_DEBT"]))
        except (TypeError, ValueError):
            pass
    got = _lines(wb[look.LOOK], "REV_DEBT")
    assert got["Loans"] == 2000 and got["Smallest"] == min(nums) and got["Largest"] == max(nums)
    # and a band column taken off: REV_DEBT gone, a split added: ORIG_BAL drawn with its scatter
    _choose(b, bands=("REV_DEBT",), split="ORIG_BAL")
    assert book.run(b).ok
    wb = load_workbook(b)
    assert look.drawn_columns(wb) == ["ORIG_BAL", "REV_DEBT"]
    titles = [c.title.tx.rich.p[0].r[0].t for c in wb[look.LOOK]._charts if isinstance(c, ScatterChart)]
    assert titles == ["ORIG_BAL against REV_DEBT"]


def test_look_banded_unchanged_run_does_not_redraw_look(tmp_path):
    _, out = _set_up(tmp_path, bands=("FICO", "ORIG_BAL"))
    b = out.book
    _answer(b)
    assert book.run(b).ok                         # FICO's -9999 answered Missing: drawn again, as before
    wb = load_workbook(b)
    wb[look.LOOK][MARK] = "left here"
    wb.save(b)
    assert book.run(b).ok
    wb = load_workbook(b)
    assert wb[look.LOOK][MARK].value == "left here"
    assert look.drawn_columns(wb) == ["FICO", "ORIG_BAL"]
    assert not look.columns_moved(wb, ["FICO", "ORIG_BAL"], None)
    assert look.columns_moved(wb, ["FICO"], None) and look.columns_moved(wb, ["FICO", "ORIG_BAL"], "REV_DEBT")


def test_look_banded_columns_still_lists_every_column(tmp_path):
    x, out = _set_up(tmp_path, bands=("FICO",))
    wb = load_workbook(out.book)
    listed = [str(r[book.C_NAME - 1].value) for r in book.table_rows(wb["Columns"]) if r[book.C_NAME - 1].value]
    assert set(read_table(x).columns) <= set(listed)
    assert look.drawn_columns(wb) == ["FICO"]


def test_look_banded_nothing_refers_to_a_missing_look_block(tmp_path):
    x = synth.write_extract(tmp_path, n=2000, ratio=True)
    b = book.set_up(x, choices=ch.Choices(run_kind=ch.BLEED, segments=("CHANNEL",), bands=("FICO",))).book
    _control(b, **{"derived|1": ("INCOME_TO_SALES", "INCOME", "SALES")})
    said = book.set_up(x).lines
    # the made column is not a band column chosen, so Set up names Columns only
    assert any(s.startswith("Made INCOME_TO_SALES = INCOME ÷ SALES on Columns.") for s in said), said
    wb = load_workbook(b)
    drawn = look.drawn_columns(wb)
    assert drawn == ["FICO"]
    rows = range(look.FIRST, look.FIRST + look.BLOCK * len(drawn))
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                v = c.value if isinstance(c.value, str) else ""
                # every formula reading Look reads a row of a block it has
                for at in re.findall(r"Look!\$?[A-Z]+\$?(\d+)", v):
                    assert int(at) in rows, (ws.title, c.coordinate, v)
    # Look's own words name no column it has no block for
    others = [n for n in read_table(x).columns + ["INCOME_TO_SALES"] if n not in drawn]
    for row in wb[look.LOOK].iter_rows():
        for c in row:
            if isinstance(c.value, str):
                assert not any(re.search(rf"\b{n}\b", c.value) for n in others), (c.coordinate, c.value)
    # the method note says which columns get a block, once
    note = [c.value for row in wb[look.LOOK].iter_rows(max_row=look.FIRST) for c in row if isinstance(c.value, str)]
    assert sum("band column chosen on Control" in t for t in note) == 1
