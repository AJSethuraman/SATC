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
                                             HOUSEHOLD_NAME, SERIES_COLS, TAB, TOPICS, axis_view, build, glossary,
                                             nice_axis)

C = SERIES_COLS

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


def _state(ws, st):
    """A state's row on States, and the first column of the table it sits in: two tables side by side."""
    firsts = [c for c in range(1, ws.max_column + 1) if ws.cell(4, c).value == "State"]
    return next((r, c) for c in firsts for r in range(5, ws.max_row + 1) if ws.cell(r, c).value == st)


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
    # the tab bar follows the Overview's rows, States after the core series (Claude Design, round 1)
    assert wb.sheetnames == (["Overview", DASHBOARD] + tabs + ["States", CARE_NAME] + care
                             + ["State data", "Glossary", "Not read", "Run", "Sources", DASH_DATA])
    assert wb[DASH_DATA].sheet_state == "hidden"
    colour = {ws.title: (ws.sheet_properties.tabColor.rgb[-6:] if ws.sheet_properties.tabColor else None)
              for ws in wb.worksheets}
    assert colour["Overview"] == colour[DASHBOARD] == colour["States"] == "0A0908"           # ink
    for t, (_, keys) in enumerate(TOPICS):                    # slate and stone in turn, by topic
        assert {colour[TAB[k]] for k in keys} == {("57534B", "B9B4AC")[t % 2]}
    assert {colour[n] for n in care + [CARE_NAME]} == {"E4DFD5"}                              # mist
    assert all(colour[n] is None for n in ("State data", "Glossary", "Run", "Sources"))


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
    tiles = {ws.cell(4, c).value: ws.cell(5, c).value for c in range(2, 13) if ws.cell(4, c).value}
    assert tiles["Changes read"] == len(national)
    for d in ("Increasing", "Stable", "Decreasing"):
        key = next(k for k in tiles if k.endswith(d))
        assert tiles[key] == sum(1 for r in national if r["direction"] == d)


def test_the_overview_has_one_header_and_its_method_note_folded_away_at_its_foot(book):
    # Claude Design, round 1: the column header repeated per section is one frozen header; "How this tab works"
    # moves from above the table to its foot, folded away, with no word changed.
    _, result, wb = book
    ws = wb["Overview"]
    assert [ws.cell(7, c).value for c in range(2, 7)] == ["Series", "Latest", "Value", "Unit", "Level: at or above"]
    how = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 2).value == "How this tab works")
    assert sum(1 for r in range(1, how) if ws.cell(r, 2).value == "Series") == 1
    assert ws.freeze_panes == "C8" and ws.cell(8, 2).value == TOPICS[0][0]
    u = _row(ws, "Unemployment rate")
    assert u == 9                                                 # the first series, on the first screen
    # the change's own month only when it is not the latest's
    chg = next(r for r in result["readings"] if r["key"] == "unemployment" and r["reading"] == "change")
    lvl = next(r for r in result["readings"] if r["key"] == "unemployment" and r["reading"] == "position")
    assert chg["date"] == lvl["date"] and ws.cell(u, 8).value is None
    for name in ("Overview", "Unemployment", HOUSEHOLD_NAME, "States", DASHBOARD):
        sheet = wb[name] if name in wb.sheetnames else None
        if sheet is None:
            continue
        how = next(r for r in range(1, sheet.max_row + 1) if sheet.cell(r, 2).value == "How this tab works")
        under = [r for r in range(how + 1, sheet.max_row + 1) if sheet.row_dimensions[r].outlineLevel == 1]
        assert under and all(sheet.row_dimensions[r].hidden for r in under), name
        assert how > max(r for r in range(1, how) if sheet.cell(r, 2).value is not None) - 1


def test_a_series_tab_reads_in_tiles_then_its_two_charts_side_by_side(book):
    # Claude Design, round 1: the figures in tiles under the labels the tables use, the level and change charts
    # side by side, a change-only series' chart the full width, what it is after them; the history past them.
    out, _, wb = book
    ws = wb["Unemployment"]
    assert (ws["B4"].value, ws["H4"].value) == ("LEVEL", "CHANGE OVER 6 MONTHS")
    assert [ws.cell(6, c).value for c in (2, 4, 6, 8, 10, 12, 14, 16)] == [
        "Level: at or above", "Lowest", "Highest", "Normal from", "Normal to", "Typical moves", "Since",
        "History from"]
    assert ws.cell(4, C["date"]).value == "Date" and ws.freeze_panes == "A4"
    # a figure reads from the left of its tile: numbers left alone sat at the right (LibreOffice, 22 Oct 2026)
    assert all(ws.cell(r, c).alignment.horizontal == "left" for r, c in ((5, 2), (7, 2), (7, 8), (7, 12)))
    anchors = sorted((c.anchor._from.col, c.anchor._from.row, c.anchor.to.col) for c in ws._charts)
    assert anchors[0][0] == 1 and anchors[1][0] == 13 and anchors[0][1] == anchors[1][1]    # B and N, one row
    assert anchors[0][2] == 13 and anchors[1][2] == 25                                       # to M and to Y
    only = wb["Prices"]._charts
    assert len(only) == 1 and (only[0].anchor._from.col, only[0].anchor.to.col) == (1, 25)  # the full width
    text = _text(ws)
    what = _row(ws, "What it is")
    assert what > anchors[0][1] and "Level" in [ws.cell(r, 2).value for r in range(what, ws.max_row + 1)]
    assert "at or above" in text and "typical moves above the median change" in text      # the tool's sentences
    # every history chart: gridlines in the row rule's colour, a triangle for each reading off the axis
    hist = [x for x in _charts(out).values() if "'Unemployment'!" in x and "Sahm" not in x]
    assert hist and all("<majorGridlines>" in x and "EFEBE4" in x for x in hist)
    assert all('<symbol val="triangle"/>' in x for x in hist)


