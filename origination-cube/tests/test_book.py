"""The workbook route (ruling OC-22): set up from an extract, answer in Excel,
run, read the results in Excel. Nobody types a command, and nothing a person
has answered is thrown away."""

from openpyxl import load_workbook

from origination_cube import book, control, memory, synth, house, results
from origination_cube import record
import tabs

PICK = {"run_kind": "Where the book bleeds", "min_loans": "30", "min_events": "10",
        "materiality": "1% of the book's total losses", "compare_to": "The rest of its band",
        "worse_at": "1.25 times", "better_at": "0.8 times", "confidence": "95%",
        "revenue_line": "Each pocket's own test (suggested)"}


def _answer(path, confirm=True, odd=True):
    wb = load_workbook(path)
    for r in wb["Control"].iter_rows(min_row=control.FIRST_ROW):
        k = r[control.KEY_COL - 1].value
        if k in PICK:
            r[control.CHOOSE_COL - 1].value = PICK[k]
    if confirm:
        wb["Columns"][book.CONFIRM_CELL] = "Yes"
    if odd:
        treat_odd(wb, "FICO", "Missing")
    wb.save(path)


def at(wb_or_ws, name: str, col: int) -> str:
    """The cell on Columns for one extract column's row: at(wb, "FICO", book.C_EDGES) is "I14"."""
    ws = wb_or_ws["Columns"] if hasattr(wb_or_ws, "sheetnames") else wb_or_ws
    row = next(r[0].row for r in book.table_rows(ws) if r[book.C_NAME - 1].value == name)
    return f"{book._col(col)}{row}"


def treat_all(wb, answer: str, only_blank: bool = True) -> None:
    """Answer every odd value on Columns (Treat as) that is still blank, or every one."""
    for r in book.table_rows(wb["Columns"]):
        key = r[book.C_QKEY - 1].value
        if isinstance(key, str) and key.count("|") == 2 and not (only_blank and r[book.C_TREAT - 1].value):
            r[book.C_TREAT - 1].value = answer


def treat_odd(wb, column: str, answer: str | None) -> list[int]:
    """Answer every odd value found in `column` on Columns (Treat as); the rows answered."""
    rows = []
    for r in book.table_rows(wb["Columns"]):
        key = r[book.C_QKEY - 1].value
        if isinstance(key, str) and key.split("|")[0] == column and key.count("|") == 2:
            r[book.C_TREAT - 1].value = answer
            rows.append(r[0].row)
    return rows


def test_set_up_writes_every_tab_a_person_needs(tmp_path):
    out = book.set_up(synth.write_extract(tmp_path, n=3000))
    assert out.ok and out.book.exists()
    names = load_workbook(out.book).sheetnames
    assert names[:4] == ["Start here", "Control", "Columns", "Look"]
    assert "Odd values" not in names and "Learned" not in names     # both on Columns since the redesign


def test_run_refuses_until_answered_naming_each_cell(tmp_path):
    out = book.set_up(synth.write_extract(tmp_path, n=3000))
    ran = book.run(out.book)
    assert not ran.ok
    text = "\n".join(ran.lines)
    assert "Control!C" in text and "Columns!C3" in text
    assert "Traceback" not in text and "`" not in text          # words, not code
    wb = load_workbook(out.book)
    assert wb[record.LOG]["A1"].value == "Log" and "Couldn't run" in str(
        wb[record.LOG].cell(row=book.LOG_FIRST, column=2).value)
    assert "Couldn't run" in tabs.runs(wb)[0]                  # Record's Every Run shows the refusal at once


def test_answers_survive_a_second_set_up(tmp_path):
    x = synth.write_extract(tmp_path, n=3000)
    out = book.set_up(x)
    _answer(out.book)
    wb = load_workbook(out.book)
    wb["Columns"][at(wb, "CHANNEL", book.C_MEANS)] = "servicing"      # changed by hand
    wb.save(out.book)
    book.set_up(x)
    wb = load_workbook(out.book)
    assert wb["Columns"][book.CONFIRM_CELL].value == "Yes"
    assert wb["Columns"][at(wb, "CHANNEL", book.C_MEANS)].value == "Servicing data"      # shown as its label
    picked = {r[control.KEY_COL - 1].value: r[control.CHOOSE_COL - 1].value
              for r in wb["Control"].iter_rows(min_row=control.FIRST_ROW)}
    assert picked["confidence"] == "95%" and picked["materiality"] == PICK["materiality"]


def test_a_full_run_writes_results_into_the_workbook(tmp_path):
    out = book.set_up(synth.write_extract(tmp_path, n=6000))
    _answer(out.book)
    ran = book.run(out.book)
    assert ran.ok, ran.lines
    assert any("tie-out checks agree" in line for line in ran.lines)
    assert any("Worst for GCO per booked dollar: FICO " in line and "Broker" in line for line in ran.lines)
    wb = load_workbook(out.book)
    for t in (results.POCKETS, results.GRIDS, record.SHEET, record.LOG):
        assert t in wb.sheetnames
    first = [r for r in wb[results.LIST].iter_rows(min_row=2, values_only=True)][0]
    assert first[results.L_MEAS - 1] == "Bad loans" and first[results.L_SEG - 1] == "Broker"
    assert out.book.with_name(f"{out.book.stem} - what ran.yaml").exists()      # the record of what ran


