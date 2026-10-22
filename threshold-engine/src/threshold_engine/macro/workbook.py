"""The workbook the consumer and commercial teams read.

Made only from a finished run of readings, so it cannot exist without the
firm's settings. Nothing in it is rated (the firm, 22 Oct 2026: "We are not
rating these. At most these are directional"): each series shows where its
level sits in its own history and whether its change is Increasing, Stable or
Decreasing against its normal movement. Every number is a value written by
Python. Outside the Dashboard nothing is a formula, so nothing moves after it
is written; the Dashboard's formulas only look up values written on its
hidden data tab, so the firm can pick which two series it draws.

Its look is PocketBook's workbook (pocketbook/docs/redesign-2026-09-26, built
in pocketbook/src/pocketbook/house.py): a dark title band with the red rule
under it, one "How this tab works" note per tab that folds away, tiles for the
headline figures, dark section bands, and tabs coloured for what they hold
(results dark, the record grey). Its charts follow Claude Design's for the
threshold workbook (docs/design/HANDOFF.md, in keybank_style.py): the history
in ink, the latest reading ringed and labelled, the normal range shaded behind
a change, and a second set of settings drawn as dashed lines.

    Overview          every core series by topic: where its level sits, its
                      change against its normal range, and which way it reads
    Dashboard         pick any two series: both changes in typical moves on one
                      chart, both levels as where they sit in their own history
                      on another, and each one's own charts
    What if           only with --compare: every reading under a second set of
                      settings, side by side with the first
    States            unemployment by state: level and change
    Household debt    the NY Fed's household debt by type, stacked as it
                      reports it, and each type's change
    Usable with care  the report's "usable with care" group, read the same
                      way, with why each needs care, and the rest of the group
    one per series    its level and change, its charts, what it is
    State data        every state's unemployment rate, month by month
    Not read          only when something could not be read, and why
    Glossary          every term, and how it is worked out
    Run               when it was built, from which pull, with which settings
    Sources           every file: address, licence, when fetched, SHA-256
    Dashboard data    hidden: the values the Dashboard looks up
"""
import datetime
import math

from .catalog import BY_KEY, CARE, CARE_NOT_READ, DERIVED, HOUSEHOLD_DEBT, READ, SERIES, STATES
from .compare import CALLED, NOT_ASKED, plain, row_label, spans, when
from .readings import DECREASING, DIRECTIONS, INCREASING, STABLE, changes, kept, percentile, sahm, window_of
from .settings import QUESTIONS, Refused, left_out_set, quarter_index, quarter_of, readings_of

ROW_RULE = "EFEBE4"      # PocketBook's one-pixel line between rows
ARROW = {INCREASING: "▲ Increasing", STABLE: "Stable", DECREASING: "▼ Decreasing"}
HOUSEHOLD_KEYS = [k for k, _, _ in HOUSEHOLD_DEBT]
#: What a series' tab says of the research's direction of stress: a fact about the research, not a rating.
RESEARCH = {"higher is worse": "Higher readings signal stress, the research says",
            "lower is worse": "Lower readings signal stress, the research says",
            None: "The research does not say which way it signals stress"}
HOUSEHOLD_NAME = "Household debt"
CARE_NAME = "Usable with care"
DASHBOARD = "Dashboard"
DASH_DATA = "Dashboard data"
#: The six types of household debt, in the NY Fed's order, coloured from the reference categorical palette
#: (dataviz skill), checked with its validator for adjacent pairs on 22 Oct 2026: every check passes; three
#: sit below 3:1 against white, so the tab carries a legend and the table of every type.
HOUSEHOLD_COLOURS = ("2A78D6", "EB6834", "1BAF7A", "EDA100", "E87BA4", "008300")
#: The Dashboard's two picks: the reference palette's first two slots, which pass every pair.
PICK_COLOURS = ("2A78D6", "EB6834")

#: The Overview's sections, in reading order, and each series' tab name.
TOPICS = [
    ("Jobs", ["unemployment", "initial_claims", "continuing_claims", "payrolls"]),
    ("Prices and insurance", ["cpi", "cpi_core", "gasoline", "motor_insurance", "used_cars", "home_insurance"]),
    ("Housing and household credit", ["house_prices", "house_price_to_income", "mortgage_rate", "mortgage_spread",
                                      "mortgage_30_89", "mortgage_90", "mortgage_90_government",
                                      "revolving_credit", "card_standards"] + HOUSEHOLD_KEYS),
    ("Business and the economy", ["real_gdp", "industrial_production", "capacity_use", "cfnai", "cre_prices",
                                  "ci_standards", "ci_demand"]),
    ("Markets and financial conditions", ["prime_rate", "gz_spread", "excess_bond_premium",
                                          "bond_recession_probability", "nfci", "nfci_adjusted", "stlfsi", "kcfsi",
                                          "yield_curve"]),
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
    "prime_rate": "Prime rate", "gz_spread": "Bond spread", "excess_bond_premium": "Excess bond premium",
    "bond_recession_probability": "Bond recession prob", "nfci": "NFCI", "nfci_adjusted": "NFCI adjusted",
    "stlfsi": "St Louis stress", "kcfsi": "Kansas City stress", "yield_curve": "Yield curve",
    **{k: HOUSEHOLD_NAME for k in HOUSEHOLD_KEYS},
}

#: The Usable with care tab's sections, and each series' tab name.
CARE_TOPICS = [
    ("Jobs and income", ["underemployment", "job_openings", "layoffs_rate", "quits_rate", "temp_help", "wages_eci",
                         "hourly_earnings", "real_income", "income_ex_transfers", "saving_rate"]),
    ("Household debt, credit and housing", ["debt_service", "debt_service_mortgage", "debt_service_consumer",
                                            "card_minimum_payment", "expected_missed_payment", "auto_standards",
                                            "other_consumer_standards", "new_home_supply"]),
    ("Business", ["equipment_orders", "business_applications", "likely_employer_applications",
                  "philadelphia_survey", "empire_survey", "dallas_survey", "cre_standards_construction",
                  "cre_standards_nonresidential", "cre_standards_multifamily", "customs_duties"]),
    ("Policy and markets", ["policy_uncertainty", "trade_policy_uncertainty", "vix"]),
]
CARE_TAB = {
    "underemployment": "Underemployment", "job_openings": "Job openings", "layoffs_rate": "Layoffs rate",
    "quits_rate": "Quits rate", "temp_help": "Temp help jobs", "wages_eci": "Wages (ECI)",
    "hourly_earnings": "Hourly earnings", "real_income": "Real income", "income_ex_transfers": "Income ex transfers",
    "saving_rate": "Saving rate", "debt_service": "Debt service", "debt_service_mortgage": "Mortgage debt service",
    "debt_service_consumer": "Consumer debt service", "card_minimum_payment": "Card minimum payments",
    "expected_missed_payment": "Expected missed payments", "auto_standards": "Auto loan standards",
    "other_consumer_standards": "Other consumer standards", "new_home_supply": "New home supply",
    "equipment_orders": "Equipment orders", "business_applications": "Business applications",
    "likely_employer_applications": "Likely-employer applications", "philadelphia_survey": "Philadelphia survey",
    "empire_survey": "Empire State survey", "dallas_survey": "Dallas survey",
    "cre_standards_construction": "CRE construction standards",
    "cre_standards_nonresidential": "CRE nonresidential standards",
    "cre_standards_multifamily": "CRE multifamily standards", "customs_duties": "Customs duties",
    "policy_uncertainty": "Policy uncertainty", "trade_policy_uncertainty": "Trade policy uncertainty",
    "vix": "VIX",
}


def tab_of(key):
    """The tab a series' name links to."""
    if key.startswith("unemployment_"):
        return "States"
    return TAB.get(key) or CARE_TAB[key]


def reading_name(reading, months):
    return "Level" if reading == "position" else "Change over %d months" % months


def _date(d):
    return datetime.date.fromisoformat(d[:10])


