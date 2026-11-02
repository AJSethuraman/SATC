# Prompt: Book 2, consumer drivers (for the agent building it)

Hand this whole file to the agent building Book 2. It states what Book 1 now
is, what the analyst decided, what Book 2 reads from Book 1 and how, and the
contracts both books keep. Nothing here changes Book 1; Book 1's owner is
told of anything Book 2 needs that is not here.

---

## What Book 1 is now (18 October 2026)

`threshold-engine/books/consumer-public.json` builds the Consumer Industry
Analysis workbook: one set of 1 Low to 5 High lines per product and measure,
set from the history of one source the analyst picks (the industry, the
15-bank peer group, or KeyBank), and every source rated on those lines.
Public FDIC Call Report data, plus one public Philadelphia Fed series.

- **Products:** Credit card, Mortgage, Home equity, Other consumer, Auto, and
  two combined products, "All consumer" and "Credit card + Other consumer".
- **Measures:** Net charge-offs, Gross charge-offs (trailing twelve months,
  % of average balances); 30-89 days past due, 90+ days past due and
  accruing, Nonaccrual, 30+ days past due incl. nonaccrual, 90+ days past due
  incl. nonaccrual (quarter-end, % of balances); and, from 18 October, for
  credit card and other consumer: **30+ to charge-off** (of the dollars past
  due at a quarter-end, the share charged off gross over the next two
  quarters; four-quarter average), **Gap to peers on 30+ to charge-off** and
  **Gap to industry on 30+ to charge-off** (KeyBank's four-quarter average
  less the peer group's or the industry's, same quarter, percentage points;
  no floor at zero); and for credit card, **Share paying only the minimum**
  (large banks, Philadelphia Fed, 2012Q3 on).
- **Sources:** Industry (every bank), Peer group (15 banks), KeyBank, and
  for the one Philadelphia Fed measure, Large banks (Philadelphia Fed).
- **A fourth source, "Industry (every bank) from 1990"**: the industry's net
  and gross charge-offs for credit card, home equity and other consumer over
  a cache that starts in 1990Q1, as separate series (`peers industry-long`;
  committed under `data/industry/*_industry-from-1990_*.csv`). The 2006
  series are unchanged. Two credit cycles before 2008 for the lines.
- **164 series**, listed in `books/consumer-public-series.csv` with the exact
  Product, Measure and Source names and each series' file.

## What the analyst decided, and why Book 2 should know it

The record is `docs/early-warning-2026-10/EVIDENCE.html` (and `.pdf`): every
signal tested, drawn against what later happened. The outcomes that bear on
Book 2:

1. **Refreshed FICO was set aside.** It moves in the same quarter as 30-89
   days past due; its year's lead on charge-offs is only the time delinquency
   takes to become a loss. Book 2 should not treat a refreshed score as a
   driver that leads delinquency.
2. **Origination quality and underwriting standards lead card losses by two
   to three years**: the score of the bottom tenth of new card accounts, the
   share of new accounts under 660 (Philadelphia Fed), and the net share of
   banks easing card standards (Senior Loan Officer Survey, FRED
   `DRTSCLCC`). The analyst put them beside Book 1's ratings as context, not
   as ratings, because they are lending policy, closer to an economic
   indicator. **These belong with Book 2's drivers.** The tested delays:
   easing, about 11 quarters ahead of card charge-offs; new accounts under
   660 and the origination score, 8 to 9 quarters; all about 6 quarters
   ahead of card 30-89.
3. **Mortgage losses are an outlier.** Charge-offs are near zero since 2014;
   mortgage is rated on delinquency (nonaccrual first). What turns mortgage
   delinquency into loss is equity: FHFA's National Mortgage Database shows
   0.3% of outstanding mortgages underwater in 2026Q2 against 11.3% in 2013.
   **Home prices and current loan-to-value are Book 2's territory**, and so
   is unemployment for every product.
4. **The pandemic years ran backwards.** 2020Q1 to 2023Q4 raised scores and
   cut losses, then reversed both. Every card relationship tested was
   weaker, or different, with those quarters left out. Book 2 should test
   its links with and without them and say which it rests on.
5. **Other consumer 30-89 comes about 3 quarters before mortgage 90+**, but
   mortgage's own 30-89 turns at the same time; it confirms, it does not
   lead.

