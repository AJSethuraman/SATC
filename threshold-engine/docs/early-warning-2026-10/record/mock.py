"""mock.html: the proposed Book 1 measures, each laid out as it would sit on Decide, from real numbers."""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.argv = [sys.argv[0]]
src = (HERE / "focus.py").read_text(encoding="utf-8").split('t = (HERE / "template.html")')[0]
g = {"__file__": str(HERE / "focus.py")}
exec(compile(src, "focus.py", "exec"), g)
globals().update({k: v for k, v in g.items() if not k.startswith("__")})


# ---------- the numbers behind each chart ----------
NUM = json.loads((S / "rolls" / "numbers.json").read_text())
YEARS = ["%dQ4" % y for y in range(2012, 2026)]


def tbl(caption, heads, rows):
    body = "".join("<tr>%s</tr>" % "".join('<td class="num">%s</td>' % c if i else "<td>%s</td>" % c for i, c in enumerate(r)) for r in rows)
    return ('<details class="raw" open><summary>Numbers behind it: %s (one row per year, the fourth quarter, plus the latest)</summary><div style="overflow-x:auto"><table class="begins">'
            '<tr>%s</tr>%s</table></div></details>' % (caption, "".join("<th>%s</th>" % h for h in heads), body))


def m(v):                     # $ thousands -> $ millions or billions
    return ("$%.1fbn" % (v / 1e6)) if abs(v) >= 1e6 else ("$%.0fm" % (v / 1e3))


def next2(series, q_):
    ks = sorted(series); i = ks.index(q_)
    return sum(series[k]["gco"] for k in ks[i + 1:i + 3]) if i + 2 < len(ks) else None


def flow_rows(key, quarters):
    v = NUM[key]; rows = []
    for q_ in quarters:
        if q_ not in v:
            continue
        r = v[q_]; d30 = r["p3"] + r["p9"] + r["na"]; c2 = next2(v, q_)
        rows.append([q_, m(r["p3"]), m(r["p9"]), m(r["na"]), m(d30), m(c2) if c2 is not None else "&mdash;",
                     ("%.1f%%" % (100 * c2 / d30)) if c2 is not None and d30 else "&mdash;"])
    return rows


FLOW_HEADS = ["Quarter-end", "30&ndash;89", "90+ accruing", "Nonaccrual", "All 30+ (sum)", "Gross charge-offs, next two quarters",
              "Share charged off (this quarter-end)"]


def nco_rows(key, quarters):
    v = NUM[key]; ks = sorted(v); rows = []
    for q_ in quarters:
        if q_ not in v:
            continue
        i = ks.index(q_)
        if i < 7:
            continue
        w, w0 = ks[i - 3:i + 1], ks[i - 7:i - 3]
        net = sum(v[k]["gco"] - v[k]["rec"] for k in w); bal = sum(v[k]["bal"] for k in w) / 4
        net0 = sum(v[k]["gco"] - v[k]["rec"] for k in w0); bal0 = sum(v[k]["bal"] for k in w0) / 4
        rows.append([q_, m(net), m(bal), "%.2f%%" % (100 * net / bal), "%+.2f pts" % (100 * net / bal - 100 * net0 / bal0)])
    return rows


NCO_HEADS = ["Quarter", "Net charge-offs, four quarters", "Average balances", "Net charge-off rate", "Change from a year earlier (the &ldquo;rise&rdquo;)"]


def dq_rows(key, field, quarters, label):
    v = NUM[key]; rows = []
    for q_ in quarters:
        k0 = "%dQ%s" % (int(q_[:4]) - 1, q_[5])
        if q_ in v and k0 in v:
            amt = sum(v[q_][f] for f in field); amt0 = sum(v[k0][f] for f in field)
            r1, r0 = 100 * amt / v[q_]["bal"], 100 * amt0 / v[k0]["bal"]
            rows.append([q_, m(amt), m(v[q_]["bal"]), "%.2f%%" % r1, "%+.2f pts" % (r1 - r0)])
    return rows

NAMES = ["1 Low", "2 Moderate-Low", "3 Moderate", "4 Moderate-High", "5 High"]


def rating(v, b):
    return 1 + sum(v >= x for x in b)


