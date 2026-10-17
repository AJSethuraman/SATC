import numpy as np, pandas as pd
r = np.random.default_rng(2026)
as_of = pd.Timestamp("2026-09-30")
spec = {2021: 1500, 2022: 1500, 2023: 1600, 2024: 1100, 2025: 900}
vint_mult = {2021: 1.0, 2022: 1.0, 2023: 1.6, 2024: 0.8, 2025: 0.7}   # 2023 bad, better after
rows, i = [], 0
for yr, n in spec.items():
    for _ in range(n):
        i += 1
        orig = pd.Timestamp(yr, 1, 1) + pd.Timedelta(days=int(r.integers(0, 365)))
        fico = int(np.clip(round(r.normal(705, 50)), 560, 830)); low = fico < 680
        inc = int(r.random() < (0.30 if low else 0.12)); nb = int(r.random() < (0.45 if low else 0.20))
        amt = float(round(r.uniform(10, 150)) * 1000)
        mult = vint_mult[yr] * 2.0 ** ((700 - fico) / 50) * (1.4 if inc else 1.0)
        f90 = co = pif = None; dpd = 0; months_active = 0
        for mob in range(1, 200):
            d = orig + pd.DateOffset(months=mob)
            if d > as_of: break
            months_active = mob
            h = mult * 0.0030 * (1 + 1.2 * np.exp(-((mob - 16) / 9) ** 2))
            u = r.random()
            if u < h * 0.15:                       # fast charge-off, never 90+ (fraud/bankruptcy)
                co = d; break
            if u < h:                              # goes 90+
                f90 = d
                if r.random() < 0.75:              # most roll to charge-off 2-6 months later
                    c = d + pd.DateOffset(months=int(r.integers(2, 7)))
                    if c <= as_of: co = c
                    else: dpd = 120
                else:
                    dpd = 0                        # cured
                break
            if u < h + 0.012: pif = d; break
        rate = 0.08 + (700 - fico) / 2500
        rev = amt * rate / 12 * months_active - amt * 0.04 / 12 * months_active - (amt * 0.6 if co else 0)
        rows.append(dict(loan_id=f"B{i:05d}", orig_date=orig.date(), first_90_date=f90.date() if f90 else None,
                         chargeoff_date=co.date() if co else None, payoff_date=pif.date() if pif else None,
                         dpd_asof=dpd, fico=fico, income_gt_sales="Y" if inc else "N", new_business=nb,
                         amount=amt, net_revenue=round(rev, 2)))
df = pd.DataFrame(rows); df.to_csv(__import__("sys").argv[1] if len(__import__("sys").argv) > 1 else "fake_book.csv", index=False)
print(len(df), "loans |", df.chargeoff_date.notna().sum(), "charge-offs |", df.first_90_date.notna().sum(), "hit 90+")
