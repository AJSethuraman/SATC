"""The workbook the teams read: built only from a finished run, values not
formulas, a missing month left empty so no chart draws it as zero, and the
five rating bands drawn under every history line."""
import re
import zipfile

import pytest

openpyxl = pytest.importorskip("openpyxl")

from threshold_engine.macro import rate as R
from threshold_engine.macro.catalog import HIGHER, LOWER, RATED, SERIES, STATES
from threshold_engine.macro.settings import check
from threshold_engine.macro.workbook import TAB, TOPICS, band_heights, build, glossary, nice_axis

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


def _text(ws):
    return " ".join(str(c.value) for row in ws.iter_rows() for c in row if c.value is not None)


def test_every_national_series_has_one_topic_and_one_tab():
    states = {"unemployment_" + st.lower() for st in STATES}
    national = sorted(i.key for i in RATED if i.key not in states)
    in_topics = [k for _, keys in TOPICS for k in keys]
    assert sorted(in_topics) == national and len(set(in_topics)) == len(in_topics)
    assert sorted(TAB) == national
    assert len(set(TAB.values())) == len(TAB) and all(len(v) <= 31 for v in TAB.values())


def test_the_sheets_are_the_ratings_first_then_one_per_series_by_topic(book):
    _, _, wb = book
    tabs = [TAB[k] for _, keys in TOPICS for k in keys]
    assert wb.sheetnames == (["Ratings", "States"] + tabs
                             + ["State data", "Not rated", "Glossary", "Run", "Sources"])


def test_the_ratings_sheet_rates_every_national_series_under_its_topic(book):
    _, result, wb = book
    ws = wb["Ratings"]
    series_rows = [c.row for col in ws.iter_cols(min_col=2, max_col=2) for c in col if c.hyperlink]
    chips = [ws.cell(r, j).value for r in series_rows for j in (5, 8)
             if re.match(r"[1-5] (Low|Moderate|High)", str(ws.cell(r, j).value))]
    national = [r for r in result["ratings"] if not r["key"].startswith("unemployment_")]
    assert len(chips) == len(national)                  # one chip per rated reading
    text = _text(ws)
    for topic, _ in TOPICS:
        assert topic in text
    # the fixture's record unemployment rate is rated 5, and its row links to its tab
    link = next(c for row in ws.iter_rows(min_col=2, max_col=2) for c in row if c.value == "Unemployment rate")
    assert link.hyperlink.location == "'Unemployment'!A1" or link.hyperlink.target.endswith("'Unemployment'!A1")
    assert ws.cell(link.row, 5).value == "5 High"
    # the counts at the top are of national readings only, one per rating
    top = next(c.row for col in ws.iter_cols(min_col=5, max_col=5) for c in col if c.value == "5 High")
    counts = [ws.cell(top + 1, j).value for j in range(5, 10)]
    assert sum(counts) == len(national)
    assert counts == [sum(1 for r in national if r["rating"] == k) for k in (5, 4, 3, 2, 1)]


def test_a_missing_month_is_an_empty_cell_and_says_so(book):
    _, _, wb = book
    ws = wb["Unemployment"]
    row = next(c.row for col in ws.iter_cols(min_col=14, max_col=14) for c in col
               if getattr(c.value, "isoformat", None) and c.value.isoformat()[:10] == "2025-10-01")
    assert ws.cell(row, 15).value is None               # not zero, not text a chart would draw as zero
    assert ws.cell(row, 17).value == "no value published"


def test_every_chart_leaves_gaps_plots_its_hidden_bands_and_draws_them_under_the_line(book):
    out, _, _ = book
    with zipfile.ZipFile(out) as z:
        charts = [z.read(n) for n in z.namelist() if n.startswith("xl/charts/chart")]
    assert charts
    banded = [c for c in charts if b"areaChart" in c]
    assert banded
    for c in charts:
        assert re.search(rb'dispBlanksAs val="gap"', c)
    for c in banded:
        assert re.search(rb'plotVisOnly val="0"', c)    # the bands live in hidden columns
        assert c.index(b"areaChart") < c.index(b"lineChart")   # drawn first, so underneath


