"""Summary's vintage chart, and its grey rows (the firm, 3 Oct 2026).

The chart. The firm: *"Could the summary tab have vintage graphs as well? Showing our primary targeted info, maybe an
option for average booked, amount booked, basically whatever is there except graphed out"*; chosen: *"Pocket vs rest
vs book"*. Under the Summary table: origination year across the bottom, a Vintage measure dropdown offering every
Summary column, and a Vintage row dropdown picking one row of the column Summary shows (the pocket). Three lines, per
origination year: that row, the rest of the book (every loan in the view not in that row), and the whole book.
Summary's "Only loans where" applies to all three, as it does to the table.

Every number is worked out in the Run (`vintage`, called from engine.run, by engine.summary_rows, so a point is the
same arithmetic as a Summary row on the loans made that year) and put on _views; the tab's cells only pick them, so
the dropdowns redraw the chart live, as Compare's do. A point on a line with fewer loans that year than the Run's
Fewest loans in a pocket is #N/A, so it is not drawn; the table under the chart still shows it, in grey. A book with no
column marked Origination date gets one plain sentence where the chart would be.

A scatter with lines, as Compare's: a point at #N/A is left off in Excel and LibreOffice alike (LibreOffice draws a
line chart's #N/A at zero). Its x is the year itself, so the axis reads the years with no labels drawn by hand.

The grey rows. The firm: *"make the really low unit counts grayed out to a degree... so it's easier to spot quick
trends and not look left at the unit count. However this count should be separately adjustable from all other config
items - no dependencies just a simple number for this view specifically"*. A number typed at the top of Summary
("Grey rows under [50] loans"), read by one conditional format: every Summary row whose Loans is below it reads in
light grey. A plain number in a cell: nothing on Control, Fewest loans or the cube config reads it or feeds it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from types import SimpleNamespace

from openpyxl.chart import Reference, ScatterChart, Series
from openpyxl.chart.data_source import StrRef
from openpyxl.chart.legend import Legend
from openpyxl.chart.series import SeriesLabel
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties
from openpyxl.styles import Font

from . import engine, house, live

# --------------------------------------------------------------------------
# The Run's part: every point, worked out from the loans

SAY_NO_DATE = ("No vintage chart: no column in this extract is marked Origination date on Columns, so there are no "
               "years to draw across.")
SAY_NOT_IN = "No vintage chart: {col} is marked Origination date, but it isn't in this extract."
SAY_UNREAD = "No vintage chart: {why}."
SAY_NO_YEARS = "No vintage chart: no loan has a readable date in {col}."
#: the label the rest of the book carries while its row is worked out (never shown)
_REST = "\x00rest"


@dataclass
class Vintage:
    """Every point of Summary's vintage chart. `years` across the bottom, in order; `said` the one sentence shown
    instead of the chart when there is none (no Origination date, or no year read from it). `keys` are Summary's
    columns, in order. For each Summary view (the keys of Result.summaries): `book` the whole view's values, and
    `rows` each Summary row's (pocket, rest) values, in the order Summary lists the rows (All left off). Each is one
    flat list, column after column, a year after a year: the value of column k (from 0) in year y (from 0) is at
    k * len(years) + y; None where there is nothing to show."""
    years: list[str] = field(default_factory=list)
    said: str | None = None
    keys: list[str] = field(default_factory=list)
    book: dict[tuple, list] = field(default_factory=dict)
    rows: dict[tuple, list[tuple[list, list]]] = field(default_factory=dict)


def vintage(config, table, measures, per_row, labels_of: dict[str, list], booked, summaries: dict, rows_of: dict,
            total, book_size) -> Vintage:
    """The vintage chart's points, for every Summary view. `labels_of` is each Summary column's label per loan (a
    band column's band, a category's value), `rows_of` each filtered view's loans (keyed as Result.summaries is,
    after the column's name), `booked` each loan's booked amount (None without one)."""
    col = config.origination_date
    if not col:
        return Vintage(said=SAY_NO_DATE)
    if col not in table.columns:
        return Vintage(said=SAY_NOT_IN.format(col=col))
    try:
        years_of = engine.origination_years(table, col)
    except engine.DataRefused as exc:
        return Vintage(said=SAY_UNREAD.format(why=str(exc).rstrip(".")))
    years = sorted({y for y in years_of if y != engine.NO_DATE}, key=int)
    if not years:
        return Vintage(said=SAY_NO_YEARS.format(col=col))
    n = len(years_of)
    keys = engine.summary_columns(SimpleNamespace(measures=measures, summaries=summaries))
    out = Vintage(years=years, keys=keys)
    for key, whole in summaries.items():
        band, view = key[0], key[1:]
        idx = range(n) if all(v is None for v in view) else rows_of[view]
        labels = [x for x in whole.labels if x != engine.ALL]
        book = [None] * (len(keys) * len(years))
        rows = [([None] * len(book), [None] * len(book)) for _ in labels]
        for y, s in enumerate(_by_year(band, measures, per_row, labels_of[band], booked, labels, idx, years_of,
                                       years)):
            if s is None:
                continue
            _put(book, y, len(years), keys, _rows(key, s, measures, total, book_size)[-1][1])
            for j, lab in enumerate(labels):
                pocket, rest = _rows(key, _against_rest(s, lab, measures), measures, total, book_size)[:2]
                _put(rows[j][0], y, len(years), keys, pocket[1])
                _put(rows[j][1], y, len(years), keys, rest[1])
        out.book[key], out.rows[key] = book, rows
    return out


def _by_year(band: str, measures, per_row, labels_of: list, booked, labels: list[str], idx, years_of: list[str],
             years: list[str]) -> list:
    """One Summary of the column per year, on the loans at `idx` made that year (None for a year with none), as
    engine._summary builds one: each row's cell and booked dollars, then All. One pass over the loans, every row and
    year at once, rather than a pass per year and row."""
    want = set(years)
    sub = [i for i in idx if years_of[i] in want]
    cells = engine._accumulate(measures, {m: [vals[i] for i in sub] for m, vals in per_row.items()},
                               [(labels_of[i], years_of[i]) for i in sub])
    money: dict[tuple, list[float]] = {}
    if booked is not None:
        for i in sub:
            if booked[i] is not None:
                money.setdefault((labels_of[i], years_of[i]), []).append(booked[i])
    out = []
    for y in years:
        if not any((lab, y) in cells for lab in labels):
            out.append(None)
            continue
        got = {lab: cells.get((lab, y)) or engine._merge([], measures) for lab in labels}
        for c in got.values():
            engine._finish_cell(c, measures)
        got[engine.ALL] = engine._merge(list(got.values()), measures)
        dollars, under = {}, {}
        if booked is not None:
            for lab in labels:
                xs = money.get((lab, y), [])
                dollars[lab], under[lab] = math.fsum(xs), len(xs)
            every = [x for lab in labels for x in money.get((lab, y), [])]
            dollars[engine.ALL], under[engine.ALL] = math.fsum(every), len(every)
        out.append(engine.Summary(band=band, labels=labels + [engine.ALL], cells=got, booked=dollars,
                                  booked_loans=under))
    return out


def _against_rest(s, lab: str, measures):
    """A Summary of three rows: `lab`, every other loan of `s` together, and All, so that engine.summary_rows works
    out the pocket and the rest of the book by the same arithmetic as a Summary row, shares of the year's loans."""
    others = [x for x in s.labels if x not in (lab, engine.ALL)]
    cells = {lab: s.cells[lab], _REST: engine._merge([s.cells[x] for x in others], measures),
             engine.ALL: s.cells[engine.ALL]}
    booked, under = {}, {}
    if s.booked:
        booked = {lab: s.booked[lab], _REST: math.fsum(s.booked[x] for x in others), engine.ALL: s.booked[engine.ALL]}
        under = {lab: s.booked_loans[lab], _REST: sum(s.booked_loans[x] for x in others),
                 engine.ALL: s.booked_loans[engine.ALL]}
    return engine.Summary(band=s.band, labels=[lab, _REST, engine.ALL], cells=cells, booked=booked, booked_loans=under)


