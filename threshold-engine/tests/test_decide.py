"""The Decide, Thresholds and Summary tabs of the book (decide_tab.py,
thresholds_tab.py, summary_tab.py), and Lines by source, the per-series table
the book renames (workbook.py, round 2).

One set of lines per product and measure (the firm, 15 Oct 2026: "we don't
need to set thresholds on all 3, we need to use all 3 to set appropriate
thresholds"). Decide has one row per product and measure; its Lines set from
picks the source whose history sets the lines; its settings apply to every
source of the row, and its period left out to the source picked.

Decide is where the bank types; Assess's settings and periods-left-out cells
read it. The proof is a twin: the same workbook built without Decide, the same
thing typed on Assess, and every number on Lines by source the same as on the
twin's Thresholds. The two lay the table out differently, so the twin is read
by meaning (``decide_tab.TH_BOOK`` and ``TH_PLAIN``), never by letter.

The test engine (``formulas``) has no SUBTOTAL, which is how Decide knows the
one row its slicers leave visible. So the tests stand in for the slicers by
writing the Shown column themselves, 1 on the row shown and 0 on the rest;
SUBTOTAL and the slicers are proved in Excel itself (tools/check_slicers_in_excel.ps1).
"""
import re
import zipfile

import pytest
from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string as CI
from openpyxl.utils import get_column_letter as L

from conftest import DATA
from threshold_engine import decide_tab as DT
from threshold_engine import keybank_style as K
from threshold_engine.workbook import assess_layout, build, quarter
from test_workbook import recalc

SER = [("Card - Net - Industry", DATA / "cards_nco_ttm.csv"),
       ("Card - Net - Bank", DATA / "home_equity_nco_ttm.csv"),
       ("Mortgage - Net - Industry", DATA / "mortgage_nco_ttm.csv"),
       ("Card - Gross - Industry", DATA / "other_consumer_as_filed_nco_ttm.csv")]
LABELS = [lbl for lbl, _ in SER]
PAIRS = [("Card", "Net"), ("Mortgage", "Net"), ("Card", "Gross")]       # Decide's rows, in order
NAMES = ["Product", "Measure", "Source"]
ABSENT = [{"parts": {"Product": "Mortgage", "Measure": "Net", "Source": "Bank"},
           "why": "The bank's mortgage file was not given (a test note)."}]
SETTINGS = dict(name="N", unit="%", direction="higher_is_worse", frequency="quarterly", smoothing=1,
                floor_at_zero=True, moderate_halfwidth=0.5, low_step=1.0, high_z=2.5, on_the_line="worse",
                half_lives=(), percentiles=(50,), horizon=4, min_history=41)
#: What a per-series row holds, by meaning.
MEANINGS = ("median", "move", "worst", "l2", "l3", "l4", "l5", "quarter", "value", "rating", "rating_name", "refusal")
LBS = DT.LINES_TAB.upper()


def decide_spec(compare=("Bank", "Industry"), lines_from=None):
    return {"names": NAMES, "parts": {lbl: tuple(lbl.split(" - ")) for lbl in LABELS}, "absent": ABSENT,
            "compare": compare, "notes": ["A note the book gave."], "lines_from": lines_from}


@pytest.fixture(scope="module")
def pair(tmp_path_factory):
    d = tmp_path_factory.mktemp("decide")
    with_ = build(d / "decide.xlsx", SER, decide=decide_spec(), **SETTINGS)
    plain = build(d / "plain.xlsx", SER, **SETTINGS)
    return d, with_, plain


def col(info, name):
    return L(info["decide"]["columns"][name])


def at(info, name, i):
    """Decide's cell in column ``name`` on row ``i`` (0-based, PAIRS order)."""
    return "Decide!%s%d" % (col(info, name), info["decide"]["first"] + i)


def typed(src, dst, cells, show=None, info=None):
    """Type into a copy: cells is {'Sheet!A1': value}; show names the rows
    (PAIRS) the slicers leave visible (Shown = 1 on its row, 0 elsewhere)."""
    wb = load_workbook(src)
    for ref, v in cells.items():
        sh, a = ref.split("!")
        wb[sh][a] = v
    if show is not None:
        d = info["decide"]
        for i, pr in enumerate(PAIRS):
            wb["Decide"]["%s%d" % (col(info, "Shown"), d["first"] + i)] = 1 if pr in show else 0
    wb.save(dst)
    return recalc(dst)


def lbs_rows(vals, sheet=LBS, cols=DT.TH_BOOK, n=len(LABELS)):
    return [[vals.get("%s!%s%d" % (sheet, cols[k], 5 + i)) for k in MEANINGS] for i in range(n)]


def plain_rows(vals):
    return lbs_rows(vals, "THRESHOLDS", DT.TH_PLAIN)


def lb(vals, key, row):
    """A cell of Lines by source, by meaning."""
    return vals["%s!%s%d" % (LBS, DT.TH_BOOK[key], row)]


def same(a, b):
    for ra, rb in zip(a, b):
        for x, y in zip(ra, rb):
            if isinstance(x, float) and isinstance(y, float):
                assert x == pytest.approx(y, abs=1e-12)
            else:
                assert x == y


def rate(x, lines, rule="worse", floor=True):
    """A value's rating on four lines, as the workbook rates it (higher is worse)."""
    if floor and x <= 0:
        return 1
    return 1 + sum(1 for ln in lines if (ln <= x if rule == "worse" else ln < x))


def test_untouched_decide_changes_no_number(pair):
    d, w, p = pair
    same(lbs_rows(recalc(w["path"])), plain_rows(recalc(p["path"])))


@pytest.mark.parametrize("setting, assess_col, value", [("How rare High is (z)", "Q", 3.5),
                                                         ("Width of Moderate", "O", 0.25),
                                                         ("Moderate-Low begins", "P", 1.5),
                                                         ("On a line, rate it", "R", "better")])
