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
from threshold_engine.macro.workbook import (SHOWN_NAME, SHOWN_TAB, SHOWN_TOPICS, TAB, TOPICS, band_heights, build,
                                             glossary, nice_axis)

from test_macro_rate import cache, shown_cache  # noqa: F401  (the fixtures: pulls on disk)
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
    shown = [SHOWN_TAB[k] for _, keys in SHOWN_TOPICS for k in keys]
    assert wb.sheetnames == (["Ratings", "States", SHOWN_NAME] + tabs + shown
                             + ["State data", "Not rated", "Glossary", "Run", "Sources"])


def test_the_ratings_sheet_rates_every_national_series_under_its_topic(book):
    _, result, wb = book
    ws = wb["Ratings"]
    series_rows = [c.row for col in ws.iter_cols(min_col=2, max_col=2) for c in col if c.hyperlink]
    chips = [ws.cell(r, j).value for r in series_rows for j in (6, 9)
             if re.match(r"[1-5] (Low|Moderate|High)", str(ws.cell(r, j).value))]
    national = [r for r in result["ratings"] if not r["key"].startswith("unemployment_")]
    assert len(chips) == len(national)                  # one chip per rated reading
    text = _text(ws)
    for topic, _ in TOPICS:
        assert topic in text
    # the fixture's record unemployment rate is rated 5, and its row links to its tab
    link = next(c for row in ws.iter_rows(min_col=2, max_col=2) for c in row if c.value == "Unemployment rate")
    assert link.hyperlink.location == "'Unemployment'!A1" or link.hyperlink.target.endswith("'Unemployment'!A1")
    assert ws.cell(link.row, 6).value == "5 High"
    # the counts at the top are of national readings only, one per rating
    top = next(c.row for col in ws.iter_cols(min_col=6, max_col=6) for c in col if c.value == "5 High")
    counts = [ws.cell(top + 1, j).value for j in range(6, 11)]
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
    got = {ws.cell(r, 2).value: ws.cell(r, 3).value for r in range(1, ws.max_row + 1)}
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
    terms = {wb["Glossary"].cell(r, 2).value for r in range(1, wb["Glossary"].max_row + 1)}
    for needed in ("Level", "Change over 6 months", "Percentile", "Rating", "From", "History from",
                   "At this rating since", "What stands out", "Change only", "Sahm reading", "No value published"):
        assert needed in terms, needed
    assert "2 starts at the 40th, 3 at the 60th, 4 at the 80th and 5 at the 97th" in dict(
        glossary(check(answered())))["Rating"]


def test_the_sources_sheet_fingerprints_every_file_the_pull_fetched(book):
    _, _, wb = book
    ws = wb["Sources"]
    rows = {ws.cell(r, 2).value: [ws.cell(r, j).value for j in range(2, 11)] for r in range(1, ws.max_row + 1)}
    assert all(s.title in rows for s in SERIES)
    assert len(rows["Unemployment rate"][8]) == 64     # SHA-256 of the file the rating read
    assert rows["Initial jobless claims"][7] == "not in this pull"


def test_the_fingerprint_is_of_the_bytes_rated_not_of_the_file_when_the_workbook_is_built(cache, tmp_path):  # noqa: F811
    # Codex on #452: a file changed between the rating and the build was hashed as it was at the build, so
    # the Sources tab named data the ratings never used.
    import hashlib
    pull = R.Pull(cache)
    result = R.rate_all(cache, check(answered(show_sahm=False)), pull=pull)
    path = pull.folder / "fred-UNRATE.csv"
    rated = hashlib.sha256(path.read_bytes()).hexdigest()
    with open(path, "a") as fh:
        fh.write("2026-10-01,2.0\n")                     # after the rating, before the workbook
    wb = openpyxl.load_workbook(build(tmp_path / "macro.xlsx", result, pull))
    ws = wb["Sources"]
    row = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 2).value == "Unemployment rate")
    assert ws.cell(row, 10).value == rated and ws.cell(row, 11).value is None
    facts = {wb["Run"].cell(r, 2).value: wb["Run"].cell(r, 3).value for r in range(1, wb["Run"].max_row + 1)}
    assert facts["Files changed since the pull"] == "none"


def test_a_series_rated_on_its_change_only_still_shows_its_latest_value(book):
    # Walk, 16 Oct 2026 (W6): gasoline read "change only" and never said $4.33 a gallon.
    _, _, wb = book
    ws = wb["Ratings"]
    row = next(c.row for col in ws.iter_cols(min_col=2, max_col=2) for c in col if c.value == "Consumer prices, all items")
    assert ws.cell(row, 6).value == "change only"
    assert isinstance(ws.cell(row, 4).value, float) and ws.cell(row, 5).value.startswith("index")


