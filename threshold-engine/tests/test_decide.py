"""The Decide and Summary tabs (decide_tab.py, summary_tab.py), and Thresholds
as the book lays it out (workbook.py, round 2).

Decide is where the bank types; Assess's settings and periods-left-out cells
read it. The proof is a twin: the same workbook built without Decide, the same
thing typed on Assess, and every number on Thresholds the same. The two lay
Thresholds out differently, so the twin is read by meaning
(``decide_tab.TH_BOOK`` and ``TH_PLAIN``), never by letter.

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
NAMES = ["Product", "Measure", "Source"]
ABSENT = [{"parts": {"Product": "Mortgage", "Measure": "Net", "Source": "Bank"},
           "why": "The bank's mortgage file was not given (a test note)."}]
SETTINGS = dict(name="N", unit="%", direction="higher_is_worse", frequency="quarterly", smoothing=1,
                floor_at_zero=True, moderate_halfwidth=0.5, low_step=1.0, high_z=2.5, on_the_line="worse",
                half_lives=(), percentiles=(50,), horizon=4, min_history=41)
#: What a Thresholds row holds, by meaning.
MEANINGS = ("median", "move", "worst", "l2", "l3", "l4", "l5", "quarter", "value", "rating", "rating_name", "refusal")


def decide_spec(compare=("Bank", "Industry")):
    return {"names": NAMES, "parts": {lbl: tuple(lbl.split(" - ")) for lbl in LABELS}, "absent": ABSENT,
            "compare": compare, "notes": ["A note the book gave."]}


@pytest.fixture(scope="module")
def pair(tmp_path_factory):
    d = tmp_path_factory.mktemp("decide")
    with_ = build(d / "decide.xlsx", SER, decide=decide_spec(), **SETTINGS)
    plain = build(d / "plain.xlsx", SER, **SETTINGS)
    return d, with_, plain


def col(info, name):
    return L(info["decide"]["columns"][name])


def typed(src, dst, cells, show=None, info=None):
    """Type into a copy: cells is {'Sheet!A1': value}; show names the series
    the slicers leave visible (Shown = 1 on its row, 0 elsewhere)."""
    wb = load_workbook(src)
    for ref, v in cells.items():
        sh, a = ref.split("!")
        wb[sh][a] = v
    if show is not None:
        d = info["decide"]
        for i, lbl in enumerate(LABELS):
            wb["Decide"]["%s%d" % (col(info, "Shown"), d["first"] + i)] = 1 if lbl in show else 0
    wb.save(dst)
    return recalc(dst)


def th_rows(vals, cols=DT.TH_BOOK, n=len(LABELS)):
    return [[vals.get("THRESHOLDS!%s%d" % (cols[k], 5 + i)) for k in MEANINGS] for i in range(n)]


def th(vals, key, row):
    """A cell of the book's Thresholds, by meaning."""
    return vals["THRESHOLDS!%s%d" % (DT.TH_BOOK[key], row)]


def same(a, b):
    for ra, rb in zip(a, b):
        for x, y in zip(ra, rb):
            if isinstance(x, float) and isinstance(y, float):
                assert x == pytest.approx(y, abs=1e-12)
            else:
                assert x == y


def test_untouched_decide_changes_no_number(pair):
    d, w, p = pair
    same(th_rows(recalc(w["path"])), th_rows(recalc(p["path"]), DT.TH_PLAIN))


@pytest.mark.parametrize("setting, assess_col, value", [("How rare High is (z)", "Q", 3.5),
                                                         ("Width of Moderate", "O", 0.25),
                                                         ("Moderate-Low begins", "P", 1.5),
                                                         ("On a line, rate it", "R", "better")])
def test_a_setting_typed_on_decide_is_the_same_as_on_assess(pair, setting, assess_col, value):
    d, w, p = pair
    i = 1                                                       # the second series
    dec = typed(w["path"], d / "dz.xlsx", {"Decide!%s%d" % (col(w, setting), w["decide"]["first"] + i): value})
    ref = typed(p["path"], d / "pz.xlsx", {"Assess!%s%d" % (assess_col, assess_layout(4)["set_top"] + i): value})
    same(th_rows(dec), th_rows(ref, DT.TH_PLAIN))
    assert th_rows(dec) != th_rows(recalc(p["path"]), DT.TH_PLAIN) or setting == "On a line, rate it"