def test_a_setting_typed_on_decide_applies_to_every_source_of_its_row(pair, setting, assess_col, value):
    """Card, Net is one row on Decide and two series (Industry and Bank): the
    setting typed on the row is the twin's setting typed for both."""
    d, w, p = pair
    dec = typed(w["path"], d / "dz.xlsx", {at(w, setting, 0): value})
    top = assess_layout(4)["set_top"]
    ref = typed(p["path"], d / "pz.xlsx", {"Assess!%s%d" % (assess_col, top): value,
                                           "Assess!%s%d" % (assess_col, top + 1): value})
    same(lbs_rows(dec), plain_rows(ref))
    assert lbs_rows(dec) != plain_rows(recalc(p["path"])) or setting == "On a line, rate it"


def test_a_period_left_out_applies_to_the_source_the_lines_are_set_from(pair):
    """Two rows with a source picked and a period left out, typed out of order;
    Assess lists them in table order, each under the series picked, and Lines
    by source equals the twin."""
    d, w, p = pair
    lay = assess_layout(4)
    dec = typed(w["path"], d / "dl.xlsx", {
        at(w, DT.LINES_FROM, 2): "Industry", at(w, "Leave out from", 2): "2009Q1", at(w, "Leave out to", 2): "2011Q4",
        at(w, "Why left out", 2): "crisis",
        at(w, DT.LINES_FROM, 0): "Bank", at(w, "Leave out from", 0): "2020Q2", at(w, "Leave out to", 0): "2021Q4",
        at(w, "Why left out", 0): "pandemic"})
    lo = lay["lo_top"]
    ref = typed(p["path"], d / "pl.xlsx", {
        "Assess!N%d" % lo: LABELS[1], "Assess!O%d" % lo: "2020Q2", "Assess!P%d" % lo: "2021Q4", "Assess!Q%d" % lo:
        "pandemic", "Assess!N%d" % (lo + 1): LABELS[3], "Assess!O%d" % (lo + 1): "2009Q1",
        "Assess!P%d" % (lo + 1): "2011Q4", "Assess!Q%d" % (lo + 1): "crisis"})
    same(lbs_rows(dec), plain_rows(ref))
    assert [dec["ASSESS!N%d" % (lo + k)] for k in range(3)] == [LABELS[1], LABELS[3], ""]
    assert lbs_rows(dec)[1] != plain_rows(recalc(p["path"]))[1]
    assert lbs_rows(dec)[0] == lbs_rows(recalc(w["path"]))[0]             # Industry's own history is untouched


def test_with_no_source_picked_a_period_left_out_sets_nothing_and_the_row_is_blank(pair):
    d, w, p = pair
    v = typed(w["path"], d / "dn.xlsx", {at(w, "Leave out from", 0): "2020Q2", at(w, "Leave out to", 0): "2021Q4",
                                         at(w, "Why left out", 0): "pandemic"}, show={PAIRS[0]}, info=w)
    same(lbs_rows(v), lbs_rows(recalc(w["path"])))
    info = w["decide"]
    assert v["DECIDE!%s%d" % (col(w, "Check"), info["first"])] == "Pick a source"
    lay = info["layout"]
    assert v["DECIDE!B%d" % lay["headline"]] == "Card, net: no source picked to set the lines yet"
    assert v["DECIDE!I%d" % lay["chip"]] == "No rating: see the Check"
    assert v["DECIDE!B%d" % info["check_row"]] == ("Check: pick the source whose history sets the lines, under "
                                                   "Lines set from.")
    assert v["THRESHOLDS!D5"] == "" and v["THRESHOLDS!H5"] == ""
    t = w["thresholds"]
    # Round 3: an undecided row is blank from Lines set from to Check, but for each source's latest quarter.
    assert all(v["THRESHOLDS!%s5" % t["per"][s]["rating"]] == "" for s in ("Bank", "Industry"))
    assert v["THRESHOLDS!%s5" % t["cols"]["check"]] == "" and v["THRESHOLDS!%s5" % t["cols"]["decision"]] == ""
    assert all(isinstance(v["THRESHOLDS!%s5" % t["per"][s]["latest"]], float) for s in ("Bank", "Industry"))


def test_a_period_left_out_is_drawn_apart_and_said(pair):
    """The quarters left out leave the solid line and form the STONE stretch,
    joined to the quarters either side; the panel and Left out now say so."""
    d, w, p = pair
    info = w["decide"]
    h = info["helpers"]
    third = info["sources"]
    v = typed(w["path"], d / "dlo.xlsx", {
        at(w, DT.LINES_FROM, 0): "Industry", at(w, "Leave out from", 0): "2020Q2", at(w, "Leave out to", 0):
        "2021Q4", at(w, "Why left out", 0): "pandemic"}, show={PAIRS[0]}, info=w)
    q = {v["DECIDE!%s%d" % (h["q"], r)]: r for r in range(2, 200) if v.get("DECIDE!%s%d" % (h["q"], r))}
    num = lambda c_, qq: isinstance(v["DECIDE!%s%d" % (h[c_], q[qq])], float)          # noqa: E731
    k = "pick%d" % third.index("Industry")
    assert not num(k, "2020Q2") and not num(k, "2021Q4") and num(k, "2022Q1")
    assert num("left", "2020Q2") and num("left", "2021Q4")
    assert num("left", "2020Q1") and num("left", "2022Q1")            # joined to its neighbours
    assert not num("left", "2019Q4") and not num("left", "2022Q2")
    lay = info["layout"]
    assert v["DECIDE!D%d" % lay["left_now"]] == ("Left out: 2020Q2 to 2021Q4, pandemic. The chart draws these "
                                                 "quarters in gray; the lines are set without them.")
    kept = v["DECIDE!N%d" % lay["median"]]
    assert re.fullmatch(r"(\d+) of the (\d+) quarters on file are kept\.", kept)
    a, b = map(int, re.findall(r"\d+", kept))
    assert b - a == 7
    assert v["DECIDE!P%d" % info["compare_rows"]["Industry"]] == a


