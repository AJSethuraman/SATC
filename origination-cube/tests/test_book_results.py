"""The result tabs added on 25 Sep 2026 (median per pocket, the split, losses
against revenue, materiality) and the second walkthrough's defects, each held
by a test that goes red if it comes back."""

import shutil

from openpyxl import load_workbook

from origination_cube import book, synth
from test_book import _answer


def _row(ws, name):
    for r in ws.iter_rows(min_row=book.COL_FIRST):
        if r[book.C_NAME - 1].value == name:
            return r[0].row
    raise KeyError(name)


def _set(path, name, col, value):
    wb = load_workbook(path)
    ws = wb["Columns"]
    ws.cell(row=_row(ws, name), column=col, value=value)
    wb.save(path)


def _ready(tmp_path, n=6000):
    out = book.set_up(synth.write_extract(tmp_path, n=n))
    _answer(out.book)
    return out.book


def test_median_per_pocket_is_shown_on_the_grids(tmp_path):
    b = _ready(tmp_path)
    _set(b, "REV_DEBT", book.C_SHOW, "median")
    assert book.run(b).ok
    text = {c.value for row in load_workbook(b)["Grids"].iter_rows() for c in row if isinstance(c.value, str)}
    assert any("median REV_DEBT per pocket" in t for t in text)


def test_median_of_a_category_is_refused_by_cell(tmp_path):
    b = _ready(tmp_path, n=2000)
    _set(b, "CHANNEL", book.C_SHOW, "average")
    ran = book.run(b)
    assert not ran.ok and any(f"Columns!{book._col(book.C_SHOW)}8" in x for x in ran.lines)


def test_split_by_a_number_finds_the_planted_revolving_debt_effect(tmp_path):
    b = _ready(tmp_path, n=8000)
    _set(b, "REV_DEBT", book.C_SPLIT, "Yes")
    raw, problems, _ = book.read_book(b)
    assert not problems and raw["split"] == {"field": "REV_DEBT", "how": "own_median"}
    assert "REV_DEBT" not in {x["field"] for x in raw["bands"]}      # it splits; it isn't also cut
    assert book.run(b).ok
    ws = load_workbook(b)["Split"]
    said = [c.value for row in ws.iter_rows() for c in row if isinstance(c.value, str) and "Pooled" in c.value]
    assert said, "the pooled sentence is missing"
    odds = float(said[0].split("are ")[1].split("x")[0])
    assert odds > 1.3                                          # planted: 1.8x the chance of the outcome
    assert "High half vs low" in {c.value for row in ws.iter_rows() for c in row}


def test_split_by_a_category_repeats_the_grid_once_per_value(tmp_path):
    b = _ready(tmp_path)
    _set(b, "ASSET_CLASS", book.C_CUT, "No")
    _set(b, "ASSET_CLASS", book.C_SPLIT, "Yes")
    assert book.read_book(b)[0]["split"]["how"] == "each_value"
    assert book.run(b).ok
    heads = {c.value for row in load_workbook(b)["Grids"].iter_rows() for c in row if isinstance(c.value, str)}
    assert {"ASSET_CLASS = 1", "ASSET_CLASS = 4"} <= heads


def test_only_one_column_can_split(tmp_path):
    b = _ready(tmp_path, n=2000)
    _set(b, "REV_DEBT", book.C_SPLIT, "Yes")
    _set(b, "ORIG_BAL", book.C_SPLIT, "Yes")
    ran = book.run(b)
    assert not ran.ok and any("only one column can split" in x for x in ran.lines)


def test_losses_vs_revenue_puts_every_pocket_in_a_box_and_charts_it(tmp_path):
    b = _ready(tmp_path)
    assert book.run(b).ok
    ws = load_workbook(b)["Losses vs revenue"]
    boxes = [ws.cell(row=r, column=9).value for r in range(5, ws.max_row + 1) if ws.cell(row=r, column=2).value]
    assert boxes and set(boxes) <= set(book.QUADRANTS)
    for r in range(5, 5 + len(boxes)):
        gco, ranr, box = (ws.cell(row=r, column=c).value for c in (7, 8, 9))
        assert box == book.QUADRANTS[(0 if gco > 1 else 2) + (0 if ranr < 1 else 1)]
    assert sum(ws.cell(row=r, column=16).value for r in range(5, 9)) == len(boxes)
    assert ws.cell(row=4, column=13).value == "RANR flag"
    assert ws._charts                                        # the scatter survives the Log's save


def test_materiality_tab_shows_what_each_level_keeps(tmp_path):
    b = _ready(tmp_path, n=4000)
    assert book.run(b).ok
    ws = load_workbook(b)["Materiality"]
    heads = {c.value for row in ws.iter_rows() for c in row}
    assert "Share of the book's total" in heads and "Pockets kept" in heads
    assert any(isinstance(v, str) and v.startswith("In use:") for v in (c.value for row in ws.iter_rows()
                                                                         for c in row))


