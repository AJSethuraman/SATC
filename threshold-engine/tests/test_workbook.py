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
              floor_at_zero=True, top_fraction=0.75, on_the_line="worse", half_lives=(10,),
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
    assert st["F6"].value == "Leave out 2007Q4 to 2012Q4"
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
    wb["Settings"]["E6"] = "better"
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
    rows = {r[0].value: r for r in run.iter_rows(min_row=8) if r[0].value}
    for label, path in SERIES:
        assert rows[label][2].value == hashlib.sha256(path.read_bytes()).hexdigest()


def test_mixed_or_duplicate_inputs_are_refused(tmp_path):
    with pytest.raises(ValueError):
        build(tmp_path / "x.xlsx", SERIES[:1] * 2, "NCO", "%", "higher_is_worse", "quarterly", 1, True,
              0.75, "worse", (), (50, 75, 90, 95), 4, 41)
    with pytest.raises(ValueError):
        make(tmp_path / "y.xlsx", on_the_line="sometimes")
