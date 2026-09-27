"""The New variables tab (the redesign, section 9; capabilities 4b and 4e): does each candidate still tell good loans
from bad on loans it was never found on, and once the held-fixed columns are held fixed? It replaces the
Confirmatory test tab and keeps every statistic that tab showed.

A test of a new variable today confirms a saved shortlist, the pre-spec: its column cut into groups, each group
compared with the reference group. Each row of the table is one candidate comparison, a group against the reference:

    Found                    on the development loans, where the groups came from, nothing held fixed
    Confirmed · held back    the same comparison on the holdout, nothing held fixed; Holds up?
    Confirmed, X held fixed  the same again inside the pockets the held-fixed columns make; Still holds?
    Excess, Material?        the group's losses on the holdout above its share, scaled to the whole book, against
                             Control's materiality line
    In words                 the two verdicts together

Each input is reported with and without the columns held fixed (the firm's lean pre-spec, 26 Sep 2026). A saved
shortlist was found on another run, so its Found columns are hidden, and Record names the file (the spec).

Under the chart, the tests in full: B3 and B4 (does the column matter at all, and in one direction), B5 (each
group's odds ratio with its range) on every set of loans with and without the columns held fixed, and 4e's
concentration on the holdout. Each has its finding in one plain line.

Live (OC-40): Holds up?, Still holds?, Material?, In words, every "significant", every range and the chart's worse
line follow Control (confidence, materiality, worse at). The odds ratios, statistics and p-values are the Run's;
none depends on those settings. No SORT, FILTER or LET.
"""

from __future__ import annotations

import math

from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.series import SeriesLabel
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from . import house, live

SHEET = "New variables"
OLD_SHEET = "Confirmatory test"                            # the tab this replaces; a Run takes it off
INK, SLATE, PAPER = house.INK_TEXT, house.SLATE, house.PAPER
WORSE_FILL, BETTER_FILL = house.ALERT_FG, house.POSITIVE_BG
FIRST, LAST = 2, 14                                        # columns B to N
#: the table's columns
(N_CAND, N_COMP, N_FG, N_FP, N_CG, N_CP, N_HOLDS, N_HG, N_HP, N_STILL, N_EX, N_MAT, N_WORDS) = range(2, 15)
LINE_COL = 24                                              # X, hidden: the chart's worse line, =worse_at a row
HELPER = 26                                                # Z, hidden: the pieces the plain lines join
Z = "NORMSINV(1-(1-confidence)/2)"                         # the live z, as the Split tab writes it
P_FMT = '[<0.0001]"under 0.01%";[<0.01]0.00%;0.0%'         # book.P_FMT
X_FMT = '0.00"×"'
LIFT_TAIL = " times the holdout's bad rate"
YES, NO = "Yes", "No"
WIDTHS = {1: 2, N_CAND: 20, N_COMP: 30, N_FG: 10, N_FP: 11, N_CG: 12, N_CP: 12, N_HOLDS: 16, N_HG: 12, N_HP: 12,
          N_STILL: 16, N_EX: 14, N_MAT: 12, N_WORDS: 42}
#: the tests in full keep their numbers in F to N, never in Found's two columns, which a saved shortlist hides
DATA = N_CG
TEXT_WIDE = 190                                            # about how many characters fit across C to N


def _c(n: int) -> str:
    return live.col(n)


def _q(s: str) -> str:
    return live.q(s)


def _cell(ws, r: int, c: int, v=None, *, bold=False, color=INK, h="center", fmt=None, size=10):
    x = ws.cell(row=r, column=c, value=v)
    x.font = Font(name="Calibri", bold=bold, size=size, color=color)
    x.alignment = Alignment(horizontal=h, vertical="center")
    if fmt:
        x.number_format = fmt
    return x


def _rule(ws, r: int, first: int = FIRST, last: int = LAST) -> None:
    for c in range(first, last + 1):
        ws.cell(row=r, column=c).border = Border(bottom=Side(style="thin", color=house.ROW_RULE))
    ws.row_dimensions[r].height = 18


def _line(ws, r: int, label: str | None, text, chars: int | None = None) -> int:
    """A finding in words: a label in B and the words across C to N. Prose, so it may wrap. Returns the next row."""
    if label is not None:
        _cell(ws, r, FIRST, label, bold=True, h="left").alignment = Alignment(horizontal="left", vertical="top")
    ws.merge_cells(start_row=r, start_column=FIRST + 1, end_row=r, end_column=LAST)
    c = ws.cell(row=r, column=FIRST + 1, value=text)
    c.alignment = Alignment(wrap_text=True, vertical="top", horizontal="left")
    c.font = Font(name="Calibri", size=10, color=INK)
    n = chars if chars is not None else len(str(text))
    ws.row_dimensions[r].height = 15.0 * max(1, math.ceil(n / TEXT_WIDE)) + 4
    return r + 1


def _sig_word(ref: str) -> str:
    return f'IF({ref}="","",IF({live.sig(ref)},"significant","not significant"))'


def _held_words(strata) -> str:
    return " and ".join(strata)


def _num(v) -> float | None:
    return None if v is None or (isinstance(v, float) and not math.isfinite(v)) else v


