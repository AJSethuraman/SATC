"""The Confirmatory test tab (capabilities 4b and 4e): the pre-spec's column in its own groups, each against
the reference group inside the pockets, on the development range and on the holdout side by side, then how
concentrated the bad loans are on the holdout. The numbers come from confirmatory.run_test; this only lays
them out.

Live (OC-40): every "significant" on the tab compares a p-value with the one rounded bar, significance_bar, and
every range is worked out at the confidence on Control, as the Split tab's are. The p-values, odds ratios and
statistics are the Run's: none depends on the confidence level.

Each section: a table, one plain line per range saying what it found (a formula, so it follows the confidence
level), and the method in plain words. Standard terms are shown and explained once."""

from __future__ import annotations

import math

from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill

from . import kgroups, live, stats

SHEET = "Confirmatory test"
INK, SLATE, PAPER = "16130F", "57534B", "FFFFFF"          # the workbook's colours (book.py)
WORSE_FILL, BETTER_FILL, HEAD_FILL = "F7DEDE", "E2EFDA", "E4DFD5"
FIRST, LAST = 2, 14                                        # columns B to N
HELPER = 26                                                # column Z, hidden: the pieces the plain lines join
Z = "NORMSINV(1-(1-confidence)/2)"                         # the live z, as the Split tab writes it
P_FMT = '[<0.0001]"under 0.01%";[<0.01]0.00%;0.0%'         # book.P_FMT
LIFT_TAIL = " times the holdout's bad rate"
WIDE = 140                                                 # about how many characters fit across C to N


def _c(n: int) -> str:
    return live.col(n)


def _height(chars: int, per_line: int = WIDE) -> float:
    return 15.0 * max(1, math.ceil(chars / per_line)) + 3


def _heading(ws, r: int, text: str, size: int = 13) -> None:
    ws.cell(row=r, column=FIRST, value=text).font = Font(name="Calibri", bold=True, size=size)


def _head(ws, r: int, c: int, text, span: int = 1, fill: str = INK, color: str = PAPER) -> None:
    if span > 1:
        ws.merge_cells(start_row=r, start_column=c, end_row=r, end_column=c + span - 1)
    for j in range(c, c + span):
        ws.cell(row=r, column=j).fill = PatternFill("solid", fgColor=fill)
    cell = ws.cell(row=r, column=c, value=text)
    cell.font = Font(name="Calibri", bold=True, color=color)
    cell.alignment = Alignment(wrap_text=True, vertical="top", horizontal="left" if c == FIRST else "center")


def _line(ws, r: int, label: str | None, text, chars: int | None = None, bold_label: bool = True,
          italic: bool = False) -> int:
    """A label in B and words across C to N. Returns the next row."""
    if label is not None:
        c = ws.cell(row=r, column=FIRST, value=label)
        c.font = Font(name="Calibri", bold=bold_label)
        c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=r, start_column=FIRST + 1, end_row=r, end_column=LAST)
    c = ws.cell(row=r, column=FIRST + 1, value=text)
    c.alignment = Alignment(wrap_text=True, vertical="top")
    c.font = Font(name="Calibri", italic=italic, color=SLATE if italic else INK)
    n = chars if chars is not None else len(str(text))
    ws.row_dimensions[r].height = max(_height(n), _height(len(label or ""), 30))
    return r + 1


def _sig_word(ref: str) -> str:
    return f'IF({ref}="","",IF({live.sig(ref)},"significant","not significant"))'


def _q(s: str) -> str:
    return live.q(s)


