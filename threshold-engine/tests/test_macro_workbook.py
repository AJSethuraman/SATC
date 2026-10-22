"""The workbook the teams read: built only from a finished run, values not formulas outside the Dashboard, a
missing month left empty so no chart draws it as zero, every change drawn over its normal range, and nothing
rated anywhere."""
import math
import re
import zipfile

import pytest

openpyxl = pytest.importorskip("openpyxl")

from threshold_engine.macro import readings as R
from threshold_engine.macro.catalog import CARE, CARE_DERIVED, CARE_NOT_READ, CORE, SCE_CREDIT, SERIES, STATES
from threshold_engine.macro.settings import Refused, check
from threshold_engine.macro.workbook import (CARE_NAME, CARE_TAB, CARE_TOPICS, DASH_DATA, DASHBOARD, HOUSEHOLD_KEYS,
                                             HOUSEHOLD_NAME, TAB, TOPICS, axis_view, build, glossary, nice_axis)

from test_macro_readings import _fetcher, cache, care_cache  # noqa: F401  (the fixtures: pulls on disk)
from test_macro_settings import answered


def _build(cache, path, zoom=None, **answers):  # noqa: F811
    pull = R.Pull(cache)
    result = R.read_all(cache, check(answered(**answers)), pull=pull)
    out = build(path, result, pull, zoom=zoom)
    return out, result, openpyxl.load_workbook(out)


@pytest.fixture
def book(cache, tmp_path):  # noqa: F811
    return _build(cache, tmp_path / "macro.xlsx", show_sahm=False)


def _text(ws):
    return " ".join(str(c.value) for row in ws.iter_rows() for c in row if c.value is not None)


def _row(ws, title, col=2):
    return next(c.row for c_ in ws.iter_cols(min_col=col, max_col=col) for c in c_ if c.value == title)


def _to(cell):
    """The tab an in-workbook link opens, however openpyxl read it back."""
    h = cell.hyperlink
    return re.match(r"#?'(.*)'!A1$", h.location or h.target).group(1)


def _charts(out):
    with zipfile.ZipFile(out) as z:
        return {n: z.read(n).decode() for n in z.namelist() if n.startswith("xl/charts/chart")}


def test_every_national_series_has_one_topic_and_one_tab():
    states = {"unemployment_" + st.lower() for st in STATES}
    national = sorted(i.key for i in CORE if i.key not in states)
    in_topics = [k for _, keys in TOPICS for k in keys]
    assert sorted(in_topics) == national and len(set(in_topics)) == len(in_topics)
    assert sorted(TAB) == national
    # every series has its own tab but the household types, which share one
    own = [v for k, v in TAB.items() if k not in HOUSEHOLD_KEYS]
    assert len(set(own)) == len(own) and HOUSEHOLD_NAME not in own
    assert {TAB[k] for k in HOUSEHOLD_KEYS} == {HOUSEHOLD_NAME}
    names = own + [HOUSEHOLD_NAME] + list(CARE_TAB.values())
    assert len(set(names)) == len(names) and all(len(v) <= 31 for v in names)


def test_every_care_series_has_one_topic_and_one_tab():
    in_topics = [k for _, keys in CARE_TOPICS for k in keys]
    assert sorted(in_topics) == sorted(s.key for s in CARE + CARE_DERIVED) and len(set(in_topics)) == len(in_topics)
    assert sorted(CARE_TAB) == sorted(in_topics)


def test_the_sheets_are_the_overview_and_dashboard_first_then_one_per_series_by_topic(book):
    _, _, wb = book
    tabs = []
    for _, keys in TOPICS:
        for k in keys:
            if TAB[k] not in tabs:
                tabs.append(TAB[k])
    care = [CARE_TAB[k] for _, keys in CARE_TOPICS for k in keys]
    assert wb.sheetnames == (["Overview", DASHBOARD, "States", CARE_NAME] + tabs + care
                             + ["State data", "Not read", "Glossary", "Run", "Sources", DASH_DATA])
    assert wb[DASH_DATA].sheet_state == "hidden"


def test_the_overview_reads_every_national_series_under_its_topic_and_rates_none(book):
    _, result, wb = book
    ws = wb["Overview"]
    text = _text(ws)
    for topic, _ in TOPICS:
        assert topic in text
    assert not re.search(r"\b[1-5] (Low|Moderate|High|Mod-)", text) and "Rating" not in text
    rows = [c.row for col in ws.iter_cols(min_col=2, max_col=2) for c in col if c.hyperlink
            and _to(c) not in (CARE_NAME, DASHBOARD)]
    ways = [ws.cell(r, 11).value for r in rows if ws.cell(r, 11).value]
    national = [r for r in result["readings"] if r["reading"] == "change" and not r["care"]
                and not r["key"].startswith("unemployment_")]
    assert len(ways) == len(national) and set(ways) <= {"▲ Increasing", "Stable", "▼ Decreasing"}
    # the fixture's unemployment jumps to a record: Increasing, its level at the top, its row linked to its tab
    u = _row(ws, "Unemployment rate")
    assert _to(ws.cell(u, 2)) == "Unemployment"
    assert ws.cell(u, 11).value == "▲ Increasing" and ws.cell(u, 6).value == 1.0
    chg = next(r for r in national if r["key"] == "unemployment")
    assert (ws.cell(u, 9).value, ws.cell(u, 10).value) == (pytest.approx(chg["normal_low"]),
                                                          pytest.approx(chg["normal_high"]))
    assert ws.cell(u, 12).value == pytest.approx(chg["movement"])
    assert ws.cell(u, 13).value.date().isoformat() == chg["since"]
    # the tiles count the national changes by direction
    tiles = {ws.cell(3, c).value: ws.cell(4, c).value for c in range(2, 13) if ws.cell(3, c).value}
    assert tiles["Changes read"] == len(national)
    for d in ("Increasing", "Stable", "Decreasing"):
        key = next(k for k in tiles if k.endswith(d))
        assert tiles[key] == sum(1 for r in national if r["direction"] == d)


def test_a_missing_month_is_an_empty_cell_and_says_so(book):
    _, _, wb = book
    ws = wb["Unemployment"]
    row = next(c.row for col in ws.iter_cols(min_col=14, max_col=14) for c in col
               if getattr(c.value, "isoformat", None) and c.value.isoformat()[:10] == "2025-10-01")
    assert ws.cell(row, 15).value is None               # not zero, not text a chart would draw as zero
    assert ws.cell(row, 17).value == "no value published"


