"""One run, one workbook: every product's facts, evidence, backtest and live cutoffs.

Python does the statistics once -- spells, robust z-scores, scenarios, recency,
the backtest -- and writes their results as values. The cutoffs are Excel
formulas over the data, driven by the red Settings tab, so the bank's
judgements are made in the workbook and the thresholds move as they are made:

    Settings (red)  which periods to leave out, where score 5 begins, and
                    whether a value on a line takes the worse or better score
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

import csv
import datetime as dt
import hashlib
from pathlib import Path
from typing import Sequence, Tuple

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation

from . import keybank_style as K
from .backtest import backtest
from .engine import VERSION
from .evidence import evidence
from .series import Point

RATINGS = ("Low", "Moderate-Low", "Moderate", "Moderate-High", "High")
INPUT = PatternFill("solid", fgColor="FFF2CC")
NOTE = Font(name="Arial", size=9, italic=True, color=K.SLATE)


def _wrap(ws, row, height=34):
    """Header labels wrap in their column instead of being cut off."""
    for cell in ws[row]:
        if cell.value is not None:
            cell.alignment = Alignment(wrap_text=True, vertical="center",
                                       horizontal=cell.alignment.horizontal or "left")
    ws.row_dimensions[row].height = height


def quarter(date: str) -> str:
    """'2010-04-01' and '2010-06-30' are both 2010Q2."""
    return "%sQ%d" % (date[:4], (int(date[5:7]) - 1) // 3 + 1)


def read_series(path: Path):
    with open(path, encoding="utf-8") as fh:
        rows = csv.DictReader(line for line in fh if not line.startswith("#"))
        return [Point(r["date"], float(r["value"])) for r in rows]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(out: Path, series: Sequence[Tuple[str, Path]], name: str, unit: str,
          direction: str, frequency: str, smoothing: int, floor_at_zero: bool,
          top_fraction: float, on_the_line: str, half_lives: Sequence[float],
          percentiles: Sequence[float], horizon: int, min_history: int) -> dict:
    if frequency != "quarterly":
        raise ValueError("the workbook's calendar is quarterly; monthly series are not built yet")
    if on_the_line not in ("worse", "better"):
        raise ValueError("on_the_line must be 'worse' or 'better'")
    if len({lbl for lbl, _ in series}) != len(series):
        raise ValueError("two series share a label")
    higher = direction == "higher_is_worse"

    loaded = []
    for label, path in series:
        pts = read_series(Path(path))
        ev = evidence(pts, label, unit, direction, frequency, smoothing, 5,
                      top_fraction, floor_at_zero, half_lives)
        bt = backtest(pts, label, unit, direction, frequency, smoothing, percentiles,
                      horizon, min_history, floor_at_zero, half_lives)
        by_q = {quarter(p.date): p.value for p in pts}
        if len(by_q) != len(pts):
            raise ValueError("%s has two observations in one quarter" % label)
        loaded.append(dict(label=label, path=Path(path), points=pts, ev=ev, bt=bt, by_q=by_q))
    grid = sorted(set().union(*(s["by_q"] for s in loaded)))
    n, first, last = len(loaded), 2, len(grid) + 1

    wb = Workbook()
    th = wb.active
    th.title = "Thresholds"
    st, ch, evs, bts, da, run = (wb.create_sheet(t) for t in
                                 ("Settings", "Chart", "Evidence", "Backtest", "Data", "Run"))
    st.sheet_properties.tabColor = K.KEY_RED
    for ws in (th, st, ch, evs, bts, run):
        K.hide_gridlines(ws)

    # ---- Data: one calendar, raw values, and the values each product keeps ----
    da.append(["Quarter"] + [s["label"] for s in loaded] + ["%s, kept" % s["label"] for s in loaded])
    srow = {s["label"]: 6 + i for i, s in enumerate(loaded)}       # Settings row per product
    for r, q in enumerate(grid, start=2):
        da.cell(r, 1, q)
        for k, s in enumerate(loaded):
            raw = L(2 + k)
            if q in s["by_q"]:
                da.cell(r, 2 + k, s["by_q"][q])
            sr = srow[s["label"]]
            da.cell(r, 2 + n + k,
                    '=IF({raw}{r}="","",IF(AND(Settings!$B${sr}<>"",$A{r}>=Settings!$B${sr},'
                    '$A{r}<=Settings!$C${sr}),"",{raw}{r}))'.format(raw=raw, r=r, sr=sr))
    K.freeze_below(da, 1)

    # ---- Settings (red): the bank's judgements ----
    r = K.brand_banner(st, 1, 7, "Settings — the bank's judgements",
                       "Yellow cells are yours. The Thresholds and Chart tabs recalculate as you change them.")
    st.cell(4, 1, "Leave a period out by typing its first and last quarter (e.g. 2007Q4 and 2012Q4). "
                  "Blank keeps every period.").font = NOTE
    K.header_row(st, 5, ["Product", "Leave out from", "Leave out to", "Score 5 begins (share of the way from normal to worst)",
                         "A value on a line takes the", "What the evidence says", "Why"])
    _wrap(st, 5, 46)
    dv = DataValidation(type="list", formula1='"worse,better"', allow_blank=False)
    st.add_data_validation(dv)
    for s in loaded:
        rr = srow[s["label"]]
        c = s["ev"]["scenarios"][2]
        lg = s["ev"]["largest"]
        if c["removed"]:
            end = c["removed"][1]
            last_q = grid[grid.index(quarter(end)) - 1] if end else grid[-1]
            say = "Leave out %s to %s" % (quarter(c["removed"][0]), last_q)
            why = "Another spell is also unusual (%s); 2008-sized losses are not the only stress on record" % c["decided_by"]
        else:
            say = "Keep every period"
            why = ("The largest spell (peak %s, z %.1f) is the only unusual one: it is the only evidence of stress"
                   % (quarter(lg["peak_date"]), lg["robust_z"]) if lg else "No spell above the median")
        vals = [s["label"], None, None, top_fraction, on_the_line, say, why]
        for col, v in enumerate(vals, start=1):
            cell = st.cell(rr, col, v)
            if col in (2, 3, 4, 5):
                cell.fill = INPUT
        dv.add("E%d" % rr)
    for col, w in zip("ABCDEFG", (22, 14, 14, 26, 14, 34, 70)):
        st.column_dimensions[col].width = w
    st.cell(srow[loaded[-1]["label"]] + 2, 1,
            "The cutoffs: score 2 begins at the median of the periods kept; score 5 begins the stated share of "
            "the way to the worst period kept; scores 3 and 4 are equal steps between.").font = NOTE

    # ---- Thresholds: live ----
    K.brand_banner(th, 1, 13, "%s — candidate thresholds" % name,
                   "Live: recalculates from the Settings tab. Candidates for the bank to accept, adjust or reject.")
    K.header_row(th, 4, ["Product", "Normal (median kept)", "Worst kept", "2 Moderate-Low from", "3 Moderate from",
                         "4 Moderate-High from", "5 High from", "Latest quarter", "Latest (%s)" % unit,
                         "Score", "Rating", "Check"], right_from=1)
    _wrap(th, 4, 46)
    for k, s in enumerate(loaded):
        r = 5 + k
        sr = srow[s["label"]]
        kept = "Data!$%s$%d:$%s$%d" % (L(2 + n + k), first, L(2 + n + k), last)
        th.cell(r, 1, s["label"])
        th.cell(r, 2, "=MEDIAN(%s)" % kept)
        th.cell(r, 3, "=%s(%s)" % ("MAX" if higher else "MIN", kept))
        th.cell(r, 12, '=IF(AND(%s,B{r}<=0),"Refused: normal level at or below zero",'
                       'IF(C{r}=B{r},"Refused: nothing worse than normal",""))'.format(r=r)
                       % ("TRUE" if floor_at_zero and higher else "FALSE"))
        for i in range(4):
            th.cell(r, 4 + i, '=IF($L{r}<>"","",$B{r}+{i}*Settings!$D${sr}*($C{r}-$B{r})/3)'
                    .format(r=r, i=i, sr=sr))
        lp = s["points"][-1]
        th.cell(r, 8, quarter(lp.date))
        th.cell(r, 9, lp.value)
        op_worse, op_better = ("<=", "<") if higher else (">=", ">")
        bounds = "$D{r}:$G{r}".format(r=r)
        floor = "AND(I{r}<=0,{f})".format(r=r, f="TRUE" if floor_at_zero and higher else "FALSE")
        th.cell(r, 10, '=IF($L{r}<>"","",IF({floor},1,1+IF(Settings!$E${sr}="worse",'
                       'COUNTIF({b},"{w}"&I{r}),COUNTIF({b},"{bt}"&I{r}))))'
                .format(r=r, floor=floor, sr=sr, b=bounds, w=op_worse, bt=op_better))
        th.cell(r, 11, '=IF(J{r}="","",CHOOSE(J{r},"{0}","{1}","{2}","{3}","{4}"))'.format(*RATINGS, r=r))
        for col in range(2, 8):
            th.cell(r, col).number_format = "0.000"
        th.cell(r, 9).number_format = "0.000"
    for col, w in zip("ABCDEFGHIJKL", (20, 12, 11, 12, 12, 12, 12, 10, 10, 7, 15, 34)):
        th.column_dimensions[col].width = w
    th.cell(6 + n, 1, "Scores: 1 Low, 2 Moderate-Low, 3 Moderate, 4 Moderate-High, 5 High. A loss at or below "
                      "zero is always Low." if floor_at_zero and higher else
                      "Scores: 1 Low, 2 Moderate-Low, 3 Moderate, 4 Moderate-High, 5 High.").font = NOTE

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
    pv = DataValidation(type="list", formula1='"(none),%s"' % ",".join(s["label"] for s in loaded))
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
                    .format(c=L(4 + i), e=4 + n, p=lr))
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
    lc.visible_cells_only = False      # its helper columns are hidden; plot them anyway
    ch.add_chart(lc, "A%d" % (lr + 3))
    for col in range(h0, h0 + n + 5):
        ch.column_dimensions[L(col)].hidden = True

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
        r = evs.max_row + 1
        r = K.header_row(evs, r, ["Scenario", "Normal", "Worst kept", "2 from", "3 from", "4 from", "5 from",
                                  "Latest score"])
        for sc in ev["scenarios"]:
            evs.append([sc["scenario"], sc["normal"], sc["worst_kept"], *sc["bounds"], sc["latest_score"]])
        for rc in ev["recency"]:
            evs.append(["C, normal weighted, %g-yr half-life (%.0f effective quarters)"
                        % (rc["half_life_years"], rc["effective_quarters"]), rc["normal"],
                        rc.get("worst_kept"), *(rc.get("bounds") or [None] * 4),
                        rc.get("latest_score", rc.get("refused"))])
        for row in evs.iter_rows(min_row=r, max_row=evs.max_row, min_col=2, max_col=7):
            for cell in row:
                cell.number_format = "0.000"
        r = evs.max_row
    evs.column_dimensions["A"].width = 58
    for col in "BCDEFGH":
        evs.column_dimensions[col].width = 13

    # ---- Backtest (values) ----
    r = K.brand_banner(bts, 1, 9, "How predictive would the scale have been?",
                       "Each quarter scored on cutoffs at percentiles %s of only the history before it, then "
                       "compared with %d quarters later. Overlapping windows: description, not proof."
                       % ("/".join("%g" % p for p in percentiles), horizon))
    for s in loaded:
        r = K.section_band(bts, r + 1, s["label"], 9)
        r = K.header_row(bts, r, ["Weighting", "Spearman: score vs level ahead", "Spearman: score vs change ahead",
                                  "Change after 1", "after 2", "after 3", "after 4", "after 5", "Quarters tested"])
        _wrap(bts, r - 1, 46)
        for run_ in s["bt"]["runs"]:
            bts.append(["none" if run_["half_life_years"] is None else "%g-yr half-life" % run_["half_life_years"],
                        run_["score_vs_level_ahead"], run_["score_vs_change_ahead"],
                        *[b["mean_change_ahead"] for b in run_["by_score"]], run_["periods_tested"]])
            for col in range(2, 9):
                bts.cell(bts.max_row, col).number_format = "0.00"
        r = bts.max_row
    bts.column_dimensions["A"].width = 18
    for col in "BCDEFGHI":
        bts.column_dimensions[col].width = 15

    # ---- Run ----
    run.append(["threshold-engine", VERSION])
    run.append(["Built", dt.datetime.now().isoformat(timespec="seconds")])
    run.append(["Measure", name, unit, direction, "smoothing %d" % smoothing,
                "floor at zero" if floor_at_zero else "no floor"])
    run.append(["Evidence settings", "top fraction %g" % top_fraction, "on the line: %s" % on_the_line,
                "half-lives %s" % (", ".join("%g" % h for h in half_lives) or "none")])
    run.append(["Backtest settings", "percentiles %s" % "/".join("%g" % p for p in percentiles),
                "horizon %d" % horizon, "min history %d" % min_history])
    run.append([])
    run.append(["Product", "File", "SHA-256", "Rows", "First", "Last"])
    for s in loaded:
        run.append([s["label"], str(s["path"]), _sha(s["path"]), len(s["points"]),
                    s["points"][0].date, s["points"][-1].date])
    run.column_dimensions["A"].width = 18
    run.column_dimensions["B"].width = 60
    run.column_dimensions["C"].width = 66

    out = Path(out)
    wb.save(out)
    return {"path": out, "products": [s["label"] for s in loaded], "quarters": len(grid),
            "evidence": {s["label"]: s["ev"] for s in loaded}}