def test_periods_left_out_on_decide_are_the_same_as_on_assess(pair):
    """Two series with a period left out, typed out of order on Decide; Assess
    lists them in table order, and Thresholds equals the twin."""
    d, w, p = pair
    f = w["decide"]["first"]
    lay = assess_layout(4)
    dec = typed(w["path"], d / "dl.xlsx", {
        "Decide!%s%d" % (col(w, "Leave out from"), f + 2): "2009Q1", "Decide!%s%d" % (col(w, "Leave out to"), f + 2):
        "2011Q4", "Decide!%s%d" % (col(w, "Why left out"), f + 2): "crisis",
        "Decide!%s%d" % (col(w, "Leave out from"), f): "2020Q2", "Decide!%s%d" % (col(w, "Leave out to"), f):
        "2021Q4", "Decide!%s%d" % (col(w, "Why left out"), f): "pandemic"})
    lo = lay["lo_top"]
    ref = typed(p["path"], d / "pl.xlsx", {
        "Assess!N%d" % lo: LABELS[0], "Assess!O%d" % lo: "2020Q2", "Assess!P%d" % lo: "2021Q4", "Assess!Q%d" % lo:
        "pandemic", "Assess!N%d" % (lo + 1): LABELS[2], "Assess!O%d" % (lo + 1): "2009Q1",
        "Assess!P%d" % (lo + 1): "2011Q4", "Assess!Q%d" % (lo + 1): "crisis"})
    same(th_rows(dec), th_rows(ref, DT.TH_PLAIN))
    assert [dec["ASSESS!N%d" % (lo + k)] for k in range(3)] == [LABELS[0], LABELS[2], ""]
    assert th_rows(dec)[0] != th_rows(recalc(p["path"]), DT.TH_PLAIN)[0]


def test_a_period_left_out_is_drawn_apart_and_said(pair):
    """The quarters left out leave the picked line and form the STONE stretch,
    joined to the quarters either side; the panel and Left out now say so."""
    d, w, p = pair
    info = w["decide"]
    h, f = info["helpers"], info["first"]
    v = typed(w["path"], d / "dlo.xlsx", {
        "Decide!%s%d" % (col(w, "Leave out from"), f): "2020Q2", "Decide!%s%d" % (col(w, "Leave out to"), f):
        "2021Q4", "Decide!%s%d" % (col(w, "Why left out"), f): "pandemic"}, show={LABELS[0]}, info=w)
    q = {v["DECIDE!%s%d" % (h["q"], r)]: r for r in range(2, 200) if v.get("DECIDE!%s%d" % (h["q"], r))}
    num = lambda c_, qq: isinstance(v["DECIDE!%s%d" % (h[c_], q[qq])], float)          # noqa: E731
    assert not num("pick0", "2020Q2") and not num("pick0", "2021Q4") and num("pick0", "2022Q1")
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


def test_a_half_typed_period_refuses_its_series_in_words(pair):
    d, w, p = pair
    f = w["decide"]["first"]
    v = typed(w["path"], d / "dh.xlsx", {"Decide!%s%d" % (col(w, "Leave out from"), f + 1): "2009Q1"})
    assert "not whole" in th(v, "refusal", 6)
    assert v["DECIDE!%s%d" % (col(w, "Check"), f + 1)] == "Refused: see the fix below"
    assert v["DECIDE!%s%d" % (col(w, "Check"), f)] == "OK"
    assert th(v, "refusal", 5) == ""
    assert th(v, "check", 6).startswith("To fix: Finish its row on Decide") and th(v, "check", 5) == "OK"


