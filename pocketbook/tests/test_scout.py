"""Scouting (Goal 2 item 9; capability 4a; docs/statistics.md B7): one Run, two steps, in order. Find on the
development loans (a random forest ranks every candidate), write the pre-spec from what it proposes, then confirm it
on the loans held back, exactly as a saved shortlist is confirmed.

The firm, 26 Sep 2026: scouting is "to try and guess importance ... it should be wider", and "dates are for the
scouting pipeline" (OC-39); each input is tested "once with and once without" the columns held fixed.

The book is the first synthetic book with UTIL (a cliff planted above 0.9) and TENURE (nothing planted), the
income / sales cliffs (below 0.1 and above 2.0), and filler this file adds from a stream of its own: four number
columns with nothing behind them, F2 moving with F1, and a category, REGION. Every count and split is made here from
the extract by hand."""

import copy
import csv
import math
import os
import random
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
import yaml
from openpyxl import load_workbook

from pocketbook import book, confirm_tab, confirmatory, control, deps, launcher, prespec, scout, scout_tab, synth
import tabs
from test_book import _answer
from test_book_dates import _choose, _control

NEW = "Finding and testing a new variable"
FILLER = ["F1", "F2", "F3", "F4", "REGION"]
PLANTED = {"income_to_sales", "UTIL"}
HOLD = ("FICO", "CHANNEL")
TEST = ("UTIL", "TENURE", "F1", "F2", "F3", "F4", "REGION")


def _filler(rows: list[dict]) -> None:
    rng = random.Random("scout-filler")
    for r in rows:
        f1 = rng.gauss(50, 15)
        r["F1"] = round(f1, 2)
        r["F2"] = round(0.9 * f1 + rng.gauss(0, 3), 2)          # moves with F1: rank correlation about 0.97
        r["F3"] = round(rng.gauss(10, 1), 3)
        r["F4"] = round(rng.uniform(0, 100), 1)
        r["REGION"] = rng.choice(["North", "South", "East", "West", "Central"])


def _extract(folder: Path, n: int) -> Path:
    rows = synth.add_shortlist(synth.make_rows(n, 7, ratio=True), 7)
    _filler(rows)
    folder.mkdir(parents=True, exist_ok=True)
    x = folder / "loans.csv"
    with x.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return x


SUGGESTED = "The month start nearest 70% of the loans (suggested)"


def _book(folder: Path, n: int, test=TEST, hold=HOLD, cutoff=SUGGESTED):
    """The workbook set up for scouting: income / sales made on Columns, `test` ticked Test it, `hold` Hold fixed,
    BAD_FLAG the outcome, as the launcher's Next writes them, and the cutoff on Control answered (`cutoff`: the
    suggestion's label, a date typed under Or your own, or None to leave it blank)."""
    x = _extract(folder, n)
    b = book.set_up(x).book
    _answer(b)
    _control(b, run_kind=NEW, new_variable_step="Scout first", **{"derived|1": ("income_to_sales", "INCOME", "SALES")})
    book.set_up(x)
    wb = load_workbook(b)
    names = [str(r[book.C_NAME - 1].value) for r in book.table_rows(wb["Columns"]) if r[book.C_NAME - 1].value]
    _choose(b, drop=tuple(c for c in names if c not in hold), run_kind="new_variable", outcome="BAD_FLAG",
            test=tuple(test), hold=tuple(hold))
    if cutoff is not None:
        _control(b, cutoff=cutoff if isinstance(cutoff, str) else ("own", cutoff))   # OC-51: the analyst's call
    wb = load_workbook(b)
    wb["Columns"][book.CONFIRM_CELL] = "Yes"
    wb.save(b)
    return x, b


def _run(b, mp):
    seen = {}
    real = confirmatory.state

    def spy(*a, **k):
        seen["res"] = a[2]
        return real(*a, **k)
    mp.setattr(confirmatory, "state", spy)
    ran = book.run(b)
    return ran, seen.get("res")


@pytest.fixture(scope="module")
def wide(tmp_path_factory):
    """Nine candidates (seven ticked and income / sales made on Columns), FICO and CHANNEL held fixed: 12,000 loans."""
    folder = tmp_path_factory.mktemp("wide")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GIT_CEILING_DIRECTORIES", str(folder))
        mp.setenv("POCKETBOOK_MEMORY", str(folder / "memory.yaml"))
        x, b = _book(folder, 12000)
        ran, res = _run(b, mp)
    assert ran.ok, ran.lines
    return {"x": x, "b": b, "ran": ran, "res": res, "sc": res.scout, "folder": folder}


# --------------------------------------------------------------------------
# By hand, from the extract


def _rows(x):
    with open(x, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _suggested(x, share=0.7):
    """The suggested cutoff, by hand (OC-51): the loans ordered by origination date, the date by which `share` of them
    had been made, and of the first of its month and the first of the next, the nearer (the earlier on a tie)."""
    dates = sorted(date.fromisoformat(r["ORIG_DATE"]) for r in _rows(x))
    at = dates[math.ceil(share * len(dates)) - 1]
    this = at.replace(day=1)
    nxt = (this + timedelta(days=32)).replace(day=1)
    return min((this, nxt), key=lambda d: (abs((d - at).days), d)), dates[0], dates[-1]


def _value(r, column):
    if column == "income_to_sales":
        return None if r["SALES"] in ("", "0") else float(r["INCOME"]) / float(r["SALES"])
    try:
        return float(r[column])
    except ValueError:
        return None


def _ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    out = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return out


def _spearman(a, b):
    ra, rb = _ranks(a), _ranks(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    return num / math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))


