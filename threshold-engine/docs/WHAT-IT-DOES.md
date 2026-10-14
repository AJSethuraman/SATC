# What threshold-engine does, piece by piece (12 Oct 2026, v1 round 2 built)

Written so it can be checked against the code. Each part names its file, what
goes in, what comes out, and what proves it. Where something was run only as a
one-off analysis rather than built into the tool, the last section says so.

**State of the code:** on `main` (pull requests #426 and #428), with the
walkthrough and the Assess redesign on their branches. 783 tests
pass (13 Oct 2026). Nothing has been run on KeyBank's internal data. Nothing
internal is in the repository, by rule.

**Walked, tied and ready for site (13 Oct 2026):** the walkthrough runs 30
steps in Excel 16 and reads 433 cells against expected answers, all as
expected (`docs/walkthrough/`, one PDF). 355 of those answers were written
and committed before Excel was first opened (6f3505d); the rest were added
after a run, each with its reason in LOG.md. One card line was
tied to the Federal Reserve's own table (`docs/tie-out/cards-moderate-line-2026-10-13/`).
The bank-machine checklist and its kit are `docs/ON-SITE-CHECKLIST.md` and
`tools/bank_kit.py`, dry-run on a clean Python with no add-ons.

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

The industry series are the FDIC's, every filer summed, for all five
products, charge-offs and delinquency (`data/industry/`, built 14 Oct 2026;
the firm: "FDIC for all", the Fed kept as a cross-check). The tests rehearse
with five older public series (`tests/data/`): Federal Reserve card and
mortgage rates, and FDIC home equity and other consumer rates.

## The workbook: the deliverable (`workbook.py`, command `workbook`)

One command reads every product and writes one Excel file. Python works out
the statistics once. The lines are live Excel formulas, so they move when the
bank changes a setting.

| Tab | What it holds | Live? |
|---|---|---|
| **Thresholds** | Per product: median kept, typical yearly move, worst kept, the four lines where scores 2–5 begin, the latest value, its score and rating, and a Check column that says why it refuses when it does | Yes |
| **Assess** (red; first, and it opens here) | Where the bank works, on one screen (Claude Design's layout, 13 Oct 2026). Top: the product picker, the latest quarter, value and score, and the Check, which says why it refuses and what to type to fix it. Left: the chart, five score bands behind every quarter, the latest quarter marked, left-out quarters as grey dots over a dark strip; under it, what the evidence says. Right: **Scores for** the product (lines and quarters in each score), **Your settings** (one row per product, the picked one highlighted, each row's own Check) and **Periods left out** (up to 12 rows from dropdowns of real quarters, a Status that says what is missing). Every input cell explains itself when selected. Below: **What happens if** (your lines against keeping every quarter, table and chart), what the lines rest on, what each setting does, and a **dial** per setting with its chart beside it | Inputs, and live |
| **Chart** | Any combination of products on one scale, switched on and off, with one product's lines drawn | Yes |
| **Evidence** | Per product: each spell above the median with its robust z, how often history was that bad, its deepest dip, and the temporary departures (stretches that left their path and came back) | No, written at build |
| **Backtest** | How predictive a percentile scale would have been, rebuilt each quarter from the history up to and including that quarter, never after | No |
| **Sources** | What each series' file says about itself, printed as written: what is measured, who is in it, the Call Report lines where they apply, numerator, denominator, basis, period and source. A key every file should give (measure, as of, basis, source) and this one does not is marked *Not stated in the file*, never filled in. The same for public files and the bank's template files | No |
| **Glossary** | 36 terms: what each means and exactly how it is calculated | No |
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
  change on Assess, and on every row of every dial.
- The workbook has been opened in Excel 16 on this machine, the settings
  changed by hand, and the results captured. That is how the blank chart, the
  missing axis labels, the slivered strip and the clipped headers were found.
- The walkthrough (13 Oct 2026) did every kind of change on Assess and every
  refusal in Excel 16 and reads 433 cells back against expected answers (355
  of them committed before the first run).
  It found the Assess chart drawing wrong bands for any product whose data
  starts after the calendar's first quarter, and a credit score's chart
  starting at zero; both fixed, each with a test.
- Every heading on Thresholds and Assess's inputs must have a Glossary entry,
  or a test fails, except four plain ones the test lists by name: Product,
  From, To, Reason.
- No formula may point at a row that doesn't exist, which Excel would report
  as a damaged file.
- Hand-made faults in each guard turn a test red. The log records each round
  and every survivor that needed a new test.

## The other commands

| Command | File | What it does | Note |
|---|---|---|---|
| `profile` | `profile.py` | Facts only, no judgement settings: distribution, every spell above the median, how often each upper percentile was reached, percentiles without the largest spell, where the latest value ranks | Consistent with the workbook |
| `evidence` | `evidence.py` | The statistics behind each judgement (robust z of each spell, return periods, deepest dips, temporary departures), then the lines under three scenarios and at stated half-lives | On the workbook's scale (`scale.py`) since 12 Oct |
| `backtest` | `backtest.py` | Rebuilds a percentile scale each quarter from the history up to and including that quarter (never after), and reports how well scores predicted the level and the change a stated number of quarters ahead, with and without recency weighting | Uses a percentile scale, not the workbook's |
| `compare` | `compare.py` | Two series of one measure matched by calendar quarter (a series dated at the quarter's first day meets one dated at its end): the quarters both hold, the mean and largest difference, and with `--every` one line per quarter. Facts only, no tolerance | The cross-check: FDIC industry series against the Federal Reserve's (the firm, 13 Oct: "FDIC for all", the Fed kept as a cross-check) |

## The window (`launcher.py`, `Thresholds.pyw`)

Double-click `Thresholds.pyw`. Steps down the left: **Series** (the CSVs, each
with its product label), **Measure**, **Settings** (the scale's starting
values), **Build** (where the workbook goes; Run writes it and opens it). Every
field starts empty and Run stays off, naming what is missing, until each is
stated. It refuses what the builder would refuse (a label Excel would read as a
formula, two labels differing only in capitals, nan, a file without the
`date,value` header) before it builds. **Peers** pulls and builds the peer
workbook, through `peers/run.py`, the same function `peers pull` and `peers
build` call, so the two cannot drift. Every rule starts empty. Pull and Build
run on a worker thread with a status line; a second press while one runs is
refused.

**What proves it:** 61 tests (113 with their cases) drive every decision the
window makes without a display; three open a real window, one of them
pressing Run.

## Synthesis (`synthesis.py`, command `synthesize`)

The firm, 13 Oct 2026: an industry perspective, a competitive one and an
internal one, synthesized into reasonable thresholds. For one product and
one measure, each perspective proposes the four lines where ratings 2 to 5
begin, and the firm names which perspective each line is taken from
(`--leads`, four words, no default):

| Perspective | Its lines |
|---|---|
| internal | the workbook's scale on KeyBank's own history. A calm history (2014 on, the pandemic its only stress) can place lines 2 to 4 and refuses line 5, saying so |
| industry | the same scale on the industry's history, which holds 2008-10, carried to the internal level (`--translation "median ratio"`: times the median of internal / industry over the quarters both hold; or `none`) |
| peers | each peer's median over the internal quarters, the stated percentiles of those (`--peer-percentiles`, four, rising), carried to the internal level by the median of internal / KeyBank filed |

The chosen lines must still run in order; if not, it refuses and names the
pair. Beside them it states the latest internal quarter's rating and how
many peers KeyBank's filed median is worse than: facts, no alarm level.
`peers build` writes each peer's own charge-off series to
`SERIES-DIR/banks/` for `--peer NAME=FILE`.

## Peers (`peers/`, commands `peers pull` and `peers build`)

Public FDIC Call Report data for KeyBank and a 16-bank roster
(`config/peers.json`), so the bank can see where it sits.

| Part | What it does |
|---|---|
| `peers pull` (`fdic.py`) | Fetches every filer's quarter into a cache folder, only quarters not already there. Refuses a quarter the FDIC has not published (0 filers), a page count that does not match the API's own total, or a row that arrives twice. With `--mergers`, the FDIC's acquisition record, classified; a change code nobody has classified stops the pull and is named |
| `peers pull --delinquency yes` | Also the 30-89, 90+ accruing and nonaccrual fields per product. A cache pulled without them is refused by name for a delinquency build |
| `peers build` (`books.py`, `analyses.py`, `delinquency.py`, `peers_workbook.py`, through `run.py`) | Reads the cache only. Per bank, product and quarter: TTM gross and net charge-off rates, with a window left out when the book moved more than the stated jump, when that quarter's recorded acquisitions brought in at least the stated acquisition share of the book, or when it was under the stated minimum. Where a bank absorbed another under the same parent, the absorbed bank's year-to-date, which the survivor's filing repeats, is taken off, so no dollar counts twice (the industry series included). Writes the peer workbook and, per product, `date,value` CSVs the main workbook reads: pack composite, pack median, KeyBank, industry, and each peer's own book under `banks/`. A year-to-date that restarts mid-year under a new parent (push-down accounting) is read as that quarter's flow, not differenced. Other consumer's balance is RC-C 6.b + 6.d; card quarters before 2010 are labelled as excluding securitized cards |

With `--delinquency yes` it also writes, per product, measure and basis,
the delinquency CSVs for the pack composite, KeyBank and the industry: 150
for five products. Every rule is a required flag (`peers build --help`
lists 24).

**Delinquency** (`peers/delinquency.py`): five measures, `30-89`, `90+
accruing`, `nonaccrual`, `90+ incl. nonaccrual` and `30+ incl. nonaccrual`,
each on two bases: the quarter-end rate (numerator over balance, one filing)
and the four-quarter average (the mean of four quarter-end rates). The
jump rule applies to the average, which spans four filings, and not to a
quarter-end rate; a bank it blanks is left out of the pack composite's
average too. A blank field is "not filed", never 0. The first quarter
each field was filed is recorded in the module.

**The peer workbook:**

| Tab | What it holds | Live? |
|---|---|---|
| **Pack** (red) | Which peers are in (Include), the product, Peer A and Peer B (any peer, or best/worst in pack), how best and worst are ranked, how many banks a composite needs | Inputs |
| **Peers** | Gross and net charts: pack band (10th–90th, 25th–75th), pack composite, KeyBank, Peer A, Peer B | Yes |
| **Balances** | Each bank's book as an index, with and without acquisitions | No |
| **Lagged** | A year's losses over the book lent two years earlier (the runoff question) | No |
| **Normalisation** | How far each rate moved between two years (post-Covid) | No |
| **Mix** | KeyBank's move against the industry's (the Laurel Road question) | No |
| **Delinquency** | Pickers for product, measure and basis; the pack band, composite, KeyBank, Peer A and Peer B, from the same Include cells as Peers | Yes |
| **DelinquencyData** | Every bank, product, measure and quarter: numerator, balance, rate, four-quarter average, why a value is missing, and whether the composite's average left the bank out | No |
| **Glossary**, **Data**, **Run** | Terms, including **Left out, and why**: one row per reason a number is kept out, saying why and where each is recorded; every bank's flows and rates with why a quarter was left out; sources, pull dates, fingerprints, rules | — |

**What proves it:**
- `books.py` matches the earlier build to 4 decimals on 9,984 values (every
  bank, product and quarter) and on the composite.
- The industry series matches the repository's other consumer CSVs (as filed,
  and with auto added) on all 135 quarters, at most 0.00005 apart. That check
  needs the evidence pack, so it is run by hand and is not in the suite.
- The live formulas are recalculated with `formulas` and must equal the Python.
- Each module was reviewed by two agents who tried to break it. Every finding
  was reproduced, fixed, and given a test that fails without the fix.
  Mutation runs found no surviving mutant that can be reached.
- **Tied to a filing:** KeyBank card 90+ accruing 2026Q2, read from
  DelinquencyData in Excel, is 9,346 ($000), the same as RC-N line 5.a column
  B on KeyBank's filed Call Report (page and XBRL). Balance and rate tie.
  `docs/tie-out/keybank-card-90plus-2026-10-12/`.
- Run end to end on 12 Oct 2026 against the real cache. Pull: 82 quarters
  cached, 0 fetched. The live merger record matched the test fixture for all
  16 roster banks. Build: 4½ minutes. Opened in Excel 16: every chart draws,
  and no cell holds a formula error. The CSVs it writes load straight into
  the `workbook` command.

Round 2 end to end (12 Oct): pull with `--delinquency yes --refresh`, 82
quarters in 6 minutes; build 11½ minutes, 180 CSVs; the Delinquency chart
opened in Excel under three settings with no formula error.

The pack composite's four-quarter average leaves out a bank whose own
average the jump blanked (usually mid-acquisition), as the band does, so both
are built from the same banks (the bank's decision, 12 Oct). Each composite
row names them (`avg4_left_out`), the CSV notes list them by bank and
quarter, and DelinquencyData marks them in its last column. The Glossary's
**Left out, and why** rows list every reason a number is kept out, one row
each, and where each is recorded.

## Templates for internal data (`templates.py`, command `template`)

Internal measures are run on site; nothing internal comes back. Seven
templates: `wapd`, `refreshed-score` (lower is worse), `epd`,
`student-loans`, `other-consumer-ex-student`, `card-rewards`,
`card-non-rewards`. `template write KEY OUT.csv` writes an empty file whose
`#` notes ask what the bank must state (measure, numerator and denominator
or the score's scale, as-of, basis, source, who prepared it and when), plus
a checklist. `template check KEY FILE.csv` lists every problem at once and
exits 2: a note missing or still a placeholder, any column besides `date`
and `value` (so no account-level data can travel), a date not a quarter-end,
a gap or a repeat, a value not a finite number, a % outside 0–100, a score
outside the stated scale, fewer than 9 quarters. A checked file is an
ordinary series for `workbook` and the window.

**What proves it:** each template is written, filled with synthetic values,
checked and built through the workbook in a test; each refusal has a test
with its exact words.

## What was run outside the tool

All public data. These were first run as one-off scripts, kept with the
evidence pack at `C:\Users\ajish\SATC-evidence\threshold-analysis-2026-10-06`.
On 12 Oct 2026 the bank said *"all of it"*, so every row marked "in the tool"
is now built in and tested. The last two rows are still one-offs.

| Analysis | Kept as | Reproducible? |
|---|---|---|
| FDIC pulls 2006–2026 and 1992–2026; merger history | Now `peers pull`. The evidence-pack scripts remain as the earlier record | Yes, in the tool |
| Peer gross and net rates, composite, best and worst | Now `peers build`, Peers tab | Yes, in the tool |
| Balance trends, growth without acquisitions | Now the Balances tab | Yes, in the tool |
| KeyBank other consumer mix (Laurel Road) | Now the Mix tab | Yes, in the tool |
| Card post-Covid normalisation, lagged rates | Now the Normalisation and Lagged tabs | Yes, in the tool |
| Industry series (other consumer as filed and with auto) | Now `peers build --industry-combined` | Yes, in the tool |
| Federal Reserve "other consumer" series, read from the charge-off release | `fedco/`. Parsed inline, with no script kept | Partly |
| Seven-option comparison of card scales, High before and after | Inline only, `make_high.py` for the page | Partly |

*12 Oct 2026: the first engine (`engine.py`, `episodes.py`) and its `cutoffs`
command were retired, on the bank's decision, so the tool has one scale.*
