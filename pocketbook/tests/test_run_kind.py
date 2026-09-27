"""What are you running? (the firm, 26 Sep 2026: "it likely makes sense for the
script to ask which we are doing so it does indeed have the minimum required").

Two answers on Control, and each checks its own minimum:
- Where the book bleeds: the five core columns, and never a date. A pre-spec is
  refused: the run isn't a test of a new variable.
- Finding and testing a new variable: only what it uses (Goal 2 item 2; the
  firm, 26 Sep 2026: "what's the point in that if you are searching for
  possibly important variables to the outcome?"). The key, the outcome, a
  column marked Origination date, the column it tests and the pre-spec's
  strata; the booked amount, GCO and RANR are optional, and a tab shows dollars
  only when they are there. Then one more answer: scout first (not built, so
  refused) or test from a pre-spec, whose file must be named and whose column
  must be on Columns.
A blank answer is refused by its cell, like every other call on Control: the
tool never picks for the analyst."""

import csv
import math
import shutil

import pytest
from openpyxl import load_workbook

from conftest import cube, table
from pocketbook import book, confirm_tab, confirmatory, control, engine, prespec, scout, synth, results
from pocketbook import config as cfgmod
from recalc import recalc
from test_book import _answer
from test_book_dates import _check, _choose, _columns, _control
from test_confirm_test import BINS as SMALL_BINS, SPEC as SMALL_SPEC, _dated
from test_confirmatory import _held, _log, _spec, git
import tabs

BLEED, NEW = "Where the book bleeds", "Finding and testing a new variable"
SCOUT, FROM_SPEC = "Scout first", "Test from a pre-spec"
needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed on this machine")


def _cell(b, key) -> str:
    return f"Control!C{control.row_of(load_workbook(b)[control.SHEET], key)}"