def test_a_half_typed_period_refuses_the_source_picked_in_words(pair):
    d, w, p = pair
    f = w["decide"]["first"]
    v = typed(w["path"], d / "dh.xlsx", {at(w, DT.LINES_FROM, 0): "Bank", at(w, "Leave out from", 0): "2009Q1"})
    assert "not whole" in lb(v, "refusal", 6)
    assert lb(v, "refusal", 5) == ""
    assert v["DECIDE!%s%d" % (col(w, "Check"), f)] == "Refused: see the fix below"
    assert v["DECIDE!%s%d" % (col(w, "Check"), f + 1)] == "Pick a source"
    ck = w["thresholds"]["cols"]["check"]
    assert v["THRESHOLDS!%s5" % ck].startswith("To fix: Finish its row on Decide")
    assert v["THRESHOLDS!H5"] == "" and v["THRESHOLDS!%s5" % w["thresholds"]["per"]["Bank"]["rating"]] == "Refused"


@pytest.mark.parametrize("picked", ["Industry", "Bank"])
def test_the_screen_follows_the_one_row_shown_and_rates_every_source_on_the_lines_picked(pair, picked):
    d, w, p = pair
    info = w["decide"]
    lay = info["layout"]
    v = typed(w["path"], d / ("ds%s.xlsx" % picked), {at(w, DT.LINES_FROM, 0): picked}, show={PAIRS[0]}, info=w)
    rows_ = {"Industry": 5, "Bank": 6}                                 # their rows on Lines by source
    assert v["DECIDE!B%d" % lay["headline"]] == "Card, net: lines set from %s" % picked
    lines = [lb(v, k, rows_[picked]) for k in ("l2", "l3", "l4", "l5")]
    assert lb(v, "refusal", rows_[picked]) == ""
    names = DT.RATINGS
    want = {s: rate(lb(v, "value", rows_[s]), lines) for s in rows_}
    assert v["DECIDE!I%d" % lay["chip"]] == "Bank: %d %s" % (want["Bank"], names[want["Bank"] - 1])
    rows = info["compare_rows"]
    for s in rows_:
        assert v["DECIDE!M%d" % rows[s]] == "%d %s" % (want[s], names[want[s] - 1])
        assert v["DECIDE!N%d" % rows[s]] == pytest.approx(lb(v, "value", rows_[s]))
        assert v["DECIDE!O%d" % rows[s]] == lb(v, "quarter", rows_[s])
    # the source picked rates on its own lines as Lines by source rates it
    assert want[picked] == lb(v, "rating", rows_[picked])
    diff = lb(v, "value", 6) - lb(v, "value", 5)
    assert v["DECIDE!L%d" % lay["compare_line"]] == "Bank is %.2f percentage points %s than Industry." % (
        abs(diff), "higher" if diff >= 0 else "lower")
    other = "Bank" if picked == "Industry" else "Industry"
    assert v["DECIDE!L%d" % rows[picked]] == "━ " + picked and v["DECIDE!L%d" % rows[other]] == "╍ " + other
    assert v["DECIDE!B%d" % info["check_row"]] == "Check: OK, your settings fit the history the lines are set from."
    # Thresholds holds the same lines and the same ratings
    t = w["thresholds"]
    assert [v["THRESHOLDS!%s5" % c] for c in "HIJK"] == pytest.approx(lines)
    assert v["THRESHOLDS!D5"] == picked
    for s in rows_:
        assert v["THRESHOLDS!%s5" % t["per"][s]["rating"]] == "%d %s" % (want[s], names[want[s] - 1])
    # what each source's own history would give, side by side
    g = info["gives_rows"]
    for s in rows_:
        assert [v["DECIDE!%s%d" % (c, g[s])] for c in "MNOP"] == pytest.approx(
            [lb(v, k, rows_[s]) for k in ("l2", "l3", "l4", "l5")])
        assert v["DECIDE!Q%d" % g[s]] == pytest.approx(lb(v, "worst", rows_[s]))


def test_the_check_band_says_why_and_what_to_type(pair):
    d, w, p = pair
    info = w["decide"]
    v = typed(w["path"], d / "db.xlsx", {at(w, DT.LINES_FROM, 0): "Bank", at(w, "How rare High is (z)", 0): -1},
              show={PAIRS[0]}, info=w)
    assert v["DECIDE!B%d" % info["check_row"]] == "Refused: High's z must be above 0"
    assert v["DECIDE!I%d" % info["check_row"]] == "To fix: Type a number above 0 in How rare High is."
    assert v["DECIDE!%s%d" % (col(w, "Check"), info["first"])] == "Refused: see the fix below"
    assert v["DECIDE!I%d" % info["layout"]["chip"]] == "No rating: see the Check"
    ck = w["thresholds"]["cols"]["check"]
    assert v["THRESHOLDS!%s5" % ck] == "To fix: Type a number above 0 in How rare High is."
    assert v["DECIDE!M%d" % info["compare_rows"]["Industry"]] == "No rating"
    # both sources' own lines are refused: the settings are the row's
    assert v["DECIDE!M%d" % info["gives_rows"]["Industry"]] == "Refused"


