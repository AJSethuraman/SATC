"""The competitor section: each bank on the score ruler at the latest quarter,
and its share under 660 since 2019Q4 (exact lines, proven ranges as bands)."""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
P = HERE / "data" / "peerfico"
sys.path.insert(0, str(HERE))
import peers as PE  # noqa: E402

DATA = json.loads((P / sys.argv[1]).read_text()) if len(sys.argv) > 1 else json.loads((P / "peers.json").read_text())
PRODUCTS = ["Card", "Mortgage", "Home equity", "Other consumer", "Auto"]
LABELLED = {620, 660, 680, 700, 720, 740, 750, 780, 800}
SHOW_RANGES = False      # ranges are read on the ruler; over time they are too wide to read
HISTORY_OFF = {"SoFi"}     # $0.1bn to $0.5bn at fair value; its early quarters jump from 3% to 30%


def breaks():
    """Each bank-product whose published cuts changed: (bank, product, quarter, before, after)."""
    out = []
    for product, banks in DATA.items():
        for bank, by in banks.items():
            prev = None
            for d in sorted(by):
                cuts = [e for e, _ in by[d]["edges"]]
                if prev is not None and cuts != prev:
                    out.append((bank, product, ql(d), prev, cuts))
                prev = cuts
    return out


def ql(d):
    return "%sQ%d" % (d[:4], (int(d[5:7]) - 1) // 3 + 1)


def pct(lo, hi):
    return "%.1f%%" % (100 * lo) if abs(lo - hi) < 1e-12 else "%.1f&ndash;%.1f%%" % (100 * lo, 100 * hi)


def ruler(product):
    banks = DATA.get(product, {})
    latest = max(max(by) for by in banks.values())
    rows = []
    for bank, by in banks.items():
        if latest in by:
            r = by[latest]
            rows.append((bank, r))
    rows.sort(key=lambda t: (t[1]["lo"] + t[1]["hi"]) / 2)
    w, rh, pl, pr = 700, 40, 118, 150
    lo_s, hi_s = 590, 820
    x = lambda v: pl + (w - pl - pr) * (min(max(v, lo_s), hi_s) - lo_s) / (hi_s - lo_s)    # noqa: E731
    h = rh * len(rows) + 34
    p = ['<svg viewBox="0 0 %d %d" role="img" aria-label="%s: each bank&rsquo;s share of scored balances under '
         'each score edge it publishes, %s">' % (w, h, product, ql(latest))]
    p.append('<rect x="%.1f" y="0" width="%.1f" height="%d" fill="var(--z5)"/>' % (x(lo_s), x(660) - x(lo_s), rh * len(rows)))
    p.append('<line x1="%.1f" x2="%.1f" y1="0" y2="%d" stroke="var(--c-card)" stroke-width="1.5"/>' % (x(660), x(660), rh * len(rows)))
    for v in (600, 650, 700, 750, 800):
        p.append('<text x="%.1f" y="%d" class="tk" text-anchor="middle">%d</text>' % (x(v), h - 8, v))
    for i, (bank, r) in enumerate(rows):
        yy = rh * i + 26
        me = bank == "KeyCorp"
        ink = "var(--key)" if me else "var(--ink)"
        p.append('<text x="%d" y="%d" class="%s" text-anchor="end"%s>%s</text>'
                 % (pl - 10, yy + 4, "an", ' style="fill:var(--key);font-weight:700"' if me else "", bank))
        es = [(e, s) for e, s in r["edges"]]
        p.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="var(--muted)" stroke-width="2"/>'
                 % (x(es[0][0]), x(es[-1][0]), yy, yy))
        for e, s in es:
            p.append('<circle cx="%.1f" cy="%d" r="4.5" fill="var(--panel)" stroke="%s" stroke-width="2"/>' % (x(e), yy, ink))
            if e in LABELLED or len(es) <= 4:
                p.append('<text x="%.1f" y="%d" class="tk halo" text-anchor="middle">%.0f%%</text>' % (x(e), yy - 9, 100 * s))
        p.append('<text x="%d" y="%d" class="an" text-anchor="start"%s>%s under 660</text>'
                 % (w - pr + 12, yy + 4, ' style="fill:var(--key);font-weight:700"' if me else "", pct(r["lo"], r["hi"])))
    p.append("</svg>")
    return "".join(p), latest


