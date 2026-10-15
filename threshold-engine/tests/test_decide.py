"""The Decide and Summary tabs (decide_tab.py, summary_tab.py).

Decide is where the bank types; Assess's settings and periods-left-out cells
read it. The proof is a twin: the same workbook built without Decide, the same
thing typed on Assess, and every number on Thresholds the same.

The test engine (``formulas``) has no SUBTOTAL, which is how Decide knows the
one row its slicers leave visible. So the tests stand in for the slicers by
writing the Shown column themselves, 1 on the row shown and 0 on the rest;
SUBTOTAL and the slicers are proved in Excel itself (tools/walk_book.ps1).
"""
from pathlib import Path

import pytest
from openpyxl import load_workbook

from conftest import DATA
from threshold_engine import decide_tab as DT
from threshold_engine.workbook import assess_layout, build
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
    from openpyxl.utils import get_column_letter
    return get_column_letter(info["decide"]["columns"][name])


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


def th_rows(vals, n=len(LABELS)):
    return [[vals.get("THRESHOLDS!%s%d" % (c, 5 + i)) for c in "BCDEFGHIJKLM"] for i in range(n)]


def same(a, b):
    for ra, rb in zip(a, b):
        for x, y in zip(ra, rb):
            if isinstance(x, float) and isinstance(y, float):
                assert x == pytest.approx(y, abs=1e-12)
            else:
                assert x == y


def test_untouched_decide_changes_no_number(pair):
    d, w, p = pair
    same(th_rows(recalc(w["path"])), th_rows(recalc(p["path"])))


@pytest.mark.parametrize("setting, assess_col, value", [("How rare High is (z)", "Q", 3.5),
                                                         ("Width of Moderate", "O", 0.25),
                                                         ("Moderate-Low begins", "P", 1.5),
                                                         ("On a line, rate it", "R", "better")])
def test_a_setting_typed_on_decide_is_the_same_as_on_assess(pair, setting, assess_col, value):
    d, w, p = pair
    i = 1                                                       # the second series
    dec = typed(w["path"], d / "dz.xlsx", {"Decide!%s%d" % (col(w, setting), w["decide"]["first"] + i): value})
    ref = typed(p["path"], d / "pz.xlsx", {"Assess!%s%d" % (assess_col, assess_layout(4)["set_top"] + i): value})
    same(th_rows(dec), th_rows(ref))
    assert th_rows(dec) != th_rows(recalc(p["path"])) or setting == "On a line, rate it"


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
    same(th_rows(dec), th_rows(ref))
    assert [dec["ASSESS!N%d" % (lo + k)] for k in range(3)] == [LABELS[0], LABELS[2], ""]
    assert th_rows(dec)[0] != th_rows(recalc(p["path"]))[0]


def test_a_half_typed_period_refuses_its_series_in_words(pair):
    d, w, p = pair
    f = w["decide"]["first"]
    v = typed(w["path"], d / "dh.xlsx", {"Decide!%s%d" % (col(w, "Leave out from"), f + 1): "2009Q1"})
    assert "not whole" in v["THRESHOLDS!M6"]
    assert v["DECIDE!%s%d" % (col(w, "Check"), f + 1)].startswith("Refused:")
    assert v["THRESHOLDS!M5"] == ""


def test_the_screen_follows_the_one_row_shown(pair):
    d, w, p = pair
    info = w["decide"]
    v = typed(w["path"], d / "ds.xlsx", {}, show={"Card - Net - Bank"}, info=w)
    top = info["screen_top"]
    assert v["DECIDE!B%d" % top] == ""                             # one row: no message
    head = v["DECIDE!B%d" % (top + 3)]
    assert head.startswith("Bank, net, card: ") and " in 2026Q2" in head
    assert ("%.2f%%" % v["THRESHOLDS!J6"]) in head
    rows = info["compare_rows"]
    assert v["DECIDE!E%d" % rows["Bank"]] == pytest.approx(v["THRESHOLDS!J6"])
    assert v["DECIDE!E%d" % rows["Industry"]] == pytest.approx(v["THRESHOLDS!J5"])
    assert "points" in v["DECIDE!B%d" % (rows["Industry"] + 1)]
    chk = v["DECIDE!B%d" % info["check_row"]]
    assert chk == "Check: OK, your settings fit this series." or chk.startswith("Refused:")


