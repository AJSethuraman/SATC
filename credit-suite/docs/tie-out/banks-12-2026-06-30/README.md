# Tie-out: all twelve banks against their own Call Reports — 30 June 2026

**634 of 636 lines tie. 2 differ. 0 could not.**

One PDF per bank, each self-contained: 53 lines, and for every line both the
workbook cell photographed out of Excel and the row of that bank's own filed
Call Report that carries the code. 685 pages and 1,116 filing strips in total.
Open the PDFs, not this.

Start with `../TIE-OUT-ROSTER-all-sets-2026-09-05.pdf`, which covers these twelve
plus the 142 macro series in one page of denominators.

## What was compared

The left of every comparison is a cell read out of the shipped
`example-output/Bank_Peer_Monitor.xlsm`, through the same code path the runner's
own tie-out uses. Never re-fetched. The right is the bank's own Call Report as
the FFIEC serves it — the document the bank signed, not the FDIC's
republication of it.

Each bank contributes 53 lines: 48 dollar amounts read straight off the form,
three quarterly charge-off flows, and two capital ratios.

## The five lines the runner skips, and why they are here anyway

`--tieout --filing` reports five lines per bank as "skipped with a stated
reason". Both reasons are true and neither is a verdict.

- **The two capital ratios** are said to have no single filed line to compare a
  percentage with. The filing publishes them itself, as percentages, on
  Schedule RC-R Part I — line 31 and line 51. They are read off the facsimile.
- **The three quarterly flows** are said to be year-to-date in the filing. They
  are, so the quarter is the difference of two filings, which is the subtraction
  the objection had just finished describing.

## What does not tie

**PNC Bank, two lines.** Credit card and C&I net charge-offs for the quarter
differ from PNC's own filed report by 515 and 652 thousand dollars. The workbook
carries the FDIC's published quarterly figure to the dollar, and the FDIC's own
year-to-date figure matches PNC's filing exactly — so the FDIC's quarterly and
annual figures do not reconcile with each other:

```
FDIC quarterly  Q1  43,842 + Q2  47,617 =  91,459
FDIC year-to-date at Q2                  =  91,974    off by 515
PNC's filed Call Report                  =  91,974
```

The same check across twelve banks and three flow fields reconciles 34 times out
of 36. No merger explains it. **I believe the filing**, and nothing was
adjusted.

## Three defects in the checking itself

Worth recording, because the instrument is a likelier culprit than the data and
was here:

1. I first cited **C&I charge-offs to U.S. addressees only**. The measure is
   U.S. *and* non-U.S., which is also how the C&I balance is built. Ten of
   twelve banks failed, by 9% at JPMorgan and 57% at Goldman Sachs.
2. I took **the first column of the total capital ratio**. An advanced-approaches
   bank that has exited parallel run files two, and must meet the lower. Only
   Citibank files both; the other eleven print "NR".
3. My first twelve source photographs included **six blank white rectangles that
   reported "ok"**, because `window.scrollBy` captures empty in headless Chrome.

Each announced itself as an implausibly uniform failure across every entity.
That uniformity is the tell.

## Reproducing it

Scripts are in `../../../tools/tieout/`:

```
python tools/tieout/gather_banks.py        # rosters, both filings, both XBRL sets
python tools/tieout/bank_ratios.py         # the two filed ratios, off the facsimile
python tools/tieout/bank_rosters.py        # ours vs filed, with the five closed
python tools/tieout/bank_excel_shots.py    # photograph all 636 workbook cells
python tools/tieout/bank_strips.py         # cut 1,116 strips from the filings
python tools/tieout/build_bank_exhibits.py # twelve self-contained PDFs
python tools/tieout/build_master_roster.py # the roster over both sets
```

`bank_ratios.py` and `bank_strips.py` need PyMuPDF; the others need the
`credit_suite` package. They carry absolute paths from the session that wrote
them and are kept as the record of what was run.

## What this does not prove

- **One quarter.** The workbook holds sixteen per bank; the other fifteen were
  not compared.
- **Raw lines, not the ratios built on them.** The FDIC's computed ratios and
  the dashboard's alert logic are arithmetic over figures this proves, and are
  not checked here.
- **The provenance map passed; it was not proved universal.** Every code it
  cites was found on all twelve filings. A citation right for these filers and
  wrong for a bank filing a different form would not show up.
- **Nothing here was checked by a second person.**