def test_the_panel_counts_each_rating_as_the_reference_does(pair):
    """Where each rating begins: the quarters kept of the history picked in
    each rating, rated on the lines as scale.py rates them, and the share of
    all kept; the lead source's latest is marked on the rating it takes."""
    from threshold_engine.scale import scale, score
    from threshold_engine.series import check, read_csv
    d, w, p = pair
    lay = w["decide"]["layout"]
    v = typed(w["path"], d / "dp.xlsx", {at(w, DT.LINES_FROM, 0): "Industry"}, show={PAIRS[0]}, info=w)
    pts = check(read_csv(SER[0][1]), "quarterly")
    vals_ = [pt.value for pt in pts]
    ref = scale(vals_, "higher_is_worse", 0.5, 1.0, 2.5, True)
    assert ref["refused"] is None
    want = [0] * 5
    for x in vals_:
        want[score(x, ref["bounds"], "higher_is_worse", "worse", True) - 1] += 1
    first = lay["ratings_first"]
    assert [v["DECIDE!N%d" % (first + k)] for k in range(5)] == want
    for k in range(5):
        assert v["DECIDE!O%d" % (first + k)] == pytest.approx(want[k] / len(vals_))
        if k:
            assert v["DECIDE!M%d" % (first + k)] == pytest.approx(ref["bounds"][k - 1])
    bank = check(read_csv(SER[1][1]), "quarterly")
    latest = score(bank[-1].value, ref["bounds"], "higher_is_worse", "worse", True)
    assert [v["DECIDE!P%d" % (first + k)] for k in range(5)] == [
        "◀ Bank " + quarter(bank[-1].date) if k + 1 == latest else "" for k in range(5)]
    assert v["DECIDE!M%d" % lay["median"]] == pytest.approx(ref["median"])
    assert v["DECIDE!N%d" % lay["median"]] == "%d of the %d quarters on file are kept." % (len(vals_), len(vals_))
    worst = pts[vals_.index(max(vals_))].date
    assert v["DECIDE!N%d" % lay["worst"]] == "Kept in %s. High must begin at or below it." % quarter(worst)
    assert v["DECIDE!L%d" % lay["lines_label"]] == "What the lines rest on: Industry's history, quarters kept"


def test_the_chart_draws_every_source_and_the_one_picked_solid_and_follows_the_window(pair):
    d, w, p = pair
    info = w["decide"]
    h = info["helpers"]
    win = "M%d" % info["layout"]["window"]
    v = typed(w["path"], d / "dw.xlsx", {"Decide!" + win: "Last 20 quarters", at(w, DT.LINES_FROM, 0): "Bank"},
              show={PAIRS[0]}, info=w)
    third = info["sources"]
    rows = range(2, 200)
    got = lambda key: [v.get("DECIDE!%s%d" % (h[key], r)) for r in rows]      # noqa: E731
    nums = lambda xs: [x for x in xs if isinstance(x, float)]                  # noqa: E731
    # the source picked is drawn solid, in its own series only
    assert nums(got("pick%d" % third.index("Bank"))) and not nums(got("pick%d" % third.index("Industry")))
    # every other source is on the chart from the start, dashed; the one picked never is
    assert nums(got("over%d" % third.index("Industry"))) and not nums(got("over%d" % third.index("Bank")))
    first, count = int(v["DECIDE!%s2" % h["fit"]]), v["DECIDE!%s3" % h["fit"]]
    assert count == 20 and v["DECIDE!%s4" % h["fit"]] == first + 19 and v["DECIDE!%s5" % h["fit"]] == 2
    labels = [v["DECIDE!%s%d" % (h["cat"], r)] for r in range(first, first + 20)]
    assert labels[-1] == v["DECIDE!%s%d" % (h["q"], first + 19)] and sum(1 for x in labels if x) == 10
    # each rating's label sits on the last quarter drawn and nowhere else
    for j in range(4):
        lab = got("lab%d" % j)
        assert [r for r, x in zip(rows, lab) if isinstance(x, float)] in ([], [first + 19])
    assert v["DECIDE!B%d" % info["layout"]["section"]] == "Every source over the five rating zones · last 20 quarters"
    # switched off, a source leaves the chart
    off = typed(w["path"], d / "dwo.xlsx", {at(w, DT.LINES_FROM, 0): "Bank",
                                            "Decide!Q%d" % info["compare_rows"]["Industry"]: "No"},
                show={PAIRS[0]}, info=w)
    assert not nums([off.get("DECIDE!%s%d" % (h["over%d" % third.index("Industry")], r)) for r in rows])


def test_no_row_shown_says_so_and_prints_the_books_reason(pair):
    d, w, p = pair
    head = w["decide"]["layout"]["headline"]
    v = typed(w["path"], d / "d0.xlsx", {}, show=set(), info=w)
    msg = v["DECIDE!B%d" % head]
    assert msg.startswith("No product and measure in this workbook match") and ABSENT[0]["why"] in msg
    v2 = typed(w["path"], d / "d2.xlsx", {}, show={PAIRS[0], PAIRS[2]}, info=w)
    assert v2["DECIDE!B%d" % head].startswith("2 rows match")


def test_the_decided_count_and_both_decision_columns(pair):
    d, w, p = pair
    v = typed(w["path"], d / "dc.xlsx", {at(w, "Decision", 0): "Accept these lines", at(w, DT.LINES_FROM, 0): "Bank",
                                         at(w, "Decision", 2): "Reject"})
    assert v["DECIDE!L1"] == "Decided: 2 of 3 · accepted 1 · rejected 1"
    dc = w["thresholds"]["cols"]["decision"]
    # Round 3: a row with no source picked and nothing decided is blank; a decision typed shows.
    assert [v["THRESHOLDS!%s%d" % (dc, 5 + i)] for i in range(3)] == ["Accept these lines", "", "Reject"]
    # on Lines by source the decision shows on the source the lines are set from
    assert [lb(v, "decision", 5 + i) for i in range(4)] == ["", "Accept these lines", "", ""]


def test_a_starting_source_some_row_lacks_is_refused(tmp_path):
    with pytest.raises(ValueError, match="Mortgage - Net, Card - Gross"):
        build(tmp_path / "x.xlsx", SER, decide=decide_spec(lines_from="Bank"), **SETTINGS)
    with pytest.raises(ValueError, match="decide needs lines_from"):
        spec = decide_spec()
        del spec["lines_from"]
        build(tmp_path / "y.xlsx", SER, decide=spec, **SETTINGS)


