"""Write fico.html: the public refreshed-FICO evidence, every figure read from
the filings and series named on the page."""
import csv, json, re, sys, collections
from pathlib import Path

S = Path(__file__).resolve().parent / "data"              # the record's own copies of the public data
TE = Path(__file__).resolve().parents[3]                 # threshold-engine, for the book's series files
sys.path.insert(0, str(TE / "src"))
from threshold_engine.scale import scale  # noqa: E402

HW, LS, Z = 0.5, 1.0, 2.5          # the book's agreed settings
COMP_DATA = sys.argv[1] if len(sys.argv) > 1 else "peers.json"


def ql(d):                          # '2026-06-30' -> '2026Q2'
    return "%sQ%d" % (d[:4], (int(d[5:7]) - 1) // 3 + 1)


def qrange(a, b):
    y, q = int(a[:4]), int(a[5])
    out = []
    while True:
        out.append("%dQ%d" % (y, q))
        if out[-1] == b:
            return out
        q += 1
        if q == 5:
            y, q = y + 1, 1


# ---------- KeyCorp, from its own 10-Q / 10-K XBRL ----------
key = json.loads((S / "keyhist" / "series.json").read_text())


def shares(rows):
    out = {}
    for d, a in rows:
        scored = sum(v for k, v in a.items() if k != "none")
        out[ql(d)] = {"u660": 100 * a.get("u660", 0) / scored, "bal": scored / 1e9, "none": a.get("none", 0) / 1e9,
                      "b750": 100 * a.get("750", 0) / scored}
    return out


K = {name: shares(rows) for name, rows in key.items()}
KQ = qrange("2018Q2", "2026Q2")

# ---------- peers at 2026Q2: each bank's share of scored balances under 660, read from its 10-Q
# XBRL (peerfico_pull.py, bands.py, peers.py) and kept here as data ----------
PEERS = json.loads((S / "peerfico" / "under660_2026q2.json").read_text())

# ---------- industry card, Philadelphia Fed (FRED copies) and the book's card series ----------
def fred(sid):
    rows = list(csv.reader(open(S / ("%s.csv" % sid))))[1:]
    return {"%sQ%d" % (a[:4], (int(a[5:7]) - 1) // 3 + 1): float(b) for a, b in rows if b not in ("", ".")}


P10, P25, P50 = fred("RCCCBSCOREPCT10"), fred("RCCCBSCOREPCT25"), fred("RCCCBSCOREPCT50")
M10, M25, M50 = fred("RCMFLBSCOREPCT10"), fred("RCMFLBSCOREPCT25"), fred("RCMFLBSCOREPCT50")
NCO = {ql(r[0]): float(r[1]) for r in csv.reader(open(TE / "docs/walkthrough-book/out/series/credit-card_industry_net.csv"))
       if r and r[0][:2] == "20"}
PQ = qrange("2012Q3", "2026Q2")


def lines_for(vals, direction="higher_is_worse", floor=True):
    out = scale(vals, direction, HW, LS, Z, floor)
    fits = None
    if out["bounds"] is None and out["spread_of_levels"]:
        sg = 1 if direction == "higher_is_worse" else -1
        fits = sg * (out["worst"] - out["median"]) / out["spread_of_levels"]
    return out, fits


# ---------- SVG ----------
W, PADL, PADR, PADT, PADB = 660, 46, 14, 14, 30
ZONE = ["var(--z1)", "var(--z2)", "var(--z3)", "var(--z4)", "var(--z5)"]


def svg_chart(Q, series, y0, y1, ticks, fmt, h=210, zones=None, notes=(), label="", bars=None, bar_max=None, ytitle=None):
    named = any(s.get("name") for s in series)
    PR = 172 if named else PADR
    PT = PADT + (16 if ytitle else 0)
    h = h + (16 if ytitle else 0)
    ih = h - PT - PADB
    iw = W - PADL - PR
    xs = {q: PADL + iw * i / (len(Q) - 1) for i, q in enumerate(Q)}
    y = lambda v: PT + ih * (1 - (min(max(v, y0), y1) - y0) / (y1 - y0))      # noqa: E731
    p = ['<svg viewBox="0 0 %d %d" role="img" aria-label="%s">' % (W, h, label)]
    if ytitle:
        p.append('<text x="%d" y="12" class="an" text-anchor="start" style="font-weight:600">%s</text>' % (PADL - 40, ytitle))
    if zones:
        edges = [y0] + [min(max(bd, y0), y1) for bd in zones] + [y1]
        for i in range(5):
            lo, hi = edges[i], edges[i + 1]
            if hi > lo:
                p.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>' % (PADL, y(hi), iw, y(lo) - y(hi), ZONE[i]))
    for t in ticks:
        p.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--grid)" stroke-width="1"/>' % (PADL, W - PR, y(t), y(t)))
        p.append('<text x="%d" y="%.1f" class="tk" text-anchor="end">%s</text>' % (PADL - 6, y(t) + 4, fmt(t)))
    step = 2 if len(Q) > 30 else 1
    for q in Q:
        if q.endswith("Q1") and int(q[:4]) % step == 0:
            p.append('<text x="%.1f" y="%d" class="tk" text-anchor="middle">%s</text>' % (xs[q], h - 10, q[:4]))
            p.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="var(--grid)" stroke-width="1"/>' % (xs[q], xs[q], PT + ih, PT + ih + 4))
    if bars:
        bw = iw / len(Q) * 0.62
        for q, v in bars.items():
            if q in xs:
                p.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="var(--bar)"/>' % (xs[q] - bw / 2, y(v), bw, y(y0) - y(v)))
    ends = []
    for s in series:
        pts, segs = [], []
        for q in Q:
            v = s["data"].get(q)
            if v is None:
                if pts:
                    segs.append(pts)
                pts = []
            else:
                pts.append("%.1f,%.1f" % (xs[q], y(v)))
        if pts:
            segs.append(pts)
        for sg in segs:
            if len(sg) == 1:
                x_, y_ = sg[0].split(",")
                p.append('<circle cx="%s" cy="%s" r="2.5" fill="%s"/>' % (x_, y_, s["color"]))
            else:
                p.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%s"%s/>'
                         % (" ".join(sg), s["color"], s.get("w", 2), ' stroke-dasharray="5 4"' if s.get("dash") else ""))
        have = [q for q in Q if s["data"].get(q) is not None]
        if not have:
            continue
        last = max(have, key=Q.index)
        p.append('<circle cx="%.1f" cy="%.1f" r="3.5" fill="%s"/>' % (xs[last], y(s["data"][last]), s["color"]))
        if s.get("name"):
            ends.append([y(s["data"][last]), s["name"], s["color"], fmt(s["data"][last]) if s.get("value", True) else ""])
    ends.sort()
    for i in range(1, len(ends)):
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 13)
    for yy, nm, col, val in ends:
        p.append('<text x="%d" y="%.1f" class="an" style="fill:%s;font-weight:600">%s%s</text>'
                 % (W - PR + 8, yy + 4, col, nm, (" " + val) if val else ""))
    for k, (q, text) in enumerate(notes):
        if q in xs:
            p.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="var(--muted)" stroke-dasharray="2 3"/>' % (xs[q], xs[q], PT, PT + ih))
            if text:
                anchor = "end" if xs[q] > (W - PR) * 0.6 else "start"
                dx = -4 if anchor == "end" else 4
                p.append('<text x="%.1f" y="%d" class="an" text-anchor="%s">%s</text>' % (xs[q] + dx, PT + 11 + 14 * k, anchor, text))
    p.append("</svg>")
    return "".join(p)


pct = lambda v: "%g%%" % v          # noqa: E731
COL = {"Card": "var(--c-card)", "Mortgage": "var(--c-mtg)", "Home equity": "var(--c-he)",
       "Other consumer": "var(--c-oth)"}

# ---------- KeyCorp panels ----------
panels = []
spec = [("Card", "Card", None, [0, 5, 10, 15], (0, 15), None),
        ("Home equity", "Home equity", "Residential (mortgage + home equity before 2020)", [0, 4, 8, 12], (0, 12), None),
        ("Mortgage", "Mortgage", None, [0, 2, 4, 6], (0, 6), None),
        ("Other consumer", "Other consumer (direct + indirect)", None, [0, 5, 10, 15, 20], (0, 20), "2021Q4")]
