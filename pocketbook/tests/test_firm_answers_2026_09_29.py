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

import pytest
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


# ---- later the same day, at the bank: a category splits the pockets too
# The firm: "I kind of figured I'd be able to see a view with system flag and origination FICO and asset segment
# somehow" ... "I'd rather make it able to happen within the config or launcher. Like I know it can't break down too
# far but can we not make something work?"


def _flag_file(tmp_path, n=1500, seed=29):
    """The synthetic book with two categories added after every other value is drawn, so no planted number
    moves: SYS_FLAG (Y or N, a blank on every 97th loan) and REGION (seven values)."""
    src = synth.write_extract(tmp_path / "src", n=n)
    rows = list(csv.DictReader(open(src, encoding="utf-8")))
    rng = random.Random(seed)
    out = tmp_path / "flagged.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(list(rows[0]) + ["SYS_FLAG", "REGION"])
        for i, r in enumerate(rows):
            flag = "" if i % 97 == 0 else rng.choice("YN")
            w.writerow(list(r.values()) + [flag, rng.choice(["R1", "R2", "R3", "R4", "R5", "R6", "R7"])])
    return out


def test_category_split_launcher_offers_split_by_on_a_category_and_never_segments_by_it_too(tmp_path):
    f = _flow(_flag_file(tmp_path))
    rows = {r["name"]: r for r in f.rows()}
    assert rows["SYS_FLAG"]["c"] == {"on": False, "radio": True}          # a category can split
    assert rows["CHANNEL"]["c"] is not None and rows["FICO"]["c"] is not None
    f.click("SYS_FLAG", "c")
    rows = {r["name"]: r for r in f.rows()}
    assert f.split == "SYS_FLAG" and "SYS_FLAG" not in f.seg               # unticked from Segment by
    assert rows["SYS_FLAG"]["c"]["on"] and not rows["SYS_FLAG"]["b"]["on"]
    f.pick_outcome("BAD_FLAG")
    f.answer_outcome(True)
    got = f.choices()
    assert got.split == "SYS_FLAG" and "SYS_FLAG" not in got.segments and "CHANNEL" in got.segments
    ok, said = f.summary()
    assert ok and "split by SYS_FLAG" in said
    f.pick_every("b", True)                                                 # All leaves the split alone
    assert "SYS_FLAG" not in f.seg and f.split == "SYS_FLAG"
    f.click("SYS_FLAG", "b")                                                # ticked as a segment: no longer splits
    assert f.split is None and "SYS_FLAG" in f.seg
    f.click("SYS_FLAG", "c")
    f.click("REV_DEBT", "c")                                                # still one split column, or none
    assert f.split == "REV_DEBT" and "SYS_FLAG" not in f.seg


def test_category_split_too_many_values_is_refused_in_words_in_the_launcher_and_at_the_run(tmp_path, monkeypatch):
    assert ch.too_many_values("X", ch.SPLIT_MOST_VALUES) is None           # six values split
    said = ch.too_many_values("REGION", 7)
    assert said == ("REGION has 7 values. A category can split the pockets by 6 values at most: with more, each "
                    "pocket's parts are too thin to read. Split by a column with fewer values, or by none.")
    f = _flow(_flag_file(tmp_path))
    f.pick_outcome("BAD_FLAG")
    f.answer_outcome(True)
    f.click("REGION", "c")
    assert f.summary() == (False, said) and f.states()["next"] == "disabled"
    # the Run refuses it too, in the same words, whatever wrote the workbook
    monkeypatch.setenv("POCKETBOOK_MEMORY", str(tmp_path / "memory.yaml"))
    out = book.set_up(f.extract, choices=ch.Choices(run_kind=ch.BLEED, bands=("FICO",), segments=("CHANNEL",),
                                                    split="REGION", outcome="BAD_FLAG"))
    _answer(out.book)
    ran = book.run(out.book)
    assert not ran.ok and ran.lines == [f"Couldn't run: {said}"]