def test_every_reference_to_the_per_series_table_follows_its_new_title(pair):
    """The per-series table is built as Thresholds and renamed Lines by
    source; nothing but the tabs built after the rename (Thresholds and
    Summary) reads the new Thresholds, and nothing recalculates to an error
    other than the #N/A the charts draw as gaps."""
    d, w, p = pair
    wb = load_workbook(w["path"])
    after = {"THRESHOLDS", "SUMMARY"}
    stray = [(ws.title, c.coordinate) for ws in wb.worksheets if ws.title.upper() not in after
             for row in ws.iter_rows() for c in row
             if isinstance(c.value, str) and c.value.startswith("=") and re.search(r"(?<![\w'])Thresholds!", c.value)]
    assert not stray, stray[:5]
    assert all("Thresholds!" not in (dv.formula1 or "") for ws in wb.worksheets for dv in
               ws.data_validations.dataValidation if ws.title != "Thresholds")
    # The engine has no SUBTOTAL: stand in for the slicers, as every test here does.
    v = typed(w["path"], d / "dr.xlsx", {at(w, DT.LINES_FROM, 0): "Bank"}, show={PAIRS[0]}, info=w)
    errs = [k for k, x in v.items() if str(x).startswith("#") and str(x) != "#N/A"]
    assert not errs, errs[:5]


def test_decide_is_laid_out_to_round_3(pair):
    """docs/design/round-3/handoff/README.md, Decide: the columns in pixels
    (L:Q the right panel's), the slicer rows 4-7 at 15 / 18 / 18 / 18 pt and
    every row under them one lower than round 2's, the table's header in 9."""
    d, w, p = pair
    ws = load_workbook(w["path"])["Decide"]
    lay = w["decide"]["layout"]
    px = {c: round(ws.column_dimensions[c].width * 7) for c in "ABCDEFGHIJKLMNOPQ"}
    assert px == {"A": 16, "B": 110, "C": 200, "D": 150, "E": 130, "F": 84, "G": 84, "H": 84, "I": 74, "J": 80,
                  "K": 80, "L": 220, "M": 130, "N": 110, "O": 90, "P": 90, "Q": 120}
    heights = {r: ws.row_dimensions[r].height for r in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, lay["headline"],
                                                        lay["check"], lay["section"], lay["chart_end"])}
    assert heights == {1: 25.5, 2: 15, 3: 6, 4: 15, 5: 18, 6: 18, 7: 18, 8: 6, 9: 27, 10: 34.5,
                       lay["headline"]: 30, lay["check"]: 25.5, lay["section"]: 16.5, lay["chart_end"]: 16.5}
    tbl = ws.tables[DT.TABLE]
    assert tbl.ref == "B9:Q%d" % lay["last"] and lay["last"] == 9 + len(PAIRS)
    assert [ws.cell(9, c).value for c in range(2, 6)] == ["Product", "Measure", DT.LINES_FROM, "Decision"]
    assert all(ws.cell(10, c).fill.fgColor.rgb.endswith(K.INPUT) for c in range(CI("D"), CI("M") + 1))
    assert all(ws.cell(10, c).number_format == ";;;" for c in range(CI("O"), CI("Q") + 1))
    # the slicers: Product three buttons to a row over B:E, Measure five over F:Q, rows 3 to 8
    assert DT.SLICER_ANCHORS == ((1, 2, 5, 8), (5, 2, 17, 8)) and DT.SLICER_COLUMNS == (3, 5)
    # the book's rows: 35 products and measures, three sources
    big = DT.layout(35, 3, True)
    assert (big["headline"], big["check"], big["section"], big["chart_top"], big["chart_end"], big["window"],
            big["gives_first"], big["history"], big["pack_line"]) == (46, 47, 49, 50, 67, 62, 71, 75, 68)
    # no peer tabs in this workbook, so no pack line under the chart
    assert ws.cell(lay["pack_line"], 2).value is None
    anchor = ws._charts[0].anchor
    assert (anchor._from.col, anchor._from.row, anchor.to.col, anchor.to.row) == (1, lay["chart_top"] - 1, 11,
                                                                                 lay["chart_end"])


def test_lines_by_source_and_thresholds_are_laid_out(pair):
    d, w, p = pair
    wb = load_workbook(w["path"])
    assert wb.sheetnames[:4] == ["Summary", "Decide", "Thresholds", DT.LINES_TAB]
    ws = wb[DT.LINES_TAB]
    T = DT.TH_BOOK
    assert [ws.cell(4, c).value for c in range(2, 17)] == [
        "Product", "Measure", "Source", "Median kept", "Yearly move", "Worst kept", "2 Moderate-Low",
        "3 Moderate", "4 Moderate-High", "5 High", "Quarter", "Value", "Rating", "Decision", "Check"]
    assert ws.freeze_panes == "E5"
    # Round 3: a reference tab; values 0.00; the widths of the hand-off.
    assert ws["B1"].font.size == 14 and ws.cell(4, 2).fill.fgColor.rgb.endswith(K.MIST)
    assert all(ws["%s5" % T[k]].number_format == "0.00" for k in ("median", "l2", "l5", "value"))
    assert {c: ws.column_dimensions[c].width for c in "BCDEP"} == {"B": 20.71, "C": 30.14, "D": 20.71, "E": 9.57,
                                                                  "P": 36.43}
    assert ws["%s5" % T["check"]].alignment.wrap_text
    assert [(ws.cell(5 + i, 1).value, tuple(ws.cell(5 + i, c).value for c in (2, 3, 4))) for i in range(4)] == [
        (lbl, tuple(lbl.split(" - "))) for lbl in LABELS]
    a, b = DT.TH_HIDDEN
    assert all(ws.column_dimensions[L(c)].hidden for c in range(CI(a), CI(b) + 1))
    cf = {str(r.sqref): [x.formula for x in r.rules] for r in ws.conditional_formatting}
    assert cf["%s5:%s8" % (T["product"], T["product"])] == [["$B5=$B4"]]
    th = wb["Thresholds"]
    t = w["thresholds"]
    assert [th.cell(4, c).value for c in range(2, 12)] == [
        "Product", "Measure", DT.LINES_FROM, "Median kept", "Yearly move", "Worst kept", "2 Moderate-Low",
        "3 Moderate", "4 Moderate-High", "5 High"]
    assert [th["%s4" % t["per"][s][k]].value for s in ("Bank", "Industry") for k in ("latest", "rating")] == [
        "Bank latest", "Bank rating", "Industry latest", "Industry rating"]
    assert [(th.cell(5 + i, 2).value, th.cell(5 + i, 3).value) for i in range(3)] == PAIRS
    assert th.freeze_panes == "D5" and th.auto_filter.ref == "B4:%s7" % t["cols"]["check"]
    h1, h2 = t["hidden"]
    assert all(th.column_dimensions[L(c)].hidden for c in range(CI(h1), CI(h2) + 1))
    assert th["%s6" % t["per"]["Bank"]["rating"]].value is None                  # Mortgage has no Bank: blank
    assert {c: th.column_dimensions[c].width for c in "BCDE"} == {"B": 20.71, "C": 32.43, "D": 20.14, "E": 9.0}
    assert th[t["count"]].value.startswith('="Lines picked: "') and th["H5"].number_format == "0.00"