def fit_lines(series, floor, z=Z):
    vals = [series[q_] for q_ in sorted(series)]
    o = scale(vals, "higher_is_worse", HW, LS, z, floor)
    if o["bounds"]:
        return o["bounds"], z, None, o
    fit = (o["worst"] - o["median"]) / o["spread_of_levels"] if o["spread_of_levels"] else None
    if fit and fit > 0.3:
        z2 = round(fit - 0.005, 2)
        o2 = scale(vals, "higher_is_worse", HW, LS, z2, floor)
        if o2["bounds"]:
            return o2["bounds"], z2, o["refused"], o2
    return None, None, o["refused"], o


def chip(r):
    return '<span class="chip r%d">%s</span>' % (r, NAMES[r - 1]) if r else '<span class="chip">no rating</span>'


def card(product, measure, source, lines_from, series_lines, rate_series, Qs, ylo, yhi, ticks, fmt, unit, floor=True, note="", ytitle="", numbers=""):
    bounds, z, refused, o = fit_lines(series_lines, floor)
    last = max(q_ for q_ in rate_series)
    r = rating(rate_series[last], bounds) if bounds else None
    lines = []
    for nm, d_, col, w, dash in SERIES_STYLE(series_lines, rate_series, lines_from, source):
        lines.append({"data": d_, "color": col, "w": w, "dash": dash, "name": nm})
    chart = svg_chart(Qs, lines, ylo, yhi, ticks, fmt, h=230, zones=bounds, ytitle=ytitle,
                      label="%s %s, %s rated on lines from %s" % (product, measure, source, lines_from))
    rows = ""
    if bounds:
        starts = [None] + list(bounds)
        for i in range(5):
            share = sum(rating(v, bounds) == i + 1 for v in rate_series.values()) / len(rate_series)
            rows += ('<tr><td><span class="sw2 r%d"></span>%s</td><td class="num">%s</td><td class="num">%.0f%%</td></tr>'
                     % (i + 1, NAMES[i], ("from " + fmt(starts[i])) if starts[i] is not None else "below " + fmt(bounds[0]), 100 * share))
    settings = ('Width of Moderate <b>%g</b> &middot; Moderate-Low begins <b>%g</b> &middot; How rare High is (z) <b>%s</b>%s'
                % (HW, LS, ("%.2f" % z) if z else "&mdash;", " &middot; floor at zero <b>off</b>" if not floor else ""))
    status = ("" if not refused else
              ('<div class="warn">At z 2.5 the Check says: %s. %s</div>' % (refused, ("Shown at z %.2f, the highest that fits." % z) if z else "No z fits.")))
    return ('<article class="row"><div class="rowhead"><div><div class="pm">%s &middot; %s</div><div class="src">Rated: %s &middot; Lines set from: %s</div></div>'
            '<div class="now"><div class="lbl">Rating now (%s)</div>%s<div class="val">%s</div></div></div>'
            '<div class="settings">%s</div>%s<div class="grid2"><div class="chart">%s</div>'
            '<table class="begins"><tr><th>Rating</th><th>Begins</th><th>Share of quarters</th></tr>%s</table></div>'
            '<p class="cap">%s</p>%s</article>'
            % (product, measure, source, lines_from, last, chip(r), fmt(rate_series[last]) + unit, settings, status, chart, rows, note, numbers))


def SERIES_STYLE(series_lines, rate_series, lines_from, source):
    out = []
    if lines_from != source and series_lines != rate_series:
        out.append((lines_from, series_lines, "var(--muted)", 1.8, True))
    out.append((source, rate_series, "var(--key)", 2.8, False))
    return out


# ---------- the measures ----------
C_IND, C_PG, C_KB = flow4("Card", "Industry"), flow4("Card", "Peer group"), flow4("Card", "KeyBank")
O_IND, O_PG, O_KB = flow4("Other consumer", "Industry"), flow4("Other consumer", "Peer group"), flow4("Other consumer", "KeyBank")
C_KB2 = {q_: v for q_, v in C_KB.items() if q_ >= "2017Q1"}
gap = lambda a, b: {q_: a[q_] - b[q_] for q_ in a if q_ in b}       # noqa: E731
pctf = lambda v: "%.1f%%" % v                                       # noqa: E731
ptsf = lambda v: "%+.1f" % v if v else "0"                          # noqa: E731

