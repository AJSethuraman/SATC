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
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation

from . import keybank_style as K
from .backtest import backtest
from . import VERSION
from .evidence import evidence
from .glossary import TERMS
from .scale import scale as _scale
from .series import LABEL_RULE, check, label_ok, read_csv, smooth

RATINGS = ("Low", "Moderate-Low", "Moderate", "Moderate-High", "High")
INPUT = PatternFill("solid", fgColor="FFF2CC")
# A conditional format's fill is read from its background colour, so both
# are set (with fgColor alone Excel drew the highlighted row white).
PICKED = PatternFill("solid", fgColor="F6D9A8", bgColor="F6D9A8")
# The Assess tab's inputs. Leave-outs are a list under the chart: any product,
# any number of periods up to LO_ROWS, each picked from the calendar. Excel
# without macros cannot let one cell follow the product picker and still keep
# a value per product, so the settings are a table, one row per product, with
# the picked product's row highlighted (the bank's choice, 13 Oct 2026).
LO_TOP, LO_ROWS = 42, 12            # Assess rows 42-53: Product, From, To, Reason, Status
SET_TOP = 58                        # Assess rows 58...: one per product, columns B-E
NOTE = Font(name="Arial", size=9, italic=True, color=K.SLATE)


def _wrap(ws, row, height=34):
    """Header labels wrap in their column instead of being cut off."""
    for cell in ws[row]:
        if cell.value is not None:
            cell.alignment = Alignment(wrap_text=True, vertical="center",
                                       horizontal=cell.alignment.horizontal or "left")
    ws.row_dimensions[row].height = height