def _when(d, frequency):
    day = _date(d)
    if frequency == "quarterly":
        return "%d Q%d" % (day.year, (day.month - 1) // 3 + 1)
    if frequency == "monthly":
        return day.strftime("%b %Y")
    return "%d %s" % (day.day, day.strftime("%b %Y"))


def value_format(x):
    """Whole numbers with commas for big values; two decimals at most otherwise."""
    return "#,##0" if x is not None and abs(x) >= 1000 else "#,##0.0#"


def _num(x):
    a = abs(x)
    if a >= 1000:
        return "{:,.0f}".format(x)
    if a >= 1:
        return ("%.2f" % x).rstrip("0").rstrip(".")
    return "0" if x == 0 else "%.3g" % x


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


def axis_view(dated, cut, keep=()):
    """The axis a chart draws ``dated`` (date, value) on: from the value ``cut`` percent of the way up the
    readings to the one ``cut`` percent from the top, widened to hold every value in ``keep`` (the latest
    reading, a normal range), then rounded out to a tidy step. Returns (low, high, step, above, below), the
    last two the readings that run off each end. Only the view changes; no reading does."""
    values = sorted(v for _, v in dated)
    k = int(len(values) * cut / 100)
    lo, hi = values[k], values[len(values) - 1 - k]
    lo, hi = min([lo] + list(keep)), max([hi] + list(keep))
    a, b, step = nice_axis(lo, hi)
    return a, b, step, [(d, v) for d, v in dated if v > b], [(d, v) for d, v in dated if v < a]


def off_edge(above, below, frequency, fmt=_num):
    """The note under a chart that some readings run off its edge, naming the furthest of each end, with
    ``fmt`` saying a value in its unit."""
    parts = []
    for got, end, pick in ((above, "top", max), (below, "bottom", min)):
        if got:
            d, v = pick(got, key=lambda dv: dv[1])
            parts.append("%s %s off the %s, the %s %s %s %s" % (
                "{:,}".format(len(got)), "reading runs" if len(got) == 1 else "readings run", end,
                "highest" if end == "top" else "lowest", fmt(v), "on" if frequency in ("daily", "weekly") else "in",
                _when(d, frequency)))
    return ("Off the chart: %s. The axis leaves them off so the rest can be read; no reading changes."
            % "; ".join(parts)) if parts else ""


def move_text(rows, months):
    """How a series' readings stand under the what-if, as an Overview or States cell says it: each change
    whose direction differs, each reading read on one side only, and each asked for and read under neither.
    Empty when there is nothing to say, and the caller writes "same direction" or "not read under either"
    (Codex on #452: a row left out of the cell let a failed reading read as unchanged). ``months`` is each
    side's horizon; a change counted over different months names the what-if's when the what-if is the side
    reported (Fable on #452)."""
    if all(not (r["a"] or r["b"]) and r["why_a"] != NOT_ASKED and r["why_b"] != NOT_ASKED for r in rows):
        return ""                         # none, or every reading asked for under both and read under neither
    parts = []
    for r in rows:
        what = "Level" if r["reading"] == "position" else "Change"
        if r["a"] and r["b"]:
            if r["move"]:
                when_ = "" if r["same_measure"] else " (what if: over %d months)" % months[1]
                parts.append("%s %s → %s%s" % (what, r["a"]["direction"], r["b"]["direction"], when_))
        elif r["a"] or r["b"]:
            when_ = "" if r["same_measure"] or not r["b"] else " (what if: over %d months)" % months[1]
            parts.append("%s%s: read %s only" % (what, when_, "as you have it" if r["a"] else "under the what-if"))
        else:
            asked_a, asked_b = r["why_a"] != NOT_ASKED, r["why_b"] != NOT_ASKED
            when_ = "" if r["same_measure"] or not asked_b else " (what if: over %d months)" % months[1]
            parts.append("%s%s: not read %s" % (what, when_, "under either" if asked_a and asked_b else
                                                "as you have it" if asked_a else "under the what-if"))
    return "; ".join(parts)


def summary_text(rows, months):
    """The whole Overview or States cell for a series: what moved or failed, else that it reads the same."""
    return move_text(rows, months) or ("same direction" if any(r["a"] and r["b"] for r in rows) else
                                       "not read under either")


def zoom_rows(dates, zoom):
    """The first and last index of ``dates`` inside the zoom's quarters, or None when none is."""
    if not zoom:
        return (0, len(dates) - 1) if dates else None
    a, b = quarter_index(zoom[0]), quarter_index(zoom[1])
    inside = [i for i, d in enumerate(dates) if a <= quarter_index(quarter_of(d)) <= b]
    return (inside[0], inside[-1]) if inside else None


def excel_day(d):
    """A date as Excel counts days, for a value axis of dates."""
    return (_date(d) - datetime.date(1899, 12, 30)).days


def build(out, result, pull, whatif=None, zoom=None):
    """Write the workbook for one run of readings (``read_all``'s result) to ``out``.

    ``whatif`` is ``compare.compare``'s result for a second set of settings on
    the same pull; with it the workbook gains the What if tab, a column for it
    on Overview and States, and dashed lines on every change chart it applies
    to. ``zoom`` is two quarters, ["2019Q1", "2026Q2"]: every chart is drawn
    over them only, and nothing else changes. A what-if made from other bytes,
    or against other settings than this run's, is refused: every input is
    checked against one reading of the pull (Codex on #452)."""
    if result["vintage"] != pull.vintage:
        raise Refused("the readings are of the pull of %s and the Pull given is of %s: build from the Pull the "
                      "readings used." % (result["vintage"], pull.vintage))
    if whatif and (whatif["vintage"] != result["vintage"] or whatif["read_sha"] != result["read_sha"]
                   or whatif["baseline"] != result["settings"]):
        raise Refused("the what-if was not compared against these readings (another pull, other bytes of it, or "
                      "other settings as you have it). Compare these readings and build from the same Pull.")
    from openpyxl import Workbook
    from openpyxl.chart import AreaChart, BarChart, LineChart, Reference, ScatterChart, Series
    from openpyxl.chart.label import DataLabelList
    from openpyxl.chart.legend import Legend
    from openpyxl.chart.series import SeriesLabel, StrRef
    from openpyxl.chart.shapes import GraphicalProperties
    from openpyxl.chart.text import RichText
    from openpyxl.drawing.line import LineProperties
    from openpyxl.drawing.text import CharacterProperties, Paragraph, ParagraphProperties
    from openpyxl.styles import Alignment, Border, Font, Side
    from openpyxl.utils import get_column_letter as L
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.worksheet.pagebreak import Break

    from .. import VERSION
    from .. import keybank_style as K

    s = result["settings"]
    months = s["change_months"]
    vintage = result["vintage"]
    left = left_out_set(s["left_out"])
    by_key = {}
    for r in result["readings"]:
        by_key.setdefault(r["key"], {})[r["reading"]] = r
    missing_by = {}
    for x in result["not_read"]:
        missing_by.setdefault(x["key"], {})[x["reading"]] = x["why"]
    items = {i.key: i for i in READ}
    state_keys = {"unemployment_" + st.lower() for st in STATES}
    national = [k for _, keys in TOPICS for k in keys]
    topic_of = {k: t for t, keys in TOPICS for k in keys}
    wrows = {}
    b_months = None
    if whatif:
        for x in whatif["rows"]:
            wrows.setdefault(x["key"], {})[x["reading"]] = x
        b_months = "%d months" % whatif["months"][1]
    formulas = set()          # the Dashboard's own formula cells: the only cells left as formulas

    F_DATA = Font(name="Calibri", size=10, color=K.INK_TEXT)
    F_BOLD = Font(name="Calibri", size=10, bold=True, color=K.INK_TEXT)
    F_NOTE = Font(name="Calibri", size=10, color=K.SLATE)
    F_FIELD = Font(name="Arial", size=8, bold=True, color=K.SLATE)
    F_BIG = Font(name="Calibri", size=14, bold=True, color=K.INK_TEXT)
    F_LINK = Font(name="Calibri", size=10, color="1F4E79", underline="single")
    F_UP = Font(name="Calibri", size=10, bold=True, color=K.INK_TEXT)
    WRAP = Alignment(wrap_text=True, vertical="top")
    CENTER = Alignment(horizontal="center", vertical="center")
    MIDDLE = Alignment(vertical="center")
    RIGHT = Alignment(horizontal="right", vertical="center")

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

    def title_band(ws, title, sub, last, record=False, tab=None):
        """Row 1: the tab's name in white on ink, a one-line subtitle beside it, a thick red rule under it.
        The record tabs are slate with a stone rule, and their tabs grey. ``tab`` sets another tab colour: the
        usable-with-care tabs are slate, between the results and the record."""
        fill, rule_ = (K.SLATE, K.STONE) if record else (K.INK, K.KEY_RED)
        for col in range(1, last + 1):
            c = ws.cell(1, col)
            c.fill = K.solid(fill)
            c.border = Border(bottom=side("thick", rule_))
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
        ws.sheet_properties.tabColor = tab or (K.STONE if record else K.INK)

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

    def way(ws, row, col, d, size=9):
        """A direction as a cell shows it: moving bold on mist, Stable plain. No colour says better or worse."""
        c = ws.cell(row, col, ARROW[d])
        moving = d != STABLE
        c.font = Font(name="Arial", bold=moving, size=size, color=K.INK if moving else K.SLATE)
        if moving:
            c.fill = K.solid(K.MIST)
        c.alignment = CENTER
        c.border = Border(left=side("thin", K.PAPER), right=side("thin", K.PAPER))
        return c

    def link(cell, sheet_name, text_=None):
        if text_ is not None:
            cell.value = text_
        cell.hyperlink = "#'%s'!A1" % sheet_name
        cell.font = F_LINK
        cell.alignment = MIDDLE

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

    def formula(ws, row, col, text_, fmt=None, font=None, align=None):
        """A Dashboard formula, kept as one when every other text beginning "=" is made text."""
        c = put(ws, row, col, text_, fmt, font, align)
        formulas.add((ws.title, c.coordinate))
        return c

    def change_value(item, v):
        """A change as a cell holds it: a percent change as a fraction, so the cell's format shows %."""
        if item.change_in == "percent":
            return v / 100, "+#,##0.0#%;-#,##0.0#%;0%"
        return v, "+#,##0.0#;-#,##0.0#;0"

    def signed(item, v):
        return "%s%s%s" % ("+" if v > 0 else "", _num(v), "%" if item.change_in == "percent" else "")

    def latest_of(item):
        pts = pull.points(item)
        return next(((d, v) for d, v in reversed(pts) if v is not None), None) if not isinstance(pts, str) else None

    left_words = ("Left out of every history: %s. A reading in those quarters is not measured against, and a "
                  "change with either end in one is not counted." % spans(s["left_out"])) if s["left_out"] else ""
    zoom_words = ("The charts show %s to %s only. Every reading is measured against its history all the same; "
                  "only the view changes." % tuple(zoom)) if zoom else ""

    # -- the reading tables (Overview, States, Usable with care) ----------------------------------------------
    TABLE = ["Series", "Latest", "Value", "Unit", "Level: at or above", "Change over %d months" % months,
             "Change to", "Normal from", "Normal to", "Direction", "Typical moves", "Since", "History from"]

    def reading_row(ws, row, key, name_col_text=None, unit=True):
        """One series' row: the latest value, where it sits, its change against its normal range."""
        item = items[key]
        got = by_key.get(key, {})
        lvl, chg = got.get("position"), got.get("change")
        link(ws.cell(row, 2), tab_of(key), name_col_text or item.title)
        if unit:
            put(ws, row, 5, item.unit, font=F_NOTE)
        now = latest_of(item)
        if now:
            put(ws, row, 3, _date(now[0]), "yyyy-mm-dd")
            put(ws, row, 4, now[1], value_format(now[1]))
        else:
            put(ws, row, 3, "not in this pull", font=F_NOTE)
        if lvl:
            put(ws, row, 6, lvl["percentile"] / 100, "0.0%")
        elif item.position:
            put(ws, row, 6, "change only", font=F_NOTE, align=RIGHT)
        if chg:
            put(ws, row, 7, *change_value(item, chg["value"]))
            # The change's own month beside it: when a reading the horizon back is missing (October 2025) or
            # left out, the latest change is an earlier one's (Codex on #452).
            put(ws, row, 8, _date(chg["date"]), "yyyy-mm-dd", align=CENTER,
                font=F_BOLD if now and chg["date"] != now[0] else None)
            for col, v in ((9, chg["normal_low"]), (10, chg["normal_high"])):
                put(ws, row, col, *change_value(item, v))
            way(ws, row, 11, chg["direction"])
            put(ws, row, 12, chg["movement"], "+0.0;-0.0;0.0", align=CENTER)
            put(ws, row, 13, _date(chg["since"]), "yyyy-mm", align=CENTER)
        if lvl or chg:
            put(ws, row, 14, _date((lvl or chg)["history_from"]), "yyyy-mm", align=CENTER)
        return got

    # -- Overview -----------------------------------------------------------
    ws = sheet("Overview", first=True)
    last = 15 if whatif else 14
    widths(ws, [46, 11, 12, 26, 11, 12, 11, 11, 11, 14, 9, 9, 9] + ([30] if whatif else []))
    title_band(ws, "Economic conditions", "Public data, pulled %s. Where each series sits in its own history, "
                                          "and whether it is moving more than it normally does." % vintage, last)
    core_changes = [r for r in result["readings"] if r["reading"] == "change" and not r["care"]
                    and r["key"] not in state_keys]
    tile(ws, 3, 2, 2, "From the pull of", vintage)
    tile(ws, 3, 3, 4, "Changes read", len(core_changes), "#,##0")
    for i, d in enumerate((INCREASING, STABLE, DECREASING)):
        tile(ws, 3, 5 + 2 * i, 6 + 2 * i, ARROW[d], sum(1 for r in core_changes if r["direction"] == d), "#,##0")
    sahm_x = next(iter(result["alongside"]), None)
    if sahm_x:
        tile(ws, 3, 11, 12, "Sahm reading, beside the change", "%.2f in %s" % (
            sahm_x["value"], _date(sahm_x["date"]).strftime("%b %Y")))
    if whatif:
        nat = [x for x in whatif["rows"] if x["key"] not in state_keys and x["reading"] == "change"]
        tile(ws, 3, 13, 15, "What if: %s" % whatif["b"], "%d of %d changes read another way" % (
            sum(1 for x in nat if x["move"]), sum(1 for x in nat if x["move"] is not None)), to="What if")
    link(ws.cell(2, 2), CARE_NAME, "Also read, with care: %d series" % len(CARE))
    link(ws.cell(2, 4), DASHBOARD, "Dashboard: any two series together")
    width_words = "one typical move" if s["normal_width"] == 1 else "%g typical moves" % s["normal_width"]
    entries = [
        ("Level: at or above", "Where the latest reading sits in the series' own history: the share of every "
                               "reading in that history it is at or above, counted from the lowest. 100% is the "
                               "highest. It says where the reading sits, not whether that is good or bad."),
        ("Change", "The change over %d months: in points for a rate, a spread or an index, in percent for a level "
                   "that grows. A series that grows with prices and output is read on its change only." % months),
        ("Normal from, to", "The series' normal movement: the median of every such change in its history, plus "
                            "or minus %s. A typical move is 1.4826 times the median distance of the changes from "
                            "their median, the measure the loss thresholds use; a spike does not widen it."
                            % width_words),
        ("Direction", "Stable inside the normal range. Increasing at or above its top, Decreasing at or below its "
                      "bottom. For a series that usually grows, such as prices, Increasing means growing faster "
                      "than it normally does and Decreasing slower."),
        ("Typical moves", "How far the change is from the median change, in typical moves: the size of the move on "
                          "one scale for every series. Past %s either way is outside the normal range."
                          % ("%g" % s["normal_width"])),
        ("Since", "The first of the unbroken run of changes, up to the latest, that read the same way."),
        ("History from", "The first reading each series is measured against: %s." % (
            "the full history the publisher has" if s["history"] == "full" else
            "the last %d years up to the latest reading" % s["history"]["years"])),
    ]
    if left_words:
        entries.append(("Quarters left out", left_words))
    if sahm_x:
        entries.append(("Sahm reading", "The 3-month average unemployment rate minus its lowest 3-month average in "
                                        "the 12 months before. Sahm's published trigger is 0.50; shown beside the "
                                        "change, never used to read it."))
    if whatif:
        entries.append(("What if", "Each change that reads another way under %s, from the same pull. The What if "
                                   "tab sets every reading side by side." % whatif["b"]))
    entries.append(("Series", "Each name opens the series' tab: its level and change, and their charts."))
    entries.append((CARE_NAME, "%d more series, short, broken or heavily revised, are on the %s tab, read the "
                               "same way." % (len(CARE), CARE_NAME)))
    row = method_note(ws, 6, last, entries)
    cols = TABLE + (["What if"] if whatif else [])
    for topic, keys in TOPICS:
        row = section(ws, row, topic, last)
        row = sub_header(ws, row, cols, right=(1, 2, 4, 5, 7, 8), centre=(6, 9, 10, 11, 12))
        for key in keys:
            got = reading_row(ws, row, key)
            if not got:
                put(ws, row, 6, "not read: see the Not read tab", font=F_NOTE)
            if whatif:
                mine = list(wrows.get(key, {}).values())
                put(ws, row, 15, summary_text(mine, whatif["months"]),
                    font=F_UP if move_text(mine, whatif["months"]) else F_NOTE, align=Alignment(
                        vertical="center", wrap_text=True))
            ws.row_dimensions[row].height = 18 if not whatif else 30
            rule(ws, row, 2, last)
            row += 1
        row += 1
    ws.freeze_panes = "C2"

    # -- Dashboard (written after the data it looks up; its place in the tab order is kept here) ---------------
    dash = sheet(DASHBOARD)

    # -- What if ----------------------------------------------------------
    if whatif:
        ws = sheet("What if")
        last = 14
        widths(ws, [54, 22] + [12] * 10 + [10])
        title_band(ws, "What if", "%s against %s, both reading the pull of %s." % (whatif["b"], whatif["a"], vintage),
                   last)
        link(ws.cell(2, 2), "Overview", "Back to Overview")
        nat = [x for x in whatif["rows"] if x["key"] not in state_keys]
        sts = [x for x in whatif["rows"] if x["key"] in state_keys]
        both = [x for x in nat if x["move"] is not None]
        tile(ws, 3, 2, 2, "National changes read under both", len(both))
        tile(ws, 3, 3, 3, "The same way", sum(1 for x in both if x["move"] == 0))
        tile(ws, 3, 4, 5, "More upward", sum(1 for x in both if x["move"] > 0))
        tile(ws, 3, 6, 7, "More downward", sum(1 for x in both if x["move"] < 0))
        tile(ws, 3, 8, 10, "State changes read another way", "%d of %d" % (
            sum(1 for x in sts if x["move"]), sum(1 for x in sts if x["move"] is not None)))
        tile(ws, 3, 11, 14, "Read under one set only", sum(1 for x in whatif["rows"] if not (x["a"] and x["b"])
                                                           and (x["a"] or x["b"])))
        row = method_note(ws, 6, last, [
            ("What it is", "Every reading twice from the same pull: with the settings in %s (as you have it) and "
                           "with those in %s (what if). Nothing but the settings differs." % (whatif["a"],
                                                                                              whatif["b"])),
            ("Direction, typical moves", "Each side's direction for the change, how far it is from its median in "
                                         "typical moves, its normal range and the first reading of its history."),
            ("Move", "From Decreasing through Stable to Increasing: ▲ when the what-if reads the change more upward, "
                     "▼ more downward."),
            ("The grid", "National changes only. The direction as you have it runs down the side and the what-if's "
                         "across; the diagonal holds the changes that read the same way under both."),
            ("Folded rows", "The changes that read the same way, and every level, are listed last in rows folded "
                            "away. The plus sign beside the row numbers opens them."),
            ("The files", "Neither settings file is changed. The Run tab lists both files' answers."),
        ])
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
            put(ws, row, 2, "None: the two files give the same answers, so every reading is the same.", font=F_BOLD)
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

        # the grid, national changes, with the counts drawn beside it
        row = section(ws, row, "National changes: the direction as you have it against the what-if's", last)
        grid = [[0] * 3 for _ in range(3)]
        for x in both:
            grid[DIRECTIONS.index(x["a"]["direction"])][DIRECTIONS.index(x["b"]["direction"])] += 1
        top = row + 1
        ws.merge_cells(start_row=top, start_column=6, end_row=top, end_column=8)
        put(ws, top, 6, "WHAT IF", font=F_FIELD, align=CENTER)
        put(ws, top + 1, 5, "AS YOU HAVE IT", font=F_FIELD, align=RIGHT)
        for k, d in enumerate(DIRECTIONS):
            way(ws, top + 1, 6 + k, d)
            way(ws, top + 2 + k, 5, d)
            for j in range(3):
                n = grid[k][j]
                c = put(ws, top + 2 + k, 6 + j, n if (n or j == k) else None, "#,##0",
                        font=F_BOLD if j == k else F_DATA, align=CENTER)
                if j == k:
                    c.fill = K.solid(K.CANVAS)
                elif n:
                    c.fill = K.solid(K.MIST)
            put(ws, top + 2 + k, 9, sum(grid[k]), "#,##0", F_BOLD, CENTER)
            put(ws, top + 5, 6 + k, sum(g[k] for g in grid), "#,##0", F_BOLD, CENTER)
        put(ws, top + 1, 9, "Total", font=F_FIELD, align=CENTER)
        put(ws, top + 5, 5, "Total", font=F_FIELD, align=RIGHT)
        put(ws, top + 5, 9, len(both), "#,##0", F_BOLD, CENTER)
        for rr in range(top, top + 6):
            ws.row_dimensions[rr].height = 20
        for col in range(5, 10):
            ws.cell(top + 4, col).border = Border(bottom=side("thin", K.STONE))
        # the chart's own numbers, hidden beside the table
        put(ws, top, 16, "Direction", font=F_NOTE)
        put(ws, top, 17, "As you have it", font=F_NOTE)
        put(ws, top, 18, "What if", font=F_NOTE)
        for k, d in enumerate(DIRECTIONS):
            ws.cell(top + 1 + k, 16, d)
            ws.cell(top + 1 + k, 17, sum(grid[k]))
            ws.cell(top + 1 + k, 18, sum(g[k] for g in grid))
        for col in (16, 17, 18):
            ws.column_dimensions[L(col)].hidden = True
        bar = BarChart()
        bar.type, bar.grouping, bar.gapWidth, bar.overlap = "col", "clustered", 60, -10
        bar.add_data(Reference(ws, min_col=17, max_col=18, min_row=top, max_row=top + 3), titles_from_data=True)
        bar.set_categories(Reference(ws, min_col=16, min_row=top + 1, max_row=top + 3))
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
        bar.title = "National changes in each direction"
        bar.title.tx.rich.p[0].pPr = ParagraphProperties(defRPr=CharacterProperties(sz=1000, b=True,
                                                                                      solidFill=K.INK))
        bar.visible_cells_only = False
        bar.height, bar.width = 5.6, 10
        bar.roundedCorners = False
        bar.graphical_properties = GraphicalProperties(ln=LineProperties(noFill=True))
        ws.add_chart(bar, "J%d" % top)
        row = top + 9

        heads = ["Series", "Reading", "Latest", "Value", "Direction", "Typical moves", "Normal range",
                 "History from", "Direction", "Typical moves", "Normal range", "History from", "Move"]

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
            return header(ws, rr + 1, heads, right=(2, 3, 5), centre=(4, 6, 7, 8, 9, 10, 11, 12), height=18)

        def compared_row(rr, x):
            item = items[x["key"]]
            link(ws.cell(rr, 2), tab_of(x["key"]), item.title)
            one = x["a"] or x["b"]                # None when read under neither: no latest value to show
            if x["same_measure"]:
                put(ws, rr, 3, reading_name(x["reading"], months), font=F_NOTE)
                if one:
                    put(ws, rr, 4, _date(one["date"]), "yyyy-mm-dd")
                    v, fmt = change_value(item, one["value"]) if x["reading"] == "change" else (
                        one["value"], value_format(one["value"]))
                    put(ws, rr, 5, v, fmt)
            else:
                # Two different changes: each side's reading is of its own, so neither value is shown as shared.
                put(ws, rr, 3, row_label(x, whatif["months"]).capitalize(), font=F_NOTE,
                    align=Alignment(vertical="center", wrap_text=True))
            for col, got, why in ((6, x["a"], x["why_a"]), (10, x["b"], x["why_b"])):
                if got and x["reading"] == "change":
                    way(ws, rr, col, got["direction"])
                    put(ws, rr, col + 1, got["movement"], "+0.0;-0.0;0.0", align=CENTER)
                    put(ws, rr, col + 2, "%s to %s" % (signed(item, got["normal_low"]),
                                                       signed(item, got["normal_high"])), align=CENTER)
                    put(ws, rr, col + 3, _date(got["history_from"]), "yyyy-mm", align=CENTER)
                elif got:
                    ws.merge_cells(start_row=rr, start_column=col, end_row=rr, end_column=col + 2)
                    put(ws, rr, col, "at or above %.1f%% of %s readings" % (got["percentile"],
                                                                           "{:,}".format(got["readings"])),
                        font=F_DATA, align=CENTER)
                    put(ws, rr, col + 3, _date(got["history_from"]), "yyyy-mm", align=CENTER)
                else:
                    ws.merge_cells(start_row=rr, start_column=col, end_row=rr, end_column=col + 3)
                    put(ws, rr, col, "Not read: " + why, font=F_NOTE, align=WRAP)
            if x["move"]:
                put(ws, rr, 14, ("▲ %d" if x["move"] > 0 else "▼ %d") % abs(x["move"]), font=F_UP, align=CENTER)
            elif x["move"] == 0:
                put(ws, rr, 14, "same", font=F_NOTE, align=CENTER)
            ws.row_dimensions[rr].height = 18 if x["same_measure"] else 28
            rule(ws, rr, 2, last)

        topics_ = [t for t, _ in TOPICS]

        def ordered(rows_):
            return sorted(rows_, key=lambda x: (topics_.index(topic_of[x["key"]]) if x["key"] in topic_of else 99,
                                               -abs(x["move"] or 0), x["title"], x["reading"] != "position"))

        changed = ordered([x for x in nat if x["move"]])
        row = section(ws, row, "National changes that read another way (%d)" % len(changed), last)
        row = groups(row)
        if not changed:
            put(ws, row, 2, "None: every national change read under both reads the same way.", font=F_BOLD)
            row += 1
        topic = None
        for x in changed:
            if topic_of.get(x["key"]) != topic:
                topic = topic_of.get(x["key"])
                for col in range(2, last + 1):
                    ws.cell(row, col).fill = K.solid(K.CANVAS)
                put(ws, row, 2, topic or CARE_NAME, font=Font(name="Arial", bold=True, size=9, color=K.SLATE))
                row += 1
            compared_row(row, x)
            row += 1
        row += 1
        st_changed = sorted([x for x in sts if x["move"]], key=lambda x: (-abs(x["move"]), x["title"]))
        row = section(ws, row, "State changes that read another way (%d of %d)" % (
            len(st_changed), sum(1 for x in sts if x["move"] is not None)), last)
        row = groups(row)
        if not st_changed:
            put(ws, row, 2, "None: every state change read under both reads the same way.", font=F_BOLD)
            row += 1
        for x in st_changed:
            compared_row(row, x)
            row += 1
        row += 1
        one_side = [x for x in whatif["rows"] if not (x["a"] and x["b"]) and (x["a"] or x["b"])]
        if one_side:
            row = section(ws, row, "Read under one set of settings only (%d)" % len(one_side), last)
            row = groups(row)
            for x in ordered(one_side):
                compared_row(row, x)
                row += 1
            row += 1
        # Asked for by either and read by neither, each with its run's reason (Codex on #452).
        neither = [x for x in whatif["rows"] if not (x["a"] or x["b"])]
        if neither:
            row = section(ws, row, "Read under neither set of settings (%d)" % len(neither), last)
            row = groups(row)
            for x in ordered(neither):
                compared_row(row, x)
                row += 1
            row += 1
        for words, pick in (("National changes that read the same way under both (%d, folded away)",
                             lambda x: x["move"] == 0),
                            ("National levels under both (%d, folded away)",
                             lambda x: x["reading"] == "position" and x["a"] and x["b"])):
            same = ordered([x for x in nat if pick(x)])
            row = section(ws, row, words % len(same), last)
            row = groups(row)
            start = row
            for x in same:
                compared_row(row, x)
                row += 1
            if same:
                ws.row_dimensions.group(start, row - 1, outline_level=1, hidden=True)
            row += 1
        ws.print_area = "A1:N%d" % row

    # -- States -----------------------------------------------------------
    ws = sheet("States")
    last = 13 if whatif else 12
    widths(ws, [8, 12, 12, 13, 13, 11, 11, 11, 14, 9, 9] + ([24] if whatif else []))
    title_band(ws, "Unemployment by state", "Bureau of Labor Statistics, Local Area Unemployment Statistics "
                                            "(LAUS), pulled %s." % vintage, last)
    link(ws.cell(2, 2), "Overview", "Back to Overview")
    entries = [("Rate", "The unemployment rate, seasonally adjusted, in percent; each state is read against its "
                        "own history, as the national series are."),
               ("Level, Change", "Level: the share of the state's months its latest rate is at or above. Change: "
                                 "the change over %d months, in points, against the state's normal range." % months),
               ("Order", "Moving states first, the furthest from their median change at the top, then the rest "
                         "by state.")]
    if left_words:
        entries.append(("Quarters left out", left_words))
    if whatif:
        entries.append(("What if", "Each change that reads another way under %s." % whatif["b"]))
    row = method_note(ws, 3, last, entries, label_cols=2)
    head = row
    row = header(ws, row, ["State", "Latest", "Unemployment rate", "Level: at or above",
                           "Change over %d months" % months, "Normal from", "Normal to", "Direction",
                           "Typical moves", "Since", "History from"] + (["What if"] if whatif else []),
                 right=(1, 2, 3, 4, 5, 6), centre=(7, 8, 9, 10))

    def standing(st):
        chg = by_key.get("unemployment_" + st.lower(), {}).get("change")
        if not chg:
            return (2, 0, st)
        return (0 if chg["direction"] != STABLE else 1, -abs(chg["movement"]), st)
    for st in sorted(STATES, key=standing):
        key = "unemployment_" + st.lower()
        got = by_key.get(key, {})
        lvl, chg = got.get("position"), got.get("change")
        put(ws, row, 2, st)
        if lvl:
            put(ws, row, 3, _date(lvl["date"]), "yyyy-mm")
            put(ws, row, 4, lvl["value"], "0.0")
            put(ws, row, 5, lvl["percentile"] / 100, "0.0%")
            put(ws, row, 12, _date(lvl["history_from"]), "yyyy-mm", align=CENTER)
        if chg:
            put(ws, row, 6, chg["value"], "+0.0;-0.0;0.0")
            put(ws, row, 7, chg["normal_low"], "+0.00;-0.00;0.00")
            put(ws, row, 8, chg["normal_high"], "+0.00;-0.00;0.00")
            way(ws, row, 9, chg["direction"])
            put(ws, row, 10, chg["movement"], "+0.0;-0.0;0.0", align=CENTER)
            put(ws, row, 11, _date(chg["since"]), "yyyy-mm", align=CENTER)
        if not got:
            put(ws, row, 3, "not in this pull", font=F_NOTE)
        if whatif:
            mine = list(wrows.get(key, {}).values())
            put(ws, row, 13, summary_text(mine, whatif["months"]),
                font=F_UP if move_text(mine, whatif["months"]) else F_NOTE)
        rule(ws, row, 2, last)
        row += 1
    ws.freeze_panes = ws.cell(head + 1, 3)

    # -- charts -------------------------------------------------------------
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

    def finish(chart_, title, unit, axis, step, x_axis):
        """The value axis, the title and the frame every history chart shares."""
        ax = chart_.y_axis
        ax.delete = False
        ax.majorGridlines = None
        ax.spPr = GraphicalProperties(ln=ln(K.STONE, 0.75))
        ax.txPr = text()
        ax.scaling.min, ax.scaling.max = axis
        ax.majorUnit = step
        ax.number_format = "#,##0.0#" if abs(axis[1]) < 1000 and abs(axis[0]) < 1000 else "#,##0"
        ax.title = unit
        # The band and the latest point live in hidden helper columns; a chart plots only visible cells unless
        # told otherwise.
        chart_.visible_cells_only = False
        chart_.title = title
        chart_.title.tx.rich.p[0].pPr = ParagraphProperties(defRPr=CharacterProperties(sz=1000, b=True,
                                                                                        solidFill=K.INK))
        chart_.legend = None
        chart_.display_blanks = "gap"
        chart_.height, chart_.width = 8.5, 24
        chart_.roundedCorners = False
        chart_.graphical_properties = GraphicalProperties(ln=LineProperties(noFill=True))

    def history_chart(ws, title, unit, data_col, first, last, latest_col, frequency, axis, step, band_col=None,
                      dashed_col=None, head=None):
        """The history in ink with the latest reading ringed, over rows ``first`` to ``last``; ``head`` is the
        header row naming each column. With ``band_col``, the normal range is shaded behind it (two hidden
        columns: an unfilled base at the range's bottom and the range's height); with ``dashed_col``, the
        what-if's range is dashed over it.

        The band is the chart underneath and the lines are laid over it: LibreOffice draws in the order
        charts are combined, Excel draws areas first whatever the order, so this order reads the same in
        both."""
        cats = Reference(ws, min_col=14, min_row=first, max_row=last)

        def add(chart_, col):
            # Each series titled from the header row and drawn from the rows asked for: a zoomed range does not
            # start under its header. Every series carries its own dates; without them Excel places a line on
            # 1, 2, 3 ... of a date axis, 1900 (Fable's report on #452).
            ser = Series(Reference(ws, min_col=col, min_row=first, max_row=last), title=ws.cell(head, col).value)
            chart_.series.append(ser)
            return ser
        x_axis = years_axis([ws.cell(first, 14).value.isoformat(), ws.cell(last, 14).value.isoformat()], frequency)
        line = LineChart()
        hist = add(line, data_col)
        line.set_categories(cats)
        hist.graphicalProperties.line = ln(K.INK, 2.0)
        hist.marker.symbol = "none"
        hist.smooth = False
        latest = LineChart()
        pt = add(latest, latest_col)
        latest.set_categories(cats)
        pt.graphicalProperties.line.noFill = True
        pt.marker.symbol = "circle"
        pt.marker.size = 7
        pt.marker.graphicalProperties = GraphicalProperties(solidFill="FFFFFF", ln=ln(K.INK, 1.5))
        pt.dLbls = DataLabelList()
        pt.dLbls.showVal, pt.dLbls.showCatName, pt.dLbls.showSerName, pt.dLbls.showLegendKey = True, False, False, False
        pt.dLbls.position = "l"
        pt.dLbls.numFmt = "#,##0.0#"
        pt.dLbls.txPr = text(9, K.INK_TEXT, True)
        dashed = None
        if dashed_col:
            dashed = LineChart()
            for col in (dashed_col, dashed_col + 1):
                s_ = add(dashed, col)
                s_.graphicalProperties.line = ln(K.CRIMSON, 1.25, "dash")
                s_.marker.symbol = "none"
                s_.smooth = False
            dashed.set_categories(cats)
        base = line
        if band_col:
            base = AreaChart()
            base.grouping = "stacked"
            under, band = add(base, band_col), add(base, band_col + 1)
            base.set_categories(cats)
            under.graphicalProperties.noFill = True
            under.graphicalProperties.line.noFill = True
            band.graphicalProperties.solidFill = K.MIST
            band.graphicalProperties.line.noFill = True
        layers = [base] + ([line] if band_col else []) + ([dashed] if dashed else []) + [latest]
        for chart_ in layers:
            chart_.x_axis = x_axis              # one axis for every layer, or the lines drift off the band
            # and the value axis crosses that axis: left at its default (10, an axis this chart does not have),
            # Excel refused the whole file (17 Oct 2026); LibreOffice drew it anyway
            chart_.y_axis.crossAx = x_axis.axId
        finish(base, title, unit, axis, step, x_axis)
        if frequency == "daily":
            # A day with no reading is a holiday, not a gap in the record: the line joins the days either side,
            # or a daily line breaks at every holiday (the prime rate, 22 Oct 2026). A month or a week with no
            # value still leaves a gap.
            base.display_blanks = "span"
        for chart_ in layers[1:]:
            base += chart_
        return base

    def history_tab(ws, key, item, mine, points, row, top_cols=12):
        """The history table on the right, every chart of the series, and the note under each: N to Q hold
        the date, the value, the change as read and a note; T onwards the hidden columns the charts draw."""
        chg = dict(changes(kept(points, s["left_out"]), months, item.frequency, item.change_in))
        ws.row_breaks.append(Break(id=row - 1))     # printed, the charts start a page of their own
        top = row
        header(ws, top, ["Date", "Value", "Change over %d months" % months, "Note"], first=14, right=(1, 2))
        first = top + 1
        dates = []
        for i, (d, v) in enumerate(points):
            rr = first + i
            dates.append(_date(d).isoformat())
            put(ws, rr, 14, _date(d), "yyyy-mm-dd")
            # A missing value stays an empty cell: text there would be drawn as zero on the chart, the very
            # error the readers are kept from.
            if v is not None:
                put(ws, rr, 15, v, value_format(v))
                if quarter_of(dates[-1]) in left:
                    put(ws, rr, 17, "left out (%s)" % quarter_of(dates[-1]), font=F_NOTE)
                else:
                    ws.cell(rr, 20, v)              # the level as drawn: left-out quarters stay empty
            else:
                put(ws, rr, 17, "no value published", font=F_NOTE)
            if dates[-1] in chg:
                put(ws, rr, 16, chg[dates[-1]], "#,##0.0#")
        last = first + len(points) - 1
        span = zoom_rows(dates, zoom)
        for col in range(20, 27):
            ws.column_dimensions[L(col)].hidden = True
        put(ws, top, 20, "Level", font=F_NOTE)
        drawn = 0
        for reading in readings_of(item):
            r = mine.get(reading)
            w = (wrows.get(key, {}).get(reading) or {}) if whatif else {}
            wb_ = w.get("b") if w and w.get("same_measure") and reading == "change" else None
            if not r and not wb_:
                continue
            if span is None:
                put(ws, row, 2, "No reading of its %s falls in %s to %s, the quarters the charts are zoomed to."
                    % ("level" if reading == "position" else "change", zoom[0], zoom[1]), font=F_NOTE)
                row += 2
                continue
            a, b = first + span[0], first + span[1]
            data_col = 20 if reading == "position" else 16
            seen = [(dates[i - first], ws.cell(i, data_col).value) for i in range(a, b + 1)
                    if ws.cell(i, data_col).value is not None]
            if not seen:
                continue
            ref = r or wb_
            keep = []
            latest_row = first + dates.index(_date(ref["date"]).isoformat())
            if a <= latest_row <= b:
                keep.append(ws.cell(latest_row, data_col).value)
            band_col = dashed_col = None
            if reading == "change":
                if r:
                    keep += [r["normal_low"], r["normal_high"]]
                if wb_:
                    keep += [wb_["normal_low"], wb_["normal_high"]]
            lo, hi, step, above, below = axis_view(seen, s["axis_cut"], keep)
            latest_col = 21 if reading == "position" else 24
            put(ws, top, latest_col, "Latest", font=F_NOTE)
            if a <= latest_row <= b:
                # Rounded here: LibreOffice ignores a label's own number format.
                ws.cell(latest_row, latest_col, round(ws.cell(latest_row, data_col).value, 2))
            if reading == "change" and r:
                band_col = 22
                put(ws, top, 22, "Normal from", font=F_NOTE)
                put(ws, top, 23, "Normal range", font=F_NOTE)
                for rr in range(a, b + 1):
                    ws.cell(rr, 22, r["normal_low"])
                    ws.cell(rr, 23, r["normal_high"] - r["normal_low"])
            if wb_:
                # The what-if's range: two lines over the years its history covers.
                dashed_col = 25
                start = _date(wb_["history_from"]).isoformat()
                put(ws, top, 25, "What if: normal from", font=F_NOTE)
                put(ws, top, 26, "What if: normal to", font=F_NOTE)
                for i in range(a, b + 1):
                    if dates[i - first] >= start:
                        ws.cell(i, 25, wb_["normal_low"])
                        ws.cell(i, 26, wb_["normal_high"])
            title = ("Level against its history" if reading == "position" else
                     "Change over %d months, its normal range shaded" % months)
            if reading == "change" and not r:
                title = "Change over %d months; not read under these settings" % months
            if dashed_col:
                title += " (dashed: the normal range under the what-if)"
            unit = item.unit if reading == "position" else ("percent" if item.change_in == "percent" else "points")
            ws.add_chart(history_chart(ws, title, unit, data_col, a, b, latest_col, item.frequency, (lo, hi), step,
                                       band_col, dashed_col, head=top), "B%d" % row)
            row += 18
            said = off_edge(above, below, item.frequency,
                            (lambda v: "%s %s" % (_num(v), item.unit)) if reading == "position" else
                            (lambda v: signed(item, v) + ("" if item.change_in == "percent" else " points")))
            if said:
                note(ws, row, 2, said, top_cols)
                ws.row_dimensions[row].height = 28
                row += 1
            row += 1
            drawn += 1
        return row, top, first, last, dates, span

    def facts_rows(ws, row, facts):
        for k, v in facts:
            put(ws, row, 2, k, font=F_BOLD, align=WRAP)
            ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=12)
            put(ws, row, 3, v, align=WRAP)
            ws.row_dimensions[row].height = 15 * (1 + len(v) // 120)
            rule(ws, row, 2, 12)
            row += 1
        return row

    def boxes(ws, item, key, mine, row):
        """The level and the change at the top of a series' tab, each in its own box."""
        tall = 4 if whatif else 3
        said = []
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
                v, fmt = change_value(item, r["value"]) if reading == "change" else (r["value"],
                                                                                   value_format(r["value"]))
                if reading == "change":
                    way(ws, row + 1, col, r["direction"], size=11)
                    put(ws, row + 1, col + 1, v, fmt, F_BIG, RIGHT)
                else:
                    put(ws, row + 1, col, v, fmt, F_BIG, Alignment(horizontal="left", vertical="center"))
                put(ws, row + 1, col + 2, _date(r["date"]), "yyyy-mm-dd", F_NOTE,
                    Alignment(horizontal="left", vertical="center", indent=1))
                said.append(r["sentence"])
            elif reading == "position" and item.position:
                put(ws, row + 1, col, "change only", font=F_NOTE, align=MIDDLE)
                said.append("Change only: " + item.position + ".")
            else:
                said.append("Not read: %s." % missing_by.get(key, {}).get(reading, "not in this pull"))
            note(ws, row + 2, col, said[-1], end, F_DATA)
            w = wrows.get(key, {}).get(reading) if whatif else None
            if w:
                put(ws, row + 3, col, "WHAT IF", font=F_FIELD, align=MIDDLE)
                b = w["b"]
                if b and reading == "change":
                    way(ws, row + 3, col + 1, b["direction"])
                    noun = "changes" if w["same_measure"] else "changes over %s" % b_months
                    words = "%s: %+.1f typical moves; normal range %s to %s, from %s %s since %s." % (
                        "Read under the what-if only" if not w["a"] else "The same way" if w["move"] == 0 else
                        "Reads another way", b["movement"], signed(item, b["normal_low"]),
                        signed(item, b["normal_high"]), "{:,}".format(b["readings"]), noun, when(b["history_from"]))
                    note(ws, row + 3, col + 2, words, end, F_UP if w["move"] else F_DATA)
                elif b:
                    note(ws, row + 3, col + 1, "At or above %.1f%% of %s readings since %s." % (
                        b["percentile"], "{:,}".format(b["readings"]), when(b["history_from"])), end, F_DATA)
                else:
                    note(ws, row + 3, col + 1, "Not read under the what-if: %s." % w["why_b"], end)
        ws.row_dimensions[row].height = 16
        ws.row_dimensions[row + 1].height = 24
        ws.row_dimensions[row + 2].height = 14 * max(math.ceil(len(x) / (width_of(ws, 2, 6) * 1.2))
                                                     for x in said) + 4
        if whatif:
            ws.row_dimensions[row + 3].height = 30
        return row + tall + 1

    def chart_entries(item, extra=()):
        width_ = "one typical move" if s["normal_width"] == 1 else "%g typical moves" % s["normal_width"]
        out_ = [("The charts", "The history in black; the circle is the latest reading. On the change chart the "
                               "shaded band is the normal range: the median change plus or minus %s." % width_)]
        out_ += list(extra)
        if s["axis_cut"]:
            out_.append(("Off the chart", "Up to %g%% of the readings drawn may run off each end of a chart's "
                                          "axis, so a spike does not flatten the rest; a note under the chart "
                                          "names the furthest one. The latest reading and the normal range always "
                                          "stay on. No reading changes." % s["axis_cut"]))
        if zoom_words:
            out_.append(("Zoom", zoom_words))
        if left_words:
            out_.append(("Quarters left out", left_words + " They are not drawn."))
        if item.frequency == "daily":
            out_.append(("Holidays", "A daily series has no reading on a holiday. Its line joins the days either "
                                     "side; the table shows the day as no value published."))
        out_.append(("History", "Every reading, with its change over %d months as read, is in columns N to Q. A "
                                "period the publisher left blank stays empty and reads no value published." % months))
        return out_

    def series_tab(key, care=False):
        item = items[key]
        mine = by_key.get(key, {})
        ws = sheet(CARE_TAB[key] if care else TAB[key])
        widths(ws, [18, 13, 13, 13, 13, 18, 13, 13, 13, 13, 13, 2.71, 12, 13, 13, 22, 12, 9])
        source = BY_KEY.get(key)
        title_band(ws, item.title, "%s · %s · %s · pulled %s%s" % (
            source.publisher if source else "made from two series", item.unit, item.frequency, vintage,
            " · usable with care" if care else ""), 17, tab=K.SLATE if care else None)
        link(ws.cell(2, 2), CARE_NAME if care else "Overview", "Back to " + (CARE_NAME if care else "Overview"))
        link(ws.cell(2, 4), DASHBOARD, "Dashboard")
        if whatif:
            link(ws.cell(2, 6), "What if", "What if")
        row = boxes(ws, item, key, mine, 4)
        extra = []
        if whatif and any((wrows.get(key, {}).get(rd) or {}).get("b") for rd in ("change",)):
            extra.append(("Dashed lines", "The normal range under %s, over the years its history covers. Drawn "
                                          "only where the two count the change over the same months." % whatif["b"]))
        row = method_note(ws, row, 12, chart_entries(item, extra))
        points = pull.points(item)
        if isinstance(points, str) or not any(v is not None for _, v in points):
            # Nothing to draw: said, not drawn (Fable on #452: a file of headers only crashed the Sahm chart).
            put(ws, row, 2, points if isinstance(points, str) else
                "The pull of %s holds no values for this series." % vintage, font=F_NOTE)
            ws.print_area = "A1:L%d" % row
            return ws
        row, top, first, last, dates, span = history_tab(ws, key, item, mine, points, row)
        sahm_drawn = key == "unemployment" and s["show_sahm"] and span is not None
        if sahm_drawn:
            ws.row_breaks.append(Break(id=row - 1))     # printed, the chart starts a page whole
            sv = dict(sahm(points))
            header(ws, top, ["Sahm reading", "Trigger"], first=18, right=(0, 1))
            for i, d in enumerate(dates):
                if d in sv:
                    put(ws, first + i, 18, sv[d], "0.00")
                    ws.cell(first + i, 19, 0.50)
            a, b = first + span[0], first + span[1]
            sc = LineChart()
            for col in (18, 19):                # the zoom's rows, each titled by its header
                sc.series.append(Series(Reference(ws, min_col=col, min_row=a, max_row=b),
                                        title=ws.cell(top, col).value))
            sc.set_categories(Reference(ws, min_col=14, min_row=a, max_row=b))
            sc.series[0].graphicalProperties.line = ln(K.INK, 1.5)
            sc.series[1].graphicalProperties.line = ln(K.CRIMSON, 1.25, "sysDash")
            for s_ in sc.series:
                s_.marker.symbol = "none"
                s_.smooth = False
            sc.x_axis = years_axis([dates[span[0]], dates[span[1]]], "monthly")
            sc.y_axis.crossAx = sc.x_axis.axId
            sc.y_axis.delete = False
            sc.y_axis.majorGridlines = None
            sc.y_axis.spPr = GraphicalProperties(ln=ln(K.STONE, 0.75))
            sc.y_axis.txPr = text()
            sc.title = "Sahm reading, beside the change: dashed line at Sahm's trigger, 0.50"
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
        facts.append(("How it is read", "Change only: " + item.position if item.position else "Level and change"))
        facts.append(("In the research", RESEARCH.get(item.stress, RESEARCH[None])))
        if care:
            facts += [("Why with care", item.care[0].upper() + item.care[1:]), ("Where in the research", item.report)]
        if item.note:
            facts.append(("Note", item.note))
        for when_, what in item.breaks:
            facts.append(("Break", "%s: %s" % (when_, what)))
        if getattr(item, "credit", ""):
            facts.append(("Credit", item.credit))
        row = facts_rows(ws, row, facts)
        # Printed, a tab is its readings, charts and facts; its history stays on screen.
        ws.print_area = "A1:L%d" % row
        return ws

    # -- Household debt -----------------------------------------------------
    def household_tab():
        ws = sheet(HOUSEHOLD_NAME)
        widths(ws, [22, 13, 11, 13, 11, 11, 14, 9, 9, 11, 13, 2.71, 12, 11, 11, 11, 11, 11, 11, 11, 12])
        title_band(ws, HOUSEHOLD_NAME, "NY Fed, Quarterly Report on Household Debt and Credit · trillions of "
                                       "dollars · quarterly · pulled %s" % vintage, 22)
        link(ws.cell(2, 2), "Overview", "Back to Overview")
        link(ws.cell(2, 4), DASHBOARD, "Dashboard")
        total = by_key.get("household_total", {}).get("change")
        now = latest_of(BY_KEY["household_total"])
        if now:
            tile(ws, 3, 2, 3, "Total, %s" % _when(now[0], "quarterly"), "$%.2f trillion" % now[1])
        if total:
            tile(ws, 3, 4, 6, "Total: change over %d months" % months, "%s, %s" % (
                signed(BY_KEY["household_total"], total["value"]), total["direction"]))
        row = method_note(ws, 6, 12, [
            ("As reported", "The NY Fed's own split and its own chart, Total Debt Balance and Its Composition: "
                            "mortgage, home equity revolving, auto loan, credit card, student loan and other, in "
                            "trillions of dollars, from 2003 Q1."),
            ("Share", "Each type's balance as a share of the total, this workbook's arithmetic."),
            ("Change, direction", "Each type's change over %d months in percent, against its own normal range, "
                                  "read as every other series is." % months),
        ] + chart_entries(BY_KEY["household_total"])[1:-1] + [
            ("History", "Every quarter, each type as the NY Fed reports it, is in columns N to U. A quarter with no "
                        "figure stays empty.")])
        row = section(ws, row, "Each type, latest quarter", 12)
        row = sub_header(ws, row, ["Type, as the NY Fed heads it", "Balance, $ trillions", "Share of total",
                                   "Change over %d months" % months, "Normal from", "Normal to", "Direction",
                                   "Typical moves", "Since", "History from"], right=(1, 2, 3, 4, 5),
                         centre=(6, 7, 8, 9))
        for key, column, _ in HOUSEHOLD_DEBT:
            item = BY_KEY[key]
            put(ws, row, 2, column, font=F_BOLD if key == "household_total" else F_DATA)
            v = latest_of(item)
            if v:
                put(ws, row, 3, v[1], "#,##0.000")
                if now and now[0] == v[0] and now[1]:
                    put(ws, row, 4, v[1] / now[1], "0.0%")
            chg = by_key.get(key, {}).get("change")
            if chg:
                put(ws, row, 5, *change_value(item, chg["value"]))
                put(ws, row, 6, *change_value(item, chg["normal_low"]))
                put(ws, row, 7, *change_value(item, chg["normal_high"]))
                way(ws, row, 8, chg["direction"])
                put(ws, row, 9, chg["movement"], "+0.0;-0.0;0.0", align=CENTER)
                put(ws, row, 10, _date(chg["since"]), "yyyy-mm", align=CENTER)
                put(ws, row, 11, _date(chg["history_from"]), "yyyy-mm", align=CENTER)
            elif key in missing_by:
                ws.merge_cells(start_row=row, start_column=5, end_row=row, end_column=11)
                put(ws, row, 5, "Not read: " + missing_by[key]["change"], font=F_NOTE)
            rule(ws, row, 2, 11)
            row += 1
        row += 1
        cols = {key: dict(p) for key, p in ((k, pull.points(BY_KEY[k])) for k in HOUSEHOLD_KEYS)
                if not isinstance(p, str)}
        quarters = sorted({d for c in cols.values() for d in c})
        if not quarters:
            put(ws, row, 2, "The pull of %s holds no household debt figures." % vintage, font=F_NOTE)
            ws.print_area = "A1:L%d" % row
            return ws
        top = row
        ws.row_breaks.append(Break(id=row - 1))
        header(ws, top, ["Quarter"] + [c for _, c, _ in HOUSEHOLD_DEBT] + ["Note"], first=14,
               right=tuple(range(1, 8)))
        first = top + 1
        for i, d in enumerate(quarters):
            rr = first + i
            put(ws, rr, 14, _date(d), "yyyy-mm-dd")
            out_ = quarter_of(d) in left
            for j, key in enumerate(HOUSEHOLD_KEYS):
                v = cols.get(key, {}).get(d)
                if v is not None:
                    put(ws, rr, 15 + j, v, "#,##0.000")
                    if not out_ and key != "household_total":
                        ws.cell(rr, 24 + j, v)          # as drawn: left-out quarters stay empty
            if out_:
                put(ws, rr, 22, "left out (%s)" % quarter_of(d), font=F_NOTE)
        for j, (_, column, _) in enumerate(HOUSEHOLD_DEBT[:-1]):
            ws.cell(top, 24 + j, column)
            ws.column_dimensions[L(24 + j)].hidden = True
        span = zoom_rows(quarters, zoom)
        if span is None:
            put(ws, row, 2, "No quarter falls in %s to %s, the quarters the charts are zoomed to." % tuple(zoom),
                font=F_NOTE)
            ws.print_area = "A1:L%d" % row
            return ws
        a, b = first + span[0], first + span[1]
        # Bars side by side, one a quarter, as the NY Fed draws them. On a date axis a quarter's bar takes a
        # month's width and leaves two empty, so the axis is of labels: the year under each first quarter, every
        # one, two or five years so that at most about twelve show (LibreOffice prints every label of a text axis).
        years_ = max(1, int(quarters[span[1]][:4]) - int(quarters[span[0]][:4]))
        every_ = next(k for k in (1, 2, 5, 10) if years_ / k <= 12)
        ws.cell(top, 30, "Label")
        ws.column_dimensions[L(30)].hidden = True
        for i in range(span[0], span[1] + 1):
            d = quarters[i]
            if d[5:7] == "01" and int(d[:4]) % every_ == 0:   # the other quarters' labels stay empty cells
                ws.cell(first + i, 30, d[:4])
        stack = BarChart()
        stack.type, stack.grouping, stack.overlap, stack.gapWidth = "col", "stacked", 100, 25
        for j, (_, column, _) in enumerate(HOUSEHOLD_DEBT[:-1]):
            ser = Series(Reference(ws, min_col=24 + j, min_row=a, max_row=b), title=column)
            ser.graphicalProperties.solidFill = HOUSEHOLD_COLOURS[j]
            ser.graphicalProperties.line.noFill = True
            stack.series.append(ser)
        stack.set_categories(Reference(ws, min_col=30, min_row=a, max_row=b))
        x_axis = stack.x_axis
        x_axis.tickLblSkip, x_axis.tickMarkSkip = 1, 4
        x_axis.delete = False
        x_axis.majorGridlines = None
        x_axis.spPr = GraphicalProperties(ln=ln(K.STONE, 0.75))
        x_axis.txPr = text()
        x_axis.tickLblPos = "low"
        stack.y_axis.crossAx = x_axis.axId
        totals = [cols.get("household_total", {}).get(quarters[i]) for i in range(span[0], span[1] + 1)]
        top_ = max([v for v in totals if v is not None] or [1.0])
        lo, hi, step = nice_axis(0, top_)
        finish(stack, "Total Debt Balance and Its Composition (the NY Fed's chart, as it reports it)",
               "trillions of dollars", (0, hi), step, x_axis)
        stack.legend = Legend()
        stack.legend.position = "b"
        stack.legend.txPr = text(9, K.INK_TEXT)
        stack.height = 10
        ws.add_chart(stack, "B%d" % row)
        row += 21
        note(ws, row, 2, BY_KEY["household_total"].credit, 12)
        ws.row_dimensions[row].height = 30
        row += 2
        # The total's change, drawn as every series' change is, from the table's own columns: the change is
        # written beside it in a column of its own.
        item = BY_KEY["household_total"]
        chg = dict(changes(kept(list(cols.get("household_total", {}).items()), s["left_out"]), months, "quarterly",
                           "percent"))
        header(ws, top, ["Total: change"], first=23)
        for i, d in enumerate(quarters):
            if d in chg:
                put(ws, first + i, 23, chg[d], "#,##0.0#")
        r = by_key.get("household_total", {}).get("change")
        if r:
            seen = [(quarters[i], chg[quarters[i]]) for i in range(span[0], span[1] + 1) if quarters[i] in chg]
            if seen:
                latest_row = first + quarters.index(r["date"])
                keep = [r["normal_low"], r["normal_high"]] + ([chg[r["date"]]] if a <= latest_row <= b else [])
                lo, hi, step, above, below = axis_view(seen, s["axis_cut"], keep)
                for col, words in ((31, "Normal from"), (32, "Normal range"), (33, "Latest")):
                    ws.cell(top, col, words)
                    ws.column_dimensions[L(col)].hidden = True
                for rr in range(a, b + 1):
                    ws.cell(rr, 31, r["normal_low"])
                    ws.cell(rr, 32, r["normal_high"] - r["normal_low"])
                if a <= latest_row <= b:
                    ws.cell(latest_row, 33, round(chg[r["date"]], 2))
                ws.add_chart(history_chart(ws, "Total: change over %d months, its normal range shaded" % months,
                                           "percent", 23, a, b, 33, "quarterly", (lo, hi), step, 31, head=top),
                             "B%d" % row)
                row += 18
                said = off_edge(above, below, "quarterly", lambda v: signed(item, v))
                if said:
                    note(ws, row, 2, said, 12)
                    row += 1
                row += 1
        ws.row_breaks.append(Break(id=row - 1))
        row = section(ws, row, "What it is", 12)
        row = facts_rows(ws, row, [
            ("Source", "NY Fed, Quarterly Report on Household Debt and Credit: the data workbook's sheet Page 3 "
                       "Data, read from the file the report's own page links to"),
            ("Licence", item.licence), ("First reading", item.starts),
            ("How it is read", "Change only, each type: " + item.position),
            ("In the research", RESEARCH[None]),
            ("Break", "%s: %s" % item.breaks[0]), ("Credit", item.credit)])
        ws.print_area = "A1:L%d" % row
        return ws

    # -- Usable with care ---------------------------------------------------
    ws = sheet(CARE_NAME)
    last = 15
    widths(ws, [62, 11, 12, 26, 11, 12, 11, 11, 11, 14, 9, 9, 9, 80])
    title_band(ws, CARE_NAME, "The research's \"usable with care\" group, read the same way as the rest.", last,
               tab=K.SLATE)
    link(ws.cell(2, 2), "Overview", "Back to Overview")
    tile(ws, 3, 2, 2, "Series read", len(CARE), "#,##0")
    tile(ws, 3, 3, 4, "In the group, not read", len(CARE_NOT_READ), "#,##0")
    care_changes = [r for r in result["readings"] if r["reading"] == "change" and r["care"]]
    for i, d in enumerate((INCREASING, STABLE, DECREASING)):
        tile(ws, 3, 5 + 2 * i, 6 + 2 * i, ARROW[d], sum(1 for r in care_changes if r["direction"] == d), "#,##0")
    row = method_note(ws, 6, last, [
        (CARE_NAME, "Series the research calls usable with care: short, broken or heavily revised. They are read "
                    "the same way as the series on the Overview, so they can be set beside them, with why each "
                    "needs care in the last column."),
        ("Columns", "As on the Overview: where the level sits, the change against its normal range, and which way "
                    "it reads."),
    ] + ([("Quarters left out", left_words)] if left_words else []))
    cols = TABLE + ["Why with care"]
    for topic, keys in CARE_TOPICS:
        row = section(ws, row, topic, last)
        row = sub_header(ws, row, cols, right=(1, 2, 4, 5, 7, 8), centre=(6, 9, 10, 11, 12))
        for key in keys:
            reading_row(ws, row, key)
            item = items[key]
            care = item.care[0].upper() + item.care[1:] + "."
            put(ws, row, 15, care, font=F_NOTE, align=Alignment(wrap_text=True, vertical="center"))
            ws.row_dimensions[row].height = max(18, 14 * math.ceil(len(care) / 95) + 3)
            rule(ws, row, 2, last)
            row += 1
        row += 1
    not_read_care = [x for x in result["not_read"] if x["care"]]
    if not_read_care:
        row = section(ws, row, "Nothing to show, and why", last)
        row = sub_header(ws, row, ["Series", "Reading", "Why"], height=18)
        for x in not_read_care:
            put(ws, row, 2, BY_KEY[x["key"]].title, align=WRAP)
            put(ws, row, 3, reading_name(x["reading"], months), align=WRAP)
            ws.merge_cells(start_row=row, start_column=4, end_row=row, end_column=last)
            put(ws, row, 4, x["why"], font=F_NOTE, align=WRAP)
            ws.row_dimensions[row].height = 14 * max(2, math.ceil(len(x["why"]) / (width_of(ws, 4, last) * 1.2))) + 3
            rule(ws, row, 2, last)
            row += 1
        row += 1
    row = section(ws, row, "In the group, not read, and why", last)
    row = sub_header(ws, row, ["Series", "Why it is not read"], height=18)
    for what, why in CARE_NOT_READ:
        put(ws, row, 2, what)
        ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=last)
        put(ws, row, 3, why[0].upper() + why[1:] + ".", font=F_NOTE, align=WRAP)
        rule(ws, row, 2, last)
        row += 1
    credits = [(x.title, x.credit) for x in CARE if x.credit]
    if credits:
        row = section(ws, row + 1, "Credits the publishers' licences require", last)
        for what, words in credits:
            put(ws, row, 2, what, font=F_BOLD, align=WRAP)
            ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=last)
            put(ws, row, 3, words, align=WRAP)
            ws.row_dimensions[row].height = 14 * math.ceil(len(words) / 150) + 3
            rule(ws, row, 2, last)
            row += 1
    ws.freeze_panes = ws.cell(6, 3)

    # -- one sheet per series ----------------------------------------------
    for key in national:
        if key in HOUSEHOLD_KEYS:
            if key == HOUSEHOLD_KEYS[0]:
                household_tab()
            continue
        series_tab(key)
    for _, keys in CARE_TOPICS:
        for key in keys:
            series_tab(key, care=True)

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

    # -- Not read -----------------------------------------------------------
    if result["not_read"]:
        ws = sheet("Not read")
        widths(ws, [44, 24, 90])
        title_band(ws, "Not read", "Each reading the catalog holds that could not be read, and why.", 4,
                   record=True)
        row = sub_header(ws, 3, ["Series", "Reading", "Why"], height=18)
        for x in result["not_read"]:
            for j, v in enumerate((items[x["key"]].title, reading_name(x["reading"], months), x["why"]), 2):
                put(ws, row, j, v)
            rule(ws, row, 2, 4)
            row += 1

    # -- Glossary -----------------------------------------------------------
    ws = sheet("Glossary")
    widths(ws, [30, 120])
    title_band(ws, "Glossary", "Every term in this workbook, and how it is worked out.", 3, record=True)
    row = sub_header(ws, 3, ["Term", "What it means, and how it is worked out"], height=18)
    for term, meaning in glossary(s, whatif, zoom):
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
    # The fingerprint of each file's bytes as the run read them, not as the manifest recorded it at the pull
    # (Fable on #452: a file changed after the pull was published with the old fingerprint), and not as the file
    # is when the workbook is built (Codex on #452: the readings come from the bytes read).
    from .pull import file_name
    files = pull.manifest.get("files", {})
    # The readings' own fingerprints come first: a workbook drawn from other bytes than the run read would
    # publish one version's readings beside another's history, so it is refused (Codex on #452). Every file
    # the run could have read is read here too, so the two are compared whole: a file changed, gone or new since
    # the run is a mismatch (Codex on #452, twice).
    for item in READ:
        pull.points(item)
    ran = result["read_sha"]
    other = sorted(n for n in set(ran) | set(pull.read_sha) if ran.get(n) != pull.read_sha.get(n))
    if other:
        raise Refused("the workbook would draw %s from other bytes than the run read: changed, gone or new since "
                      "the run. Build the workbook from the Pull the run used." % ", ".join(other))
    read_sha = ran
    changed = [n for n, h in read_sha.items() if files.get(n, {}).get("sha256") not in (None, h)]
    # A file the pull fetched and the run never read (gone, unreadable, or one the pull could not read) has no
    # fingerprint as read: it is said so, not given the manifest's (Codex on #452).
    unread = {}
    for name in sorted({file_name(x) for x in SERIES}):
        if files.get(name, {}).get("sha256") and name not in read_sha:
            errs = [v["error"] for v in pull.manifest.get("series", {}).values()
                    if v.get("file") == name and v.get("error")]
            unread[name] = ("not read: the pull could not read it (%s)" % errs[0] if errs else
                            "not read: missing from the pull folder" if not (pull.folder / name).exists() else
                            "not read: it could not be read when the run read it")
    facts = [("Built", datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")),
             ("From the pull of", vintage), ("Tool", "threshold-engine %s, economic conditions" % VERSION),
             ("Readings", "%d (%d in the usable-with-care group)" % (
                 len(result["readings"]), sum(1 for r in result["readings"] if r["care"]))),
             ("Readings not read", len(result["not_read"])),
             ("Charts zoomed to", "%s to %s; no reading changes with it" % tuple(zoom) if zoom else
              "not zoomed: every chart draws its whole history"),
             ("Files changed since the pull", "%d: see Sources" % len(changed) if changed else "none"),
             ("Files fetched and not read", "%d: see Sources" % len(unread) if unread else "none")]
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
    for vals in rows:
        for j, v in enumerate(vals, 2):
            put(ws, row, j, v, align=WRAP, font=F_BOLD if whatif and j == 4 and vals[1] != vals[2] else None)
        ws.row_dimensions[row].height = 30
        rule(ws, row, 2, last)
        row += 1

    # -- Sources ------------------------------------------------------------
    ws = sheet("Sources")
    widths(ws, [44, 36, 30, 34, 13, 28, 60, 26, 66, 44])
    title_band(ws, "Sources", "Every file the pull fetched, and its fingerprint as the run read it.", 11,
               record=True)
    row = sub_header(ws, 3, ["Series", "Publisher", "Id at the source", "Licence", "First reading", "File", "Address",
                             "Fetched", "SHA-256 as read", "Since the pull"], height=18)
    for x in SERIES:
        name = file_name(x)
        f = files.get(name, {})
        for j, v in enumerate((x.title, x.publisher, x.source_id, x.licence, x.starts, name, f.get("url", ""),
                               f.get("fetched_at", f.get("error", "not in this pull")),
                               read_sha.get(name, "")), 2):
            put(ws, row, j, v)
        ws.cell(row, 10).font = Font(name="Consolas", size=9, color=K.SLATE)
        if name in changed:
            put(ws, row, 11, "changed after the pull, which recorded %s…" % f["sha256"][:16],
                font=Font(name="Calibri", size=10, bold=True, color=K.CRIMSON))
        elif name in unread:
            put(ws, row, 11, unread[name], font=Font(name="Calibri", size=10, bold=True, color=K.CRIMSON))
        rule(ws, row, 2, 11)
        row += 1
    for d in DERIVED:
        put(ws, row, 2, d.title)
        put(ws, row, 3, "made from " + " and ".join(BY_KEY[k].title for k in d.inputs))
        rule(ws, row, 2, 11)
        row += 1
    ws.freeze_panes = ws.cell(4, 3)

    # -- Dashboard data, then the Dashboard that looks it up ---------------------------------------------------
    # The data tab holds, month by month, every series' level, change, change in typical moves and where its
    # level sits in its history, all values; the Dashboard's formulas only pick two of those columns. A daily or
    # weekly series is drawn at each month's last reading.
    pickable = [k for k in national] + [k for _, keys in CARE_TOPICS for k in keys]
    monthly = {}
    for key in pickable:
        item = items[key]
        points = pull.points(item)
        if isinstance(points, str):
            continue
        mine = by_key.get(key, {})
        got = {"level": {}, "change": {}, "moves": {}, "place": {}}
        for d, v in kept(points, s["left_out"]):
            if v is not None:
                got["level"][d[:7]] = v
        chg = mine.get("change")
        for d, v in changes(kept(points, s["left_out"]), months, item.frequency, item.change_in):
            got["change"][d[:7]] = v
            if chg:
                got["moves"][d[:7]] = (v - chg["median"]) / chg["typical"]
        if mine.get("position"):
            window, _ = window_of(item, "position", points, s)
            ordered = sorted(v for _, v in window)
            for d, v in window:
                got["place"][d[:7]] = percentile(v, ordered) / 100
        monthly[key] = got
    every = sorted({m for g in monthly.values() for part in g.values() for m in part})
    if zoom:
        every = [m for m in every if quarter_index(zoom[0]) <= quarter_index(quarter_of(m + "-01"))
                 <= quarter_index(zoom[1])]
    dd = sheet(DASH_DATA)
    dd.sheet_state = "hidden"
    put(dd, 2, 1, "Month", font=F_BOLD)
    first_row, last_row = 3, 3 + max(len(every), 1) - 1
    for i, m in enumerate(every):
        dd.cell(first_row + i, 1, _date(m + "-01")).number_format = "yyyy-mm"
    names = []
    for j, key in enumerate(pickable):
        item, c0 = items[key], 2 + 4 * j
        names.append(item.title)
        dd.cell(1, c0, item.title)
        for k, (part, words) in enumerate((("level", "Level"), ("change", "Change"), ("moves", "Typical moves"),
                                           ("place", "At or above"))):
            dd.cell(2, c0 + k, words)
            for i, m in enumerate(every):
                v = monthly.get(key, {}).get(part, {}).get(m)
                if v is not None:
                    dd.cell(first_row + i, c0 + k, v)
    shown_months = set(every)
    s0 = 2 + 4 * len(pickable) + 1                  # the summary of each series, one row each, and the pick list
    stats = ["Series", "Unit", "Latest", "Value", "Level: at or above", "Change", "Change in", "Change to",
             "Normal from", "Normal to", "Direction", "Typical moves", "Since"]
    for k, words in enumerate(stats):
        dd.cell(2, s0 + k, words)
    for j, key in enumerate(pickable):
        item, mine, rr = items[key], by_key.get(key, {}), first_row + j
        now = latest_of(item)
        lvl, chg = mine.get("position"), mine.get("change")
        vals = [item.title, item.unit, _date(now[0]) if now else None, now[1] if now else None,
                lvl["percentile"] / 100 if lvl else ("change only" if item.position else None),
                chg["value"] if chg else None, "%" if item.change_in == "percent" else "points",
                _date(chg["date"]) if chg else None, chg["normal_low"] if chg else None,
                chg["normal_high"] if chg else None, ARROW[chg["direction"]] if chg else "not read",
                chg["movement"] if chg else None, _date(chg["since"]) if chg else None]
        drawn_ = sorted(m for part in ("level", "change") for m in monthly.get(key, {}).get(part, {})
                        if m in shown_months)
        vals += [_date(drawn_[0] + "-01") if drawn_ else None, _date(drawn_[-1] + "-01") if drawn_ else None]
        for k, v in enumerate(vals):
            if v is not None:
                dd.cell(rr, s0 + k, v)
    span_cols = (s0 + len(stats), s0 + len(stats) + 1)        # each series' first and last month drawn
    dd.cell(2, span_cols[0], "First month drawn")
    dd.cell(2, span_cols[1], "Last month drawn")
    data_end = L(span_cols[1])

    ws = dash
    widths(ws, [16, 13, 13, 18, 12, 12, 9, 12, 11, 11, 14, 11, 11])
    title_band(ws, DASHBOARD, "Pick any two series: both drawn together on scales they share, then each on "
                              "its own.", 14)
    link(ws.cell(2, 2), "Overview", "Back to Overview")
    picks = [("First series", "Unemployment rate"), ("Second series", "Initial jobless claims")]
    for i, (words, default) in enumerate(picks):
        rr = 4 + i
        put(ws, rr, 2, words, font=F_BOLD)
        ws.merge_cells(start_row=rr, start_column=3, end_row=rr, end_column=6)
        c = put(ws, rr, 3, default if default in names else names[i], font=Font(
            name="Arial", bold=True, size=11, color=PICK_COLOURS[i]))
        c.fill = K.solid(K.CANVAS)
        c.border = Border(bottom=side("medium", PICK_COLOURS[i]))
        ws.row_dimensions[rr].height = 20
    put(ws, 4, 8, "Pick a series from the list in each box.", font=F_NOTE)
    pick_list = "'%s'!$%s$%d:$%s$%d" % (DASH_DATA, L(s0), first_row, L(s0), first_row + len(names) - 1)
    dv = DataValidation(type="list", formula1=pick_list, allow_blank=False, showErrorMessage=True,
                        errorTitle="Not a series in this workbook", error="Pick a series from the list.")
    ws.add_data_validation(dv)
    dv.add("C4")
    dv.add("C5")
    # Where each pick's columns start on the data tab, and its row in the summary: hidden helpers.
    HELP = 40                                       # AN onwards, hidden: the helpers and the drawn columns
    for i in range(2):
        rr = 4 + i
        formula(ws, rr, HELP, "=MATCH($C$%d,'%s'!$1:$1,0)" % (rr, DASH_DATA))
        formula(ws, rr, HELP + 1, "=MATCH($C$%d,'%s'!$%s$%d:$%s$%d,0)" % (
            rr, DASH_DATA, L(s0), first_row, L(s0), first_row + len(names) - 1))
    header(ws, 7, [""] + stats[1:], right=(3, 4, 5, 8, 9), centre=(2, 6, 7, 10, 11, 12), height=20)
    fmts = [None, None, "yyyy-mm-dd", "General", "0.0%", "+#,##0.0#;-#,##0.0#;0", None, "yyyy-mm-dd",
            "+#,##0.0#;-#,##0.0#;0", "+#,##0.0#;-#,##0.0#;0", None, "+0.0;-0.0;0.0", "yyyy-mm"]
    for i in range(2):
        rr = 8 + i
        formula(ws, rr, 2, "=C%d" % (4 + i), font=Font(name="Calibri", size=10, bold=True, color=PICK_COLOURS[i]))
        for k in range(1, len(stats)):
            col = L(s0 + k)
            formula(ws, rr, 2 + k, "=IF(INDEX('%s'!$%s$%d:$%s$%d,$%s$%d)=\"\",\"\",INDEX('%s'!$%s$%d:$%s$%d,$%s$%d))"
                    % (DASH_DATA, col, first_row, col, first_row + len(names) - 1, L(HELP + 1), 4 + i, DASH_DATA, col,
                       first_row, col, first_row + len(names) - 1, L(HELP + 1), 4 + i), fmts[k],
                    align=CENTER if k in (6, 7, 10, 11, 12) else None)
        rule(ws, rr, 2, 14)
    row = method_note(ws, 11, 14, [
        ("Pick", "Choose a series in each box from its list. Every chart below follows the two boxes; nothing else "
                 "in the workbook changes."),
        ("Together, moving", "Each series' change over %d months, measured in its own typical moves from its own "
                             "median change, so two series of different units share one scale. Between the dashed "
                             "lines at %s and %s is normal movement; past them the change reads Increasing or "
                             "Decreasing." % (months, "%+g" % s["normal_width"], "%+g" % -s["normal_width"])),
        ("Together, levels", "Where each level sits in its own history, from 0% (its lowest) to 100% (its "
                             "highest), month by month. A series read on its change only has no line here."),
        ("Each on its own", "Each series' level and its change in its own units, the change with its normal range "
                            "dashed. Axes here fit whatever is picked, so a spike is not left off."),
        ("Months", "Every chart here is drawn month by month: a daily or weekly series at each month's last "
                   "reading, a quarterly one at the first month of each quarter."),
        ("Formulas", "This tab is the one place with formulas. They only look up values written on a hidden tab, "
                     "%s, so no reading moves." % DASH_DATA),
    ] + ([("Zoom", zoom_words)] if zoom_words else []) + ([("Quarters left out", left_words)] if left_words else []))
    # The drawn columns: the month, then for each pick the month again where it has a reading (so the time axis
    # fits the picks rather than every series in the book), its level, change, typical moves and place in its
    # history; a month with nothing is #N/A, which a chart skips.
    put(ws, 2, HELP + 2, "Month", font=F_NOTE)

    def col_of(i, k):
        """Pick i's drawn column k: 0 its months, 1 level, 2 change, 3 typical moves, 4 at or above."""
        return HELP + 3 + 5 * i + k
    for i in range(2):
        for k, words in enumerate(("Months", "Level", "Change", "Typical moves", "At or above")):
            put(ws, 2, col_of(i, k), "%s: %s" % (picks[i][0], words), font=F_NOTE)
    for n, m in enumerate(every):
        rr = first_row + n
        ws.cell(rr, HELP + 2, _date(m + "-01")).number_format = "yyyy-mm"
        for i in range(2):
            for k in range(4):
                where = "INDEX('%s'!$A$%d:$%s$%d,ROW()-%d,$%s$%d+%d)" % (
                    DASH_DATA, first_row, data_end, last_row, first_row - 1, L(HELP), 4 + i, k)
                formula(ws, rr, col_of(i, k + 1), "=IF(%s=\"\",NA(),%s)" % (where, where))
            formula(ws, rr, col_of(i, 0), "=IF(AND(ISNA(%s%d),ISNA(%s%d)),NA(),%s%d)" % (
                L(col_of(i, 1)), rr, L(col_of(i, 2)), rr, L(HELP + 2), rr), "yyyy-mm")
    # The dashed lines: two points each, from the first month either pick has to the last, or each pick's own,
    # looked up as values (a newer spreadsheet function such as AGGREGATE reads #NAME? unless the file marks it).
    LINES_AT = HELP + 13
    if every:
        def span_of(i, n):
            col = L(span_cols[n])
            return "INDEX('%s'!$%s$%d:$%s$%d,$%s$%d)" % (DASH_DATA, col, first_row, col, first_row + len(names) - 1,
                                                       L(HELP + 1), 4 + i)
        for n in range(2):
            rr = first_row + n
            pick = "MIN" if n == 0 else "MAX"
            one, two = span_of(0, n), span_of(1, n)
            formula(ws, rr, LINES_AT, "=%s(IFERROR(%s,%s),IFERROR(%s,%s))" % (pick, one, two, two, one), "yyyy-mm")
            ws.cell(rr, LINES_AT + 1, s["normal_width"])
            ws.cell(rr, LINES_AT + 2, -s["normal_width"])
            for i in range(2):
                formula(ws, rr, LINES_AT + 3 + 3 * i, "=IFERROR(%s+0,NA())" % span_of(i, n), "yyyy-mm")
                for k, col in enumerate((s0 + 8, s0 + 9)):     # each pick's normal range, from the summary
                    formula(ws, rr, LINES_AT + 4 + 3 * i + k, "=IFERROR(INDEX('%s'!$%s$%d:$%s$%d,$%s$%d)+0,NA())"
                            % (DASH_DATA, L(col), first_row, L(col), first_row + len(names) - 1, L(HELP + 1),
                               4 + i))
    for col in range(HELP, LINES_AT + 10):
        ws.column_dimensions[L(col)].hidden = True
    every_moves = [(m + "-01", v) for g in monthly.values() for m, v in g["moves"].items() if m in shown_months]

    def scatter(title, unit, ys, lines_=(), bounds=None, fmt="General"):
        """A chart of months: each of ``ys`` a (column, colour, the cell naming it); ``lines_`` dashed two-point
        lines (column, colour, words). ``bounds`` fixes the value axis; without it the axis fits the picks."""
        from openpyxl.chart.axis import NumericAxis
        ch = ScatterChart()
        ch.scatterStyle = "line"
        for col, xcol, colour, name in ys:
            xs = Reference(ws, min_col=xcol, min_row=first_row, max_row=last_row)
            ser = Series(Reference(ws, min_col=col, min_row=first_row, max_row=last_row), xs)
            ser.tx = SeriesLabel(strRef=StrRef(f="'%s'!%s" % (DASHBOARD, name)))
            ser.graphicalProperties.line = ln(colour, 2.0)
            ser.marker.symbol = "none"
            ser.smooth = False
            ch.series.append(ser)
        for col, xcol, colour, words in lines_:
            ser = Series(Reference(ws, min_col=col, min_row=first_row, max_row=first_row + 1),
                         Reference(ws, min_col=xcol, min_row=first_row, max_row=first_row + 1), title=words)
            ser.graphicalProperties.line = ln(colour, 1.25, "dash")
            ser.marker.symbol = "none"
            ser.smooth = False
            ch.series.append(ser)
        # The time axis is left to fit whatever is picked: its months are #N/A wherever a pick has no reading.
        x = NumericAxis(axId=500, crossAx=100)
        x.number_format = "yyyy"
        x.delete = False
        x.majorGridlines = None
        x.spPr = GraphicalProperties(ln=ln(K.STONE, 0.75))
        x.txPr = text()
        x.tickLblPos = "low"
        ch.x_axis = x
        y = ch.y_axis
        y.axId, y.crossAx = 100, 500
        y.delete = False
        y.majorGridlines = None
        y.spPr = GraphicalProperties(ln=ln(K.STONE, 0.75))
        y.txPr = text()
        y.number_format = fmt
        y.title = unit
        if bounds:
            y.scaling.min, y.scaling.max = bounds[0], bounds[1]
            y.majorUnit = bounds[2]
        ch.title = title
        ch.title.tx.rich.p[0].pPr = ParagraphProperties(defRPr=CharacterProperties(sz=1000, b=True,
                                                                                    solidFill=K.INK))
        ch.legend = Legend()
        ch.legend.position = "b"
        ch.legend.txPr = text(9, K.INK_TEXT)
        ch.display_blanks = "gap"
        ch.visible_cells_only = False       # the drawn columns are hidden helpers
        ch.height, ch.width = 9, 26
        ch.roundedCorners = False
        ch.graphical_properties = GraphicalProperties(ln=LineProperties(noFill=True))
        return ch

    if every:
        w_ = s["normal_width"]
        lo, hi, step, above, below = axis_view(every_moves or [("", 0.0)], s["axis_cut"], [w_, -w_])
        moves_title = "Both changes over %d months, in typical moves from each one's median" % months
        ws.add_chart(scatter(moves_title, "typical moves", [(col_of(0, 3), col_of(0, 0), PICK_COLOURS[0], "$C$4"),
                                                             (col_of(1, 3), col_of(1, 0), PICK_COLOURS[1], "$C$5")],
                             [(LINES_AT + 1, LINES_AT, K.STONE, "Normal: top"),
                              (LINES_AT + 2, LINES_AT, K.STONE, "Normal: bottom")],
                             (lo, hi, step), "+0.0;-0.0;0"), "B%d" % row)
        row += 19
        if s["axis_cut"] and (above or below):
            note(ws, row, 2, "The axis runs from %s to %s typical moves: %g%% of every series' changes at each end "
                             "run off it, so the rest can be read. No reading changes." % (
                                 "%+g" % lo, "%+g" % hi, s["axis_cut"]), 14)
            row += 1
        row += 1
        ws.add_chart(scatter("Both levels: where each sits in its own history", "at or above, of its history",
                             [(col_of(0, 4), col_of(0, 0), PICK_COLOURS[0], "$C$4"),
                              (col_of(1, 4), col_of(1, 0), PICK_COLOURS[1], "$C$5")],
                             bounds=(0, 1, 0.25), fmt="0%"), "B%d" % row)
        row += 21
        for i in range(2):
            formula(ws, row, 2, "=C%d" % (4 + i), font=Font(name="Arial", bold=True, size=11, color=PICK_COLOURS[i]))
            row += 1
            ws.add_chart(scatter("Level", "its own units", [(col_of(i, 1), col_of(i, 0), PICK_COLOURS[i],
                                                             "$C$%d" % (4 + i))]), "B%d" % row)
            row += 19
            ws.add_chart(scatter("Change over %d months, its normal range dashed" % months, "points or percent",
                                 [(col_of(i, 2), col_of(i, 0), PICK_COLOURS[i], "$C$%d" % (4 + i))],
                                 [(LINES_AT + 4 + 3 * i, LINES_AT + 3 + 3 * i, K.STONE, "Normal from"),
                                  (LINES_AT + 5 + 3 * i, LINES_AT + 3 + 3 * i, K.STONE, "Normal to")]), "B%d" % row)
            row += 20
    else:
        put(ws, row, 2, "No months to draw%s." % (" in %s to %s" % tuple(zoom) if zoom else ""), font=F_NOTE)
    ws.print_area = "A1:N%d" % row
    wb.calculation.fullCalcOnLoad = True            # Excel works out the lookups when the file opens

    # Values only, whatever wrote them: a text beginning with "=" (a settings file named "=x.json", say) is kept
    # as text and never stored as a formula (Codex on #452). The Dashboard's own lookups are the one exception,
    # and each was recorded as it was written.
    # Only the cells that exist: walking every row would add an empty one to the file wherever a row has none.
    for sheet_ in wb.worksheets:
        for c in sheet_._cells.values():
            if c.data_type == "f" and (sheet_.title, c.coordinate) not in formulas:
                c.data_type = "s"
    wb.save(out)
    return out


def glossary(s, whatif=None, zoom=None):
    """Every term the workbook uses, worded from the settings the run used."""
    m, w = s["change_months"], s["normal_width"]
    moves = "one typical move" if w == 1 else "%g typical moves" % w
    terms = [
        ("Level", "The latest reading itself, compared with every reading in the series' own history."),
        ("Level: at or above", "The share of the readings in the series' history that the latest is at or above, "
                               "counted from the lowest. 100% is the highest reading in that history; near 0% is "
                               "near the lowest. It says where the reading sits, not whether that is good or bad."),
        ("Change over %d months" % m,
         "The latest reading minus the reading %d months earlier. For a rate, a spread or an index around zero it "
         "is in points; for a level that grows (prices, jobs, output, credit, claims, debt) it is a percent of the "
         "earlier reading. Weekly and daily series count whole weeks (12 months is 52), as FRED does; a day with "
         "no reading that many weeks before has no change." % m),
        ("Typical move", "1.4826 times the median distance of a series' changes from their median change: for "
                         "changes shaped like a bell, about one standard deviation, but a spike does not widen it. "
                         "It is the measure the loss thresholds use for ordinary year-to-year movement."),
        ("Normal range", "The median change in the series' history plus or minus %s. Each series has its own."
         % moves),
        ("Increasing, Stable, Decreasing", "Stable: the change is inside its normal range. Increasing: at or above "
                                           "its top. Decreasing: at or below its bottom. For a series that usually "
                                           "grows, such as prices, Increasing means growing faster than it "
                                           "normally does and Decreasing slower, or falling. None of the three "
                                           "says better or worse."),
        ("Typical moves (a number)", "How far the change is from the median change, in typical moves: +2.0 is two "
                                     "typical moves above it. The same scale for every series, so their moves can be "
                                     "compared; the Dashboard draws two together on it."),
        ("Since", "The first of the unbroken run of changes, up to the latest, that read the same way, each read "
                  "against the same normal range."),
        ("History from", "The first reading each series is measured against. %s"
         % ("Every series is measured against its full history." if s["history"] == "full" else
            "Each is measured against the last %d years." % s["history"]["years"])),
        ("Quarters left out", "Quarters the firm takes out of every history: %s. A reading in one is not measured "
                              "against and not drawn; a change with either end in one is not counted."
         % (spans(s["left_out"]) if s["left_out"] else "none at present")),
        ("Off the chart", "A chart's axis may leave off up to %g%% of its readings at each end, so a spike does not "
                          "flatten the rest; a note under the chart names the furthest. The latest reading and the "
                          "normal range always stay on, and no reading changes." % s["axis_cut"]
         if s["axis_cut"] else "Every reading stays on every chart: the firm's settings leave none off."),
        ("Change only", "A level that climbs over the decades with prices and the economy sits near the top of "
                        "its own history in almost every year, so its place there says nothing. Only its change is "
                        "read."),
        ("In the research", "Which way the research says a series signals stress, where it says so. It is shown "
                            "on each series' tab as a fact about the research and changes no reading."),
        ("Sahm reading", "The 3-month average unemployment rate minus its lowest 3-month average in the 12 months "
                         "before. Sahm's published trigger is 0.50. Shown beside the change, never used to read it. "
                         "Where a month has no value (October 2025), the average is taken from the two months that "
                         "do, as FRED does."),
        ("Pulled", "The day the data was downloaded. Every pull is kept in its own folder, so a reading can always "
                   "be traced to the release it used."),
        ("No value published", "A period the publisher left blank, such as October 2025 (the lapse in "
                               "appropriations). It stays empty: never filled, never read as zero."),
        ("Made from two series", "House prices against income, and the mortgage rate over the 10-year Treasury, "
                                 "are worked out from two series in the same pull. Each tab says how."),
        ("Break", "A change in how the publisher builds the series, or a known seasonal step, that a reader should "
                  "know before comparing across it."),
        ("Not read", "A reading the catalog holds that the pull could not supply or that has too little history. "
                     "The Not read tab says which and why, when there are any."),
        (CARE_NAME, "A series from the research's usable-with-care group: short, broken or heavily revised. It is "
                    "read the same way as the rest, with why it needs care beside it."),
        (HOUSEHOLD_NAME, "The NY Fed's household debt by type, as its Quarterly Report on Household Debt and "
                         "Credit gives it, from the New York Fed Consumer Credit Panel / Equifax."),
        (DASHBOARD, "Pick any two series to see together: both changes in typical moves, both levels as where "
                    "they sit in their own histories, and each one's own charts."),
    ]
    if zoom:
        terms.append(("Zoom", "Every chart in this workbook is drawn over %s to %s only. The readings are "
                              "measured against their whole history windows all the same." % tuple(zoom)))
    if whatif:
        terms += [
            ("As you have it", "The readings from the firm's settings file, %s: every reading on every other tab."
             % whatif["a"]),
            ("What if", "The same pull read with a second settings file, %s. It changes no reading anywhere else in "
                        "the workbook, and neither file is changed." % whatif["b"]),
            ("Move", "From Decreasing through Stable to Increasing: ▲ when the what-if reads a change more upward, ▼ "
                     "more downward."),
            ("Dashed lines", "On a series' change chart: its normal range under the what-if, over the years its "
                             "history covers. Drawn only where the two count the change over the same months."),
        ]
    return terms