def test_a_reading_off_the_axis_is_marked_at_the_edge(tmp_path):
    out, result, wb = _build(_spiked(tmp_path, ["unemployment"]), tmp_path / "m.xlsx", axis_cut=1, history="full")
    ws = wb["Unemployment"]
    lvl = next(x for x in _charts(out).values() if "Level against its history" in x)
    hi = float(re.search(r'<max val="([\d.]+)"', lvl).group(1))
    marked = {ws.cell(r, C["date"]).value.date().isoformat(): ws.cell(r, C["off_level"]).value
              for r in range(5, ws.max_row + 1) if ws.cell(r, C["off_level"]).value is not None}
    assert marked == {"2020-04-01": hi, "2020-05-01": hi}          # at the axis's top, on each reading off it


def test_the_dashboard_cuts_each_pick_at_the_firms_setting_and_marks_what_runs_off(book):
    # Claude Design, round 1: past each series' cut (the firm's 1% at each end) a drawn value is #N/A, so the
    # axis fits the rest, and a triangle marks it at the cut; the line under the charts set together counts them.
    out, result, wb = book
    ws = wb[DASHBOARD]
    data = wb[DASH_DATA]
    col = {data.cell(2, c).value: c for c in range(2, data.max_column + 1) if data.cell(2, c).value}
    r = next(r for r in range(3, data.max_row + 1) if data.cell(r, col["Series"]).value == "Unemployment rate")
    lo, hi = data.cell(r, col["Moves: off below"]).value, data.cell(r, col["Moves: off above"]).value
    chg = next(x for x in result["readings"] if x["key"] == "unemployment" and x["reading"] == "change")
    assert lo <= -1.5 and hi >= max(1.5, chg["movement"] - 1e-9)   # the normal band and the latest always stay on
    assert ws["AN8"].value == "=IFERROR(%s+0,NA())" % re.search(r"(INDEX\(.*\))\+0", ws["AN8"].value).group(1)
    drawn, marker = ws.cell(3, 43 + 7).value, ws.cell(3, 43 + 10).value
    assert drawn == "=IF(ISNUMBER(AT3),IF(OR(AT3>$AN$9,AT3<$AN$8),NA(),AT3),NA())", drawn
    assert marker == "=IF(ISNUMBER(AQ3),IF(ISNUMBER(AT3),IF(AT3>$AN$9,$AN$9,IF(AT3<$AN$8,$AN$8,NA())),NA()),NA())"
    assert "COUNTIF(" in ws["AN14"].value and "the furthest" in ws["AN14"].value
    note_ = [c.value for row in ws.iter_rows(min_col=2, max_col=2) for c in row
             if isinstance(c.value, str) and c.value.startswith("=$AN$14&")]
    assert note_ == ['=$AN$14&IF(AND($AN$14<>"",$AN$15<>"")," ","")&$AN$15']
    moves = next(x for x in _charts(out).values() if "Both changes" in x)
    assert moves.count('<symbol val="triangle"/>') == 2
    gone = set(re.findall(r'<legendEntry><idx val="(\d+)"/><delete val="1"/></legendEntry>', moves))
    assert gone == {"3", "4", "5"}                    # the second "Normal movement" and both pick's triangles


def test_a_missing_month_is_an_empty_cell_and_says_so(book):
    _, _, wb = book
    ws = wb["Unemployment"]
    row = next(c.row for col in ws.iter_cols(min_col=C["date"], max_col=C["date"]) for c in col
               if getattr(c.value, "isoformat", None) and c.value.isoformat()[:10] == "2025-10-01")
    assert ws.cell(row, C["value"]).value is None       # not zero, not text a chart would draw as zero
    assert ws.cell(row, C["note"]).value == "no value published"


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
    head = _row(ws, "Normal from", col=C["band"])
    filled = {(ws.cell(r, C["band"]).value, ws.cell(r, C["band"] + 1).value) for r in range(head + 1, ws.max_row + 1)
              if ws.cell(r, C["band"]).value is not None}
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
                    "MAX", "COUNTIF", "ABS", "TEXT", "CORREL", "SUMPRODUCT", "TDIST", "SQRT", "AVERAGE", "SUM",
                    "COUNT"}, used
    for x in formulas:
        for sheet in re.findall(r"'([^']+)'!", x):
            assert sheet in (DASH_DATA, DASHBOARD), x
    # four pickers: two series, each from the list of every national and care series, and two quarters
    dvs = {str(d.sqref): d for d in ws.data_validations.dataValidation}
    series_dv = next(d for k, d in dvs.items() if set(k.split()) == {"B5", "H5"})
    quarter_dv = next(d for k, d in dvs.items() if set(k.split()) == {"N5", "Q5"})
    assert len(dvs) == 2 and series_dv.type == quarter_dv.type == "list"
    data = wb[DASH_DATA]
    col = re.match(r"'%s'!\$([A-Z]+)\$" % DASH_DATA, series_dv.formula1).group(1)
    names = [c.value for c in data[col][2:] if c.value]
    national = [k for _, keys in TOPICS for k in keys] + [k for _, keys in CARE_TOPICS for k in keys]
    assert len(names) == len(national) and ws["B5"].value in names and ws["H5"].value in names
    col = re.match(r"'%s'!\$([A-Z]+)\$" % DASH_DATA, quarter_dv.formula1).group(1)
    quarters = [c.value for c in data[col][2:] if c.value]
    assert quarters[0] == "2000 Q1" and quarters[-1] == "2026 Q3" and len(quarters) == len(set(quarters))
    assert (ws["N5"].value, ws["Q5"].value) == ("2000 Q1", "2026 Q3")      # opens on every quarter
    assert ws.freeze_panes == "A6"                                          # the four boxes stay in view