MEAS = []
MEAS.append(("Inherent risk: how much delinquency turns into loss",
    card("Credit card", "30+ to charge-off", "KeyBank", "Peer group (15 banks)", C_PG, C_KB2, qrange("2011Q4", "2025Q4"), 60, 110,
         [60, 70, 80, 90, 100, 110], pctf, "", note="Gross charge-offs over the next two quarters &divide; (30&ndash;89 + 90+ + nonaccrual) at the quarter-end, "
         "four-quarter average. KeyBank shown from 2017 (its card book was small before). KeyBank&rsquo;s 30+ includes its nonaccrual card loans; "
         "the internal check (nonaccrual card balances by days past due) decides whether that flatters it.",
         ytitle="% of 30+ dollars charged off within two quarters",
         numbers=tbl("KeyBank card, $ as filed", FLOW_HEADS, flow_rows("Card|KeyBank", YEARS[5:]))
                 + tbl("Peer group card, $ as filed (15 banks summed)", FLOW_HEADS, flow_rows("Card|Peer group", YEARS[5:])))
    + card("Other consumer", "30+ to charge-off", "KeyBank", "Peer group (15 banks)", O_PG, O_KB, qrange("2011Q4", "2025Q4"), 0, 110,
           [0, 25, 50, 75, 100], pctf, "", note="Every source stepped up from about 35% to 60&ndash;85% from 2023, which looks like reporting and "
           "product mix; lines across the whole history flag everything since. Leaving out the quarters before 2023 is the alternative, with a "
           "short history.", ytitle="% of 30+ dollars charged off within two quarters",
           numbers=tbl("KeyBank other consumer, $ as filed", FLOW_HEADS, flow_rows("Other consumer|KeyBank", YEARS))
                   + tbl("Peer group other consumer, $ as filed", FLOW_HEADS, flow_rows("Other consumer|Peer group", YEARS)))))
MEAS.append(("Relative performance: KeyBank against peers and industry",
    card("Credit card", "KeyBank minus peers, 30+ to charge-off", "KeyBank minus peer group", "its own history", gap(C_KB2, C_PG), gap(C_KB2, C_PG),
         qrange("2017Q1", "2025Q4"), -30, 30, [-30, -15, 0, 15, 30], ptsf, " pts", floor=False,
         note="Below zero: KeyBank turns less of its delinquency into loss than the peer group in the same quarter. Zones here come from the "
              "gap&rsquo;s own history; anchoring them at zero (worse than peers = 4 or 5) is the other choice.",
         ytitle="KeyBank minus peer group, points")
    + card("Credit card", "KeyBank minus industry, 30+ to charge-off", "KeyBank minus industry", "its own history", gap(C_KB2, C_IND), gap(C_KB2, C_IND),
           qrange("2017Q1", "2025Q4"), -30, 30, [-30, -15, 0, 15, 30], ptsf, " pts", floor=False, ytitle="KeyBank minus industry, points")
    + card("Other consumer", "KeyBank minus peers, 30+ to charge-off", "KeyBank minus peer group", "its own history", gap(O_KB, O_PG), gap(O_KB, O_PG),
           qrange("2011Q4", "2025Q4"), -50, 50, [-50, -25, 0, 25, 50], ptsf, " pts", floor=False,
           note="Measured in the same quarter, so the industry-wide step in 2023 largely cancels out.", ytitle="KeyBank minus peer group, points")
    + card("Other consumer", "KeyBank minus industry, 30+ to charge-off", "KeyBank minus industry", "its own history", gap(O_KB, O_IND), gap(O_KB, O_IND),
           qrange("2011Q4", "2025Q4"), -50, 50, [-50, -25, 0, 25, 50], ptsf, " pts", floor=False, ytitle="KeyBank minus industry, points")))
