"""floor_off: a measure the book names has no floor at zero (17 Oct 2026, the
gap measures). Its lines are set without the floor, its series' flag on Lines
by source is FALSE, and every rating formula reads that flag instead of a
constant, so a negative gap is rated on its lines, never 1 Low by the floor."""
import json
import shutil
from pathlib import Path

import pytest
from openpyxl import load_workbook

from conftest import DATA
from threshold_engine import book as BK
from threshold_engine import decide_tab as DT
from threshold_engine.scale import scale
from threshold_engine.workbook import read_series

WORKBOOK = {"name": "A test", "unit": "%", "direction": "higher_is_worse", "frequency": "quarterly", "smoothing": 1,
            "floor_at_zero": True, "moderate_halfwidth": 0.5, "low_step": 1.0, "high_z": 2.5, "on_the_line": "worse",
            "half_lives": [], "percentiles": [50, 75, 90], "horizon": 4, "min_history": 20}


def write_book(folder, floor_off, series_extra=()):
    files = folder / "files"
    files.mkdir(parents=True)
    shutil.copy(DATA / "cards_nco_ttm.csv", files / "cards_nco_ttm.csv")
    pts = read_series(DATA / "cards_nco_ttm.csv")
    # A gap: the series less its own median, so it runs negative half the time.
    med = sorted(p.value for p in pts)[len(pts) // 2]
    with (files / "gap.csv").open("w", encoding="utf-8") as fh:
        fh.write("# Card, Gap to peers on Net: a test series that is negative half the time.\ndate,value\n")
        for p in pts:
            fh.write("%s,%s\n" % (p.date, p.value - med))
    book = {"workbook": dict(WORKBOOK), "parts": ["Product", "Measure", "Source"],
            "lines_from": {"part": "Source", "start": "Bank"},
            "series": [{"Product": "Card", "Measure": "Net", "Source": "Bank", "file": "files/cards_nco_ttm.csv"},
                       {"Product": "Card", "Measure": "Gap to peers on Net", "Source": "Bank", "file": "files/gap.csv"}]
            + list(series_extra),
            "not_in_book": [], "compare": None, "notes": [], "peers": None, "internal": None, "loan_classes": None,
            "reporting_changes": None, "floor_off": floor_off, "large_banks": None, "signals": None}
    p = folder / "book.json"
    p.write_text(json.dumps(book), encoding="utf-8")
    return p


def test_floor_off_must_name_a_measure_of_the_book(tmp_path):
    with pytest.raises(BK.BookError, match="floor_off names 'Nope', which is not a Measure"):
        BK.load(write_book(tmp_path, ["Nope"]))
    bk = BK.load(write_book(tmp_path / "b", ["Gap to peers on Net"]))
    assert bk["decide"]["floor_off"] == ["Gap to peers on Net"]


def test_floor_off_with_no_floor_to_switch_off_is_refused(tmp_path):
    p = write_book(tmp_path, ["Gap to peers on Net"])
    raw = json.loads(p.read_text(encoding="utf-8"))
    raw["workbook"]["floor_at_zero"] = False
    p.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(BK.BookError, match="no floor at zero to switch off"):
        BK.load(p)


def test_a_measure_without_a_floor_is_rated_on_its_lines(tmp_path):
    out = tmp_path / "out.xlsx"
    info = BK.build(write_book(tmp_path, ["Gap to peers on Net"]), out, say=lambda s: None)
    wb = load_workbook(out)
    # On Decide, round 3: a row without a floor has no bottom, so 1 Low
    # begins below line 2; zero is drawn where the axis crosses, SLATE 0.75 pt.
    lay = info["decide"]["layout"]
    fz_ = "$%s$12" % DT.L(DT.H)
    low = wb["Decide"].cell(lay["ratings_first"], 13).value
    assert fz_ in low and '"the bottom"' in low and '"below "&TEXT(' in low
    zero = info["decide"]["helpers"]["zero"]
    assert wb["Decide"]["%s2" % zero].value == "=IF(AND(%s,NOT(%s),%s),0,NA())" % (
        "AND($%s$2=1,ISNUMBER($%s$3))" % (DT.L(DT.H), DT.L(DT.H)), fz_,
        "AND(2>=$%s$2,2<=$%s$4)" % (info["decide"]["helpers"]["fit"], info["decide"]["helpers"]["fit"]))
    chart = wb["Decide"]._charts[0]
    first = chart.series[0]
    assert first.val.numRef.f == "Decide!dq_zero"
    assert first.spPr.ln.solidFill.srgbClr == DT.K.SLATE and first.spPr.ln.w == 9525
    lbs = wb[DT.LINES_TAB]
    T = DT.TH_BOOK
    assert lbs["%s4" % T["floor"]].value == "Floor at zero"
    flags = {lbs["A%d" % r].value: lbs["%s%d" % (T["floor"], r)].value for r in (5, 6)}
    assert flags == {"Card - Net - Bank": True, "Card - Gap to peers on Net - Bank": False}
    assert lbs.column_dimensions[T["floor"]].hidden
    # The gap's lines are set without the floor: the refusal formula's floor term is FALSE for it.
    assert "IF(AND(FALSE," in lbs["%s6" % T["refusal"]].value and "IF(AND(TRUE," in lbs["%s5" % T["refusal"]].value
    # Decide's rating formulas read the flag of the row shown, never a constant.
    de = wb["Decide"]
    fz = "$%s$12" % DT.L(DT.H)
    assert de["%s" % fz].value.startswith("=IF(")
    formulas = [c.value for row in de.iter_rows() for c in row if isinstance(c.value, str) and "<=0),1," in c.value]
    assert formulas and all(fz in f for f in formulas)
    # The gap's own lines, set without the floor, as scale.py sets them.
    pts = read_series(tmp_path / "files" / "gap.csv")
    ref = scale([p.value for p in pts], "higher_is_worse", 0.5, 1.0, 2.5, False)
    assert ref["bounds"] is not None and ref["bounds"][0] < 0
    # Thresholds rates the gap row with FALSE and the rate row with TRUE.
    th = wb["Thresholds"]
    cells = {th["C%d" % r].value: [c.value for c in th[r] if isinstance(c.value, str) and "<=0),1," in c.value]
             for r in (5, 6)}
    assert all("AND(TRUE," in f for f in cells["Net"]) and all("AND(FALSE," in f for f in cells["Gap to peers on Net"])
    note = [c.value for row in wb["Thresholds"].iter_rows() for c in row
            if isinstance(c.value, str) and c.value.startswith("Ratings: 1 Low")][0]
    assert "except on Gap to peers on Net, which has no floor at zero" in note
