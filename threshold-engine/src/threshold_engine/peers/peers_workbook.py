"""The peer workbook: KeyBank against its peers, from public FDIC Call Reports.

docs/PEERS-SPEC.md, "peers_workbook.py", is the contract. Python works out
every bank's books once (``books.bank_book``) and writes them to the Data tab
as values. The comparisons are Excel formulas over that tab, driven by the red
Pack tab, so the bank's choices are made in the workbook and the lines move as
they are made:

    Pack (red)      which peers are in the pack (Include), the product drawn,
                    Peer A and Peer B (any peer, best or worst in pack), how
                    best and worst are ranked, and how many banks a composite
                    or band needs
    Peers           gross and net charts for the product picked: the pack band
                    (10th-90th, 25th-75th), the pack composite, KeyBank, Peer
                    A and Peer B, and who best and worst resolved to -- live
    Delinquency     the same chart for delinquency and nonaccrual, with its
                    own product, measure and basis pickers, over the same
                    Include cells, Peer A and Peer B -- live (or a line saying
                    it was not built)
    Balances       each bank's book as an index, as reported and without
                    acquisitions, and its acquisition quarters (values)
    Lagged          a year's losses over the book lent earlier (values)
    Normalisation   how far each rate moved between two years (values)
    Mix             KeyBank's move against the industry's (values)
    Glossary        every term, and how it is calculated
    Data            per bank, product and quarter: the TTM flows, average
                    balance, rates, kept and why
    DelinquencyData per product, measure, bank and quarter-end: numerator,
                    balance, quarter-end rate, four-quarter average, kept and
                    why (``peers.delinquency``, docs/V1-ROUND2-SPEC.md, A)
    Run            sources, when each cache file was pulled, fingerprints,
                    the acquisitions record, roster and the rules as stated

Lessons from ``workbook.py`` kept here: a chart combining lines and areas has
the LineChart as its base (with an AreaChart base Excel 16 drew no tick
labels); helper columns sit apart from anything visible, are hidden, and the
charts plot them anyway (``visible_cells_only = False``); no formula refers to
a row above row 1. Excel joins a line straight across #N/A, which would draw a
false bridge over quarters not kept, so every chart here is also told to show
#N/A as a gap (Excel 2016+'s ``dispNaAsBlank``; see :func:`_na_as_gap`).

The band is drawn as up-down bars between two invisible lines (10th to 90th,
then 25th to 75th), not as a stacked area: an area cannot leave a gap, so
Excel drew it falling to 0 at every quarter without a band and the band
appeared to reach 0% beside each gap (seen in Excel, 12 Oct 2026). An up-down
bar is drawn only where both its ends have a value, and it spans negative
rates as well as positive ones.

Public data only. Every setting that is a judgement is a required argument.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.chart.axis import ChartLines
from openpyxl.chart.series import SeriesLabel
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.chart.updown_bars import UpDownBars
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation

from .. import VERSION
from .. import keybank_style as K
from . import roster as R
from .analyses import calendar_year, lagged_rate, normalisation, organic_index, mix_factor
from . import delinquency as D
from .books import PRODUCTS, _fields, bank_book, composite, label, quarter_end
from .glossary import PEER_TERMS

INPUT = PatternFill("solid", fgColor="FFF2CC")
SELF_FILL = PatternFill("solid", fgColor=K.ALERT_FG)
NOTE = Font(name="Arial", size=9, italic=True, color=K.SLATE)
WORST, BEST = "Worst in pack", "Best in pack"
PACKS = ("all", "regionals")
SOURCES = ("FDIC BankFind financials: https://banks.data.fdic.gov/api/financials",
           "FDIC BankFind structure changes: https://banks.data.fdic.gov/api/history")

# Pack tab layout.
P_PRODUCT, P_A, P_B, P_KIND, P_LASTN, P_MINOBS, P_MINBANKS = (4, 5, 6, 7, 8, 9, 10)
P_BEST, P_WORST = 11, 12
P_HEAD = 14                       # the peers' header row; peers from the row below
P_HELP = 10                       # hidden list columns start at J

# Peers tab layout: helpers from column T, hidden, apart from the charts.
H0 = 20
H_HEAD = 10                       # helper header row; quarters from the row below

# Delinquency tab layout: the pickers in column B, the helpers as on Peers.
D_PRODUCT, D_MEASURE, D_BASIS = 4, 5, 6
D_CHART = 11                      # the chart's top row
D_TABLE = 38                      # the visible table's header row, under the chart
#: What ``delinquency`` must name when the tabs are built; nothing is defaulted.
D_KEYS = ("data", "products", "jump", "min_book", "exempt_self", "acquired", "measure", "basis")
NOT_BUILT = ("Delinquency was not built for this workbook: the build was told not to "
             "(delinquency=None, or --delinquency no).")


def _wrap(ws, row, height=34):
    """Header labels wrap in their column instead of being cut off."""
    for cell in ws[row]:
        if cell.value is not None:
            cell.alignment = Alignment(wrap_text=True, vertical="center",
                                       horizontal=cell.alignment.horizontal or "left")
    ws.row_dimensions[row].height = height


def _fingerprint(data: Dict[str, list]) -> str:
    """SHA-256 of the pull as canonical JSON: the same rows give the same print."""
    blob = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _na_as_gap(path: Path) -> None:
    """Tell every chart in the file to show #N/A as a gap, not to join across it.

    openpyxl cannot write the option, so it is added to each chart's XML as
    Excel 2016+ writes it (``c16r3:dataDisplayOptions16/dispNaAsBlank`` in the
    extLst that closes ``<c:chart>``), with ``dispBlanksAs="gap"`` already set
    by openpyxl. Older Excel ignores it."""
    ext = ('<extLst><ext uri="{56B9EC1D-385E-4148-901F-78D8002777C0}" '
           'xmlns:c16r3="http://schemas.microsoft.com/office/drawing/2017/03/chart">'
           '<c16r3:dataDisplayOptions16><c16r3:dispNaAsBlank val="1"/>'
           '</c16r3:dataDisplayOptions16></ext></extLst>')
    chart_ns = 'xmlns="http://schemas.openxmlformats.org/drawingml/2006/chart"'
    tmp = path.with_suffix(path.suffix + ".tmp")
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            body = zin.read(item.filename)
            if re.match(r"xl/charts/chart\d+\.xml$", item.filename):
                text = body.decode("utf-8")
                if "dispNaAsBlank" not in text:
                    # openpyxl writes the chart namespace as the default one;
                    # Excel keeps this option in the extLst closing <chart>.
                    if chart_ns not in text or text.count("</chart>") != 1 or "</extLst></chart>" in text:
                        raise RuntimeError("unexpected chart XML in %s" % item.filename)
                    text = text.replace("</chart>", ext + "</chart>")
                body = text.encode("utf-8")
            zout.writestr(item, body)
    tmp.replace(path)


def _line_chart(title: str, height=12, width=26) -> LineChart:
    lc = LineChart()
    lc.title = title
    lc.height, lc.width = height, width
    lc.x_axis.delete = False
    lc.y_axis.delete = False
    lc.y_axis.number_format = "0.0"
    lc.legend.position = "t"
    lc.legend.overlay = False              # without it Excel draws the legend over the plot
    lc.display_blanks = "gap"
    lc.visible_cells_only = False          # its helper columns are hidden; plot them anyway
    return lc


def _band(ws, lo_col: int, hi_col: int, first_row: int, last_row: int, fill: str, names) -> LineChart:
    """One band as up-down bars between two invisible lines, lo and hi.

    Excel draws an up-down bar from a chart group's first series to its last,
    and only where both have a value, so a quarter without a band is a gap
    rather than a wedge down to 0. ``names`` labels the two lines in the
    legend (the low one blank, so the band is named once)."""
    lc = LineChart()
    for c, name in zip((lo_col, hi_col), names):
        lc.add_data(Reference(ws, min_col=c, min_row=first_row, max_row=last_row), titles_from_data=False)
        s_ = lc.series[-1]
        s_.tx = SeriesLabel(v=name)
        s_.smooth = False
        s_.graphicalProperties.line.noFill = True
        s_.marker.symbol = "none"
    lc.upDownBars = UpDownBars(gapWidth=0)
    for which in ("upBars", "downBars"):
        gp = GraphicalProperties(solidFill=fill)
        gp.line.noFill = True
        setattr(lc.upDownBars, which, ChartLines(spPr=gp))
    return lc


def _written(path: Path) -> str:
    """When a cache file was last written, i.e. pulled: its modification time, local, to the second."""
    return dt.datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")


def _whole_at_least_1(name: str, value) -> None:
    """A count setting must be a whole number of at least 1 (a bool is not one)."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("%s must be a whole number of at least 1, not %r" % (name, value))


def _acquisitions(mergers: Dict[str, Sequence[str]], extras: Dict[str, Sequence[str]], cert: str):
    """The bank's acquisition quarters as (quarter, declared?) in date order."""
    found = {quarter_end(q): False for q in mergers.get(cert, [])}
    for q in extras.get(cert, []):
        found.setdefault(quarter_end(q), True)
    return [(label(d.replace("-", "")), found[d]) for d in sorted(found)]