def _rows(key: tuple, s, measures, total, book_size):
    """engine.summary_rows over one Summary `s`, keyed as Result.summaries is: × book is against the whole book."""
    res = SimpleNamespace(summaries={key: s}, measures=measures, total=total, book_size=book_size)
    return engine.summary_rows(res, *key)


def _put(flat: list, y: int, ny: int, keys: list[str], vals: dict) -> None:
    for k, name in enumerate(keys):
        flat[k * ny + y] = vals.get(name)


# --------------------------------------------------------------------------
# The workbook's part

GREY_LABEL = "Grey rows under"
GREY_DEFAULT = 50
GREY_AFTER = "loans"
#: where the number sits: row 2, between the title band and the note, in the first data column (C2)
GREY_ROW = 2

HEADING = "Vintage: one row against the rest of the book, by origination year"
MEASURE = "Vintage measure"
ROW = "Vintage row"
POCKET_HUE, REST_HUE = "2A78D6", "EB6834"          # Compare's first two hues; the whole book dashed grey, as there
REST_LINE = "Rest of the book"
BOOK_LINE = "Whole book"
CHART_ROWS = 21                     # rows the chart covers (11 cm at 15 pt a row), so its table starts under it
#: a share or a rate is drawn in per cent (7.12, not 0.0712): the chart's axis can't take its format from a dropdown,
#: so every measure is drawn on one plain number format and the caption says per cent
PER_CENT = ("share", "pct")
AXIS_FMT = "#,##0.0#"
TABLE_HEADS = ("Year", None, "Loans", REST_LINE, "Loans", BOOK_LINE, "Loans")


