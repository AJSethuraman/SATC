"""The workbook the consumer and commercial teams read.

Made only from a finished rating run, so it cannot exist without the firm's
settings. Every number in it is a value written by Python; nothing is a
formula, so nothing moves after it is written.

    Ratings      every national reading, highest rating first, with what drove it
    States       unemployment by state: level and change
    one per series   what it is, where it comes from, how it is read, its
                 ratings and where each rating starts, its history and a chart
    State data   every state's unemployment rate, month by month
    Not rated    only when something could not be rated, and why
    Settings     the firm's answers the run used
    Sources      every file: address, licence, when fetched, SHA-256
"""
import datetime

from .catalog import BY_KEY, DERIVED, RATED, SERIES, STATES
from .rate import changes
from .settings import QUESTIONS, readings_of

RATINGS = ("Low", "Moderate-Low", "Moderate", "Moderate-High", "High")


def label(r):
    return "%d %s" % (r, RATINGS[r - 1])


def reading_name(reading, months):
    return "Level" if reading == "position" else "Change over %d months" % months


def _date(d):
    return datetime.date.fromisoformat(d[:10])


def value_format(x):
    """Whole numbers with commas for big values; two decimals at most otherwise."""
    return "#,##0" if x is not None and abs(x) >= 1000 else "#,##0.0#"