MP = {q_: v for q_, v in MINPAY.items()}
ACCTS = _ph_bal("Number of Accounts (Millions)")
MEAS.append(("Borrower strain",
    card("Credit card", "Share of accounts paying only the minimum", "Large banks (Philadelphia Fed)", "Large banks (Philadelphia Fed)", MP, MP,
         qrange("2012Q3", "2026Q2"), 6, 12, [6, 8, 10, 12], pctf, "",
         note="Large banks&rsquo; card accounts, quarterly from 2012. Moves with 30&ndash;89 days past due and about a year ahead of charge-offs; "
              "tracks the most stretched tenth&rsquo;s utilization (0.92). An industry reading: there is no public KeyBank figure.",
         ytitle="% of card accounts making only the minimum payment",
         numbers=tbl("large banks&rsquo; card accounts", ["Quarter", "Accounts (millions)", "Share paying only the minimum", "Accounts paying only the minimum (millions, implied)"],
                     [[q_, "%.1f" % ACCTS[q_], "%.2f%%" % MP[q_], "%.1f" % (ACCTS[q_] * MP[q_] / 100)] for q_ in YEARS + ["2026Q2"] if q_ in MP and q_ in ACCTS]))))
MN_I, MN_K = lvl("mortgage", "industry", "nonaccrual"), lvl("mortgage", "keybank", "nonaccrual")
MEAS.append(("Mortgage",
    card("Mortgage", "Nonaccrual", "KeyBank", "Industry (every bank)", MN_I, MN_K, qrange("2006Q1", "2026Q2"), 0, 7, [0, 2, 4, 6], lambda v: "%.2f%%" % v, "",
         note="Mortgage rated on delinquency rather than charge-offs (near zero since 2014). Nonaccrual leaves out government-guaranteed 90+ "
              "loans that carry no loss. Lines from the whole history are set by 2008; lines from 2016 on are the other choice.",
         ytitle="mortgage nonaccrual, % of balances",
         numbers=tbl("KeyBank mortgage (closed-end first liens), $ as filed", ["Quarter-end", "Nonaccrual", "Balances", "Nonaccrual rate", "Change from a year earlier"],
                     dq_rows("Mortgage|KeyBank", ["na"], ["%dQ4" % y for y in range(2007, 2026)] + ["2026Q2"], ""))
                 + tbl("Industry mortgage, $ as filed", ["Quarter-end", "Nonaccrual", "Balances", "Nonaccrual rate", "Change from a year earlier"],
                       dq_rows("Mortgage|Industry", ["na"], ["%dQ4" % y for y in range(2007, 2026)] + ["2026Q2"], "")))))

# ---------- context panels, not rated ----------
def ctx(title, chart, note, plain_=""):
    return '<article class="row ctx"><div class="rowhead"><div><div class="pm">%s</div><div class="src">Shown beside the ratings, not rated</div></div></div>%s<div class="chart">%s</div><p class="cap">%s</p></article>' % (title, plain_, chart, note)



ORIG_N = _philly("26Q2-CreditCardOriginations.csv", "Number of New Accounts (Millions)")
ORIG_D = _philly("26Q2-CreditCardOriginations.csv", "New Originations ($Billions)")
ctx_new = tbl("what &ldquo;new accounts under 660&rdquo; and &ldquo;rise in card charge-offs&rdquo; are, in counts and dollars",
              ["Quarter", "New card accounts opened (millions)", "Share with a score under 660", "New accounts under 660 (millions, implied)",
               "New credit lines opened ($bn)", "Share of those lines ($) under 660"],
              [[q_, "%.1f" % ORIG_N[q_], "%.1f%%" % SUB_ACC[q_], "%.2f" % (ORIG_N[q_] * SUB_ACC[q_] / 100), "%.1f" % ORIG_D[q_], "%.1f%%" % SUB_COM[q_]]
               for q_ in YEARS + ["2026Q2"] if q_ in ORIG_N]) + \
          tbl("industry card net charge-offs (every bank, Call Report)", NCO_HEADS, nco_rows("Card|Industry", YEARS + ["2026Q2"]))
ctx_ease = tbl("what the survey number is", ["Quarter", "Net share of banks easing card standards"],
               [[q_, "%+.1f%%" % EASE[q_]] for q_ in YEARS + ["2026Q2", "2026Q3"] if q_ in EASE]) + \
           tbl("industry card net charge-offs (every bank, Call Report)", NCO_HEADS, nco_rows("Card|Industry", YEARS + ["2026Q2"]))
