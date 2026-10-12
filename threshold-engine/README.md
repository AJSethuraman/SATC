# threshold-engine

Sets the lines a separate scoring file uses to rate a consumer credit measure
1 to 5 (Low, Moderate-Low, Moderate, Moderate-High, High). It does not score a
portfolio. Give it one CSV per product and it writes one Excel workbook in which
the bank's judgements are cells and the lines are live formulas.

**Read next:** `docs/WHAT-IT-DOES.md` (every part, what goes in and out, what
proves it) and `docs/NEXT-GOAL.md` (what is left before it goes out). The
decisions behind it, in the bank's words, are in `LOG.md`.

## Install

```
cd threshold-engine
python -m pip install .
```

Python 3.9 or later. The one add-on is `openpyxl`. The tests also need `pytest`
and `formulas` (`python -m pip install ".[test]"`).

## Build the workbook

```
threshold-engine workbook consumer-thresholds.xlsx --series "Credit card=tests/data/cards_nco_ttm.csv" --series "Mortgage=tests/data/mortgage_nco_ttm.csv" --series "Home equity=tests/data/home_equity_nco_ttm.csv" --series "Other consumer=tests/data/other_consumer_as_filed_nco_ttm.csv" --name "Net charge-offs, trailing twelve months" --unit % --direction higher_is_worse --frequency quarterly --smoothing 1 --floor-at-zero yes --moderate-halfwidth 0.5 --low-step 1.0 --high-z 2.5 --on-the-line worse --percentiles 50 75 90 95 --horizon 4 --min-history 41
```

A CSV has a `date,value` header; lines starting with `#` are notes. Every
setting that is a judgement must be stated: nothing has a default.

## The other commands

| Command | What it does |
|---|---|
| `profile` | Facts about one series, no judgement settings |
| `evidence` | The statistics behind each judgement, and the lines under three scenarios, on the workbook's scale |
| `backtest` | How predictive a percentile scale would have been, rebuilt each quarter from only the past |

`threshold-engine COMMAND --help` lists each command's settings.

## Verify

```
python -m pip install ".[test]"
python -m pytest -q
```

The workbook's live formulas are recalculated in the tests and must equal
`scale.py`, the Python reference, for every product and setting.