def test_the_latest_point_on_a_chart_is_labelled_rounded(book):
    # Walk (W7): the label printed 41.4897092453; LibreOffice ignores a label's own format.
    _, _, wb = book
    ws = wb["Prices"]
    hidden = [c for c in range(20, 40) if ws.column_dimensions[openpyxl.utils.get_column_letter(c)].hidden]
    latest = [ws.cell(r, c).value for c in hidden for r in range(1, ws.max_row + 1)
              if ws.cell(r, c).value is not None and isinstance(ws.cell(r, c).value, float)
              and ws.cell(r - 1, c).value in (None, "Latest") and ws.cell(r + 1, c).value is None]
    assert latest and all(round(v, 2) == v for v in latest)


def test_a_series_tab_prints_its_ratings_and_charts_not_its_whole_history(book):
    # Walk (W14): the workbook printed 856 pages, about 800 of them data.
    _, _, wb = book
    for name in [TAB[k] for _, keys in TOPICS for k in keys]:
        assert wb[name].print_area and wb[name].print_area.startswith("'%s'!$A$1:$L$" % name), name


def test_a_change_the_settings_did_not_ask_for_is_not_called_a_failure(cache, tmp_path):  # noqa: F811
    # Codex on #436: with change_for listing only some series, the others have no
    # change rating by design, and their tabs said "Not rated: see the Not rated tab",
    # a tab that says nothing about them.
    out, result, wb = _build(cache, tmp_path / "level.xlsx", change_for=[])
    assert not any(x["key"] == "unemployment" and x["reading"] == "change" for x in result["not_rated"])
    tab = _text(wb["Unemployment"])
    assert "Not asked for: the firm's settings rate this series on its level only." in tab
    assert "Not rated: see the Not rated tab" not in tab
    ws = wb["Ratings"]
    row = next(c.row for col in ws.iter_cols(min_col=2, max_col=2) for c in col if c.value == "Unemployment rate")
    assert ws.cell(row, 9).value == "level only"


# --- What if (W12) -------------------------------------------------------------------------------------------

def _whatif(cache, path, a=None, b=None):  # noqa: F811
    from threshold_engine.macro.compare import compare
    pull = R.Pull(cache)
    ra = R.rate_all(cache, check(answered(**(a or {}))), pull=pull)
    rb = R.rate_all(cache, check(answered(**(b or {}))), pull=pull)
    c = compare(ra, rb, "settings.json", "what-if.json")
    out = build(path, ra, pull, whatif=c)
    return out, c, openpyxl.load_workbook(out)


def test_the_what_if_tab_sets_every_national_reading_side_by_side(cache, tmp_path):  # noqa: F811
    out, c, wb = _whatif(cache, tmp_path / "w.xlsx", {"history": "full"}, {"history": {"years": 3}})
    assert wb.sheetnames[:3] == ["Ratings", "What if", "States"]
    ws = wb["What if"]
    text = _text(ws)
    assert "History each reading is measured against" in text and "the last 3 years" in text
    # every national reading rated under both (the partial pull leaves the rest rated under neither)
    national = [x for x in c["rows"] if not x["key"].startswith("unemployment_") and x["a"] and x["b"]]
    # the grid: the rating as you have it down the side, the what-if across, every national reading once
    corner = next(cl for row in ws.iter_rows() for cl in row if cl.value == "AS YOU HAVE IT")
    grid = [[ws.cell(corner.row + k, corner.column + j).value or 0 for j in range(1, 6)] for k in range(1, 6)]
    assert sum(map(sum, grid)) == len(national)
    for x in national:
        assert grid[x["a"]["rating"] - 1][x["b"]["rating"] - 1] >= 1
    # every national reading that moves is listed, linked to its tab, with both chips and the move
    moved = [x for x in national if x["move"]]
    assert moved
    for x in moved:
        cell = next(cl for col in ws.iter_cols(min_col=2, max_col=2) for cl in col
                    if cl.value == x["title"] and ws.cell(cl.row, 14).value not in (None, "same"))
        assert cell.hyperlink is not None
        assert ws.cell(cell.row, 14).value == ("▲ %d" if x["move"] > 0 else "▼ %d") % abs(x["move"])
        assert ws.cell(cell.row, 6).value[0] == str(x["a"]["rating"])
        assert ws.cell(cell.row, 10).value[0] == str(x["b"]["rating"])
    # the readings at the same rating are listed too, folded away, so the count can be checked
    same = [x for x in national if x["move"] == 0]
    folded = [r for r in range(1, ws.max_row + 1) if ws.cell(r, 14).value == "same"]
    assert len(folded) == len(same) and all(ws.row_dimensions[r].hidden for r in folded)
    # Ratings says which readings move, beside each series
    rt = wb["Ratings"]
    for x in moved:
        row = next(cl.row for col in rt.iter_cols(min_col=2, max_col=2) for cl in col if cl.value == x["title"])
        assert "%d → %d" % (x["a"]["rating"], x["b"]["rating"]) in rt.cell(row, 13).value