class _Views:
    """The four sets of numbers a candidate is read on, by the words the tab uses for them."""

    def __init__(self, t):
        held = _held_words(t.strata)
        self.held = held
        dev, hold = t.development, t.holdout
        if t.held:
            self.all = [(t.development_plain, "Found, nothing held fixed", "On development, with nothing held fixed,"),
                        (dev, f"Found, {held} held fixed", "On development,"),
                        (t.holdout_plain, "Confirmed on the held-back loans, nothing held fixed",
                         "On the holdout, with nothing held fixed,"),
                        (hold, f"Confirmed on the held-back loans, {held} held fixed", "On the holdout,")]
        else:
            self.all = [(dev, "Found, nothing held fixed", "On development,"),
                        (hold, "Confirmed on the held-back loans, nothing held fixed", "On the holdout,")]


def _method(res, st, t, excess, stamp: str) -> list[tuple[str, object]]:
    """The tab's one method note (tenet T1): every test and choice behind the rows, once, in plain words."""
    K = len(t.groups)
    ref = t.groups[t.ref]
    held = _held_words(t.strata)
    dev, hold = t.development, t.holdout
    out = [("The column", f"{t.column}, in {K} groups: {'; '.join(t.groups)}. The groups are the pre-spec's."),
           ("Compared with", f"{ref}, the pre-spec's reference group. Every other group is compared with it.")]
    said = []
    for side, what in ((dev, "found on: where the groups were chosen"), (hold, "held back: the test that counts")):
        rate = side.n_bad / side.n if side.n else None
        said.append(f"Loans made {side.range.text()}: {side.n:,} loans, {side.n_bad:,} bad"
                    + (f" ({rate:.2%})" if rate is not None else "") + f"; {what}.")
    if t.left_out:
        words = "; ".join(f"{v:,} {k}" if k.startswith("made") else f"{v:,} with {k}" for k, v in t.left_out.items())
        said.append(f"Left out of this test: {words}. Record counts every loan.")
    out.append(("Found, then confirmed", " ".join(said) + " The comparison is made once on each; only the "
                                                          "held-back result counts."))
    out.append(("Gap", f"The odds ratio against {ref}. Odds are bad loans divided by good ones, and an odds ratio is "
                       f"a group's odds divided by {ref}'s: 2.00× means twice the odds of going bad. While few loans "
                       f"go bad it is close to how many times as often they do. Worked out by conditional logistic "
                       f"regression, which compares the groups inside each pocket and takes each pocket's own count "
                       f"of bad loans as given, instead of estimating a rate for every pocket, which biases the "
                       f"answer when pockets are thin."))
    out.append(("p-value", live.text("The chance of a gap at least this big if the group were no different from "
                                     f"{ref}. Below ", ('TEXT(significance_bar,"0%")',), " is significant, at ",
                                     ('TEXT(confidence,"0%")',), " sure. Two-sided: a gap either way counts.")))
    out.append(("Holds up?", "Yes when the held-back loans show the gap on the same side of 1 as the found loans "
                             "did, and significant. Only the held-back result counts: the found one is where the "
                             "idea came from."))
    if t.held:
        out.append((f"{held} held fixed",
                    f"The held-back comparison made again with every loan compared only with loans in its own "
                    f"pocket, cut by {held} at the band edges on Record. A difference in the {held} mix then can't "
                    f"pass for a difference in {t.column}. Still holds? says whether the gap stays; if it goes, "
                    f"the candidate was mostly telling you {held}. Every pocket counts, however small: fewest "
                    f"loans and fewest losses decide only whether one pocket can be read on its own, and a "
                    f"pocket where no loan, or every loan, went bad says nothing and adds nothing."))
    else:
        out.append(("Nothing held fixed", "The pre-spec holds no column fixed, so the whole book is one pocket and "
                                          "there is one confirmation."))
    if excess is not None:
        what = "charge-offs" if excess.unit == "dollars" else "bad loans"
        out.append(("Material?", f"Excess is a group's {what} on the held-back loans above its share of them (its "
                                 f"share of the held-back loans), times the whole book's {what} over the held-back "
                                 f"loans', so it sits on the same scale as Control's materiality line. Material? is "
                                 f"Yes when it reaches the line."))
    out.append(("In words", f"The two verdicts read together: holds up, and not just {held or 'the columns held fixed'}; "
                            f"holds up, but it was mostly {held or 'those columns'}; holds up only with them held "
                            f"fixed; or didn't hold up on held-back loans." if t.held else
                "Holds up on held-back loans, or didn't."))
    out.append(("The tests in full", f"Under the chart. Does {t.column} matter at all: the general test (the "
                                     f"Mantel-Haenszel test for {K} groups: a standard way to add pockets up without "
                                     f"mixing their loans), read against a chi-square on {K - 1} degrees of freedom, "
                                     f"one fewer than the groups; the trend test, which gives the groups the scores "
                                     f"1 to {K} and asks whether the bad rate climbs or falls steadily with them, on 1 "
                                     f"degree of freedom; and the regression's block test (a likelihood ratio test, "
                                     f"on {K - 1} degrees of freedom), whether the groups together add anything. A "
                                     f"difference with no trend is a U or a hump, which a straight-line test would "
                                     f"call nothing. Then each group's odds ratio with its range, and how much of the "
                                     f"held-back loans' losses sit in each group (on the holdout only, and on the "
                                     f"book as a whole, not pocket by pocket: the lift, the group's bad rate over "
                                     f"the holdout's, is the finding, never the share of all losses)."))
    gaps = [s.mh_gap for s in (dev, hold) if s.mh_gap is not None]
    out.append(("The range", live.text("Where the true odds ratio sits, ", ('TEXT(confidence,"0%")',), " sure: the "
                                       "log odds ratio plus and minus the multiple of its standard error that the "
                                       "confidence level sets."
                                       + (f" As a check, each odds ratio held fixed was worked out a second way, pair "
                                          f"by pair with Mantel-Haenszel: the largest gap between the two is "
                                          f"{max(gaps):.1%}." if gaps else ""))))
    if st is not None:
        out.append(("Written shortlist", f"This run confirms the saved shortlist {st.name}, the pre-spec. Its Found "
                                         f"columns are hidden (unhide columns D and E to see them) and Record names "
                                         f"the file. The tests in full show both sets of loans."))
    out.append(("Choices made here that no ruling settles yet", " ".join((
        f"The trend test scores the groups 1 to {K}, evenly spaced, rather than by where their numbers sit.",
        "Conditional logistic regression is used in every pocket, whatever its size: the unconditional fit the scope "
        "allows for pockets over a few thousand loans isn't used, as the conditional one is exact and quick at any "
        "size.",
        "A loan with no readable value in a column the pockets are cut by sits in a pocket of its own, as on the "
        "grids.",
        "A group with no bad loan, or only bad loans, in the pockets that say something has no odds ratio; the "
        "others are fitted as if its loans weren't there, which is where the regression heads anyway.",
        "Excess is scaled to the whole book by its losses over the held-back loans' losses."))))
    out.append(("As of", f"The numbers are the last Run's, {stamp}. Holds up?, Still holds?, Material?, In words, "
                         f"every range and the chart's worse line follow Control."))
    return out