def _table(b) -> dict:
    """The Scouting tab's table as the analyst reads it: {candidate: {heading: value}}."""
    ws = load_workbook(b)[scout.SHEET]
    head = next(r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=scout_tab.S_NAME).value == "Candidate")
    heads = [ws.cell(row=head, column=c).value for c in range(scout_tab.FIRST, scout_tab.LAST + 1)]
    out = {}
    for r in range(head + 1, ws.max_row + 1):
        name = ws.cell(row=r, column=scout_tab.S_NAME).value
        if not name:
            break
        out[name] = dict(zip(heads, (ws.cell(row=r, column=c).value
                                     for c in range(scout_tab.FIRST, scout_tab.LAST + 1))))
    return out


def _note(b) -> dict:
    ws = load_workbook(b)[scout.SHEET]
    return {ws.cell(row=r, column=2).value: ws.cell(row=r, column=3).value for r in range(3, 30)
            if ws.cell(row=r, column=2).value}


# --------------------------------------------------------------------------
# What it finds


def test_scouting_ranks_the_planted_inputs_first_and_proposes_them_not_tenure_or_filler(wide):
    sc = wide["sc"]
    assert sc.problem is None and len(sc.candidates) == 8          # seven ticked, and income / sales made on Columns
    ranked = [c.name for c in sc.candidates]
    assert set(ranked[:2]) == PLANTED, ranked
    wrong = [(c.name, c.proposed, c.importance, c.importance_held) for c in sc.candidates
             if c.proposed != (c.name in PLANTED)]
    assert wrong == [], (wrong, sc.floor)
    below = [(c.name, v) for c in sc.candidates if c.name not in PLANTED
             for v in (c.importance, c.importance_held) if v > sc.floor]
    assert below == [], (below, sc.floor)
    assert next(c for c in sc.candidates if c.name == "TENURE").why == scout.BELOW
    assert next(c for c in sc.candidates if c.name == "REGION").kind == scout.CATEGORY
    # the tab says the same, row for row
    got = _table(wide["b"])
    assert list(got) == ranked
    said = {n: row["Proposed?"] for n, row in got.items()}
    assert said == {c.name: "Yes" if c.proposed else "No" for c in sc.candidates}


def test_importance_is_reported_with_and_without_the_held_fixed_columns(wide):
    sc = wide["sc"]
    missing = [c.name for c in sc.candidates if c.importance is None or c.importance_held is None]
    assert missing == []
    assert any(c.importance != c.importance_held for c in sc.candidates)
    assert [h for h, _ in sc.held] == list(HOLD)
    assert dict(sc.held)["FICO"] > sc.floor                        # the book's own driver, held fixed
    got = _table(wide["b"])
    heads = list(next(iter(got.values())))
    assert heads[2:4] == ["Importance", "FICO and CHANNEL held fixed"]
    shown = [(n, row["Importance"], row["FICO and CHANNEL held fixed"]) for n, row in got.items()]
    want = [(c.name, round(c.importance, 6), round(c.importance_held, 6)) for c in sc.candidates]
    assert shown == want
    assert "given FICO and CHANNEL as well" in _note(wide["b"])["With and without"]


def test_a_correlated_pair_is_flagged_on_both_rows_and_the_line_is_said_once(wide):
    sc = wide["sc"]
    cut = wide["sc"].cutoff
    dev = [r for r in _rows(wide["x"]) if date.fromisoformat(r["ORIG_DATE"]) < cut and r["BAD_FLAG"] in ("0", "1")]
    nums = ["income_to_sales", "UTIL", "TENURE", "F1", "F2", "F3", "F4"]
    want = set()
    for i, a in enumerate(nums):
        for b in nums[i + 1:]:
            pairs = [(_value(r, a), _value(r, b)) for r in dev]
            pairs = [(u, v) for u, v in pairs if u is not None and v is not None]
            rho = _spearman([u for u, _ in pairs], [v for _, v in pairs])
            if abs(rho) >= 0.7:
                want |= {(a, b), (b, a)}
    got = {(c.name, p) for c in sc.candidates for p, _ in c.partners if "(held fixed)" not in p}
    assert got == want and ("F1", "F2") in got
    f1 = next(c for c in sc.candidates if c.name == "F1")
    assert f1.partners[0][1] >= 0.7
    assert _table(wide["b"])["F1"]["Correlated with"].startswith("F2 (+0.")
    note = " ".join(str(v) for v in _note(wide["b"]).values())
    assert note.count("0.7 or more") == 1


