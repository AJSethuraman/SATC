# Tie-out: all twelve banks against their own Call Reports — 30 June 2026

**715 of 720 lines tie. 5 differ. 0 could not.**

One PDF per bank, each self-contained: 60 lines, and for every line both the
workbook cell photographed out of Excel and the row of that bank's own filed
Call Report that carries the code. 824 pages and 1,584 filing strips in total.
Open the PDFs, not this.

Start with `../TIE-OUT-ROSTER-all-sets-2026-09-05.pdf`, which covers these twelve
plus the 142 macro series in one page of denominators.

## The denominator

Each bank has **69** raw fields in the workbook.

| | |
|---:|---|
| **60** | compared here, against the bank's own filed Call Report |
| **8** | ratios the FDIC computes from lines proved here — out of scope, and named below rather than omitted |
| **1** | `NTRENREQ`, which the FDIC publishes no quarterly figure for, so it is blank for every bank |

The eight out of scope: `NCLNLSR`, `NTLNLSQR`, `LNATRESR`, `LNRESNCR`, `EQV`,
`ROAQ`, `NIMY`, `EEFFR`.

**This is the second edition.** The first said "53 of 53 lines tie" and never
mentioned the other sixteen. See the correction below.

## What was compared

The left of every comparison is a cell read out of the shipped
`example-output/Bank_Peer_Monitor.xlsm`, through the same code path the runner's
own tie-out uses. Never re-fetched. The right is the bank's own Call Report as
the FFIEC serves it — the document the bank signed, not the FDIC's
republication of it.

Of the 60: 51 dollar amounts read straight off the form, five quarterly net
charge-offs differenced between two filings, two capital ratios the bank files
itself, and two more past-due lines recovered in this edition.

## The correction

The first edition compared 53 of 69 fields per bank and reported the result as
if it were all of them. Chasing the missing sixteen found three faults in the
provenance map, every one in a row already flagged `[V]` for verified:

1. **Seven rows carried no citation at all** — the literal text
   `(not in tie-out map)` where the MDRM code belongs. The workbook landed a
   value and nothing recorded where it came from, so the tie-out walked past
   them. *A check that examines what the map documents cannot discover what the
   map omits.*
2. **Parentheses do not parse.** The expression reader rebuilds a string
   character for character and has no notion of a bracketed group, so
   `(C891+C893) - (C892+C894)` silently became nothing. Every quarterly-flow
   citation was affected.
3. **A bare code resolves against RCFD then RCON only** — right for a
   balance-sheet line, useless for an income-statement one, which needs `RIAD`.
   And the two capital ratios cited `RCOA`, the form-041 prefix, on twelve banks
   that all file 031, where it is `RCFA`.

Separately, the filing parser kept only whole numbers, discarding **every ratio
in every filing** before any tie-out could see it. Dollar amounts are whole
numbers, so nothing dollar-denominated ever looked wrong. The capital ratios
were in the XBRL the whole time, as fractions with `unitRef="PURE"`; they now
agree three ways — XBRL × 100, the rendered facsimile, and the workbook — on all
24 bank-ratio pairs.

`tests/test_provenance_citations.py` is the guard that was missing: every
citation must parse, and must find its line on a real filed Call Report.

## What does not tie

**PNC Bank, five lines.** Every quarterly net-charge-off field PNC reports
differs from its own filed report:

```
field       FDIC Q1 + FDIC Q2   =   sum      FDIC year-to-date   gap
NTCRCDQ       43,842 +  47,617  =   91,459          91,974       515
NTCIQ        101,857 + 109,201  =  211,058         211,710       652
NTCONOTQ      15,470 +  10,994  =   26,464          26,566       102
NTRERESQ       1,113 +   1,880  =    2,993           2,999         6
NTRECONQ         -48 +    -571  =     -619            -431       188
```

PNC's filed Call Report agrees with the year-to-date column, not with the sum of
the two quarters. The workbook carries the FDIC's quarterly figure to the
dollar. The same reconciliation across twelve banks and seven flow fields holds
**79 times out of 84**, and the five that fail are exactly these. No merger
explains it — PNC's only 2026 acquisition events are branch transfers dated
6 July 2026, after the reporting date.

**I believe the filing**, and nothing was adjusted.

## Three defects in the checking itself

The instrument is a likelier culprit than the data, and was:

1. I first cited **C&I charge-offs to U.S. addressees only**. The measure is
   U.S. *and* non-U.S. Ten of twelve banks failed, by 9% at JPMorgan and 57% at
   Goldman Sachs.
2. I took **the first column of the total capital ratio**. An advanced-approaches
   bank that has exited parallel run files two and must meet the lower. Only
   Citibank files both.
3. My first twelve source photographs included **six blank white rectangles that
   reported "ok"**, because `window.scrollBy` captures empty in headless Chrome.

Each announced itself as an implausibly uniform failure across every entity.

## Reproducing it

Scripts are in `../../../tools/tieout/`:

```
python tools/tieout/gather_banks.py        # rosters, both filings, both XBRL sets
python tools/tieout/bank_ratios.py         # the two filed ratios, off the facsimile
python tools/tieout/bank_rosters.py        # ours vs filed, with the five closed
python tools/tieout/close_the_gap.py       # the eight fields the map could not cite
python tools/tieout/merge_gap.py           # fold them in, state the denominator
python tools/tieout/bank_excel_shots.py    # photograph all 732 workbook cells
python tools/tieout/bank_strips.py         # cut 1,584 strips from the filings
python tools/tieout/build_bank_exhibits.py # twelve self-contained PDFs
python tools/tieout/build_master_roster.py # the roster over both sets
```

`bank_ratios.py`, `bank_strips.py` and `close_the_gap.py` need PyMuPDF. They
carry absolute paths from the session that wrote them and are kept as the record
of what was run.

## What this still does not prove

- **One quarter.** The workbook holds sixteen per bank; the other fifteen were
  not compared.
- **The eight computed ratios per bank**, named above.
- **The dashboard's own logic** — z-scores, bands, alerts. Arithmetic over
  figures this proves.
- **The provenance map passed; it was not proved universal.** Every code it
  cites was found on all twelve filings. A citation right for these filers and
  wrong for a bank filing form 041 would not show up here.
- **Nothing here was checked by a second person.**
