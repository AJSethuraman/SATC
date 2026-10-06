"""The workbook: Excel's live cutoffs must equal Python's, before and after the
bank changes a setting. Recalculated with the `formulas` engine, so no copy of
Excel is needed; a skip is reported, never counted as a pass."""
import pytest
from openpyxl import load_workbook

from conftest import DATA
from threshold_engine.workbook import build, quarter

formulas = pytest.importorskip("formulas", reason="the formulas engine recalculates the workbook")

SERIES = [("Credit card", DATA / "cards_nco_ttm.csv"), ("Mortgage", DATA / "mortgage_nco_ttm.csv"),
          ("Home equity", DATA / "home_equity_nco_ttm.csv"),
          ("Other consumer", DATA / "other_consumer_as_filed_nco_ttm.csv")]


def make(path, **over):
    kw = dict(name="NCO", unit="%", direction="higher_is_worse", frequency="quarterly", smoothing=1,
              floor_at_zero=True, score2_percentile=50, top_fraction=0.75, on_the_line="worse", half_lives=(10,),
              percentiles=(50, 75, 90, 95), horizon=4, min_history=41)
    kw.update(over)
    return build(path, SERIES, **kw)


def recalc(path):
    """Every cell's value after a full recalculation, keyed 'SHEET!A1'."""
    model = formulas.ExcelModel().loads(str(path)).finish()
    sol = model.calculate()
    out = {}
    for key, val in sol.items():
        ref = key.split("]")[-1].upper()          # "'[book.xlsx]THRESHOLDS'!B5" -> "THRESHOLDS'!B5"
        v = getattr(val, "value", val)
        try:
            v = v.item(0) if hasattr(v, "item") else v
        except Exception:                          # noqa: BLE001
            pass
        out[ref.replace("'", "")] = v
    return out


def row(vals, r):
    return [vals.get("THRESHOLDS!%s%d" % (c, r)) for c in "BCDEFGJ"]


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    p = tmp_path_factory.mktemp("wb") / "t.xlsx"
    info = make(p)
    return p, info, recalc(p)


def test_as_built_the_live_cutoffs_equal_scenario_a(built):
    _, info, vals = built
    for r, (label, _) in enumerate(SERIES, start=5):
        a = info["evidence"][label]["scenarios"][0]
        got = row(vals, r)
        assert got[0] == pytest.approx(a["normal"]) and got[1] == pytest.approx(a["worst_kept"])
        assert got[2:6] == pytest.approx(a["bounds"])
        assert got[6] == a["latest_score"]


def test_typing_the_evidence_suggestion_reproduces_scenario_c(built, tmp_path):
    p, info, _ = built
    wb = load_workbook(p)
    st = wb["Settings"]
    assert st["K6"].value == "Leave out 2007Q4 to 2012Q4"
    st["B6"], st["C6"] = "2007Q4", "2012Q4"
    q = tmp_path / "c.xlsx"
    wb.save(q)
    got = row(recalc(q), 5)
    c = info["evidence"]["Credit card"]["scenarios"][2]
    assert got[2:6] == pytest.approx(c["bounds"])
    assert [round(x, 3) for x in got[2:6]] == [3.720, 4.441, 5.162, 5.882]


def test_the_on_the_line_rule_is_live(built, tmp_path):
    # Cards' latest 3.978 sits exactly on the as-built score-2 line.
    p, _, vals = built
    assert row(vals, 5)[6] == 2
    wb = load_workbook(p)
    wb["Settings"]["J6"] = "better"
    q = tmp_path / "b.xlsx"
    wb.save(q)
    assert row(recalc(q), 5)[6] == 1


def test_a_floor_at_zero_normal_is_refused_in_the_workbook(tmp_path):
    p = tmp_path / "z.xlsx"
    make(p)
    wb = load_workbook(p)
    # Mortgage with everything before 2018 left out: the quiet years alone,
    # whose median is below zero. The cutoffs must refuse, not draw a scale.
    wb["Settings"]["B7"], wb["Settings"]["C7"] = "1991Q4", "2017Q4"
    wb.save(p)
    vals = recalc(p)
    assert row(vals, 6)[0] <= 0
    assert vals["THRESHOLDS!L6"] == "Refused: normal level at or below zero"
    assert vals["THRESHOLDS!D6"] == "" and vals["THRESHOLDS!J6"] == ""