def test_the_screen_follows_the_one_row_shown(pair):
    d, w, p = pair
    info = w["decide"]
    lay = info["layout"]
    v = typed(w["path"], d / "ds.xlsx", {}, show={"Card - Net - Bank"}, info=w)
    assert v["DECIDE!B%d" % lay["headline"]] == "Bank, net, card: %.2f%% in %s" % (th(v, "value", 6),
                                                                                    th(v, "quarter", 6))
    k = th(v, "rating", 6)
    assert v["DECIDE!I%d" % lay["chip"]] == ("No rating: see the Check" if k == "" else
                                             "%d %s" % (k, th(v, "rating_name", 6)))
    rows = info["compare_rows"]
    assert v["DECIDE!N%d" % rows["Bank"]] == pytest.approx(th(v, "value", 6))
    assert v["DECIDE!N%d" % rows["Industry"]] == pytest.approx(th(v, "value", 5))
    diff = th(v, "value", 6) - th(v, "value", 5)
    assert v["DECIDE!L%d" % lay["compare_line"]] == "Bank is %.2f percentage points %s than Industry." % (
        abs(diff), "higher" if diff >= 0 else "lower")
    assert v["DECIDE!L%d" % rows["Bank"]] == "━ Bank" and v["DECIDE!L%d" % rows["Industry"]] == "╍ Industry"
    chk = v["DECIDE!B%d" % info["check_row"]]
    if th(v, "refusal", 6) == "":
        assert chk == "Check: OK, your settings fit this series." and v["DECIDE!I%d" % info["check_row"]] == ""
    else:
        assert chk == th(v, "refusal", 6)


def test_the_check_band_says_why_and_what_to_type(pair):
    d, w, p = pair
    info = w["decide"]
    i = 1
    v = typed(w["path"], d / "db.xlsx", {"Decide!%s%d" % (col(w, "How rare High is (z)"), info["first"] + i): -1},
              show={LABELS[i]}, info=w)
    assert v["DECIDE!B%d" % info["check_row"]] == "Refused: High's z must be above 0"
    assert v["DECIDE!I%d" % info["check_row"]] == "To fix: Type a number above 0 in How rare High is."
    assert v["DECIDE!%s%d" % (col(w, "Check"), info["first"] + i)] == "Refused: see the fix below"
    assert v["DECIDE!I%d" % info["layout"]["chip"]] == "No rating: see the Check"
    assert th(v, "check", 5 + i) == "To fix: Type a number above 0 in How rare High is."
    assert th(v, "rating_shown", 5 + i) == "Refused"


def test_the_panel_counts_each_rating_as_the_reference_does(pair):
    """Where each rating begins: the quarters kept in each rating, rated on
    the lines as scale.py rates them, and the share of all kept."""
    from threshold_engine.scale import scale, score
    from threshold_engine.series import check, read_csv
    d, w, p = pair
    lay = w["decide"]["layout"]
    i = 0
    v = typed(w["path"], d / "dp.xlsx", {}, show={LABELS[i]}, info=w)
    pts = check(read_csv(SER[i][1]), "quarterly")
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
    latest = score(vals_[-1], ref["bounds"], "higher_is_worse", "worse", True)
    assert [v["DECIDE!P%d" % (first + k)] for k in range(5)] == [
        "◀ " + quarter(pts[-1].date) if k + 1 == latest else "" for k in range(5)]
    assert v["DECIDE!M%d" % lay["median"]] == pytest.approx(ref["median"])
    assert v["DECIDE!N%d" % lay["median"]] == "%d of the %d quarters on file are kept." % (len(vals_), len(vals_))
    worst = pts[vals_.index(max(vals_))].date
    assert v["DECIDE!N%d" % lay["worst"]] == "Kept in %s. High must begin at or below it." % quarter(worst)