for title, name, before, ticks, (y0, y1), start in spec:
    d = {q: v["u660"] for q, v in K[name].items()}
    vals = [d[q] for q in KQ if q in d and (start is None or KQ.index(q) >= KQ.index(start))]
    out, fits = lines_for(vals)
    series = [{"data": d, "color": COL[title], "w": 2.4}]
    if before:
        series.append({"data": {q: v["u660"] for q, v in K[before].items()}, "color": "var(--muted)", "dash": True, "w": 1.6})
    notes = [("2021Q3", "Indirect auto sold, $3.3bn")] if title == "Other consumer" else []
    if title in ("Mortgage", "Home equity"):
        notes = [("2020Q1", "CECL tables begin")]
    chart = svg_chart(KQ, series, y0, y1, ticks, pct, zones=out["bounds"], notes=notes,
                      label="KeyCorp %s: share of scored balances with refreshed FICO under 660" % title.lower())
    bal = {q: v["bal"] for q, v in K[name].items()}
    bmax = max(bal.values())
    btick = [0, round(bmax / 2, 1), round(bmax, 1)] if bmax > 2 else [0, 0.5, 1.0]
    bchart = svg_chart(KQ, [], 0, max(btick) * 1.08, btick, lambda v: "$%gbn" % v, h=110, bars=bal,
                       label="KeyCorp %s scored balance" % title.lower())
    first, last_q = min(d, key=KQ.index), max(d, key=KQ.index)
    if out["bounds"]:
        b = out["bounds"]
        verdict = ("Lines from its own %d quarters: 2 begins %.2f%%, 3 %.2f%%, 4 %.2f%%, <b>5 High %.2f%%</b>. "
                   "Latest %.1f%%." % (len(vals), b[0], b[1], b[2], b[3], d[last_q]))
    else:
        verdict = ("<b>Refused</b> at z %.1f over its %d quarters: no quarter reaches High. Fits at z &le; %.2f. "
                   "Latest %.1f%%." % (Z, len(vals), fits, d[last_q]))
    if start:
        verdict += (" Lines from %s on: the quarters before the 2021Q3 sale are left out, as the book&rsquo;s jump rule "
                    "would leave them (scored balance $8.5bn to $5.0bn, -41%%)." % start)
    panels.append((title, chart, bchart, verdict, first, last_q, before))

# ---------- peers bars ----------
prods = ["Card", "Mortgage", "Home equity", "Other consumer"]
peer_rows = []
for prod in prods:
    have = [(bank, PEERS[bank][prod]) for bank in PEERS if prod in PEERS[bank]]
    have.sort(key=lambda t: t[1][0])
    mx = 20
    bars = []
    for bank, (v, bal) in have:
        me = bank == "KeyCorp"
        bars.append('<div class="pb%s"><span class="pn">%s</span><span class="pt"><span class="pf" style="width:%.1f%%"></span></span>'
                    '<span class="pv">%.1f%%</span><span class="ps">$%sbn</span></div>'
                    % (" me" if me else "", bank, 100 * v / mx, v, ("%.1f" % bal) if bal < 10 else "%.0f" % bal))
    peer_rows.append((prod, "".join(bars)))

# ---------- Philadelphia Fed card ----------
o10, f10 = lines_for([P10[q] for q in PQ], "lower_is_worse", False)
phil = svg_chart(PQ, [{"data": P50, "color": "var(--c-mtg)"}, {"data": P25, "color": "var(--c-he)"},
                      {"data": P10, "color": "var(--c-card)", "w": 2.6}],
                 600, 790, [600, 650, 700, 750], lambda v: "%d" % v, h=230,
                 notes=[("2019Q4", "10th pct low: 624"), ("2021Q2", "high: 644")],
                 label="Large-bank card accounts: current credit score percentiles")
mtg = svg_chart(PQ, [{"data": M50, "color": "var(--c-mtg)"}, {"data": M25, "color": "var(--c-he)"},
                     {"data": M10, "color": "var(--c-card)", "w": 2.6}],
                550, 800, [550, 600, 650, 700, 750, 800], lambda v: "%d" % v, h=230,
                label="Large-bank first-lien mortgage accounts: current credit score percentiles")
mnco = svg_chart(PQ, [{"data": {ql(r[0]): float(r[1]) for r in csv.reader(open(TE / "docs/walkthrough-book/out/series/mortgage_industry_net.csv")) if r and r[0][:2] == "20"},
                       "color": "var(--ink)"}], -0.05, 0.9, [0, 0.3, 0.6, 0.9], lambda v: "%g%%" % v, h=130,
                 label="Industry mortgage net charge-off rate, trailing four quarters")
nco = svg_chart(PQ, [{"data": NCO, "color": "var(--ink)"}], 0, 5, [0, 1, 2, 3, 4, 5], pct, h=150,
                label="Industry card net charge-off rate, trailing four quarters")


# ---------- KeyCorp waterfall from the vintage split ----------
VIN = json.loads((S / "keyhist" / "vintage.json").read_text())


def waterfall(d0, d1, cls):
    y0 = int(d0[:4])

    def buckets(date):
        out = {}
        for k, bb in VIN[date].items():
            c, v = k.split("|")
            if c != cls:
                continue
            sc = sum(x for kk, x in bb.items() if kk != "none")
            key = "older" if v == "prior" or (v.isdigit() and int(v) <= y0 - 2) else "new" if v.isdigit() and int(v) > y0 else v
            a = out.setdefault(key, [0.0, 0.0]); a[0] += sc; a[1] += bb.get("u660", 0)
        return out
    b0, b1 = buckets(d0), buckets(d1)
    t0, t1 = sum(v[0] for v in b0.values()), sum(v[0] for v in b1.values())
    s0, s1 = sum(v[1] for v in b0.values()) / t0, sum(v[1] for v in b1.values()) / t1
    nw = b1.get("new", [0, 0]); new_c = nw[1] / t1 - nw[0] / t1 * s0
    drift = run = 0.0
    for k in set(b0) | set(b1):
        if k == "new":
            continue
        a0, a1 = b0.get(k, [0, 0]), b1.get(k, [0, 0])
        r0 = a0[1] / a0[0] if a0[0] else 0; r1 = a1[1] / a1[0] if a1[0] else r0
        drift += a1[0] / t1 * (r1 - r0); run += (a1[0] / t1 - a0[0] / t0) * (r0 - s0)
    return [100 * s0, 100 * new_c, 100 * run, 100 * drift, 100 * s1], t0 / 1e9, t1 / 1e9


def wf_svg(vals, lo, hi, label):
    w, h, pl, pr, pt, pb = 660, 190, 46, 14, 16, 34
    names = ["End-2023", "New loans", "Run-off and mix", "Score drift", "Mid-2026"]
    iw, ih = w - pl - pr, h - pt - pb
    y = lambda v: pt + ih * (1 - (v - lo) / (hi - lo))         # noqa: E731
    p = ['<svg viewBox="0 0 %d %d" role="img" aria-label="%s">' % (w, h, label)]
    step = (hi - lo) / 4
    for i in range(5):
        tv = lo + i * step
        p.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--grid)"/>' % (pl, w - pr, y(tv), y(tv)))
        p.append('<text x="%d" y="%.1f" class="tk" text-anchor="end">%.1f%%</text>' % (pl - 6, y(tv) + 4, tv))
    bw = iw / 5 * 0.56
    run = vals[0]
    for i, nm in enumerate(names):
        cx = pl + iw * (i + 0.5) / 5
        if i in (0, 4):
            a, z, col = lo, vals[i], "var(--bar)"
            txt = "%.2f%%" % vals[i]
        else:
            a, z = run, run + vals[i]
            col = "var(--c-card)" if vals[i] > 0 else "var(--c-he)"
            txt = "%+.2f" % vals[i]
            run = z
        top, bot = max(a, z), min(a, z)
        p.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>' % (cx - bw / 2, y(top), bw, max(1.2, y(bot) - y(top)), col))
        p.append('<text x="%.1f" y="%.1f" class="tk" text-anchor="middle">%s</text>' % (cx, y(top) - 5, txt))
        p.append('<text x="%.1f" y="%d" class="an" text-anchor="middle">%s</text>' % (cx, h - 12, nm))
    p.append("</svg>")
    return "".join(p)


WF = []
for title, cls, lo, hi in (("Mortgage", "RealEstateResidentialMortgage", 0, 2.4), ("Home equity", "HomeEquityLoan", 6, 8.4)):
    vals, t0, t1 = waterfall("2023-12-31", "2026-06-30", cls)
    WF.append((title, wf_svg(vals, lo, hi, "KeyCorp %s: change in share under 660, end-2023 to mid-2026" % title.lower()), vals, t0, t1))


def bracket(p10, p25, p50):
    if p10 >= 660:
        return "fewer than 1 in 10 under 660"
    if p25 >= 660:
        return "1 in 10 to 1 in 4 under 660"
    if p50 >= 660:
        return "1 in 4 to half under 660"
    return "more than half under 660"


