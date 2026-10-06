# threshold-engine

Give it a dated series: a charge-off rate, a delinquency rate, a weighted
average probability of default, any continuous signal. There are two
commands.

**`profile` reports facts and decides nothing.** You get the distribution,
every spell worse than the median (start, peak, end, length, rise and fall
times, peak � median), how often each upper percentile was reached, the
percentiles with the largest spell removed, and where the latest value ranks.
It takes no judgement settings. What counts as stress is left to the expert
reading it.

**`cutoffs` applies the bank's stated judgements.** It returns:

- the series' **normal level**
- each **stress episode**: when it started, its peak, when it ended, and
  whether it is complete
- whether the worst episode is an **outlier**, and whether enough other
  episodes remain to set it aside
- **candidate cutoffs** for a rating scale, plus the score the latest value
  takes on them

It exists to set the thresholds a separate scoring file uses. It does not
score a portfolio. The design is in the *Consumer Risk Thresholds: Design
Proposal*, section 3a.

## Run it

```
cd threshold-engine
python -m pip install -e .
```

```
threshold-engine profile tests/data/mortgage_nco_ttm.csv --name "Mortgage net charge-offs, TTM" --unit % --direction higher_is_worse --frequency quarterly --smoothing 1
```

```
threshold-engine cutoffs tests/data/cards_nco_ttm.csv --name "Card net charge-offs, TTM" --unit % --direction higher_is_worse --frequency quarterly --smoothing 1 --floor-at-zero yes --scale-points 5 --top-fraction 0.75 --episode-height 0.25 --materiality none --outlier-ratio 2 --min-other-episodes 1
```

The CSV needs a `date,value` header. Lines starting with `#` are notes.
`--json` prints everything, provenance included.

## The rules

**Every setting is required.** None of them has a default, either in
`Settings` or on the command line. `--materiality none` counts as a stated
setting and is recorded as one.

**It refuses rather than guesses.** It refuses a missing quarter rather than
fill it in, and a series with no complete stress episode rather than scale it.
Each refusal carries a stable code and a reason.

| Stage | Rule, as a reviewer would redo it by hand |
|---|---|
| Check | One observation per period, no gaps, no duplicates |
| Smooth | Trailing mean over the stated periods. Partial windows are dropped |
| Normal | Median of the series |
| Episodes | Each unbroken stretch above normal whose peak clears normal by `episode-height × normal` and reaches `materiality`. A second peak inside the same stretch belongs to the same episode. An episode is *complete* only if it starts after the data begins and returns to normal before it ends |
| Outlier | The worst episode's rise above normal ÷ the next worst's. At or above `outlier-ratio`, the stretch above the next worst's peak is excluded, but only when at least `min-other-episodes` complete episodes remain |
| Cutoffs | Recomputed after exclusions. Score 2 begins at the normal level and the top score at `top-fraction` of the way to the worst retained level, in equal steps. A value on a bound takes the worse score. With `floor-at-zero`, a value at or below zero is always a 1 |

`lower_is_worse` measures such as a credit score are mirrored, scored, and
mirrored back.

## What it found on public data

`tests/test_public_series.py` runs it on Federal Reserve and FDIC net
charge-off history:

- **Cards.** 2008 is an outlier (2.46× the 2002 peak) and is excluded. The
  candidate cutoffs, 3.80 / 4.50 / 5.20 / 5.90%, match the hand analysis.
- **Mortgage and home equity** look like cards under one rule: each has one
  complete episode before 2008, peaking at 0.24% around 2002. So 2008 is
  excluded, and the scale tops out below 0.3%. They keep 2008 only when a
  stated materiality, such as 0.5%, says a 0.24% year was not stress. That
  level is the bank's to set.
- **Other consumer** from the 2011 Call Report break holds no complete cycle,
  and the engine refuses it.

## Verify

```
python -m pytest -q
```

62 tests: profile figures checked against hand and Excel calculations, planted cycles, every refusal, the outlier rule both ways, scoring
on a bound, mirror symmetry, provenance, the command line, the public series,
and an independent recomputation of the card cutoffs that uses only the
standard library. Each of 23 hand-made mutants (14 in the cutoffs, 9 in the
profile) turns a test red.

## Not built yet

- Stage 6: the peer-percentile comparison beside each scale
- The audit workbook. Results are text or JSON for now
- Many-entity input weighted by balance, such as banks and their books
- Spacing other than equal steps