def test_the_bands_fill_the_axis_bottom_up_in_the_direction_of_stress():
    lines = {"2": 2.0, "3": 3.0, "4": 4.0, "5": None}
    base, heights, order = band_heights(lines, HIGHER, 1.0, 6.0)
    assert base == 1.0 and order == [1, 2, 3, 4, 5]
    assert heights == [1.0, 1.0, 1.0, 2.0, 0.0]         # 5 never reached: a band of no height
    assert sum(heights) == 5.0
    base, heights, order = band_heights({"2": 4.0, "3": 3.0, "4": 2.0, "5": 1.5}, LOWER, 1.0, 6.0)
    assert order == [5, 4, 3, 2, 1] and heights == [0.5, 0.5, 1.0, 1.0, 2.0]


def test_an_axis_rounds_out_to_a_tidy_step():
    assert nice_axis(2.5, 14.8) == (2.5, 15.0, 2.5)
    lo, hi, step = nice_axis(-9.6, 10.6)
    assert lo <= -9.6 and hi >= 10.6 and step == 5


def test_every_number_is_a_value_not_a_formula(book):
    _, _, wb = book
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                assert not (isinstance(c.value, str) and c.value.startswith("=")), (ws.title, c.coordinate)


def test_the_run_sheet_shows_the_answers_the_run_used(book):
    _, _, wb = book
    ws = wb["Run"]
    got = {ws.cell(r, 1).value: ws.cell(r, 2).value for r in range(1, ws.max_row + 1)}
    assert got["Where ratings 2 to 5 start"].startswith("40, 60, 80, 97")
    assert got["Sahm reading shown"] == "no" and got["History each reading is measured against"] == "the last 20 years"
    assert got["From the pull of"] == "2026-10-15"


def test_the_sahm_reading_appears_only_when_the_firm_asked_for_it(book, cache, tmp_path):  # noqa: F811
    assert "Sahm's published trigger" not in _text(book[2]["Ratings"])
    shown = _build(cache, tmp_path / "sahm.xlsx", show_sahm=True)[2]
    assert "Sahm's published trigger is 0.50" in _text(shown["Ratings"])
    assert "Sahm reading" in _text(shown["Unemployment"])


def test_states_have_their_own_sheet_and_stay_off_the_national_one(book):
    _, result, wb = book
    assert any(r["key"] == "unemployment_ca" for r in result["ratings"])
    assert "Unemployment rate, CA" not in _text(wb["Ratings"])
    ws = wb["States"]
    ca = next(c.row for col in ws.iter_cols(min_col=2, max_col=2) for c in col if c.value == "CA")
    assert ws.cell(ca, 5).value[0].isdigit() and ws.cell(ca, 8).value[0].isdigit()
    tx = next(c.row for col in ws.iter_cols(min_col=2, max_col=2) for c in col if c.value == "TX")
    assert ws.cell(tx, 3).value == "not in this pull"


def test_the_glossary_explains_every_term_a_reader_meets(book):
    _, _, wb = book
    terms = {wb["Glossary"].cell(r, 1).value for r in range(1, wb["Glossary"].max_row + 1)}
    for needed in ("Level", "Change over 6 months", "Percentile", "Rating", "From", "History from",
                   "At this rating since", "What stands out", "Change only", "Sahm reading", "No value published"):
        assert needed in terms, needed
    assert "2 starts at the 40th, 3 at the 60th, 4 at the 80th and 5 at the 97th" in dict(
        glossary(check(answered())))["Rating"]


def test_the_sources_sheet_fingerprints_every_file_the_pull_fetched(book):
    _, _, wb = book
    ws = wb["Sources"]
    rows = {ws.cell(r, 1).value: [ws.cell(r, j).value for j in range(1, 10)] for r in range(1, ws.max_row + 1)}
    assert all(s.title in rows for s in SERIES)
    assert len(rows["Unemployment rate"][8]) == 64     # SHA-256 of the file the rating read
    assert rows["Initial jobless claims"][7] == "not in this pull"