def ruler(rows):
    w, rh, pl, pr = 660, 50, 62, 14
    lo, hi = 500, 900
    x = lambda v: pl + (w - pl - pr) * (v - lo) / (hi - lo)     # noqa: E731
    h = rh * len(rows) + 30
    p = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Where the 10th, 25th and 50th percentile mortgage scores sat against 660">' % (w, h)]
    p.append('<rect x="%.1f" y="0" width="%.1f" height="%d" fill="var(--z5)"/>' % (x(lo), x(660) - x(lo), rh * len(rows)))
    p.append('<line x1="%.1f" x2="%.1f" y1="0" y2="%d" stroke="var(--c-card)" stroke-width="1.5"/>' % (x(660), x(660), rh * len(rows)))
    p.append('<text x="%.1f" y="%d" class="an" text-anchor="end">under 660</text>' % (x(660) - 6, rh * len(rows) - 6))
    for v in (500, 550, 600, 650, 700, 750, 800, 850):
        p.append('<text x="%.1f" y="%d" class="tk" text-anchor="middle">%d</text>' % (x(v), h - 8, v))
    for i, (q, a, b_, c) in enumerate(rows):
        yy = rh * i + 30
        p.append('<text x="%d" y="%d" class="tk" text-anchor="end">%s</text>' % (pl - 8, yy + 4, q))
        p.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="var(--muted)" stroke-width="2"/>' % (x(a), x(c), yy, yy))
        for v, nm in ((a, "10th"), (b_, "25th"), (c, "median")):
            p.append('<circle cx="%.1f" cy="%d" r="5" fill="var(--panel)" stroke="var(--ink)" stroke-width="2"/>' % (x(v), yy))
            p.append('<text x="%.1f" y="%d" class="tk" text-anchor="middle">%d</text>' % (x(v), yy - 10, v))
        p.append('<text x="%.1f" y="%d" class="an" text-anchor="start">%s</text>' % (x(c) + 10, yy + 4, bracket(a, b_, c)))
    p.append("</svg>")
    return "".join(p)


RULER = ruler([(q, M10[q], M25[q], M50[q]) for q in ("2012Q3", "2016Q2", "2020Q2", "2026Q2")])

sys.argv = [sys.argv[0], COMP_DATA]
sys.path.insert(0, str(Path(__file__).parent))
import comp as CP  # noqa: E402
COMP = CP.section()


# ---------- change in FICO: the early-warning view ----------
FALL = {PQ[i]: P10[PQ[i - 4]] - P10[PQ[i]] for i in range(4, len(PQ))}
CQ = PQ[4:]
fo = scale([FALL[q] for q in CQ], "higher_is_worse", HW, LS, 2.0, False)
fall_chart = svg_chart(CQ, [{"data": FALL, "color": "var(--c-card)", "w": 2.6}], -16, 10, [-15, -10, -5, 0, 5, 10],
                       lambda v: "%+d" % v if v else "0", h=230, zones=fo["bounds"],
                       notes=[("2020Q4", "low-score balances paid down"), ("2022Q3", "7-point fall")],
                       label="Fall in the large-bank card 10th percentile score over four quarters, with rating zones")
nco_c = svg_chart(CQ, [{"data": NCO, "color": "var(--ink)"}], 0, 5, [0, 1, 2, 3, 4, 5], pct, h=140,
                  label="Industry card net charge-off rate, trailing four quarters")
rate = lambda v: 1 + sum(v >= x for x in fo["bounds"])      # noqa: E731
FALL_HIGH = [q for q in CQ if rate(FALL[q]) == 5]

KS = {ql(d): 100 * a.get("u660", 0) / sum(x for k, x in a.items() if k != "none") for d, a in key["Card"]}
KQ2 = [q for q in KQ if q in KS]
KRISE = {q: KS[q] - KS["%dQ%s" % (int(q[:4]) - 1, q[5])] for q in KQ2 if "%dQ%s" % (int(q[:4]) - 1, q[5]) in KS}
ko = scale([KRISE[q] for q in KQ if q in KRISE], "higher_is_worse", HW, LS, 2.0, False)
kfit = (ko["worst"] - ko["median"]) / ko["spread_of_levels"]
KNCO = {ql(r[0]): float(r[1]) for r in csv.reader(open(TE / "docs/walkthrough-book/out/series/credit-card_keybank_net.csv"))
        if r and r[0][:2] == "20"}
krise_chart = svg_chart(KQ, [{"data": KRISE, "color": "var(--key)", "w": 2.6}], -3, 3, [-3, -2, -1, 0, 1, 2, 3],
                        lambda v: "%+g" % v if v else "0", h=200,
                        label="Rise in KeyCorp's card share under 660 over four quarters, percentage points")
knco_chart = svg_chart(KQ, [{"data": KNCO, "color": "var(--ink)"}], 0, 5, [0, 1, 2, 3, 4, 5], pct, h=130,
                       label="KeyBank card net charge-off rate, trailing four quarters")
CHANGE = (
    '<section class="box"><h2>Change in FICO: the early-warning measure</h2>'
    '<p class="cap">The level of a score trends with lending policy, but its change over a year moved ahead of card losses. '
    'The series is the score of the weakest tenth of card accounts at the large banks, on outstandings, so it falls for either of two '
    'reasons the data cannot separate: existing cardholders&rsquo; scores fall, or more low-score borrowers carry balances and so '
    'make up more of the accounts. Both lead to losses. '
    'Over 12 separate years, the large-bank card 10th percentile&rsquo;s change and the next year&rsquo;s change in industry '
    'card net charge-offs correlate at &minus;0.91; measured in the same year, &minus;0.36. Shown as a fall, so higher is worse, '
    'like the loss series.</p>'
    '<div class="zones"><span style="background:var(--z1)">1 Low</span><span style="background:var(--z2)">2 Moderate-Low</span>'
    '<span style="background:var(--z3)">3 Moderate</span><span style="background:var(--z4)">4 Moderate-High</span>'
    '<span style="background:var(--z5)">5 High</span></div>'
    '<h3>Large banks, card: fall in the score of the weakest tenth of accounts over four quarters (points)</h3>'
    '<div class="chart">%s</div><div class="chart">%s</div>'
    '<p class="cap">Zones from this history with width 0.5, Moderate-Low 1.0 and z 2.0, with no floor at zero (a change can '
    'be negative). At z 2.5 it is refused; it fits at z &le; 2.02. High begins at a %.1f-point fall: %s, before industry card '
    'losses rose from 1.8%% (2022Q3) to 4.6%% (2025Q1). Below: industry card net charge-offs, same quarters.</p>'
    '<h3>KeyCorp, card: rise in share under 660 over four quarters (percentage points)</h3>'
    '<div class="chart">%s</div><div class="chart">%s</div>'
    '<p class="cap">From KeyCorp&rsquo;s 10-Qs, 2019Q2 on (2021Q1 not read). Its change goes with KeyBank&rsquo;s card losses in the '
    'same year (correlation 0.67, 27 quarters) and the next (0.59, 23). Lines from its own history are refused at z 2.0; '
    'it fits at z &le; %.2f. Below: KeyBank card net charge-offs.</p></section>'
    % (fall_chart, nco_c, fo["bounds"][3], ", ".join(FALL_HIGH), krise_chart, knco_chart, kfit))


# ---------- evaluating FICO change as a rating ----------
ALLQ = sorted(NCO)
def next_year(q_):
    i = ALLQ.index(q_)
    return NCO[ALLQ[i + 4]] - NCO[q_] if i + 4 < len(ALLQ) else None
EV = [(q_, FALL[q_], next_year(q_), rate(FALL[q_])) for q_ in CQ if next_year(q_) is not None]
COVID = lambda q_: "2020Q1" <= q_ <= "2021Q4"          # noqa: E731


