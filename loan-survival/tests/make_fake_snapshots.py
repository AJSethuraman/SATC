import numpy as np, pandas as pd
rng = np.random.default_rng(11)
S = ["Current","30-59","60-89","90-119","120+","Charged off","Paid off"]
dpd_of = {"Current":0,"30-59":45,"60-89":75,"90-119":105,"120+":150}
P = np.array([  # true monthly transition matrix (rows = from)
 [0.970,0.012,0.000,0.000,0.000,0.003,0.015],
 [0.450,0.300,0.240,0.000,0.000,0.000,0.010],
 [0.200,0.100,0.200,0.500,0.000,0.000,0.000],
 [0.080,0.020,0.050,0.150,0.600,0.100,0.000],
 [0.030,0.000,0.000,0.020,0.550,0.400,0.000]])
months = pd.date_range("2021-01-31","2026-09-30",freq="ME")
snap, loans = [], []
for i in range(3000):
    start = int(rng.integers(0, len(months)-6)); s = 0
    rec = dict(loan_id=f"D{i:05d}", first_90_date=None, chargeoff_date=None, payoff_date=None, dpd_asof=None)
    for m in months[start:]:
        if s >= 5: break
        if S[s] in ("90-119","120+") and rec["first_90_date"] is None: rec["first_90_date"] = m.date()
        snap.append(dict(loan_id=rec["loan_id"], month_end=m.date(), dpd=dpd_of[S[s]], status="OPEN"))
        rec["dpd_asof"] = dpd_of[S[s]]
        s = rng.choice(7, p=P[s])
        if s == 5: rec["chargeoff_date"] = (m + pd.offsets.MonthEnd(1)).date()
        if s == 6: rec["payoff_date"] = (m + pd.offsets.MonthEnd(1)).date()
        if s >= 5 and (m + pd.offsets.MonthEnd(1)) <= months[-1]:
            snap.append(dict(loan_id=rec["loan_id"], month_end=(m + pd.offsets.MonthEnd(1)).date(), dpd=0,
                             status="CO" if s == 5 else "PIF"))
    loans.append(rec)
pd.DataFrame(snap).to_csv("dq_snapshots.csv", index=False)
pd.DataFrame(loans).to_csv("dq_loans.csv", index=False)
print(len(snap), "snapshot rows;", len(loans), "loans")
