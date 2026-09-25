"""The result tabs added on 25 Sep 2026 (median per pocket, the split, losses
against revenue, materiality) and the second walkthrough's defects, each held
by a test that goes red if it comes back."""

import shutil
import pytest

from openpyxl import load_workbook

from origination_cube import book, engine, meanings, synth
from origination_cube.ingest import read_table
from test_book import _answer



LVR_KEYS = ("band", "seg", "loans", "g_rate", "g_rest", "g_x", "g_read", "g_over",
            "r_rate", "r_rest", "r_x", "r_read", "r_over")


def _lvr(ws) -> list[dict]:
    """The Losses vs revenue rows, by name, with the fill on each side's multiple."""
    out = []
    for r in range(5, ws.max_row + 1):
        if not isinstance(ws.cell(row=r, column=4).value, int):
            continue
        x = dict(zip(LVR_KEYS, (ws.cell(row=r, column=c).value for c in range(2, 15))))
        x["row"] = r
        for k, col in (("g_fill", book.LVR_G + 2), ("r_fill", book.LVR_R + 2)):
            f = ws.cell(row=r, column=col).fill
            x[k] = f.fgColor.rgb[-6:] if f and f.fill_type == "solid" else None
        out.append(x)
    return out

def _row(ws, name):
    for r in ws.iter_rows(min_row=book.COL_FIRST):
        if r[book.C_NAME - 1].value == name:
            return r[0].row
    raise KeyError(name)


def _set(path, name, col, value):
    wb = load_workbook(path)
    ws = wb["Columns"]
    ws.cell(row=_row(ws, name), column=col).value = value     # value=None in ws.cell() doesn't clear a cell
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
    # the method is said once, at the top (asked for on 25 Sep 2026), not under every grid
    labels = [ws.cell(row=r, column=2).value for r in range(4, 11)]
    assert labels[:6] == ["How this tab works", "What it does", "High half vs low", "Luck alone",
                          "Pooled across pockets", "What it assumes"]
    grids = [(r, ws.cell(row=r, column=2).value) for r in range(11, ws.max_row + 1)
             if isinstance(ws.cell(row=r, column=2).value, str) and " x " in ws.cell(row=r, column=2).value]
    assert grids[0][1].startswith("FICO x")                   # grids that hold the score fixed come first
    r0 = grids[0][0]
    assert "holds FICO fixed" in ws.cell(row=r0 + 1, column=2).value
    assert ws.cell(row=r0 + 3, column=2).value == "Outcome, share of loans"
    ratio = ws.cell(row=r0 + 3, column=5).value
    assert 1.3 < ratio < 2.6                                   # planted: 1.8x the bad rate
    lines = [ws.cell(row=r + 1, column=2).value for r, _ in grids]
    assert any("doesn't hold FICO fixed" in x for x in lines)


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
    untested = (engine.THIN, engine.FEW)
    """Ruling OC-26; the third walk, defects 1 and 5. Each side reads more, the
    same or less by the Control lines, against the same comparison as its flag."""
    b = _ready(tmp_path)
    wb = load_workbook(b)
    for r in wb["Control"].iter_rows(min_row=4):
        if r[6].value == "revenue_line":
            r[2].value = "10 percent either way"
    wb.save(b)
    assert book.run(b).ok
    ws = load_workbook(b)["Losses vs revenue"]
    rows = [x for x in _lvr(ws) if x["g_read"] not in untested and x["r_read"] not in untested]
    assert rows
    sub = ws["B2"].value
    hi = float(sub.split("counts as more at ")[2].split("x")[0])
    lo = float(sub.split("and less at ")[2].split("x")[0])
    assert (hi, lo) == (1.10, 0.90)
    for x in rows:
        # the lines on Control decide each side (the firm, 25 Sep 2026); luck is marked, not gated
        g = "losing more" if x["g_x"] >= 1.25 else "losing less" if x["g_x"] <= 0.8 else "about the same"
        rv = "earning more" if x["r_x"] >= hi else "earning less" if x["r_x"] <= lo else "about the same"
        assert x["g_read"].split(" (")[0] == g and x["r_read"].split(" (")[0] == rv, x
        assert x["loans"] >= 30
        # the numbers behind a reading are on the row (the firm, 25 Sep 2026: "find a clean way to
        # display the comparable metrics"): the multiple is this pocket's rate over the rest's
        assert x["g_x"] == pytest.approx(x["g_rate"] / x["g_rest"])
        assert x["r_x"] == pytest.approx(x["r_rate"] / x["r_rest"])
    # the first grid is FICO x CHANNEL, largest GCO excess first: the planted pocket, which
    # loses far more and earns about the same, is not read as a trade-off
    assert ws["B4"].value == "FICO x CHANNEL"
    assert [ws.cell(row=6, column=c).value for c in (5, 6, 7, 8, 9)] == [
        "This pocket", "Rest of band", "Multiple", "Reading", "Over the rest ($)"]
    assert "Which box" not in [c.value for c in ws[6]]
    band, seg, gread, rread = ws["B7"].value, ws["C7"].value, ws["H7"].value, ws["M7"].value
    firsts, r = [], 7
    while ws.cell(row=r, column=2).value:                 # the first grid's rows
        v = str(ws.cell(row=r, column=2).value)
        if v[0].isdigit():                                # not "(marked missing)"
            firsts.append(int(v.split(" - ")[0]))
        r += 1
    assert int(band.split(" - ")[0]) == min(firsts) and seg == "Broker"      # the lowest FICO band
    assert gread.startswith("losing more") and not rread.startswith("earning more") or "could be luck" in rread
    assert len(ws._charts) == 6
    grids = [c.value for c in ws["B"] if isinstance(c.value, str) and " x " in c.value]
    assert len(grids) == 6 and len(ws._charts) == len(grids)     # one chart per grid


