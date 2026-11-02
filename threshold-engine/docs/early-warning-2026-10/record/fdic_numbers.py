"""Dollar amounts behind the ratios, per quarter, for industry, peer group and KeyBank ($ thousands as filed):
balance, 30-89, 90+ accruing, nonaccrual, gross charge-offs and recoveries in the quarter (year to date differenced)."""
import json, sys
from pathlib import Path

CACHE, ROSTER, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
PROD = {"Card": ("LNCRCD", "P3CRCD", "P9CRCD", "NACRCD", "DRCRCD", "CRCRCD"),
        "Other consumer": ("LNCONOTH+LNCONRP", "P3CONOTH", "P9CONOTH", "NACONOTH", "DRCONOTH", "CRCONOTH"),
        "Mortgage": ("LNRERSFM", "P3RERSFM", "P9RERSFM", "NARERSFM", "DRRERSFM", "CRRERSFM")}
peers = {str(b["cert"]) for b in json.loads(ROSTER.read_text())["banks"] if b["group"] == "peer"}
num = lambda r, f: sum(float(r.get(p) or 0) for p in f.split("+"))       # noqa: E731
data = {}
for f in sorted(CACHE.glob("q*.json")):
    d = json.loads(f.read_text()); rows = d if isinstance(d, list) else d.get("rows", d)
    data[f.stem[1:]] = {str(r["CERT"]): r for r in rows}
qs = sorted(data)
lab = lambda q: "%sQ%d" % (q[:4], (int(q[4:6]) - 1) // 3 + 1)            # noqa: E731
out = {}
for prod, (ln, p3, p9, na, dr, cr) in PROD.items():
    for who, mem in (("Industry", None), ("Peer group", peers), ("KeyBank", {"17534"})):
        s = {}
        for i in range(1, len(qs)):
            q, qp = qs[i], qs[i - 1]
            cur, prv = data[q], data[qp]
            banks = [c for c in cur if mem is None or c in mem]
            both = [c for c in banks if c in prv]
            stock = lambda f: sum(num(cur[c], f) for c in banks)          # noqa: E731
            flow = lambda f: (sum(num(cur[c], f) for c in both) if q[4:6] == "03"
                              else sum(num(cur[c], f) - num(prv[c], f) for c in both))   # noqa: E731
            s[lab(q)] = {"bal": stock(ln), "p3": stock(p3), "p9": stock(p9), "na": stock(na), "gco": flow(dr), "rec": flow(cr)}
        out["%s|%s" % (prod, who)] = s
OUT.write_text(json.dumps(out))
print("ok", {k: len(v) for k, v in out.items()})
