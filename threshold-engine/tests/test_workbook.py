"""The workbook: Excel's live lines must equal Python's reference scale
(threshold_engine.scale), as built and after the bank changes a setting.
Recalculated with the `formulas` engine, so no copy of Excel is needed; a skip
is reported, never counted as a pass."""
import hashlib

import pytest
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from conftest import DATA, load
from threshold_engine.glossary import TERMS
from threshold_engine.scale import scale, score
from threshold_engine.workbook import build, quarter

formulas = pytest.importorskip("formulas", reason="the formulas engine recalculates the workbook")

SERIES = [("Credit card", DATA / "cards_nco_ttm.csv"), ("Mortgage", DATA / "mortgage_nco_ttm.csv"),
          ("Home equity", DATA / "home_equity_nco_ttm.csv"),
          ("Other consumer", DATA / "other_consumer_as_filed_nco_ttm.csv")]
CARD_CUTS = (("2007Q4", "2012Q4"), ("2021Q3", "2023Q1"))
SET = dict(halfwidth=0.5, low_step=1.5, high_fraction=0.5)


def make(path, **over):
    kw = dict(name="NCO", unit="%", direction="higher_is_worse", frequency="quarterly", smoothing=1,
              floor_at_zero=True, moderate_halfwidth=SET["halfwidth"], low_step=SET["low_step"],
              high_fraction=SET["high_fraction"], on_the_line="worse", half_lives=(10,),
              percentiles=(50, 75, 90, 95), horizon=4, min_history=41)
    kw.update(over)
    return build(path, SERIES, **kw)


def recalc(path):
    """Every cell's value after a full recalculation, keyed 'SHEET!A1'."""
    model = formulas.ExcelModel().loads(str(path)).finish()
    sol = model.calculate()
    out = {}
    for key, val in sol.items():
        ref = key.split("]")[-1].upper()
        v = getattr(val, "value", val)
        try:
            v = v.item(0) if hasattr(v, "item") else v
        except Exception:                          # noqa: BLE001
            pass
        out[ref.replace("'", "")] = v
    return out


def row(vals, r):
    """Median, typical yearly move, worst, the four lines, score."""
    return [vals.get("THRESHOLDS!%s%d" % (c, r)) for c in "BCDEFGHK"]


def reference(file, cuts=(), **over):
    pts = load(file)
    kept = [None if any(a <= quarter(p.date) <= b for a, b in cuts) else p.value for p in pts]
    kw = dict(SET, **over)
    ref = scale(kept, "higher_is_worse", kw["halfwidth"], kw["low_step"], kw["high_fraction"], True)
    return pts, kept, ref


def with_settings(p, tmp_path, name, cells):
    wb = load_workbook(p)
    for ref, v in cells.items():
        wb["Settings"][ref] = v
    q = tmp_path / name
    wb.save(q)
    return recalc(q)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    p = tmp_path_factory.mktemp("wb") / "t.xlsx"
    info = make(p)
    return p, info, recalc(p)


def test_as_built_every_product_equals_the_reference_scale(built):
    _, _, vals = built
    for r, (label, path) in enumerate(SERIES, start=5):
        pts, _, ref = reference(path.name)
        got = row(vals, r)
        assert got[0] == pytest.approx(ref["median"])
        assert got[1] == pytest.approx(ref["typical_yearly_move"])
        assert got[2] == pytest.approx(ref["worst"])
        assert got[3:7] == pytest.approx(ref["bounds"])
        assert got[7] == score(pts[-1].value, ref["bounds"], "higher_is_worse", "worse", True)


def test_cards_with_both_periods_left_out_equal_the_reference(built, tmp_path):
    p, _, _ = built
    vals = with_settings(p, tmp_path, "cuts.xlsx", {"B6": "2007Q4", "C6": "2012Q4", "E6": "2021Q3", "F6": "2023Q1"})
    _, _, ref = reference("cards_nco_ttm.csv", CARD_CUTS)
    got = row(vals, 5)
    assert got[1] == pytest.approx(ref["typical_yearly_move"])
    assert got[3:7] == pytest.approx(ref["bounds"])
    assert [round(x, 3) for x in got[3:7]] == [2.879, 3.464, 4.050, 5.326]
    assert got[7] == 3                                 # today's 3.98% is Moderate


def test_each_multiplier_on_settings_is_live(built, tmp_path):
    p, _, _ = built
    vals = with_settings(p, tmp_path, "mult.xlsx", {"H6": 0.25, "I6": 1.0, "J6": 0.75})
    _, _, ref = reference("cards_nco_ttm.csv", halfwidth=0.25, low_step=1.0, high_fraction=0.75)
    assert row(vals, 5)[3:7] == pytest.approx(ref["bounds"])