def _check_delinquency(spec: Optional[dict], roster: List[dict], me: dict) -> Optional[dict]:
    """None for no delinquency tabs; otherwise the stated settings, checked,
    with every bank's rows worked out once (``delinquency.bank_delinquency``,
    per product, measure and bank) under ``books`` and the quarter-ends under
    ``grid``.

    Refused (ValueError), each with its reason, whatever the type of the
    value given: anything but None or a dict; a key missing or not known
    (every one is a judgement or the data, so none is filled in); products
    that are not distinct names from ``delinquency.FIELDS``; a measure or
    basis that is not one of the names the module builds; ``exempt_self``
    that is not True or False; a jump or minimum book that is not a number
    (a bool or a string is not one) or is below 0 (refused by the module);
    data that is not ``{REPDTE: [rows]}``, or has no quarter; a quarter with
    no rows (nobody filed, which is not a field missing); and a field of a
    product absent from every row of a quarter. That last is a field that was
    not pulled, which is not the same as a field not filed (a blank value,
    which the module reads as not filed): ``fdic.pull`` refuses the same."""
    if spec is None:
        return None
    if not isinstance(spec, dict):
        raise ValueError("delinquency must be None (not built) or a dict of %s, not %r" % (", ".join(D_KEYS), spec))
    missing = [k for k in D_KEYS if k not in spec]
    unknown = sorted(k for k in spec if k not in D_KEYS)
    if missing or unknown:
        raise ValueError("delinquency needs exactly %s; %s" % (", ".join(D_KEYS), "; ".join(
            x for x in ("missing: " + ", ".join(missing) if missing else "",
                        "not known: " + ", ".join(unknown) if unknown else "") if x)))
    products = list(spec["products"]) if not isinstance(spec["products"], str) else [spec["products"]]
    if not products or any(p not in D.FIELDS for p in products) or len(set(products)) != len(products):
        raise ValueError("delinquency products must be distinct names from %s, not %r"
                         % (list(D.FIELDS), spec["products"]))
    if not isinstance(spec["measure"], str) or spec["measure"] not in D.MEASURES:
        raise ValueError("delinquency measure must be one of %s, not %r" % (list(D.MEASURES), spec["measure"]))
    if not isinstance(spec["basis"], str) or spec["basis"] not in D.BASES:
        raise ValueError("delinquency basis must be one of %s, not %r" % (list(D.BASES), spec["basis"]))
    if not isinstance(spec["exempt_self"], bool):
        raise ValueError("delinquency exempt_self must be True or False, not %r" % (spec["exempt_self"],))
    for name in ("jump", "min_book"):
        if isinstance(spec[name], bool) or not isinstance(spec[name], (int, float)):
            raise ValueError("delinquency %s must be a number, not %r" % (name, spec[name]))
    if not isinstance(spec["acquired"], dict) or any(p not in spec["acquired"] for p in products):
        raise ValueError("delinquency acquired must be {product: {cert: [quarter-ends]}} for every "
                         "product, not %r" % (spec["acquired"],))
    data = spec["data"]
    if not isinstance(data, dict):
        raise ValueError("delinquency data must be {REPDTE: [rows]} as fdic.pull returns it, not a %s"
                         % type(data).__name__)
    if not data:
        raise ValueError("delinquency data has no quarter-ends, so nothing can be drawn")
    empty = [q for q in sorted(data) if not data[q]]
    if empty:
        raise ValueError("delinquency data has no rows (no filer) in %d quarter(s), first %s: a quarter-end "
                         "nobody filed cannot be drawn; pull it again or leave it out" % (len(empty), empty[0]))
    for p in products:
        for f in D.FIELDS[p]:
            lacking = [q for q in sorted(data) if not any(f in row for row in data[q])]
            if lacking:
                raise ValueError("delinquency for %s needs %s, which the data does not carry in %d quarter(s), "
                                 "first %s: pull it with the delinquency fields" % (p, f, len(lacking), lacking[0]))
    books = {p: {m: {b["cert"]: D.bank_delinquency(data, b["cert"], p, m, spec["jump"], spec["min_book"],
                                                   spec["exempt_self"] and b is me,
                                                   acquired=spec["acquired"][p].get(b["cert"], []))
                     for b in roster} for m in D.MEASURES} for p in products}
    grid = [r["q"] for r in books[products[0]][spec["measure"]][me["cert"]]]
    return dict(spec, products=products, books=books, grid=grid)


