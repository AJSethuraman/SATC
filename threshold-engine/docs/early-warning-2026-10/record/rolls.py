"""Estimated roll-forward and cure from Call Report stocks and flows, per quarter,
for industry (every filer), the peer group (roster peers, as filed) and KeyBank.

  30-89 -> 90+ roll  = 90+ (incl. nonaccrual) at t  /  30-89 at t-1
  estimated cure     = 1 - that roll (what left 30-89 without reaching 90+;
                       also includes loans charged off or sold early, and is
                       an aggregate estimate, not a tracked cohort)
  90+ -> charge-off  = gross charge-offs in quarter t  /  90+ (incl. nonaccrual) at t-1
All amounts $ thousands; charge-offs are year to date, differenced."""
import json, sys
from pathlib import Path

CACHE = Path(sys.argv[1]); ROSTER = Path(sys.argv[2]); OUT = Path(sys.argv[3])
PROD = {"Card": ("LNCRCD", "P3CRCD", "P9CRCD", "NACRCD", "DRCRCD"),
        "Other consumer": ("LNCONOTH+LNCONRP", "P3CONOTH", "P9CONOTH", "NACONOTH", "DRCONOTH")}
roster = json.loads(ROSTER.read_text())["banks"]
peers = {str(b["cert"]) for b in roster if b["group"] == "peer"}
KEY = "17534"


def num(row, f):
    return sum(float(row.get(p) or 0) for p in f.split("+"))


files = sorted(CACHE.glob("q*.json"))
data = {}
for f in files:
    d = json.loads(f.read_text())
    rows = d if isinstance(d, list) else d.get("rows", d)
    data[f.stem[1:]] = {str(r["CERT"]): r for r in rows}
qs = sorted(data)
lab = lambda q: "%sQ%d" % (q[:4], (int(q[4:6]) - 1) // 3 + 1)      # noqa: E731
out = {}
for prod, (ln, p3, p9, na, dr) in PROD.items():
    for who, members in (("Industry", None), ("Peer group", peers), ("KeyBank", {KEY})):
        series = {}
        for i in range(1, len(qs)):
            q, qp = qs[i], qs[i - 1]
            cur, prv = data[q], data[qp]
            both = [c for c in cur if c in prv and (members is None or c in members)]
            if not both:
                continue
            s = lambda rows, f: sum(num(rows[c], f) for c in both)          # noqa: E731
            p3_prev = s(prv, p3)
            sev_prev = s(prv, p9) + s(prv, na)
            sev_now = s(cur, p9) + s(cur, na)
            co = s(cur, dr) if q[4:6] == "03" else s(cur, dr) - s(prv, dr)
            if p3_prev > 0 and sev_prev > 0:
                series[lab(q)] = {"roll": sev_now / p3_prev, "cure": 1 - sev_now / p3_prev, "co_from_90": co / sev_prev,
                                  "p3": s(cur, p3), "sev": sev_now, "co": co, "bal": s(cur, ln)}
        out["%s|%s" % (prod, who)] = series
OUT.write_text(json.dumps(out))
for k, v in out.items():
    ks = sorted(v)
    pick = [q for q in ("2007Q4", "2009Q2", "2012Q4", "2016Q4", "2019Q4", "2021Q2", "2023Q4", "2026Q2") if q in v]
    print("%-28s %d qtrs | roll 30-89->90+: %s" % (k, len(ks), "  ".join("%s %.2f" % (q, v[q]["roll"]) for q in pick)))
    print("%-28s         | 90+ -> charge-off: %s" % ("", "  ".join("%s %.2f" % (q, v[q]["co_from_90"]) for q in pick)))