def test_the_book_has_two_slicers_of_button_rows_and_no_filter_arrows(pair):
    d, w, p = pair
    z = zipfile.ZipFile(w["path"])
    sl = z.read("xl/slicers/slicer1.xml").decode()
    got = re.findall(r'<slicer name="(\w+)"[^>]*? columnCount="(\d+)" style="(\w+)" rowHeight="(\d+)"', sl)
    assert got == [("Pick1", "3", "SlicerStyleOther2", "182880"), ("Pick2", "5", "SlicerStyleOther2", "182880")]
    table = next(t for t in (z.read(n).decode() for n in z.namelist() if n.startswith("xl/tables/"))
                 if 'displayName="Decisions"' in t)
    assert table.count('hiddenButton="1"') == len(DT.FIXED) + 2


def test_summary_reads_thresholds_and_marks_what_is_not_there(pair):
    d, w, p = pair
    ws = load_workbook(w["path"])["Summary"]
    s = w["summary"]
    assert s["sources"] == ["Bank", "Industry"] and s["dropped"] == []
    # Round 3: no Product column; each product is a header row over its measures.
    assert [ws.cell(5, c).value for c in range(2, 8)] == ["Measure", "Latest", "Rating", "Points", "Latest", "Rating"]
    assert ws.cell(4, 3).value == "Bank" and ws.cell(4, 5).value == "vs Industry" and ws.cell(4, 6).value == "Industry"
    (bl, br), (il, ir), pt = s["columns"]["Bank"], s["columns"]["Industry"], s["columns"]["points"]
    assert s["heads"]["Card"] == (6, 2) and ws.cell(6, 2).value == "Card" and ws.cell(6, 2).font.b
    r, base = s["placed"][("Card", "Net")]
    assert (r, base) == (7, 2) and ws.cell(r, 2).value == "Net"
    assert {c: ws.column_dimensions[c].width for c in "BCDEFG"} == {"B": 36.43, "C": 8.43, "D": 17.0, "E": 7.86,
                                                                   "F": 7.29, "G": 15.29}
    assert ws.row_dimensions[6].height == 16.5 and ws.row_dimensions[7].height == 15.75
    v0 = recalc(w["path"])
    assert v0["SUMMARY!%s%d" % (L(ir), r)] == "—" and v0["SUMMARY!%s%d" % (L(br), r)] == "—"
    assert v0["SUMMARY!" + s["count"]] == "Lines picked: 0 of 3 · Bank rated 4 or 5: 0 · refused: 0"
    v = typed(w["path"], d / "su.xlsx", {at(w, DT.LINES_FROM, 0): "Industry"})
    assert v["SUMMARY!%s%d" % (L(il), r)] == pytest.approx(lb(v, "value", 5))
    assert v["SUMMARY!%s%d" % (L(bl), r)] == pytest.approx(lb(v, "value", 6))
    lines = [lb(v, k, 5) for k in ("l2", "l3", "l4", "l5")]
    for col_, row_ in ((ir, 5), (br, 6)):
        k = rate(lb(v, "value", row_), lines)
        assert v["SUMMARY!%s%d" % (L(col_), r)] == "%d %s" % (k, DT.RATINGS[k - 1])
    assert v["SUMMARY!%s%d" % (L(pt), r)] == pytest.approx(lb(v, "value", 6) - lb(v, "value", 5))
    # Card has two rows and goes left; Mortgage goes right, past the gutter.
    assert s["placed"][("Card", "Gross")] == (r + 1, 2)
    mr, mb = s["placed"][("Mortgage", "Net")]
    assert mb == 2 + 6 + 1 and s["heads"]["Mortgage"] == (6, mb) and ws.cell(mr, mb).value == "Net"
    # A source with no series for the row: blank.
    assert ws.cell(mr, mb + br - 2).value is None and ws.cell(mr, mb + bl - 2).value is None
    # Three footnotes: rating, points, nothing else (the book's notes are on Sources).
    notes = [ws.cell(r_, 2).value for r_ in range(s["notes"], ws.max_row + 1) if ws.cell(r_, 2).value]
    assert [n_.split(":")[0] for n_ in notes] == ["Rating", "Points"]
    assert all(ws.cell(s["notes"] + i, 2).font.size == 10 for i in range(2))


ATTN = [("A - Net - Bank", DATA / "other_consumer_as_filed_nco_ttm.csv"),
        ("A - Net - Peer", DATA / "cards_nco_ttm.csv"),
        ("B - Net - Bank", DATA / "other_consumer_with_auto_nco_ttm.csv"),
        ("C - Net - Bank", DATA / "cards_nco_ttm.csv"),
        ("D - Net - Bank", DATA / "home_equity_nco_ttm.csv")]


@pytest.fixture(scope="module")
def attention(tmp_path_factory):
    """Every row's lines set from the bank's own history from the start."""
    d = tmp_path_factory.mktemp("attention")
    spec = {"names": NAMES, "parts": {lbl: tuple(lbl.split(" - ")) for lbl, _ in ATTN}, "absent": [],
            "compare": ("Bank", "Peer"), "notes": [], "lines_from": "Bank"}
    info = build(d / "a.xlsx", ATTN, decide=spec, **SETTINGS)
    return d, info