def write(wb, res, stamp: str = "") -> None:
    st = getattr(res, "prespec", None)
    t = getattr(st, "test", None) if st is not None else None
    if t is None:
        return
    from . import confirmatory, results
    for old in (SHEET, OLD_SHEET):
        if old in wb.sheetnames:
            del wb[old]
    ws = wb.create_sheet(SHEET)
    live.ensure(wb, res)
    for c, w in WIDTHS.items():
        ws.column_dimensions[_c(c)].width = w
    house.title_band(ws, SHEET, f"Does {t.column} still tell good loans from bad on loans it was never found on, "
                                f"and once {_held_words(t.strata) or 'the columns held fixed'} "
                                f"{'are' if len(t.strata) != 1 else 'is'} held fixed?", FIRST, LAST,
                     tab=house.TAB_RESULT)
    if t.problem:
        r = house.method_note(ws, 3, FIRST, LAST, [("Not run", f"The confirmatory test couldn't be run: "
                                                              f"{t.problem}. Record says why.")])
        _finish(ws, r)
        return
    excess = confirmatory.excess(res, t)
    r = house.method_note(ws, 3, FIRST, LAST, _method(res, st, t, excess, stamp or "as of the last Run"))

    # ---------------------------------------------------------------- what was tested: the tiles
    dev, hold = t.development, t.holdout
    outcome = next((m.flag for m in res.measures if m.name == "outcome_loans"), "the outcome")
    _cell(ws, r, FIRST, "WHAT WAS TESTED", bold=True, color=SLATE, h="left", size=8)
    _cell(ws, r + 1, FIRST, "from the saved shortlist", color=SLATE, h="left", size=8)
    # tiles sit only over columns that are never hidden: Found's two are, for a saved shortlist
    tiles = [("Outcome", outcome, N_COMP, N_COMP), ("Candidates", t.column, N_CG, N_HOLDS),
             ("Held fixed", " · ".join(t.strata) or "Nothing", N_HG, N_STILL),
             ("Material at · live", results.material_at(res), N_EX, N_MAT),
             ("Loans", f"{dev.n:,} found · {hold.n:,} held back", N_WORDS, N_WORDS)]
    for label, value, a, b in tiles:
        house.tile(ws, r, a, b, label, value, top=house.KEY_RED if label.startswith("Material") else house.INK)
    r += 3
    n = f'COUNTIF(Status,"{house.WAITING}")'
    _cell(ws, r, FIRST, f"The numbers are from the last Run, {stamp or 'as of the last Run'}. The verdicts, the "
                        f"materiality line and the chart's worse line follow Control.", color=SLATE, h="left", size=9)
    _cell(ws, r + 1, FIRST, f'=IFERROR(IF({n}=0,"","↻ "&{n}&IF({n}=1," Control change waits for a Run.",'
                            f'" Control changes wait for a Run.")),"")', bold=True, color=house.CRIMSON, h="left",
          size=9)
    r += 3

    # ---------------------------------------------------------------- the table
    held = _held_words(t.strata)
    unit_dollars = excess is not None and excess.unit == "dollars"
    groups = [(N_FG, N_FP, f"Found · {dev.n:,} loans", house.STONE, SLATE),
              (N_CG, N_HOLDS, f"Confirmed · {hold.n:,} held back", house.INK, INK),
              (N_HG, N_STILL, f"Confirmed, {held} held fixed" if t.held else "Nothing held fixed: the pre-spec holds "
                                                                          "no column fixed", house.INK, INK)]
    for a, b, text, rule, colour in groups:
        ws.merge_cells(start_row=r, start_column=a, end_row=r, end_column=b)
        _cell(ws, r, a, text, bold=True, color=colour, size=9)
        for c in (a, b):
            ws.cell(row=r, column=c).border = Border(bottom=Side(style="medium", color=rule))
    head = r + 1
    house.header(ws, head, FIRST, ["Candidate", "Compared", "Gap", "p-value", "Gap", "p-value", "Holds up?", "Gap",
                                   "p-value", "Still holds?", "Excess $" if unit_dollars else "Excess bad loans",
                                   "Material?", "In words"], centre_from=2)
    ws.cell(row=head, column=N_WORDS).alignment = Alignment(horizontal="left", vertical="center")
    ref = t.groups[t.ref]
    fit = lambda side, k: (None if side is None or side.fit.odds[k] is None else side.fit.odds[k],   # noqa: E731
                           None if side is None else side.fit.p[k])
    key = live.q("gco_rate" if unit_dollars else "outcome_loans")
    line = f'IF(materiality_kind="none",0,INDEX(line_values,MATCH({key},line_keys,0)))'
    first_row = head + 1
    r = first_row
    for k, name in enumerate(t.groups):
        if k == t.ref:
            continue
        fg, fp = fit(t.development_plain, k)
        cg, cp = fit(t.holdout_plain, k)
        hg, hp = fit(t.holdout, k) if t.held else (None, None)
        vals = {N_CAND: t.column, N_COMP: f"{name} vs {ref}", N_FG: _num(fg), N_FP: fp, N_CG: _num(cg), N_CP: cp,
                N_HG: _num(hg), N_HP: hp,
                N_EX: None if excess is None or excess.per_group[k] is None else round(excess.per_group[k], 6)}
        for c, v in vals.items():
            fmt = X_FMT if c in (N_FG, N_CG, N_HG) else P_FMT if c in (N_FP, N_CP, N_HP) else \
                ('"$"#,##0;-"$"#,##0' if unit_dollars else "#,##0.0") if c == N_EX else None
            _cell(ws, r, c, v, bold=c in (N_CAND, N_CG, N_HG), h="left" if c in (N_CAND,) else "center", fmt=fmt,
                  color=SLATE if c in (N_FG, N_FP, N_COMP) else INK)
        F, G, C_, P, H, J = (f"${_c(c)}{r}" for c in (N_FG, N_FP, N_CG, N_CP, N_HG, N_HP))

        def same(x):
            return f"IF(ISNUMBER({F}),({F}>1)=({x}>1),{x}>1)"
        _cell(ws, r, N_HOLDS, f'=IF(NOT(ISNUMBER({C_})),"",IF(AND({live.sig(P)},{same(C_)}),"{YES}","{NO}"))', bold=True)
        _cell(ws, r, N_STILL, f'=IF(NOT(ISNUMBER({H})),"",IF(AND({live.sig(J)},{same(H)}),"{YES}","{NO}"))',
              bold=True)
        L = f"${_c(N_EX)}{r}"
        _cell(ws, r, N_MAT, f'=IFERROR(IF(NOT(ISNUMBER({L})),"",IF({line}="","",IF(AND({L}>0,{L}>={line}),'
                            f'"{YES}","{NO}"))),"")')
        hu, sh = f"${_c(N_HOLDS)}{r}", f"${_c(N_STILL)}{r}"
        if t.held:
            words = (f'=IF({hu}="","",IF({hu}="{YES}",IF({sh}="{YES}",{_q(f"Holds up, and not just {held}")},'
                     f'{_q(f"Holds up, but it was mostly {held}")}),IF({sh}="{YES}",'
                     f'{_q(f"Holds up only with {held} held fixed")},"Didn\'t hold up on held-back loans")))')
        else:
            words = f'=IF({hu}="","",IF({hu}="{YES}","Holds up on held-back loans","Didn\'t hold up on held-back loans"))'
        _cell(ws, r, N_WORDS, words, h="left")
        ws.cell(row=r, column=LINE_COL, value="=worse_at")
        _rule(ws, r)
        r += 1
    last_row = r - 1
    rng = lambda c: f"{_c(c)}{first_row}:{_c(c)}{last_row}"                 # noqa: E731
    for c in (N_HOLDS, N_STILL):
        ws.conditional_formatting.add(rng(c), FormulaRule(
            formula=[f'{_c(c)}{first_row}="{YES}"'], font=Font(bold=True, color=house.POSITIVE),
            fill=PatternFill("solid", fgColor=house.POSITIVE_BG, bgColor=house.POSITIVE_BG)))
        ws.conditional_formatting.add(rng(c), FormulaRule(formula=[f'{_c(c)}{first_row}="{NO}"'],
                                                          font=Font(bold=True, color=SLATE)))
    ws.conditional_formatting.add(rng(N_MAT), FormulaRule(
        formula=[f'{_c(N_MAT)}{first_row}="{YES}"'], font=Font(bold=True),
        fill=PatternFill("solid", fgColor=house.MIST, bgColor=house.MIST)))
    found_hidden = st is not None                              # a saved shortlist: found on another run (the spec)
    if found_hidden:
        for c in (N_FG, N_FP):
            ws.column_dimensions[_c(c)].hidden = True
    ws.freeze_panes = f"A{head + 1}"
    r += 1

    # ---------------------------------------------------------------- the chart
    r = _chart(ws, t, first_row, last_row, r, found_hidden)

    # ---------------------------------------------------------------- the tests in full
    views = _Views(t)
    helper_rows: list[int] = []
    house.section(ws, r, FIRST, LAST, "The tests in full")
    r += 2
    r = _matters(ws, t, views, r)
    r = _odds(ws, t, views, r, helper_rows)
    r = _concentration(ws, t, r, helper_rows)
    _finish(ws, r, helper_rows)


