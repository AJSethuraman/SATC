"""Read a paystub by reading its COLUMN HEADINGS, not by counting numbers.

THE FIRM SET THE PROBLEM, 31 August 2026:

    "it's hard to say on this, i imagine it needs to read all pages available
     and would need to use key words and phrases to identify the right numbers"

    "Another piece to the ocr is the fallback to ollama for judgmental
     processing. I really want it deterministic first though"

WHAT THE READER BESIDE THIS ONE DOES, AND WHY IT IS NOT ENOUGH.
:mod:`satc.ingest.readers.paystub` finds a label on a line of extracted text and
then takes the first dollar amount after it as the current period and the second
as the year-to-date. That is a POSITIONAL rule, and a paystub is not a positional
document. ADP's published earnings table has four columns -- ``rate``, ``hours``,
``this period``, ``year to date`` -- so on the line

    Regular    31.25    40.00    1,250.00    26,250.00

the positional rule reports an hourly rate of $31.25 as this period's gross pay
and 40 hours as the year-to-date, at HIGH confidence, with nothing anywhere
saying it is unsure. That number then becomes a projection, and the projection
becomes a W-4. **A confident wrong number is the worst output available** (S5).

THE ANSWER TO "HOW DOES IT TELL A YEAR-TO-DATE COLUMN FROM A CURRENT ONE", and
it is not "guess": the stub says so, in a heading, in words, above the number.
So this reader works on WORD BOXES rather than on a line of text. It finds the
row that names the columns, records where on the page each named column sits,
and then takes a number only when that number sits under a column the stub
itself has named. A number under ``rate`` is a rate. A number under nothing is
nothing. **A stub that does not name its columns is not read at all** -- see
:data:`REASONS` -- because the alternative is the positional guess above.

That is prevention rather than detection (S30): the wrong column is not
something this reader does and then notices, it is something it cannot reach.

WHICH PAGES IT READS. All of them, per the firm. :mod:`satc.ingest.pages` is NOT
reused here and the reason is worth writing down rather than rediscovering: that
module answers "is this page the IRS explaining the form", and its whole
vocabulary -- "Instructions for Recipient", "Employers, Please Note" -- is IRS
guidance-page vocabulary. A paystub has no such page. Applying it would drop
nothing and prove nothing. The multi-page question a stub actually poses is a
different one: the totals may be on the last page, the same face may be printed
twice, and two pages may disagree. So each page is read on its own, and the
answers are then compared -- agreement is taken, DISAGREEMENT IS REFUSED and
names both pages. Picking one silently and reading correctly look identical in a
filled-in box.

WHAT IT REPORTS. Its denominator (S2), always, including on a clean read:
pages examined, tables found, rows examined, money figures seen, fields asked
for, fields answered, fields refused. A read that answered nothing says how much
it looked at before answering nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from satc.ingest.paystub_layout import (
    PaystubError,
    Word,
    _merge_number_fragments,
    parse_currency,
    parse_date,
)
from satc.ingest.readers.base import ReadResult
from satc.ingest.readers.paystub import (
    LABEL_EMPLOYER,
    LABEL_FED_WH_CURRENT,
    LABEL_FED_WH_YTD,
    LABEL_GROSS_CURRENT,
    LABEL_GROSS_YTD,
    LABEL_PAY_FREQUENCY,
    LABEL_RETIREMENT_CURRENT,
    _employer,
)

# The one label `readers.paystub` never emitted. It is printed on the stub, in
# the year-to-date column of the retirement row, and it was thrown away -- so
# `withholding.intake` reconstructed it by MULTIPLYING this period's deferral by
# the number of periods it guessed had elapsed. A person who changed their
# deferral rate in March, or maxed out, or had one deducted from a bonus, gets a
# taxable-wage figure that was never on any document.
LABEL_RETIREMENT_YTD = "Paystub — Pre-tax retirement 401(k)/403(b) (YTD)"


# --------------------------------------------------------------------------
# What a column heading may say
# --------------------------------------------------------------------------
# Extend these lists rather than loosening a match. Every phrase here was either
# seen in a payroll provider's own documentation or is an abbreviation of one;
# a phrase nobody has seen printed does not belong here, because each addition
# is a new way for a number to be taken.

CURRENT_HEADINGS: tuple[str, ...] = (
    "this period", "current period", "this pay period", "current amount",
    "period amount", "this check", "current", "amount",
)
YTD_HEADINGS: tuple[str, ...] = (
    "year to date", "year-to-date", "yeartodate", "ytd amount",
    "year to date amount", "ytd", "y-t-d", "yr to date",
)
# Named columns that are NOT money we want. They earn their place by keeping
# their own numbers out: `rate` and `hours` are why the positional reader reads
# an hourly rate as a paycheck. `prior ytd` is here so it can never be mistaken
# for `ytd` -- it is the year to date BEFORE this cheque, a different number.
OTHER_HEADINGS: tuple[str, ...] = (
    "prior ytd", "prior year to date", "rate", "hours", "hrs", "units",
    "qty", "quantity", "balance", "accrued", "used", "taken", "earned",
    "employer", "employer amount", "employer ytd", "goal", "remaining",
)

# How a schedule is SAID, as against how it is stored. "biweekly" is a value
# this software passes around; "every two weeks" is what a person says. A
# refusal that uses the first is talking about itself.
IN_WORDS: dict[str, str] = {
    "weekly": "every week",
    "biweekly": "every two weeks",
    "semimonthly": "twice a month",
    "monthly": "once a month",
}


def in_money(value: str) -> str:
    """A figure the way it is printed on the stub, not the way it is stored."""
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):          # pragma: no cover
        return str(value)


CURRENT = "current"
YTD = "ytd"
OTHER = "other"

_HEADINGS: dict[str, str] = {}
for _p in CURRENT_HEADINGS:
    _HEADINGS[_p] = CURRENT
for _p in YTD_HEADINGS:
    _HEADINGS[_p] = YTD
for _p in OTHER_HEADINGS:
    _HEADINGS[_p] = OTHER
_MAX_HEADING_WORDS = max(len(p.split()) for p in _HEADINGS)


# --------------------------------------------------------------------------
# Which row is which figure
# --------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class _Row:
    """A field this reader can look for, and the row labels that carry it."""

    key: str
    plain: str                 # how the refusal text names it to a preparer
    current_label: str
    ytd_label: str
    anchors: tuple[str, ...]


ROWS: tuple[_Row, ...] = (
    _Row("gross", "gross pay", LABEL_GROSS_CURRENT, LABEL_GROSS_YTD,
         ("gross pay", "gross earnings", "gross wages", "total gross",
          "total gross pay", "gross", "total earnings")),
    _Row("federal", "federal income tax withheld", LABEL_FED_WH_CURRENT, LABEL_FED_WH_YTD,
         ("federal income tax", "federal income tax withheld", "fed income tax",
          "federal withholding", "fed withholding", "federal tax withheld",
          "fed w/h", "federal w/h", "fed tax", "federal tax", "fit")),
    _Row("retirement", "pre-tax retirement", LABEL_RETIREMENT_CURRENT, LABEL_RETIREMENT_YTD,
         ("401(k)", "401k", "403(b)", "403b", "pre-tax 401(k)", "pretax 401(k)",
          "retirement plan", "pretax retirement", "pre-tax retirement",
          "457(b)", "457b")),
)


# --------------------------------------------------------------------------
# What a refusal says, in words a preparer already has
# --------------------------------------------------------------------------
# `client-documents/plainspoken.py` is the rule these follow: a screen may not
# name a file, a code identifier or a piece of our own vocabulary. "Column",
# "year-to-date" and "pay period" are printed on the document in the preparer's
# hand. "Anchor", "heading row" and "token" are ours, and are not here.

REASONS: dict[str, str] = {
    "no_columns":
        "This stub never says which column is this pay period and which is the "
        "year-to-date total, so nothing was filled in. Type {what} in from the stub.",
    "one_column_only":
        "This stub shows one column of figures, headed “{named}”, and no "
        "year-to-date column beside it. Type {what} in from the stub.",
    "not_found":
        "Nothing on this stub is labelled {what}. Type it in if it is there under "
        "another name.",
    "rows_disagree":
        "This stub shows {what} more than once, as {values}. Type in the right one.",
    "pages_disagree":
        "Page {a} says {what} is {va} and page {b} says {vb}. Type in the right one.",
    "ytd_below_period":
        "The year-to-date {what} ({ytd}) is smaller than this pay period's ({period}), "
        "which cannot both be true, so neither was filled in.",
    "column_unclear":
        "A figure on the {what} row does not sit under either column, so it was left alone.",
    "frequency_unknown":
        "This stub does not say how often this person is paid, and its dates do not "
        "say either. Choose the pay schedule before running an estimate.",
    "frequency_conflict":
        "This stub says the person is paid {said}, but the pay period on it covers "
        "{days} days, which is {implied}. Choose which is right.",
}


# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------

@dataclass(slots=True)
class Figure:
    """One figure, or one refusal. Never both, and never neither."""

    label: str
    plain: str
    value: str | None = None
    page: int | None = None
    column_said: str = ""        # the heading, as PRINTED, that placed this number
    reason_code: str = ""
    problem: str = ""

    @property
    def read(self) -> bool:
        return self.value is not None


@dataclass(slots=True)
class PaystubRead:
    figures: dict[str, Figure] = field(default_factory=dict)
    pages_examined: int = 0
    tables_found: int = 0
    rows_examined: int = 0
    money_seen: int = 0
    # A table that named ONE of the two columns. Not the same fact as a table
    # that named neither, and a preparer told the wrong one of those goes
    # looking for a heading that is printed right there.
    half_labelled: str = ""
    employer: str = ""
    notes: list[str] = field(default_factory=list)

    # -- the denominator (S2) -------------------------------------------------
    def census(self) -> dict[str, int]:
        """How much was looked at, so a nil answer can be told from a nil look."""
        return {
            "pages_examined": self.pages_examined,
            "tables_found": self.tables_found,
            "rows_examined": self.rows_examined,
            "money_seen": self.money_seen,
            "fields_asked": len(self.figures),
            "fields_read": sum(1 for f in self.figures.values() if f.read),
            "fields_refused": sum(1 for f in self.figures.values() if not f.read),
        }

    def summary(self) -> str:
        c = self.census()
        if c["pages_examined"] == 0:
            return "NOTHING TO READ — no page of this file carried any text."
        def n(count: int, one: str, many: str) -> str:
            return f"{count} {one if count == 1 else many}"

        return (f"{c['fields_read']} of {c['fields_asked']} figures read, "
                f"{c['fields_refused']} refused — from {n(c['rows_examined'], 'row', 'rows')} "
                f"under {n(c['tables_found'], 'labelled table', 'labelled tables')} "
                f"across {n(c['pages_examined'], 'page', 'pages')} "
                f"({c['money_seen']} figures seen).")

    def unresolved(self) -> dict[str, str]:
        """``{label: why it could not be read}`` — and the ONLY thing a model may
        be asked about. See :mod:`satc.ingest.readers.paystub_judgement`."""
        return {f.label: f.problem for f in self.figures.values() if not f.read}

    def problems(self) -> list[str]:
        return [f.problem for f in self.figures.values() if f.problem]

    def to_read_result(self) -> ReadResult:
        """The labeled fields, with the page each came off.

        `deterministic=True` is a statement about THIS READER — word boxes, a
        printed heading and a regex, no model, same file twice gives the same
        answer. It is not a claim that the answer is right, which is what
        `uncertain_labels` is for.
        """
        labeled: dict[str, str] = {}
        pages: dict[str, int] = {}
        uncertain: set[str] = set()
        for fig in self.figures.values():
            if not fig.read:
                continue
            labeled[fig.label] = fig.value or ""
            if fig.page is not None:
                pages[fig.label] = fig.page
            if fig.reason_code == "confirm":
                uncertain.add(fig.label)
        if self.employer:
            labeled[LABEL_EMPLOYER] = self.employer
            uncertain.add(LABEL_EMPLOYER)         # free text always gets a look
        return ReadResult(labeled_fields=labeled, uncertain_labels=uncertain,
                          pages=pages, deterministic=True,
                          backend="PaystubColumnReader")


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------

# How far off a heading's own width a number may sit and still be counted as
# under it. In normalized page width; 0.015 of a US Letter page is about 9pt,
# roughly one character. Wider than this and a number midway between two
# columns starts being claimed by one of them, which is the guess this reader
# exists to refuse.
COLUMN_TOLERANCE = 0.015
# Two headings may overlap a number (a wide heading beside a narrow one). The
# closer right edge wins only if it is closer by this much; otherwise the number
# is left alone. Money columns are right-aligned under right-aligned headings,
# so the right edge is the edge that means something.
AMBIGUITY_MARGIN = 0.004
ROW_TOLERANCE = 0.6              # share of a word's height, for "same row"


@dataclass(slots=True)
class _Column:
    kind: str        # CURRENT / YTD / OTHER
    printed: str     # the heading exactly as it appears on the stub
    x0: float
    x1: float


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().strip(":;|").lower())


def _rows_of(words: list[Word]) -> list[list[Word]]:
    """Words grouped into printed rows, each sorted left to right."""
    rows: list[dict] = []
    for w in sorted(words, key=lambda w: w.cy):
        height = max(w.y1 - w.y0, 1e-6)
        for row in rows:
            if abs(w.cy - row["cy"]) <= ROW_TOLERANCE * height:
                row["ws"].append(w)
                break
        else:
            rows.append({"cy": w.cy, "ws": [w]})
    return [sorted(r["ws"], key=lambda w: w.x0) for r in rows]


def _headings_in(row: list[Word]) -> list[_Column]:
    """Every column heading printed on this row, longest phrase first."""
    low = [_norm(w.text) for w in row]
    out: list[_Column] = []
    i = 0
    while i < len(row):
        for n in range(min(_MAX_HEADING_WORDS, len(row) - i), 0, -1):
            phrase = " ".join(low[i: i + n]).replace("- ", "-")
            kind = _HEADINGS.get(phrase)
            if kind is None:
                continue
            run = row[i: i + n]
            out.append(_Column(kind=kind,
                               printed=" ".join(w.text for w in run),
                               x0=min(w.x0 for w in run), x1=max(w.x1 for w in run)))
            i += n
            break
        else:
            i += 1
    return out


def _is_header_row(cols: list[_Column]) -> bool:
    """A row names the columns only if it names BOTH of the two that matter.

    STRICT ON PURPOSE. If a stub names its year-to-date column and leaves the
    other unnamed, the unnamed one might be this period, or a rate, or an
    employer contribution -- and telling those apart by position is the guess.
    The cost is `current_only_no_ytd` in the corpus, a stub with a single
    `Amount` column, which this reads as nothing. That is a real limitation and
    it is written down rather than papered over.
    """
    return any(c.kind == CURRENT for c in cols) and any(c.kind == YTD for c in cols)


def _column_for(word: Word, cols: list[_Column]) -> _Column | None:
    """The column a number sits under, or None when it sits under none clearly."""
    hits = [c for c in cols
            if word.x0 <= c.x1 + COLUMN_TOLERANCE and word.x1 >= c.x0 - COLUMN_TOLERANCE]
    if not hits:
        return None
    if len(hits) == 1:
        return hits[0]
    hits.sort(key=lambda c: abs(word.x1 - c.x1))
    if abs(word.x1 - hits[0].x1) + AMBIGUITY_MARGIN < abs(word.x1 - hits[1].x1):
        return hits[0]
    return None                   # two columns could claim it: leave it alone


def _money(word: Word) -> str | None:
    value = parse_currency(word.text)
    if value is None:
        return None
    return f"{abs(value):.2f}"


def _row_labels(row: list[Word], first_money: Word | None) -> list[str]:
    """What this row could be calling itself. Two readings, because one is not enough.

    A PAYSTUB IS NOT ONE TABLE DOWN THE PAGE. Employee number, department,
    cheque number and net pay print in a block at the LEFT while the earnings
    table runs down the right, so one line across the page carries words from
    two unrelated blocks:

        Dept 22        Gross Pay        2,400.00      31,200.00
        Net 1,982.00   401(k)             120.00       1,560.00

    Reading "everything left of the first number" calls those rows ``dept`` and
    ``net``, and the stub goes unread. FOUND BY RENDERING A CASE AND LOOKING AT
    IT: every other case in the corpus was a single table down the page, which
    is not what a stub looks like, and no test could have told me so.

    So a row offers two readings and a match on either is a match:

      1. everything left of the row's first figure — right when the label
         column is the leftmost thing on the line, which is the simple layout;
      2. the run of words immediately left of the first figure that sits under
         a named column — right when something else is printed further left.

    Neither reading may INVENT a label: both are runs of words actually printed
    on the row, so a row that says nothing still matches nothing.
    """
    plain: list[str] = []
    for w in row:
        if parse_currency(w.text) is not None:
            break
        plain.append(w.text)

    beside: list[str] = []
    if first_money is not None:
        for w in reversed([w for w in row if w.x1 <= first_money.x0]):
            if parse_currency(w.text) is not None:
                break
            beside.insert(0, w.text)

    out = [_norm(" ".join(plain))]
    joined = _norm(" ".join(beside))
    if joined and joined != out[0]:
        out.append(joined)
    return [c for c in out if c]


def _matches_any(labels: list[str], anchors: tuple[str, ...]) -> bool:
    return any(_matches(label, anchors) for label in labels)


def _matches(label: str, anchors: tuple[str, ...]) -> bool:
    """Whole-label matching, not substring.

    ``in`` would make ``gross`` match ``adjusted gross`` and ``fed tax`` match
    ``fed tax employer portion``. Those are different numbers.
    """
    for a in anchors:
        if label == a or label.startswith(a + " ") or label.startswith(a + ":"):
            return True
    return False


# --------------------------------------------------------------------------
# Page reading
# --------------------------------------------------------------------------

@dataclass(slots=True)
class _Found:
    value: str
    page: int
    printed: str


def _read_page(words: list[Word], number: int, out: PaystubRead
               ) -> dict[tuple[str, str], list[_Found]]:
    """``{(field key, current|ytd): [what this page said]}`` for one page."""
    found: dict[tuple[str, str], list[_Found]] = {}
    cols: list[_Column] = []
    for row in _rows_of(words):
        out.rows_examined += 1
        headings = _headings_in(row)
        if _is_header_row(headings):
            cols = headings
            out.tables_found += 1
            continue
        named = {c.kind for c in headings} & {CURRENT, YTD}
        if len(named) == 1 and not out.half_labelled:
            out.half_labelled = next(c.printed for c in headings if c.kind in named)
        numbers = [w for w in row if parse_currency(w.text) is not None]
        out.money_seen += len(numbers)
        if not cols or not numbers:
            continue
        placed = [w for w in numbers
                  if (c := _column_for(w, cols)) is not None and c.kind != OTHER]
        labels = _row_labels(row, placed[0] if placed else None)
        for spec in ROWS:
            if not _matches_any(labels, spec.anchors):
                continue
            for w in numbers:
                col = _column_for(w, cols)
                # THIS LINE IS BELT AND BRACES, AND MUTATION TESTING SAID SO.
                # On 2 September 2026 removing `or col.kind == OTHER` changed
                # nothing any test could see, because `_settle` only ever asks
                # for the two kinds it wants, so a rate parked under
                # ("gross", "other") is unreachable either way. It is kept —
                # deleting it would leave a loop that reads as though it accepts
                # every named column — but it is NOT a control and nothing here
                # should be read as claiming it stops something (S30). What
                # actually keeps a rate out of a paycheck figure is
                # `_column_for` refusing a number that sits under no heading,
                # and that one is measured: `unheaded_extra_column`.
                if col is None or col.kind == OTHER:
                    continue
                value = _money(w)
                if value is None:
                    continue
                found.setdefault((spec.key, col.kind), []).append(
                    _Found(value=value, page=number, printed=col.printed))
    return found


# --------------------------------------------------------------------------
# Pay frequency — two deterministic signals that must not contradict
# --------------------------------------------------------------------------

_FREQ_WORDS: tuple[tuple[str, str], ...] = (
    ("semi-monthly", "semimonthly"), ("semimonthly", "semimonthly"),
    ("semi monthly", "semimonthly"), ("twice a month", "semimonthly"),
    ("bi-weekly", "biweekly"), ("biweekly", "biweekly"), ("bi weekly", "biweekly"),
    ("every two weeks", "biweekly"), ("fortnightly", "biweekly"),
    ("weekly", "weekly"), ("monthly", "monthly"),
)
_FREQ_CONTEXT = ("frequency", "pay period", "pay type", "pay cycle", "pay schedule",
                 "period ending", "period beginning", "paid", "payroll frequency")
# A pay period covers an EXACT number of days, and the ranges must not overlap.
# THEY DID: the first cut wrote biweekly as 13-15 days and semimonthly as 15-17,
# so a 1st-to-15th semimonthly period -- fifteen days -- matched biweekly first
# and came back as a 26-cheque year on a 24-cheque job. The corpus caught it on
# its first run, which is what a corpus is for. A span outside these bands is
# not a signal, and is not stretched into one.
_SPAN_TO_FREQ: tuple[tuple[int, int, str], ...] = (
    (7, 7, "weekly"),
    (14, 14, "biweekly"),
    (15, 16, "semimonthly"),
    (28, 31, "monthly"),
)
_DATE = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")


def _freq_from_words(text: str) -> str:
    low = text.lower()
    for line in low.splitlines():
        if any(ctx in line for ctx in _FREQ_CONTEXT):
            for needle, norm in _FREQ_WORDS:
                if needle in line:
                    return norm
    return ""


def _freq_from_dates(text: str) -> tuple[str, int]:
    """``(frequency, days covered)`` from a printed pay period, else ``("", 0)``.

    A SECOND SIGNAL, and deliberately independent of the first: the printed
    words and the printed dates are put on the stub by different parts of a
    payroll system, so when they agree that is corroboration, and when they
    disagree that is a fact worth stopping on rather than a tie to break.
    """
    for line in text.splitlines():
        low = line.lower()
        if not any(ctx in low for ctx in _FREQ_CONTEXT):
            continue
        dates: list[date] = []
        for m in _DATE.finditer(line):
            iso = parse_date(m.group(0))
            if iso:
                dates.append(date.fromisoformat(iso))
        if len(dates) < 2:
            continue
        dates.sort()
        days = (dates[-1] - dates[0]).days + 1
        for low_d, high_d, freq in _SPAN_TO_FREQ:
            if low_d <= days <= high_d:
                return freq, days
        return "", days
    return "", 0


def _pay_frequency(text: str) -> Figure:
    fig = Figure(label=LABEL_PAY_FREQUENCY, plain="pay schedule")
    said = _freq_from_words(text)
    implied, days = _freq_from_dates(text)
    if said and implied and said != implied:
        fig.reason_code = "frequency_conflict"
        fig.problem = REASONS["frequency_conflict"].format(
            said=IN_WORDS.get(said, said), days=days,
            implied=IN_WORDS.get(implied, implied))
        return fig
    chosen = said or implied
    if not chosen:
        fig.reason_code = "frequency_unknown"
        fig.problem = REASONS["frequency_unknown"]
        return fig
    fig.value = chosen
    if not (said and implied):
        fig.reason_code = "confirm"        # one signal only -> a preparer looks
    return fig


# --------------------------------------------------------------------------
# Pages in, figures out
# --------------------------------------------------------------------------

def page_words(source: str | Path) -> list[tuple[int, list[Word]]]:
    """Every page's words with normalized boxes.

    `paystub_layout.extract_layout` does this for ONE page -- `page = doc[0]` --
    which is the whole of the firm's "read all pages available" left undone on
    the geometric path. The number-fragment stitching it does (`6 , 653.85`
    arriving as three tokens) is reused rather than rewritten.
    """
    try:
        import pymupdf
    except ImportError:                                  # pragma: no cover
        try:
            import fitz as pymupdf                       # type: ignore
        except ImportError as exc:                       # pragma: no cover
            raise PaystubError(
                "Reading a paystub needs PyMuPDF. Install it with: pip install pymupdf"
            ) from exc
    out: list[tuple[int, list[Word]]] = []
    with pymupdf.open(str(source)) as doc:
        for number, page in enumerate(doc, 1):
            rect = page.rect
            pw, ph = float(rect.width), float(rect.height)
            if pw <= 0 or ph <= 0:
                continue
            raw = page.get_text("words")
            items = [[w[0], w[1], w[2], w[3], str(w[4])] for w in raw if str(w[4]).strip()]
            if not items:
                out.append((number, []))
                continue
            items = _merge_number_fragments(items)
            out.append((number, [Word(text=it[4], x0=it[0] / pw, y0=it[1] / ph,
                                      x1=it[2] / pw, y1=it[3] / ph) for it in items]))
    return out


def _settle(spec: _Row, kind: str, label: str, plain: str,
            found: list[_Found]) -> Figure:
    """One field's answer across every page, or the refusal that replaces it."""
    fig = Figure(label=label, plain=plain)
    if not found:
        fig.reason_code = "not_found"
        fig.problem = REASONS["not_found"].format(what=plain)
        return fig

    by_page: dict[int, set[str]] = {}
    for f in found:
        by_page.setdefault(f.page, set()).add(f.value)

    # Two figures for the same thing ON ONE PAGE is a different fact from two
    # pages disagreeing, and a preparer needs to be told which happened.
    for page, values in sorted(by_page.items()):
        if len(values) > 1:
            fig.reason_code = "rows_disagree"
            fig.problem = REASONS["rows_disagree"].format(
                what=f"{plain} ({'this period' if kind == CURRENT else 'year to date'})",
                values=" and ".join(in_money(v) for v in sorted(values)))
            return fig

    pages = sorted(by_page)
    first = by_page[pages[0]].pop()
    for page in pages[1:]:
        other = next(iter(by_page[page]))
        if other != first:
            fig.reason_code = "pages_disagree"
            fig.problem = REASONS["pages_disagree"].format(
                a=pages[0], b=page,
                what=f"{plain} ({'this period' if kind == CURRENT else 'year to date'})",
                va=in_money(first), vb=in_money(other))
            return fig

    winner = next(f for f in found if f.page == pages[0])
    fig.value = first
    fig.page = winner.page
    fig.column_said = winner.printed
    return fig