def test_the_dashed_lines_are_the_what_ifs_cut_offs_over_the_years_its_history_covers(cache, tmp_path):  # noqa: F811
    out, c, wb = _whatif(cache, tmp_path / "w.xlsx", {"history": "full"}, {"history": {"years": 3}})
    ws = wb["Unemployment"]
    row = next(x for x in c["rows"] if x["key"] == "unemployment" and x["reading"] == "position")
    head = next(cl for col in ws.iter_cols(min_col=34, max_col=34) for cl in col if cl.value == "What if: 2 from")
    for j, k in enumerate(range(2, 6)):
        col = 34 + j
        assert ws.column_dimensions[openpyxl.utils.get_column_letter(col)].hidden
        filled = [(ws.cell(r, 14).value, ws.cell(r, col).value) for r in range(head.row + 1, ws.max_row + 1)
                  if ws.cell(r, col).value is not None]
        if row["b"]["lines"][str(k)] is None:
            assert not filled
            continue
        assert filled and {v for _, v in filled} == {row["b"]["lines"][str(k)]}
        assert min(d for d, _ in filled).isoformat()[:10] == row["b"]["history_from"][:10]
    with zipfile.ZipFile(out) as z:
        charts = [z.read(n) for n in z.namelist() if n.startswith("xl/charts/chart")]
    assert any(ch.count(b'prstDash val="dash"') == 4 for ch in charts)


def test_a_different_change_horizon_draws_no_dashed_lines_on_the_change(cache, tmp_path):  # noqa: F811
    # Six months against twelve is a different measure: its lines would sit on the wrong scale.
    out, c, wb = _whatif(cache, tmp_path / "w.xlsx", {"change_months": 6}, {"change_months": 12})
    assert all(not x["same_measure"] for x in c["rows"] if x["reading"] == "change")
    ws = wb["Unemployment"]
    assert any(ws.cell(r, 34).value == "What if: 2 from" for r in range(1, 80))      # the level's lines
    assert not any(ws.cell(r, 38).value for r in range(1, ws.max_row + 1))         # none for the change
    # Codex on #452: the What if tab named the 6-month change and showed its value beside a rating of the
    # 12-month one. Each side is its own change, so the row names both and shows neither as shared.
    wi = wb["What if"]
    rows = [r for r in range(1, wi.max_row + 1) if str(wi.cell(r, 3).value).startswith("Change over")]
    assert rows
    for r in rows:
        assert wi.cell(r, 3).value == "Change over 6 months; what if: over 12 months"
        assert wi.cell(r, 4).value is None and wi.cell(r, 5).value is None
    assert any(wi.cell(r, 3).value == "Level" and wi.cell(r, 5).value is not None for r in range(1, wi.max_row + 1))
    # and the series' own table gives the what-if's starting points under its own horizon's name
    assert "What if: change over 12 months from" in _text(ws)
    # and Ratings says whose horizon a moved change is
    moved = next(x for x in c["rows"] if x["key"] == "cpi" and x["reading"] == "change")
    assert moved["move"]
    rt = wb["Ratings"]
    row = next(cl.row for col in rt.iter_cols(min_col=2, max_col=2) for cl in col
               if cl.value == "Consumer prices, all items")
    assert "(what if: over 12 months)" in rt.cell(row, 13).value


def test_a_reading_only_the_what_if_rates_still_shows_where_its_ratings_start(cache, tmp_path):  # noqa: F811
    # Codex on #452: the table was built from this run's ratings alone, so it dropped the what-if's.
    from threshold_engine.macro.settings import template as T
    directions = {k: {r: LOWER for r in v} for k, v in T()["directions"]["answer"].items()}
    directions["cpi"]["change"] = "not rated"
    out, c, wb = _whatif(cache, tmp_path / "w.xlsx", {"directions": directions}, {})
    row = next(x for x in c["rows"] if x["key"] == "cpi" and x["reading"] == "change")
    assert row["a"] is None and row["b"]
    ws = wb["Prices"]
    head = next(cl for row_ in ws.iter_rows() for cl in row_ if cl.value == "What if: change from")
    want = [row["b"]["lines"][str(k)] for k in range(2, 6)]
    got = [ws.cell(head.row + k, head.column).value for k in range(2, 6)]
    assert got == [pytest.approx(w / 100) if w is not None else "not reached" for w in want]   # in percent


