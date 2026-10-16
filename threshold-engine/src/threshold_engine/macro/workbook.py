"""The workbook the consumer and commercial teams read.

Made only from a finished rating run, so it cannot exist without the firm's
settings. Every number in it is a value written by Python; nothing is a
formula, so nothing moves after it is written. It follows the threshold
workbook's design (Claude Design's hand-off, 13 Oct 2026, in
keybank_style.py): titles on paper, canvas headers, and the same five rating
colours, as chips in the tables and as shaded bands behind every chart.

    Ratings      every national series by topic: its level and its change,
                 each rated, and the reading that stands out
    States       unemployment by state: level and change
    one per series   its ratings, where each rating starts, its history over
                 the five bands, what it is and where it comes from
    State data   every state's unemployment rate, month by month
    Not rated    only when something could not be rated, and why
    Glossary     every term, and how it is worked out
    Run          when it was built, from which pull, with which settings
    Sources      every file: address, licence, when fetched, SHA-256
"""
import datetime

from .catalog import BY_KEY, DERIVED, HIGHER, RATED, SERIES, STATES
from .rate import changes, sahm
from .settings import QUESTIONS, readings_of

RATINGS = ("Low", "Moderate-Low", "Moderate", "Moderate-High", "High")

#: The Ratings tab's sections, in reading order, and each series' tab name.
TOPICS = [
    ("Jobs", ["unemployment", "initial_claims", "continuing_claims", "payrolls"]),
    ("Prices and insurance", ["cpi", "cpi_core", "gasoline", "motor_insurance", "used_cars", "home_insurance"]),
    ("Housing and household credit", ["house_prices", "house_price_to_income", "mortgage_rate", "mortgage_spread",
                                      "mortgage_30_89", "mortgage_90", "mortgage_90_government",
                                      "revolving_credit", "card_standards"]),
    ("Business and the economy", ["real_gdp", "industrial_production", "capacity_use", "cfnai", "cre_prices",
                                  "ci_standards", "ci_demand"]),
    ("Markets and financial conditions", ["gz_spread", "excess_bond_premium", "bond_recession_probability",
                                          "nfci", "nfci_adjusted", "stlfsi", "kcfsi", "yield_curve"]),
]
TAB = {
    "unemployment": "Unemployment", "initial_claims": "Initial claims", "continuing_claims": "Continuing claims",
    "payrolls": "Payrolls", "cpi": "Prices", "cpi_core": "Core prices", "gasoline": "Gasoline",
    "motor_insurance": "Motor insurance", "used_cars": "Used cars", "home_insurance": "Home insurance",
    "house_prices": "House prices", "house_price_to_income": "House prices to income",
    "mortgage_rate": "Mortgage rate", "mortgage_spread": "Mortgage spread", "mortgage_30_89": "Mortgages 30-89",
    "mortgage_90": "Mortgages 90+", "mortgage_90_government": "Gov mortgages 90+",
    "revolving_credit": "Revolving credit", "card_standards": "Card standards", "real_gdp": "Real GDP",
    "industrial_production": "Industrial production", "capacity_use": "Capacity use", "cfnai": "Activity index",
    "cre_prices": "CRE prices", "ci_standards": "Business loan standards", "ci_demand": "Business loan demand",
    "gz_spread": "Bond spread", "excess_bond_premium": "Excess bond premium",
    "bond_recession_probability": "Bond recession prob", "nfci": "NFCI", "nfci_adjusted": "NFCI adjusted",
    "stlfsi": "St Louis stress", "kcfsi": "Kansas City stress", "yield_curve": "Yield curve",
}


def label(r):
    return "%d %s" % (r, RATINGS[r - 1])


def reading_name(reading, months):
    return "Level" if reading == "position" else "Change over %d months" % months


def _date(d):
    return datetime.date.fromisoformat(d[:10])


def value_format(x):
    """Whole numbers with commas for big values; two decimals at most otherwise."""
    return "#,##0" if x is not None and abs(x) >= 1000 else "#,##0.0#"


def nice_axis(low, high):
    """Round an axis out to a tidy step, about five steps from bottom to top."""
    import math
    span = (high - low) or abs(high) or 1.0
    raw = span / 5
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    return math.floor(low / step) * step, math.ceil(high / step) * step, step