def write(wb, res) -> None:
    st = getattr(res, "prespec", None)
    t = getattr(st, "test", None) if st is not None else None
    if t is None:
        return
    from . import book as bk                              # the workbook's own helpers; book imports this module
    ws = wb.create_sheet(SHEET)
    live.ensure(wb, res)
    last = _c(LAST)
    bk._title(ws, "Confirmatory test",
              f"Does {t.column} tell good loans from bad, comparing loans only inside their own pocket? Tested "
              f"once on the loans the groups were chosen on, and once on the loans kept back. The pre-spec "
              f"({st.name}) set every choice here.", f"B:{last}")
    bk._in_use(ws, "Every \"significant\" and every range here follows the confidence level on Control. The "
                   "odds ratios, statistics and p-values are as of the last Run.", last, 30)
    r = 5
    if t.problem:
        _line(ws, r, "Not run", f"The confirmatory test couldn't be run: {t.problem}.")
        _finish(ws, bk, r + 1)
        return
    K = len(t.groups)
    ref = t.groups[t.ref]
    dev, hold = t.development, t.holdout
    sides = ((dev, "On development,", FIRST + 1), (hold, "On the holdout,", FIRST + 7))
    strata = " and ".join(t.strata) if t.strata else "nothing (the whole book is one pocket)"
    helper_rows: list[int] = []

    # ---------------------------------------------------------------- what was tested
    _heading(ws, r, "What was tested")
    r += 1
    r = _line(ws, r, "The column", f"{t.column}, in {K} groups: {'; '.join(t.groups)}. The groups are the "
                                   f"pre-spec's.")
    r = _line(ws, r, "Compared with", f"{ref}, the pre-spec's reference group. Every other group is compared "
                                      f"with it.")
    pk = max(len(dev.pockets), len(hold.pockets))
    r = _line(ws, r, "Pockets", f"Cut by {strata}, at the band edges on Check. A loan is only ever compared with loans "
                                f"in its own pocket, so a difference in the pocket mix can't pass for a difference "
                                f"in {t.column}. Up to {pk:,} pockets hold a loan.")
    for side, what in ((dev, "where the groups were chosen"), (hold, "kept back: the test that counts")):
        rate = side.n_bad / side.n if side.n else None
        r = _line(ws, r, side.name.capitalize(),
                  f"Loans made {side.range.text()}: {side.n:,} loans, {side.n_bad:,} bad"
                  + (f" ({rate:.2%})" if rate is not None else "") + f"; {what}.")
    if t.left_out:
        words = "; ".join(f"{v:,} {k}" if k.startswith("made") else f"{v:,} with {k}" for k, v in t.left_out.items())
        r = _line(ws, r, "Left out of this test", f"{words}. Check counts every loan.")
    r += 1

    # ---------------------------------------------------------------- 1. does the column matter (B3, B4, B5 block)
    _heading(ws, r, f"1. Does {t.column} matter?")
    r += 1
    _head(ws, r, FIRST, None)
    for side, _, c in sides:
        _head(ws, r, c, f"{side.name.capitalize()}: {side.range.text()}", 6)
    r += 1
    _head(ws, r, FIRST, "Test", fill=HEAD_FILL, color=INK)
    for _, _, c in sides:
        for j, h in enumerate(("Statistic", "Degrees of freedom", "p-value")):
            _head(ws, r, c + j, h, fill=HEAD_FILL, color=INK)
        _head(ws, r, c + 3, "Reading", 3, fill=HEAD_FILL, color=INK)
    ws.row_dimensions[r].height = 44
    r += 1
    tests = (("Any difference across the groups (general)", lambda s: (s.association.general, s.association.df,
                                                                       s.association.p_general)),
             ("A steady climb or fall (trend)", lambda s: (s.association.trend, 1 if s.association.trend is not None
                                                           else None, s.association.p_trend)),
             ("Any difference, from the regression (block test)", lambda s: (s.fit.block, s.fit.df, s.fit.p_block)))
    pcell: dict = {}
    for i, (label, get) in enumerate(tests):
        ws.cell(row=r, column=FIRST, value=label).alignment = Alignment(wrap_text=True, vertical="top")
        for side, _, c in sides:
            stat, df, p = get(side)
            ws.cell(row=r, column=c, value=None if stat is None else round(stat, 6)).number_format = "0.00"
            ws.cell(row=r, column=c + 1, value=df).number_format = "0"
            ws.cell(row=r, column=c + 2, value=p).number_format = P_FMT
            ref_p = f"{_c(c + 2)}{r}"
            ws.merge_cells(start_row=r, start_column=c + 3, end_row=r, end_column=c + 5)
            ws.cell(row=r, column=c + 3, value=f"={_sig_word(ref_p)}")
            for j in range(c, c + 6):
                ws.cell(row=r, column=j).alignment = Alignment(horizontal="center", vertical="top")
            pcell[(side.name, i)] = ref_p
        ws.row_dimensions[r].height = 30
        r += 1
    r += 1
    for side, lead, _ in sides:
        a = side.association
        g, tr = pcell[(side.name, 0)], pcell[(side.name, 1)]
        way = "rises" if a.direction > 0 else "falls"
        f = (f'=IF(AND({live.sig(g)},{live.sig(tr)}),{_q(f"{lead} the bad rate differs across the groups, and {way} steadily as {t.column} rises.")},'
             f'IF({live.sig(g)},{_q(f"{lead} the bad rate differs across the groups, but not in one direction: higher in some groups, lower in others.")},'
             f'IF({live.sig(tr)},{_q(f"{lead} the groups taken all at once do not differ significantly, but the bad rate {way} steadily as {t.column} rises (the trend test).")},'
             f'{_q(f"{lead} no difference across the groups shows at ")}&TEXT(confidence,"0%")&{_q(" sure. That is not proof there is none.")})))')
        r = _line(ws, r, "What it found" if side is dev else None, _empty(side, lead) or f, chars=140)
    r += 1
    r = _line(ws, r, "How it's worked out",
              f"Every loan is compared only with loans in its own pocket. The general test (the Mantel-Haenszel "
              f"test for {K} groups: a standard way to add pockets up without mixing their loans) asks whether the "
              f"bad rate differs across the groups in any shape. It is read against a chi-square on "
              f"{K - 1} degrees of freedom, one fewer than the groups. The trend test gives the groups the scores "
              f"1 to {K}, lowest first, and asks whether the bad rate climbs or falls steadily with them, on 1 "
              f"degree of freedom. Read them together: a difference with no trend is a U or a hump, which a "
              f"straight-line test would call nothing.", italic=True)
    r = _line(ws, r, None, live.text("The p-value is the chance of a difference at least this big if the groups "
                                     "were no different. Below ", ('TEXT(significance_bar,"0%")',),
                                     " is significant. Every pocket counts, however small: fewest loans and "
                                     "fewest losses on Control decide only whether one pocket can be read on its "
                                     "own. A pocket where no loan, or every loan, went bad says nothing about the "
                                     "groups and adds nothing."), chars=330, italic=True)
    r += 1

    # ---------------------------------------------------------------- 2. how much worse is each group (B5)
    _heading(ws, r, f"2. How much more often does each group go bad than {ref}?")
    r += 1
    _head(ws, r, FIRST, None)
    for side, _, c in sides:
        _head(ws, r, c, f"{side.name.capitalize()}: {side.range.text()}", 6)
    r += 1
    _head(ws, r, FIRST, f"Group of {t.column}", fill=HEAD_FILL, color=INK)
    for _, _, c in sides:
        for j, h in enumerate(("Loans", "Bad loans", "Bad rate", "Odds ratio", live.text("Range (",
                                                                                         ('TEXT(confidence,"0%")',),
                                                                                         " sure)"), "p-value")):
            _head(ws, r, c + j, h, fill=HEAD_FILL, color=INK)
    ws.row_dimensions[r].height = 32
    r += 1
    first_group = r
    cells: dict = {}
    for k, name in enumerate(t.groups):
        ws.cell(row=r, column=FIRST, value=name + (" (reference)" if k == t.ref else ""))
        for side, _, c in sides:
            f = side.fit
            ws.cell(row=r, column=c, value=side.loans[k]).number_format = "#,##0"
            ws.cell(row=r, column=c + 1, value=side.bad[k]).number_format = "#,##0"
            ws.cell(row=r, column=c + 2, value=side.bad[k] / side.loans[k] if side.loans[k] else None
                    ).number_format = "0.00%"
            if k == t.ref:
                ws.cell(row=r, column=c + 3, value="1.00")
            elif f.odds[k] is None:
                ws.cell(row=r, column=c + 3, value="none")
            else:
                ws.cell(row=r, column=c + 3, value=round(f.odds[k], 10)).number_format = '0.00"x"'
                b, se = live.num(f.beta[k]), live.num(f.se[k])
                ws.cell(row=r, column=c + 4, value=(f'=TEXT(EXP({b}-{Z}*{se}),"0.00")&"x to "&'
                                                     f'TEXT(EXP({b}+{Z}*{se}),"0.00")&"x"'))
                ws.cell(row=r, column=c + 5, value=f.p[k]).number_format = P_FMT
                cells[(side.name, k)] = (f"{_c(c + 3)}{r}", f"{_c(c + 5)}{r}", b, se)
            for j in range(c, c + 6):
                ws.cell(row=r, column=j).alignment = Alignment(horizontal="center", vertical="top")
        r += 1
    for side, _, c in sides:
        # a significant odds ratio shaded, red above 1 and green below, against the one bar (OC-40)
        o, p = f"${_c(c + 3)}{first_group}", f"${_c(c + 5)}{first_group}"
        for fill, cmp_ in ((WORSE_FILL, ">1"), (BETTER_FILL, "<1")):
            ws.conditional_formatting.add(f"{_c(c + 3)}{first_group}:{_c(c + 5)}{r - 1}", FormulaRule(
                formula=[f"AND(ISNUMBER({o}),ISNUMBER({p}),{p}<{live.BAR},{o}{cmp_})"],
                fill=PatternFill("solid", fgColor=fill, bgColor=fill)))
    r += 1
    for side, lead, _ in sides:
        pieces = []
        for k, name in enumerate(t.groups):
            got = cells.get((side.name, k))
            if got is None:
                continue
            o, p, b, se = got
            rng = (f'" ("&TEXT(EXP({b}-{Z}*{se}),"0.00")&"x to "&TEXT(EXP({b}+{Z}*{se}),"0.00")&"x)"')
            said = (f'IF({o}>=1,{_q(f"; {name} goes bad ")}&TEXT({o},"0.00")&{_q(f" times as often as {ref}")},'
                    f'{_q(f"; {name} goes bad less often than {ref}, ")}&TEXT({o},"0.00")&" times as often")')
            pieces.append(f'IF({live.sig(p)},{said}&{rng},"")')
        h = _helper(ws, r, "&".join(pieces) if pieces else '""')
        f = (f'=IF({h}="",{_q(f"{lead} no group differs from {ref} at ")}&TEXT(confidence,"0%")&'
             f'{_q(" sure, with the pockets held fixed.")},{_q(lead + " ")}&MID({h},3,2000)&'
             f'{_q(", with the pockets held fixed.")})')
        r = _line(ws, r, "What it found" if side is dev else None, _empty(side, lead) or f, chars=60 + 80 * (K - 1))
        helper_rows.append(r - 1)
    r += 1
    methods = {kgroups.CONDITIONAL: "conditional logistic regression, in every pocket",
               kgroups.UNCONDITIONAL: "logistic regression with a constant for each pocket"}
    gaps = [s.mh_gap for s in (dev, hold) if s.mh_gap is not None]
    r = _line(ws, r, "How it's worked out",
              f"Odds are bad loans divided by good ones. An odds ratio is a group's odds divided by {ref}'s: 2.00x "
              f"means twice the odds of going bad. While few loans go bad it is close to how many times as often "
              f"they do. The odds ratios come from {methods[t.method]}: a regression that compares the groups "
              f"inside each pocket and takes each pocket's own count of bad loans as given, instead of estimating "
              f"a rate for every pocket, which biases the answer when pockets are thin.", italic=True)
    r = _line(ws, r, None, live.text(
        "The range is where the true odds ratio sits, ", ('TEXT(confidence,"0%")',), " sure. The p-value asks "
        "whether it could be 1: no different from " + ref + ". The block test asks whether the groups together "
        "add anything (a likelihood ratio test, on " + f"{K - 1}" + " degrees of freedom)."
        + (f" As a check, each odds ratio was worked out a second way, pair by pair with Mantel-Haenszel: the "
           f"largest gap between the two is {max(gaps):.1%}." if gaps else "")), chars=380, italic=True)
    for side in (dev, hold):
        for k, why in side.fit.not_estimable.items():
            r = _line(ws, r, None, f"{side.name.capitalize()}, {t.groups[k]}: no odds ratio, because {why}.",
                      italic=True)
        if not side.fit.settled:
            r = _line(ws, r, None, f"{side.name.capitalize()}: the regression didn't settle on an answer, so its "
                                   f"odds ratios are not reliable.", italic=True)
    r += 1

    # ---------------------------------------------------------------- 3. concentration on the holdout (B6)
    _heading(ws, r, "3. How much of the holdout's losses sit in each group?")
    r += 1
    # the dollar columns only when the run has GCO: a test of a new variable needs none (Goal 2 item 2), and then
    # the table says what it does hold and nothing about dollars (the firm: "don't note what it does not include,
    # just note what it does")
    cols = [("Loans", "#,##0"), ("Share of loans", "0.0%"), ("Bad loans", "#,##0"), ("Share of bad loans", "0.0%")]
    if t.dollars:
        cols += [("GCO", "$#,##0"), ("Share of GCO", "0.0%")]
    cols += [("Bad rate", "0.00%"), ("Times the holdout's bad rate", '0.00"x"')]
    heads, fmts = [h for h, _ in cols], tuple(f for _, f in cols)
    at = {h: FIRST + 1 + j for j, h in enumerate(heads)}          # each column by its heading
    _head(ws, r, FIRST, f"Group of {t.column}")
    for j, h in enumerate(heads):
        _head(ws, r, FIRST + 1 + j, h)
    ws.row_dimensions[r].height = 58
    r += 1
    conc = t.concentration()

    def keep(loans, flag, bad, capture, gco, gco_capture, rate, lift):
        return (loans, flag, bad, capture) + ((gco, gco_capture) if t.dollars else ()) + (rate, lift)

    lift_col = at["Times the holdout's bad rate"]
    crow = {}
    for k, name in enumerate(t.groups):
        x = conc[k]
        ws.cell(row=r, column=FIRST, value=name + (" (reference)" if k == t.ref else ""))
        for j, (v, fm) in enumerate(zip(keep(x.loans, x.flag_rate, x.bad, x.capture, x.gco, x.gco_capture,
                                             x.bad_rate, x.lift), fmts)):
            c = ws.cell(row=r, column=FIRST + 1 + j, value=v)
            c.number_format = fm
            c.alignment = Alignment(horizontal="center")
        crow[k] = r
        r += 1
    total_gco = math.fsum(g for g in hold.gco_of if g is not None)
    vals = ("All holdout loans in the test",) + keep(hold.n, 1.0 if hold.n else None, hold.n_bad,
                                                     1.0 if hold.n_bad else None, total_gco,
                                                     1.0 if total_gco else None,
                                                     hold.n_bad / hold.n if hold.n else None, 1.0 if hold.n else None)
    for j, (v, fm) in enumerate(zip(vals, ("",) + fmts)):
        c = ws.cell(row=r, column=FIRST + j, value=v)
        c.font = Font(name="Calibri", bold=True)
        if j:
            c.number_format = fm
            c.alignment = Alignment(horizontal="center")
    r += 2
    pieces = []
    for k, name in enumerate(t.groups):
        got = cells.get((hold.name, k))
        if got is None:
            continue
        o, p, _, _ = got
        rr = crow[k]
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
    r += 1
    gco_note = (f" {t.gco_unread:,} holdout loans have no readable GCO and are left out of the GCO figures only."
                if t.gco_unread else "")
    what = ("Share of bad loans and of GCO: how much of the holdout's bad loans and GCO dollars sit in the group."
            if t.dollars else "Share of bad loans: how much of the holdout's bad loans sit in the group.")
    r = _line(ws, r, "How it's worked out",
              f"On the holdout only, and on the book as a whole, not pocket by pocket. Share of loans: the group's "
              f"loans divided by all holdout loans in this test. {what} Times the holdout's bad rate (the lift): the "
              f"group's bad rate divided by the rate of every holdout loan here.{gco_note} No group on one column "
              f"will hold most of the losses, because most losses sit in ordinary loans, which are most of the "
              f"book. So the finding is the lift{' and the dollars' if t.dollars else ''}, never the share of all "
              f"losses.", italic=True)
    r += 1

    # ---------------------------------------------------------------- choices for the firm
    _heading(ws, r, "Choices made here that no ruling settles yet")
    r += 1
    for text in (
            f"The trend test scores the groups 1 to {K}, evenly spaced, rather than by where their numbers sit.",
            "Conditional logistic regression is used in every pocket, whatever its size. The unconditional fit the "
            "scope allows for pockets over a few thousand loans isn't used: the conditional one is exact and quick "
            "at any size.",
            "The ranges are the usual kind for an odds ratio: the log odds ratio plus and minus the multiple of its "
            "standard error that the confidence level sets.",
            f"A loan with no readable value in a column the pockets are cut by sits in a pocket of its own, as on "
            f"the grids.",
            "A group with no bad loan, or only bad loans, in the pockets that say something has no odds ratio. "
            "The others are fitted as if its loans weren't there, which is where the regression heads anyway."):
        r = _line(ws, r, None, text, italic=True)
    _finish(ws, bk, r, helper_rows)


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


def _finish(ws, bk, last_row: int, helper_rows=()) -> None:
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions[_c(FIRST)].width = 34
    for side in (0, 6):
        for j, w in enumerate((9, 9, 12, 10, 17, 12)):
            ws.column_dimensions[_c(FIRST + 1 + side + j)].width = w
    ws.column_dimensions[_c(HELPER)].hidden = True
    ws.print_area = f"B1:{_c(LAST)}{last_row}"
    bk._fit(ws)


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
        ws.cell(row=r + 1, column=2, value=f"The confirmatory test couldn't be run: {problem}. Check says why.").font \
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
    link = ws.cell(row=last + 1, column=2, value="Development beside the holdout, and how it's worked out: the "
                                                 "Confirmatory test tab.")
    link.hyperlink = f"#'{SHEET}'!A1"
    link.font = Font(name="Calibri", size=10, color=house.KEY_RED, underline="single")
    return last + 3