def test_the_on_the_line_rule_is_live(built, tmp_path):
    # Half-width 0 puts Moderate and Moderate-High both on the median, 3.978,
    # which is also cards' latest value: "worse" scores it 4, "better" 2.
    p, _, _ = built
    worse = with_settings(p, tmp_path, "w.xlsx", {"H6": 0})
    better = with_settings(p, tmp_path, "b.xlsx", {"H6": 0, "K6": "better"})
    assert row(worse, 5)[0] == pytest.approx(3.978)
    assert (row(worse, 5)[7], row(better, 5)[7]) == (4, 2)


def test_a_median_at_or_below_zero_is_refused(built, tmp_path):
    p, _, _ = built
    vals = with_settings(p, tmp_path, "z.xlsx", {"B7": "1991Q4", "C7": "2017Q4"})
    assert vals["THRESHOLDS!B6"] <= 0
    assert vals["THRESHOLDS!M6"] == "Refused: the median is at or below zero"
    assert vals["THRESHOLDS!K6"] == ""


def test_moderate_low_must_begin_below_moderate(built, tmp_path):
    p, _, _ = built
    vals = with_settings(p, tmp_path, "order.xlsx", {"H6": 1.0, "I6": 0.5})
    assert vals["THRESHOLDS!M5"] == "Refused: Moderate-Low must begin further from the median than Moderate"


def test_every_series_is_on_one_quarterly_calendar(built):
    p, info, _ = built
    da = load_workbook(p)["Data"]
    qs = [c.value for c in da["A"][1:]]
    assert qs == sorted(qs) and len(qs) == info["quarters"] and qs[0] == "1985Q4"
    assert quarter("2010-04-01") == quarter("2010-06-30") == "2010Q2"


def test_the_run_tab_fingerprints_every_file(built):
    p, _, _ = built
    run = load_workbook(p)["Run"]
    rows = {r[0].value: r for r in run.iter_rows(min_row=8)
            if r[0].value and len(str(r[2].value or "")) == 64}
    for label, path in SERIES:
        assert rows[label][2].value == hashlib.sha256(path.read_bytes()).hexdigest()


def test_mixed_duplicate_or_impossible_inputs_are_refused(tmp_path):
    with pytest.raises(ValueError):
        build(tmp_path / "x.xlsx", SERIES[:1] * 2, "NCO", "%", "higher_is_worse", "quarterly", 1, True,
              0.5, 1.5, 0.5, "worse", (), (50, 75, 90, 95), 4, 41)
    for bad in (dict(on_the_line="sometimes"), dict(low_step=0.5), dict(high_fraction=0)):
        with pytest.raises(ValueError):
            make(tmp_path / "y.xlsx", **bad)


def test_two_leave_out_windows_carry_their_reasons_to_the_run_tab(built, tmp_path):
    p, _, _ = built
    vals = with_settings(p, tmp_path, "two.xlsx", {"B6": "2007Q4", "C6": "2012Q4", "D6": "Financial crisis",
                                                   "E6": "2021Q3", "F6": "2023Q1", "G6": "Pandemic forbearance"})
    run = {v for k, v in vals.items() if k.startswith("RUN!")}
    assert {"2007Q4 to 2012Q4", "Financial crisis", "2021Q3 to 2023Q1", "Pandemic forbearance"} <= run


def test_settings_says_what_the_evidence_found(built):
    p, _, _ = built
    st = load_workbook(p)["Settings"]
    assert st["L6"].value == "Leave out 2007Q4 to 2012Q4"
    assert "2021Q3 to 2023Q1 below the path" in st["M6"].value
    assert "2008" not in (st["N6"].value or "")


def test_assess_counts_the_quarters_in_each_score(built, tmp_path):
    p, _, _ = built
    vals = with_settings(p, tmp_path, "assess.xlsx", {"B6": "2007Q4", "C6": "2012Q4", "E6": "2021Q3", "F6": "2023Q1"})
    pts, kept, ref = reference("cards_nco_ttm.csv", CARD_CUTS)
    sc = lambda v: score(v, ref["bounds"], "higher_is_worse", "worse", True)      # noqa: E731
    want_kept = [sum(1 for v in kept if v is not None and sc(v) == k) for k in range(1, 6)]
    want_all = [sum(1 for x in pts if sc(x.value) == k) for k in range(1, 6)]
    assert [vals["ASSESS!E%d" % r] for r in range(8, 13)] == want_kept
    assert [vals["ASSESS!G%d" % r] for r in range(8, 13)] == want_all
    assert sum(want_kept) == 135


