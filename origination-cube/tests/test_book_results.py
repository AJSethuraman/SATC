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
    said = [c.value for row in ws.iter_rows() for c in row
            if isinstance(c.value, str) and "has the outcome" in c.value]
    assert said, "the pooled sentence is missing"
    ratio = float(said[0].split("has the outcome ")[1].split(" times")[0])
    assert 1.3 < ratio < 2.6                                   # planted: 1.8x the bad rate
    assert "High half vs low" in {c.value for row in ws.iter_rows() for c in row}
    # the grids that hold the score fixed come first, and the others say what they don't hold fixed
    heads = [c.value for row in ws.iter_rows() for c in row if isinstance(c.value, str) and " x " in c.value
             and ":" in c.value]
    assert heads[0].startswith("FICO x")
    assert any("doesn't hold FICO fixed" in x for x in said)


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


def test_losses_vs_revenue_boxes_follow_the_lines_on_control(tmp_path):
    """Ruling OC-26; the third walk, defects 1 and 5. Each side reads more, the
    same or less by the Control lines, against the same comparison as its flag."""
    b = _ready(tmp_path)
    assert book.run(b).ok
    ws = load_workbook(b)["Losses vs revenue"]
    rows = [[ws.cell(row=r, column=c).value for c in range(2, 12)] for r in range(5, ws.max_row + 1)]
    rows = [x for x in rows if x[7] in book.BOXES]
    assert rows
    sub = ws["B2"].value
    hi = float(sub.split("counts as more at ")[2].split("x")[0])
    lo = float(sub.split("and less at ")[2].split("x")[0])
    for band, seg, loans, gco, gflag, ranr, rflag, box, _, _ in rows:
        # GCO's side is its flag: past the Control line and not luck
        g = {"worse": "more", "better": "less"}.get(gflag, "same")
        assert box.startswith(book.box_of(g, "same").split(",")[0]) or (g == "same" and box.startswith(
            ("About the same", "Losing the same"))), (band, seg, gco, gflag, box)
        # revenue moves off "the same" only past its own line
        if "earning more" in box:
            assert ranr >= hi
        if "earning less" in box:
            assert ranr <= lo
        assert loans >= 30
    # the first grid is FICO x CHANNEL, largest GCO excess first: the planted pocket, which
    # loses far more and earns about the same, is not read as a trade-off
    assert ws["B4"].value == "FICO x CHANNEL"
    band, seg, box = ws["B7"].value, ws["C7"].value, ws["I7"].value
    assert band.startswith("under") and seg == "Broker"
    assert box in ("Losing more, earning the same", "Losing more, earning less")
    grids = [c.value for c in ws["B"] if isinstance(c.value, str) and " x " in c.value]
    assert len(grids) == 6 and len(ws._charts) == len(grids)     # one chart per grid


def test_the_suggested_revenue_line_is_worked_out_from_the_book(tmp_path):
    b = _ready(tmp_path)
    assert book.run(b).ok
    check = {r[1].value: r[2].value for r in load_workbook(b)["Check"].iter_rows(min_row=4)}
    said = check["Revenue counts as more or less at"]
    assert "what luck alone can move it" in said
    hi = float(said.split("x")[0])
    assert 1.05 < hi < 3


def test_materiality_tab_shows_what_each_level_keeps(tmp_path):
    b = _ready(tmp_path, n=4000)
    assert book.run(b).ok
    ws = load_workbook(b)["Materiality"]
    heads = {c.value for row in ws.iter_rows() for c in row}
    assert "Share of the book's loans with the outcome" in heads and "Pockets kept" in heads
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


def test_three_way_pockets_are_tested_and_ranked(tmp_path):
    """Ruling OC-27; the third walk, defect 3: a category split drew pictures only."""
    b = _ready(tmp_path)
    _set(b, "ASSET_CLASS", book.C_SPLIT, "Yes")
    ran = book.run(b)
    assert ran.ok and any("Split by ASSET_CLASS" in x for x in ran.lines)
    wb = load_workbook(b)
    ws = wb["Three-way"]
    first = [c.value for c in ws[5]]
    assert first[4] == "CHANNEL / ASSET_CLASS" and " / ASSET_CLASS " in first[5]
    assert first[16]                                          # every row carries a flag
    check = {r[1].value: r[2].value for r in wb["Check"].iter_rows(min_row=4)}
    assert "ASSET_CLASS" in check["Split"] and "isn't cut on its own" in check["Split"]


def test_a_split_on_a_column_that_cant_split_is_refused_by_cell(tmp_path):
    """The third walk, defect 7: GCO split by itself read 93.83x."""
    b = _ready(tmp_path, n=2000)
    _set(b, "GCO_AMT", book.C_SPLIT, "Yes")
    ran = book.run(b)
    assert not ran.ok and any("Columns!H11" in x and "can't split the pockets" in x for x in ran.lines)


