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
SET = dict(halfwidth=0.5, low_step=1.0, high_z=2.5)


def make(path, **over):
    kw = dict(name="NCO", unit="%", direction="higher_is_worse", frequency="quarterly", smoothing=1,
              floor_at_zero=True, moderate_halfwidth=SET["halfwidth"], low_step=SET["low_step"],
              high_z=SET["high_z"], on_the_line="worse", half_lives=(10,),
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
    ref = scale(kept, "higher_is_worse", kw["halfwidth"], kw["low_step"], kw["high_z"], True)
    return pts, kept, ref


def top_of(vals, first):
    return vals["ASSESS!U%d" % first]


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
    vals = with_settings(p, tmp_path, "cuts.xlsx", {"B6": "2007Q4", "C6": "2012Q4", "D6": "Financial crisis",
        "E6": "2021Q3", "F6": "2023Q1", "G6": "Pandemic forbearance"})
    _, _, ref = reference("cards_nco_ttm.csv", CARD_CUTS)
    got = row(vals, 5)
    assert got[1] == pytest.approx(ref["typical_yearly_move"])
    assert got[3:7] == pytest.approx(ref["bounds"])
    assert [round(x, 3) for x in got[3:7]] == [3.171, 3.464, 4.050, 5.981]
    assert got[7] == 3                                 # today's 3.98% is Moderate


def test_each_multiplier_on_settings_is_live(built, tmp_path):
    p, _, _ = built
    vals = with_settings(p, tmp_path, "mult.xlsx", {"H6": 0.25, "I6": 1.5, "J6": 3.0})
    _, _, ref = reference("cards_nco_ttm.csv", halfwidth=0.25, low_step=1.5, high_z=3.0)
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
    vals = with_settings(p, tmp_path, "z.xlsx", {"B7": "1991Q4", "C7": "2017Q4", "D7": "test"})
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
              0.5, 1.0, 2.5, "worse", (), (50, 75, 90, 95), 4, 41)
    nan, inf = float("nan"), float("inf")
    for bad in (dict(on_the_line="sometimes"), dict(low_step=0.5), dict(high_z=0),
                dict(high_z=nan), dict(high_z=inf), dict(moderate_halfwidth=nan), dict(low_step=inf)):
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
    vals = with_settings(p, tmp_path, "assess.xlsx", {"B6": "2007Q4", "C6": "2012Q4", "D6": "Financial crisis",
        "E6": "2021Q3", "F6": "2023Q1", "G6": "Pandemic forbearance"})
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
    "High begins at this z: median + z x spread of levels": "High begins at this z",
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



def test_high_beyond_everything_kept_is_refused(built, tmp_path):
    # Cards with the crisis left out: z 3.5 puts High above the worst quarter kept.
    p, _, _ = built
    vals = with_settings(p, tmp_path, "z35.xlsx", {"B6": "2007Q4", "C6": "2012Q4", "D6": "Financial crisis",
        "E6": "2021Q3", "F6": "2023Q1", "G6": "Pandemic forbearance",
                                                   "J6": 3.5})
    assert vals["THRESHOLDS!M5"] == "Refused: High would begin beyond the worst quarter kept"
    _, _, ref = reference("cards_nco_ttm.csv", CARD_CUTS, high_z=3.5)
    assert ref["bounds"] is None and "beyond the worst" in ref["refused"]