def note_words(res) -> str:
    """Summary's note line for the vintage block: where it is, or the sentence saying why there is none."""
    v = getattr(res, "vintage", None)
    if v is None or v.said is not None:
        return v.said if v is not None else SAY_NO_DATE
    return ("Under the table: one row against the rest of the book and the whole book, by the year each loan was made "
            f"({res.config.origination_date}).")


def grey_input(ws, left: int) -> str:
    """Grey rows under [50] loans, at the top of Summary: the label, the number (an answer that changes the tab now)
    and "loans". Returns the number's absolute address."""
    from .results import _cell
    _cell(ws, GREY_ROW, left, GREY_LABEL, bold=True, size=9, color=house.SLATE, h="right", name="Arial")
    x = ws.cell(row=GREY_ROW, column=left + 1, value=GREY_DEFAULT)
    house.changes_now(x)
    x.number_format = "#,##0"
    _cell(ws, GREY_ROW, left + 2, GREY_AFTER, size=9, color=house.SLATE, h="left")
    ws.row_dimensions[GREY_ROW].height = 18
    from .results import col
    return f"${col(left + 1)}${GREY_ROW}"


def typed_grey(wb) -> float | None:
    """The number the analyst typed in Grey rows under, read before a Run rewrites Summary, so the next Run keeps it
    (the firm, 2 Oct 2026: "separately adjustable from all other config items"). None when there is none to keep."""
    from .results import SUMMARY
    if SUMMARY not in wb.sheetnames:
        return None
    ws = wb[SUMMARY]
    for c in ws[GREY_ROW]:
        if c.value == GREY_LABEL:
            v = ws.cell(row=GREY_ROW, column=c.column + 1).value
            return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None
    return None


def keep_grey(wb, v: float | None) -> None:
    """Put the analyst's Grey rows under number back after the Run wrote Summary with the default."""
    from .results import SUMMARY
    if v is None or SUMMARY not in wb.sheetnames:
        return
    ws = wb[SUMMARY]
    for c in ws[GREY_ROW]:
        if c.value == GREY_LABEL:
            ws.cell(row=GREY_ROW, column=c.column + 1).value = v
            return


def grey_rule(cut: str, loans: str) -> tuple:
    """The conditional format that greys a Summary row: its Loans (`loans`, the column fixed, the row free) below the
    number at `cut`. Light grey, never hidden. As a results.cf rule."""
    return (f"AND(ISNUMBER({cut}),ISNUMBER({loans}),{loans}<{cut})", None, Font(color=house.DISABLED_TEXT), None)