def test_the_suggested_bins_sit_on_the_planted_cliffs_and_the_reference_holds_the_median(wide):
    sc = wide["sc"]
    by = {c.name: c for c in sc.candidates}
    util, ratio = by["UTIL"], by["income_to_sales"]
    assert any(0.85 <= e <= 0.95 for e in util.bins), util.bins
    assert any(0.08 <= e <= 0.12 for e in ratio.bins), ratio.bins
    assert any(1.7 <= e <= 2.3 for e in ratio.bins), ratio.bins
    cut = wide["sc"].cutoff
    dev = [r for r in _rows(wide["x"]) if date.fromisoformat(r["ORIG_DATE"]) < cut and r["BAD_FLAG"] in ("0", "1")]
    for c in (util, ratio):
        vals = sorted(v for v in (_value(r, c.name) for r in dev) if v is not None)
        n = len(vals)
        med = (vals[(n - 1) // 2] + vals[n // 2]) / 2
        edges = [-math.inf, *c.bins, math.inf]
        k = c.reference_index
        assert edges[k] <= med < edges[k + 1], (c.name, med, c.bins, k)
        # every suggested group holds at least MIN_SHARE of the development loans
        small = [g for g in range(len(c.bins) + 1)
                 if sum(1 for v in vals if edges[g] <= v < edges[g + 1]) < scout.MIN_SHARE * n]
        assert small == [], (c.name, c.bins, small)


def test_scouting_prints_without_the_candidates_header_over_the_pre_spec(wide):
    """K, the firm's answer of 27 Sep 2026: printed, the print titles carried the candidates table's header onto the
    page where the pre-spec file starts."""
    ws = load_workbook(wide["b"])[scout.SHEET]
    assert ws.print_title_rows is None and ws.print_title_cols is None
    pre = [c.row for row in ws.iter_rows() for c in row if c.value == "The pre-spec"]
    assert pre and ws.print_area                                  # the pre-spec is on the page, under no header


def test_the_cutoff_splits_the_loans_exactly_by_date(wide):
    """OC-51: the loans made before the cutoff on Control build the tree; those made on it or after are held back, to
    the day. The book answered the suggestion, the month start nearest 70% of the loans, worked out here by hand; a
    date typed by hand splits the same way."""
    sc, res = wide["sc"], wide["res"]
    cut, first, end = _suggested(wide["x"])
    assert sc.cutoff == cut and cut.day == 1
    assert sc.development == prespec.DateRange(first, cut - timedelta(days=1))
    assert sc.holdout == prespec.DateRange(cut, end)
    rows = _rows(wide["x"])
    assert sc.n_held_back == sum(1 for r in rows if date.fromisoformat(r["ORIG_DATE"]) >= cut)
    dev = [r for r in rows if date.fromisoformat(r["ORIG_DATE"]) < cut]
    assert sc.n_dev == sum(1 for r in dev if r["BAD_FLAG"] in ("0", "1"))
    assert sc.n_dev_bad == sum(1 for r in dev if r["BAD_FLAG"] == "1")
    col = res.config.origination_date
    for typed in (date(2024, 1, 1), date(2023, 6, 15), cut + timedelta(days=1)):
        got, lo, before, hi, after, why = scout.development_rows(res, typed)
        assert why is None and (lo, before, hi) == (first, typed - timedelta(days=1), end)
        want = [i for i, r in enumerate(res.table.rows) if date.fromisoformat(str(r[col])[:10]) < typed]
        assert sorted(got) == want
        assert after == len(res.table.rows) - len(want)
    # a cutoff that leaves nothing on one side is refused in words, never split some other way
    assert "none is left to hold back" in scout.development_rows(res, end + timedelta(days=1))[-1]
    assert "no loan was made before the cutoff" in scout.development_rows(res, first)[-1]


def test_scouting_never_reads_the_held_back_loans(wide):
    """Every held-back loan's outcome turned over, and every other value of it scrambled but its date: the identical
    shortlist, number for number, and the identical file."""
    res, sc = wide["res"], wide["sc"]
    cut = sc.cutoff
    col = res.config.origination_date
    rng = random.Random("scramble")
    other = copy.copy(res)
    other.table = copy.copy(res.table)
    rows = []
    changed = 0
    for r in res.table.rows:
        if date.fromisoformat(str(r[col])[:10]) >= cut:
            r = dict(r)
            for k in list(r):
                if k == col:
                    continue
                v = r[k]
                if k == "BAD_FLAG":
                    r[k] = {"0": "1", "1": "0", 0: 1, 1: 0}.get(v, v)
                    continue
                try:
                    x = float(v)
                except (TypeError, ValueError):
                    r[k] = rng.choice(["North", "Broker", "X"])
                    continue
                r[k] = x * rng.uniform(0.2, 5.0)
            changed += 1
        rows.append(r)
    other.table.rows = rows
    assert changed == sc.n_held_back
    again = scout.run(other, load_choices(wide["b"]), cutoff=sc.cutoff)

    def said(s):
        return [(c.name, c.rank, c.importance, c.importance_held, c.bins, c.reference_index, c.proposed, c.partners,
                 c.curve) for c in s.candidates] + [s.floor, s.held, s.development, s.holdout]
    diffs = [(i, x, y) for a, b in zip(said(sc), said(again)) if a != b
             for i, (x, y) in enumerate(zip(a, b) if isinstance(a, tuple) else [(a, b)]) if x != y]
    assert diffs == []
    today = date(2026, 9, 27)
    assert scout.text(again, today) == scout.text(sc, today)


def load_choices(b):
    return control.read_choices(load_workbook(b)[control.SHEET])[0]


def test_the_pre_spec_is_written_beside_the_workbook_and_logged_before_any_held_back_result(wide):
    sc, b = wide["sc"], wide["b"]
    p = scout.prespec_for(b)
    assert p == b.with_name("loans - pre-spec.yaml") and p.is_file() and sc.action == scout.WROTE
    spec = prespec.load(p)
    assert spec.columns == tuple(c.name for c in sc.proposed)
    assert spec.strata == HOLD and spec.outcome == "BAD_FLAG"
    assert (spec.development, spec.holdout) == (sc.development, sc.holdout)
    fp = confirmatory.fingerprint(p.read_text(encoding="utf-8"))
    assert sc.fingerprint == fp
    entry = tabs.runs(b)
    at = {k: next(i for i, v in enumerate(entry) if v.startswith(k))
          for k in ("Scouting on", confirmatory.HOLDOUT_MARK, "Follows pre-spec")}
    assert at["Scouting on"] < at["Follows pre-spec"] < at[confirmatory.HOLDOUT_MARK]
    assert f"Wrote the pre-spec {p.name} on " in entry[at["Scouting on"]] and fp in entry[at["Scouting on"]]
    assert any(v.startswith(f"Pre-spec {p.name} written: fingerprint {fp}") for v in entry)
    rec = tabs.record(b)
    assert rec["Scouting"].startswith("8 candidates") and "none of their outcomes" in rec["Scouting held back"]


def test_one_run_finds_then_confirms_on_the_shortlist_path_with_found_shown(wide):
    res, sc = wide["res"], wide["sc"]
    st = res.prespec
    assert st.scouted and [t.column for t in st.tests] == [c.name for c in sc.proposed]
    wb = load_workbook(wide["b"])
    assert wb.sheetnames.index(scout.SHEET) + 1 == wb.sheetnames.index(confirm_tab.SHEET)
    ws = wb[confirm_tab.SHEET]
    hidden = [c for c in (confirm_tab.N_FG, confirm_tab.N_FP)
              if ws.column_dimensions[confirm_tab._c(c)].hidden]
    assert hidden == []
    assert "Open loans - PocketBook.xlsx: start with New variables." in wide["ran"].lines


def test_the_written_pre_spec_confirms_figure_for_figure_against_a_hand_written_one(wide, tmp_path, monkeypatch):
    """The same content written by hand, groups named and not numbered, confirmed as a saved shortlist on a copy of
    the workbook: every count, odds ratio and p-value the same."""
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    monkeypatch.setenv("POCKETBOOK_MEMORY", str(tmp_path / "memory.yaml"))
    for f in (wide["x"], wide["b"]):
        shutil.copy(f, tmp_path / f.name)
    spec = prespec.load(scout.prespec_for(wide["b"]))
    hand = {"prespec": 1, "written": "2026-09-27", "outcome": "BAD_FLAG",
            "inputs": [{"column": i.column, "bins": list(i.bins), "reference": i.groups[i.reference_index]}
                       for i in spec.inputs],
            "strata": list(spec.strata), "confidence": spec.confidence,
            "holdout": {"from": spec.holdout.start.isoformat(), "to": spec.holdout.end.isoformat()},
            "development": {"from": spec.development.start.isoformat(), "to": spec.development.end.isoformat()}}
    (tmp_path / "hand.yaml").write_text(yaml.safe_dump(hand, sort_keys=False), encoding="utf-8")
    b = tmp_path / wide["b"].name
    _choose(b, shortlist="hand.yaml", run_kind="new_variable")
    ran, res = _run(b, monkeypatch)
    assert ran.ok, ran.lines
    assert res.scout is None and not res.prespec.scouted

    def figures(tests):
        out = []
        for t in tests:
            for name in confirmatory.SETS:
                s = getattr(t, name)
                out.append((t.column, name, s.loans, s.bad, s.fit.odds, s.fit.p, s.allowed))
        return out
    mine, theirs = figures(wide["res"].prespec.tests), figures(res.prespec.tests)
    assert len(mine) == len(theirs) == 4 * len(spec.inputs)
    diffs = [(a, b) for a, b in zip(mine, theirs) if a != b]
    assert diffs == []


def test_the_same_extract_writes_the_same_file_and_an_edit_after_the_held_back_run_is_labelled(
        wide, tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    monkeypatch.setenv("POCKETBOOK_MEMORY", str(tmp_path / "memory.yaml"))
    for f in (wide["x"], wide["b"]):
        shutil.copy(f, tmp_path / f.name)
    b = tmp_path / wide["b"].name
    first = scout.prespec_for(wide["b"]).read_text(encoding="utf-8")
    ran, res = _run(b, monkeypatch)                    # no pre-spec beside this copy: scouting writes it again
    assert ran.ok, ran.lines
    p = scout.prespec_for(b)
    assert p.read_text(encoding="utf-8") == first and res.scout.fingerprint == wide["sc"].fingerprint
    assert _table(b) == _table(wide["b"])
    # the analyst edits it after that held-back run: the next Run keeps the edit, confirms it and labels the change
    edited = first.replace("bins: [0.9]", "bins: [0.8]")
    assert edited != first
    p.write_text(edited, encoding="utf-8")
    ran, res = _run(b, monkeypatch)
    assert ran.ok, ran.lines
    assert p.read_text(encoding="utf-8") == edited
    assert res.scout.action == scout.KEPT and any(d.startswith("UTIL: the file cuts at 0.8") for d in res.scout.differs)
    assert res.prespec.tests[[t.column for t in res.prespec.tests].index("UTIL")].bins == (0.8,)
    entry = tabs.runs(b)
    changed = [v for v in entry if v.startswith(confirmatory.CHANGED)]
    assert changed and f"fingerprint {wide['sc'].fingerprint} then" in changed[0], entry[:8]
    words = " ".join(str(v) for v in _note_rows(b))
    assert "confirmed as it stands" in words and "UTIL: the file cuts at 0.8" in words
    # OC-51: every Run here read the held-back loans twice (the tree's check, then the test), and counts once: the
    # copy carried the fixture's Run, then two Runs on the copy
    touched = sum(1 for v in tabs.runs(b) if v.startswith(confirmatory.HOLDOUT_MARK))
    assert touched == 6 and tabs.record(b)["Runs that touched the holdout"] == \
        "3 on Record's Every Run, this one included"


def _note_rows(b):
    ws = load_workbook(b)[scout.SHEET]
    return [ws.cell(row=r, column=scout_tab.S_NAME).value for r in range(1, ws.max_row + 1)
            if ws.cell(row=r, column=scout_tab.S_NAME).value]


def test_with_nothing_held_fixed_the_strata_wait_for_an_answer_and_nothing_is_confirmed(tmp_path, monkeypatch):
    """OC-13: the columns to hold fixed are the analyst's call. With none chosen in the launcher, the pre-spec says
    so as [CONFIRM: ...], and the held-back loans are not tested until it is answered."""
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    monkeypatch.setenv("POCKETBOOK_MEMORY", str(tmp_path / "memory.yaml"))
    x, b = _book(tmp_path, 6000, test=("UTIL", "TENURE"), hold=())
    ran, res = _run(b, monkeypatch)
    assert not ran.ok
    p = scout.prespec_for(b)
    assert "strata: \"[CONFIRM: the columns to hold fixed" in p.read_text(encoding="utf-8")
    assert ran.problems and all(x.startswith(f"{p.name}: ") for x in ran.problems), ran.problems
    assert "strata" in ran.problems[0] and "[CONFIRM:" in ran.problems[0]
    wb = load_workbook(b)
    assert scout.SHEET in wb.sheetnames and confirm_tab.SHEET not in wb.sheetnames
    assert res is None or res.prespec is None
    assert any(v.startswith("Confirmation waits: ") for v in tabs.runs(b))
    # OC-51: the tree's out-of-time check waits for the pre-spec too: no held-back loan read while it is unanswered
    assert not any("the tree's out-of-time check" in v for v in tabs.runs(b))
    assert _table(b)["UTIL"]["Held fixed"] == "Nothing held"
    # answered: nothing held fixed
    p.write_text(p.read_text(encoding="utf-8").replace(
        'strata: "[CONFIRM: the columns to hold fixed, such as [FICO, CHANNEL]; [] for none]"', "strata: []"),
        encoding="utf-8")
    ran, res = _run(b, monkeypatch)
    assert ran.ok, ran.lines
    assert res.prespec.spec.strata == () and confirm_tab.SHEET in load_workbook(b).sheetnames


# --------------------------------------------------------------------------
# The pieces, one at a time


def test_steps_cut_where_the_curve_steps_and_not_where_it_wobbles():
    flat = [0.07, 0.072, 0.069, 0.071, 0.07, 0.068, 0.071, 0.07]
    w = [1 / 8] * 8
    assert scout.steps(flat, w) == []
    cliff = [0.06, 0.061, 0.059, 0.06, 0.06, 0.13, 0.13, 0.128]
    assert scout.steps(cliff, w) == [4]
    two = [0.11, 0.105, 0.07, 0.07, 0.07, 0.07, 0.17, 0.18]
    assert scout.steps(two, w) == [1, 5]
    # a step on too few loans is not cut
    assert scout.steps(cliff, [0.3, 0.3, 0.2, 0.1, 0.09, 0.005, 0.003, 0.002]) == []


def test_the_edge_sits_where_the_forest_split_most_and_reads_in_two_figures():
    splits = [(0.9012, 50.0), (0.8931, 5.0), (0.95, 1.0), (0.4, 99.0)]
    assert scout.edge(splits, 0.856, 0.914) == 0.9
    assert scout.edge([], 0.856, 0.914) == 0.89               # no split there: the midpoint
    assert scout.round_edge(1.9712, 1.65, 1.98) == 1.97        # 2.0 would put a loan at 1.98 below the edge
    assert scout.round_edge(0.0934, 0.092, 0.1) == 0.093


def test_a_sliver_between_two_close_steps_is_merged():
    import numpy as np
    v = np.array([0.05] * 30 + [0.5] * 900 + [1.98] * 5 + [2.5] * 65, dtype=float)
    grid = [0.05, 0.5, 1.98, 2.5]
    pd = [0.1, 0.07, 0.12, 0.18]
    # the sliver from 1.97 to 2.0 (half a percent of the loans) joins the side whose rate is closer: below it
    assert scout.merge_small([0.1, 1.97, 2.0], v, grid, pd) == [0.1, 2.0]


def test_the_file_is_seeded_and_repeatable_and_reads_back(wide):
    sc = wide["sc"]
    today = date(2026, 9, 27)
    a, b = scout.text(sc, today), scout.text(sc, today)
    assert a == b and confirmatory.fingerprint(a) == confirmatory.fingerprint(b)
    spec = prespec.parse(yaml.safe_load(a), text=a)
    assert [(i.column, i.bins, i.reference_index) for i in spec.inputs] == \
        [(c.name, c.bins, c.reference_index) for c in sc.proposed]
    assert scout.differences(spec, sc) == []


# --------------------------------------------------------------------------
# Without scikit-learn


def test_scouting_is_refused_in_words_without_scikit_learn_and_a_saved_shortlist_still_confirms(tmp_path):
    """scikit-learn is optional (like numpy was before OC-34, the launcher offers it). Simulated missing, as
    test_perm does for numpy: finding is refused by the Control cell that chose it; confirming a saved shortlist
    runs; the launcher starts, says nothing is missing that the cube needs, and offers the add-on."""
    code = f"""
import sys; sys.modules['sklearn'] = None
from pathlib import Path
import yaml
from pocketbook import book, deps, launcher, scout
import test_scout
from test_book_dates import _choose
assert deps.missing() == [], deps.missing()
assert deps.missing_optional() == ['scikit-learn']
assert scout.missing() is not None
x, b = test_scout._book(Path({str(tmp_path)!r}), 3000, test=('UTIL', 'TENURE'))
ran = book.run(b)
print('SCOUT', ran.ok, '|'.join(ran.problems))
spec = {{'prespec': 1, 'written': '2026-09-27', 'outcome': 'BAD_FLAG',
        'inputs': [{{'column': 'UTIL', 'bins': [0.9], 'reference': 0}}], 'strata': ['FICO', 'CHANNEL'],
        'confidence': 0.95, 'holdout': {{'from': '2024-11-02', 'to': '2026-12-31'}},
        'development': {{'from': '2020-01-01', 'to': '2024-11-01'}}}}
(b.parent / 'saved.yaml').write_text(yaml.safe_dump(spec, sort_keys=False))
_choose(b, shortlist='saved.yaml', run_kind='new_variable')
ran = book.run(b)
print('SAVED', ran.ok)
gate = launcher.AddOns()
print('GATE', gate.missing, gate.optional)
"""
    here = Path(__file__).parent
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(here.parent / "src"), str(here)]),
               GIT_CEILING_DIRECTORIES=str(tmp_path), POCKETBOOK_MEMORY=str(tmp_path / "memory.yaml"))
    got = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=here.parent)
    assert got.returncode == 0, got.stderr[-3000:]
    out = {line.split(" ", 1)[0]: line.split(" ", 1)[1] for line in got.stdout.splitlines() if " " in line}
    ok, problems = out["SCOUT"].split(" ", 1)
    assert ok == "False"
    assert problems.startswith("Control!C") and ": Finding new variables needs one add-on: scikit-learn" in problems
    assert out["SAVED"] == "True"
    assert out["GATE"] == "[] ['scikit-learn']"


