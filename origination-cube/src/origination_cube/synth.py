"""A synthetic book with a known answer, so the engine can be proved without
bank data. Nothing here is real and nothing here reaches the engine: the
cube file written beside the extract is the only thing that names columns.

The plant: loans with a score under 620 that came through the broker channel
charge off at several times the book's rate. That one pocket should be the
worst cell by excess dollars in the score x channel grid, and nothing else
should come close.

The dirt, on purpose, one of each kind the engine must count and not zero:
a bureau score of -9999 (missing by rule) on every 50th loan, a blank score,
a charge-off amount written as text, a blank balance, and a flag that is
neither 0 nor 1. RANR is negative on about a third of loans, and that is real:
`cube init` should ask about it, not decide.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

COLUMNS = ["LOAN_NBR", "FICO", "CHANNEL", "ORIG_BAL", "BAD_FLAG", "GCO_AMT", "RANR_AMT"]
CHANNELS = ["Branch", "Broker", "Online"]

CONFIG = """\
# A cube over the synthetic book. Column names here are the synthetic
# extract's; for a real extract, `cube inspect` lists the real ones.
name: synthetic_origination_cube
schema_version: 1
key: LOAN_NBR              # loan number: needed to map results back to loans
booked: ORIG_BAL           # weights the reporting-level rates
outcome: BAD_FLAG          # any yes/no column; or {field: COLUMN, is: VALUE}
gco: GCO_AMT
ranr: RANR_AMT
missing:
  FICO: {below: -1000}        # the bureau writes -9999 when it has no score
bands:
  - {name: fico, field: FICO, edges: [620, 680, 740]}      # or: count: 5, cut: equal_loans
dimensions:
  - {name: channel, field: CHANNEL}
measures:                  # extras; the core rates are built from the lines above
  - {name: loans, mode: count}
  - {name: gco_per_loan, mode: sumnum, value: GCO_AMT, per: each_loan}   # a straight average
  - {name: fico_median, mode: median, value: FICO}
benchmark:
  min_units: 30            # below this a pocket is shown but not tested
  worse_at: 1.25
  better_at: 0.8
  confidence: 0.95
  power: 0.8
"""


def make_rows(n: int = 20000, seed: int = 7) -> list[dict]:
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        fico = int(rng.gauss(700, 55))
        channel = rng.choice(CHANNELS)
        bal = round(rng.uniform(5000, 60000), 2)
        p = 0.03 if fico >= 680 else 0.06
        if fico < 620 and channel == "Broker":
            p = 0.30
        bad = 1 if rng.random() < p else 0
        gco = round(bal * rng.uniform(0.3, 0.8), 2) if bad else 0.0
        ranr = round(rng.uniform(-200, 400), 2)          # signed (D47)
        rows.append({"LOAN_NBR": f"L{i:07d}", "FICO": fico, "CHANNEL": channel, "ORIG_BAL": bal,
                     "BAD_FLAG": bad, "GCO_AMT": gco, "RANR_AMT": ranr})
    # a bureau missing-score code on 2% of loans, as a real extract carries it
    for i in range(0, n, 50):
        rows[i]["FICO"] = -9999
    # the dirt, one of each
    rows[0]["FICO"] = -9999
    rows[1]["FICO"] = ""
    rows[2]["GCO_AMT"] = "#N/A"             # as Excel writes an error
    rows[3]["ORIG_BAL"] = ""
    rows[4]["BAD_FLAG"] = 2
    return rows


def write(out: str | Path, n: int = 20000, seed: int = 7) -> tuple[Path, Path]:
    d = Path(out)
    d.mkdir(parents=True, exist_ok=True)
    data = d / "loans.csv"
    with data.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(make_rows(n, seed))
    cfg = d / "cube.yaml"
    cfg.write_text(CONFIG, encoding="utf-8")
    return cfg, data