def _without(x, *drop):
    """The extract with some columns taken out."""
    with open(x, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    with open(x, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=[k for k in rows[0] if k not in drop])
        w.writeheader()
        w.writerows({k: v for k, v in r.items() if k not in drop} for r in rows)
    return x


def _refused(ran) -> str:
    assert not ran.ok, ran.lines
    text = "\n".join(ran.lines)
    assert "Traceback" not in text and "`" not in text
    return text


def _new_variable(tmp_path, monkeypatch, n=1500, step=FROM_SPEC):
    """A new-variable run ready but for the pre-spec: INCOME / SALES made on Control and splitting the pockets."""
    from test_confirmatory import _ready
    x, b = _ready(tmp_path, monkeypatch, n=n)
    _control(b, run_kind=NEW, new_variable_step=step)
    return x, b


# --------------------------------------------------------------------------
# The question itself


def test_control_asks_what_you_are_running_first_with_two_answers_and_no_default(tmp_path):
    b = book.set_up(synth.write_extract(tmp_path, n=1500)).book
    s = {x.key: x for x in control.load_settings()}
    assert s["run_kind"].question == "What are you running?"
    assert [o.label for o in s["run_kind"].options] == [BLEED, NEW]
    assert s["new_variable_step"].question == "Scout first, or test from a pre-spec already written?"
    assert [o.label for o in s["new_variable_step"].options] == [SCOUT, FROM_SPEC]
    assert s["run_kind"].judgment and s["new_variable_step"].judgment
    ws = load_workbook(b)[control.SHEET]
    keys = [r[control.KEY_COL - 1].value for r in ws.iter_rows(min_row=control.FIRST_ROW)
            if r[control.KEY_COL - 1].value]
    # the first thing in the block the launcher fills, at the foot of the tab (the redesign, phase 2)
    at = keys.index("launcher|head")
    assert keys[at:at + 3] == ["launcher|head", "run_kind", "new_variable_step"]
    assert at > keys.index(control.BLOCK_RUN) > keys.index(control.BLOCK_NOW)
    for k in keys[1:3]:
        assert ws.cell(row=control.row_of(ws, k), column=control.CHOOSE_COL).value is None     # nothing picked
    # the scouting answer says what PocketBook does instead, not what it doesn't (the firm, 26 Sep 2026)
    said = {o.label: o.explains for o in s["new_variable_step"].options}
    # (Goal 2 item 9: scouting is built, so it says what scouting does)
    assert "write the pre-spec" in said[SCOUT] and "confirm it on the loans held back" in said[SCOUT]
    assert "built" not in said[SCOUT]
    # Set up asks for it, in the launcher
    out = book.set_up(synth.write_extract(tmp_path, n=1500))
    assert any("in the launcher, choose what you're running" in line and BLEED in line and NEW in line
               for line in out.lines), out.lines


def test_a_blank_answer_is_refused_by_its_cell_and_nothing_is_picked_for_you(tmp_path):
    b = book.set_up(synth.write_extract(tmp_path, n=1500)).book
    _answer(b)
    _control(b, run_kind=None)
    text = _refused(book.run(b))
    assert (f'{_cell(b, "run_kind")}: "What are you running?" is chosen in the launcher. '
            f'{control.LAUNCHER_NOTE}') in text
    # the follow-up isn't asked until the answer says it applies
    assert "Scout first" not in text
    wb = load_workbook(b)
    assert "Couldn't run" in _log(b)[0]
    assert wb[control.SHEET].cell(row=control.row_of(wb[control.SHEET], "run_kind"),
                                  column=control.CHOOSE_COL).value is None


def test_the_follow_up_is_refused_blank_only_when_testing_a_new_variable(tmp_path):
    x = synth.write_extract(tmp_path, n=1500)
    b = book.set_up(x).book
    _answer(b)
    _control(b, run_kind=NEW, new_variable_step=None)
    text = _refused(book.run(b))
    assert (f'{_cell(b, "new_variable_step")}: "Scout first, or test from a pre-spec already written?" is chosen '
            f'in the launcher.') in text
    _control(b, run_kind=BLEED)
    assert book.run(b).ok


# --------------------------------------------------------------------------
# Where the book bleeds: the five core columns, and no date


def test_a_bleed_run_needs_only_the_five_core_columns_and_never_asks_for_a_date(tmp_path):
    x = _without(synth.write_extract(tmp_path, n=3000), "ORIG_DATE")
    out = book.set_up(x)
    _answer(out.book)
    b = out.book
    ran = book.run(b)
    assert ran.ok, ran.lines
    said = list(out.lines) + list(ran.lines) + _log(b) + [f"{k} {v}" for k, v in _check(b).items()]
    assert not any("date" in str(s).lower() for s in said), [s for s in said if "date" in str(s).lower()]
    chk = _check(b)
    assert chk["What was run"] == BLEED
    assert "Pre-spec" not in chk and "Holdout" not in chk


def test_a_bleed_run_refuses_a_missing_core_column_by_name(tmp_path):
    x = synth.write_extract(tmp_path, n=1500)
    b = book.set_up(x).book
    _answer(b)
    for name in ("GCO_AMT", "RANR_AMT"):
        _columns(b, name, C_MEANS="Not used")
    text = _refused(book.run(b))
    assert f"Columns: {BLEED} needs one column marked GCO dollars, and none is." in text
    assert f"Columns: {BLEED} needs one column marked RANR dollars, and none is." in text
    assert "Origination date" not in text


def test_a_bleed_run_uses_a_marked_origination_date_only_for_checks_line(tmp_path):
    x = synth.write_extract(tmp_path, n=1500)
    b = book.set_up(x).book
    _answer(b)
    assert book.run(b).ok
    chk = _check(b)
    assert chk["Origination dates"].endswith("(1,500 loans; 0 without a readable date)")
    assert "Holdout" not in chk and not any(k.startswith("Pre-spec") for k in chk)


def test_a_pre_spec_under_a_bleed_run_is_refused_with_its_reason(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    x = synth.write_extract(tmp_path, n=1500)
    b = book.set_up(x).book
    _answer(b)
    f = _spec(x.parent, commit=False)
    cell = _held(b, str(f))
    text = _refused(book.run(b))
    assert (f'{cell}: Where the book bleeds isn\'t a test of a new variable, so it isn\'t held to a pre-spec. '
            f'Clear the cell, or change "What are you running?" ({_cell(b, "run_kind")}).') in text
    _held(b, None)
    assert book.run(b).ok


# --------------------------------------------------------------------------
# Finding and testing a new variable: an origination date, and the column tested


def test_a_new_variable_run_needs_an_origination_date_and_says_so_by_name(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    x = _without(synth.write_extract(tmp_path / "x", n=1500, ratio=True), "ORIG_DATE")
    b = book.set_up(x).book
    _answer(b)
    _control(b, run_kind=NEW, new_variable_step=FROM_SPEC,
             **{"derived|1": ("INCOME_TO_SALES", "INCOME", "SALES")})
    book.set_up(x)
    wb = load_workbook(b)
    wb["Columns"][book.CONFIRM_CELL] = "Yes"
    wb.save(b)
    _held(b, str(_spec(x.parent, commit=False)))
    text = _refused(book.run(b))
    assert f"Columns: {NEW} needs one column marked Origination date, and none is." in text
    # the same extract runs Where the book bleeds once the pre-spec is cleared
    _held(b, None)
    _control(b, run_kind=BLEED)
    assert book.run(b).ok


def test_a_new_variable_run_refuses_two_origination_dates(tmp_path, monkeypatch):
    x, b = _new_variable(tmp_path, monkeypatch)
    _held(b, str(_spec(x.parent, commit=False)))
    _columns(b, "INCOME", C_MEANS="Origination date")
    text = _refused(book.run(b))
    assert f"Columns: {NEW} needs one column marked Origination date, and 2 are: ORIG_DATE, INCOME." in text


def test_scouting_is_refused_on_its_own_minimum_by_the_launcher_cells(tmp_path, monkeypatch):
    """Scouting is built (Goal 2 item 9; it was refused as not built until then). It needs an outcome and something
    to rank, both chosen in the launcher; without the outcome it is refused by that cell, before anything runs."""
    x, b = _new_variable(tmp_path, monkeypatch, step=SCOUT)
    got, cells = control.read_choices(load_workbook(b)[control.SHEET])
    assert got.outcome is None
    text = _refused(book.run(b))
    assert f"{cells['outcome']}: pick the outcome in the launcher." in text
    assert "pick the outcome in the launcher" in "\n".join(_log(b))
    assert scout.SHEET not in load_workbook(b).sheetnames


def test_testing_from_a_pre_spec_needs_the_file_named(tmp_path, monkeypatch):
    x, b = _new_variable(tmp_path, monkeypatch)
    cell = _held(b, None)
    text = _refused(book.run(b))
    assert f'{cell}: "{FROM_SPEC}" needs the pre-spec file named here.' in text


def test_the_column_a_pre_spec_tests_must_be_on_columns(tmp_path, monkeypatch):
    x, b = _new_variable(tmp_path, monkeypatch)
    cell = _held(b, str(_spec(x.parent, commit=False, column="DEBT_TO_SALES")))
    text = _refused(book.run(b))
    assert (f"{cell}: the pre-spec tests DEBT_TO_SALES, and no column on Columns has that name. Make it under "
            f"Add a column on Columns and press Set up again, or fix the pre-spec.") in text


@needs_git
def test_what_was_run_is_recorded_on_check_the_log_control_and_the_record(tmp_path, monkeypatch):
    x, b = _new_variable(tmp_path, monkeypatch)
    _spec(x.parent)
    _held(b, "prespec.yaml")
    ran = book.run(b)
    assert ran.ok, ran.lines
    said = f"{NEW}: {FROM_SPEC.lower()}"
    assert _check(b)["What was run"] == said
    assert _log(b)[0].endswith(f"What was run: {said}.")
    assert any(line.endswith(f"What was run: {said}.") for line in ran.lines)
    # Control shows it in the launcher's block, read-only (the redesign, phase 2)
    ws = load_workbook(b)[control.SHEET]
    shown = {r[control.KEY_COL - 1].value: r[control.CHOOSE_COL - 1].value
             for r in ws.iter_rows(min_row=control.FIRST_ROW)}
    assert shown["run_kind"] == NEW and shown["new_variable_step"] == FROM_SPEC
    record = b.with_name(f"{b.stem} - what ran.yaml").read_text(encoding="utf-8")
    assert f"# What was run: {said}\n" in record
    # and a bleed run records itself, with no follow-up
    _held(b, None)
    _control(b, run_kind=BLEED)
    assert book.run(b).ok
    assert _check(b)["What was run"] == BLEED
    assert _log(b)[0].endswith(f"What was run: {BLEED}.")
    assert f"What was run: {BLEED}\n" in b.with_name(f"{b.stem} - what ran.yaml").read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# Goal 2 item 2: a test of a new variable needs only what it uses. The booked amount, GCO and RANR are optional
# for it; the bleed analysis still needs all five.

DOLLARS = ("ORIG_BAL", "GCO_AMT", "RANR_AMT")
#: words that only a run with dollar columns has any business saying on a result tab ("$" is looked for only once
#: the formulas are calculated, since a formula's cell references carry it)
DOLLAR_WORDS = ("GCO", "RANR", "booked", "Booked", "profit", "Profit")


def _lean(tmp_path, monkeypatch, n=3000):
    """The dated synthetic book with no booked amount, GCO or RANR: a new variable tested from a committed
    pre-spec, INCOME / SALES splitting the pockets at its bins so the Prevalence tab counts it too."""
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    x = _without(synth.write_extract(tmp_path / "x", n=n, ratio=True), *DOLLARS)
    first = book.set_up(x)
    assert first.ok, first.lines
    b = first.book
    _answer(b)
    _control(b, run_kind=NEW, new_variable_step=FROM_SPEC, **{"derived|1": ("INCOME_TO_SALES", "INCOME", "SALES")})
    again = book.set_up(x)
    assert again.ok, again.lines
    # Set up doesn't mark any column as a dollar column that isn't one
    means = {r[book.C_NAME - 1].value: r[book.C_MEANS - 1].value
             for r in load_workbook(b)["Columns"].iter_rows(min_row=book.COL_FIRST)}
    for c, m in means.items():
        if m in ("Booked amount", "GCO dollars", "RANR dollars"):
            _columns(b, c, C_MEANS="Amount or number")
    _columns(b, "INCOME_TO_SALES", C_EDGES="0.1; 0.25; 0.5; 1; 2")
    _choose(b, drop=("REV_DEBT", "ASSET_CLASS", "INCOME", "SALES"), split="INCOME_TO_SALES")
    wb = load_workbook(b)
    wb["Columns"][book.CONFIRM_CELL] = "Yes"
    wb.save(b)
    _spec(x.parent)
    _held(b, "prespec.yaml")
    return x, b, again


@needs_git
def test_a_new_variable_run_needs_no_booked_amount_gco_or_ranr(tmp_path, monkeypatch):
    """The extract carries the key, the outcome, the origination date, the two columns the tested one is made
    from and the strata, and nothing else the run could use. Set up says nothing about the dollar columns once
    the run is a new variable, the Run goes through, and the confirmatory test is the one a full extract gets."""
    x, b, again = _lean(tmp_path, monkeypatch)
    d3 = str(load_workbook(b)["Columns"]["D3"].value or "")
    for label in ("Booked amount", "GCO dollars", "RANR dollars"):
        assert label not in d3 and not any(label in line for line in again.lines), (label, d3, again.lines)
    seen = {}
    real = confirmatory.state

    def spy(*a, **k):
        seen["st"] = real(*a, **k)
        return seen["st"]

    monkeypatch.setattr(confirmatory, "state", spy)
    ran = book.run(b)
    assert ran.ok, ran.lines
    chk = _check(b)
    assert chk["What was run"] == f"{NEW}: {FROM_SPEC.lower()}"
    assert chk["Differs from the pre-spec"] == "nowhere: this run used what it says"
    assert "Profit counts as more or less" not in chk and "How profit reads" not in chk
    assert "The profit line" not in chk

    # the test is the one a full extract gets: its loans and bad loans, counted by hand from the csv
    t = seen["st"].test
    with open(x, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for side, lo, hi in ((t.development, "2022-01-01", "2023-12-31"), (t.holdout, "2024-01-01", "2024-12-31")):
        mine = [(sum(float(r["INCOME"]) / float(r["SALES"]) >= e for e in SMALL_BINS), int(r["BAD_FLAG"]))
                for r in rows if lo <= r["ORIG_DATE"] <= hi and r["SALES"] not in ("", "0")
                and r["BAD_FLAG"] in ("0", "1")]
        assert side.loans == [sum(1 for g, _ in mine if g == k) for k in range(6)]
        assert side.bad == [sum(y for g, y in mine if g == k) for k in range(6)]
    assert not t.dollars

    # 4e's table: loans and bad loans, and no dollar column
    ws = load_workbook(b)[confirm_tab.SHEET]
    texts = [str(c.value) for row in ws.iter_rows() for c in row if isinstance(c.value, str)]
    assert not [s for s in texts if any(w in s for w in DOLLAR_WORDS)], \
        [s for s in texts if any(w in s for w in DOLLAR_WORDS)]
    C = confirm_tab.CONC_FIRST
    heads = next([ws.cell(row=r, column=c).value for c in range(C, C + 8)]
                 for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=C).value == "Loans"
                 and ws.cell(row=r, column=C + 1).value == "Share of loans")
    assert heads == ["Loans", "Share of loans", "Bad loans", "Share of bad loans", "Bad rate",
                     "Times the holdout's bad rate", None, None]

    # no tab with nothing to show, and no dollars on the tabs a new variable's run does write
    wb = load_workbook(b)
    # the bleed's tabs aren't built by a test of a new variable (OC-42), nor the ones the redesign replaced
    assert not {*results.TABS, *results.OLD_TABS} & set(wb.sheetnames)
    calc = recalc(b, tmp_path / "calc")
    for tab in (confirm_tab.SHEET, results.POCKETS, results.GRIDS, results.SPLIT):
        if tab not in calc.sheetnames:
            continue
        said = [str(c.value) for row in calc[tab].iter_rows() for c in row if isinstance(c.value, str)]
        assert not [s for s in said if s.startswith(("#N/A", "#VALUE", "#NAME", "#REF", "#DIV", "#NUM")) or "Err:" in s], tab
        assert not [s for s in said if any(w in s for w in DOLLAR_WORDS + ("$",))], \
            (tab, [s for s in said if any(w in s for w in DOLLAR_WORDS + ("$",))])
    check = [x for row in tabs.record_rows(calc) for x in row[1:3] if isinstance(x, str)] + tabs.runs(calc)
    assert not [s for s in check if any(w in s for w in ("GCO", "RANR", "booked dollars", "Profit and contrib"))], \
        [s for s in check if any(w in s for w in ("GCO", "RANR", "booked dollars", "Profit and contrib"))]


def test_a_bleed_run_still_refuses_an_extract_without_the_dollar_columns(tmp_path):
    """The other direction: the same lean extract, run as Where the book bleeds, is refused naming each missing
    column, and Set up keeps saying they are missing while the run is the bleed analysis."""
    x = _without(synth.write_extract(tmp_path, n=1500, ratio=True), *DOLLARS)
    out = book.set_up(x)
    b = out.book
    _answer(b)                                                  # Where the book bleeds
    again = book.set_up(x)
    assert "No column was found for Booked amount" in str(load_workbook(b)["Columns"]["D3"].value)
    text = _refused(book.run(b))
    for label in ("Booked amount", "GCO dollars", "RANR dollars"):
        assert f"Columns: {BLEED} needs one column marked {label}, and none is." in text, text
    assert again.ok


# --------------------------------------------------------------------------
# The same rule in a cube file, and 4e's dollars only where there is GCO


def test_a_cube_file_needs_the_dollar_lines_unless_it_tests_a_new_variable():
    with pytest.raises(cfgmod.ConfigError) as got:
        cube(booked=None, gco=None, ranr=None)
    said = "\n".join(got.value.problems)
    for k in ("booked", "gco", "ranr"):
        assert f"`{k}:`" in said, said
    cfg = cube(run_kind="new_variable", booked=None, gco=None, ranr=None)
    assert [m.name for m in cfg.measures if m.core] == ["outcome_loans"]
    assert cfg.run_kind == "new_variable" and cfg.booked == "" and cfg.gco == ""
    # every line given, a new variable's run builds every rate, as the bleed analysis does
    assert [m.name for m in cube(run_kind="new_variable").measures if m.core] == list(cfgmod.CORE_NAMES)
    with pytest.raises(cfgmod.ConfigError) as got:
        cube(run_kind="scout")
    assert "`run_kind:` is 'scout'; it takes bleed or new_variable" in got.value.problems


def _mixed():
    out = []
    for d, n in (("2022-03-01", 60), ("2024-06-01", 60)):
        for i in range(n):
            out.append((d, "AB"[i % 2], (0.5, 1.5, 2.5)[i % 3], 1 if i % 5 == 0 or (i % 3 == 2 and i % 4 == 0) else 0))
    return out


def test_4e_shows_gco_dollars_only_when_there_is_a_gco_column():
    """GCO alone is enough for 4e's dollars (it needs no booked amount); without it, 4e says nothing about
    dollars and every other figure is the same."""
    rows = _dated(_mixed())
    ps = prespec.parse(SMALL_SPEC)
    got = {}
    for name, lines in (("gco", {"booked": None, "ranr": None}), ("none", {"booked": None, "ranr": None, "gco": None})):
        res = engine.run(cube(origination_date="ORIG", run_kind="new_variable", **lines), table(rows))
        got[name] = confirmatory.run_test(res, prespec.named(ps, *confirmatory.column_range(res, "R")))
    with_gco, without = got["gco"], got["none"]
    assert with_gco.dollars and not without.dollars
    hold = [(d, v, bad) for d, _, v, bad in _mixed() if d.startswith("2024")]
    for k in range(3):
        want = math.fsum(50 * bad for _, v, bad in hold if (v > 1) + (v > 2) == k)
        assert with_gco.concentration()[k].gco == want
        assert without.concentration()[k].gco == 0.0
        assert (with_gco.concentration()[k].loans, with_gco.concentration()[k].lift) == \
            (without.concentration()[k].loans, without.concentration()[k].lift)
    assert with_gco.holdout.fit.odds == without.holdout.fit.odds