def test_the_dashboard_charts_fit_their_picks_in_years_and_draw_no_point_legends(book):
    # The firm, 22 Oct 2026, in Excel: years from 1900 to 2036 printed over the legends, and rows of unnamed
    # dashes under the one-line charts.
    out, result, wb = book
    charts = [x for n, x in _charts(out).items() if "scatterChart" in x]
    assert len(charts) == 1                                       # both changes together; the rest are tables
    for x in charts:
        assert re.search(r"'Dashboard'!\$(B|H)\$5|'Dashboard'!\$AO\$1[45]", x)   # named by the boxes
        assert '<varyColors val="0"/>' in x                       # one colour a line: no legend entry a point
        x_axis = re.search(r'<valAx><axId val="500"/>.*?</valAx>', x, re.S).group(0)
        assert '<axPos val="b"/>' in x_axis and 'formatCode="0"' in x_axis       # years, along the foot
        assert "<min " not in x_axis and "<max " not in x_axis                    # fitted to what is picked
        legend = re.search(r"<legend>.*?</legend>", x, re.S)
        picks = len(re.findall(r"<ser>.*?<strRef>", x, re.S))
        assert (legend is None) == (picks == 1)                   # a chart of one pick has no legend
        if legend:
            assert '<legendPos val="t"/>' in legend.group(0)       # above, clear of the years
            gone = re.findall(r'<legendEntry><idx val="(\d+)"/><delete val="1"/></legendEntry>', legend.group(0))
            names = re.findall(r"<ser>.*?<tx>(.*?)</tx>", x, re.S)
            shown = [n for k, n in enumerate(names) if str(k) not in gone]
            assert len(shown) == len(set(shown)), shown            # no name twice
        assert '<dispBlanksAs val="span"/>' in x                  # a quarterly pick drawn beside a monthly one
    # the drawn years are the months in years, and the window helpers read the From and To quarters
    ws = wb[DASHBOARD]
    # one row a month, none skipped, from 12 months before the first reading (the longest lead back, -12 in the
    # test settings) to 24 after the last (the longest forward)
    years = [ws.cell(r, 42).value for r in range(3, 3 + 14)]
    assert years[0] == 1999.0 and years[12] == 2000.0
    assert all(abs(b - a - 1 / 12) < 1e-9 for a, b in zip(years, years[1:]))
    t0, t1 = (ws.cell(r, 40).value for r in (6, 7))
    assert t0.startswith("=INDEX(") and "$N$5" in t0 and t1.startswith("=INDEX(") and "$Q$5" in t1
    # each month is drawn only from the From quarter's first month to the To quarter's last
    for col in (43, 55):
        x = ws.cell(3, col).value
        assert ",$AP3>=$AN$6,$AP3<=$AN$7),$AP3,NA())" in x, x


def test_the_dashed_lines_run_only_inside_the_quarters_chosen(book):
    # Codex on #471 read the dashed lines' ends as clamped the wrong way round, which would stretch every change
    # chart back over the whole history. They were not (in LibreOffice, From 2020 Q2 to 2026 Q3 drew them from
    # 2020.25 to 2026.7), but no test would have failed had they been: each line starts at the later of From and
    # the pick's first month, and ends at the earlier of To and its last.
    _, _, wb = book
    ws = wb[DASHBOARD]
    lines_at = 40 + 3 + 24                                  # the normal movement lines across the chart
    for col in (lines_at,):
        start, end = ws.cell(3, col).value, ws.cell(4, col).value
        assert re.match(r"=(IFERROR\()?MAX\(\$AN\$6,", start), start
        assert re.match(r"=(IFERROR\()?MIN\(\$AN\$7,", end), end


def _dash_cols(ws):
    """The Dashboard's hidden comparison columns, by the names in their row 2."""
    return {ws.cell(2, c).value: c for c in range(40, ws.max_column + 1) if isinstance(ws.cell(2, c).value, str)}