def scatter(EV=EV, bounds=None, hollow=None, marks=("2015Q4", "2017Q1", "2019Q4", "2022Q3", "2021Q1")):
    bounds = bounds or fo["bounds"]
    hollow = hollow or COVID
    w, h, pl, pr, pt, pb = 700, 340, 56, 16, 16, 44
    x0, x1, y0, y1 = -16, 10, -2.0, 2.0
    X = lambda v: pl + (w - pl - pr) * (v - x0) / (x1 - x0)       # noqa: E731
    Y = lambda v: pt + (h - pt - pb) * (1 - (v - y0) / (y1 - y0))  # noqa: E731
    p = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Each quarter: fall in score against the change in card losses over the next year">' % (w, h)]
    edges = [x0] + [max(x0, min(x1, t)) for t in bounds] + [x1]
    for i in range(5):
        p.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="%s"/>' % (X(edges[i]), pt, X(edges[i + 1]) - X(edges[i]), h - pt - pb, ZONE[i]))
        p.append('<text x="%.1f" y="%d" class="an" text-anchor="middle">%d</text>' % ((X(edges[i]) + X(edges[i + 1])) / 2, pt + 14, i + 1))
    for t in (-2, -1, 0, 1, 2):
        p.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--grid)"/>' % (pl, w - pr, Y(t), Y(t)))
        p.append('<text x="%d" y="%.1f" class="tk" text-anchor="end">%+g pt</text>' % (pl - 6, Y(t) + 4, t))
    p.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--ink)" stroke-width="1.2"/>' % (pl, w - pr, Y(0), Y(0)))
    for t in (-15, -10, -5, 0, 5, 10):
        p.append('<text x="%.1f" y="%d" class="tk" text-anchor="middle">%+d</text>' % (X(t), h - 26, t))
    p.append('<text x="%.1f" y="%d" class="an" text-anchor="middle">fall in the weakest tenth&rsquo;s score over four quarters (points) &rarr; worse</text>' % ((pl + w - pr) / 2, h - 8))
    p.append('<text x="14" y="%.1f" class="an" transform="rotate(-90 14 %.1f)" text-anchor="middle">card losses over the next year</text>' % ((pt + h - pb) / 2, (pt + h - pb) / 2))
    for q_, f, a, r in EV:
        cv = hollow(q_)
        p.append('<circle cx="%.1f" cy="%.1f" r="5" fill="%s" stroke="var(--ink)" stroke-width="1.2"><title>%s: fall %+g, losses next year %+.2f</title></circle>'
                 % (X(f), Y(max(y0, min(y1, a))), "none" if cv else "var(--ink)", q_, f, a))
    for q_, f, a, r in EV:
        if q_ in marks:
            p.append('<text x="%.1f" y="%.1f" class="an" text-anchor="start">%s</text>' % (X(f) + 7, Y(max(y0, min(y1, a))) - 6, q_))
    p.append("</svg>")
    return "".join(p)


def bars(EV=EV):
    w, rh, pl, pr = 700, 34, 150, 120
    g = {}
    for q_, f, a, r in EV:
        g.setdefault(r, []).append(a)
    h = rh * 5 + 20
    X = lambda v: pl + (w - pl - pr) * v                     # noqa: E731
    p = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Share of quarters at each rating followed by rising card losses">' % (w, h)]
    names = ["1 Low", "2 Moderate-Low", "3 Moderate", "4 Moderate-High", "5 High"]
    for i, k in enumerate(range(5, 0, -1)):
        v = g.get(k, [])
        up = sum(a > 0 for a in v)
        yy = 6 + rh * i
        p.append('<text x="%d" y="%d" class="an" text-anchor="end">%s</text>' % (pl - 10, yy + 17, names[k - 1]))
        p.append('<rect x="%d" y="%d" width="%.1f" height="20" fill="var(--grid)"/>' % (pl, yy + 4, X(1) - pl))
        if v:
            p.append('<rect x="%d" y="%d" width="%.1f" height="20" fill="%s"/>' % (pl, yy + 4, X(up / len(v)) - pl, ZONE[k - 1].replace("--z", "--z") if False else "var(--c-card)"))
        p.append('<text x="%.1f" y="%d" class="an" text-anchor="start">%d of %d quarters</text>' % (X(1) + 8, yy + 18, up, len(v)))
    p.append("</svg>")
    return "".join(p)


YEARS = {2013: (4, -0.29), 2014: (0, -0.29), 2015: (-3, 0.11), 2016: (-3, 0.52), 2017: (-2, 0.21), 2018: (1, 0.07),
         2019: (-1, 0.02), 2020: (9, -1.40), 2021: (4, -0.60), 2022: (-7, 1.27), 2023: (-5, 1.39), 2024: (-2, -0.17)}


def years_chart():
    w, h, pl, pr, pt, pb = 700, 250, 46, 16, 16, 40
    ys = sorted(YEARS)
    cw = (w - pl - pr) / len(ys)
    Y = lambda v: pt + (h - pt - pb) * (1 - (v + 10) / 20)    # noqa: E731
    p = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Each year: change in the weakest tenth&rsquo;s score, and the change in card losses the year after">' % (w, h)]
    for i, y_ in enumerate(ys):
        if y_ in (2020, 2021, 2022, 2023):
            p.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="var(--z5)" fill-opacity="0.5"/>' % (pl + cw * i, pt, cw, h - pt - pb))
    for t in (-10, -5, 0, 5, 10):
        p.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--grid)"/>' % (pl, w - pr, Y(t), Y(t)))
        p.append('<text x="%d" y="%.1f" class="tk" text-anchor="end">%+d</text>' % (pl - 6, Y(t) + 4, t))
    p.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--ink)"/>' % (pl, w - pr, Y(0), Y(0)))
    for i, y_ in enumerate(ys):
        s_, l_ = YEARS[y_]
        cx = pl + cw * i
        for j, (v, col) in enumerate(((s_, "var(--c-mtg)"), (l_ * 5, "var(--c-card)"))):
            top, bot = (Y(v), Y(0)) if v >= 0 else (Y(0), Y(v))
            p.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>' % (cx + cw * (0.18 + 0.32 * j), top, cw * 0.3, max(1, bot - top), col))
        p.append('<text x="%.1f" y="%d" class="tk" text-anchor="middle">%d&ndash;%02d</text>' % (cx + cw / 2, h - 22, y_ - 1, y_ % 100))
    p.append('<text x="%d" y="%d" class="an">shaded: pandemic years</text>' % (pl, h - 4))
    p.append("</svg>")
    return "".join(p)


EVAL = ('<section class="box"><h2>Should FICO change be a rating? The evidence, drawn</h2>'
        '<p class="cap">Each dot is a quarter: how far the weakest tenth&rsquo;s score fell over the past year (left to right, worse to the '
        'right), and what card losses did over the next year (up is worse). Background bands are the five ratings the book&rsquo;s method '
        'draws from this history (width 0.5, Moderate-Low 1.0, z 2.0, no floor). Hollow dots are 2020&ndash;21. If the measure works, dots '
        'in bands 4 and 5 sit above the line.</p><div class="chart">%s</div>'
        '<h3>At each rating, how often card losses rose over the next year</h3><div class="chart">%s</div>'
        '<h3>Year by year: the score change (blue) and the next year&rsquo;s change in losses (red, &times;5 to share the scale)</h3>'
        '<div class="chart">%s</div>'
        '<p class="cap">Read the blue bar against the red one: a falling score (blue below zero) should be followed by rising losses (red above). '
        'Outside the shaded years the moves are small: 2014&ndash;16 is the only clear one, a 3-point fall twice, then losses up 0.5. '
        'The lines here are drawn from the same history they rate, so the dots flatter the measure; a test that sets the lines only from '
        'earlier quarters is still to do.</p></section>' % (scatter(), bars(), years_chart()))


# ---------- the same test with 2020-2023 left out ----------
OUT = lambda q_: "2020Q1" <= q_ <= "2023Q4"            # noqa: E731
KEPT = [None if OUT(q_) else FALL[q_] for q_ in CQ]
fo2 = scale(KEPT, "higher_is_worse", HW, LS, 2.0, False)
fit2 = (fo2["worst"] - fo2["median"]) / fo2["spread_of_levels"]
if fo2["bounds"] is None:
    fo2b = scale(KEPT, "higher_is_worse", HW, LS, round(fit2 - 0.005, 2), False)["bounds"]
    z2 = round(fit2 - 0.005, 2)
else:
    fo2b, z2 = fo2["bounds"], 2.0
rate2 = lambda v: 1 + sum(v >= t for t in fo2b)         # noqa: E731
EV2 = [(q_, f, a, rate2(f)) for q_, f, a, r in EV if not OUT(q_)]
EVAL2 = ('<section class="box"><h2>The same test with 2020&ndash;2023 left out</h2>'
         '<p class="cap">The pandemic years raised the score and cut losses, then reversed both, so they are left out here as the book '
         'would leave out a period, with that reason. Lines are redrawn from the %d quarters that remain. At z 2.0 %s; shown at z %.2f, '
         'the highest that fits. Quarters after 2023 are rated too.</p><div class="chart">%s</div>'
         '<h3>At each rating, how often card losses rose over the next year (2020&ndash;2023 left out)</h3><div class="chart">%s</div>'
         '<p class="cap">What is left is %d quarters of small moves, 2013 to 2025: the score&rsquo;s fall ranged from %+d to %+d points '
         'and losses moved by at most %.2f points a year.</p></section>'
         % (sum(v is not None for v in KEPT),
            "the method refuses (nothing left reaches High)" if fo2["bounds"] is None else "the lines fit",
            z2, scatter(EV2, fo2b, lambda q_: False, ("2015Q4", "2016Q3", "2017Q1", "2019Q4", "2024Q1")), bars(EV2), len(EV2),
            min(f for _, f, _, _ in EV2), max(f for _, f, _, _ in EV2), max(abs(a) for _, _, a, _ in EV2)))


# ---------- when does the score move, against delinquency and losses ----------
import statistics as _st


def _rd(f):
    return {ql(r[0]): float(r[1]) for r in csv.reader(open(TE / "docs/walkthrough-book/out/series" / f)) if r and r[0][:2] == "20"}


