"""signals-mock.html: a mock-up of the book's Signals tab, one page holding
every signal found, compared against any product and measure the analyst
picks, with the peer group recorded beside every chart that draws on it.
Built from the same data and helpers as the evidence record (mock.py ->
focus.py -> build.py), so every number here is real and public.

Second cut (18 Oct 2026, the analyst's notes on the first): balances in
"where the dollars are" and every product drawn; peer panel with three
states (in, out by rule, off by you); the gap in points with the area shaded
and priced; the rescaled view with real units on both axes and its inputs
printed; the roll steps replaced by the pipeline (30+ incl. NA -> 90+ incl.
NA -> charge-offs) with refreshed FICO laid over it; minimum payment and
utilization both drawn; underwriting as one chart.
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.argv = [sys.argv[0]]
src = (HERE / "mock.py").read_text(encoding="utf-8").split('\nt = (HERE / "template.html")')[0]
g = {"__file__": str(HERE / "mock.py")}
exec(compile(src, "mock.py", "exec"), g)
globals().update({k: v for k, v in g.items() if not k.startswith("__")})

T = (HERE / "template.html").read_text(encoding="utf-8")
STYLE = T[:T.index("<main>")].replace("<title>Refreshed FICO Evidence</title>", "<title>Signals Tab Mock-up</title>")
EXTRA = """<style>
main { max-width: 1180px; }
.tab { background: var(--panel); border: 1px solid var(--grid); border-top: 6px solid var(--key); padding: 14px 18px; display: grid; gap: 14px; }
.tabname { display: inline-block; font: 600 12px var(--f-mono); background: var(--key); color: #fff; padding: 3px 10px; border-radius: 3px 3px 0 0; }
.controls { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 10px; background: var(--bg); border: 1px solid var(--grid); padding: 10px 12px; }
.ctl .lbl { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
.ctl .sel { font: 500 13px var(--f-mono); border: 1px solid var(--muted); border-radius: 3px; padding: 4px 8px; background: #fff; margin-top: 3px; display: flex; justify-content: space-between; }
.ctl .sel:after { content: "\\25BE"; color: var(--muted); }
.sec { border: 1px solid var(--grid); border-radius: 4px; padding: 12px 14px; display: grid; gap: 10px; background: var(--panel); }
.sec h2 { font-size: 16px; margin: 0; border-bottom: 3px solid var(--key); padding-bottom: 6px; }
.sec h2 small { font-weight: 500; color: var(--muted); font-size: 12px; margin-left: 10px; }
.sec h3 { font-size: 13px; margin: 6px 0 0; }
.two { display: grid; grid-template-columns: minmax(0, 2.3fr) minmax(0, 1fr); gap: 14px; align-items: start; }
@media (max-width: 760px) { .two { grid-template-columns: 1fr; } }
.peers { background: var(--bg); border: 1px solid var(--grid); padding: 8px 10px; font-size: 12px; display: grid; gap: 4px; }
.peers .ph { font-weight: 700; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }
.peers .live { color: var(--c-he); font-weight: 700; } .peers .stated { color: var(--c-mtg); font-weight: 700; }
.peers ul { margin: 0; padding-left: 16px; } .peers li.out { color: var(--c-card); } .peers li.off { color: var(--muted); text-decoration: line-through; }
.peers li.off span { text-decoration: none; font-style: italic; }
table.m { border-collapse: collapse; font-size: 12px; width: 100%; } table.m th, table.m td { padding: 3px 6px; border-bottom: 1px solid var(--grid); text-align: left; }
table.m td.num { text-align: right; font-family: var(--f-mono); } table.m tr.best td { font-weight: 700; background: var(--z2); }
table.m th { color: var(--muted); font-weight: 600; }
.cap b { color: var(--ink); }
.stack { display: grid; gap: 4px; }
.note { font-size: 12px; color: var(--muted); }
.inputs { font-size: 12px; background: var(--bg); border: 1px solid var(--grid); padding: 6px 10px; }
.inputs b { font-family: var(--f-mono); }
</style>"""

TARGETS = [
    ("Card net charge-offs, industry", _rd("credit-card_industry_net.csv")),
    ("Card net charge-offs, KeyBank", _rd("credit-card_keybank_net.csv")),
    ("Other consumer net charge-offs, industry", _rd("other-consumer_industry_net.csv")),
    ("Other consumer net charge-offs, KeyBank", _rd("other-consumer_keybank_net.csv")),
    ("Card 30-89, industry", _rd("credit-card_industry_delinquency-30-89_quarter-end.csv")),
    ("Other consumer 30+ incl. nonaccrual, KeyBank", _rd("other-consumer_keybank_delinquency-30-plus-incl-nonaccrual_quarter-end.csv")),
    ("Mortgage 90+ incl. nonaccrual, industry", _rd("mortgage_industry_delinquency-90-plus-incl-nonaccrual_quarter-end.csv")),
    ("Home equity 90+ incl. nonaccrual, industry", _rd("home-equity_industry_delinquency-90-plus-incl-nonaccrual_quarter-end.csv")),
]
PICK = "Other consumer 30+ incl. nonaccrual, KeyBank"           # the compare-against pick this mock shows
PICKED = dict(TARGETS)[PICK]
pct1 = lambda v: "%.1f%%" % v          # noqa: E731
pct2 = lambda v: "%.2f%%" % v          # noqa: E731
Q12 = qrange("2012Q3", "2026Q2")
Q11 = qrange("2011Q1", "2026Q2")
OUTQ = lambda q_: "2020Q1" <= q_ <= "2023Q4"       # noqa: E731


# ---------------------------------------------------------------- the rescaled view, with its inputs shown
def norm_inputs(s, excl):
    """The engine's own normal and yearly move for a series (scale.py):
    median of the quarters kept, and 1.4826 x the median absolute deviation
    of its four-quarter changes. Returns (median, move, quarters used)."""
    ks = sorted(s)
    vals = [None if (excl and OUTQ(q_)) else s[q_] for q_ in ks]
    o = scale(vals, "higher_is_worse", HW, LS, Z, False)
    return o["median"], o["typical_yearly_move"], sum(v is not None for v in vals)


def dual_chart(Q, a, a_name, a_fmt, a_col, b, b_name, b_fmt, k=0, excl=False, h=250):
    """Two series on one picture with real units on both axes: each is
    drawn as (value - its normal) / its typical yearly move, so one grid line
    is one yearly move for either series; the left axis reads in the
    signal's units, the right in the picked series'. The signal is slid k
    quarters later. The shaded window is 2020-23 when it is left out of the
    normal and the move."""
    am, amv, an = norm_inputs(a, excl)
    bm, bmv, bn = norm_inputs(b, excl)
    za = {q_: (v - am) / amv for q_, v in _shift(a, k).items()}
    zb = {q_: (v - bm) / bmv for q_, v in b.items()}
    PR, PT, PB, PL = 150, 42, 34, 70
    ih, iw = h - PT - PB, W - PL - PR
    xs = {q_: PL + iw * i / (len(Q) - 1) for i, q_ in enumerate(Q)}
    lo, hi = -4, 4
    y = lambda v: PT + ih * (1 - (min(max(v, lo), hi) - lo) / (hi - lo))      # noqa: E731
    p = ['<svg viewBox="0 0 %d %d" role="img" aria-label="%s laid over %s, one yearly move per grid line, real units on both axes">' % (W, h, a_name, b_name)]
    if excl:
        q0, q1 = max("2020Q1", Q[0]), min("2023Q4", Q[-1])
        if q0 in xs and q1 in xs:
            p.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="var(--grid)" fill-opacity="0.5"/>' % (xs[q0], PT, xs[q1] - xs[q0], ih))
            p.append('<text x="%.1f" y="%d" class="tk" text-anchor="middle">2020-23 left out of the normal</text>' % ((xs[q0] + xs[q1]) / 2, PT + ih - 4))
    for z in (-2, -1, 0, 1, 2):
        p.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="%s"/>' % (PL, W - PR, y(z), y(z), "var(--ink)" if z == 0 else "var(--grid)", 1.4 if z == 0 else 1))
        p.append('<text x="%d" y="%.1f" class="tk" text-anchor="end" style="fill:%s">%s</text>' % (PL - 6, y(z) + 4, a_col, a_fmt(am + z * amv)))
        p.append('<text x="%d" y="%.1f" class="tk" text-anchor="start" style="fill:var(--key)">%s</text>' % (W - PR + 6, y(z) + 4, b_fmt(bm + z * bmv)))
    p.append('<text x="%d" y="%d" class="an" text-anchor="start" style="fill:%s;font-weight:600">dashed: %s</text>' % (PL - 60, 12, a_col, a_name + (", slid %d quarters later" % k if k else "")))
    p.append('<text x="%d" y="%d" class="an" text-anchor="start" style="fill:var(--key);font-weight:600">solid, picked: %s</text>' % (PL - 60, 26, b_name))
    step = 2 if len(Q) > 30 else 1
    for q_ in Q:
        if q_.endswith("Q1") and int(q_[:4]) % step == 0:
            p.append('<text x="%.1f" y="%d" class="tk" text-anchor="middle">%s</text>' % (xs[q_], h - 10, q_[:4]))
    for d_, col, w, dash in ((zb, "var(--key)", 2.6, False), (za, a_col, 2.2, True)):
        pts = " ".join("%.1f,%.1f" % (xs[q_], y(d_[q_])) for q_ in Q if q_ in d_)
        p.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%s"%s/>' % (pts, col, w, ' stroke-dasharray="5 4"' if dash else ""))
    for z, word in ((0, "each line's own normal"), (1, "+1 yearly move"), (2, "+2 yearly moves"), (-1, "-1 yearly move")):
        p.append('<text x="%d" y="%.1f" class="tk" text-anchor="start" style="fill:var(--muted)">%s</text>' % (PL + 4, y(z) - 3, word))
    p.append("</svg>")
    inputs = ('<div class="inputs">What the picture is made of &mdash; <span style="color:%s">%s</span>: normal <b>%s</b>, one yearly move <b>%s</b>, from %d quarters%s; '
              '<span style="color:var(--key)">%s</span>: normal <b>%s</b>, one yearly move <b>%s</b>, from %d quarters. One grid line up is one typical yearly move for either line, '
              'so the left axis says what that is in the signal&rsquo;s units and the right axis in the picked series&rsquo;. The shape and every turn are the series&rsquo; own; only the two heights are made comparable.</div>'
              % (a_col, a_name, a_fmt(am), a_fmt(amv), an, " (2020-23 left out)" if excl else "", b_name, b_fmt(bm), b_fmt(bmv), bn))
    return "".join(p) + inputs


# ---------------------------------------------------------------- fit table
def matrix(signal, is_change=False):
    x = signal if is_change else yoy(signal)
    rows = []
    for name, tgt in TARGETS:
        y = yoy(tgt)
        all_ = {k: v for k, v in uw_profile(x, y, False).items() if v is not None}
        ex = {k: v for k, v in uw_profile(x, y, True).items() if v is not None}
        if not all_:
            rows.append((name, None, None, None, None)); continue
        k = max(all_, key=lambda k_: all_[k_])
        rows.append((name, k, all_[k], ex.get(k), len([a for a in x if a in y])))
    best = max((r for r in rows if r[1] is not None), key=lambda r: r[2])
    out = ['<table class="m"><tr><th>Compared against</th><th>Fits best</th><th>How well (all)</th><th>Without 2020-23</th><th>Quarters</th></tr>']
    for name, k, r_all, r_ex, n in rows:
        if k is None:
            out.append('<tr><td>%s</td><td colspan="4" class="note">too few overlapping quarters</td></tr>' % name); continue
        when = "same quarter" if k == 0 else ("%d qtrs ahead" % k if k > 0 else "%d qtrs after" % -k)
        out.append('<tr%s><td>%s%s</td><td class="num">%s</td><td class="num">%.2f</td><td class="num">%s</td><td class="num">%d</td></tr>'
                   % (' class="best"' if name == best[0] else "", name, " &larr; picked" if name == PICK else "", when, r_all,
                      ("%.2f" % r_ex) if r_ex is not None else "&mdash;", n))
    out.append("</table>")
    return "".join(out), best


HOW_TO_READ = ('<p class="note"><b>Reading the fit table.</b> Each row lays the signal&rsquo;s change over a year against that series&rsquo; change over a year, at every lead from a year after to three years ahead. '
               '<i>Fits best</i> is the lead where they move together most; <i>how well</i> is that agreement, 1.00 moving together exactly, 0 no relation, negative moving opposite; '
               '<i>without 2020-23</i> is the same with the pandemic quarters dropped; <i>quarters</i> is how many overlap. Rule of thumb: above 0.8 is a linkage, 0.5 to 0.8 is loose, below 0.5 is none worth a rating. '
               'A row that fits best &ldquo;after&rdquo; is a signal that follows that series, not one that warns of it.</p>')


# ---------------------------------------------------------------- peer panels
def left_out_now(prod, quarter="2026Q2"):
    f = TE / "docs/walkthrough-book/out/series" / ("%s_pack-composite_delinquency-30-plus-incl-nonaccrual_four-quarter-average.csv" % prod)
    note = next((l[2:] for l in f.read_text(encoding="utf-8").splitlines() if l.startswith("# Left out of this average")), "")
    out = {}
    for m_ in re.finditer(r"([A-Z][A-Za-z&.' ]+?) \((\d+)\) ((?:\d{4}Q\d(?: to \d{4}Q\d)?(?:, )?)+)", note):
        for s_ in [x.strip() for x in m_.group(3).split(",")]:
            a, _, b = s_.partition(" to ")
            if a <= quarter <= (b or a):
                out[m_.group(1).strip()] = "book moved more than the jump"
    return out


ROSTER = [b for b in json.loads((TE / "config" / "peers.json").read_text(encoding="utf-8"))["banks"] if b["short"] != "KeyBank"]
FICO_BANKS = json.loads((S / "peerfico" / "under660_2026q2.json").read_text())


def peer_panel(kind, prod=None, quarter="2026Q2", manual=()):
    if kind == "live":
        out = left_out_now(prod, quarter)
        items = []
        for b in ROSTER:
            n = b["short"]
            if n in manual:
                items.append('<li class="off">%s <span>&mdash; off: turned off under Banks in the pack</span></li>' % n)
            elif n in out:
                items.append('<li class="out">%s &mdash; out: %s</li>' % (n, out[n]))
            else:
                items.append('<li>%s</li>' % n)
        n_in = len(ROSTER) - len(out) - len([m_ for m_ in manual if m_ not in out])
        return ('<div class="peers"><div class="ph">Peer group in this chart <span class="live">live</span></div>'
                '<div>%d of %d peers in the %s composite; follows <b>Banks in the pack</b> on Peers.</div><ul>%s</ul>'
                '<div class="note">Three states: in; <span style="color:var(--c-card)">out by the book&rsquo;s rules</span> (that bank&rsquo;s own four-quarter average was blanked this quarter by the jump or the acquisition share); '
                '<span style="text-decoration:line-through">off</span> because you unticked it under Banks in the pack. Every quarter&rsquo;s list is on Peers delinquency data.%s</div></div>'
                % (n_in, len(ROSTER), quarter, "".join(items), " (The strike-through here is an example of a manual toggle.)" if manual else ""))
    if kind == "fico":
        items = "".join('<li>%s &mdash; %s</li>' % (b, ", ".join(FICO_BANKS[b])) for b in FICO_BANKS)
        return ('<div class="peers"><div class="ph">Banks in this chart <span class="stated">stated, from filings</span></div>'
                '<div>Read from each holding company&rsquo;s 10-Q, where it cuts its FICO table at 660:</div><ul>%s</ul>'
                '<div class="note">Not drawn: the other peers (no FICO table at 660 in the filing, or a different cut). Does not follow Banks in the pack: nothing live to follow.</div></div>' % items)
    if kind == "y14":
        return ('<div class="peers"><div class="ph">Whose accounts <span class="stated">stated</span></div>'
                '<div>The bank holding companies that file FR Y-14M (assets of $100bn and over), as the Philadelphia Fed publishes them: an industry panel, <b>not our peer group</b>, and it changes as banks cross $100bn. No KeyBank figure.</div></div>')
    if kind == "survey":
        return ('<div class="peers"><div class="ph">Who answered <span class="stated">stated</span></div>'
                '<div>The Federal Reserve&rsquo;s Senior Loan Officer Opinion Survey: about 60 large domestic banks, named by the Fed, not our peer group. Net share of banks reporting easier card standards.</div></div>')
    if kind == "nmdb":
        return ('<div class="peers"><div class="ph">Whose loans <span class="stated">stated</span></div>'
                '<div>FHFA&rsquo;s National Mortgage Database: a 5% sample of every first-lien mortgage in the U.S., all lenders. Not a bank panel.</div></div>')
    raise ValueError(kind)


def section(title, sub, raw, slid, mtx, panel, cap):
    return ('<section class="sec"><h2>%s<small>%s</small></h2><div class="two"><div>%s<p class="cap">%s</p></div>%s</div>'
            '<h3>Rescaled and slid, with real units on both axes</h3>%s'
            '<h3>How this signal fits every loss and delinquency series in the book</h3>%s%s</section>'
            % (title, sub, raw, cap, panel, slid, mtx, HOW_TO_READ if title.startswith("30+ to charge-off") else ""))


# ---------------------------------------------------------------- A. where the dollars are
KP = json.loads((S / "keybank_products.json").read_text())
PRODS = ["Credit card", "Other consumer", "Home equity", "Mortgage", "Auto"]
PCOL = {"Credit card": "var(--c-card)", "Other consumer": "var(--c-oth)", "Home equity": "var(--c-he)", "Mortgage": "var(--c-mtg)", "Auto": "var(--muted)"}
q = "2026Q2"
tb = sum(KP[p][q]["bal"] or 0 for p in PRODS); tg = sum(KP[p][q]["gco4"] or 0 for p in PRODS); td = sum(KP[p][q]["d30"] or 0 for p in PRODS)
why_rows = "".join('<tr><td><span class="sw2" style="background:%s"></span>%s</td><td class="num">%s</td><td class="num">%.0f%%</td><td class="num">%s</td><td class="num">%.0f%%</td><td class="num">%s</td><td class="num">%.0f%%</td></tr>'
                   % (PCOL[p], p, m(KP[p][q]["bal"]), 100 * KP[p][q]["bal"] / tb, m(KP[p][q]["gco4"] or 0), 100 * (KP[p][q]["gco4"] or 0) / tg,
                      m(KP[p][q]["d30"] or 0), 100 * (KP[p][q]["d30"] or 0) / td) for p in PRODS)
why_rows += '<tr><td><b>Consumer</b></td><td class="num"><b>%s</b></td><td class="num">100%%</td><td class="num"><b>%s</b></td><td class="num">100%%</td><td class="num"><b>%s</b></td><td class="num">100%%</td></tr>' % (m(tb), m(tg), m(td))
KQ_ = qrange("2012Q1", "2026Q2")


def share_chart(key, title):
    tot = {q_: sum(KP[p][q_][key] or 0 for p in PRODS) for q_ in KQ_}
    series = [{"data": {q_: 100 * (KP[p][q_][key] or 0) / tot[q_] for q_ in KQ_ if tot[q_]}, "color": PCOL[p], "w": 2.2, "name": p} for p in PRODS]
    return svg_chart(KQ_, series, 0, 100, [0, 25, 50, 75, 100], lambda v: "%d%%" % v, h=190, ytitle=title + " (the five add to 100%)", label=title)


bal_chart = svg_chart(KQ_, [{"data": {q_: (KP[p][q_]["bal"] or 0) / 1e6 for q_ in KQ_}, "color": PCOL[p], "w": 2.2, "name": p} for p in PRODS],
                      0, 30, [0, 10, 20, 30], lambda v: "$%gbn" % v, h=190, ytitle="KeyBank consumer balances by product, $bn, quarter-end", label="balances")
WHY = ('<section class="sec"><h2>Where the dollars are<small>KeyBank, from its Call Report, %s; the same table and charts exist for every peer, the pack composite and the industry, and follow the source picked</small></h2>'
       '<div class="two"><div><table class="m"><tr><th>Product</th><th>Balance</th><th>share</th><th>Gross charge-offs, 4 qtrs</th><th>share</th><th>30+ incl. nonaccrual</th><th>share</th></tr>%s</table>'
       '<p class="cap"><b>Card is 3%% of the consumer book and 40%% of its losses; other consumer 15%% and 56%%.</b> Mortgage is 71%% of the book, 2%% of the losses, and 51%% of the past-due dollars. '
       'A loss signal is a card and other consumer question; a delinquency signal is mostly a mortgage question.</p></div>'
       '<div class="peers"><div class="ph">Whose book <span class="live">live</span></div><div>KeyBank (certificate 17534), its own Call Report. Pick Peer group or Industry and the table and the three charts redraw for it.</div></div></div>'
       '<div class="stack"><div class="chart">%s</div><div class="chart">%s</div><div class="chart">%s</div></div></section>'
       % (q, why_rows, bal_chart, share_chart("gco4", "share of consumer gross charge-offs, 4 quarters"), share_chart("d30", "share of consumer 30+ incl. nonaccrual dollars")))

# ---------------------------------------------------------------- B. controls
CONTROLS = ('<div class="controls">'
            '<div class="ctl"><div class="lbl">Compare against: product</div><div class="sel">Other consumer</div></div>'
            '<div class="ctl"><div class="lbl">Measure</div><div class="sel">30+ incl. nonaccrual</div></div>'
            '<div class="ctl"><div class="lbl">Source</div><div class="sel">KeyBank</div></div>'
            '<div class="ctl"><div class="lbl">Shift the signal by (quarters)</div><div class="sel">fits best (auto)</div></div>'
            '<div class="ctl"><div class="lbl">Window for the normal</div><div class="sel">Without 2020-23</div></div>'
            '<div class="ctl"><div class="lbl">Banks in the pack</div><div class="sel">14 of 15 (from Peers)</div></div></div>'
            '<p class="note">Any product (the five, All consumer, Credit card + Other consumer), any measure (net or gross charge-offs; 30-89; 90+ accruing; nonaccrual; 30+ incl. nonaccrual; 90+ incl. nonaccrual; 30+ to charge-off) and any source. '
            'The pick is the red line laid on every signal below and the highlighted row of every fit table; the tables show every other series too. One rescale-and-slide chart, driven by the pick, draws every signal here and any series in the book, the ones set aside included.</p>')


def kpi(prod):
    return (_rd("%s_industry_delinquency-30-plus-incl-nonaccrual_quarter-end.csv" % prod),
            _rd("%s_pack-composite_delinquency-30-plus-incl-nonaccrual_quarter-end.csv" % prod),
            _rd("%s_keybank_delinquency-30-plus-incl-nonaccrual_quarter-end.csv" % prod))


def kpi_chart(prod, label, hi, ticks):
    i, p, k = kpi(prod)
    return svg_chart(Q11, [{"data": i, "color": "var(--ink)", "w": 1.8, "dash": True, "name": "Industry"},
                           {"data": p, "color": "var(--muted)", "w": 1.8, "name": "Peer group"},
                           {"data": k, "color": "var(--key)", "w": 2.6, "name": "KeyBank"}],
                     0, hi, ticks, pct2, h=180, ytitle="%s 30+ days past due incl. nonaccrual, %% of balances" % label, label=label)


THIRTY = ('<section class="sec"><h2>30+ incl. nonaccrual, every product<small>KeyBank against the peer group and the industry, quarter-end</small></h2>'
          '<div class="two"><div class="stack">%s%s%s%s</div><div class="stack">%s%s</div></div>'
          '<p class="cap">Each product on its own axis so nothing looks bigger or smaller than it is. The picked series (other consumer, KeyBank) is the red line in the second chart; every section below lays it over the signal.</p></section>'
          % (kpi_chart("credit-card", "Card", 4, [0, 1, 2, 3, 4]), kpi_chart("other-consumer", "Other consumer", 3, [0, 1, 2, 3]),
             kpi_chart("mortgage", "Mortgage", 10, [0, 2.5, 5, 7.5, 10]), kpi_chart("home-equity", "Home equity", 5, [0, 1, 2, 3, 4, 5]),
             peer_panel("live", "other-consumer", manual=("Citi",)), peer_panel("live", "credit-card", manual=("Citi",))))

# ---------------------------------------------------------------- the signals
secs = []
NUMK = NUM["Card|KeyBank"]


def gap_chart(kb, pg, Q, prod_num):
    """KeyBank minus peers in points, zero line, the area shaded (above zero
    = KeyBank turning more of its delinquency into loss), and what the area
    is worth in dollars: the gap times KeyBank's delinquent dollars."""
    gap = {q_: kb[q_] - pg[q_] for q_ in Q if q_ in kb and q_ in pg}
    PR, PT, PB, PL, h = 150, 24, 34, 60, 230
    ih, iw = h - PT - PB, W - PL - PR
    xs = {q_: PL + iw * i / (len(Q) - 1) for i, q_ in enumerate(Q)}
    lo, hi = -30, 30
    y = lambda v: PT + ih * (1 - (min(max(v, lo), hi) - lo) / (hi - lo))      # noqa: E731
    p = ['<svg viewBox="0 0 %d %d" role="img" aria-label="KeyBank minus peers, 30+ to charge-off, points">' % (W, h)]
    for t in (-30, -15, 0, 15, 30):
        p.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="%s"/>' % (PL, W - PR, y(t), y(t), "var(--ink)" if t == 0 else "var(--grid)", 1.4 if t == 0 else 1))
        p.append('<text x="%d" y="%.1f" class="tk" text-anchor="end">%+d</text>' % (PL - 6, y(t) + 4, t))
    qs_ = [q_ for q_ in Q if q_ in gap]
    for i in range(len(qs_) - 1):
        a, b = qs_[i], qs_[i + 1]
        va, vb = gap[a], gap[b]
        col = "var(--z4)" if (va + vb) / 2 > 0 else "var(--z1)"
        p.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s" fill-opacity="0.85"/>'
                 % (xs[a], y(0), xs[a], y(va), xs[b], y(vb), xs[b], y(0), col))
    p.append('<polyline points="%s" fill="none" stroke="var(--key)" stroke-width="2.4"/>' % " ".join("%.1f,%.1f" % (xs[q_], y(gap[q_])) for q_ in qs_))
    for q_ in Q:
        if q_.endswith("Q1") and int(q_[:4]) % 2 == 0:
            p.append('<text x="%.1f" y="%d" class="tk" text-anchor="middle">%s</text>' % (xs[q_], h - 10, q_[:4]))
    p.append('<text x="%d" y="%.1f" class="an" style="fill:var(--key);font-weight:600">KeyBank minus peers %+.1f</text>' % (W - PR + 8, y(gap[qs_[-1]]) + 4, gap[qs_[-1]]))
    p.append('<text x="%d" y="%.1f" class="an" style="fill:var(--c-card)">above: more of KeyBank&rsquo;s</text>' % (W - PR + 8, y(22)))
    p.append('<text x="%d" y="%.1f" class="an" style="fill:var(--c-card)">delinquent dollars became loss</text>' % (W - PR + 8, y(18.5)))
    p.append('<text x="%d" y="%.1f" class="an" style="fill:var(--c-he)">below: fewer did</text>' % (W - PR + 8, y(-20)))
    p.append("</svg>")
    # the area priced: gap (share of delinquent dollars) x KeyBank's delinquent dollars that quarter
    worth = 0.0; n = 0
    for q_ in qs_:
        r = prod_num.get(q_)
        if r:
            dq = r["p3"] + r["p9"] + r["na"]
            worth += gap[q_] / 100 * dq / 4; n += 1          # four-quarter average gap: a quarter's share of it
    since, last = qs_[0], qs_[-1]
    cap = ('<p class="cap">The shaded area is the gap through time. Priced, it is the gap times KeyBank&rsquo;s delinquent dollars each quarter: %s to %s, KeyBank charged off about <b>%s %s</b> than it would have at the peer group&rsquo;s conversion rate '
           '(%d quarters; the card book was $%.1fbn at the end). The sign is the whole reading: red above zero is loss arriving faster than peers, green below is slower or more cures.</p>'
           % (since, last, m(abs(worth)), "less" if worth < 0 else "more", n, NUMK[last]["bal"] / 1e6))
    return "".join(p) + cap


# 1 30+ to charge-off and the gap
ind, pg, kb = flow4("Card", "Industry"), flow4("Card", "Peer group"), flow4("Card", "KeyBank")
lvl_chart = svg_chart(GQ, [{"data": ind, "color": "var(--ink)", "w": 1.8, "dash": True, "name": "Industry"}, {"data": pg, "color": "var(--muted)", "w": 1.8, "name": "Peer group"},
                           {"data": kb, "color": "var(--key)", "w": 2.6, "name": "KeyBank"}], 60, 110, [60, 80, 100], lambda v: "%d%%" % v, h=180,
                      ytitle="card: of the dollars 30+ (incl. nonaccrual) at quarter-end, % charged off over the next two quarters (4q avg)", label="card 30+ to charge-off")
def window_rate(key, n):
    v = NUM[key]; qs = [q_ for q_ in sorted(v) if q_ >= "2011Q1"]; out = {}
    for i, q_ in enumerate(qs):
        r = v[q_]; d = r["p3"] + r["p9"] + r["na"]
        if d > 0 and i + n < len(qs):
            out[q_] = 100 * sum(v[qs[k]]["gco"] for k in range(i + 1, i + n + 1)) / d
    return avg4(out)


win_chart = svg_chart(GQ, [{"data": window_rate("Card|Industry", 1), "color": "var(--c-he)", "w": 2.0, "name": "next 1 quarter"},
                           {"data": window_rate("Card|Industry", 2), "color": "var(--ink)", "w": 2.6, "name": "next 2 quarters (the book)"},
                           {"data": window_rate("Card|Industry", 3), "color": "var(--c-mtg)", "w": 2.0, "name": "next 3 quarters"}],
                      0, 160, [0, 40, 80, 120, 160], lambda v: "%d%%" % v, h=190,
                      ytitle="card, industry: % of quarter-end 30+ (incl. nonaccrual) dollars charged off over the next 1, 2 or 3 quarters (4q avg)",
                      label="window test")
raw = ('<div class="stack">%s<h3>The gap, literally: KeyBank minus peers, points</h3>%s'
       '<h3>Why two quarters: the same measure over the next one, two and three quarters</h3>%s'
       '<p class="cap">A card charges off at 180 days past due, so a dollar that is 30 days late at quarter-end has up to 150 days to go: two quarters covers the whole bucket, '
       'one quarter catches only the 90+ half (about 43%%), and three quarters counts dollars that were current at the quarter-end (over 100%%). Industry median 42%%, 86%%, 130%%; the two-quarter line is also the smoothest.</p></div>'
       % (lvl_chart, gap_chart(kb, pg, GQ, NUMK), win_chart))
mtx, best = matrix(kb)
secs.append(section("30+ to charge-off, and the gap to peers", "in the book: rated by level; the gap has no floor at zero",
                    raw, dual_chart(qrange("2012Q4", "2027Q2"), kb, "KeyBank card 30+ to charge-off", lambda v: "%.0f%%" % v, "var(--c-oth)", PICKED, PICK, pct2, k=max(best[1], 0), excl=True),
                    mtx, peer_panel("live", "credit-card", manual=("Citi",)),
                    "80%% means 80 cents of every dollar that was delinquent at quarter-end became a loss within six months. KeyBank now %.1f%%, peers %.1f%%." % (kb[max(kb)], pg[max(pg)])))


# 2 the pipeline: 30+ incl. NA -> 90+ incl. NA -> charge-offs, with refreshed FICO laid over it
def rate_series(key, fields):
    v = NUM[key]
    return {q_: 100 * sum(v[q_][f] for f in fields) / v[q_]["bal"] for q_ in v if v[q_]["bal"] and q_ >= "2011Q1"}


def gco_rate(key):
    v = NUM[key]; ks = sorted(v); out = {}
    for i in range(3, len(ks)):
        w = ks[i - 3:i + 1]
        b = sum(v[x]["bal"] for x in w) / 4
        if b and ks[i] >= "2011Q1":
            out[ks[i]] = 100 * sum(v[x]["gco"] for x in w) / b
    return out


def pipe_chart(title, fn, hi, ticks, fmt_):
    return svg_chart(Q11, [{"data": fn("Card|Industry"), "color": "var(--ink)", "w": 1.8, "dash": True, "name": "Industry"},
                           {"data": fn("Card|Peer group"), "color": "var(--muted)", "w": 1.8, "name": "Peer group"},
                           {"data": fn("Card|KeyBank"), "color": "var(--key)", "w": 2.6, "name": "KeyBank"}],
                     0, hi, ticks, fmt_, h=170, ytitle=title, label=title)


pipe = ('<div class="stack">%s%s%s</div>' % (
    pipe_chart("1. card 30+ incl. nonaccrual, % of balances, quarter-end", lambda k_: rate_series(k_, ("p3", "p9", "na")), 4, [0, 1, 2, 3, 4], pct2),
    pipe_chart("2. card 90+ incl. nonaccrual, % of balances, quarter-end", lambda k_: rate_series(k_, ("p9", "na")), 2.5, [0, 0.5, 1, 1.5, 2, 2.5], pct2),
    pipe_chart("3. card gross charge-offs, trailing four quarters, % of average balances", gco_rate, 8, [0, 2, 4, 6, 8], pct2)))
k30 = rate_series("Card|KeyBank", ("p3", "p9", "na"))
mtx, best = matrix(k30)
secs.append(section("The pipeline: 30+ incl. nonaccrual, then 90+ incl. nonaccrual, then charge-offs", "the three levels on one timeline; the roll steps between them add little once nonaccrual is in both",
                    pipe, dual_chart(qrange("2018Q2", "2026Q2"), KS, "KeyCorp card: share of balances with refreshed FICO under 660", pct1, "var(--c-mtg)", k30, "KeyBank card 30+ incl. nonaccrual", pct2, k=0, excl=False),
                    mtx, peer_panel("live", "credit-card", manual=("Citi",)),
                    "The level of 30+ incl. nonaccrual runs three quarters ahead of charge-offs (0.95 industry, 0.92 peers, 2011-2026); 90+ incl. nonaccrual divided by 30+ incl. nonaccrual adds 0.41 and 0.08. Below, refreshed FICO (the dashed line, not slid) turns in the same quarters as 30+: it is read off the same loans going delinquent, which is why the pipeline is the signal and FICO is not."))

# 3 paying only the minimum, and utilization
raw = ('<div class="stack">%s%s%s</div>' % (
    plain(Q12, MINPAY, "share of card accounts paying only the minimum", "var(--c-oth)", "large banks: share of active card accounts paying only the minimum, %", pct1),
    plain(Q12, UTIL90, "utilization, 90th percentile", "var(--c-mtg)", "large banks: utilization of the most stretched tenth of active accounts, %", pct1),
    plain(Q12, PICKED, PICK, "var(--key)", "compared against: " + PICK, pct2)))
mtx, best = matrix(MINPAY)
secs.append(section("Paying only the minimum, and stretched utilization", "in the book: the minimum-payment share is rated by level; utilization shown beside it",
                    raw, dual_chart(qrange("2013Q3", "2027Q2"), MINPAY, "share paying only the minimum", pct1, "var(--c-oth)", PICKED, PICK, pct2, k=max(best[1], 0), excl=True),
                    mtx, peer_panel("y14"), "The two move together (0.92). Both turn with card 30-89 in the same quarter and about a year ahead of card charge-offs."))

# 4 refreshed FICO
u660 = svg_chart(UQ, [{"data": U660[b_], "color": cols[b_], "w": 2.8 if b_ == "KeyCorp" else 1.8, "name": b_} for b_ in U660], 0, 25, [0, 5, 10, 15, 20, 25], pct1, h=200,
                 ytitle="share of scored card balances under 660, each bank's 10-Q, %", label="under 660 by bank")
raw = '<div class="stack">%s%s</div>' % (u660, plain(KQ, PICKED, PICK, "var(--key)", "compared against: " + PICK, pct2))
mtx, best = matrix(KS)
secs.append(section("Refreshed FICO", "set aside as a rating: it moves with 30-89; kept as the peer comparison",
                    raw, dual_chart(qrange("2019Q2", "2027Q2"), KS, "KeyCorp share under 660", pct1, "var(--c-mtg)", PICKED, PICK, pct2, k=max(best[1], 0), excl=False),
                    mtx, peer_panel("fico"), "KeyCorp&rsquo;s share under 660 and the weakest tenth&rsquo;s score (Philadelphia Fed) both turn in the same quarter as 30-89."))

# 5 purchase volume
raw = '<div class="stack">%s%s</div>' % (
    plain(qrange("2013Q3", "2026Q2"), PVG, "purchase volume by accounts under 660, change over a year", "var(--c-he)", "large banks: purchase volume by accounts under 660, % change over a year", lambda v: "%+.0f%%" % v),
    plain(qrange("2013Q3", "2026Q2"), PICKED, PICK, "var(--key)", "compared against: " + PICK, pct2))
mtx, best = matrix(PVG, is_change=True)
secs.append(section("Purchase volume by low-score accounts", "set aside: it falls as delinquency rises, a reaction",
                    raw, dual_chart(qrange("2013Q3", "2027Q2"), PVG, "purchase volume under 660, change", lambda v: "%+.0f%%" % v, "var(--c-he)", PICKED, PICK, pct2, k=max(best[1], 0), excl=True),
                    mtx, peer_panel("y14"), "Inverse (-0.7 to -0.85): low-score cardholders spend less in the quarters delinquency rises. Purchases, not balances."))

# 6 underwriting: one chart
YKNCO = yoy(_rd("credit-card_industry_net.csv"))
secs.append('<section class="sec"><h2>Underwriting: banks easing card standards, and what followed<small>context, not rated: lending policy, two to three years ahead of card losses</small></h2>'
            '<div class="two"><div>%s<p class="cap">One picture: the net share of banks easing card standards (dashed, slid 11 quarters later, the lead that fits) against the change in industry card charge-offs over a year (red). '
            'Where the dashed line is above its normal, more banks were easing; the red line follows. The stretch past 2026 is what banks already reported.</p></div>%s</div>'
            '<h3>How it fits every loss and delinquency series in the book</h3>%s</section>'
            % (dual_chart(qrange("2008Q1", "2029Q2"), EASE, "net share of banks easing card standards", lambda v: "%+.0f%%" % v, "var(--c-mtg)", YKNCO, "change in card net charge-offs over a year, industry", lambda v: "%+.1f" % v, k=11, excl=False, h=270),
               peer_panel("survey"), matrix(EASE, is_change=True)[0]))

# 7 mortgage
raw = ('<div class="stack">%s%s%s</div>' % (
    plain(qrange("2013Q1", "2026Q2"), over90, "mortgages owing more than 90% of the home's value", "var(--c-mtg)", "share of outstanding mortgages with mark-to-market LTV over 90%", pct1, 0),
    plain(qrange("1998Q1", "2025Q4"), PUR["PCT_DTI_GE44"], "purchase loans with DTI 44% or more", "var(--c-oth)", "share of new purchase mortgages, DTI 44%+", pct1, 0),
    plain(qrange("2002Q1", "2026Q2"), _rd("mortgage_industry_delinquency-90-plus-incl-nonaccrual_quarter-end.csv"), "mortgage 90+ incl. nonaccrual, industry", "var(--key)", "mortgage 90+ incl. nonaccrual, industry", pct2, 0)))
mtx, best = matrix(over90)
secs.append(section("Mortgage: equity and terms at origination", "set aside as ratings; the equity cushion is why mortgage delinquency is not turning into loss",
                    raw, dual_chart(qrange("2014Q1", "2027Q2"), over90, "share owing over 90% of value", pct1, "var(--c-mtg)", PICKED, PICK, pct2, k=max(best[1], 0), excl=True),
                    mtx, peer_panel("nmdb"), "0.3% of mortgages were underwater in 2026Q2 against 11.3% in 2013; DTI moves with rates and refinancing. Economic data, Book 2."))

# 8 across products: three pictures
MG90L = _rd("mortgage_industry_delinquency-90-plus-incl-nonaccrual_quarter-end.csv")
OC30L = _rd("other-consumer_industry_delinquency-30-89_quarter-end.csv")
MG30L = _rd("mortgage_industry_delinquency-30-89_quarter-end.csv")
XQ2 = qrange("2007Q1", "2026Q2")
x_raw = ('<div class="stack">%s%s%s</div>' % (
    plain(XQ2, OC30L, "other consumer 30-89, industry", "var(--c-oth)", "1. other consumer 30-89 days past due, industry, % of balances", pct2, 0),
    plain(XQ2, MG30L, "mortgage 30-89, industry", "var(--c-mtg)", "2. mortgage 30-89 days past due, industry, % of balances", pct2, 0),
    plain(XQ2, MG90L, "mortgage 90+ incl. nonaccrual, industry", "var(--key)", "3. mortgage 90+ incl. nonaccrual, industry, % of balances", pct2, 0)))
secs.append('<section class="sec"><h2>Across products<small>does early delinquency in one product come before another&rsquo;s? three pictures</small></h2>'
            '<div class="two"><div>%s<p class="cap"><b>Picture 1, the raw series.</b> Other consumer 30-89 turns up in 2007 and again in 2022; mortgage 30-89 turns at the same time in 2007; mortgage 90+ peaks two years later. The raw levels say the sizes: mortgage 90+ reached 8%% in 2010, other consumer 30-89 never passed 3%%.</p></div>%s</div>'
            '<h3>Picture 2: other consumer 30-89 slid 3 quarters later, laid over mortgage 90+ incl. nonaccrual, real units on both axes</h3>%s'
            '<p class="cap">Slid three quarters, the rise in other consumer early delinquency sits on the rise in mortgage late delinquency through 2007-2010 and again in 2022-2024. That is the linkage the lead profile below measures: 0.80 at three quarters.</p>'
            '<h3>Picture 3: how strongly a rise in other consumer 30-89 goes with a rise in each mortgage and home equity series, that many quarters later</h3><div class="chart">%s</div>'
            '<p class="cap">The peak of each curve is the lead. Mortgage 90+ peaks at about three quarters (0.80); mortgage&rsquo;s own 30-89 peaks in the same quarter, so other consumer is not earlier than mortgage&rsquo;s own early delinquency, it confirms it. '
            'What this section is for: when a product has no good signal of its own (mortgage losses are near zero), it says which other product&rsquo;s delinquency to watch, and how far ahead.</p></section>'
            % (x_raw, peer_panel("live", "other-consumer", manual=("Citi",)),
               dual_chart(qrange("2008Q1", "2027Q1"), OC30L, "other consumer 30-89, industry", pct2, "var(--c-oth)", MG90L, "mortgage 90+ incl. nonaccrual, industry", pct2, k=3, excl=False),
               xlag(OC30, TG)))

html = (STYLE + EXTRA + '<main><header style="display:grid;gap:6px"><div class="eyebrow">CONSUMER INDUSTRY ANALYSIS &middot; MOCK-UP OF ONE TAB, SECOND CUT &middot; %s</div>'
        '<h1>Signals</h1><p class="lede">One tab holding every signal found, each in its own units, compared against whichever product, measure and source the analyst picks, '
        'with the banks behind every chart recorded beside it. The numbers are real (public data, 2026Q2); the controls are drawn to show what the tab would offer.</p></header>'
        '<div class="tab"><span class="tabname">Signals</span>%s%s%s%s</div></main>'
        % (dt.date.today().strftime("%d %b %Y").upper(), CONTROLS, WHY, THIRTY, "".join(secs)))
out = HERE / "signals-mock.html"
out.write_text(html, encoding="utf-8")
print("written", out, len(html))