def test_the_chart_draws_the_picked_line_in_its_sources_color_and_follows_the_window(pair):
    d, w, p = pair
    info = w["decide"]
    h = info["helpers"]
    i = 1                                                          # Card - Net - Bank
    win = "M%d" % info["layout"]["window"]
    on = "Q%d" % info["compare_rows"]["Industry"]
    v = typed(w["path"], d / "dw.xlsx", {"Decide!" + win: "Last 20 quarters", "Decide!" + on: "Yes"},
              show={LABELS[i]}, info=w)
    third = ["Industry", "Bank"]
    rows = range(2, 200)
    got = lambda key: [v.get("DECIDE!%s%d" % (h[key], r)) for r in rows]      # noqa: E731
    nums = lambda xs: [x for x in xs if isinstance(x, float)]                  # noqa: E731
    # the picked line is drawn in the series for its own source only
    assert nums(got("pick%d" % third.index("Bank"))) and not nums(got("pick%d" % third.index("Industry")))
    # the other source switched on is an overlay; the picked one never is
    assert nums(got("over%d" % third.index("Industry"))) and not nums(got("over%d" % third.index("Bank")))
    first, count = int(v["DECIDE!%s2" % h["fit"]]), v["DECIDE!%s3" % h["fit"]]
    assert count == 20 and v["DECIDE!%s4" % h["fit"]] == first + 19 and v["DECIDE!%s5" % h["fit"]] == 2
    labels = [v["DECIDE!%s%d" % (h["cat"], r)] for r in range(first, first + 20)]
    assert labels[-1] == v["DECIDE!%s%d" % (h["q"], first + 19)] and sum(1 for x in labels if x) == 10
    # each rating's label sits on the last quarter drawn and nowhere else
    for j in range(4):
        lab = got("lab%d" % j)
        assert [r for r, x in zip(rows, lab) if isinstance(x, float)] in ([], [first + 19])
    assert v["DECIDE!B%d" % info["layout"]["section"]] == "The history over the five rating zones · last 20 quarters"


def test_no_row_shown_says_so_and_prints_the_books_reason(pair):
    d, w, p = pair
    head = w["decide"]["layout"]["headline"]
    v = typed(w["path"], d / "d0.xlsx", {}, show=set(), info=w)
    msg = v["DECIDE!B%d" % head]
    assert msg.startswith("No series in this workbook matches") and ABSENT[0]["why"] in msg
    v2 = typed(w["path"], d / "d2.xlsx", {}, show={LABELS[0], LABELS[3]}, info=w)
    assert v2["DECIDE!B%d" % head].startswith("2 series match")


def test_the_decided_count_and_thresholds_decision_column(pair):
    d, w, p = pair
    f = w["decide"]["first"]
    v = typed(w["path"], d / "dc.xlsx", {"Decide!%s%d" % (col(w, "Decision"), f): "Accept these lines",
                                         "Decide!%s%d" % (col(w, "Decision"), f + 3): "Reject"})
    assert v["DECIDE!L1"] == "Decided: 2 of 4 · accepted 1 · rejected 1"
    assert [th(v, "decision", 5 + i) for i in range(4)] == ["Accept these lines", "Not decided", "Not decided",
                                                             "Reject"]


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
    assert tbl.ref == "B8:Q%d" % lay["last"]
    assert all(ws.cell(9, c).fill.fgColor.rgb.endswith(K.INPUT) for c in range(CI("E"), CI("M") + 1))
    assert all(ws.cell(9, c).number_format == ";;;" for c in range(CI("O"), CI("Q") + 1))
    # the book's rows: chart over B119:K136 beside the panel, for 105 series and three sources
    big = DT.layout(105, 3, True)
    assert (big["headline"], big["check"], big["section"], big["chart_top"], big["chart_end"], big["window"],
            big["history"]) == (115, 116, 118, 119, 136, 131, 138)
    anchor = ws._charts[0].anchor
    assert (anchor._from.col, anchor._from.row, anchor.to.col, anchor.to.row) == (1, lay["chart_top"] - 1, 11,
                                                                                 lay["chart_end"])


