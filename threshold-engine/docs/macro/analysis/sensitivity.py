"""Change-on-change: rise in a loss rate over four quarters, k quarters on, against the rise in the
economic series over four quarters. Fit on one window, test on the next. Also each recession's rise in
losses per point of unemployment (trough to peak, NBER peaks).

    (from threshold-engine/)
    python docs/macro/analysis/sensitivity.py work/macro-analysis.json work/macro-sensitivity.json
"""
import json, math, sys
A = json.load(open(sys.argv[1])); S = A["series"]
qi = lambda q: int(q[:4]) * 4 + int(q[-1]) - 1
qs = lambda i: "%dQ%d" % (i // 4, i % 4 + 1)
def d4(s): return {q: v - s[qs(qi(q) - 4)] for q, v in s.items() if qs(qi(q) - 4) in s}
def pairs(x, y, k, lo, hi):
    out = [(v, y[qs(qi(q) + k)]) for q, v in x.items() if qs(qi(q) + k) in y and qi(lo) <= qi(q) + k <= qi(hi)]
    return [a for a, _ in out], [b for _, b in out]
def ols(xs, ys):
    n = len(xs); mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx; a = my - b * mx
    res = [y - a - b * x for x, y in zip(xs, ys)]
    se = math.sqrt(sum(e * e for e in res) / (n - 2)); seb = se / math.sqrt(sxx)
    r = b * math.sqrt(sxx) / math.sqrt(sum((y - my) ** 2 for y in ys))
    return {"a": a, "b": b, "se": se, "se_b": seb, "r": r, "n": n}
CASES = [("UR", "Card NCO (TTM, Fed)", 4), ("UR", "Card NCO (TTM, Fed)", 2), ("UR", "Other consumer incl. auto NCO (TTM, FDIC)", 4),
         ("UR", "Card 30+ incl. nonaccrual (Fed)", 2), ("UR", "Mortgage NCO (TTM, Fed)", 4), ("UR", "Home equity NCO (TTM, FDIC)", 4)]
out = []
for xname, yname, k in CASES:
    dx, dy = d4(S[xname]), d4(S[yname])
    row = {"x": "Rise in unemployment over 4 quarters (points)", "y": "Rise in " + yname + " over 4 quarters, %d quarters later" % k, "k": k}
    for fit_name, (lo, hi) in {"fit to 2007": ("1985Q1", "2007Q4"), "fit to 2019": ("1985Q1", "2019Q4")}.items():
        xs, ys = pairs(dx, dy, k, lo, hi)
        if len(xs) < 12: row[fit_name] = None; continue
        f = ols(xs, ys); row[fit_name] = {kk: round(v, 3) if isinstance(v, float) else v for kk, v in f.items()}
        tests = {}
        for tname, (tlo, thi) in {"2008-2019": ("2008Q1", "2019Q4"), "2020-2026": ("2020Q1", "2026Q2")}.items():
            if fit_name == "fit to 2019" and tname == "2008-2019": continue
            tx, ty = pairs(dx, dy, k, tlo, thi)
            if not tx: continue
            pred = [f["a"] + f["b"] * x for x in tx]; err = [y - p for y, p in zip(ty, pred)]
            tests[tname] = {"n": len(tx), "rmse": round(math.sqrt(sum(e * e for e in err) / len(err)), 3),
                            "corr_pred_actual": round(sum((p - sum(pred)/len(pred)) * (y - sum(ty)/len(ty)) for p, y in zip(pred, ty)) /
                                                       (math.sqrt(sum((p - sum(pred)/len(pred))**2 for p in pred)) * math.sqrt(sum((y - sum(ty)/len(ty))**2 for y in ty)) or 1), 3),
                            "largest_actual_rise": round(max(ty), 3), "predicted_at_that_quarter": round(pred[ty.index(max(ty))], 3)}
        row[fit_name]["tests"] = tests
    out.append(row)
# episode ratios: rise in loss (trough to peak) per point of unemployment rise
eps = []
for t in A["turning"]:
    ur = t["ur_peak_value"] - t["ur_trough_value"]
    for lname in ("Card NCO (TTM, Fed)", "Other consumer incl. auto NCO (TTM, FDIC)", "Mortgage NCO (TTM, Fed)", "Home equity NCO (TTM, FDIC)"):
        v = t[lname]
        if v.get("trough_value") is None or v.get("peak_value") is None: continue
        rise = v["peak_value"] - v["trough_value"]
        eps.append({"episode": t["episode"], "loss": lname, "ur_rise": round(ur, 2), "loss_rise": round(rise, 3),
                    "per_point": round(rise / ur, 3) if ur else None, "ur_from": t["ur_trough"], "ur_to": t["ur_peak"],
                    "loss_from": v["trough"], "loss_to": v["peak"]})
json.dump({"change_fits": out, "episodes": eps}, open(sys.argv[2], "w"), indent=1)
for r in out:
    for fn in ("fit to 2007", "fit to 2019"):
        f = r.get(fn)
        if f: print("%-75s %s b=%.3f (se %.3f) r=%.2f n=%d tests=%s" % (r["y"][:75], fn, f["b"], f["se_b"], f["r"], f["n"], f["tests"]))
for e in eps: print(e)