def test_every_change_is_drawn_over_its_normal_range_and_every_chart_leaves_gaps(book):
    out, result, wb = book
    charts = _charts(out)
    banded = [x for x in charts.values() if "areaChart" in x]
    assert banded
    for x in charts.values():
        if "scatterChart" not in x and "barChart" not in x:
            assert 'dispBlanksAs val="gap"' in x or 'dispBlanksAs val="span"' in x
    for x in banded:
        assert 'plotVisOnly val="0"' in x                # the band lives in hidden columns
        assert x.index("areaChart") < x.index("lineChart")   # drawn first, so underneath
    # the band is the normal range: an unfilled base at its bottom and its height above
    ws = wb["Unemployment"]
    chg = next(r for r in result["readings"] if r["key"] == "unemployment" and r["reading"] == "change")
    head = _row(ws, "Normal from", col=22)
    filled = {(ws.cell(r, 22).value, ws.cell(r, 23).value) for r in range(head + 1, ws.max_row + 1)
              if ws.cell(r, 22).value is not None}
    assert filled == {(chg["normal_low"], chg["normal_high"] - chg["normal_low"])}


def _spiked(tmp_path, keys):
    """A pull whose unemployment rate spikes in April and May 2020 and whose prime rate is daily with holidays."""
    import datetime
    from threshold_engine.macro import pull as P
    base = _fetcher()

    def fetch(url):
        if url.endswith("id=UNRATE"):
            rows, d, i = ["observation_date,UNRATE"], datetime.date(2000, 1, 1), 0
            while d <= datetime.date(2026, 9, 1):
                v = {"2020-04-01": 14.8, "2020-05-01": 13.2}.get(d.isoformat(), 4.0 + ((i * i) % 7) / 10)
                rows.append("%s,%s" % (d.isoformat(), v))
                d, i = (d.replace(day=1) + datetime.timedelta(days=32)).replace(day=1), i + 1
            return ("\n".join(rows) + "\n").encode()
        if url.endswith("id=DPRIME"):
            rows, d, i = ["observation_date,DPRIME"], datetime.date(2000, 1, 3), 0
            while d <= datetime.date(2026, 10, 13):
                if d.weekday() < 5:
                    rows.append("%s,%s" % (d.isoformat(), "." if (d.month, d.day) in ((1, 1), (7, 4), (12, 25))
                                           else 4 + ((i * i) % 9) / 4))
                    i += 1
                d += datetime.timedelta(days=1)
            return ("\n".join(rows) + "\n").encode()
        return base(url)
    P.pull(tmp_path, keys=keys, today="2026-10-15", fetcher=fetch)
    return tmp_path


def test_a_spike_runs_off_the_chart_and_the_note_under_it_names_it(tmp_path):
    out, result, wb = _build(_spiked(tmp_path, ["unemployment"]), tmp_path / "cut.xlsx", axis_cut=1,
                             history="full")
    text = _text(wb["Unemployment"])
    assert "Off the chart: 2 readings run off the top, the highest 14.8 percent in Apr 2020." in text
    lvl = next(x for x in _charts(out).values() if "Level against its history" in x)
    assert float(re.search(r'<max val="([\d.]+)"', lvl).group(1)) < 13.2       # the axis stops below the spike
    _, _, plain = _build(tmp_path, tmp_path / "nocut.xlsx", axis_cut=0, history="full")
    assert "Off the chart" not in _text(plain["Unemployment"])


def test_a_daily_line_joins_across_a_holiday_and_a_monthly_one_leaves_its_gap(tmp_path):
    # The prime rate, 22 Oct 2026: every holiday broke its line. October 2025 still shows as a gap.
    out, _, wb = _build(_spiked(tmp_path, ["prime_rate", "unemployment"]), tmp_path / "d.xlsx", history="full")
    charts = _charts(out)
    prime = [x for x in charts.values() if "'Prime rate'!" in x]
    monthly = [x for x in charts.values() if "'Unemployment'!" in x and "Sahm" not in x]
    assert prime and all('dispBlanksAs val="span"' in x for x in prime)
    assert monthly and all('dispBlanksAs val="gap"' in x for x in monthly)
    assert "A daily series has no reading on a holiday" in _text(wb["Prime rate"])


def test_an_axis_rounds_out_to_a_tidy_step():
    assert nice_axis(2.5, 14.8) == (2.5, 15.0, 2.5)
    lo, hi, step = nice_axis(-9.6, 10.6)
    assert lo <= -9.6 and hi >= 10.6 and step == 5


def test_a_spike_runs_off_the_axis_but_the_latest_reading_and_the_normal_range_stay_on():
    dated = [("d%03d" % i, 1.0 + (i % 5) / 10) for i in range(200)] + [("spike", 60.0), ("spike2", 55.0)]
    lo, hi, step, above, below = axis_view(dated, 1, keep=[0.5])
    assert hi < 55 and above == [("spike", 60.0), ("spike2", 55.0)] and not below
    assert lo <= 0.5                                     # kept on, though no reading is that low
    assert axis_view(dated, 0, keep=[])[1] >= 60        # a cut of 0 keeps every reading on the chart


def test_every_number_outside_the_dashboard_is_a_value_not_a_formula(book):
    out, _, wb = book
    for ws in wb.worksheets:
        if ws.title == DASHBOARD:
            continue
        for row in ws.iter_rows():
            for c in row:
                assert not (isinstance(c.value, str) and c.value.startswith("=")), (ws.title, c.coordinate)


def test_the_dashboard_only_looks_up_values_written_on_its_hidden_tab(book):
    out, result, wb = book
    ws = wb[DASHBOARD]
    formulas = [c.value for row in ws.iter_rows() for c in row if isinstance(c.value, str) and c.value.startswith("=")]
    assert formulas
    used = {f for x in formulas for f in re.findall(r"([A-Z]+)\(", x)}
    # Functions every Excel since 2007 knows by name: one newer (AGGREGATE) read #NAME? unless the file marks it.
    assert used <= {"INDEX", "MATCH", "ROW", "IF", "IFERROR", "ISNA", "ISNUMBER", "AND", "OR", "NA", "MIN",
                    "MAX"}, used
    for x in formulas:
        for sheet in re.findall(r"'([^']+)'!", x):
            assert sheet in (DASH_DATA, DASHBOARD), x
    # four pickers: two series, each from the list of every national and care series, and two quarters
    dvs = {str(d.sqref): d for d in ws.data_validations.dataValidation}
    series_dv = next(d for k, d in dvs.items() if set(k.split()) == {"C4", "C5"})
    quarter_dv = next(d for k, d in dvs.items() if set(k.split()) == {"C6", "C7"})
    assert len(dvs) == 2 and series_dv.type == quarter_dv.type == "list"
    data = wb[DASH_DATA]
    col = re.match(r"'%s'!\$([A-Z]+)\$" % DASH_DATA, series_dv.formula1).group(1)
    names = [c.value for c in data[col][2:] if c.value]
    national = [k for _, keys in TOPICS for k in keys] + [k for _, keys in CARE_TOPICS for k in keys]
    assert len(names) == len(national) and ws["C4"].value in names and ws["C5"].value in names
    col = re.match(r"'%s'!\$([A-Z]+)\$" % DASH_DATA, quarter_dv.formula1).group(1)
    quarters = [c.value for c in data[col][2:] if c.value]
    assert quarters[0] == "2000 Q1" and quarters[-1] == "2026 Q3" and len(quarters) == len(set(quarters))
    assert (ws["C6"].value, ws["C7"].value) == ("2000 Q1", "2026 Q3")      # opens on every quarter
    assert ws.freeze_panes == "A8"                                          # the four boxes stay in view


