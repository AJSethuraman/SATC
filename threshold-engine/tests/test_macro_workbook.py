"""The workbook the teams read: built only from a finished run, values not
formulas, and a missing month left empty so no chart draws it as zero."""
import re
import zipfile

import pytest

openpyxl = pytest.importorskip("openpyxl")

from threshold_engine.macro import rate as R
from threshold_engine.macro.catalog import RATED, SERIES, STATES
from threshold_engine.macro.settings import check
from threshold_engine.macro.workbook import build

from test_macro_rate import cache  # noqa: F401  (the fixture: a pull on disk)
from test_macro_settings import answered


def _build(cache, path, **answers):  # noqa: F811
    pull = R.Pull(cache)
    result = R.rate_all(cache, check(answered(**answers)), pull=pull)
    out = build(path, result, pull)
    return out, result, openpyxl.load_workbook(out)


@pytest.fixture
def book(cache, tmp_path):  # noqa: F811
    return _build(cache, tmp_path / "macro.xlsx", show_sahm=False)


def test_the_sheets_are_the_ratings_first_then_one_per_national_series(book):
    _, result, wb = book
    states = {"unemployment_" + st.lower() for st in STATES}
    national = [i.key for i in RATED if i.key not in states]
    assert wb.sheetnames == (["Ratings", "States"] + national
                             + ["State data", "Not rated", "Settings", "Sources"])


def test_the_ratings_sheet_lists_every_national_rating_highest_first(book):
    _, result, wb = book
    ws = wb["Ratings"]
    head = next(r for r in range(1, 20) if ws.cell(r, 1).value == "Rating")
    rows = [ws.cell(r, 1).value for r in range(head + 1, ws.max_row + 1)
            if ws.cell(r, 1).value and ws.cell(r, 1).value[0].isdigit()]
    national = [r for r in result["ratings"] if not r["key"].startswith("unemployment_")]
    assert len(rows) == len(national)
    assert rows == sorted(rows, key=lambda x: -int(x[0]))
    assert rows[0] == "5 High"                          # the fixture's record unemployment rate


def test_a_missing_month_is_an_empty_cell_and_says_so(book):
    _, _, wb = book
    ws = wb["unemployment"]
    row = next(r for r in range(1, ws.max_row + 1)
               if getattr(ws.cell(r, 1).value, "isoformat", None) and ws.cell(r, 1).value.isoformat()[:10] == "2025-10-01")
    assert ws.cell(row, 2).value is None                # not zero, not text a chart would draw as zero
    assert ws.cell(row, 4).value == "no value published"


def test_every_chart_leaves_a_gap_where_a_value_is_missing(book):
    out, _, _ = book
    with zipfile.ZipFile(out) as z:
        charts = [n for n in z.namelist() if n.startswith("xl/charts/chart")]
        assert charts
        for n in charts:
            assert re.search(rb'dispBlanksAs val="gap"', z.read(n)), n


def test_every_number_is_a_value_not_a_formula(book):
    _, _, wb = book
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                assert not (isinstance(c.value, str) and c.value.startswith("=")), (ws.title, c.coordinate)


def test_the_settings_sheet_shows_the_answers_the_run_used(book):
    _, _, wb = book
    ws = wb["Settings"]
    got = {ws.cell(r, 1).value: ws.cell(r, 2).value for r in range(2, ws.max_row + 1)}
    assert got["Where ratings 2 to 5 start"].startswith("40, 60, 80, 97")
    assert got["Sahm reading shown"] == "no" and got["History each reading is measured against"] == "the last 20 years"


def test_the_sahm_reading_appears_only_when_the_firm_asked_for_it(book, cache, tmp_path):  # noqa: F811
    def text(wb):
        return " ".join(str(c.value) for row in wb["Ratings"].iter_rows() for c in row if c.value is not None)
    assert "Sahm reading for" not in text(book[2]) and "not shown" in text(book[2])
    shown = _build(cache, tmp_path / "sahm.xlsx", show_sahm=True)[2]
    assert "Sahm reading for" in text(shown) and "trigger 0.50" in text(shown)
    assert shown["Settings"]["B6"].value == "yes"


def test_states_have_their_own_sheet_and_stay_off_the_national_one(book):
    _, result, wb = book
    assert any(r["key"] == "unemployment_ca" for r in result["ratings"])
    ratings = " ".join(str(c.value) for row in wb["Ratings"].iter_rows() for c in row if c.value)
    assert "Unemployment rate, CA" not in ratings
    ws = wb["States"]
    ca = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 1).value == "CA")
    assert ws.cell(ca, 4).value[0].isdigit() and ws.cell(ca, 7).value[0].isdigit()
    tx = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 1).value == "TX")
    assert ws.cell(tx, 2).value == "not in this pull"


def test_the_sources_sheet_fingerprints_every_file_the_pull_fetched(book):
    _, _, wb = book
    ws = wb["Sources"]
    rows = {ws.cell(r, 1).value: [ws.cell(r, j).value for j in range(1, 10)] for r in range(2, ws.max_row + 1)}
    assert all(s.title in rows for s in SERIES)
    assert len(rows["Unemployment rate"][8]) == 64     # SHA-256 of the file the rating read
    assert rows["Initial jobless claims"][7] == "not in this pull"