def _chart(ws, t, first_row: int, last_row: int, r: int, found_hidden: bool) -> int:
    """Three bars a candidate (found STONE, confirmed INK, held fixed KEY_RED) and a dashed red line at the worse line,
    read from the table's cells, so it follows them."""
    ch = BarChart()
    ch.type = "col"
    ch.grouping = "clustered"
    ref = t.groups[t.ref]
    ch.title = f"The gap against {ref} (dashed: the worse line)"
    ch.y_axis.title = "Odds ratio"
    ch.y_axis.number_format = '0.00"×"'
    ch.y_axis.majorGridlines = None
    cats = Reference(ws, min_col=N_COMP, min_row=first_row, max_row=last_row)
    series = [] if found_hidden else [(N_FG, "Found", house.STONE)]
    series += [(N_CG, "Confirmed", house.INK)]
    if t.held:
        series += [(N_HG, f"Confirmed, {_held_words(t.strata)} held fixed", house.KEY_RED)]
    for c, name, colour in series:
        ch.add_data(Reference(ws, min_col=c, min_row=first_row, max_row=last_row), titles_from_data=False)
        s = ch.series[-1]
        s.tx = SeriesLabel(v=name)
        s.graphicalProperties.solidFill = colour
        s.graphicalProperties.line.solidFill = colour
    ch.set_categories(cats)
    line = LineChart()
    line.add_data(Reference(ws, min_col=LINE_COL, min_row=first_row, max_row=last_row), titles_from_data=False)
    s = line.series[0]
    s.tx = SeriesLabel(v="Worse at")
    s.graphicalProperties.line.solidFill = house.KEY_RED
    s.graphicalProperties.line.dashStyle = "dash"
    s.graphicalProperties.line.width = 19050
    s.marker.symbol = "none"
    s.smooth = False
    line.set_categories(cats)
    ch += line
    ch.legend.position = "b"
    ch.height, ch.width = 8.5, 26
    ch.visible_cells_only = False                              # the worse line sits in a hidden column
    ws.add_chart(ch, f"{_c(FIRST)}{r}")
    return r + 19