def test_the_dashboard_charts_fit_their_picks_in_years_and_draw_no_point_legends(book):
    # The firm, 22 Oct 2026, in Excel: years from 1900 to 2036 printed over the legends, and rows of unnamed
    # dashes under the one-line charts.
    out, result, wb = book
    charts = [x for n, x in _charts(out).items() if "scatterChart" in x]
    assert len(charts) == 6
    for x in charts:
        assert "'Dashboard'!$C$4" in x or "'Dashboard'!$C$5" in x
        assert '<varyColors val="0"/>' in x                       # one colour a line: no legend entry a point
        x_axis = re.search(r'<valAx><axId val="500"/>.*?</valAx>', x, re.S).group(0)
        assert '<axPos val="b"/>' in x_axis and 'formatCode="0"' in x_axis       # years, along the foot
        assert "<min " not in x_axis and "<max " not in x_axis                    # fitted to what is picked
        legend = re.search(r"<legend>.*?</legend>", x, re.S)
        lines = len(re.findall(r"<ser>", x)) - x.count('prstDash val="dash"')
        assert (legend is None) == (lines == 1)                   # a one-line chart has no legend
        if legend:
            assert '<legendPos val="t"/>' in legend.group(0)       # above, clear of the years
            gone = re.findall(r'<legendEntry><idx val="(\d+)"/><delete val="1"/></legendEntry>', legend.group(0))
            names = re.findall(r"<ser>.*?<tx>(.*?)</tx>", x, re.S)
            shown = [n for k, n in enumerate(names) if str(k) not in gone]
            assert len(shown) == len(set(shown)), shown            # no name twice
        assert '<dispBlanksAs val="span"/>' in x                  # a quarterly pick drawn beside a monthly one
    # the drawn years are the months in years, and the window helpers read the From and To quarters
    ws = wb[DASHBOARD]
    years = [ws.cell(r, 42).value for r in range(3, 8)]
    assert years[:2] == [2000.0, pytest.approx(2000 + 1 / 12)]
    t0, t1 = (ws.cell(r, 40).value for r in (6, 7))
    assert t0.startswith("=INDEX(") and "$C$6" in t0 and t1.startswith("=INDEX(") and "$C$7" in t1
    # each month is drawn only from the From quarter's first month to the To quarter's last
    for col in (43, 48):
        x = ws.cell(3, col).value
        assert ",$AP3>=$AN$6,$AP3<=$AN$7),$AP3,NA())" in x, x


def test_the_dashboard_says_why_a_pick_has_no_line_on_the_levels_chart(book):
    _, _, wb = book
    ws = wb[DASHBOARD]
    said = [c.value for row in ws.iter_rows(min_col=2, max_col=2) for c in row
            if isinstance(c.value, str) and "read on their change only" in c.value]
    assert len(said) == 1 and "has no line here: it is read on its change only" in said[0]
    # both picks are tested on their own, and together: four tests of the cell that says "change only"
    tests = re.findall(r"(INDEX\([^()]*\))=\"change only\"", said[0])
    assert len(tests) == 4 and len(set(tests)) == 2 and tests[:2] == tests[2:], tests


def test_a_zoom_opens_the_dashboard_on_its_quarters_and_keeps_every_month(cache, tmp_path):  # noqa: F811
    _, _, wb = _build(cache, tmp_path / "z.xlsx", zoom=["2024Q1", "2026Q3"])
    ws = wb[DASHBOARD]
    assert (ws["C6"].value, ws["C7"].value) == ("2024 Q1", "2026 Q3")
    assert ws.cell(3, 42).value == 2000.0                         # the From box can still widen the view


def test_the_dashboard_data_are_each_series_month_by_month_in_typical_moves_from_its_median(book):
    _, result, wb = book
    data = wb[DASH_DATA]
    head = {data.cell(1, c).value: c for c in range(2, data.max_column + 1) if data.cell(1, c).value}
    c0 = head["Unemployment rate"]
    chg = next(r for r in result["readings"] if r["key"] == "unemployment" and r["reading"] == "change")
    row = next(r for r in range(3, data.max_row + 1) if data.cell(r, 1).value.date().isoformat() == "2026-09-01")
    assert data.cell(row, c0).value == 9.0
    assert data.cell(row, c0 + 1).value == pytest.approx(chg["value"])
    assert data.cell(row, c0 + 2).value == pytest.approx(chg["movement"])
    assert data.cell(row, c0 + 3).value == 1.0               # at the top of its history


def test_the_run_sheet_shows_the_answers_the_run_used(book):
    _, _, wb = book
    ws = wb["Run"]
    got = {ws.cell(r, 2).value: ws.cell(r, 3).value for r in range(1, ws.max_row + 1)}
    assert got["Normal movement"] == "the median change plus or minus 1.5 typical moves"
    assert got["Quarters left out"] == "none" and got["Readings a chart may leave off its axis"] == "none: every reading stays on"
    assert got["Sahm reading shown"] == "no" and got["History each reading is measured against"] == "the last 20 years"
    assert got["From the pull of"] == "2026-10-15" and got["Charts zoomed to"].startswith("not zoomed")


def test_the_sahm_reading_appears_only_when_the_firm_asked_for_it(book, cache, tmp_path):  # noqa: F811
    assert "Sahm's published trigger" not in _text(book[2]["Overview"])
    shown = _build(cache, tmp_path / "sahm.xlsx", show_sahm=True)[2]
    assert "Sahm's published trigger is 0.50" in _text(shown["Overview"])
    assert "Sahm reading" in _text(shown["Unemployment"])


def test_states_have_their_own_sheet_and_stay_off_the_national_one(book):
    _, result, wb = book
    assert any(r["key"] == "unemployment_ca" for r in result["readings"])
    assert "Unemployment rate, CA" not in _text(wb["Overview"])
    ws = wb["States"]
    ca = _row(ws, "CA")
    assert ws.cell(ca, 9).value in ("▲ Increasing", "Stable", "▼ Decreasing")
    assert 0 < ws.cell(ca, 5).value <= 1
    assert ws.cell(_row(ws, "TX"), 3).value == "not in this pull"