LAGSER = [("30-89 days past due", _rd("credit-card_industry_delinquency-30-89_quarter-end.csv"), "var(--c-he)"),
          ("90+ incl. nonaccrual", _rd("credit-card_industry_delinquency-90-plus-incl-nonaccrual_quarter-end.csv"), "var(--c-oth)"),
          ("Net charge-offs", NCO, "var(--c-card)")]
LAGS = list(range(-4, 9))


def _corr(a, c):
    ma, mc = _st.mean(a), _st.mean(c)
    return sum((x - ma) * (y - mc) for x, y in zip(a, c)) / ((sum((x - ma) ** 2 for x in a) * sum((y - mc) ** 2 for y in c)) ** .5)


def lag_profile(s, excl):
    Qs = sorted(s); out = {}
    for k in LAGS:
        xs, ys = [], []
        for i in range(4, len(PQ)):
            a = PQ[i]
            if a not in Qs:
                continue
            j = Qs.index(a) + k
            if j - 4 < 0 or j >= len(Qs):
                continue
            if excl and ("2020Q1" <= a <= "2023Q4" or "2020Q1" <= Qs[j] <= "2023Q4"):
                continue
            xs.append(P10[a] - P10[PQ[i - 4]]); ys.append(s[Qs[j]] - s[Qs[j - 4]])
        out[k] = -_corr(xs, ys)
    return out


def lag_chart(excl):
    w, h, pl, pr, pt, pb = 700, 250, 46, 160, 14, 40
    X = lambda k: pl + (w - pl - pr) * (k - LAGS[0]) / (LAGS[-1] - LAGS[0])   # noqa: E731
    Y = lambda v: pt + (h - pt - pb) * (1 - (v + 0.6) / 1.6)                  # noqa: E731
    p = ['<svg viewBox="0 0 %d %d" role="img" aria-label="How strongly a falling score goes with rising delinquency and losses, by how many quarters later">' % (w, h)]
    for t in (-0.5, 0, 0.5, 1.0):
        p.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="%s"/>' % (pl, w - pr, Y(t), Y(t), "var(--ink)" if t == 0 else "var(--grid)"))
        p.append('<text x="%d" y="%.1f" class="tk" text-anchor="end">%.1f</text>' % (pl - 6, Y(t) + 4, t))
    for k in LAGS:
        lab = {-4: "1 yr before", 0: "same quarter", 4: "1 yr later", 8: "2 yrs later"}.get(k)
        if lab:
            p.append('<text x="%.1f" y="%d" class="tk" text-anchor="middle">%s</text>' % (X(k), h - 22, lab))
            p.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="var(--grid)"/>' % (X(k), X(k), pt, h - pb))
    ends = []
    for name, s, col in LAGSER:
        prof = lag_profile(s, excl)
        p.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.4"/>' % (" ".join("%.1f,%.1f" % (X(k), Y(v)) for k, v in prof.items()), col))
        kmax = max(prof, key=prof.get)
        p.append('<circle cx="%.1f" cy="%.1f" r="5" fill="%s"/>' % (X(kmax), Y(prof[kmax]), col))
        ends.append((Y(prof[LAGS[-1]]), name, col, kmax, prof[kmax]))
    ends.sort()
    last = None
    for yy, name, col, kmax, v in ends:
        yy = max(yy, last + 26) if last is not None else yy
        last = yy
        when = "same quarter" if kmax == 0 else "1 qtr later" if kmax == 1 else "%d qtrs later" % kmax
        p.append('<text x="%d" y="%.1f" class="an" style="fill:%s;font-weight:700">%s</text>' % (w - pr + 8, yy, col, name))
        p.append('<text x="%d" y="%.1f" class="an">peak %.2f, %s</text>' % (w - pr + 8, yy + 12, v, when))
    p.append('<text x="%d" y="%d" class="an">dots: where each link is strongest</text>' % (pl, h - 4))
    p.append("</svg>")
    return "".join(p)


LAG = ('<section class="box"><h2>When does the score move: before delinquency, or with it?</h2>'
       '<p class="cap">Scores fall when people run up their cards and when they go delinquent, so the score should move with '
       'delinquency, and charge-offs come later (cards charge off at 180 days past due). Each line is how strongly a fall in the '
       'weakest tenth&rsquo;s score over a year goes with a rise in that measure over a year, measured that many quarters later '
       '(1 means they move together exactly; 0, no link). All three are the book&rsquo;s industry card series.</p>'
       '<h3>All quarters</h3><div class="chart">%s</div><h3>2020&ndash;2023 left out</h3><div class="chart">%s</div>'
       '<p class="cap">The score moves within a quarter of 30&ndash;89 days past due, one to two quarters ahead of 90+ and nonaccrual, '
       'and about a year ahead of charge-offs. Its lead on charge-offs is the time delinquency takes to become a loss; '
       'against 30&ndash;89 it is not ahead.</p></section>' % (lag_chart(False), lag_chart(True)))


# ---------- the three series on one timeline ----------
D3089 = LAGSER[0][1]
def yoy(s):
    ks = sorted(s)
    return {ks[i]: s[ks[i]] - s[ks[i - 4]] for i in range(4, len(ks))}
Y3089, YNCO = yoy(D3089), yoy(NCO)
PEAKS = [("2015Q4", ""), ("2022Q3", "")]
stack = (svg_chart(CQ, [{"data": FALL, "color": "var(--c-mtg)", "w": 2.4}], -16, 10, [-15, -10, -5, 0, 5, 10],
                   lambda v: "%+d" % v if v else "0", h=170, notes=[("2016Q1", "fall peaks"), ("2022Q4", "fall peaks")],
                   label="Fall in the weakest tenth's score over four quarters")
         + svg_chart(CQ, [{"data": Y3089, "color": "var(--c-he)", "w": 2.4}], -0.6, 0.6, [-0.6, -0.3, 0, 0.3, 0.6],
                     lambda v: "%+.1f" % v if v else "0", h=150, notes=[("2016Q1", ""), ("2022Q4", "")],
                     label="Change in card 30-89 days past due over four quarters")
         + svg_chart(CQ, [{"data": YNCO, "color": "var(--c-card)", "w": 2.4}], -2, 2, [-2, -1, 0, 1, 2],
                     lambda v: "%+d" % v if v else "0", h=150, notes=[("2016Q1", ""), ("2022Q4", ""), ("2017Q1", "+1 yr"), ("2023Q4", "+1 yr")],
                     label="Change in card net charge-offs over four quarters"))
STACK = ('<section class="box"><h2>The same thing on one timeline</h2>'
         '<p class="cap">Top: how far the weakest tenth&rsquo;s score fell over the past year (points; up is worse). Middle: how much card '
         '30&ndash;89 days past due rose over the past year (percentage points). Bottom: how much card net charge-offs rose over the past '
         'year. Same quarters on each. The dotted lines mark where the score&rsquo;s fall peaked; in the middle chart delinquency rises at '
         'the same time, and in the bottom chart charge-offs peak about a year later (the second pair of lines).</p>'
         '<div class="chart">%s</div></section>' % stack)


# ---------- underwriting: does loosening lead? ----------
def _philly(fname, col):
    r = list(csv.reader(open(S / "philly" / fname, encoding="utf-8-sig")))
    j = r[0].index(col)
    return {x[0]: float(x[j].replace("%", "").replace("$", "").replace(",", "")) for x in r[1:]
            if x and x[0][:2] == "20" and "Q" in x[0] and x[j].strip() not in ("", ".")}


EASE = {ql(a): -float(v) for a, v in list(csv.reader(open(S / "sloos" / "DRTSCLCC.csv")))[1:] if v not in ("", ".")}
SUB_ACC = _philly("26Q2-CreditCardOriginations.csv", "Percentage of New Accounts with < 660 Credit Score")
SUB_COM = _philly("26Q2-CreditCardOriginations.csv", "Percentage of New Commitments with < 660 Credit Score")
UWSER = [("Banks easing card standards", EASE, "var(--c-mtg)"),
         ("New card accounts under 660", SUB_ACC, "var(--c-he)"),
         ("New card lines ($) under 660", SUB_COM, "var(--c-oth)")]
ULAGS = list(range(-4, 13))


def uw_profile(x, y, excl):
    Y = sorted(y); out = {}
    for k in ULAGS:
        xs, ys = [], []
        for a in sorted(x):
            if a not in Y:
                continue
            i = Y.index(a) + k
            if not 0 <= i < len(Y):
                continue
            if excl and ("2020Q1" <= a <= "2023Q4" or "2020Q1" <= Y[i] <= "2023Q4"):
                continue
            xs.append(x[a]); ys.append(y[Y[i]])
        out[k] = _corr(xs, ys) if len(xs) > 8 else None
    return out


