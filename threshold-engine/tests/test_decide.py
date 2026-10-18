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
            "compare": compare, "notes": ["A note the book gave."], "lines_from": lines_from, "kind": "consumer"}


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


def test_with_no_source_picked_a_period_left_out_sets_nothing_and_the_row_says_pick(pair):
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
    assert all(v["THRESHOLDS!%s5" % t["per"][s]["rating"]] == "Pick a source" for s in ("Bank", "Industry"))
    assert v["THRESHOLDS!%s5" % t["cols"]["check"]] == "Pick a source under Lines set from on Decide."


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
    assert [v["THRESHOLDS!%s%d" % (dc, 5 + i)] for i in range(3)] == ["Accept these lines", "Not decided", "Reject"]
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


def test_decide_is_laid_out_to_round_2(pair):
    d, w, p = pair
    ws = load_workbook(w["path"])["Decide"]
    lay = w["decide"]["layout"]
    widths = {c: round(ws.column_dimensions[c].width, 2) for c in "ABCDEFGHIJKLMNOPQ"}
    assert widths == {"A": 1.57, "B": 16.43, "C": 20.71, "D": 17.86, "E": 17.86, "F": 11.29, "G": 11.29,
                      "H": 11.29, "I": 9.86, "J": 10.71, "K": 10.71, "L": 27.86, "M": 30.71, "N": 15.0,
                      "O": 13.57, "P": 13.57, "Q": 14.43}
    heights = {r: ws.row_dimensions[r].height for r in (1, 2, 3, 4, 5, 6, 7, 8, 9, lay["headline"],
                                                        lay["check"], lay["section"], lay["chart_end"])}
    assert heights == {1: 25.5, 2: 15, 3: 6, 4: 19.5, 5: 19.5, 6: 19.5, 7: 6, 8: 27, 9: 34.5, lay["headline"]: 30,
                       lay["check"]: 25.5, lay["section"]: 16.5, lay["chart_end"]: 16.5}
    tbl = ws.tables[DT.TABLE]
    assert tbl.ref == "B8:Q%d" % lay["last"] and lay["last"] == 8 + len(PAIRS)
    assert [ws.cell(8, c).value for c in range(2, 6)] == ["Product", "Measure", DT.LINES_FROM, "Decision"]
    assert all(ws.cell(9, c).fill.fgColor.rgb.endswith(K.INPUT) for c in range(CI("D"), CI("M") + 1))
    assert all(ws.cell(9, c).number_format == ";;;" for c in range(CI("O"), CI("Q") + 1))
    # the book's rows: 35 products and measures, three sources
    big = DT.layout(35, 3, True)
    assert (big["headline"], big["check"], big["section"], big["chart_top"], big["chart_end"], big["window"],
            big["gives_first"], big["history"]) == (45, 46, 48, 49, 66, 61, 70, 74)
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
        "Product", "Measure", "Source", "Median kept", "Typical yearly move", "Worst kept", "2 Moderate-Low",
        "3 Moderate", "4 Moderate-High", "5 High", "Quarter", "Value", "Rating", "Decision", "Check"]
    assert ws.freeze_panes == "E5"
    assert [(ws.cell(5 + i, 1).value, tuple(ws.cell(5 + i, c).value for c in (2, 3, 4))) for i in range(4)] == [
        (lbl, tuple(lbl.split(" - "))) for lbl in LABELS]
    a, b = DT.TH_HIDDEN
    assert all(ws.column_dimensions[L(c)].hidden for c in range(CI(a), CI(b) + 1))
    cf = {str(r.sqref): [x.formula for x in r.rules] for r in ws.conditional_formatting}
    assert cf["%s5:%s8" % (T["product"], T["product"])] == [["$B5=$B4"]]
    th = wb["Thresholds"]
    t = w["thresholds"]
    assert [th.cell(4, c).value for c in range(2, 12)] == [
        "Product", "Measure", DT.LINES_FROM, "Median kept", "Typical yearly move", "Worst kept", "2 Moderate-Low",
        "3 Moderate", "4 Moderate-High", "5 High"]
    assert [th["%s4" % t["per"][s][k]].value for s in ("Bank", "Industry") for k in ("latest", "rating")] == [
        "Bank latest", "Bank rating", "Industry latest", "Industry rating"]
    assert [(th.cell(5 + i, 2).value, th.cell(5 + i, 3).value) for i in range(3)] == PAIRS
    assert th.freeze_panes == "E5" and th.auto_filter.ref == "B4:%s7" % t["cols"]["check"]
    h1, h2 = t["hidden"]
    assert all(th.column_dimensions[L(c)].hidden for c in range(CI(h1), CI(h2) + 1))
    assert th["%s6" % t["per"]["Bank"]["rating"]].value == "Not in this workbook"         # Mortgage has no Bank


def test_the_book_has_two_slicers_of_button_rows_and_no_filter_arrows(pair):
    d, w, p = pair
    z = zipfile.ZipFile(w["path"])
    sl = z.read("xl/slicers/slicer1.xml").decode()
    got = re.findall(r'<slicer name="(\w+)"[^>]*? columnCount="(\d+)" style="(\w+)" rowHeight="(\d+)"', sl)
    assert got == [("Pick1", "3", "SlicerStyleOther2", "228600"), ("Pick2", "4", "SlicerStyleOther2", "228600")]
    table = next(t for t in (z.read(n).decode() for n in z.namelist() if n.startswith("xl/tables/"))
                 if 'displayName="Decisions"' in t)
    assert table.count('hiddenButton="1"') == len(DT.FIXED) + 2