def _ranges(formula):
    """Each column range in a formula, as (column, first row, last row)."""
    return [(a, int(b), int(d)) for a, b, c, d in re.findall(r"\$([A-Z]+)\$(\d+):\$([A-Z]+)\$(\d+)", formula)]


def test_the_dashboard_sets_each_lead_beside_the_second_series_that_many_months_later(book):
    # The firm, 23 Oct 2026: the Dashboard becomes the comparison of two series, "As the Excel version": one
    # reading a year at four starting points, the leads the settings name, p < 0.05 after allowing for the leads.
    _, result, wb = book
    ws = wb[DASHBOARD]
    col = _dash_cols(ws)
    first_start = col["First series: change at starting point 1"]
    second = openpyxl.utils.get_column_letter(col["Second series: change in the quarters chosen"])
    leads = [-12, 0, 6, 12, 24]                                   # the test settings' compare_leads
    words = [ws.cell(19 + j, 2).value for j in range(len(leads))]
    assert words == ["Second leads by 12 months", "At the same time", "First leads by 6 months",
                     "First leads by 12 months", "First leads by 24 months"]
    for j, lead in enumerate(leads):
        found = [c.value for c in ws[19 + j] if isinstance(c.value, str) and "CORREL(" in c.value]
        assert len(found) == 4                                     # one r at each starting point
        for f, x in enumerate(found):
            (c1, a1, b1), (c2, a2, b2) = _ranges(x)
            assert c1 == openpyxl.utils.get_column_letter(first_start + f) and c2 == second, x
            assert (a2 - a1, b2 - b1) == (lead, lead), (lead, x)   # the second, that many months later
            assert a1 - 3 == 12 and ws.max_row >= b2               # the padding before holds the longest lead back
    # each starting point keeps the first series' change in its month only: January, April, July, October
    month = openpyxl.utils.get_column_letter(col["Month of the year"])
    for f in range(4):
        x = ws.cell(20, first_start + f).value
        assert x.startswith("=IF($%s20=%d," % (month, 3 * f)), x
    # each change is kept only inside the From and To quarters
    x = ws.cell(20, col["Second series: change in the quarters chosen"]).value
    assert ">=$AN$6" in x and "<=$AN$7" in x


def test_a_lead_holds_only_when_every_starting_point_passes_after_allowing_for_the_leads_tried(book):
    _, _, wb = book
    ws = wb[DASHBOARD]
    row = [c.value for c in ws[21] if isinstance(c.value, str)]
    ps = [x for x in row if "TDIST(" in x]
    assert len(ps) == 4 and all(">=6" in x and "-2,2)" in x for x in ps)          # 6 pairs at least; two-tailed
    holds_in = next(x for x in row if x.startswith("=IF(") and "COUNTIF(" in x and '"<"&0.05/MAX(' in x)
    tested = re.search(r"/MAX\((\$[A-Z]+\$\d+),1\)", holds_in).group(1)
    assert ws[tested.replace("$", "")].value.startswith("=SUM(")              # the leads tested, counted
    holds = next(x for x in row if x.startswith("=AND(") and "=4," in x)
    assert holds.count("=1") == 1                                               # tested, all 4 pass, same sign
    same_sign = next(x for x in row if '">0")=4' in x and '"<0")=4' in x)
    assert same_sign.startswith("=IF(")
    # each starting point's p is on its effective pairs, n(1 - y1 y2)/(1 + y1 y2) and never more than n, y1 and y2
    # each series' change against its own a year earlier: readings a year apart are not independent (Codex on #472)
    cells = {c.coordinate: c.value for c in ws[21] if isinstance(c.value, str)}
    effs = {k: v for k, v in cells.items() if v.startswith("=IFERROR(MIN(")}
    assert len(effs) == 4
    for k, v in effs.items():
        m = re.fullmatch(r'=IFERROR\(MIN\(([A-Z]+21),\1\*\(1-(\$\w+\$\d+)\*(\$\w+\$\d+)\)/\(1\+\2\*\3\)\),""\)', v)
        assert m, v
        assert sum("SQRT((%s-2)/" % k in p and ",%s-2,2)" % k in p for p in ps) == 1, k
    # a lead is tested only with a p at every starting point: too few effective pairs give none, and such a lead
    # must neither read 0 passes nor count among the leads the level is divided by (Codex on #472)
    p_at = [k for k, v in cells.items() if "TDIST(" in v]
    tested_here = next(v for v in cells.values() if v.startswith("=IF(AND(MIN("))
    assert "COUNT(%s:%s)=4" % (p_at[0], p_at[-1]) in tested_here, tested_here
    col = _dash_cols(ws)
    for y, who in zip(m.groups()[1:], ("First", "Second")):
        (c1, a1, b1), (c2, a2, b2) = _ranges(ws[y.replace("$", "")].value)
        assert c1 == c2 == openpyxl.utils.get_column_letter(col["%s series: change in the quarters chosen" % who])
        assert (a2 - a1, b2 - b1) == (12, 12)                                   # a year on
    assert "on effective pairs" in ws.cell(19 + 5, 2).value                    # the note under the five leads
    # at the same time, on every shared reading: effective readings n(1 - r1 r2)/(1 + r1 r2), and p on them
    eff = ws["I15"].value
    target = ws[eff.lstrip("=").replace("$", "")].value
    assert re.search(r"\*\(1-(\$\w+\$\d+)\*(\$\w+\$\d+)\)/\(1\+\1\*\2\)", target), target
    assert re.search(r"MIN\((\$\w+\$\d+),\1\*", target), target                # never more than the readings
    p = ws[ws["J15"].value.lstrip("=").replace("$", "")].value
    assert "TDIST(" in p and "-2,2)" in p
    answer = ws["B11"].value
    assert "holding at all 4 starting points" in answer and "which passes" in answer and "From is after To" in answer
    # a near miss, the same sign at every starting point without passing at all, reads in the table's words, "holds
    # in 2 of 4, 11 years tested", not "no lead holds" (the firm, 23 Oct 2026: "just say something like 2 of 4,
    # tested x"); the years are the table's fewest pairs at the strongest lead
    sign_col = next(c.column_letter for c in ws[21] if isinstance(c.value, str) and '">0")=4' in c.value)
    hin_col = next(c.column_letter for c in ws[21] if isinstance(c.value, str) and c.value.startswith("=IF(")
                   and '"<"&0.05/MAX(' in c.value)
    near = answer.index('IF(AND(INDEX($%s$19:$%s$23,' % (sign_col, sign_col))
    assert answer.startswith(',INDEX($%s$19:$%s$23,' % (hin_col, hin_col), answer.index("),", near) + 1)  # 1 of 4 at least
    assert answer.index('", holds in "&', near) < answer.index("No lead holds at every starting point", near)
    assert '&INDEX($I$19:$I$23,' in answer and '" years tested."' in answer