def test_every_series_is_on_one_quarterly_calendar(built):
    p, info, _ = built
    da = load_workbook(p)["Data"]
    qs = [c.value for c in da["A"][1:]]
    assert qs == sorted(qs) and len(qs) == info["quarters"] and qs[0] == "1985Q4"
    assert quarter("2010-04-01") == quarter("2010-06-30") == "2010Q2"


def test_the_run_tab_fingerprints_every_file(built):
    import hashlib
    p, _, _ = built
    run = load_workbook(p)["Run"]
    rows = {r[0].value: r for r in run.iter_rows(min_row=8)
            if r[0].value and len(str(r[2].value or "")) == 64}
    for label, path in SERIES:
        assert rows[label][2].value == hashlib.sha256(path.read_bytes()).hexdigest()


def test_mixed_or_duplicate_inputs_are_refused(tmp_path):
    with pytest.raises(ValueError):
        build(tmp_path / "x.xlsx", SERIES[:1] * 2, "NCO", "%", "higher_is_worse", "quarterly", 1, True,
              50, 0.75, "worse", (), (50, 75, 90, 95), 4, 41)
    with pytest.raises(ValueError):
        make(tmp_path / "y.xlsx", on_the_line="sometimes")


def test_two_leave_out_windows_combine_and_each_carries_a_reason(built, tmp_path):
    import statistics
    from conftest import load
    p, _, _ = built
    wb = load_workbook(p)
    st = wb["Settings"]
    st["B6"], st["C6"], st["D6"] = "2007Q4", "2012Q4", "Largest spell; not the only stress"
    st["E6"], st["F6"], st["G6"] = "2021Q3", "2023Q1", "Pandemic forbearance"
    q = tmp_path / "two.xlsx"
    wb.save(q)
    vals = recalc(q)
    kept = [x.value for x in load("cards_nco_ttm.csv")
            if not ("2007Q4" <= quarter(x.date) <= "2012Q4" or "2021Q3" <= quarter(x.date) <= "2023Q1")]
    assert vals["THRESHOLDS!B5"] == pytest.approx(statistics.median(kept))
    assert vals["THRESHOLDS!C5"] == pytest.approx(max(kept))
    run = {k: v for k, v in vals.items() if k.startswith("RUN!")}
    assert "2021Q3 to 2023Q1" in run.values() and "Pandemic forbearance" in run.values()


def test_settings_lists_the_departures_the_data_found(built):
    p, info, _ = built
    st = load_workbook(p)["Settings"]
    assert "2021Q3 to 2023Q1 below the path" in st["L6"].value
    assert "2008" not in (st["M6"].value or "")


def test_assess_counts_the_quarters_in_each_score_live(built, tmp_path):
    import statistics
    from conftest import load
    p, _, _ = built
    wb = load_workbook(p)
    st = wb["Settings"]
    st["B6"], st["C6"] = "2007Q4", "2012Q4"
    st["E6"], st["F6"] = "2021Q3", "2023Q1"
    q = tmp_path / "assess.xlsx"
    wb.save(q)
    vals = recalc(q)
    pts = load("cards_nco_ttm.csv")
    gone = lambda x: "2007Q4" <= quarter(x.date) <= "2012Q4" or "2021Q3" <= quarter(x.date) <= "2023Q1"  # noqa: E731
    kept = [x.value for x in pts if not gone(x)]
    n_, w_ = statistics.median(kept), max(kept)
    b = [n_ + i * 0.75 * (w_ - n_) / 3 for i in range(4)]
    score = lambda v: 1 + sum(1 for x in b if v >= x)                                        # noqa: E731
    want_kept = [sum(1 for v in kept if score(v) == k) for k in range(1, 6)]
    want_all = [sum(1 for x in pts if score(x.value) == k) for k in range(1, 6)]
    assert [vals["ASSESS!E%d" % r] for r in range(8, 13)] == want_kept == [67, 29, 22, 12, 5]
    assert [vals["ASSESS!G%d" % r] for r in range(8, 13)] == want_all
    assert vals["ASSESS!F8"] == pytest.approx(67 / 135)