def test_summary_reads_thresholds_and_marks_what_is_not_there(pair):
    d, w, p = pair
    ws = load_workbook(w["path"])["Summary"]
    s = w["summary"]
    assert s["sources"] == ["Bank", "Industry"]
    assert [ws.cell(5, c).value for c in range(2, 9)] == ["Product", "Measure", "Latest", "Rating", "Points",
                                                          "Latest", "Rating"]
    assert ws.cell(4, 4).value == "Bank" and ws.cell(4, 6).value == "vs Industry" and ws.cell(4, 7).value == "Industry"
    (bl, br), (il, ir), pt = s["columns"]["Bank"], s["columns"]["Industry"], s["columns"]["points"]
    r, base = s["placed"][("Card", "Net")]
    assert base == 2 and ws.cell(r, 2).value == "Card" and ws.cell(r, 3).value == "Net"
    v0 = recalc(w["path"])
    assert v0["SUMMARY!%s%d" % (L(ir), r)] == "Pick a source" and v0["SUMMARY!%s%d" % (L(br), r)] == "Pick a source"
    assert v0["SUMMARY!" + s["count"]] == "Bank: 0 rated 4 or 5 · 0 refused · 1 with no source picked"
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
    assert mb == 2 + 7 + 1 and ws.cell(mr, mb).value == "Mortgage"
    assert ws.cell(mr, mb + br - 2).value == "Not in this workbook"
    notes = [ws.cell(r_, 2).value for r_ in range(s["notes"], ws.max_row + 1)]
    assert "Not in this workbook: " + ABSENT[0]["why"] in notes and "A note the book gave." in notes


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
            "compare": ("Bank", "Peer"), "notes": [], "lines_from": "Bank", "kind": "consumer"}
    info = build(d / "a.xlsx", ATTN, decide=spec, **SETTINGS)
    return d, info


def _attention_read(v, s):
    a, base = s["attention"], s["panels"][1]
    rate_ = base + s["columns"]["Bank"][1] - 2
    got = [(v["SUMMARY!%s%d" % (L(base), r)], v["SUMMARY!%s%d" % (L(rate_), r)],
            v["SUMMARY!%s%d" % (L(rate_ + 1), r)]) for r in a["rows"]]
    return [g for g in got if g[0]], v["SUMMARY!%s%d" % (L(base), a["more"])], \
        (v["SUMMARY!%s%d" % (L(base), a["refused"])], v["SUMMARY!%s%d" % (L(rate_), a["refused"])])


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
    listed, more, refused = _attention_read(v, s)
    assert listed == [("%s · Net" % l[0], "%d %s" % (k, lb(v, "rating_name", rows[l])),
                       "%.2f%% in %s" % (j, lb(v, "quarter", rows[l]))) for k, j, l in want]
    assert more == "" and refused == ("0 of 4 Bank series", "None refused")
    sheet = load_workbook(info["path"])["Summary"]
    assert sheet.cell(s["attention"]["head"], s["panels"][1]).value == "Needs your attention · Bank"
    assert v["SUMMARY!" + s["count"]] == "Bank: 2 rated 4 or 5 · 0 refused · 0 with no source picked"


def test_a_refused_series_is_counted_and_not_listed(attention):
    d, info = attention
    s = info["summary"]
    z = col(info, "How rare High is (z)")
    f = info["decide"]["first"]
    cells = {"Decide!%s%d" % (z, f): 50, "Decide!%s%d" % (z, f + 3): 50}        # rows A and D
    v = typed(info["path"], d / "refused.xlsx", cells)
    assert lb(v, "refusal", 5).startswith("Refused") and lb(v, "refusal", 9).startswith("Refused")
    listed, more, refused = _attention_read(v, s)
    assert [x[0] for x in listed] == ["B · Net"]
    assert refused == ("2 of 4 Bank series", "Refused")


def test_more_leave_outs_than_rows_is_said(tmp_path):
    from threshold_engine.assess_tab import LO_ROWS
    ser = [("P%d - M - S" % k, DATA / "cards_nco_ttm.csv") for k in range(LO_ROWS + 1)]
    spec = {"names": NAMES, "parts": {lbl: tuple(lbl.split(" - ")) for lbl, _ in ser}, "absent": [],
            "compare": None, "notes": [], "lines_from": "S", "kind": "consumer"}
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
    heads.add(ws.cell(w["summary"]["attention"]["head"], w["summary"]["panels"][1]).value.split(" · ")[0])
    assert heads == {"Latest", "Rating", "Points", "Needs your attention"} and heads <= terms
    assert {DT.LINES_FROM, DT.LINES_TAB, "Thresholds", "Rating on these lines", "Pick a source",
            "What each source's own history would give", "Quarters kept", "Worst kept"} <= terms


def test_without_a_compare_pair_the_first_source_leads_and_there_are_no_points():
    from threshold_engine import summary_tab as SU
    parts = {lbl: tuple(lbl.split(" - ")) for lbl in LABELS}
    lay = SU.layout(LABELS, parts, None)
    assert lay["sources"] == ["Industry", "Bank"] and "points" not in lay["offsets"] and lay["width"] == 6
    lay = SU.layout(LABELS, parts, ("Bank", "Industry"))
    assert lay["sources"] == ["Bank", "Industry"] and lay["offsets"]["points"] == 4
