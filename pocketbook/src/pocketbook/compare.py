"""The Compare tab: the filters' values as lines across one band column's bands, in small charts side by side.

The firm, 30 Sep 2026: *"can we make it so they can be visually compared in a graph? Like if we used origination
date as a filter it would essentially be vintage years"*, with lines (one per value) across FICO bands; then *"if we
are proving things exist across categories it should not be vintage analysis only so let's make sure that is the
case and how would we show that say vintage analysis mixed with like underwriter/system approved?"*

So the lines are by either filter picked in the launcher (Filter 1 or Filter 2), and the panels by the other one, or
none. Every number is worked out in the Run (engine.summaries, the same cells Summary shows) and put on _views; the
tab's formulas only pick them, as every result tab's do, so the dropdowns redraw the charts live.

How the charts are built, so they work alike in Excel and LibreOffice:
- Each chart's series read a hidden helper block on this tab whose cells change with the dropdowns (as Look's live
  charts do). A point whose cell has fewer loans than the Run's fewest loans is #N/A there, so it is not drawn.
- One scale for every panel, live. A chart's axis bounds can't be set by formula, and bounds fixed at write time
  could not follow the Measure dropdown (a bad-loan rate near 10% and RANR near -2% can't share fixed bounds). So
  every panel carries one more, invisible series: the smallest and the largest value plotted in ANY panel for what
  is picked now. Each chart scales itself to take in those two points, the same two in every panel, so every panel
  lands on the same axis, whatever is picked. The trade-off: the bounds are the programs' own rounding of that
  range, not numbers we choose.
"""

from __future__ import annotations

from openpyxl.chart import LineChart, Reference, Series
from openpyxl.chart.data_source import StrRef
from openpyxl.chart.legend import Legend, LegendEntry
from openpyxl.chart.series import SeriesLabel
from openpyxl.styles import Font

from . import engine, house, live
from .choices import ORIG_YEAR
from .results import (ALL_LOANS, CANVAS, KEYS, Choices, Views, _cell, _fit, _hide, _widths, col, dropdown, fewest,
                      match, pick, plain, rates, view_key, xk, YEAR_SAID)

SHEET = "Compare"
#: the rows that aren't bands on the x axis: loans the column couldn't place
SPECIAL = {engine.BLANK_LABEL, engine.NOT_NUMBER_LABEL, engine.MISSING_RULE_LABEL, engine.NO_DATE}
NONE = "None"
BOOK_LINE = "Whole book"
#: one hue per line, in a fixed order, never cycled (the reference palette, validated for colour-blind readers); the
#: whole book is a dashed grey line of its own
HUES = ("2A78D6", "EB6834", "1BAF7A", "EDA100", "E87BA4", "008300", "4A3AA7", "E34948")
PANEL_COLS = 6              # columns a panel's chart spans
CHART_ROWS = 17             # rows it covers
DATA_W = 11                 # the width of every column but the first
SAY_THIN = "A point with fewer loans than the {few:,} in Fewest loans in a pocket on Control is left off its line."
SAY_SAME = "Panels by is the filter the lines are by, so one chart is drawn. Pick the other filter, or None."
SAY_READ = "If the lines have the same shape in every panel, the pattern holds across both categories."


def band_options(res) -> tuple[list[str], list[str]]:
    """Every band column the Run cut (engine name) and how the dropdown names it: its column, as Summary does."""
    from . import book as bk
    names = bk._names(res)
    bands = [b.name for b in res.config.bands if (b.name, None, None) in res.summaries]
    shown = [names[b] for b in bands]
    return bands, [x if shown.count(x) == 1 else f"{x} ({b})" for x, b in zip(shown, bands)]


def band_labels(res, band: str) -> list[str]:
    """The bands of one column in order: the x axis. The loans it couldn't place and All are left off."""
    return [x for x in res.summaries[(band, None, None)].labels if x != engine.ALL and x not in SPECIAL]