def test_the_suggested_revenue_line_is_worked_out_from_the_book(tmp_path):
    b = _ready(tmp_path)
    assert book.run(b).ok
    check = {r[1].value: r[2].value for r in load_workbook(b)["Check"].iter_rows(min_row=4)}
    assert "past what luck alone can move that pocket" in check["Revenue counts as more or less"]
    ws = load_workbook(b)["Losses vs revenue"]
    reads = [x["r_read"] for x in _lvr(ws)]
    assert reads and not any("could be luck" in x for x in reads)   # nothing left to mark


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
    assert not ran.ok and any("Columns!F7" in x and "50 bands or fewer" in x for x in ran.lines)


def test_suggested_answers_are_worked_out_from_the_book(tmp_path):
    """The firm, 25 Sep 2026: suggestions "where there's a calculation", never pre-chosen."""
    b = _ready(tmp_path, n=6000)
    wb = load_workbook(b)
    for r in wb["Control"].iter_rows(min_row=4):
        if r[6].value == "min_loans":
            r[2].value = "Enough for 5 expected losses (suggested)"
        if r[6].value in ("worse_at", "better_at"):
            r[2].value = "What luck alone can move it (suggested)"
    wb.save(b)
    ran = book.run(b)
    assert ran.ok, ran.lines
    check = {r[1].value: r[2].value for r in load_workbook(b)["Check"].iter_rows(min_row=4)}
    said = check["Worked out from this book"]
    loans = int(said.split("fewest loans ")[1].split(" ")[0].replace(",", ""))
    assert 60 < loans < 90                                     # 5 / 7.1% bad = about 71 (the firm, 25 Sep 2026)
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
    rows = _lvr(ws)
    untested = [x for x in rows if {x["g_read"], x["r_read"]} & {engine.THIN, engine.FEW}]
    for x in rows:
        if x["g_read"].startswith("losing more"):
            assert x["g_over"] > 0, x
        if x["g_read"].startswith("losing less"):
            assert x["g_over"] < 0, x
        if x["r_read"].startswith("earning more"):
            assert x["r_over"] > 0, x
    assert any(x["g_read"].startswith("losing more") for x in rows)
    # untested on either side: no colour on either side
    assert untested and all(x["g_fill"] is None and x["r_fill"] is None for x in untested)
    # and they sit at the foot of their grid, off the chart
    prev, seen_untested = None, False
    for x in rows:
        if prev is None or x["row"] != prev + 1:
            seen_untested = False                         # a new grid
        is_untested = x in untested
        assert is_untested or not seen_untested, x
        seen_untested |= is_untested
        prev = x["row"]
    assert "RANR already includes credit losses" in ws["B2"].value


