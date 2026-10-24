"""Illustrations for the macro-helper proposal, on public data only.

Inputs (all public):
  repo threshold-engine/tests/data/*.csv  the tool's own loss series (TTM NCO)
  repo credit-suite/verified-data/macro-observations.csv  Fed/FHFA/G.19 series
  SOURCES/UNRATE.csv               BLS unemployment rate via FRED
  SOURCES/dol-claims-us.xml        DOL weekly initial claims, national
  SOURCES/fed-dsr.json             Fed household debt service ratio table (fetch.py)

Run (from threshold-engine/):
    python docs/macro/analysis/analyse.py .. work/macro-sources work/macro-analysis.json
"""
import csv, json, math, re, statistics as st, sys
from collections import defaultdict
from pathlib import Path

REPO, DATA, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])


def q_of(date):
    y, m = int(date[:4]), int(date[5:7])
    return "%dQ%d" % (y, (m - 1) // 3 + 1)


def qi(q):
    return int(q[:4]) * 4 + int(q[-1]) - 1


def qs(i):
    return "%dQ%d" % (i // 4, i % 4 + 1)


def tool_series(name):
    out = {}
    for line in open(REPO / "threshold-engine/tests/data" / name, encoding="utf-8"):
        if line.startswith("#") or line.startswith("date"):
            continue
        d, v = line.strip().split(",")
        out[q_of(d)] = float(v)
    return out


verified = defaultdict(dict)
for r in csv.DictReader(open(REPO / "credit-suite/verified-data/macro-observations.csv", encoding="utf-8")):
    verified[r["series_id"]][r["date"]] = float(r["value"]) if r["value"] not in ("", ".") else None


def quarterly_mean(dated):
    acc = defaultdict(list)
    for d, v in dated.items():
        if v is not None:
            acc[q_of(d)].append(v)
    return {q: sum(v) / len(v) for q, v in acc.items() if len(v) >= 1}


def complete_quarters(dated, per_q):
    acc = defaultdict(list)
    for d, v in dated.items():
        if v is not None:
            acc[q_of(d)].append(v)
    return {q: sum(v) / len(v) for q, v in acc.items() if len(v) >= per_q}


def yoy(s):
    return {q: 100 * (v / s[qs(qi(q) - 4)] - 1) for q, v in s.items() if qs(qi(q) - 4) in s and s[qs(qi(q) - 4)]}


def d4(s):
    return {q: v - s[qs(qi(q) - 4)] for q, v in s.items() if qs(qi(q) - 4) in s}


# ---------------------------------------------------------------- losses
LOSS = {
    "Card NCO (TTM, Fed)": tool_series("cards_nco_ttm.csv"),
    "Mortgage NCO (TTM, Fed)": tool_series("mortgage_nco_ttm.csv"),
    "Home equity NCO (TTM, FDIC)": tool_series("home_equity_nco_ttm.csv"),
    "Other consumer incl. auto NCO (TTM, FDIC)": tool_series("other_consumer_with_auto_nco_ttm.csv"),
    "Card 30+ incl. nonaccrual (Fed)": {q_of(d): v for d, v in verified["DRCCLACBS"].items()},
    "Other consumer 30+ incl. nonaccrual (Fed)": {q_of(d): v for d, v in verified["DROCLACBS"].items()},
    "Mortgage 30+ incl. nonaccrual (Fed)": {q_of(d): v for d, v in verified["DRSFRMACBS"].items()},
}

# ---------------------------------------------------------------- macro
unrate = {}
for r in csv.DictReader(open(DATA / "UNRATE.csv")):
    if r["UNRATE"].strip():
        unrate[r["observation_date"]] = float(r["UNRATE"])
UR = complete_quarters(unrate, 3)

claims_w = {}
xml = (DATA / "dol-claims-us.xml").read_text("utf-8", "replace")
for m in re.finditer(r"<weekEnded>(\d\d)/(\d\d)/(\d{4})</weekEnded>\s*<InitialClaims>.*?<SA>([^<]*)</SA>", xml, re.S):
    mm, dd, yy, sa = m.groups()
    sa = sa.replace(",", "").strip()
    if sa and sa != "&#160;" and re.match(r"^\d+$", sa):
        claims_w["%s-%s-%s" % (yy, mm, dd)] = float(sa) / 1000.0
CLAIMS = complete_quarters(claims_w, 12)

dsr_rows = json.load(open(DATA / "fed-dsr.json"))
DSR = {}
for row in dsr_rows:
    y, qn = row[0].split(":")
    if row[2] not in ("ND", ""):
        DSR["%sQ%s" % (y, qn)] = float(row[2])

HPI = {q_of(d): v for d, v in verified["USSTHPI"].items()}
REV = complete_quarters(verified["REVOLSL"], 3)
SLOOS = {q_of(d): v for d, v in verified["DRTSCLCC"].items() if v is not None}

MACRO = {
    "Unemployment rate (level)": UR,
    "Unemployment rate (change over 4 quarters)": d4(UR),
    "Initial claims, 000s (change over 4 quarters, %)": yoy(CLAIMS),
    "Household debt service ratio (level)": DSR,
    "House prices, FHFA (change over 4 quarters, %)": yoy(HPI),
    "Revolving consumer credit (growth over 4 quarters, %)": yoy(REV),
    "Card lending standards, net % tightening (SLOOS)": SLOOS,
}


def corr(a, b):
    n = len(a)
    if n < 12:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((y - mb) ** 2 for y in b))
    if sa == 0 or sb == 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb)