def test_every_dial_row_equals_the_reference_scale(built, tmp_path):
    p, _, _ = built
    vals = with_settings(p, tmp_path, "dial.xlsx", {"B6": "2007Q4", "C6": "2012Q4", "D6": "Financial crisis",
        "E6": "2021Q3", "F6": "2023Q1", "G6": "Pandemic forbearance"})
    pts, kept, _ = reference("cards_nco_ttm.csv", CARD_CUTS)
    rows = {}
    r = 51
    for name, values in (("high_z", (2.0, 2.5, 3.0, 3.5)), ("halfwidth", (0.25, 0.5, 0.75, 1.0)),
                         ("low_step", (0.75, 1.0, 1.5, 2.0))):
        for v in list(values) + [None]:
            rows[(name, v)] = r
            r += 1
        r += 3
    for (name, v), r in rows.items():
        kw = dict(SET)
        if v is not None:
            kw[name] = v
        ref = scale(kept, "higher_is_worse", kw["halfwidth"], kw["low_step"], kw["high_z"], True)
        note = vals["ASSESS!K%d" % r]
        if ref["bounds"] is None:
            assert str(note).startswith("refused"), (name, v, note)
            continue
        assert [vals["ASSESS!%s%d" % (c, r)] for c in "BCDE"] == pytest.approx(ref["bounds"]), (name, v)
        want = [sum(1 for x in kept if x is not None and score(x, ref["bounds"], "higher_is_worse", "worse", True) == k)
                for k in range(1, 6)]
        assert [vals["ASSESS!%s%d" % (c, r)] for c in "FGHIJ"] == want, (name, v)
        assert note == ("<- now" if v is None else ""), (name, v, note)


@pytest.mark.parametrize("rule", ["worse", "better"])
def test_the_dials_current_row_counts_exactly_as_the_main_table(built, tmp_path, rule):
    # Half-width 0 puts two lines on the median, 3.978, a value cards actually
    # took: counts then depend on the on-the-line rule, in the dial as above.
    p, _, _ = built
    vals = with_settings(p, tmp_path, "dl-%s.xlsx" % rule, {"H6": 0, "K6": rule})
    main = [vals["ASSESS!E%d" % r] for r in range(8, 13)]
    for now_row in (55, 63, 71):
        assert [vals["ASSESS!%s%d" % (c, now_row)] for c in "FGHIJ"] == main
        assert vals["ASSESS!K%d" % now_row] == "<- now"



def test_too_little_history_kept_is_refused_in_the_workbook(built, tmp_path):
    # Leave out everything but the last four quarters of cards: no four-quarter
    # change has both ends kept, so there is no typical yearly move.
    p, _, _ = built
    vals = with_settings(p, tmp_path, "short.xlsx", {"B6": "1985Q4", "C6": "2025Q2", "D6": "test"})
    assert vals["THRESHOLDS!M5"] == "Refused: too little history kept for a typical yearly move"
    assert vals["THRESHOLDS!K5"] == ""


def test_a_smoothed_workbook_builds_its_live_lines_from_the_smoothed_series(tmp_path):
    """The Codex review (13 Oct 2026): with smoothing above 1 the evidence and
    backtest used the smoothed series while Data, Thresholds and the score
    used the raw file, so the workbook disagreed with itself. Now every line
    is built from the smoothed values, and Excel's equal Python's on them."""
    from threshold_engine.series import check, smooth
    p = tmp_path / "s.xlsx"
    make(p, smoothing=4)
    vals = recalc(p)
    da = load_workbook(p)["Data"]
    for r, (label, path) in enumerate(SERIES, start=5):
        sm = smooth(check(load(path.name), "quarterly"), 4)
        k = [c.value for c in da[1]].index(label) + 1
        col = {da.cell(i, 1).value: da.cell(i, k).value for i in range(2, da.max_row + 1)}
        assert [col[quarter(x.date)] for x in sm] == pytest.approx([x.value for x in sm])
        assert sum(v is not None for v in col.values()) == len(sm)
        ref = scale([x.value for x in sm], "higher_is_worse", SET["halfwidth"], SET["low_step"], SET["high_z"], True)
        got = row(vals, r)
        assert got[0] == pytest.approx(ref["median"]) and got[3:7] == pytest.approx(ref["bounds"])
        assert vals["THRESHOLDS!J%d" % r] == pytest.approx(sm[-1].value)
        assert got[7] == score(sm[-1].value, ref["bounds"], "higher_is_worse", "worse", True)
    run = [r for r in load_workbook(p)["Run"].iter_rows(values_only=True) if r and r[0] == "Smoothing"]
    assert run and "trailing mean over 4 quarters" in run[0][1]


