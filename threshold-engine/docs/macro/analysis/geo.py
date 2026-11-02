"""KeyBank's deposit footprint (FDIC Summary of Deposits) as weights on state
unemployment, against the national rate.

    (from threshold-engine/)
    python docs/macro/analysis/geo.py --sources work/macro-sources \
        --states ../credit-suite/verified-data/macro-observations.csv --out work/macro-geo.json
"""
import argparse
import collections
import csv
import json
import math
from pathlib import Path


def corr(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(
        sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sources", required=True)
    ap.add_argument("--states", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    src = Path(a.sources)
    weights = {}
    for yr in (2008, 2015, 2025):
        rows = [x["data"] for x in json.loads((src / ("sod-17534-%d.json" % yr)).read_text("utf-8"))["data"]]
        rows.sort(key=lambda r: -float(r["DEPSUMBR"] or 0))
        allw, exho = collections.Counter(), collections.Counter()
        for r in rows:
            allw[r["STALPBR"]] += float(r["DEPSUMBR"] or 0)
        for r in rows[1:]:  # the largest branch is the Cleveland head office
            exho[r["STALPBR"]] += float(r["DEPSUMBR"] or 0)
        tot = sum(allw.values())
        print(yr, len(rows), "branches, $%.1fbn;" % (tot / 1e6), "largest branch %s %s %.1f%%" % (
            rows[0]["CNTYNAMB"], rows[0]["STALPBR"], 100 * float(rows[0]["DEPSUMBR"]) / tot))
        weights[yr] = (allw, exho)
    ur = collections.defaultdict(dict)
    for r in csv.DictReader(open(a.states, encoding="utf-8")):
        sid = r["series_id"]
        if len(sid) == 4 and sid.endswith("UR") and r["value"] not in ("", "."):
            ur[sid[:2]][r["date"]] = float(r["value"])
    nat = {r["observation_date"]: float(r["UNRATE"]) for r in csv.DictReader(open(src / "UNRATE.csv")) if r["UNRATE"].strip()}
    out = {}
    for label, w in (("2025 deposits", weights[2025][0]), ("2025 deposits, head-office branch out", weights[2025][1]),
                     ("2008 deposits", weights[2008][0])):
        fw = {}
        for d in sorted(nat):
            num = den = 0.0
            for st, wt in w.items():
                if d in ur.get(st, {}):
                    num += wt * ur[st][d]
                    den += wt
            if den > 0.95 * sum(w.values()):
                fw[d] = num / den
        common = [d for d in sorted(fw) if d in nat]
        lv = corr([fw[d] for d in common], [nat[d] for d in common])
        ch = [(fw[d] - fw[p], nat[d] - nat[p]) for p, d in zip(common, common[12:])]
        cc = corr([x for x, _ in ch], [y for _, y in ch])
        gaps = sorted((fw[d] - nat[d], d) for d in common)
        print("%-40s levels r=%.3f, 12-month changes r=%.3f, gap %+.2f (%s) to %+.2f (%s)" % (
            label, lv, cc, gaps[0][0], gaps[0][1], gaps[-1][0], gaps[-1][1]))
        out[label] = {"levels_r": lv, "changes_r": cc, "series": fw}
    json.dump({"footprint": out, "weights_2025": dict(weights[2025][0])}, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