def uw_chart(target, excl):
    w, h, pl, pr, pt, pb = 700, 250, 46, 190, 14, 40
    X = lambda k: pl + (w - pl - pr) * (k - ULAGS[0]) / (ULAGS[-1] - ULAGS[0])   # noqa: E731
    Yp = lambda v: pt + (h - pt - pb) * (1 - (v + 1) / 2)                        # noqa: E731
    p = ['<svg viewBox="0 0 %d %d" role="img" aria-label="How strongly looser underwriting goes with a later rise, by how many quarters later">' % (w, h)]
    for t in (-1, -0.5, 0, 0.5, 1):
        p.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="%s"/>' % (pl, w - pr, Yp(t), Yp(t), "var(--ink)" if t == 0 else "var(--grid)"))
        p.append('<text x="%d" y="%.1f" class="tk" text-anchor="end">%.1f</text>' % (pl - 6, Yp(t) + 4, t))
    for k, lab in ((-4, "1 yr before"), (0, "same quarter"), (4, "1 yr later"), (8, "2 yrs later"), (12, "3 yrs later")):
        p.append('<text x="%.1f" y="%d" class="tk" text-anchor="middle">%s</text>' % (X(k), h - 22, lab))
        p.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="var(--grid)"/>' % (X(k), X(k), pt, h - pb))
    ends = []
    for name, s, col in UWSER:
        prof = {k: v for k, v in uw_profile(s, target, excl).items() if v is not None}
        p.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.4"/>' % (" ".join("%.1f,%.1f" % (X(k), Yp(v)) for k, v in prof.items()), col))
        kmax = max(prof, key=prof.get)
        p.append('<circle cx="%.1f" cy="%.1f" r="5" fill="%s"/>' % (X(kmax), Yp(prof[kmax]), col))
        ends.append((Yp(prof[max(prof)]), name, col, kmax, prof[kmax]))
    ends.sort(); last = None
    for yy, name, col, kmax, v in ends:
        yy = max(yy, last + 26) if last is not None else yy
        last = yy
        p.append('<text x="%d" y="%.1f" class="an" style="fill:%s;font-weight:700">%s</text>' % (w - pr + 8, yy, col, name))
        p.append('<text x="%d" y="%.1f" class="an">peak %.2f, %d qtrs later</text>' % (w - pr + 8, yy + 12, v, kmax))
    p.append('<text x="%d" y="%d" class="an">dots: where each link is strongest</text>' % (pl, h - 4))
    p.append("</svg>")
    return "".join(p)


SQ = qrange("1996Q1", "2026Q2")
ease_chart = svg_chart(SQ, [{"data": EASE, "color": "var(--c-mtg)", "w": 2.2}], -90, 40, [-80, -40, 0, 40],
                       lambda v: "%+d%%" % v if v else "0", h=170, notes=[("2001Q1", "tightening"), ("2008Q4", "tightening")],
                       label="Net share of banks easing credit card standards, Senior Loan Officer Survey")
nco_long = svg_chart(SQ, [{"data": YNCO, "color": "var(--c-card)", "w": 2.2}], -3, 6, [-3, 0, 3, 6],
                     lambda v: "%+d" % v if v else "0", h=150, label="Rise in industry card net charge-offs over four quarters")
sub_chart = svg_chart(PQ, [{"data": SUB_ACC, "color": "var(--c-he)", "w": 2.2}, {"data": SUB_COM, "color": "var(--c-oth)", "w": 2.2}],
                      0, 30, [0, 10, 20, 30], lambda v: "%d%%" % v, h=170, notes=[("2015Q4", "loosest"), ("2024Q3", "tightest")],
                      label="Share of new card accounts and new card lines going to scores under 660")
nco_short = svg_chart(PQ, [{"data": YNCO, "color": "var(--c-card)", "w": 2.2}], -2, 2, [-2, -1, 0, 1, 2],
                      lambda v: "%+d" % v if v else "0", h=140, label="Rise in industry card net charge-offs over four quarters")
M = {c: _philly("26Q2-First-LienOriginations.csv", c) for c in
     ("Original Back-End Debt-to-Income (DTI) (75th percentile)", "Original Back-End Debt-to-Income (DTI) (90th percentile)",
      "Original Loan-to-Value (LTV) (75th percentile)", "Original Loan-to-Value (LTV) (90th percentile)",
      "Original Credit Score (10th percentile)")}
mdti = svg_chart(PQ, [{"data": M["Original Back-End Debt-to-Income (DTI) (75th percentile)"], "color": "var(--c-he)", "w": 2.2},
                      {"data": M["Original Back-End Debt-to-Income (DTI) (90th percentile)"], "color": "var(--c-card)", "w": 2.2}],
                 30, 50, [30, 35, 40, 45, 50], lambda v: "%d%%" % v, h=170,
                 label="Back-end debt-to-income at origination, first-lien mortgages, 75th and 90th percentile")
mltv = svg_chart(PQ, [{"data": M["Original Loan-to-Value (LTV) (75th percentile)"], "color": "var(--c-he)", "w": 2.2},
                      {"data": M["Original Loan-to-Value (LTV) (90th percentile)"], "color": "var(--c-card)", "w": 2.2}],
                 60, 100, [60, 70, 80, 90, 100], lambda v: "%d%%" % v, h=170,
                 label="Loan-to-value at origination, first-lien mortgages, 75th and 90th percentile")
mfico = svg_chart(PQ, [{"data": M["Original Credit Score (10th percentile)"], "color": "var(--c-mtg)", "w": 2.2}],
                  600, 740, [600, 650, 700], lambda v: "%d" % v, h=150,
                  label="Credit score at origination, first-lien mortgages, 10th percentile")

UW = ('<section class="box"><h2>Underwriting: does loosening come first?</h2>'
      '<p class="cap">Refreshed FICO moved with delinquency. Underwriting sits earlier in the chain: who is approved, and on what terms, '
      'comes before anyone goes delinquent. Two public card measures: the Federal Reserve&rsquo;s Senior Loan Officer Survey (the net share '
      'of banks easing card standards; easing is up), from 1996; and the share of new card accounts, and of new credit lines in dollars, '
      'going to scores under 660 at the large banks (Philadelphia Fed), from 2012.</p>'
      '<h3>Banks easing card standards (1996 on), and the rise in card charge-offs (2007 on)</h3><div class="chart">%s%s</div>'
      '<h3>New card accounts and lines going to scores under 660, and the rise in card charge-offs</h3>'
      '<div class="legend"><span><i class="sw" style="background:var(--c-he)"></i>new accounts</span><span><i class="sw" style="background:var(--c-oth)"></i>new lines ($)</span></div>'
      '<div class="chart">%s%s</div>'
      '<h3>How strongly looser underwriting goes with a later rise in charge-offs</h3><p class="cap">All quarters, then 2020&ndash;2023 left out. '
      'Below zero in the first year is banks reacting: they tighten while losses climb.</p><div class="chart">%s</div><div class="chart">%s</div>'
      '<h3>The same against a later rise in 30&ndash;89 days past due</h3><div class="chart">%s</div>'
      '<p class="cap">Unlike refreshed FICO, these come before delinquency, not with it: easier underwriting is followed by rising 30&ndash;89 '
      'about one and a half to two years later and by rising charge-offs two to three years later. The left-out view rests on 20 to 37 '
      'quarters, and the survey before 2006 has no card loss series here to test against.</p>'
      '<h3>Mortgage terms at origination (large banks, 2012 on)</h3>'
      '<div class="legend"><span><i class="sw" style="background:var(--c-he)"></i>75th percentile</span><span><i class="sw" style="background:var(--c-card)"></i>90th percentile</span></div>'
      '<p class="cap">Back-end debt-to-income</p><div class="chart">%s</div><p class="cap">Loan-to-value</p><div class="chart">%s</div>'
      '<p class="cap">Credit score, 10th percentile</p><div class="chart">%s</div>'
      '<p class="cap">Mortgage losses have been near zero since 2014, so these cannot be tested against losses here; they show how terms '
      'have moved. The survey&rsquo;s mortgage questions were redrawn in 2015, so its mortgage history is in two pieces.</p></section>'
      % (ease_chart, nco_long, sub_chart, nco_short, uw_chart(YNCO, False), uw_chart(YNCO, True), uw_chart(Y3089, False),
         mdti, mltv, mfico))


# ---------- slid forward and laid over the loss line ----------
def _std(s):
    v = list(s.values()); m = _st.mean(v); sd = _st.pstdev(v)
    return {k: (x - m) / sd for k, x in s.items()}


def _shift(s, k):
    allq = qrange("1995Q1", "2030Q4")
    return {allq[allq.index(q_) + k]: v for q_, v in s.items()}


def short(t):
    return t if len(t) <= 24 else t[:23] + '…'