def vintage_views(res, views, bands: list[str], shown: list[str]) -> None:
    """Every vintage point on _views: "V|<column>|rows" (how many rows, then their labels), and for each view
    "V|<column><view>|book", "V|<column><view>|<i>" (row i, the pocket) and "V|<column><view>|<i>|rest"."""
    from .results import view_key
    v = getattr(res, "vintage", None)
    if v is None or v.said is not None:
        return
    opt_of = dict(zip(bands, shown))
    for b, opt in opt_of.items():
        labels = [x for x in res.summaries[(b, None, None, None)].labels if x != engine.ALL]
        views.put(f"V|{opt}|rows", [len(labels)] + labels)
    for key, book in v.book.items():
        if key[0] not in opt_of:
            continue
        pre = f"V|{opt_of[key[0]]}" + view_key(*key[1:])
        views.put(f"{pre}|book", book)
        for i, (pocket, rest) in enumerate(v.rows[key], start=1):
            views.put(f"{pre}|{i}", pocket)
            views.put(f"{pre}|{i}|rest", rest)


def write(ws, res, choices, views, *, got: dict, left: int, last: int, hid: int, top: int, B: str, VW: str,
          filters: list[tuple[str, str]]) -> None:
    """The vintage block on Summary, from row `top` (under the table, a row clear of it): a heading, what it is, the
    two dropdowns, a live caption, the chart and its points. `B` is Summary's column dropdown, `VW` the cell holding
    the view's key (the column and its filters), `filters` each (column name, dropdown cell) of Only loans where.
    The helper cells sit in hidden columns from `hid` + 2."""
    from .results import (_cell, _hide, cf, col, dropdown, fewest, match, pick, SUMMARY_FMT, SUMMARY_HEADS)
    v = getattr(res, "vintage", None)
    house.section(ws, top, left, last, HEADING)
    if v is None or v.said is not None:
        said = v.said if v is not None else SAY_NO_DATE
        _cell(ws, top + 1, left, said, size=10, h="left")
        return
    vintage_views(res, views, got["bands"], got["options"])
    keys, years = v.keys, v.years
    Y = len(years)
    few = fewest(res)
    oc = res.config.origination_date
    heads = [SUMMARY_HEADS[k][0] for k in keys]
    kinds = [SUMMARY_HEADS[k][1] for k in keys]
    scales = [100 if k in PER_CENT else 1 for k in kinds]
    words = (f"Pick a measure and one row of the column above. Its line is that row's loans; {REST_LINE} is every "
             f"other loan; the dashed grey line is all of them. Each point is the loans made that year ({oc}): the "
             f"same figure as the table above, on those loans only. A share is of that year's loans. × book is still "
             f"against the whole book. Loans with no readable date are left out. A rate or a share is drawn in per "
             f"cent.")
    if few is not None:
        words += (f" A point with fewer loans than the {few:,} in Fewest loans in a pocket on Control is left off its "
                  f"line; the table under the chart shows it in grey.")
    ws.merge_cells(start_row=top + 1, start_column=left, end_row=top + 1, end_column=last)
    _cell(ws, top + 1, left, words, size=9, color=house.SLATE, h="left", wrap=True)
    ws.row_dimensions[top + 1].height = 14 * 3 + 3
    s = top + 3                                     # the dropdowns; their labels on the row above
    m_rng, (k_rng, kind_rng, scale_rng) = choices.add("Summary: Vintage measure", heads, keys, kinds, scales)
    M = dropdown(ws, s, left, MEASURE, m_rng, heads[0])
    # the rows: the column picked's own labels, laid out in hidden cells as Summary's column dropdown changes
    H = hid + 2                                     # the picks worked out
    RL = H + 1                                      # the row labels, one a row from s
    most = max((len(r) for r in v.rows.values()), default=1)
    at = lambda k: f"${col(H)}${s + k}"             # noqa: E731
    RK, RN, MI, KIND, SCALE, I, NAME, FEW = (at(k) for k in range(8))
    PR, RR, BR = at(8), at(9), at(10)
    ws[RK.replace("$", "")] = "=" + match(f'"V|"&{B}&"|rows"')
    ws[RN.replace("$", "")] = f'=IF({RK}="",0,{pick(RK, 1)})'
    for i in range(1, most + 1):
        ws.cell(row=s + i - 1, column=RL, value=f'=IF({i}>{RN},"",{pick(RK, i + 1)})')
    rl = f"${col(RL)}${s}:${col(RL)}${s + most - 1}"
    first_label = next((x for x in res.summaries[(got["bands"][0], None, None, None)].labels if x != engine.ALL), "") \
        if got["bands"] else ""
    R = dropdown(ws, s, left + 1, ROW, f"OFFSET(${col(RL)}${s},0,0,MAX(1,{RN}),1)", first_label)
    ws.merge_cells(start_row=s, start_column=left + 1, end_row=s, end_column=left + 3)
    ws[MI.replace("$", "")] = f"=IFERROR(MATCH({M},{m_rng},0),1)"
    ws[KIND.replace("$", "")] = f"=INDEX({kind_rng},{MI})"
    ws[SCALE.replace("$", "")] = f"=INDEX({scale_rng},{MI})"
    # a row no longer in the column picked (the column dropdown changed): the first row, named in the caption
    ws[I.replace("$", "")] = f"=IFERROR(MATCH({R},{rl},0),1)"
    ws[NAME.replace("$", "")] = f"=INDEX({rl},{I})&\"\""
    ws[FEW.replace("$", "")] = few if few is not None else 0
    ws[PR.replace("$", "")] = "=" + match(f'"V|"&{VW}&"|"&{I}')
    ws[RR.replace("$", "")] = "=" + match(f'"V|"&{VW}&"|"&{I}&"|rest"')
    ws[BR.replace("$", "")] = "=" + match(f'"V|"&{VW}&"|book"')
    # the caption, live: what is drawn, on which loans
    where = "".join(f'&IF(OR({c}="",{c}="All loans"),"",{live.q(f" · only loans where {name} is ")}&{c})'
                    for name, c in filters)
    cap = s + 1
    ws.merge_cells(start_row=cap, start_column=left, end_row=cap, end_column=last)
    _cell(ws, cap, left, f'={M}&IF({SCALE}=100," (per cent)","")&" by origination year: "&{NAME}&", the rest of the '
                         f'book and the whole book"{where}', bold=True, size=10, h="left")
    # the helper block: per year, a row; per line, its value, its loans, the value drawn (or #N/A) and its x
    D0 = s + 1
    YC = H + 2                                      # the year, as a number
    lines = ((PR, "pocket"), (RR, "rest"), (BR, "book"))
    nloans = keys.index("loans")
    hc = {}
    for j, (row, _) in enumerate(lines):
        c = YC + 1 + 4 * j
        hc[j] = (c, c + 1, c + 2, c + 3)            # value, loans, drawn y, drawn x
    TITLES = D0 - 1
    for j, title in enumerate((f"={NAME}", live.q(REST_LINE), live.q(BOOK_LINE))):
        ws.cell(row=TITLES, column=hc[j][2], value=title if title.startswith("=") else f"={title}")
    for y, yr in enumerate(years):
        r = D0 + y
        ws.cell(row=r, column=YC, value=int(yr))
        for j, (row, _) in enumerate(lines):
            val, n_, dy, dx = hc[j]
            ws.cell(row=r, column=val, value=f"={pick(row, f'({MI}-1)*{Y}+{y + 1}')}")
            ws.cell(row=r, column=n_, value=f"={pick(row, nloans * Y + y + 1)}")
            V, N = f"{col(val)}{r}", f"{col(n_)}{r}"
            ws.cell(row=r, column=dy, value=f'=IF(OR(NOT(ISNUMBER({V})),NOT(ISNUMBER({N}))),NA(),'
                                            f'IF({N}<{FEW},NA(),{V}*{SCALE}))')
            ws.cell(row=r, column=dx, value=f"=IF(ISNUMBER({col(dy)}{r}),{col(YC)}{r},NA())")
    chart_at = cap + 1
    ws.add_chart(_chart(ws, years, D0, TITLES, hc), f"{col(left)}{chart_at + 1}")
    # the points, under the chart: what each line has each year, grey where it is left off
    t = chart_at + CHART_ROWS + 2
    for c, head in enumerate(TABLE_HEADS):
        x = _cell(ws, t, left + c, f"={NAME}" if head is None else head, bold=True, size=9, color=house.PAPER,
                  name="Arial", h="left" if c == 0 else "center", wrap=True)
        x.fill = house.fill(house.INK)
    ws.row_dimensions[t].height = 28
    fmts = {k: SUMMARY_FMT[k] for k in set(kinds)}
    for y, yr in enumerate(years):
        r = t + 1 + y
        _cell(ws, r, left, int(yr), h="left", indent=1, fmt="0")
        for j in range(3):
            val, n_, _, _ = hc[j]
            cv, cn = left + 1 + 2 * j, left + 2 + 2 * j
            _cell(ws, r, cv, f'=IF(ISNUMBER({col(val)}{D0 + y}),{col(val)}{D0 + y},"")', fmt="#,##0.00")
            _cell(ws, r, cn, f'=IF(ISNUMBER({col(n_)}{D0 + y}),{col(n_)}{D0 + y},"")', fmt="#,##0")
            thin = f"AND(ISNUMBER(${col(cn)}{r}),${col(cn)}{r}<{FEW})"
            grey = Font(color=house.DISABLED_TEXT)
            # each value's format follows the measure picked; a thin point's pair is grey (results.cf: LibreOffice
            # applies the first rule that holds, so each rule carries all a cell needs)
            rules = []
            for kind, fmt in fmts.items():
                rules.append((f'AND({thin},{KIND}="{kind}")', None, grey, fmt))
                rules.append((f'{KIND}="{kind}"', None, None, fmt))
            cf(ws, f"{col(cv)}{r}", rules)
            cf(ws, f"{col(cn)}{r}", [(thin, None, grey, None)])
        ws.row_dimensions[r].height = 16
    _hide(ws, H, hc[2][3])