def test_the_launcher_offers_scikit_learn_only_where_finding_needs_it(tmp_path, monkeypatch):
    monkeypatch.setattr(deps, "missing", lambda: [])
    monkeypatch.setattr(deps, "missing_optional", lambda: ["scikit-learn"])
    x = _extract(tmp_path, 1500)
    flow = launcher.Flow(extract=str(x))
    flow.set_up()
    flow.set_mode("new")
    flow.click("UTIL", "b")
    ok, said = flow.summary()
    assert not ok and said.startswith("One add-on is missing: scikit-learn, which finds new variables (scouting).")
    st = flow.states()
    assert st["next"] == "disabled" and st["install_optional"] == "normal" and st["setup"] == "normal"
    assert flow.gate.start(optional=True) == ["scikit-learn"]
    flow.gate.installing = []
    # a saved shortlist needs no forest: Next is on, and nothing is offered
    spec = tmp_path / "saved.yaml"
    spec.write_text(yaml.safe_dump({"prespec": 1, "written": "2026-09-27", "outcome": "BAD_FLAG",
                                    "inputs": [{"column": "UTIL", "bins": [0.9], "reference": 0}], "strata": [],
                                    "confidence": 0.95, "holdout": {"from": "2025-01-01", "to": "2026-12-31"},
                                    "development": {"from": "2020-01-01", "to": "2024-12-31"}}), encoding="utf-8")
    flow.pick_shortlist(str(spec))
    ok, _ = flow.summary()
    assert ok and flow.states()["install_optional"] == "disabled"
    # the bleed never asks for it
    flow.pick_shortlist(None)
    flow.set_mode("bleed")
    assert flow.states()["install_optional"] == "disabled"


