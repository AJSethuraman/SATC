"""The firm at the bank machine, 29 Sep 2026 (BACKLOG §6d, "Held for the firm's final decision", items 2 to 6).

- "I have no idea why it automatically decided this random column was an outcome ... it should be a pop-up to say
  explicitly this is going to be what our outcome is." It had picked "% orig commitments" over "EVER GCO".
- "yes no or 01 ... that can be part of the hygiene process, but I need to know how it's accepting stuff"
- "every time I click the button screen kind of blinks scroll all the way up" and a way to "select everything or
  not by the press of a button".
- "there's a lot of white space to use, and it should really use it".
- 12 and 50 "read like one scale".
"""

import csv
import random

from openpyxl import load_workbook

from pocketbook import book, choices as ch, control, launcher, meanings, synth
from test_book import _answer

import yaml


def _bank_file(tmp_path, n=1500):
    """The synthetic book as the bank's file had it: the outcome named EVER GCO, and a 0/1 percent column whose
    name, run together, holds both `co` and `gco`."""
    src = synth.write_extract(tmp_path / "src", n=n)
    rows = list(csv.DictReader(open(src, encoding="utf-8")))
    rng = random.Random(29)
    out = tmp_path / "bank.csv"
    names = [("EVER GCO" if c == "BAD_FLAG" else c) for c in rows[0]] + ["% orig commitments"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(names)
        for r in rows:
            w.writerow(list(r.values()) + [rng.choice([0, 1])])
    return out


def _flow(x) -> launcher.Flow:
    f = launcher.Flow(gate=launcher.AddOns())
    f.gate.optional = []                             # scouting's add-on, there or not: these tests aren't about it
    f.pick(str(x))
    f.set_up()
    assert f.screen() == "L2", f.message
    return f


# ---- the outcome: names read as words, never a tie broken by the alphabet, never picked for the analyst


def test_a_column_name_is_read_as_words_not_as_letters_run_together():
    cat = meanings.catalog()
    hint = lambda c, m: meanings.hint_in(c, cat[m].hints)  # noqa: E731
    assert meanings.words("% orig commitments") == ["orig", "commitments"]
    assert meanings.words("EVER GCO") == ["ever", "gco"] and meanings.words("LoanNumber") == ["loan", "number"]
    assert hint("% orig commitments", "outcome") is None and hint("% orig commitments", "gco") is None
    assert hint("EVER GCO", "outcome") and hint("EVER_30DPD", "outcome") == "ever"
    # what the old reading found still reads the same
    assert hint("BAD_FLAG", "outcome") == "bad" and hint("GCO_AMT", "gco") == "gco"
    assert hint("ORIG_BAL", "booked") == "bal" and hint("ORIGBAL", "booked") == "bal"
    assert hint("LOAN_NBR", "key") == "loan" and hint("CHARGEOFF_FLAG", "outcome") == "chargeoff"


def test_the_bank_file_reads_ever_gco_as_the_yes_no_column_and_the_percent_column_as_yes_no_too(tmp_path):
    got = {c.name: c for c in book.read_extract(_bank_file(tmp_path)).columns}
    assert got["EVER GCO"].kind == "out" and got["% orig commitments"].kind != "out"
    assert got["% orig commitments"].yes is not None                  # still offered: the analyst decides
    assert got["EVER GCO"].yes + got["EVER GCO"].no + got["EVER GCO"].other == 1500
    assert got["ORIG_BAL"].yes is None                                # a column of amounts is never offered


def test_two_names_that_fit_the_outcome_equally_leave_it_for_the_analyst(tmp_path):
    x = tmp_path / "two.csv"
    rng = random.Random(1)
    with open(x, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["LOAN_NBR", "BAD_A", "BAD_B", "ORIG_BAL"])
        for i in range(400):
            w.writerow([1000 + i, int(rng.random() < 0.1), int(rng.random() < 0.2), rng.randint(1000, 9000)])
    table = book.read_table(x)
    sugg = meanings.suggest(table)
    assert not [c for c, s in sugg.items() if s.means == "outcome"]


def test_the_outcome_is_never_suggested_from_its_values_alone(tmp_path):
    x = tmp_path / "plain.csv"
    rng = random.Random(2)
    with open(x, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["LOAN_NBR", "WENT_SOUTH", "ORIG_BAL"])
        for i in range(400):
            w.writerow([1000 + i, int(rng.random() < 0.1), rng.randint(1000, 9000)])
    sugg = meanings.suggest(book.read_table(x))
    assert sugg["WENT_SOUTH"].means != "outcome"


def test_nothing_is_picked_as_the_outcome_and_a_pick_is_asked_about_in_counts(tmp_path):
    f = _flow(_bank_file(tmp_path))
    for mode in ("bleed", "new"):
        f.set_mode(mode)
        assert f.outcome is None and f.summary() == (False, launcher.NO_OUTCOME)
    assert [c.name for c in f.outcome_choices()] == ["EVER GCO", "% orig commitments"]
    f.pick_outcome("% orig commitments")
    q = f.outcome_question()
    assert q.startswith("Use % orig commitments as the outcome?") and "1 means the loan went bad" in q
    f.answer_outcome(False)                                            # no: nothing changes
    assert f.outcome is None and f.asking is None
    f.click("CHANNEL", "b")
    f.pick_outcome("EVER GCO")
    c = next(c for c in f.outcome_choices() if c.name == "EVER GCO")
    assert f"{c.yes:,} loans" in f.outcome_question() and f"{c.no:,}." in f.outcome_question()
    f.answer_outcome(True)
    assert f.outcome == "EVER GCO"
    rows = {r["name"]: r for r in f.rows()}
    assert rows["EVER GCO"]["what"].startswith("The outcome · 1 on ")
    assert rows["% orig commitments"]["what"].startswith("Yes/no · 1 on ")
    assert rows["EVER GCO"]["b"] is None and rows["EVER GCO"]["c"] is None    # the outcome isn't tested or held
    f.pick_outcome("ORIG_BAL")                                         # not a yes/no column: not offered
    assert f.asking is None


def test_all_and_none_tick_every_input_or_none_and_all_leaves_hold_fixed_alone(tmp_path):
    f = _flow(_bank_file(tmp_path))
    f.set_mode("new")
    f.click("FICO", "c")
    f.test_every(True)
    offered = [r["name"] for r in f.rows() if r["b"] is not None]
    assert "FICO" in offered and "FICO" not in f.test and f.hold == ["FICO"]
    assert f.test == [n for n in offered if n != "FICO"]
    f.test_every(False)
    assert f.test == [] and f.hold == ["FICO"]
    f.set_mode("bleed")
    f.test_every(True)                                                 # only for a new variable
    assert f.test == []


def test_the_picked_outcome_goes_on_columns_and_the_run_reads_it(tmp_path, monkeypatch):
    monkeypatch.setenv("POCKETBOOK_MEMORY", str(tmp_path / "memory.yaml"))
    f = _flow(_bank_file(tmp_path))
    f.pick_outcome("EVER GCO")
    f.answer_outcome(True)
    assert "EVER GCO" not in f.choices().segments and "EVER GCO" not in f.choices().bands
    f.next()
    b = launcher.book_for(f.extract)
    ws = load_workbook(b)["Columns"]
    means = {r[book.C_NAME - 1].value: r[book.C_MEANS - 1].value for r in book.table_rows(ws)}
    assert means["EVER GCO"] == meanings.catalog()["outcome"].label
    assert [c for c, m in means.items() if m == meanings.catalog()["outcome"].label] == ["EVER GCO"]
    _answer(b)
    _, problems, _ = book.read_book(b)
    assert not [p for p in problems if "Outcome" in p], problems
    # picked again the other way: it moves, and only one column is ever the outcome
    f.go(2)
    f.pick_outcome("% orig commitments")
    f.answer_outcome(True)
    assert "% orig commitments" not in f.choices().segments          # the outcome never cuts the pockets
    f.next()
    means = {r[book.C_NAME - 1].value: r[book.C_MEANS - 1].value
             for r in book.table_rows(load_workbook(b)["Columns"])}
    assert [c for c, m in means.items() if m == meanings.catalog()["outcome"].label] == ["% orig commitments"]


# ---- the window: its size, and the two settings' words


def test_the_window_opens_at_the_screen_it_is_on():
    assert launcher.window_size(1366, 768) == (1180, 628)
    assert launcher.window_size(1920, 1080) == (1180, 860)
    assert launcher.window_size(800, 600) == (720, 560)


def test_the_two_column_limits_say_which_columns_they_are_for():
    got = {s.key: s.question for s in control.load_settings() if s.key in ("few_values", "many_values")}
    assert got["few_values"].startswith("Number columns:") and "cut into bands" in got["few_values"]
    assert got["many_values"].startswith("Text columns:") and "never cut into bands" in got["many_values"]
    assert yaml.safe_load(open(control.__file__.replace("control.py", "settings.yaml"), encoding="utf-8"))


def test_a_click_keeps_the_table_where_it_was_scrolled_and_the_outcome_is_asked(monkeypatch, tmp_path):
    """On the window (needs a display: xvfb-run on Linux): a tick changes its box in place, so a table scrolled
    half way down stays there; All ticks every input; picking the outcome asks first, in counts."""
    from test_deps import _window
    root = _window()                                 # skips where there is no Tk or no display
    from tkinter import messagebox
    try:
        from pocketbook import deps
        monkeypatch.setattr(launcher, "PREFS", tmp_path / "launcher.json")
        monkeypatch.setattr(deps, "missing", lambda: [])
        monkeypatch.setattr(deps, "missing_optional", lambda: [])     # scouting's add-on, there or not
        asked = []
        monkeypatch.setattr(messagebox, "askyesno", lambda title, text, parent=None: asked.append(text) or True)
        w = launcher.build(root)
        root.geometry("900x520")                 # a small window, so the table scrolls
        root.deiconify()                         # shown: the table only has a height on a window that is
        flow = w["flow"]
        flow.pick(str(_bank_file(tmp_path)))
        flow.set_up()
        flow.set_mode("new")
        w["render"]()
        root.update()
        t = w["table"]
        t.yview_moveto(0.5)
        root.update()
        before = t.yview()
        assert before[0] > 0
        w["box_FICO_b"].event_generate("<Button-1>")
        root.update()
        assert flow.test == ["FICO"] and t.yview() == before
        w["test_all"].event_generate("<Button-1>")
        root.update()
        assert len(flow.test) > 3 and t.yview() == before
        w["box_EVER GCO_a"].event_generate("<Button-1>")
        root.update()
        assert flow.outcome == "EVER GCO" and asked and asked[0].startswith("Use EVER GCO as the outcome?")
        assert w["outcome"].get() == "EVER GCO" and w["next"].cget("state") == "normal"
    finally:
        root.destroy()


# ---- the same day, later: All · None for the bleed, and Columns shows only what this Run uses


def test_all_and_none_for_the_bleeds_bands_and_segments_leave_the_split_alone(tmp_path):
    f = _flow(_bank_file(tmp_path))
    f.click("REV_DEBT", "c")                                            # split by REV_DEBT
    f.pick_every("a", False)
    f.pick_every("b", False)
    assert f.cut == set() and f.seg == set() and f.split == "REV_DEBT"
    f.pick_every("a", True)
    nums = {r["name"] for r in f.rows() if r["a"] is not None}
    assert f.cut == nums - {"REV_DEBT"} and f.split == "REV_DEBT"
    f.pick_every("b", True)
    assert f.seg == {r["name"] for r in f.rows() if r["b"] is not None}
    f.pick_every("c", False)                                            # the split has no All or None
    assert f.split == "REV_DEBT"


def test_columns_hides_what_the_launcher_didnt_pick_and_asks_nothing_about_it(tmp_path, monkeypatch):
    monkeypatch.setenv("POCKETBOOK_MEMORY", str(tmp_path / "memory.yaml"))
    x = synth.write_extract(tmp_path, n=1500)
    picked = ch.Choices(run_kind=ch.BLEED, bands=("ORIG_BAL",), segments=("CHANNEL",), outcome="BAD_FLAG")
    out = book.set_up(x, choices=picked)
    ws = load_workbook(out.book)["Columns"]
    rows = {r[book.C_NAME - 1].value: r for r in book.table_rows(ws) if r[book.C_NAME - 1].value}
    hidden = {n for n, r in rows.items() if ws.row_dimensions[r[0].row].hidden}
    assert "FICO" in hidden and "ASSET_CLASS" in hidden and "REV_DEBT" in hidden
    assert not hidden & {"LOAN_NBR", "ORIG_BAL", "CHANNEL", "BAD_FLAG", "GCO_AMT", "RANR_AMT"}
    keys = [r[book.C_QKEY - 1].value for r in ws.iter_rows(min_row=book.COL_FIRST) if len(r) >= book.C_QKEY]
    assert not [k for k in keys if k and str(k).startswith("FICO|")]  # FICO's -9999 isn't asked about
    assert f"{len(hidden)} not picked in the launcher are hidden" in ws["D3"].value
    _answer(out.book)
    _, problems, _ = book.read_book(out.book)
    assert not problems, problems
    # nothing picked (Set up without the launcher): every column shows, and FICO's code is asked about again
    ws = load_workbook(book.set_up(x).book)["Columns"]
    assert not any(ws.row_dimensions[r[0].row].hidden for r in book.table_rows(ws))
    keys = [r[book.C_QKEY - 1].value for r in ws.iter_rows(min_row=book.COL_FIRST) if len(r) >= book.C_QKEY]
    assert [k for k in keys if k and str(k).startswith("FICO|")]


def test_look_charts_have_no_axis_title_for_excel_to_draw_over_the_numbers(tmp_path, monkeypatch):
    """At the bank, in Excel: "The axis title is out of place" -- "Loans" sat on top of 800 and 1,000."""
    import zipfile
    monkeypatch.setenv("POCKETBOOK_MEMORY", str(tmp_path / "memory.yaml"))
    out = book.set_up(synth.write_extract(tmp_path, n=1500), choices=ch.Choices(
        run_kind=ch.BLEED, bands=("FICO", "ORIG_BAL"), segments=("CHANNEL",), outcome="BAD_FLAG"))
    with zipfile.ZipFile(out.book) as z:
        charts = [z.read(n).decode("utf-8") for n in z.namelist() if n.startswith("xl/charts/chart")]
    assert charts and not [c for c in charts if "<a:t>Loans</a:t>" in c]


def _as_excel_saves_it(path):
    """Rewrite a workbook the way Excel saves it: every dropdown whose list sits on another sheet moves
    out of the sheet's dropdowns and into Excel's 2010 extension block (the x14 dataValidations)."""
    import re
    import zipfile
    from pocketbook import excel_lists as xl
    src = path.read_bytes()
    moved = 0
    with zipfile.ZipFile(__import__("io").BytesIO(src)) as zin, zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.startswith("xl/worksheets/sheet"):
                xml = data.decode("utf-8")
                ext = []
                def pull(m):
                    body = m.group(0)
                    f = re.search(r"<formula1>(.*?)</formula1>", body).group(1)
                    if "!" not in f:
                        return body
                    attrs = re.search(r"<dataValidation ([^>]*)>", body).group(1)
                    sq = re.search(r'sqref="([^"]*)"', attrs).group(1)
                    attrs = re.sub(r'\s*sqref="[^"]*"', "", attrs)
                    ext.append(f'<x14:dataValidation {attrs}><x14:formula1><xm:f>{f.lstrip("=")}</xm:f>'
                               f'</x14:formula1><xm:sqref>{sq}</xm:sqref></x14:dataValidation>')
                    return ""
                xml = re.sub(r"<dataValidation [^>]*>.*?</dataValidation>", pull, xml, flags=re.S)
                if ext:
                    moved += len(ext)
                    xml = re.sub(r"<dataValidations[^>]*>\s*</dataValidations>", "", xml)
                    xml = re.sub(r'(<dataValidations count=")\d+', lambda m: m.group(1) + str(
                        len(re.findall(r"<dataValidation ", xml))), xml)
                    block = (f'<extLst><ext uri="{xl.DV_EXT}" xmlns:x14="{xl.X14}"><x14:dataValidations '
                             f'count="{len(ext)}" xmlns:xm="{xl.XM}">{"".join(ext)}</x14:dataValidations></ext></extLst>')
                    xml = xml.replace("</worksheet>", block + "</worksheet>")
                data = xml.encode("utf-8")
            z.writestr(item, data)
    return moved


def _lists(path):
    wb = load_workbook(path)
    return sorted((ws.title, str(d.sqref), (d.formula1 or "").lstrip("="))
                  for ws in wb for d in ws.data_validations.dataValidation)


def test_dropdowns_excel_saved_on_another_sheet_survive_the_next_run(tmp_path, monkeypatch):
    """At the bank: "I have no drop downs in most places now", after changing an answer on Control. Excel keeps
    a dropdown whose list is on another sheet in its extension block; openpyxl dropped that block, so the next
    Run saved the workbook without them. Only Yes/No and the other typed-in lists were left."""
    import warnings
    from pocketbook import excel_lists, perm
    from test_book import _answer
    monkeypatch.setenv("POCKETBOOK_MEMORY", str(tmp_path / "memory.yaml"))
    monkeypatch.setattr(perm, "SHUFFLES", 300)
    b = book.set_up(synth.write_extract(tmp_path, n=1500)).book
    _answer(b)
    assert book.run(b).ok
    before = _lists(b)
    assert _as_excel_saves_it(b) > 10
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert len(_lists(b)) < len(before)                    # openpyxl alone loses them: the bug
    assert sum(len(v) for v in excel_lists.extended(b).values()) > 10
    assert book.run(b).ok
    after = _lists(b)
    for sheet in ("Control", "Columns"):                       # kept in place by a Run, never rebuilt
        assert [x for x in after if x[0] == sheet] == [x for x in before if x[0] == sheet]
    assert {x[0] for x in after} == {x[0] for x in before}


def test_opening_the_workbook_at_a_cell_keeps_the_dropdowns_excel_saved(tmp_path, monkeypatch):
    """The launcher's Open the workbook button saves it once to pick the cell: that save lost them too."""
    monkeypatch.setenv("POCKETBOOK_MEMORY", str(tmp_path / "memory.yaml"))
    b = book.set_up(synth.write_extract(tmp_path, n=800)).book
    before = _lists(b)
    _as_excel_saves_it(b)
    assert book.open_at(b, "Control", "C15")
    assert _lists(b) == before