ctx_mtg = tbl("other consumer 30&ndash;89 days past due, industry", ["Quarter-end", "30&ndash;89", "Balances", "Rate", "Change from a year earlier"],
              dq_rows("Other consumer|Industry", ["p3"], ["%dQ4" % y for y in range(2007, 2026)] + ["2026Q2"], "")) + \
          tbl("mortgage 90+ including nonaccrual, industry", ["Quarter-end", "90+ incl. nonaccrual", "Balances", "Rate", "Change from a year earlier"],
              dq_rows("Mortgage|Industry", ["p9", "na"], ["%dQ4" % y for y in range(2007, 2026)] + ["2026Q2"], ""))


# ---------- plain series: as published, nothing calculated ----------
def rate_of(key, fields):
    v = NUM[key]
    return {q_: 100 * sum(v[q_][f] for f in fields) / v[q_]["bal"] for q_ in v if v[q_]["bal"]}


def plain(Qs, data_, name, col, ytitle, fmt_, lo=None, hi=None):
    vals = [data_[q_] for q_ in Qs if q_ in data_]
    a, z, ticks = _nice(min(vals) if lo is None else lo, max(vals) if hi is None else hi)
    return svg_chart(Qs, [{"data": data_, "color": col, "w": 2.4, "name": name}], a, z, ticks, fmt_, h=170, ytitle=ytitle,
                     label=name + ", as published")


def plain_block(charts):
    return ('<div class="plain"><div class="pm" style="font-size:13px">As published: the two series, nothing calculated</div>%s'
            '<p class="cap">Same quarters on both. Below: the same two drawn for timing (rescaled and slid), then the numbers.</p></div>'
            % "".join(charts))


PL_Q = qrange("2012Q3", "2026Q2")
PL_LONG = qrange("2006Q4", "2026Q3")
pl_new = plain_block([
    plain(PL_Q, NCO, "Card net charge-off rate", "var(--c-card)", "industry card net charge-offs, four quarters, % of average balances",
          lambda v: "%.1f%%" % v, 0),
    plain(PL_Q, SUB_ACC, "New accounts under 660", "var(--c-he)", "% of new card accounts opened in the quarter with a score under 660 (large banks)",
          lambda v: "%.0f%%" % v, 0)])
pl_ease = plain_block([
    plain(PL_LONG, NCO, "Card net charge-off rate", "var(--c-card)", "industry card net charge-offs, four quarters, % of average balances",
          lambda v: "%.0f%%" % v, 0),
    plain(PL_LONG, EASE, "Net share easing", "var(--c-mtg)", "net share of banks easing card standards (Senior Loan Officer Survey; up = easing)",
          lambda v: "%+.0f%%" % v if v else "0")])
OC30L, MG90L = rate_of("Other consumer|Industry", ["p3"]), rate_of("Mortgage|Industry", ["p9", "na"])
pl_mtg = plain_block([
    plain(qrange("2007Q1", "2026Q2"), OC30L, "Other consumer 30-89", "var(--c-oth)", "industry other consumer 30&ndash;89 days past due, % of balances",
          lambda v: "%.1f%%" % v, 0),
    plain(qrange("2007Q1", "2026Q2"), MG90L, "Mortgage 90+ incl. nonaccrual", "var(--c-card)", "industry mortgage 90+ including nonaccrual, % of balances",
          lambda v: "%.0f%%" % v, 0)])