def test_the_glossary_explains_every_term_a_reader_meets(book):
    _, _, wb = book
    terms = {wb["Glossary"].cell(r, 2).value for r in range(1, wb["Glossary"].max_row + 1)}
    for needed in ("Level", "Level: at or above", "Change over 6 months", "Typical move", "Normal range",
                   "Increasing, Stable, Decreasing", "Typical moves (a number)", "Since", "History from",
                   "Quarters left out", "Off the chart", "Change only", "In the research", "Sahm reading",
                   "No value published", CARE_NAME, HOUSEHOLD_NAME, DASHBOARD):
        assert needed in terms, needed
    assert not {"Rating", "Percentile", "What stands out"} & terms
    words = dict(glossary(check(answered(left_out=["2020Q2-2021Q2"]))))
    assert "2020Q2 to 2021Q2" in words["Quarters left out"] and "1.5 typical moves" in words["Normal range"]


def test_the_sources_sheet_fingerprints_every_file_the_pull_fetched(book):
    _, _, wb = book
    ws = wb["Sources"]
    rows = {ws.cell(r, 2).value: [ws.cell(r, j).value for j in range(2, 11)] for r in range(1, ws.max_row + 1)}
    assert all(s.title in rows for s in SERIES)
    assert len(rows["Unemployment rate"][8]) == 64     # SHA-256 of the file the run read
    assert rows["Initial jobless claims"][7] == "not in this pull"


def test_the_fingerprint_is_of_the_bytes_read_not_of_the_file_when_the_workbook_is_built(cache, tmp_path):  # noqa: F811
    # Codex on #452: a file changed between the run and the build was hashed as it was at the build, so the
    # Sources tab named data the readings never used.
    import hashlib
    pull = R.Pull(cache)
    result = R.read_all(cache, check(answered(show_sahm=False)), pull=pull)
    path = pull.folder / "fred-UNRATE.csv"
    read = hashlib.sha256(path.read_bytes()).hexdigest()
    with open(path, "a") as fh:
        fh.write("2026-10-01,2.0\n")                     # after the run, before the workbook
    wb = openpyxl.load_workbook(build(tmp_path / "macro.xlsx", result, pull))
    ws = wb["Sources"]
    row = _row(ws, "Unemployment rate")
    assert ws.cell(row, 10).value == read and ws.cell(row, 11).value is None
    facts = {wb["Run"].cell(r, 2).value: wb["Run"].cell(r, 3).value for r in range(1, wb["Run"].max_row + 1)}
    assert facts["Files changed since the pull"] == "none"


def test_a_series_read_on_its_change_only_still_shows_its_latest_value(book):
    # Walk, 16 Oct 2026 (W6): gasoline read "change only" and never said $4.33 a gallon.
    _, _, wb = book
    ws = wb["Overview"]
    row = _row(ws, "Consumer prices, all items")
    assert ws.cell(row, 6).value == "change only"
    assert isinstance(ws.cell(row, 4).value, float) and ws.cell(row, 5).value.startswith("index")


def test_the_latest_point_on_a_chart_is_labelled_rounded(book):
    # Walk (W7): the label printed 41.4897092453; LibreOffice ignores a label's own format.
    _, _, wb = book
    ws = wb["Prices"]
    head = _row(ws, "Latest", col=24)
    latest = [ws.cell(r, 24).value for r in range(head + 1, ws.max_row + 1) if ws.cell(r, 24).value is not None]
    assert len(latest) == 1 and round(latest[0], 2) == latest[0]


def test_a_series_tab_prints_its_readings_and_charts_not_its_whole_history(book):
    # Walk (W14): the workbook printed 856 pages, about 800 of them data.
    _, _, wb = book
    for name in {TAB[k] for _, keys in TOPICS for k in keys}:
        assert wb[name].print_area and wb[name].print_area.startswith("'%s'!$A$1:$L$" % name), name


def test_quarters_left_out_are_not_drawn_and_are_said_on_every_tab(cache, tmp_path):  # noqa: F811
    out, result, wb = _build(cache, tmp_path / "left.xlsx", history="full", left_out=["2026Q3"])
    ws = wb["Unemployment"]
    rows = {ws.cell(r, 14).value.date().isoformat(): r for r in range(1, ws.max_row + 1)
            if getattr(ws.cell(r, 14).value, "date", None)}
    sep = rows["2026-09-01"]
    assert ws.cell(sep, 15).value == 9.0                         # the publisher's figure is kept in the table
    assert ws.cell(sep, 17).value == "left out (2026Q3)" and ws.cell(sep, 20).value is None     # but not drawn
    assert ws.cell(rows["2026-06-01"], 20).value is not None
    for name in ("Overview", "Unemployment", "States"):
        assert "Left out of every history: 2026Q3" in _text(wb[name]), name
    # Codex on #471: the latest shown is the latest kept, beside the readings measured from it
    ov = wb["Overview"]
    u = _row(ov, "Unemployment rate")
    lvl = next(r for r in result["readings"] if r["key"] == "unemployment" and r["reading"] == "position")
    assert ov.cell(u, 3).value.date().isoformat() == lvl["date"] == "2026-06-01" and ov.cell(u, 4).value == lvl["value"]
    data = wb[DASH_DATA]
    stats = next(r for r in range(3, data.max_row + 1) for c in range(2, data.max_column + 1)
                 if data.cell(2, c).value == "Series" and data.cell(r, c).value == "Unemployment rate")
    latest_col = next(c for c in range(2, data.max_column + 1) if data.cell(2, c).value == "Latest")
    assert data.cell(stats, latest_col).value.date().isoformat() == "2026-06-01"
    assert "Later readings, to Sep 2026, fall in quarters left out." in _text(ws)
    _, _, sahm_ = _build(cache, tmp_path / "left-sahm.xlsx", history="full", left_out=["2026Q3"], show_sahm=True)
    ws = sahm_["Unemployment"]
    drawn = {ws.cell(r, 14).value.date().isoformat(): ws.cell(r, 18).value for r in range(1, ws.max_row + 1)
             if getattr(ws.cell(r, 14).value, "date", None)}
    assert drawn["2026-06-01"] is not None and drawn["2026-07-01"] is None and drawn["2026-09-01"] is None
    assert "2026Q3" in dict((wb["Run"].cell(r, 2).value, wb["Run"].cell(r, 3).value)
                            for r in range(1, wb["Run"].max_row + 1))["Quarters left out"]


def test_a_zoom_draws_only_its_quarters_and_changes_no_reading(cache, tmp_path):  # noqa: F811
    whole_out, whole, _ = _build(cache, tmp_path / "whole.xlsx", history="full")
    out, zoomed, wb = _build(cache, tmp_path / "zoom.xlsx", zoom=["2024Q1", "2026Q3"], history="full")
    assert zoomed["readings"] == whole["readings"]               # the readings are made before the workbook
    ws = wb["Unemployment"]
    first_drawn = {}
    for n, x in _charts(out).items():
        refs = re.findall(r"<f>'Unemployment'!\$N\$(\d+):\$N\$(\d+)</f>", x)
        if refs:
            first_drawn[n] = refs[0]
    assert first_drawn
    for a, b in first_drawn.values():
        assert ws.cell(int(a), 14).value.date().isoformat() == "2024-01-01"
        assert ws.cell(int(b), 14).value.date().isoformat() == "2026-09-01"
    assert "The charts show 2024Q1 to 2026Q3 only" in _text(ws)
    run = {wb["Run"].cell(r, 2).value: wb["Run"].cell(r, 3).value for r in range(1, wb["Run"].max_row + 1)}
    assert run["Charts zoomed to"] == "2024Q1 to 2026Q3; no reading changes with it"
    # the whole history is still in the table
    assert any(getattr(ws.cell(r, 14).value, "year", 0) == 2000 for r in range(1, ws.max_row + 1))