def _matters(ws, t, views, r: int) -> int:
    """B3, B4 and the block test on every set of loans: does the column matter at all?"""
    K = len(t.groups)
    _cell(ws, r, FIRST, f"Does {t.column} matter?", bold=True, h="left", size=11)
    r += 1
    house.header(ws, r, FIRST, ["Test", None, None, None, "Statistic", "Degrees of freedom", "p-value", "Reading",
                                None], centre_from=2)
    ws.merge_cells(start_row=r, start_column=FIRST, end_row=r, end_column=FIRST + 1)
    _wrap(ws, r)
    r += 1
    tests = (("Any difference across the groups (general)", lambda s: (s.association.general, s.association.df,
                                                                       s.association.p_general)),
             ("A steady climb or fall (trend)", lambda s: (s.association.trend, 1 if s.association.trend is not None
                                                           else None, s.association.p_trend)),
             ("Any difference, from the regression (block test)", lambda s: (s.fit.block, s.fit.df, s.fit.p_block)))
    for side, where, lead in views.all:
        house.sub_header(ws, r, FIRST, [f"{where}: loans made {side.range.text()}"])
        for c in range(FIRST + 1, LAST + 1):
            ws.cell(row=r, column=c).fill = house.fill(house.CANVAS)
        r += 1
        cells = []
        for label, get in tests:
            ws.merge_cells(start_row=r, start_column=FIRST, end_row=r, end_column=FIRST + 1)
            _cell(ws, r, FIRST, label, h="left")
            stat, df, p = get(side)
            _cell(ws, r, DATA, None if stat is None else round(stat, 6), fmt="0.00")
            _cell(ws, r, DATA + 1, df, fmt="0")
            _cell(ws, r, DATA + 2, p, fmt=P_FMT)
            ref_p = f"{_c(DATA + 2)}{r}"
            ws.merge_cells(start_row=r, start_column=DATA + 3, end_row=r, end_column=DATA + 4)
            _cell(ws, r, DATA + 3, f"={_sig_word(ref_p)}")
            cells.append(ref_p)
            _rule(ws, r, FIRST, DATA + 4)
            r += 1
        a = side.association
        g, tr = cells[0], cells[1]
        way = "rises" if a.direction > 0 else "falls"
        f = (f'=IF(AND({live.sig(g)},{live.sig(tr)}),{_q(f"{lead} the bad rate differs across the groups, and {way} steadily as {t.column} rises.")},'
             f'IF({live.sig(g)},{_q(f"{lead} the bad rate differs across the groups, but not in one direction: higher in some groups, lower in others.")},'
             f'IF({live.sig(tr)},{_q(f"{lead} the groups taken all at once do not differ significantly, but the bad rate {way} steadily as {t.column} rises (the trend test).")},'
             f'{_q(f"{lead} no difference across the groups shows at ")}&TEXT(confidence,"0%")&{_q(" sure. That is not proof there is none.")})))')
        r = _line(ws, r, "What it found", _empty(side, lead) or f, chars=150)
        r += 1
    return r


