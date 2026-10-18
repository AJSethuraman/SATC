"""The Signals tab: every public signal found in the October 2026
early-warning work, laid beside the book's own series, compared against
whichever product, measure and source the analyst picks, with the peer
group recorded beside every chart that draws on it.

The specification is the mock-up the analyst reviewed three times on 18 Oct
2026 (``docs/early-warning-2026-10/record/signals-mock.html``). Three
sheets:

- **Signals** (shown): the controls, where the dollars are, 30+ incl.
  nonaccrual for every product, 30+ to charge-off and the gap, the pipeline,
  then one section per signal with the raw series, the picked series, the
  two rescaled and slid, the inputs of the rescale, the fit table and the
  peer panel.
- **Signals data** (shown, far right): the public series behind the tab,
  one column each, on the book's calendar, with each one's source.
- **Signals workings** (hidden): the formulas. The picked series is looked up
  on Data by its label; each signal's change over a year, its normal (the
  median of the quarters in the window) and its typical yearly move (1.4826
  times the median absolute deviation of its yearly changes, ``scale.py``'s
  rule) are columns; the fit tables are CORREL over the two series' yearly
  changes at every lead from four quarters after to twelve ahead.

Everything that depends on the pick, the window, the shift or Banks in the
pack is a formula. Nothing is rated here; the tab shows, the analyst decides
on Decide.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple

from openpyxl.chart import AreaChart, LineChart, Reference
from openpyxl.chart.series import SeriesLabel
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation

from . import keybank_style as K

TITLE, DATA_TITLE, WORK_TITLE = "Signals", "Signals data", "Signals workings"
LEADS = list(range(-4, 13))
WINDOWS = ("All quarters", "Without 2020-23")
FIT_AUTO = "fits best"
OUT_FROM, OUT_TO = "2020Q1", "2023Q4"
YES = "Yes"
F_BODY = Font(name="Calibri", size=11, color=K.INK_TEXT)
F_BOLD = Font(name="Calibri", size=11, bold=True, color=K.INK_TEXT)
F_NOTE = Font(name="Calibri", size=10, color=K.SLATE)
F_LAB = Font(name="Arial", size=9, bold=True, color=K.SLATE)
F_HEAD = Font(name="Arial", size=11, bold=True, color=K.INK)
INPUT = PatternFill("solid", fgColor=K.INPUT, bgColor=K.INPUT)
HAIR = Side(style="thin", color=K.MIST)

#: The fixed series every fit table compares against: (product, measure, source) of the book.
FIT_TARGETS = (
    ("Credit card", "Net charge-offs", "Industry (every bank)"),
    ("Credit card", "Net charge-offs", "KeyBank"),
    ("Other consumer", "Net charge-offs", "Industry (every bank)"),
    ("Other consumer", "Net charge-offs", "KeyBank"),
    ("Credit card", "30-89 days past due", "Industry (every bank)"),
    ("Other consumer", "30+ days past due incl. nonaccrual", "KeyBank"),
    ("Mortgage", "90+ days past due incl. nonaccrual", "Industry (every bank)"),
    ("Home equity", "90+ days past due incl. nonaccrual", "Industry (every bank)"),
)
#: The signal sections, in order: (key in Signals data, section title, what it is, kind: level or change,
#: the peer panel kind, the fit's own units format).
SIGNALS = (
    ("fico_keycorp", "Refreshed FICO", "KeyCorp: share of scored card balances with a refreshed FICO under 660, from its 10-Qs; the peers that cut at 660 beside it on Signals data", "level", "fico", "0.0"),
    ("minpay", "Paying only the minimum", "Share of active card accounts at the large banks whose payment was only the minimum due", "level", "y14", "0.0"),
    ("util90", "Stretched utilization", "Utilization of the most stretched tenth of active card accounts at the large banks (90th percentile)", "level", "y14", "0.0"),
    ("pv660", "Purchase volume by low-score accounts", "Average purchase volume per card account scored under 660 (large banks); the fit reads its change over a year, in %", "level", "y14", "#,##0"),
    ("easing", "Underwriting: banks easing card standards", "Net share of banks reporting easier card standards (Senior Loan Officer Survey); above zero, more banks eased", "change", "survey", "0.0"),
    ("score10", "Underwriting: who got new accounts", "Credit score of the weakest tenth of new card accounts (large banks); lower is looser", "level", "y14", "0"),
    ("ltv90", "Mortgage: equity", "Share of outstanding mortgages owing more than 90% of the home's value (FHFA NMDB, all lenders)", "level", "nmdb", "0.0"),
)
PANELS = {
    "fico": "Stated, from filings: each holding company's 10-Q where it cuts its FICO table at 660. Not drawn: the other peers (no table at 660). Does not follow Banks in the pack.",
    "y14": "Stated: the bank holding companies that file FR Y-14M (assets of $100bn and over), as the Philadelphia Fed publishes them. An industry panel, not our peer group; no KeyBank figure.",
    "survey": "Stated: the Federal Reserve's Senior Loan Officer Opinion Survey, about 60 large domestic banks named by the Fed. Not our peer group.",
    "nmdb": "Stated: FHFA's National Mortgage Database, a 5% sample of every first-lien mortgage in the U.S., all lenders. Not a bank panel.",
}
PRODUCTS = ("Credit card", "Other consumer", "Home equity", "Mortgage", "Auto")
DQ30 = "30+ days past due incl. nonaccrual"
DQ90 = "90+ days past due incl. nonaccrual"
DQ_KEY_30 = "30+ incl. nonaccrual"                 # the measure's name on Peers delinquency data


def _q(s: str) -> str:
    return s.replace('"', '""')


def _sheet(title: str) -> str:
    return "'%s'!" % title.replace("'", "''")


def _ln(hex_, w=None, dash=None):
    from .assess_tab import _ln as ln
    return ln(hex_, w, dash)


def _line_chart(title, ws_from, cats, cols: Sequence[Tuple[int, str, str, float, Optional[str]]], first, last,
                y_title="", y_min=None, y_max=None, height=7.2, width=15.5, fmt=None):
    """A line chart over rows ``first..last`` of ``ws_from``: ``cols`` are
    (column, series name, color, width, dash)."""
    from .assess_tab import _quiet_axes, _text
    ch = LineChart()
    ch.title = None
    ch.varyColors = False                                  # one series: a legend entry per quarter otherwise
    ch.height, ch.width = height, width
    ch.legend.position = "t"
    ch.legend.txPr = _text(8)
    for col, name, color, w, dash in cols:
        ref = Reference(ws_from, min_col=col, min_row=first, max_row=last)
        ch.add_data(ref, titles_from_data=False)
        s_ = ch.series[-1]
        s_.tx = SeriesLabel(v=name)
        s_.graphicalProperties.line = _ln(color, w, dash)
        s_.smooth = False
        s_.marker.symbol = "none"
    ch.set_categories(Reference(ws_from, min_col=cats, min_row=first, max_row=last))
    _quiet_axes(ch, 16)
    ch.x_axis.tickLblPos = "low"
    ch.caption = y_title                                                 # written above the chart by chart_at
    if y_min is not None:
        ch.y_axis.scaling.min = y_min
    if y_max is not None:
        ch.y_axis.scaling.max = y_max
    if fmt:
        ch.y_axis.number_format = fmt
        ch.y_axis.numFmt.sourceLinked = False
    ch.display_blanks_as = "gap"
    return ch


def layout_rows(n_quarters: int) -> dict:
    return {"first": 2, "last": 1 + n_quarters}


def build(wb, *, labels: Sequence[str], parts: Dict[str, Tuple[str, str, str]], grid: Sequence[str],
          signals: dict, peers: Sequence[dict], include: Dict[str, str], peers_sheet: str,
          data_sheet: str, dq_sheet: str, self_short: str, latest: str) -> dict:
    """Add Signals, Signals data and Signals workings to ``wb`` (which holds
    Data, Peers data and Peers delinquency data). ``signals`` is what
    ``signals_data.load`` returned; ``peers`` the roster's peers (short
    names) with ``include`` their Yes/No cells on the Peers tab (A1, without
    the sheet); ``latest`` the last quarter on the calendar."""
    R0, R1 = 2, 1 + len(grid)
    N = len(grid)
    F06 = R0 + (grid.index("2006Q1") if "2006Q1" in grid else 0)         # the first row charts draw from
    F11 = R0 + (grid.index("2011Q1") if "2011Q1" in grid else 0)
    by_key = {k: (t, u, d) for k, t, u, d in signals["series"]}
    sources = signals["sources"]
    present = {lbl: parts[lbl] for lbl in labels}
    inv = {v: k for k, v in present.items()}
    DA = _sheet(data_sheet)
    PE = _sheet(peers_sheet)
    PD = _sheet("Peers data")
    DD = _sheet(dq_sheet)

    # ---------------------------------------------------------------- Signals data
    sd = wb.create_sheet(DATA_TITLE)
    sd.sheet_properties.tabColor = K.TAB_DATA
    sd.cell(1, 1, "Quarter").font = F_LAB
    keys = [k for k, _, _, _ in signals["series"]]
    kcol = {k: 2 + i for i, k in enumerate(keys)}
    for i, q in enumerate(grid):
        sd.cell(R0 + i, 1, q)
    for k, title, unit, d in signals["series"]:
        c = kcol[k]
        sd.cell(1, c, k).font = F_LAB
        for i, q in enumerate(grid):
            if q in d:
                sd.cell(R0 + i, c, d[q])
    # the series, described, to the right of the values
    sc = 2 + len(keys) + 1
    for j, h in enumerate(("Key", "What it is", "Unit", "Quarters")):
        sd.cell(1, sc + j, h).font = F_LAB
    for i, (k, title, unit, d) in enumerate(signals["series"]):
        sd.cell(2 + i, sc, k); sd.cell(2 + i, sc + 1, title); sd.cell(2 + i, sc + 2, unit)
        sd.cell(2 + i, sc + 3, "%d, %s to %s" % (len(d), min(d), max(d)) if d else "none")
    r = 3 + len(signals["series"])
    sd.cell(r, sc, "Sources").font = F_HEAD
    for i, (what, file, sha) in enumerate(sources):
        sd.cell(r + 1 + i, sc, what); sd.cell(r + 1 + i, sc + 1, file); sd.cell(r + 1 + i, sc + 2, sha)
    sd.column_dimensions[L(sc + 1)].width = 90
    sd.freeze_panes = "B2"

    # ---------------------------------------------------------------- Signals: the controls
    ws = wb.create_sheet(TITLE)
    ws.sheet_properties.tabColor = K.TAB_WORK
    ws.sheet_view.showGridLines = False
    widths = {"A": 1.57, "B": 38, "C": 24, "D": 22, "E": 14, "F": 16, "G": 14, "H": 14, "I": 14, "J": 14,
              "K": 14, "L": 14, "M": 14, "N": 14, "O": 14, "P": 14, "Q": 14, "R": 14, "S": 4, "T": 30, "U": 46}
    for c_, w in widths.items():
        ws.column_dimensions[c_].width = w
    K.light_title(ws, 1, 20, "Signals · every signal found, compared against any series in the book",
                  "Pick what to compare against in the yellow cells. Every chart below lays that series over a signal; every fit "
                  "table shows the signal against the same eight series whatever is picked. The banks behind each chart are beside it.",
                  first_col=2)
    products = sorted({p for p, _, _ in present.values()}, key=lambda p: list(PRODUCTS).index(p) if p in PRODUCTS else 99)
    measures = list(dict.fromkeys(m for _, m, _ in present.values()))
    srcs = list(dict.fromkeys(s for _, _, s in present.values()))
    for j, (lab, start) in enumerate((("Compare against: product", "Other consumer"), ("Measure", DQ30),
                                      ("Source", self_short), ("Shift the signal by (quarters)", FIT_AUTO),
                                      ("Window for the normal", WINDOWS[0]))):
        ws.cell(4, 2 + j, lab).font = F_LAB
        c = ws.cell(5, 2 + j, start)
        c.fill = INPUT; c.font = F_BOLD
        c.border = Border(top=HAIR, bottom=HAIR, left=HAIR, right=HAIR)
    lists_at = 2 + len(keys) + 6                                           # on Signals data, out of the way
    for j, items in enumerate((products, measures, srcs)):
        col = lists_at + j
        sd.cell(1, col, ("Products", "Measures", "Sources")[j]).font = F_LAB
        for i, v in enumerate(items):
            sd.cell(2 + i, col, v)
        dv = DataValidation(type="list", formula1="=%s$%s$2:$%s$%d" % (_sheet(DATA_TITLE), L(col), L(col), 1 + len(items)),
                            allow_blank=False)
        ws.add_data_validation(dv)
        dv.add("%s5" % L(2 + j))
    dv = DataValidation(type="list", formula1='"%s,0,1,2,3,4,5,6,7,8,9,10,11,12"' % FIT_AUTO, allow_blank=False)
    ws.add_data_validation(dv); dv.add("E5")
    dv = DataValidation(type="list", formula1='"%s"' % ",".join(WINDOWS), allow_blank=False)
    ws.add_data_validation(dv); dv.add("F5")
    SG = _sheet(TITLE)
    # The controls, as every other sheet's formula must name them: a bare $B$5 on
    # the workings would be the workings' own B5 (found the hard way, 18 Oct 2026:
    # a circular reference and an empty picked series).
    P_, M_, S_, SH, WIN = (SG + "$B$5", SG + "$C$5", SG + "$D$5", SG + "$E$5", SG + "$F$5")
    LBL = '%s&" - "&%s&" - "&%s' % (P_, M_, S_)
    ws.cell(4, 7, "Picked").font = F_LAB
    ws.cell(5, 7, "=%s" % LBL).font = F_BODY
    ws.merge_cells("G5:J5")
    ws.cell(4, 11, "In the book?").font = F_LAB
    ws.cell(5, 11, '=IF(ISNUMBER(MATCH(%s,%s$1:$1,0)),"yes","no such series: pick another")' % (LBL, DA)).font = F_BODY
    ws.merge_cells("K5:N5")
    ws.cell(4, 15, "Banks in the pack").font = F_LAB
    # A bank is in the pack when Peers data says so now (its In the pack now
    # column follows the picker and each bank's Yes/No/Pack on Peers).
    in_pack = ['COUNTIFS({pd}$B:$B,"{b}",{pd}$P:$P,TRUE)>0'.format(pd=PD, b=_q(b["short"])) for b in peers]
    ws.cell(5, 15, '=(%s)&" of %d, from Peers"' % ("+".join("(%s)" % c for c in in_pack), len(peers))).font = F_BODY
    ws.merge_cells("O5:R5")
    ws.cell(6, 2, "Any product, measure and source the book holds. The window sets which quarters the normal and the typical yearly move "
                  "are taken from. Banks in the pack is set on Peers and followed here.").font = F_NOTE
    ws.merge_cells("B6:R6")

    # ---------------------------------------------------------------- Signals workings
    wk = wb.create_sheet(WORK_TITLE)
    wk.sheet_state = "hidden"
    WK = _sheet(WORK_TITLE)
    col = {"q": 1}
    nxt = [2]

    def take(name, n=1):
        col[name] = nxt[0]; nxt[0] += n
        return col[name]

    def A(name, r, j=0):
        return "%s%d" % (L(col[name] + j), r)

    def R(name, j=0):
        return "$%s$%d:$%s$%d" % (L(col[name] + j), R0, L(col[name] + j), R1)

    def RW(name, j=0):
        return WK + R(name, j)

    for i, q in enumerate(grid):
        wk.cell(R0 + i, 1, q)
    wk.cell(1, 1, "Quarter")
    QN = lambda r: "$A%d" % r                                                          # noqa: E731
    sig_q = "%s$A$%d:$A$%d" % (WK, R0, R1)
    out_window = lambda r: 'AND(%s="%s",%s>="%s",%s<="%s")' % (WIN, WINDOWS[1], QN(r), OUT_FROM, QN(r), OUT_TO)   # noqa: E731

    def series_block(name, value_formula, change: str = "diff"):
        """Columns for one series: value, change over a year, value in the
        window, change in the window, absolute deviation of that change, and
        the standardized value (its z). ``change`` 'diff' or 'pct'."""
        c0 = take(name, 8)
        heads = ("value", "change over a year", "value, in the window", "change, in the window", "deviation of the change", "z",
                 "change, without 2020-23", "value, without 2020-23")
        for j, h in enumerate(heads):
            wk.cell(1, c0 + j, "%s: %s" % (name, h))
        v, ch, vw, cw, dev, z = (L(c0 + j) for j in range(6))
        for r in range(R0, R1 + 1):
            wk.cell(r, c0, value_formula(r))
            if r - 4 >= R0:
                if change == "pct":
                    wk.cell(r, c0 + 1, '=IF(AND(ISNUMBER({v}{r}),ISNUMBER({v}{p}),{v}{p}<>0),100*({v}{r}/{v}{p}-1),"")'.format(v=v, r=r, p=r - 4))
                else:
                    wk.cell(r, c0 + 1, '=IF(AND(ISNUMBER({v}{r}),ISNUMBER({v}{p})),{v}{r}-{v}{p},"")'.format(v=v, r=r, p=r - 4))
            else:
                wk.cell(r, c0 + 1, '=""')
            wk.cell(r, c0 + 2, '=IF(OR({ow},NOT(ISNUMBER({v}{r}))),"",{v}{r})'.format(ow=out_window(r), v=v, r=r))
            wk.cell(r, c0 + 3, '=IF(OR({ow},NOT(ISNUMBER({c}{r}))),"",{c}{r})'.format(ow=out_window(r), c=ch, r=r))
            wk.cell(r, c0 + 4, '=IF(ISNUMBER({cw}{r}),ABS({cw}{r}-MEDIAN({cwr})),"")'.format(cw=cw, r=r, cwr=R(name, 3)))
            wk.cell(r, c0 + 5, '=IF(AND(ISNUMBER({v}{r}),COUNT({vw})>0,MEDIAN({dv})>0),({v}{r}-MEDIAN({vw}))/(1.4826*MEDIAN({dv})),"")'
                    .format(v=v, r=r, vw=R(name, 2), dv=R(name, 4)))
            # the fit table's "without 2020-23" always leaves those quarters out, whatever the window control says
            wk.cell(r, c0 + 6, '=IF(OR(AND({q}>="{a}",{q}<="{b}"),NOT(ISNUMBER({c}{r}))),"",{c}{r})'
                    .format(q=QN(r), a=OUT_FROM, b=OUT_TO, c=ch, r=r))
            wk.cell(r, c0 + 7, '=IF(OR(AND({q}>="{a}",{q}<="{b}"),NOT(ISNUMBER({v}{r}))),"",{v}{r})'
                    .format(q=QN(r), a=OUT_FROM, b=OUT_TO, v=v, r=r))
        return c0

    # the picked series, looked up on Data by its label
    picked = series_block("picked", lambda r: '=IFERROR(IF(INDEX(%s$%d:$%d,1,MATCH(%s,%s$1:$1,0))="","",INDEX(%s$%d:$%d,1,MATCH(%s,%s$1:$1,0))),"")'
                          % (DA, r, r, LBL, DA, DA, r, r, LBL, DA))
    # the fixed fit targets
    targets = []
    for p, m, s in FIT_TARGETS:
        lbl = " - ".join((p, m, s))
        if lbl not in present:
            continue
        name = "t%d" % len(targets)
        c0 = series_block(name, lambda r, lbl=lbl: '=IFERROR(IF(INDEX(%s$%d:$%d,1,MATCH("%s",%s$1:$1,0))="","",INDEX(%s$%d:$%d,1,MATCH("%s",%s$1:$1,0))),"")'
                          % (DA, r, r, _q(lbl), DA, DA, r, r, _q(lbl), DA))
        targets.append((name, "%s %s, %s" % (p, m.lower() if m != "Net charge-offs" else "net charge-offs", s.replace(" (every bank)", "").replace(" (15 banks)", "")), lbl))
    # each signal, from Signals data, plus the shifted z
    SDt = _sheet(DATA_TITLE)

    def sd_value(key):
        c = L(kcol[key])
        return lambda r: '=IF(%s$%s%d="","",%s$%s%d)' % (SDt, c, r, SDt, c, r)

    sig_cols = {}
    for key, title, what, kind, panel, fmt in SIGNALS:
        c0 = series_block(key, sd_value(key), "pct" if key == "pv660" else "diff")
        sig_cols[key] = c0
    # the where-the-dollars-are workings: per product, by the source picked
    for p in PRODUCTS:
        slug = re.sub(r"[^a-z0-9]+", "-", p.lower()).strip("-")
        c0 = take("dollars_" + slug, 3)
        for j, (k, head) in enumerate((("bal", "balance"), ("gco4", "gross charge-offs, 4q"), ("d30", "30+ incl. nonaccrual"))):
            wk.cell(1, c0 + j, "%s: %s, source picked" % (p, head))
            kb, ind = "keybank_%s_%s" % (slug, k), "industry_%s_%s" % (slug, k)
            kbc = L(kcol[kb]) if kb in kcol else None
            inc = L(kcol[ind]) if ind in kcol else None
            for r in range(R0, R1 + 1):
                if k == "bal":
                    pack = 'SUMIFS({pd}$N:$N,{pd}$A:$A,"{p}",{pd}$D:$D,{q},{pd}$P:$P,TRUE)'.format(pd=PD, p=_q(p), q=QN(r))
                elif k == "gco4":
                    pack = 'SUMIFS({pd}$E:$E,{pd}$A:$A,"{p}",{pd}$D:$D,{q},{pd}$J:$J,TRUE,{pd}$P:$P,TRUE)'.format(pd=PD, p=_q(p), q=QN(r))
                else:
                    pack = 'SUMIFS({dd}$F:$F,{dd}$A:$A,"{p}",{dd}$B:$B,"{m}",{dd}$E:$E,{q},{dd}$O:$O,TRUE)'.format(dd=DD, p=_q(p), m=DQ_KEY_30, q=QN(r))
                kb_v = ('IF({s}$%s%d="","",{s}$%s%d)' % (kbc, r, kbc, r)).format(s=SDt) if kbc else '""'
                in_v = ('IF({s}$%s%d="","",{s}$%s%d)' % (inc, r, inc, r)).format(s=SDt) if inc else '""'
                wk.cell(r, c0 + j, '=IF({src}="{me}",{kb},IF(LEFT({src},10)="Peer group",IF({pk}=0,"",{pk}),IF({src}="Industry (every bank)",{ind},"")))'
                        .format(src=S_, me=_q(self_short), kb=kb_v, pk=pack, ind=in_v))
    # the gap: KeyBank minus peers, card 30+ to charge-off, and its parts for the shading
    co_lbl = {s: " - ".join(("Credit card", "30+ to charge-off", s)) for s in srcs}
    c0 = take("gap", 4)
    for j, h in enumerate(("KeyBank card 30+ to charge-off", "peer group card 30+ to charge-off", "gap, points", "gap above zero", "gap below zero")):
        if j < 4:
            wk.cell(1, c0 + j, h)
    take("gap_neg", 1); wk.cell(1, col["gap_neg"], "gap below zero")
    take("gap_priced", 1); wk.cell(1, col["gap_priced"], "gap priced: gap x KeyBank's delinquent card dollars / 4 ($000)")
    kb_l = next((l for l in present if present[l] == ("Credit card", "30+ to charge-off", self_short)), None)
    pg_l = next((l for l in present if present[l][:2] == ("Credit card", "30+ to charge-off") and present[l][2].startswith("Peer group")), None)
    for r in range(R0, R1 + 1):
        for j, lbl in ((0, kb_l), (1, pg_l)):
            wk.cell(r, c0 + j, ('=IFERROR(IF(INDEX(%s$%d:$%d,1,MATCH("%s",%s$1:$1,0))="","",INDEX(%s$%d:$%d,1,MATCH("%s",%s$1:$1,0))),"")'
                                % (DA, r, r, _q(lbl), DA, DA, r, r, _q(lbl), DA)) if lbl else '=""')
        a, b = A("gap", r, 0), A("gap", r, 1)
        wk.cell(r, c0 + 2, '=IF(AND(ISNUMBER({a}),ISNUMBER({b})),{a}-{b},"")'.format(a=a, b=b))
        wk.cell(r, c0 + 3, '=IF(ISNUMBER({g}),MAX({g},0),"")'.format(g=A("gap", r, 2)))
        wk.cell(r, col["gap_neg"], '=IF(ISNUMBER({g}),MIN({g},0),"")'.format(g=A("gap", r, 2)))
        dk_ = "keybank_credit-card_d30"
        if dk_ in kcol:
            dv_ = "%s$%s%d" % (SDt, L(kcol[dk_]), r)
            wk.cell(r, col["gap_priced"], '=IF(AND(ISNUMBER({g}),ISNUMBER({d})),{g}/100*{d}/4,"")'.format(g=A("gap", r, 2), d=dv_))
        else:
            wk.cell(r, col["gap_priced"], '=""')
    # shifted z per signal: the signal's z moved k quarters later, k from the shift cell or the best fit
    shift_cells = {}
    for key, *_ in SIGNALS:
        c0 = take(key + "_zs", 1)
        wk.cell(1, c0, "%s: z, slid" % key)
    # fit grids: per signal, 17 leads x targets (+ the picked), all quarters and without 2020-23
    FIT0 = R1 + 4
    fit_at = {}
    tcols = [(name, nice, lbl) for name, nice, lbl in targets] + [("picked", "the picked series", None)]
    for si, (key, title, what, kind, panel, fmt) in enumerate(SIGNALS):
        top = FIT0 + si * (len(LEADS) + 4)
        fit_at[key] = top
        wk.cell(top, 1, "%s: fit by lead, all quarters" % key).font = F_LAB
        wk.cell(top, 2 + len(tcols) + 1, "%s: fit by lead, without 2020-23" % key).font = F_LAB
        sig_ch = "change over a year" if kind == "level" else "value"
        for j, (tname, nice, lbl) in enumerate(tcols):
            wk.cell(top + 1, 2 + j, nice); wk.cell(top + 1, 2 + len(tcols) + 2 + j, nice)
        for i, k in enumerate(LEADS):
            r = top + 2 + i
            wk.cell(r, 1, k)
            n = N - abs(k)
            s_off, t_off = max(0, -k), max(0, k)
            for j, (tname, nice, lbl) in enumerate(tcols):
                # a level signal's fit reads its change over a year; a change signal (the survey) its value; the
                # "without 2020-23" fit reads the columns that always leave those quarters out (Codex on #457)
                for g, (sj, tj) in enumerate(((1 if kind == "level" else 0, 1), (6 if kind == "level" else 7, 6))):
                    sig_first = "%s$%s$%d" % (WK, L(col[key] + sj), R0)
                    tgt_first = "%s$%s$%d" % (WK, L(col[tname] + tj), R0)
                    f = '=IFERROR(CORREL(OFFSET(%s,%d,0,%d,1),OFFSET(%s,%d,0,%d,1)),"")' % (sig_first, s_off, n, tgt_first, t_off, n)
                    wk.cell(r, 2 + j + g * (len(tcols) + 2), f)
        # the best lead per target (all quarters), and the shift this signal uses
        rb = top + 2 + len(LEADS)
        wk.cell(rb, 1, "best lead")
        for j in range(len(tcols)):
            rng = "$%s$%d:$%s$%d" % (L(2 + j), top + 2, L(2 + j), top + 1 + len(LEADS))
            wk.cell(rb, 2 + j, '=IFERROR(INDEX($A$%d:$A$%d,MATCH(MAX(%s),%s,0)),"")' % (top + 2, top + 1 + len(LEADS), rng, rng))
            wk.cell(rb, 2 + j + len(tcols) + 2, '=IFERROR(INDEX(%s,MATCH(%s,$A$%d:$A$%d,0)),"")'
                    % ("$%s$%d:$%s$%d" % (L(2 + j + len(tcols) + 2), top + 2, L(2 + j + len(tcols) + 2), top + 1 + len(LEADS)),
                       "%s%d" % (L(2 + j), rb), top + 2, top + 1 + len(LEADS)))
        # the shift used: typed, or the best lead against the picked series, never below zero
        sh = "%s$%s$%d" % (WK, L(2 + len(tcols) - 1), rb)
        wk.cell(rb + 1, 1, "shift used")
        wk.cell(rb + 1, 2, '=IF(ISNUMBER(%s),%s,IF(ISNUMBER(%s),MAX(0,%s),0))' % (SH, SH, sh, sh))
        shift_cells[key] = "%s$B$%d" % (WK, rb + 1)
        zc = col[key + "_zs"]
        for r in range(R0, R1 + 1):
            wk.cell(r, zc, '=IFERROR(IF(INDEX(%s,%d-%s)="","",INDEX(%s,%d-%s)),"")'
                    % (RW(key, 5), r - R0 + 1, shift_cells[key], RW(key, 5), r - R0 + 1, shift_cells[key]))

    # ---------------------------------------------------------------- Signals: the sections
    row = 8
    CH_H = 17                                                              # rows a chart and its caption take

    def section(title, sub):
        nonlocal row
        K.quiet_section(ws, row, title, 20, first_col=2)
        ws.cell(row + 1, 2, sub).font = F_NOTE
        ws.merge_cells(start_row=row + 1, start_column=2, end_row=row + 1, end_column=18)
        row += 2

    def panel(kind, product_cell: Optional[str], top: int, col_: int = 20):
        """The banks behind a chart: live for the Call Report (in, out by the
        rules this quarter, off under Banks in the pack), stated otherwise."""
        ws.cell(top, col_, "Peer group in this chart" if kind == "live" else "Whose data").font = F_LAB
        if kind != "live":
            c = ws.cell(top + 1, col_, PANELS[kind]); c.font = F_NOTE
            c.alignment = Alignment(wrap_text=True, vertical="top")
            ws.merge_cells(start_row=top + 1, start_column=col_, end_row=top + 6, end_column=col_ + 1)
            return
        ws.cell(top, col_ + 1, '="live: follows Banks in the pack on Peers; "&%s' % ws["O5"].value[1:]).font = F_NOTE
        for j, b in enumerate(peers):
            r = top + 1 + j
            ws.cell(r, col_, b["short"]).font = F_BODY
            out = ('COUNTIFS({dd}$A:$A,{p},{dd}$B:$B,"{m}",{dd}$C:$C,"{b}",{dd}$E:$E,"{q}",{dd}$N:$N,TRUE)>0'
                   .format(dd=DD, p=product_cell, m=DQ_KEY_30, b=_q(b["short"]), q=latest))
            ws.cell(r, col_ + 1, '=IF(NOT({inc}),"off: turned off under Banks in the pack",IF({out},"out: its own four-quarter average was blanked this quarter by the jump or the acquisition share","in"))'
                    .format(inc=in_pack[j], out=out)).font = F_NOTE
        ws.cell(top + 1 + len(peers), col_, "Three states: in; out by the book's rules; off because unticked on Peers. "
                                                  "Every quarter's list is on Peers delinquency data.").font = F_NOTE

    def chart_at(ch, r, c):
        cap = getattr(ch, "caption", None)
        if cap:
            ws.cell(r, c, cap).font = F_LAB
        ws.add_chart(ch, "%s%d" % (L(c), r + 1))

    # A. where the dollars are
    section("Where the dollars are", "For the source picked: each product's balance, gross charge-offs over four quarters and 30+ incl. nonaccrual dollars, "
                                      "and its share. The peer group's are summed from Peers data over the banks in the pack; KeyBank's and the industry's from the Call Report at build.")
    heads = ("Product", "Balance ($000)", "share", "Gross charge-offs, 4 qtrs ($000)", "share", "30+ incl. nonaccrual ($000)", "share")
    for j, h in enumerate(heads):
        ws.cell(row, 2 + j, h).font = F_LAB
    rl = R1                                                                # the latest quarter's row on the workings
    tot = {k: "SUM(%s)" % ",".join("%s%s%d" % (WK, L(col["dollars_" + re.sub(r"[^a-z0-9]+", "-", p.lower()).strip("-")] + j), rl) for p in PRODUCTS)
           for j, k in enumerate(("bal", "gco4", "d30"))}
    for i, p in enumerate(PRODUCTS):
        r = row + 1 + i
        ws.cell(r, 2, p).font = F_BODY
        cp = col["dollars_" + re.sub(r"[^a-z0-9]+", "-", p.lower()).strip("-")]
        for j, k in enumerate(("bal", "gco4", "d30")):
            v = "%s%s%d" % (WK, L(cp + j), rl)
            ws.cell(r, 3 + 2 * j, '=IF(%s="","",%s)' % (v, v)).number_format = "#,##0"
            ws.cell(r, 4 + 2 * j, '=IF(OR(%s="",%s=0),"",%s/%s)' % (v, tot[k], v, tot[k])).number_format = "0%"
    r = row + 1 + len(PRODUCTS)
    ws.cell(r, 2, "Consumer, %s" % latest).font = F_BOLD
    for j, k in enumerate(("bal", "gco4", "d30")):
        ws.cell(r, 3 + 2 * j, "=%s" % tot[k]).number_format = "#,##0"; ws.cell(r, 3 + 2 * j).font = F_BOLD
    for rr in range(row, r + 1):
        for cc in range(2, 9):
            ws.cell(rr, cc).border = Border(bottom=HAIR)
    ws.cell(r + 1, 2, '=IF(OR({s}="{me}",LEFT({s},10)="Peer group",{s}="Industry (every bank)"),"","No Call Report dollars for "&{s}&": the table and the charts are blank for this source.")'
            .format(s=S_, me=_q(self_short))).font = F_NOTE
    ws.merge_cells(start_row=r + 1, start_column=2, end_row=r + 1, end_column=18)
    panel("live", P_, row)
    row = r + 2
    for j, (k, title, fmt_) in enumerate((("bal", "balances by product, $000", "#,##0"), ("gco4", "gross charge-offs by product, 4 quarters, $000", "#,##0"),
                                           ("d30", "30+ incl. nonaccrual dollars by product, $000", "#,##0"))):
        cols_ = [(col["dollars_" + re.sub(r"[^a-z0-9]+", "-", p.lower()).strip("-")] + j, p, c_, 1.75, None)
                 for p, c_ in zip(PRODUCTS, (K.KEY_RED, "C8811E", "2F5D50", "4C6B8A", K.STONE))]
        chart_at(_line_chart(title, wk, 1, cols_, F06, R1, y_title=title, fmt=fmt_, width=9.5, height=7.0), row, 2 + 6 * j)
    row += CH_H

    # B. 30+ incl. nonaccrual, every product
    section("30+ incl. nonaccrual, every product", "KeyBank against the peer group and the industry, quarter-end, each product on its own axis.")
    dq_labels = {}
    for p in ("Credit card", "Other consumer", "Mortgage", "Home equity"):
        dq_labels[p] = [(s, " - ".join((p, DQ30, s))) for s in srcs if " - ".join((p, DQ30, s)) in present]
    head = {}
    data_ws = wb[data_sheet]
    for c in range(1, data_ws.max_column + 1):
        head[data_ws.cell(1, c).value] = c
    STYLES = {self_short: (K.KEY_RED, 2.25, None)}

    def style(s):
        if s == self_short:
            return K.KEY_RED, 2.25, None
        if s.startswith("Peer group"):
            return K.INK, 1.5, None
        return K.MEDIAN, 1.5, "dash"

    for i, p in enumerate(("Credit card", "Other consumer", "Mortgage", "Home equity")):
        cols_ = [(head[lbl], s, *style(s)) for s, lbl in dq_labels[p] if lbl in head]
        chart_at(_line_chart(p, data_ws, 1, cols_, F06, 1 + N, y_title="%s %s, %%" % (p, DQ30.lower()), fmt="0.0", width=9.5, height=7.0),
                 row + CH_H * (i // 2), 2 + 6 * (i % 2))
    panel("live", '"Other consumer"', row)
    panel("live", '"Credit card"', row + CH_H + 2)
    row += 2 * CH_H

    # C. 30+ to charge-off and the gap
    section("30+ to charge-off, and the gap to peers", "Of the dollars 30+ (incl. nonaccrual) at quarter-end, the share charged off over the next two quarters: 80% means 80 cents of every "
                                                       "delinquent dollar became a loss within six months. The gap is KeyBank minus the peer group, in points; above zero, more of KeyBank's delinquent dollars became loss.")
    cols_ = [(head[lbl], s, *style(s)) for s, lbl in ((s, co_lbl[s]) for s in srcs) if lbl in head]
    chart_at(_line_chart("card 30+ to charge-off", data_ws, 1, cols_, F11, 1 + N, y_title="card 30+ to charge-off, 4q avg, %", fmt="0", width=9.5, height=7.0), row, 2)
    # the gap: shaded above and below zero, the line over it
    from .assess_tab import _quiet_axes, _text
    area = AreaChart(); area.grouping = "standard"; area.height, area.width = 7.0, 9.5; area.varyColors = False
    for j, (name, color) in enumerate((("above zero: more of KeyBank's delinquent dollars became loss", "FAE0CA"), ("below zero: fewer did", "E9F1E3"))):
        ref = Reference(wk, min_col=(col["gap"] + 3) if j == 0 else col["gap_neg"], min_row=F11, max_row=R1)
        area.add_data(ref, titles_from_data=False)
        s_ = area.series[-1]; s_.tx = SeriesLabel(v=name); s_.graphicalProperties.solidFill = color; s_.graphicalProperties.line.noFill = True
    area.set_categories(Reference(wk, min_col=1, min_row=F11, max_row=R1))
    line = LineChart()
    ref = Reference(wk, min_col=col["gap"] + 2, min_row=F11, max_row=R1)
    line.add_data(ref, titles_from_data=False)
    s_ = line.series[-1]; s_.tx = SeriesLabel(v="KeyBank minus peers, points"); s_.graphicalProperties.line = _ln(K.KEY_RED, 2.25); s_.smooth = False; s_.marker.symbol = "none"
    area += line
    _quiet_axes(area, 16); area.x_axis.tickLblPos = "low"; area.legend.position = "t"; area.legend.txPr = _text(8)
    area.caption = "KeyBank minus peers, card 30+ to charge-off, points (shaded above zero: more of KeyBank's delinquent dollars became loss)"
    area.y_axis.number_format = "+0;-0;0"; area.y_axis.numFmt.sourceLinked = False
    area.display_blanks_as = "gap"
    chart_at(area, row, 8)
    wcols = [(kcol[k], nm, c_, w, d) for k, nm, c_, w, d in (("win1", "next 1 quarter", "2F5D50", 1.5, None), ("win2", "next 2 quarters (the book)", K.INK, 2.25, None), ("win3", "next 3 quarters", "4C6B8A", 1.5, None)) if k in kcol]
    if wcols:
        chart_at(_line_chart("window test", sd, 1, wcols, F11, R1, y_title="industry card: % of 30+ dollars charged off over the next 1, 2, 3 quarters", fmt="0", width=9.5, height=7.0), row, 14)
    # the area priced
    dk = "keybank_credit-card_d30"
    if dk in kcol:
        pr_ = RW("gap_priced")
        ws.cell(row + CH_H, 2, '="The gap priced: gap times KeyBank\'s delinquent card dollars each quarter: "&TEXT(SUM(%s)/1000,"$#,##0")&"m over "&COUNT(%s)&" quarters (negative: less charged off than at the peer group\'s conversion rate)."'
                % (pr_, pr_)).font = F_NOTE
        ws.merge_cells(start_row=row + CH_H, start_column=2, end_row=row + CH_H, end_column=18)
    ws.cell(row + CH_H + 1, 2, "Why two quarters: a card charges off at 180 days past due, so a dollar 30 days late at quarter-end has up to 150 days to go. "
                               "One quarter catches only the 90+ half; three count dollars that were current at the quarter-end.").font = F_NOTE
    panel("live", '"Credit card"', row + CH_H + 3)
    row += CH_H + 3 + len(peers) + 3

    # D. the pipeline
    section("The pipeline: 30+ incl. nonaccrual, then 90+ incl. nonaccrual, then charge-offs",
            "Card, the three levels on one timeline: the level of 30+ runs about three quarters ahead of charge-offs; the steps between them add little once nonaccrual is in both. "
            "Refreshed FICO (next section) turns in the same quarters as 30+.")
    for j, (m, ttl) in enumerate(((DQ30, "1. card 30+ incl. nonaccrual, %"), (DQ90, "2. card 90+ incl. nonaccrual, %"), ("Gross charge-offs", "3. card gross charge-offs, 4 quarters, %"))):
        cols_ = [(head[" - ".join(("Credit card", m, s))], s, *style(s)) for s in srcs if " - ".join(("Credit card", m, s)) in head]
        chart_at(_line_chart(ttl, data_ws, 1, cols_, F11, 1 + N, y_title=ttl, fmt="0.0", width=9.5, height=7.0), row, 2 + 6 * j)
    panel("live", '"Credit card"', row + CH_H)
    row += CH_H + len(peers) + 4

    # E. one section per signal
    tcol_ws = {}
    for key, title, what, kind, pkind, fmt in SIGNALS:
        section(title, what)
        c0 = sig_cols[key]
        # raw signal, the picked series, the two rescaled and slid
        f_sig = F06 if key in ("easing", "ltv90") else F11
        chart_at(_line_chart(title, wk, 1, [(c0, "this signal", "C8811E", 2.0, None)], f_sig, R1, y_title="%s (%s)" % (by_key[key][0][:70], by_key[key][1]), fmt=fmt, width=9.5, height=7.0), row, 2)
        chart_at(_line_chart("picked", wk, 1, [(col["picked"], "the picked series", K.KEY_RED, 2.0, None)], f_sig, R1, y_title="the picked series, own units", fmt="0.00", width=9.5, height=7.0), row, 8)
        chart_at(_line_chart("rescaled", wk, 1, [(col["picked"] + 5, "the picked series", K.KEY_RED, 2.25, None), (col[key + "_zs"], "this signal, slid", "C8811E", 2.0, "dash")],
                             f_sig, R1, y_title="rescaled and slid: yearly moves from each line's own normal (one grid line = one move)", y_min=-4, y_max=4, fmt="+0;-0;0", width=9.5, height=7.0), row, 14)
        r = row + CH_H
        # the inputs of the rescale
        med_s, mv_s = "MEDIAN(%s)" % RW(key, 2), "1.4826*MEDIAN(%s)" % RW(key, 4)
        med_p, mv_p = "MEDIAN(%s)" % RW("picked", 2), "1.4826*MEDIAN(%s)" % RW("picked", 4)
        ws.cell(r, 2, "What the rescaled picture is made of").font = F_LAB
        ws.cell(r + 1, 2, '="This signal: normal "&TEXT(%s,"%s")&", one yearly move "&TEXT(%s,"%s")&", from "&COUNT(%s)&" quarters; slid "&%s&" quarter(s) later ("&IF(ISNUMBER(%s),"typed","the lead that fits the picked series best")&")."'
                % (med_s, fmt, mv_s, fmt, RW(key, 2), shift_cells[key], SH)).font = F_NOTE
        ws.cell(r + 2, 2, '="The picked series: normal "&TEXT(%s,"0.00")&", one yearly move "&TEXT(%s,"0.00")&", from "&COUNT(%s)&" quarters. One grid line on the chart is one typical yearly move for either line; the window is "&%s&"."'
                % (med_p, mv_p, RW("picked", 2), WIN)).font = F_NOTE
        for rr in (r + 1, r + 2):
            ws.merge_cells(start_row=rr, start_column=2, end_row=rr, end_column=18)
        # the fit table
        r += 4
        ws.cell(r, 2, "How this signal fits every loss and delinquency series in the book").font = F_LAB
        for j, h in enumerate(("Compared against", "Fits best", "How well (all quarters)", "Without 2020-23", "Quarters overlapping")):
            ws.cell(r + 1, 2 + j, h).font = F_LAB
        top = fit_at[key]
        rb = top + 2 + len(LEADS)
        for j, (tname, nice, lbl) in enumerate(tcols):
            rr = r + 2 + j
            ws.cell(rr, 2, nice if tname != "picked" else '="the picked series: "&%s' % LBL).font = F_BODY
            best = "%s%s%d" % (WK, L(2 + j), rb)
            rng = "%s$%s$%d:$%s$%d" % (WK, L(2 + j), top + 2, L(2 + j), top + 1 + len(LEADS))
            ws.cell(rr, 3, '=IF(%s="","",IF(%s=0,"same quarter",IF(%s>0,%s&" qtrs ahead",-%s&" qtrs after")))' % (best, best, best, best, best)).font = F_BODY
            ws.cell(rr, 4, '=IFERROR(MAX(%s),"")' % rng).number_format = "0.00"
            ws.cell(rr, 5, '=IF(%s="","",%s)' % ("%s%s%d" % (WK, L(2 + j + len(tcols) + 2), rb), "%s%s%d" % (WK, L(2 + j + len(tcols) + 2), rb))).number_format = "0.00"
            sig_ch_col = col[key] + (1 if kind == "level" else 0)
            tgt_ch_col = col[tname] + 1
            ws.cell(rr, 6, '=SUMPRODUCT(--ISNUMBER(%s),--ISNUMBER(%s))' % (RW(key, 1 if kind == "level" else 0), RW(tname, 1))).number_format = "0"
            for cc in range(2, 7):
                ws.cell(rr, cc).border = Border(bottom=HAIR)
        ws.cell(r + 2 + len(tcols), 2, "Fits best: the lead where the signal's change over a year moves with that series' most. How well: 1.00 moving together exactly, 0 no relation, "
                                       "negative opposite. Above 0.8 is a linkage, 0.5 to 0.8 loose, below 0.5 none worth a rating. 'After' means the signal follows that series.").font = F_NOTE
        ws.merge_cells(start_row=r + 2 + len(tcols), start_column=2, end_row=r + 2 + len(tcols), end_column=18)
        panel(pkind, None, row)
        row = r + 4 + len(tcols)

    # across products: the two series, raw
    section("Across products", "Does early delinquency in one product come before another's? Other consumer 30-89 against mortgage 90+ incl. nonaccrual, the industry. "
                               "Pick Other consumer, 30-89 days past due, Industry above and any mortgage series in the fit tables to read the lead.")
    for j, (p, m) in enumerate((("Other consumer", "30-89 days past due"), ("Mortgage", "30-89 days past due"), ("Mortgage", DQ90))):
        lbl = " - ".join((p, m, "Industry (every bank)"))
        if lbl in head:
            chart_at(_line_chart(lbl, data_ws, 1, [(head[lbl], "%s %s, industry" % (p, m.lower()), K.INK, 2.0, None)], F06, 1 + N, y_title="%s %s, industry, %%" % (p, m.lower()), fmt="0.00", width=9.5, height=7.0), row, 2 + 6 * j)
    row += CH_H
    ws.freeze_panes = "B7"
    return {"sheet": TITLE, "data": DATA_TITLE, "workings": WORK_TITLE, "rows": row, "signals": [k for k, *_ in SIGNALS],
            "fit_targets": [t[2] for t in targets], "controls": {"product": "B5", "measure": "C5", "source": "D5", "shift": "E5", "window": "F5"}}