def _category_run(tmp_path, field, many_tests="bh", n=12000):
    from pocketbook import config as cfgmod, engine
    from pocketbook.ingest import read_table
    cfg, _ = synth.write(tmp_path / "cube", n=n)
    raw = cfgmod.load(cfg).raw
    raw["split"] = {"field": field, "how": "each_value"}
    raw["benchmark"]["many_tests"] = many_tests
    return engine.run(cfgmod.parse(raw), read_table(_flag_file(tmp_path, n=n)))


def test_category_split_engine_sets_each_value_against_the_rest_of_its_pocket(tmp_path):
    """Asset class 4 goes bad 1.4 times as often as the others (synth.py): each value against the rest of its
    pocket finds it, pocket by pocket and pooled, and every figure is worked out again here from the parts."""
    from pocketbook import engine, stats
    res = _category_run(tmp_path, "ASSET_CLASS")
    g = res.grids[0]                                                         # FICO x CHANNEL
    assert g.split_parts == ["1", "2", "3", "4"] and not g.split_compare     # no halves
    four = g.part_pooled["4"]["outcome_loans"]
    assert 1.2 < four["ratio"] < 1.8 and four["odds_p"] < 0.01 and four["pockets"] >= 8
    assert g.part_pooled["1"]["outcome_loans"]["ratio"] < 1
    # every value is one comparison: the value's rate over the rest of its pocket's, and the p-value of the z test,
    # after one allowance for many tests across every value and pocket of the grid
    raw, want = {}, {}
    for v in g.split_parts:
        for (b, d) in g.part_tested[v]["outcome_loans"]:
            me = g.split_cells[(b, d, v)].rates["outcome_loans"]
            rest = [g.split_cells[(b, d, x)].rates["outcome_loans"] for x in g.split_parts
                    if x != v and (b, d, x) in g.split_cells]
            num, den, units = sum(r.num for r in rest), sum(r.den for r in rest), sum(r.units for r in rest)
            assert g.part_compare[v][(b, d)]["outcome_loans"][0] == pytest.approx(stats.multiple(me.rate, num / den))
            raw[(v, b, d)] = stats.two_prop_z(me.num, me.units, num, units)[1]
    for k, p in zip(raw, engine.adjust(list(raw.values()), "bh")):
        want[k] = p
    got = {(v, b, d): x["outcome_loans"][1] for v in g.split_parts for (b, d), x in g.part_compare[v].items()
           if x.get("outcome_loans", (None, None))[1] is not None}
    assert got.keys() == want.keys() and all(got[k] == pytest.approx(want[k]) for k in want)
    # a dollar rate's parts are shuffled within their pocket, like the halves
    gco = [x["gco_rate"][1] for x in g.part_compare["4"].values() if x.get("gco_rate", (None,))[0] is not None]
    assert gco and all(p is not None for p in gco)
    # whether the values differ at all: B3 on three degrees of freedom, and the planted class shows
    b3 = g.split_general["outcome_loans"]
    assert b3["df"] == 3 and b3["p"] < 0.001
    assert "gco_rate" not in g.split_general                                 # no k-group test for a dollar rate
    # the families Record counts: every value's pockets in one family per grid and rate
    from pocketbook import checks
    fam = [f for f in checks.families(res) if f[0] == "split values" and f[2] == "outcome_loans"
           and f[1] == f"{g.band} x {g.dimension}"]
    assert fam and fam[0][4] == len(want)