def _odds(ws, t, views, r: int, helper_rows: list) -> int:
    """B5: each group's odds ratio against the reference, with its range and p-value, on each set of loans, with
    nothing held fixed and with the columns held fixed side by side."""
    ref = t.groups[t.ref]
    K = len(t.groups)
    _cell(ws, r, FIRST, f"How much more often does each group go bad than {ref}?", bold=True, h="left", size=11)
    r += 1
    rng_head = live.text("Range (", ('TEXT(confidence,"0%")',), " sure)")
    held = _held_words(t.strata)
    heads = [f"Group of {t.column}", None, None, None, "Loans", "Bad loans", "Bad rate", "Odds ratio", "p-value",
             rng_head]
    if t.held:
        heads += [f"Odds ratio, {held} held fixed", "p-value", rng_head]
    ranges = ((t.development_plain, t.development, "Found", "On development,"),
              (t.holdout_plain, t.holdout, "Confirmed on the held-back loans", "On the holdout,"))
    for plain, side, where, lead in ranges:
        house.header(ws, r, FIRST, heads, centre_from=2)
        ws.merge_cells(start_row=r, start_column=FIRST, end_row=r, end_column=FIRST + 1)
        _wrap(ws, r)
        r += 1
        house.sub_header(ws, r, FIRST, [f"{where}: loans made {side.range.text()}"])
        for c in range(FIRST + 1, LAST + 1):
            ws.cell(row=r, column=c).fill = house.fill(house.CANVAS)
        r += 1
        first_group = r
        cells: dict = {}
        fits = [(plain.fit, DATA + 3, "plain"), (side.fit, DATA + 6, "held")] if t.held else \
            [(side.fit, DATA + 3, "held")]
        for k, name in enumerate(t.groups):
            ws.merge_cells(start_row=r, start_column=FIRST, end_row=r, end_column=FIRST + 1)
            _cell(ws, r, FIRST, name + (" (reference)" if k == t.ref else ""), h="left")
            _cell(ws, r, DATA, side.loans[k], fmt="#,##0")
            _cell(ws, r, DATA + 1, side.bad[k], fmt="#,##0")
            _cell(ws, r, DATA + 2, side.bad[k] / side.loans[k] if side.loans[k] else None, fmt="0.00%")
            for f, c, which in fits:
                if k == t.ref:
                    _cell(ws, r, c, "1.00")
                elif f.odds[k] is None:
                    _cell(ws, r, c, "none")
                else:
                    _cell(ws, r, c, round(f.odds[k], 10), fmt=X_FMT)
                    b, se = live.num(f.beta[k]), live.num(f.se[k])
                    _cell(ws, r, c + 1, f.p[k], fmt=P_FMT)
                    _cell(ws, r, c + 2, (f'=TEXT(EXP({b}-{Z}*{se}),"0.00")&"x to "&'
                                               f'TEXT(EXP({b}+{Z}*{se}),"0.00")&"x"'))
                    cells[(which, k)] = (f"{_c(c)}{r}", f"{_c(c + 1)}{r}", b, se)
            _rule(ws, r)
            r += 1
        for f, c, which in fits:
            # a significant odds ratio shaded, red above 1 and green below, against the one bar (OC-40)
            o, p = f"${_c(c)}{first_group}", f"${_c(c + 1)}{first_group}"
            for fill, cmp_ in ((WORSE_FILL, ">1"), (BETTER_FILL, "<1")):
                ws.conditional_formatting.add(f"{_c(c)}{first_group}:{_c(c + 2)}{r - 1}", FormulaRule(
                    formula=[f"AND(ISNUMBER({o}),ISNUMBER({p}),{p}<{live.BAR},{o}{cmp_})"],
                    fill=PatternFill("solid", fgColor=fill, bgColor=fill)))
        said_lines = [("plain", f"{lead[:-1]}, with nothing held fixed,"), ("held", lead)] if t.held else \
            [("held", lead)]
        for which, lead_ in said_lines:
            pieces = []
            for k, name in enumerate(t.groups):
                got = cells.get((which, k))
                if got is None:
                    continue
                o, p, b, se = got
                rng = f'" ("&TEXT(EXP({b}-{Z}*{se}),"0.00")&"x to "&TEXT(EXP({b}+{Z}*{se}),"0.00")&"x)"'
                said = (f'IF({o}>=1,{_q(f"; {name} goes bad ")}&TEXT({o},"0.00")&{_q(f" times as often as {ref}")},'
                        f'{_q(f"; {name} goes bad less often than {ref}, ")}&TEXT({o},"0.00")&" times as often")')
                pieces.append(f'IF({live.sig(p)},{said}&{rng},"")')
            h = _helper(ws, r, "&".join(pieces) if pieces else '""')
            tail = ", with the pockets held fixed." if which == "held" else "."
            f = (f'=IF({h}="",{_q(f"{lead_} no group differs from {ref} at ")}&TEXT(confidence,"0%")&'
                 f'{_q(" sure" + tail)},{_q(lead_ + " ")}&MID({h},3,2000)&{_q(tail)})')
            src = plain if which == "plain" else side
            r = _line(ws, r, "What it found", _empty(src, lead_) or f, chars=60 + 80 * (K - 1))
            helper_rows.append(r - 1)
        named = [(plain.fit, "nothing held fixed"), (side.fit, f"{held} held fixed")] if t.held else \
            [(side.fit, "the pockets held fixed")]
        for fit_, name_ in named:
            for k, why in fit_.not_estimable.items():
                r = _line(ws, r, None, f"{where}, {name_}, {t.groups[k]}: no odds ratio, because {why}.")
            if not fit_.settled:
                r = _line(ws, r, None, f"{where}, {name_}: the regression didn't settle on an answer, so its odds "
                                       f"ratios are not reliable.")
        r += 1
    return r