def test_the_lowest_group_is_named_from_its_own_values_and_the_pre_spec_reads_the_name_back():
    """Found 27 Sep 2026 on the bins scouting suggested for income / sales, [0.1, 2]: over values from 0.03 the
    lowest group read "0.0 - 0.0", a range below every value in it. It is named from its own values now, and the
    pre-spec recognises a group named that way, so a run held to it doesn't read as deviating."""
    from pocketbook import engine
    assert engine.band_labels((0.1, 2.0), 0.03, 8.3) == ["0.03 - 0.09", "0.10 - 1.99", "2.00 - 8.30"]
    assert engine.band_labels((620.0, 680.0), 619.5, 850.0) == ["619 - 619", "620 - 679", "680 - 850"]
    raw = {"prespec": 1, "written": "2026-09-27", "outcome": "BAD_FLAG",
           "inputs": [{"column": "income_to_sales", "bins": [0.1, 2], "reference": 1}], "strata": ["FICO"],
           "confidence": 0.95, "holdout": {"from": "2025-01-01", "to": "2025-12-31"},
           "development": {"from": "2022-01-01", "to": "2024-12-31"}}
    ps = prespec.named(prespec.parse(raw), ranges={"income_to_sales": (0.03, 8.3)})
    assert ps.inputs[0].reference == "0.10 - 1.99"
    used = {"outcome": "BAD_FLAG", "inputs": [{"column": "income_to_sales", "bins": [0.1, 2.0],
                                               "reference": "0.10 - 1.99"}],
            "strata": ["FICO"], "confidence": 0.95, "holdout": ps.holdout}
    assert prespec.deviations(ps, used) == []


