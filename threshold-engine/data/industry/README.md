# Industry series, from the FDIC (built 14 Oct 2026)

Every FDIC filer summed, per product: the industry perspective the
workbook and `synthesize` read. The firm, 13 Oct 2026: "FDIC for all", with
the Federal Reserve's series kept as a cross-check (`compare`). Public data
only.

**What is here:** for Credit card, Mortgage (closed-end first liens), Home
equity (lines), Other consumer (RC-C 6.b + 6.d) and Auto, the net and gross
charge-off rate, trailing four quarters (`<product>_industry_<net|gross>.csv`);
other consumer and auto summed (`other-consumer-auto_industry_*.csv`); and
every delinquency measure on both bases
(`<product>_industry_delinquency-<measure>_<basis>.csv`). 2006 to 2026Q2.
Each file's `#` notes say what it is, how it was built and what it leaves
out; the workbook's Sources tab prints them.

**How they were made** (from a folder holding the cache, so the notes name
it without a local path):

```
python -m threshold_engine peers pull --cache ind_cache --first 2006Q1 --last 2026Q2 --products "Credit card" Mortgage "Home equity" "Other consumer" Auto --delinquency yes --mergers 2005-01-01
python -m threshold_engine peers build ind_out/peers.xlsx --cache ind_cache --roster config/peers.json --series-dir ind_out/series --first 2006Q1 --last 2026Q2 --products "Credit card" Mortgage "Home equity" "Other consumer" Auto --mergers ind_cache/mergers.json --absorptions ind_cache/absorptions.json --extra-acquisitions 6672=2022Q2 --delinquency yes --industry-combined "Other consumer+Auto" --jump 0.25 --acquisition-share 0.05 --min-book 1000000 --exempt-self yes --pack all --min-banks 5 --rank-by net --last-n 8 --min-obs 6 --base-quarter 2019Q4 --index-min-book 1000000 --lagged-years 2019 2025 --lag-years 2 --normalisation-years 2019 2025 --mix-base-year 2019
```

then the `*_industry_*` files copied here. The industry series do not use
the jump, minimum book or pack settings; the other flags are what `build`
requires.

**Checked against:** the FDIC's own Quarterly Banking Profile totals,
`docs/tie-out/industry-qbp-2026-10-14/` (card, auto and other consumer tie;
home equity and mortgage tie outside 2008Q3-Q4, with small pre-2012
differences, all stated there). Against the Federal Reserve's card series
(`tests/data/cards_nco_ttm.csv`), 2006Q4-2026Q2: mean difference 0.000
points, largest 0.229 (2011Q3); the two are built differently (the Fed's is
commercial banks only, seasonally adjusted, a mean of quarterly rates).

## The industry from 1990 (added 18 Oct 2026)

`<product>_industry-from-1990_<net|gross>.csv` for credit card, home equity
and other consumer: the same sums (`books.industry`) over a cache that
starts in 1990Q1, written by `peers industry-long` as **separate series**
under the source "Industry (every bank) from 1990". The 2006 files above are
unchanged; the analyst asked for both (17 Oct 2026). Absorptions under common
control are taken off only where the merger record (pulled from 2005) names
them; before that a survivor's repeated year to date stays in the sum, and
each file's notes say so.

```
python -m threshold_engine peers pull --cache ind_cache --first 1990Q1 --last 2005Q4 --products "Credit card" "Home equity" "Other consumer" --delinquency no --mergers 2005-01-01
python -m threshold_engine peers industry-long data/industry --cache ind_cache --first 1990Q1 --last 2026Q2 --products "Credit card" "Home equity" "Other consumer" --absorptions ind_cache/absorptions.json --reporting-changes config/reporting-changes.json
```