def test_a_lower_is_worse_workbook_shades_five_bands_of_positive_width(tmp_path):
    """The Codex review (13 Oct 2026): for a lower-is-worse measure the lines
    fall, and the Assess chart's stacked bands came out with negative widths.
    The stack now starts at score 5 and every band is the gap between two
    lines, in the measure's own order."""
    src = tmp_path / "score.csv"
    rows = ["date,value"] + ["%s,%r" % (p.date, 800 - 40 * p.value) for p in load("cards_nco_ttm.csv")]
    src.write_text("\n".join(rows) + "\n", encoding="utf-8")
    p = tmp_path / "low.xlsx"
    build(p, [("Score", src)], name="Score", unit="", direction="lower_is_worse", frequency="quarterly",
          smoothing=1, floor_at_zero=False, moderate_halfwidth=0.5, low_step=1.0, high_z=2.5,
          on_the_line="worse", half_lives=(), percentiles=(50, 75, 90, 95), horizon=4, min_history=41)
    vals = recalc(p)
    lines = [vals["THRESHOLDS!%s5" % c] for c in "EFGH"]            # 2..5 begin, falling
    assert lines == sorted(lines, reverse=True) and vals["THRESHOLDS!M5"] == ""
    heads = [vals.get("ASSESS!%s%d" % (L, 15)) for L in ("P", "Q", "R", "S", "T")]
    ws = load_workbook(p)["Assess"]
    first = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 12).value == "Quarter") + 1
    names = [ws.cell(first - 1, c).value for c in range(16, 21)]
    assert names == ["5 High", "4 Moderate-High", "3 Moderate", "2 Moderate-Low", "1 Low"]
    widths = [vals["ASSESS!%s%d" % (get_column_letter(c), first)] for c in range(16, 21)]
    floor = vals["ASSESS!U%d" % (first + 1)]
    mn = min(min(lines), min(800 - 40 * x.value for x in load("cards_nco_ttm.csv")))
    assert 0 < floor < mn                     # not floored at zero: the axis starts just below the data
    # Nothing the chart plots sits at zero, or Excel stretches the axis down to it (the walkthrough, 13 Oct
    # 2026): the strip stands on an invisible base under the floor and is 0 high where nothing is left out.
    h = vals["ASSESS!U%d" % (first + 2)]
    rows = range(first, first + len(load("cards_nco_ttm.csv")))
    assert all(vals["ASSESS!Y%d" % r] == pytest.approx(floor - h) for r in rows) and floor - h > 0
    assert all(vals["ASSESS!W%d" % r] == 0 for r in rows)                   # nothing left out here
    assert all(vals["ASSESS!V%d" % r] == pytest.approx(floor) for r in rows)
    # and the axis itself starts at a round number just under that, not at Excel's automatic zero
    y_min = load_workbook(p)["Assess"]._charts[0].y_axis.scaling.min
    assert y_min is not None and 0 < y_min <= floor - h and floor - y_min < 0.2 * (top_of(vals, first) - floor)
    assert floor + widths[0] == pytest.approx(lines[3])                 # up to where High begins
    assert widths[1:4] == pytest.approx([lines[2] - lines[3], lines[1] - lines[2], lines[0] - lines[1]])
    assert all(x >= 0 for x in widths)