# --------------------------------------------------------------------------
# OC-51 (the firm, 27 Sep 2026): "import --> tree runs --> tree guesses on 2024 data if 2022-2023 are used to build
# branches --> regress shortlist?". The cutoff is the analyst's; the tree is checked on the loans after it; the
# shortlist is regressed together (tests/test_together.py holds the regression's own arithmetic).


def _held_back(x, cut):
    """The held-back loans by hand: made on or after the cutoff, with a readable outcome, in the extract's order."""
    return [r for r in _rows(x) if date.fromisoformat(r["ORIG_DATE"]) >= cut and r["BAD_FLAG"] in ("0", "1")]


def _num(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return math.nan
    return x


def test_the_trees_out_of_time_auc_is_scikit_learns_on_loans_it_never_saw(wide):
    """The forest grown on every development loan scores the held-back loans, rebuilt here from the extract by hand:
    the same outcomes, the same columns, the same scores, and scikit-learn's own AUC of them."""
    import numpy as np
    from sklearn.metrics import roc_auc_score
    sc = wide["sc"]
    o = sc.oot
    assert o is not None and o.problem is None and o.held_back == sc.holdout
    rows = _held_back(wide["x"], sc.cutoff)
    y = np.array([int(r["BAD_FLAG"]) for r in rows])
    assert (o.loans, o.bad) == (len(rows), int(y.sum())) and list(o.y) == list(y)

    def column(name, rs):
        if name == "income_to_sales":
            return [(_value(r, name) if _value(r, name) is not None else math.nan) for r in rs]
        if name in ("REGION", "CHANNEL"):
            dev = [r for r in _rows(wide["x"]) if date.fromisoformat(r["ORIG_DATE"]) < sc.cutoff
                   and r["BAD_FLAG"] in ("0", "1")]
            levels = sorted({r[name] for r in dev if r[name] != ""})
            return [levels.index(r[name]) if r[name] in levels else math.nan for r in rs]
        vals = [_num(r[name]) for r in rs]
        return [math.nan if name == "FICO" and v < -1000 else v for v in vals]
    X = np.column_stack([column(n, rows) for n in sc.forests["names"]])
    Xh = np.column_stack([X] + [np.array(column(h, rows)) for h in sc.hold])
    plain, held = sc.forests["plain"], sc.forests["held"]
    assert np.allclose(o.scores, plain.predict_proba(X)[:, 1], rtol=0, atol=1e-12)
    assert np.allclose(o.scores_held, held.predict_proba(Xh)[:, 1], rtol=0, atol=1e-12)
    assert o.auc == roc_auc_score(y, o.scores) and o.auc_held == roc_auc_score(y, o.scores_held)
    assert math.isclose(o.auc, roc_auc_score(y, plain.predict_proba(X)[:, 1]), abs_tol=1e-9)
    # the forest that scored them never saw them: it was grown on the development loans alone
    assert plain.n_features_in_ == len(sc.forests["names"]) and sc.forests["dev"][0].shape[0] == sc.n_dev
    # the planted inputs carry the tree on loans it never saw, well past a coin flip
    assert o.auc > 0.55 and o.auc_held > o.auc


def test_a_category_keeps_its_development_numbering_on_the_held_back_loans(wide):
    """A category is given one number per value, in the order of the development loans' values. On held-back loans
    missing a value (here, no Central), every other value keeps its number, so the forest reads them as it learnt
    them."""
    import numpy as np
    sc, res = wide["sc"], wide["res"]
    col = res.config.origination_date
    other = copy.copy(res)
    other.table = copy.copy(res.table)
    other.table.rows = [dict(r, REGION="West") if r["REGION"] == "Central"
                        and date.fromisoformat(str(r[col])[:10]) >= sc.cutoff else r for r in res.table.rows]
    again = copy.copy(sc)
    o = scout.out_of_time(other, again)
    assert again.oot is o and sc.oot is not o and o.problem is None
    rows = [r for r in other.table.rows if date.fromisoformat(str(r[col])[:10]) >= sc.cutoff
            and str(r["BAD_FLAG"]) in ("0", "1")]
    levels = sc.levels["REGION"]
    j = sc.forests["names"].index("REGION")
    X = again.forests["dev"][0]
    assert set(np.unique(X[:, j][~np.isnan(X[:, j])])) == set(range(len(levels)))      # the development numbering
    got = []
    for name in sc.forests["names"]:
        v, _ = scout._values(other, rows, name, next(c.kind for c in sc.candidates if c.name == name),
                             levels if name == "REGION" else None)
        got.append(v)
    want = sc.forests["plain"].predict_proba(np.column_stack(got))[:, 1]
    assert "Central" in levels and np.allclose(o.scores, want, rtol=0, atol=1e-12)


def test_the_out_of_time_check_is_recorded_as_a_touch_of_the_holdout(wide):
    sc, b = wide["sc"], wide["b"]
    o = sc.oot
    entry = tabs.runs(b)
    touched = [v for v in entry if v.startswith(confirmatory.HOLDOUT_MARK)]
    tree = [v for v in touched if "the tree's out-of-time check" in v]
    assert len(tree) == 1 and len(touched) == 2, touched
    assert (f"scored {o.loans:,} loans made {sc.holdout.text()}, after the pre-spec was written" in tree[0]
            and scout.auc_words(sc) in tree[0])
    # after the scouting line: the file was written before the tree read a held-back loan
    assert entry.index(tree[0]) > next(i for i, v in enumerate(entry) if v.startswith("Scouting on"))
    rec = tabs.record(b)
    assert rec["Scouting out of time"] == scout.auc_words(sc)
    # one Run, however many lines say it touched the holdout: counted once
    assert rec["Runs that touched the holdout"] == "1 on Record's Every Run, this one included"


def test_the_one_line_reads_built_then_unseen(wide):
    sc = wide["sc"]
    said = scout.auc_words(sc)
    assert said == (f"Built on loans made {sc.development.text()}: AUC {sc.auc:.2f}. On loans made "
                    f"{sc.holdout.text()}, unseen: {sc.oot.auc:.2f}. With FICO and CHANNEL in the forest too: "
                    f"{sc.auc_held:.2f} built, {sc.oot.auc_held:.2f} unseen.")


def test_new_variables_leads_with_the_tree_then_all_together_then_each_on_its_own(wide, tmp_path_factory):
    from recalc import recalc
    res, sc = wide["res"], wide["sc"]
    j = res.prespec.joint
    ws = load_workbook(wide["b"])[confirm_tab.SHEET]
    where = {}
    for r in range(1, ws.max_row + 1):
        v = ws.cell(row=r, column=confirm_tab.FIRST).value
        if isinstance(v, str) and v not in where:
            where[v] = r
    together = next(k for k in where if k.startswith("All ") and k.endswith("together, on the held-back loans"))
    heads = [r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=confirm_tab.N_CAND).value == "Candidate"]
    assert where["The tree on loans it never saw"] < where[together] < heads[0] < where["Each candidate on its own"] \
        < heads[1]
    assert ws.cell(row=where["The tree on loans it never saw"] + 1, column=confirm_tab.FIRST + 1).value == \
        scout.auc_words(sc)
    # the joint table: a row per group against its reference, the odds ratio together, and per candidate what it adds
    calc = recalc(wide["b"], tmp_path_factory.mktemp("wide_calc"))[confirm_tab.SHEET]
    seen = {}
    r = heads[0] + 1
    cand = None
    while ws.cell(row=r, column=confirm_tab.J_COMP).value:
        cand = ws.cell(row=r, column=confirm_tab.J_CAND).value or cand
        seen[(cand, ws.cell(row=r, column=confirm_tab.J_COMP).value)] = r
        r += 1
    want = [(t.column, f"{g} vs {t.groups[t.ref]}") for t in j.terms for k, g in enumerate(t.groups) if k != t.ref]
    assert list(seen) == want
    for t in j.terms:
        top = seen[(t.column, f"{t.groups[1 if t.ref == 0 else 0]} vs {t.groups[t.ref]}")]
        assert ws.cell(row=top, column=confirm_tab.J_STAT).value == f"{t.lr:.2f} on {t.df}"
        assert ws.cell(row=top, column=confirm_tab.J_PADD).value == pytest.approx(t.p_allowed, rel=1e-12)
        adds = calc.cell(row=top, column=confirm_tab.J_ADDS).value
        assert adds == ("Yes" if t.p_allowed < 0.05 else "No"), (t.column, adds)
        for k, g in enumerate(t.groups):
            if k != t.ref:
                rr = seen[(t.column, f"{g} vs {t.groups[t.ref]}")]
                assert ws.cell(row=rr, column=confirm_tab.J_ODDS).value == round(t.odds[k], 10)
                lo, hi = (math.exp(t.beta[k] + s * 1.959963984540054 * t.se[k]) for s in (-1, 1))
                assert calc.cell(row=rr, column=confirm_tab.J_RANGE).value == f"{lo:.2f}x to {hi:.2f}x"
    # the planted inputs add something net of each other, and the line under the table says so
    assert {t.column for t in j.terms} == PLANTED
    found = calc.cell(row=_row_after(ws, heads[0], "What it found"), column=confirm_tab.FIRST + 1).value
    assert found.startswith("Adds something the others don't: ") and all(c in found for c in PLANTED), found
    # the method note says the two new things once each
    note = {ws.cell(row=r, column=2).value for r in range(3, where["WHAT WAS TESTED"])}
    assert {"The tree, unseen", "All together"} <= note