def test_three_way_rows_say_what_their_grid_holds_fixed(tmp_path):
    """The fourth walk, defect 1: the Three-way tab carried no caveat at all."""
    b = _ready(tmp_path)
    _set(b, "REV_DEBT", book.C_SPLIT, "Yes")
    assert book.run(b).ok
    ws = load_workbook(b)["Three-way"]
    assert ws.cell(row=4, column=19).value == "Holds FICO fixed?"
    rows = [(ws.cell(row=r, column=3).value, ws.cell(row=r, column=19).value) for r in range(5, ws.max_row + 1)
            if ws.cell(row=r, column=2).value == "Outcome, share of loans"]
    assert rows[0][0] == "FICO" and rows[0][1] == "yes"
    assert any(band == "ORIG_BAL" and words.startswith("no: may be mostly FICO") for band, words in rows)
    # no red on those rows (the firm, 25 Sep 2026, after the seventh walk); red stays for the rest
    rules = [r.formula[0] for rng in ws.conditional_formatting for r in rng.rules
             if r.dxf.fill.fgColor.rgb.endswith(book.WORSE_FILL)]
    assert rules == ['AND($Q5="worse",LEFT($S5,3)<>"no:")']
    where = load_workbook(b)["Where it bleeds"]
    assert [r.formula[0] for rng in where.conditional_formatting for r in rng.rules
            if r.dxf.fill.fgColor.rgb.endswith(book.WORSE_FILL)] == ['$Q5="worse"']
    firsts = [i for i, (band, _) in enumerate(rows) if band == "ORIG_BAL"]
    assert all(rows[i][0] == "FICO" for i in range(min(firsts)))           # held-fixed grids first
    split = load_workbook(b)["Split"]
    texts = [c.value for row in split.iter_rows() for c in row if isinstance(c.value, str)]
    assert sum(1 for x in texts if "holds FICO fixed" in x) == 2        # once per FICO grid, not per measure


def test_the_luck_line_is_luck_alone_not_the_catch_rate(tmp_path):
    """The fourth walk, defect 4: at 80% caught it was the gap a pocket can find."""
    b = _ready(tmp_path)
    assert book.run(b).ok
    wb = load_workbook(b)
    for r in wb["Control"].iter_rows(min_row=4):
        if r[6].value == "worse_at":
            r[2].value = "What luck alone can move it (suggested)"
    wb.save(b)
    assert book.run(b).ok
    check = {r[1].value: r[2].value for r in load_workbook(b)["Check"].iter_rows(min_row=4)}
    worse = float(check["Worked out from this book"].split("worse at ")[1].split("x")[0])
    assert 1.1 < worse < 1.45                                  # luck alone; the catch-rate gap is bigger


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
    assert ws["B7"].value.endswith(" - 619") and ws["C7"].value == "Broker"
    # the suggested revenue option is each pocket's own luck range (the firm, 25 Sep 2026, after the
    # sixth walk): 1.17x on 176 loans is inside it, so the worst pocket isn't read as a trade-off
    assert (ws["H7"].value, ws["M7"].value) == ("losing more", "about the same")
    assert ws["G7"].fill.fgColor.rgb.endswith(book.RED_CELL) and ws["L7"].fill.fill_type is None


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


def test_a_luck_gap_keeps_its_box_and_says_so(tmp_path):
    """The firm, 25 Sep 2026, after the fifth walk: the lines decide, luck is marked."""
    b = _ready(tmp_path, n=8000)
    _set(b, "FICO", book.C_EDGES, "620; 680; 740")
    assert book.run(b).ok
    ws = load_workbook(b)["Losses vs revenue"]
    rows = _lvr(ws)
    marked = [x for x in rows if x["g_read"].endswith("(could be luck)")]
    assert marked and all(x["g_fill"] is None for x in marked)              # marked and left plain
    assert any(x["g_fill"] == book.RED_CELL for x in rows)