def test_a_zoom_with_no_reading_in_it_says_so_rather_than_drawing_nothing(cache, tmp_path):  # noqa: F811
    out, _, wb = _build(cache, tmp_path / "early.xlsx", zoom=["1990Q1", "1991Q4"])
    assert "No reading of its level falls in 1990Q1 to 1991Q4" in _text(wb["Unemployment"])
    assert not wb["Unemployment"]._charts


def test_the_command_line_refuses_a_zoom_it_cannot_use(cache, tmp_path, capsys):  # noqa: F811
    import json
    from threshold_engine.macro.__main__ import main
    s = tmp_path / "s.json"
    s.write_text(json.dumps(answered()))
    for zoom, says in (("2026Q3:2024Q1", "the first not after the second"), ("2024-01:2026-09", "two quarters")):
        assert main(["read", "--cache", str(cache), "--settings", str(s), "--workbook", str(tmp_path / "x.xlsx"),
                     "--zoom", zoom]) == 2
        assert says in capsys.readouterr().err
    assert main(["read", "--cache", str(cache), "--settings", str(s), "--zoom", "2024Q1:2026Q3"]) == 2
    assert "needs --workbook" in capsys.readouterr().err


# --- What if (W12) -------------------------------------------------------------------------------------------

def _whatif(cache, path, a=None, b=None):  # noqa: F811
    from threshold_engine.macro.compare import compare
    pull = R.Pull(cache)
    ra = R.read_all(cache, check(answered(**(a or {}))), pull=pull)
    rb = R.read_all(cache, check(answered(**(b or {}))), pull=pull)
    c = compare(ra, rb, "settings.json", "what-if.json")
    out = build(path, ra, pull, whatif=c)
    return out, c, openpyxl.load_workbook(out)


def test_the_what_if_tab_sets_every_national_change_side_by_side(cache, tmp_path):  # noqa: F811
    out, c, wb = _whatif(cache, tmp_path / "w.xlsx", {"history": "full"}, {"history": "full", "left_out": ["2026Q3"]})
    assert wb.sheetnames[:4] == ["Overview", DASHBOARD, "What if", "States"]
    ws = wb["What if"]
    text = _text(ws)
    assert "Quarters left out" in text and "2026Q3" in text
    national = [x for x in c["rows"] if not x["key"].startswith("unemployment_") and x["move"] is not None]
    corner = next(cl for row in ws.iter_rows() for cl in row if cl.value == "AS YOU HAVE IT")
    grid = [[ws.cell(corner.row + 1 + k, corner.column + 1 + j).value or 0 for j in range(3)] for k in range(3)]
    assert sum(map(sum, grid)) == len(national)
    from threshold_engine.macro.readings import DIRECTIONS
    for x in national:
        assert grid[DIRECTIONS.index(x["a"]["direction"])][DIRECTIONS.index(x["b"]["direction"])] >= 1
    moved = [x for x in national if x["move"]]
    assert moved
    for x in moved:
        cell = next(cl for col in ws.iter_cols(min_col=2, max_col=2) for cl in col
                    if cl.value == x["title"] and ws.cell(cl.row, 14).value not in (None, "same"))
        assert cell.hyperlink is not None
        assert ws.cell(cell.row, 14).value == ("▲ %d" if x["move"] > 0 else "▼ %d") % abs(x["move"])
        assert ws.cell(cell.row, 6).value.endswith(x["a"]["direction"])
        assert ws.cell(cell.row, 10).value.endswith(x["b"]["direction"])
    same = [x for x in national if x["move"] == 0]
    folded = [r for r in range(1, ws.max_row + 1) if ws.cell(r, 14).value == "same"]
    assert len(folded) == len(same) and all(ws.row_dimensions[r].hidden for r in folded)
    ov = wb["Overview"]
    for x in moved:
        assert "%s → %s" % (x["a"]["direction"], x["b"]["direction"]) in ov.cell(_row(ov, x["title"]), 15).value


def test_the_dashed_lines_are_the_what_ifs_normal_range_over_the_years_its_history_covers(cache, tmp_path):  # noqa: F811
    out, c, wb = _whatif(cache, tmp_path / "w.xlsx", {"history": "full"}, {"history": {"years": 3}})
    ws = wb["Unemployment"]
    row = next(x for x in c["rows"] if x["key"] == "unemployment" and x["reading"] == "change")
    head = _row(ws, "What if: normal from", col=25)
    for col, want in ((25, row["b"]["normal_low"]), (26, row["b"]["normal_high"])):
        assert ws.column_dimensions[openpyxl.utils.get_column_letter(col)].hidden
        filled = [(ws.cell(r, 14).value, ws.cell(r, col).value) for r in range(head + 1, ws.max_row + 1)
                  if ws.cell(r, col).value is not None]
        assert filled and {v for _, v in filled} == {want}
        assert min(d for d, _ in filled).isoformat()[:10] == row["b"]["history_from"][:10]
    assert any(x.count('prstDash val="dash"') == 2 and "areaChart" in x for x in _charts(out).values())


def test_the_what_if_row_on_a_series_tab_is_as_tall_as_its_words(cache, tmp_path):  # noqa: F811
    # The example, 22 Oct 2026: "Reads another way: ..." in bold ran to a third line in a row two lines tall.
    _, _, wb = _whatif(cache, tmp_path / "w.xlsx", {"history": "full"}, {"history": {"years": 3}})
    seen = 0
    for ws in wb.worksheets:
        row = next((r for r in range(1, 12) if ws.cell(r, 7).value == "WHAT IF"), None)
        words = ws.cell(row, 9).value if row else None
        if not words:
            continue
        width = sum(ws.column_dimensions[openpyxl.utils.get_column_letter(c)].width or 9 for c in range(9, 12))
        assert ws.row_dimensions[row].height >= 14 * math.ceil(len(words) / (width * 1.1)), ws.title
        seen += 1
    assert seen


