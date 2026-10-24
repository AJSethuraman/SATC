# Tie-out: all twelve banks against their own Call Reports — 30 June 2026

**720 of 720 lines tie. 0 differ. 0 could not.**

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

Nothing. All 720 lines agree with the banks' own filed Call Reports.

**A withdrawn finding.** The first two editions reported five PNC lines as
differences and concluded that the FDIC's own quarterly and annual figures
disagreed with each other. **That was my error, not a defect.**

PNC merged **FirstBank** of Lakewood, Colorado (cert 18714) into itself on
**18 June 2026**, twelve days before the reporting date. A quarterly flow is the
year-to-date total less the previous quarter's — and across a merger the
acquired bank's prior year-to-date has to come off too, because the survivor's
total already contains it. I subtracted only PNC's own.

```
field      Q2 year-to-date   less PNC Q1   less FirstBank Q1   = quarter   FDIC
NTCRCDQ             91,974        43,842                 515      47,617  47,617
NTCIQ              211,710       101,857                 652     109,201 109,201
NTCONOTQ            26,566        15,470                 102      10,994  10,994
NTRERESQ             2,999         1,113                   6       1,880   1,880
NTRECONQ              -431           -48                 188        -571    -571
NTAUTOQ             17,837        10,233                   0       7,604   7,604
NTREMULQ              -273          -286                   0          13      13
```

Every gap equalled FirstBank's Q1 figure to the dollar, and the two fields that
did tie are the two where FirstBank's figure was zero. That is not coincidence;
it is the shape of the mistake.

**The workbook had already worked this out.** Its `_mergers` tab records the
acquisition and says, in its own words, that the quarter ending 2026-06-30
"spans a merger … a quarterly flow is the year-to-date total less the previous
quarter's, so across a merger it mixes two banks and is not a quarter of
anything." I never opened that tab. I queried the FDIC's history API instead,
filtered on processing date, saw only branch transfers dated 6 July 2026, and
wrote "no merger explains it" into twelve exhibits and a roster.

The flow derivation now consults the merger record for every bank.

**Still true, and worth keeping:** the figure is arithmetically correct *and* it
mixes two banks, so this quarter is not comparable with PNC's other quarters.
That is why the trend tooling blanks flows across a merger rather than charting
them.

## Four defects in the checking itself

The instrument is a likelier culprit than the data, and was — four times:

1. **The PNC merger, above.** The biggest of them, and the one that reached the
   firm as a finding before it was caught.
2. I first cited **C&I charge-offs to U.S. addressees only**. The measure is
   U.S. *and* non-U.S. Ten of twelve banks failed, by 9% at JPMorgan and 57% at
   Goldman Sachs.
3. I took **the first column of the total capital ratio**. An advanced-approaches
   bank that has exited parallel run files two and must meet the lower. Only
   Citibank files both.
4. My first twelve source photographs included **six blank white rectangles that
   reported "ok"**, because `window.scrollBy` captures empty in headless Chrome.

Numbers 2 to 4 announced themselves as an implausibly uniform failure across
every entity. Number 1 did the opposite — it looked like a finding about exactly
one bank, which is precisely why it was believable.

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
