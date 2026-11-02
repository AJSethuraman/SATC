#!/usr/bin/env python3
"""
validate.py - Checks loan_survival.py against independent references. Run after ANY change to the math.

    python tests/validate.py

Needs scipy (survival curves, log-rank). statsmodels is optional (Cox check is skipped without it).
Exits non-zero on any failure.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import loan_survival as ls  # noqa: E402

from scipy import stats  # noqa: E402

FAIL = []


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")
    if not ok:
        FAIL.append(name)


# 1. hand-worked toy example (6 loans): 83.3%, 62.5%, 41.7% survival at months 4, 10, 14
t = np.array([4, 10, 6, 18, 14, 24]); e = np.array([1, 1, 0, 0, 1, 0])
km = ls.kaplan_meier(t, e).set_index("month_on_book")["cum_bad_rate"]
got = [1 - km[4], 1 - km[10], 1 - km[14]]
check("toy Kaplan-Meier", np.allclose(got, [5 / 6, 0.625, 0.625 * 2 / 3]), str(np.round(got, 4)))

# 2. chi-square p-value fallback vs scipy
pairs = [(3.84, 1), (10.0, 3), (45.2, 3), (0.5, 2), (120.0, 5)]
diff = max(abs(ls._gammaincc(df / 2, x / 2) - stats.chi2.sf(x, df)) for x, df in pairs)
check("p-value fallback", diff < 1e-10, f"max diff {diff:.2e}")

# 3. full run on fake book
book = ROOT / "sample" / "fake_book.csv"
settings = ROOT / "sample" / "settings_example.ini"
with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "out.xlsx"
    r = subprocess.run([sys.executable, str(ROOT / "loan_survival.py"), str(book), "--settings", str(settings),
                        "--out", str(out)], capture_output=True, text=True)
    check("end-to-end run", r.returncode == 0, r.stderr[-500:] if r.returncode else "")
    if r.returncode:
        sys.exit(1)
    tests = pd.read_excel(out, "Tests")
    models = pd.read_excel(out, "Models")

st = ls.Settings(settings.read_text())
raw = pd.read_csv(book)
df, _ = ls.prepare(raw, st)
L = ls.add_time_event(df, st, pd.Timestamp("2026-09-30"), ["first_90_date", "chargeoff_date"])

# 4. KM vs scipy, every vintage
worst = 0.0
for y, v in L.groupby(L.orig_date.dt.year):
    T, E = v._time.to_numpy(), v._event.to_numpy()
    k = ls.kaplan_meier(T, E)
    ref = stats.ecdf(stats.CensoredData(uncensored=T[E == 1], right=T[E == 0])).sf
    worst = max(worst, np.abs((1 - k.cum_bad_rate.to_numpy()) - ref.evaluate(k.month_on_book.to_numpy())).max())
check("Kaplan-Meier vs scipy", worst < 1e-12, f"max diff {worst:.1e}")

# 5. log-rank vs scipy (2-group comparisons)
S = L[L.orig_date <= "2022-12-31"]
for c in (640, 680, 700):
    g = np.where(S.fico < c, "lo", "hi")
    stat, _, p = ls.logrank(S._time.to_numpy(), S._event.to_numpy(), g)
    cd = lambda m: stats.CensoredData(uncensored=S._time[m & (S._event == 1)].to_numpy(),
                                      right=S._time[m & (S._event == 0)].to_numpy())
    ref = stats.logrank(cd(g == "lo"), cd(g == "hi"))
    check(f"log-rank vs scipy (fico {c})", abs(stat - ref.statistic ** 2) < 1e-6 and abs(p - ref.pvalue) < 1e-9,
          f"chi2 {stat:.4f} vs {ref.statistic ** 2:.4f}")

# 6. Cox vs statsmodels (Efron ties)
try:
    from statsmodels.duration.hazard_regression import PHReg
    X = np.c_[S.fico / -50, (S.income_gt_sales == "Y").astype(float), S.new_business]
    ref = PHReg(S._time.to_numpy() + 0.5, X, status=S._event.to_numpy(), ties="efron").fit()
    b, se, p = ls.cox_fit(S._time.to_numpy(), S._event.to_numpy(), X)
    check("Cox vs statsmodels", np.allclose(b, ref.params, atol=1e-6) and np.allclose(se, ref.bse, atol=1e-6),
          f"HR {np.round(np.exp(b), 4)}")
    tool = models.set_index("variable")["HR_together"].to_numpy()
    check("Models sheet matches fit", np.allclose(tool, np.exp(b), atol=1e-9))
except ImportError:
    print("[SKIP] Cox vs statsmodels (statsmodels not installed)")

# 7. economics vs plain pandas
raw["yr"] = pd.to_datetime(raw.orig_date).dt.year.astype(str)
ref = raw.groupby("yr").apply(lambda d: d.net_revenue.sum() / d.amount.sum() * 1000, include_groups=False)
tool = tests[tests.comparison == "origination year"].assign(group=lambda d: d.group.astype(str)).set_index("group")["net_revenue_per_1000"]
check("net revenue per $1,000", np.allclose(tool.sort_index().to_numpy(), ref.sort_index().to_numpy()))

# 8. bad-event check vs plain pandas
f = raw.copy()
for c in ("first_90_date", "chargeoff_date"):
    f[c] = pd.to_datetime(f[c])
pop = f[f.first_90_date <= pd.Timestamp("2025-09-30")]
share = (pop.chargeoff_date <= pop.first_90_date + pd.DateOffset(months=12)).sum() / len(pop)
m, _, _, _ = ls.bad_event_check(df, st, pd.Timestamp("2026-09-30"))
tool_share = float(m.set_index("measure").loc["share charged off within 12 months", "value"])
check("bad-event share", abs(share - tool_share) < 1e-12, f"{tool_share:.4f}")

print("\nALL PASSED" if not FAIL else f"\nFAILED: {FAIL}")
sys.exit(1 if FAIL else 0)