def test_a_different_change_horizon_draws_no_dashed_lines_and_names_both_horizons(cache, tmp_path):  # noqa: F811
    # Six months against twelve is a different measure: its range would sit on the wrong scale.
    out, c, wb = _whatif(cache, tmp_path / "w.xlsx", {"change_months": 6}, {"change_months": 12})
    assert all(not x["same_measure"] for x in c["rows"] if x["reading"] == "change")
    ws = wb["Unemployment"]
    assert not any(ws.cell(r, 25).value for r in range(1, ws.max_row + 1))
    # Codex on #452: each side is its own change, so the row names both and shows neither value as shared.
    wi = wb["What if"]
    rows = [r for r in range(1, wi.max_row + 1) if str(wi.cell(r, 3).value).startswith("Change over")]
    assert rows
    for r in rows:
        assert wi.cell(r, 3).value == "Change over 6 months; what if: over 12 months"
        assert wi.cell(r, 4).value is None and wi.cell(r, 5).value is None
    moved = [x for x in c["rows"] if x["move"]]
    assert moved
    ov = wb["Overview"]
    for x in moved:
        if not x["key"].startswith("unemployment_"):
            assert "(what if: over 12 months)" in ov.cell(_row(ov, x["title"]), 15).value


def test_a_series_in_neither_run_is_not_called_the_same(cache, tmp_path):  # noqa: F811
    # Codex on #452: an unpulled state read "not in this pull" and "same rating" on one row.
    out, c, wb = _whatif(cache, tmp_path / "w.xlsx", {"history": "full"}, {"history": {"years": 3}})
    st = wb["States"]
    tx = _row(st, "TX")
    assert st.cell(tx, 3).value == "not in this pull" and st.cell(tx, 13).value == "not read under either"
    ov = wb["Overview"]
    assert ov.cell(_row(ov, "Initial jobless claims"), 15).value == "not read under either"


def test_a_reading_neither_run_reads_has_its_own_rows_with_each_runs_reason(cache, tmp_path):  # noqa: F811
    out, c, wb = _whatif(cache, tmp_path / "w.xlsx", {}, {"history": {"years": 3}})
    neither = [x for x in c["rows"] if x["a"] is None and x["b"] is None]
    ws = wb["What if"]
    head = next(cl.row for col in ws.iter_cols(min_col=2, max_col=2) for cl in col
                if str(cl.value).startswith("Read under neither set of settings"))
    assert ws.cell(head, 2).value == "Read under neither set of settings (%d)" % len(neither)
    assert ws.cell(head + 3, 6).value.startswith("Not read: not in the pull of 2026-10-15")


def test_a_change_only_one_side_reads_names_that_sides_horizon(cache, tmp_path):  # noqa: F811
    # Codex on #452: the summary named the what-if's horizon for a change that moved, not for one only the
    # what-if read, so a 12-month reading read as the 6-month change beside it.
    out, c, wb = _whatif(cache, tmp_path / "w.xlsx", {"change_months": 400}, {"change_months": 12})
    row = next(x for x in c["rows"] if x["key"] == "unemployment" and x["reading"] == "change")
    assert row["a"] is None and row["b"] and not row["same_measure"]
    ov = wb["Overview"]
    assert ov.cell(_row(ov, "Unemployment rate"), 15).value == "Change (what if: over 12 months): read under the " \
                                                                 "what-if only"
    wi = wb["What if"]
    head = next(cl.row for col in wi.iter_cols(min_col=2, max_col=2) for cl in col
                if str(cl.value).startswith("Read under one set of settings only"))
    r = next(rr for rr in range(head, wi.max_row + 1) if wi.cell(rr, 2).value == "Unemployment rate")
    assert wi.cell(r, 3).value == "Change (what if: over 12 months)"