def test_the_dashboards_marks_are_keybanks_colours_and_the_house_mist_never_blue_or_orange(book):
    # The firm, 23 Oct 2026: "not a huge fan of the blue and orange - i would rather use more Keybank esque colors"
    out, _, wb = book
    moves = next(x for x in _charts(out).values() if "Both changes" in x)
    assert "0A0908" in moves and "CC0000" in moves
    assert "2A78D6" not in moves and "EB6834" not in moves
    ws = wb[DASHBOARD]
    rules = [r for cf in ws.conditional_formatting for r in cf.rules]
    fills = {r.dxf.fill.fgColor.rgb[-6:] for r in rules if r.dxf and r.dxf.fill is not None}
    assert fills == {"E4DFD5"}                                  # mist: the answer that holds, the strongest lead


def test_a_zoom_opens_the_dashboard_on_its_quarters_and_keeps_every_month(cache, tmp_path):  # noqa: F811
    _, _, wb = _build(cache, tmp_path / "z.xlsx", zoom=["2024Q1", "2026Q3"])
    ws = wb[DASHBOARD]
    assert (ws["N5"].value, ws["Q5"].value) == ("2024 Q1", "2026 Q3")
    assert ws.cell(3 + 12, 42).value == 2000.0                    # the From box can still widen the view


def test_a_zoom_from_a_quarter_left_out_or_past_the_data_still_opens_on_quarters_the_boxes_offer(cache, tmp_path):  # noqa: F811,E501
    # Codex on #471: the From and To lists held only quarters with a reading, so a zoom from the first quarter left
    # out, or to one past the data, opened the boxes on a quarter the lookup could not find, and every chart broke.
    for zoom, left in ((["2020Q2", "2026Q3"], ["2020Q2-2021Q2"]), (["2024Q1", "2027Q2"], [])):
        _, _, wb = _build(cache, tmp_path / ("z%s.xlsx" % zoom[0]), zoom=zoom, left_out=left)
        ws, data = wb[DASHBOARD], wb[DASH_DATA]
        dq = next(d for d in ws.data_validations.dataValidation if set(str(d.sqref).split()) == {"N5", "Q5"})
        col = re.match(r"'%s'!\$([A-Z]+)\$" % DASH_DATA, dq.formula1).group(1)
        quarters = [c.value for c in data[col][2:] if c.value]
        assert ws["N5"].value in quarters and ws["Q5"].value in quarters, (zoom, ws["N5"].value, ws["Q5"].value)
        assert len(quarters) == len(set(quarters))
        # one quarter after another, none skipped
        idx = [int(q[:4]) * 4 + int(q[-1]) for q in quarters]
        assert idx == list(range(idx[0], idx[-1] + 1))


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
    out, _, shown = _build(cache, tmp_path / "sahm.xlsx", show_sahm=True)
    assert "Sahm's published trigger is 0.50" in _text(shown["Overview"])
    ws = shown["Unemployment"]
    assert "Sahm reading" in _text(ws) and ws["T4"].value == "SAHM READING, BESIDE THE CHANGE"
    # its columns are hidden helpers, so the chart is told to plot them: left alone it drew nothing (22 Oct 2026)
    sahm = next(x for x in _charts(out).values() if "Sahm reading" in x)
    assert 'plotVisOnly val="0"' in sahm