@pytest.mark.parametrize("rule", ["worse", "better"])
def test_a_lower_is_worse_workbook_equals_the_reference_scale(tmp_path, rule):
    """NEXT-GOAL section 2: a lower-is-worse measure (a credit score) was
    tested in scale.py and never through the workbook's lines and score. A
    mirrored cards series, built, recalculated, and held to scale() and
    score() with the direction reversed, under each on-the-line rule."""
    src = tmp_path / "score.csv"
    pts = load("cards_nco_ttm.csv")
    src.write_text("date,value\n" + "".join("%s,%r\n" % (x.date, 800 - 40 * x.value) for x in pts),
                   encoding="utf-8")
    p = tmp_path / ("low-%s.xlsx" % rule)
    build(p, [("Score", src)], name="Score", unit="", direction="lower_is_worse", frequency="quarterly",
          smoothing=1, floor_at_zero=False, moderate_halfwidth=0.5, low_step=1.0, high_z=2.5,
          on_the_line=rule, half_lives=(), percentiles=(50, 75, 90, 95), horizon=4, min_history=41)
    vals = recalc(p)
    mirrored = [800 - 40 * x.value for x in pts]
    ref = scale(mirrored, "lower_is_worse", 0.5, 1.0, 2.5, False)
    got = row(vals, 5)
    assert vals["THRESHOLDS!M5"] == "" and ref["refused"] is None
    assert got[0] == pytest.approx(ref["median"]) and got[3:7] == pytest.approx(ref["bounds"])
    assert ref["bounds"] == sorted(ref["bounds"], reverse=True)          # lower is worse: lines fall
    assert vals["THRESHOLDS!J5"] == pytest.approx(mirrored[-1])
    assert got[7] == score(mirrored[-1], ref["bounds"], "lower_is_worse", rule, False)
    want = [sum(1 for x in mirrored if score(x, ref["bounds"], "lower_is_worse", rule, False) == k)
            for k in range(1, 6)]
    assert [vals["ASSESS!E%d" % r] for r in range(8, 13)] == want


@pytest.mark.parametrize("cells, which", [
    ({"B6": "2008Q1"}, "first"),                                        # a start and nothing else
    ({"B6": "2012Q4", "C6": "2008Q1", "D6": "x"}, "first"),              # reversed
    ({"B6": "2008Q1", "C6": "2012Q4"}, "first"),                         # no reason
    ({"B6": "2008-Q1", "C6": "2012Q4", "D6": "x"}, "first"),             # not a quarter on the calendar
    ({"E6": "2020Q1", "F6": "2021Q1"}, "second"),
])
def test_a_leave_out_that_is_not_whole_is_refused_live(built, tmp_path, cells, which):
    p, _, _ = built
    vals = with_settings(p, tmp_path, "lo.xlsx", cells)
    assert vals["THRESHOLDS!M5"] == ("Refused: the %s leave-out needs a first and a last quarter from the data, "
                                     "in order, and a reason" % which)
    assert vals["THRESHOLDS!K5"] == ""


def test_a_whole_leave_out_is_not_refused(built, tmp_path):
    p, _, _ = built
    vals = with_settings(p, tmp_path, "ok.xlsx", {"B6": "2007Q4", "C6": "2012Q4", "D6": "the 2008 crisis"})
    assert vals["THRESHOLDS!M5"] == ""


@pytest.mark.parametrize("cells, why", [({"H6": -0.5}, "Moderate's half-width must be 0 or more"),
                                        ({"J6": 0}, "High's z must be above 0")])
def test_the_workbook_refuses_a_negative_half_width_or_z_live(built, tmp_path, cells, why):
    p, _, _ = built
    assert with_settings(p, tmp_path, "neg.xlsx", cells)["THRESHOLDS!M5"] == "Refused: " + why


def test_the_workbook_is_never_written_over_its_own_input(tmp_path):
    src = tmp_path / "cards.csv"
    src.write_bytes((DATA / "cards_nco_ttm.csv").read_bytes())
    before = src.read_bytes()
    for out in (src, tmp_path / "x" / ".." / "cards.csv"):
        with pytest.raises(ValueError, match="must be written to a .xlsx file"):
            make(out)
    alias = tmp_path / "cards.xlsx"
    alias.write_bytes(before)
    with pytest.raises(ValueError, match="would be written over cards.xlsx"):
        build(alias, [("Cards", alias)], name="NCO", unit="%", direction="higher_is_worse",
              frequency="quarterly", smoothing=1, floor_at_zero=True, moderate_halfwidth=0.5, low_step=1.0,
              high_z=2.5, on_the_line="worse", half_lives=(), percentiles=(50,), horizon=4, min_history=41)
    assert src.read_bytes() == before and alias.read_bytes() == before