def test_category_split_engine_with_two_values_is_the_cmh_test_for_the_differ_at_all(tmp_path):
    """With two values, B3 is Cochran-Mantel-Haenszel's chi-square (docs/statistics.md B3: "With two groups it
    collapses to A6"), worked out here from every pocket's four counts; and Y against the rest is Y against N."""
    from pocketbook import stats
    g = _category_run(tmp_path, "SYS_FLAG", many_tests="none", n=8000).grids[0]
    assert g.split_parts == ["N", "Y", "(blank)"]                          # a blank is a value of its own
    assert g.split_general["outcome_loans"]["df"] == 2
    t = _two_valued(tmp_path).grids[0]
    assert t.split_parts == ["N", "Y"]
    strata = []
    for (b, d), _ in t.inner():
        cells = [t.split_cells.get((b, d, v)) for v in ("Y", "N")]
        s = [c.rates["outcome_loans"] if c else None for c in cells]
        strata.append(tuple(x for r in s for x in ((r.events, r.units - r.events) if r else (0, 0))))
    chi, p = stats.cmh(strata)
    assert t.split_general["outcome_loans"]["df"] == 1
    assert t.split_general["outcome_loans"]["q"] == pytest.approx(chi, rel=1e-9)
    assert t.split_general["outcome_loans"]["p"] == pytest.approx(p, rel=1e-9)
    for (b, d), x in t.part_compare["Y"].items():                           # Y against the rest is Y against N
        if x["outcome_loans"][0] is not None:
            y, n_ = (t.split_cells[(b, d, v)].rates["outcome_loans"] for v in ("Y", "N"))
            assert x["outcome_loans"][0] == pytest.approx(stats.multiple(y.rate, n_.rate))
            assert x["outcome_loans"][1] == pytest.approx(stats.two_prop_z(y.num, y.units, n_.num, n_.units)[1])


def _two_valued(tmp_path, n=8000):
    """SYS_FLAG with its blanks read as N: two values."""
    from pocketbook import config as cfgmod, engine
    from pocketbook.ingest import read_table
    src = _flag_file(tmp_path / "two", n=n)
    rows = list(csv.DictReader(open(src, encoding="utf-8")))
    out = tmp_path / "two.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({**r, "SYS_FLAG": r["SYS_FLAG"] or "N"})
    cfg, _ = synth.write(tmp_path / "cube2", n=n)
    raw = cfgmod.load(cfg).raw
    raw["split"] = {"field": "SYS_FLAG", "how": "each_value"}
    raw["benchmark"]["many_tests"] = "none"
    return engine.run(cfgmod.parse(raw), read_table(out))


def test_category_split_workbook_carries_the_flag_through_every_tab(tmp_path, monkeypatch):
    """FICO x asset segment by the system flag, as the firm asked: Grids, Pockets, Split, Record and Start here."""
    from pocketbook import results
    import tabs
    monkeypatch.setenv("POCKETBOOK_MEMORY", str(tmp_path / "memory.yaml"))
    x = _flag_file(tmp_path, n=6000)
    out = book.set_up(x, choices=ch.Choices(run_kind=ch.BLEED, bands=("FICO",), segments=("CHANNEL", "ASSET_CLASS"),
                                            split="SYS_FLAG", outcome="BAD_FLAG"))
    _answer(out.book)
    assert book.read_book(out.book)[0]["split"] == {"field": "SYS_FLAG", "how": "each_value"}
    ran = book.run(out.book)
    assert ran.ok, ran.lines
    b = out.book
    wb = load_workbook(b)
    assert "FICO x ASSET_CLASS / SYS_FLAG" in tabs.options(wb, results.GRIDS, "Grid")
    assert tabs.options(wb, results.POCKETS, "Pockets") == ["Two-way", "Split by SYS_FLAG"]
    split = tabs.options(wb, results.SPLIT, "Grid")
    assert "FICO x ASSET_CLASS · SYS_FLAG Y vs rest" in split and "FICO x CHANNEL · SYS_FLAG N vs rest" in split
    ws = tabs.calculated(tabs.choose(b, tmp_path / "g.xlsx", results.GRIDS, grid="FICO x ASSET_CLASS / SYS_FLAG"),
                         results.GRIDS)
    heads = set(c for _, c in tabs.block(ws, "vs the book"))
    assert {"ASSET_CLASS 4 · Y", "ASSET_CLASS 4 · N"} <= heads or {"4 · Y", "4 · N"} <= heads
    ws = tabs.calculated(tabs.choose(b, tmp_path / "s.xlsx", results.SPLIT, grid="FICO x ASSET_CLASS · SYS_FLAG Y vs "
                                                                                 "rest"), results.SPLIT)
    text = [str(v) for row in ws.iter_rows(values_only=True) for v in row if v is not None]
    assert "Worse than the rest in" in text and "Value vs rest, all" in text
    assert "Bad loans, value vs rest" in text
    differ = next(t for t in text if t.startswith("Do the values of SYS_FLAG differ at all? Bad loans: "))
    assert "degrees of freedom" in differ and "Charge-offs" in differ and "not tested: dollar rate" in differ
    assert not [t for t in text if "high half" in t.lower() or "High vs low" in t]
    rec = {k: v for k, v, *_ in tabs.record_rows(b)}
    assert "each value set against the rest of its pocket" in rec["Split"]
    assert "for the split's values" in rec["Families of tests"]
    assert "K-group Mantel-Haenszel" in rec["Tests"]
    start = [str(v) for row in load_workbook(b)["Start here"].iter_rows(values_only=True) for v in row if v]
    assert "Split: each pocket split" in start


