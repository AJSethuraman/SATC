# Prompt: the Signals tab, into production (for a cloud session)

Repository `AJSethuraman/SATC`, folder `threshold-engine`, branch
`threshold-engine-book` (PR #442 is merged; start a new branch off `main`
or continue on `threshold-engine-book`, which is at `main` plus this file).
Read `threshold-engine/CLAUDE.md`-level guidance in the repo's `CLAUDE.md`,
`docs/DESIGN-PRINCIPLES.md`, `threshold-engine/LOG.md` (18 October entries)
and `threshold-engine/docs/early-warning-2026-10/README.md` first.

## What to build

A `Signals` tab in the consumer book (`books/consumer-public.json`), built
by the book command like every other tab, holding every signal found in the
October early-warning work and ways to compare them. **The specification is
the mock-up**: `docs/early-warning-2026-10/record/signals-mock.html`, built
by `record/signals_mock.py` from the data beside it. The analyst reviewed it
three times (18 Oct 2026) and said "okay put this into production and
generate a workbook for review". Build what the mock shows, section by
section, in this order:

1. **Controls** — compare against any product (the five, All consumer,
   Credit card + Other consumer), any measure (net and gross charge-offs;
   30-89; 90+ accruing; nonaccrual; 30+ incl. nonaccrual; 90+ incl.
   nonaccrual; 30+ to charge-off), any source; a shift in quarters (or "fits
   best"); a window for the normal (all quarters / without 2020-23); and
   *Banks in the pack*, the same picker as Peers. The pick drives every
   section's overlay and highlights its row in every fit table.
2. **Where the dollars are** — balances, gross charge-offs (4 quarters) and
   30+ incl. nonaccrual dollars by product, with shares that add to 100%,
   for the source picked (KeyBank, each peer, the pack composite, the
   industry), as a table and three charts over time.
3. **30+ incl. nonaccrual, every product** — KeyBank, peer group, industry,
   each product on its own axis.
4. **30+ to charge-off and the gap** — the level; the gap KeyBank minus
   peers in points with the area shaded above/below zero and priced (gap ×
   KeyBank's delinquent dollars); the window test (next 1, 2, 3 quarters).
5. **The pipeline** — 30+ incl. NA → 90+ incl. NA → charge-offs, three
   levels, KeyBank/peers/industry, with KeyCorp's refreshed-FICO share under
   660 laid over KeyBank's 30+ on the dual-axis chart.
6. **Paying only the minimum and 90th-percentile utilization** (Philadelphia
   Fed), **refreshed FICO** (KeyCorp and the peers that cut at 660, from
   10-Qs), **purchase volume by low-score accounts**, **underwriting** (SLOOS
   easing slid over the change in card charge-offs, one chart), **mortgage
   equity and terms** (NMDB), **across products** (three pictures).
7. Under every signal: the **rescaled-and-slid chart with real units on both
   axes** (each line is (value − its normal) ÷ its typical yearly move,
   `scale.py`'s median and 1.4826 × MAD; one grid line = one yearly move for
   either; left axis in the signal's units, right axis in the picked
   series'; the inputs printed under it), and the **fit table** against
   every loss and delinquency series in the book (fits best, how well, without
   2020-23, quarters) with its reading key.
8. **Peer panel beside every chart that draws on the pack**, three states:
   in; out by the book's rules (jump / acquisition share, with why); off
   because unticked under Banks in the pack. Live for Call Report series;
   stated (which banks, which class) for filing-based ones; "not our peer
   group" for the Y-14M, survey and NMDB panels.

## How

- A new module `src/threshold_engine/signals_tab.py`, a `signals` key in the
  book (required, every setting stated, none defaulted), and a `Signals data`
  tab holding the public series the tab draws that are not already on Data
  (Philadelphia Fed balances and originations files, SLOOS `DRTSCLCC`, NMDB,
  the 10-Q FICO shares, KeyBank's by-product dollars). Each is fetched by a
  `peers`-style pull command into the cache with the file's SHA-256 on Run,
  as `peers large-banks-pull` already does; the 10-Q FICO shares come from
  `record/peerfico_pull.py` + `bands.py` + `peers.py`, which need an SEC
  contact (`--user-agent`), never stored.
- Formulas, not pasted values, wherever the pick or Banks in the pack can
  change the picture (the rescale, the fit table, the peer panel, the
  where-the-dollars-are table). No macros. Named ranges and the chart
  conventions of `decide_tab.py` / `peers_workbook.py`.
- Nothing already in the book changes: add the tab, add the data, add the
  glossary terms. Prove it the way #442 did: every old series, tab and read
  unchanged (`docs/walkthrough-book`), and extend the walkthrough with reads
  on the new tab.
- The Excel walkthrough (`walk.ps1`) and the slicer check need Excel 16 on
  Windows; a cloud session cannot run them. Build the workbook, run the
  Python tests and `expected.py`, and hand the workbook back for the Excel
  walkthrough on the analyst's PC.

## Decisions the analyst made (18 Oct 2026), verbatim where there are words

- *"i do not want it to be comparable against only card"* — any product and
  measure; *"i should be able to demonstrate why we are so reliant on card"* —
  the where-the-dollars-are section.
- *"signals include 30+ nonaccrual"* — section 3, and 30+ incl. nonaccrual
  is a target in every fit table.
- *"peers should carry throughout the workbook"*; *"if i change the peers
  judgmentally it should show which turned off manually"* — the three-state
  panel.
- The roll step 30-89 → 90+ is dropped in favour of the pipeline: the level
  of 30+ incl. nonaccrual leads charge-offs by 3 quarters at 0.95 (industry);
  the step ratios add 0.41 and 0.08.
- Two quarters for 30+ to charge-off: industry converts 42% in one quarter,
  86% in two, 130% in three.
- *"make the next mock up … show the size as well"* — the dual-axis
  rescale with its inputs printed.

## Rules (binding)

Public data only in the repository; nothing from KeyBank's books; the SEC
contact email goes in a request header only, never in a file. Never invent a
threshold, weight, delay or cut-off. Facts recorded, not inferred; report what
was not checked. Never push to `main`; draft PR, merge after CI and the Codex
review read *Completed*, with the branch containing current `main`.