def test_the_assess_bands_stack_from_the_floor_when_values_go_below_zero(tmp_path):
    """The Codex review (13 Oct 2026): with cut-offs below zero the first band
    was the cut-off itself, a negative width. The stack now starts at an
    invisible base, the chart's floor, and every band is a gap >= 0."""
    src = tmp_path / "neg.csv"
    src.write_text("date,value\n" + "".join("%s,%r\n" % (p.date, p.value - 6) for p in load("cards_nco_ttm.csv")),
                   encoding="utf-8")
    p = tmp_path / "neg.xlsx"
    build(p, [("Net", src)], name="Net", unit="%", direction="higher_is_worse", frequency="quarterly",
          smoothing=1, floor_at_zero=False, moderate_halfwidth=0.5, low_step=1.0, high_z=2.5,
          on_the_line="worse", half_lives=(), percentiles=(50, 75, 90, 95), horizon=4, min_history=41)
    vals = recalc(p)
    lines = [vals["THRESHOLDS!%s5" % c] for c in "EFGH"]
    assert vals["THRESHOLDS!M5"] == "" and lines[0] < 0
    ws = load_workbook(p)["Assess"]
    first = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 12).value == "Quarter") + 1
    floor = vals["ASSESS!U%d" % (first + 1)]
    top = vals["ASSESS!U%d" % first]
    data = [v for v in (vals.get("ASSESS!O%d" % r) for r in range(first, ws.max_row + 1)) if isinstance(v, float)]
    mn, mx = min(min(data), min(lines)), max(max(data), max(lines))
    assert floor == pytest.approx(mn - 0.08 * (mx - mn)) and top > mx        # not floored: 8% below the lowest
    assert vals["ASSESS!V%d" % first] == pytest.approx(floor)                  # the base
    widths = [vals["ASSESS!%s%d" % (get_column_letter(c), first)] for c in range(16, 21)]
    assert all(w >= 0 for w in widths)
    assert floor + sum(widths) == pytest.approx(top)
    assert floor + widths[0] == pytest.approx(lines[0])


def test_the_assess_axis_labels_negative_numbers_only_when_they_are_real(built, tmp_path):
    """Mortgage and home equity net charge-offs go below zero (net recoveries),
    and the axis used to hide every negative label; now it hides them only
    when nothing real can be negative (floored, and no value below zero)."""
    fmt = lambda p: load_workbook(p)["Assess"]._charts[0].y_axis.number_format.formatCode     # noqa: E731
    assert fmt(built[0]) == "0.0"                          # mortgage and home equity dip below zero
    cards = tmp_path / "cards.xlsx"
    build(cards, SERIES[:1], name="NCO", unit="%", direction="higher_is_worse", frequency="quarterly",
          smoothing=1, floor_at_zero=True, moderate_halfwidth=0.5, low_step=1.0, high_z=2.5,
          on_the_line="worse", half_lives=(), percentiles=(50,), horizon=4, min_history=41)
    assert fmt(cards) == "0.0;;0.0"                        # nothing below zero: the strip is unlabelled
    assert load_workbook(cards)["Assess"]._charts[0].y_axis.scaling.min is None      # floored: Excel's own
    src = tmp_path / "neg.csv"
    src.write_text("date,value\n" + "".join("%s,%r\n" % (p.date, p.value - 6) for p in load("cards_nco_ttm.csv")),
                   encoding="utf-8")
    p = tmp_path / "neg.xlsx"
    build(p, [("Net", src)], name="Net", unit="%", direction="higher_is_worse", frequency="quarterly",
          smoothing=1, floor_at_zero=False, moderate_halfwidth=0.5, low_step=1.0, high_z=2.5,
          on_the_line="worse", half_lives=(), percentiles=(50,), horizon=4, min_history=41)
    assert fmt(p) == "0.0"


def test_text_in_the_moderate_low_step_is_refused_not_an_error(built, tmp_path):
    p, _, _ = built
    vals = with_settings(p, tmp_path, "ls.xlsx", {"I6": "one"})
    assert vals["THRESHOLDS!M5"] == "Refused: Moderate-Low's step must be a number"
    assert vals["THRESHOLDS!K5"] == "" and vals["THRESHOLDS!E5"] == ""


