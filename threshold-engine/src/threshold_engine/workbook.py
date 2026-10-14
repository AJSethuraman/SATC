"""One run, one workbook: every product's facts, evidence, backtest and live cutoffs.

Python does the statistics once -- spells, robust z-scores, scenarios, recency,
the backtest -- and writes their results as values. The cutoffs are Excel
formulas over the data, driven by the red Assess tab, so the bank's
judgements are made in the workbook and the thresholds move as they are made:

    Assess (red)    pick a product and see where its history falls; pick the
                    periods to leave out from lists of real quarters, and set
                    the scale's three distances and the on-the-line rule
    Thresholds      median and worst of the periods kept, the four cutoffs,
                    the latest value's score and rating -- all live
    Chart           any combination of products on one scale, with one
                    product's cutoffs drawn, switched on the tab itself
    Evidence        spells, robust z, scenarios, recency (values)
    Backtest        how predictive the scale would have been (values)
    Data            every series on one quarterly calendar, and the periods kept
    Run             what went in: files, fingerprints, rows, settings

Every product must share one measure (name, unit, direction); a credit score
and a loss rate do not belong on one scale or one chart.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import math
from pathlib import Path
from typing import Sequence, Tuple

from openpyxl import Workbook
from openpyxl.chart import AreaChart, BarChart, LineChart, Reference
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation

from . import assess_tab as AT
from . import keybank_style as K
from .backtest import backtest
from . import VERSION
from .evidence import evidence
from .glossary import TERMS
from .scale import scale as _scale
from .series import CORE_NOTES, LABEL_RULE, check, label_ok, read_csv, read_notes, smooth

RATINGS = ("Low", "Moderate-Low", "Moderate", "Moderate-High", "High")
INPUT = PatternFill("solid", fgColor="FFF2CC")
# A conditional format's fill is read from its background colour, so both
# are set (with fgColor alone Excel drew the highlighted row white).
PICKED = PatternFill("solid", fgColor="F6D9A8", bgColor="F6D9A8")
# The Assess tab's inputs, laid out by assess_tab (Claude Design's hand-off,
# 13 Oct 2026): Your settings N:R from SET_TOP, one row per product; Periods
# left out N:Q below it, LO_ROWS rows; hidden helpers from column Z (HC).
SET_TOP, LO_ROWS, HC = AT.SET_TOP, AT.LO_ROWS, AT.HC
NOTE = Font(name="Arial", size=9, italic=True, color=K.SLATE)


def _wrap(ws, row, height=34):
    """Header labels wrap in their column instead of being cut off."""
    for cell in ws[row]:
        if cell.value is not None:
            cell.alignment = Alignment(wrap_text=True, vertical="center",
                                       horizontal=cell.alignment.horizontal or "left")
    ws.row_dimensions[row].height = height


def _axis_floor(loaded, direction, halfwidth, low_step, high_z):
    """A round number under every product's lowest value and starting line,
    and under the strip that marks quarters left out, or None if that is not
    above zero (then the axis starts at zero anyway). Rounded down to a half
    of the range's order of magnitude."""
    lows, highs = [], []
    for s in loaded:
        vals = [p.value for p in s["points"]]
        ref = _scale(vals, direction, halfwidth, low_step, high_z, False)
        both = vals + list(ref["bounds"] or [])
        lows.append(min(both))
        highs.append(max(both))
    lo, hi = min(lows), max(highs)
    # As the sheet works them out: the floor, the top, and the strip under the
    # floor for quarters left out, which must stay on the chart.
    floor = lo - 0.08 * (hi - lo)
    top = hi + 0.08 * (hi - floor)
    target = floor - 0.06 * (top - floor)
    if hi <= lo or target <= 0:
        return None
    unit = 10 ** math.floor(math.log10(hi - lo)) / 2
    return math.floor(target / unit) * unit


def assess_layout(n: int) -> dict:
    """Where things sit on Assess for n products: one place for the builder,
    the tests and the walkthrough (see assess_tab.layout)."""
    return AT.layout(n)