def test_a_dollar_materiality_line_is_gco_only(tmp_path):
    """The third walk, defect 8: $100,000 of GCO made every RANR shortfall immaterial."""
    from test_book import PICK
    b = _ready(tmp_path, n=3000)
    wb = load_workbook(b)
    for r in wb["Control"].iter_rows(min_row=4):
        if r[6].value == "materiality":
            r[2].value, r[3].value = None, 100000
    wb.save(b)
    assert book.run(b).ok, PICK
    check = {r[1].value: r[2].value for r in load_workbook(b)["Check"].iter_rows(min_row=4)}
    assert check["Materiality line: GCO per booked dollar"] == "100,000 GCO_AMT dollars"
    assert "GCO amount" in check["Materiality line: RANR per booked dollar"]
    assert check["Smallest excess loss worth reporting"] == "$100,000 of GCO"


def test_a_forget_holds_until_a_person_confirms_again(tmp_path):
    """The third walk, defect 9: the next Run re-learned the column silently."""
    from origination_cube import memory
    b = _ready(tmp_path, n=3000)
    assert book.run(b).ok
    wb = load_workbook(b)
    for r in wb["Learned"].iter_rows(min_row=4):
        if r[2].value == "CHANNEL":
            r[0].value = memory.FORGET
    wb.save(b)
    assert book.run(b).ok
    ws = load_workbook(b)["Columns"]
    assert ws[book.CONFIRM_CELL].value is None and "CHANNEL" in ws["D3"].value
    ran = book.run(b)
    assert not ran.ok and any("Columns!C3" in x for x in ran.lines)
    assert "CHANNEL" not in memory.load()["columns"]


def test_the_workbook_is_refused_as_its_own_extract(tmp_path):
    """The third walk, defect 10."""
    b = _ready(tmp_path, n=500)
    out = book.set_up(b)
    assert not out.ok and "is the workbook, not the loan file" in out.lines[0]
    assert not b.with_name(f"{b.stem} - Origination Cube.xlsx").exists()


def test_a_renamed_column_says_to_press_set_up(tmp_path):
    b = _ready(tmp_path, n=1000)
    x = tmp_path / "loans.csv"
    text = x.read_text().splitlines()
    x.write_text("\n".join([text[0].replace("CHANNEL", "CHNL")] + text[1:]) + "\n")
    ran = book.run(b)
    said = " ".join(ran.lines)
    assert not ran.ok and "a segment" in said and "press Set up again" in said and "dimension" not in said


def test_the_heat_maps_leave_out_pockets_under_the_minimum(tmp_path):
    """The third walk, defect 4: a 1-loan row was among the strongest colours."""
    b = _ready(tmp_path, n=4000)
    assert book.run(b).ok
    ws = load_workbook(b)["Grids"]
    start = next(c for row in ws.iter_rows() for c in row if c.value == "Vs the book")
    blank_rows = [r for r in range(start.row + 1, start.row + 12)
                  if ws.cell(row=r, column=start.column).value == "(blank)"]
    assert blank_rows
    r = blank_rows[0]
    assert all(ws.cell(row=r, column=start.column + k).value is None for k in range(1, 4))


def test_band_width_every_20_cuts_and_is_remembered(tmp_path):
    """The firm, 25 Sep 2026: "20 point bands look very different", and yes to
    remembering a column's edges."""
    from origination_cube import memory
    b = _ready(tmp_path, n=6000)
    _set(b, "FICO", book.C_EDGES, "every 20")
    ran = book.run(b)
    assert ran.ok, ran.lines
    check = {r[1].value: r[2].value for r in load_workbook(b)["Check"].iter_rows(min_row=4)}
    edges = check["Band edges used: FICO"]
    pts = [float(x) for x in edges.split("(")[0].replace(",", "").split(";")]
    assert all(p % 20 == 0 for p in pts) and len(pts) > 10
    assert memory.load()["columns"]["FICO"]["edges"] == "every 20"
    other = tmp_path / "next"
    x2 = synth.write_extract(other, n=2000, seed=3)
    again = book.set_up(x2)
    assert load_workbook(again.book)["Columns"]["F7"].value == "every 20"


def test_a_band_width_too_narrow_is_refused(tmp_path):
    b = _ready(tmp_path, n=2000)
    _set(b, "FICO", book.C_EDGES, "every 1")
    ran = book.run(b)
    assert not ran.ok and any("50 at most" in x for x in ran.lines)


def test_suggested_answers_are_worked_out_from_the_book(tmp_path):
    """The firm, 25 Sep 2026: suggestions "where there's a calculation", never pre-chosen."""
    b = _ready(tmp_path, n=6000)
    wb = load_workbook(b)
    for r in wb["Control"].iter_rows(min_row=4):
        if r[6].value == "min_loans":
            r[2].value = "Enough for 10 expected losses (suggested)"
        if r[6].value in ("worse_at", "better_at"):
            r[2].value = "What luck alone can move it (suggested)"
    wb.save(b)
    ran = book.run(b)
    assert ran.ok, ran.lines
    check = {r[1].value: r[2].value for r in load_workbook(b)["Check"].iter_rows(min_row=4)}
    said = check["Worked out from this book"]
    loans = int(said.split("fewest loans ")[1].split(" ")[0].replace(",", ""))
    assert 100 < loans < 200                                   # 10 / 7.1% bad = about 141
    assert "worse at" in said and "better at" in said
    import yaml
    ran_with = yaml.safe_load(b.with_name(f"{b.stem} - what ran.yaml").read_text())["benchmark"]
    assert ran_with["min_units"] == loans and ran_with["worse_at"] > 1