def test_a_copied_workbook_runs_the_extract_picked_not_the_old_path(tmp_path):
    """Second walk, defect 1."""
    b = _ready(tmp_path / "a", n=3000)
    other = tmp_path / "b"
    other.mkdir()
    copy = shutil.copy(b, other / b.name)
    x2 = synth.write_extract(other, n=2500, seed=11)
    ran = book.run(copy, x2)
    assert ran.ok and any("Ran on 2,500 loans from loans.csv" in x for x in ran.lines)


def test_a_moved_pair_finds_the_extract_beside_the_workbook(tmp_path):
    b = _ready(tmp_path / "a", n=3000)
    moved = tmp_path / "b"
    shutil.copytree(tmp_path / "a", moved)
    shutil.rmtree(tmp_path / "a")
    ran = book.run(moved / b.name)
    assert ran.ok and any("Ran on 3,000 loans" in x for x in ran.lines)


def test_edges_excel_read_as_one_number_are_refused(tmp_path):
    """Second walk, defect 2: 620,680,740 became 620680740."""
    b = _ready(tmp_path, n=2000)
    _set(b, "FICO", book.C_EDGES, 620680740)
    ran = book.run(b)
    assert not ran.ok and any("Excel dropped the commas" in x and "Columns!F7" in x for x in ran.lines)


def test_edges_with_semicolons_are_read(tmp_path):
    b = _ready(tmp_path, n=2000)
    _set(b, "FICO", book.C_EDGES, "620; 680; 740")
    assert book.read_book(b)[0]["bands"][0]["edges"] == [620, 680, 740]


def test_a_new_column_takes_the_yes_back(tmp_path):
    """Second walk, defect 4."""
    x = synth.write_extract(tmp_path, n=2000)
    out = book.set_up(x)
    _answer(out.book)
    text = x.read_text().splitlines()
    x.write_text("\n".join([text[0] + ",NEW_LINE"] + [t + ",1" for t in text[1:]]) + "\n")
    again = book.set_up(x)
    assert any("NEW_LINE" in line for line in again.lines)
    ws = load_workbook(out.book)["Columns"]
    assert ws[book.CONFIRM_CELL].value is None and "NEW_LINE" in ws["D3"].value


def test_set_up_again_keeps_the_last_results(tmp_path):
    """Second walk, defect 6."""
    x = synth.write_extract(tmp_path, n=3000)
    out = book.set_up(x)
    _answer(out.book)
    assert book.run(out.book).ok
    book.set_up(x)
    names = load_workbook(out.book).sheetnames
    assert {"Where it bleeds", "Grids", "Check", "Losses vs revenue"} <= set(names)


def test_a_workbook_open_in_excel_is_refused_before_anything_changes(tmp_path, monkeypatch):
    """Second walk, defect 8."""
    b = _ready(tmp_path, n=2000)
    before = b.read_bytes()
    monkeypatch.setattr(book, "_writable", lambda p: False)
    ran = book.run(b)
    assert not ran.ok and "open in Excel" in ran.lines[0]
    assert b.read_bytes() == before
    assert not b.with_name(f"{b.stem} - what ran.yaml").exists()


def test_start_here_says_when_it_last_ran(tmp_path):
    """Second walk, defect 9."""
    b = _ready(tmp_path, n=3000)
    assert book.run(b).ok
    ws = load_workbook(b)["Start here"]
    status = {ws.cell(row=r, column=3).value: ws.cell(row=r, column=4).value for r in range(12, 16)}
    assert status["Calls still to make on Control"] == 0
    assert "tie-out checks agree" in status["Last run"]


def test_ranr_is_marked_more_is_better_and_its_gap_reads_or_less(tmp_path):
    """Second walk, defects 13 and 14."""
    b = _ready(tmp_path)
    assert book.run(b).ok
    wb = load_workbook(b)
    heads = [c.value for row in wb["Grids"].iter_rows() for c in row if isinstance(c.value, str)]
    assert any("RANR per booked dollar  (more is better)" in h for h in heads)
    ws = wb["Where it bleeds"]
    for r in range(5, ws.max_row + 1):
        if ws.cell(row=r, column=2).value == "RANR per booked dollar":
            assert "or less" in ws.cell(row=r, column=18).number_format
            break
    else:
        raise AssertionError("no RANR row on Where it bleeds")


def test_an_edge_outside_the_columns_values_is_refused_by_cell(tmp_path):
    """Second walk, defect 2: one edge above every FICO made a single band."""
    b = _ready(tmp_path, n=2000)
    _set(b, "FICO", book.C_EDGES, "620; 680; 9000")
    ran = book.run(b)
    assert not ran.ok
    said = next(x for x in ran.lines if "Columns!F7" in x)
    assert "9,000" in said or "9000" in said
    assert "-9,999" not in said and "-9999" not in said          # the answered missing code is not the range