def test_assess_follows_the_on_the_line_rule(built, tmp_path):
    # As built, cards' median 3.978 is a recorded value and sits on the score-2
    # line: "worse" counts it in score 2, "better" in score 1.
    p, _, vals = built
    worse = [vals["ASSESS!E%d" % r] for r in (8, 9)]
    wb = load_workbook(p)
    wb["Settings"]["J6"] = "better"
    q = tmp_path / "line.xlsx"
    wb.save(q)
    v2 = recalc(q)
    better = [v2["ASSESS!E%d" % r] for r in (8, 9)]
    on_line = sum(1 for x in __import__("conftest").load("cards_nco_ttm.csv") if x.value == 3.978)
    assert on_line >= 1
    assert better[0] - worse[0] == on_line and worse[1] - better[1] == on_line


def test_the_strip_marks_exactly_the_quarters_left_out_and_the_caption_says_why(built, tmp_path):
    from openpyxl.utils import get_column_letter
    p, info, _ = built
    wb = load_workbook(p)
    st = wb["Settings"]
    st["B6"], st["C6"], st["D6"] = "2007Q4", "2012Q4", "Financial crisis"
    st["E6"], st["F6"], st["G6"] = "2021Q3", "2023Q1", "Pandemic forbearance"
    q = tmp_path / "strip.xlsx"
    wb.save(q)
    vals = recalc(q)
    qcol, scol = get_column_letter(12), get_column_letter(23)        # quarter, strip
    marked = [vals["ASSESS!%s%d" % (qcol, r)] for r in range(2, info["quarters"] + 2)
              if vals["ASSESS!%s%d" % (scol, r)] != 0]
    want = [x for x in (vals["ASSESS!%s%d" % (qcol, r)] for r in range(2, info["quarters"] + 2))
            if "2007Q4" <= x <= "2012Q4" or "2021Q3" <= x <= "2023Q1"]
    assert marked == want and len(marked) == 21 + 7
    assert vals["ASSESS!A41"] == "2007Q4 to 2012Q4: Financial crisis"
    assert vals["ASSESS!A42"] == "2021Q3 to 2023Q1: Pandemic forbearance"
    assert vals["ASSESS!A43"] == ""


def test_with_nothing_left_out_the_caption_says_so(built):
    _, _, vals = built
    assert vals["ASSESS!A41"] == "" and vals["ASSESS!A43"] == "Nothing left out: every quarter counts."



def test_score_2_can_begin_lower_and_assess_shows_what_that_does(built, tmp_path):
    from conftest import load
    from threshold_engine.profile import percentile
    p, _, _ = built
    wb = load_workbook(p)
    st = wb["Settings"]
    st["B6"], st["C6"] = "2007Q4", "2012Q4"
    st["E6"], st["F6"] = "2021Q3", "2023Q1"
    st["H6"] = 33
    q = tmp_path / "p33.xlsx"
    wb.save(q)
    vals = recalc(q)
    pts = load("cards_nco_ttm.csv")
    gone = lambda x: "2007Q4" <= quarter(x.date) <= "2012Q4" or "2021Q3" <= quarter(x.date) <= "2023Q1"  # noqa: E731
    kept = [x.value for x in pts if not gone(x)]
    start = percentile(kept, 33)                     # Excel's PERCENTILE, same interpolation
    assert vals["THRESHOLDS!B5"] == pytest.approx(start)
    b = [start + i * 0.75 * (max(kept) - start) / 3 for i in range(4)]
    want = [sum(1 for v in kept if 1 + sum(1 for x in b if v >= x) == k) for k in range(1, 6)]
    assert [vals["ASSESS!E%d" % r] for r in range(8, 13)] == want
    assert want[0] == 45                             # Low: a third of 135 quarters, not half


def test_a_score_2_percentile_out_of_range_is_refused(tmp_path):
    with pytest.raises(ValueError):
        make(tmp_path / "bad.xlsx", score2_percentile=0)
