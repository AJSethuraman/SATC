# Worked Example — Meridian Fabrication LLC (sample private credit)

A walkthrough of one private middle-market name through the workbench, from
inputs to exported memo, with commentary on how a challenge function would
use each piece. The borrower is fictional and instructive by design; the
benchmark levels come from the v1 **synthetic demonstration snapshot** (see
the data caveat stamped on everything below).

## 1. The credit

Meridian Fabrication LLC: a metal-fabrication C&I borrower, core middle
market by EBITDA ($32M FY2024 — the workbench auto-assigns the CMM band
from the EBITDA input). The line of business presents it as a stable,
adequately-secured relationship. Three fiscal years, lender-provided, $M:

| | FY2022 | FY2023 | FY2024 |
|---|---|---|---|
| Revenue | 252 | 246 | 240 |
| EBITDA (normalized) | 40 | 35.5 | 32 |
| Total debt | 140 | 150 | 162 |
| Interest expense | 8.4 | 11.6 | 14.6 |
| Receivables / Inventory | 33 / 38 | 36 / 41 | 38 / 42 |

(Full inputs: `data/sample_borrower.json` — paste-ready for the workbench.)

The LOB rationale this review challenges: *"leverage of ~5x is in line with
where the market is for this profile, margins are above peer average, and
the working-capital build reflects growth investment."*

## 2. What the workbench shows

Loaded in two clicks (the Sample button, or paste the JSON). Segment: C&I;
band: CMM (auto). Grading view: **private-MM adjusted** (raw shown as ghost
band on every strip).

The position table from the actual export (flags graded against the
adjusted distribution):

- **Total Debt / EBITDA 5.06x — WATCH (p76)**, peer median 3.92x adj.
- **Net Debt / EBITDA 4.88x — WATCH (p77)**, peer median 3.04x adj.
- **EBITDA / Interest 2.19x — IN RANGE (p33)**, but the *path* is 4.76x →
  3.06x → 2.19x.
- **EBITDA margin 13.3% — IN RANGE (p71)**: the one LOB claim that survives.
- **DSO 58d / DIO 91d / CCC 103d — all WATCH (p83/p84/p84)**.
- **Debt / Total Assets 77.1% — SEVERE (p98)**.
- Through-cycle leverage: not applicable for C&I (agribusiness basis), so
  no spurious row appears.

Three reads the raw numbers alone would not give:

1. **Departure vs. normalization.** Every flagged metric is classified from
   the 3-year path. Leverage is a *structural departure in motion* — the gap
   to the peer median widened each year (3.5x → 4.23x → 5.06x against a flat
   peer median). This is not a name reverting to normal after a one-off; it
   is the pattern that precedes criticized-asset migration, and the memo
   says so in those words.
2. **The raw-vs-adjusted toggle quantifies the size argument.** On the raw
   public distribution 5.06x sits at ~p77 of peers; on the
   private-adjusted CMM distribution (dispersion ×1.25, survivorship tail
   +12% of IQR) it reads p76 — the widening concedes that private
   middle-market dispersion is genuinely wider than the public record
   shows, while the extended tail moves the *severe* boundary out to where
   the censored failures lived. Both views grade WATCH here; what the
   toggle proves is that the flag does not depend on the adjustment
   judgment. A reviewer who disputes the calibration sees the exact
   parameters in the drawer and the memo, and can re-bake with different
   ones.
3. **Mechanism, not delta.** The CCC finding doesn't say "103 days vs. 62
   median"; it says the lengthening cycle is the classic mechanism of
   profitable companies running out of cash, that each CCC day must be
   funded by the revolver, and that the "growth investment" story requires
   rising revenue — Meridian's revenue *fell* 2.4%, which makes the
   inventory build involuntary until proven otherwise. That is the question
   the LOB rationale has to answer.

## 3. The challenge, in one paragraph

The LOB's "~5x is market" claim fails on basis: against an addback-free,
size-adjusted CMM C&I distribution, 5.06x gross / 4.88x net is outside the
adjusted interquartile range and moving away from it, funded at floating
rates that have already cut coverage from 4.8x to 2.2x in two years — with
the entire working-capital cycle elongating against falling revenue, and
balance-sheet leverage (77% of book assets) in the survivorship-extended
severe zone. The margin strength is real but is the *only* in-range core
metric, and margins are the first casualty of the involuntary-inventory
scenario. Recommended posture: reject "in line with market"; require the
aging schedule, maintenance-vs-growth capex split, revolver availability
and hedging detail the mechanism notes identify before the next renewal.

## 4. The exported memo

One click produces `docs/sample_memo_export.md` (committed verbatim as
exported from the GUI — every figure basis-labeled, sources and coverage
gaps included, adjustment parameters and validation stats disclosed, data
caveat at the top). The memo is the review-file deliverable; the workbench
is how you got there.

## 5. Honest caveats on this example

- Benchmark levels are **synthetic demonstration data** (the environment
  could not reach EDGAR; see methodology memo §9). The flags above
  demonstrate the machinery, not a market calibration. After a live
  refresh, the same inputs re-grade against real distributions.
- Meridian's EBITDA is lender-normalized; the peer EBITDA basis is
  addback-free. The memo carries this comparability note — it means peer
  comparisons *flatter* the borrower.
- CMM C&I peer coverage in the demo snapshot is adequate (n≈8 companies),
  but the same borrower one band down (LMM) would grade against a 3-company
  cell with loud thin-coverage warnings — by design, that is what the
  public record actually supports there.