def band_heights(lines, direction, low, high):
    """The five stacked bands behind a chart, bottom up, from ``low`` to ``high``.

    Returns (base, heights, ratings): an invisible base at ``low``, then each
    band's height and the rating it shows. Where higher is worse, 1 Low is at
    the bottom; where lower is worse, 5 High is. A rating no reading reached
    has a band of no height."""
    worse_end = high if direction == HIGHER else low
    edge = {k: (lines[str(k)] if lines[str(k)] is not None else worse_end) for k in range(2, 6)}
    if direction == HIGHER:
        cuts, order = [low, edge[2], edge[3], edge[4], edge[5], high], [1, 2, 3, 4, 5]
    else:
        cuts, order = [low, edge[5], edge[4], edge[3], edge[2], high], [5, 4, 3, 2, 1]
    cuts = [min(max(c, low), high) for c in cuts]
    return low, [max(b - a, 0.0) for a, b in zip(cuts, cuts[1:])], order


def build(out, result, pull):
    """Write the workbook for one rating run (``rate_all``'s result) to ``out``."""
    from openpyxl import Workbook
    from openpyxl.chart import AreaChart, LineChart, Reference
    from openpyxl.chart.label import DataLabelList
    from openpyxl.chart.shapes import GraphicalProperties
    from openpyxl.chart.text import RichText
    from openpyxl.drawing.line import LineProperties
    from openpyxl.drawing.text import CharacterProperties, Paragraph, ParagraphProperties
    from openpyxl.styles import Alignment, Border, Font, Side
    from openpyxl.utils import get_column_letter as L

    from .. import VERSION
    from .. import keybank_style as K

    s = result["settings"]
    months = s["change_months"]
    vintage = result["vintage"]
    by_key = {}
    for r in result["ratings"]:
        by_key.setdefault(r["key"], {})[r["reading"]] = r
    items = {i.key: i for i in RATED}
    state_keys = {"unemployment_" + st.lower() for st in STATES}
    national = [k for _, keys in TOPICS for k in keys]

    F_DATA = Font(name="Calibri", size=11, color=K.INK_TEXT)
    F_NOTE = Font(name="Calibri", size=10, color=K.SLATE)
    F_LABEL = Font(name="Arial", size=9, bold=True, color=K.SLATE)
    F_LINK = Font(name="Calibri", size=11, color="1F4E79", underline="single")
    WRAP = Alignment(wrap_text=True, vertical="top")
    CENTER = Alignment(horizontal="center", vertical="center")

    def ln(hex_, width_pt=None, dash=None):
        lp = LineProperties(solidFill=hex_)
        if width_pt is not None:
            lp.w = int(width_pt * 12700)
        if dash:
            lp.prstDash = dash
        return lp

    def text(size=9, color=K.SLATE, bold=False):
        cp = CharacterProperties(sz=int(size * 100), b=bold, solidFill=color, latin=None)
        return RichText(p=[Paragraph(pPr=ParagraphProperties(defRPr=cp), endParaRPr=cp)])

    wb = Workbook()

    def sheet(title, first=False):
        ws = wb.active if first else wb.create_sheet()
        ws.title = title
        K.hide_gridlines(ws)
        ws.page_setup.orientation = "landscape"
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
        return ws

    def widths(ws, ws_widths, first=1):
        for i, w in enumerate(ws_widths, first):
            ws.column_dimensions[L(i)].width = w

    def chip(ws, row, col, r, size=9):
        c = ws.cell(row, col, label(r))
        c.font = Font(name="Arial", bold=True, size=size, color=K.INK)
        c.fill = K.solid(K.BANDS[r - 1])
        c.alignment = CENTER
        c.border = Border(left=Side(style="thin", color=K.PAPER), right=Side(style="thin", color=K.PAPER))
        return c

    def link(cell, sheet_name, text_=None):
        if text_ is not None:
            cell.value = text_
        cell.hyperlink = "#'%s'!A1" % sheet_name
        cell.font = F_LINK

    def note(ws, row, col, value, last_col):
        ws.merge_cells(start_row=row, start_column=col, end_row=row, end_column=last_col)
        c = ws.cell(row, col, value)
        c.font, c.alignment = F_NOTE, WRAP
        return c

    def standout(key):
        got = by_key.get(key, {})
        if not got:
            return None
        return max(got.values(), key=lambda r: (r["rating"], r["reading"] == "change"))

    # -- Ratings ----------------------------------------------------------
    ws = sheet("Ratings", first=True)
    widths(ws, [2.71, 46, 11, 12, 16, 12, 12, 16, 12, 11, 34, 90])
    row = K.light_title(ws, 1, 11, "Economic conditions",
                        "Public data, pulled %s. Each series against its own history: 1 Low to 5 High."
                        % vintage, first_col=2)
    row += 1
    every = [r for r in result["ratings"] if r["key"] not in state_keys]
    ws.cell(row, 2, "Readings at each rating, national series").font = F_LABEL
    short = {5: "5 High", 4: "4 Mod-High", 3: "3 Moderate", 2: "2 Mod-Low", 1: "1 Low"}
    for i, k in enumerate((5, 4, 3, 2, 1)):
        chip(ws, row, 5 + i, k).value = short[k]
        c = ws.cell(row + 1, 5 + i, sum(1 for r in every if r["rating"] == k))
        c.font, c.alignment = Font(name="Calibri", size=14, bold=True, color=K.INK_TEXT), CENTER
    ws.row_dimensions[row + 1].height = 21
    sahm_x = next(iter(result["alongside"]), None)
    if sahm_x:
        ws.cell(row + 2, 2, "Sahm reading").font = F_LABEL
        c = ws.cell(row + 2, 3, "%.2f in %s. Sahm's published trigger is 0.50; shown, not rated."
                    % (sahm_x["value"], _date(sahm_x["date"]).strftime("%b %Y")))
        c.font = F_DATA
    row += 4
    cut = s["cutoffs"]
    note(ws, row, 2, "Level: where the latest reading sits in the series' own history. Change: how its change over "
                     "%d months compares with every such change in that history. A rating of 2 starts at the "
                     "%gth percentile, 3 at the %gth, 4 at the %gth and 5 at the %gth. Click a series to open it."
                     % (months, cut[0], cut[1], cut[2], cut[3]), 12)
    ws.row_dimensions[row].height = 30
    row += 2
    cols = ["Series", "Latest", "Value", "Level", "Level percentile", "Change over %d months" % months,
            "Change", "Change percentile", "History from", "Unit", "What stands out"]
    for topic, keys in TOPICS:
        row = K.quiet_section(ws, row, topic, 11, first_col=2)
        row = K.canvas_header(ws, row, cols, first_col=2, right_from=None)
        for j in (5, 8):
            ws.cell(row - 1, j).alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        for j in (3, 4, 6, 7, 9, 10):
            ws.cell(row - 1, j).alignment = Alignment(wrap_text=True, vertical="center", horizontal="right")
        ranked = sorted(keys, key=lambda k: (-(standout(k) or {"rating": 0})["rating"], items[k].title))
        for key in ranked:
            got = by_key.get(key, {})
            lvl, chg, top = got.get("position"), got.get("change"), standout(key)
            link(ws.cell(row, 2), TAB[key], items[key].title)
            first = lvl or chg
            if first:
                ws.cell(row, 3, _date(first["date"])).number_format = "yyyy-mm-dd"
                ws.cell(row, 3).font = F_DATA
            ws.cell(row, 11, items[key].unit).font = F_NOTE
            if lvl:
                c = ws.cell(row, 4, lvl["value"])
                c.number_format, c.font = value_format(lvl["value"]), F_DATA
                chip(ws, row, 5, lvl["rating"])
                c = ws.cell(row, 6, lvl["percentile"] / 100)
                c.number_format, c.font = "0.0%", F_DATA
            elif items[key].position:
                c = ws.cell(row, 5, "change only")
                c.font, c.alignment = F_NOTE, CENTER
            if chg:
                c = ws.cell(row, 7, chg["value"])
                c.number_format = "+#,##0.0#%;-#,##0.0#%;0%" if items[key].change_in == "percent" else \
                    "+#,##0.0#;-#,##0.0#;0"
                if items[key].change_in == "percent":
                    c.value = chg["value"] / 100
                c.font = F_DATA
                chip(ws, row, 8, chg["rating"])
                c = ws.cell(row, 9, chg["percentile"] / 100)
                c.number_format, c.font = "0.0%", F_DATA
            if first:
                c = ws.cell(row, 10, _date(first["history_from"]))
                c.number_format, c.font = "yyyy-mm", F_DATA
            if top:
                c = ws.cell(row, 12, top["sentence"])
                c.font, c.alignment = F_NOTE, WRAP
            if not got:
                ws.cell(row, 12, "Not rated: see the Not rated tab").font = F_NOTE
            for j in range(2, 13):
                ws.cell(row, j).alignment = Alignment(vertical="center", wrap_text=j == 12,
                                                      horizontal=ws.cell(row, j).alignment.horizontal)
            ws.row_dimensions[row].height = 30
            K.hairlines(ws, row, 2, 12)
            row += 1
        row += 1
    ws.freeze_panes = "C3"

    # -- States -----------------------------------------------------------
    ws = sheet("States")
    widths(ws, [2.71, 8, 12, 14, 15, 11, 16, 15, 11, 11])
    row = K.light_title(ws, 1, 9, "Unemployment by state",
                        "BLS (LAUS), pulled %s. Each state against its own history, worst first." % vintage,
                        first_col=2)
    row += 1
    head = row
    row = K.canvas_header(ws, row, ["State", "Latest", "Unemployment rate", "Level", "Level percentile",
                                    "Change over %d months" % months, "Change", "Change percentile",
                                    "History from"], first_col=2)
    for j in (4, 6, 7, 9):
        ws.cell(head, j).alignment = Alignment(wrap_text=True, vertical="center", horizontal="right")

    def worst(st):
        got = by_key.get("unemployment_" + st.lower(), {})
        return -max([x["rating"] for x in got.values()] or [0])
    for st in sorted(STATES, key=lambda st: (worst(st), st)):
        got = by_key.get("unemployment_" + st.lower(), {})
        lvl, chg = got.get("position"), got.get("change")
        ws.cell(row, 2, st).font = F_DATA
        if lvl:
            c = ws.cell(row, 3, _date(lvl["date"]))
            c.number_format, c.font = "yyyy-mm", F_DATA
            c = ws.cell(row, 4, lvl["value"])
            c.number_format, c.font = "0.0", F_DATA
            chip(ws, row, 5, lvl["rating"])
            c = ws.cell(row, 6, lvl["percentile"] / 100)
            c.number_format, c.font = "0.0%", F_DATA
            c = ws.cell(row, 10, _date(lvl["history_from"]))
            c.number_format, c.font = "yyyy-mm", F_DATA
        if chg:
            c = ws.cell(row, 7, chg["value"])
            c.number_format, c.font = "+0.0;-0.0;0.0", F_DATA
            chip(ws, row, 8, chg["rating"])
            c = ws.cell(row, 9, chg["percentile"] / 100)
            c.number_format, c.font = "0.0%", F_DATA
        if not got:
            ws.cell(row, 3, "not in this pull").font = F_NOTE
        K.hairlines(ws, row, 2, 10)
        row += 1
    ws.freeze_panes = ws.cell(head + 1, 3)

    # -- one sheet per national series --------------------------------------
    def banded_chart(ws, title, unit, data_col, first, last, helper_col, r, frequency):
        """History line over the five rating bands, with the latest reading marked.

        The bands are the chart underneath and the lines are laid over them:
        LibreOffice draws in the order charts are combined, Excel draws areas
        first whatever the order, so this order reads the same in both."""
        area = AreaChart()
        area.grouping = "stacked"
        area.add_data(Reference(ws, min_col=helper_col, max_col=helper_col + 5, min_row=first - 1, max_row=last),
                      titles_from_data=True)
        area.set_categories(Reference(ws, min_col=14, min_row=first, max_row=last))
        area.series[0].graphicalProperties.noFill = True
        area.series[0].graphicalProperties.line.noFill = True
        for i, s_ in enumerate(area.series[1:]):
            s_.graphicalProperties.solidFill = K.BANDS[r["order"][i] - 1]
            s_.graphicalProperties.line.noFill = True
        line = LineChart()
        line.add_data(Reference(ws, min_col=data_col, min_row=first - 1, max_row=last), titles_from_data=True)
        hist = line.series[0]
        hist.graphicalProperties.line = ln(K.INK, 1.75)
        hist.marker.symbol = "none"
        hist.smooth = False
        latest = LineChart()
        latest.add_data(Reference(ws, min_col=helper_col + 6, min_row=first - 1, max_row=last), titles_from_data=True)
        pt = latest.series[0]
        pt.graphicalProperties.line.noFill = True
        pt.marker.symbol = "circle"
        pt.marker.size = 7
        pt.marker.graphicalProperties = GraphicalProperties(solidFill="FFFFFF", ln=ln(K.INK, 1.5))
        pt.dLbls = DataLabelList()
        pt.dLbls.showVal, pt.dLbls.showCatName, pt.dLbls.showSerName, pt.dLbls.showLegendKey = True, False, False, False
        pt.dLbls.position = "l"
        pt.dLbls.numFmt = "#,##0.0#"
        pt.dLbls.txPr = text(9, K.INK_TEXT, True)
        for ax in (area.x_axis, area.y_axis):
            ax.delete = False
            ax.majorGridlines = None
            ax.spPr = GraphicalProperties(ln=ln(K.STONE, 0.75))
            ax.txPr = text()
        n = last - first + 1
        area.x_axis.number_format = "yyyy"
        area.x_axis.tickLblSkip = area.x_axis.tickMarkSkip = max(1, n // 8)
        area.x_axis.tickLblPos = "low"
        area.y_axis.scaling.min, area.y_axis.scaling.max = r["axis"]
        area.y_axis.majorUnit = r["step"]
        area.y_axis.number_format = "#,##0.0#" if abs(r["axis"][1]) < 1000 else "#,##0"
        area.y_axis.title = unit
        # The bands and the latest point live in hidden helper columns; a
        # chart plots only visible cells unless told otherwise.
        area.visible_cells_only = False
        area.title = title
        area.title.tx.rich.p[0].pPr = ParagraphProperties(defRPr=CharacterProperties(sz=1000, b=True,
                                                                                      solidFill=K.INK))
        area.legend = None
        area.display_blanks = "gap"
        area.height, area.width = 8.5, 24
        area.roundedCorners = False
        area.graphical_properties = GraphicalProperties(ln=LineProperties(noFill=True))
        area += line
        area += latest
        return area

    for key in national:
        item = items[key]
        mine = by_key.get(key, {})
        ws = sheet(TAB[key])
        widths(ws, [2.71, 18, 13, 13, 13, 13, 18, 13, 13, 13, 13, 13, 2.71, 12, 13, 13, 22, 12, 9])
        source = BY_KEY.get(key)
        row = K.light_title(ws, 1, 11, item.title, "%s. %s, %s. Pulled %s." % (
            source.publisher if source else "Made from two series", item.unit, item.frequency, vintage),
            first_col=2)
        link(ws.cell(row, 2), "Ratings", "Back to Ratings")
        row += 1
        for j, reading in enumerate(("position", "change")):
            col = 2 + 5 * j
            ws.cell(row, col, reading_name(reading, months)).font = F_LABEL
            r = mine.get(reading)
            if r:
                chip(ws, row + 1, col, r["rating"], size=11)
                v = ws.cell(row + 1, col + 1, r["value"] / 100 if reading == "change" and
                            item.change_in == "percent" else r["value"])
                v.number_format = ("+#,##0.0#%;-#,##0.0#%;0%" if item.change_in == "percent" else
                                   "+#,##0.0#;-#,##0.0#;0") if reading == "change" else value_format(r["value"])
                v.font = Font(name="Calibri", size=14, bold=True, color=K.INK_TEXT)
                d = ws.cell(row + 1, col + 2, _date(r["date"]))
                d.number_format, d.font = "yyyy-mm-dd", F_NOTE
                note(ws, row + 2, col, r["sentence"], col + 4)
            elif reading == "position" and item.position:
                note(ws, row + 1, col, "Change only: " + item.position + ".", col + 4)
            else:
                note(ws, row + 1, col, "Not rated: see the Not rated tab.", col + 4)
        ws.row_dimensions[row + 1].height = 21
        ws.row_dimensions[row + 2].height = 58
        row += 4

        # where each rating starts, and how many readings took it
        row = K.quiet_section(ws, row, "Where each rating starts", 11, first_col=2)
        head_cols = ["Rating"]
        for reading in ("position", "change"):
            if reading in mine:
                head_cols += ["%s from" % ("Level" if reading == "position" else "Change"),
                              "Readings" if reading == "position" else "Changes"]
        row = K.canvas_header(ws, row, head_cols, first_col=2, right_from=1)
        for k in range(1, 6):
            chip(ws, row, 2, k)
            col = 3
            for reading in ("position", "change"):
                r = mine.get(reading)
                if not r:
                    continue
                if k == 1:
                    c = ws.cell(row, col, "below 2" if r["direction"] == HIGHER else "above 2")
                    c.font, c.alignment = F_NOTE, Alignment(horizontal="right")
                else:
                    edge = r["lines"][str(k)]
                    if edge is None:
                        c = ws.cell(row, col, "not reached")
                        c.font, c.alignment = F_NOTE, Alignment(horizontal="right")
                    else:
                        shown = edge / 100 if reading == "change" and item.change_in == "percent" else edge
                        c = ws.cell(row, col, shown)
                        c.font = F_DATA
                        c.number_format = "#,##0.0#%" if reading == "change" and item.change_in == "percent" \
                            else value_format(edge)
                c = ws.cell(row, col + 1, r["counts"][str(k)])
                c.font, c.number_format = F_DATA, "#,##0"
                col += 2
            K.hairlines(ws, row, 2, 2 + len(head_cols) - 1)
            row += 1
        side = {"position": None, "change": None}
        for reading in ("position", "change"):
            if reading in mine:
                side[reading] = "at or above" if mine[reading]["direction"] == HIGHER else "at or below"
        note(ws, row, 2, "From: in this history, the least extreme reading that took the rating. Readings %s it "
                         "took that rating or higher." % " / ".join(sorted({v for v in side.values() if v})), 11)
        row += 2

        # the history, on the right: Date, Value, Change, Note; hidden helper columns for the bands
        points = pull.points(item)
        if isinstance(points, str):
            ws.cell(row, 2, points).font = F_NOTE
            continue
        chg = dict(changes(points, months, item.frequency, item.change_in))
        top = row          # beside the first chart, below the tall rows at the top
        K.canvas_header(ws, top, ["Date", "Value", "Change over %d months" % months, "Note"], first_col=14,
                        right_from=1)
        ws.cell(top, 17).alignment = Alignment(wrap_text=True, vertical="center")
        first = top + 1
        dates = []
        for i, (d, v) in enumerate(points):
            rr = first + i
            dates.append(_date(d).isoformat())
            c = ws.cell(rr, 14, _date(d))
            c.number_format, c.font = "yyyy-mm-dd", F_DATA
            # A missing value stays an empty cell: text there would be drawn
            # as zero on the chart, the very error the readers are kept from.
            if v is not None:
                c = ws.cell(rr, 15, v)
                c.number_format, c.font = value_format(v), F_DATA
            else:
                ws.cell(rr, 17, "no value published").font = F_NOTE
            if dates[-1] in chg:
                c = ws.cell(rr, 16, chg[dates[-1]])
                c.number_format, c.font = "#,##0.0#", F_DATA
        last = first + len(points) - 1

        helper = 20                                 # T onwards, hidden
        for reading, data_col in (("position", 15), ("change", 16)):
            r = mine.get(reading)
            if not r:
                helper += 7
                continue
            values = [v for _, v in points if v is not None] if reading == "position" else list(chg.values())
            lo, hi, step = nice_axis(min(values + [r["low"]]), max(values + [r["high"]]))
            base, heights, order = band_heights(r["lines"], r["direction"], lo, hi)
            r = dict(r, order=order, axis=(lo, hi), step=step)
            names = ["base"] + [label(k) for k in order] + ["Latest"]
            for j, name in enumerate(names):
                ws.cell(top, helper + j, name).font = F_NOTE
            latest_row = first + dates.index(_date(r["date"]).isoformat())
            for rr in range(first, last + 1):
                ws.cell(rr, helper, base)
                for j, h in enumerate(heights):
                    ws.cell(rr, helper + 1 + j, h)
            ws.cell(latest_row, helper + 6, ws.cell(latest_row, data_col).value)
            for j in range(7):
                ws.column_dimensions[L(helper + j)].hidden = True
            chart = banded_chart(ws, ("Level against its history" if reading == "position" else
                                      "Change over %d months against its history" % months),
                                 item.unit if reading == "position" else
                                 ("percent" if item.change_in == "percent" else "points"),
                                 data_col, first, last, helper, r, item.frequency)
            ws.add_chart(chart, "B%d" % row)
            row += 18
            helper += 7

        if key == "unemployment" and s["show_sahm"]:
            sv = dict(sahm(points))
            K.canvas_header(ws, top, ["Sahm reading", "Trigger"], first_col=18, right_from=0)
            for i, d in enumerate(dates):
                if d in sv:
                    c = ws.cell(first + i, 18, sv[d])
                    c.number_format = "0.00"
                    ws.cell(first + i, 19, 0.50)
            sc = LineChart()
            sc.add_data(Reference(ws, min_col=18, max_col=19, min_row=top, max_row=last), titles_from_data=True)
            sc.set_categories(Reference(ws, min_col=14, min_row=first, max_row=last))
            sc.series[0].graphicalProperties.line = ln(K.INK, 1.5)
            sc.series[1].graphicalProperties.line = ln(K.CRIMSON, 1.25, "sysDash")
            for s_ in sc.series:
                s_.marker.symbol = "none"
                s_.smooth = False
            for ax in (sc.x_axis, sc.y_axis):
                ax.delete = False
                ax.majorGridlines = None
                ax.spPr = GraphicalProperties(ln=ln(K.STONE, 0.75))
                ax.txPr = text()
            sc.x_axis.number_format = "yyyy"
            sc.x_axis.tickLblSkip = sc.x_axis.tickMarkSkip = max(1, len(points) // 8)
            sc.x_axis.tickLblPos = "low"
            sc.title = "Sahm reading (shown, not rated): dashed line at Sahm's trigger, 0.50"
            sc.legend = None
            sc.display_blanks = "gap"
            sc.height, sc.width = 8.5, 24
            ws.add_chart(sc, "B%d" % row)
            row += 18

        row = K.quiet_section(ws, row, "What it is", 11, first_col=2)
        facts = []
        if source:
            facts += [("Source", "%s %s" % (source.source.upper().replace("_", " "), source.source_id)),
                      ("Licence", source.licence), ("First reading", source.starts)]
        else:
            facts += [("Made from", " and ".join(BY_KEY[k].title for k in item.inputs)), ("How", item.how)]
        if item.position:
            how = "Change only: " + item.position
        elif "change" in readings_of(item, s["change_for"]):
            how = "Level and change"
        else:
            how = "Level only: the firm did not ask for its change"
        facts.append(("How it is read", how))
        facts.append(("Which way is worse", item.stress + " (from the research)" if item.stress else
                      "; ".join("%s: %s (set by the firm)" % (reading_name(k, months), v["direction"])
                                for k, v in sorted(mine.items())) or "not rated"))
        if item.note:
            facts.append(("Note", item.note))
        for when, what in item.breaks:
            facts.append(("Break", "%s: %s" % (when, what)))
        for k, v in facts:
            c = ws.cell(row, 2, k)
            c.font, c.alignment = F_LABEL, WRAP
            c = ws.cell(row, 3, v)
            ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=12)
            c.font, c.alignment = F_DATA, WRAP
            ws.row_dimensions[row].height = 15 * (1 + len(v) // 120)
            row += 1

    # -- State data ---------------------------------------------------------
    ws = sheet("State data")
    row = K.light_title(ws, 1, 12, "Unemployment rate by state, month by month",
                        "Percent. An empty cell is a month with no value published (October 2025: the lapse "
                        "in appropriations).", live=False, first_col=1)
    head = row + 1
    row = K.canvas_header(ws, head, ["Date"] + list(STATES), right_from=1)
    columns = {}
    for j, st in enumerate(STATES, 2):
        pts = pull.points(BY_KEY["unemployment_" + st.lower()])
        columns[j] = dict(pts) if not isinstance(pts, str) else {}
    for d in sorted({d for c in columns.values() for d in c}):
        ws.cell(row, 1, _date(d)).number_format = "yyyy-mm"
        for j, c in columns.items():
            if d in c and c[d] is not None:
                ws.cell(row, j, c[d])
        row += 1
    ws.freeze_panes = ws.cell(head + 1, 2)

    # -- Not rated ----------------------------------------------------------
    if result["not_rated"]:
        ws = sheet("Not rated")
        widths(ws, [44, 24, 90])
        row = K.light_title(ws, 1, 3, "Not rated", "Each reading the settings call for that has no rating, "
                                                   "and why.", live=False)
        row = K.canvas_header(ws, row + 1, ["Series", "Reading", "Why"])
        for x in result["not_rated"]:
            for j, v in enumerate((items[x["key"]].title, reading_name(x["reading"], months), x["why"]), 1):
                ws.cell(row, j, v).font = F_DATA
            row += 1

    # -- Glossary -----------------------------------------------------------
    ws = sheet("Glossary")
    widths(ws, [30, 120])
    row = K.light_title(ws, 1, 2, "Glossary", "Every term in this workbook, and how it is worked out.",
                        live=False)
    row = K.canvas_header(ws, row + 1, ["Term", "What it means, and how it is worked out"])
    for term, meaning in glossary(s):
        c = ws.cell(row, 1, term)
        c.font, c.alignment = Font(name="Calibri", size=11, bold=True, color=K.INK_TEXT), WRAP
        c = ws.cell(row, 2, meaning)
        c.font, c.alignment = F_DATA, WRAP
        ws.row_dimensions[row].height = 15 * (1 + len(meaning) // 150)
        row += 1

    # -- Run ----------------------------------------------------------------
    ws = sheet("Run")
    widths(ws, [42, 40, 100])
    row = K.light_title(ws, 1, 3, "Run", "What went into this workbook.", live=False)
    row += 1
    for k, v in (("Built", datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")),
                 ("From the pull of", vintage), ("Tool", "threshold-engine %s, economic conditions" % VERSION),
                 ("Readings rated", len(result["ratings"])), ("Readings not rated", len(result["not_rated"]))):
        ws.cell(row, 1, k).font = F_LABEL
        c = ws.cell(row, 2, v)
        c.font, c.alignment = F_DATA, Alignment(horizontal="left")
        row += 1
    row += 1
    row = K.canvas_header(ws, row, ["Setting", "The firm's answer", "The question"])
    asked = {q[0]: q[1] for q in QUESTIONS}
    plain = {
        "cutoffs": ", ".join("%g" % c for c in s["cutoffs"]) + " (percentiles where 2, 3, 4 and 5 start)",
        "on_the_line": s["on_the_line"] + " rating",
        "history": "full history" if s["history"] == "full" else "the last %d years" % s["history"]["years"],
        "change_months": "%d months" % months,
        "show_sahm": "yes" if s["show_sahm"] else "no",
        "change_for": "all series" if s["change_for"] == "all" else ", ".join(s["change_for"]) or "none",
    }
    called = {"cutoffs": "Where ratings 2 to 5 start", "on_the_line": "A reading exactly on a cut-off",
              "history": "History each reading is measured against", "change_months": "Change counted over",
              "show_sahm": "Sahm reading shown", "change_for": "Also rated on their change"}
    rows = [(called[n], a, asked[n]) for n, a in plain.items()]
    rows += [("Which way is worse: %s, %s" % (items[k].title, reading_name(rd, months).lower()), d,
              asked["directions"]) for k, rd, d in s["directions"]]
    for vals in rows:
        for j, v in enumerate(vals, 1):
            c = ws.cell(row, j, v)
            c.font, c.alignment = F_DATA, WRAP
        ws.row_dimensions[row].height = 30
        row += 1

    # -- Sources ------------------------------------------------------------
    ws = sheet("Sources")
    widths(ws, [44, 36, 30, 34, 13, 28, 60, 26, 66])
    row = K.light_title(ws, 1, 9, "Sources", "Every file the pull fetched, as fetched.", live=False)
    row = K.canvas_header(ws, row + 1, ["Series", "Publisher", "Id at the source", "Licence", "First reading",
                                        "File", "Address", "Fetched", "SHA-256"])
    from .pull import file_name
    files = pull.manifest.get("files", {})
    for x in SERIES:
        name = file_name(x)
        f = files.get(name, {})
        for j, v in enumerate((x.title, x.publisher, x.source_id, x.licence, x.starts, name, f.get("url", ""),
                               f.get("fetched_at", f.get("error", "not in this pull")), f.get("sha256", "")), 1):
            ws.cell(row, j, v).font = F_DATA
        ws.cell(row, 9).font = Font(name="Consolas", size=9, color=K.SLATE)
        row += 1
    for d in DERIVED:
        ws.cell(row, 1, d.title).font = F_DATA
        ws.cell(row, 2, "made from " + " and ".join(BY_KEY[k].title for k in d.inputs)).font = F_DATA
        row += 1
    ws.freeze_panes = ws.cell(4, 2)

    wb.save(out)
    return out


def glossary(s):
    """Every term the workbook uses, worded from the settings the run used."""
    c, m = s["cutoffs"], s["change_months"]
    return [
        ("Level", "The latest reading itself, compared with every reading in the series' own history."),
        ("Change over %d months" % m,
         "The latest reading minus the reading %d months earlier. For a rate, a spread or an index around zero it "
         "is in points; for a level that grows (prices, jobs, output, credit, claims) it is a percent of the "
         "earlier reading. Weekly and daily series count whole weeks (12 months is 52), as FRED does; a day with "
         "no reading that many weeks before has no change." % m),
        ("Percentile",
         "The share of the series' history that the latest reading is at or above (where higher is worse) or at "
         "or below (where lower is worse). The latest reading counts in its own history, so a new record is 100%."),
        ("Rating",
         "1 Low to 5 High, from the percentile: 2 starts at the %gth, 3 at the %gth, 4 at the %gth and 5 at the "
         "%gth. A reading exactly on a cut-off takes the %s rating." % (c[0], c[1], c[2], c[3],
                                                                         s["on_the_line"])),
        ("From", "Where a rating starts, in the series' own units: the least extreme reading in this history "
                 "that took the rating."),
        ("Readings, Changes", "How many readings (or changes) in the history took each rating."),
        ("History from", "The first reading the rating is measured against. %s"
         % ("Every series is measured against its full history." if s["history"] == "full" else
            "Each is measured against the last %d years." % s["history"]["years"])),
        ("At this rating since", "The first of the unbroken run of readings, up to the latest, that share the "
                                 "latest rating, each rated against the same history."),
        ("What stands out", "The sentence behind the higher of the series' two ratings (the change on a tie)."),
        ("Change only", "A level that climbs over the decades with prices and the economy sits near the top of "
                        "its own history in almost every year, so its place there says nothing. Only its change is "
                        "rated."),
        ("Higher is worse, lower is worse", "Which way stress runs for a reading: from the research where it says, "
                                            "otherwise set by the firm. Each series' tab says which."),
        ("Sahm reading", "The 3-month average unemployment rate minus its lowest 3-month average in the 12 months "
                         "before. Sahm's published trigger is 0.50. Shown, not rated. Where a month has no value "
                         "(October 2025), the average is taken from the two months that do, as FRED does."),
        ("Pulled", "The day the data was downloaded. Every pull is kept in its own folder, so a rating can always "
                   "be traced to the release it used."),
        ("No value published", "A period the publisher left blank, such as October 2025 (the lapse in "
                               "appropriations). It stays empty: never filled, never read as zero."),
        ("Made from two series", "House prices against income, and the mortgage rate over the 10-year Treasury, "
                                 "are worked out from two series in the same pull. Each tab says how."),
        ("Break", "A change in how the publisher builds the series, or a known seasonal step, that a reader should "
                  "know before comparing across it."),
        ("Not rated", "A reading the settings call for that has no rating: not in the pull, or chosen by the firm "
                      "not to be rated. The Not rated tab says which and why, when there are any."),
    ]