def test_states_have_their_own_sheet_and_stay_off_the_national_one(book):
    _, result, wb = book
    assert any(r["key"] == "unemployment_ca" for r in result["readings"])
    assert "Unemployment rate, CA" not in _text(wb["Overview"])
    ws = wb["States"]
    ca, c0 = _state(ws, "CA")
    assert ws.cell(ca, c0 + 7).value in ("▲ Increasing", "Stable", "▼ Decreasing")
    assert 0 < ws.cell(ca, c0 + 3).value <= 1
    tx, c0 = _state(ws, "TX")
    assert ws.cell(tx, c0 + 1).value == "not in this pull"
    # two tables side by side, 26 states and 25, all 51 in rows 5 to 30 (Claude Design, round 1)
    firsts = [c for c in range(1, ws.max_column + 1) if ws.cell(4, c).value == "State"]
    counts = [sum(1 for r in range(5, 40) if ws.cell(r, c).value in STATES) for c in firsts]
    assert len(firsts) == 2 and counts == [26, 25] and ws.freeze_panes == "A5"


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
    assert rows["Initial jobless claims"][6] == "not in this pull"     # fetched; the address and SHA at the end


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
    col = C["latest_change"]
    head = _row(ws, "Latest", col=col)
    latest = [ws.cell(r, col).value for r in range(head + 1, ws.max_row + 1) if ws.cell(r, col).value is not None]
    assert len(latest) == 1 and round(latest[0], 2) == latest[0]


def test_a_series_tab_prints_its_readings_and_charts_not_its_whole_history(book):
    # Walk (W14): the workbook printed 856 pages, about 800 of them data.
    _, _, wb = book
    for name in {TAB[k] for _, keys in TOPICS for k in keys}:
        assert wb[name].print_area and wb[name].print_area.startswith("'%s'!$A$1:$Y$" % name), name


def test_quarters_left_out_are_not_drawn_and_are_said_on_every_tab(cache, tmp_path):  # noqa: F811
    out, result, wb = _build(cache, tmp_path / "left.xlsx", history="full", left_out=["2026Q3"])
    ws = wb["Unemployment"]
    rows = {ws.cell(r, C["date"]).value.date().isoformat(): r for r in range(1, ws.max_row + 1)
            if getattr(ws.cell(r, C["date"]).value, "date", None)}
    sep = rows["2026-09-01"]
    assert ws.cell(sep, C["value"]).value == 9.0                 # the publisher's figure is kept in the table
    assert ws.cell(sep, C["note"]).value == "left out (2026Q3)" and ws.cell(sep, C["level"]).value is None
    assert ws.cell(rows["2026-06-01"], C["level"]).value is not None
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
    assert data.cell(stats, latest_col).value == "2026-06"            # as the Dashboard shows a month
    assert "Later readings, to Sep 2026, fall in quarters left out." in _text(ws)
    _, _, sahm_ = _build(cache, tmp_path / "left-sahm.xlsx", history="full", left_out=["2026Q3"], show_sahm=True)
    ws = sahm_["Unemployment"]
    drawn = {ws.cell(r, C["date"]).value.date().isoformat(): ws.cell(r, C["sahm"]).value
             for r in range(1, ws.max_row + 1) if getattr(ws.cell(r, C["date"]).value, "date", None)}
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
        refs = re.findall(r"<f>'Unemployment'!\$AA\$(\d+):\$AA\$(\d+)</f>", x)
        if refs:
            first_drawn[n] = refs[0]
    assert first_drawn
    for a, b in first_drawn.values():
        assert ws.cell(int(a), C["date"]).value.date().isoformat() == "2024-01-01"
        assert ws.cell(int(b), C["date"]).value.date().isoformat() == "2026-09-01"
    assert "The charts show 2024Q1 to 2026Q3 only" in _text(ws)
    run = {wb["Run"].cell(r, 2).value: wb["Run"].cell(r, 3).value for r in range(1, wb["Run"].max_row + 1)}
    assert run["Charts zoomed to"] == "2024Q1 to 2026Q3; no reading changes with it"
    # the whole history is still in the table
    assert any(getattr(ws.cell(r, C["date"]).value, "year", 0) == 2000 for r in range(1, ws.max_row + 1))


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
    assert wb.sheetnames[:4] == ["Overview", DASHBOARD, "What if", "Unemployment"]
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
    # blank when every reading of the series reads the same way: the tile counts those (Claude Design, round 1)
    alike = {x["title"] for x in c["rows"] if x["key"] not in {y["key"] for y in c["rows"] if y["move"]}
             and x["a"] and x["b"] and not x["key"].startswith("unemployment_")}
    assert alike and all(ov.cell(_row(ov, t), 15).value is None for t in alike)


def test_the_dashed_lines_are_the_what_ifs_normal_range_over_the_years_its_history_covers(cache, tmp_path):  # noqa: F811
    out, c, wb = _whatif(cache, tmp_path / "w.xlsx", {"history": "full"}, {"history": {"years": 3}})
    ws = wb["Unemployment"]
    row = next(x for x in c["rows"] if x["key"] == "unemployment" and x["reading"] == "change")
    head = _row(ws, "What if: normal from", col=C["whatif"])
    for col, want in ((C["whatif"], row["b"]["normal_low"]), (C["whatif"] + 1, row["b"]["normal_high"])):
        assert ws.column_dimensions[openpyxl.utils.get_column_letter(col)].hidden
        filled = [(ws.cell(r, C["date"]).value, ws.cell(r, col).value) for r in range(head + 1, ws.max_row + 1)
                  if ws.cell(r, col).value is not None]
        assert filled and {v for _, v in filled} == {want}
        assert min(d for d, _ in filled).isoformat()[:10] == row["b"]["history_from"][:10]
    # slate, dashed, 1 pt: one way to draw the what-if's range on every tab (Claude Design, round 1)
    assert any(x.count('prstDash val="sysDash"') == 2 and "areaChart" in x and '57534B' in x
               for x in _charts(out).values())