def _axis_floor(loaded, direction, halfwidth, low_step, high_z):
    """A round number under every product's lowest value and line, and under
    the strip that marks quarters left out, or None if that is not above zero
    (then the axis starts at zero anyway). Rounded down to a half of the
    range's order of magnitude.

    The axis cannot follow a cell, so its minimum has to hold for the
    settings the bank may still type, not only the starting ones (Codex on
    #432: raising Moderate-Low's step pushed score 2's line off the bottom).
    It covers every value the dials offer as well as the starting values:
    a width up to 1, a Moderate-Low step up to 2, a z from 2 to 3.5."""
    s_ = 1.0 if direction == "higher_is_worse" else -1.0
    lows, highs = [], []
    for s in loaded:
        vals = [p.value for p in s["points"]]
        ref = _scale(vals, direction, halfwidth, low_step, high_z, False)
        med, move, spread = ref["median"], ref["typical_yearly_move"] or 0.0, ref["spread_of_levels"]
        lines = []
        for hw in {halfwidth, 0.25, 1.0}:
            for ls in {low_step, 0.75, 2.0}:
                for z in {high_z, 2.0, 3.5}:
                    lines += [med - s_ * ls * move, med - s_ * hw * move, med + s_ * hw * move, med + s_ * z * spread]
        both = vals + lines
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
    """Where things sit on Assess for n products, one place for the builder,
    the tests and the walkthrough: the leave-out rows, the settings rows, the
    notes, the evidence, the scenarios, what the lines rest on, and the first
    value row of each dial (High's z, the width, the Moderate-Low step)."""
    set_end = SET_TOP + n - 1
    expl_top = set_end + 2
    ev_top = expl_top + 8
    scen_top = ev_top + 5
    base_row = scen_top + 43
    dial = base_row + 6
    return dict(lo_top=LO_TOP, lo_end=LO_TOP + LO_ROWS - 1, set_top=SET_TOP, set_end=set_end, expl_top=expl_top,
                ev_top=ev_top, scen_top=scen_top, base_row=base_row,
                dials={"high_z": dial, "halfwidth": dial + 8, "low_step": dial + 16})


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
    n, first, last = len(loaded), 2, len(grid) + 1

    wb = Workbook()
    th = wb.active
    th.title = "Thresholds"
    asx, ch, evs, bts, gl, da, run = (wb.create_sheet(t) for t in
                                      ("Assess", "Chart", "Evidence", "Backtest", "Glossary", "Data", "Run"))
    asx.sheet_properties.tabColor = K.KEY_RED
    wb.active = 1                        # it opens where the bank works: Assess
    for ws in (th, asx, ch, evs, bts, gl, run):
        K.hide_gridlines(ws)
    lo_end = LO_TOP + LO_ROWS - 1
    set_end = SET_TOP + n - 1
    # The leave-out list, as ranges: the product typed, the calendar positions
    # of From and To (hidden helpers), whether the row is whole, and whether it
    # is in use at all.
    lo_rng = lambda c_: "Assess!${c}${a}:${c}${b}".format(c=c_, a=LO_TOP, b=lo_end)     # noqa: E731
    LO_PROD, LO_FROM, LO_TO, LO_OK, LO_USED = (lo_rng(c_) for c_ in ("A", "Z", "AA", "AB", "AC"))

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
    K.brand_banner(th, 1, 13, "%s — candidate thresholds" % name,
                   "Live: recalculates from your choices on the Assess tab. Candidates for the bank to accept, "
                   "adjust or reject.")
    K.header_row(th, 4, ["Product", "Median kept", "Typical yearly move", "Worst kept", "2 Moderate-Low from",
                         "3 Moderate from", "4 Moderate-High from", "5 High from", "Latest quarter",
                         "Latest (%s)" % unit, "Score", "Rating", "Check"], right_from=1)
    _wrap(th, 4, 46)
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
        hw, ls, hz = ("Assess!$%s$%d" % (c_, sr) for c_ in "BCD")
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
        th.cell(r, 11, '=IF($M{r}<>"","",IF({floor},1,1+IF(Assess!$E${sr}="worse",'
                       'COUNTIF({b},"{w}"&J{r}),COUNTIF({b},"{bt}"&J{r}))))'
                .format(r=r, floor=floor, sr=sr, b=bounds, w=op_worse, bt=op_better))
        th.cell(r, 12, '=IF(K{r}="","",CHOOSE(K{r},"{0}","{1}","{2}","{3}","{4}"))'.format(*RATINGS, r=r))
        for c_ in range(2, 9):
            th.cell(r, c_).number_format = "0.000"
        th.cell(r, 10).number_format = "0.000"
    th.column_dimensions["O"].hidden = True
    for c_ in "PQRST":
        th.column_dimensions[c_].hidden = True
    for c_, w in zip("ABCDEFGHIJKLM", (20, 10, 10, 10, 12, 12, 12, 12, 10, 10, 7, 15, 34)):
        th.column_dimensions[c_].width = w
    th.cell(6 + n, 1, "Scores: 1 Low, 2 Moderate-Low, 3 Moderate, 4 Moderate-High, 5 High. A loss at or below "
                      "zero is always Low. Every term is defined on the Glossary tab." if floor_at_zero and higher
                      else "Scores: 1 Low, 2 Moderate-Low, 3 Moderate, 4 Moderate-High, 5 High. Every term is "
                      "defined on the Glossary tab.").font = NOTE

    # ---- Chart: switches, one scale, one product's cutoffs ----
    ch.cell(1, 1, "Show").font = Font(bold=True)
    for k, s in enumerate(loaded):
        ch.cell(2 + k, 1, s["label"])
        c = ch.cell(2 + k, 2, k < 2)
        c.fill = INPUT
    sw = DataValidation(type="list", formula1='"TRUE,FALSE"')
    ch.add_data_validation(sw)
    sw.add("B2:B%d" % (1 + n))
    lr = 3 + n
    ch.cell(lr, 1, "Draw cutoffs for").font = Font(bold=True)
    pick = ch.cell(lr, 2, loaded[0]["label"])
    pick.fill = INPUT
    # The pickers read their choices from cells: an inline list longer than
    # 255 characters is one Excel drops or repairs on open.
    lists_col = 4 + n + 6
    for i, v in enumerate(["(none)"] + [s["label"] for s in loaded]):
        ch.cell(1 + i, lists_col, v)
    ch.column_dimensions[L(lists_col)].hidden = True
    pv = DataValidation(type="list", formula1="=$%s$1:$%s$%d" % (L(lists_col), L(lists_col), 1 + n))
    ch.add_data_validation(pv)
    pv.add(pick.coordinate)
    ch.column_dimensions["A"].width = 18
    h0 = 4                                   # helper columns start at D
    ch.cell(1, h0, "Quarter")
    for k, s in enumerate(loaded):
        ch.cell(1, h0 + 1 + k, s["label"])
    for i in range(4):
        ch.cell(1, h0 + 1 + n + i, "Score %d from" % (i + 2))
    for r in range(first, last + 1):
        ch.cell(r, h0, "=Data!A%d" % r)
        for k in range(n):
            col = L(2 + k)
            ch.cell(r, h0 + 1 + k, '=IF(AND($B${sw},ISNUMBER(Data!{c}{r})),Data!{c}{r},NA())'
                    .format(sw=2 + k, c=col, r=r))
        for i in range(4):
            ch.cell(r, h0 + 1 + n + i,
                    '=IFERROR(INDEX(Thresholds!${c}$5:${c}${e},MATCH($B${p},Thresholds!$A$5:$A${e},0))+0,NA())'
                    .format(c=L(5 + i), e=4 + n, p=lr))
    lc = LineChart()
    lc.title = "%s, %s (one scale)" % (name, unit)
    lc.height, lc.width = 12, 28
    lc.add_data(Reference(ch, min_col=h0 + 1, max_col=h0 + n + 4, min_row=1, max_row=last), titles_from_data=True)
    lc.set_categories(Reference(ch, min_col=h0, min_row=2, max_row=last))
    for s_ in lc.series:
        s_.smooth = False
    for s_ in lc.series[n:]:
        s_.graphicalProperties.line.dashStyle = "dash"
        s_.graphicalProperties.line.width = 12000
    lc.x_axis.tickLblSkip = 20
    lc.x_axis.delete = False
    lc.y_axis.delete = False
    # Below the plot: on the right, Excel 16 drew the legend over the cutoff
    # lines' right-hand ends (seen in the walkthrough, 13 Oct 2026).
    lc.legend.position = "b"
    lc.legend.overlay = False
    lc.visible_cells_only = False      # its helper columns are hidden; plot them anyway
    ch.add_chart(lc, "A%d" % (lr + 3))
    for col in range(h0, h0 + n + 5):
        ch.column_dimensions[L(col)].hidden = True

    # ---- Assess: one product, its score bands, and where history fell ----
    # Live. Pick a product; the bands are its cutoffs from Thresholds, the line
    # is the quarters kept, grey is what the list under it leaves out, and the table
    # counts the quarters kept in each score.
    K.brand_banner(asx, 1, 11, "Assess and set one product's thresholds",
                   "Pick a product. The bands are its five scores and the line is its history. Leave periods out "
                   "and change your settings below the chart; everything here follows as you type.")
    asx.cell(4, 1, "Product").font = Font(bold=True)
    apick = asx.cell(4, 2, loaded[0]["label"])
    apick.fill = INPUT
    av = DataValidation(type="list", formula1="=Chart!$A$2:$A$%d" % (1 + n))
    asx.add_data_validation(av)
    av.add(apick.coordinate)
    tr = "MATCH($B$4,Thresholds!$A$5:$A${e},0)".format(e=4 + n)
    asx.cell(5, 1, "Check")
    asx.cell(5, 2, "=INDEX(Thresholds!$M$5:$M${e},{m})".format(e=4 + n, m=tr))
    # The latest quarter's score, here, so nothing needs the Thresholds tab
    # while working (the bank: "i dont want to flip back and forth").
    ix_th = lambda c_: "INDEX(Thresholds!${c}$5:${c}${e},{m})".format(c=c_, e=4 + n, m=tr)   # noqa: E731
    asx.cell(4, 4, "Latest").font = Font(bold=True)
    asx.cell(4, 5, '={q}&": "&TEXT({v},"0.000")&"  ->  "&IF({k}="","no score: see Check",{k}&" "&{lb})'
             .format(q=ix_th("I"), v=ix_th("J"), k=ix_th("K"), lb=ix_th("L"))).font = Font(bold=True)
    K.header_row(asx, 7, ["Score", "Rating", "From", "To", "Quarters kept", "Share kept",
                          "Every quarter", "Share of every quarter"], right_from=2)
    _wrap(asx, 7, 48)
    bnd = ["INDEX(Thresholds!${c}$5:${c}${e},{m})".format(c=c_, e=4 + n, m=tr) for c_ in "EFGH"]
    online = "INDEX(Assess!$E${a}:$E${b},{m})".format(a=SET_TOP, b=set_end, m=tr)
    hc = 12                                   # helper columns start at L
    rng = lambda c_: "${c}${a}:${c}${b}".format(c=L(c_), a=first, b=last)           # noqa: E731
    kept_r, raw_r = rng(hc + 1), rng(hc + 3)
    for i in range(5):
        r = 8 + i
        asx.cell(r, 1, i + 1)
        asx.cell(r, 2, RATINGS[i])
        lo = "" if i == 0 else bnd[i - 1]
        hi = "" if i == 4 else bnd[i]
        asx.cell(r, 3, "=IFERROR(%s+0,\"\")" % lo if lo else "")
        asx.cell(r, 4, "=IFERROR(%s+0,\"\")" % hi if hi else "")
        for col, data in ((5, kept_r), (7, raw_r)):
            # A value on a line takes the worse score, or the better, as Your settings says.
            if higher:
                ge, lt = ('">="', '"<"'), ('">"', '"<="')
            else:
                ge, lt = ('"<="', '">"'), ('"<"', '">="')
            def crit(op_pair_w, op_pair_b, ref):
                return 'IF({o}="worse",{w},{b})&{ref}'.format(o=online, w=op_pair_w, b=op_pair_b, ref=ref)
            parts = []
            if lo:
                parts.append('{d},{c}'.format(d=data, c=crit(ge[0], lt[0], lo)))
            if hi:
                parts.append('{d},{c}'.format(d=data, c=crit(ge[1], lt[1], hi)))
            asx.cell(r, col, '=IF($U$5<>1,"",COUNTIFS(%s))' % ",".join(parts))
        asx.cell(r, 6, '=IF(E{r}="","",E{r}/SUM($E$8:$E$12))'.format(r=r))
        asx.cell(r, 8, '=IF(G{r}="","",G{r}/SUM($G$8:$G$12))'.format(r=r))
        for col in (3, 4):
            asx.cell(r, col).number_format = "0.000"
        for col in (6, 8):
            asx.cell(r, col).number_format = "0%"
    asx.cell(13, 1, "Counts use the same rule as the score: a value on a line takes the score Your settings "
                    "says. "
                    "A loss at or below zero falls in score 1.").font = NOTE
    for col, w in zip("ABCDEFGH", (10, 15, 10, 10, 10, 10, 10, 12)):
        asx.column_dimensions[col].width = w

    # ---- Assess: dials. For the product shown, what each setting would do at
    # other values, the others held as in Your settings. Live, like everything else.
    ix = lambda sheet, c_, top: "INDEX({s}!${c}${t}:${c}${e},{m})".format(                    # noqa: E731
        s=sheet, c=c_, t=top, e=top - 1 + n, m=tr)
    # Below the chart: the inputs (rows LO_TOP..), then what the settings mean
    # and what the evidence says, then what the lines rest on, then the dials.
    lay = assess_layout(n)
    expl_top, ev_top, scen_top, base_row = lay["expl_top"], lay["ev_top"], lay["scen_top"], lay["base_row"]
    asx.cell(base_row, 1, "What it rests on").font = Font(bold=True)
    base = [("Median kept", ix("Thresholds", "B", 5)), ("Typical yearly move", ix("Thresholds", "C", 5)),
            ("Spread of levels", ix("Thresholds", "P", 5)), ("Worst kept", ix("Thresholds", "D", 5)),
            ("Half-width now", ix("Assess", "B", SET_TOP)), ("Moderate-Low step now", ix("Assess", "C", SET_TOP)),
            ("High z now", ix("Assess", "D", SET_TOP))]
    for j, (lbl, f) in enumerate(base):
        lc = asx.cell(base_row + 1, 1 + j, lbl)
        lc.font = Font(bold=True, size=9)
        lc.alignment = Alignment(wrap_text=True, vertical="bottom")
        c = asx.cell(base_row + 2, 1 + j, "=" + f)
        c.number_format = "0.000"
    asx.row_dimensions[base_row + 1].height = 26
    MED, MOVE, SPREAD, WORST, HW, LS, HZ = ("$%s$%d" % (L(1 + j), base_row + 2) for j in range(7))
    sgn = "1" if higher else "-1"
    if higher:
        ge, lt = ('">="', '"<"'), ('">"', '"<="')
    else:
        ge, lt = ('"<="', '">"'), ('"<"', '">="')

    def counts(r, cols, num="TRUE"):
        """Quarters kept in each score, for the four lines in this row's columns;
        blank when ``num`` (the row's settings are numbers) is false."""
        b = ["%s%d" % (c_, r) for c_ in cols]
        for k in range(5):
            parts = []
            if k > 0:
                parts.append('{d},IF({o}="worse",{w},{bt})&{ref}'.format(d=kept_r, o=online, w=ge[0], bt=lt[0],
                                                                          ref=b[k - 1]))
            if k < 4:
                parts.append('{d},IF({o}="worse",{w},{bt})&{ref}'.format(d=kept_r, o=online, w=ge[1], bt=lt[1],
                                                                          ref=b[k]))
            asx.cell(r, 6 + k, '=IF(NOT(%s),"",COUNTIFS(%s))' % (num, ",".join(parts)))

    dials = [("High's z", HZ, (2.0, 2.5, 3.0, 3.5)),
             ("Moderate's half-width, in typical yearly moves", HW, (0.25, 0.5, 0.75, 1.0)),
             ("Moderate-Low step, in typical yearly moves", LS, (0.75, 1.0, 1.5, 2.0))]
    r = base_row + 4
    dial_rows = []
    for title, now, values in dials:
        K.section_band(asx, r, "Dial: " + title + " (the other settings as in Your settings)", 11)
        K.header_row(asx, r + 1, ["Value", "2 from", "3 from", "4 from", "5 from",
                                  "Low", "Mod-Low", "Moderate", "Mod-High", "High", ""], right_from=0)
        r += 2
        dial_rows.append((title, r))
        for v in list(values) + [None]:
            val = now if v is None else repr(v)
            asx.cell(r, 1, "=" + now if v is None else v)
            hw_, ls_, hz_ = (val if now == x else x for x in (HW, LS, HZ))
            # Text in a setting is refused on Thresholds; here it would be
            # multiplied into #VALUE!, so the row is blank and says why.
            num = "AND(ISNUMBER({}),ISNUMBER({}),ISNUMBER({}))".format(hw_, ls_, hz_)
            asx.cell(r, 2, '=IF({n},{m}-{s}*{ls}*{mv},"")'.format(n=num, m=MED, s=sgn, ls=ls_, mv=MOVE))
            asx.cell(r, 3, '=IF({n},{m}-{s}*{hw}*{mv},"")'.format(n=num, m=MED, s=sgn, hw=hw_, mv=MOVE))
            asx.cell(r, 4, '=IF({n},{m}+{s}*{hw}*{mv},"")'.format(n=num, m=MED, s=sgn, hw=hw_, mv=MOVE))
            asx.cell(r, 5, '=IF({n},{m}+{s}*{hz}*{sp},"")'.format(n=num, m=MED, s=sgn, hz=hz_, sp=SPREAD))
            counts(r, "BCDE", num)
            asx.cell(r, 11, ('=IF(NOT({n}),"refused: a setting is not a number",'
                             'IF({ls}<={hw},"refused: Moderate-Low inside Moderate",'
                             'IF({s}*(E{r}-D{r})<=0,"refused: High inside Moderate-High",'
                             'IF({s}*({w}-E{r})<0,"refused: High beyond the worst kept",{now}))))')
                     .format(n=num, ls=ls_, hw=hw_, s=sgn, r=r, w=WORST, now='"<- now"' if v is None else '""'))
            for c_ in range(2, 6):
                asx.cell(r, c_).number_format = "0.000"
            if v is None:
                for c_ in range(1, 12):
                    asx.cell(r, c_).fill = INPUT
            r += 1
        r += 1
    asx.cell(r, 1, "Each dial changes one setting and holds the others as they are in Your settings. The "
                   "highlighted row is the current setting and matches the table above. Change a setting in Your "
                   "settings and "
                   "every row follows.").font = NOTE
    asx.column_dimensions["I"].width = 10
    asx.column_dimensions["J"].width = 10
    asx.column_dimensions["K"].width = 34       # column L onward holds the chart's hidden helpers
    # The bands stack upward from the lowest line. Higher-is-worse lines rise
    # (score 1 at the bottom); lower-is-worse lines fall, so the stack starts
    # at score 5 and the line order, headings and colours are reversed.
    order = list(range(5)) if higher else list(range(4, -1, -1))
    heads = ["Quarter", "Kept", "Quarter left out", "Every quarter"] + ["%d %s" % (i + 1, RATINGS[i]) for i in order]
    for j, h in enumerate(heads):
        asx.cell(first - 1, hc + j, h)
    asx.cell(first - 1, hc + 9, "Top")
    asx.cell(first - 1, hc + 10, " ")         # the invisible base the bands stack on
    pk = "MATCH($B$4,Data!$B$1:${c}$1,0)".format(c=L(1 + n))
    for r in range(first, last + 1):
        asx.cell(r, hc, "=Data!A%d" % r)
        raw = "INDEX(Data!$B{r}:${c}{r},{m})".format(r=r, c=L(1 + n), m=pk)
        kept = "INDEX(Data!${a}{r}:${b}{r},{m})".format(a=L(2 + n), b=L(1 + 2 * n), r=r, m=pk)
        asx.cell(r, hc + 1, '=IF(ISNUMBER({k}),{k},NA())'.format(k=kept))
        asx.cell(r, hc + 2, '=IF(AND(ISNUMBER({raw}),NOT(ISNUMBER({k}))),{raw},NA())'.format(raw=raw, k=kept))
        asx.cell(r, hc + 3, '=IF(ISNUMBER({raw}),{raw},NA())'.format(raw=raw))
        # The same, blank instead of #N/A, for the chart's top and floor: MAX
        # and MIN over a range holding #N/A give #N/A, and a product whose
        # data starts after the calendar lost its Low and High bands (Excel
        # 16, the walkthrough, 13 Oct 2026).
        asx.cell(r, hc + 12, '=IF(ISNUMBER({raw}),{raw},"")'.format(raw=raw))
        top = "${c}${r0}".format(c=L(hc + 9), r0=first)
        b = ["$C$9", "$C$10", "$C$11", "$C$12"]
        if not higher:
            b = b[::-1]
        # The stack starts at the chart's floor (the base, invisible), so the
        # first band is its distance from there, never a cut-off read as a
        # width: below zero a cut-off is negative and a band is not.
        base = "${c}${r0}".format(c=L(hc + 9), r0=first + 1)
        asx.cell(r, hc + 10, '=IF($U$5<>1,NA(),{lo})'.format(lo=base))
        asx.cell(r, hc + 4, '=IF($U$5<>1,NA(),{b0}-{lo})'.format(b0=b[0], lo=base))
        for i in range(1, 4):
            asx.cell(r, hc + 4 + i, '=IF($U$5<>1,NA(),{b1}-{b0})'.format(b1=b[i], b0=b[i - 1]))
        asx.cell(r, hc + 8, '=IF($U$5<>1,NA(),MAX({t}-{b3},0))'.format(t=top, b3=b[3]))
    # Top and floor take in the cut-offs as well as the data, and the top sits
    # 8% of the whole range above the highest, which works below zero too.
    cuts, axis_r = "$C$9:$C$12", rng(hc + 12)
    asx.cell(first - 1, hc + 12, "For the axis")
    asx.cell(first, hc + 9, "=MAX(MAX({r}),MAX({c}))+0.08*(MAX(MAX({r}),MAX({c}))-{lo})"
             .format(r=axis_r, c=cuts, lo="${c}${r}".format(c=L(hc + 9), r=first + 1)))
    # The strip that marks quarters left out: a bar under the data, below zero
    # or below the lowest value if that is negative, 6% of the chart's height.
    asx.cell(first - 1, hc + 11, "Period left out")
    lo_c, top_c = "${c}${r}".format(c=L(hc + 9), r=first + 1), "${c}${r}".format(c=L(hc + 9), r=first)
    h_c = "${c}${r}".format(c=L(hc + 9), r=first + 2)
    # A measure floored at zero keeps zero on the chart. One that is not (a
    # credit score) starts 8% of its range below its lowest value or line:
    # from zero, a score of 380-730 filled the top half and the bands were
    # slivers (Excel 16, the walkthrough, 13 Oct 2026).
    if floor_at_zero:
        asx.cell(first + 1, hc + 9, "=MIN(0,MIN(%s),MIN(%s))" % (axis_r, cuts))
    else:
        mn, mx = "MIN(MIN(%s),MIN(%s))" % (axis_r, cuts), "MAX(MAX(%s),MAX(%s))" % (axis_r, cuts)
        asx.cell(first + 1, hc + 9, "=%s-0.08*(%s-%s)" % (mn, mx, mn))
    asx.cell(first + 2, hc + 9, "=({t}-{lo})*0.06".format(t=top_c, lo=lo_c))
    # Whether the bands and counts can be drawn: the four lines are numbers in
    # their order. Not whether the product is refused: a refused product still
    # shows where its lines fall, which is how the bank sees why (13 Oct 2026:
    # other consumer refused at z 2.5 drew no colour at all, and the dials hid
    # the way out).
    asx.cell(5, hc + 9, "=IF(AND(ISNUMBER(C9),ISNUMBER(C10),ISNUMBER(C11),ISNUMBER(C12),"
                        "{s}*(C10-C9)>=0,{s}*(C11-C10)>=0,{s}*(C12-C11)>=0),1,0)".format(s=sgn))
    for r in range(first, last + 1):
        gone_c = "{c}{r}".format(c=L(hc + 2), r=r)
        # The strip stands on an invisible base just under the floor, and is
        # its own height where a quarter is left out, 0 elsewhere. Drawn as
        # one series from zero, its zeros pulled the axis down to zero.
        asx.cell(r, hc + 13, '={lo}-{h}'.format(lo=lo_c, h=h_c))
        asx.cell(r, hc + 11, '=IF(ISNUMBER({g}),{h},0)'.format(g=gone_c, h=h_c))
    area = AreaChart()
    area.grouping = "stacked"
    area.title = None
    area.height, area.width = 12, 26
    area.add_data(Reference(asx, min_col=hc + 10, max_col=hc + 10, min_row=first - 1, max_row=last),
                  titles_from_data=True)
    area.add_data(Reference(asx, min_col=hc + 4, max_col=hc + 8, min_row=first - 1, max_row=last),
                  titles_from_data=True)
    area.set_categories(Reference(asx, min_col=hc, min_row=first, max_row=last))
    area.series[0].graphicalProperties.noFill = True
    area.series[0].graphicalProperties.line.noFill = True
    for i, s_ in enumerate(area.series[1:]):
        s_.graphicalProperties.solidFill = ("F4F1EC", "E4DFD5", "EFD7CF", "E0A6A6", "CC8080")[order[i]]
        s_.graphicalProperties.line.noFill = True
    # Every quarter as one line, and the quarters left out as grey markers on
    # it. Excel joins a line straight across #N/A, so a "kept" line would draw
    # a false bridge over each period left out; markers are never joined.
    line = LineChart()
    line.add_data(Reference(asx, min_col=hc + 3, max_col=hc + 3, min_row=first - 1, max_row=last),
                  titles_from_data=True)
    line.add_data(Reference(asx, min_col=hc + 2, max_col=hc + 2, min_row=first - 1, max_row=last),
                  titles_from_data=True)
    every, gone = line.series
    every.graphicalProperties.line.solidFill = K.INK
    every.graphicalProperties.line.width = 19050
    gone.graphicalProperties.line.noFill = True
    gone.marker.symbol = "circle"
    gone.marker.size = 5
    gone.marker.graphicalProperties.solidFill = "8A857C"
    gone.marker.graphicalProperties.line.solidFill = "8A857C"
    for s_ in line.series:
        s_.smooth = False
    # The line chart is the base and the bands are added to it. With the area
    # chart as the base, Excel 16 drew no tick labels at all, whatever the
    # axes were given (6 Oct 2026); a line chart's axes draw as on the Chart tab.
    line.height, line.width = 12, 26
    line.x_axis.tickLblSkip = 20
    line.x_axis.delete = False
    line.y_axis.delete = False
    line.y_axis.number_format = "0.0"
    line.legend.position = "t"
    line.visible_cells_only = False
    # The strip is an area, not columns: Excel drew 163 stacked columns sharing
    # this axis as thin slivers whatever their gap width (Excel 16, 6 Oct 2026).
    strip = AreaChart()
    strip.grouping = "stacked"
    asx.cell(first - 1, hc + 13, " ")
    strip.add_data(Reference(asx, min_col=hc + 13, max_col=hc + 13, min_row=first - 1, max_row=last),
                   titles_from_data=True)
    strip.add_data(Reference(asx, min_col=hc + 11, max_col=hc + 11, min_row=first - 1, max_row=last),
                   titles_from_data=True)
    strip.series[0].graphicalProperties.noFill = True
    strip.series[0].graphicalProperties.line.noFill = True
    cut = strip.series[1]
    cut.graphicalProperties.solidFill = "57534B"
    cut.graphicalProperties.line.noFill = True
    # No labels on the strip's negative space, unless the measure itself can
    # go below zero: then those numbers are real and must be labelled.
    below_zero = not floor_at_zero or any(p.value < 0 for s in loaded for p in s["points"])
    line.y_axis.number_format = "0.0" if below_zero else "0.0;;0.0"
    # Excel starts an automatic axis at zero unless the lowest value is within
    # about a sixth of the highest, so a credit score of 380-730 still drew
    # from zero (the walkthrough, 13 Oct 2026). No cell can drive an axis, so
    # a measure not floored at zero gets a fixed minimum at build: just under
    # the lowest value or starting line of any product, at a round number.
    if not floor_at_zero:
        y_min = _axis_floor(loaded, direction, moderate_halfwidth, low_step, high_z)
        if y_min is not None:
            line.y_axis.scaling.min = y_min
            # No fixed axis can follow every leave-out (Codex on #432): leaving
            # out a calm stretch can widen the spread and push a line below it.
            # Say so, in the cell over the chart, rather than clip in silence.
            asx.cell(14, 1, '=IF({f}-{h}<{m},"Part of a line or the left-out strip is below the axis of this chart '
                            '(fixed at build at {m}): the numbers are right, the picture is cut off.","")'
                     .format(f=lo_c, h=h_c, m=y_min)).font = Font(bold=True, color=K.CRIMSON)
    line.x_axis.tickLblPos = "low"                 # year labels below the strip, not on it
    line += area
    line += strip
    asx.add_chart(line, "A15")
    # ---- Assess: the inputs, under the chart ----
    # Periods left out: pick the product and two quarters from lists, say why.
    # Any product, any number of periods up to LO_ROWS. A row that is in use
    # but not whole refuses its product on Thresholds, and its Status says why.
    K.section_band(asx, LO_TOP - 2, "Periods left out: pick the product, the first and last quarter, and say why",
                   11)
    # No merged cells: a row is cleared by selecting it and pressing Delete,
    # which Excel refuses over a merge. Reason and Status run into the empty
    # cells beside them.
    K.header_row(asx, LO_TOP - 1, ["Product", "From", "To", "Reason", "", "", "", "Status", "", "", ""])
    cal = "Data!$A${a}:$A${b}".format(a=first, b=last)
    prod_list = DataValidation(type="list", formula1="=Chart!$A$2:$A$%d" % (1 + n))
    q_list = DataValidation(type="list", formula1="=" + cal)
    for dv_ in (prod_list, q_list):
        asx.add_data_validation(dv_)
    names = "Thresholds!$A$5:$A${e}".format(e=4 + n)
    for r in range(LO_TOP, lo_end + 1):
        for c_ in (1, 2, 3, 4):
            asx.cell(r, c_).fill = INPUT
        prod_list.add("A%d" % r)
        q_list.add("B%d:C%d" % (r, r))
        asx.cell(r, hc + 14, '=IFERROR(MATCH(B{r},{cal},0),"")'.format(r=r, cal=cal))       # Z: From's place
        asx.cell(r, hc + 15, '=IFERROR(MATCH(C{r},{cal},0),"")'.format(r=r, cal=cal))       # AA: To's place
        asx.cell(r, hc + 16, '=IF(AND(ISNUMBER(MATCH(A{r},{nm},0)),ISNUMBER(Z{r}),ISNUMBER(AA{r}),'
                             'Z{r}<=AA{r},TRIM(D{r})<>""),1,0)'.format(r=r, nm=names))       # AB: whole
        asx.cell(r, hc + 17, '=IF(OR(A{r}<>"",B{r}<>"",C{r}<>"",TRIM(D{r})<>""),1,0)'.format(r=r))   # AC: in use
        asx.cell(r, 8, '=IF(AC{r}=0,"",IF(AB{r}=1,"Left out: "&(AA{r}-Z{r}+1)&" quarters",'
                       'IF(NOT(ISNUMBER(MATCH(A{r},{nm},0))),"Pick a product",'
                       'IF(OR(NOT(ISNUMBER(Z{r})),NOT(ISNUMBER(AA{r}))),'
                       '"Pick a first and a last quarter from the list",'
                       'IF(Z{r}>AA{r},"The first quarter must come before the last","Say why")))))'
                 .format(r=r, nm=names))
    asx.cell(lo_end + 1, 1, "Left-out quarters stay on the chart as grey dots over a dark strip; the lines are set "
                            "from the rest. Clear a row (all four cells) to put its quarters back.").font = NOTE
    for c_ in "BCDE":
        asx.column_dimensions[c_].width = max(asx.column_dimensions[c_].width or 0, 12)

    # Your settings: one row per product, the picked one highlighted.
    K.section_band(asx, SET_TOP - 2, "Your settings: one row per product (the product picked above is highlighted)",
                   11)
    K.header_row(asx, SET_TOP - 1, ["Product", "Width of Moderate", "Moderate-Low begins", "How rare High is (z)",
                                    "A value on a line takes the", "", "", "", "", "", ""], right_from=1)
    _wrap(asx, SET_TOP - 1, 46)
    rule_list = DataValidation(type="list", formula1='"worse,better"', allow_blank=False)
    asx.add_data_validation(rule_list)
    for s in loaded:
        rr = srow[s["label"]]
        lg, nx = s["ev"]["largest"], s["ev"]["next_unusual"]
        if lg and nx:
            end_ = lg["end"]
            last_q = grid[grid.index(quarter(end_)) - 1] if end_ else grid[-1]
            say = "Leave out %s to %s" % (quarter(lg["start"]), last_q)
            why = ("Another spell is also unusual (%s, z %.1f), so the largest is not the only stress on record"
                   % (quarter(nx["start"]), nx["robust_z"]))
        else:
            say = "Keep every period"
            why = ("The largest spell (peak %s, z %.1f) is the only unusual one: it is the only evidence of stress"
                   % (quarter(lg["peak_date"]), lg["robust_z"]) if lg else "No spell above the median")
        deps = "; ".join("%s to %s %s (z %+.1f)" % (quarter(d["first"]), quarter(d["last"]),
                                                    d["direction"], d["robust_z"])
                         for d in s["ev"]["departures"]) or "None found"
        asx.cell(rr, 1, s["label"])
        for c_, v in ((2, moderate_halfwidth), (3, low_step), (4, high_z), (5, on_the_line)):
            asx.cell(rr, c_, v).fill = INPUT
        rule_list.add("E%d" % rr)
        for c_, v in ((hc + 18, say), (hc + 19, deps), (hc + 20, why)):             # AD, AE, AF: the evidence
            asx.cell(rr, c_, v)
    asx.conditional_formatting.add("A{a}:E{b}".format(a=SET_TOP, b=set_end),
                                   FormulaRule(formula=["$A{a}=$B$4".format(a=SET_TOP)], fill=PICKED))
    good, bad = ("below", "above") if higher else ("above", "below")
    expl = [
        "What each setting does",
        "Width of Moderate: how far either side of the middle of history counts as normal, in typical yearly "
        "moves (how much the measure ordinarily changes in a year). 0.5 is half a year's movement each way. "
        "Raise it and more quarters rate Moderate.",
        "Moderate-Low begins: how far %s the middle score 2 starts, in the same units; it must be more than the "
        "width. Raise it and fewer quarters rate Low." % good,
        "How rare High is: High begins this many spreads %s the middle (a robust z: 2.5 is rare, 3.5 is the "
        "usual line for an outlier). Raise it and fewer quarters rate High." % bad,
        "A value on a line: whether a quarter exactly on a line takes the worse score or the better.",
        "Leaving a period out takes it out of the middle, the typical move and the spread, so the lines come "
        "from the quarters you count as representative. The dials further down show each setting at other values.",
    ]
    # Each note spans the tab's width and wraps, rather than running off it.
    for i, t in enumerate(expl):
        c = asx.cell(expl_top + i, 1, t)
        c.font = Font(bold=True) if i == 0 else NOTE
        if i:
            asx.merge_cells(start_row=expl_top + i, start_column=1, end_row=expl_top + i, end_column=11)
            c.alignment = Alignment(wrap_text=True, vertical="top")
            asx.row_dimensions[expl_top + i].height = 26
    ev_row = "MATCH($B$4,$A${a}:$A${b},0)".format(a=SET_TOP, b=set_end)
    asx.cell(ev_top, 1, '="What the evidence says about "&$B$4').font = Font(bold=True)
    for i, (lbl, col) in enumerate((("Suggested", hc + 18), ("Temporary departures", hc + 19), ("Why", hc + 20))):
        asx.cell(ev_top + 1 + i, 1, lbl).font = Font(bold=True, size=9)
        asx.cell(ev_top + 1 + i, 2, '=IFERROR(INDEX(${c}${a}:${c}${b},{m}),"")'
                 .format(c=L(col), a=SET_TOP, b=set_end, m=ev_row)).font = NOTE

    # ---- Assess: scenarios. What changes as quarters are left out or a
    # setting moves, side by side and live (the bank, 13 Oct 2026: "a few
    # different views in assess for charts that show what changes", and "i
    # dont want to flip back and forth"). Nothing here is an input.
    K.section_band(asx, scen_top, "Scenarios: what your choices change, for the product picked above", 11)
    K.header_row(asx, scen_top + 1, ["", "2 from", "3 from", "4 from", "5 from",
                                      "Low", "Mod-Low", "Moderate", "Mod-High", "High", ""], right_from=1)
    th_all = lambda c_: "INDEX(Thresholds!${c}$5:${c}${e},{m})".format(c=c_, e=4 + n, m=tr)   # noqa: E731
    med_a, move_a, spread_a = th_all("Q"), th_all("S"), th_all("T")
    all_lines = ["{m}-{s}*{ls}*{mv}".format(m=med_a, s=sgn, ls=LS, mv=move_a),
                 "{m}-{s}*{hw}*{mv}".format(m=med_a, s=sgn, hw=HW, mv=move_a),
                 "{m}+{s}*{hw}*{mv}".format(m=med_a, s=sgn, hw=HW, mv=move_a),
                 "{m}+{s}*{hz}*{sp}".format(m=med_a, s=sgn, hz=HZ, sp=spread_a)]
    ra, rb = scen_top + 2, scen_top + 3
    asx.cell(ra, 1, "As you have it")
    asx.cell(rb, 1, "Keeping every quarter")
    for i in range(4):
        asx.cell(ra, 2 + i, "=IFERROR(C%d+0,\"\")" % (9 + i))
        asx.cell(rb, 2 + i, '=IFERROR(%s,"")' % all_lines[i])
    for i in range(5):
        asx.cell(ra, 6 + i, "=E%d" % (8 + i))
    # Every quarter scored on the every-quarter lines, under the same on-the-line rule.
    b_ = ["%s%d" % (c_, rb) for c_ in "BCDE"]
    for k in range(5):
        parts = []
        if k > 0:
            parts.append('{d},IF({o}="worse",{w},{bt})&{ref}'.format(d=raw_r, o=online, w=ge[0], bt=lt[0],
                                                                      ref=b_[k - 1]))
        if k < 4:
            parts.append('{d},IF({o}="worse",{w},{bt})&{ref}'.format(d=raw_r, o=online, w=ge[1], bt=lt[1],
                                                                      ref=b_[k]))
        asx.cell(rb, 6 + k, '=IF(COUNT(B{r}:E{r})<4,"",COUNTIFS({p}))'.format(r=rb, p=",".join(parts)))
    for rr_ in (ra, rb):
        for c_ in range(2, 6):
            asx.cell(rr_, c_).number_format = "0.000"
    asx.cell(rb + 1, 1, "Keeping every quarter: the same settings, with nothing left out. Counts are quarters "
                        "kept (as you have it) and every quarter (keeping every quarter).").font = NOTE

    # Chart: the history, with the lines both ways. Solid: as you have it.
    # Dashed: keeping every quarter. Eight flat series in hidden columns.
    sc0 = hc + 21                                          # AG onward
    names_ = ["2 from", "3 from", "4 from", "5 from"]
    for i in range(4):
        asx.cell(first - 1, sc0 + i, "%s (yours)" % names_[i])
        asx.cell(first - 1, sc0 + 4 + i, "%s (all kept)" % names_[i])
    for r in range(first, last + 1):
        for i in range(4):
            asx.cell(r, sc0 + i, '=IF(ISNUMBER($%s$%d),$%s$%d,NA())' % (L(2 + i), ra, L(2 + i), ra))
            asx.cell(r, sc0 + 4 + i, '=IF(ISNUMBER($%s$%d),$%s$%d,NA())' % (L(2 + i), rb, L(2 + i), rb))
    cmp_ = LineChart()
    cmp_.title = "Your leave-outs against keeping every quarter"
    cmp_.add_data(Reference(asx, min_col=hc + 3, max_col=hc + 3, min_row=first - 1, max_row=last),
                  titles_from_data=True)
    cmp_.add_data(Reference(asx, min_col=sc0, max_col=sc0 + 7, min_row=first - 1, max_row=last),
                  titles_from_data=True)
    cmp_.set_categories(Reference(asx, min_col=hc, min_row=first, max_row=last))
    hues = ("8A857C", "C9A227", "D9822B", "B03A2E")      # one colour per line, both ways
    cmp_.series[0].graphicalProperties.line.solidFill = K.INK
    cmp_.series[0].graphicalProperties.line.width = 19050
    for i, s_ in enumerate(cmp_.series[1:]):
        s_.graphicalProperties.line.solidFill = hues[i % 4]
        s_.graphicalProperties.line.width = 15875
        if i >= 4:
            s_.graphicalProperties.line.dashStyle = "dash"
    for s_ in cmp_.series:
        s_.smooth = False
    cmp_.height, cmp_.width = 10, 26
    cmp_.x_axis.tickLblSkip = 20
    cmp_.x_axis.delete = False
    cmp_.y_axis.delete = False
    cmp_.y_axis.number_format = "0.0"
    cmp_.legend.position = "r"
    cmp_.legend.overlay = False
    cmp_.visible_cells_only = False
    if line.y_axis.scaling.min is not None:
        cmp_.y_axis.scaling.min = line.y_axis.scaling.min
    asx.add_chart(cmp_, "A%d" % (scen_top + 6))

    # One chart per setting: how many quarters kept fall in each score at each
    # value the dial tries. Read from the dial tables further down.
    for j, (title, first_row) in enumerate(dial_rows):
        bc = BarChart()
        bc.type = "col"
        bc.grouping = "stacked"
        bc.overlap = 100
        bc.title = "Quarters in each score, by " + title.split(",")[0].replace("'s", "") + " (last bar: yours)"
        bc.add_data(Reference(asx, min_col=6, max_col=10, min_row=first_row - 1, max_row=first_row + 4),
                    titles_from_data=True)
        bc.set_categories(Reference(asx, min_col=1, min_row=first_row, max_row=first_row + 4))
        for i, s_ in enumerate(bc.series):
            s_.graphicalProperties.solidFill = ("F4F1EC", "E4DFD5", "EFD7CF", "E0A6A6", "CC8080")[i]
            s_.graphicalProperties.line.solidFill = "8A857C"
        bc.height, bc.width = 8.5, 7.9
        bc.legend.position = "b"
        bc.legend.overlay = False
        bc.x_axis.delete = False
        bc.y_axis.delete = False
        asx.add_chart(bc, "%s%d" % (("A", "E", "I")[j], scen_top + 25))
    for col in range(hc, hc + 29):
        asx.column_dimensions[L(col)].hidden = True
    asx.column_dimensions["A"].width = 21

    # ---- Evidence (values) ----
    r = K.brand_banner(evs, 1, 8, "Evidence for each judgement",
                       "Robust z of each spell's peak against every period outside it (3.5 = unusual; "
                       "Iglewicz and Hoaglin, 1993). Distances from history, not probabilities.")
    for s in loaded:
        ev = s["ev"]
        r = K.section_band(evs, r + 1, s["label"], 8)
        r = K.header_row(evs, r, ["Spell from", "Peak quarter", "Peak", "Peak ÷ median", "Robust z",
                                  "Years per spell this bad", "Deepest dip (sd of quarterly change)", "Note"])
        _wrap(evs, r - 1, 46)
        for sp in ev["spells"]:
            evs.append([quarter(sp["start"]), quarter(sp["peak_date"]), sp["peak"],
                        sp["peak_over_median"], sp["robust_z"], sp["return_period_years"],
                        sp["dip"]["in_sd_of_change"] if sp["dip"] else None, sp["note"]])
            for col, fmt in ((3, "0.000"), (4, "0.00"), (5, "0.0"), (6, "0.0"), (7, "0.0")):
                evs.cell(evs.max_row, col).number_format = fmt
        r = K.header_row(evs, evs.max_row + 1, ["Temporary departure: first quarter", "Last quarter",
                                                "Direction", "Mean off the path", "Robust z",
                                                "Rank among windows of its length", "Window (quarters)", ""])
        _wrap(evs, r - 1, 62)
        for d in ev["departures"]:
            evs.append([quarter(d["first"]), quarter(d["last"]), d["direction"], d["mean_departure"],
                        d["robust_z"], "1 of %d" % d["of"], d["length"]])
            evs.cell(evs.max_row, 4).number_format = "0.000"
            evs.cell(evs.max_row, 5).number_format = "0.0"
        r = evs.max_row
    evs.column_dimensions["A"].width = 58
    for col in "BCDEFGH":
        evs.column_dimensions[col].width = 13
    evs.column_dimensions["C"].width = 16

    # ---- Backtest (values) ----
    # One mean-change column per score: one more score than percentiles.
    n_scores = len(percentiles) + 1
    width = 4 + n_scores
    r = K.brand_banner(bts, 1, width, "How predictive would the scale have been?",
                       "Each quarter scored on cutoffs at percentiles %s of the history up to and including it "
                       "(nothing after it), then "
                       "compared with %d quarters later. Change after a score: the mean change over those "
                       "quarters, in the measure's own units. Overlapping windows: description, not proof."
                       % ("/".join("%g" % p for p in percentiles), horizon))
    for s in loaded:
        r = K.section_band(bts, r + 1, s["label"], width)
        r = K.header_row(bts, r, ["Weighting", "Spearman: score vs level ahead", "Spearman: score vs change ahead",
                                  "Change after 1"] + ["after %d" % k for k in range(2, n_scores + 1)]
                         + ["Quarters tested"])
        _wrap(bts, r - 1, 46)
        for run_ in s["bt"]["runs"]:
            bts.append(["none" if run_["half_life_years"] is None else "%g-yr half-life" % run_["half_life_years"],
                        run_["score_vs_level_ahead"], run_["score_vs_change_ahead"],
                        *[b["mean_change_ahead"] for b in run_["by_score"]], run_["periods_tested"]])
            for col in range(2, 4 + n_scores):
                bts.cell(bts.max_row, col).number_format = "0.00"
        r = bts.max_row
    bts.column_dimensions["A"].width = 18
    for col in range(2, width + 1):
        bts.column_dimensions[L(col)].width = 15

    # ---- Glossary ----
    K.brand_banner(gl, 1, 3, "Glossary",
                   "What each term means, and exactly how the workbook calculates it.")
    K.header_row(gl, 4, ["Term", "What it means", "How it is calculated"])
    for term, meaning, calc in TERMS:
        gl.append([term, meaning, calc])
        for c_ in range(1, 4):
            gl.cell(gl.max_row, c_).alignment = Alignment(wrap_text=True, vertical="top")
        gl.cell(gl.max_row, 1).font = Font(bold=True)
    for c_, w in zip("ABC", (30, 60, 80)):
        gl.column_dimensions[c_].width = w
    K.freeze_below(gl, 4)

    # ---- Run ----
    run.append(["threshold-engine", VERSION])
    run.append(["Built", dt.datetime.now().isoformat(timespec="seconds")])
    if smoothing > 1:
        run.append(["Smoothing", "The Data tab holds each file's values as a trailing mean over %d quarters, "
                    "dated at the last; the first %d quarters of each file have no full window and are not "
                    "used. Every line, score and test is built from those values." % (smoothing, smoothing - 1)])
    run.append(["Measure", name, unit, direction, "smoothing %d" % smoothing,
                "floor at zero" if floor_at_zero else "no floor"])
    run.append(["Scale, starting values", "Moderate half-width %g" % moderate_halfwidth,
                "Moderate-Low step %g" % low_step, "High z %g" % high_z,
                "on the line: %s" % on_the_line])
    run.append(["Backtest half-lives", ", ".join("%g" % h for h in half_lives) or "none"])
    run.append(["Backtest settings", "percentiles %s" % "/".join("%g" % p for p in percentiles),
                "horizon %d" % horizon, "min history %d" % min_history])
    run.append([])
    run.append(["Product", "File", "SHA-256", "Rows", "First", "Last"])
    for s in loaded:
        run.append([s["label"], str(s["path"]), _sha(s["path"]), len(s["raw"]),
                    s["raw"][0].date, s["raw"][-1].date])
    run.append([])
    run.append(["Periods left out, as on Assess (live)", "Product", "From", "To", "Reason", "Status"])
    for r in range(LO_TOP, lo_end + 1):
        run.append([""] + ['=IF(Assess!{c}{r}="","",Assess!{c}{r})'.format(c=c_, r=r) for c_ in "ABCD"]
                   + ["=Assess!H%d" % r])
    run.append([])
    run.append(["Your settings, as on Assess (live)", "Width of Moderate", "Moderate-Low begins",
                "How rare High is (z)", "A value on a line takes the"])
    for s in loaded:
        run.append([s["label"]] + ["=Assess!%s%d" % (c_, srow[s["label"]]) for c_ in "BCDE"])
    run.column_dimensions["A"].width = 30
    run.column_dimensions["B"].width = 60
    run.column_dimensions["C"].width = 66
    run.column_dimensions["D"].width = 18
    run.column_dimensions["E"].width = 60

    out = Path(out)
    wb.save(out)
    return {"path": out, "products": [s["label"] for s in loaded], "quarters": len(grid),
            "evidence": {s["label"]: s["ev"] for s in loaded}}