CTX = (ctx("Credit card &middot; New accounts going to scores under 660 (leads charge-offs about 2 years)",
           ov(SUB_ACC, 9, YNCO, qrange("2013Q1", "2028Q3"), "var(--c-he)", "new accounts under 660, 9 quarters earlier", "rise in card charge-offs"),
           "&ldquo;New accounts under 660&rdquo; is the percent of new card accounts opened in the quarter at the large banks whose borrower scored under 660 "
           "(a count of accounts, not dollars). &ldquo;Rise in card charge-offs&rdquo; is the change in the industry&rsquo;s net charge-off rate "
           "(net charge-offs over four quarters &divide; average balances) from a year earlier, in percentage points. Drawn 9 quarters later; the "
           "stretch past today is what it already points to." + ctx_new, pl_new)
       + ctx("Credit card &middot; Banks easing card standards (leads charge-offs about 3 years)",
             ov(EASE, 11, YNCO, qrange("2007Q1", "2029Q1"), "var(--c-mtg)", "banks easing, 11 quarters earlier", "rise in card charge-offs"),
             "Senior Loan Officer Survey, 1996 on. Banks tighten while losses rise (a reaction); easing is the early signal. Closer to an "
             "economic indicator, so it may sit with Book 2. The survey number is the share of banks reporting tighter card standards minus the "
             "share reporting easier, sign flipped so easing is up: a count of banks, not dollars." + ctx_ease, pl_ease)
       + ctx("Mortgage &middot; Other consumer 30&ndash;89 as a confirming signal for mortgage 90+",
             ov(OC30, 3, MG90, qrange("2008Q1", "2027Q1"), "var(--c-oth)", "other consumer 30-89 rise, 3 quarters earlier", "rise in mortgage 90+"),
             "Industry, 2007 on. A rise in other consumer 30&ndash;89 went with a rise in mortgage 90+ about 3 quarters later (0.80). Mortgage&rsquo;s "
             "own 30&ndash;89 turns at the same time, so this confirms rather than leads. Both are rates of balances; the rise is the change in "
             "the rate from a year earlier, in percentage points." + ctx_mtg, pl_mtg))

t = (HERE / "template.html").read_text(encoding="utf-8")
style = t[:t.index("<main>")].replace("<title>Refreshed FICO Evidence</title>", "<title>Book 1 New Measures</title>")
extra = """<style>
.row { background: var(--panel); border: 1px solid var(--grid); border-radius: 4px; padding: 14px 16px; display: grid; gap: 8px; }
.rowhead { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; border-bottom: 3px solid var(--key); padding-bottom: 8px; }
.pm { font-weight: 700; font-size: 16px; } .src { font-size: 12px; color: var(--muted); }
.now { text-align: right; } .now .lbl { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
.now .val { font: 500 13px var(--f-mono); }
.chip { display: inline-block; padding: 3px 10px; border-radius: 3px; font-weight: 700; font-size: 13px; background: var(--grid); color: var(--ink); }
.chip.r1, .sw2.r1 { background: var(--z1); } .chip.r2, .sw2.r2 { background: var(--z2); } .chip.r3, .sw2.r3 { background: var(--z3); }
.chip.r4, .sw2.r4 { background: var(--z4); } .chip.r5, .sw2.r5 { background: var(--z5); }
.settings { font-size: 12px; background: var(--bg); padding: 6px 8px; border: 1px solid var(--grid); }
.warn { font-size: 12px; color: var(--c-card); }
.grid2 { display: grid; grid-template-columns: minmax(0, 2.2fr) minmax(0, 1fr); gap: 14px; align-items: start; }
@media (max-width: 640px) { .grid2 { grid-template-columns: 1fr; } }
table.begins { border-collapse: collapse; font-size: 12px; width: 100%; } table.begins th { text-align: left; color: var(--muted); font-weight: 600; }
table.begins td, table.begins th { padding: 4px 6px; border-bottom: 1px solid var(--grid); } td.num { text-align: right; font-family: var(--f-mono); }
.sw2 { display: inline-block; width: 10px; height: 10px; margin-right: 6px; border: 1px solid var(--grid); }
.ctx .rowhead { border-bottom-color: var(--muted); }
h2.grp { font-size: 15px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); margin: 8px 0 0; }
</style>"""
html = (style + extra + '<main><header style="display:grid;gap:8px"><div class="eyebrow">CONSUMER INDUSTRY ANALYSIS &middot; MOCK-UP &middot; 18 OCT 2026</div>'
        '<h1>Proposed new measures, as they would sit in the book</h1>'
        '<p class="lede">Each row is laid out like a row on Decide: what is rated, which history the lines come from, the settings, the rating '
        'now, the chart with its five zones, and where each rating begins. Real numbers; agreed settings (width 0.5, Moderate-Low 1.0, z 2.5) '
        'unless the Check refuses them, which the row says. Nothing here is built into the workbook yet.</p></header>'
        + "".join('<h2 class="grp">%s</h2>%s' % (gname, body) for gname, body in MEAS)
        + '<h2 class="grp">Context, shown beside the ratings</h2>' + CTX + "</main>")
(HERE / "mock.html").write_text(html, encoding="utf-8")
print("written", len(html))