def overlay(lead, k, lead_name, target, target_name, Qs, lead_col):
    a = _std(_shift(lead, k)); t = _std(target)
    return svg_chart(Qs, [{"data": t, "color": "var(--c-card)", "w": 2.6, "name": short(target_name), "value": False},
                          {"data": a, "color": lead_col, "w": 2.2, "dash": True, "name": short(lead_name), "value": False}],
                     -4, 4, [-3, 0, 3], lambda v: "" if v else "normal", h=220, ytitle="each line around its own normal",
                     label="%s, moved %d quarters later, laid over %s" % (lead_name, k, target_name))


OQ = qrange("2007Q1", "2026Q2")
SHIFT = ('<section class="box"><h2>Read it this way: slide underwriting forward and lay it over losses</h2>'
         '<p class="cap">The red line is how much card charge-offs (or 30&ndash;89 days past due) rose over the past year. The dashed line '
         'is an underwriting measure, moved later by the delay where it matched best, so a loosening in 2015 is drawn in 2017. Both are '
         'drawn on their own scale around their own average (the middle line), because they are in different units: read the shape, '
         'not the height. Where the dashed line rises, the red one should rise with it.</p>'
         '<h3>New card accounts under 660, moved 9 quarters later, over the rise in charge-offs</h3>'
         '<div class="legend"><span><i class="sw" style="background:var(--c-card)"></i>rise in card charge-offs</span>'
         '<span><i class="sw" style="background:var(--c-he)"></i>new accounts under 660, 9 quarters earlier</span></div>'
         '<div class="chart">%s</div>'
         '<h3>Banks easing card standards, moved 11 quarters later, over the rise in charge-offs</h3>'
         '<div class="legend"><span><i class="sw" style="background:var(--c-card)"></i>rise in card charge-offs</span>'
         '<span><i class="sw" style="background:var(--c-mtg)"></i>banks easing, 11 quarters earlier</span></div>'
         '<div class="chart">%s</div>'
         '<h3>New card accounts under 660, moved 6 quarters later, over the rise in 30&ndash;89 days past due</h3>'
         '<div class="legend"><span><i class="sw" style="background:var(--c-card)"></i>rise in card 30&ndash;89</span>'
         '<span><i class="sw" style="background:var(--c-he)"></i>new accounts under 660, 6 quarters earlier</span></div>'
         '<div class="chart">%s</div>'
         '<p class="cap">The dashed line runs past 2026 where it has already happened: that stretch is what the measure says is coming.</p></section>'
         % (overlay(SUB_ACC, 9, "New card accounts under 660", YNCO, "the rise in charge-offs", qrange("2013Q1", "2028Q3"), "var(--c-he)"),
            overlay(EASE, 11, "Banks easing card standards", YNCO, "the rise in charge-offs", qrange("2007Q1", "2029Q1"), "var(--c-mtg)"),
            overlay(SUB_ACC, 6, "New card accounts under 660", Y3089, "the rise in 30-89", qrange("2013Q1", "2027Q4"), "var(--c-he)")))


# ---------- one scale: every signal slid forward by its delay, over the rise in charge-offs ----------
NQ = qrange("2019Q1", "2029Q1")
ONE = [("Rise in card charge-offs (actual)", _std(YNCO), "var(--c-card)", 0, False),
       ("Rise in 30-89, 2 quarters earlier", _std(_shift(Y3089, 2)), "var(--ink)", 2, True),
       ("Fall in weakest tenth's score, 4 quarters earlier", _std(_shift(FALL, 4)), "var(--c-oth)", 4, True),
       ("New accounts under 660, 9 quarters earlier", _std(_shift(SUB_ACC, 9)), "var(--c-he)", 9, True),
       ("Banks easing standards, 11 quarters earlier", _std(_shift(EASE, 11)), "var(--c-mtg)", 11, True)]


def one_scale():
    w, h, pl, pr, pt, pb = 700, 300, 112, 16, 14, 30
    iw, ih = w - pl - pr, h - pt - pb
    xs = {q_: pl + iw * i / (len(NQ) - 1) for i, q_ in enumerate(NQ)}
    Y = lambda v: pt + ih * (1 - (max(-3.5, min(3.5, v)) + 3.5) / 7)    # noqa: E731
    p = ['<svg viewBox="0 0 %d %d" role="img" aria-label="Every signal on one scale, moved later by its delay, over the rise in card charge-offs">' % (w, h)]
    now = xs["2026Q2"]
    p.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="var(--z3)" fill-opacity="0.6"/>' % (now, pt, w - pr - now, ih))
    p.append('<text x="%.1f" y="%d" class="an" text-anchor="start">ahead of today: what the signals already say</text>' % (now + 6, pt + 12))
    for t, lab in ((-2, "well below normal"), (0, "normal"), (2, "well above normal")):
        p.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="%s"/>' % (pl, w - pr, Y(t), Y(t), "var(--ink)" if t == 0 else "var(--grid)"))
        p.append('<text x="%d" y="%.1f" class="an" text-anchor="end">%s</text>' % (pl - 6, Y(t) + 4, lab))
    for q_ in NQ:
        if q_.endswith("Q1"):
            p.append('<text x="%.1f" y="%d" class="tk" text-anchor="middle">%s</text>' % (xs[q_], h - 10, q_[:4]))
    for name, s, col, k, dash in ONE:
        pts = ["%.1f,%.1f" % (xs[q_], Y(s[q_])) for q_ in NQ if q_ in s]
        p.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%s"%s/>' % (" ".join(pts), col, 3 if not dash else 2, ' stroke-dasharray="5 4"' if dash else ""))
    p.append("</svg>")
    return "".join(p)


def now_rows():
    rows = []
    for name, s, unit, k, good in (
            ("Card net charge-offs", NCO, "%", 0, None),
            ("Rise in card charge-offs over the year", YNCO, " pts", 0, "down"),
            ("Rise in card 30-89 days past due over the year", Y3089, " pts", 2, "down"),
            ("Fall in the weakest tenth's score over the year", FALL, " pts", 4, "down"),
            ("New card accounts going to scores under 660", SUB_ACC, "%", 9, "down"),
            ("New card lines ($) going to scores under 660", SUB_COM, "%", 9, "down"),
            ("Banks easing card standards (net share)", EASE, "%", 11, "down")):
        ks = sorted(s)
        last, yr = ks[-1], ks[-5]
        rows.append((name, last, s[last], s[yr], unit, k))
    return rows


NOW = ('<section class="box"><h2>Where each signal stands now, and what it points to</h2>'
       '<p class="cap">One scale for everything: each line is drawn around its own normal (the middle line), in units of its usual swing, '
       'so they can share one chart. Each signal is moved later by the delay where it best matched charge-offs, so its line already '
       'runs past today. The solid red line is what charge-offs actually did.</p>'
       '<div class="legend">' + "".join('<span><i class="sw" style="background:%s"></i>%s</span>' % (c, n) for n, _, c, _, _ in ONE) + '</div>'
       '<div class="chart">%s</div>' % one_scale() +
       '<table style="width:100%%;border-collapse:collapse;font-size:13px"><tr><th style="text-align:left">Signal</th><th>Latest</th><th>A year earlier</th><th>Reads ahead by</th></tr>' +
       "".join('<tr style="border-top:1px solid var(--grid)"><td>%s</td><td style="text-align:right;font-family:var(--f-mono)">%s %+.2f%s</td>'
               '<td style="text-align:right;font-family:var(--f-mono)">%+.2f%s</td><td style="text-align:right">%s</td></tr>'
               % (n, q_, v, u, v0, u, ("%d quarters" % k) if k else "now") for n, q_, v, v0, u, k in now_rows()).replace("+4.01%", "4.01%").replace("+4.46%", "4.46%") +
       '</table><p class="cap">Read it as: charge-offs are already falling (the red line has turned down); 30&ndash;89 and the refreshed '
       'score are flat, so little new is entering the loss pipeline; the tightening of 2023&ndash;25 (green and blue dashed lines below '
       'normal) points to calm charge-offs into 2027. The share of new accounts under 660 has risen since 2025, which on its 9-quarter '
       'delay is the first sign of pressure from about 2028. These are the lines read forward, not a forecast.</p></section>')


# ---------- who got new loans: scores at origination, read literally ----------
CO = {c: _philly("26Q2-CreditCardOriginations.csv", "Original Credit Score (%s percentile)" % c) for c in ("10th", "25th", "50th")}
MO = {c: _philly("26Q2-First-LienOriginations.csv", "Original Credit Score (%s percentile)" % c) for c in ("10th", "25th", "50th")}
orig_card = svg_chart(PQ, [{"data": CO["50th"], "color": "var(--c-mtg)"}, {"data": CO["25th"], "color": "var(--c-he)"},
                           {"data": CO["10th"], "color": "var(--c-card)", "w": 2.6}], 550, 800, [550, 600, 650, 700, 750, 800],
                      lambda v: "%d" % v, h=230, label="Credit score at origination, new card accounts at the large banks")