def test_forget_on_columns_prunes_the_memory_on_the_next_run(tmp_path):
    x = synth.write_extract(tmp_path, n=3000)
    out = book.set_up(x)
    _answer(out.book)
    assert book.run(out.book).ok
    assert memory.load()["columns"]["FICO"]["means"] == "fico"
    book.set_up(x)                               # Columns shows what is remembered, with Forget? beside it
    _answer(out.book)
    wb = load_workbook(out.book)
    wb["Columns"][at(wb, "FICO", book.C_FORGET)] = book.FORGET_YES
    wb["Columns"][at(wb, "FICO", book.C_MEANS)] = "score"          # it was a custom score all along
    wb.save(out.book)
    assert book.run(out.book).ok
    assert "FICO" not in memory.load()["columns"]          # a Forget is not learned straight back
    assert not book.run(out.book).ok                        # ... nor on the next Run, until a person says yes
    wb = load_workbook(out.book)
    wb["Columns"][book.CONFIRM_CELL] = "Yes"
    wb.save(out.book)
    assert book.run(out.book).ok
    assert memory.load()["columns"]["FICO"]["means"] == "score"
    assert "changed_from" not in memory.load()["columns"]["FICO"]      # forgotten first, so learned fresh


def test_taking_away_every_category_is_said_in_words(tmp_path):
    out = book.set_up(synth.write_extract(tmp_path, n=3000))
    _answer(out.book)
    wb = load_workbook(out.book)
    channel, asset = at(wb, "CHANNEL", book.C_MEANS), at(wb, "ASSET_CLASS", book.C_MEANS)
    wb["Columns"][channel] = "servicing"
    wb["Columns"][asset] = "servicing"           # now no category is left
    wb.save(out.book)
    ran = book.run(out.book)
    assert not ran.ok and any("Nothing is left to cut across" in line for line in ran.lines)
    said = next(line for line in ran.lines if "Nothing is left" in line)
    assert f"CHANNEL (Columns!{channel}, now Servicing data)" in said and f"ASSET_CLASS (Columns!{asset}" in said


def test_a_bad_band_edge_is_named_by_cell(tmp_path):
    out = book.set_up(synth.write_extract(tmp_path, n=3000))
    _answer(out.book)
    wb = load_workbook(out.book)
    edges = at(wb, "FICO", book.C_EDGES)
    wb["Columns"][edges] = "700, 650"                       # edges not rising
    wb.save(out.book)
    ran = book.run(out.book)
    assert not ran.ok and any(f"Columns!{edges}" in line for line in ran.lines)


def test_own_band_edges_are_used(tmp_path):
    out = book.set_up(synth.write_extract(tmp_path, n=6000))
    _answer(out.book)
    wb = load_workbook(out.book)
    wb["Columns"][at(wb, "FICO", book.C_EDGES)] = "620, 680, 740"
    wb.save(out.book)
    assert book.run(out.book).ok
    check = tabs.record(out.book)
    assert check["Band edges used: FICO"] == "620; 680; 740  (4 bands)"


def test_the_launchers_cut_chooses_what_goes_into_the_grids(tmp_path):
    """What is cut into bands is ticked in the launcher (the redesign; it was Columns' "Cut by it?")."""
    from test_book_dates import _choose
    out = book.set_up(synth.write_extract(tmp_path, n=4000))
    _answer(out.book)
    chosen, _ = control.read_choices(load_workbook(out.book)[control.SHEET])
    assert chosen.bands is None                              # every number column, ORIG_BAL too, by default
    _choose(out.book, drop=("ORIG_BAL",))
    assert book.run(out.book).ok
    check = set(tabs.record(out.book))
    assert "Band edges used: FICO" in check and "Band edges used: ORIG_BAL" not in check
    book.set_up(synth.write_extract(tmp_path, n=4000))       # and it survives a second set-up
    chosen, _ = control.read_choices(load_workbook(out.book)[control.SHEET])
    assert "ORIG_BAL" not in chosen.bands and "FICO" in chosen.bands


def test_grids_are_heat_maps_against_the_book_and_against_peers(tmp_path):
    """The Grids tab (the redesign, section 7): four blocks for the grid and measure picked, and the heat scale
    in the spec's tokens, one step at 2x and over, 0.5x and under the greenest; a gap in points (profit) on the
    same steps, measured against the largest in the grid, less being red."""
    out = book.set_up(synth.write_extract(tmp_path, n=4000))
    _answer(out.book)
    assert book.run(out.book).ok
    ws = load_workbook(out.book)[results.GRIDS]
    heads = {c.value for row in ws.iter_rows() for c in row if c.value}
    assert {"vs the book", "vs rest of band", "Loans"} <= heads and any(str(h).startswith('="Rate · "') for h in heads)
    fills = {r.dxf.fill.fgColor.rgb[-6:] for rng in ws.conditional_formatting for r in rng.rules
             if r.dxf is not None and r.dxf.fill is not None}
    assert {house.HEAT_GOOD, house.HEAT_MID, house.HEAT_BAD, house.HEAT_BAD2} <= fills
    steps = [r.formula[0] for rng in ws.conditional_formatting for r in rng.rules if "LOG(" in r.formula[0]]
    assert any(">=1.0)" in f for f in steps) and any("<=-0.585)" in f for f in steps)
    assert all('="pts",-' in f for f in steps)                 # a gap in points: less is worse