def _concentration(ws, t, r: int, helper_rows: list) -> int:
    """4e: how much of the holdout's losses sit in each group, on the holdout only."""
    K = len(t.groups)
    ref = t.groups[t.ref]
    hold = t.holdout
    _cell(ws, r, FIRST, "How much of the held-back loans' losses sit in each group?", bold=True, h="left", size=11)
    r += 1
    # the dollar columns only when the run has GCO: a test of a new variable needs none (Goal 2 item 2), and then
    # the table says what it does hold and nothing about dollars (the firm: "don't note what it does not include,
    # just note what it does")
    cols = [("Loans", "#,##0"), ("Share of loans", "0.0%"), ("Bad loans", "#,##0"), ("Share of bad loans", "0.0%")]
    if t.dollars:
        cols += [("GCO", "$#,##0"), ("Share of GCO", "0.0%")]
    cols += [("Bad rate", "0.00%"), ("Times the holdout's bad rate", '0.00"x"')]
    heads, fmts = [h for h, _ in cols], tuple(f for _, f in cols)
    at = {h: CONC_FIRST + j for j, h in enumerate(heads)}          # each column by its heading
    house.header(ws, r, FIRST, [f"Group of {t.column}", None, None, None] + heads, centre_from=2)
    ws.merge_cells(start_row=r, start_column=FIRST, end_row=r, end_column=FIRST + 1)
    _wrap(ws, r)
    r += 1
    conc = t.concentration()

    def keep(loans, flag, bad, capture, gco, gco_capture, rate, lift):
        return (loans, flag, bad, capture) + ((gco, gco_capture) if t.dollars else ()) + (rate, lift)

    lift_col = at["Times the holdout's bad rate"]
    crow = {}
    for k, name in enumerate(t.groups):
        x = conc[k]
        ws.merge_cells(start_row=r, start_column=FIRST, end_row=r, end_column=FIRST + 1)
        _cell(ws, r, FIRST, name + (" (reference)" if k == t.ref else ""), h="left")
        for j, (v, fm) in enumerate(zip(keep(x.loans, x.flag_rate, x.bad, x.capture, x.gco, x.gco_capture,
                                             x.bad_rate, x.lift), fmts)):
            _cell(ws, r, CONC_FIRST + j, v, fmt=fm)
        crow[k] = r
        _rule(ws, r)
        r += 1
    total_gco = math.fsum(g for g in hold.gco_of if g is not None)
    vals = keep(hold.n, 1.0 if hold.n else None, hold.n_bad, 1.0 if hold.n_bad else None, total_gco,
                1.0 if total_gco else None, hold.n_bad / hold.n if hold.n else None, 1.0 if hold.n else None)
    ws.merge_cells(start_row=r, start_column=FIRST, end_row=r, end_column=FIRST + 1)
    _cell(ws, r, FIRST, "All held-back loans in the test", bold=True, h="left")
    for j, (v, fm) in enumerate(zip(vals, fmts)):
        _cell(ws, r, CONC_FIRST + j, v, bold=True, fmt=fm)
    r += 2
    pieces = []
    for k, name in enumerate(t.groups):
        f = t.holdout.fit
        if k == t.ref or f.odds[k] is None:
            continue
        rr = crow[k]
        o, p = f"{live.num(f.odds[k])}", live.num(f.p[k]) if f.p[k] is not None else '""'
        share = lambda h: f'TEXT({_c(at[h])}{rr},"0.0%")'          # noqa: E731
        held = (f'{share("Share of loans")}&{_q(" of the loans, ")}&{share("Share of bad loans")}&'
                + (f'{_q(" of the bad loans and ")}&{share("Share of GCO")}&{_q(" of the GCO, at ")}' if t.dollars
                   else f'{_q(" of the bad loans, at ")}'))
        pieces.append(f'IF(AND({live.sig(p)},{o}>1),{_q(f"; {name} holds ")}&{held}&'
                      f'TEXT({_c(lift_col)}{rr},"0.00")&{_q(LIFT_TAIL)},"")')
    h = _helper(ws, r, "&".join(pieces) if pieces else '""')
    f = (f'=IF({h}="",{_q(f"On the holdout, no group goes bad significantly more often than {ref}, so none is singled out; every group is in the table.")},'
         f'{_q("On the holdout, ")}&MID({h},3,2000)&".")')
    r = _line(ws, r, "What it found", _empty(hold, "On the holdout,") or f, chars=40 + 125 * (K - 1))
    helper_rows.append(r - 1)
    if t.gco_unread:
        r = _line(ws, r, None, f"{t.gco_unread:,} holdout loans have no readable GCO and are left out of the GCO "
                               f"figures only.")
    return r + 1


CONC_FIRST = DATA                                          # the concentration table's first number column


def _wrap(ws, r: int) -> None:
    """A header row of the tests in full on two lines: their headings are longer than the table's columns."""
    for c in range(FIRST, LAST + 1):
        x = ws.cell(row=r, column=c)
        x.alignment = Alignment(horizontal=x.alignment.horizontal, vertical="center", wrap_text=True)
    ws.row_dimensions[r].height = 30


def _empty(side, lead: str) -> str | None:
    """What a range's plain line says when nothing on it can be tested; None when something can."""
    if side.association.pockets:
        return None
    if not side.n:
        return f"{lead} nothing to test: no loan in this test was made {side.range.text()}."
    return f"{lead} nothing to test: no pocket holds both a bad loan and a good one."


def _helper(ws, r: int, expr: str) -> str:
    c = ws.cell(row=r, column=HELPER, value=f"={expr}")
    c.alignment = Alignment(wrap_text=False)
    return f"${_c(HELPER)}${r}"