def _attention_read(v, s):
    a = s["attention"]
    keys = ("measure", "latest", "rating", "product")
    got = [tuple(v["SUMMARY!%s%d" % (L(a["columns"][k]), r)] for k in keys) for r in a["rows"]]
    return [g for g in got if g[0]]


def test_a_series_rated_4_or_5_is_listed_by_rating_then_value(attention):
    d, info = attention
    v = recalc(info["path"])
    s = info["summary"]
    rows = {lbl: 5 + i for i, (lbl, _) in enumerate(ATTN)}
    bank = [lbl for lbl, _ in ATTN if lbl.endswith("Bank")]
    want = sorted(((lb(v, "rating", rows[l]), lb(v, "value", rows[l]), l) for l in bank
                   if lb(v, "rating", rows[l]) not in ("", None) and lb(v, "rating", rows[l]) >= 4),
                  key=lambda t: (-t[0], -t[1]))
    assert [l for _, _, l in want] == ["A - Net - Bank", "B - Net - Bank"]     # the data rate them 4
    listed = _attention_read(v, s)
    assert listed == [("Net", pytest.approx(j), "%d %s" % (k, lb(v, "rating_name", rows[l])),
                       "%s · lines from Bank" % l[0]) for k, j, l in want]
    sheet = load_workbook(info["path"])["Summary"]
    # Round 3: under the left panel.
    assert sheet.cell(s["attention"]["head"], s["panels"][0]).value == "Needs your attention · Bank rated 4 or 5"
    assert v["SUMMARY!" + s["count"]] == "Lines picked: 4 of 4 · Bank rated 4 or 5: 2 · refused: 0"


def test_a_refused_series_is_counted_and_not_listed(attention):
    d, info = attention
    s = info["summary"]
    z = col(info, "How rare High is (z)")
    f = info["decide"]["first"]
    cells = {"Decide!%s%d" % (z, f): 50, "Decide!%s%d" % (z, f + 3): 50}        # rows A and D
    v = typed(info["path"], d / "refused.xlsx", cells)
    assert lb(v, "refusal", 5).startswith("Refused") and lb(v, "refusal", 9).startswith("Refused")
    listed = _attention_read(v, s)
    assert [x[3].split(" · ")[0] for x in listed] == ["B"]
    assert v["SUMMARY!" + s["count"]] == "Lines picked: 4 of 4 · Bank rated 4 or 5: 1 · refused: 2"
    # None rated 4 or 5: the first row says so.
    v2 = typed(info["path"], d / "none.xlsx", {"Decide!%s%d" % (z, f + k): 50 for k in range(4)})
    assert _attention_read(v2, s)[0][0] == "None rated 4 or 5."


def test_more_leave_outs_than_rows_is_said(tmp_path):
    from threshold_engine.assess_tab import LO_ROWS
    ser = [("P%d - M - S" % k, DATA / "cards_nco_ttm.csv") for k in range(LO_ROWS + 1)]
    spec = {"names": NAMES, "parts": {lbl: tuple(lbl.split(" - ")) for lbl, _ in ser}, "absent": [],
            "compare": None, "notes": [], "lines_from": "S"}
    info = build(tmp_path / "many.xlsx", ser, decide=spec, **SETTINGS)["decide"]
    wb = load_workbook(tmp_path / "many.xlsx")
    c = info["columns"]
    for i in range(LO_ROWS + 1):
        r = info["first"] + i
        wb["Decide"]["%s%d" % (L(c["Leave out from"]), r)] = "2009Q1"
        wb["Decide"]["%s%d" % (L(c["Leave out to"]), r)] = "2010Q4"
        wb["Decide"]["%s%d" % (L(c["Why left out"]), r)] = "x"
    wb.save(tmp_path / "many2.xlsx")
    v = recalc(tmp_path / "many2.xlsx")
    assert v["DECIDE!B%d" % info["check_row"]].startswith("More than %d rows" % LO_ROWS)


@pytest.mark.parametrize("names, err", [(["Product", "Measure"], "exactly three"),
                                        (["Product", "Measure", "Decision"], "can't name a part"),
                                        (["Product", "Measure", "product"], "three different")])
def test_bad_part_names_are_refused(tmp_path, names, err):
    spec = decide_spec()
    spec["names"] = names
    with pytest.raises(ValueError, match=err):
        build(tmp_path / "x.xlsx", SER, decide=spec, **SETTINGS)


def test_a_label_must_be_its_parts_joined(tmp_path):
    spec = decide_spec()
    spec["parts"]["Card - Net - Bank"] = ("Card", "Net", "Bank B")
    with pytest.raises(ValueError, match="should be labelled"):
        build(tmp_path / "x.xlsx", SER, decide=spec, **SETTINGS)


def test_every_summary_and_decide_heading_is_defined_in_the_glossary(pair):
    """Every column label on Summary, the attention block's heading, and the
    headings Decide adds for the one set of lines have a Glossary entry; the
    part names are the book's own and need none."""
    from threshold_engine.glossary import TERMS
    d, w, p = pair
    ws = load_workbook(w["path"])["Summary"]
    terms = {t for t, _, _ in TERMS}
    heads = {ws.cell(5, c).value for c in range(1, ws.max_column + 1) if ws.cell(5, c).value} - set(NAMES)
    heads.add(ws.cell(w["summary"]["attention"]["head"], w["summary"]["panels"][0]).value.split(" · ")[0])
    assert heads == {"Latest", "Rating", "Points", "Needs your attention"} and heads <= terms
    assert {DT.LINES_FROM, DT.LINES_TAB, "Thresholds", "Rating on these lines", "Pick a source",
            "What each source's own history would give", "Quarters kept", "Worst kept"} <= terms


