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
threshold-engine workbook consumer-thresholds.xlsx --series "Credit card=data/industry/credit-card_industry_net.csv" --series "Mortgage=data/industry/mortgage_industry_net.csv" --series "Home equity=data/industry/home-equity_industry_net.csv" --series "Other consumer=data/industry/other-consumer_industry_net.csv" --series "Auto=data/industry/auto_industry_net.csv" --name "Net charge-offs, trailing twelve months" --unit % --direction higher_is_worse --frequency quarterly --smoothing 1 --floor-at-zero yes --moderate-halfwidth 0.5 --low-step 1.0 --high-z 2.5 --on-the-line worse --percentiles 50 75 90 95 --horizon 4 --min-history 41
```

The industry series are the FDIC's, every filer summed (`data/industry/`, its README says how they were
built and what they were checked against). A CSV has a `date,value` header; lines starting with `#` are notes. Every
setting that is a judgement must be stated: nothing has a default.

Or double-click `Thresholds.pyw` for a window that asks for the same things
and builds the same workbook.

## Peers

KeyBank against a 16-bank roster (`config/peers.json`), from public FDIC Call
Reports. Pull once into a cache folder, then build from the cache:

```
threshold-engine peers pull --cache fdic-cache --first 2006Q1 --last 2026Q2 --products "Credit card" Mortgage "Home equity" "Other consumer" --mergers 2005-10-01 --delinquency yes
```

```
threshold-engine peers build peers.xlsx --cache fdic-cache --roster config/peers.json --series-dir peer-series --first 2006Q1 --last 2026Q2 --products "Credit card" Mortgage "Home equity" "Other consumer" --mergers fdic-cache/mergers.json --extra-acquisitions 6672=2022Q2 --delinquency yes --industry-combined --jump 0.25 --min-book 1000000 --exempt-self yes --pack all --min-banks 5 --rank-by net --last-n 20 --min-obs 12 --base-quarter 2019Q4 --index-min-book 500000 --lagged-years 2019 2025 --lag-years 2 --normalisation-years 2019 2025 --mix-base-year 2019
```

`6672=2022Q2` is Fifth Third's purchase of Dividend Finance, a nonbank the FDIC
record does not show. The build writes the peer workbook and, in
`peer-series`, `date,value` CSVs the `workbook` command reads: charge-offs
and, with `--delinquency yes`, five delinquency and nonaccrual measures per
product on two bases (quarter-end and four-quarter average). A cache pulled
without `--delinquency yes` is refused for a delinquency build; pull again
with `--refresh`.

## Templates for internal data

Internal measures are run on site and nothing internal comes back. A template
is an empty `date,value` file whose `#` notes ask what the bank must state;
`check` refuses a file that does not match, before a build:

```
threshold-engine template list
threshold-engine template write wapd wapd.csv
threshold-engine template check wapd wapd.csv
```

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
