"""Does the split find revolving debt where there is no revolving-debt effect?

    WALK=<scratch> CUBE_SRC=<frozen src> python3.12 noplant.py

Makes the walk's 8,000-loan synthetic book twice from the same seed: once as
synth.py plants it (above-usual revolving debt for the score goes bad 1.8x as
often) and once with that plant switched off (the 1.8 set to 1.0; the score,
channel and asset-class plants unchanged). Runs the split the walk ran on both
(REV_DEBT at each pocket's own median; FICO and ORIG_BAL in five equal bands,
by CHANNEL and ASSET_CLASS) and prints the pooled answer per grid.

Not a screen: this checks what the Split tab's sentence says against a book
where the true answer is known to be "no effect".
"""
import csv
import inspect
import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ["CUBE_SRC"])
from origination_cube import config as cf, engine, synth  # noqa: E402
from origination_cube.ingest import read_table  # noqa: E402

W = Path(os.environ["WALK"])
src = inspect.getsource(synth.make_rows).replace("p *= 1.8", "p *= 1.0")
ns = {"CHANNELS": synth.CHANNELS}
exec("import random\n" + src, ns)
books = {}
for label, make in (("no plant", ns["make_rows"]), ("planted", synth.make_rows)):
    p = W / "noplant" / f"{label.replace(' ', '-')}.csv"
    p.parent.mkdir(exist_ok=True)
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=synth.COLUMNS)
        w.writeheader()
        w.writerows(make(8000, 7))
    books[label] = p

raw = {"name": "noplant", "schema_version": 1, "columns_confirmed": True,
       "columns": {"LOAN_NBR": "key", "FICO": "fico", "CHANNEL": "category", "ORIG_BAL": "booked",
                   "BAD_FLAG": "outcome", "GCO_AMT": "gco", "RANR_AMT": "ranr", "ASSET_CLASS": "category",
                   "REV_DEBT": "amount"},
       "bands": [{"name": "fico", "field": "FICO", "count": 5, "cut": "equal_loans"},
                 {"name": "orig_bal", "field": "ORIG_BAL", "count": 5, "cut": "equal_loans"}],
       "dimensions": [{"name": "channel", "field": "CHANNEL"}, {"name": "asset_class", "field": "ASSET_CLASS"}],
       "measures": [{"name": "loans", "mode": "count"}], "min_age_months": 0,
       "benchmark": {"min_units": 30, "min_events": 10, "worse_at": 1.25, "better_at": 0.8, "confidence": 0.95,
                     "power": 0.8, "compare_to": "peers", "many_tests": "bh", "materiality": "1% of losses"},
       "questions": [{"column": "FICO", "pattern": "repeated_value", "value": -9999.0, "answer": "missing"}],
       "split": {"field": "REV_DEBT", "how": "own_median"}}
for label, path in books.items():
    res = engine.run(cf.parse(raw), read_table(path))
    for g in res.grids:
        p = g.split_pooled["outcome_loans"]
        print(f"{label:8} {g.band:8} x {g.dimension:11} odds {p['odds']:.2f}  bad-rate ratio {p['ratio']:.2f}  "
              f"high half worse in {p['high_worse']} of {p['pockets']}  p {p['odds_p']:.2g}")