def test_without_a_compare_pair_the_first_source_leads_and_there_are_no_points():
    from threshold_engine import summary_tab as SU
    parts = {lbl: tuple(lbl.split(" - ")) for lbl in LABELS}
    lay = SU.layout(LABELS, parts, None)
    assert lay["sources"] == ["Industry", "Bank"] and "points" not in lay["offsets"] and lay["width"] == 5
    lay = SU.layout(LABELS, parts, ("Bank", "Industry"))
    assert lay["sources"] == ["Bank", "Industry"] and lay["offsets"]["points"] == 3


def test_the_panels_split_where_the_taller_is_shortest():
    """Round 3: the book's products, counted with a header row each, split
    Credit card, Mortgage, Home equity | the rest (28 rows against 35)."""
    from threshold_engine import summary_tab as SU
    blocks = [("Credit card", 11), ("Mortgage", 7), ("Home equity", 7), ("Other consumer", 10), ("Auto", 7),
              ("All consumer", 7), ("Credit card + Other consumer", 7)]
    assert SU.split_panels(blocks) == (["Credit card", "Mortgage", "Home equity"],
                                       ["Other consumer", "Auto", "All consumer", "Credit card + Other consumer"])


NARROW = SER + [("Card - Min - Wide", DATA / "cards_nco_ttm.csv")] + [
    ("P%d - Net - Industry" % k, DATA / "cards_nco_ttm.csv") for k in range(3)]


@pytest.fixture(scope="module")
def narrow(tmp_path_factory):
    """A source with one series, on a row nothing else covers: no column on
    Summary or Thresholds, a strip in Summary's row 2."""
    d = tmp_path_factory.mktemp("narrow")
    spec = {"names": NAMES, "parts": {lbl: tuple(lbl.split(" - ")) for lbl, _ in NARROW}, "absent": [],
            "compare": ("Bank", "Industry"), "notes": [], "lines_from": None}
    return d, build(d / "n.xlsx", NARROW, decide=spec, **SETTINGS)


def test_a_source_on_few_rows_gets_no_column_and_a_live_strip(narrow):
    d, info = narrow
    s, t = info["summary"], info["thresholds"]
    assert s["sources"] == ["Bank", "Industry"] and s["dropped"] == ["Wide"]
    assert t["shown"] == ["Bank", "Industry"] and t["dropped"] == ["Wide"]
    wb = load_workbook(info["path"])
    ws, th = wb["Summary"], wb["Thresholds"]
    # No column for Wide on Thresholds; its cells are hidden workings.
    heads = [th.cell(4, c).value for c in range(1, CI(t["cols"]["check"]) + 1)]
    assert not any("Wide" in str(h) for h in heads)
    assert th.column_dimensions[t["per"]["Wide"]["latest"]].hidden
    # The row only Wide covers says so where the bank's rating would be.
    r, base = s["placed"][("Card", "Min")]
    assert ws.cell(r, base + s["columns"]["Bank"][1] - 2).value == "Wide only"
    strip = s["strips"][0]
    assert strip["source"] == "Wide" and strip["row"] == 2
    assert ws[strip["text"]].value.startswith('="Wide · Card · Min · "&IF(ISNUMBER(Thresholds!')
    assert ws[strip["text"]].alignment.horizontal == "right"
    # Live: the value is the series' own latest on Lines by source; no lines picked reads "—".
    v = recalc(info["path"])
    row = 5 + [lbl for lbl, _ in NARROW].index("Card - Min - Wide")
    assert v["SUMMARY!" + strip["text"]] == "Wide · Card · Min · %.2f%% · %s · rating —" % (
        lb(v, "value", row), lb(v, "quarter", row))
    notes = [ws.cell(r_, 2).value for r_ in range(s["notes"], s["notes"] + 3)]
    assert notes[2] == "Wide: its latest quarter and its own lines are on Lines by source."


def test_backtest_folds_into_lines_by_source(pair):
    """The book's fold (fold_backtest): Backtest's three summary columns and
    its averages by rating join Lines by source past the hidden workings, the
    tab goes, and nothing recalculates to an error."""
    from threshold_engine.workbook import fold_backtest
    d, w, p = pair
    wb = load_workbook(w["path"])
    bt = wb["Backtest"]
    want = {}
    for r in range(5, 5 + 2 * len(LABELS)):
        if bt.cell(r, 5).value == "none":
            want[tuple(bt.cell(r, c).value for c in (2, 3, 4))] = [bt.cell(r, c).value for c in range(6, 11)]
    assert want
    got = fold_backtest(wb)
    assert "Backtest" not in wb.sheetnames
    assert got["columns"] == {"spearman_value": "AB", "spearman_change": "AC", "tested": "AD"}
    assert got["by_rating"] == ["AE", "AF"] and got["horizon"] == 4       # one percentile: two ratings
    ws = wb[DT.LINES_TAB]
    assert [ws[c + "4"].value for c in ("AB", "AC", "AD", "AE", "AF")] == [
        "Spearman, value", "Spearman, change", "Quarters tested", "1 Low", "2 Moderate-Low"]
    assert ws["AB3"].value == "How predictive, 4 quarters ahead"
    assert ws.column_dimensions["AE"].hidden and ws.column_dimensions["AE"].outline_level == 1
    assert not ws.column_dimensions["AB"].hidden
    for r in range(5, 5 + len(LABELS)):
        key = tuple(ws.cell(r, c).value for c in (2, 3, 4))
        vals = [ws[c + str(r)].value for c in ("AB", "AC", "AE", "AF", "AD")]
        if key in want:
            assert vals == want[key]
        else:
            assert vals[:2] == [None, None] and vals[4] == 0
    assert ws["AB5"].number_format == "0.00" and ws["AD5"].number_format == "0"
    # The engine has no SUBTOTAL: stand in for the slicers, as every test here does.
    for i in range(len(PAIRS)):
        wb["Decide"]["%s%d" % (col(w, "Shown"), w["decide"]["first"] + i)] = 1 if i == 0 else 0
    wb.save(d / "folded.xlsx")
    v = recalc(d / "folded.xlsx")
    errs = [k for k, x in v.items() if str(x).startswith("#") and str(x) != "#N/A"]
    assert not errs, errs[:5]