def test_remembered_edges_only_fill_a_column_the_workbook_has_not_seen(tmp_path):
    """The fifth walk: another copy's edges came into this workbook, and clearing didn't undo it."""
    from origination_cube import memory
    b = _ready(tmp_path, n=3000)
    _set(b, "FICO", book.C_EDGES, "every 20")
    assert book.run(b).ok
    _set(b, "FICO", book.C_EDGES, None)                       # cleared on this workbook
    assert book.run(b).ok
    assert "edges" not in memory.load()["columns"]["FICO"]     # and forgotten with it
    book.set_up(tmp_path / "loans.csv")
    assert load_workbook(b)["Columns"]["F7"].value is None
    # a remembered edge fills only a workbook that hasn't seen the column, and says so
    _set(b, "FICO", book.C_EDGES, "every 25")
    assert book.run(b).ok
    other = book.set_up(synth.write_extract(tmp_path / "q4", n=1000, seed=5))
    ws = load_workbook(other.book)["Columns"]
    assert ws["F7"].value == "every 25" and "remembered from before" in ws["I7"].value


def test_control_shows_what_the_last_run_used(tmp_path):
    """The fifth walk: a suggested option showed no number anywhere on Control."""
    from origination_cube import control
    b = _ready(tmp_path, n=3000)
    wb = load_workbook(b)
    for r in wb["Control"].iter_rows(min_row=control.FIRST_ROW):
        if r[control.KEY_COL - 1].value == "min_loans":
            r[control.CHOOSE_COL - 1].value = "Enough for 5 expected losses (suggested)"
    wb.save(b)
    ran = book.run(b)
    assert ran.ok and any(x.startswith("Worked out from this book: fewest loans") for x in ran.lines)
    ws = load_workbook(b)["Control"]
    col = control.KEY_COL + 1
    assert ws.cell(row=control.FIRST_ROW - 1, column=col).value == "Last Run used"
    used = {r[control.KEY_COL - 1].value: ws.cell(row=r[0].row, column=col).value
            for r in ws.iter_rows(min_row=control.FIRST_ROW) if r[control.KEY_COL - 1].value}
    assert "worked out from this book" in used["min_loans"] and used["revenue_line"] == "each pocket's own luck range"
    book.set_up(tmp_path / "loans.csv")                        # and it stays through Set up again
    ws = load_workbook(b)["Control"]
    assert ws.cell(row=control.FIRST_ROW - 1, column=col).value == "Last Run used"


def test_another_workbooks_edges_stay_out_of_this_one(tmp_path):
    """The fifth walk's scenario: edges typed on another copy must not come into a
    workbook that already has the column, not even as a note."""
    a = _ready(tmp_path / "a", n=2000)
    assert book.run(a).ok                                    # FICO confirmed here with no edges
    b = _ready(tmp_path / "b", n=2000)
    _set(b, "FICO", book.C_EDGES, "every 25")
    assert book.run(b).ok                                    # remembered from the other copy
    book.set_up(tmp_path / "a" / "loans.csv")
    ws = load_workbook(a)["Columns"]
    assert ws["F7"].value is None
    assert "remembered from before" not in str(ws["I7"].value or "")