def build(out, result, pull):
    """Write the workbook for one rating run (``rate_all``'s result) to ``out``."""
    from openpyxl import Workbook
    from openpyxl.chart import LineChart, Reference
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter as L

    from .. import keybank_style as K

    heat = {5: PatternFill("solid", fgColor=K.HEAT_BAD), 4: PatternFill("solid", fgColor=K.HEAT_BAD),
            3: PatternFill("solid", fgColor=K.HEAT_WARM)}
    wrap = Alignment(wrap_text=True, vertical="top")
    s = result["settings"]
    months = s["change_months"]
    vintage = result["vintage"]
    ratings = result["ratings"]
    by_key = {}
    for r in ratings:
        by_key.setdefault(r["key"], {})[r["reading"]] = r
    items = {i.key: i for i in RATED}
    state_keys = {"unemployment_" + st.lower() for st in STATES}

    wb = Workbook()

    def sheet(title, first=False):
        ws = wb.active if first else wb.create_sheet()
        ws.title = title
        K.hide_gridlines(ws)
        # Printed landscape, every column on the page.
        ws.page_setup.orientation = "landscape"
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
        return ws

    def widths(ws, ws_widths):
        for i, w in enumerate(ws_widths, 1):
            ws.column_dimensions[L(i)].width = w

    def rating_cell(ws, row, col, r):
        c = ws.cell(row, col, label(r))
        c.font = Font(name="Calibri", bold=r >= 4, size=11, color=K.INK_TEXT)
        if r in heat:
            c.fill = heat[r]
        return c

    # -- Ratings ----------------------------------------------------------
    ws = sheet("Ratings", first=True)
    cols = ["Rating", "Series", "Reading", "Group", "Latest", "Value", "Unit", "Percentile",
            "Measured against", "At this rating since", "What drove it"]
    row = K.brand_banner(ws, 1, len(cols), "Economic conditions",
                         "Public data, pulled %s. Each series against its own history: 1 Low to 5 High."
                         % vintage)
    national = [r for r in ratings if r["key"] not in state_keys]
    counts = [sum(1 for r in national if r["rating"] == n) for n in (5, 4, 3)]
    sahm = next(iter(result["alongside"]), None)
    tiles = [("RATED 5 HIGH", counts[0], "readings"), ("RATED 4 MODERATE-HIGH", counts[1], "readings"),
             ("RATED 3 MODERATE", counts[2], "readings"),
             ("SAHM READING", "%.2f" % sahm["value"] if sahm else "not shown",
              ("%s; trigger 0.50" % sahm["date"][:7]) if sahm else "")]
    row = K.kpi_tiles(ws, row + 1, tiles, span=2) + 1
    head = row
    row = K.header_row(ws, row, cols)
    for j in (6, 8):
        ws.cell(head, j).alignment = K.RIGHT
    for r in sorted(national, key=lambda r: (-r["rating"], r["group"], r["title"], r["reading"])):
        rating_cell(ws, row, 1, r["rating"])
        vals = [r["title"], reading_name(r["reading"], months), r["group"], r["date"], r["value"], r["unit"],
                r["percentile"] / 100, "{:,} {} since {}".format(
                    r["readings"], "readings" if r["reading"] == "position" else "changes", r["history_from"][:10]),
                "%s (%d %s)" % (r["since"][:10], r["held"], "reading" if r["held"] == 1 else "readings"),
                r["sentence"]]
        for j, v in enumerate(vals, 2):
            c = ws.cell(row, j, v)
            c.font = K.DATA_FONT
        ws.cell(row, 6).number_format = value_format(r["value"])
        ws.cell(row, 8).number_format = "0.0%"
        ws.cell(row, 11).alignment = wrap
        ws.row_dimensions[row].height = 30
        row += 1
    if sahm:
        ws.cell(row + 1, 1, sahm["sentence"]).font = K.NOTE_FONT
    ws.cell(row + 2, 1, "Percentile: the share of the series' own history that the latest reading is at or "
                        "above (at or below where lower is worse).").font = K.NOTE_FONT
    K.freeze_below(ws, head)
    widths(ws, [18, 50, 22, 12, 12, 12, 30, 11, 30, 26, 90])

    # -- States -----------------------------------------------------------
    ws = sheet("States")
    cols = ["State", "Latest", "Unemployment rate", "Level rating", "Level percentile",
            "Change over %d months" % months, "Change rating", "Change percentile", "History from"]
    row = K.brand_banner(ws, 1, len(cols), "Unemployment by state",
                         "BLS (LAUS), pulled %s. Each state against its own history." % vintage)
    head = row
    row = K.header_row(ws, row, cols)
    for j in (3, 5, 6, 8):
        ws.cell(head, j).alignment = K.RIGHT
    for j in (4, 7):
        ws.cell(head, j).alignment = K.CENTER

    def worst(st):
        got = by_key.get("unemployment_" + st.lower(), {})
        return -max([x["rating"] for x in got.values()] or [0])
    for st in sorted(STATES, key=lambda st: (worst(st), st)):
        got = by_key.get("unemployment_" + st.lower(), {})
        lvl, chg = got.get("position"), got.get("change")
        ws.cell(row, 1, st).font = K.DATA_FONT
        if lvl:
            ws.cell(row, 2, lvl["date"]).font = K.DATA_FONT
            ws.cell(row, 3, lvl["value"]).font = K.DATA_FONT
            rating_cell(ws, row, 4, lvl["rating"])
            ws.cell(row, 5, lvl["percentile"] / 100).number_format = "0.0%"
            ws.cell(row, 9, lvl["history_from"]).font = K.DATA_FONT
        if chg:
            ws.cell(row, 6, chg["value"]).number_format = "+0.0;-0.0;0.0"
            rating_cell(ws, row, 7, chg["rating"])
            ws.cell(row, 8, chg["percentile"] / 100).number_format = "0.0%"
        if not got:
            ws.cell(row, 2, "not in this pull").font = K.NOTE_FONT
        for j in (4, 7):
            ws.cell(row, j).alignment = K.CENTER
        row += 1
    K.freeze_below(ws, head)
    widths(ws, [8, 13, 20, 20, 17, 25, 20, 19, 14])

    # -- one sheet per national series --------------------------------------
    for item in [i for i in RATED if i.key not in state_keys]:
        ws = sheet(item.key[:31])
        source = BY_KEY.get(item.key)
        row = K.brand_banner(ws, 1, 8, item.title, "%s. %s, %s." % (
            source.publisher if source else "Made from two series", item.unit, item.frequency))
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
        stated = item.stress
        facts.append(("Which way is worse", stated + " (from the research)" if stated else
                      "; ".join("%s: %s (set by the firm)" % (reading_name(k, months), v["direction"])
                                for k, v in sorted(by_key.get(item.key, {}).items())) or "not rated"))
        if item.note:
            facts.append(("Note", item.note))
        for when, what in item.breaks:
            facts.append(("Break", "%s: %s" % (when, what)))
        for k, v in facts:
            c = ws.cell(row, 1, k)
            c.font, c.alignment = K.KPI_LABEL, wrap
            c = ws.cell(row, 2, v)
            c.font = K.DATA_FONT
            ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=8)
            c.alignment = wrap
            ws.row_dimensions[row].height = 15 * (1 + len(v) // 110)
            row += 1
        row += 1
        mine = by_key.get(item.key, {})
        if mine:
            row = K.header_row(ws, row, ["Reading", "Rating", "Latest", "Value", "2 from", "3 from", "4 from",
                                         "5 from"], right_from=3)
            for reading in ("position", "change"):
                r = mine.get(reading)
                if not r:
                    continue
                ws.cell(row, 1, reading_name(reading, months)).font = K.DATA_FONT
                rating_cell(ws, row, 2, r["rating"])
                ws.cell(row, 3, r["date"]).font = K.DATA_FONT
                ws.cell(row, 4, r["value"]).number_format = value_format(r["value"])
                for j, n in enumerate("2345", 5):
                    c = ws.cell(row, j, r["lines"][n] if r["lines"][n] is not None else "not reached")
                    c.number_format = value_format(r["lines"][n])
                row += 1
                c = ws.cell(row, 1, r["sentence"])
                c.font = K.SECONDARY
                ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=8)
                c.alignment = wrap
                ws.row_dimensions[row].height = 32
                row += 1
            note = ws.cell(row, 1, "\"2 from\": in this history, readings this far or further in the direction "
                                   "of stress were rated 2 or more; the same for 3, 4 and 5.")
            note.font = K.NOTE_FONT
            row += 2
        points = pull.points(item)
        if isinstance(points, str):
            ws.cell(row, 1, points).font = K.NOTE_FONT
            widths(ws, [22, 18, 14, 14, 12, 12, 12, 12])
            continue
        chg = dict(changes(points, months, item.frequency, item.change_in))
        head = row
        row = K.header_row(ws, row, ["Date", "Value", "Change over %d months" % months, "Note"], right_from=1)
        ws.cell(head, 4).alignment = K.LEFT
        first = row
        for d, v in points:
            ws.cell(row, 1, _date(d)).number_format = "yyyy-mm-dd"
            # A missing value stays an empty cell: text there would be drawn
            # as zero on the chart, the very error the readers are kept from.
            if v is not None:
                ws.cell(row, 2, v).number_format = value_format(v)
            else:
                ws.cell(row, 4, "no value published").font = K.NOTE_FONT
            iso = _date(d).isoformat()
            if iso in chg:
                ws.cell(row, 3, chg[iso]).number_format = "#,##0.0#"
            row += 1
        chart = LineChart()
        chart.title = item.title
        chart.height, chart.width = 8, 22
        chart.legend = None
        chart.y_axis.title = item.unit
        chart.add_data(Reference(ws, min_col=2, min_row=head, max_row=row - 1), titles_from_data=True)
        chart.set_categories(Reference(ws, min_col=1, min_row=first, max_row=row - 1))
        chart.x_axis.number_format = "yyyy"
        chart.x_axis.tickLblSkip = chart.x_axis.tickMarkSkip = max(1, len(points) // 10)
        chart.display_blanks = "gap"
        chart.x_axis.tickLblPos = "low"         # below the plot, not across it at zero
        ws.add_chart(chart, "F%d" % head)
        widths(ws, [22, 18, 24, 20, 12, 12, 12, 12])

    # -- State data ---------------------------------------------------------
    ws = sheet("State data")
    ws.cell(1, 1, "Unemployment rate by state, percent. An empty cell is a month with no value published "
                  "(October 2025: the lapse in appropriations).").font = K.NOTE_FONT
    row = K.header_row(ws, 2, ["Date"] + list(STATES), right_from=1)
    columns = {}
    for j, st in enumerate(STATES, 2):
        pts = pull.points(BY_KEY["unemployment_" + st.lower()])
        columns[j] = dict(pts) if not isinstance(pts, str) else {}
    dates = sorted({d for c in columns.values() for d in c})
    for d in dates:
        ws.cell(row, 1, _date(d)).number_format = "yyyy-mm"
        for j, c in columns.items():
            if d in c and c[d] is not None:
                ws.cell(row, j, c[d])
        row += 1
    K.freeze_below(ws, 2, 2)

    # -- Not rated ----------------------------------------------------------
    if result["not_rated"]:
        ws = sheet("Not rated")
        row = K.header_row(ws, 1, ["Series", "Reading", "Why"])
        for x in result["not_rated"]:
            for j, v in enumerate((items[x["key"]].title, reading_name(x["reading"], months), x["why"]), 1):
                ws.cell(row, j, v).font = K.DATA_FONT
            row += 1
        widths(ws, [40, 24, 90])

    # -- Settings -----------------------------------------------------------
    ws = sheet("Settings")
    row = K.header_row(ws, 1, ["Setting", "The firm's answer", "The question"])
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
    for name, answer in plain.items():
        for j, v in enumerate((called[name], answer, asked[name]), 1):
            c = ws.cell(row, j, v)
            c.font = K.DATA_FONT
            c.alignment = wrap
        ws.row_dimensions[row].height = 30
        row += 1
    for key, reading, direction in s["directions"]:
        for j, v in enumerate(("Which way is worse: %s, %s" % (items[key].title, reading_name(reading, months)
                                                                .lower()), direction, asked["directions"]), 1):
            c = ws.cell(row, j, v)
            c.font = K.DATA_FONT
            c.alignment = wrap
        ws.row_dimensions[row].height = 30
        row += 1
    widths(ws, [52, 34, 100])

    # -- Sources ------------------------------------------------------------
    ws = sheet("Sources")
    cols = ["Series", "Publisher", "Id at the source", "Licence", "First reading", "File", "Address",
            "Fetched", "SHA-256"]
    row = K.header_row(ws, 1, cols)
    from .pull import file_name
    files = pull.manifest.get("files", {})
    for x in SERIES:
        name = file_name(x)
        f = files.get(name, {})
        for j, v in enumerate((x.title, x.publisher, x.source_id, x.licence, x.starts, name, f.get("url", ""),
                               f.get("fetched_at", f.get("error", "not in this pull")), f.get("sha256", "")), 1):
            ws.cell(row, j, v).font = K.DATA_FONT
        row += 1
    for d in DERIVED:
        ws.cell(row, 1, d.title).font = K.DATA_FONT
        ws.cell(row, 2, "made from " + " and ".join(BY_KEY[k].title for k in d.inputs)).font = K.DATA_FONT
        row += 1
    K.freeze_below(ws, 1)
    widths(ws, [44, 36, 30, 34, 13, 28, 60, 26, 66])

    wb.save(out)
    return out