def lagged(mac, loss, k, lo, hi):
    """Pairs (macro at t, loss at t+k) for t+k within [lo, hi]."""
    xs, ys = [], []
    for q, v in mac.items():
        t = qs(qi(q) + k)
        if t in loss and qi(lo) <= qi(t) <= qi(hi):
            xs.append(v)
            ys.append(loss[t])
    return xs, ys


WINDOWS = {"to 2019": ("1985Q1", "2019Q4"), "to 2007": ("1985Q1", "2007Q4"),
           "2008-2019": ("2008Q1", "2019Q4"), "2020-2026": ("2020Q1", "2026Q2")}

PAIRS = [
    ("Unemployment rate (level)", "Card NCO (TTM, Fed)"),
    ("Unemployment rate (change over 4 quarters)", "Card NCO (TTM, Fed)"),
    ("Unemployment rate (level)", "Card 30+ incl. nonaccrual (Fed)"),
    ("Unemployment rate (level)", "Other consumer incl. auto NCO (TTM, FDIC)"),
    ("Unemployment rate (level)", "Other consumer 30+ incl. nonaccrual (Fed)"),
    ("Initial claims, 000s (change over 4 quarters, %)", "Card NCO (TTM, Fed)"),
    ("Initial claims, 000s (change over 4 quarters, %)", "Other consumer incl. auto NCO (TTM, FDIC)"),
    ("Household debt service ratio (level)", "Card NCO (TTM, Fed)"),
    ("Revolving consumer credit (growth over 4 quarters, %)", "Card NCO (TTM, Fed)"),
    ("Card lending standards, net % tightening (SLOOS)", "Card NCO (TTM, Fed)"),
    ("House prices, FHFA (change over 4 quarters, %)", "Mortgage NCO (TTM, Fed)"),
    ("House prices, FHFA (change over 4 quarters, %)", "Mortgage 30+ incl. nonaccrual (Fed)"),
    ("House prices, FHFA (change over 4 quarters, %)", "Home equity NCO (TTM, FDIC)"),
    ("Unemployment rate (level)", "Mortgage NCO (TTM, Fed)"),
    ("Unemployment rate (level)", "Home equity NCO (TTM, FDIC)"),
]

leadlag = []
for mname, lname in PAIRS:
    row = {"macro": mname, "loss": lname, "windows": {}}
    for wname, (lo, hi) in WINDOWS.items():
        cs = []
        for k in range(0, 13):
            xs, ys = lagged(MACRO[mname], LOSS[lname], k, lo, hi)
            c = corr(xs, ys)
            cs.append(None if c is None else round(c, 3))
        valid = [(abs(c), k, c) for k, c in enumerate(cs) if c is not None]
        best = max(valid)[1:] if valid else (None, None)
        row["windows"][wname] = {"by_k": cs, "best_k": best[0], "best_r": best[1],
                                 "n_at_0": len(lagged(MACRO[mname], LOSS[lname], 0, lo, hi)[0])}
    leadlag.append(row)

# ---------------------------------------------------------------- turning points (NBER peaks)
NBER_PEAKS = {"1990": "1990Q3", "2001": "2001Q1", "2007": "2007Q4", "2020": "2019Q4"}


def peak_after(series, start, span=16):
    cand = [(series[qs(i)], qs(i)) for i in range(qi(start), qi(start) + span) if qs(i) in series]
    return max(cand)[1] if cand else None


def trough_before(series, start, back=8, fwd=4):
    cand = [(series[qs(i)], qs(i)) for i in range(qi(start) - back, qi(start) + fwd) if qs(i) in series]
    return min(cand)[1] if cand else None