def quarter(date: str) -> str:
    """'2010-04-01' and '2010-06-30' are both 2010Q2."""
    return "%sQ%d" % (date[:4], (int(date[5:7]) - 1) // 3 + 1)


#: One reader for every front door (``series.read_csv``).
read_series = read_csv


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(out: Path, series: Sequence[Tuple[str, Path]], name: str, unit: str,
          direction: str, frequency: str, smoothing: int, floor_at_zero: bool,
          moderate_halfwidth: float, low_step: float, high_z: float, on_the_line: str,
          half_lives: Sequence[float],
          percentiles: Sequence[float], horizon: int, min_history: int) -> dict:
    if frequency != "quarterly":
        raise ValueError("the workbook's calendar is quarterly; monthly series are not built yet")
    out = Path(out)
    if out.suffix.lower() != ".xlsx":
        raise ValueError("the workbook must be written to a .xlsx file, not %s" % out.name)
    for lbl, path in series:
        # Saving over an input would destroy the data it was built from.
        if out.resolve() == Path(path).resolve():
            raise ValueError("the workbook would be written over %s, the series for %s; write it elsewhere"
                             % (Path(path).name, lbl))
    if not all(math.isfinite(v) for v in
               (moderate_halfwidth, low_step, high_z, *half_lives, *percentiles)):
        raise ValueError("every setting must be a number, not nan or infinity")
    if moderate_halfwidth < 0 or low_step <= moderate_halfwidth or high_z <= 0:
        raise ValueError("need 0 <= moderate_halfwidth < low_step, and high_z above 0")
    if on_the_line not in ("worse", "better"):
        raise ValueError("on_the_line must be 'worse' or 'better'")
    for lbl, _ in series:
        if not lbl.strip():
            raise ValueError("every series needs a product label")
        if not label_ok(lbl):
            raise ValueError("the label %r can't be used: %s" % (lbl, LABEL_RULE))
    if len({lbl.casefold() for lbl, _ in series}) != len(series):
        raise ValueError("two series share a label (Excel ignores capitals, so 'Cards' and 'cards' are one)")
    higher = direction == "higher_is_worse"

    loaded = []
    for label, path in series:
        pts = read_series(Path(path))
        ev = evidence(pts, label, unit, direction, frequency, smoothing, None, floor_at_zero)
        bt = backtest(pts, label, unit, direction, frequency, smoothing, percentiles,
                      horizon, min_history, floor_at_zero, half_lives)
        # Smoothing comes before anything else, as the window says: the live
        # lines, the latest value and the score are built from the series the
        # evidence and backtest use, never from the raw file beside it.
        used = smooth(check(pts, frequency), smoothing)
        by_q = {quarter(p.date): p.value for p in used}
        if len(by_q) != len(used):
            raise ValueError("%s has two observations in one quarter" % label)
        loaded.append(dict(label=label, path=Path(path), raw=pts, points=used, ev=ev, bt=bt, by_q=by_q))
    grid = sorted(set().union(*(s["by_q"] for s in loaded)))
    # Decimals to suit the values: 3.978 (a rate) keeps three, 714.5 (a score)
    # one; three decimals on a credit score read as false precision.
    biggest = max(abs(p.value) for s in loaded for p in s["points"])
    NF = "0.0" if biggest >= 100 else "0.00" if biggest >= 10 else "0.000"
    n, first, last = len(loaded), 2, len(grid) + 1

    wb = Workbook()
    asx = wb.active
    asx.title = "Assess"                 # first, and where it opens: where the bank works
    th, ch, evs, bts, srcs, gl, da, run = (wb.create_sheet(t) for t in
                                           ("Thresholds", "Chart", "Evidence", "Backtest", "Sources", "Glossary",
                                            "Data", "Run"))
    for ws in (th, asx, ch, evs, bts, srcs, gl, run):
        K.hide_gridlines(ws)
    lay = assess_layout(n)
    LO_TOP, lo_end, set_end = lay["lo_top"], lay["lo_end"], lay["set_end"]
    # The leave-out list, as ranges: the product typed, the calendar positions
    # of From and To (hidden helpers), whether the row is whole, and whether it
    # is in use at all.
    lo_rng = lambda c_: "Assess!${c}${a}:${c}${b}".format(c=c_, a=LO_TOP, b=lo_end)     # noqa: E731
    LO_PROD, LO_FROM, LO_TO, LO_OK, LO_USED = (lo_rng(c_) for c_ in ("N",) + tuple(L(HC + 14 + i) for i in range(4)))

    # ---- Data: one calendar, raw values, and the values each product keeps ----
    da.append(["Quarter"] + [s["label"] for s in loaded] + ["%s, kept" % s["label"] for s in loaded]
              + ["%s, change over 4 quarters kept" % s["label"] for s in loaded]
              + ["%s, distance from the median change" % s["label"] for s in loaded]
              + ["%s, distance from the median kept" % s["label"] for s in loaded]
              + ["%s, change over 4 quarters, every quarter" % s["label"] for s in loaded]
              + ["%s, distance from the median change, every quarter" % s["label"] for s in loaded]
              + ["%s, distance from the median, every quarter" % s["label"] for s in loaded])
    srow = {s["label"]: SET_TOP + i for i, s in enumerate(loaded)}      # Your settings row per product
    for r, q in enumerate(grid, start=2):
        da.cell(r, 1, q)
        for k, s in enumerate(loaded):
            raw = L(2 + k)
            if q in s["by_q"]:
                da.cell(r, 2 + k, s["by_q"][q])
            # Left out when a whole row of the list names this product and its
            # From..To takes in this quarter's place on the calendar. An exact
            # match on the product (SUMPRODUCT, not COUNTIFS, which would read
            # * and ? in a label as wildcards).
            left_out = ('SUMPRODUCT(({p}=Thresholds!$A${t})*({f}<={pos})*({to}>={pos})*({ok}=1))>0'
                        .format(p=LO_PROD, f=LO_FROM, to=LO_TO, ok=LO_OK, t=5 + k, pos=r - 1))
            da.cell(r, 2 + n + k,
                    '=IF({raw}{r}="","",IF({lo},"",{raw}{r}))'.format(raw=raw, r=r, lo=left_out))
            kc = L(2 + n + k)
            if r >= first + 4:
                da.cell(r, 2 + 2 * n + k, '=IF(AND(ISNUMBER({c}{r}),ISNUMBER({c}{p})),{c}{r}-{c}{p},"")'
                        .format(c=kc, r=r, p=r - 4))
            else:
                da.cell(r, 2 + 2 * n + k, "")
            yc = L(2 + 2 * n + k)
            da.cell(r, 2 + 3 * n + k, '=IF({y}{r}="","",ABS({y}{r}-Thresholds!$O${tr}))'
                    .format(y=yc, r=r, tr=5 + k))
            da.cell(r, 2 + 4 * n + k, '=IF({c}{r}="","",ABS({c}{r}-Thresholds!$B${tr}))'
                    .format(c=kc, r=r, tr=5 + k))
            # The same three, with nothing left out: the Scenarios on Assess
            # set them beside the lines as the bank has them.
            if r >= first + 4:
                da.cell(r, 2 + 5 * n + k, '=IF(AND(ISNUMBER({c}{r}),ISNUMBER({c}{p})),{c}{r}-{c}{p},"")'
                        .format(c=raw, r=r, p=r - 4))
            ac = L(2 + 5 * n + k)
            da.cell(r, 2 + 6 * n + k, '=IF({a}{r}="","",ABS({a}{r}-Thresholds!$R${tr}))'.format(a=ac, r=r, tr=5 + k))
            da.cell(r, 2 + 7 * n + k, '=IF({c}{r}="","",ABS({c}{r}-Thresholds!$Q${tr}))'.format(c=raw, r=r, tr=5 + k))
    K.freeze_below(da, 1)

    # ---- Thresholds: live ----
    th.sheet_properties.tabColor = K.KEY_RED
    K.light_title(th, 1, 13, "%s · candidate thresholds" % name,
                  "Live: follows every choice on Assess. Candidates for the bank to accept, adjust or reject.")
    for c1, c2, lbl in ((2, 4, "What the lines rest on"), (5, 8, "Each rating begins at"), (9, 12, "Latest quarter"),
                        (13, 13, "Check")):
        th.cell(3, c1, lbl).font = Font(name="Arial", bold=True, size=9, color=K.INK)
        for c_ in range(c1, c2 + 1):
            th.cell(3, c_).border = Border(bottom=Side(style="thin", color=K.INK))
    th.row_dimensions[3].height = 15
    K.canvas_header(th, 4, ["Series", "Median kept", "Typical yearly move", "Worst kept", "2 Moderate-Low from",
                            "3 Moderate from", "4 Moderate-High from", "5 High from", "Latest quarter",
                            "Latest value", "Rating", "Rating name", "Check"], right_from=1,
                    fills=[None] * 4 + list(K.BANDS[1:]) + [None] * 5)
    sg = 1 if higher else -1
    fz = "TRUE" if floor_at_zero and higher else "FALSE"
    for k, s in enumerate(loaded):
        r = 5 + k
        sr = srow[s["label"]]
        col = lambda c_: "Data!$%s$%d:$%s$%d" % (L(c_), first, L(c_), last)        # noqa: E731
        kept, yoy, dev = col(2 + n + k), col(2 + 2 * n + k), col(2 + 3 * n + k)
        levdev = col(2 + 4 * n + k)
        th.cell(r, 1, s["label"])
        th.cell(r, 2, "=MEDIAN(%s)" % kept)
        th.cell(r, 15, "=MEDIAN(%s)" % yoy)                          # helper: the median four-quarter change
        th.cell(r, 3, "=1.4826*MEDIAN(%s)" % dev)
        th.cell(r, 4, "=%s(%s)" % ("MAX" if higher else "MIN", kept))
        th.cell(r, 16, "=1.4826*MEDIAN(%s)" % levdev)                 # helper: the spread of levels
        # Helpers for the Scenarios: the same, keeping every quarter.
        raw_all, chg_all = col(2 + k), col(2 + 5 * n + k)
        th.cell(r, 17, "=MEDIAN(%s)" % raw_all)                         # Q: median, every quarter
        th.cell(r, 18, "=MEDIAN(%s)" % chg_all)                         # R: median change, every quarter
        th.cell(r, 19, "=1.4826*MEDIAN(%s)" % col(2 + 6 * n + k))       # S: typical yearly move, every quarter
        th.cell(r, 20, "=1.4826*MEDIAN(%s)" % col(2 + 7 * n + k))       # T: spread of levels, every quarter
        hw, ls, hz = ("Assess!$%s$%d" % (c_, sr) for c_ in "OPQ")
        # A period left out for this product must be whole: two quarters from
        # the calendar, in order, and a reason. Half of one would silently keep
        # every quarter, so the product is refused until the row is fixed.
        bad_lo = ('SUMPRODUCT(({p}=$A{r})*({u}=1)*({ok}=0))>0'
                  .format(p=LO_PROD, u=LO_USED, ok=LO_OK, r=r))
        th.cell(r, 13, ('=IF({lo},"Refused: a period left out for this product is not whole; its Status on Assess '
                        'says what is missing",'
                        'IF(OR(NOT(ISNUMBER({hw})),{hw}<0),"Refused: Moderate\'s half-width must be 0 or more",'
                        'IF(OR(NOT(ISNUMBER({hz})),{hz}<=0),"Refused: High\'s z must be above 0",'
                        'IF(NOT(ISNUMBER({ls})),"Refused: Moderate-Low\'s step must be a number",'
                        'IF(ISERROR(C{r}),"Refused: too little history kept for a typical yearly move",'
                        'IF(AND({fz},B{r}<=0),"Refused: the median is at or below zero",'
                        'IF({ls}<={hw},"Refused: Moderate-Low must begin further from the median than Moderate",'
                        'IF({sg}*(H{r}-G{r})<=0,"Refused: High must begin beyond Moderate-High\'s line",'
                        'IF({sg}*(D{r}-H{r})<0,"Refused: High would begin beyond the worst quarter kept",'
                        'IF(AND({fz},E{r}<=0),"Refused: Moderate-Low would begin at or below zero",""))))))))))')
                .format(fz=fz, r=r, ls=ls, hw=hw, hz=hz, sg=sg, lo=bad_lo))
        # U (hidden): what to do about the refusal in M, in the same order,
        # with the numbers that would clear it worked out live.
        went = "higher" if higher else "lower"
        th.cell(r, 21, ('=IF({lo},"Finish that row under Periods left out (product, From, To and a reason), or clear '
                        'all four of its cells.",'
                        'IF(OR(NOT(ISNUMBER({hw})),{hw}<0),"Type 0 or more in Width of Moderate.",'
                        'IF(OR(NOT(ISNUMBER({hz})),{hz}<=0),"Type a number above 0 in How rare High is.",'
                        'IF(NOT(ISNUMBER({ls})),"Type a number in Moderate-Low begins.",'
                        'IF(ISERROR(C{r}),"Put back a period, so that more than a year of quarters is kept.",'
                        'IF(AND({fz},B{r}<=0),"Put back periods so the quarters kept centre above zero.",'
                        'IF({ls}<={hw},"Raise Moderate-Low begins above "&{hw}&", or lower Width of Moderate below "'
                        '&{ls}&".",'
                        'IF({sg}*(H{r}-G{r})<=0,"Raise How rare High is above "&TEXT(ROUNDUP({hw}*C{r}/P{r},2),'
                        '"0.00")&".",'
                        'IF({sg}*(D{r}-H{r})<0,"Lower How rare High is to "&TEXT(ROUNDDOWN({sg}*(D{r}-B{r})/P{r},2),'
                        '"0.00")&" or less, or put back a period that went {went}.",'
                        'IF(AND({fz},E{r}<=0),"Lower Moderate-Low begins to "&TEXT(ROUNDDOWN(B{r}/C{r},2),"0.00")'
                        '&" or less.",""))))))))))')
                .format(fz=fz, r=r, ls=ls, hw=hw, hz=hz, sg=sg, lo=bad_lo, went=went))
        th.cell(r, 7, "=$B{r}+{sg}*{hw}*$C{r}".format(r=r, sg=sg, hw=hw))
        th.cell(r, 6, "=$B{r}-{sg}*{hw}*$C{r}".format(r=r, sg=sg, hw=hw))
        th.cell(r, 5, "=IF(ISNUMBER({ls}),$B{r}-{sg}*{ls}*$C{r},\"\")".format(r=r, sg=sg, ls=ls))
        th.cell(r, 8, "=$B{r}+{sg}*{hz}*$P{r}".format(r=r, sg=sg, hz=hz))
        lp = s["points"][-1]
        th.cell(r, 9, quarter(lp.date))
        th.cell(r, 10, lp.value)
        op_worse, op_better = ("<=", "<") if higher else (">=", ">")
        bounds = "$E{r}:$H{r}".format(r=r)
        floor = "AND(J{r}<=0,{f})".format(r=r, f=fz)
        th.cell(r, 11, '=IF($M{r}<>"","",IF({floor},1,1+IF(Assess!$R${sr}="worse",'
                       'COUNTIF({b},"{w}"&J{r}),COUNTIF({b},"{bt}"&J{r}))))'
                .format(r=r, floor=floor, sr=sr, b=bounds, w=op_worse, bt=op_better))
        th.cell(r, 12, '=IF(K{r}="","",CHOOSE(K{r},"{0}","{1}","{2}","{3}","{4}"))'.format(*RATINGS, r=r))
        for c_ in range(2, 9):
            th.cell(r, c_).number_format = NF
        th.cell(r, 10).number_format = NF
    th.column_dimensions["O"].hidden = True
    for c_ in "PQRSTU":
        th.column_dimensions[c_].hidden = True
    for c_, w in zip("ABCDEFGHIJKLM", (15, 11, 11, 11, 11, 11, 11, 11, 10, 10, 8, 15, 70)):
        th.column_dimensions[c_].width = w
    for r in range(5, 5 + n):
        th.row_dimensions[r].height = 15
        K.hairlines(th, r, 1, 13)
        for c_ in range(1, 14):
            th.cell(r, c_).font = Font(name="Calibri", size=11, color=K.INK_TEXT)
    for k in range(5):
        th.conditional_formatting.add("K5:K%d" % (4 + n), FormulaRule(formula=["$K5=%d" % (k + 1)],
                                                                      fill=K.solid(K.BANDS[k]), font=Font(bold=True)))
    th.conditional_formatting.add("M5:M%d" % (4 + n), FormulaRule(formula=['LEFT($M5,8)="Refused:"'],
                                                                  fill=K.solid(K.ALERT_FG),
                                                                  font=Font(bold=True, color=K.CRIMSON)))
    th.freeze_panes = "B5"
    th.cell(6 + n, 1, "Ratings: 1 Low, 2 Moderate-Low, 3 Moderate, 4 Moderate-High, 5 High. A value at or below "
                      "zero is always Low. Every term is defined on the Glossary tab." if floor_at_zero and higher
                      else "Ratings: 1 Low, 2 Moderate-Low, 3 Moderate, 4 Moderate-High, 5 High. Every term is "
                      "defined on the Glossary tab.").font = NOTE

    # ---- Chart: every product on one scale, switched on and off in one row,
    # with one product's five score bands behind them (the hand-off) ----
    ch.sheet_properties.tabColor = K.INK
    K.light_title(ch, 1, 2 + n + 2, "%s · every series on one scale" % name,
                  "TRUE in row 5 shows a series; FALSE hides it. The shaded bands are the five ratings of the "
                  "series picked under Bands for.", live=False)
    ch.column_dimensions["A"].width = 2.71
    for k, s in enumerate(loaded):
        col = 2 + k
        c = ch.cell(4, col, s["label"])
        c.font = Font(name="Arial", bold=True, size=9, color=K.SLATE)
        c.alignment = Alignment(wrap_text=True, vertical="bottom")
        c.border = Border(bottom=Side(style="thick", color=K.SERIES[k % len(K.SERIES)]))
        sw_c = ch.cell(5, col, k < 2)
        sw_c.fill = K.solid(K.INPUT)
        sw_c.border = Border(*(Side(style="thin", color=K.INPUT_EDGE),) * 4)
        sw_c.font = Font(name="Calibri", size=11, bold=True)
        ch.column_dimensions[L(col)].width = 15
    ch.row_dimensions[4].height = 25.5
    sw = DataValidation(type="list", formula1='"TRUE,FALSE"', showInputMessage=True, promptTitle="Show",
                        prompt="TRUE draws this product; FALSE hides it.")
    ch.add_data_validation(sw)
    sw.add("B5:%s5" % L(1 + n))
    pc = 3 + n                                            # the Bands for picker, after a gap
    ch.cell(4, pc, "Bands for").font = Font(name="Arial", bold=True, size=9, color=K.SLATE)
    ch.cell(4, pc).alignment = Alignment(vertical="bottom")
    pick = ch.cell(5, pc, loaded[0]["label"])
    pick.fill = K.solid(K.INPUT)
    pick.border = Border(*(Side(style="thin", color=K.INPUT_EDGE),) * 4)
    pick.font = Font(name="Calibri", size=11, bold=True)
    ch.column_dimensions[L(pc)].width = 18
    # The pickers read their choices from cells: an inline list longer than
    # 255 characters is one Excel drops or repairs on open.
    h0 = 40                                               # hidden helpers from column AN
    lists_col = h0 + n + 16
    for i, v in enumerate(["(none)"] + [s["label"] for s in loaded]):
        ch.cell(1 + i, lists_col, v)
    pv = DataValidation(type="list", formula1="=$%s$1:$%s$%d" % (L(lists_col), L(lists_col), 1 + n))
    ch.add_data_validation(pv)
    pv.add(pick.coordinate)
    ch.cell(1, h0, "Quarter")
    for k, s in enumerate(loaded):
        ch.cell(1, h0 + 1 + k, s["label"])
    band_names = ["1 Low", "2 Moderate-Low", "3 Moderate", "4 Moderate-High", "5 High"]
    bc0 = h0 + 1 + n                                      # base, five bands, top/floor
    ch.cell(1, bc0, " ")
    order_c = list(range(5)) if higher else list(range(4, -1, -1))
    for j, i in enumerate(order_c):
        ch.cell(1, bc0 + 1 + j, band_names[i])
    tf = bc0 + 6                                          # top in row 2, floor in row 3, drawable in row 4
    cutsc = ["IFERROR(INDEX(Thresholds!${c}$5:${c}${e},MATCH(${pc}$5,Thresholds!$A$5:$A${e},0))+0,NA())"
             .format(c=L(5 + i), e=4 + n, pc=L(pc)) for i in range(4)]
    if not higher:
        cutsc = cutsc[::-1]
    raw_all = "Data!$B${a}:${e}${b}".format(a=first, b=last, e=L(1 + n))
    ch.cell(2, tf, "=MAX(MAX({r}),{c})*1.08".format(r=raw_all, c=",".join(cutsc)))
    if floor_at_zero:
        ch.cell(3, tf, "=MIN(0,MIN({r}),{c})".format(r=raw_all, c=",".join(cutsc)))
    else:
        ch.cell(3, tf, "=MIN(MIN({r}),{c})-0.08*(MAX(MAX({r}),{c})-MIN(MIN({r}),{c}))".format(r=raw_all,
                                                                                         c=",".join(cutsc)))
    ch.cell(4, tf, "=IF(ISNUMBER(SUM({c})),1,0)".format(c=",".join(cutsc)))
    T_, F_, D_ = ("${c}${r}".format(c=L(tf), r=r_) for r_ in (2, 3, 4))
    for r in range(first, last + 1):
        ch.cell(r, h0, "=Data!A%d" % r)
        for k in range(n):
            col = L(2 + k)
            ch.cell(r, h0 + 1 + k, '=IF(AND(${c}$5,ISNUMBER(Data!{d}{r})),Data!{d}{r},NA())'
                    .format(c=L(2 + k), d=col, r=r))
        ch.cell(r, bc0, "=IF({d}<>1,NA(),{f})".format(d=D_, f=F_))
        ch.cell(r, bc0 + 1, "=IF({d}<>1,NA(),{a}-{f})".format(d=D_, a=cutsc[0], f=F_))
        for j in range(1, 4):
            ch.cell(r, bc0 + 1 + j, "=IF({d}<>1,NA(),{b}-{a})".format(d=D_, a=cutsc[j - 1], b=cutsc[j]))
        ch.cell(r, bc0 + 5, "=IF({d}<>1,NA(),MAX({t}-{a},0))".format(d=D_, t=T_, a=cutsc[3]))
    lc = LineChart()
    lc.add_data(Reference(ch, min_col=h0 + 1, max_col=h0 + n, min_row=1, max_row=last), titles_from_data=True)
    lc.set_categories(Reference(ch, min_col=h0, min_row=2, max_row=last))
    for k, s_ in enumerate(lc.series):
        s_.smooth = False
        s_.marker.symbol = "none"
        s_.graphicalProperties.line = AT._ln(K.SERIES[k % len(K.SERIES)], 2)
    bands_ch = AreaChart()
    bands_ch.grouping = "stacked"
    bands_ch.add_data(Reference(ch, min_col=bc0, max_col=bc0 + 5, min_row=1, max_row=last), titles_from_data=True)
    bands_ch.series[0].graphicalProperties.noFill = True
    bands_ch.series[0].graphicalProperties.line.noFill = True
    for j, s_ in enumerate(bands_ch.series[1:]):
        s_.graphicalProperties.solidFill = K.BANDS[order_c[j]]
        s_.graphicalProperties.line.noFill = True
    AT._quiet_axes(lc, 20)
    lc.y_axis.number_format = "0.0"
    lc.x_axis.tickLblPos = "low"
    # The swatches over row 5 are the products' key; the bands' key is the
    # note under the chart (Excel 16 ignores deleted legend entries, so a
    # legend would also list the bands' invisible base).
    lc.legend = None
    lc.visible_cells_only = False
    lc += bands_ch
    AT._square(lc)
    AT._place(ch, lc, 1, 7, 2 + n + 6, 34)
    for col in range(h0, lists_col + 1):
        ch.column_dimensions[L(col)].hidden = True

    # ---- Assess: the bank's tab, built by assess_tab ----
    AT.build(asx, loaded=loaded, grid=grid, first=first, last=last, n=n, higher=higher,
             floor_at_zero=floor_at_zero, name=name, unit=unit, moderate_halfwidth=moderate_halfwidth,
             low_step=low_step, high_z=high_z, on_the_line=on_the_line, quarter=quarter,
             y_min=None if floor_at_zero else _axis_floor(loaded, direction, moderate_halfwidth, low_step, high_z),
             nf=NF)

    # ---- The reference tabs: one quiet pattern (the hand-off). A title on
    # paper over a stone rule, section names over an ink rule, canvas
    # headers, hairline rows. Red is kept for the two live tabs. ----
    for ws in (evs, bts, srcs, gl, da, run):
        ws.sheet_properties.tabColor = K.STONE
    DATA_F = Font(name="Calibri", size=11, color=K.INK_TEXT)

    # ---- Evidence: each product's spells and departures, side by side ----
    K.light_title(evs, 1, 16, "Evidence for each judgement",
                  "How unusual each stretch worse than the median was. Robust z: how far its peak sits from the rest "
                  "of history; 3.5 or more is unusual. A distance, not a probability.", live=False)
    r = 4
    for s in loaded:
        ev = s["ev"]
        K.quiet_section(evs, r, s["label"], 16)
        K.canvas_header(evs, r + 1, ["Spell from", "Peak quarter", "Peak", "Peak ÷ median", "Robust z",
                                     "Years per spell this bad", "Deepest dip (sd of quarterly change)", "Note"],
                        right_from=2)
        K.canvas_header(evs, r + 1, ["Temporary departure: first quarter", "Last quarter", "Worse or better",
                                     "Average distance from trend", "Robust z", "Rank among windows of its length",
                                     "Window (quarters)"], first_col=10, right_from=3)
        evs.row_dimensions[r + 1].height = 34.5
        for i, sp in enumerate(ev["spells"]):
            rr = r + 2 + i
            for col, v in enumerate([quarter(sp["start"]), quarter(sp["peak_date"]), sp["peak"],
                                     sp["peak_over_median"], sp["robust_z"], sp["return_period_years"],
                                     sp["dip"]["in_sd_of_change"] if sp["dip"] else None, sp["note"]], start=1):
                evs.cell(rr, col, v).font = DATA_F
            for col, fmt in ((3, NF), (4, "0.00"), (5, "+0.0;-0.0;0.0"), (6, "0.0"), (7, "0.0")):
                evs.cell(rr, col).number_format = fmt
            K.hairlines(evs, rr, 1, 8)
        for i, d in enumerate(ev["departures"]):
            rr = r + 2 + i
            for col, v in enumerate([quarter(d["first"]), quarter(d["last"]), d["direction"], d["mean_departure"],
                                     d["robust_z"], "1 of %d" % d["of"], d["length"]], start=10):
                evs.cell(rr, col, v).font = DATA_F
            evs.cell(rr, 13).number_format = NF
            evs.cell(rr, 14).number_format = "+0.0;-0.0;0.0"
            K.hairlines(evs, rr, 10, 16)
        r += 2 + max(len(ev["spells"]), len(ev["departures"]), 1) + 1
    for rng_ in ("E5:E%d" % r, "N5:N%d" % r):
        evs.conditional_formatting.add(rng_, FormulaRule(formula=["AND(ISNUMBER(%s5),ABS(%s5)>=3.5)"
                                                                  % (rng_[0], rng_[0])],
                                                         fill=K.solid(K.BANDS[2]), font=Font(bold=True)))
    for col, w in zip("ABCDEFGHIJKLMNOP", (12, 12, 10, 10, 10, 12, 14, 34, 2.71, 16, 12, 14, 11, 10, 14, 11)):
        evs.column_dimensions[col].width = w
    evs.freeze_panes = "A4"

    # ---- Backtest: one table, a row per product and weighting ----
    n_scores = len(percentiles) + 1
    width = 5 + n_scores
    K.light_title(bts, 1, width, "How predictive would the scale have been?",
                  "Each quarter is rated on lines at percentiles %s of the history up to and including it, then compared with "
                  "the value %d quarters later. Spearman: 1 means a higher rating always came before a higher "
                  "value, 0 means no link. Average change ahead: in the measure's own units. Neighbouring quarters "
                  "overlap, so read this as a description, not proof."
                  % ("/".join("%g" % p for p in percentiles), horizon), live=False)
    bts.row_dimensions[2].height = 42
    bts["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    for c1, c2, lbl in ((3, 4, "Spearman: rating against"), (5, 4 + n_scores, "Average change ahead, by rating")):
        bts.cell(4, c1, lbl).font = Font(name="Arial", bold=True, size=9, color=K.INK)
        for c_ in range(c1, c2 + 1):
            bts.cell(4, c_).border = Border(bottom=Side(style="thin", color=K.INK))
    K.canvas_header(bts, 5, ["Series", "Weighting", "Value ahead", "Change ahead"]
                    + ["%d" % k for k in range(1, n_scores + 1)] + ["Quarters tested"], right_from=2)
    r = 6
    for s in loaded:
        for run_ in s["bt"]["runs"]:
            vals_ = [s["label"], "none" if run_["half_life_years"] is None else "%g-yr half-life"
                     % run_["half_life_years"], run_["score_vs_level_ahead"], run_["score_vs_change_ahead"],
                     *[b["mean_change_ahead"] for b in run_["by_score"]], run_["periods_tested"]]
            for col, v in enumerate(vals_, start=1):
                bts.cell(r, col, v).font = DATA_F
            for col in range(3, 5 + n_scores):
                bts.cell(r, col).number_format = "0.00"
            K.hairlines(bts, r, 1, width)
            r += 1
    bts.column_dimensions["A"].width = 18
    bts.column_dimensions["B"].width = 15
    for col in range(3, width + 1):
        bts.column_dimensions[L(col)].width = 12
    bts.freeze_panes = "C6"

    # ---- Sources: what each file says about itself. Generic by construction:
    # the tab prints the file's own description lines ("# key: text", the
    # keys the internal templates ask for) and adds nothing; a key every file
    # should give and this one does not is marked, never filled in. ----
    K.light_title(srcs, 1, 2, "Sources",
                  "What each series' file says about itself, as written in the file. Nothing here is added.",
                  live=False)
    srcs.row_dimensions[2].height = 27
    srcs["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    shown = {"measure": "Measure", "population": "Who is in it", "call-report": "Call Report lines",
             "numerator": "Numerator", "denominator": "Denominator", "basis": "Basis",
             "as-of": "As of", "source": "Source", "checked": "Checked", "prepared-by": "Prepared by",
             "prepared-on": "Prepared on", "note": "Note"}
    r = 4
    for s in loaded:
        notes = read_notes(s["path"])
        r = K.quiet_section(srcs, r, s["label"], 2)
        rows_ = [("File", "%s (%d rows, %s to %s; its SHA-256 is on Run)"
                  % (s["path"].name, len(s["raw"]), s["raw"][0].date, s["raw"][-1].date))]
        rows_ += [(shown.get(k, k.replace("-", " ").capitalize()), v) for k, v in notes]
        given = {k for k, _ in notes}
        missing = [k for k in CORE_NOTES if k not in given]
        for lbl, v in rows_:
            srcs.cell(r, 1, lbl).font = Font(name="Arial", bold=True, size=9, color=K.SLATE)
            c = srcs.cell(r, 2, v)
            c.font = DATA_F
            c.alignment = Alignment(wrap_text=True, vertical="top")
            srcs.cell(r, 1).alignment = Alignment(vertical="top")
            srcs.row_dimensions[r].height = 15 * max(1, -(-len(str(v)) // 140)) + 2
            K.hairlines(srcs, r, 1, 2)
            r += 1
        for k in missing:
            srcs.cell(r, 1, shown.get(k, k)).font = Font(name="Arial", bold=True, size=9, color=K.CRIMSON)
            srcs.cell(r, 2, "Not stated in the file").font = Font(name="Calibri", size=11, bold=True, color=K.CRIMSON)
            srcs.cell(r, 2).fill = K.solid(K.ALERT_FG)
            K.hairlines(srcs, r, 1, 2)
            r += 1
        r += 1
    srcs.column_dimensions["A"].width = 22
    srcs.column_dimensions["B"].width = 130

    # ---- Glossary: the one tab whose rows wrap ----
    K.light_title(gl, 1, 3, "Glossary", "What each term means, and exactly how the workbook calculates it.",
                  live=False)
    K.canvas_header(gl, 4, ["Term", "What it means", "How it is calculated"])
    widths_g = (30, 60, 80)
    for i, (term, meaning, calc) in enumerate(TERMS):
        rr = 5 + i
        for col, v in enumerate((term, meaning, calc), start=1):
            c = gl.cell(rr, col, v)
            c.alignment = Alignment(wrap_text=True, vertical="top")
            c.font = Font(name="Calibri", size=11, color=K.INK_TEXT, bold=col == 1)
        lines = max(-(-len(str(v)) // int(w * 1.1)) for v, w in zip((term, meaning, calc), widths_g))
        gl.row_dimensions[rr].height = 15 * max(1, lines) + 3
        K.hairlines(gl, rr, 1, 3)
    for c_, w in zip("ABC", widths_g):
        gl.column_dimensions[c_].width = w
    gl.freeze_panes = "B5"

    # ---- Data: its header wraps; column groups alternate canvas and mist ----
    groups = 8                                       # raw, kept, change, distances x2, the same keeping every quarter
    for g in range(groups):
        for k in range(n):
            col = 2 + g * n + k
            c = da.cell(1, col)
            c.fill = K.solid(K.CANVAS if g % 2 == 0 else K.MIST)
            c.font = Font(name="Arial", bold=True, size=9, color=K.SLATE)
            c.alignment = Alignment(wrap_text=True, vertical="center")
            da.column_dimensions[L(col)].width = 12
    da.cell(1, 1).fill = K.solid(K.CANVAS)
    da.cell(1, 1).font = Font(name="Arial", bold=True, size=9, color=K.SLATE)
    da.row_dimensions[1].height = 34.5
    for r in range(first, last + 1):
        for col in range(2, 2 + groups * n):
            da.cell(r, col).number_format = NF
    da.freeze_panes = "B2"

    # ---- Run: four sections on fixed columns; the hash goes last ----
    K.light_title(run, 1, 6, "Run", "What went in: the build, the files and their fingerprints, and the choices "
                                    "made on Assess, live.", live=False)
    r = K.quiet_section(run, 4, "This build", 6)
    build_rows = [("threshold-engine", VERSION), ("Built", dt.datetime.now().isoformat(timespec="seconds"))]
    if smoothing > 1:
        build_rows.append(("Smoothing", "The Data tab holds each file's values as a trailing mean over %d quarters, "
                           "dated at the last; the first %d quarters of each file have no full window and are not "
                           "used. Every line, score and test is built from those values." % (smoothing, smoothing - 1)))
    build_rows += [("Measure", "%s (%s); %s; %s; %s" % (
                        name, unit, "higher is worse" if higher else "lower is worse",
                        "no smoothing" if smoothing == 1 else "smoothed over %d quarters" % smoothing,
                        "a value at or below zero is always Low" if floor_at_zero else "no floor at zero")),
                   ("Starting settings", "Width of Moderate %g; Moderate-Low begins %g; How rare High is %g; on a "
                    "line, rate it %s" % (moderate_halfwidth, low_step, high_z, on_the_line)),
                   ("Backtest half-lives", ", ".join("%g" % h for h in half_lives) or "none"),
                   ("Backtest settings", "percentiles %s; horizon %d; min history %d"
                    % ("/".join("%g" % p for p in percentiles), horizon, min_history))]
    for lbl, v in build_rows:
        run.cell(r, 1, lbl).font = Font(name="Arial", bold=True, size=9, color=K.SLATE)
        run.cell(r, 2, v).font = DATA_F
        r += 1
    r = K.quiet_section(run, r + 1, "Files", 6)
    files_head = r
    r = K.canvas_header(run, r, ["Series", "File", "Rows", "First", "Last", "SHA-256"])
    for s in loaded:
        for col, v in enumerate([s["label"], str(s["path"]), len(s["raw"]), s["raw"][0].date, s["raw"][-1].date,
                                 _sha(s["path"])], start=1):
            run.cell(r, col, v).font = DATA_F
        run.cell(r, 6).font = Font(name="Consolas", size=9, color=K.SLATE)
        K.hairlines(run, r, 1, 6)
        r += 1
    r = K.quiet_section(run, r + 1, "Periods left out, as on Assess (live)", 6)
    lo_head_run = r
    r = K.canvas_header(run, r, ["Series", "From", "To", "Reason", "Status", ""])
    for rr in range(LO_TOP, lo_end + 1):
        for col, c_ in enumerate("NOPQ", start=1):
            run.cell(r, col, '=IF(Assess!{c}{r}="","",Assess!{c}{r})'.format(c=c_, r=rr)).font = DATA_F
        run.cell(r, 5, "=Assess!T%d" % rr).font = DATA_F
        r += 1
    r = K.quiet_section(run, r + 1, "Your settings, as on Assess (live)", 6)
    r = K.canvas_header(run, r, ["Series", "Width of Moderate", "Moderate-Low begins", "How rare High is (z)",
                                 "On a line, rate it", ""])
    for s in loaded:
        run.cell(r, 1, s["label"]).font = DATA_F
        for col, c_ in enumerate("OPQR", start=2):
            run.cell(r, col, "=Assess!%s%d" % (c_, srow[s["label"]])).font = DATA_F
        r += 1
    for c_, w in zip("ABCDEF", (24, 52, 12, 26, 30, 70)):
        run.column_dimensions[c_].width = w

    out = Path(out)
    wb.save(out)
    return {"path": out, "products": [s["label"] for s in loaded], "quarters": len(grid),
            "evidence": {s["label"]: s["ev"] for s in loaded}}
