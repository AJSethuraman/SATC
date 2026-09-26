"""A synthetic book with a known answer, so the engine can be proved without
bank data. Nothing here is real and nothing here reaches the engine: the
cube file written beside the extract is the only thing that names columns.

The plants:
- loans with a score under 620 that came through the broker channel charge
  off at several times the book's rate. That pocket should be the worst cell
  by excess dollars in the score x channel grid, and nothing else close.
- revolving debt at origination (REV_DEBT) runs higher as the score falls,
  and within any score, a borrower carrying more than is usual for that score
  goes bad 1.8 times as often. So cut into fixed bands, revolving debt mostly
  re-sorts the score; split within each pocket at its own median, the high
  half should be worse than the low half, pocket after pocket.
- asset class 4 of 1-4 goes bad 1.4 times as often as the others.
- one pocket is priced for its risk: loans through the online channel with a
  score from 680 to 739 go bad twice as often as the rest of their band, and
  carry an interest rate 6 points higher. It loses more (GCO) and keeps more
  (RANR): "priced for it" on Losses vs revenue.

RANR is profit after losses, as the firm defines it (NEXT-GOAL 3.5; OC-29,
OC-35): contribution = interest on the balance over the months on book, at a
rate set by the score (risk-based pricing), plus fees, less the cost of funds
on the balance over the same months; RANR = contribution - GCO. So RANR per
booked dollar falls where losses climb, and the broker pocket under 620, priced
like its band, keeps less. Every loan has an origination date (ORIG_DATE) a
few years before the as-of date (AS_OF), which gives its months on book.

The dirt, on purpose, one of each kind the engine must count and not zero:
a bureau score of -9999 (a missing code) on every 50th loan, a blank score,
a charge-off amount written as text, a blank balance, and a flag that is
neither 0 nor 1. RANR is negative on most loans that charged off, and that is
real: `cube init` should ask about it, not decide.
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

COLUMNS = ["LOAN_NBR", "FICO", "CHANNEL", "ORIG_BAL", "BAD_FLAG", "GCO_AMT", "RANR_AMT", "ASSET_CLASS", "REV_DEBT",
           "ORIG_DATE"]
CHANNELS = ["Branch", "Broker", "Online"]
#: the date the extract was taken; every loan was made 3 to 60 months before it
AS_OF = date(2026, 6, 30)
#: the cost of funds a year, on the balance
COST_OF_FUNDS = 0.04
#: the pocket priced for its risk: (channel, lowest score, first score above), its extra interest a year, and
#: how many times as often it goes bad as the rest of its band
PRICED_FOR_IT = ("Online", 680, 740)
PREMIUM, PRICED_BAD = 0.02, 2.0


def interest_rate(fico: int) -> float:
    """Risk-based pricing: 6% a year at a score of 760 and up, 0.06 points more
    for every point below it (15.6% at 600)."""
    return 0.06 + max(0, 760 - fico) * 0.0006


def months_on_book(made: date, as_of: date = AS_OF) -> int:
    """Whole calendar months, one fewer when the as-of day is earlier than the
    origination day (as engine.age_filter counts them)."""
    return (as_of.year - made.year) * 12 + (as_of.month - made.month) - (1 if as_of.day < made.day else 0)

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
  - {name: gco_per_loan, mode: sumnum, value: GCO_AMT, per: each_loan, higher_is: worse}   # a straight average
  - {name: fico_median, mode: median, value: FICO}
min_age_months: 0          # every loan (the synthetic book has no dates)
benchmark:
  min_units: 30            # below this the outcome's share of loans gets the exact test
  min_events: 10           # a loss rate on fewer losses than this is not tested
  worse_at: 1.25
  better_at: 0.8
  confidence: 0.95
  power: 0.8
  compare_to: peers        # the rest of its band decides the flag
  many_tests: bh
  materiality: 1% of losses
"""


def make_rows(n: int = 20000, seed: int = 7, dated: bool = False) -> list[dict]:
    """`dated`: add the dated outcome and the income / sales columns (add_dated),
    after every other value is drawn, so every other plant is the same loan for
    loan with or without them."""
    rng = random.Random(seed)
    # the dates and the priced pocket's extra losses draw from their own stream, so every number the
    # book had before RANR became profit (the plants, walk 6's 29 bad of 50) is drawn exactly as it was
    more = random.Random(seed * 1_000_003 + 17)
    rows = []
    for i in range(n):
        fico = int(rng.gauss(700, 55))
        channel = rng.choice(CHANNELS)
        bal = round(rng.uniform(5000, 60000), 2)
        asset = rng.choice((1, 2, 3, 4))
        usual = max(1000.0, 12000.0 - (fico - 700) * 60)       # usual revolving debt for this score
        rev = round(max(0.0, rng.gauss(usual, 0.45 * usual)), 2)
        p = 0.03 if fico >= 680 else 0.06
        if fico < 620 and channel == "Broker":
            p = 0.30
        if rev > usual:
            p *= 1.8
        if asset == 4:
            p *= 1.4
        p = min(p, 0.95)
        priced = channel == PRICED_FOR_IT[0] and PRICED_FOR_IT[1] <= fico < PRICED_FOR_IT[2]
        u = rng.random()
        bad = 1 if u < (min(p * PRICED_BAD, 0.95) if priced else p) else 0
        # a loan the priced pocket's extra risk turned bad takes its loss from the second stream
        gco = round(bal * (rng if u < p else more).uniform(0.3, 0.8), 2) if bad else 0.0
        fees = round(200 + rng.uniform(-200, 400), 2)      # $0 to $600 (the draw the flat RANR used)
        made = AS_OF - timedelta(days=more.randint(92, 1826))
        years = months_on_book(made) / 12
        apr = interest_rate(fico) + (PREMIUM if priced else 0.0)
        contribution = bal * apr * years + fees - bal * COST_OF_FUNDS * years
        ranr = round(contribution - gco, 2)                # profit after losses, signed (D47)
        rows.append({"LOAN_NBR": f"L{i:07d}", "FICO": fico, "CHANNEL": channel, "ORIG_BAL": bal,
                     "BAD_FLAG": bad, "GCO_AMT": gco, "RANR_AMT": ranr, "ASSET_CLASS": asset, "REV_DEBT": rev,
                     "ORIG_DATE": made.isoformat()})
    # a bureau missing-score code on 2% of loans, as a real extract carries it
    for i in range(0, n, 50):
        rows[i]["FICO"] = -9999
    # the dirt, one of each
    rows[0]["FICO"] = -9999
    rows[1]["FICO"] = ""
    rows[2]["GCO_AMT"] = "#N/A"             # as Excel writes an error
    rows[3]["ORIG_BAL"] = ""
    rows[4]["BAD_FLAG"] = 2
    return add_dated(rows, seed) if dated else rows


