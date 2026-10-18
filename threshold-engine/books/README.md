# Books: one file, one workbook

A **book** is a file that says everything a workbook is built from: the
settings, every series and where its file is, what is missing and why, and
(optionally) the peers build. One command reads it and writes the whole
workbook: Summary, Decide, Thresholds, Assess, the peer tabs and the
reference tabs. No Excel is needed to build it, and nothing in the book has a
default: a missing setting is refused, by name.

`consumer-public.json` is the consumer credit workbook on public FDIC data:
5 products × 7 measures (net and gross charge-offs, five delinquency
measures) from the industry, the 15-bank peer group and KeyBank: 105 series.
A KeyBank series shorter than the others keeps its lines; only its Backtest
row says it was not tested.
`consumer-public-series.csv` is its series list; open it in Excel to see or
change what goes in.

`commercial-public.json` is the commercial book on the firm's answers of 17
Oct 2026 to questions 1 to 12 of `docs/COMMERCIAL-PROPOSAL.md` (on main):
6 portfolios (C&I, Nonfarm nonresidential CRE and its two parts, Multifamily,
Construction) x 2 measures (nonaccrual and net charge-offs) from the
industry, the peer median, the peer total and KeyBank: 48 series, from
1991Q1 where the data holds it. **Its settings are the consumer book's,
pending the firm's choice**: the firm has chosen none for commercial but the
minimum book (0). The book's name says so, so Summary's and Chart's titles
and the Run tab's Measure line carry it, and so does its first note. It declares no extra
acquisition: the consumer book's is a consumer deal. Its notes say how each
answer was applied and
what was not. Its cache paths name a scratch folder; change them to build it
elsewhere.

Every book states its `kind`. A consumer book calls the first part
**Product**; a commercial book calls it **Portfolio**, on every tab, and shows
its portfolios by commercial names, with the Call Report's own name for each
on the Glossary. The firm asked only for more commercial names ("names in
this should be changed to be more commercial ... product sounds consumer");
the names themselves were proposed by the session that built the book
(Claude) the same day, 17 Oct 2026, and the firm did not object. A book that does not state its kind is refused.

## Build it at work: the one file

`Consumer credit thresholds.pyzw` is the whole tool in one file
(`python tools/make_app.py OUT_FOLDER` writes it). The work machine needs
Python 3.9 or later from python.org, installed for the user, and nothing else.

1. Double-click `Consumer credit thresholds.pyzw`. A window opens.
2. **Folder**: where the FDIC data, the book's files and the workbook go
   (it starts as Documents\Consumer credit thresholds).
3. **Latest quarter**: the last quarter filed, for example `2026Q2`.
4. **SEC contact**: a name and an email. SEC refuses requests without one;
   it is sent to SEC only and never stored.
5. **Internal file**: optional; the bank's file in the internal import layout
   (`docs/INTERNAL-IMPORT.md`).
6. Click **1. Get the data** (the FDIC quarters the folder does not hold, and
   each peer's SEC filing for the Peer loan classes tab), then **2. Build the
   workbook** (about nine minutes). Excel opens it.

Followed on 15 Oct 2026 with Python's site-packages switched off, so only what
is inside the file was used: the workbook was built in 530 seconds.

## Build it at work: from the folder

You need Python 3.9 or later and the `threshold-engine` folder. Every
command runs from inside `threshold-engine`. Followed from nothing on 15 Oct
2026 (a fresh copy of the folder, a new Python environment): the build took
8 minutes 17 seconds and wrote 105 series.

1. Install the tool and its one dependency, `openpyxl` (once, and again after
   the folder is updated):

   ```
   python -m pip install .
   ```

2. Pull the FDIC data into `books/ind_cache` (public data; this is the slow
   step, and only the quarters not already in the cache are fetched next time).
   If the folder came with `books/ind_cache` already in it, skip to step 3
   until a new quarter is filed:

   ```
   python -m threshold_engine peers pull --cache books/ind_cache --first 2006Q1 --last 2026Q2 --products "Credit card" Mortgage "Home equity" "Other consumer" Auto --delinquency yes --mergers 2005-01-01
   ```

3. Build the workbook:

   ```
   python -m threshold_engine book books/consumer-public.json consumer-credit.xlsx
   ```

   It prints `Wrote consumer-credit.xlsx: 105 series, 82 quarters; open it on
   Summary, decide on Decide`. The peers build inside it also writes every
   series file to `books/out/series` and its own notes.

4. Open `consumer-credit.xlsx` in Excel. If a yellow bar says **Protected
   View**, click **Enable Editing**: until then the buttons and dropdowns do
   nothing.

## Using it

- **Summary**: every series' latest quarter and its rating, 1 Low to 5 High,
  on its product and measure's one set of lines, products down the side,
  industry, peers and KeyBank across.
- **Decide**: click a product and a measure. The one yellow row under the
  buttons is that row's decision: **Lines set from** (the source whose history
  sets the lines; the book's `lines_from` says what it starts as, null for
  blank), Accept these lines or Reject, its four settings, a period to leave
  out of that source's history (first quarter, last quarter, why) and a note.
  Everything under it follows as you type: every source rated on the lines,
  every source on one chart over the five rating zones, where each rating
  begins, what each source's own history would give, whether the settings fit
  (or why not, and the number that would fix it), and what the history
  suggests. **Save the file (Ctrl+S) to keep your decisions.** The count at
  the top says how many of the 35 are decided.
- **Thresholds** (one row per product and measure), **Lines by source** (each
  series' own lines) and **Assess** follow Decide; nothing is typed there.
- The **Peers** tabs: KeyBank against the 15 banks, as `peers build` writes
  them.
- **Reporting changes**: every change to the Call Report the workbook labels
  (`config/reporting-changes.json`), with its source. Each series it touches
  says so on Sources, and the charts on Decide and Peers mark the quarters
  with a diamond.

No macros: the buttons are Excel slicers, which banks allow.

## Adding the bank's own series

An internal series (from `threshold-engine internal series`, run on site) is
one more row in the series CSV, for example:

```
Credit card,Net charge-offs,KeyBank internal,internal/credit-card_net.csv
```

Its source becomes a fourth column on Summary and a fourth choice under
Lines set from on Decide.
Internal files stay on site; the book only names where they are.

## Your own book

Copy `consumer-public.json` and its CSV, change what you need, and build.
`threshold-engine book --help` and the top of `src/threshold_engine/book.py`
say what each key means. Relative paths are read from the book's own folder.