def test_assess_follows_the_on_the_line_rule(built, tmp_path):
    p, _, _ = built
    worse = with_settings(p, tmp_path, "aw.xlsx", {"H6": 0})
    better = with_settings(p, tmp_path, "ab.xlsx", {"H6": 0, "K6": "better"})
    on_line = sum(1 for x in load("cards_nco_ttm.csv") if x.value == 3.978)
    assert on_line >= 1
    # With Moderate empty, a quarter on the median is Moderate-High under
    # "worse" and Moderate-Low under "better".
    assert worse["ASSESS!G11"] - better["ASSESS!G11"] == on_line
    assert better["ASSESS!G9"] - worse["ASSESS!G9"] == on_line


def test_the_strip_marks_exactly_the_quarters_left_out_and_the_caption_says_why(built, tmp_path):
    p, info, _ = built
    vals = with_settings(p, tmp_path, "strip.xlsx", {"B6": "2007Q4", "C6": "2012Q4", "D6": "Financial crisis",
                                                     "E6": "2021Q3", "F6": "2023Q1", "G6": "Pandemic forbearance"})
    qcol, scol = get_column_letter(12), get_column_letter(23)
    qs = [vals["ASSESS!%s%d" % (qcol, r)] for r in range(2, info["quarters"] + 2)]
    marked = [q for r, q in zip(range(2, info["quarters"] + 2), qs) if vals["ASSESS!%s%d" % (scol, r)] != 0]
    assert marked == [q for q in qs if any(a <= q <= b for a, b in CARD_CUTS)] and len(marked) == 28
    assert vals["ASSESS!A41"] == "2007Q4 to 2012Q4: Financial crisis"
    assert vals["ASSESS!A42"] == "2021Q3 to 2023Q1: Pandemic forbearance"


def test_with_nothing_left_out_the_caption_says_so(built):
    _, _, vals = built
    assert vals["ASSESS!A41"] == "" and vals["ASSESS!A43"] == "Nothing left out: every quarter counts."


# Every heading a reader meets on Thresholds and Settings, and the glossary
# entry that explains it. Headings that need no definition are listed as such,
# so a new heading fails here until someone decides which it is.
PLAIN = {"Product", "Reason", "to", "Why", "Leave out from", "Leave out to", "Second leave-out from",
         "Largest spell: what the evidence says", "Temporary departures the data found"}
DEFINED_BY = {
    "Median kept": "Median kept", "Typical yearly move": "Typical yearly move", "Worst kept": "Worst kept",
    "2 Moderate-Low from": "2 Moderate-Low from, 3 Moderate from, 4 Moderate-High from, 5 High from",
    "3 Moderate from": "2 Moderate-Low from, 3 Moderate from, 4 Moderate-High from, 5 High from",
    "4 Moderate-High from": "2 Moderate-Low from, 3 Moderate from, 4 Moderate-High from, 5 High from",
    "5 High from": "2 Moderate-Low from, 3 Moderate from, 4 Moderate-High from, 5 High from",
    "Latest quarter": "Latest", "Latest (%)": "Latest", "Score": "Score", "Rating": "Rating", "Check": "Check",
    "Moderate: half-width, in typical yearly moves": "Moderate: half-width",
    "Moderate-Low begins this many typical yearly moves below the median": "Moderate-Low begins",
    "High begins this share of the way from Moderate-High to the worst quarter kept":
        "High begins (share of the way)",
    "A value on a line takes the": "A value on a line takes the",
}


def test_every_heading_is_defined_in_the_glossary(built):
    p, _, _ = built
    wb = load_workbook(p)
    terms = {t for t, _, _ in TERMS}
    headings = [c.value for c in wb["Thresholds"][4] if c.value] + [c.value for c in wb["Settings"][5] if c.value]
    for h in headings:
        assert h in PLAIN or DEFINED_BY.get(h) in terms, "no glossary entry for %r" % h


def test_the_glossary_tab_carries_every_term(built):
    p, _, _ = built
    gl = load_workbook(p)["Glossary"]
    on_tab = [r[0].value for r in gl.iter_rows(min_row=5) if r[0].value]
    assert on_tab == [t for t, _, _ in TERMS]
    assert all(m and c for _, m, c in TERMS)


def test_no_formula_refers_to_a_row_that_does_not_exist(built):
    # The four-quarter change starts on the fifth quarter: a formula on an
    # earlier row would point above row 1, which Excel reports as a damaged
    # file even where the formulas engine shrugs.
    import re
    p, _, _ = built
    wb = load_workbook(p)
    bad = []
    for ws in wb.worksheets:
        for row_ in ws.iter_rows():
            for c in row_:
                if isinstance(c.value, str) and c.value.startswith("="):
                    for m in re.finditer(r"(?<![A-Za-z])\$?[A-Z]{1,3}\$?(-?\d+)(?![\d(])", c.value):
                        if int(m.group(1)) < 1:
                            bad.append((ws.title, c.coordinate, c.value))
    assert bad == []