def test_a_series_in_neither_run_is_not_called_the_same_rating(cache, tmp_path):  # noqa: F811
    # Codex on #452: an unpulled state read "not in this pull" and "same rating" on one row.
    out, c, wb = _whatif(cache, tmp_path / "w.xlsx", {"history": "full"}, {"history": {"years": 3}})
    st = wb["States"]
    tx = next(cl.row for col in st.iter_cols(min_col=2, max_col=2) for cl in col if cl.value == "TX")
    assert st.cell(tx, 3).value == "not in this pull" and st.cell(tx, 11).value == "not rated under either"
    rt = wb["Ratings"]
    claims = next(cl.row for col in rt.iter_cols(min_col=2, max_col=2) for cl in col
                  if cl.value == "Initial jobless claims")
    assert rt.cell(claims, 13).value == "not rated under either"



def test_a_reading_neither_run_rates_has_its_own_rows_with_each_runs_reason(cache, tmp_path):  # noqa: F811
    # Codex on #452: one only the what-if asked for, and could not rate, had no row on the What if tab.
    out, c, wb = _whatif(cache, tmp_path / "w.xlsx", {"change_for": []}, {})
    neither = [x for x in c["rows"] if x["a"] is None and x["b"] is None]
    ws = wb["What if"]
    head = next(cl.row for col in ws.iter_cols(min_col=2, max_col=2) for cl in col
                if str(cl.value).startswith("Rated under neither set of settings"))
    assert ws.cell(head, 2).value == "Rated under neither set of settings (%d)" % len(neither)
    texts = [(ws.cell(r, 6).value, ws.cell(r, 10).value) for r in range(head + 1, head + 2 + len(neither) + 1)]
    assert ("Not rated: not asked for by these settings",
            next(t for _, t in texts if t and "not in the pull" in t)) in texts
    tiles = [ws.cell(4, col).value for col in range(2, 15)]
    assert c["totals"]["only_a"] + c["totals"]["only_b"] in tiles     # the one-set tile does not count them


def test_a_change_neither_run_rates_is_labelled_with_the_horizon_that_asked_for_it(cache, tmp_path):  # noqa: F811
    # Codex on #452: the What if tab gave it both horizons, though only the what-if asked for it.
    out, c, wb = _whatif(cache, tmp_path / "w.xlsx", {"change_for": [], "change_months": 6}, {"change_months": 12})
    ws = wb["What if"]
    head = next(cl.row for col in ws.iter_cols(min_col=2, max_col=2) for cl in col
                if str(cl.value).startswith("Rated under neither set of settings"))
    labels = {ws.cell(r, 3).value for r in range(head + 1, ws.max_row + 1)
              if ws.cell(r, 6).value == "Not rated: not asked for by these settings"}
    assert labels == {"Change (what if: over 12 months)"}



def test_a_reading_only_the_what_if_asked_for_and_could_not_rate_is_not_called_the_same_rating(cache, tmp_path):  # noqa: F811,E501
    # Codex on #452: the level held, the what-if's change could not be counted (400 months is longer than the
    # history), and the Ratings cell read "same rating"; the What if tab said every reading took the same rating.
    out, c, wb = _whatif(cache, tmp_path / "w.xlsx", {"change_for": []}, {"change_months": 400})
    row = next(x for x in c["rows"] if x["key"] == "unemployment" and x["reading"] == "change")
    assert row["a"] is None and row["b"] is None and row["why_a"] == "not asked for by these settings"
    assert next(x for x in c["rows"] if x["key"] == "unemployment" and x["reading"] == "position")["move"] == 0
    rt = wb["Ratings"]
    r = next(cl.row for col in rt.iter_cols(min_col=2, max_col=2) for cl in col if cl.value == "Unemployment rate")
    assert rt.cell(r, 13).value == "Change (what if: over 400 months): not rated under the what-if"
    assert "None: every national reading rated under both takes the same rating." in _text(wb["What if"])
    assert "every national reading takes the same rating under both" not in _text(wb["What if"])

