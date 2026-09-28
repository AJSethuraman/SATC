"""The suggested revenue line is the smallest gap a typical pocket catches 80% of the time. What luck alone
moves a pocket's revenue is the 95% range with no real gap: the same sum with the catch rate set to 50%.

    CUBE_SRC=<frozen src> python3.12 luckline.py "<book> - what ran.yaml" EXTRACT.csv
"""
import os, sys, statistics, yaml
sys.path.insert(0, os.environ["CUBE_SRC"])
from origination_cube import config as cf, engine, book
from origination_cube.ingest import read_table
raw = yaml.safe_load(open(sys.argv[1]))
for power in (0.8, 0.5):
    raw["benchmark"]["power"] = power
    res = engine.run(cf.parse(raw), read_table(sys.argv[2]))
    print(f"power {power}: suggested line", round(book.revenue_lines(res)[1], 4))
# pockets whose own RANR test vs the rest of the band says 'not luck' before the many-tests allowance
raw["benchmark"]["power"] = 0.8
res = engine.run(cf.parse(raw), read_table(sys.argv[2]))
lo, hi, _ = book.revenue_lines(res)
n = k = 0
for g in res.grids:
    for _, c in g.inner():
        s = c.rates["ranr_rate"]
        if s.units < 30 or s.vs_band is None: continue
        n += 1
        if s.p_band is not None and s.p_band < 0.05 and lo < s.vs_band < hi:
            k += 1; print("  p<0.05 but 'earning the same':", g.band, g.dimension, _, round(s.vs_band, 3), round(s.p_band, 4), s.reading_band)
print(n, "pockets;", k, "read 'the same' with p under 5% before the allowance")
