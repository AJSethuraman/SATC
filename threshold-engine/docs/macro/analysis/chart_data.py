"""Write the two chart files the proposal's charts read, from analyse.py's output.

    (from threshold-engine/)
    python docs/macro/analysis/chart_data.py work/macro-analysis.json docs/macro/data
"""
import csv
import json
import sys

A = json.load(open(sys.argv[1]))
OUT = sys.argv[2]
sr = A["series"]
qi = lambda q: int(q[:4]) * 4 + int(q[-1]) - 1
qs = lambda i: "%dQ%d" % (i // 4, i % 4 + 1)
UR, card = sr["UR"], sr["Card NCO (TTM, Fed)"]
# NBER peak and trough quarters, from NBER's table of US business cycles
rec = set()
for pk, tr in (("1990Q3", "1991Q1"), ("2001Q1", "2001Q4"), ("2007Q4", "2009Q2"), ("2019Q4", "2020Q2")):
    rec.update(qs(i) for i in range(qi(pk), qi(tr) + 1))
with open(OUT + "/card_losses_and_unemployment_change.csv", "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["quarter", "card_nco_ttm_pct", "unemployment_change_4q_pts", "nber_recession"])
    for q in sorted(card, key=qi):
        if qi(q) < qi("1986Q1"):
            continue
        prev = qs(qi(q) - 4)
        w.writerow([q, card[q], round(UR[q] - UR[prev], 2) if q in UR and prev in UR else "", 1 if q in rec else 0])
with open(OUT + "/unemployment_bands_card_losses_1985_2019.csv", "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["unemployment_band", "quarters", "card_nco_4q_later_min", "card_nco_4q_later_median", "card_nco_4q_later_max"])
    for b in A["bands"]:
        if b["window"] != "to 2019":
            continue
        if b["ur_from"] == 0:
            lab = "under %.1f%%" % b["ur_to"]
        elif b["ur_to"] >= 20:
            lab = "%.1f%% and over" % b["ur_from"]
        else:
            lab = "%.1f to %.1f%%" % (b["ur_from"], b["ur_to"])
        w.writerow([lab, b["n"], b["min"], b["median"], b["max"]])
print("wrote", OUT)