def history(product):
    banks = DATA.get(product, {})
    Q = sorted({d for by in banks.values() for d in by})
    w, h, pl, pr, pt, pb = 700, 230, 46, 170, 14, 30
    iw, ih = w - pl - pr, h - pt - pb
    top = max(max((r["lo"] for r in by.values() if abs(r["lo"] - r["hi"]) < 1e-12), default=0) for by in banks.values())
    y1 = min(1.0, max(0.05, (int(top * 100 / 5) + 1) * 5 / 100))
    xs = {d: pl + iw * i / max(1, len(Q) - 1) for i, d in enumerate(Q)}
    y = lambda v: pt + ih * (1 - min(v, y1) / y1)            # noqa: E731
    p = ['<svg viewBox="0 0 %d %d" role="img" aria-label="%s: share of scored balances under 660 by bank">' % (w, h, product)]
    for t in range(0, int(y1 * 100) + 1, 5 if y1 > 0.2 else 2 if y1 > 0.08 else 1):
        p.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--grid)"/>' % (pl, w - pr, y(t / 100), y(t / 100)))
        p.append('<text x="%d" y="%.1f" class="tk" text-anchor="end">%d%%</text>' % (pl - 6, y(t / 100) + 4, t))
    for d in Q:
        if d.endswith("12-31"):
            p.append('<text x="%.1f" y="%d" class="tk" text-anchor="middle">%s</text>' % (xs[d], h - 10, d[:4]))
    labels = []
    order = sorted(((b, by) for b, by in banks.items() if b not in HISTORY_OFF), key=lambda kv: kv[0] == "KeyCorp")
    for bank, by in order:
        ds = sorted(by)
        me = bank == "KeyCorp"
        col = "var(--key)" if me else "var(--muted)"
        runs, cur = [], []
        for d in ds:
            kind = abs(by[d]["lo"] - by[d]["hi"]) < 1e-12
            if cur and cur[-1][1] != kind:
                runs.append(cur); cur = [cur[-1][0:1] + (kind,)] if False else []
            cur.append((d, kind))
        if cur:
            runs.append(cur)
        for run in runs:
            dd = [d for d, _ in run]
            if run[0][1]:
                if len(dd) == 1:
                    p.append('<circle cx="%.1f" cy="%.1f" r="2" fill="%s"/>' % (xs[dd[0]], y(by[dd[0]]["lo"]), col))
                else:
                    p.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (
                        " ".join("%.1f,%.1f" % (xs[d], y(by[d]["lo"])) for d in dd), col, 2.6 if me else 1.4))
            elif SHOW_RANGES:
                hi_pts = ["%.1f,%.1f" % (xs[d], y(min(by[d]["hi"], y1))) for d in dd]
                lo_pts = ["%.1f,%.1f" % (xs[d], y(by[d]["lo"])) for d in reversed(dd)]
                if len(dd) == 1:
                    p.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="var(--bar)" stroke-width="3"/>' % (
                        xs[dd[0]], xs[dd[0]], y(min(by[dd[0]]["hi"], y1)), y(by[dd[0]]["lo"])))
                else:
                    p.append('<polygon points="%s" fill="var(--bar)" fill-opacity="0.35" stroke="var(--bar)" stroke-width="0.8"/>'
                             % " ".join(hi_pts + lo_pts))
        r = by[ds[-1]]
        exact = abs(r["lo"] - r["hi"]) < 1e-12
        if exact:
            labels.append((y(r["lo"]), bank, pct(r["lo"], r["hi"]), me))
    labels.sort()
    placed = []
    for yy, name, val, me in labels:
        yy = max(yy, (placed[-1] + 13) if placed else pt + 4)
        placed.append(yy)
        p.append('<text x="%d" y="%.1f" class="an" text-anchor="start"%s>%s %s</text>'
                 % (w - pr + 8, yy + 4, ' style="fill:var(--key);font-weight:700"' if me else "", name, val))
    p.append("</svg>")
    return "".join(p)


def section():
    parts = ['<section class="box"><h2>Competitors on the same ruler</h2>'
             '<p class="cap">Each bank&rsquo;s 10-Q prints its consumer loans in FICO bands, cut wherever that bank '
             'chooses. Each dot is one of its cuts, with the share of its scored balances under it. Where a bank cuts '
             'at 660 the share under 660 is exact; where it does not, the share must lie between its nearest cuts, '
             'and that proven range is what is shown. KeyCorp in red.</p>']
    for product in PRODUCTS:
        if product not in DATA:
            continue
        svg, latest = ruler(product)
        parts.append('<div class="wfc"><h3>%s, %s</h3><div class="chart">%s</div></div>' % (product, ql(latest), svg))
    parts.append('</section><section class="box"><h2>Share under 660 since 2019</h2>'
                 '<p class="cap">Only exact figures: a bank appears in the quarters it cut at 660. Banks on other cuts, and '
                 'quarters before a bank moved to 660, are ranges, read on the rulers above. KeyCorp in red.</p>')
    for product in PRODUCTS:
        if product not in DATA:
            continue
        parts.append('<div class="wfc"><h3>%s</h3><div class="chart">%s</div></div>' % (product, history(product)))
    parts.append('</section><section class="box"><h2>What was inferred, and how</h2><div class="notes"><ul>')
    for who, text in PE.CONCESSIONS:
        parts.append("<li><b>%s.</b> %s</li>" % (who, text))
    bk = breaks()
    if bk:
        parts.append("<li><b>Cuts that changed.</b> A bank that moved its cuts is exact on one side of the change "
                     "and a proven range on the other: " + "; ".join(
                         "%s %s from %s (%s to %s)" % (b, p_.lower(), q, "/".join(map(str, a)), "/".join(map(str, c)))
                         for b, p_, q, a, c in bk) + ".</li>")
    parts.append("<li><b>SoFi</b> is on the card ruler but not the history: its book is $0.1bn to $0.5bn, held at "
                 "fair value, and its early quarters jump from 3% to 30% under 660.</li>")
    parts.append("</ul></div></section>")
    return "".join(parts)


if __name__ == "__main__":
    print(len(section()))