def points(res, band: str, measure: str, v1: str | None, v2: str | None) -> list[tuple[float | None, int]]:
    """Each band's (rate, loans) on the loans with Filter 1 = v1 and Filter 2 = v2 (None: All loans), as _views holds
    them: (None, 0) where the view has no loans."""
    s = res.summaries.get((band, v1, v2))
    out = []
    for lab in band_labels(res, band):
        c = s.cells.get(lab) if s is not None else None
        out.append((c.rates[measure].rate, c.rows) if c is not None and c.rows else (None, 0))
    return out


def compare_views(res, views: Views) -> dict:
    """Every Compare view on _views: "C|<band column>|labels", then for every filtered view (and the whole book) the
    loans in each band ("C|<band column>|loans<view>") and each rate ("C|<band column>|<measure><view>")."""
    bands, shown = band_options(res)
    ms = rates(res)
    most = 2
    for b, opt in zip(bands, shown):
        labels = band_labels(res, b)
        most = max(most, len(labels))
        views.put(f"C|{opt}|labels", labels)
        for (bb, v1, v2) in [k for k in res.summaries if k[0] == b]:
            key = view_key(v1, v2)
            got = {m.name: points(res, b, m.name, v1, v2) for m in ms}
            views.put(f"C|{opt}|loans{key}", [n for _, n in got[ms[0].name]] if ms else [])
            for m in ms:
                views.put(f"C|{opt}|{m.name}{key}", [r for r, _ in got[m.name]])
    return {"options": shown, "most": most, "measures": ms}