def test_a_file_gone_before_the_run_has_no_fingerprint_as_read(tmp_path):
    # Codex on #452: a file deleted after the pull kept the manifest's fingerprint under "SHA-256 as read".
    from threshold_engine.macro import pull as P
    P.pull(tmp_path, keys=["unemployment", "cpi"], today="2026-10-17", fetcher=_fetcher())
    pull = R.Pull(tmp_path)
    (pull.folder / "fred-UNRATE.csv").unlink()
    result = R.read_all(tmp_path, check(answered(show_sahm=False)), pull=pull)
    wb = openpyxl.load_workbook(build(tmp_path / "b.xlsx", result, pull))
    ws = wb["Sources"]
    u, cpi = _row(ws, "Unemployment rate"), _row(ws, "Consumer prices, all items")
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
    names is one the chart has, every axis crosses one it has, every series carries its own categories (or,
    on the Dashboard's charts of months, its own months), and no cell holds rich-text runs."""
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
                # without its own categories Excel places a line at 1, 2, 3 ... on a date axis, in 1900
                # (Fable's review of #452, not checked in Excel)
                for ser in re.findall(r"<ser>.*?</ser>", x, re.S):
                    assert "<cat>" in ser or "<xVal>" in ser, (n, ser[:200])
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
    zoomed, _, _ = _build(cache, tmp_path / "z.xlsx", zoom=["2020Q1", "2026Q3"], show_sahm=True)
    assert _holds_together_in_excel(zoomed) > 0


def test_a_workbook_drawn_from_other_bytes_than_the_run_read_is_refused(cache, tmp_path):  # noqa: F811
    # Codex on #452: a run with its own Pull, a file replaced, then a build with a new Pull, published the new
    # file's fingerprint beside readings made from the old one.
    result = R.read_all(cache, check(answered(show_sahm=False)))         # its own Pull, kept inside
    with open(R.Pull(cache).folder / "fred-UNRATE.csv", "a") as fh:
        fh.write("2026-10-01,2.0\n")
    with pytest.raises(Refused, match="fred-UNRATE.csv from other bytes than the run read"):
        build(tmp_path / "macro.xlsx", result, R.Pull(cache))


def test_a_workbook_from_a_new_pull_of_unchanged_files_publishes_the_runs_fingerprints(cache, tmp_path):  # noqa: F811
    result = R.read_all(cache, check(answered(show_sahm=False)))
    wb = openpyxl.load_workbook(build(tmp_path / "macro.xlsx", result, R.Pull(cache)))
    ws = wb["Sources"]
    assert ws.cell(_row(ws, "Unemployment rate"), 10).value == result["read_sha"]["fred-UNRATE.csv"]


def test_a_workbook_whose_pull_lacks_a_file_the_run_read_is_refused(cache, tmp_path):  # noqa: F811
    # Codex on #452: a file gone before the workbook's Pull read it passed the check, its old fingerprint shown.
    result = R.read_all(cache, check(answered(show_sahm=False)))
    (R.Pull(cache).folder / "fred-CPIAUCSL.csv").unlink()
    with pytest.raises(Refused, match="fred-CPIAUCSL.csv from other bytes than the run read"):
        build(tmp_path / "macro.xlsx", result, R.Pull(cache))


def test_a_what_if_not_compared_against_these_readings_is_refused(cache, tmp_path):  # noqa: F811
    # Codex on #452: a what-if from an earlier reading of the pull, or against other settings, was accepted.
    from threshold_engine.macro.compare import compare
    pull = R.Pull(cache)
    ra = R.read_all(cache, check(answered()), pull=pull)
    rb = R.read_all(cache, check(answered(history={"years": 3})), pull=pull)
    c = compare(ra, rb, "settings.json", "what-if.json")
    other = R.read_all(cache, check(answered(normal_width=2)), pull=pull)
    with pytest.raises(Refused, match="not compared against these readings"):
        build(tmp_path / "a.xlsx", other, pull, whatif=c)              # other settings as you have it
    with open(pull.folder / "fred-UNRATE.csv", "a") as fh:
        fh.write("2026-10-01,2.0\n")
    fresh = R.Pull(cache)
    now = R.read_all(cache, check(answered()), pull=fresh)
    with pytest.raises(Refused, match="not compared against these readings"):
        build(tmp_path / "b.xlsx", now, fresh, whatif=c)               # an earlier reading of the pull
    assert build(tmp_path / "c.xlsx", ra, pull, whatif=c)              # the run it was made from
    with pytest.raises(Refused, match="not compared against these readings"):
        build(tmp_path / "d.xlsx", ra, pull, whatif=dict(c, vintage="2026-10-14"))   # another pull's name


def test_readings_built_with_the_pull_of_another_day_are_refused(cache, tmp_path):  # noqa: F811
    # Codex on #452: the workbook names result["vintage"] as its pull; a Pull of another day with the same bytes
    # would make that provenance false.
    import shutil
    pull = R.Pull(cache)
    result = R.read_all(cache, check(answered(show_sahm=False)), pull=pull)
    shutil.copytree(pull.folder, pull.folder.parent / "2026-10-16")
    with pytest.raises(Refused, match="the readings are of the pull of 2026-10-15 and the Pull given is of 2026-10-16"):
        build(tmp_path / "macro.xlsx", result, R.Pull(cache, "2026-10-16"))


def test_a_settings_file_named_like_a_formula_is_written_as_text(cache, tmp_path):  # noqa: F811
    # Codex on #452: a what-if file named "=b.json" went into the Run tab as a formula. The Dashboard's own
    # lookups are the only formulas left in the file.
    from threshold_engine.macro.compare import compare
    pull = R.Pull(cache)
    ra = R.read_all(cache, check(answered()), pull=pull)
    rb = R.read_all(cache, check(answered(history={"years": 3})), pull=pull)
    out = build(tmp_path / "w.xlsx", ra, pull, whatif=compare(ra, rb, "=a.json", "=SUM(1,2)"))
    wb = openpyxl.load_workbook(out)
    with zipfile.ZipFile(out) as z:
        names = {ws.title: "xl/worksheets/sheet%d.xml" % (i + 1) for i, ws in enumerate(wb.worksheets)}
        with_formulas = [t for t, n in names.items() if "<f>" in z.read(n).decode("utf-8")]
    assert with_formulas == [DASHBOARD]
    run = wb["Run"]
    assert "=SUM(1,2)" in {c.value for row in run.iter_rows() for c in row}


# -- the usable-with-care group ---------------------------------------------------------------------------------

@pytest.fixture
def care_book(care_cache, tmp_path):  # noqa: F811
    return _build(care_cache, tmp_path / "care.xlsx", show_sahm=False, history="full")


def test_the_care_tab_reads_every_series_in_the_group_and_names_the_rest(care_book):
    _, result, wb = care_book
    ws = wb[CARE_NAME]
    links = {ws.cell(r, 2).value: _to(ws.cell(r, 2)) for r in range(1, ws.max_row + 1)
             if ws.cell(r, 2).hyperlink and _to(ws.cell(r, 2)) != "Overview"}
    assert links == {s.title: CARE_TAB[s.key] for s in CARE + CARE_DERIVED}
    text = _text(ws)
    assert all(what in text for what, _ in CARE_NOT_READ) and SCE_CREDIT in text
    assert not re.search(r"\b[1-5] (Low|Moderate|High)", text)
    # the saving rate's latest is its lowest: at or above its 1 reading of 321, and its change Decreasing
    row = _row(ws, "Personal saving rate")
    assert ws.cell(row, 4).value == 1.0 and ws.cell(row, 6).value == pytest.approx(1 / 321)
    assert ws.cell(row, 11).value == "▼ Decreasing"
    row = _row(ws, "Real disposable income")
    assert ws.cell(row, 6).value == "change only" and ws.cell(row, 7).value is not None
    assert "Nothing to show, and why" in text and "Job openings" in text
    assert _to(wb["Overview"].cell(2, 2)) == CARE_NAME


def test_a_care_series_tab_draws_its_level_and_its_change_over_its_normal_range(care_book):
    out, result, wb = care_book
    ws = wb["Saving rate"]
    text = _text(ws)
    assert "usable with care" in text and "Why with care" in text
    assert len(ws._charts) == 2                         # its level and its change
    assert type(ws._charts[1]).__name__ == "AreaChart"  # the change, over its normal range
    assert len(wb["Real income"]._charts) == 1          # change only
    assert SCE_CREDIT in _text(wb["Expected missed payments"])
    assert "Not read" in _text(wb["Job openings"]) and not wb["Job openings"]._charts
    assert _holds_together_in_excel(out) > 0


def test_a_build_refuses_a_pull_whose_care_file_changed_since_the_run(care_cache, tmp_path):  # noqa: F811
    result = R.read_all(care_cache, check(answered()))
    pull = R.Pull(care_cache)
    (pull.folder / "nyfed_sce.xlsx").write_bytes((pull.folder / "nyfed_sce.xlsx").read_bytes() + b" ")
    with pytest.raises(Refused, match="nyfed_sce.xlsx"):
        build(tmp_path / "x.xlsx", result, pull)


def test_a_change_is_dated_by_its_own_month_when_the_latest_has_none(tmp_path):
    # Codex on #452: a reading missing the horizon back leaves the latest month with no change, so the change
    # shown is an earlier month's; written beside the latest date alone, it read as the latest month's.
    from test_macro_sources import sce_workbook
    base = _fetcher()

    def fetch(url):
        if "newyorkfed.org" in url and "hhdc" not in url.lower():    # March 2026 missing: no change to September
            return sce_workbook([(100 * (2013 + (5 + i) // 12) + (5 + i) % 12 + 1,
                                  None if i == 153 else 10 + (i * i) % 7) for i in range(160)])
        return base(url)
    R.P.pull(tmp_path, keys=["expected_missed_payment"], today="2026-10-15", fetcher=fetch)
    out, result, wb = _build(tmp_path, tmp_path / "x.xlsx")
    chg = next(x for x in result["readings"] if x["key"] == "expected_missed_payment" and x["reading"] == "change")
    assert chg["date"] == "2026-08-01"
    ws = wb[CARE_NAME]
    row = _row(ws, "Expected chance of missing a minimum debt payment")
    assert ws.cell(row, 3).value.date().isoformat() == "2026-09-01"     # the latest reading
    assert ws.cell(row, 8).value.date().isoformat() == "2026-08-01"     # the month the change runs to


def test_the_printout_and_the_record_carry_the_credit_a_licence_requires(care_cache, tmp_path, capsys):  # noqa: F811
    # Codex on #452: the printout showed the NY Fed's numbers without the attribution its licence requires.
    import json
    from threshold_engine.macro.__main__ import main
    settings = tmp_path / "s.json"
    settings.write_text(json.dumps(answered()))
    assert main(["read", "--cache", str(care_cache), "--settings", str(settings)]) == 0
    out = capsys.readouterr().out
    assert "expected_missed_payment" in out and SCE_CREDIT in out and "rated" not in out
    assert main(["read", "--cache", str(care_cache), "--settings", str(settings), "--json"]) == 0
    record = json.loads(capsys.readouterr().out)
    sce = [x for x in record["readings"] if x["key"] == "expected_missed_payment"]
    assert sce and all(x["credit"] == SCE_CREDIT for x in sce)


def test_show_prints_the_credit_with_the_survey_data_it_prints(care_cache, capsys):  # noqa: F811
    # Codex on #452: show printed the NY Fed survey's observations without the attribution its licence requires.
    from threshold_engine.macro.__main__ import main
    assert main(["show", "--cache", str(care_cache), "expected_missed_payment", "--tail", "3"]) == 0
    out = capsys.readouterr().out
    assert "2026-09-01" in out and out.rstrip().endswith(SCE_CREDIT)
    assert main(["show", "--cache", str(care_cache), "saving_rate", "--tail", "3"]) == 0
    assert "Survey of Consumer Expectations" not in capsys.readouterr().out     # only where a licence asks


# -- household debt -------------------------------------------------------------------------------------------

@pytest.fixture
def household_book(tmp_path):
    from threshold_engine.macro import pull as P
    P.pull(tmp_path, keys=HOUSEHOLD_KEYS, today="2026-10-22", fetcher=_fetcher())
    return _build(tmp_path, tmp_path / "hh.xlsx", history="full", change_months=12)


def test_household_debt_is_one_tab_stacked_as_the_ny_fed_reports_it_with_its_credit(household_book):
    out, result, wb = household_book
    ws = wb[HOUSEHOLD_NAME]
    text = _text(ws)
    for column in ("Mortgage", "HE Revolving", "Auto Loan", "Credit Card", "Student Loan", "Other", "Total"):
        assert column in text
    assert "Source: New York Fed Consumer Credit Panel / Equifax." in text
    stack = next(x for x in _charts(out).values() if "barChart" in x and 'grouping val="stacked"' in x)
    for column in ("Mortgage", "HE Revolving", "Auto Loan", "Credit Card", "Student Loan", "Other"):
        assert "<v>%s</v>" % column in stack                         # the legend: the NY Fed's own names
    assert "Total Debt Balance and Its Composition" in stack
    # each type's row: its latest balance, its share and its change against its own normal range
    row = _row(ws, "Credit Card")
    cards = next(r for r in result["readings"] if r["key"] == "household_credit_card")
    total = next(r for r in result["readings"] if r["key"] == "household_total")
    assert ws.cell(row, 5).value == pytest.approx(cards["value"] / 100)
    assert ws.cell(row, 8).value in ("▲ Increasing", "Stable", "▼ Decreasing")
    assert ws.cell(row, 4).value == pytest.approx(ws.cell(row, 3).value / ws.cell(_row(ws, "Total"), 3).value)
    assert total["direction"] in ("Increasing", "Stable", "Decreasing")
    # the Overview lists every type, each linked to this one tab
    ov = wb["Overview"]
    links = {_to(ov.cell(_row(ov, "Household debt: " + t), 2)) for t in ("mortgage", "credit card", "total")}
    assert links == {HOUSEHOLD_NAME}
    assert _holds_together_in_excel(out) > 0


def test_every_tab_showing_the_ny_feds_figures_carries_its_credit_once(tmp_path):
    # Codex on #471: the Overview showed each type's balance and change without the attribution the NY Fed's
    # terms of use ask for wherever its data are shown. So do the Dashboard (any series can be picked) and the
    # What if tab; the Household debt tab carried it already.
    from threshold_engine.macro import pull as P
    P.pull(tmp_path, keys=HOUSEHOLD_KEYS, today="2026-10-22", fetcher=_fetcher())
    _, _, wb = _whatif(tmp_path, tmp_path / "w.xlsx", {"history": "full"}, {"history": {"years": 3}})
    credit = "Source: New York Fed Consumer Credit Panel / Equifax."
    for name in ("Overview", DASHBOARD, "What if"):
        assert _text(wb[name]).count(credit) == 1, name
    assert credit in _text(wb[HOUSEHOLD_NAME])               # under its chart and in its facts, as before
    assert credit not in _text(wb[CARE_NAME])                # no NY Fed debt figures on it


def test_a_tab_without_a_credited_series_read_carries_no_credits(cache, tmp_path):  # noqa: F811
    _, _, wb = _build(cache, tmp_path / "b.xlsx")
    for name in ("Overview", DASHBOARD, CARE_NAME):
        assert "Credits the publishers' licences require" not in _text(wb[name]), name


def test_a_quarter_left_out_neither_draws_nor_stretches_the_household_debt_chart(tmp_path):
    # Codex on #471: a left-out quarter's total still sized the axis, so a spike it held flattened the bars.
    from threshold_engine.macro import pull as P
    from test_macro_sources import hhdc_page, hhdc_workbook
    base = _fetcher()
    rows = [("%02d:Q%d" % (24 + i // 4, i % 4 + 1), 13.0, 0.4, 1.6, 1.2, 1.6, 0.5, 18.3) for i in range(10)]
    rows[5] = rows[5][:7] + (100.0,)                                  # 2025 Q2's total: a spike

    def fetch(url):
        if "hhdc-iframe" in url:
            return hhdc_page("2026Q2")
        if "HHD_C_Report" in url:
            return hhdc_workbook(rows)
        return base(url)
    P.pull(tmp_path, keys=HOUSEHOLD_KEYS, today="2026-10-22", fetcher=fetch)

    def top(**answers):
        out = _build(tmp_path, tmp_path / ("%s.xlsx" % len(answers)), history="full", change_months=12, **answers)[0]
        stack = next(x for x in _charts(out).values() if "barChart" in x and 'grouping val="stacked"' in x)
        return float(re.search(r'<max val="([\d.]+)"', stack).group(1))
    assert top() >= 100                                               # drawn, the spike sets the axis
    assert top(left_out=["2025Q2"]) == nice_axis(0, 18.3)[1]          # left out, it neither draws nor stretches it