def test_a_suggestion_with_nothing_to_work_from_says_so(tmp_path):
    """The sixth walk, defect 3: a default was reported as "worked out from this book",
    and a book where nothing could be tested read "Nothing is worse"."""
    from origination_cube import control
    b = _ready(tmp_path, n=2000)
    wb = load_workbook(b)
    for r in wb["Control"].iter_rows(min_row=control.FIRST_ROW):
        key = r[control.KEY_COL - 1].value
        if key == "min_loans":
            r[control.CHOOSE_COL - 1].value, r[control.OWN_COL - 1].value = None, 100000
        if key in ("worse_at", "better_at"):
            r[control.CHOOSE_COL - 1].value = "What luck alone can move it (suggested)"
    wb.save(b)
    ran = book.run(b)
    assert ran.ok
    said = " ".join(ran.lines)
    assert "Nothing in this book to work these out from" in said and "Worked out from this book" not in said
    assert "No pocket had enough loans or losses to test" in said and "Nothing is worse" not in said
    ws = load_workbook(b)["Control"]
    used = [ws.cell(row=r, column=control.KEY_COL + 1).value for r in range(control.FIRST_ROW, ws.max_row + 1)]
    assert any(isinstance(x, str) and "the usual value" in x for x in used)
    # Check names the fallback as Control does and never calls it worked out (the seventh walk, defect 6)
    check = {r[1].value: r[2].value for r in load_workbook(b)["Check"].iter_rows(min_row=4)}
    fell = check["Suggested values"]
    assert "luck alone can make" not in fell and "how much better (0.80x) and how much worse (1.25x)" in fell
    assert "_at" not in fell and check["Pockets tested"].startswith("none of")


def test_split_gaps_that_could_be_luck_are_bracketed(tmp_path):
    """The sixth walk, defect 9: a 2.33x at 61% luck was deep red."""
    b = _ready(tmp_path)
    _set(b, "REV_DEBT", book.C_SPLIT, "Yes")
    assert book.run(b).ok
    ws = load_workbook(b)["Split"]
    vals = [c.value for row in ws.iter_rows() for c in row if isinstance(c.value, str)]
    assert any(v.startswith("(") and v.endswith("x)") for v in vals)


def test_material_pockets_too_small_to_test_are_pointed_out(tmp_path):
    """The firm, 25 Sep 2026: whether a small pocket matters is a materiality thing."""
    from origination_cube import control
    b = _ready(tmp_path, n=4000)
    wb = load_workbook(b)
    for r in wb["Control"].iter_rows(min_row=control.FIRST_ROW):
        if r[control.KEY_COL - 1].value == "min_loans":
            r[control.CHOOSE_COL - 1].value, r[control.OWN_COL - 1].value = None, 400
    wb.save(b)
    ran = book.run(b)
    assert ran.ok and any("material but too small to test" in x for x in ran.lines)
    ws = load_workbook(b)["Where it bleeds"]
    # the window counts pockets, once each, and the rows the tab shades (the seventh walk, defect 7)
    said = next(x for x in ran.lines if "material but too small to test" in x)
    blue = [ws.cell(row=r, column=c).value for r in range(5, ws.max_row + 1)
            for c in (17,) if ws.cell(row=r, column=12).value == "yes"
            and str(ws.cell(row=r, column=17).value or "").startswith("too few")]
    pockets = {(ws.cell(row=r, column=3).value, ws.cell(row=r, column=4).value, ws.cell(row=r, column=5).value,
                ws.cell(row=r, column=6).value) for r in range(5, ws.max_row + 1)
               if ws.cell(row=r, column=12).value == "yes"
               and str(ws.cell(row=r, column=17).value or "").startswith("too few")}
    assert said.startswith(f"{len(pockets)} pocket")
    if len(blue) != len(pockets):
        assert f"({len(blue)} rows" in said
    rules = [r for rng in ws.conditional_formatting for r in rng.rules]
    assert any('LEFT($Q5,7)="too few"' in (r.formula or [""])[0] for r in rules)