# ---- Look reads the Treat as answers (at the bank, 29 Sep 2026: "This median call seems to ignore that I said the
# -99... values that represent things missing from the bureau are treating as missing. Look into this and see if
# this leaks elsewhere"). Look was drawn at Set up, before any answer, and a Run never drew its blocks again.

def _bureau_file(tmp_path, n=1500):
    """The synthetic book with SHORT_HIST: months of credit history, and where the bureau has none one of four
    codes from -99,000,901, none on 1% of loans, so no one of them is "likely a code" and Columns asks about the
    negatives, as it did at the bank."""
    src = synth.write_extract(tmp_path, n=n)
    rows = list(csv.DictReader(open(src, encoding="utf-8")))
    rng = random.Random(3)
    for i, r in enumerate(rows):
        r["SHORT_HIST"] = -99000901 - (i // 40) % 4 if i % 40 == 0 else rng.randint(0, 435)
    out = tmp_path / "bureau.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return out


def _look_block(path, column):
    from pocketbook import look
    wb = load_workbook(path)
    i = look.drawn_columns(wb).index(column)
    ws, r = wb[look.LOOK], look.FIRST + look.BLOCK * i
    return {str(ws.cell(row=r + k, column=look.STATS_COL).value): ws.cell(row=r + k, column=look.VALUE_COL).value
            for k in range(1, look.R_TREAT)}


def test_look_leaves_out_what_columns_answered_missing_once_run(tmp_path, monkeypatch):
    from pocketbook import perm
    from test_book import _answer, treat_odd
    monkeypatch.setenv("POCKETBOOK_MEMORY", str(tmp_path / "memory.yaml"))
    monkeypatch.setattr(perm, "SHUFFLES", 200)
    b = book.set_up(_bureau_file(tmp_path), choices=ch.Choices(
        run_kind=ch.BLEED, bands=("FICO", "SHORT_HIST"), segments=("CHANNEL",), outcome="BAD_FLAG")).book
    before = _look_block(b, "SHORT_HIST")
    assert before["Smallest"] == -99000904 and before["Mean"] < 0            # unanswered: used as recorded
    wb = load_workbook(b)
    assert treat_odd(wb, "SHORT_HIST", "Missing")
    wb.save(b)
    _answer(b)                                                               # FICO's -9999 answered Missing too
    assert book.run(b).ok
    after = _look_block(b, "SHORT_HIST")
    assert after["Smallest"] >= 0 and after["Largest"] <= 435 and after["Mean"] > 0
    assert after["Answered missing, left out"] == sum(1 for i in range(1500) if i % 40 == 0)
    fico = _look_block(b, "FICO")
    assert fico["Smallest"] > 0 and fico["Answered missing, left out"] > 0
    wb = load_workbook(b)
    note = [c.value for row in wb["Look"].iter_rows() for c in row if isinstance(c.value, str)
            and "negative values" in c.value]
    assert note                                                              # it says what was answered


def test_look_keeps_a_bars_from_or_to_the_analyst_typed_when_it_is_drawn_again(tmp_path, monkeypatch):
    from pocketbook import look, perm
    from test_book import _answer, treat_odd
    monkeypatch.setenv("POCKETBOOK_MEMORY", str(tmp_path / "memory.yaml"))
    monkeypatch.setattr(perm, "SHUFFLES", 200)
    b = book.set_up(_bureau_file(tmp_path), choices=ch.Choices(
        run_kind=ch.BLEED, bands=("FICO", "SHORT_HIST"), segments=("CHANNEL",), outcome="BAD_FLAG")).book
    wb = load_workbook(b)
    i = look.drawn_columns(wb).index("SHORT_HIST")
    r = look.FIRST + look.BLOCK * i
    wb[look.LOOK].cell(row=r + look.R_BARS, column=look.VALUE_COL).value = 50
    wb[look.LOOK].cell(row=r + look.R_TO, column=look.VALUE_COL).value = 250
    treat_odd(wb, "SHORT_HIST", "Missing")
    wb.save(b)
    _answer(b)
    assert book.run(b).ok
    got = _look_block(b, "SHORT_HIST")
    assert got["Bars"] == 50 and got["To"] == 250


def test_looks_dots_leave_out_what_columns_answered_missing(tmp_path):
    """The scatters read each loan's value the same way: an answered missing is no dot, as it is no loan in a band."""
    from pocketbook import config as cfgmod, look
    from pocketbook.ingest import read_table
    t = read_table(_bureau_file(tmp_path, n=400))
    got = look._readable(t, "SHORT_HIST", None, cfgmod.MissingRule(below=0.0))
    assert [v for v in got if v is not None] and min(v for v in got if v is not None) >= 0
    assert sum(v is None for v in got) == sum(1 for i in range(400) if i % 40 == 0)


# ---- later still, at the bank: one cell of a grid read out in words
# The firm: "It would be useful to be able to maybe select a particular line and say I want this as an example and
# it fills in the band saying what versus book means what versus band means and what loans means and it changes
# obviously depending on the grid and measure you're looking at, but the measures should be constant from run to
# run the grid may change, but like that's really just the band."


@pytest.fixture(scope="module")
def one_cell_book(tmp_path_factory):
    """A Run on the synthetic book, shuffled only a little: these tests read words, not p-values."""
    from pocketbook import perm
    d = tmp_path_factory.mktemp("one_cell")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("POCKETBOOK_MEMORY", str(d / "memory.yaml"))
        mp.setattr(perm, "SHUFFLES", 200)
        b = book.set_up(synth.write_extract(d, n=4000)).book
        _answer(b)
        ran = book.run(b)
        assert ran.ok, ran.lines
    return b


def _said(ws) -> dict:
    """What one cell says, as calculated: the cell's name under "name", then each line by its label."""
    for r in range(1, ws.max_row + 1):
        if ws.cell(row=r, column=2).value == "What one cell says":
            out = {"name": ws.cell(row=r + 1, column=2).value}
            for k in range(2, 7):
                out[ws.cell(row=r + k, column=2).value] = ws.cell(row=r + k, column=3).value
            return out
    raise KeyError("What one cell says")


def _grids(b, out, **picks):
    """Grids with its dropdowns set, calculated: the sheet, its four blocks by title, and what one cell says."""
    from pocketbook import results
    import tabs
    ws = tabs.calculated(tabs.choose(b, out, results.GRIDS, **picks), results.GRIDS)
    blocks = {t: tabs.block(ws, t) for t in ("Rate", "vs the book", "vs rest of band", "Loans")}
    return ws, blocks, _said(ws)


def _pockets(loans: dict) -> dict:
    """The inner pockets with loans in them, {(row, column): loans}."""
    return {k: v for k, v in loans.items() if "All" not in k and isinstance(v, (int, float)) and v > 0}


def _shade(v, kind: str, bound: float) -> str:
    """The heat scale's colour for a gap, worked out here from results.HEAT_STEPS' limits and not its formula."""
    import math
    if not isinstance(v, (int, float)):
        return "blank"
    t = -v / bound if kind == "pts" else (math.log2(v) if v > 0 else 0)
    for lim, word in ((1.0, "deep red"), (0.585, "red"), (0.263, "light red")):
        if t >= lim:
            return word
    for lim, word in ((-0.585, "green"), (-0.263, "light green")):
        if t <= lim:
            return word
    return "pale"


def _min_losses(b) -> int:
    from pocketbook import config as cfgmod
    return cfgmod.parse(book.read_book(b)[0]).benchmark.min_events


def test_one_cell_reads_the_blocks_own_numbers_in_words_for_a_multiple_and_a_gap_in_points(one_cell_book, tmp_path):
    b = one_cell_book
    for measure, kind in (("Charge-offs", "x"), ("Kept after losses", "pts")):
        _, blocks, _ = _grids(b, tmp_path / f"{kind}-0.xlsx", measure=measure)
        rate, bk, bd, loans = (blocks[t] for t in ("Rate", "vs the book", "vs rest of band", "Loans"))
        both = [k for k in _pockets(loans) if isinstance(bk[k], (int, float)) and isinstance(bd[k], (int, float))]
        bl, d = both[-1]                                          # not the pocket the tab opens on
        assert (bl, d) != both[0]
        ws, blocks, said = _grids(b, tmp_path / f"{kind}.xlsx", measure=measure, row=bl, column=d)
        assert blocks["Rate"] == rate                             # picking a cell changes nothing above it
        n, v, w = loans[(bl, d)], bk[(bl, d)], bd[(bl, d)]
        r = f"{rate[(bl, d)] * 100:.2f}%"
        others = [c for (x, c) in _pockets(loans) if x == bl and c != d]
        named = f" (the {', '.join(others)} loans)" if 1 <= len(others) <= 3 else ""
        assert said["name"] == f"{bl} · {d}, {measure}"
        if kind == "x":
            assert said["Rate"] == f"These {n:,} loans charged off {r} of their booked dollars."
            assert said["vs the book"] == f"{v:.2f}× the charge-off rate of the whole book."
            assert said["vs rest of band"] == f"{w:.2f}× the charge-off rate of the other loans in {bl}{named}."
        else:
            side = lambda g: "less" if g < 0 else "more"                                 # noqa: E731
            assert said["Rate"] == f"These {n:,} loans kept {r} of their booked dollars after losses."
            assert said["vs the book"] == (f"Kept {abs(v):.2f} points {side(v)} of their booked dollars than the "
                                           "whole book.")
            assert said["vs rest of band"] == (f"Kept {abs(w):.2f} points {side(w)} of their booked dollars than the "
                                               f"other loans in {bl}{named}.")
        assert said["Loans"] == f"{n:,} loans; {bl} has {loans[(bl, 'All')]:,} in all."
        bound = max([abs(x) for blk in (bk, bd) for x in blk.values() if isinstance(x, (int, float))] + [0.01])
        assert said["The colour"].startswith(f"vs the book is {_shade(v, kind, bound)}, vs rest of band "
                                             f"{_shade(w, kind, bound)}.")


def test_one_cell_says_why_a_blank_is_blank_alone_in_its_band_or_too_few_losses(one_cell_book, tmp_path):
    from pocketbook import results
    b = one_cell_book
    few = f"Blank: fewer losses than the minimum ({_min_losses(b)} losses), so not compared."
    _, blocks, _ = _grids(b, tmp_path / "blank-0.xlsx", measure="Charge-offs")
    bk, bd, loans = blocks["vs the book"], blocks["vs rest of band"], blocks["Loans"]
    pockets = _pockets(loans)
    mates = lambda k: sum(1 for j in pockets if j[0] == k[0])                                  # noqa: E731
    alone = next(k for k in pockets if mates(k) == 1)
    thin = next(k for k in pockets if mates(k) > 1 and bk[k] is None and bd[k] is None)
    assert bd[alone] is None
    for measure in ("Charge-offs", "Kept after losses"):
        _, _, said = _grids(b, tmp_path / f"alone-{measure[0]}.xlsx", measure=measure, row=alone[0], column=alone[1])
        assert said["vs rest of band"] == f"Blank: alone in its band. Nothing else in {alone[0]} to compare with."
    _, _, said = _grids(b, tmp_path / "alone.xlsx", measure="Charge-offs", row=alone[0], column=alone[1])
    if loans[alone] == 1:                                         # one loan reads as one, not "1 loans"
        assert said["Rate"].startswith("This one loan charged off ") and said["Rate"].endswith(" of its booked "
                                                                                             "dollars.")
        assert said["Loans"].startswith("1 loan; ")
    if bk[alone] is None:
        assert said["vs the book"] == few                        # only one reason a comparison with the book is blank
    _, _, said = _grids(b, tmp_path / "few.xlsx", measure="Charge-offs", row=thin[0], column=thin[1])
    assert said["vs the book"] == few and said["vs rest of band"] == few
    assert "alone" not in said["The colour"] and said["The colour"].startswith("vs the book is blank, vs rest of band "
                                                                               "blank.")
    ws = load_workbook(b)[results.GRIDS]
    notes = [c.value for row in ws.iter_rows() for c in row if isinstance(c.value, str) and c.value.startswith("A blank")]
    assert notes == ["A blank: alone in its band, or fewer losses than the minimum, so not compared."]


def _listed(ws, label: str) -> list:
    """A Row or Column dropdown's list as it stands (calculated): its OFFSET over the hidden labels, worked out."""
    import re
    import tabs
    cell = tabs.dropdown(ws.formulas, label)
    dv = next(v for v in ws.formulas.data_validations.dataValidation if cell.coordinate in str(v.sqref))
    m = re.fullmatch(r"=?OFFSET\(\$([A-Z]+)\$(\d+),0,0,MAX\(1,\$([A-Z]+)\$(\d+)\),1\)", dv.formula1)
    assert m, dv.formula1
    c, r, nc_, nr_ = m.groups()
    n = max(1, int(ws[f"{nc_}{nr_}"].value or 0))
    return [ws[f"{c}{int(r) + k}"].value for k in range(n)]


def test_one_cell_row_and_column_lists_follow_the_grid_picked(one_cell_book, tmp_path):
    from pocketbook import results
    import tabs
    b = one_cell_book
    grids = tabs.options(load_workbook(b), results.GRIDS, "Grid")
    ws, blocks, said = _grids(b, tmp_path / "g0.xlsx")
    rows0 = [bl for bl, d in blocks["Loans"] if d == "All" and bl != "All"]
    cols0 = [d for bl, d in blocks["Loans"] if bl == "All" and d != "All"]
    assert _listed(ws, "Row") == rows0 and _listed(ws, "Column") == cols0
    assert said["name"] == f"{tabs.dropdown(ws, 'Row').value} · {tabs.dropdown(ws, 'Column').value}, Bad loans"
    other = next(g for g in grids if " / " not in g and g.split(" x ")[0] != grids[0].split(" x ")[0]
                 and g.split(" x ")[1] != grids[0].split(" x ")[1])
    ws, blocks, said = _grids(b, tmp_path / "g1.xlsx", grid=other)
    rows1 = [bl for bl, d in blocks["Loans"] if d == "All" and bl != "All"]
    cols1 = [d for bl, d in blocks["Loans"] if bl == "All" and d != "All"]
    assert rows1 != rows0 and cols1 != cols0
    assert _listed(ws, "Row") == rows1 and _listed(ws, "Column") == cols1
    # the Row and Column left from the other grid aren't in this one: it asks, and reads out nothing
    assert said["name"] == results.SAY_PICK and not any(said[k] for k in said if k != "name")
    k = next(iter(_pockets(blocks["Loans"])))
    _, blocks, said = _grids(b, tmp_path / "g2.xlsx", grid=other, row=k[0], column=k[1])
    assert said["name"] == f"{k[0]} · {k[1]}, Bad loans"
    assert said["Loans"].startswith(f"{blocks['Loans'][k]:,} loans; {k[0]} has ")