turning = []
for ep, pk in NBER_PEAKS.items():
    r = {"episode": ep, "nber_peak": pk}
    r["ur_trough"] = trough_before(UR, pk)
    r["ur_peak"] = peak_after(UR, pk)
    for lname in ["Card NCO (TTM, Fed)", "Card 30+ incl. nonaccrual (Fed)", "Other consumer incl. auto NCO (TTM, FDIC)",
                  "Mortgage NCO (TTM, Fed)", "Home equity NCO (TTM, FDIC)"]:
        s = LOSS[lname]
        r[lname] = {"trough": trough_before(s, pk), "peak": peak_after(s, pk)}
        if r[lname]["peak"]:
            r[lname]["peak_value"] = s[r[lname]["peak"]]
            r[lname]["trough_value"] = s.get(r[lname]["trough"])
    r["ur_peak_value"] = UR.get(r["ur_peak"])
    r["ur_trough_value"] = UR.get(r["ur_trough"])
    turning.append(r)

# ---------------------------------------------------------------- level mapping and out-of-sample
def ols(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    a = my - b * mx
    res = [y - (a + b * x) for x, y in zip(xs, ys)]
    return a, b, math.sqrt(sum(e * e for e in res) / (n - 2))


fits = {}
for lname, mname in [("Card NCO (TTM, Fed)", "Unemployment rate (level)"),
                     ("Other consumer incl. auto NCO (TTM, FDIC)", "Unemployment rate (level)"),
                     ("Mortgage NCO (TTM, Fed)", "House prices, FHFA (change over 4 quarters, %)")]:
    out = {}
    for k in (0, 2, 4):
        xs, ys = lagged(MACRO[mname], LOSS[lname], k, "1985Q1", "2007Q4")
        a, b, se = ols(xs, ys)
        test = {}
        for wname in ("2008-2019", "2020-2026"):
            lo, hi = WINDOWS[wname]
            tx, ty = lagged(MACRO[mname], LOSS[lname], k, lo, hi)
            pred = [a + b * x for x in tx]
            err = [y - p for y, p in zip(ty, pred)]
            test[wname] = {"n": len(ty), "rmse": round(math.sqrt(sum(e * e for e in err) / len(err)), 3),
                           "mean_error": round(sum(err) / len(err), 3),
                           "max_actual": round(max(ty), 3), "max_predicted": round(max(pred), 3)}
        xs2, ys2 = lagged(MACRO[mname], LOSS[lname], k, "1985Q1", "2019Q4")
        a2, b2, se2 = ols(xs2, ys2)
        out["k%d" % k] = {"fit_to_2007": {"a": round(a, 3), "b": round(b, 3), "se": round(se, 3), "n": len(xs)},
                          "fit_to_2019": {"a": round(a2, 3), "b": round(b2, 3), "se": round(se2, 3), "n": len(xs2)},
                          "test": test}
    fits[lname + " on " + mname] = out

# unemployment bands against card losses four quarters later, 1985-2019 and 2020-2026
bands = []
edges = [(0, 4.5), (4.5, 5.5), (5.5, 6.5), (6.5, 7.5), (7.5, 8.5), (8.5, 20)]
for lo_e, hi_e in edges:
    for wname in ("to 2019", "2020-2026"):
        lo, hi = WINDOWS[wname]
        vals = [LOSS["Card NCO (TTM, Fed)"][qs(qi(q) + 4)] for q, v in UR.items()
                if lo_e <= v < hi_e and qs(qi(q) + 4) in LOSS["Card NCO (TTM, Fed)"] and qi(lo) <= qi(q) + 4 <= qi(hi)]
        bands.append({"ur_from": lo_e, "ur_to": hi_e, "window": wname, "n": len(vals),
                      "min": round(min(vals), 2) if vals else None, "median": round(st.median(vals), 2) if vals else None,
                      "max": round(max(vals), 2) if vals else None})

series_out = {"UR": UR, "CLAIMS": CLAIMS, "DSR": DSR, "HPI_yoy": yoy(HPI), "REV_yoy": yoy(REV), "SLOOS": SLOOS}
series_out.update({k: v for k, v in LOSS.items()})
json.dump({"leadlag": leadlag, "turning": turning, "fits": fits, "bands": bands,
           "series": {k: dict(sorted(v.items(), key=lambda kv: qi(kv[0]))) for k, v in series_out.items()}},
          open(OUT, "w"), indent=1)
print("wrote", OUT)
for row in leadlag:
    w = row["windows"]
    print("%-52s -> %-42s to2019 k=%s r=%s | to2007 k=%s r=%s | 08-19 k=%s r=%s | 20-26 k=%s r=%s" % (
        row["macro"][:52], row["loss"][:42], w["to 2019"]["best_k"], w["to 2019"]["best_r"], w["to 2007"]["best_k"],
        w["to 2007"]["best_r"], w["2008-2019"]["best_k"], w["2008-2019"]["best_r"], w["2020-2026"]["best_k"], w["2020-2026"]["best_r"]))
