"""A made-up loan book with a known answer, and the question file that asks it.

The fixtures are the test strategy: you know the right answer in advance and
assert the pack recovers it. Column names are generic on purpose (the tool
must know no domain), and every draw comes from one seeded generator so the
same seed gives the same book byte for byte.

What is planted (the `effect` mode): the odds of the event rise with the rule
value on a log scale — each doubling of the ratio multiplies the odds by
`effect` — independently of the loan's size, so a stratified read should
*survive*. The generator writes `planted.json` beside the book with the exact
marginal odds ratio of flagged against unflagged loans, computed from the
true probabilities it drew with, so a test compares against what was
actually planted rather than a round number.

`null` plants nothing. `confounded` (used from slice 4) makes the outcome
depend on `field_b` alone: small `field_b` fires the flag mechanically, so
the flag looks predictive until stratified by size, and then it should
*collapse*.
"""

from __future__ import annotations

import csv
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

from .population import add_months

ASOF = date(2026, 6, 30)
FIRST_ORIGINATION = date(2019, 1, 1)


def _lognormal(rng: random.Random, median: float, sigma: float) -> float:
    return median * math.exp(rng.gauss(0.0, sigma))


def generate(out_dir: str | Path, *, seed: int = 20260918, loans: int = 40000,
             effect: float = 2.0, mode: str = "effect", window_months: int = 24,
             base_rate: float = 0.012) -> dict:
    """Write loans.csv, config.yaml and planted.json into out_dir. Returns the
    planted facts."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    span_days = (ASOF - FIRST_ORIGINATION).days
    rows = []
    truth = []   # (fires, bucket_value, p_event) for planted.json
    categories_1 = ["north", "south", "east", "west", "central"]
    for i in range(loans):
        orig = FIRST_ORIGINATION + timedelta(days=rng.randrange(span_days + 1))
        b = _lognormal(rng, 400_000.0, 1.0)               # a size-like figure
        ratio = _lognormal(rng, 0.5, 0.9)                 # a independent of b: no size confound
        if mode == "confounded":
            a = _lognormal(rng, 90_000.0, 0.5)            # a independent of b => small b fires the flag
            ratio = a / b
        else:
            a = ratio * b
        amount = _lognormal(rng, 120_000.0, 0.8)
        cat1 = categories_1[rng.randrange(len(categories_1))]
        cat2 = "kind_" + str(rng.randrange(1, 7))
        code = str(rng.randrange(11, 93)) + str(rng.randrange(1000, 9999))
        # blanks: a slice of field_a and field_b, plus one quarter where field_b was rarely captured
        a_blank = rng.random() < 0.05
        b_blank = rng.random() < 0.08 or (orig.year == 2019 and orig.month <= 3 and rng.random() < 0.40)
        # the planted outcome
        if mode == "effect":
            mult = effect ** math.log2(max(ratio, 1e-9))
        elif mode == "confounded":
            mult = (400_000.0 / max(b, 1.0)) ** 0.9
        else:
            mult = 1.0
        odds = base_rate / (1.0 - base_rate) * mult
        p = odds / (1.0 + odds)
        fires_true = ratio > 1.0
        truth.append((fires_true, p))
        event_in_window = rng.random() < p
        outcome_date = ""
        if event_in_window:
            months = rng.randrange(1, window_months + 1)
            ed = add_months(orig, months)
            if ed <= ASOF:
                outcome_date = ed.isoformat()
            else:
                outcome_date = ""      # would have happened after as-of: not observed yet
        elif rng.random() < 0.004:
            ed = add_months(orig, window_months + rng.randrange(1, 13))
            outcome_date = ed.isoformat() if ed <= ASOF else ""
        # a bank-windowed flag (the same in-window event, already cut to the window by "the bank")
        flag_1 = 1 if (outcome_date and add_months(orig, window_months) >= date.fromisoformat(outcome_date)) else 0
        # a snapshot measure at as-of: measure_a / measure_b rises with the same planted odds
        measure_b = amount
        util = min(1.0, max(0.0, rng.betavariate(2.0, 2.0) * (1.0 + 0.5 * (mult - 1.0))))
        measure_a = measure_b * util
        rows.append({
            "loan_id": f"L{i + 1:06d}",
            "origination_date": orig.isoformat(),
            "field_a": "" if a_blank else f"{a:.2f}",
            "field_b": "" if b_blank else f"{b:.2f}",
            "amount": f"{amount:.2f}",
            "category_1": cat1,
            "category_2": cat2,
            "code_1": code,
            "outcome_date": outcome_date,
            "flag_1": flag_1,
            "measure_a": f"{measure_a:.2f}",
            "measure_b": f"{measure_b:.2f}",
        })
    rows.sort(key=lambda r: r["loan_id"])
    with (out / "loans.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # the exact planted marginal contrast, from the probabilities drawn with
    def mean_p(flag: bool) -> float:
        ps = [p for f, p in truth if f == flag]
        return sum(ps) / len(ps) if ps else 0.0
    p1, p0 = mean_p(True), mean_p(False)
    planted_or = (p1 / (1 - p1)) / (p0 / (1 - p0)) if p0 > 0 and p1 > 0 else None
    planted = {
        "seed": seed, "loans": loans, "mode": mode, "effect_per_doubling": effect if mode == "effect" else None,
        "base_rate": base_rate, "asof": ASOF.isoformat(), "window_months": window_months,
        "true_marginal_flag_odds_ratio": planted_or,
        "note": "true_marginal_flag_odds_ratio is the odds ratio of flagged (ratio > 1) against unflagged loans "
                "computed from the probabilities the generator drew with, before sampling noise and before "
                "seasoning; it is what the pack should recover within its interval.",
    }
    (out / "planted.json").write_text(json.dumps(planted, indent=2) + "\n", encoding="utf-8")

    config = f"""# A made-up book with a known answer. Column names are generic on purpose.
name: synthetic_{mode}
schema_version: 1
rule_type: contradiction
population:
  loan_id: loan_id
  origination_date: origination_date
  date_format: "%Y-%m-%d"
fields:
  loan_id:          {{known: at_origination}}
  origination_date: {{known: at_origination}}
  field_a:          {{known: at_origination}}
  field_b:          {{known: at_origination}}
  amount:           {{known: at_origination}}
  category_1:       {{known: at_origination}}
  category_2:       {{known: at_origination}}
  code_1:           {{known: at_origination, derive: {{kind: prefix, length: 2}}}}
  outcome_date:     {{known: later}}
  flag_1:           {{known: later}}
  measure_a:        {{known: later}}
  measure_b:        {{known: later}}
rule:
  kind: ratio
  field_a: field_a
  field_b: field_b
  fires_when: {{op: ">", value: 1.0}}
  buckets: [0.5, 1.0, 2.0, 5.0]
outcome:
  label: event
  date_field: outcome_date
window_months: {window_months}
confounders:
  - {{name: size_band, field: field_b, edges: [100000, 200000, 400000, 800000, 1600000]}}
  - {{name: amount_band, field: amount, edges: [60000, 250000]}}
  - {{name: category_2, field: category_2}}
controls:
  - {{name: origination_year, derived: origination_year}}
  - {{name: amount, field: amount, as: log}}
  - {{name: category_1, field: category_1}}
decompose_by: [category_1, amount_band, origination_year]
existing_control: none
drives:
  field_a: "decision one"
  field_b: "decision two"
model: {{tree_depth: 3, min_leaf_events: 10, min_leaf_loans: 100}}
intervals: {{confidence: 0.95, method: wilson}}
survives_threshold: 0.5
"""
    (out / "config.yaml").write_text(config, encoding="utf-8")
    return planted