def write_compare(wb, res, choices: Choices, views: Views) -> None:
    """Compare (after Summary): pickers for the band column, the measure, what the lines are by and what the panels
    are by; one small chart per panel, side by side on one scale; and under them every point's rate and loans."""
    sf, sf2 = res.config.filter_by, (res.config.filter_by2 if res.filter_values2 else None)
    if not (sf and res.filter_values):
        return
    got = compare_views(res, views)
    ms, MB = got["measures"], got["most"]
    vals1, vals2 = list(res.filter_values), list(res.filter_values2) if sf2 else []
    L = max(len(vals1), len(vals2))                         # line slots
    P = max(len(vals1), len(vals2)) if sf2 else 1          # panel slots
    few = fewest(res)
    ws = wb.create_sheet(SHEET)
    left = 2
    table_w = 1 + 2 * (L + 1)
    last = max(left + P * PANEL_COLS - 1, left + table_w - 1, left + 18)
    S0 = last + 3                                           # hidden: the picks worked out, then the helper block
    HB = S0 + 6
    CATC, PH, HS = HB, HB + 1, HB + 2
    n_series = P * (L + 1)

    def scol(p: int, j: int, clean: bool = False) -> int:
        """The helper column of panel p's line j (0 the whole book)."""
        return HS + (p - 1) * (L + 1) + j + (n_series if clean else 0)
    lw = house.fit([str(x) for b, _ in zip(*band_options(res)) for x in band_labels(res, b)] + ["Whole book"],
                   floor=12, cap=28, pad=3)
    _widths(ws, {1: 2, left: lw, **{c: DATA_W for c in range(left + 1, S0)}})
    house.title_band(ws, SHEET, "The filters' values as lines across the bands, side by side on one scale.", left,
                     last, tab=house.TAB_RESULT)
    note = [
        ("What it is", "Pick a band column and a measure. Each line is one value of the filter picked in Lines by, "
                       "across the bands. The dashed grey line is the whole book."),
        ("Panels", ("Panels by draws one small chart for each value of the other filter, side by side. Every panel "
                    "has the same scale, so higher in one panel is higher in all.") if sf2 else
                   "Pick a second filter in the launcher (Filter 2) to draw one small chart for each of its values."),
        ("Thin points", (SAY_THIN.format(few=few) if few is not None else "Every point is drawn.")
                        + " The table under the charts still shows it, in grey."),
        ("Reading it", SAY_READ + " Nothing here is tested. As of the last Run."),
    ]
    if ORIG_YEAR in (sf, sf2):
        note.append(("Years", YEAR_SAID.format(res.config.origination_date).strip()))
    r = house.method_note(ws, 3, left, last, note)
    bands_opt = got["options"]
    opt1, opt2 = f"Filter 1: {sf}", (f"Filter 2: {sf2}" if sf2 else None)
    lines_opts = [opt1] + ([opt2] if sf2 else [])
    panel_opts = [NONE] + lines_opts
    b_rng, _ = choices.add("Compare: Band column", bands_opt)
    m_rng, (k_rng,) = choices.add("Compare: Measure", [plain(m) for m in ms], [m.name for m in ms])
    l_rng, _ = choices.add("Compare: Lines by", lines_opts)
    p_rng, _ = choices.add("Compare: Panels by", panel_opts)
    y_rng, _ = choices.add("Compare: Whole book line", ["Yes", "No"])
    s = r + 1
    B = dropdown(ws, s, left, "Band column", b_rng, bands_opt[0] if bands_opt else "")
    M = dropdown(ws, s, left + 3, "Measure", m_rng, plain(ms[0]) if ms else "")
    LB_ = dropdown(ws, s, left + 6, "Lines by", l_rng, opt1)
    PB_ = dropdown(ws, s, left + 9, "Panels by", p_rng, opt2 or NONE)
    Y = dropdown(ws, s, left + 12, "Whole book line", y_rng, "Yes")
    for c0 in (left, left + 3, left + 6, left + 9, left + 12):
        ws.merge_cells(start_row=s, start_column=c0, end_row=s, end_column=c0 + 1)
    # the picks, worked out once in hidden cells
    hr = s
    at = lambda c, k: f"${col(c)}${hr + k}"                   # noqa: E731
    LB, PB, BAND, MKEY, FEW, SHOW, LABR = (at(S0, k) for k in range(7))
    q2 = live.q(opt2) if opt2 else '""'
    f = {LB: f'IF({LB_}={q2},2,1)',
         PB: f'IF(OR({PB_}="",{PB_}="{NONE}"),0,IF({PB_}={live.q(opt1)},IF({LB}=1,0,1),IF({LB}=2,0,2)))',
         BAND: f"{B}&\"\"", MKEY: f'IFERROR(INDEX({k_rng},MATCH({M},{m_rng},0)),"")',
         SHOW: f'{Y}="Yes"', LABR: match(xk("C|", (BAND,), "|labels"))}
    for cell, x in f.items():
        ws[cell.replace("$", "")] = f"={x}"
    ws[FEW.replace("$", "")] = few if few is not None else 0
    for i in range(max(len(vals1), len(vals2), 1)):
        ws.cell(row=hr + i, column=S0 + 4, value=str(vals1[i]) if i < len(vals1) else None)
        ws.cell(row=hr + i, column=S0 + 5, value=str(vals2[i]) if i < len(vals2) else None)
    V1 = lambda i: f"${col(S0 + 4)}${hr + i - 1}"            # noqa: E731
    V2 = lambda i: f"${col(S0 + 5)}${hr + i - 1}"            # noqa: E731
    LV = lambda j: f"${col(S0 + 1)}${hr + j - 1}"            # noqa: E731
    PV = lambda p: f"${col(S0 + 2)}${hr + p - 1}"            # noqa: E731
    USED = lambda p: f"${col(S0 + 3)}${hr + p - 1}"          # noqa: E731
    for j in range(1, L + 1):
        ws[LV(j).replace("$", "")] = f'=IF({LB}=1,{V1(j)}&"",{V2(j)}&"")'
    for p in range(1, P + 1):
        ws[PV(p).replace("$", "")] = f'=IF({PB}=0,"",IF({PB}=1,{V1(p)}&"",{V2(p)}&""))'
        ws[USED(p).replace("$", "")] = f'=IF({PB}=0,{p}=1,{PV(p)}<>"")'
    # the helper block: two key rows (the rate's _views row, the loans'), the series' names, then one row per band
    R_RATE, R_LOANS, R_TITLE, DR = hr, hr + 1, hr + 2, hr + 3
    rows_ = range(DR, DR + MB)
    for i, rr in enumerate(rows_, start=1):
        ws.cell(row=rr, column=CATC, value=f"={pick(LABR, i)}")
    for p in range(1, P + 1):
        for j in range(0, L + 1):
            c = scol(p, j)
            if j == 0:                                  # the whole book, in every panel drawn
                on = f"AND({USED(p)},{SHOW})"
                sfx, title = "", live.q(BOOK_LINE)
            else:
                on = f'AND({USED(p)},{LV(j)}<>"")'
                v1 = f"IF({LB}=1,{LV(j)},{PV(p)})"
                v2 = f"IF({LB}=1,{PV(p)},{LV(j)})"
                sfx = (f'&IF({v1}="","",{live.q("|where ")}&{v1})'
                       f'&IF({v2}="","",{live.q("|and ")}&{v2})')
                title = LV(j)
            rk = f'"C|"&{BAND}&"|"&{MKEY}{sfx}'
            lk = f'"C|"&{BAND}&"|loans"{sfx}'
            ws.cell(row=R_RATE, column=c, value=f'=IF({on},{match(rk)},"")')
            ws.cell(row=R_LOANS, column=c, value=f'=IF({on},{match(lk)},"")')
            ws.cell(row=R_TITLE, column=c, value=f'=IF({col(c)}{R_RATE}="","",{title})')
            RR, RL = f"${col(c)}${R_RATE}", f"${col(c)}${R_LOANS}"
            for i, rr in enumerate(rows_, start=1):
                rate, loans = pick(RR, i), pick(RL, i)
                # left off the line: no rate, or fewer loans than the Run's fewest (the Grids' grey rule)
                ws.cell(row=rr, column=c, value=f"=IF(OR({rate}=\"\",NOT(ISNUMBER({loans}))),NA(),"
                                                f"IF({loans}<{FEW},NA(),{rate}))")
                ws.cell(row=rr, column=scol(p, j, True), value=f'=IF(ISNUMBER({col(c)}{rr}),{col(c)}{rr},"")')
    clean = f"${col(scol(1, 0, True))}${DR}:${col(scol(P, L, True))}${DR + MB - 1}"
    # one scale for every panel: the smallest and largest value drawn anywhere, as an invisible series in each
    for i, rr in enumerate(rows_, start=1):
        ws.cell(row=rr, column=PH, value=f"=IF(COUNT({clean})=0,NA(),MIN({clean}))" if i == 1 else
                f"=IF(COUNT({clean})=0,NA(),MAX({clean}))" if i == 2 else "=NA()")
    status = s + 1
    _cell(ws, status, left, f'=IF(AND({PB_}<>"{NONE}",{PB}=0),{live.q(SAY_SAME)},"")', size=9,
          color=house.CRIMSON, h="left")
    top = status + 2
    pb_name = f'IF({PB}=1,{live.q(sf)},{live.q(sf2 or "")})'
    for p in range(1, P + 1):
        c0 = left + (p - 1) * PANEL_COLS
        _cell(ws, top, c0, f'=IF({USED(p)},IF({PB}=0,"All loans",{pb_name}&" is "&{PV(p)}),"")', bold=True,
              h="left", name="Arial")
        ws.merge_cells(start_row=top, start_column=c0, end_row=top, end_column=c0 + PANEL_COLS - 1)
        ws.add_chart(_chart(ws, p, L, MB, DR, CATC, PH, scol, R_TITLE), f"{col(c0)}{top + 1}")
    _cell(ws, top + CHART_ROWS + 1, left, f'="Band column: "&{B}&" · "&{M}&" · lines by "&IF({LB}=1,'
          f'{live.q(sf)},{live.q(sf2 or "")})&". "&' + live.q(SAY_READ), size=9, color=house.SLATE, h="left")
    r = top + CHART_ROWS + 3
    for p in range(1, P + 1):
        r = _table(ws, r, left, p, L, MB, USED(p), PV(p), PB, pb_name, B, FEW, CATC, DR, scol, R_TITLE, R_RATE,
                   R_LOANS) + 1
    _hide(ws, S0, scol(P, L, True))
    ws.freeze_panes = f"A{s + 1}"
    _fit(ws)