def test_the_what_if_row_on_a_series_tab_is_as_tall_as_its_words(cache, tmp_path):  # noqa: F811
    # The example, 22 Oct 2026: "Reads another way: ..." in bold ran to a third line in a row two lines tall.
    _, _, wb = _whatif(cache, tmp_path / "w.xlsx", {"history": "full"}, {"history": {"years": 3}})
    seen = 0
    for ws in wb.worksheets:
        row = next((r for r in range(1, 12) if ws.cell(r, 8).value == "WHAT IF"), None)     # the change tile's
        words = ws.cell(row, 11).value if row else None
        if not words:
            continue
        room = sum(7 * (ws.column_dimensions[openpyxl.utils.get_column_letter(c)].width or 8.43) + 5
                   for c in range(11, 20)) - 8
        assert ws.row_dimensions[row].height >= 15 * math.ceil(len(words) * 6.6 / room), ws.title
        seen += 1
    assert seen


def test_a_change_read_only_under_the_what_if_still_builds_its_tab(tmp_path):
    # Codex on #471: a quarterly series with every quarter but two left out, six months apart, has one change over
    # six months as you have it, too few to read, while the what-if reads it. The chart was sized from the what-if's latest date in
    # the column of the first side's changes, found an empty cell, and the whole build failed.
    from threshold_engine.macro import pull as P
    base = _fetcher()

    def fetch(url):                                   # a quarterly series, 2000 Q1 to 2026 Q3, irregular
        if "id=DRTSCLCC" in url:
            rows = ["observation_date,DRTSCLCC"] + ["%d-%02d-01,%d" % (2000 + i // 4, 3 * (i % 4) + 1, (i * i) % 9 - 4)
                                                    for i in range(107)]
            return ("\n".join(rows) + "\n").encode()
        return base(url)
    P.pull(tmp_path, keys=["card_standards"], today="2026-10-22", fetcher=fetch)
    out, c, wb = _whatif(tmp_path, tmp_path / "w.xlsx",
                         {"history": "full", "left_out": ["1990Q1-2024Q2", "2024Q4", "2025Q2-2026Q4"]},
                         {"history": "full"})
    row = next(x for x in c["rows"] if x["key"] == "card_standards" and x["reading"] == "change")
    assert row["a"] is None and row["b"] is not None              # read under the what-if only
    assert "Read under the what-if only" in _text(wb["Card standards"])
    assert _holds_together_in_excel(out) > 0


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
    tx, c0 = _state(st, "TX")
    assert st.cell(tx, c0 + 1).value == "not in this pull" and st.cell(tx, c0 + 11).value == "not read under either"
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
    assert _to(wb["Overview"].cell(2, 3)) == CARE_NAME


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


def test_new_bankruptcies_have_a_care_tab_with_the_2005_law_marked_and_the_ny_feds_credit(tmp_path):
    # The firm, 23 Oct 2026, "build it": the NY Fed's count of people with a new bankruptcy on their credit report.
    from threshold_engine.macro import pull as P
    from threshold_engine.macro.catalog import HHDC_CREDIT
    P.pull(tmp_path, keys=["new_bankruptcies"], today="2026-10-22", fetcher=_fetcher())
    out, result, wb = _build(tmp_path, tmp_path / "b.xlsx", history="full", change_months=12)
    got = {x["reading"]: x for x in result["readings"] if x["key"] == "new_bankruptcies"}
    assert set(got) == {"position", "change"} and all(x["care"] for x in got.values())
    ws = wb[CARE_TAB["new_bankruptcies"]]
    text = _text(ws)
    assert "17 October 2005" in text and "Why with care" in text and HHDC_CREDIT in text
    assert len(ws._charts) == 2                                       # its level and its change
    care = wb[CARE_NAME]
    row = _row(care, "People with a new bankruptcy on their credit report")
    assert _to(care.cell(row, 2)) == CARE_TAB["new_bankruptcies"]
    assert _text(care).count(HHDC_CREDIT) == 1                        # its figures shown there: credited once
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
    # the table beside the NY Fed's chart, N to Y (Claude Design, round 1)
    row = _row(ws, "Credit Card", col=14)
    cards = next(r for r in result["readings"] if r["key"] == "household_credit_card")
    total = next(r for r in result["readings"] if r["key"] == "household_total")
    assert ws.cell(row, 18).value == pytest.approx(cards["value"] / 100)
    assert ws.cell(row, 21).value in ("▲ Increasing", "Stable", "▼ Decreasing")
    assert ws.cell(row, 17).value == pytest.approx(ws.cell(row, 16).value / ws.cell(_row(ws, "Total", col=14), 16).value)
    assert total["direction"] in ("Increasing", "Stable", "Decreasing")
    # the Overview lists every type, each linked to this one tab; the six types folded away under the total
    ov = wb["Overview"]
    links = {_to(ov.cell(_row(ov, "Household debt: " + t), 2)) for t in ("mortgage", "credit card", "total")}
    assert links == {HOUSEHOLD_NAME}
    t, m = _row(ov, "Household debt: total"), _row(ov, "Household debt: mortgage")
    assert m == t + 1 and ov.row_dimensions[m].hidden and not ov.row_dimensions[t].hidden
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
    # the count of new bankruptcies comes from the same NY Fed file, so it is read and credited there too
    assert _text(wb[CARE_NAME]).count(credit) == 1


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



def test_a_type_blank_in_the_newest_quarter_says_so_instead_of_showing_an_older_quarter(tmp_path):
    # Codex on #471: a type the NY Fed left blank in its newest quarter showed its previous quarter's balance and
    # change under "Each type, latest quarter", as though they were the newest quarter's.
    from threshold_engine.macro import pull as P
    from test_macro_sources import hhdc_page, hhdc_workbook
    base = _fetcher()
    rows = [("%02d:Q%d" % (24 + i // 4, i % 4 + 1), 13.0 + i / 10, 0.4, 1.6, 1.2 + i / 100, 1.6, 0.5, 18.3 + i / 10)
            for i in range(10)]
    rows[-1] = rows[-1][:4] + (None,) + rows[-1][5:]                 # 2026 Q2: no credit card balance

    def fetch(url):
        if "hhdc-iframe" in url:
            return hhdc_page("2026Q2")
        if "HHD_C_Report" in url:
            return hhdc_workbook(rows)
        return base(url)
    P.pull(tmp_path, keys=HOUSEHOLD_KEYS, today="2026-10-22", fetcher=fetch)
    _, _, wb = _build(tmp_path, tmp_path / "hh.xlsx", history="full", change_months=12)
    ws = wb[HOUSEHOLD_NAME]
    cards = _row(ws, "Credit Card", col=14)
    assert ws.cell(cards, 16).value == "No 2026 Q2 value in the NY Fed's file; its latest is 2026 Q1."
    assert all(ws.cell(cards, c).value is None for c in range(17, 26))
    mortgage = _row(ws, "Mortgage", col=14)
    assert ws.cell(mortgage, 16).value == pytest.approx(13.9)       # a type the newest quarter holds, as before


def test_the_household_debt_chart_draws_the_what_ifs_normal_range_as_every_series_tab_does(tmp_path):
    # Codex on #471: under --compare the series tabs dashed the what-if's normal range over their change charts;
    # the household total's chart, drawn by its own code, did not.
    from threshold_engine.macro import pull as P
    P.pull(tmp_path, keys=HOUSEHOLD_KEYS, today="2026-10-22", fetcher=_fetcher())
    out, c, wb = _whatif(tmp_path, tmp_path / "w.xlsx", {"history": "full"}, {"history": {"years": 3}})
    row = next(x for x in c["rows"] if x["key"] == "household_total" and x["reading"] == "change")
    assert row["same_measure"] and row["b"]
    ws = wb[HOUSEHOLD_NAME]
    head = next(cl for r in ws.iter_rows() for cl in r if cl.value == "What if: normal from")
    for col, want in ((head.column, row["b"]["normal_low"]), (head.column + 1, row["b"]["normal_high"])):
        assert ws.column_dimensions[openpyxl.utils.get_column_letter(col)].hidden
        filled = [(ws.cell(r, 27).value, ws.cell(r, col).value) for r in range(head.row + 1, ws.max_row + 1)
                  if ws.cell(r, col).value is not None]
        assert filled and all(v == pytest.approx(want, abs=1e-9) for _, v in filled)
        assert min(d for d, _ in filled).isoformat()[:10] == row["b"]["history_from"][:10]
    chart = next(x for x in _charts(out).values() if "Total: change over" in x)
    assert chart.count('prstDash val="sysDash"') == 2 and "the normal range under the what-if" in chart


def test_the_household_total_read_under_the_what_if_only_still_draws_its_change_chart(tmp_path):
    # Codex on #471: with the total too short to read as you have it but read under the what-if, the chart was
    # skipped, so the tab showed neither the change nor the what-if's range. The series tabs draw it.
    from threshold_engine.macro import pull as P
    P.pull(tmp_path, keys=HOUSEHOLD_KEYS, today="2026-10-22", fetcher=_fetcher())
    left = ["2003Q1-2025Q3", "2026Q1"]                               # one change over 6 months: too few
    out, c, wb = _whatif(tmp_path, tmp_path / "w.xlsx", {"history": "full", "left_out": left}, {"history": "full"})
    row = next(x for x in c["rows"] if x["key"] == "household_total" and x["reading"] == "change")
    assert row["a"] is None and row["b"] and row["same_measure"]
    chart = next(x for x in _charts(out).values() if "Total: change over" in x)
    assert "not read under these settings" in chart and chart.count('prstDash val="sysDash"') == 2
    assert "areaChart" not in chart                                   # no normal range of its own to shade
    assert _holds_together_in_excel(out) > 0