def _delinquency_tabs(de, dd, dq: dict, roster: List[dict], me: dict, peers: List[dict],
                      first_peer: int, all_banks: str) -> dict:
    """Write DelinquencyData (values) and the live Delinquency tab over it.

    DelinquencyData holds one row per product, measure (``delinquency.MEASURES``
    order), bank (roster order) and quarter-end, in that order: the live
    formulas find a row by position, so the order is load-bearing. Each row is
    ``bank_delinquency``'s, plus whether the four-quarter average was kept and
    whether the jump blanked it, so no formula has to read a blank cell (Excel
    reads one as 0).

    On Delinquency, three yellow pickers (product, measure, basis) and the
    Pack tab's Include cells, Peer A and Peer B and banks needed drive hidden
    helpers from column T, one row per quarter-end:

    - per bank: kept on the quarter-end basis, and its value on the basis
      picked (#N/A when there is none);
    - per peer, filtered by Include: the numerator and balance when kept
      (for the composite) and the value on the basis (for the band);
    - the composite: summed numerators / summed balances of the included
      peers kept, #N/A below the banks needed; its four-quarter average at i
      is the mean of the four composite quarter-end rates i-3..i, each
      recomputed without the peers whose own four-quarter average at i the
      jump blanked, only when all four exist on consecutive quarter-ends and
      each has the banks needed (``composite_delinquency``);
    - the band: PERCENTILE of the included peers' values on the basis, #N/A
      below the banks needed (``band_delinquency``);
    - KeyBank, Peer A and Peer B: their values on the basis.

    The chart is drawn as the Peers tab's: the two bands as up-down bars
    between invisible lines on a LineChart base, then the four lines; #N/A is
    a gap. Returns where the helpers are, for tests and the caller."""
    products, grid, books = dq["products"], dq["grid"], dq["books"]
    measures = list(D.MEASURES)
    bases = list(D.BASES)
    NB, NP, DQ, NM = len(roster), len(peers), len(grid), len(measures)
    bidx = {b["cert"]: i for i, b in enumerate(roster)}

    # ---- DelinquencyData ----
    K.header_row(dd, 1, ["Product", "Measure", "Bank", "Certificate", "Quarter-end", "Numerator ($000)",
                         "Balance ($000)", "Quarter-end rate (%)", "Kept", "Why not kept",
                         "Four-quarter average (%)", "Four-quarter average kept", "Why no four-quarter average",
                         "Left out of the composite's four-quarter average (jump)"],
                 right_from=5)
    _wrap(dd, 1, 46)
    for p in products:
        for m in measures:
            for b in roster:
                for r in books[p][m][b["cert"]]:
                    dd.append([p, m, b["short"], b["cert"], r["q"], r["numerator"], r["balance"], r["rate"],
                               r["kept"], r["why"], r["avg4"], r["avg4"] is not None, r["why_avg4"],
                               (r["why_avg4"] or "").startswith(D.LEFT_OUT)])
    nrow = 1 + len(products) * NM * NB * DQ
    for row in dd.iter_rows(min_row=2, max_row=nrow, min_col=6, max_col=11):
        for c in row:
            if c.column in (6, 7):
                c.number_format = "#,##0"
            elif c.column in (8, 11):
                c.number_format = "0.0000"
    for c_, w in zip("ABCDEFGHIJKLMN", (14, 20, 16, 13, 12, 14, 16, 14, 8, 40, 16, 16, 60, 18)):
        dd.column_dimensions[c_].width = w
    K.freeze_below(dd, 1)

    def at(pi, mi, bi, k):
        return 2 + ((pi * NM + mi) * NB + bi) * DQ + k

    # ---- Delinquency: hidden helpers ----
    first, last = H_HEAD + 1, H_HEAD + DQ
    col, x = {}, H0 + 2
    for name, width in (("uk", NB), ("uv", NB), ("ok", NP), ("n", NP), ("b", NP), ("v", NP), ("s", NP),
                        ("banks", 1), ("cq", 1), ("ca", 1), ("c", 1), ("bandn", 1),
                        ("p10", 1), ("p25", 1), ("p75", 1), ("p90", 1), ("k", 1), ("a", 1), ("bb", 1),
                        ("lp", 1), ("lm", 1), ("lb", 1)):
        col[name] = x
        x += width
    width_of = {"uk": NB, "uv": NB, "ok": NP, "n": NP, "b": NP, "v": NP, "s": NP}
    rng = lambda name, r: "${a}{r}:${z}{r}".format(                                          # noqa: E731
        a=L(col[name]), z=L(col[name] + width_of.get(name, 1) - 1), r=r)
    ref = lambda name, r, j=0: "{c}{r}".format(c=L(col[name] + j), r=r)                    # noqa: E731
    lists = {name: "${c}${a}:${c}${z}".format(c=L(col[name]), a=first, z=first + len(items) - 1)
             for name, items in (("lp", products), ("lm", measures), ("lb", bases))}
    for name, items in (("lp", products), ("lm", measures), ("lb", bases)):
        de.cell(H_HEAD, col[name], {"lp": "Products", "lm": "Measures", "lb": "Bases"}[name])
        for i, v in enumerate(items):
            de.cell(first + i, col[name], v)
    u = L(H0 + 1)
    prod_at, meas_at, basis_at, a_at, b_at, sel = ("$%s$%d" % (u, r) for r in (4, 5, 6, 7, 8, 9))
    for r, text, f in (
            (4, "Product number", "=MATCH($B$%d,%s,0)" % (D_PRODUCT, lists["lp"])),
            (5, "Measure number", "=MATCH($B$%d,%s,0)" % (D_MEASURE, lists["lm"])),
            (6, "Basis number", "=MATCH($B$%d,%s,0)" % (D_BASIS, lists["lb"])),
            (7, "Peer A, bank number", "=IFERROR(MATCH(Pack!$C$%d,Pack!%s,0),NA())" % (P_A, all_banks)),
            (8, "Peer B, bank number", "=IFERROR(MATCH(Pack!$C$%d,Pack!%s,0),NA())" % (P_B, all_banks)),
            (9, "Product and measure", "=(%s-1)*%d+%s" % (prod_at, NM, meas_at))):
        de.cell(r, H0, text)
        de.cell(r, H0 + 1, f)
    mb = "Pack!$B$%d" % P_MINBANKS

    def pick(letter, bi, k):
        """The DelinquencyData cell in this column for the picked product and measure."""
        cells = ",".join("DelinquencyData!$%s$%d" % (letter, at(pi, mi, bi, k))
                         for pi in range(len(products)) for mi in range(NM))
        return "CHOOSE(%s,%s)" % (sel, cells)

    def pick_balance(bi, k):
        """The balance for the picked product: the same for every measure, so the first's."""
        cells = ",".join("DelinquencyData!$G$%d" % at(pi, 0, bi, k) for pi in range(len(products)))
        return "CHOOSE(%s,%s)" % (prod_at, cells)

    de.cell(H_HEAD, H0, "Quarter-end")
    de.cell(H_HEAD, H0 + 1, "Four consecutive quarter-ends")
    for name, banks in (("uk", roster), ("uv", roster), ("ok", peers), ("n", peers), ("b", peers), ("v", peers),
                        ("s", peers)):
        for j, b in enumerate(banks):
            de.cell(H_HEAD, col[name] + j, "%s %s" % (b["short"], name))
    for name, h in (("banks", "Banks in the quarter-end composite"), ("cq", "Composite, quarter-end"), ("ca", "Composite, four-quarter average"),
                    ("c", "Pack composite"), ("bandn", "Banks in the band"), ("p10", "10th"), ("p25", "25th"),
                    ("p75", "75th"), ("p90", "90th"), ("k", me["short"])):
        de.cell(H_HEAD, col[name], h)
    de.cell(H_HEAD, col["a"], '="Peer A: "&Pack!$C$%d' % P_A)
    de.cell(H_HEAD, col["bb"], '="Peer B: "&Pack!$C$%d' % P_B)
    follows = D._consecutive(grid)
    me_i = bidx[me["cert"]]
    for k, q in enumerate(grid):
        r = first + k
        four = k >= 3 and all(follows[i] for i in range(k - 2, k + 1))
        de.cell(r, H0, q)
        de.cell(r, H0 + 1, four)
        for j in range(NB):
            uk = ref("uk", r, j)
            de.cell(r, col["uk"] + j, "=" + pick("I", j, k))
            de.cell(r, col["uv"] + j, "=IF({b}=1,IF({uk},{rate},NA()),IF({k4},{avg},NA()))".format(
                b=basis_at, uk=uk, rate=pick("H", j, k), k4=pick("L", j, k), avg=pick("K", j, k)))
        for j, b in enumerate(peers):
            i = bidx[b["cert"]]
            inc = "Pack!$D$%d" % (first_peer + j)
            ok = ref("ok", r, j)
            uv = ref("uv", r, i)
            de.cell(r, col["ok"] + j, "=AND(%s,%s)" % (inc, ref("uk", r, i)))
            de.cell(r, col["n"] + j, '=IF(%s,%s,"")' % (ok, pick("F", i, k)))
            de.cell(r, col["b"] + j, '=IF(%s,%s,"")' % (ok, pick_balance(i, k)))
            de.cell(r, col["v"] + j, '=IF(AND(%s,ISNUMBER(%s)),%s,"")' % (inc, uv, uv))
            # 1 when this peer stays in the composite's four-quarter average
            # at this quarter-end, 0 when the jump blanked its own.
            de.cell(r, col["s"] + j, "=IF(%s,0,1)" % pick("N", i, k))
        banks, bandn = ref("banks", r), ref("bandn", r)
        de.cell(r, col["banks"], "=COUNT(%s)" % rng("n", r))
        de.cell(r, col["cq"], "=IF({n}>={mb},100*SUM({x})/SUM({b}),NA())"
                .format(n=banks, mb=mb, x=rng("n", r), b=rng("b", r)))
        if four:
            # Each of the four quarter-ends recomputed over the peers kept
            # there that stay at this one (``s`` on this row).
            stay = rng("s", r)
            cnt = ["COUNTIFS(%s,1,%s,TRUE)" % (stay, rng("ok", w)) for w in range(r - 3, r + 1)]
            rate = ["100*SUMIFS(%s,%s,1)/SUMIFS(%s,%s,1)" % (rng("n", w), stay, rng("b", w), stay)
                    for w in range(r - 3, r + 1)]
            de.cell(r, col["ca"], "=IF(AND(%s),AVERAGE(%s),NA())"
                    % (",".join("%s>=%s" % (c, mb) for c in cnt), ",".join(rate)))
        else:
            de.cell(r, col["ca"], "=NA()")
        de.cell(r, col["c"], "=IF(%s=1,%s,%s)" % (basis_at, ref("cq", r), ref("ca", r)))
        de.cell(r, col["bandn"], "=COUNT(%s)" % rng("v", r))
        for p in (10, 25, 75, 90):
            de.cell(r, col["p%d" % p], "=IF({n}>={mb},PERCENTILE({v},{p}),NA())"
                    .format(n=bandn, mb=mb, v=rng("v", r), p=p / 100))
        de.cell(r, col["k"], "=" + ref("uv", r, me_i))
        for name, num in (("a", a_at), ("bb", b_at)):
            de.cell(r, col[name], "=IFERROR(INDEX({row},{n}),NA())".format(row=rng("uv", r), n=num))
    for c_ in range(H0, col["lb"] + 1):
        de.column_dimensions[L(c_)].hidden = True

    # ---- Delinquency: what the bank sees ----
    K.brand_banner(de, 1, 15, "Delinquency and nonaccrual: KeyBank against the pack",
                   "Live from the yellow cells here and the Pack tab's Include cells, Peer A and Peer B.")
    for r, text, val, items in ((D_PRODUCT, "Product", dq["products"][0], "lp"),
                                (D_MEASURE, "Measure", dq["measure"], "lm"),
                                (D_BASIS, "Basis", dq["basis"], "lb")):
        de.cell(r, 1, text).font = Font(bold=True)
        c = de.cell(r, 2, val)
        c.fill = INPUT
        dv = DataValidation(type="list", formula1="=" + lists[items], allow_blank=False)
        de.add_data_validation(dv)
        dv.add(c.coordinate)
    de.cell(7, 1, "Peer A").font = Font(bold=True)
    de.cell(7, 2, '=Pack!$C$%d&IF(Pack!$B$%d=Pack!$C$%d,""," ("&Pack!$B$%d&")")' % (P_A, P_A, P_A, P_A))
    de.cell(8, 1, "Peer B").font = Font(bold=True)
    de.cell(8, 2, '=Pack!$C$%d&IF(Pack!$B$%d=Pack!$C$%d,""," ("&Pack!$B$%d&")")' % (P_B, P_B, P_B, P_B))
    # Best and worst are ranked on the Pack tab's charge-off product, which
    # need not be the product picked here: the note names it, live.
    de.cell(7, 3, '="Picked on the Pack tab. Best and worst in pack are ranked there on "&LOWER(Pack!$B$%d)'
                  '&" charge-offs, not on delinquency."' % P_PRODUCT).font = NOTE
    de.cell(9, 1, "Light band: 10th to 90th percentile of the included peers' rates on the basis picked; dark "
                  "band: 25th to 75th. Each is blank when fewer banks than the Pack tab asks for are in it: "
                  "the table counts both.").font = NOTE
    de.cell(10, 1, "A gap in a line: no rate that quarter-end (DelinquencyData says why). On the four-quarter "
                   "average the composite leaves out a bank mid-acquisition, as the band does. Every term, and "
                   "everything left out and why, is on the Glossary tab.").font = NOTE
    de.column_dimensions["A"].width = 14            # "Quarter-end" heads the table under the chart
    de.column_dimensions["B"].width = 30
    lc = _band(de, col["p10"], col["p90"], first, last, K.MIST, (" ", "10th to 90th (light band)"))
    lc.title = "Delinquency rate (%): product, measure and basis as picked above"
    lc.height, lc.width = 12, 26
    lc.x_axis.delete = False
    lc.y_axis.delete = False
    lc.y_axis.number_format = "0.00"
    lc.legend.position = "b"
    lc.legend.overlay = False
    lc.display_blanks = "gap"
    lc.visible_cells_only = False
    lc.set_categories(Reference(de, min_col=H0, min_row=first, max_row=last))
    lc.x_axis.tickLblSkip = max(1, min(8, DQ // 6))
    lc.x_axis.tickLblPos = "low"
    lc += _band(de, col["p25"], col["p75"], first, last, "CFC6B6", (" ", "25th to 75th (dark band)"))
    lines = LineChart()
    for name in ("c", "k", "a", "bb"):
        lines.add_data(Reference(de, min_col=col[name], min_row=H_HEAD, max_row=last), titles_from_data=True)
    styles = ((K.INK, 28575, None), (K.KEY_RED, 28575, None), (K.SLATE, 15875, "dash"), ("1F5F8B", 15875, "sysDot"))
    for s_, (colour, width, dash) in zip(lines.series, styles):
        s_.smooth = False
        s_.graphicalProperties.line.solidFill = colour
        s_.graphicalProperties.line.width = width
        if dash:
            s_.graphicalProperties.line.dashStyle = dash
    lc += lines
    de.add_chart(lc, "A%d" % D_CHART)
    # The composite and the band count different banks on the four-quarter
    # average (the composite's are those kept at the quarter-end; the band's,
    # those with a four-quarter average), so the table gives each its own
    # count rather than one "Banks in" that is the band's only on quarter-end.
    K.header_row(de, D_TABLE, ["Quarter-end", "Banks in the quarter-end composite", "Pack composite", "KeyBank",
                               "Peer A", "Peer B", "Banks in the band", "10th", "90th"], right_from=1)
    _wrap(de, D_TABLE, 48)
    for c_, w in zip("CDEFGHI", (13, 11, 11, 11, 11, 9, 9)):     # A and B are set above
        de.column_dimensions[c_].width = w
    for k in range(DQ):
        r, hr = D_TABLE + 1 + k, first + k
        de.cell(r, 1, "=%s%d" % (L(H0), hr))
        de.cell(r, 2, "=%s" % ref("banks", hr))
        de.cell(r, 7, "=%s" % ref("bandn", hr))
        for c_, name in zip((3, 4, 5, 6, 8, 9), ("c", "k", "a", "bb", "p10", "p90")):
            de.cell(r, c_, '=IFERROR(%s+0,"")' % ref(name, hr))
            de.cell(r, c_).number_format = "0.00"
    return {"quarters": grid, "products": products, "helpers": {name: L(c) for name, c in col.items()},
            "first_row": first, "data_rows": nrow - 1}


def build_peers_workbook(out, data: Dict[str, list], roster: List[dict], products: Sequence[str],
                         jump: float, min_book: float, pack: str,
                         mergers: Dict[str, Sequence[str]], extra_acquisitions: Dict[str, Sequence[str]],
                         base_quarter: str, *,
                         exempt_self: bool, min_banks: int, rank_by: str, last_n: int, min_obs: int,
                         index_min_book: float, lagged_years: Sequence[int], lag_years: int,
                         normalisation_years: Sequence[int], mix_base_year: int,
                         industry: Optional[Dict[str, List[dict]]],
                         delinquency: Optional[dict],
                         acquired: Dict[str, Dict[str, Sequence[str]]],
                         sources: Iterable[str] = (), cache_dir=None, mergers_file=None,
                         peer_a: str = WORST, peer_b: str = BEST,
                         product: Optional[str] = None) -> dict:
    """Write the peer workbook to ``out`` and return what went in.

    ``data`` is ``{REPDTE: [rows]}`` as ``fdic.pull`` returns it; ``roster`` the
    banks as ``roster.load`` returns them. The judgements, none defaulted:

    - ``jump``, ``min_book`` ($000) and ``exempt_self``: the rules of
      ``books.bank_book``; ``exempt_self`` lifts the minimum for KeyBank;
    - ``acquired``: ``{product: {cert: [YYYYMMDD]}}``, the quarters whose
      recorded acquisitions brought in at least the acquisition share
      (``books.acquired_quarters``), for every product built; the delinquency
      spec carries the same under its ``acquired`` key;
    - ``pack``: 'all' or 'regionals', the peers Include starts TRUE for;
    - ``min_banks``: how many kept banks a composite or band needs (a live
      cell on Pack, starting here);
    - ``rank_by`` ('gross' or 'net'), ``last_n``, ``min_obs``: how best and
      worst in pack are found (``books.best_worst``), live cells on Pack;
    - ``mergers`` (``{cert: [quarter-end dates]}``, as ``fdic.classify``
      returns) and ``extra_acquisitions`` (declared purchases the FDIC record
      does not show), ``base_quarter`` and ``index_min_book`` ($000, the
      smallest book at the base that is indexed): the Balances tab;
    - ``lagged_years`` and ``lag_years``: the Lagged tab;
    - ``normalisation_years``: (base year, end year) for the Normalisation tab;
    - ``mix_base_year`` and ``industry`` (``{product: books.industry(...)}``
      over every filer, or None, in which case the Mix tab says it was not
      supplied rather than standing the roster in for the industry);
    - ``delinquency``: None, and the Delinquency and DelinquencyData tabs say
      it was not built; or a dict of exactly these keys, none defaulted (see
      :func:`_check_delinquency`): ``data`` (``{REPDTE: [rows]}`` carrying
      ``delinquency.FIELDS`` for its products, usually the same pull as
      ``data``), ``products`` (names from ``delinquency.FIELDS``), ``jump``,
      ``min_book`` ($000) and ``exempt_self`` (the rules of
      ``delinquency.bank_delinquency``, stated for delinquency rather than
      borrowed from the charge-off ones), and ``measure`` and ``basis``, the
      measure and basis pickers' starting positions. The composite and band
      need the Pack tab's live number of banks, as the charge-off ones do.

    ``peer_a``, ``peer_b`` and ``product`` are only the pickers' starting
    positions; nothing is computed from them that the bank cannot change.

    Provenance for the Run tab: ``sources`` (lines of text), ``cache_dir``
    (the folder ``fdic.pull`` read; each file's name, when it was written,
    which is when it was pulled, and its SHA-256) and ``mergers_file`` (the
    acquisitions file ``mergers`` came from, named with its date and SHA-256).
    The ``mergers`` given are fingerprinted whatever their source.

    Refused (ValueError), each with its reason: a setting outside its range, a
    base quarter that is not in the data, a product whose fields the data does
    not carry, a roster with no peers, a regionals pack with no regionals, and
    banks or products that do not share one quarter calendar.
    """
    if pack not in PACKS:
        raise ValueError("pack must be 'all' or 'regionals', not %r" % (pack,))
    if rank_by not in ("gross", "net"):
        raise ValueError("rank_by must be 'gross' or 'net', not %r" % (rank_by,))
    products = list(products)
    if not products or any(p not in PRODUCTS for p in products) or len(set(products)) != len(products):
        raise ValueError("products must be distinct names from %s, not %r" % (sorted(PRODUCTS), products))
    if len(normalisation_years) != 2:
        raise ValueError("normalisation_years is (base year, end year)")
    for name, value in (("min_banks", min_banks), ("last_n", last_n), ("min_obs", min_obs)):
        _whole_at_least_1(name, value)
    product = product or products[0]
    if product not in products:
        raise ValueError("the starting product %r is not one of %r" % (product, products))
    base_repdte = quarter_end(base_quarter).replace("-", "")       # refuses '2019Q5'
    if base_repdte not in data:
        qs = sorted(data)
        raise ValueError("the base quarter %s is not in the data (%s), so no book can be indexed to it"
                         % (base_quarter, "%s to %s" % (label(qs[0]), label(qs[-1])) if qs else "no quarters"))
    # A field absent from a quarter's every row would be read as 0 for every
    # bank: an empty book, not a missing one. fdic.pull refuses the same.
    for p in products:
        for f in _fields(p):
            lacking = [q for q in sorted(data) if not any(f in row for row in data[q])]
            if lacking:
                raise ValueError("%s needs %s, which the data does not carry in %d quarter(s), first %s: "
                                 "pull it with that field" % (p, f, len(lacking), lacking[0]))
    me = R.self_bank(roster)
    peers = R.peers(roster)
    if not peers:
        raise ValueError("the roster has no peers, so there is nothing to compare %s with" % me["short"])
    if pack == "regionals" and not R.regionals(roster):
        raise ValueError("pack 'regionals' was asked for, but no peer on the roster is marked regional")
    shorts = [b["short"] for b in peers]
    for pick in (peer_a, peer_b):
        if pick not in shorts + [WORST, BEST]:
            raise ValueError("a peer pick must be a peer's short name, %r or %r, not %r" % (WORST, BEST, pick))
    in_pack = {b["cert"] for b in (R.peers(roster) if pack == "all" else R.regionals(roster))}
    dq = _check_delinquency(delinquency, roster, me)

    books = {p: {b["cert"]: bank_book(data, b["cert"], p, jump, min_book,
                                      exempt_min_book=exempt_self and b is me,
                                      acquired=acquired[p].get(b["cert"], []))
                 for b in roster} for p in products}
    grid = [r["quarter"] for r in books[products[0]][me["cert"]]]
    for p in products:
        for b in roster:
            if [r["quarter"] for r in books[p][b["cert"]]] != grid:
                raise ValueError("%s %s does not share the quarter calendar" % (b["short"], p))
    NB, NP, Q = len(roster), len(peers), len(grid)
    if Q < 1:
        raise ValueError("the data has no TTM quarter: it needs at least five quarter-ends")
    bidx = {b["cert"]: i for i, b in enumerate(roster)}

    wb = Workbook()
    pk = wb.active
    pk.title = "Pack"
    pe, de, ba, lg, nm, mx, gl, da, dd, run = (wb.create_sheet(t) for t in (
        "Peers", "Delinquency", "Balances", "Lagged", "Normalisation", "Mix", "Glossary", "Data",
        "DelinquencyData", "Run"))
    pk.sheet_properties.tabColor = K.KEY_RED
    for ws in (pk, pe, de, ba, lg, nm, mx, gl, run):
        K.hide_gridlines(ws)

    # ---- Data: one row per product, bank (roster order) and quarter ----
    # The live formulas find a row by position: product block, then bank
    # block, then quarter, so the order here is load-bearing.
    K.header_row(da, 1, ["Product", "Bank", "Certificate", "Quarter", "Gross charge-offs, TTM ($000)",
                         "Recoveries, TTM ($000)", "Average balance ($000)", "Gross rate (%)",
                         "Net rate (%)", "Kept", "Why not kept"], right_from=4)
    _wrap(da, 1, 46)
    for p in products:
        for b in roster:
            for r in books[p][b["cert"]]:
                da.append([p, b["short"], b["cert"], r["quarter"], r["gross"], r["recoveries"],
                           r["avg_balance"], r["gross_rate"], r["net_rate"], r["kept"], r["why"]])
    nrow = 1 + len(products) * NB * Q
    for row in da.iter_rows(min_row=2, max_row=nrow, min_col=5, max_col=9):
        for c in row:
            c.number_format = "#,##0" if c.column <= 7 else "0.0000"
    for col, w in zip("ABCDEFGHIJK", (16, 16, 11, 9, 14, 14, 16, 10, 10, 8, 44)):
        da.column_dimensions[col].width = w
    K.freeze_below(da, 1)

    # ---- Pack (red): the bank's choices ----
    K.brand_banner(pk, 1, 7, "Pack: who KeyBank is compared with",
                   "Yellow cells are yours. The Peers and Delinquency tabs recalculate as you change them.")
    first_peer, last_peer = P_HEAD + 1, P_HEAD + NP
    hl = {"all": L(P_HELP), "opts": L(P_HELP + 1), "prod": L(P_HELP + 2)}     # hidden lists J, K, L
    for i, b in enumerate(roster):
        pk.cell(P_HEAD + 1 + i, P_HELP, b["short"])
    for i, o in enumerate(shorts + [WORST, BEST]):
        pk.cell(P_HEAD + 1 + i, P_HELP + 1, o)
    for i, p in enumerate(products):
        pk.cell(P_HEAD + 1 + i, P_HELP + 2, p)
    pk.cell(P_HEAD, P_HELP, "All banks")
    pk.cell(P_HEAD, P_HELP + 1, "Peer picks")
    pk.cell(P_HEAD, P_HELP + 2, "Products")
    lst = lambda key, n: "$%s$%d:$%s$%d" % (hl[key], P_HEAD + 1, hl[key], P_HEAD + n)    # noqa: E731
    settings = [
        (P_PRODUCT, "Product", product, "=" + lst("prod", len(products))),
        (P_A, "Peer A", peer_a, "=" + lst("opts", NP + 2)),
        (P_B, "Peer B", peer_b, "=" + lst("opts", NP + 2)),
        (P_KIND, "Best and worst are ranked by the", rank_by, '"gross,net"'),
        (P_LASTN, "rate's mean over the last (quarters)", last_n, None),
        (P_MINOBS, "among peers kept in at least (quarters of them)", min_obs, None),
        (P_MINBANKS, "Banks needed for a composite or band", min_banks, None),
    ]
    for r, text, val, choices in settings:
        pk.cell(r, 1, text).font = Font(bold=True)
        c = pk.cell(r, 2, val)
        c.fill = INPUT
        if choices:
            dv = DataValidation(type="list", formula1=choices, allow_blank=False)
            pk.add_data_validation(dv)
            dv.add(c.coordinate)
    # The counts refuse anything but a whole number of at least 1, as the
    # build does: a 0 for the kept quarters needed turned best, worst, Peer A
    # and B and the caption into #DIV/0! (an excluded peer's AVERAGE of nothing).
    counts = DataValidation(type="whole", operator="greaterThanOrEqual", formula1="1", allow_blank=False,
                            showErrorMessage=True, errorTitle="A whole number of at least 1",
                            error="Type a whole number of 1 or more.")
    pk.add_data_validation(counts)
    for r in (P_LASTN, P_MINOBS, P_MINBANKS):
        counts.add("B%d" % r)
    pk.cell(P_A, 3, '=IF(B{r}="{w}",$B${wr},IF(B{r}="{b}",$B${br},B{r}))'
            .format(r=P_A, w=WORST, b=BEST, wr=P_WORST, br=P_BEST))
    pk.cell(P_B, 3, '=IF(B{r}="{w}",$B${wr},IF(B{r}="{b}",$B${br},B{r}))'
            .format(r=P_B, w=WORST, b=BEST, wr=P_WORST, br=P_BEST))
    means = "$E${a}:$E${z}".format(a=first_peer, z=last_peer)
    names = "$A${a}:$A${z}".format(a=first_peer, z=last_peer)
    for r, text, fn in ((P_BEST, "Best in pack is", "MIN"), (P_WORST, "Worst in pack is", "MAX")):
        pk.cell(r, 1, text).font = Font(bold=True)
        pk.cell(r, 2, '=IF(COUNT({m})=0,"(none qualifies)",INDEX({n},MATCH({f}({m}),{m},0)))'
                .format(m=means, n=names, f=fn))
    pk.cell(P_A, 4, "<- draws this peer").font = NOTE
    K.header_row(pk, P_HEAD, ["Peer", "Certificate", "Regional", "Include",
                              "Mean rate, last quarters (live)", "Kept quarters in that window"], right_from=4)
    _wrap(pk, P_HEAD, 46)
    inc = DataValidation(type="list", formula1='"TRUE,FALSE"', allow_blank=False)
    pk.add_data_validation(inc)
    for i, b in enumerate(peers):
        r = first_peer + i
        pk.cell(r, 1, b["short"])
        pk.cell(r, 2, b["cert"])
        pk.cell(r, 3, "yes" if b["regional"] else "no")
        c = pk.cell(r, 4, b["cert"] in in_pack)
        c.fill = INPUT
        inc.add(c.coordinate)
    pk.cell(last_peer + 2, 1, "The pack started as %s. Best and worst count only included peers; Peer A and Peer B "
                              "are drawn whether or not they are included. KeyBank (certificate %s) is never in "
                              "its own pack. Every term is on the Glossary tab."
            % ("every peer" if pack == "all" else "the regionals only", me["cert"])).font = NOTE
    for col, w in zip("ABCDEF", (34, 16, 10, 10, 14, 14)):
        pk.column_dimensions[col].width = w
    for col in range(P_HELP, P_HELP + 3):
        pk.column_dimensions[L(col)].hidden = True

    # ---- Peers: live helpers (hidden), then the charts over them ----
    # Columns from H0: the quarter, the in-window flag, then one block per
    # measure -- every bank's kept flag and rates (unfiltered, for KeyBank and
    # Peer A and B), then each peer's figures filtered by Include -- so each
    # measure is one contiguous range. A helper reads Data by direct reference,
    # CHOOSE picking the product's block: an INDEX over the whole Data column
    # works too, but costs the recalculation engine the tests use ~100 times
    # as much per cell.
    first, last = H_HEAD + 1, H_HEAD + Q
    p_at, a_at, b_at = ("$%s$%d" % (L(H0 + 1), r) for r in (5, 6, 7))
    pe.cell(5, H0, "Product number")
    pe.cell(5, H0 + 1, "=MATCH(Pack!$B${r},Pack!{l},0)".format(r=P_PRODUCT, l=lst("prod", len(products))))
    for r, prow in ((6, P_A), (7, P_B)):
        pe.cell(r, H0, "Peer %s, bank number" % ("A" if r == 6 else "B"))
        pe.cell(r, H0 + 1, "=IFERROR(MATCH(Pack!$C${r},Pack!{l},0),NA())".format(r=prow, l=lst("all", NB)))
    col, at = {}, H0 + 2
    for name, width in (("uk", NB), ("ug", NB), ("un", NB), ("ok", NP), ("g", NP), ("rc", NP), ("bal", NP),
                        ("gr", NP), ("nr", NP), ("win", NP), ("banks", 1), ("cg", 1), ("cn", 1),
                        ("g10", 1), ("g25", 1), ("g75", 1), ("g90", 1), ("n10", 1), ("n25", 1), ("n75", 1),
                        ("n90", 1), ("kg", 1), ("kn", 1), ("ag", 1), ("an", 1), ("bg", 1), ("bn", 1)):
        col[name] = at
        at += width
    width_of = {"uk": NB, "ug": NB, "un": NB}
    rng = lambda name, r: "${a}{r}:${z}{r}".format(                                          # noqa: E731
        a=L(col[name]), z=L(col[name] + width_of.get(name, NP) - 1), r=r)
    ref = lambda name, r, j=0: "{c}{r}".format(c=L(col[name] + j), r=r)                    # noqa: E731
    heads = {"banks": "Banks in", "cg": "Pack composite", "cn": "Pack composite",
             "g10": "10th", "g25": "25th", "g75": "75th", "g90": "90th",
             "n10": "10th", "n25": "25th", "n75": "75th", "n90": "90th",
             "kg": me["short"], "kn": me["short"]}
    pe.cell(H_HEAD, H0, "Quarter")
    pe.cell(H_HEAD, H0 + 1, "In the best/worst window")
    for name in ("uk", "ug", "un"):
        for j, b in enumerate(roster):
            pe.cell(H_HEAD, col[name] + j, "%s %s" % (b["short"], name))
    for name in ("ok", "g", "rc", "bal", "gr", "nr", "win"):
        for j, b in enumerate(peers):
            pe.cell(H_HEAD, col[name] + j, "%s %s" % (b["short"], name))
    for name, h in heads.items():
        pe.cell(H_HEAD, col[name], h)
    for name, which in (("ag", "A"), ("an", "A"), ("bg", "B"), ("bn", "B")):
        pe.cell(H_HEAD, col[name], '="Peer %s: "&Pack!$C$%d' % (which, P_A if which == "A" else P_B))
    mb = "Pack!$B$%d" % P_MINBANKS
    dcol = {"gross": "E", "rec": "F", "bal": "G", "grate": "H", "nrate": "I", "kept": "J"}

    def pick(key, b, k):
        """The Data cell for this measure, bank (roster position) and quarter, in the picked product."""
        cells = ",".join("Data!$%s$%d" % (dcol[key], 2 + i * NB * Q + b * Q + k) for i in range(len(products)))
        return "CHOOSE(%s,%s)" % (p_at, cells)

    for k, q in enumerate(grid):
        r = first + k
        pe.cell(r, H0, q)
        pe.cell(r, H0 + 1, "={k}>={q}-Pack!$B${n}".format(k=k, q=Q, n=P_LASTN))
        for j, b in enumerate(roster):
            pe.cell(r, col["uk"] + j, "=" + pick("kept", j, k))
            pe.cell(r, col["ug"] + j, "=IF({ok},{v},NA())".format(ok=ref("uk", r, j), v=pick("grate", j, k)))
            pe.cell(r, col["un"] + j, "=IF({ok},{v},NA())".format(ok=ref("uk", r, j), v=pick("nrate", j, k)))
        for j, b in enumerate(peers):
            i = bidx[b["cert"]]
            ok = ref("ok", r, j)
            pe.cell(r, col["ok"] + j, "=AND(Pack!$D${pr},{uk})".format(pr=first_peer + j, uk=ref("uk", r, i)))
            for name, key in (("g", "gross"), ("rc", "rec"), ("bal", "bal")):
                pe.cell(r, col[name] + j, '=IF({ok},{v},"")'.format(ok=ok, v=pick(key, i, k)))
            for name, u in (("gr", "ug"), ("nr", "un")):
                pe.cell(r, col[name] + j, '=IF({ok},{v},"")'.format(ok=ok, v=ref(u, r, i)))
            pe.cell(r, col["win"] + j, '=IF(${w}{r},IF(Pack!$B${kd}="gross",{g},{n}),"")'
                    .format(w=L(H0 + 1), r=r, kd=P_KIND, g=ref("gr", r, j), n=ref("nr", r, j)))
        banks = ref("banks", r)
        pe.cell(r, col["banks"], "=COUNT(%s)" % rng("nr", r))
        pe.cell(r, col["cg"], "=IF({n}>={mb},100*SUM({g})/SUM({b}),NA())"
                .format(n=banks, mb=mb, g=rng("g", r), b=rng("bal", r)))
        pe.cell(r, col["cn"], "=IF({n}>={mb},100*(SUM({g})-SUM({rc}))/SUM({b}),NA())"
                .format(n=banks, mb=mb, g=rng("g", r), rc=rng("rc", r), b=rng("bal", r)))
        for kind, rates in (("g", "gr"), ("n", "nr")):
            for p in (10, 25, 75, 90):
                pe.cell(r, col["%s%d" % (kind, p)], "=IF({n}>={mb},PERCENTILE({v},{p}),NA())"
                        .format(n=banks, mb=mb, v=rng(rates, r), p=p / 100))
        me_i = bidx[me["cert"]]
        pe.cell(r, col["kg"], "=" + ref("ug", r, me_i))
        pe.cell(r, col["kn"], "=" + ref("un", r, me_i))
        for name, u, num in (("ag", "ug", a_at), ("an", "un", a_at), ("bg", "ug", b_at), ("bn", "un", b_at)):
            pe.cell(r, col[name], "=IFERROR(INDEX({row},{n}),NA())".format(row=rng(u, r), n=num))
    # Pack's live means for best and worst, from the window helpers.
    for j in range(NP):
        w = "{c}${a}:{c}${z}".format(c=L(col["win"] + j), a=first, z=last)
        pr = first_peer + j
        pk.cell(pr, 6, "=COUNT(Peers!%s)" % w)
        pk.cell(pr, 5, '=IF(F{r}>=$B${m},AVERAGE(Peers!{w}),"")'.format(r=pr, m=P_MINOBS, w=w))
        pk.cell(pr, 5).number_format = "0.00"

    K.brand_banner(pe, 1, 15, "KeyBank against the pack",
                   "Live from the Pack tab: the band and composite are the included peers, kept quarters only.")
    pe.cell(4, 1, "Product").font = Font(bold=True)
    pe.cell(4, 2, "=Pack!$B$%d" % P_PRODUCT)
    pe.cell(5, 1, "Peer A").font = Font(bold=True)
    pe.cell(5, 2, '=Pack!$C$%d&IF(Pack!$B$%d=Pack!$C$%d,""," ("&Pack!$B$%d&")")' % (P_A, P_A, P_A, P_A))
    pe.cell(6, 1, "Peer B").font = Font(bold=True)
    pe.cell(6, 2, '=Pack!$C$%d&IF(Pack!$B$%d=Pack!$C$%d,""," ("&Pack!$B$%d&")")' % (P_B, P_B, P_B, P_B))
    pe.cell(7, 1, ('="Best in pack resolved to "&Pack!$B${b}&"; worst to "&Pack!$B${w}&", on the mean "'
                   '&Pack!$B${k}&" rate over the last "&Pack!$B${n}&" quarters, among peers kept in at least "'
                   '&Pack!$B${o}&" of them."').format(b=P_BEST, w=P_WORST, k=P_KIND, n=P_LASTN, o=P_MINOBS))
    pe.cell(8, 1, "Light band: 10th to 90th percentile of the pack's kept rates; dark band: 25th to 75th. "
                  "No band: fewer pack banks kept than needed. A gap in a line: a quarter not kept "
                  "(Data tab says why).").font = NOTE
    pe.column_dimensions["A"].width = 10
    pe.column_dimensions["B"].width = 30
    tick = max(1, min(8, Q // 6))
    styles = ((K.INK, 28575, None), (K.KEY_RED, 28575, None), (K.SLATE, 15875, "dash"), ("1F5F8B", 15875, "sysDot"))
    for i, kind in enumerate(("gross", "net")):
        k = kind[0]
        # The bands are the first chart groups, so the lines are drawn over
        # them. The base is a line chart: with an area chart as the base,
        # Excel 16 drew no tick labels at all (6 Oct 2026).
        lc = _band(pe, col[k + "10"], col[k + "90"], first, last, K.MIST, (" ", "10th to 90th (light band)"))
        lc.title = "%s charge-off rate, TTM (%%)" % kind.capitalize()
        lc.height, lc.width = 12, 26
        lc.x_axis.delete = False
        lc.y_axis.delete = False
        lc.y_axis.number_format = "0.0"
        lc.legend.position = "b"
        lc.legend.overlay = False
        lc.display_blanks = "gap"
        lc.visible_cells_only = False
        lc.set_categories(Reference(pe, min_col=H0, min_row=first, max_row=last))
        lc.x_axis.tickLblSkip = tick
        lc.x_axis.tickLblPos = "low"
        lc += _band(pe, col[k + "25"], col[k + "75"], first, last, "CFC6B6", (" ", "25th to 75th (dark band)"))
        lines = LineChart()
        for name in ("c" + k, "k" + k, "a" + k, "b" + k):
            lines.add_data(Reference(pe, min_col=col[name], min_row=H_HEAD, max_row=last), titles_from_data=True)
        for s_, (colour, width, dash) in zip(lines.series, styles):
            s_.smooth = False
            s_.graphicalProperties.line.solidFill = colour
            s_.graphicalProperties.line.width = width
            if dash:
                s_.graphicalProperties.line.dashStyle = dash
        lc += lines
        pe.add_chart(lc, "A%d" % (10 + 26 * i))
    # A table of the live lines under the charts, for reading values off.
    t0 = 64
    K.header_row(pe, t0, ["Quarter", "Banks in", "Composite gross", "Composite net", "KeyBank gross",
                          "KeyBank net", "Peer A net", "Peer B net"], right_from=1)
    _wrap(pe, t0, 34)
    for k in range(Q):
        r, hr = t0 + 1 + k, first + k
        pe.cell(r, 1, "=%s%d" % (L(H0), hr))
        pe.cell(r, 2, "=%s" % ref("banks", hr))
        for c_, name in zip(range(3, 9), ("cg", "cn", "kg", "kn", "an", "bn")):
            pe.cell(r, c_, '=IFERROR(%s+0,"")' % ref(name, hr))
            pe.cell(r, c_).number_format = "0.00"
    for c_ in range(H0, col["bn"] + 1):
        pe.column_dimensions[L(c_)].hidden = True

    # ---- Delinquency and DelinquencyData: live over the same Pack ----
    d_info = _delinquency_tabs(de, dd, dq, roster, me, peers, first_peer, lst("all", NB)) if dq else None
    if not dq:
        for ws in (de, dd):
            ws.cell(1, 1, NOT_BUILT).font = Font(bold=True)
            ws.column_dimensions["A"].width = 100

    # ---- Balances (values) ----
    r = K.brand_banner(ba, 1, 6, "Balances: growth as reported and without acquisitions",
                       "Index, %s = 100. Without acquisitions, growth in an acquisition quarter counts as none."
                       % label(quarter_end(base_quarter).replace("-", "")))
    base_lbl = label(quarter_end(base_quarter).replace("-", ""))
    for p in products:
        r = K.section_band(ba, r + 1, "%s: book index, %s = 100" % (p, base_lbl), 6)
        r = K.header_row(ba, r, ["Bank", "Book at the base ($m)", "As reported, %s" % grid[-1],
                                 "Without acquisitions, %s" % grid[-1], "Acquisition quarters", "Note"],
                         right_from=1)
        _wrap(ba, r - 1, 34)
        series = {}
        for b in roster:
            acq = _acquisitions(mergers, extra_acquisitions, b["cert"])
            listed = ", ".join(q + (" (declared)" if d else "") for q, d in acq) or "none"
            try:
                idx = organic_index(data, b["cert"], p, base_quarter, [q for q, _ in acq])
            except ValueError:
                # The base quarter is in the data (checked above), so this is
                # the bank having no filing or a zero book there.
                idx = None
            at_base = next((x["balance"] for x in idx if x["date"] == quarter_end(base_quarter)), None) \
                if idx else None
            note = None
            if idx is None:
                note = "no book at the base"
            elif at_base < index_min_book:
                note = "under the minimum at the base: not indexed"
            else:
                series[b["cert"]] = [x for x in idx if x["date"] >= quarter_end(base_quarter)]
            latest = series[b["cert"]][-1] if b["cert"] in series else None
            ba.append([b["short"], None if at_base is None else at_base / 1000,
                       latest["reported"] if latest else None, latest["organic"] if latest else None,
                       listed, note])
            row = ba.max_row
            ba.cell(row, 2).number_format = "#,##0"
            for c_ in (3, 4):
                ba.cell(row, c_).number_format = "0"
            ba.cell(row, 5).alignment = Alignment(wrap_text=True, vertical="top")
            if b is me:
                for c_ in range(1, 7):
                    ba.cell(row, c_).fill = SELF_FILL
                ba.cell(row, 1).font = Font(bold=True, color=K.CRIMSON)
        # Quarterly table for the chart: without acquisitions, banks indexed.
        r = ba.max_row + 25                       # below the chart, which is ~20 rows tall
        chart_at = ba.max_row + 2
        indexed = [b for b in roster if b["cert"] in series]
        if indexed:
            ba.cell(r - 1, 2, "Without acquisitions").font = Font(bold=True)
            ba.cell(r - 1, 3 + len(indexed), "As reported").font = Font(bold=True)
            ba.cell(r, 1, "Quarter").font = Font(bold=True)
            for j, b in enumerate(indexed):
                ba.cell(r, 2 + j, b["short"]).font = Font(bold=True)
                ba.cell(r, 3 + len(indexed) + j, b["short"]).font = Font(bold=True)
            _wrap(ba, r, 30)
            quarters = [x["quarter"] for x in series[indexed[0]["cert"]]]
            for k, q in enumerate(quarters):
                ba.cell(r + 1 + k, 1, q)
                for j, b in enumerate(indexed):
                    x = series[b["cert"]][k]
                    for c_, v in ((2 + j, x["organic"]), (3 + len(indexed) + j, x["reported"])):
                        if v is not None:
                            ba.cell(r + 1 + k, c_, v).number_format = "0.0"
            lc = _line_chart("%s: book without acquisitions, %s = 100" % (p, base_lbl), height=10, width=24)
            lc.add_data(Reference(ba, min_col=2, max_col=1 + len(indexed), min_row=r, max_row=r + len(quarters)),
                        titles_from_data=True)
            lc.set_categories(Reference(ba, min_col=1, min_row=r + 1, max_row=r + len(quarters)))
            for s_, b in zip(lc.series, indexed):
                s_.smooth = False
                s_.graphicalProperties.line.width = 28575 if b is me else 9525
                if b is me:
                    s_.graphicalProperties.line.solidFill = K.KEY_RED
            lc.x_axis.tickLblSkip = 4
            lc.legend.position = "r"
            ba.add_chart(lc, "A%d" % chart_at)
            r = r + len(quarters) + 1
        else:
            r = ba.max_row + 1
    ba.column_dimensions["A"].width = 18
    for c_, w in zip("BCDEF", (14, 14, 14, 60, 34)):
        ba.column_dimensions[c_].width = w

    # ---- Lagged (values) ----
    r = K.brand_banner(lg, 1, 2 + len(lagged_years), "Lagged rates: a year's losses over the book lent earlier",
                       "100 x calendar-year net charge-offs (Q4 year-to-date, as filed) / the mean balance %d "
                       "year%s earlier. Totals sum the dollars." % (lag_years, "" if lag_years == 1 else "s"))
    all_certs = [b["cert"] for b in R.peers(roster)]
    reg_certs = [b["cert"] for b in R.regionals(roster)]
    # A total is named with its count: the regionals are every peer the roster
    # marks regional, which is not the same set as a handful named elsewhere.
    totals = [("All peers, total (%d banks)" % len(all_certs), all_certs)]
    if reg_certs:
        totals.append(("Regionals, total (%d banks)" % len(reg_certs), reg_certs))
    reg_names = ", ".join(b["short"] for b in R.regionals(roster)) or "none on the roster"
    for p in products:
        r = K.section_band(lg, r + 1, p, 1 + len(lagged_years))
        r = K.header_row(lg, r, ["Bank"] + ["%d net over %d book (%%)" % (y, y - lag_years) for y in lagged_years],
                         right_from=1)
        _wrap(lg, r - 1, 34)
        rows = [(b["short"], b["cert"], b is me) for b in roster]
        rows += [(name, certs, False) for name, certs in totals]
        for name, certs, mine in rows:
            vals = [lagged_rate(data, certs, p, y, lag_years)["rate"] for y in lagged_years]
            lg.append([name] + vals)
            for c_ in range(2, 2 + len(vals)):
                lg.cell(lg.max_row, c_).number_format = "0.00"
            if mine:
                lg.cell(lg.max_row, 1).font = Font(bold=True, color=K.CRIMSON)
        r = lg.max_row
    lg.cell(r + 2, 1, "Blank: a bank did not file every quarter of a year needed. A total is blank if any of its "
                      "banks is, rather than worked out over the banks that remain.").font = NOTE
    lg.cell(r + 3, 1, "The regionals are the peers the roster marks regional: %s." % reg_names).font = NOTE
    lg.column_dimensions["A"].width = 22
    for c_ in range(2, 2 + len(lagged_years)):
        lg.column_dimensions[L(c_)].width = 16

    # ---- Normalisation (values) ----
    y0, y1 = normalisation_years
    r = K.brand_banner(nm, 1, 4, "Normalisation: how far each net rate moved, %d to %d" % (y0, y1),
                       "Each year is the mean of its four quarterly TTM net rates, kept quarters only.")
    for p in products:
        r = K.section_band(nm, r + 1, p, 4)
        r = K.header_row(nm, r, ["Bank", "%d (%%)" % y0, "%d (%%)" % y1, "%d / %d" % (y1, y0)], right_from=1)
        rows = [(b["short"], [(x["quarter"], x["net_rate"]) for x in books[p][b["cert"]]], b is me)
                for b in roster]
        for name, certs in (("All-peer composite (%d banks)" % len(all_certs), all_certs),
                            ("Regional composite (%d banks)" % len(reg_certs), reg_certs)):
            if not certs:
                continue
            comp = composite(books[p], certs, min_banks=min_banks)
            rows.append((name, [(x["quarter"], x["net_rate"]) for x in comp], False))
        for name, ser, mine in rows:
            n_ = normalisation(ser, y0, y1)
            nm.append([name, n_["base"], n_["end"], n_["ratio"]])
            for c_ in (2, 3, 4):
                nm.cell(nm.max_row, c_).number_format = "0.00"
            if mine:
                nm.cell(nm.max_row, 1).font = Font(bold=True, color=K.CRIMSON)
        r = nm.max_row
    nm.cell(r + 2, 1, "Composites need %d kept banks a quarter, as the Pack tab started. A year is blank when a "
                      "quarter of it was not kept. The ratio is also blank when the earlier year is 0 or below "
                      "(net recoveries): a ratio to it would read the wrong way." % min_banks).font = NOTE
    nm.column_dimensions["A"].width = 22
    for c_ in "BCD":
        nm.column_dimensions[c_].width = 12

    # ---- Mix (values) ----
    r = K.brand_banner(mx, 1, 7, "Mix: KeyBank's move against the industry's, base %d" % mix_base_year,
                       "Own factor above 1: KeyBank worsened more than the industry since the base year.")
    years = sorted({int(q[:4]) for q in data if all("%s%s" % (q[:4], md) in data
                                                    for md in ("0331", "0630", "0930", "1231"))})
    years = [y for y in years if y >= mix_base_year]
    for p in products:
        r = K.section_band(mx, r + 1, p, 7)
        ind = (industry or {}).get(p)
        if not ind:
            mx.cell(r, 1, "No industry series was supplied for %s, so no mix factor is worked out. The roster "
                          "banks are not the industry and do not stand in for it." % p).font = NOTE
            continue
        ind_rate = {int(x["quarter"][:4]): x["net_rate"] for x in ind if x["quarter"].endswith("Q4")}
        if mix_base_year not in ind_rate:
            mx.cell(r, 1, "The industry series has no %d to measure from." % mix_base_year).font = NOTE
            continue
        if mix_base_year not in years:
            mx.cell(r, 1, "The data does not hold all four quarters of %d, so the banks have no %d to measure "
                          "from." % (mix_base_year, mix_base_year)).font = NOTE
            continue
        r = K.header_row(mx, r, ["Year", "KeyBank net rate (%)", "Industry net rate (%)", "KeyBank / base year",
                                 "Industry / base year", "Own factor", "Balance factor"], right_from=1)
        _wrap(mx, r - 1, 34)
        own = {}
        for b in roster:
            cy = {y: calendar_year(data, b["cert"], p, y) for y in years}
            rate = {y: lagged_rate(data, b["cert"], p, y, 0)["rate"] for y in years}
            bal = {y: cy[y]["balance"] for y in years}
            rows = mix_factor(rate, {y: ind_rate.get(y) for y in years}, bal, mix_base_year)
            own[b["cert"]] = {x["year"]: x["own_factor"] for x in rows}
            if b is me:
                for x in rows:
                    mx.append([x["year"], rate[x["year"]], ind_rate.get(x["year"]), x["bank_ratio"],
                               x["industry_ratio"], x["own_factor"], x["balance_factor"]])
                    for c_ in range(2, 8):
                        mx.cell(mx.max_row, c_).number_format = "0.00"
        r = mx.max_row + 2
        mx.cell(r, 1, "Own factor, every bank").font = Font(bold=True)
        r = K.header_row(mx, r + 1, ["Bank"] + [str(y) for y in years], right_from=1)
        for b in roster:
            mx.append([b["short"]] + [own[b["cert"]].get(y) for y in years])
            for c_ in range(2, 2 + len(years)):
                mx.cell(mx.max_row, c_).number_format = "0.00"
            if b is me:
                mx.cell(mx.max_row, 1).font = Font(bold=True, color=K.CRIMSON)
        r = mx.max_row
    mx.cell(r + 2, 1, "Calendar-year net rate: Q4 year-to-date net charge-offs as filed / the mean of the year's "
                      "four quarter-end balances. The industry's is its TTM net rate at Q4.").font = NOTE
    mx.column_dimensions["A"].width = 16
    for c_ in range(2, 2 + max(7, len(years))):
        mx.column_dimensions[L(c_)].width = 11

    # ---- Glossary ----
    K.brand_banner(gl, 1, 3, "Glossary", "What each term means, and exactly how the workbook calculates it.")
    K.header_row(gl, 4, ["Term", "What it means", "How it is calculated"])
    for term, meaning, calc in PEER_TERMS:
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
    run.append(["Sources"] + list(SOURCES))
    for s in sources:
        run.append(["", s])
    qs = sorted(data)
    run.append(["Quarter-ends in the pull", len(qs), "%s to %s" % (qs[0], qs[-1]) if qs else ""])
    run.append(["Pull fingerprint (SHA-256 of the rows as canonical JSON)", _fingerprint(data)])
    # Pull dates: a cache file is written when its quarter is fetched, so its
    # modification time is when that quarter was pulled.
    if cache_dir is not None:
        files = sorted(Path(cache_dir).glob("q*.json"))
        stamps = sorted(_written(f) for f in files)
        run.append(["Cache folder", str(cache_dir), "%d files" % len(files)])
        run.append(["Pulled (cache files written)", "%s to %s" % (stamps[0], stamps[-1]) if stamps else "no files"])
        run.append(["Cache file", "Pulled (written)", "SHA-256"])
        for f in files:
            run.append([f.name, _written(f), hashlib.sha256(f.read_bytes()).hexdigest()])
    else:
        run.append(["Pulled", "not recorded: no cache folder was given, so the rows came straight from the caller"])
    run.append(["Acquisitions record (SHA-256 of it as canonical JSON)", _fingerprint(mergers),
                "%d banks, %d acquisition quarters" % (len(mergers), sum(len(v) for v in mergers.values()))])
    if mergers_file is not None:
        mf = Path(mergers_file)
        run.append(["Acquisitions file", str(mf), "pulled (written) %s, SHA-256 %s"
                    % (_written(mf), hashlib.sha256(mf.read_bytes()).hexdigest())])
    else:
        run.append(["Acquisitions file", "not named by the caller"])
    run.append([])
    run.append(["Rules, as stated"])
    run.append(["Jump", jump, "a quarter-on-quarter balance move above this is structural"])
    run.append(["Minimum book ($000)", min_book, "KeyBank exempt" if exempt_self else "KeyBank not exempt"])
    run.append(["Banks needed for a composite or band (starting)", min_banks])
    run.append(["Pack (starting)", pack])
    run.append(["Best and worst (starting)", "%s rate, last %d quarters, at least %d kept"
                % (rank_by, last_n, min_obs)])
    run.append(["Balance index", "base %s" % base_lbl, "books of at least %s ($000) at the base" % index_min_book])
    run.append(["Declared acquisitions", "; ".join("%s: %s" % (c, ", ".join(v))
                                                   for c, v in sorted(extra_acquisitions.items())) or "none"])
    run.append(["Lagged", "years %s" % ", ".join(str(y) for y in lagged_years), "lag %d" % lag_years])
    run.append(["Normalisation", "%d to %d" % (y0, y1)])
    run.append(["Mix base year", mix_base_year, "industry supplied" if industry else "no industry supplied"])
    if dq:
        dqs = sorted(dq["data"])
        run.append(["Delinquency", ", ".join(dq["products"]),
                    "quarter-ends %s to %s" % (label(dqs[0]), label(dqs[-1]))])
        run.append(["Delinquency pull fingerprint (SHA-256 of the rows as canonical JSON)", _fingerprint(dq["data"])])
        run.append(["Delinquency jump", dq["jump"], "blanks a four-quarter average; never a quarter-end rate"])
        run.append(["Delinquency minimum book ($000)", dq["min_book"],
                    "KeyBank exempt" if dq["exempt_self"] else "KeyBank not exempt"])
        run.append(["Delinquency pickers (starting)", "%s, %s" % (dq["measure"], dq["basis"])])
    else:
        run.append(["Delinquency", "not built"])
    run.append([])
    run.append(["Roster"])
    run.append(["Certificate", "Name", "Short", "Group", "Regional"])
    for b in roster:
        run.append([b["cert"], b["name"], b["short"], b["group"], "yes" if b["regional"] else "no"])
    run.column_dimensions["A"].width = 44
    run.column_dimensions["B"].width = 60
    run.column_dimensions["C"].width = 66

    out = Path(out)
    wb.save(out)
    _na_as_gap(out)
    return {"path": out, "products": products, "quarters": grid,
            "pack": [b["cert"] for b in peers if b["cert"] in in_pack],
            "data_rows": nrow - 1,
            # Where the live lines are on Peers: first column of each helper
            # block, and the row of the first quarter.
            "peers_helpers": {name: L(c) for name, c in col.items()}, "peers_first_row": first,
            # None when not built; else its quarters, helper columns and first row.
            "delinquency": d_info}
