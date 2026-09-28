"""What the suggested Control numbers are made of, worked out again from the run's own record.

    CUBE_SRC=<frozen src> python3.12 luckline.py "<book> - what ran.yaml" EXTRACT.csv [what ran with a split ...]

For the seventh walk (commit a5a8aa2), where "worse at", "better at" and the revenue line can all be
suggestions. Prints, per measure, the gap luck alone can make in a pocket of typical size (the
median over pockets at or above the fewest-loans floor, at the Control confidence, catch rate left
out), the spread of that gap from the smallest tested pocket to the largest, and the book's rate.
The tool uses the outcome's figure for "worse at" / "better at" on every loss measure, and the
RANR figure for the revenue line.
"""
import math, os, statistics, sys, yaml
sys.path.insert(0, os.environ["CUBE_SRC"])
from origination_cube import config as cf, engine, book, stats
from origination_cube.ingest import read_table

raw = yaml.safe_load(open(sys.argv[1]))
table = read_table(sys.argv[2])
res = engine.run(cf.parse(raw), table)
b = res.config.benchmark
print(f"floor {b.min_units} loans, confidence {b.confidence}, worse_at {b.worse_at}, better_at {b.better_at}, "
      f"revenue_line {b.revenue_line}")
rate = res.total.rates["outcome_loans"].rate
print(f"book bad rate {rate:.4%}; 5 / rate = {5 / rate:.1f} -> {math.ceil(5 / rate)} loans (OC-30: 5 expected losses)")
for m in ("outcome_loans", "outcome_booked", "gco_rate", "ranr_rate"):
    ln = res.loans_needed.get(m)
    gaps, sizes = [], []
    for g in res.grids:
        for _, c in g.inner():
            s = c.rates[m]
            if s.units >= b.min_units:
                x = stats.smallest_gap(s.units, ln.rate, ln.s_d, ln.x_bar, b.confidence, 0.5)
                if x:
                    gaps.append(x); sizes.append(s.units)
    if gaps:
        print(f"  {m:15} luck gap median {statistics.median(gaps):.3f} over {len(gaps)} pockets "
              f"(sizes {min(sizes)} to {max(sizes)}, median {statistics.median(sizes)}); "
              f"smallest pocket's {max(gaps):.2f}x, largest pocket's {min(gaps):.2f}x")
print("revenue lines as the tab states them:", book.revenue_lines(res)[:2])