def test_a_file_gone_before_the_rating_has_no_fingerprint_as_read(tmp_path):
    # Codex on #452: a file deleted after the pull kept the manifest's fingerprint under "SHA-256 as read".
    from threshold_engine.macro import pull as P
    from test_macro_rate import _fetcher
    P.pull(tmp_path, keys=["unemployment", "cpi"], today="2026-10-17", fetcher=_fetcher())
    pull = R.Pull(tmp_path)
    (pull.folder / "fred-UNRATE.csv").unlink()
    result = R.rate_all(tmp_path, check(answered(show_sahm=False)), pull=pull)
    wb = openpyxl.load_workbook(build(tmp_path / "b.xlsx", result, pull))
    ws = wb["Sources"]
    rows = {ws.cell(r, 2).value: r for r in range(1, ws.max_row + 1)}
    u, cpi = rows["Unemployment rate"], rows["Consumer prices, all items"]
    assert ws.cell(u, 10).value is None and ws.cell(u, 11).value == "not read: missing from the pull folder"
    assert len(ws.cell(cpi, 10).value) == 64 and ws.cell(cpi, 11).value is None
    run = {wb["Run"].cell(r, 2).value: wb["Run"].cell(r, 3).value for r in range(1, wb["Run"].max_row + 1)}
    assert run["Files fetched and not read"] == "1: see Sources" and run["Files changed since the pull"] == "none"

def test_the_run_tab_lists_both_files_answers_side_by_side(cache, tmp_path):  # noqa: F811
    out, c, wb = _whatif(cache, tmp_path / "w.xlsx", {"history": "full"}, {"history": {"years": 3}})
    ws = wb["Run"]
    got = {ws.cell(r, 2).value: (ws.cell(r, 3).value, ws.cell(r, 4).value) for r in range(1, ws.max_row + 1)}
    assert got["History each reading is measured against"] == ("full history", "the last 3 years")
    assert got["What-if file"][0] == "what-if.json" and got["Settings file"][0] == "settings.json"
    terms = {wb["Glossary"].cell(r, 2).value for r in range(1, wb["Glossary"].max_row + 1)}
    assert {"As you have it", "What if", "Move", "Dashed lines"} <= terms


def _holds_together_in_excel(out):
    """What LibreOffice forgives and Excel does not, as far as it can be checked here: every axis a chart
    names is one the chart has, every axis crosses one it has, and no cell holds rich-text runs (which no
    workbook the firm opens in Excel uses; plain strings are inline in every openpyxl file)."""
    with zipfile.ZipFile(out) as z:
        charts = 0
        for n in z.namelist():
            if n.startswith("xl/charts/chart"):
                charts += 1
                x = z.read(n).decode()
                defined = re.findall(r'<(?:catAx|valAx|dateAx|serAx)><axId val="(\d+)"/>', x)
                assert defined and len(defined) == len(set(defined)), (n, defined)
                crosses = set(re.findall(r'<crossAx val="(\d+)"/>', x))
                named = set(re.findall(r'<axId val="(\d+)"/>', x))
                assert crosses <= set(defined) and named <= set(defined), (n, defined, crosses)
                # every series carries its own categories: without them Excel places a line at 1, 2, 3 ... on
                # a date axis, in 1900 (Fable's review of #452, not checked in Excel)
                for ser in re.findall(r"<ser>.*?</ser>", x, re.S):
                    assert "<cat>" in ser, (n, ser[:200])
            elif n.startswith("xl/worksheets/sheet"):
                assert b"<is><r>" not in z.read(n), n
        return charts


def test_every_chart_crosses_axes_it_has_so_excel_can_open_it(book, cache, tmp_path):  # noqa: F811
    # The firm, 17 Oct 2026: Excel said the example "is corrupt and cannot be opened". Every banded chart's
    # value axis crossed axis 10 after the date axis (500) replaced it; LibreOffice drew them all anyway,
    # and the file passed the ISO schemas and the Open XML SDK. This is the check that would have failed.
    assert _holds_together_in_excel(book[0]) > 0
    out, _, _ = _whatif(cache, tmp_path / "w.xlsx", {"history": "full"}, {"history": {"years": 3}})
    assert _holds_together_in_excel(out) > 0
    shown, _, _ = _build(cache, tmp_path / "sahm.xlsx", show_sahm=True)
    assert _holds_together_in_excel(shown) > 0