def test_a_real_loss_keeps_its_red_when_revenue_could_be_luck(tmp_path):
    """The seventh walk, defect 1: under 5 percent either way, under 620 / Broker
    (GCO 5.35x, a finding) lost its shading because its revenue side could be
    luck. Each side is now coloured on its own."""
    b = _ready(tmp_path, n=8000)
    _set(b, "FICO", book.C_EDGES, "620; 680; 740")
    wb = load_workbook(b)
    for r in wb["Control"].iter_rows(min_row=4):
        if r[6].value == "revenue_line":
            r[2].value = "5 percent either way"
    wb.save(b)
    assert book.run(b).ok
    ws = load_workbook(b)["Losses vs revenue"]
    assert ws["C7"].value == "Broker" and ws["H7"].value == "losing more"
    assert ws["G7"].fill.fgColor.rgb.endswith(book.RED_CELL)
    if "could be luck" in ws["M7"].value:
        assert ws["L7"].fill.fill_type is None
    rows = _lvr(ws)
    assert any("could be luck" in x["r_read"] for x in rows)             # the fixed option does mark some
    real_worse = [x for x in rows if x["g_read"] == "losing more"]
    assert real_worse and all(x["g_fill"] == book.RED_CELL for x in real_worse)
    # Control explains the suggested option as it works now: each pocket's own test (defect 2)
    opts = [r[4] for r in load_workbook(b)["_options"].iter_rows(min_row=2, values_only=True)
            if r[1] == "revenue_line" and r[3] == "luck"]
    assert opts and "own test" in opts[0] and "typical size" not in opts[0]


def test_the_category_limits_on_control_apply_at_set_up(tmp_path):
    """Found checking the seventh walk's blank "Last Run used" rows: Set up
    always used the recommended 12 and 50, whatever Control said."""
    from origination_cube import control
    b = _ready(tmp_path)
    assert book.run(b).ok
    wb = load_workbook(b)
    for r in wb["Control"].iter_rows(min_row=control.FIRST_ROW):
        if r[control.KEY_COL - 1].value == "few_values":
            r[control.CHOOSE_COL - 1].value, r[control.OWN_COL - 1].value = None, 3
    wb.save(b)
    extract = next(tmp_path.rglob("*.csv"))
    assert book.set_up(extract, b).ok
    ws = load_workbook(b)["Control"]
    used = {r[control.KEY_COL - 1].value: r[control.KEY_COL].value for r in ws.iter_rows(min_row=control.FIRST_ROW)}
    assert used["few_values"] == "3 values (applied at Set up)"
    # at 3, a column of four numbers is an amount, not a category (Set up's guess; a confirmed meaning wins)
    table = read_table(extract)
    four = next(c for c in table.columns if c == "ASSET_CLASS")
    assert meanings.suggest(table, few_values=3)[four].means != "category"
    assert meanings.suggest(table)[four].means == "category"
    wb = load_workbook(b)
    wb["Columns"][book.CONFIRM_CELL] = "Yes"
    wb.save(b)
    assert book.run(b).ok
    used = {r[control.KEY_COL - 1].value: r[control.KEY_COL].value
            for r in load_workbook(b)["Control"].iter_rows(min_row=control.FIRST_ROW)}
    assert used["band_count"] and used["band_cut"] and used["few_values"].startswith("3 values")


def test_revenue_reads_the_same_on_both_tabs(tmp_path):
    """The seventh walk, defect 3, and the firm's call (25 Sep 2026): the revenue
    setting on Control decides revenue on Where it bleeds too, so a pocket can't
    read "earning less" on one tab and "in line" on the other."""
    word = {"worse": "earning less", "worse, but could be luck": "earning less (could be luck)",
            "in line": "about the same", "better": "earning more",
            "better, but could be luck": "earning more (could be luck)"}
    for option in ("What luck alone can move it (suggested)", "5 percent either way"):
        b = _ready(tmp_path / option[:4], n=8000)
        wb = load_workbook(b)
        for r in wb["Control"].iter_rows(min_row=4):
            if r[6].value == "revenue_line":
                r[2].value = option
        wb.save(b)
        assert book.run(b).ok
        wb = load_workbook(b)
        lvr = {(x["band"], x["seg"]): x["r_read"] for x in _lvr(wb["Losses vs revenue"])}
        ws = wb["Where it bleeds"]
        seen = 0
        for r in range(5, ws.max_row + 1):
            if ws.cell(row=r, column=2).value != "RANR per booked dollar":
                continue
            flag = ws.cell(row=r, column=17).value
            key = (ws.cell(row=r, column=4).value, ws.cell(row=r, column=6).value)
            if flag in word and key in lvr:
                assert lvr[key] == word[flag], (option, key, flag, lvr[key])
                seen += 1
        assert seen, option