def _row_after(ws, start: int, label: str) -> int:
    return next(r for r in range(start, ws.max_row + 1) if ws.cell(row=r, column=confirm_tab.FIRST).value == label)


def test_a_blank_cutoff_waits_for_an_answer_like_the_other_judgment_settings(tmp_path, monkeypatch):
    """OC-13: the cutoff is suggested beside the setting and never chosen. Blank, the Run refuses by the cell, and
    no loan is scouted or held back; answered with the suggestion, it runs on the date shown."""
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    monkeypatch.setenv("POCKETBOOK_MEMORY", str(tmp_path / "memory.yaml"))
    x, b = _book(tmp_path, 3000, test=("UTIL", "TENURE"), cutoff=None)
    ws = load_workbook(b)[control.SHEET]
    r = control.row_of(ws, "cutoff")
    cut, _, _ = _suggested(x)
    before = sum(1 for row in _rows(x) if date.fromisoformat(row["ORIG_DATE"]) < cut)
    assert ws.cell(row=r, column=control.CHOOSE_COL).value is None and not ws.row_dimensions[r].hidden
    assert ws.cell(row=r, column=control.SUGGEST_COL).value == (
        f"suggested: {cut.isoformat()} ({before:,} loans before, {3000 - before:,} after)")
    ran, res = _run(b, monkeypatch)
    q = next(s.question for s in control.load_settings() if s.key == "cutoff")
    assert not ran.ok and f'Control!C{r}: "{q}" needs an answer. Pick one, or enter your own in column D.' in \
        ran.problems, ran.problems
    assert not scout.prespec_for(b).exists() and scout.SHEET not in load_workbook(b).sheetnames
    # a date typed under Or your own is used to the day
    _control(b, cutoff=("own", date(2024, 3, 1)))
    ran, res = _run(b, monkeypatch)
    assert ran.ok, ran.lines
    assert res.scout.cutoff == date(2024, 3, 1) and res.prespec.spec.holdout.start == date(2024, 3, 1)
    assert tabs.record(b)["Loans made before this date find the candidates; the rest are held back"] == "2024-03-01"


def test_the_cutoff_is_asked_only_when_scouting(wide, tmp_path):
    """Control shows the cutoff for scouting and folds it away for a saved shortlist and for the bleed."""
    from recalc import recalc
    b = tmp_path / "copy.xlsx"
    shutil.copy(wide["b"], b)
    # blanked after a Run, the cell is shaded and Status says nothing (it read "Same as last Run" on the walk)
    _control(b, cutoff=None)
    ws = recalc(b, tmp_path / "calc")[control.SHEET]
    r = control.row_of(ws, "cutoff")
    assert ws.cell(row=r, column=control.NEED_COL).value == 1
    assert ws.cell(row=r, column=control.STATUS_COL).value in (None, "")
    for changes, hidden in (({}, False), ({"shortlist": "some.yaml", "run_kind": "new_variable"}, True),
                            ({"run_kind": "bleed"}, True)):
        if changes:
            _choose(b, **changes)
        ws = load_workbook(b)[control.SHEET]
        assert ws.row_dimensions[control.row_of(ws, "cutoff")].hidden is hidden, changes
