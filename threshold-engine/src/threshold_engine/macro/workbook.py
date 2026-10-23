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

from .catalog import BY_KEY, CARE, CARE_DERIVED, CARE_NOT_READ, DERIVED, HOUSEHOLD_DEBT, READ, SERIES, STATES
from .compare import CALLED, NOT_ASKED, plain, row_label, spans, when
from .readings import (DECREASING, DIRECTIONS, INCREASING, STABLE, changes, kept, percentile, sahm_kept,
                       window_of)
from .settings import QUESTIONS, Refused, left_out_set, quarter_index, quarter_label, quarter_of, readings_of

#: Claude Design's tokens for this workbook, round 1 (docs/macro/design/round-1, keybank_style_additions.py). Kept
#: here rather than appended to keybank_style.py, which the threshold workbook also reads; the rest are its tokens.
MACRO_LINK = "1F4E79"    # every link: series names, the row of links under the title, the What if tile; no underline
MACRO_RULE = "EFEBE4"    # the rule under every data row, and the charts' gridlines
ROW_RULE = MACRO_RULE
#: Where a series tab keeps its history, past the 24 columns its tiles and charts use (B:Y), and the hidden columns
#: its charts draw from.
SERIES_COLS = {"date": 27, "value": 28, "change": 29, "note": 30, "level": 32, "latest_level": 33, "band": 34,
               "latest_change": 36, "whatif": 37, "off_level": 39, "off_change": 40, "sahm": 41, "trigger": 42}
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
#: The Dashboard's two picks: the reference palette's first two slots, which pass every pair. 4.4:1 and 3.0:1 on white,
#: so every chart that draws them carries a legend, and the readings table names them.
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
                         "real_wages_eci", "hourly_earnings", "wage_tracker", "real_income", "income_ex_transfers",
                         "saving_rate"]),
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
    "real_wages_eci": "Wages after inflation", "hourly_earnings": "Hourly earnings", "wage_tracker": "Wage tracker",
    "real_income": "Real income", "income_ex_transfers": "Income ex transfers",
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
    from openpyxl.chart.legend import Legend, LegendEntry
    from openpyxl.chart.series import SeriesLabel, StrRef
    from openpyxl.chart.shapes import GraphicalProperties
    from openpyxl.chart.text import RichText
    from openpyxl.drawing.line import LineProperties
    from openpyxl.drawing.text import CharacterProperties, Paragraph, ParagraphProperties
    from openpyxl.styles import Alignment, Border, Font, Side
    from openpyxl.utils import get_column_letter as L
    from openpyxl.worksheet.datavalidation import DataValidation

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

    F_DATA = Font(name="Calibri", size=11, color=K.INK_TEXT)
    F_BOLD = Font(name="Calibri", size=11, bold=True, color=K.INK_TEXT)
    F_NOTE = Font(name="Calibri", size=10, color=K.SLATE)
    F_FIELD = Font(name="Arial", size=9, bold=True, color=K.SLATE)        # a tile's, a box's or a header's label
    F_LABEL = Font(name="Calibri", size=9, color=K.SLATE)                 # a field's label inside a tile
    F_BIG = Font(name="Arial", size=14, bold=True, color=K.INK_TEXT)       # a tile's figure on a chart tab
    F_LINK = Font(name="Calibri", size=11, color=MACRO_LINK)
    F_NAV = Font(name="Calibri", size=10, color=MACRO_LINK)                # the links in row 2
    F_UP = Font(name="Calibri", size=11, bold=True, color=K.INK_TEXT)
    WRAP = Alignment(wrap_text=True, vertical="top")
    CENTER = Alignment(horizontal="center", vertical="center")
    MIDDLE = Alignment(vertical="center")
    RIGHT = Alignment(horizontal="right", vertical="center")
    INDENT = Alignment(horizontal="left", vertical="center", indent=1)

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

    # -- the house anatomy (Claude Design's round 1 for this workbook, docs/macro/design/round-1) -------------------
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

    def px(ws, col):
        """A column's width in pixels at 100%: 7 a width unit, and 5."""
        return 7 * (ws.column_dimensions[L(col)].width or 8.43) + 5

    def width_of(ws, first, last):
        return sum((ws.column_dimensions[L(c)].width or 9) for c in range(first, last + 1))

    def lines_of(ws, words, first, last):
        """How many lines ``words`` takes across columns ``first`` to ``last``, at 6.6 pixels a character."""
        room = sum(px(ws, c) for c in range(first, last + 1)) - 8
        return max(1, math.ceil(len(str(words)) * 6.6 / max(room, 1)))

    def title_band(ws, title, sub, last, record=False, tab=None):
        """Row 1, 27 pt: the tab's name in Arial 16 bold on ink (slate on the record tabs), the subtitle in the
        first column past the name, a thick red rule under both (stone on the record tabs). Row 2 holds the links
        and row 3 is a spacer. ``tab`` is the tab's colour; the record tabs have none."""
        fill, rule_ = (K.SLATE, K.STONE) if record else (K.INK, K.KEY_RED)
        for col in range(1, last + 1):
            c = ws.cell(1, col)
            c.fill = K.solid(fill)
            c.border = Border(bottom=side("thick", rule_))
        c = ws.cell(1, 2, title)
        c.font = Font(name="Arial", bold=True, size=16, color=K.PAPER)
        c.alignment = MIDDLE
        # The subtitle is its own cell, in the first column past the title (Arial 16 bold runs about 12.4 px a
        # character), as PocketBook writes it. Not rich text in one cell: no workbook the firm opens in Excel uses
        # that, and the firm's Excel refused this one (17 Oct 2026).
        need, col, used = len(title) * 12.4 + 20, 2, 0
        while used < need and col < last:
            used += px(ws, col)
            col += 1
        s_ = ws.cell(1, col, sub)
        s_.font = Font(name="Calibri", size=10, color=K.MIST if record else K.STONE)
        s_.alignment = MIDDLE
        ws.row_dimensions[1].height = 27
        ws.row_dimensions[2].height = 15
        ws.row_dimensions[3].height = 6
        ws.sheet_properties.tabColor = tab

    def method_note(ws, top, last, entries, label_cols=1, first=2):
        """The tab's one method note, at its foot and folded away: a canvas heading row, then one row per entry,
        the label bold and the words in one merged cell that wraps. The plus beside the row numbers opens it. It
        moved here from the top of the tab with no word changed (Claude Design, round 1)."""
        for col in range(first, last + 1):
            ws.cell(top, col).fill = K.solid(K.CANVAS)
        ws.cell(top, first, "How this tab works").font = F_FIELD
        ws.row_dimensions[top].height = 15
        text_col = first + label_cols
        r = top + 1
        for name, words in entries:
            for col in range(first, last + 1):
                ws.cell(r, col).fill = K.solid(K.CANVAS)
            a = ws.cell(r, first, name)
            a.font, a.alignment = F_BOLD, Alignment(vertical="top")
            ws.merge_cells(start_row=r, start_column=text_col, end_row=r, end_column=last)
            b = ws.cell(r, text_col, words)
            b.font, b.alignment = F_DATA, WRAP
            ws.row_dimensions[r].height = 15 * lines_of(ws, words, text_col, last) + 3
            r += 1
        if r > top + 1:
            ws.row_dimensions.group(top + 1, r - 1, outline_level=1, hidden=True)
        ws.sheet_properties.outlinePr.summaryBelow = False
        return r + 1

    def tile(ws, row, first, last, name, value, fmt=None, to=None, big=False):
        """A headline figure over two rows: canvas, a thick red rule on top and a white edge on the left (the gap
        between tiles), the label in Arial 9 bold, the figure in Arial 12 bold (14 on a chart tab)."""
        for rr in (row, row + 1):
            for col in range(first, last + 1):
                c = ws.cell(rr, col)
                c.fill = K.solid(K.CANVAS)
                c.border = Border(top=side("thick", K.KEY_RED) if rr == row else None,
                                  left=side("medium", K.PAPER) if col == first else None)
            if last > first:
                ws.merge_cells(start_row=rr, start_column=first, end_row=rr, end_column=last)
        a = ws.cell(row, first, name)
        a.font, a.alignment = F_FIELD, INDENT
        b = ws.cell(row + 1, first, value)
        b.font = Font(name="Arial", bold=True, size=14 if big else 12, color=MACRO_LINK if to else K.INK_TEXT)
        b.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        if fmt:
            b.number_format = fmt
        if to:
            b.hyperlink = "#'%s'!A1" % to
        ws.row_dimensions[row].height = 15
        ws.row_dimensions[row + 1].height = 22

    def section(ws, row, words, last, first=2):
        """A section's name in Arial 10 bold over a medium ink rule, 18 pt, and no band: the title band is the one
        dark thing on a tab (Claude Design, round 1)."""
        for col in range(first, last + 1):
            ws.cell(row, col).border = Border(bottom=side("medium", K.INK))
        c = ws.cell(row, first, words)
        c.font, c.alignment = Font(name="Arial", bold=True, size=10, color=K.INK), Alignment(vertical="bottom")
        ws.row_dimensions[row].height = 18
        return row + 1

    def header(ws, row, heads, first=2, right=(), centre=(), height=24):
        """A table's column headers: canvas, Arial 9 bold slate, wrapped, a thin stone rule under them, each aligned
        as its column's figures."""
        for i, h in enumerate(heads):
            c = ws.cell(row, first + i, h)
            c.fill = K.solid(K.CANVAS)
            c.font = F_FIELD
            c.border = Border(bottom=side("thin", K.STONE))
            c.alignment = Alignment(wrap_text=True, vertical="bottom", horizontal="right" if i in right else
                                    "center" if i in centre else "left")
        ws.row_dimensions[row].height = height
        return row + 1
    sub_header = header

    def rule(ws, row, first, last):
        for col in range(first, last + 1):
            c = ws.cell(row, col)
            c.border = Border(left=c.border.left, bottom=side("thin", MACRO_RULE))

    def way(ws, row, col, d, size=11):
        """A direction as a cell shows it: moving bold on mist, the same fill both ways, so it reads as moving and
        never as better or worse; Stable slate, unfilled."""
        c = ws.cell(row, col, ARROW[d])
        moving = d != STABLE
        c.font = Font(name="Calibri", bold=moving, size=size, color=K.INK if moving else K.SLATE)
        if moving:
            c.fill = K.solid(K.MIST)
        c.alignment = CENTER
        return c

    def link(cell, sheet_name, text_=None, nav=False):
        if text_ is not None:
            cell.value = text_
        cell.hyperlink = "#'%s'!A1" % sheet_name
        cell.font = F_NAV if nav else F_LINK
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

    def merged(ws, row, first, last, value, fmt=None, font=None, align=None):
        if last > first:
            ws.merge_cells(start_row=row, start_column=first, end_row=row, end_column=last)
        return put(ws, row, first, value, fmt, font, align)

    def formula(ws, row, col, text_, fmt=None, font=None, align=None):
        """A Dashboard formula, kept as one when every other text beginning "=" is made text."""
        c = put(ws, row, col, text_, fmt, font, align)
        formulas.add((ws.title, c.coordinate))
        return c

    def when_cell(ws, row, col, d, frequency, font=None, align=None, last=None):
        """A reading's date as the tables give it: a quarter as text ("2026 Q2"), a month as yyyy-mm, a week or a
        day as yyyy-mm-dd."""
        put_ = (lambda *a: merged(ws, row, col, last, *a)) if last else (lambda *a: put(ws, row, col, *a))
        if frequency == "quarterly":
            return put_(_when(d, "quarterly"), None, font, align or RIGHT)
        return put_(_date(d), "yyyy-mm-dd" if frequency in ("daily", "weekly") else "yyyy-mm", font, align or RIGHT)

    def since_cell(ws, row, col, d, frequency, font=None, align=None, last=None):
        """Since and History from: a quarter as text, anything else as yyyy-mm."""
        return when_cell(ws, row, col, d, "quarterly" if frequency == "quarterly" else "monthly", font, align, last)

    def change_value(item, v):
        """A change as a cell holds it: a percent change as a fraction, so the cell's format shows %."""
        if item.change_in == "percent":
            return v / 100, "+0.00%;-0.00%;0.00%"
        return v, "+0.00;-0.00;0.00"

    def signed(item, v):
        return "%s%s%s" % ("+" if v > 0 else "", _num(v), "%" if item.change_in == "percent" else "")

    def latest_of(item):
        """The latest reading kept: one in a quarter left out is not shown as the latest beside readings measured
        from an earlier one (Codex on #471); the series' tab says when later readings were left out."""
        pts = pull.points(item)
        if isinstance(pts, str):
            return None
        return next(((d, v) for d, v in reversed(kept(pts, s["left_out"])) if v is not None), None)

    left_words = ("Left out of every history: %s. A reading in those quarters is not measured against, and a "
                  "change with either end in one is not counted." % spans(s["left_out"])) if s["left_out"] else ""
    zoom_words = ("The charts show %s to %s only. Every reading is measured against its history all the same; "
                  "only the view changes." % tuple(zoom)) if zoom else ""

    # -- the reading tables (Overview, States, Usable with care) ----------------------------------------------
    TABLE = ["Series", "Latest", "Value", "Unit", "Level: at or above", "Change over %d months" % months,
             "Change to", "Normal from", "Normal to", "Direction", "Typical moves", "Since", "History from"]
    TABLE_RIGHT, TABLE_CENTRE = (1, 2, 4, 5, 6, 7, 8, 10, 11, 12), (9,)
    TABLE_WIDTHS = [58, 10.71, 10.71, 31, 10.71, 11.86, 10.71, 11.86, 11.86, 14.57, 9.29, 9.29, 9.29]

    def reading_row(ws, row, key, name_col_text=None, unit=True):
        """One series' row: the latest value, where it sits, its change against its normal range."""
        item = items[key]
        got = by_key.get(key, {})
        lvl, chg = got.get("position"), got.get("change")
        link(ws.cell(row, 2), tab_of(key), name_col_text or item.title)
        if unit:
            put(ws, row, 5, item.unit, font=F_NOTE, align=INDENT)
        now = latest_of(item)
        if now:
            when_cell(ws, row, 3, now[0], item.frequency)
            put(ws, row, 4, now[1], value_format(now[1]), align=RIGHT)
        else:
            put(ws, row, 3, "not in this pull", font=F_NOTE, align=RIGHT)
        if lvl:
            put(ws, row, 6, lvl["percentile"] / 100, "0.0%", align=RIGHT)
        elif item.position:
            put(ws, row, 6, "change only", font=F_NOTE, align=RIGHT)
        if chg:
            put(ws, row, 7, *change_value(item, chg["value"]), align=RIGHT)
            # The change's own month, only when it is not the latest's, and then bold: when a reading the horizon
            # back is missing (October 2025) or left out, the latest change is an earlier one's (Codex on #452).
            if not now or chg["date"] != now[0]:
                when_cell(ws, row, 8, chg["date"], item.frequency, font=F_BOLD)
            for col, v in ((9, chg["normal_low"]), (10, chg["normal_high"])):
                put(ws, row, col, *change_value(item, v), align=RIGHT)
            way(ws, row, 11, chg["direction"])
            put(ws, row, 12, chg["movement"], "+0.0;-0.0;0.0", align=RIGHT)
            since_cell(ws, row, 13, chg["since"], item.frequency)
        if lvl or chg:
            since_cell(ws, row, 14, (lvl or chg)["history_from"], item.frequency)
        return got

    def what_if_text(key):
        """A series' What if cell: what moved, or was read on one side only, or under neither. Blank when its
        readings read the same way under both: the tile counts those (Claude Design, round 1)."""
        mine = list(wrows.get(key, {}).values())
        said = move_text(mine, whatif["months"])
        return said or ("" if any(r["a"] and r["b"] for r in mine) else "not read under either"), bool(said)

    def credits(ws, row, last, keys, label_last=2):
        """The wording a publisher's licence asks for wherever its figures are shown: once for each publisher
        whose series the tab shows, at the foot of the tab (Codex on #471: the Overview showed the NY Fed's
        household debt without it)."""
        said = {}
        for key in keys:
            item = items.get(key)
            if key in by_key and getattr(item, "credit", ""):     # only where its figures are on the tab
                said.setdefault(item.credit, item.publisher)
        if not said:
            return row
        row = section(ws, row + 1, "Credits the publishers' licences require", last)
        for words, who in said.items():
            merged(ws, row, 2, label_last, who, font=F_BOLD, align=WRAP)
            merged(ws, row, label_last + 1, last, words, font=F_NOTE, align=WRAP)
            ws.row_dimensions[row].height = 15 * max(lines_of(ws, words, label_last + 1, last),
                                                     lines_of(ws, who, 2, label_last)) + 3
            rule(ws, row, 2, last)
            row += 1
        return row

    # -- Overview -----------------------------------------------------------
    ws = sheet("Overview", first=True)
    last = 15 if whatif else 14
    widths(ws, TABLE_WIDTHS + ([26] if whatif else []))
    title_band(ws, "Economic conditions", "Public data, pulled %s. Where each series sits in its own history, "
                                          "and whether it is moving more than it normally does." % vintage, last,
               tab=K.INK)
    link(ws.cell(2, 2), DASHBOARD, "Dashboard: any two series together", nav=True)
    link(ws.cell(2, 3), CARE_NAME, "Also read, with care: %d series" % len(CARE + CARE_DERIVED), nav=True)
    core_changes = [r for r in result["readings"] if r["reading"] == "change" and not r["care"]
                    and r["key"] not in state_keys]
    tile(ws, 4, 2, 2, "From the pull of", vintage)
    tile(ws, 4, 3, 4, "Changes read", len(core_changes), "#,##0")
    for i, d in enumerate((INCREASING, STABLE, DECREASING)):
        first_ = (5, 6, 8)[i]
        tile(ws, 4, first_, (5, 7, 9)[i], ARROW[d], sum(1 for r in core_changes if r["direction"] == d), "#,##0")
    sahm_x = next(iter(result["alongside"]), None)
    if sahm_x:
        tile(ws, 4, 10, 12, "Sahm reading, beside the change", "%.2f in %s" % (
            sahm_x["value"], _date(sahm_x["date"]).strftime("%b %Y")))
    if whatif:
        nat = [x for x in whatif["rows"] if x["key"] not in state_keys and x["reading"] == "change"]
        tile(ws, 4, 13, 15, "What if: %s" % whatif["b"], "%d of %d changes read another way" % (
            sum(1 for x in nat if x["move"]), sum(1 for x in nat if x["move"] is not None)), to="What if")
    ws.row_dimensions[6].height = 9
    header(ws, 7, TABLE + (["What if"] if whatif else []), right=TABLE_RIGHT, centre=TABLE_CENTRE)
    row = 8

    def overview_row(row, key):
        got = reading_row(ws, row, key)
        if not got:
            put(ws, row, 6, "not read: see the Not read tab", font=F_NOTE)
        height = 15
        if whatif:
            said, moved = what_if_text(key)
            put(ws, row, 15, said, font=F_UP if moved else F_NOTE, align=Alignment(vertical="center",
                                                                                  wrap_text=True))
            height = 15 * lines_of(ws, said, 15, 15)
        ws.row_dimensions[row].height = height
        rule(ws, row, 2, last)
        return row + 1
    for t, (topic, keys) in enumerate(TOPICS):
        if t:
            ws.row_dimensions[row].height = 6
            row += 1
        row = section(ws, row, topic, last)
        for key in keys:
            if key in HOUSEHOLD_KEYS and key != "household_total":
                continue                                    # folded under the total, below
            row = overview_row(row, key)
            if key == "household_total":
                start = row
                for k in HOUSEHOLD_KEYS[:-1]:
                    row = overview_row(row, k)
                ws.row_dimensions.group(start, row - 1, outline_level=1, hidden=True)
    row = credits(ws, row, last, national)
    ws.row_dimensions[row].height = 12
    row += 1
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
                               "same way." % (len(CARE + CARE_DERIVED), CARE_NAME)))
    method_note(ws, row, last, entries)
    ws.freeze_panes = "C8"

    # -- Dashboard (written after the data it looks up; its place in the tab order is kept here) ---------------
    dash = sheet(DASHBOARD)

    # -- What if ----------------------------------------------------------
    if whatif:
        ws = sheet("What if")
        last = 14
        widths(ws, [54, 22, 11, 11, 14.57, 9.29, 20, 11, 14.57, 9.29, 20, 11, 9])
        title_band(ws, "What if", "%s against %s, both reading the pull of %s." % (whatif["b"], whatif["a"], vintage),
                   last, tab=K.INK)
        link(ws.cell(2, 2), "Overview", "Back to Overview", nav=True)
        nat = [x for x in whatif["rows"] if x["key"] not in state_keys]
        sts = [x for x in whatif["rows"] if x["key"] in state_keys]
        both = [x for x in nat if x["move"] is not None]
        tile(ws, 4, 2, 2, "National changes read under both", len(both))
        tile(ws, 4, 3, 3, "The same way", sum(1 for x in both if x["move"] == 0))
        tile(ws, 4, 4, 5, "More upward", sum(1 for x in both if x["move"] > 0))
        tile(ws, 4, 6, 7, "More downward", sum(1 for x in both if x["move"] < 0))
        tile(ws, 4, 8, 10, "State changes read another way", "%d of %d" % (
            sum(1 for x in sts if x["move"]), sum(1 for x in sts if x["move"] is not None)))
        tile(ws, 4, 11, 14, "Read under one set only", sum(1 for x in whatif["rows"] if not (x["a"] and x["b"])
                                                           and (x["a"] or x["b"])))
        ws.row_dimensions[6].height = 9
        row = 7
        what_if_entries = [
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
        ]
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
            ws.row_dimensions[rr].height = 15 if max(len(x["a"]), len(x["b"])) < 50 else 30
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
                    c.fill = K.solid(K.CANVAS)
                    c.border = Border(left=side("medium", K.PAPER) if col == a else None)
                c = ws.cell(rr, a, words)
                c.font, c.alignment = F_FIELD, CENTER
            ws.row_dimensions[rr].height = 15
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
            ws.row_dimensions[rr].height = 15 if x["same_measure"] else 28
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
        row = credits(ws, row, last, [x["key"] for x in whatif["rows"]])
        row = method_note(ws, row + 1, last, what_if_entries)
        ws.print_area = "A1:N%d" % row

    # -- States -----------------------------------------------------------
    # Two tables side by side, 26 states and 25, so all 51 sit on one screen; read down the left, then the right
    # (Claude Design, round 1). Each table: State, Latest, rate, level, change, normal range, direction, typical
    # moves, since, history from, and What if with a second settings file.
    ws = sheet("States")
    per = 12 if whatif else 11
    # "Unemployment rate" broke mid-word at the design's 9.57 (LibreOffice, 22 Oct 2026): its column is 12.
    one = [7, 9.57, 12, 9.57, 9.57, 9.57, 9.57, 14.57, 9.29, 9.29, 9.29] + ([13] if whatif else [])
    widths(ws, one + [2.71] + one)
    last = 2 + 2 * per
    title_band(ws, "Unemployment by state", "Bureau of Labor Statistics, Local Area Unemployment Statistics "
                                            "(LAUS), pulled %s." % vintage, last, tab=K.INK)
    link(ws.cell(2, 2), "Overview", "Back to Overview", nav=True)
    heads = ["State", "Latest", "Unemployment rate", "Level: at or above", "Change over %d months" % months,
             "Normal from", "Normal to", "Direction", "Typical moves", "Since", "History from"] + (
        ["What if"] if whatif else [])
    for c0 in (2, 3 + per):
        header(ws, 4, heads, first=c0, right=(1, 2, 3, 4, 5, 6, 8, 9, 10), centre=(7,), height=33)

    def standing(st):
        chg = by_key.get("unemployment_" + st.lower(), {}).get("change")
        if not chg:
            return (2, 0, st)
        return (0 if chg["direction"] != STABLE else 1, -abs(chg["movement"]), st)
    ordered_states = sorted(STATES, key=standing)
    half = (len(ordered_states) + 1) // 2
    tall = 0
    for n, st in enumerate(ordered_states):
        c0 = 2 if n < half else 3 + per
        row = 5 + (n if n < half else n - half)
        key = "unemployment_" + st.lower()
        got = by_key.get(key, {})
        lvl, chg = got.get("position"), got.get("change")
        put(ws, row, c0, st)
        if lvl:
            put(ws, row, c0 + 1, _date(lvl["date"]), "yyyy-mm", align=RIGHT)
            put(ws, row, c0 + 2, lvl["value"], "0.0", align=RIGHT)
            put(ws, row, c0 + 3, lvl["percentile"] / 100, "0.0%", align=RIGHT)
            put(ws, row, c0 + 10, _date(lvl["history_from"]), "yyyy-mm", align=RIGHT)
        if chg:
            put(ws, row, c0 + 4, chg["value"], "+0.00;-0.00;0.00", align=RIGHT)
            put(ws, row, c0 + 5, chg["normal_low"], "+0.00;-0.00;0.00", align=RIGHT)
            put(ws, row, c0 + 6, chg["normal_high"], "+0.00;-0.00;0.00", align=RIGHT)
            way(ws, row, c0 + 7, chg["direction"])
            put(ws, row, c0 + 8, chg["movement"], "+0.0;-0.0;0.0", align=RIGHT)
            put(ws, row, c0 + 9, _date(chg["since"]), "yyyy-mm", align=RIGHT)
        if not got:
            put(ws, row, c0 + 1, "not in this pull", font=F_NOTE)
        if whatif:
            said, moved = what_if_text(key)
            put(ws, row, c0 + 11, said, font=F_UP if moved else F_NOTE)
        ws.row_dimensions[row].height = 15
        rule(ws, row, c0, c0 + per - 1)
        tall = max(tall, row)
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
    ws.row_dimensions[tall + 1].height = 12
    method_note(ws, tall + 2, last, entries, label_cols=2)
    ws.freeze_panes = "A5"

    # -- charts -------------------------------------------------------------
    from openpyxl.chart.axis import ChartLines
    C = SERIES_COLS
    HALF, FULL, TALL = 22.86, 45.72, 8.47            # chart widths and height in cm: 864 and 1,728 by 320 px

    def gridlines():
        return ChartLines(spPr=GraphicalProperties(ln=ln(MACRO_RULE, 0.75)))

    def place(ws, chart_, first_col, first_row, last_col, last_row):
        """A chart anchored to its cells corner to corner, so it fills the same columns in Excel and LibreOffice,
        which give a column different widths in pixels: drawn at a size in centimetres, the NY Fed's chart ran
        over the table beside it in LibreOffice (22 Oct 2026)."""
        from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, TwoCellAnchor
        ws.add_chart(chart_, TwoCellAnchor(_from=AnchorMarker(col=first_col - 1, row=first_row - 1),
                                           to=AnchorMarker(col=last_col, row=last_row)))

    def chart_title(chart_, words):
        chart_.title = words
        chart_.title.tx.rich.p[0].pPr = ParagraphProperties(defRPr=CharacterProperties(sz=1000, b=True,
                                                                                        solidFill=K.INK_TEXT))
        chart_.title.overlay = False

    def axis_title(ax, words):
        ax.title = words
        ax.title.tx.rich.p[0].pPr = ParagraphProperties(defRPr=CharacterProperties(sz=900, b=True,
                                                                                    solidFill=K.INK_TEXT))

    def major_years(span, full=False):
        """The x axis's step in years: 10 over 60 years drawn, 5 over 12, else 2; on a chart the full width of the
        tab, 5 (Claude Design, round 1). One for four years or fewer, so a short zoom still has its years."""
        if full:
            return 5 if span > 12 else 2 if span > 4 else 1
        return 10 if span > 60 else 5 if span > 12 else 2 if span > 4 else 1

    def years_axis(dates, frequency, full=False):
        """A date axis labelled every 1, 2, 5 or 10 years at the foot of the chart. On a text axis LibreOffice
        ignores the label skip and prints nearly every year (the walk of 16 Oct 2026)."""
        from openpyxl.chart.axis import DateAxis
        span = max(1, int(dates[-1][:4]) - int(dates[0][:4]))
        ax = DateAxis(crossAx=100)
        ax.number_format = "yyyy"
        ax.majorTimeUnit = "years"
        ax.majorUnit = major_years(span, full)
        ax.baseTimeUnit = "months" if frequency in ("monthly", "quarterly") else "days"
        ax.delete = False
        ax.majorGridlines = None
        ax.majorTickMark = "out"
        ax.spPr = GraphicalProperties(ln=ln(K.STONE, 0.75))
        ax.txPr = text()
        ax.tickLblPos = "low"
        ax.crosses = "min"                       # at the foot, wherever zero falls
        return ax

    def finish(chart_, title, unit, axis, step, x_axis, width=HALF, height=TALL, signed_axis=False):
        """The value axis, the title and the frame every history chart shares: gridlines in the row rule's colour,
        the unit as the axis title, no border."""
        ax = chart_.y_axis
        ax.delete = False
        ax.majorGridlines = gridlines()
        ax.spPr = GraphicalProperties(ln=ln(K.STONE, 0.75))
        ax.txPr = text()
        ax.scaling.min, ax.scaling.max = axis
        ax.majorUnit = step
        if signed_axis:
            ax.number_format = "+0.0;-0.0;0" if step < 1 else "+#,##0;-#,##0;0"
        else:
            ax.number_format = "#,##0" if step >= 1 else "0.0#"
        axis_title(ax, unit)
        # The band and the latest point live in hidden helper columns; a chart plots only visible cells unless
        # told otherwise.
        chart_.visible_cells_only = False
        chart_title(chart_, title)
        chart_.legend = None
        chart_.display_blanks = "gap"
        chart_.height, chart_.width = height, width
        chart_.roundedCorners = False
        chart_.graphical_properties = GraphicalProperties(ln=LineProperties(noFill=True))

    def history_chart(ws, title, unit, data_col, first, last, latest_col, frequency, axis, step, band_col=None,
                      dashed_col=None, head=None, off_col=None, width=HALF, height=TALL, full=False,
                      signed_axis=False, label_fmt="#,##0.0#", date_col=None):
        """The history in ink with the latest reading ringed, over rows ``first`` to ``last``; ``head`` is the
        header row naming each column. With ``band_col``, the normal range is shaded behind it (two hidden
        columns: an unfilled base at the range's bottom and the range's height); with ``dashed_col``, the
        what-if's range is dashed over it; with ``off_col``, a triangle at the axis's edge on each reading that
        runs off it.

        The band is the chart underneath and the lines are laid over it: LibreOffice draws in the order
        charts are combined, Excel draws areas first whatever the order, so this order reads the same in
        both."""
        date_col = date_col or C["date"]
        cats = Reference(ws, min_col=date_col, min_row=first, max_row=last)

        def add(chart_, col):
            # Each series titled from the header row and drawn from the rows asked for: a zoomed range does not
            # start under its header. Every series carries its own dates; without them Excel places a line on
            # 1, 2, 3 ... of a date axis, 1900 (Fable's report on #452).
            ser = Series(Reference(ws, min_col=col, min_row=first, max_row=last), title=ws.cell(head, col).value)
            chart_.series.append(ser)
            return ser
        x_axis = years_axis([ws.cell(first, date_col).value.isoformat(), ws.cell(last, date_col).value.isoformat()],
                            frequency, full)
        line = LineChart()
        hist = add(line, data_col)
        line.set_categories(cats)
        hist.graphicalProperties.line = ln(K.INK, 1.5)
        hist.marker.symbol = "none"
        hist.smooth = False
        latest = LineChart()
        pt = add(latest, latest_col)
        latest.set_categories(cats)
        pt.graphicalProperties.line.noFill = True
        pt.marker.symbol = "circle"
        pt.marker.size = 7
        pt.marker.graphicalProperties = GraphicalProperties(solidFill=K.PAPER, ln=ln(K.INK, 1.5))
        pt.dLbls = DataLabelList()
        pt.dLbls.showVal, pt.dLbls.showCatName, pt.dLbls.showSerName, pt.dLbls.showLegendKey = True, False, False, False
        pt.dLbls.position = "l"             # inside the plot: at the right, LibreOffice clipped it off the edge
        pt.dLbls.numFmt = label_fmt
        pt.dLbls.txPr = text(9, K.INK_TEXT, True)
        dashed = None
        if dashed_col:
            dashed = LineChart()
            for col in (dashed_col, dashed_col + 1):
                s_ = add(dashed, col)
                s_.graphicalProperties.line = ln(K.SLATE, 1.0, "sysDash")
                s_.marker.symbol = "none"
                s_.smooth = False
            dashed.set_categories(cats)
        off = None
        if off_col:
            off = LineChart()
            s_ = add(off, off_col)
            off.set_categories(cats)
            s_.graphicalProperties.line.noFill = True
            s_.marker.symbol = "triangle"
            s_.marker.size = 6
            s_.marker.graphicalProperties = GraphicalProperties(solidFill=K.STONE, ln=ln(K.SLATE, 0.75))
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
        layers = ([base] + ([line] if band_col else []) + ([dashed] if dashed else []) + ([off] if off else [])
                  + [latest])
        for chart_ in layers:
            chart_.x_axis = x_axis              # one axis for every layer, or the lines drift off the band
            # and the value axis crosses that axis: left at its default (10, an axis this chart does not have),
            # Excel refused the whole file (17 Oct 2026); LibreOffice drew it anyway
            chart_.y_axis.crossAx = x_axis.axId
        finish(base, title, unit, axis, step, x_axis, width, height, signed_axis)
        if frequency == "daily":
            # A day with no reading is a holiday, not a gap in the record: the line joins the days either side,
            # or a daily line breaks at every holiday (the prime rate, 22 Oct 2026). A month or a week with no
            # value still leaves a gap.
            base.display_blanks = "span"
        for chart_ in layers[1:]:
            base += chart_
        return base

    def history_tab(ws, key, item, mine, points, chart_row):
        """The history in AA to AD, from row 4 (date, value, the change as read, a note), the hidden columns the
        charts draw from past it, and the level and change charts side by side from ``chart_row``, each with its
        note under it. A series read on its change only has the one chart, the full width of the tab."""
        chg = dict(changes(kept(points, s["left_out"]), months, item.frequency, item.change_in))
        top = 4
        header(ws, top, ["Date", "Value", "Change over %d months" % months, "Note"], first=C["date"],
               right=(0, 1, 2), height=18)
        first = top + 1
        dates = []
        for i, (d, v) in enumerate(points):
            rr = first + i
            dates.append(_date(d).isoformat())
            put(ws, rr, C["date"], _date(d), "yyyy-mm-dd", align=RIGHT)
            # A missing value stays an empty cell: text there would be drawn as zero on the chart, the very
            # error the readers are kept from.
            if v is not None:
                put(ws, rr, C["value"], v, value_format(v), align=RIGHT)
                if quarter_of(dates[-1]) in left:
                    put(ws, rr, C["note"], "left out (%s)" % quarter_of(dates[-1]), font=F_NOTE)
                else:
                    ws.cell(rr, C["level"], v)              # the level as drawn: left-out quarters stay empty
            else:
                put(ws, rr, C["note"], "no value published", font=F_NOTE)
            if dates[-1] in chg:
                put(ws, rr, C["change"], chg[dates[-1]], "#,##0.0#", align=RIGHT)
        last = first + len(points) - 1
        span = zoom_rows(dates, zoom)
        for col in range(C["note"] + 1, C["trigger"] + 1):
            ws.column_dimensions[L(col)].hidden = True
        put(ws, top, C["level"], "Level", font=F_NOTE)
        put(ws, top, C["off_level"], "Off the axis: level", font=F_NOTE)
        put(ws, top, C["off_change"], "Off the axis: change", font=F_NOTE)
        row_of = {d: first + i for i, d in enumerate(dates)}
        plans = []
        for reading in readings_of(item):
            r = mine.get(reading)
            w = (wrows.get(key, {}).get(reading) or {}) if whatif else {}
            wb_ = w.get("b") if w and w.get("same_measure") and reading == "change" else None
            if not r and not wb_:
                continue
            if span is None:
                plans.append((reading, None, "No reading of its %s falls in %s to %s, the quarters the charts are "
                              "zoomed to." % ("level" if reading == "position" else "change", zoom[0], zoom[1])))
                continue
            a, b = first + span[0], first + span[1]
            data_col = C["level"] if reading == "position" else C["change"]
            seen = [(dates[i - first], ws.cell(i, data_col).value) for i in range(a, b + 1)
                    if ws.cell(i, data_col).value is not None]
            if seen:
                plans.append((reading, (r, wb_, a, b, data_col, seen), None))
        full = len(plans) == 1 and plans[0][0] == "change"
        anchors = ["B", "N"] if len(plans) == 2 else ["B"]
        note_cols = [(2, 13), (14, 25)] if len(plans) == 2 else [(2, 25 if full else 13)]
        tallest = 0
        for n, (reading, plan, words) in enumerate(plans):
            if plan is None:
                note(ws, chart_row + n, 2, words, 25)
                tallest = max(tallest, 1)
                continue
            r, wb_, a, b, data_col, seen = plan
            ref = r or wb_
            keep = []
            latest_row = row_of[_date(ref["date"]).isoformat()]
            # Read under the what-if only, the latest is the what-if's, which this side's column may not hold
            # (Codex on #471: an empty cell there failed the whole build).
            latest = ws.cell(latest_row, data_col).value if a <= latest_row <= b else None
            if latest is not None:
                keep.append(latest)
            band_col = dashed_col = None
            if reading == "change":
                if r:
                    keep += [r["normal_low"], r["normal_high"]]
                if wb_:
                    keep += [wb_["normal_low"], wb_["normal_high"]]
            lo, hi, step, above, below = axis_view(seen, s["axis_cut"], keep)
            latest_col = C["latest_level"] if reading == "position" else C["latest_change"]
            put(ws, top, latest_col, "Latest", font=F_NOTE)
            if latest is not None:
                # Rounded here: LibreOffice ignores a label's own number format.
                ws.cell(latest_row, latest_col, round(latest, 2))
            off_col = C["off_level"] if reading == "position" else C["off_change"]
            for d, v in above:
                ws.cell(row_of[d[:10]], off_col, hi)
            for d, v in below:
                ws.cell(row_of[d[:10]], off_col, lo)
            if reading == "change" and r:
                band_col = C["band"]
                put(ws, top, band_col, "Normal from", font=F_NOTE)
                put(ws, top, band_col + 1, "Normal range", font=F_NOTE)
                for rr in range(a, b + 1):
                    ws.cell(rr, band_col, r["normal_low"])
                    ws.cell(rr, band_col + 1, r["normal_high"] - r["normal_low"])
            if wb_:
                # The what-if's range: two lines over the years its history covers.
                dashed_col = C["whatif"]
                start = _date(wb_["history_from"]).isoformat()
                put(ws, top, dashed_col, "What if: normal from", font=F_NOTE)
                put(ws, top, dashed_col + 1, "What if: normal to", font=F_NOTE)
                for i in range(a, b + 1):
                    if dates[i - first] >= start:
                        ws.cell(i, dashed_col, wb_["normal_low"])
                        ws.cell(i, dashed_col + 1, wb_["normal_high"])
            title = ("Level against its history" if reading == "position" else
                     "Change over %d months, its normal range shaded" % months)
            if reading == "change" and not r:
                title = "Change over %d months; not read under these settings" % months
            if dashed_col:
                title += " (dashed: the normal range under the what-if)"
            unit = item.unit if reading == "position" else ("percent" if item.change_in == "percent" else "points")
            first_col = 2 if anchors[n] == "B" else 14
            place(ws, history_chart(ws, title, unit, data_col, a, b, latest_col, item.frequency, (lo, hi), step,
                                    band_col, dashed_col, head=top, off_col=off_col,
                                    width=FULL if full else HALF, full=full, signed_axis=reading == "change",
                                    label_fmt="#,##0.0#" if reading == "position" else "+0.00;-0.00;0.00"),
                  first_col, chart_row, 25 if full else first_col + 11, chart_row + 15)
            said = off_edge(above, below, item.frequency,
                            (lambda v: "%s %s" % (_num(v), item.unit)) if reading == "position" else
                            (lambda v: signed(item, v) + ("" if item.change_in == "percent" else " points")))
            if said:
                note(ws, chart_row + 16, note_cols[n][0], said, note_cols[n][1])
            tallest = 16
        if tallest == 16:
            ws.row_dimensions[chart_row + 16].height = 27
            ws.row_dimensions[chart_row + 17].height = 9
            return chart_row + 18, top, first, last, dates, span
        return chart_row + tallest + 1, top, first, last, dates, span

    def facts_rows(ws, row, facts, first=2, last=13):
        """What it is: each label bold in B:C, its words in D:M, one row each, as tall as its words."""
        for k, v in facts:
            merged(ws, row, first, first + 1, k, font=F_BOLD, align=WRAP)
            merged(ws, row, first + 2, last, v, align=WRAP)
            ws.row_dimensions[row].height = 15 * lines_of(ws, v, first + 2, last) + 2
            rule(ws, row, first, last)
            row += 1
        return row

    def boxes(ws, item, key, mine, sahm=None, level_tile=None, what_if_row=True):
        """The tiles at the top of a series' tab, rows 4 to 7: its level (B:G), its change (H:S) and, beside the
        unemployment rate, the Sahm reading (T:Y), each figure under the label the tables give it; with a what-if,
        row 8 says how each reads under it. Returns the row the charts start on (Claude Design, round 1)."""
        rows = 5 if (whatif and what_if_row) else 4
        spans_ = [(2, 7), (8, 19)] + ([(20, 25)] if sahm else [])
        for a, b in spans_:
            for rr in range(4, 4 + rows):
                for col in range(a, b + 1):
                    c = ws.cell(rr, col)
                    c.fill = K.solid(K.CANVAS)
                    c.border = Border(top=side("thick", K.KEY_RED) if rr == 4 else None,
                                      left=side("medium", K.PAPER) if col == a else None)
        put(ws, 4, 8, "CHANGE OVER %d MONTHS" % months, font=F_FIELD, align=INDENT)
        lvl, chg = mine.get("position"), mine.get("change")
        if level_tile:
            level_tile(ws)
        else:
            put(ws, 4, 2, "LEVEL", font=F_FIELD, align=INDENT)
            now = latest_of(item)
            if now:
                merged(ws, 5, 2, 3, now[1], value_format(now[1]), F_BIG, INDENT)
                merged(ws, 5, 4, 5, item.unit, font=F_NOTE, align=INDENT)
                when_cell(ws, 5, 6, now[0], item.frequency, last=7)
            if lvl:
                for col, words in ((2, "Level: at or above"), (4, "Lowest"), (6, "Highest")):
                    merged(ws, 6, col, col + 1, words, font=F_LABEL, align=Alignment(vertical="bottom", indent=1))
                merged(ws, 7, 2, 3, lvl["percentile"] / 100, "0.0%", align=INDENT)
                merged(ws, 7, 4, 5, lvl["lowest"], value_format(lvl["lowest"]), align=INDENT)
                merged(ws, 7, 6, 7, lvl["highest"], value_format(lvl["highest"]), align=INDENT)
            elif item.position:
                merged(ws, 7, 2, 7, "change only", font=F_NOTE, align=INDENT)
            else:
                merged(ws, 7, 2, 7, "not read: see What it is", font=F_NOTE, align=INDENT)
        if chg:
            ws.merge_cells(start_row=5, start_column=8, end_row=5, end_column=9)
            way(ws, 5, 8, chg["direction"])
            merged(ws, 5, 10, 11, *change_value(item, chg["value"]), font=F_BIG, align=RIGHT)
            merged(ws, 5, 12, 13, "percent" if item.change_in == "percent" else "points", font=F_NOTE,
                   align=INDENT)
            when_cell(ws, 5, 14, chg["date"], item.frequency, last=15, align=INDENT)
            for col, words in ((8, "Normal from"), (10, "Normal to"), (12, "Typical moves"), (14, "Since"),
                               (16, "History from")):
                merged(ws, 6, col, col + 1, words, font=F_LABEL, align=Alignment(vertical="bottom", indent=1))
            merged(ws, 7, 8, 9, *change_value(item, chg["normal_low"]), align=INDENT)
            merged(ws, 7, 10, 11, *change_value(item, chg["normal_high"]), align=INDENT)
            merged(ws, 7, 12, 13, chg["movement"], "+0.0;-0.0;0.0", align=INDENT)
            since_cell(ws, 7, 14, chg["since"], item.frequency, last=15, align=INDENT)
            since_cell(ws, 7, 16, chg["history_from"], item.frequency, last=17, align=INDENT)
        else:
            merged(ws, 7, 8, 19, "not read: see What it is", font=F_NOTE, align=INDENT)
        if sahm:
            put(ws, 4, 20, "SAHM READING, BESIDE THE CHANGE", font=F_FIELD, align=INDENT)
            merged(ws, 5, 20, 21, sahm["value"], "0.00", F_BIG, INDENT)
            merged(ws, 5, 22, 23, "points", font=F_NOTE, align=INDENT)
            when_cell(ws, 5, 24, sahm["date"], "monthly", last=25)
            merged(ws, 6, 20, 25, "Sahm's published trigger", font=F_LABEL,
                   align=Alignment(vertical="bottom", indent=1))
            merged(ws, 7, 20, 25, 0.50, "0.00", align=INDENT)
        for rr, h in ((4, 18), (5, 24), (6, 13.5), (7, 15)):
            ws.row_dimensions[rr].height = h
        if rows == 5:
            lines = 1
            for reading, (a, b) in (("position", (2, 7)), ("change", (8, 19))):
                w = wrows.get(key, {}).get(reading)
                if not w:
                    continue
                put(ws, 8, a, "WHAT IF", font=F_FIELD, align=INDENT)
                bb = w["b"]
                if bb and reading == "change":
                    ws.merge_cells(start_row=8, start_column=a + 1, end_row=8, end_column=a + 2)
                    way(ws, 8, a + 1, bb["direction"])
                    noun = "changes" if w["same_measure"] else "changes over %s" % b_months
                    words = "%s: %+.1f typical moves; normal range %s to %s, from %s %s since %s." % (
                        "Read under the what-if only" if not w["a"] else "The same way" if w["move"] == 0 else
                        "Reads another way", bb["movement"], signed(item, bb["normal_low"]),
                        signed(item, bb["normal_high"]), "{:,}".format(bb["readings"]), noun, when(bb["history_from"]))
                    merged(ws, 8, a + 3, b, words, font=F_UP if w["move"] else F_DATA, align=WRAP)
                    lines = max(lines, lines_of(ws, words, a + 3, b))
                else:
                    words = ("At or above %.1f%% of %s readings since %s." % (
                        bb["percentile"], "{:,}".format(bb["readings"]), when(bb["history_from"])) if bb else
                        "Not read under the what-if: %s." % w["why_b"])
                    merged(ws, 8, a + 1, b, words, align=WRAP)
                    lines = max(lines, lines_of(ws, words, a + 1, b))
            ws.row_dimensions[8].height = 15 * lines
        ws.row_dimensions[4 + rows].height = 9
        return 4 + rows + 1

    def chart_entries(item, extra=(), history_cols="AA to AD"):
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
        out_.append(("History", "Every reading, with its change over %d months as read, is in columns %s. A "
                                "period the publisher left blank stays empty and reads no value published."
                     % (months, history_cols)))
        return out_

    def sentences(item, key, mine):
        """The tool's two sentences, the level's and the change's, for the end of What it is."""
        out_ = []
        for reading in ("position", "change"):
            r = mine.get(reading)
            if r:
                words = r["sentence"]
            elif reading == "position" and item.position:
                words = "Change only: " + item.position + "."
            else:
                words = "Not read: %s." % missing_by.get(key, {}).get(reading, "not in this pull")
            out_.append((reading_name(reading, months), words))
        return out_

    def series_tab(key, care=False):
        item = items[key]
        mine = by_key.get(key, {})
        ws = sheet(CARE_TAB[key] if care else TAB[key])
        widths(ws, [9.57] * 24 + [2.71, 10.71, 12, 14, 20])
        source = BY_KEY.get(key)
        title_band(ws, item.title, "%s · %s · %s · pulled %s%s" % (
            source.publisher if source else "made from two series", item.unit, item.frequency, vintage,
            " · usable with care" if care else ""), 26)
        link(ws.cell(2, 2), CARE_NAME if care else "Overview", "Back to " + (CARE_NAME if care else "Overview"),
             nav=True)
        link(ws.cell(2, 5), DASHBOARD, "Dashboard", nav=True)
        if whatif:
            link(ws.cell(2, 8), "What if", "What if", nav=True)
        sahm_x = next(iter(result["alongside"]), None) if key == "unemployment" else None
        chart_row = boxes(ws, item, key, mine, sahm=sahm_x)
        extra = []
        if whatif and any((wrows.get(key, {}).get(rd) or {}).get("b") for rd in ("change",)):
            extra.append(("Dashed lines", "The normal range under %s, over the years its history covers. Drawn "
                                          "only where the two count the change over the same months." % whatif["b"]))
        points = pull.points(item)
        if isinstance(points, str) or not any(v is not None for _, v in points):
            # Nothing to draw: said, not drawn (Fable on #452: a file of headers only crashed the Sahm chart).
            put(ws, chart_row, 2, points if isinstance(points, str) else
                "The pull of %s holds no values for this series." % vintage, font=F_NOTE)
            row = facts_rows(ws, section(ws, chart_row + 2, "What it is", 13), sentences(item, key, mine))
            method_note(ws, row + 1, 25, chart_entries(item, extra))
            ws.print_area = "A1:Y%d" % row
            ws.freeze_panes = "A4"
            return ws
        row, top, first, last, dates, span = history_tab(ws, key, item, mine, points, chart_row)
        facts_at = row
        sahm_drawn = key == "unemployment" and s["show_sahm"] and span is not None
        if sahm_drawn:
            sv = dict(sahm_kept(points, s["left_out"]))       # as the Overview's reading is (Codex on #471)
            header(ws, top, ["Sahm reading", "Trigger"], first=C["sahm"], right=(0, 1), height=18)
            for i, d in enumerate(dates):
                if d in sv:
                    put(ws, first + i, C["sahm"], sv[d], "0.00")
                    ws.cell(first + i, C["trigger"], 0.50)
            a, b = first + span[0], first + span[1]
            sc = LineChart()
            for col in (C["sahm"], C["trigger"]):          # the zoom's rows, each titled by its header
                sc.series.append(Series(Reference(ws, min_col=col, min_row=a, max_row=b),
                                        title=ws.cell(top, col).value))
            sc.set_categories(Reference(ws, min_col=C["date"], min_row=a, max_row=b))
            sc.series[0].graphicalProperties.line = ln(K.INK, 1.5)
            sc.series[1].graphicalProperties.line = ln(K.SLATE, 1.0, "sysDash")
            for s_ in sc.series:
                s_.marker.symbol = "none"
                s_.smooth = False
            sc.x_axis = years_axis([dates[span[0]], dates[span[1]]], "monthly")
            sc.y_axis.crossAx = sc.x_axis.axId
            sc.y_axis.delete = False
            sc.y_axis.majorGridlines = gridlines()
            sc.y_axis.spPr = GraphicalProperties(ln=ln(K.STONE, 0.75))
            sc.y_axis.txPr = text()
            sc.y_axis.number_format = "+0;-0;0"
            chart_title(sc, "Sahm reading, beside the change: dashed line at Sahm's trigger, 0.50")
            sc.legend = None
            sc.display_blanks = "gap"
            sc.visible_cells_only = False         # the Sahm columns are hidden helpers
            sc.height, sc.width = 5.82, HALF
            sc.roundedCorners = False
            sc.graphical_properties = GraphicalProperties(ln=LineProperties(noFill=True))
            place(ws, sc, 14, facts_at, 25, facts_at + 10)
        row = section(ws, facts_at, "What it is", 13)
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
        row = facts_rows(ws, row, facts + sentences(item, key, mine))
        if sahm_drawn:
            row = max(row, facts_at + 12)
        ws.row_dimensions[row].height = 12
        end = method_note(ws, row + 1, 25, chart_entries(item, extra))
        # Printed, a tab is its readings, charts and facts; its history stays on screen.
        ws.print_area = "A1:Y%d" % (end - 1)
        ws.freeze_panes = "A4"
        return ws

    # -- Household debt -----------------------------------------------------
    #: Where the tab keeps the NY Fed's history, past the 24 columns of tiles and charts, and the hidden columns its
    #: charts draw from.
    HH = {"date": 27, "types": 28, "note": 35, "change": 36, "drawn": 37, "label": 43, "band": 44, "latest": 46,
          "off": 47, "whatif": 48}

    def household_tab():
        ws = sheet(HOUSEHOLD_NAME)
        widths(ws, [9.57] * 24 + [2.71, 10.71] + [10] * 7 + [16, 12])
        title_band(ws, HOUSEHOLD_NAME, "NY Fed, Quarterly Report on Household Debt and Credit · trillions of "
                                       "dollars · quarterly · pulled %s" % vintage, 26)
        link(ws.cell(2, 2), "Overview", "Back to Overview", nav=True)
        link(ws.cell(2, 5), DASHBOARD, "Dashboard", nav=True)
        item = BY_KEY["household_total"]
        now = latest_of(item)
        cols = {key: dict(p) for key, p in ((k, pull.points(BY_KEY[k])) for k in HOUSEHOLD_KEYS)
                if not isinstance(p, str)}
        quarters = sorted({d for c in cols.values() for d in c})

        def level_tile(ws):
            put(ws, 4, 2, "Total, %s" % _when(now[0], "quarterly") if now else "Total", font=F_FIELD, align=INDENT)
            if now:
                merged(ws, 5, 2, 7, now[1], '"$"0.00" trillion"', F_BIG, INDENT)
            merged(ws, 6, 2, 7, "History from", font=F_LABEL, align=Alignment(vertical="bottom", indent=1))
            if quarters:
                merged(ws, 7, 2, 7, _when(quarters[0], "quarterly"), align=INDENT)
        boxes(ws, item, "household_total", by_key.get("household_total", {}), level_tile=level_tile,
              what_if_row=False)
        # The table of every type, beside the NY Fed's chart.
        section(ws, 9, "Each type, latest quarter", 25, first=14)
        heads = [(14, 15, "Type, as the NY Fed heads it"), (16, 16, "Balance, $ trillions"), (17, 17, "Share of total"),
                 (18, 18, "Change over %d months" % months), (19, 19, "Normal from"), (20, 20, "Normal to"),
                 (21, 22, "Direction"), (23, 23, "Typical moves"), (24, 24, "Since"), (25, 25, "History from")]
        for a, b, words in heads:
            header(ws, 10, [words] + [None] * (b - a), first=a, right=() if a in (14, 21) else (0,),
                   centre=(0,) if a == 21 else (), height=33)
            if b > a:
                ws.merge_cells(start_row=10, start_column=a, end_row=10, end_column=b)
        row = 11
        for key, column, _ in HOUSEHOLD_DEBT:
            it = BY_KEY[key]
            total_row = key == "household_total"
            merged(ws, row, 14, 15, column, font=F_BOLD if total_row else F_DATA)
            v = latest_of(it)
            chg = by_key.get(key, {}).get("change")
            older = bool(v and now and v[0] != now[0])
            if older:
                # A type the NY Fed's newest quarter leaves blank: its balance and change are an older quarter's,
                # and the table is headed the latest one, so it says so instead (Codex on #471).
                merged(ws, row, 16, 25, "No %s value in the NY Fed's file; its latest is %s." % (
                    _when(now[0], "quarterly"), _when(v[0], "quarterly")), font=F_NOTE)
                chg = None
            elif v:
                put(ws, row, 16, v[1], "0.000", F_BOLD if total_row else None, RIGHT)
                if now and now[1]:
                    put(ws, row, 17, v[1] / now[1], "0.0%", F_BOLD if total_row else None, RIGHT)
            if chg:
                put(ws, row, 18, *change_value(it, chg["value"]), align=RIGHT)
                put(ws, row, 19, *change_value(it, chg["normal_low"]), align=RIGHT)
                put(ws, row, 20, *change_value(it, chg["normal_high"]), align=RIGHT)
                ws.merge_cells(start_row=row, start_column=21, end_row=row, end_column=22)
                way(ws, row, 21, chg["direction"])
                put(ws, row, 23, chg["movement"], "+0.0;-0.0;0.0", align=RIGHT)
                since_cell(ws, row, 24, chg["since"], "quarterly")
                since_cell(ws, row, 25, chg["history_from"], "quarterly")
            elif key in missing_by and not older:
                merged(ws, row, 18, 25, "Not read: " + missing_by[key]["change"], font=F_NOTE)
            ws.row_dimensions[row].height = 15
            rule(ws, row, 14, 25)
            if total_row:
                for col in range(14, 26):
                    ws.cell(row, col).border = Border(top=side("thin", K.INK), bottom=side("thin", MACRO_RULE))
            row += 1
        ws.row_dimensions[18].height = 9
        entries = [
            ("As reported", "The NY Fed's own split and its own chart, Total Debt Balance and Its Composition: "
                            "mortgage, home equity revolving, auto loan, credit card, student loan and other, in "
                            "trillions of dollars, from 2003 Q1."),
            ("Share", "Each type's balance as a share of the total, this workbook's arithmetic."),
            ("Change, direction", "Each type's change over %d months in percent, against its own normal range, "
                                  "read as every other series is." % months),
        ] + chart_entries(item)[1:-1] + [
            ("History", "Every quarter, each type as the NY Fed reports it, is in columns AA to AH. A quarter with no "
                        "figure stays empty.")]
        facts = [
            ("Source", "NY Fed, Quarterly Report on Household Debt and Credit: the data workbook's sheet Page 3 "
                       "Data, read from the file the report's own page links to"),
            ("Licence", item.licence), ("First reading", item.starts),
            ("How it is read", "Change only, each type: " + item.position),
            ("In the research", RESEARCH[None]),
            ("Break", "%s: %s" % item.breaks[0]), ("Credit", item.credit)]
        if not quarters:
            put(ws, 20, 2, "The pull of %s holds no household debt figures." % vintage, font=F_NOTE)
            row = facts_rows(ws, section(ws, 29, "What it is", 13), facts)
            method_note(ws, row + 1, 25, entries)
            ws.print_area = "A1:Y%d" % row
            ws.freeze_panes = "A4"
            return ws
        top = 4
        header(ws, top, ["Quarter"] + [c for _, c, _ in HOUSEHOLD_DEBT] + ["Note"], first=HH["date"],
               right=tuple(range(0, 8)), height=18)
        first = top + 1
        for i, d in enumerate(quarters):
            rr = first + i
            put(ws, rr, HH["date"], _date(d), "yyyy-mm-dd", align=RIGHT)
            out_ = quarter_of(d) in left
            for j, key in enumerate(HOUSEHOLD_KEYS):
                v = cols.get(key, {}).get(d)
                if v is not None:
                    put(ws, rr, HH["types"] + j, v, "#,##0.000", align=RIGHT)
                    if not out_ and key != "household_total":
                        ws.cell(rr, HH["drawn"] + j, v)          # as drawn: left-out quarters stay empty
            if out_:
                put(ws, rr, HH["note"], "left out (%s)" % quarter_of(d), font=F_NOTE)
        for j, (_, column, _) in enumerate(HOUSEHOLD_DEBT[:-1]):
            ws.cell(top, HH["drawn"] + j, column)
        for col in range(HH["change"], HH["whatif"] + 2):
            ws.column_dimensions[L(col)].hidden = True
        span = zoom_rows(quarters, zoom)
        if span is None:
            put(ws, 20, 2, "No quarter falls in %s to %s, the quarters the charts are zoomed to." % tuple(zoom),
                font=F_NOTE)
            row = facts_rows(ws, section(ws, 29, "What it is", 13), facts)
            method_note(ws, row + 1, 25, entries)
            ws.print_area = "A1:Y%d" % row
            ws.freeze_panes = "A4"
            return ws
        a, b = first + span[0], first + span[1]
        # Bars side by side, one a quarter, as the NY Fed draws them. On a date axis a quarter's bar takes a
        # month's width and leaves two empty, so the axis is of labels: the year under each first quarter, every
        # two years, or five on a long zoom (LibreOffice prints every label of a text axis).
        years_ = max(1, int(quarters[span[1]][:4]) - int(quarters[span[0]][:4]))
        every_ = next(k for k in (1, 2, 5, 10) if years_ / k <= 12)
        ws.cell(top, HH["label"], "Label")
        for i in range(span[0], span[1] + 1):
            d = quarters[i]
            if d[5:7] == "01" and int(d[:4]) % every_ == 0:   # the other quarters' labels stay empty cells
                ws.cell(first + i, HH["label"], d[:4])
        stack = BarChart()
        stack.type, stack.grouping, stack.overlap, stack.gapWidth = "col", "stacked", 100, 50
        for j, (_, column, _) in enumerate(HOUSEHOLD_DEBT[:-1]):
            ser = Series(Reference(ws, min_col=HH["drawn"] + j, min_row=a, max_row=b), title=column)
            ser.graphicalProperties.solidFill = HOUSEHOLD_COLOURS[j]
            ser.graphicalProperties.line.noFill = True
            stack.series.append(ser)
        stack.set_categories(Reference(ws, min_col=HH["label"], min_row=a, max_row=b))
        x_axis = stack.x_axis
        x_axis.tickLblSkip, x_axis.tickMarkSkip = 1, 4
        x_axis.delete = False
        x_axis.majorGridlines = None
        x_axis.majorTickMark = "out"
        x_axis.spPr = GraphicalProperties(ln=ln(K.STONE, 0.75))
        x_axis.txPr = text()
        x_axis.tickLblPos = "low"
        stack.y_axis.crossAx = x_axis.axId
        # Sized from the quarters drawn: a quarter left out is not drawn, so it must not stretch the axis (Codex on
        # #471).
        totals = [cols.get("household_total", {}).get(quarters[i]) for i in range(span[0], span[1] + 1)
                  if quarter_of(quarters[i]) not in left]
        top_ = max([v for v in totals if v is not None] or [1.0])
        lo, hi, step = nice_axis(0, top_)
        finish(stack, "Total Debt Balance and Its Composition (the NY Fed's chart, as it reports it)",
               "trillions of dollars", (0, hi), step, x_axis, height=9.74)
        stack.legend = Legend()
        stack.legend.position = "t"
        stack.legend.txPr = text(9, K.INK_TEXT)
        place(ws, stack, 2, 9, 13, 26)
        merged(ws, 27, 2, 25, item.credit, font=F_NOTE, align=WRAP)
        ws.row_dimensions[27].height = 27
        # The total's change, drawn as every series' change is, from the table's own columns: the change is
        # written beside it in a column of its own.
        chg = dict(changes(kept(list(cols.get("household_total", {}).items()), s["left_out"]), months, "quarterly",
                           "percent"))
        ws.cell(top, HH["change"], "Total: change")
        for i, d in enumerate(quarters):
            if d in chg:
                put(ws, first + i, HH["change"], chg[d], "#,##0.0#")
        r = by_key.get("household_total", {}).get("change")
        w = (wrows.get("household_total", {}).get("change") or {}) if whatif else {}
        wb_ = w.get("b") if w.get("same_measure") else None
        said = ""
        ref = r or wb_                  # read under the what-if only, the chart still draws (Codex on #471)
        if ref:
            seen = [(quarters[i], chg[quarters[i]]) for i in range(span[0], span[1] + 1) if quarters[i] in chg]
            if seen:
                latest_row = first + quarters.index(ref["date"])
                # The what-if's latest may be a quarter this side left out, so this side's column has none.
                latest = chg.get(ref["date"]) if a <= latest_row <= b else None
                keep = ([latest] if latest is not None else []) + (
                    [r["normal_low"], r["normal_high"]] if r else []) + (
                    [wb_["normal_low"], wb_["normal_high"]] if wb_ else [])
                lo, hi, step, above, below = axis_view(seen, s["axis_cut"], keep)
                for col, words in ((HH["latest"], "Latest"), (HH["off"], "Off the axis")):
                    ws.cell(top, col, words)
                band_col = None
                if r:
                    band_col = HH["band"]
                    ws.cell(top, band_col, "Normal from")
                    ws.cell(top, band_col + 1, "Normal range")
                    for rr in range(a, b + 1):
                        ws.cell(rr, band_col, r["normal_low"])
                        ws.cell(rr, band_col + 1, r["normal_high"] - r["normal_low"])
                if latest is not None:
                    ws.cell(latest_row, HH["latest"], round(latest, 2))
                for d, v in above:
                    ws.cell(first + quarters.index(d), HH["off"], hi)
                for d, v in below:
                    ws.cell(first + quarters.index(d), HH["off"], lo)
                title = ("Total: change over %d months, its normal range shaded" % months if r else
                         "Total: change over %d months; not read under these settings" % months)
                dashed_col = None
                if wb_:
                    # The what-if's range, as on every series tab: two lines over the years its history covers
                    # (Codex on #471: this chart drew only the range as you have it).
                    dashed_col = HH["whatif"]
                    ws.cell(top, dashed_col, "What if: normal from")
                    ws.cell(top, dashed_col + 1, "What if: normal to")
                    start = _date(wb_["history_from"]).isoformat()
                    for i in range(span[0], span[1] + 1):
                        if quarters[i] >= start:
                            ws.cell(first + i, dashed_col, wb_["normal_low"])
                            ws.cell(first + i, dashed_col + 1, wb_["normal_high"])
                    title += " (dashed: the normal range under the what-if)"
                place(ws, history_chart(ws, title, "percent", HH["change"], a, b, HH["latest"], "quarterly",
                                        (lo, hi), step, band_col, dashed_col, head=top, off_col=HH["off"],
                                        height=4.23, signed_axis=True, label_fmt="+0.00;-0.00;0.00",
                                        date_col=HH["date"]), 14, 19, 25, 26)
                said = off_edge(above, below, "quarterly", lambda v: signed(item, v))
        if said:
            merged(ws, 28, 14, 25, said, font=F_NOTE, align=WRAP)
            ws.row_dimensions[28].height = 27
        row = facts_rows(ws, section(ws, 29, "What it is", 13), facts)
        ws.row_dimensions[row].height = 12
        end = method_note(ws, row + 1, 25, entries)
        ws.print_area = "A1:Y%d" % (end - 1)
        ws.freeze_panes = "A4"
        return ws

    # -- Usable with care ---------------------------------------------------
    ws = sheet(CARE_NAME)
    last = 14
    widths(ws, TABLE_WIDTHS)
    title_band(ws, CARE_NAME, "The research's \"usable with care\" group, read the same way as the rest.", last,
               tab=K.MIST)
    link(ws.cell(2, 2), "Overview", "Back to Overview", nav=True)
    tile(ws, 4, 2, 2, "Series read", len(CARE + CARE_DERIVED), "#,##0")
    tile(ws, 4, 3, 4, "In the group, not read", len(CARE_NOT_READ), "#,##0")
    care_changes = [r for r in result["readings"] if r["reading"] == "change" and r["care"]]
    for i, d in enumerate((INCREASING, STABLE, DECREASING)):
        tile(ws, 4, (5, 6, 8)[i], (5, 7, 9)[i], ARROW[d], sum(1 for r in care_changes if r["direction"] == d),
             "#,##0")
    ws.row_dimensions[6].height = 9
    header(ws, 7, TABLE, right=TABLE_RIGHT, centre=TABLE_CENTRE)
    row = 8
    for t, (topic, keys) in enumerate(CARE_TOPICS):
        if t:
            ws.row_dimensions[row].height = 6
            row += 1
        row = section(ws, row, topic, last)
        for key in keys:
            reading_row(ws, row, key)
            ws.row_dimensions[row].height = 15
            item = items[key]
            care = item.care[0].upper() + item.care[1:] + "."
            merged(ws, row + 1, 2, last, care, font=F_NOTE, align=Alignment(vertical="top", indent=1))
            ws.row_dimensions[row + 1].height = 13.5 * lines_of(ws, care, 2, last)
            rule(ws, row + 1, 2, last)
            row += 2
    not_read_care = [x for x in result["not_read"] if x["care"]]
    if not_read_care:
        ws.row_dimensions[row].height = 6
        row = section(ws, row + 1, "Nothing to show, and why", last)
        row = header(ws, row, ["Series", "Reading", "Why"], height=18)
        for x in not_read_care:
            put(ws, row, 2, items[x["key"]].title, align=WRAP)
            put(ws, row, 3, reading_name(x["reading"], months), align=WRAP)
            merged(ws, row, 4, last, x["why"], font=F_NOTE, align=WRAP)
            ws.row_dimensions[row].height = 15 * lines_of(ws, x["why"], 4, last) + 3
            rule(ws, row, 2, last)
            row += 1
    ws.row_dimensions[row].height = 6
    row = section(ws, row + 1, "In the group, not read, and why", last)
    header(ws, row, ["Series", "Why it is not read"], height=18)
    ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=last)
    row += 1
    for what, why in CARE_NOT_READ:
        put(ws, row, 2, what)
        words = why[0].upper() + why[1:] + "."
        merged(ws, row, 3, last, words, font=F_NOTE, align=WRAP)
        ws.row_dimensions[row].height = 15 * lines_of(ws, words, 3, last)
        rule(ws, row, 2, last)
        row += 1
    row = credits(ws, row, last, [k for _, keys in CARE_TOPICS for k in keys])
    ws.row_dimensions[row].height = 12
    method_note(ws, row + 1, last, [
        (CARE_NAME, "Series the research calls usable with care: short, broken or heavily revised. They are read "
                    "the same way as the series on the Overview, so they can be set beside them, with why each "
                    "needs care under its name."),
        ("Columns", "As on the Overview: where the level sits, the change against its normal range, and which way "
                    "it reads."),
    ] + ([("Quarters left out", left_words)] if left_words else []))
    ws.freeze_panes = "C8"

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
    # The tab bar follows the Overview's rows: its tabs coloured by topic, slate and stone in turn only to show
    # where one topic's tabs end; the usable-with-care tabs mist (Claude Design, round 1).
    for t, (_, keys) in enumerate(TOPICS):
        for key in keys:
            wb[TAB[key]].sheet_properties.tabColor = (K.SLATE, K.STONE)[t % 2]
    for _, keys in CARE_TOPICS:
        for key in keys:
            wb[CARE_TAB[key]].sheet_properties.tabColor = K.MIST

    # -- the record tabs: one template ----------------------------------------
    def record_rows(ws, row, rows_, cols, last):
        """A record tab's rows: Calibri 11, top-aligned, a thin rule under each, each row as tall as its longest
        cell."""
        for vals in rows_:
            tall_ = 1
            for j, v in zip(cols, vals):
                if isinstance(v, tuple):
                    v, font = v
                else:
                    font = None
                put(ws, row, j, v, font=font, align=WRAP)
                if isinstance(v, str):
                    tall_ = max(tall_, lines_of(ws, v, j, j))
            ws.row_dimensions[row].height = 15 * tall_ + 3
            rule(ws, row, cols[0], last)
            row += 1
        return row

    # -- State data ---------------------------------------------------------
    ws = sheet("State data")
    widths(ws, [11] + [7] * len(STATES))
    title_band(ws, "Unemployment rate by state, month by month",
               "Percent. An empty cell is a month with no value published (October 2025: the lapse in "
               "appropriations).", 1 + 1 + len(STATES), record=True)
    link(ws.cell(2, 2), "Overview", "Back to Overview", nav=True)
    head = 3
    row = header(ws, head, ["Date"] + list(STATES), right=tuple(range(0, len(STATES) + 1)), height=18)
    columns = {}
    for j, st in enumerate(STATES, 3):
        pts = pull.points(BY_KEY["unemployment_" + st.lower()])
        columns[j] = dict(pts) if not isinstance(pts, str) else {}
    for d in sorted({d for c in columns.values() for d in c}):
        put(ws, row, 2, _date(d), "yyyy-mm", align=RIGHT)
        for j, c in columns.items():
            if d in c and c[d] is not None:
                put(ws, row, j, c[d], "0.0", align=RIGHT)
        row += 1
    ws.freeze_panes = "B4"

    # -- Not read -----------------------------------------------------------
    if result["not_read"]:
        ws = sheet("Not read")
        widths(ws, [44, 24, 110])
        title_band(ws, "Not read", "Each reading the catalog holds that could not be read, and why.", 4,
                   record=True)
        link(ws.cell(2, 2), "Overview", "Back to Overview", nav=True)
        row = header(ws, 4, ["Series", "Reading", "Why"], height=18)
        record_rows(ws, row, [(items[x["key"]].title, reading_name(x["reading"], months), x["why"])
                              for x in result["not_read"]], (2, 3, 4), 4)
        ws.freeze_panes = "A5"

    # -- Glossary -----------------------------------------------------------
    ws = sheet("Glossary")
    widths(ws, [28, 110])
    title_band(ws, "Glossary", "Every term in this workbook, and how it is worked out.", 3, record=True)
    link(ws.cell(2, 2), "Overview", "Back to Overview", nav=True)
    row = header(ws, 4, ["Term", "What it means, and how it is worked out"], height=18)
    record_rows(ws, row, [((term, F_BOLD), meaning) for term, meaning in glossary(s, whatif, zoom)], (2, 3), 3)
    ws.freeze_panes = "A5"

    # -- Run ----------------------------------------------------------------
    ws = sheet("Run")
    widths(ws, [42, 40] + ([40] if whatif else []) + [110])
    last = 5 if whatif else 4
    title_band(ws, "Run", "What went into this workbook.", last, record=True)
    link(ws.cell(2, 2), "Overview", "Back to Overview", nav=True)
    row = 4
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
        put(ws, row, 2, k, font=F_BOLD)
        put(ws, row, 3, v, align=Alignment(horizontal="left", vertical="center"))
        rule(ws, row, 2, 3)
        ws.row_dimensions[row].height = 15
        row += 1
    row += 1
    row = header(ws, row, ["Setting", "The firm's answer"] + (["What if"] if whatif else []) + ["The question"],
                 height=18)
    asked = {q[0]: q[1] for q in QUESTIONS}
    if whatif:
        rows = [(x["setting"], x["a"], x["b"], asked[x["name"]]) for x in whatif["settings"]]
    else:
        rows = [(CALLED[n], plain(n, s), asked[n]) for n in CALLED]
    record_rows(ws, row, [tuple((v, F_BOLD) if whatif and j == 2 and vals[1] != vals[2] else v
                                for j, v in enumerate(vals)) for vals in rows], tuple(range(2, last + 1)), last)

    # -- Sources ------------------------------------------------------------
    ws = sheet("Sources")
    widths(ws, [44, 36, 30, 34, 13, 28, 26, 60, 66, 44])
    title_band(ws, "Sources", "Every file the pull fetched, and its fingerprint as the run read it.", 11,
               record=True)
    link(ws.cell(2, 2), "Overview", "Back to Overview", nav=True)
    row = header(ws, 4, ["Series", "Publisher", "Id at the source", "Licence", "First reading", "File", "Fetched",
                         "Address", "SHA-256 as read", "Since the pull"], height=18)
    for x in SERIES:
        name = file_name(x)
        f = files.get(name, {})
        for j, v in enumerate((x.title, x.publisher, x.source_id, x.licence, x.starts, name,
                               f.get("fetched_at", f.get("error", "not in this pull")), f.get("url", ""),
                               read_sha.get(name, "")), 2):
            put(ws, row, j, v)
        ws.row_dimensions[row].height = 15
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
    ws.freeze_panes = "C5"

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
    # Every month, whatever the zoom: the zoom only sets the quarters the Dashboard opens on, and the From and To
    # boxes can widen them.
    every = sorted({m for g in monthly.values() for part in g.values() for m in part})
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

    def year_of(m):
        """A month as a decimal year, 2019.0 for January 2019: a chart's time axis in years fits the months it is
        given. A date axis of day numbers does not: Excel starts one at zero, 1900, unless the dates are close
        together (the firm's Dashboard, 22 Oct 2026, ran from 1900 to 2036)."""
        return int(m[:4]) + (int(m[5:7]) - 1) / 12

    # The summary of each series, one row each, and the pick list: what the Dashboard's table shows, written as the
    # tables write it (a quarter as "2026 Q2", a change with its sign and its % or points), so one cell shows any
    # pick right; then the months it draws, the firm's 1% at each end of each chart, and its normal range.
    s0 = 2 + 4 * len(pickable) + 1
    stats = ["Series", "Unit", "Latest", "Value", "Level: at or above", "Change over %d months" % months,
             "Normal from", "Normal to", "Direction", "Typical moves", "Since", "History from",
             "First month drawn", "Last month drawn", "Moves: off below", "Moves: off above", "Level: off below",
             "Level: off above", "Change: off below", "Change: off above", "Normal from, as drawn",
             "Normal to, as drawn"]
    ST = {k: i for i, k in enumerate(["series", "unit", "latest", "value", "level", "change", "normal_low",
                                      "normal_high", "direction", "moves", "since", "history", "first", "last",
                                      "moves_lo", "moves_hi", "level_lo", "level_hi", "change_lo", "change_hi",
                                      "normal_low_n", "normal_high_n"])}
    for k, words in enumerate(stats):
        dd.cell(2, s0 + k, words)

    def shown(item, v):
        """A change as the tables show it, as text: +3.14% or -0.20."""
        return ("%+.2f%%" % v) if item.change_in == "percent" else ("%+.2f" % v)

    def value_text(v):
        """A value as the tables' #,##0.0# shows it: whole thousands with commas, else one or two decimals."""
        if abs(v) >= 1000:
            return "{:,.0f}".format(v)
        two = "%.2f" % v
        return two[:-1] if two.endswith("0") else two

    def when_text(d, frequency):
        if frequency == "quarterly":
            return _when(d, "quarterly")
        return d[:10] if frequency in ("daily", "weekly") else d[:7]

    def since_text(d, frequency):
        return _when(d, "quarterly") if frequency == "quarterly" else d[:7]

    def cut_of(values, keep):
        """The firm's cut at each end of a chart's values, widened to hold ``keep``: a reading past it runs off."""
        if not values:
            return None, None
        v = sorted(values)
        k = int(len(v) * s["axis_cut"] / 100)
        return min([v[k]] + keep), max([v[len(v) - 1 - k]] + keep)
    for j, key in enumerate(pickable):
        item, mine, rr = items[key], by_key.get(key, {}), first_row + j
        now = latest_of(item)
        lvl, chg = mine.get("position"), mine.get("change")
        got = monthly.get(key, {})
        vals = {"series": item.title, "unit": item.unit,
                "latest": when_text(now[0], item.frequency) if now else None,
                "value": value_text(now[1]) if now else None,
                "level": lvl["percentile"] / 100 if lvl else ("change only" if item.position else None),
                "direction": ARROW[chg["direction"]] if chg else "not read"}
        if chg:
            vals.update(change=shown(item, chg["value"]), normal_low=shown(item, chg["normal_low"]),
                        normal_high=shown(item, chg["normal_high"]), moves=chg["movement"],
                        since=since_text(chg["since"], item.frequency), normal_low_n=chg["normal_low"],
                        normal_high_n=chg["normal_high"])
        if lvl or chg:
            vals["history"] = since_text((lvl or chg)["history_from"], item.frequency)
        drawn_ = sorted(m for part in ("level", "change") for m in got.get(part, {}) if m in shown_months)
        if drawn_:
            vals.update(first=year_of(drawn_[0]), last=year_of(drawn_[-1]))
        latest_m = lambda part: [got.get(part, {})[max(got[part])]] if got.get(part) else []   # noqa: E731
        vals["moves_lo"], vals["moves_hi"] = cut_of(list(got.get("moves", {}).values()),
                                                    [s["normal_width"], -s["normal_width"]] + latest_m("moves"))
        vals["level_lo"], vals["level_hi"] = cut_of(list(got.get("level", {}).values()), latest_m("level"))
        vals["change_lo"], vals["change_hi"] = cut_of(
            list(got.get("change", {}).values()),
            ([chg["normal_low"], chg["normal_high"]] if chg else []) + latest_m("change"))
        for name_, v in vals.items():
            if v is not None:
                dd.cell(rr, s0 + ST[name_], v)
    # The quarters the Dashboard's From and To boxes offer, each with the years its months run from and to: one
    # after another from the first month drawn to the last, and out to a zoom's ends, so a quarter left out of
    # every series, or a zoom past the data, is still one the boxes can hold (Codex on #471).
    q0 = s0 + len(stats) + 1
    ends = [quarter_index(quarter_of(m + "-01")) for m in (every[:1] + every[-1:])]
    ends += [quarter_index(q) for q in (zoom or ())]
    quarters_ = [quarter_label(i).replace("Q", " Q") for i in range(min(ends), max(ends) + 1)] if ends else []
    for k, words in enumerate(("Quarter", "From", "To")):
        dd.cell(2, q0 + k, words)
    for n, label in enumerate(quarters_):
        start = int(label[:4]) + (int(label[-1]) - 1) / 4
        dd.cell(first_row + n, q0, label)
        dd.cell(first_row + n, q0 + 1, start)
        dd.cell(first_row + n, q0 + 2, start + 0.2)    # its third month is start + 2/12
    data_end = L(s0 - 1)

    # The Dashboard: one screen, the four boxes in row 5, both readings in the Overview's columns, the two charts
    # that set the picks together side by side, and each pick's level and change under its own name (Claude Design,
    # round 1). The tab-chart grid: B to Y, 24 columns of 72 px.
    ws = dash
    widths(ws, [9.57] * 24 + [2.71])
    title_band(ws, DASHBOARD, "Pick any two series and the quarters to draw: both together on scales they "
                              "share, then each on its own.", 26, tab=K.INK)
    link(ws.cell(2, 2), "Overview", "Back to Overview", nav=True)
    BOX = {"first": (2, 7), "second": (8, 13), "from": (14, 16), "to": (17, 19)}
    CELL = {k: "$%s$5" % L(a) for k, (a, _) in BOX.items()}
    picks = [("First series", "Unemployment rate"), ("Second series", "Initial jobless claims")]
    window = zoom or ([quarters_[0].replace(" ", ""), quarters_[-1].replace(" ", "")] if quarters_ else None)
    values_ = {"first": picks[0][1] if picks[0][1] in names else names[0],
               "second": picks[1][1] if picks[1][1] in names else names[1],
               "from": window[0].replace("Q", " Q") if window else None,
               "to": window[1].replace("Q", " Q") if window else None}
    for i, (name_, words) in enumerate((("first", "First series"), ("second", "Second series"), ("from", "From"),
                                        ("to", "To"))):
        a, b = BOX[name_]
        put(ws, 4, a, words, font=F_FIELD, align=Alignment(vertical="bottom"))
        edge = side("thin", K.INPUT_EDGE)
        for col in range(a, b + 1):
            ws.cell(5, col).fill = K.solid(K.INPUT)
            ws.cell(5, col).border = Border(top=edge, left=edge if col == a else None, right=edge if col == b else None,
                                            bottom=side("medium", PICK_COLOURS[i]) if i < 2 else edge)
        merged(ws, 5, a, b, values_[name_], font=F_BOLD, align=MIDDLE)
    ws.row_dimensions[4].height = 13.5
    ws.row_dimensions[5].height = 21
    ws.row_dimensions[6].height = 6
    pick_list = "'%s'!$%s$%d:$%s$%d" % (DASH_DATA, L(s0), first_row, L(s0), first_row + len(names) - 1)
    dv = DataValidation(type="list", formula1=pick_list, allow_blank=False, showErrorMessage=True,
                        errorTitle="Not a series in this workbook", error="Pick a series from the list.")
    ws.add_data_validation(dv)
    dv.add("B5")
    dv.add("H5")
    q_list = "'%s'!$%s$%d:$%s$%d" % (DASH_DATA, L(q0), first_row, L(q0), first_row + max(len(quarters_), 1) - 1)
    dq = DataValidation(type="list", formula1=q_list, allow_blank=False, showErrorMessage=True,
                        errorTitle="Not a quarter in this workbook", error="Pick a quarter from the list.")
    ws.add_data_validation(dq)
    dq.add("N5")
    dq.add("Q5")
    # Hidden helpers, AN onwards: where each pick's columns start on the data tab and its row in the summary; the
    # years the From and To quarters run from and to; each pick's cut at each end of each chart.
    HELP = 40
    rows_of = "'%s'!$%s$%d:$%s$%d"
    for i, cell in enumerate((CELL["first"], CELL["second"])):
        rr = 4 + i
        formula(ws, rr, HELP, "=MATCH(%s,'%s'!$1:$1,0)" % (cell, DASH_DATA))
        formula(ws, rr, HELP + 1, "=MATCH(%s,%s,0)" % (cell, rows_of % (DASH_DATA, L(s0), first_row, L(s0),
                                                                         first_row + len(names) - 1)))
    q_rows = (first_row, first_row + max(len(quarters_), 1) - 1)
    for i, (col, cell) in enumerate(((q0 + 1, CELL["from"]), (q0 + 2, CELL["to"]))):
        formula(ws, 6 + i, HELP, "=INDEX(%s,MATCH(%s,%s,0))" % (
            rows_of % (DASH_DATA, L(col), q_rows[0], L(col), q_rows[1]), cell,
            rows_of % (DASH_DATA, L(q0), q_rows[0], L(q0), q_rows[1])))
    T0, T1 = "$%s$6" % L(HELP), "$%s$7" % L(HELP)
    merged(ws, 5, 20, 25, None)
    formula(ws, 5, 20, '=IF(%s>%s,"From is after To, so nothing is drawn.","")' % (T0, T1),
            font=Font(name="Calibri", size=10, bold=True, color=K.CRIMSON))

    def stat(i, k):
        """The summary's column ``k`` for pick ``i``, as a formula."""
        col = L(s0 + (ST[k] if isinstance(k, str) else k))
        return "INDEX(%s,$%s$%d)" % (rows_of % (DASH_DATA, col, first_row, col, first_row + len(names) - 1),
                                     L(HELP + 1), 4 + i)
    CUT = {}                                  # (pick, part, end) -> the hidden cell holding that cut
    for i in range(2):
        for n, part in enumerate(("moves", "level", "change")):
            for e, end in enumerate(("lo", "hi")):
                rr = 8 + 2 * n + e
                formula(ws, rr, HELP + i, "=IFERROR(%s+0,NA())" % stat(i, "%s_%s" % (part, end)))
                CUT[(i, part, end)] = "$%s$%d" % (L(HELP + i), rr)
    # The table of both picks, in the Overview's columns.
    heads = [(2, 5, "Series"), (6, 6, "Latest"), (7, 7, "Value"), (8, 9, "Unit"), (10, 10, "Level: at or above"),
             (11, 11, "Change over %d months" % months), (12, 12, "Normal from"), (13, 13, "Normal to"),
             (14, 15, "Direction"), (16, 16, "Typical moves"), (17, 17, "Since"), (18, 18, "History from")]
    shows = {6: "latest", 7: "value", 8: "unit", 10: "level", 11: "change", 12: "normal_low", 13: "normal_high",
             14: "direction", 16: "moves", 17: "since", 18: "history"}
    for a, b, words in heads:
        header(ws, 7, [words] + [None] * (b - a), first=a, right=() if a in (2, 8) else (0,),
               centre=(0,) if a == 14 else (), height=33)
        if b > a:
            ws.merge_cells(start_row=7, start_column=a, end_row=7, end_column=b)
    for i in range(2):
        rr = 8 + i
        ws.merge_cells(start_row=rr, start_column=2, end_row=rr, end_column=5)
        c = formula(ws, rr, 2, "=%s" % (CELL["first"], CELL["second"])[i], font=F_DATA)
        c.border = Border(left=side("thick", PICK_COLOURS[i]))
        for a, b, _ in heads[1:]:
            k = shows[a]
            if b > a:
                ws.merge_cells(start_row=rr, start_column=a, end_row=rr, end_column=b)
            formula(ws, rr, a, '=IF(%s="","",%s)' % (stat(i, k), stat(i, k)),
                    "0.0%" if k == "level" else "+0.0;-0.0;0.0" if k == "moves" else None,
                    font=F_NOTE if k == "unit" else None,
                    align=CENTER if k == "direction" else INDENT if k == "unit" else RIGHT)
        ws.row_dimensions[rr].height = 15
        rule(ws, rr, 2, 18)
    from openpyxl.formatting.rule import FormulaRule
    from openpyxl.styles import PatternFill
    # A moving direction bold on mist, as every table shows it; Stable plain. The same fill both ways.
    ws.conditional_formatting.add("N8:O9", FormulaRule(formula=['AND(N8<>"Stable",N8<>"",N8<>"not read")'],
                                                       fill=PatternFill("solid", fgColor=K.MIST),
                                                       font=Font(name="Calibri", size=11, bold=True, color=K.INK)))
    ws.row_dimensions[10].height = 6
    # The drawn columns: the month in years, then for each pick, twelve: the year again where the pick has a
    # reading in the quarters chosen (so every axis fits the picks and the quarters); its level, change, typical
    # moves and place in its history as written; the first three again with a reading past the firm's cut left
    # off (#N/A, which a chart skips), so the axes fit the rest; a marker at the cut for each reading left off;
    # and the typical moves of the readings left off, for the note under the chart.
    put(ws, 2, HELP + 2, "Year", font=F_NOTE)

    def col_of(i, k):
        """Pick i's drawn column k: 0 years; 1 level, 2 change, 3 typical moves, 4 at or above, as written; 5 level,
        6 change, 7 typical moves, inside the cut; 8, 9, 10 their markers; 11 typical moves left off."""
        return HELP + 3 + 12 * i + k
    names_ = ("Years", "Level", "Change", "Typical moves", "At or above", "Level, drawn", "Change, drawn",
              "Typical moves, drawn", "Level off the axis", "Change off the axis", "Typical moves off the axis",
              "Typical moves left off")
    for i in range(2):
        for k, words in enumerate(names_):
            put(ws, 2, col_of(i, k), "%s: %s" % (picks[i][0], words), font=F_NOTE)
    for n, m in enumerate(every):
        rr = first_row + n
        ws.cell(rr, HELP + 2, year_of(m))
        for i in range(2):
            for k in range(4):
                where = "INDEX('%s'!$A$%d:$%s$%d,ROW()-%d,$%s$%d+%d)" % (
                    DASH_DATA, first_row, data_end, last_row, first_row - 1, L(HELP), 4 + i, k)
                formula(ws, rr, col_of(i, k + 1), '=IF(%s="",NA(),%s)' % (where, where))
            yr = "$%s%d" % (L(HELP + 2), rr)
            x = "%s%d" % (L(col_of(i, 0)), rr)
            formula(ws, rr, col_of(i, 0), "=IF(AND(OR(ISNUMBER(%s%d),ISNUMBER(%s%d)),%s>=%s,%s<=%s),%s,NA())" % (
                L(col_of(i, 1)), rr, L(col_of(i, 2)), rr, yr, T0, yr, T1, yr))
            for k, part in ((1, "level"), (2, "change"), (3, "moves")):
                v = "%s%d" % (L(col_of(i, k)), rr)
                lo, hi = CUT[(i, part, "lo")], CUT[(i, part, "hi")]
                formula(ws, rr, col_of(i, k + 4), "=IF(ISNUMBER(%s),IF(OR(%s>%s,%s<%s),NA(),%s),NA())" % (
                    v, v, hi, v, lo, v))
                formula(ws, rr, col_of(i, k + 7), "=IF(ISNUMBER(%s),IF(ISNUMBER(%s),IF(%s>%s,%s,IF(%s<%s,%s,NA())),"
                                                  "NA()),NA())" % (x, v, v, hi, hi, v, lo, lo))
            mk = "%s%d" % (L(col_of(i, 10)), rr)
            formula(ws, rr, col_of(i, 11), '=IF(ISNUMBER(%s),%s%d,"")' % (mk, L(col_of(i, 3)), rr))
    # The dashed lines: two points each, across the quarters chosen where the picks have readings, looked up as
    # values (a newer spreadsheet function such as AGGREGATE reads #NAME? unless the file marks it).
    LINES_AT = HELP + 3 + 24
    if every:
        def span_of(i, n):
            return stat(i, "first" if n == 0 else "last")
        for n in range(2):
            rr = first_row + n
            inner, outer = ("MIN", "MAX") if n == 0 else ("MAX", "MIN")
            one, two = span_of(0, n), span_of(1, n)
            bound = T0 if n == 0 else T1
            formula(ws, rr, LINES_AT, "=%s(%s,%s(IFERROR(%s,%s),IFERROR(%s,%s)))" % (outer, bound, inner, one, two,
                                                                                    two, one))
            ws.cell(rr, LINES_AT + 1, s["normal_width"])
            ws.cell(rr, LINES_AT + 2, -s["normal_width"])
            for i in range(2):
                formula(ws, rr, LINES_AT + 3 + 3 * i, "=IFERROR(%s(%s,%s+0),NA())" % (outer, bound, span_of(i, n)))
                for k, part in enumerate(("normal_low_n", "normal_high_n")):   # each pick's normal range
                    formula(ws, rr, LINES_AT + 4 + 3 * i + k, "=IFERROR(%s+0,NA())" % stat(i, part))
    # The note under the two charts set together: for each pick, how many readings run off the movement chart at
    # each end and the furthest of them, as each series' tab says it; and each pick's name for the levels chart's
    # legend, with ": change only" when it has no level to draw.
    rows_all = (first_row, last_row)
    for i in range(2):
        mk = "$%s$%d:$%s$%d" % (L(col_of(i, 10)), rows_all[0], L(col_of(i, 10)), rows_all[1])
        off = "$%s$%d:$%s$%d" % (L(col_of(i, 11)), rows_all[0], L(col_of(i, 11)), rows_all[1])
        months_ = "'%s'!$A$%d:$A$%d" % (DASH_DATA, rows_all[0], rows_all[1])
        name_ = (CELL["first"], CELL["second"])[i]
        up, down = "COUNTIF(%s,%s)" % (mk, CUT[(i, "moves", "hi")]), "COUNTIF(%s,%s)" % (mk, CUT[(i, "moves", "lo")])
        far = "IF(ABS(MAX(%s))>=ABS(MIN(%s)),MAX(%s),MIN(%s))" % (off, off, off, off)
        formula(ws, 14 + i, HELP, (
            '=IFERROR(IF(%(up)s+%(down)s=0,"","Off the chart, "&%(name)s&": "&IF(%(up)s>0,%(up)s&IF(%(up)s=1,'
            '" reading runs"," readings run")&" off the top","")&IF(AND(%(up)s>0,%(down)s>0),", ","")&IF(%(down)s>0,'
            '%(down)s&IF(%(up)s>0," off the bottom",IF(%(down)s=1," reading runs"," readings run")&" off the '
            'bottom"),"")&"; the furthest "&TEXT(%(far)s,"+0.0;-0.0")&" typical moves in "&TEXT(INDEX(%(months)s,'
            'MATCH(%(far)s,%(off)s,0)),"mmm yyyy")&"."),"")') % {"up": up, "down": down, "name": name_, "far": far,
                                                                 "months": months_, "off": off})
        formula(ws, 14 + i, HELP + 1, '=IF(%s="change only",%s&": change only",%s)' % (stat(i, "level"), name_,
                                                                                        name_))
    for col in range(HELP, LINES_AT + 10):
        ws.column_dimensions[L(col)].hidden = True

    def scatter(title, unit, ys, lines_=(), bounds=None, fmt="General", legend=True, width=HALF, height=7.41,
                major=5, markers=()):
        """A chart of months, in years: each of ``ys`` a (column, its years' column, colour, the cell naming
        it); ``lines_`` dashed two-point lines (column, its years' column, colour, words); ``markers`` the
        readings off the axis (column, its years' column), a triangle at the cut. ``bounds`` fixes the value axis;
        without it, every axis fits the picks, the quarters chosen and the firm's cut."""
        from openpyxl.chart.axis import NumericAxis
        ch = ScatterChart()
        ch.scatterStyle = "line"
        # One colour a line, stated: left unstated, Excel colours every point of a one-line chart apart and gives
        # each its own legend entry, which drew rows of unnamed dashes under the firm's charts (22 Oct 2026).
        ch.varyColors = False
        for col, xcol, colour, name in ys:
            xs = Reference(ws, min_col=xcol, min_row=first_row, max_row=last_row)
            ser = Series(Reference(ws, min_col=col, min_row=first_row, max_row=last_row), xs)
            ser.tx = SeriesLabel(strRef=StrRef(f="'%s'!%s" % (DASHBOARD, name)))
            ser.graphicalProperties.line = ln(colour, 1.75 if legend else 1.5)
            ser.marker.symbol = "none"
            ser.smooth = False
            ch.series.append(ser)
        for col, xcol, colour, words in lines_:
            ser = Series(Reference(ws, min_col=col, min_row=first_row, max_row=first_row + 1),
                         Reference(ws, min_col=xcol, min_row=first_row, max_row=first_row + 1), title=words)
            ser.graphicalProperties.line = ln(colour, 1.25, "sysDash")
            ser.marker.symbol = "none"
            ser.smooth = False
            ch.series.append(ser)
        for col, xcol in markers:
            ser = Series(Reference(ws, min_col=col, min_row=first_row, max_row=last_row),
                         Reference(ws, min_col=xcol, min_row=first_row, max_row=last_row), title="Off the axis")
            ser.graphicalProperties.line.noFill = True
            ser.marker.symbol = "triangle"
            ser.marker.size = 6
            ser.marker.graphicalProperties = GraphicalProperties(solidFill=K.STONE, ln=ln(K.SLATE, 0.75))
            ser.smooth = False
            ch.series.append(ser)
        x = NumericAxis(axId=500, crossAx=100)
        x.axPos = "b"
        x.number_format = "0"                     # years: 2019, 2020 ...
        x.majorUnit = major
        x.delete = False
        x.majorGridlines = None
        x.majorTickMark = "out"
        x.spPr = GraphicalProperties(ln=ln(K.STONE, 0.75))
        x.txPr = text(9, K.SLATE)
        x.tickLblPos = "low"                      # at the foot of the chart, wherever zero falls
        ch.x_axis = x
        y = ch.y_axis
        y.axId, y.crossAx = 100, 500
        y.axPos = "l"
        y.delete = False
        y.majorGridlines = gridlines()
        y.spPr = GraphicalProperties(ln=ln(K.STONE, 0.75))
        y.txPr = text(9, K.SLATE)
        y.number_format = fmt
        y.tickLblPos = "low"
        axis_title(y, unit)
        if bounds:
            y.scaling.min, y.scaling.max = bounds[0], bounds[1]
            y.majorUnit = bounds[2]
        chart_title(ch, title)
        if legend:                                # above the chart, clear of the years along its foot
            ch.legend = Legend()
            ch.legend.position = "t"
            ch.legend.txPr = text(9, K.INK_TEXT)
            named = set()                         # two dashed lines of one name: the name once in the legend
            for idx, (*_, words) in enumerate(lines_, start=len(ys)):
                if words in named:
                    ch.legend.legendEntry.append(LegendEntry(idx=idx, delete=True))
                named.add(words)
            for idx in range(len(ys) + len(lines_), len(ys) + len(lines_) + len(markers)):
                ch.legend.legendEntry.append(LegendEntry(idx=idx, delete=True))
        else:
            ch.legend = None
        # Joined across a month with no reading: a quarterly series has one a quarter on this tab's monthly grid,
        # and Excel joins across #N/A anyway. Each series' own tab shows a real gap as one.
        ch.display_blanks = "span"
        ch.visible_cells_only = False       # the drawn columns are hidden helpers
        ch.height, ch.width = height, width
        ch.roundedCorners = False
        ch.graphical_properties = GraphicalProperties(ln=LineProperties(noFill=True))
        return ch

    if every:
        moves_title = "Both changes over %d months, in typical moves from each one's median" % months
        place(ws, scatter(moves_title, "typical moves",
                             [(col_of(0, 7), col_of(0, 0), PICK_COLOURS[0], CELL["first"]),
                              (col_of(1, 7), col_of(1, 0), PICK_COLOURS[1], CELL["second"])],
                             [(LINES_AT + 1, LINES_AT, K.STONE, "Normal movement"),
                              (LINES_AT + 2, LINES_AT, K.STONE, "Normal movement")], fmt="+0;-0;0",
                             markers=[(col_of(0, 10), col_of(0, 0)), (col_of(1, 10), col_of(1, 0))]),
              2, 11, 13, 24)
        place(ws, scatter("Both levels: where each sits in its own history", "at or above, of its history",
                          [(col_of(0, 4), col_of(0, 0), PICK_COLOURS[0], "$%s$14" % L(HELP + 1)),
                           (col_of(1, 4), col_of(1, 0), PICK_COLOURS[1], "$%s$15" % L(HELP + 1))],
                          bounds=(0, 1, 0.25), fmt="0%"), 14, 11, 25, 24)
        merged(ws, 25, 2, 25, None)
        formula(ws, 25, 2, '=%s&IF(AND(%s<>"",%s<>"")," ","")&%s' % (
            "$%s$14" % L(HELP), "$%s$14" % L(HELP), "$%s$15" % L(HELP), "$%s$15" % L(HELP)), font=F_NOTE,
            align=Alignment(vertical="top", wrap_text=True))
        for i, (a, b) in enumerate(((2, 13), (14, 25))):
            for col in range(a, b + 1):
                ws.cell(26, col).border = Border(bottom=side("medium", PICK_COLOURS[i]))
            merged(ws, 26, a, b, None)
            formula(ws, 26, a, "=%s" % (CELL["first"], CELL["second"])[i],
                    font=Font(name="Arial", bold=True, size=10, color=K.INK), align=Alignment(vertical="bottom"))
            name_ = (CELL["first"], CELL["second"])[i]
            place(ws, scatter("Level", "its own units", [(col_of(i, 5), col_of(i, 0), PICK_COLOURS[i], name_)],
                              fmt="#,##0.##", legend=False, width=11.32, height=6.24, major=10,
                              markers=[(col_of(i, 8), col_of(i, 0))]), a, 27, a + 5, 38)
            place(ws, scatter("Change over %d months, its normal range dashed" % months, "points or percent",
                              [(col_of(i, 6), col_of(i, 0), PICK_COLOURS[i], name_)],
                              [(LINES_AT + 4 + 3 * i, LINES_AT + 3 + 3 * i, K.STONE, "Normal from"),
                               (LINES_AT + 5 + 3 * i, LINES_AT + 3 + 3 * i, K.STONE, "Normal to")],
                              fmt="+#,##0.##;-#,##0.##;0", legend=False, width=11.32, height=6.24, major=10,
                              markers=[(col_of(i, 9), col_of(i, 0))]), a + 6, 27, a + 11, 38)
        ws.row_dimensions[25].height = 15
        ws.row_dimensions[26].height = 18
        row = 40
    else:
        put(ws, 11, 2, "No months to draw%s." % (" in %s to %s" % tuple(zoom) if zoom else ""), font=F_NOTE)
        row = 13
    row = credits(ws, row, 25, pickable, label_last=5)    # any series can be picked: every credit they could need
    ws.row_dimensions[row].height = 12
    end = method_note(ws, row + 1, 25, [
        ("Pick", "Choose a series in each of the first two boxes, and the first and last quarter to draw in the "
                 "other two. Every chart below follows the four boxes; nothing else in the workbook changes."),
        ("Together, moving", "Each series' change over %d months, measured in its own typical moves from its own "
                             "median change, so two series of different units share one scale. Between the dashed "
                             "lines at %s and %s is normal movement; past them the change reads Increasing or "
                             "Decreasing." % (months, "%+g" % s["normal_width"], "%+g" % -s["normal_width"])),
        ("Together, levels", "Where each level sits in its own history, from 0% (its lowest) to 100% (its "
                             "highest). A series read on its change only has no line here, and its name in the "
                             "legend says so."),
        ("Each on its own", "Each series' level, and its change with its normal range dashed, in its own units."),
        ("Axes", "Every axis fits what is picked and the quarters chosen. To look past a spike, such as 2020, "
                 "pick quarters after it."),
    ] + ([("Off the chart", "Up to %g%% of each series' readings, at each end of its whole history, are left off "
                            "the charts, so a spike does not flatten the rest; a triangle marks each one at the "
                            "edge, and the line under the charts set together names the furthest. The latest "
                            "reading and the normal range always stay on. No reading changes." % s["axis_cut"])]
         if s["axis_cut"] else []) + [
        ("Months", "Every chart here is drawn month by month: a daily or weekly series at each month's last "
                   "reading, a quarterly one at the first month of each quarter. A line runs across a month with "
                   "no reading; each series' own tab shows such a gap as a gap."),
        ("Formulas", "This tab is the one place with formulas. They only look up values written on a hidden tab, "
                     "%s, so no reading moves." % DASH_DATA),
    ] + ([("Quarters left out", left_words)] if left_words else []))
    for rr in range(11, 25):
        ws.row_dimensions[rr].height = 15
    for rr in range(27, 39):
        ws.row_dimensions[rr].height = 15
    ws.freeze_panes = "A6"                  # the four boxes stay in view
    ws.print_area = "A1:Y%d" % (end - 1)
    wb.calculation.fullCalcOnLoad = True            # Excel works out the lookups when the file opens

    # The tab bar follows the Overview: the front tabs, every core series in its rows' order, States, the
    # usable-with-care group, then the record (Claude Design, round 1).
    order = (["Overview", DASHBOARD] + (["What if"] if whatif else [])
             + list(dict.fromkeys(TAB[k] for _, keys in TOPICS for k in keys)) + ["States", CARE_NAME]
             + [CARE_TAB[k] for _, keys in CARE_TOPICS for k in keys]
             + ["State data", "Glossary"] + (["Not read"] if result["not_read"] else []) + ["Run", "Sources", DASH_DATA])
    assert sorted(order) == sorted(wb.sheetnames), (set(order) ^ set(wb.sheetnames))
    wb._sheets.sort(key=lambda ws_: order.index(ws_.title))
    wb.active = 0

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