@pytest.mark.parametrize("cell", ["H6", "I6", "J6"])
def test_text_in_a_setting_leaves_no_error_on_the_assess_dials(built, tmp_path, cell):
    """The Codex review (13 Oct 2026, on #426 after merge): the Thresholds tab
    refused text in the low step, but the Assess dials multiplied it and
    showed #VALUE!. Every dial row is now blank, and says why, when a setting
    it uses is not a number; the same holds for the half-width and z."""
    p, _, _ = built
    vals = with_settings(p, tmp_path, "t%s.xlsx" % cell, {cell: "one"})
    ws = load_workbook(p)["Assess"]
    rows = [r for r in range(49, ws.max_row + 1) if isinstance(ws.cell(r, 2).value, str)
            and ws.cell(r, 2).value.startswith("=") and ws.cell(r, 11).value]
    assert rows
    for r in rows:
        for c in "ABCDEFGHIJK":
            v = vals.get("ASSESS!%s%d" % (c, r))
            assert not (isinstance(v, str) and v.startswith("#")), (c, r, v)
    refused = [vals["ASSESS!K%d" % r] for r in rows]
    assert any(v == "refused: a setting is not a number" for v in refused)


@pytest.mark.parametrize("product", ["Mortgage", "Home equity", "Other consumer"])
def test_assess_draws_every_band_for_a_product_that_starts_after_the_calendar(built, tmp_path, product):
    """The walkthrough (13 Oct 2026), in Excel: for a product whose data starts
    after the first quarter on the calendar, the chart's top and floor were
    MAX and MIN over a column holding #N/A, so both were #N/A, and Low and
    High vanished while the other bands were drawn from zero."""
    p = built[0]
    wb = load_workbook(p)
    wb["Assess"]["B4"] = product
    q = tmp_path / ("assess-%s.xlsx" % product.replace(" ", "-"))
    wb.save(q)
    vals = recalc(q)
    ws = wb["Assess"]
    first = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 12).value == "Quarter") + 1
    top, floor = vals["ASSESS!U%d" % first], vals["ASSESS!U%d" % (first + 1)]
    assert all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (top, floor)), (top, floor)
    lines = [vals["ASSESS!C%d" % r] for r in (9, 10, 11, 12)]
    data = [v for v in (vals.get("ASSESS!O%d" % r) for r in range(first, ws.max_row + 1)) if isinstance(v, float)]
    assert floor == pytest.approx(min(0, min(data), min(lines))) and top > max(max(data), max(lines))
    widths = [vals["ASSESS!%s%d" % (get_column_letter(c), first)] for c in range(16, 21)]
    assert all(isinstance(w, (int, float)) and w >= 0 for w in widths), widths
    assert floor + widths[0] == pytest.approx(lines[0]) and floor + sum(widths) == pytest.approx(top)


def test_the_chart_tabs_legend_sits_below_the_plot(built):
    """The walkthrough (13 Oct 2026): in Excel 16 the legend on the right was
    drawn over the right-hand ends of the cutoff lines."""
    lc = load_workbook(built[0])["Chart"]._charts[0]
    assert lc.legend.position == "b" and not lc.legend.overlay


def test_the_backtest_glossary_entry_says_one_thing_about_the_history_used():
    """The Codex review (13 Oct 2026, on #426 after merge): the meaning said
    the scored quarter is included and the calculation said 'before it'."""
    from threshold_engine.glossary import TERMS
    entry = next(t for t in TERMS if t[0] == "Backtest")
    assert "the quarter scored and those before it" in entry[1]
    assert "that quarter and the quarters before it" in entry[2]