def test_check_says_what_the_allowance_covers(tmp_path):
    b = _ready(tmp_path, n=2000)
    assert book.run(b).ok
    check = {r[1].value: r[2].value for r in load_workbook(b)["Check"].iter_rows(min_row=4)}
    assert "each grid and measure on its own" in check["The allowance for many tests covers"]


def test_losses_vs_revenue_dollars_agree_with_the_box_and_untested_pockets_get_none(tmp_path):
    """The fourth walk, defects 2 and 3."""
    b = _ready(tmp_path)
    assert book.run(b).ok
    ws = load_workbook(b)["Losses vs revenue"]
    rows = [[ws.cell(row=r, column=c).value for c in range(2, 12)] for r in range(5, ws.max_row + 1)]
    boxed = [x for x in rows if x[7] in book.BOXES]
    assert boxed
    for x in boxed:
        if x[7].startswith("Losing more"):
            assert x[8] > 0, x
        if x[7].startswith("Losing less"):
            assert x[8] < 0, x
    untested = [x for x in rows if x[7] == book.NOT_TESTED]
    assert untested and all({x[4], x[6]} & {"too few loans to test", "too few losses to test"} for x in untested)
    assert "RANR already includes credit losses" in ws["B2"].value


def test_three_way_rows_say_what_their_grid_holds_fixed(tmp_path):
    """The fourth walk, defect 1: the Three-way tab carried no caveat at all."""
    b = _ready(tmp_path)
    _set(b, "REV_DEBT", book.C_SPLIT, "Yes")
    assert book.run(b).ok
    ws = load_workbook(b)["Three-way"]
    assert ws.cell(row=4, column=19).value == "What this grid holds fixed"
    rows = [(ws.cell(row=r, column=3).value, ws.cell(row=r, column=19).value) for r in range(5, ws.max_row + 1)
            if ws.cell(row=r, column=2).value == "Outcome, share of loans"]
    assert rows[0][0] == "FICO" and "holds FICO fixed" in rows[0][1]
    assert any(band == "ORIG_BAL" and "doesn't hold FICO fixed" in words for band, words in rows)
    split = load_workbook(b)["Split"]
    said = [c.value for row in split.iter_rows() for c in row if isinstance(c.value, str) and "has the outcome" in c.value]
    assert all(x.index("fixed") < x.index("has the outcome") for x in said)


def test_the_luck_line_is_luck_alone_not_the_catch_rate(tmp_path):
    """The fourth walk, defect 4: at 80% caught it was the gap a pocket can find."""
    b = _ready(tmp_path)
    assert book.run(b).ok
    check = {r[1].value: r[2].value for r in load_workbook(b)["Check"].iter_rows(min_row=4)}
    hi = float(check["Revenue counts as more or less at"].split("x")[0])
    assert 1.05 < hi < 1.22                                    # luck alone: about 1.17x on this book, not 1.25x
    assert "luck alone moves revenue up to" in check["Revenue counts as more or less at"]


def test_a_revenue_share_of_95_gets_advice_that_is_allowed(tmp_path):
    """The fourth walk, defect 5."""
    from origination_cube import control
    b = _ready(tmp_path, n=1000)
    wb = load_workbook(b)
    for r in wb["Control"].iter_rows(min_row=4):
        if r[6].value == "revenue_line":
            r[2].value, r[3].value = None, 95
    wb.save(b)
    ran = book.run(b)
    said = next(x for x in ran.lines if "How far revenue" in x)
    assert "type 0.95" not in said and "for 15%, type 0.15" in said


def test_the_planted_pocket_is_not_read_as_earning_more_on_noise(tmp_path):
    """The fourth walk's render: with the LOB's edges, under 620 / Broker has RANR
    1.17x its band on 176 loans, and its own test calls that luck."""
    b = _ready(tmp_path, n=8000)
    _set(b, "FICO", book.C_EDGES, "620; 680; 740")
    assert book.run(b).ok
    ws = load_workbook(b)["Losses vs revenue"]
    assert ws["B7"].value == "under 620" and ws["C7"].value == "Broker"
    assert ws["I7"].value == "Losing more, earning the same"


def test_boxes_follow_the_lines_exactly():
    """A side reads more or less only past its line; between the lines it's the
    same. (The book-level test can pass by chance when no pocket sits between
    1.00x and a line, which let 'boxes by 1.00x again' slip past the mutation
    check in CI on 25 Sep 2026.)"""
    assert book._side(1.10, 0.80, 1.25) == "same"
    assert book._side(0.90, 0.80, 1.25) == "same"
    assert book._side(1.25, 0.80, 1.25) == "more"
    assert book._side(0.80, 0.80, 1.25) == "less"
    assert book.box_of("more", "same") == "Losing more, earning the same"