# --------------------------------------------------------------------------
# Fixes 3.9 and 3.14 (26 Sep 2026): a dated outcome, and a ratio with a known effect.
#
# Kept apart from make_rows on purpose: it draws from its own random stream and
# only ADDS columns, so the flag, GCO, RANR and every plant above are the same
# loan for loan. That is also why the ratio's effect is planted by drawing the
# ratio given the outcome rather than the outcome given the ratio: a bad loan's
# ratio comes from the good loans' spread tilted by the planted odds, so within
# any score, channel or asset class the odds of bad are exactly x3 above 2.0 and
# x2 below 0.1 against the middle, as docs/scout-vs-measure.py plants them.

DATED_COLUMNS = ["ORIG_DATE", "BAD_DATE", "INCOME", "SALES"]
AS_OF = "2026-06-30"                     # the synthetic extract was "taken" on this day
FIRST_ORIG = "2021-01-01"                # loans made from here to a month before AS_OF
RATIO_ODDS = ((2.0, 3.0), (0.1, 2.0))    # above 2.0: x3; below 0.1: x2; nothing between (scout-vs-measure.py)
MONTHS_TO_BAD = (12.0, 0.7)              # median 12 months, log-spread 0.7: about 72% land by month 18


def _odds(ratio: float) -> float:
    return RATIO_ODDS[0][1] if ratio > RATIO_ODDS[0][0] else RATIO_ODDS[1][1] if ratio < RATIO_ODDS[1][0] else 1.0


def _made_on(r: dict, rng: random.Random, first, last):
    """The row's own origination date if it has one (a later synthetic book may
    carry ORIG_DATE), else one drawn evenly between `first` and `last`."""
    from datetime import date, datetime, timedelta
    v = r.get("ORIG_DATE")
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str) and v.strip():
        for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
            try:
                return datetime.strptime(v.strip(), fmt).date()
            except ValueError:
                pass
    return first + timedelta(days=rng.randrange((last - first).days + 1))


def add_dated(rows: list[dict], seed: int = 7) -> list[dict]:
    """ORIG_DATE (unless the row has one), BAD_DATE on bad loans and blank on the
    rest, and INCOME and SALES, both per year, whose ratio carries the planted
    effect. A bad loan goes bad a lognormal number of months after it was made
    (MONTHS_TO_BAD), never after AS_OF. SALES is 0 on every 997th loan and blank
    on every 1,009th, so a new column dividing by it has blanks to count."""
    import math
    from datetime import date, timedelta
    rng = random.Random(f"dated-{seed}")
    as_of, first = date.fromisoformat(AS_OF), date.fromisoformat(FIRST_ORIG)
    top = max(_odds(x) for x in (0.05, 1.0, 3.0))
    for i, r in enumerate(rows):
        made = _made_on(r, rng, first, as_of - timedelta(days=31))
        r["ORIG_DATE"] = made.isoformat()
        bad = r.get("BAD_FLAG") == 1
        r["BAD_DATE"] = ""
        if bad:
            days_on_book = (as_of - made).days
            for _ in range(1000):
                days = int(math.exp(rng.gauss(math.log(MONTHS_TO_BAD[0]), MONTHS_TO_BAD[1])) * 30.44)
                if days <= days_on_book:
                    break
            else:
                days = rng.randrange(days_on_book + 1)
            r["BAD_DATE"] = (made + timedelta(days=days)).isoformat()
        while True:                      # good: the plain spread; bad: tilted by the planted odds
            ratio = math.exp(rng.gauss(-0.7, 0.8))
            if not bad or rng.random() < _odds(ratio) / top:
                break
        sales = round(math.exp(rng.gauss(math.log(250000), 0.5)))
        r["SALES"] = sales
        r["INCOME"] = round(ratio * sales)
        if i % 997 == 500:
            r["SALES"] = 0
        elif i % 1009 == 600:
            r["SALES"] = ""
    return rows


def write_extract(out: str | Path, n: int = 20000, seed: int = 7, dated: bool = False) -> Path:
    """The extract alone, for the demo: the analyst's route starts from
    `cube init` on it, so no call is made for them (walkthrough defect 14).
    `dated` adds the dated outcome and INCOME and SALES (add_dated)."""
    d = Path(out)
    d.mkdir(parents=True, exist_ok=True)
    data = d / "loans.csv"
    with data.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS + ([c for c in DATED_COLUMNS if c not in COLUMNS] if dated else []))
        w.writeheader()
        w.writerows(make_rows(n, seed, dated))
    return data


def write(out: str | Path, n: int = 20000, seed: int = 7) -> tuple[Path, Path]:
    """The extract and an answered cube file: for the tests, which need every
    call made. The demo uses write_extract."""
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