def test_the_pickers_read_their_choices_from_cells_so_long_labels_survive(tmp_path):
    """The Codex review (13 Oct 2026): an inline dropdown list over 255
    characters is one Excel drops or repairs. The choices are cells now."""
    labels = ["%s, a long product label to push the list well past Excel's limit" % k
              for k in ("Cards", "Mortgage", "Home equity", "Other consumer")]
    labels = [l.replace(",", "") for l in labels]
    assert len(",".join(labels)) > 255
    p = tmp_path / "long.xlsx"
    build(p, list(zip(labels, [s for _, s in SERIES])), name="NCO", unit="%", direction="higher_is_worse",
          frequency="quarterly", smoothing=1, floor_at_zero=True, moderate_halfwidth=0.5, low_step=1.0,
          high_z=2.5, on_the_line="worse", half_lives=(), percentiles=(50,), horizon=4, min_history=41)
    wb = load_workbook(p)
    for sheet in ("Chart", "Assess"):
        for dv in wb[sheet].data_validations.dataValidation:
            assert len(dv.formula1) < 255 and not dv.formula1.startswith('"' + labels[0][:5]), (sheet, dv.formula1)
    chart = wb["Chart"]
    col = next(c for c in range(1, chart.max_column + 1) if chart.cell(1, c).value == "(none)")
    assert [chart.cell(1 + i, col).value for i in range(5)] == ["(none)"] + labels
    assert chart.column_dimensions[get_column_letter(col)].hidden


def test_the_backtest_tab_says_the_scored_quarter_is_in_its_own_history(built):
    banner = " ".join(str(c.value) for row in load_workbook(built[0])["Backtest"].iter_rows(max_row=3) for c in row if c.value)
    assert "up to and including it" in banner and "history before it" not in banner


def test_the_fixed_axis_holds_every_line_the_dials_offer(tmp_path):
    """Codex on #432: a measure not floored at zero gets a fixed axis minimum
    at build, which cannot follow later typing, so a larger Moderate-Low step
    could push score 2's line off the bottom. The minimum now sits under every
    line the dials try. A noisy series makes the point: at step 2 its line is
    below every value it ever took."""
    import random
    rnd = random.Random(7)
    src = tmp_path / "noisy.csv"
    pts = load("cards_nco_ttm.csv")
    src.write_text("date,value\n" + "".join("%s,%r\n" % (x.date, round(100 + 2 * rnd.random(), 3)) for x in pts),
                   encoding="utf-8")
    p = tmp_path / "noisy.xlsx"
    build(p, [("Noisy", src)], name="N", unit="", direction="higher_is_worse", frequency="quarterly", smoothing=1,
          floor_at_zero=False, moderate_halfwidth=0.5, low_step=1.0, high_z=2.5, on_the_line="worse", half_lives=(),
          percentiles=(50,), horizon=4, min_history=41)
    vals = [float(l.split(",")[1]) for l in src.read_text().splitlines()[1:]]
    ref = scale(vals, "higher_is_worse", 0.5, 2.0, 2.5, False)
    low_line = ref["median"] - 2.0 * ref["typical_yearly_move"]
    assert low_line < min(vals)                                   # the case that was clipped
    y_min = load_workbook(p)["Assess"]._charts[0].y_axis.scaling.min
    assert y_min is not None and y_min < low_line


def test_a_line_below_the_fixed_axis_is_said_not_clipped_in_silence(tmp_path):
    """Codex on #432: a fixed axis cannot follow every leave-out or setting.
    When the floor or the left-out strip falls below it, the cell over the
    chart says so; as built it says nothing."""
    import random
    rnd = random.Random(7)
    src = tmp_path / "noisy.csv"
    pts = load("cards_nco_ttm.csv")
    src.write_text("date,value\n" + "".join("%s,%r\n" % (x.date, round(100 + 2 * rnd.random(), 3)) for x in pts),
                   encoding="utf-8")
    p = tmp_path / "noisy.xlsx"
    build(p, [("Noisy", src)], name="N", unit="", direction="higher_is_worse", frequency="quarterly", smoothing=1,
          floor_at_zero=False, moderate_halfwidth=0.5, low_step=1.0, high_z=2.5, on_the_line="worse", half_lives=(),
          percentiles=(50,), horizon=4, min_history=41)
    assert recalc(p)["ASSESS!A14"] == ""
    vals = with_settings(p, tmp_path, "far.xlsx", {"I6": 6})
    assert "below the axis of this chart" in vals["ASSESS!A14"]
