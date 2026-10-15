# Books: one file, one workbook

A **book** is a file that says everything a workbook is built from: the
settings, every series and where its file is, what is missing and why, and
(optionally) the peers build. One command reads it and writes the whole
workbook: Summary, Decide, Thresholds, Assess, the peer tabs and the
reference tabs. No Excel is needed to build it, and nothing in the book has a
default: a missing setting is refused, by name.

`consumer-public.json` is the consumer credit workbook on public FDIC data:
5 products × 7 measures (net and gross charge-offs, five delinquency
measures) from the industry, the 15-bank peer group and KeyBank: 95 series.
KeyBank's own charge-offs are not in it, and the book says why.
`consumer-public-series.csv` is its series list; open it in Excel to see or
change what goes in.

## Build it at work

You need Python 3.9 or later and `openpyxl`, and the `threshold-engine`
folder. Every command runs from inside `threshold-engine`.

1. Install the one dependency (once):

   ```
   python -m pip install openpyxl
   ```

2. Pull the FDIC data into `books/ind_cache` (public data; this is the slow
   step, and only the quarters not already in the cache are fetched next time):

   ```
   python -m threshold_engine peers pull --cache books/ind_cache --first 2006Q1 --last 2026Q2 --products "Credit card" Mortgage "Home equity" "Other consumer" Auto --delinquency yes --mergers 2005-01-01
   ```

3. Build the workbook:

   ```
   python -m threshold_engine book books/consumer-public.json consumer-credit.xlsx
   ```

   It prints `Wrote consumer-credit.xlsx: 95 series, 82 quarters; open it on
   Summary, decide on Decide`. The peers build inside it also writes every
   series file to `books/out/series` and its own notes.

4. Open `consumer-credit.xlsx` in Excel. If a yellow bar says **Protected
   View**, click **Enable Editing**: until then the buttons and dropdowns do
   nothing.

## Using it

- **Summary**: every series' latest quarter and its rating, 1 Low to 5 High,
  products down the side, industry, peers and KeyBank across.
- **Decide**: click a product, a measure and a source. The one yellow row
  under the buttons is that series' decision: Accept these lines or Reject,
  its four settings, a period to leave out (first quarter, last quarter, why)
  and a note. Everything under it follows as you type: where it stands, the
  chart over its five rating zones, where each rating begins, whether the
  settings fit (or why not, and the number that would fix it), and what the
  history suggests. **Save the file (Ctrl+S) to keep your decisions.** The
  count at the top says how many of the 95 are decided.
- **Thresholds** and **Assess** follow Decide; nothing is typed there.
- The **Peers** tabs: KeyBank against the 15 banks, as `peers build` writes
  them.

No macros: the buttons are Excel slicers, which banks allow.

## Adding the bank's own series

An internal series (from `threshold-engine internal series`, run on site) is
one more row in the series CSV, for example:

```
Credit card,Net charge-offs,KeyBank internal,internal/credit-card_net.csv
```

Its source becomes a fourth column on Summary and a fourth button on Decide.
Internal files stay on site; the book only names where they are.

## Your own book

Copy `consumer-public.json` and its CSV, change what you need, and build.
`threshold-engine book --help` and the top of `src/threshold_engine/book.py`
say what each key means. Relative paths are read from the book's own folder.
