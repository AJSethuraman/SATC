"""The workbook route (ruling OC-22): set up from an extract, answer in Excel,
run, read the results in Excel. Nobody types a command, and nothing a person
has answered is thrown away."""

from openpyxl import load_workbook

from origination_cube import book, control, memory, synth

PICK = {"min_age_months": "Every loan", "min_loans": "30", "min_events": "10",
        "materiality": "1% of the book's total losses", "compare_to": "The rest of its band",
        "worse_at": "1.25 times", "better_at": "0.8 times", "confidence": "95%"}


def _answer(path, confirm=True, odd=True):
    wb = load_workbook(path)
    for r in wb["Control"].iter_rows(min_row=control.FIRST_ROW):
        k = r[control.KEY_COL - 1].value
        if k in PICK:
            r[control.CHOOSE_COL - 1].value = PICK[k]
    if confirm:
        wb["Columns"][book.CONFIRM_CELL] = "Yes"
    if odd:
        for r in wb["Odd values"].iter_rows(min_row=5):
            if r[1].value == "FICO":
                r[4].value = "missing"
    wb.save(path)


def test_set_up_writes_every_tab_a_person_needs(tmp_path):
    out = book.set_up(synth.write_extract(tmp_path, n=3000))
    assert out.ok and out.book.exists()
    names = load_workbook(out.book).sheetnames
    assert names[:5] == ["Start here", "Control", "Columns", "Odd values", "Learned"]


def test_run_refuses_until_answered_naming_each_cell(tmp_path):
    out = book.set_up(synth.write_extract(tmp_path, n=3000))
    ran = book.run(out.book)
    assert not ran.ok
    text = "\n".join(ran.lines)
    assert "Control!C" in text and "Columns!C3" in text
    assert "Traceback" not in text and "`" not in text          # words, not code
    log = load_workbook(out.book)["Log"]
    assert "Couldn't run" in str(log["B1"].value)


def test_answers_survive_a_second_set_up(tmp_path):
    x = synth.write_extract(tmp_path, n=3000)
    out = book.set_up(x)
    _answer(out.book)
    wb = load_workbook(out.book)
    wb["Columns"]["C8"] = "servicing"                       # CHANNEL, changed by hand
    wb.save(out.book)
    book.set_up(x)
    wb = load_workbook(out.book)
    assert wb["Columns"][book.CONFIRM_CELL].value == "Yes"
    assert wb["Columns"]["C8"].value == "servicing"
    picked = {r[control.KEY_COL - 1].value: r[control.CHOOSE_COL - 1].value
              for r in wb["Control"].iter_rows(min_row=control.FIRST_ROW)}
    assert picked["confidence"] == "95%" and picked["materiality"] == PICK["materiality"]


def test_a_full_run_writes_results_into_the_workbook(tmp_path):
    out = book.set_up(synth.write_extract(tmp_path, n=6000))
    _answer(out.book)
    ran = book.run(out.book)
    assert ran.ok, ran.lines
    assert any("tie-out checks agree" in line for line in ran.lines)
    assert any("Worst for GCO per booked dollar: fico under" in line and "Broker" in line for line in ran.lines)
    wb = load_workbook(out.book)
    for t in ("Where it bleeds", "Grids", "Check", "Log"):
        assert t in wb.sheetnames
    first = [c.value for c in wb["Where it bleeds"][5]]
    assert first[1] == "Outcome, share of loans" and first[5] == "Broker"
    assert out.book.with_name(f"{out.book.stem} - what ran.yaml").exists()      # the record of what ran


def test_the_learned_tab_prunes_on_the_next_run(tmp_path):
    x = synth.write_extract(tmp_path, n=3000)
    out = book.set_up(x)
    _answer(out.book)
    assert book.run(out.book).ok
    assert memory.load()["columns"]["FICO"]["means"] == "fico"
    wb = load_workbook(out.book)
    for r in wb["Learned"].iter_rows(min_row=4):
        if r[2].value == "FICO":
            r[0].value = memory.FORGET
    wb["Columns"]["C7"] = "score"                # it was a custom score all along
    wb.save(out.book)
    assert book.run(out.book).ok
    assert memory.load()["columns"]["FICO"]["means"] == "score"
    assert "changed_from" not in memory.load()["columns"]["FICO"]      # forgotten first, so learned fresh


def test_taking_away_every_category_is_said_in_words(tmp_path):
    out = book.set_up(synth.write_extract(tmp_path, n=3000))
    _answer(out.book)
    wb = load_workbook(out.book)
    wb["Columns"]["C8"] = "servicing"            # CHANNEL, the only category
    wb.save(out.book)
    ran = book.run(out.book)
    assert not ran.ok and any("Nothing is left to cut across" in line for line in ran.lines)


def test_a_bad_band_edge_is_named_by_cell(tmp_path):
    out = book.set_up(synth.write_extract(tmp_path, n=3000))
    _answer(out.book)
    wb = load_workbook(out.book)
    wb["Columns"]["E7"] = "700, 650"                        # FICO, edges not rising
    wb.save(out.book)
    ran = book.run(out.book)
    assert not ran.ok and any("Columns!E7" in line for line in ran.lines)


def test_own_band_edges_are_used(tmp_path):
    out = book.set_up(synth.write_extract(tmp_path, n=6000))
    _answer(out.book)
    wb = load_workbook(out.book)
    wb["Columns"]["E7"] = "620, 680, 740"
    wb.save(out.book)
    assert book.run(out.book).ok
    check = {r[1].value: r[2].value for r in load_workbook(out.book)["Check"].iter_rows(min_row=4)}
    assert check["Band edges used: fico"] == "620, 680, 740"