def test_a_change_only_the_what_if_rates_over_another_horizon_says_that_horizon(cache, tmp_path):  # noqa: F811
    # Codex on #452: the summary named the what-if's horizon for a change that moved, not for one only the
    # what-if rates, so a 12-month rating read as one of the 6-month change beside it.
    from threshold_engine.macro.settings import template as T
    directions = {k: {r: LOWER for r in v} for k, v in T()["directions"]["answer"].items()}
    directions["cpi"]["change"] = "not rated"
    out, c, wb = _whatif(cache, tmp_path / "w.xlsx", {"directions": directions, "change_months": 6},
                         {"change_months": 12})
    row = next(x for x in c["rows"] if x["key"] == "cpi" and x["reading"] == "change")
    assert row["a"] is None and row["b"] and not row["same_measure"]
    rt = wb["Ratings"]
    r = next(cl.row for col in rt.iter_cols(min_col=2, max_col=2) for cl in col
             if cl.value == "Consumer prices, all items")
    assert rt.cell(r, 13).value == "Change (what if: over 12 months): rated under the what-if only"
    assert "changes over 12 months since" in _text(wb["Prices"])
    # and the What if tab's row names the what-if's horizon only (Codex on #452: it named both)
    wi = wb["What if"]
    head = next(cl.row for col in wi.iter_cols(min_col=2, max_col=2) for cl in col
                if str(cl.value).startswith("Rated under one set of settings only"))
    cpi = next(rr for rr in range(head, wi.max_row + 1) if wi.cell(rr, 2).value == "Consumer prices, all items")
    assert wi.cell(cpi, 3).value == "Change (what if: over 12 months)"


def test_a_workbook_drawn_from_other_bytes_than_the_rating_read_is_refused(cache, tmp_path):  # noqa: F811
    # Codex on #452: rate_all with its own Pull, a file replaced, then build with a new Pull, published the new
    # file's fingerprint beside ratings made from the old one.
    from threshold_engine.macro.settings import Refused
    result = R.rate_all(cache, check(answered(show_sahm=False)))         # its own Pull, kept inside
    path = R.Pull(cache).folder / "fred-UNRATE.csv"
    with open(path, "a") as fh:
        fh.write("2026-10-01,2.0\n")
    with pytest.raises(Refused, match="fred-UNRATE.csv from other bytes than the rating read"):
        build(tmp_path / "macro.xlsx", result, R.Pull(cache))


def test_a_workbook_from_a_new_pull_of_unchanged_files_publishes_the_ratings_fingerprints(cache, tmp_path):  # noqa: F811
    result = R.rate_all(cache, check(answered(show_sahm=False)))
    wb = openpyxl.load_workbook(build(tmp_path / "macro.xlsx", result, R.Pull(cache)))
    ws = wb["Sources"]
    row = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 2).value == "Unemployment rate")
    assert ws.cell(row, 10).value == result["read_sha"]["fred-UNRATE.csv"]


def test_a_workbook_whose_pull_lacks_a_file_the_rating_read_is_refused(cache, tmp_path):  # noqa: F811
    # Codex on #452: a file gone before the workbook's Pull read it passed the check, its old fingerprint shown.
    from threshold_engine.macro.settings import Refused
    result = R.rate_all(cache, check(answered(show_sahm=False)))
    (R.Pull(cache).folder / "fred-CPIAUCSL.csv").unlink()
    with pytest.raises(Refused, match="fred-CPIAUCSL.csv from other bytes than the rating read"):
        build(tmp_path / "macro.xlsx", result, R.Pull(cache))


def test_a_what_if_not_compared_against_this_rating_is_refused(cache, tmp_path):  # noqa: F811
    # Codex on #452: a what-if from an earlier reading of the pull, or against other settings, was accepted.
    from threshold_engine.macro.compare import compare
    from threshold_engine.macro.settings import Refused
    pull = R.Pull(cache)
    ra = R.rate_all(cache, check(answered()), pull=pull)
    rb = R.rate_all(cache, check(answered(history={"years": 3})), pull=pull)
    c = compare(ra, rb, "settings.json", "what-if.json")
    other = R.rate_all(cache, check(answered(cutoffs=[50, 75, 90, 95])), pull=pull)
    with pytest.raises(Refused, match="not compared against this rating"):
        build(tmp_path / "a.xlsx", other, pull, whatif=c)              # other settings as you have it
    with open(pull.folder / "fred-UNRATE.csv", "a") as fh:
        fh.write("2026-10-01,2.0\n")
    fresh = R.Pull(cache)
    now = R.rate_all(cache, check(answered()), pull=fresh)
    with pytest.raises(Refused, match="not compared against this rating"):
        build(tmp_path / "b.xlsx", now, fresh, whatif=c)               # an earlier reading of the pull
    assert build(tmp_path / "c.xlsx", ra, pull, whatif=c)              # the rating it was made from
    with pytest.raises(Refused, match="not compared against this rating"):
        build(tmp_path / "d.xlsx", ra, pull, whatif=dict(c, vintage="2026-10-14"))   # another pull's name