def _chart(ws, p: int, L: int, MB: int, DR: int, CATC: int, PH: int, scol, R_TITLE: int) -> LineChart:
    """Panel p: its lines, the whole book dashed, and the invisible series that gives every panel one scale."""
    ch = LineChart()
    cats = Reference(ws, min_col=CATC, min_row=DR, max_row=DR + MB - 1)
    for j in range(0, L + 1):
        c = scol(p, j)
        ser = Series(Reference(ws, min_col=c, min_row=DR, max_row=DR + MB - 1))
        ser.tx = SeriesLabel(strRef=StrRef(f"'{SHEET}'!${col(c)}${R_TITLE}"))
        ser.smooth = False
        ln = ser.graphicalProperties.line
        if j == 0:
            ln.solidFill, ln.dashStyle, ln.width = house.SLATE, "dash", 19050
            ser.marker.symbol = "none"
        else:
            hue = HUES[(j - 1) % len(HUES)]
            ln.solidFill, ln.width = hue, 22225
            ser.marker.symbol = "circle"
            ser.marker.size = 6
            ser.marker.graphicalProperties.solidFill = hue
            ser.marker.graphicalProperties.line.solidFill = house.PAPER
        ch.series.append(ser)
    ph = Series(Reference(ws, min_col=PH, min_row=DR, max_row=DR + MB - 1))
    ph.graphicalProperties.line.noFill = True
    ph.marker.symbol = "none"
    ph.smooth = False
    ch.series.append(ph)
    ch.set_categories(cats)
    ch.legend = Legend(position="b", legendEntry=[LegendEntry(idx=L + 1, delete=True)])
    ch.display_blanks = "gap"
    ch.y_axis.number_format = "0.0%"
    ch.y_axis.majorGridlines.spPr = None
    ch.x_axis.delete = ch.y_axis.delete = False
    ch.width, ch.height = PANEL_COLS * 2.05, 8.2
    return ch


