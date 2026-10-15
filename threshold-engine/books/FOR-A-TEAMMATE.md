# Consumer credit thresholds workbook: a note for a teammate

The workbook sets one set of lines for each consumer credit product and
measure, where it moves from rating 1 Low to 5 High, and records the decision
on each. It covers five products (credit card, mortgage, home equity, other
consumer, auto) and seven measures (net and gross charge-offs, and five
delinquency measures): 35 sets of lines. Each is set from the history of one
of three sources, picked for that product and measure: the industry (every
bank that files a Call Report), a 15-bank peer group, or KeyBank's own Call
Report. All three are rated on the lines picked. That is 105 series, all public
FDIC Call Report data.

## Opening it

1. Open `consumer-credit.xlsx` in Excel (Microsoft 365).
2. If a yellow **Protected View** bar appears, click **Enable Editing**.
   Until then the buttons and dropdowns do not respond.
3. Only yellow cells take input. Every other figure is a formula.

## The tabs

| Tab | What it is for |
|---|---|
| **Decide** | One product and measure at a time. Pick a product and a measure with the buttons. The yellow row under them is that row's decision: **Lines set from** (the source whose history sets the lines), Accept these lines or Reject, the four settings, a period to leave out of that source's history (first quarter, last quarter and the reason) and a note. Everything below follows that row: each source's latest quarter rated on the lines, the Check (OK, or why the settings do not fit and the value that would), every source over the five rating zones on one chart, where each rating begins, and what each source's own history would give. |
| **Summary** | Every product and measure on one page: KeyBank, the peer group and the industry, latest quarter and rating, and KeyBank's difference from the peer group in percentage points. The KeyBank series rated 4 or 5, and the count refused, are listed under Needs your attention. |
| **Peers** | KeyBank against the peer group. Filters at the top (product, net or gross, Peer A and B, the window, the delinquency measure) and a Yes/No for each bank; every view on the tab uses the banks set to Yes. |
| **Thresholds** | One row per product and measure: the source the lines are set from, the four lines, each source's latest value and rating on them, the decision and the Check. |
| **Lines by source** | Each of the 105 series' own lines, with its product and measure's settings: what Decide compares when you pick a source. |
| **Internal**, **Internal data** | The bank's own figures, by segment, in the internal import layout (`docs/INTERNAL-IMPORT.md`): paste them into Internal data, or name the file in the book. Internal shows each product's composite and segments with balances, the composite against KeyBank's Call Report line, and how closely each outside source rates the same quarters. It ships empty. |
| Evidence, Backtest, Sources, Glossary, Run, Data | Reference. Glossary defines every heading. |

## Recording a decision

1. On **Decide**, click the product and the measure.
2. In the yellow row, pick the source under **Lines set from**. Until one is
   picked the row has no lines and no ratings, and Summary says Pick a source.
3. Choose **Accept these lines** or **Reject**, change any setting, and type a
   note.
4. Save the file (Ctrl+S). The decision is stored in the file; the count at
   the top of Decide shows how many of the 35 are decided.

A row showing **Refused** has settings that do not fit the history its lines
are set from (for example, Moderate-Low would begin at or below zero). The
Check states the reason and the value of the setting that would fix it.

## Rebuilding it from the data

The workbook is never edited by hand; it is built by a script from the source
files. From the `threshold-engine` folder, with Python 3.9 or later:

```
python -m pip install .
python -m threshold_engine peers pull --cache books/ind_cache --first 2006Q1 --last 2026Q2 --products "Credit card" Mortgage "Home equity" "Other consumer" Auto --delinquency yes --mergers 2005-01-01
python -m threshold_engine book books/consumer-public.json consumer-credit.xlsx
```

The first command installs the tool and `openpyxl` (once). The second downloads the FDIC Call Report data (only quarters not
already held). The third builds the workbook in about eight minutes.
`books/consumer-public.json` lists every setting and series;
`books/consumer-public-series.csv` lists the 105 series and can be edited in
Excel. A new quarter, another series or the bank's internal file is a change
to those two files, then the same command.

## How it was checked

- **Walkthrough in Excel:** the workbook built by the command above was used
  as a person would (buttons, typing, save, close, reopen), and every answer
  was compared with one computed independently from the source files
  (`docs/walkthrough-book/WALKTHROUGH-BOOK.pdf`).
- **Tie-out:** KeyBank's credit card nonaccrual rate for 2026Q2, 0.69%, was
  traced to KeyBank's filed Call Report (Schedule RC-N line 5.a column C over
  RC-C line 6.a): difference 0
  (`docs/tie-out/keybank-card-nonaccrual-2026-10-14/`).