def test_a_rating_built_with_the_pull_of_another_day_is_refused(cache, tmp_path):  # noqa: F811
    # Codex on #452: the workbook names result["vintage"] as its pull; a Pull of another day with the same bytes
    # would make that provenance false.
    import shutil
    from threshold_engine.macro.settings import Refused
    pull = R.Pull(cache)
    result = R.rate_all(cache, check(answered(show_sahm=False)), pull=pull)
    shutil.copytree(pull.folder, pull.folder.parent / "2026-10-16")
    with pytest.raises(Refused, match="the rating is of the pull of 2026-10-15 and the Pull given is of 2026-10-16"):
        build(tmp_path / "macro.xlsx", result, R.Pull(cache, "2026-10-16"))


def test_a_settings_file_named_like_a_formula_is_written_as_text(cache, tmp_path):  # noqa: F811
    # Codex on #452: a what-if file named "=b.json" went into the Run tab as a formula.
    from threshold_engine.macro.compare import compare
    pull = R.Pull(cache)
    ra = R.rate_all(cache, check(answered()), pull=pull)
    rb = R.rate_all(cache, check(answered(history={"years": 3})), pull=pull)
    out = build(tmp_path / "w.xlsx", ra, pull, whatif=compare(ra, rb, "=a.json", "=SUM(1,2)"))
    with zipfile.ZipFile(out) as z:
        sheets = [n for n in z.namelist() if n.startswith("xl/worksheets/sheet")]
        assert not [n for n in sheets if "<f>" in z.read(n).decode("utf-8")]
    run = openpyxl.load_workbook(out)["Run"]
    assert "=SUM(1,2)" in {c.value for row in run.iter_rows() for c in row}



# -- the shown series ------------------------------------------------------------

def test_every_shown_series_has_one_topic_and_one_tab():
    from threshold_engine.macro.catalog import SHOWN
    in_topics = [k for _, keys in SHOWN_TOPICS for k in keys]
    assert sorted(in_topics) == sorted(s.key for s in SHOWN) and len(set(in_topics)) == len(in_topics)
    assert sorted(SHOWN_TAB) == sorted(in_topics)
    names = list(SHOWN_TAB.values()) + list(TAB.values())
    assert len(set(names)) == len(names) and all(len(v) <= 31 for v in names)


@pytest.fixture
def shown_book(shown_cache, tmp_path):  # noqa: F811
    return _build(shown_cache, tmp_path / "shown.xlsx", show_sahm=False, history="full")


def test_the_shown_tab_lists_every_shown_series_and_the_rest_of_the_group(shown_book):
    from threshold_engine.macro.catalog import NOT_SHOWN, SCE_CREDIT, SHOWN
    _, result, wb = shown_book
    ws = wb[SHOWN_NAME]
    links = {ws.cell(r, 2).value: _to(ws.cell(r, 2)) for r in range(1, ws.max_row + 1)
             if ws.cell(r, 2).hyperlink and _to(ws.cell(r, 2)) != "Ratings"}
    assert links == {s.title: SHOWN_TAB[s.key] for s in SHOWN}
    text = _text(ws)
    assert all(what in text for what, _ in NOT_SHOWN) and SCE_CREDIT in text
    assert "None is rated" in text and not re.search(r"[1-5] (Low|Moderate|High)", text)
    # the saving rate's latest is its lowest: at or above its 1 reading of 321
    row = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 2).value == "Personal saving rate")
    assert ws.cell(row, 4).value == 1.0 and ws.cell(row, 6).value == pytest.approx(1 / 321)
    # a series that grows is shown on its change only
    row = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 2).value == "Real disposable income")
    assert ws.cell(row, 6).value == "change only" and ws.cell(row, 9).value is not None
    # what the pull lacks is said, with why
    assert "Nothing to show, and why" in text and "Job openings" in text
    assert _to(wb["Ratings"].cell(2, 2)) == SHOWN_NAME


def _to(cell):
    """The tab an in-workbook link opens, however openpyxl read it back."""
    h = cell.hyperlink
    return re.match(r"#?'(.*)'!A1$", h.location or h.target).group(1)