def _chart(ws, years: list[str], D0: int, TITLES: int, hc: dict) -> ScatterChart:
    """The three lines: the row picked, the rest of the book, the whole book dashed grey; the years across."""
    from .results import SUMMARY, col
    ch = ScatterChart()
    ch.scatterStyle = "lineMarker"
    ref = lambda c: Reference(ws, min_col=c, min_row=D0, max_row=D0 + len(years) - 1)     # noqa: E731
    for j, hue in enumerate((POCKET_HUE, REST_HUE, None)):
        _, _, dy, dx = hc[j]
        ser = Series(ref(dy), ref(dx))
        ser.tx = SeriesLabel(strRef=StrRef(f"'{SUMMARY}'!${col(dy)}${TITLES}"))
        ser.smooth = False
        ln = ser.graphicalProperties.line
        if hue is None:
            ln.solidFill, ln.prstDash, ln.width = house.SLATE, "dash", 19050
            ser.marker.symbol = "none"
        else:
            ln.solidFill, ln.width = hue, 22225
            ser.marker.symbol = "circle"
            ser.marker.size = 6
            ser.marker.graphicalProperties = GraphicalProperties(solidFill=hue)
            ser.marker.graphicalProperties.line.solidFill = house.PAPER
        ch.series.append(ser)
    ch.legend = Legend()
    ch.legend.position = "b"
    ch.display_blanks = "gap"
    ch.visible_cells_only = False                   # the helper block sits in hidden columns
    ch.y_axis.number_format = AXIS_FMT
    ch.y_axis.majorGridlines.spPr = GraphicalProperties(ln=LineProperties(solidFill=house.ROW_RULE))
    ch.x_axis.majorGridlines = None
    # the years themselves at the ends, so the ticks fall on whole years; one year alone, a year either side of it
    first, last_ = int(years[0]), int(years[-1])
    ch.x_axis.scaling.min = first if last_ > first else first - 1
    ch.x_axis.scaling.max = last_ if last_ > first else last_ + 1
    ch.x_axis.majorUnit = 1
    ch.x_axis.number_format = "0"
    ch.x_axis.delete = False
    ch.y_axis.delete = False
    ch.width, ch.height = 26, 11
    return ch