def _cross_check(period: Figure, ytd: Figure, plain: str) -> None:
    """A year-to-date total below one pay period's figure is not a total.

    A RUNTIME CONTROL, not a pin (S30): it fires on real input, on the exact
    failure the column rule is there to prevent, and it fires on the ONE case
    the column rule cannot see -- a stub whose headings are printed the wrong
    way round. Both figures are dropped, because one of them is wrong and
    nothing here knows which.
    """
    if not (period.read and ytd.read):
        return
    try:
        p, y = float(period.value or ""), float(ytd.value or "")
    except ValueError:                                    # pragma: no cover
        return
    if y >= p:
        return
    text = REASONS["ytd_below_period"].format(
        what=plain, ytd=in_money(ytd.value or ""), period=in_money(period.value or ""))
    for fig in (period, ytd):
        fig.value, fig.page, fig.column_said = None, None, ""
        fig.reason_code, fig.problem = "ytd_below_period", text


class PaystubColumnReader:
    """Reads a paystub by its printed column headings. No model, no network."""

    def read(self, source: str) -> PaystubRead:
        out = PaystubRead()
        pages = page_words(source)
        out.pages_examined = len(pages)
        merged: dict[tuple[str, str], list[_Found]] = {}
        text_lines: list[str] = []
        for number, words in pages:
            for row in _rows_of(words):
                text_lines.append(" ".join(w.text for w in row))
            for key, founds in _read_page(words, number, out).items():
                merged.setdefault(key, []).extend(founds)
        self._settle_all(merged, out, "\n".join(text_lines))
        return out

    def read_words(self, pages: list[tuple[int, list[Word]]]) -> PaystubRead:
        """The same read over already-extracted words (unit-testable, no file)."""
        out = PaystubRead()
        out.pages_examined = len(pages)
        merged: dict[tuple[str, str], list[_Found]] = {}
        text_lines: list[str] = []
        for number, words in pages:
            for row in _rows_of(words):
                text_lines.append(" ".join(w.text for w in row))
            for key, founds in _read_page(words, number, out).items():
                merged.setdefault(key, []).extend(founds)
        self._settle_all(merged, out, "\n".join(text_lines))
        return out

    @staticmethod
    def _settle_all(merged: dict[tuple[str, str], list[_Found]],
                    out: PaystubRead, text: str) -> None:
        for spec in ROWS:
            period = _settle(spec, CURRENT, spec.current_label, spec.plain,
                             merged.get((spec.key, CURRENT), []))
            ytd = _settle(spec, YTD, spec.ytd_label, spec.plain,
                          merged.get((spec.key, YTD), []))
            _cross_check(period, ytd, spec.plain)
            out.figures[spec.current_label] = period
            out.figures[spec.ytd_label] = ytd
        out.figures[LABEL_PAY_FREQUENCY] = _pay_frequency(text)

        # A stub that named no columns says so ONCE, rather than five times.
        if out.tables_found == 0:
            half = out.half_labelled
            for label, fig in out.figures.items():
                if label == LABEL_PAY_FREQUENCY or fig.read:
                    continue
                if half:
                    fig.reason_code = "one_column_only"
                    fig.problem = REASONS["one_column_only"].format(
                        named=half, what=fig.plain)
                else:
                    fig.reason_code = "no_columns"
                    fig.problem = REASONS["no_columns"].format(what=fig.plain)

        out.employer = _employer(text.splitlines())