def test_no_row_shown_says_so_and_prints_the_books_reason(pair):
    d, w, p = pair
    v = typed(w["path"], d / "d0.xlsx", {}, show=set(), info=w)
    msg = v["DECIDE!B%d" % w["decide"]["screen_top"]]
    assert msg.startswith("No series in this workbook matches") and ABSENT[0]["why"] in msg
    v2 = typed(w["path"], d / "d2.xlsx", {}, show={LABELS[0], LABELS[3]}, info=w)
    assert v2["DECIDE!B%d" % w["decide"]["screen_top"]].startswith("2 series match")


def test_the_decided_count(pair):
    d, w, p = pair
    f = w["decide"]["first"]
    v = typed(w["path"], d / "dc.xlsx", {"Decide!%s%d" % (col(w, "Decision"), f): "Accept these lines",
                                         "Decide!%s%d" % (col(w, "Decision"), f + 3): "Reject"})
    assert v["DECIDE!L1"] == "Decided: 2 of 4  ·  accepted 1, rejected 1"


def test_summary_reads_thresholds_and_marks_what_is_not_there(pair):
    d, w, p = pair
    v = recalc(w["path"])
    ws = load_workbook(w["path"])["Summary"]
    head = {ws.cell(5, c).value: c for c in range(1, 12) if ws.cell(5, c).value}
    from openpyxl.utils import get_column_letter as L
    row = {(ws.cell(r, 1).value or None, ws.cell(r, 2).value): r for r in range(7, 12)}
    r_card_net = 7
    assert ws.cell(7, 1).value == "Card" and ws.cell(7, 2).value == "Net"
    ci, cb = head["Industry"], head["Bank"]
    assert v["SUMMARY!%s%d" % (L(ci), 7)] == pytest.approx(v["THRESHOLDS!J5"])
    assert v["SUMMARY!%s%d" % (L(cb), 7)] == pytest.approx(v["THRESHOLDS!J6"])
    k = v["THRESHOLDS!K5"]
    assert v["SUMMARY!%s%d" % (L(ci + 1), 7)] == ("%s %s" % (k, v["THRESHOLDS!L5"]) if k != "" else "Refused")
    mort = next(r for r in range(7, 12) if ws.cell(r, 1).value == "Mortgage")
    assert ws.cell(mort, cb + 1).value == "Not in this workbook"
    diff = head["Bank vs Industry"]
    assert v["SUMMARY!%s7" % L(diff)] == pytest.approx(v["THRESHOLDS!J6"] - v["THRESHOLDS!J5"])
    notes = [ws.cell(r, 1).value for r in range(12, ws.max_row + 1)]
    assert "Not in this workbook: " + ABSENT[0]["why"] in notes and "A note the book gave." in notes


def test_more_leave_outs_than_rows_is_said(tmp_path):
    from threshold_engine.assess_tab import LO_ROWS
    ser = [("P%d - M - S" % k, DATA / "cards_nco_ttm.csv") for k in range(LO_ROWS + 1)]
    spec = {"names": NAMES, "parts": {lbl: tuple(lbl.split(" - ")) for lbl, _ in ser}, "absent": [],
            "compare": None, "notes": []}
    info = build(tmp_path / "many.xlsx", ser, decide=spec, **SETTINGS)["decide"]
    wb = load_workbook(tmp_path / "many.xlsx")
    from openpyxl.utils import get_column_letter as L
    c = info["columns"]
    for i in range(LO_ROWS + 1):
        r = info["first"] + i
        wb["Decide"]["%s%d" % (L(c["Leave out from"]), r)] = "2009Q1"
        wb["Decide"]["%s%d" % (L(c["Leave out to"]), r)] = "2010Q4"
        wb["Decide"]["%s%d" % (L(c["Why left out"]), r)] = "x"
    wb.save(tmp_path / "many2.xlsx")
    v = recalc(tmp_path / "many2.xlsx")
    assert v["DECIDE!B%d" % (info["screen_top"] + 1)].startswith("More than %d series" % LO_ROWS)


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