orig_mtg = svg_chart(PQ, [{"data": MO["50th"], "color": "var(--c-mtg)"}, {"data": MO["25th"], "color": "var(--c-he)"},
                          {"data": MO["10th"], "color": "var(--c-card)", "w": 2.6}], 600, 820, [600, 650, 700, 750, 800],
                     lambda v: "%d" % v, h=230, label="Credit score at origination, new first-lien mortgages at the large banks")
ORIG = ('<section class="box"><h2>Who got new loans: scores at origination</h2>'
        '<p class="cap">Read literally: in each quarter, the large banks&rsquo; new loans went to borrowers with these scores. One in ten new '
        'accounts scored at or below the red line; one in four at or below the green; half at or below the blue. A falling red line means '
        'banks were lending deeper into lower scores.</p>'
        '<div class="legend"><span><i class="sw" style="background:var(--c-card)"></i>10th percentile</span><span><i class="sw" style="background:var(--c-he)"></i>25th</span><span><i class="sw" style="background:var(--c-mtg)"></i>Median</span></div>'
        '<h3>New card accounts</h3><div class="chart">%s</div>'
        '<p class="cap">Latest 10th percentile %d, against %d a year earlier and %d at its lowest (%s).</p>'
        '<h3>New first-lien mortgages</h3><div class="chart">%s</div>'
        '<p class="cap">Philadelphia Fed, FR Y-14M banks, 2012Q3 to 2026Q2: the score at origination of the primary borrower, a commercially '
        'available score, not necessarily FICO. Debt-to-income and loan-to-value at origination exist for mortgages only (in the underwriting '
        'section below); there is no public card equivalent.</p></section>'
        % (orig_card, CO["10th"]["2026Q2"], CO["10th"]["2025Q2"], min(CO["10th"].values()),
           min(CO["10th"], key=CO["10th"].get), orig_mtg))


# ---------- literal terms at origination: which lead ----------
M3089 = yoy(_rd("mortgage_industry_delinquency-30-89_quarter-end.csv"))
M90 = yoy(_rd("mortgage_industry_delinquency-90-plus-incl-nonaccrual_quarter-end.csv"))
CARD_ORIG_RISK = {k: -v for k, v in CO["10th"].items()}              # lower score = riskier, drawn as up
DTI90 = M["Original Back-End Debt-to-Income (DTI) (90th percentile)"]
LTV90 = M["Original Loan-to-Value (LTV) (90th percentile)"]


def _nice(lo, hi):
    """A rounded axis covering lo..hi, with zero included when the data crosses it."""
    import math
    if hi <= lo:
        hi = lo + 1
    span = hi - lo
    step = 10 ** math.floor(math.log10(span / 4))
    for m in (1, 2, 2.5, 5, 10):
        if span / (step * m) <= 5:
            step *= m
            break
    a = math.floor(lo / step) * step
    z = math.ceil(hi / step) * step
    ticks = []
    t = a
    while t <= z + step / 2:
        ticks.append(round(t, 10))
        t += step
    return a, z, ticks


def _fmt_for(ticks):
    span = max(abs(x) for x in ticks) or 1
    if span >= 100:
        return lambda v: "%.0f" % v
    if span >= 10:
        return lambda v: "%.1f" % v
    return lambda v: "%.2f" % v


def raw_pair(lead, k, target, Qs, col, lead_name, target_name):
    """The two series in their own units, same quarters, the lead slid k quarters later: nothing rescaled."""
    sh = _shift(lead, k) if k else lead
    out = []
    for d_, nm, c_ in ((target, target_name, "var(--c-card)"), (sh, lead_name, col)):
        vals = [d_[q_] for q_ in Qs if q_ in d_]
        if not vals:
            continue
        lo, hi, ticks = _nice(min(vals), max(vals))
        f = _fmt_for(ticks)
        out.append(svg_chart(Qs, [{"data": d_, "color": c_, "w": 2.4, "name": short(nm)}], lo, hi, ticks, f, h=150,
                             ytitle="%s (own units, not rescaled)" % nm, label="%s in its own units" % nm))
    return ('<details class="raw" open><summary>The same two series in their own units</summary>%s</details>' % "".join(out))


def ov(lead, k, target, Qs, col, lead_name, target_name):
    return ('<div class="legend"><span><i class="sw" style="background:var(--c-card)"></i>%s</span>'
            '<span><i class="sw" style="background:%s"></i>%s</span></div>' % (target_name, col, lead_name)
            + overlay(lead, k, lead_name, target, target_name, Qs, col)
            + raw_pair(lead, k, target, Qs, col, lead_name, target_name))


LITERAL = ('<section class="box"><h2>Literal terms at origination: which ones come first?</h2>'
           '<p class="cap">Each chart lays an origination term (dashed) over what later happened to the book (solid red), both drawn around '
           'their own normal so the shapes can be compared. Where the dashed line is moved later, it is by the delay where it matched best.</p>'
           '<h3>Card: score at origination (10th percentile, drawn so lower scores are up), moved 8 quarters later, over the rise in card charge-offs</h3>%s'
           '<p class="cap">This one leads. When the bottom tenth of new card accounts scored lower, charge-offs rose about two years later '
           '(the 2021 dip to 614 sits over the 2023 rise). With 2020&ndash;2023 left out the match is 0.85 to 0.87; with them in, 0.42.</p>'
           '<h3>Mortgage: debt-to-income at origination (90th percentile), not moved, over the rise in mortgage 30&ndash;89</h3>%s'
           '<p class="cap">This one moves at the same time, not before: the match is strongest with no delay (0.78 to 0.85) and fades as the '
           'delay grows. Both rose and fell with interest rates and refinancing waves, so it is not evidence of a lead.</p>'
           '<h3>Mortgage: loan-to-value at origination (90th percentile), not moved, over the rise in mortgage 90+ and nonaccrual</h3>%s'
           '<p class="cap">No consistent link either way. Mortgage delinquency in 2012&ndash;2026 was driven by the pre-2008 loans running '
           'off and by pandemic forbearance, and there has been no mortgage downturn since 2012 to test these terms against.</p></section>'
           % (ov(CARD_ORIG_RISK, 8, YNCO, qrange("2013Q1", "2028Q2"), "var(--c-he)", "lower origination scores, 8 quarters earlier", "rise in card charge-offs"),
              ov(DTI90, 0, M3089, qrange("2013Q1", "2026Q2"), "var(--c-mtg)", "debt-to-income at origination", "rise in mortgage 30-89"),
              ov(LTV90, 0, M90, qrange("2013Q1", "2026Q2"), "var(--c-oth)", "loan-to-value at origination", "rise in mortgage 90+ incl. nonaccrual")))

# ---------- page ----------
def panel_html(t):
    title, chart, bchart, verdict, first, last_q, before = t
    extra = (' The dashed gray line before 2020 is KeyCorp&rsquo;s &ldquo;Residential, prime&rdquo; class, mortgage and home '
             'equity together, as it reported them then.') if before else ""
    return ('<section class="panel"><h3><span class="sw" style="background:%s"></span>%s</h3>'
            '<div class="chart">%s</div><div class="chart small">%s</div>'
            '<p class="cap">Share of scored balances with a refreshed FICO under 660, %s to %s (top; shading is the five rating '
            'zones the book&rsquo;s method draws from this history at the agreed settings); scored balance (bottom).%s</p>'
            '<p class="verdict">%s</p></section>' % (COL[title], title, chart, bchart, first, last_q, extra, verdict))


html = open(S / "fico_page" / "template.html", encoding="utf-8").read()
html = (html.replace("{{PANELS}}", "".join(panel_html(t) for t in panels))
            .replace("{{PEERS}}", "".join('<div class="pcol"><h4>%s</h4>%s</div>' % (p, b) for p, b in peer_rows))
            .replace("{{PHIL}}", phil).replace("{{MTG}}", mtg).replace("{{RULER}}", RULER).replace("{{COMP}}", COMP).replace("{{CHANGE}}", NOW + ORIG + LITERAL + UW + SHIFT + EVAL + EVAL2 + LAG + STACK + CHANGE).replace("{{WF}}", "".join(
                '<div class="wfc"><h3>%s</h3><div class="chart">%s</div><p class="cap">%.2f%% to %.2f%% under 660; scored balance $%.1fbn to $%.1fbn.</p></div>'
                % (ti, sv, v[0], v[4], a0, a1) for ti, sv, v, a0, a1 in WF)).replace("{{MNCO}}", mnco).replace("{{NCO}}", nco)
            .replace("{{P10FIT}}", "%.2f" % f10).replace("{{P10LAST}}", "%d" % P10["2026Q2"])
            .replace("{{P10MED}}", "%d" % o10["median"]))
(S / "fico_page" / "fico.html").write_text(html, encoding="utf-8")
print("written", len(html))