def test_thresholds_in_the_book_is_laid_out_to_round_2(pair):
    d, w, p = pair
    ws = load_workbook(w["path"])["Thresholds"]
    T = DT.TH_BOOK
    assert [ws.cell(4, c).value for c in range(2, 17)] == [
        "Product", "Measure", "Source", "Median kept", "Typical yearly move", "Worst kept", "2 Moderate-Low",
        "3 Moderate", "4 Moderate-High", "5 High", "Quarter", "Value", "Rating", "Decision", "Check"]
    assert ws.freeze_panes == "E5"
    assert [(ws.cell(5 + i, 1).value, tuple(ws.cell(5 + i, c).value for c in (2, 3, 4))) for i in range(4)] == [
        (lbl, tuple(lbl.split(" - "))) for lbl in LABELS]
    assert ws["A5"].number_format == ";;;"
    widths = {c: round(ws.column_dimensions[c].width, 2) for c in "ABCDEFGHIJKLMNOP"}
    assert widths == {"A": 1.57, "B": 16.43, "C": 27.86, "D": 19.29, "E": 11.29, "F": 11.29, "G": 11.29,
                      "H": 11.29, "I": 11.29, "J": 11.29, "K": 11.29, "L": 10.14, "M": 10.14, "N": 19.29,
                      "O": 16.43, "P": 55.29}
    a, b = DT.TH_HIDDEN
    assert all(ws.column_dimensions[L(c)].hidden for c in range(CI(a), CI(b) + 1))
    assert not any(ws.column_dimensions[c].hidden for c in "ABCDEFGHIJKLMNOP")
    # a thin INK rule over each product's first row, MIST over each new measure
    assert ws["B5"].border.top.color.rgb.endswith(K.INK)
    assert ws["B7"].border.top.color.rgb.endswith(K.INK)              # Mortgage starts
    assert ws["B8"].border.top.color.rgb.endswith(K.INK)              # Card again, after Mortgage
    assert ws["B6"].border.top is None or ws["B6"].border.top.style is None
    # repeated names are hidden by formatting, not removed
    cf = {str(r.sqref): [x.formula for x in r.rules] for r in ws.conditional_formatting}
    assert cf["%s5:%s8" % (T["product"], T["product"])] == [["$B5=$B4"]]
    assert ws.auto_filter.ref == "B4:P8"
    assert [fc.colId for fc in ws.auto_filter.filterColumn if fc.hiddenButton] == list(range(3, 15))


def test_the_book_has_three_slicers_of_button_rows_and_no_filter_arrows(pair):
    d, w, p = pair
    z = zipfile.ZipFile(w["path"])
    sl = z.read("xl/slicers/slicer1.xml").decode()
    got = re.findall(r'<slicer name="(\w+)"[^>]*? columnCount="(\d+)" style="(\w+)" rowHeight="(\d+)"', sl)
    assert got == [("Pick1", "3", "SlicerStyleOther2", "228600"), ("Pick2", "4", "SlicerStyleOther2", "228600"),
                   ("Pick3", "3", "SlicerStyleOther2", "228600")]
    table = next(t for t in (z.read(n).decode() for n in z.namelist() if n.startswith("xl/tables/"))
                 if 'displayName="Decisions"' in t)
    assert table.count('hiddenButton="1"') == len(DT.FIXED) + 3


def test_summary_reads_thresholds_and_marks_what_is_not_there(pair):
    d, w, p = pair
    v = recalc(w["path"])
    ws = load_workbook(w["path"])["Summary"]
    head = {ws.cell(5, c).value: c for c in range(1, 12) if ws.cell(5, c).value}
    assert ws.cell(7, 1).value == "Card" and ws.cell(7, 2).value == "Net"
    ci, cb = head["Industry"], head["Bank"]
    assert v["SUMMARY!%s%d" % (L(ci), 7)] == pytest.approx(th(v, "value", 5))
    assert v["SUMMARY!%s%d" % (L(cb), 7)] == pytest.approx(th(v, "value", 6))
    k = th(v, "rating", 5)
    assert v["SUMMARY!%s%d" % (L(ci + 1), 7)] == ("%d %s" % (k, th(v, "rating_name", 5)) if k != "" else "Refused")
    mort = next(r for r in range(7, 12) if ws.cell(r, 1).value == "Mortgage")
    assert ws.cell(mort, cb + 1).value == "Not in this workbook"
    diff = head["Bank vs Industry"]
    assert v["SUMMARY!%s7" % L(diff)] == pytest.approx(th(v, "value", 6) - th(v, "value", 5))
    notes = [ws.cell(r, 1).value for r in range(12, ws.max_row + 1)]
    assert "Not in this workbook: " + ABSENT[0]["why"] in notes and "A note the book gave." in notes


def test_more_leave_outs_than_rows_is_said(tmp_path):
    from threshold_engine.assess_tab import LO_ROWS
    ser = [("P%d - M - S" % k, DATA / "cards_nco_ttm.csv") for k in range(LO_ROWS + 1)]
    spec = {"names": NAMES, "parts": {lbl: tuple(lbl.split(" - ")) for lbl, _ in ser}, "absent": [],
            "compare": None, "notes": []}
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
    assert v["DECIDE!B%d" % info["check_row"]].startswith("More than %d series" % LO_ROWS)


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