def _finish(ws, last_row: int, helper_rows=()) -> None:
    for c in (LINE_COL, HELPER):
        ws.column_dimensions[_c(c)].hidden = True
    ws.print_area = f"B1:{_c(LAST)}{last_row}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


# --------------------------------------------------------------------------
# Start here's "What the last Run found" for a test of a new variable (OC-42): it builds no pocket, so the block
# reads the confirmation. The Run's numbers go on the hidden _found sheet, one row per group; the tiles count them
# against significance_bar, so "significant" follows the confidence on Control as the tab's own words do.

FOUND_KIND = "confirm"
G_NAME, G_LOANS, G_BAD, G_RATE, G_ODDS, G_P, G_CAPTURE, G_REF = range(2, 10)     # _found's columns B to I


def write_found(ws, res) -> None:
    """What this test found, on _found (ws), under the stamp."""
    from . import confirmatory
    h = confirmatory.headline(res)
    ws.append(["kind", FOUND_KIND])
    if h.get("problem"):
        ws.append(["problem", h["problem"]])
        return
    ws.append(["column", h["column"]])
    ws.append(["reference", h["reference"]])
    ws.append(["loans", f"{h['development']:,} on development, {h['holdout']:,} on the holdout"])
    dev = h["deviations"]
    ws.append(["follows", "Couldn't be compared" if dev is None else "Yes" if not dev
               else f"No: differs in {dev} place{'s' if dev != 1 else ''}"])
    for g in confirmatory.groups_found(res):
        ws.append(["group", g["group"], g["loans"], g["bad"], g["bad_rate"], g["odds"], g["p"], g["capture"],
                   "yes" if g["ref"] else None])


def found_block(ws, wb, r: int, value_of) -> int:
    """Four tiles and one row per group, on the holdout. value_of(key) reads _found. Returns the next free row."""
    from . import house
    from .book import FOUND
    note = Font(name="Calibri", size=10, color=SLATE)
    problem = value_of("problem")
    if problem:
        ws.cell(row=r + 1, column=2, value=f"The confirmatory test couldn't be run: {problem}. Record says why.").font \
            = note
        return r + 3
    ref = value_of("reference")
    F = lambda c: f"'{FOUND}'!${_c(c)}:${_c(c)}"                           # noqa: E731
    worse = f'COUNTIFS({F(1)},"group",{F(G_ODDS)},">1",{F(G_P)},"<"&{live.BAR})'
    groups = sum(1 for row in wb[FOUND].iter_rows(min_row=1, max_col=1, values_only=True) if row[0] == "group")
    tiles = [(f"Groups worse than {ref}, on the holdout", f'=IFERROR({worse}&" of {groups - 1}","")', None),
             ("Their share of the holdout's bad loans",
              f'=IFERROR(SUMIFS({F(G_CAPTURE)},{F(1)},"group",{F(G_ODDS)},">1",{F(G_P)},"<"&{live.BAR}),"")',
              "0%"),
             ("Loans tested", value_of("loans"), None),
             ("Follows the pre-spec", value_of("follows"), None)]
    for i, (label, f, fmt) in enumerate(tiles):
        house.tile(ws, r + 1, 2 + 2 * i, 3 + 2 * i, label, f, fmt)
    t = r + 4
    house.header(ws, t, 2, [f"Group of {value_of('column')}", "Loans", "Bad rate", f"× {ref}'s odds", "p-value",
                            "Significant?", "Share of bad loans", None], centre_from=2)
    rows = [row for row in wb[FOUND].iter_rows(min_row=1) if row[0].value == "group"]
    for i, row in enumerate(rows, start=1):
        rr, src = t + i, row[0].row
        P = lambda c: f"'{FOUND}'!${_c(c)}${src}"                          # noqa: E731
        ref_row = row[G_REF - 1].value == "yes"
        vals = [f"={P(G_NAME)}" + ('&" (reference)"' if ref_row else ""), f"={P(G_LOANS)}",
                f'=IF({P(G_RATE)}="","",{P(G_RATE)})', f'=IF({P(G_ODDS)}="","none",{P(G_ODDS)})',
                f'=IF({P(G_P)}="","",{P(G_P)})',
                None if ref_row else f'=IF({live.sig(P(G_P))},IF({P(G_ODDS)}>1,"Yes, worse","Yes, better"),"No")',
                f"={P(G_CAPTURE)}"]
        for j, v in enumerate(vals):
            c = ws.cell(row=rr, column=2 + j, value=v)
            c.font = Font(name="Calibri", size=10, color=house.INK_TEXT)
            c.alignment = Alignment(horizontal="left" if j == 0 else "center", vertical="center")
        for j, fmt in ((3, "#,##0"), (4, "0.00%"), (5, '0.00"×"'), (6, P_FMT), (8, "0%")):
            ws.cell(row=rr, column=j).number_format = fmt
        ws.row_dimensions[rr].height = 18
    last = t + max(1, len(rows))
    ws.conditional_formatting.add(f"G{t + 1}:G{last}", FormulaRule(
        formula=[f'G{t + 1}="Yes, worse"'], font=Font(bold=True, color=house.CRIMSON),
        fill=PatternFill("solid", fgColor=house.ALERT_FG, bgColor=house.ALERT_FG)))
    link = ws.cell(row=last + 1, column=2, value="Found beside confirmed, with and without the columns held fixed, "
                                                 "and how it's worked out: the New variables tab.")
    link.hyperlink = f"#'{SHEET}'!A1"
    link.font = Font(name="Calibri", size=10, color=house.KEY_RED, underline="single")
    return last + 3