def _table(ws, r: int, left: int, p: int, L: int, MB: int, USED: str, PV: str, PB: str, pb_name: str, B: str,
           FEW: str, CATC: int, DR: int, scol, R_TITLE: int, R_RATE: int, R_LOANS: int) -> int:
    """Panel p's points: the band down the side; for the whole book and each line, the rate and the loans. A point
    left off its line is grey here, as a thin pocket is on Grids. Returns the row under it."""
    _cell(ws, r, left, f'=IF({USED},IF({PB}=0,"All loans",{pb_name}&" is "&{PV}),"")', bold=True, h="left",
          name="Arial", color=house.PAPER).fill = house.fill(house.INK)
    for c in range(left + 1, left + 1 + 2 * (L + 1)):
        ws.cell(row=r, column=c).fill = house.fill(house.INK)
    _cell(ws, r + 1, left, f"=IF({USED},{B},\"\")", bold=True, size=9, color=house.SLATE, h="left", indent=1)
    for j in range(0, L + 1):
        c = left + 1 + 2 * j
        t = f"${col(scol(p, j))}${R_TITLE}"
        _cell(ws, r, c, f"={t}", bold=True, size=9, color=house.PAPER, name="Arial")
        ws.merge_cells(start_row=r, start_column=c, end_row=r, end_column=c + 1)
        _cell(ws, r + 1, c, f'=IF({t}="","","Rate")', bold=True, size=9, color=house.SLATE)
        _cell(ws, r + 1, c + 1, f'=IF({t}="","","Loans")', bold=True, size=9, color=house.SLATE)
    for c in range(left, left + 1 + 2 * (L + 1)):
        ws.cell(row=r + 1, column=c).fill = house.fill(CANVAS)
    for i in range(1, MB + 1):
        rr = r + 1 + i
        _cell(ws, rr, left, f'=IF({USED},${col(CATC)}${DR + i - 1},"")', h="left", indent=1)
        for j in range(0, L + 1):
            c = left + 1 + 2 * j
            RR, RL = f"${col(scol(p, j))}${R_RATE}", f"${col(scol(p, j))}${R_LOANS}"
            _cell(ws, rr, c, f"={pick(RR, i)}", fmt="0.00%")
            _cell(ws, rr, c + 1, f"={pick(RL, i)}", fmt="#,##0")
            grey = f"AND(ISNUMBER({col(c + 1)}{rr}),{col(c + 1)}{rr}<{FEW})"
            from .results import cf
            cf(ws, f"{col(c)}{rr}:{col(c + 1)}{rr}", [(grey, None, Font(color=house.DISABLED_TEXT), None)])
        ws.row_dimensions[rr].height = 16
    return r + 2 + MB
