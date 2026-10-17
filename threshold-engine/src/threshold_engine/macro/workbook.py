"""The workbook the consumer and commercial teams read.

Made only from a finished rating run, so it cannot exist without the firm's
settings. Every number in it is a value written by Python; nothing is a
formula, so nothing moves after it is written.

Its look is PocketBook's workbook (pocketbook/docs/redesign-2026-09-26, built
in pocketbook/src/pocketbook/house.py): a dark title band with the red rule
under it, one "How this tab works" note per tab that folds away, tiles for the
headline figures, dark section bands, and tabs coloured for what they hold
(results dark, the record grey). Its charts are Claude Design's for the
threshold workbook (docs/design/HANDOFF.md, in keybank_style.py): the five
rating bands shaded behind the history, the history in ink, the latest reading
ringed and labelled, and a second set of settings drawn as dashed lines, as
the threshold workbook draws "what happens if".

    Ratings      every national series by topic: its level and its change,
                 each rated, and the reading that stands out
    What if      only with --compare: every reading rated under a second set
                 of settings, side by side with the first
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
import math

from .catalog import BY_KEY, DERIVED, HIGHER, RATED, SERIES, STATES
from .compare import CALLED, plain, reading_label, when
from .rate import changes, sahm
from .settings import QUESTIONS, readings_of

RATINGS = ("Low", "Moderate-Low", "Moderate", "Moderate-High", "High")
SHORT = {1: "1 Low", 2: "2 Mod-Low", 3: "3 Moderate", 4: "4 Mod-High", 5: "5 High"}
ROW_RULE = "EFEBE4"      # PocketBook's one-pixel line between rows

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
WHAT_IF_LINES = 34       # AH onwards: the what-if's lines, four columns a reading, hidden


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
    span = (high - low) or abs(high) or 1.0
    raw = span / 5
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    lo, hi = math.floor(low / step) * step, math.ceil(high / step) * step
    if hi <= lo:        # every reading the same, on a step: an axis of no height (Fable on #452)
        lo, hi = lo - step, hi + step
    return lo, hi, step


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


def move_text(rows, months):
    """A series' readings that change rating under the what-if, as a Ratings or States cell says it.
    ``months`` is each side's horizon; a change counted over different months says the what-if's."""
    parts = []
    for r in rows:
        # every branch, moved or one-sided: Codex on #452 found the one-sided one left out
        # The horizon named is that of a rating the cell reports: the what-if's when the what-if rated it,
        # none when only these settings did (Fable on #452, the fourth branch of the same fault).
        what = "Level" if r["reading"] == "position" else "Change"
        when_ = "" if r["same_measure"] or not r["b"] else " (what if: over %d months)" % months[1]
        if r["move"]:
            parts.append("%s %d → %d%s" % (what, r["a"]["rating"], r["b"]["rating"], when_))
        elif r["move"] is None:
            parts.append("%s%s: rated %s only" % (what, when_, "as you have it" if r["a"] else "under the what-if"))
    return "; ".join(parts)


def build(out, result, pull, whatif=None):
    """Write the workbook for one rating run (``rate_all``'s result) to ``out``.

    ``whatif`` is ``compare.compare``'s result for a second set of settings on
    the same pull; with it the workbook gains the What if tab, a column for it
    on Ratings and States, and dashed lines on every chart it applies to."""
    from openpyxl import Workbook
    from openpyxl.chart import AreaChart, BarChart, LineChart, Reference
    from openpyxl.chart.label import DataLabelList
    from openpyxl.chart.legend import Legend
    from openpyxl.chart.shapes import GraphicalProperties
    from openpyxl.chart.text import RichText
    from openpyxl.drawing.line import LineProperties
    from openpyxl.drawing.text import CharacterProperties, Paragraph, ParagraphProperties
    from openpyxl.styles import Alignment, Border, Font, Side
    from openpyxl.utils import get_column_letter as L
    from openpyxl.worksheet.pagebreak import Break

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
    topic_of = {k: t for t, keys in TOPICS for k in keys}
    wrows = {}
    b_months = None
    if whatif:
        for x in whatif["rows"]:
            wrows.setdefault(x["key"], {})[x["reading"]] = x
        b_months = "%d months" % whatif["months"][1]

    F_DATA = Font(name="Calibri", size=10, color=K.INK_TEXT)
    F_BOLD = Font(name="Calibri", size=10, bold=True, color=K.INK_TEXT)
    F_NOTE = Font(name="Calibri", size=10, color=K.SLATE)
    F_FIELD = Font(name="Arial", size=8, bold=True, color=K.SLATE)
    F_BIG = Font(name="Calibri", size=14, bold=True, color=K.INK_TEXT)
    F_LINK = Font(name="Calibri", size=10, color="1F4E79", underline="single")
    F_UP = Font(name="Calibri", size=10, bold=True, color=K.CRIMSON)
    F_DOWN = Font(name="Calibri", size=10, bold=True, color=K.POSITIVE)
    WRAP = Alignment(wrap_text=True, vertical="top")
    CENTER = Alignment(horizontal="center", vertical="center")
    MIDDLE = Alignment(vertical="center")

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

    def side(style, color):
        return Side(style=style, color=color)

    wb = Workbook()

    # -- the house anatomy (PocketBook's house.py, written here for this workbook) ---------------------------
    def sheet(title, first=False):
        ws = wb.active if first else wb.create_sheet()
        ws.title = title
        K.hide_gridlines(ws)
        ws.page_setup.orientation = "landscape"
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
        ws.column_dimensions["A"].width = 2.71
        return ws

    def widths(ws, ws_widths, first=2):
        for i, w in enumerate(ws_widths, first):
            ws.column_dimensions[L(i)].width = w

    def title_band(ws, title, sub, last, record=False):
        """Row 1: the tab's name in white on ink, a one-line subtitle beside it, a thick red rule under it.
        The record tabs are slate with a stone rule, and their tabs grey."""
        fill, rule = (K.SLATE, K.STONE) if record else (K.INK, K.KEY_RED)
        for col in range(1, last + 1):
            c = ws.cell(1, col)
            c.fill = K.solid(fill)
            c.border = Border(bottom=side("thick", rule))
        c = ws.cell(1, 2, title)
        c.font = Font(name="Arial", bold=True, size=16, color=K.PAPER)
        c.alignment = MIDDLE
        # The subtitle is its own cell, in the first column past the title (Arial 16 bold runs about 1.9 width
        # units a character), as PocketBook writes it. Not rich text in one cell: no workbook the firm opens in
        # Excel uses that, and the firm's Excel refused this one (17 Oct 2026).
        need, col, used = len(title) * 1.9 + 3, 2, 0
        while used < need and col < last:
            used += ws.column_dimensions[L(col)].width or 9
            col += 1
        s_ = ws.cell(1, col, sub)
        s_.font = Font(name="Arial", size=10, color=K.MIST if record else K.STONE)
        s_.alignment = MIDDLE
        ws.row_dimensions[1].height = 30
        ws.sheet_properties.tabColor = K.STONE if record else K.INK

    def width_of(ws, first, last):
        return sum((ws.column_dimensions[L(c)].width or 9) for c in range(first, last + 1))

    def method_note(ws, top, last, entries, label_cols=1, first=2):
        """The tab's one method note: a heading row, then one row per entry, the label bold and the words in
        one merged cell that wraps, on canvas. The entries are grouped under the heading, so the reader folds
        them away with the outline's minus."""
        for col in range(first, last + 1):
            ws.cell(top, col).fill = K.solid(K.CANVAS)
        ws.cell(top, first, "How this tab works").font = Font(name="Arial", bold=True, size=9, color=K.SLATE)
        text_col = first + label_cols
        per_line = width_of(ws, text_col, last) * 1.4
        r = top + 1
        for name, words in entries:
            for col in range(first, last + 1):
                ws.cell(r, col).fill = K.solid(K.CANVAS)
            a = ws.cell(r, first, name)
            a.font, a.alignment = F_BOLD, Alignment(vertical="top")
            ws.merge_cells(start_row=r, start_column=text_col, end_row=r, end_column=last)
            b = ws.cell(r, text_col, words)
            b.font, b.alignment = F_DATA, WRAP
            ws.row_dimensions[r].height = 14 * max(1, math.ceil(len(words) / per_line)) + 3
            r += 1
        ws.row_dimensions.group(top + 1, r - 1, outline_level=1, hidden=False)
        ws.sheet_properties.outlinePr.summaryBelow = False
        return r + 1

    def tile(ws, row, first, last, name, value, fmt=None, to=None):
        """A headline figure over two rows: canvas, a thick red rule on top, the label small, the value bold."""
        for rr in (row, row + 1):
            for col in range(first, last + 1):
                c = ws.cell(rr, col)
                c.fill = K.solid(K.CANVAS)
                c.border = Border(top=side("thick", K.KEY_RED)) if rr == row else Border()
            if last > first:
                ws.merge_cells(start_row=rr, start_column=first, end_row=rr, end_column=last)
        a = ws.cell(row, first, name)
        a.font, a.alignment = Font(name="Calibri", size=9, color=K.SLATE), Alignment(vertical="top", indent=1)
        b = ws.cell(row + 1, first, value)
        b.font = Font(name="Arial", bold=True, size=12, color=K.INK_TEXT)
        b.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        if fmt:
            b.number_format = fmt
        if to:
            b.hyperlink = "#'%s'!A1" % to
            b.font = Font(name="Arial", bold=True, size=12, color="1F4E79", underline="single")
        ws.row_dimensions[row].height = 15
        ws.row_dimensions[row + 1].height = 22

    def section(ws, row, words, last, first=2):
        """A section's dark band, one row, with the red rule under it."""
        for col in range(first, last + 1):
            c = ws.cell(row, col)
            c.fill = K.solid(K.INK)
            c.border = Border(bottom=side("medium", K.KEY_RED))
        c = ws.cell(row, first, words)
        c.font, c.alignment = Font(name="Arial", bold=True, size=10, color=K.PAPER), MIDDLE
        ws.row_dimensions[row].height = 20
        return row + 1

    def sub_header(ws, row, heads, first=2, right=(), centre=(), height=25.5):
        """The canvas row naming a section's columns."""
        for i, h in enumerate(heads):
            c = ws.cell(row, first + i, h)
            c.fill = K.solid(K.CANVAS)
            c.font = Font(name="Arial", bold=True, size=9, color=K.SLATE)
            c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="right" if i in right else
                                    "center" if i in centre else "left")
        ws.row_dimensions[row].height = height
        return row + 1

    def header(ws, row, heads, first=2, right=(), centre=(), height=25.5):
        """A table's column headers: ink, white Arial bold."""
        for i, h in enumerate(heads):
            c = ws.cell(row, first + i, h)
            c.fill = K.solid(K.INK)
            c.font = Font(name="Arial", bold=True, size=9, color=K.PAPER)
            c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="right" if i in right else
                                    "center" if i in centre else "left")
        ws.row_dimensions[row].height = height
        return row + 1

    def rule(ws, row, first, last):
        for col in range(first, last + 1):
            ws.cell(row, col).border = Border(bottom=side("thin", ROW_RULE))

    def chip(ws, row, col, r, size=9, short=False):
        c = ws.cell(row, col, SHORT[r] if short else label(r))
        c.font = Font(name="Arial", bold=True, size=size, color=K.INK)
        c.fill = K.solid(K.BANDS[r - 1])
        c.alignment = CENTER
        c.border = Border(left=side("thin", K.PAPER), right=side("thin", K.PAPER))
        return c

    def link(cell, sheet_name, text_=None):
        if text_ is not None:
            cell.value = text_
        cell.hyperlink = "#'%s'!A1" % sheet_name
        cell.font = F_LINK

    def note(ws, row, col, value, last_col, font=None):
        ws.merge_cells(start_row=row, start_column=col, end_row=row, end_column=last_col)
        c = ws.cell(row, col, value)
        c.font, c.alignment = font or F_NOTE, WRAP
        return c

    def put(ws, row, col, value, fmt=None, font=None, align=None):
        c = ws.cell(row, col, value)
        c.font = font or F_DATA
        if fmt:
            c.number_format = fmt
        c.alignment = align or MIDDLE
        return c

    def standout(key):
        got = by_key.get(key, {})
        if not got:
            return None
        return max(got.values(), key=lambda r: (r["rating"], r["reading"] == "change"))

    def change_value(item, v):
        """A change as a cell holds it: a percent change as a fraction, so the cell's format shows %."""
        if item.change_in == "percent":
            return v / 100, "+#,##0.0#%;-#,##0.0#%;0%"
        return v, "+#,##0.0#;-#,##0.0#;0"

    def moved_font(rows):
        if any(r["move"] and r["move"] > 0 for r in rows):
            return F_UP
        if any(r["move"] and r["move"] < 0 for r in rows):
            return F_DOWN
        return F_NOTE

    # -- Ratings ----------------------------------------------------------
    ws = sheet("Ratings", first=True)
    last = 13 if whatif else 12
    widths(ws, [46, 11, 12, 30, 16, 12, 12, 16, 12, 12, 90] + ([26] if whatif else []))
    title_band(ws, "Economic conditions", "Public data, pulled %s. Each series against its own history: "
                                          "1 Low to 5 High." % vintage, last)
    every = [r for r in result["ratings"] if r["key"] not in state_keys]
    tile(ws, 3, 2, 2, "From the pull of", vintage)
    tile(ws, 3, 3, 4, "Readings rated", len(result["ratings"]), "#,##0")
    sahm_x = next(iter(result["alongside"]), None)
    if sahm_x:
        tile(ws, 3, 5, 5, "Sahm reading, shown, not rated", "%.2f in %s" % (
            sahm_x["value"], _date(sahm_x["date"]).strftime("%b %Y")))
    ws.cell(2, 6, "NATIONAL READINGS AT EACH RATING").font = F_FIELD
    for i, k in enumerate((5, 4, 3, 2, 1)):
        c = chip(ws, 3, 6 + i, k, short=True)
        if k == 1:
            c.border = Border(left=side("thin", K.STONE), right=side("thin", K.STONE), top=side("thin", K.STONE))
        c = put(ws, 4, 6 + i, sum(1 for r in every if r["rating"] == k),
                font=Font(name="Arial", size=14, bold=True, color=K.INK_TEXT), align=CENTER)
        c.fill = K.solid(K.CANVAS)
    if whatif:
        nat = [x for x in whatif["rows"] if x["key"] not in state_keys]
        moved = sum(1 for x in nat if x["move"])
        tile(ws, 3, 12, 13, "What if: %s" % whatif["b"], "%d of %d national readings change rating" % (
            moved, sum(1 for x in nat if x["move"] is not None)), to="What if")
    entries = [
        ("Level", "Where the latest reading sits in the series' own history: the share of every reading in that "
                  "history at or beyond it in the direction of stress."),
        ("Change", "The change over %d months, measured the same way against every such change in that history. "
                   "Twelve series that grow with prices and output are rated on their change only." % months),
        ("Rating", "1 Low to 5 High. Rating 2 starts at the %gth percentile, 3 at the %gth, 4 at the %gth and 5 at "
                   "the %gth. A reading exactly on a cut-off takes the %s rating." % (
                       *s["cutoffs"], s["on_the_line"])),
        ("History from", "The first reading each rating is measured against: %s." % (
            "the full history the publisher has" if s["history"] == "full" else
            "the last %d years up to the latest reading" % s["history"]["years"])),
        ("What stands out", "The sentence behind the higher of the series' two ratings; the change on a tie."),
    ]
    if sahm_x:
        entries.append(("Sahm reading", "The 3-month average unemployment rate minus its lowest 3-month average in "
                                        "the 12 months before. Sahm's published trigger is 0.50; shown, not "
                                        "rated."))
    if whatif:
        entries.append(("What if", "Each reading whose rating differs under %s, rated from the same pull. The "
                                   "What if tab sets every reading side by side." % whatif["b"]))
    entries.append(("Series", "Each name opens the series' tab: both ratings, where each rating starts, and the "
                              "history drawn over the five rating bands."))
    row = method_note(ws, 6, last, entries)
    cols = ["Series", "Latest", "Value", "Unit", "Level", "Level percentile", "Change over %d months" % months,
            "Change", "Change percentile", "History from", "What stands out"] + (["What if"] if whatif else [])
    for topic, keys in TOPICS:
        row = section(ws, row, topic, last)
        row = sub_header(ws, row, cols, right=(1, 2, 5, 6, 8), centre=(4, 7, 9))
        ranked = sorted(keys, key=lambda k: (-(standout(k) or {"rating": 0})["rating"], items[k].title))
        for key in ranked:
            got = by_key.get(key, {})
            lvl, chg, top = got.get("position"), got.get("change"), standout(key)
            item = items[key]
            link(ws.cell(row, 2), TAB[key], item.title)
            put(ws, row, 5, item.unit, font=F_NOTE)
            pts = pull.points(item)
            now = next(((d, v) for d, v in reversed(pts) if v is not None), None) if not isinstance(pts, str) else None
            if now:                     # the latest value, rated on its level or not
                put(ws, row, 3, _date(now[0]), "yyyy-mm-dd")
                put(ws, row, 4, now[1], value_format(now[1]))
            if lvl:
                chip(ws, row, 6, lvl["rating"])
                put(ws, row, 7, lvl["percentile"] / 100, "0.0%")
            elif item.position:
                put(ws, row, 6, "change only", font=F_NOTE, align=CENTER)
            if not chg and "change" not in readings_of(item, s["change_for"]):
                put(ws, row, 9, "level only", font=F_NOTE, align=CENTER)   # not asked for: not a failure
            if chg:
                v, fmt = change_value(item, chg["value"])
                put(ws, row, 8, v, fmt)
                chip(ws, row, 9, chg["rating"])
                put(ws, row, 10, chg["percentile"] / 100, "0.0%")
            first = lvl or chg
            if first:
                put(ws, row, 11, _date(first["history_from"]), "yyyy-mm", align=CENTER)
            if top:
                put(ws, row, 12, top["sentence"], font=F_NOTE, align=WRAP)
            if not got:
                put(ws, row, 12, "Not rated: see the Not rated tab", font=F_NOTE)
            if whatif:
                mine = list(wrows.get(key, {}).values())
                words = move_text(mine, whatif["months"])
                put(ws, row, 13, words or ("same rating" if mine else "not rated under either"),
                    font=moved_font(mine) if words else F_NOTE)
            for j in range(2, last + 1):
                c = ws.cell(row, j)
                c.alignment = Alignment(vertical="center", wrap_text=j in (12, 13), horizontal=c.alignment.horizontal)
            ws.row_dimensions[row].height = 30
            rule(ws, row, 2, last)
            row += 1
        row += 1
    ws.freeze_panes = "C2"

    # -- What if ----------------------------------------------------------
    if whatif:
        ws = sheet("What if")
        last = 14
        widths(ws, [40, 22] + [12] * 10 + [10])
        title_band(ws, "What if", "%s against %s, both rating the pull of %s." % (whatif["b"], whatif["a"], vintage),
                   last)
        link(ws.cell(2, 2), "Ratings", "Back to Ratings")
        nat = [x for x in whatif["rows"] if x["key"] not in state_keys]
        sts = [x for x in whatif["rows"] if x["key"] in state_keys]
        both = [x for x in nat if x["move"] is not None]
        tile(ws, 3, 2, 2, "National readings rated under both", len(both))
        tile(ws, 3, 3, 3, "At the same rating", sum(1 for x in both if x["move"] == 0))
        tile(ws, 3, 4, 5, "Rated higher", sum(1 for x in both if x["move"] > 0))
        tile(ws, 3, 6, 7, "Rated lower", sum(1 for x in both if x["move"] < 0))
        tile(ws, 3, 8, 10, "State readings that change", "%d of %d" % (
            sum(1 for x in sts if x["move"]), sum(1 for x in sts if x["move"] is not None)))
        tile(ws, 3, 11, 14, "Rated under one set only", sum(1 for x in whatif["rows"] if x["move"] is None))
        row = method_note(ws, 6, last, [
            ("What it is", "Every reading rated twice from the same pull: with the settings in %s (as you have it) "
                           "and with those in %s (what if). Nothing but the settings differs." % (
                               whatif["a"], whatif["b"])),
            ("Percentile, history", "Each side's percentile, the first reading of the history it is measured "
                                    "against, and how many readings that history holds."),
            ("Move", "The what-if rating minus the rating as you have it: above zero is a higher rating, below zero "
                     "a lower one."),
            ("The grid", "National readings only. The rating as you have it runs down the side and the what-if "
                         "rating across; the diagonal holds the readings at the same rating under both."),
            ("Same rating", "The readings at the same rating under both are listed last, in rows folded away. The "
                            "plus sign beside the row numbers opens them."),
            ("The files", "Neither settings file is changed. The Run tab lists both files' answers."),
        ])

        # what differs
        row = section(ws, row, "What differs between the two settings", last)
        sub_header(ws, row, ["Setting", "", "", "", "As you have it", "", "", "", "What if"], height=18)
        for a, b in ((2, 5), (6, 9), (10, 13)):
            ws.merge_cells(start_row=row, start_column=a, end_row=row, end_column=b)
        row += 1

        def setting_row(rr, x, strong):
            for a, b in ((2, 5), (6, 9), (10, 13)):
                ws.merge_cells(start_row=rr, start_column=a, end_row=rr, end_column=b)
            put(ws, rr, 2, x["setting"], font=F_BOLD if strong else F_NOTE, align=MIDDLE)
            put(ws, rr, 6, x["a"], font=F_DATA if strong else F_NOTE, align=Alignment(vertical="center",
                                                                                         wrap_text=True))
            put(ws, rr, 10, x["b"], font=F_BOLD if strong else F_NOTE,
                align=Alignment(vertical="center", wrap_text=True))
            if strong:
                for col in range(10, 14):
                    ws.cell(rr, col).fill = K.solid(K.MIST)
            ws.row_dimensions[rr].height = 18 if max(len(x["a"]), len(x["b"])) < 50 else 30
            rule(ws, rr, 2, 13)
        differ = [x for x in whatif["settings"] if x["differs"]]
        alike = [x for x in whatif["settings"] if not x["differs"]]
        for x in differ:
            setting_row(row, x, True)
            row += 1
        if not differ:
            put(ws, row, 2, "None: the two files give the same answers, so every rating is the same.", font=F_BOLD)
            row += 1
        if alike:
            put(ws, row, 2, "The other %d settings are the same in both (folded away below)." % len(alike),
                font=F_NOTE)
            row += 1
            start = row
            for x in alike:
                setting_row(row, x, False)
                row += 1
            ws.row_dimensions.group(start, row - 1, outline_level=1, hidden=True)
        row += 1

        # the grid, national readings, with the counts drawn beside it
        row = section(ws, row, "National readings: the rating as you have it against the what-if rating", last)
        grid = [[0] * 5 for _ in range(5)]
        for x in both:
            grid[x["a"]["rating"] - 1][x["b"]["rating"] - 1] += 1
        top = row + 1
        ws.merge_cells(start_row=top, start_column=6, end_row=top, end_column=10)
        put(ws, top, 6, "WHAT IF", font=F_FIELD, align=CENTER)
        put(ws, top + 1, 5, "AS YOU HAVE IT", font=F_FIELD, align=Alignment(horizontal="right", vertical="center"))
        for k in range(1, 6):
            chip(ws, top + 1, 5 + k, k, short=True)
            chip(ws, top + 1 + k, 5, k, short=True)
            for j in range(1, 6):
                n = grid[k - 1][j - 1]
                c = put(ws, top + 1 + k, 5 + j, n if (n or j == k) else None, "#,##0",
                        font=F_BOLD if j == k else F_DATA, align=CENTER)
                if j == k:
                    c.fill = K.solid(K.CANVAS)
                elif n:
                    c.fill = K.solid(K.HEAT_GOOD if j < k else K.HEAT_BAD if j - k >= 2 else K.HEAT_WARM)
            put(ws, top + 1 + k, 11, sum(grid[k - 1]), "#,##0", F_BOLD, CENTER)
            put(ws, top + 7, 5 + k, sum(g[k - 1] for g in grid), "#,##0", F_BOLD, CENTER)
        put(ws, top + 1, 11, "Total", font=F_FIELD, align=CENTER)
        put(ws, top + 7, 5, "Total", font=F_FIELD, align=Alignment(horizontal="right", vertical="center"))
        put(ws, top + 7, 11, len(both), "#,##0", F_BOLD, CENTER)
        for rr in range(top, top + 8):
            ws.row_dimensions[rr].height = 20
        for col in range(5, 12):
            ws.cell(top + 6, col).border = Border(bottom=side("thin", K.STONE))
        # the chart's own numbers, hidden beside the table
        put(ws, top, 16, "Rating", font=F_NOTE)
        put(ws, top, 17, "As you have it", font=F_NOTE)
        put(ws, top, 18, "What if", font=F_NOTE)
        for k in range(1, 6):
            ws.cell(top + k, 16, SHORT[k])
            ws.cell(top + k, 17, sum(grid[k - 1]))
            ws.cell(top + k, 18, sum(g[k - 1] for g in grid))
        for col in (16, 17, 18):
            ws.column_dimensions[L(col)].hidden = True
        bar = BarChart()
        bar.type, bar.grouping, bar.gapWidth, bar.overlap = "col", "clustered", 60, -10
        bar.add_data(Reference(ws, min_col=17, max_col=18, min_row=top, max_row=top + 5), titles_from_data=True)
        bar.set_categories(Reference(ws, min_col=16, min_row=top + 1, max_row=top + 5))
        for s_, colour in zip(bar.series, (K.INK, K.KEY_RED)):
            s_.graphicalProperties.solidFill = colour
            s_.graphicalProperties.line.noFill = True
        bar.dataLabels = DataLabelList()
        bar.dataLabels.showVal = True
        bar.dataLabels.showSerName = bar.dataLabels.showCatName = bar.dataLabels.showLegendKey = False
        bar.dataLabels.txPr = text(9, K.INK_TEXT, True)
        for ax in (bar.x_axis, bar.y_axis):
            ax.delete = False
            ax.majorGridlines = None
            ax.spPr = GraphicalProperties(ln=ln(K.STONE, 0.75))
            ax.txPr = text()
        bar.y_axis.delete = True
        bar.legend = Legend()
        bar.legend.position = "b"
        bar.legend.txPr = text(9, K.INK_TEXT)
        bar.title = "National readings at each rating"
        bar.title.tx.rich.p[0].pPr = ParagraphProperties(defRPr=CharacterProperties(sz=1000, b=True,
                                                                                      solidFill=K.INK))
        bar.visible_cells_only = False
        bar.height, bar.width = 5.6, 11.6
        bar.roundedCorners = False
        bar.graphical_properties = GraphicalProperties(ln=LineProperties(noFill=True))
        ws.add_chart(bar, "B%d" % top)
        row = top + 9

        heads = ["Series", "Reading", "Latest", "Value", "Rating", "Percentile", "History from", "Readings",
                 "Rating", "Percentile", "History from", "Readings", "Move"]

        def groups(rr):
            for a, b, words in ((6, 9, "As you have it"), (10, 13, "What if")):
                ws.merge_cells(start_row=rr, start_column=a, end_row=rr, end_column=b)
                for col in range(a, b + 1):
                    c = ws.cell(rr, col)
                    c.fill = K.solid(K.ONYX)
                    c.border = Border(left=side("thin", K.PAPER) if col == a else None)
                c = ws.cell(rr, a, words)
                c.font, c.alignment = Font(name="Arial", bold=True, size=9, color=K.PAPER), CENTER
            ws.row_dimensions[rr].height = 16
            return header(ws, rr + 1, heads, right=(2, 3, 5, 7, 9, 11), centre=(4, 6, 8, 10, 12), height=18)

        def reading_row(rr, x):
            item = items[x["key"]]
            name = item.title
            link(ws.cell(rr, 2), "States" if x["key"] in state_keys else TAB[x["key"]], name)
            if x["same_measure"]:
                put(ws, rr, 3, reading_name(x["reading"], months), font=F_NOTE)
                one = x["a"] or x["b"]
                put(ws, rr, 4, _date(one["date"]), "yyyy-mm-dd")
                v, fmt = change_value(item, one["value"]) if x["reading"] == "change" else (
                    one["value"], value_format(one["value"]))
                put(ws, rr, 5, v, fmt)
            else:
                # Two different changes: each side's rating is of its own, so neither value is shown as shared.
                put(ws, rr, 3, reading_label("change", whatif["months"]).capitalize(), font=F_NOTE,
                    align=Alignment(vertical="center", wrap_text=True))
            for col, got in ((6, x["a"]), (10, x["b"])):
                if got:
                    chip(ws, rr, col, got["rating"], short=True)
                    put(ws, rr, col + 1, got["percentile"] / 100, "0.0%")
                    put(ws, rr, col + 2, _date(got["history_from"]), "yyyy-mm", align=CENTER)
                    put(ws, rr, col + 3, got["readings"], "#,##0")
                else:
                    ws.merge_cells(start_row=rr, start_column=col, end_row=rr, end_column=col + 3)
                    put(ws, rr, col, "Not rated: " + x["why_missing"], font=F_NOTE, align=WRAP)
            if x["move"]:
                put(ws, rr, 14, ("▲ %d" if x["move"] > 0 else "▼ %d") % abs(x["move"]),
                    font=F_UP if x["move"] > 0 else F_DOWN, align=CENTER)
            elif x["move"] == 0:
                put(ws, rr, 14, "same", font=F_NOTE, align=CENTER)
            ws.row_dimensions[rr].height = 18 if x["same_measure"] else 28
            rule(ws, rr, 2, last)

        def ordered(rows_):
            return sorted(rows_, key=lambda x: ([t for t, _ in TOPICS].index(topic_of[x["key"]])
                                               if x["key"] in topic_of else 99,
                                               -abs(x["move"] or 0), x["title"], x["reading"] != "position"))

        changed = ordered([x for x in nat if x["move"]])
        row = section(ws, row, "National readings that change rating (%d)" % len(changed), last)
        row = groups(row)
        if not changed:
            put(ws, row, 2, "None: every national reading takes the same rating under both.", font=F_BOLD)
            row += 1
        topic = None
        for x in changed:
            if topic_of.get(x["key"]) != topic:
                topic = topic_of.get(x["key"])
                for col in range(2, last + 1):
                    ws.cell(row, col).fill = K.solid(K.CANVAS)
                put(ws, row, 2, topic, font=Font(name="Arial", bold=True, size=9, color=K.SLATE))
                row += 1
            reading_row(row, x)
            row += 1
        row += 1
        st_changed = sorted([x for x in sts if x["move"]], key=lambda x: (-abs(x["move"]), x["title"]))
        row = section(ws, row, "State readings that change rating (%d of %d)" % (
            len(st_changed), sum(1 for x in sts if x["move"] is not None)), last)
        row = groups(row)
        if not st_changed:
            put(ws, row, 2, "None: every state reading takes the same rating under both.", font=F_BOLD)
            row += 1
        for x in st_changed:
            reading_row(row, x)
            row += 1
        row += 1
        one_side = [x for x in whatif["rows"] if x["move"] is None]
        if one_side:
            row = section(ws, row, "Rated under one set of settings only (%d)" % len(one_side), last)
            row = groups(row)
            for x in ordered(one_side):
                reading_row(row, x)
                row += 1
            row += 1
        same = ordered([x for x in nat if x["move"] == 0])
        row = section(ws, row, "National readings at the same rating under both (%d, folded away)" % len(same),
                      last)
        row = groups(row)
        start = row
        for x in same:
            reading_row(row, x)
            row += 1
        if same:
            ws.row_dimensions.group(start, row - 1, outline_level=1, hidden=True)
        ws.print_area = "A1:N%d" % row

    # -- States -----------------------------------------------------------
    ws = sheet("States")
    last = 11 if whatif else 10
    widths(ws, [8, 12, 14, 15, 11, 16, 15, 11, 11] + ([22] if whatif else []))
    title_band(ws, "Unemployment by state", "Bureau of Labor Statistics, Local Area Unemployment Statistics "
                                            "(LAUS), pulled %s." % vintage, last)
    link(ws.cell(2, 2), "Ratings", "Back to Ratings")
    entries = [("Rate", "The unemployment rate, seasonally adjusted, in percent; each state is rated against its "
                        "own history, as the national series are."),
               ("Level, Change", "Level: the latest rate against every month in the state's history. Change: the "
                                 "change over %d months, in points, against every such change." % months),
               ("Order", "By the higher of the state's two ratings, then by state.")]
    if whatif:
        entries.append(("What if", "Each reading whose rating differs under %s." % whatif["b"]))
    row = method_note(ws, 3, last, entries, label_cols=2)
    head = row
    row = header(ws, row, ["State", "Latest", "Unemployment rate", "Level", "Level percentile",
                           "Change over %d months" % months, "Change", "Change percentile", "History from"]
                 + (["What if"] if whatif else []), right=(1, 2, 4, 5, 7), centre=(3, 6, 8))

    def worst(st):
        got = by_key.get("unemployment_" + st.lower(), {})
        return -max([x["rating"] for x in got.values()] or [0])
    for st in sorted(STATES, key=lambda st: (worst(st), st)):
        key = "unemployment_" + st.lower()
        got = by_key.get(key, {})
        lvl, chg = got.get("position"), got.get("change")
        put(ws, row, 2, st)
        if lvl:
            put(ws, row, 3, _date(lvl["date"]), "yyyy-mm")
            put(ws, row, 4, lvl["value"], "0.0")
            chip(ws, row, 5, lvl["rating"])
            put(ws, row, 6, lvl["percentile"] / 100, "0.0%")
            put(ws, row, 10, _date(lvl["history_from"]), "yyyy-mm", align=CENTER)
        if chg:
            put(ws, row, 7, chg["value"], "+0.0;-0.0;0.0")
            chip(ws, row, 8, chg["rating"])
            put(ws, row, 9, chg["percentile"] / 100, "0.0%")
        if not got:
            put(ws, row, 3, "not in this pull", font=F_NOTE)
        if whatif:
            mine = list(wrows.get(key, {}).values())
            words = move_text(mine, whatif["months"])
            put(ws, row, 11, words or ("same rating" if mine else "not rated under either"),
                font=moved_font(mine) if words else F_NOTE)
        rule(ws, row, 2, last)
        row += 1
    ws.freeze_panes = ws.cell(head + 1, 3)

    # -- one sheet per national series --------------------------------------
    def years_axis(dates, frequency):
        """A date axis labelled every 1, 2, 5 or 10 years, at most ten labels. On a text axis LibreOffice
        ignores the label skip and prints nearly every year (the walk of 16 Oct 2026)."""
        from openpyxl.chart.axis import DateAxis
        span = max(1, int(dates[-1][:4]) - int(dates[0][:4]))
        ax = DateAxis(crossAx=100)
        ax.number_format = "yyyy"
        ax.majorTimeUnit = "years"
        ax.majorUnit = next(k for k in (1, 2, 5, 10, 20) if span / k <= 10)
        ax.baseTimeUnit = "months" if frequency in ("monthly", "quarterly") else "days"
        ax.delete = False
        ax.majorGridlines = None
        ax.spPr = GraphicalProperties(ln=ln(K.STONE, 0.75))
        ax.txPr = text()
        ax.tickLblPos = "low"
        return ax

    def banded_chart(ws, title, unit, data_col, first, last, helper_col, r, frequency, dashed_col=None):
        """History line over the five rating bands, with the latest reading marked, and the what-if's lines
        dashed when there are any.

        The bands are the chart underneath and the lines are laid over them:
        LibreOffice draws in the order charts are combined, Excel draws areas
        first whatever the order, so this order reads the same in both."""
        area = AreaChart()
        area.grouping = "stacked"
        area.add_data(Reference(ws, min_col=helper_col, max_col=helper_col + 5, min_row=first - 1, max_row=last),
                      titles_from_data=True)
        cats = Reference(ws, min_col=14, min_row=first, max_row=last)
        area.set_categories(cats)
        area.series[0].graphicalProperties.noFill = True
        area.series[0].graphicalProperties.line.noFill = True
        for i, s_ in enumerate(area.series[1:]):
            s_.graphicalProperties.solidFill = K.BANDS[r["order"][i] - 1]
            s_.graphicalProperties.line.noFill = True
        line = LineChart()
        line.add_data(Reference(ws, min_col=data_col, min_row=first - 1, max_row=last), titles_from_data=True)
        # Every series carries its own dates. Without them Excel places a line on 1, 2, 3 ... of a date axis,
        # 1900, while LibreOffice borrows the area's (Fable's report on #452, not checked in Excel).
        line.set_categories(cats)
        hist = line.series[0]
        hist.graphicalProperties.line = ln(K.INK, 2.0)
        hist.marker.symbol = "none"
        hist.smooth = False
        dashed = None
        if dashed_col:
            dashed = LineChart()
            dashed.add_data(Reference(ws, min_col=dashed_col, max_col=dashed_col + 3, min_row=first - 1,
                                      max_row=last), titles_from_data=True)
            dashed.set_categories(cats)
            for s_, colour in zip(dashed.series, K.LINES):
                s_.graphicalProperties.line = ln(colour, 1.25, "dash")
                s_.marker.symbol = "none"
                s_.smooth = False
        latest = LineChart()
        latest.add_data(Reference(ws, min_col=helper_col + 6, min_row=first - 1, max_row=last), titles_from_data=True)
        latest.set_categories(cats)
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
        area.x_axis = years_axis([ws.cell(first, 14).value.isoformat(), ws.cell(last, 14).value.isoformat()],
                                 frequency)
        for chart_ in (area, line, latest) + ((dashed,) if dashed else ()):
            chart_.x_axis = area.x_axis           # one axis for every layer, or the lines drift off the bands
            # and the value axis crosses that axis: left at its default (10, an axis this chart does not have),
            # Excel refused the whole file (17 Oct 2026); LibreOffice drew it anyway
            chart_.y_axis.crossAx = area.x_axis.axId
        ax = area.y_axis
        ax.delete = False
        ax.majorGridlines = None
        ax.spPr = GraphicalProperties(ln=ln(K.STONE, 0.75))
        ax.txPr = text()
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
        if dashed:
            area += dashed
        area += latest
        return area

    for key in national:
        item = items[key]
        mine = by_key.get(key, {})
        ws = sheet(TAB[key])
        widths(ws, [18, 13, 13, 13, 13, 18, 13, 13, 13, 13, 13, 2.71, 12, 13, 13, 22, 12, 9])
        source = BY_KEY.get(key)
        title_band(ws, item.title, "%s · %s · %s · pulled %s" % (
            source.publisher if source else "made from two series", item.unit, item.frequency, vintage), 17)
        link(ws.cell(2, 2), "Ratings", "Back to Ratings")
        if whatif:
            link(ws.cell(2, 4), "What if", "What if")
        row = 4
        tall = 4 if whatif else 3
        for j, reading in enumerate(("position", "change")):
            col = 2 + 5 * j
            end = col + 4
            for rr in range(row, row + tall):
                for cc in range(col, end + 1):
                    ws.cell(rr, cc).fill = K.solid(K.CANVAS)
            for cc in range(col, end + 1):
                ws.cell(row, cc).border = Border(top=side("thick", K.KEY_RED))
            put(ws, row, col, reading_name(reading, months).upper(), font=F_FIELD, align=MIDDLE)
            r = mine.get(reading)
            if r:
                chip(ws, row + 1, col, r["rating"], size=11)
                v, fmt = change_value(item, r["value"]) if reading == "change" else (r["value"],
                                                                                   value_format(r["value"]))
                put(ws, row + 1, col + 1, v, fmt, F_BIG, Alignment(horizontal="right", vertical="center"))
                put(ws, row + 1, col + 2, _date(r["date"]), "yyyy-mm-dd", F_NOTE,
                    Alignment(horizontal="left", vertical="center", indent=1))
                note(ws, row + 2, col, r["sentence"], end, F_DATA)
            elif reading == "position" and item.position:
                put(ws, row + 1, col, "change only", font=F_NOTE, align=MIDDLE)
                note(ws, row + 2, col, "Change only: " + item.position + ".", end)
            elif reading not in readings_of(item, s["change_for"]):
                # Not a failure: the firm's settings rate the change only of the series they list.
                put(ws, row + 1, col, "level only", font=F_NOTE, align=MIDDLE)
                note(ws, row + 2, col, "Not asked for: the firm's settings rate this series on its level only.", end)
            else:
                note(ws, row + 2, col, "Not rated: see the Not rated tab.", end)
            w = wrows.get(key, {}).get(reading)
            if w:
                put(ws, row + 3, col, "WHAT IF", font=F_FIELD, align=MIDDLE)
                if w["b"]:
                    b = w["b"]
                    chip(ws, row + 3, col + 1, b["rating"], short=True)
                    noun = "readings" if reading == "position" else "changes" if w["same_measure"] else \
                        "changes over %s" % b_months
                    if w["move"] is None:
                        words = "Rated under the what-if only: %.1f%% of %s %s since %s." % (
                            b["percentile"], "{:,}".format(b["readings"]), noun, when(b["history_from"]))
                    elif w["move"] == 0:
                        words = "Same rating: %.1f%% of %s %s since %s." % (
                            b["percentile"], "{:,}".format(b["readings"]), noun, when(b["history_from"]))
                    else:
                        a = w["a"]
                        words = "%s %d: %.1f%% of %s %s since %s (as you have it, %.1f%% of %s since %s)." % (
                            "Up" if w["move"] > 0 else "Down", abs(w["move"]), b["percentile"],
                            "{:,}".format(b["readings"]), noun, when(b["history_from"]), a["percentile"],
                            "{:,}".format(a["readings"]), when(a["history_from"]))
                    note(ws, row + 3, col + 2, words, end, F_UP if (w["move"] or 0) > 0 else F_DOWN if
                         (w["move"] or 0) < 0 else F_DATA)
                else:
                    note(ws, row + 3, col + 1, "Not rated under the what-if: %s." % w["why_missing"], end)
        ws.row_dimensions[row].height = 16
        ws.row_dimensions[row + 1].height = 24
        said = [mine[rd]["sentence"] for rd in mine] + ["Change only: " + (item.position or "")]
        ws.row_dimensions[row + 2].height = 14 * max(math.ceil(len(x) / (width_of(ws, 2, 6) * 1.2)) for x in said) + 4
        if whatif:
            ws.row_dimensions[row + 3].height = 30
        row += tall + 1

        drawn = [rd for rd in ("position", "change") if (wrows.get(key, {}).get(rd) or {}).get("b")
                 and wrows[key][rd]["same_measure"] and mine.get(rd)]
        entries = [("The charts", "The history in black over five shaded bands, one for each rating, from 1 Low "
                                  "(lightest) to 5 High (darkest), as these settings place them. The circle is the "
                                  "latest reading.")]
        if drawn:
            entries.append(("Dashed lines", "Where ratings 2, 3, 4 and 5 start under %s, drawn over the years that "
                                            "history covers." % whatif["b"]))
        entries += [("Rating starts", "Where each rating starts: the least extreme reading in this history that "
                                      "took it, and how many readings took it."),
                    ("History", "Every reading, with its change over %d months, is in columns N to Q. A period the "
                                "publisher left blank stays empty and reads no value published." % months)]
        row = method_note(ws, row, 12, entries)

        # where each rating starts, and how many readings took it
        row = section(ws, row, "Where each rating starts", 12)
        def sides(reading):
            """This run's rating of the reading and the what-if's, either of them None when that run did not
            rate it. Codex on #452: a reading only the what-if rates still shows where its ratings start."""
            w = wrows.get(key, {}).get(reading)
            return mine.get(reading), (w["b"] if w else None)

        head_cols = ["Rating"]
        for reading in ("position", "change"):
            r, b = sides(reading)
            noun = "Level" if reading == "position" else "Change"
            if r:
                head_cols += ["%s from" % noun, "Readings" if reading == "position" else "Changes"]
            if b:
                head_cols.append("What if: %s from" % (noun.lower() if reading == "position" or
                                                       wrows[key][reading]["same_measure"] else
                                                       "change over %s" % b_months))
        row = sub_header(ws, row, head_cols, right=tuple(range(1, len(head_cols))))
        for k in range(1, 6):
            chip(ws, row, 2, k)
            col = 3
            for reading in ("position", "change"):
                pct = reading == "change" and item.change_in == "percent"
                for side_, got in zip("ab", sides(reading)):
                    if not got:
                        continue
                    edge = got["lines"][str(k)] if k > 1 else None
                    if k == 1:
                        put(ws, row, col, "below 2" if got["direction"] == HIGHER else "above 2", font=F_NOTE,
                            align=Alignment(horizontal="right", vertical="center"))
                    elif edge is None:
                        put(ws, row, col, "not reached", font=F_NOTE,
                            align=Alignment(horizontal="right", vertical="center"))
                    else:
                        put(ws, row, col, edge / 100 if pct else edge, "#,##0.0#%" if pct else value_format(edge),
                            F_DATA if side_ == "a" else F_BOLD)
                    col += 1
                    if side_ == "a":
                        put(ws, row, col, got["counts"][str(k)], "#,##0")
                        col += 1
            rule(ws, row, 2, 2 + len(head_cols) - 1)
            row += 1
        row += 1

        # the history, on the right: Date, Value, Change, Note; hidden helper columns for the bands
        points = pull.points(item)
        if isinstance(points, str) or not any(v is not None for _, v in points):
            # Nothing to draw: said, not drawn (Fable on #452: a file of headers only crashed the Sahm chart).
            put(ws, row, 2, points if isinstance(points, str) else
                "The pull of %s holds no values for this series." % vintage, font=F_NOTE)
            ws.print_area = "A1:L%d" % row
            continue
        chg = dict(changes(points, months, item.frequency, item.change_in))
        ws.row_breaks.append(Break(id=row - 1))     # printed, the charts start a page of their own
        top = row          # beside the first chart, below the tall rows at the top
        header(ws, top, ["Date", "Value", "Change over %d months" % months, "Note"], first=14, right=(1, 2))
        first = top + 1
        dates = []
        for i, (d, v) in enumerate(points):
            rr = first + i
            dates.append(_date(d).isoformat())
            put(ws, rr, 14, _date(d), "yyyy-mm-dd")
            # A missing value stays an empty cell: text there would be drawn
            # as zero on the chart, the very error the readers are kept from.
            if v is not None:
                put(ws, rr, 15, v, value_format(v))
            else:
                put(ws, rr, 17, "no value published", font=F_NOTE)
            if dates[-1] in chg:
                put(ws, rr, 16, chg[dates[-1]], "#,##0.0#")
        last = first + len(points) - 1

        helper = 20                                 # T onwards, hidden
        for n_reading, (reading, data_col) in enumerate((("position", 15), ("change", 16))):
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
                put(ws, top, helper + j, name, font=F_NOTE)
            latest_row = first + dates.index(_date(r["date"]).isoformat())
            for rr in range(first, last + 1):
                ws.cell(rr, helper, base)
                for j, h in enumerate(heights):
                    ws.cell(rr, helper + 1 + j, h)
            # Rounded here: LibreOffice ignores a label's own number format.
            ws.cell(latest_row, helper + 6, round(ws.cell(latest_row, data_col).value, 2))
            for j in range(7):
                ws.column_dimensions[L(helper + j)].hidden = True
            dashed_col = None
            if reading in drawn:
                # The what-if's lines: one column for each of 2 to 5, filled over the years its history covers.
                b = wrows[key][reading]["b"]
                dashed_col = WHAT_IF_LINES + 4 * n_reading
                start = _date(b["history_from"]).isoformat()
                for j, k in enumerate(range(2, 6)):
                    put(ws, top, dashed_col + j, "What if: %d from" % k, font=F_NOTE)
                    ws.column_dimensions[L(dashed_col + j)].hidden = True
                    edge = b["lines"][str(k)]
                    if edge is None:
                        continue
                    for i, d in enumerate(dates):
                        if d >= start:
                            ws.cell(first + i, dashed_col + j, edge)
            title = ("Level against its history" if reading == "position" else
                     "Change over %d months against its history" % months)
            if dashed_col:
                title += " (dashed: where 2 to 5 start under the what-if)"
            chart = banded_chart(ws, title, item.unit if reading == "position" else
                                 ("percent" if item.change_in == "percent" else "points"),
                                 data_col, first, last, helper, r, item.frequency, dashed_col)
            ws.add_chart(chart, "B%d" % row)
            row += 18
            helper += 7

        sahm_drawn = key == "unemployment" and s["show_sahm"]
        if sahm_drawn:
            ws.row_breaks.append(Break(id=row - 1))     # printed, the chart starts a page whole
            sv = dict(sahm(points))
            header(ws, top, ["Sahm reading", "Trigger"], first=18, right=(0, 1))
            for i, d in enumerate(dates):
                if d in sv:
                    put(ws, first + i, 18, sv[d], "0.00")
                    ws.cell(first + i, 19, 0.50)
            sc = LineChart()
            sc.add_data(Reference(ws, min_col=18, max_col=19, min_row=top, max_row=last), titles_from_data=True)
            sc.set_categories(Reference(ws, min_col=14, min_row=first, max_row=last))
            sc.series[0].graphicalProperties.line = ln(K.INK, 1.5)
            sc.series[1].graphicalProperties.line = ln(K.CRIMSON, 1.25, "sysDash")
            for s_ in sc.series:
                s_.marker.symbol = "none"
                s_.smooth = False
            sc.x_axis = years_axis(dates, "monthly")
            sc.y_axis.crossAx = sc.x_axis.axId
            sc.y_axis.delete = False
            sc.y_axis.majorGridlines = None
            sc.y_axis.spPr = GraphicalProperties(ln=ln(K.STONE, 0.75))
            sc.y_axis.txPr = text()
            sc.title = "Sahm reading (shown, not rated): dashed line at Sahm's trigger, 0.50"
            sc.title.tx.rich.p[0].pPr = ParagraphProperties(defRPr=CharacterProperties(sz=1000, b=True,
                                                                                        solidFill=K.INK))
            sc.legend = None
            sc.display_blanks = "gap"
            sc.height, sc.width = 8.5, 24
            sc.roundedCorners = False
            sc.graphical_properties = GraphicalProperties(ln=LineProperties(noFill=True))
            ws.add_chart(sc, "B%d" % row)
            row += 18

        if not sahm_drawn:
            ws.row_breaks.append(Break(id=row - 1))
        row = section(ws, row, "What it is", 12)
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
        for when_, what in item.breaks:
            facts.append(("Break", "%s: %s" % (when_, what)))
        for k, v in facts:
            put(ws, row, 2, k, font=F_BOLD, align=WRAP)
            ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=12)
            put(ws, row, 3, v, align=WRAP)
            ws.row_dimensions[row].height = 15 * (1 + len(v) // 120)
            rule(ws, row, 2, 12)
            row += 1
        # Printed, a tab is its ratings, charts and facts; its history stays on screen.
        ws.print_area = "A1:L%d" % row

    # -- State data ---------------------------------------------------------
    ws = sheet("State data")
    widths(ws, [11] + [7] * len(STATES))
    title_band(ws, "Unemployment rate by state, month by month",
               "Percent. An empty cell is a month with no value published (October 2025: the lapse in "
               "appropriations).", 1 + 1 + len(STATES), record=True)
    head = 3
    row = sub_header(ws, head, ["Date"] + list(STATES), right=tuple(range(1, len(STATES) + 1)), height=18)
    columns = {}
    for j, st in enumerate(STATES, 3):
        pts = pull.points(BY_KEY["unemployment_" + st.lower()])
        columns[j] = dict(pts) if not isinstance(pts, str) else {}
    for d in sorted({d for c in columns.values() for d in c}):
        put(ws, row, 2, _date(d), "yyyy-mm")
        for j, c in columns.items():
            if d in c and c[d] is not None:
                put(ws, row, j, c[d], "0.0")
        row += 1
    ws.freeze_panes = ws.cell(head + 1, 3)

    # -- Not rated ----------------------------------------------------------
    if result["not_rated"]:
        ws = sheet("Not rated")
        widths(ws, [44, 24, 90])
        title_band(ws, "Not rated", "Each reading the settings call for that has no rating, and why.", 4,
                   record=True)
        row = sub_header(ws, 3, ["Series", "Reading", "Why"], height=18)
        for x in result["not_rated"]:
            for j, v in enumerate((items[x["key"]].title, reading_name(x["reading"], months), x["why"]), 2):
                put(ws, row, j, v)
            rule(ws, row, 2, 4)
            row += 1

    # -- Glossary -----------------------------------------------------------
    ws = sheet("Glossary")
    widths(ws, [30, 120])
    title_band(ws, "Glossary", "Every term in this workbook, and how it is worked out.", 3, record=True)
    row = sub_header(ws, 3, ["Term", "What it means, and how it is worked out"], height=18)
    for term, meaning in glossary(s, whatif):
        put(ws, row, 2, term, font=F_BOLD, align=WRAP)
        put(ws, row, 3, meaning, align=WRAP)
        ws.row_dimensions[row].height = 14 * (1 + len(meaning) // 130) + 3
        rule(ws, row, 2, 3)
        row += 1

    # -- Run ----------------------------------------------------------------
    ws = sheet("Run")
    widths(ws, [42, 40] + ([40] if whatif else []) + [90])
    last = 5 if whatif else 4
    title_band(ws, "Run", "What went into this workbook.", last, record=True)
    row = 3
    # The fingerprint of each file's bytes as the rating read them, not as the manifest recorded it at the pull
    # (Fable on #452: a file changed after the pull was rated as changed and published with the old fingerprint),
    # and not as the file is when the workbook is built (Codex on #452: the ratings come from the bytes read).
    from .pull import file_name
    files = pull.manifest.get("files", {})
    read_sha = pull.read_sha
    changed = [n for n, h in read_sha.items() if files.get(n, {}).get("sha256") not in (None, h)]
    facts = [("Built", datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")),
             ("From the pull of", vintage), ("Tool", "threshold-engine %s, economic conditions" % VERSION),
             ("Readings rated", len(result["ratings"])), ("Readings not rated", len(result["not_rated"])),
             ("Files changed since the pull", "%d: see Sources" % len(changed) if changed else "none")]
    if whatif:
        facts += [("Settings file", whatif["a"]), ("What-if file", whatif["b"])]
    for k, v in facts:
        put(ws, row, 2, k, font=F_FIELD)
        put(ws, row, 3, v, align=Alignment(horizontal="left"))
        rule(ws, row, 2, 3)
        row += 1
    row += 1
    row = sub_header(ws, row, ["Setting", "The firm's answer"] + (["What if"] if whatif else []) + ["The question"],
                     height=18)
    asked = {q[0]: q[1] for q in QUESTIONS}
    if whatif:
        rows = [(x["setting"], x["a"], x["b"], asked[x["name"]]) for x in whatif["settings"]]
    else:
        rows = [(CALLED[n], plain(n, s), asked[n]) for n in CALLED]
        rows += [("Which way is worse: %s, %s" % (items[k].title, reading_name(rd, months).lower()), d,
                  asked["directions"]) for k, rd, d in s["directions"]]
    for vals in rows:
        for j, v in enumerate(vals, 2):
            put(ws, row, j, v, align=WRAP, font=F_BOLD if whatif and j == 4 and vals[1] != vals[2] else None)
        ws.row_dimensions[row].height = 30
        rule(ws, row, 2, last)
        row += 1

    # -- Sources ------------------------------------------------------------
    ws = sheet("Sources")
    widths(ws, [44, 36, 30, 34, 13, 28, 60, 26, 66, 44])
    title_band(ws, "Sources", "Every file the pull fetched, and its fingerprint as the rating read it.", 11,
               record=True)
    row = sub_header(ws, 3, ["Series", "Publisher", "Id at the source", "Licence", "First reading", "File", "Address",
                             "Fetched", "SHA-256 as read", "Since the pull"], height=18)
    for x in SERIES:
        name = file_name(x)
        f = files.get(name, {})
        for j, v in enumerate((x.title, x.publisher, x.source_id, x.licence, x.starts, name, f.get("url", ""),
                               f.get("fetched_at", f.get("error", "not in this pull")),
                               read_sha.get(name, f.get("sha256", ""))), 2):
            put(ws, row, j, v)
        ws.cell(row, 10).font = Font(name="Consolas", size=9, color=K.SLATE)
        if name in changed:
            put(ws, row, 11, "changed after the pull, which recorded %s…" % f["sha256"][:16],
                font=Font(name="Calibri", size=10, bold=True, color=K.CRIMSON))
        rule(ws, row, 2, 11)
        row += 1
    for d in DERIVED:
        put(ws, row, 2, d.title)
        put(ws, row, 3, "made from " + " and ".join(BY_KEY[k].title for k in d.inputs))
        rule(ws, row, 2, 11)
        row += 1
    ws.freeze_panes = ws.cell(4, 3)

    wb.save(out)
    return out


def glossary(s, whatif=None):
    """Every term the workbook uses, worded from the settings the run used."""
    c, m = s["cutoffs"], s["change_months"]
    terms = [
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
    if whatif:
        terms += [
            ("As you have it", "The ratings from the firm's settings file, %s: every rating on every other tab."
             % whatif["a"]),
            ("What if", "The same pull rated with a second settings file, %s. It changes no rating anywhere else in "
                        "the workbook, and neither file is changed." % whatif["b"]),
            ("Move", "The what-if rating minus the rating as you have it. ▲ is a higher rating, ▼ a lower one."),
            ("Dashed lines", "On a series' chart: where ratings 2 to 5 start under the what-if, over the years its "
                             "history covers. Drawn only where the two measure the same thing."),
        ]
    return terms
