# What threshold-engine does, piece by piece (12 Oct 2026)

Written so it can be checked against the code. Each part names its file, what
goes in, what comes out, and what proves it. Where something was run only as a
one-off analysis rather than built into the tool, the last section says so.

**State of the code:** branch `threshold-engine`, draft pull request #426.
138 tests pass, run twice on 12 Oct 2026: once on the working copy, and once
on a fresh clone with a fresh Python environment and only the declared
dependencies (`pip install ".[test]"`). Nothing has been run on KeyBank's
internal data. Nothing internal is in the repository, by rule.

## The job

It sets the lines a separate scoring file uses to rate a measure 1 to 5 (Low,
Moderate-Low, Moderate, Moderate-High, High). It does not score a portfolio.
The bank: *"this tool we are creating is not meant to score everything. It is
meant to help assign thresholds which will score in another file."*

## What goes in

One CSV per product, with a `date,value` header. Lines starting with `#` are
notes. Quarterly. A value is the measure as the bank reports it: a TTM net or
gross charge-off rate, a delinquency rate, or anything continuous. With the
CSV goes a short description that has no defaults: name, unit, direction
(higher or lower is worse), smoothing, and whether a value at or below zero is
always Low.

The repository holds five public series to test and rehearse with: Federal
Reserve card and mortgage rates, and FDIC home equity and other consumer
rates, as filed and with auto added back (`tests/data/`).

## The workbook: the deliverable (`workbook.py`, command `workbook`)

One command reads every product and writes one Excel file. Python works out
the statistics once. The lines are live Excel formulas, so they move when the
bank changes a setting.

| Tab | What it holds | Live? |
|---|---|---|
| **Thresholds** | Per product: median kept, typical yearly move, worst kept, the four lines where scores 2–5 begin, the latest value, its score and rating, and a Check column that says why it refuses when it does | Yes |
| **Settings** (red) | The bank's judgements per product: two leave-out periods, each with a reason; Moderate's half-width; the Moderate-Low step; High's z; which score a value exactly on a line takes. Beside them, what the evidence suggests and why, and the temporary departures the data found | Inputs |
| **Assess** | For one product picked from a list: the five score bands shaded behind every quarter, left-out periods as a dark strip under the chart, a count of quarters in each score, and a **dial** for each setting showing the lines and counts at other values | Yes |
| **Chart** | Any combination of products on one scale, switched on and off, with one product's lines drawn | Yes |
| **Evidence** | Per product: each spell above the median with its robust z, how often history was that bad, its deepest dip, and the temporary departures (stretches that left their path and came back) | No, written at build |
| **Backtest** | How predictive a percentile scale would have been, rebuilt each quarter from only the history before it | No |
| **Glossary** | 33 terms: what each means and exactly how it is calculated | No |
| **Data** | Every series on one quarterly calendar, the quarters kept, and the working columns behind the live formulas | Yes |
| **Run** | Engine version, build time, every setting's starting value, each input file's SHA-256 fingerprint, and the leave-out decisions and reasons, live | Partly |

**The scale** (`scale.py` is the Python reference the formulas are tested
against):

| Score begins | Calculation |
|---|---|
| 2 Moderate-Low | median − step × typical yearly move |
| 3 Moderate | median − half-width × typical yearly move |
| 4 Moderate-High | median + half-width × typical yearly move |
| 5 High | median + z × spread of levels |

The median, the typical yearly move (1.4826 × the median absolute deviation of
every four-quarter change with both ends kept) and the spread of levels (1.4826
× the median absolute deviation of the quarters kept) are taken over the
quarters kept. For a measure where lower is worse, the signs swap.

**It refuses, in the Check column, when:** the median is at or below zero (for
a measure floored at zero); Moderate-Low would not begin below Moderate; High
would not begin beyond Moderate-High; High would begin beyond the worst quarter
kept (nothing could rate High); or Moderate-Low would begin at or below zero.

**What proves it:**
- The formulas are recalculated in the tests with the `formulas` engine, and
  must equal `scale.py` for every product: as built, after each kind of
  Settings change, and on every row of every dial.
- The workbook has been opened in Excel 16 on this machine, the settings
  changed by hand, and the results captured. That is how the blank chart, the
  missing axis labels, the slivered strip and the clipped headers were found.
- Every heading on Thresholds and Settings must have a Glossary entry, or a
  test fails.
- No formula may point at a row that doesn't exist, which Excel would report
  as a damaged file.
- Hand-made faults in each guard turn a test red. The log records each round
  and every survivor that needed a new test.

## The other commands

| Command | File | What it does | Note |
|---|---|---|---|
| `profile` | `profile.py` | Facts only, no judgement settings: distribution, every spell above the median, how often each upper percentile was reached, percentiles without the largest spell, where the latest value ranks | Consistent with the workbook |
| `evidence` | `evidence.py` | The statistics behind each judgement (robust z of each spell, return periods, deepest dips, temporary departures), then cutoffs under three scenarios and at stated half-lives | **The scenario cutoffs use the first scale, not the workbook's** |
| `backtest` | `backtest.py` | Rebuilds a percentile scale each quarter from only the history before it, and reports how well scores predicted the level and the change a stated number of quarters ahead, with and without recency weighting | Uses a percentile scale, not the workbook's |
| `cutoffs` | `engine.py` | The first engine: stress episodes, an outlier rule, and cutoffs from median to a fraction of the worst | **Superseded by the workbook's scale; gives different lines** |

## What was run outside the tool

All public data. Scripts are kept with the evidence pack at
`C:\Users\ajish\SATC-evidence\threshold-analysis-2026-10-06`. None of these is
part of the tool, and none is tested.

| Analysis | Kept as | Reproducible? |
|---|---|---|
| FDIC pulls: every filer, 2006–2026 (cards, mortgage, home equity, other consumer) and 1992–2026 (home equity, other consumer, auto); merger history | `pull_peers_2006.py`, `pull_peers_1992.py`, `pull_mergers_2006.py` and their data | Yes |
| Industry series built from the pulls, and the 2008 test | `analyse_peers.py`, `test_2008_rule.py` | Yes |
| Federal Reserve "other consumer" series, read from the charge-off release | `fedco/` (pages and output). The parsing was run inline, with no script kept | Partly |
| Peer gross and net rates, composite and page | `peers-gross-net/build_peers.py`, `make_peers.py` | Yes |
| Balance trends page | `peers-gross-net/make_balances.py` | Yes |
| KeyBank other consumer mix (Laurel Road), against the industry | Inline only. The numbers and method are in LOG.md, 7 Oct | **No script** |
| Card post-Covid normalisation, lagged rates, runoff | Inline only. Numbers in the conversation | **No script** |
| Growth without acquisitions | Inline only (`organic.json` kept in the scratch folder) | **No script** |
| Seven-option comparison of card scales, High before and after | Inline only, `make_high.py` for the page | Partly |