## What Book 2 reads from Book 1

Book 2 reads Book 1's series files, read-only, and nothing else of Book 1's.

- **The series folder is a setting, not a fixed path.** There is no single
  folder: a repository build writes `books/out/series` (ignored by git) and
  the one-file app writes `<chosen folder>/Book/out/series`. Book 2 takes
  the folder from its own settings and prints which folder it read.
- **Read the series CSVs, never the workbook's Data tab.** The Data tab's
  peer-group and derived columns are formulas with no stored values until
  Excel recalculates and saves; a non-Excel reader sees blanks.
- **Fingerprints.** Book 1's Run tab lists every series file with its
  SHA-256. Book 2 fingerprints each file it reads and refuses one that does
  not match the Run tab of the build it names; a later `peers build`
  rewrites the files, so Book 2 reads the same build it checks against.
  Each file's notes carry the local cache path, so the same data built on
  two machines gives two fingerprints; that is expected.
- **The loss series.** Book 2's outcomes are the four the analyst rates:
  `<product>_<source>_net.csv`, `_gross.csv`, and the delinquency files
  `<product>_<source>_delinquency-30-89_quarter-end.csv` and
  `_delinquency-nonaccrual_quarter-end.csv`, for the five products and three
  sources. The new measures (30+ to charge-off, the gaps, the minimum-payment
  share) are not loss series; Book 2 does not read them as outcomes.
- **Quarters left out as built.** `left-out.csv` beside the series files:
  `Product,Measure,Source,first,last,why`, one row per span a series left out
  (before its last break, or its latest quarters with no value), with the
  reason at the break. It is build-time only: the periods the analyst leaves
  out on Decide live in the saved workbook, and Book 2 takes those from a
  list the analyst keeps.
- **The typical yearly move**, if Book 2 compares against Book 1's: 1.4826 ×
  the median absolute deviation of every four-quarter change whose both ends
  are kept, deviation measured from the median change (`scale.py`). Book 1's
  lines use the picked source's quarters after the analyst's leave-outs, so
  Book 2's figure matches only where nothing was left out.
- **Reporting changes.** `config/reporting-changes.json` lists Call Report
  definition changes with the quarters they took effect, by product and
  measure; each series file's notes name the ones touching it. The December
  2024 revision moved about $56bn out of other consumer. Book 2 must not
  read those quarters as a driver's doing.
- **Names are a contract.** Quarter labels are `YYYYQn`; quarter-end dates are
  ISO (`2026-06-30`). Product, Measure and Source names are exactly as the
  series list spells them; Book 2 filters out the two combined products if
  it does not want them. Book 1 announces a rename before making one.

## Economic data Book 2 may use

Public, and either already read for the record or named there:

- Senior Loan Officer Opinion Survey (FRED `DRTSCLCC`, card standards;
  `STDSAUTO`, `STDSOTHCONS` for auto and other consumer from 2011; mortgage
  questions redrawn in 2015).
- Philadelphia Fed large bank card originations (score percentiles, share
  under 660, credit limits, APRs) and balances (utilization, minimum
  payments, purchase volume by score): `.../Y14/<yyyy>/Q<n>/<yy>Q<n>-*.csv`.
- FHFA National Mortgage Database aggregate statistics: origination terms
  from 1998, current LTV of the outstanding book from 2013, performance.
- NY Fed Household Debt and Credit (origination scores for auto and mortgage
  from 1999; the mortgage score switched to VantageScore 4.0 in 2026Q1).
- FRED macro series (unemployment, claims, house prices, gasoline, rates),
  with the key in an environment variable only.

## Your deliverable

A proposal first, then the build: which drivers, which outcomes, which
delays, with and without 2020-2023, and the direction states
(Decreasing/Stable/Increasing) as settings the analyst types, never
defaults. Report the denominator for every count, say what you could not
check, and send Book 1's owner a note of anything you need from Book 1
before building against it.

## The firm's rules (binding)

Public data only in the repository; the bank's own figures run on site and
are never committed. Never invent a threshold, weight, delay or cut-off:
refuse and say what is needed. Facts recorded, not inferred. Every figure
in a deliverable ties to a source the firm does not control, by script.
Workbooks are built by script, never hand-edited, no macros, Excel
(Microsoft 365). Words in a workbook state facts, in American spelling, and
give no advice.
