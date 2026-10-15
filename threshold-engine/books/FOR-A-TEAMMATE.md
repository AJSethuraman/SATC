# Consumer credit thresholds workbook: a note for a teammate

The workbook proposes where each consumer credit measure moves from rating 1
Low to 5 High, from that series' own history, and records the decision on
each one. It covers five products (credit card, mortgage, home equity, other
consumer, auto) and seven measures (net and gross charge-offs, and five
delinquency measures), each from three sources: the industry (every bank that
files a Call Report), a 15-bank peer group, and KeyBank's own Call Report.
That is 105 series. All figures are public FDIC Call Report data.

## Opening it

1. Open `consumer-credit.xlsx` in Excel (Microsoft 365).
2. If a yellow **Protected View** bar appears, click **Enable Editing**.
   Until then the buttons and dropdowns do not respond.
3. Only yellow cells take input. Every other figure is a formula.

## The tabs

| Tab | What it is for |
|---|---|
| **Decide** | One series at a time. Pick a product, a measure and a source with the buttons. The yellow row under them is that series' decision: Accept these lines or Reject, the four settings, a period to leave out (first quarter, last quarter and the reason) and a note. Everything below follows that row: the latest quarter and its rating, the Check (OK, or why the settings do not fit and the value that would), the chart over the five rating zones, where each rating begins, and the same measure from the other two sources. |
| **Summary** | Every product and measure on one page: KeyBank, the peer group and the industry, latest quarter and rating, and KeyBank's difference from the peer group in percentage points. The KeyBank series rated 4 or 5, and the count refused, are listed under Needs your attention. |
| **Peers** | KeyBank against the peer group. Filters at the top (product, net or gross, Peer A and B, the window, the delinquency measure) and a Yes/No for each bank; every view on the tab uses the banks set to Yes. |
| **Thresholds** | Every series' lines, latest value, rating, decision and Check, one row each. |
| Evidence, Backtest, Sources, Glossary, Run, Data | Reference. Glossary defines every heading. |

## Recording a decision

1. On **Decide**, click the product, measure and source.
2. In the yellow row, choose **Accept these lines** or **Reject**, change any
   setting, and type a note.
3. Save the file (Ctrl+S). The decision is stored in the file; the count at
   the top of Decide shows how many of the 105 are decided.

A series showing **Refused** has settings that do not fit its history (for
example, Moderate-Low would begin at or below zero). The Check states the
reason and the value of the setting that would fix it.

## Rebuilding it from the data

The workbook is never edited by hand; it is built by a script from the source
files. From the `threshold-engine` folder, with Python and `openpyxl`:

```
python -m threshold_engine peers pull --cache books/ind_cache --first 2006Q1 --last 2026Q2 --products "Credit card" Mortgage "Home equity" "Other consumer" Auto --delinquency yes --mergers 2005-01-01
python -m threshold_engine book books/consumer-public.json consumer-credit.xlsx
```

The first command downloads the FDIC Call Report data (only quarters not
already held). The second builds the workbook in about eight minutes.
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