def test_a_shown_series_tab_draws_its_history_with_no_rating_and_no_bands(shown_book):
    out, result, wb = shown_book
    ws = wb["Saving rate"]
    text = _text(ws)
    assert "Shown, not rated" in text and "Not set: the series is shown, not rated" in text
    assert not re.search(r"[1-5] (Low|Moderate|High)", text)
    assert len(ws._charts) == 2                         # its level and its change
    for chart in ws._charts:
        assert type(chart).__name__ == "LineChart"     # no rating bands under it
    assert len(wb["Real income"]._charts) == 1          # change only
    assert SCE_CREDIT_IN(wb["Expected missed payments"])
    assert "Nothing to show" in _text(wb["Job openings"]) and not wb["Job openings"]._charts
    assert _holds_together_in_excel(out) > 0
    run = {wb["Run"].cell(r, 2).value: wb["Run"].cell(r, 3).value for r in range(1, wb["Run"].max_row + 1)}
    assert run["Series shown, not rated"].startswith("30 (5 readings shown;")


def SCE_CREDIT_IN(ws):
    from threshold_engine.macro.catalog import SCE_CREDIT
    return SCE_CREDIT in _text(ws)


def test_a_build_refuses_a_pull_whose_shown_file_changed_since_the_rating(shown_cache, tmp_path):  # noqa: F811
    # The shown series are drawn from the same reading of the pull as the ratings: a survey file changed
    # between the rating and the workbook is refused, as a rated series' file is.
    from threshold_engine.macro.settings import Refused
    result = R.rate_all(shown_cache, check(answered()))
    pull = R.Pull(shown_cache)
    (pull.folder / "nyfed_sce.xlsx").write_bytes((pull.folder / "nyfed_sce.xlsx").read_bytes() + b" ")
    with pytest.raises(Refused, match="nyfed_sce.xlsx"):
        build(tmp_path / "x.xlsx", result, pull)


def test_the_shown_tab_dates_a_change_by_its_own_month_when_the_latest_has_none(tmp_path):
    # Codex on #452: a reading missing the horizon back leaves the latest month with no change, so the change
    # shown is an earlier month's; written beside the latest date alone, it read as the latest month's.
    from test_macro_rate import _fetcher
    from test_macro_sources import sce_workbook
    base = _fetcher()

    def fetch(url):
        if "newyorkfed.org" in url:      # March 2026 missing: no change over 6 months to September
            return sce_workbook([(100 * (2013 + (5 + i) // 12) + (5 + i) % 12 + 1, None if i == 153 else 10 + i % 3)
                                 for i in range(160)])
        return base(url)
    R.P.pull(tmp_path, keys=["expected_missed_payment"], today="2026-10-15", fetcher=fetch)
    out, result, wb = _build(tmp_path, tmp_path / "x.xlsx")
    chg = next(x for x in result["shown"] if x["key"] == "expected_missed_payment" and x["reading"] == "change")
    assert chg["date"] == "2026-08-01"
    ws = wb[SHOWN_NAME]
    row = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 2).value == "Expected chance of missing a minimum "
               "debt payment")
    assert ws.cell(row, 3).value.date().isoformat() == "2026-09-01"     # the latest reading
    assert ws.cell(row, 8).value.date().isoformat() == "2026-08-01"     # the month the change runs to


def test_the_printout_and_the_record_carry_the_credit_the_survey_licence_requires(shown_cache, tmp_path, capsys):  # noqa: F811
    # Codex on #452: rate printed the NY Fed's numbers without the attribution its licence requires.
    import json
    from threshold_engine.macro.__main__ import main
    from threshold_engine.macro.catalog import SCE_CREDIT
    settings = tmp_path / "s.json"
    settings.write_text(json.dumps(answered()))
    assert main(["rate", "--cache", str(shown_cache), "--settings", str(settings)]) == 0
    out = capsys.readouterr().out
    assert "expected_missed_payment" in out and SCE_CREDIT in out
    assert main(["rate", "--cache", str(shown_cache), "--settings", str(settings), "--json"]) == 0
    record = json.loads(capsys.readouterr().out)
    sce = [x for x in record["shown"] if x["key"] == "expected_missed_payment"]
    assert sce and all(x["credit"] == SCE_CREDIT for x in sce)


def test_show_prints_the_credit_with_the_survey_data_it_prints(shown_cache, capsys):  # noqa: F811
    # Codex on #452: show printed the NY Fed survey's observations without the attribution its licence requires.
    from threshold_engine.macro.__main__ import main
    from threshold_engine.macro.catalog import SCE_CREDIT
    assert main(["show", "--cache", str(shown_cache), "expected_missed_payment", "--tail", "3"]) == 0
    out = capsys.readouterr().out
    assert "2026-09-01" in out and out.rstrip().endswith(SCE_CREDIT)
    assert main(["show", "--cache", str(shown_cache), "saving_rate", "--tail", "3"]) == 0
    assert "Survey of Consumer Expectations" not in capsys.readouterr().out     # only where a licence asks
