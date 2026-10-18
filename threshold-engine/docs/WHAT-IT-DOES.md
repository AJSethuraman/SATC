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

One dashboard tab, **Peers** (red), and the tabs it reads. Since 14 Oct 2026
(the firm: *"it is annoying to flip between stuff for peer analysis - can't they
all exist on one tab with filters like a dashboard at the top?"*); before, each
view was a tab of its own.

| Tab | What it holds | Live? |
|---|---|---|
| **Peers** (red) | At the top, yellow cells: product, charge-off rate (net or gross), Peer A and Peer B (any peer, or best/worst in pack), what the charts show (all quarters, or the last 80, 48 or 20), the delinquency measure and basis, a Yes/No under every peer for whether it is in the pack, and how best and worst are ranked and how many banks a composite needs. Under them: the headline numbers (KeyBank, the pack, KeyBank's rank, the industry), the charge-off chart (pack band, composite, KeyBank, Peer A, Peer B, industry), the delinquency chart, the book-size chart (each bank's book indexed, the pack's band and median), lagged rates with the pack total, how far each rate moved, the mix against the industry, and every bank's row. Switching a bank off moves every view with a pack in it. | Yes |
| **Workings** (hidden) | The live helpers every view reads, and the per-year values the lagged and mix views pick from | Yes |
| **DelinquencyData** | Every bank, product, measure and quarter: numerator, balance, rate, four-quarter average, why a value is missing, and whether the composite's average left the bank out | No |
| **Glossary**, **Data**, **Run** | Terms, including **Left out, and why**: one row per reason a number is kept out, saying why and where each is recorded; every bank's flows, rates and book index with why a quarter was left out; sources, pull dates, fingerprints, rules and each bank's acquisition quarters | — |

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

**In the workbook (14 Oct 2026, `synthesis_tab.py`).** The firm agreed the
synthesis belongs on Assess, *where each colour starts*. The `workbook`
command takes, per series, the same inputs, and the series' own `--series`
file is the internal one:

    --synthesis "Credit card=industry:FILE;filed:FILE;peers:FOLDER-OR-PATTERN"
    --translation "Credit card=median ratio"
    --peer-percentiles "Credit card=20,40,75,95"
    --leads "Credit card=internal,internal,internal,industry"

`industry` is required, `filed` and `peers` are optional (`peers`: a folder
means every `.csv` in it; a pattern such as `banks/credit-card_*_net.csv`
the files it matches; each peer is named by its file). A series given
`--synthesis` needs `--translation` and `--leads`, and `--peer-percentiles`
when it has peers; each is stated for that series, and there is no set that
applies to every series, because a lead that is right for cards (whose
industry history holds 2008) was not chosen for a series whose does not. Any
of them missing, or given for a series without `--synthesis`, is refused by
name. Without any synthesis flag the command and the workbook are as before.

The **Synthesis** tab (red, beside Thresholds) has a block per series: the
four lines from internal, industry and peers side by side, **Taken from
(yours)** per line, **Peers at percentile (yours)** per line, **Industry
carried by (yours)**, each a yellow cell starting from what the command said;
the **chosen line**; the latest quarter rated on the chosen lines; the
**competitive check** as a sentence; and a **Check** that says OK or why it
refuses, in `synthesis.py`'s words: a line taken from a view that does not
have it (naming the line, the view and why), lines out of order (naming the
pair and their values), peers without KeyBank's filed series, percentiles
that are not four numbers from 0 to 100 or do not rise, a lead or translation
typed outside its list. Below that, what each view rests on (quarters held,
the ratios and over how many quarters) and each peer's median.

Every number is a formula and follows **Your settings on Assess**. The
internal lines **are** Thresholds' lines, so periods left out on Assess move
them; the translations and the peer window use every quarter the internal
series holds, as `synthesis.py` does. The industry, filed and peer series are
smoothed as the measure says, like the internal ones. Their `#` notes are
printed on Sources and their SHA-256 on Run, each under its own name
(*Credit card · industry*, *· KeyBank filed*, *· peer NAME*), and Run shows
the choices live.

On **Assess**, under What each setting does, *Where each colour starts* shows
the series in B5: the three views and the chosen line for each of the four
lines, the latest rating on them and the Synthesis Check, with a link to the
tab. A series built without a synthesis says so there.

**What proves it** (`tests/test_workbook_synthesis.py`): the workbook is
recalculated with the `formulas` engine and every candidate, chosen line,
rating and Check must equal `synthesis.synthesize` on the same inputs: all
internal but High from the industry; a line led by peers; translation none;
percentiles changed on the tab; Your settings changed on Assess; a period
left out (internal moves, the others do not); lower is worse; smoothing; a
latest value exactly on a chosen line under worse and better; and each
refusal. Nine hand-made faults in the tab's formulas each turn a test red. The command's refusals when a flag is missing. Opened in Excel
16 on the public card files (LOG.md, 14 Oct 2026).

## Peers (`peers/`, commands `peers pull` and `peers build`)

Public FDIC Call Report data for KeyBank and a 16-bank roster
(`config/peers.json`), so the bank can see where it sits.

| Part | What it does |
|---|---|
| `peers pull` (`fdic.py`) | Fetches every filer's quarter into a cache folder, only quarters not already there. Refuses a quarter the FDIC has not published (0 filers), a page count that does not match the API's own total, or a row that arrives twice. With `--mergers`, the FDIC's acquisition record, classified; a change code nobody has classified stops the pull and is named |
| `peers pull --delinquency yes` | Also the 30-89, 90+ accruing and nonaccrual fields per product. A cache pulled without them is refused by name for a delinquency build |
| `peers build` (`books.py`, `analyses.py`, `delinquency.py`, `peers_workbook.py`, through `run.py`) | Reads the cache only. Per bank, product and quarter: TTM gross and net charge-off rates, with a window left out when the book moved more than the stated jump, when that quarter's recorded acquisitions brought in at least the stated acquisition share of the book, or when it was under the stated minimum. Where a bank absorbed another under the same parent, the absorbed bank's year-to-date, which the survivor's filing repeats, is taken off, so no dollar counts twice (the industry series included). Writes the peer workbook and, per product, `date,value` CSVs the main workbook reads: pack composite, pack median, KeyBank, industry, and each peer's own book under `banks/`. A year-to-date that restarts mid-year under a new parent (push-down accounting) is read as that quarter's flow, not differenced. Other consumer's balance is RC-C 6.b + 6.d; card quarters before 2010 are labelled as excluding securitized cards |

**Products.** The consumer five (credit card, mortgage, home equity, other
consumer, auto) and, from 16 Oct 2026, six commercial ones on the command
line: C&I, construction, multifamily, nonfarm nonresidential, and its
owner-occupied and other splits (`books.COMMERCIAL`, every field from
`docs/commercial-2026-10/research-fdic.md`). They are built by the same
rules, with one difference: a blank commercial field is not filed, never
0, so a bank-quarter with one is left out of the bank's book (`a field of
the product is not filed`) and of the industry, and the splits begin in
2007Q1 rather than as years of zeros. Each commercial series' notes say what
the product is and what the industry leaves out. The window still offers
the consumer five only.

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

## Reporting changes (`reporting_changes.py`, `config/reporting-changes.json`)

The firm, 16 Oct 2026: *"Definitely mark reporting changes."* Every change
to the Call Report's definitions or forms is labelled on every series it
touches, in the quarter it took effect.

| Part | What it does |
|---|---|
| The registry | One entry per change: first and last quarter it took effect (2024Q4 to 2025Q2 for the NDFI and margin-loan revision, reported on a best-efforts basis), the products and measures it touches, the Call Report items (for commercial later), one sentence of what changed, and its sources with their addresses. Twelve changes, each marked verified in `docs/commercial-2026-10/` (on main). Every key required; a malformed entry is refused by name, every problem at once |
| `peers build --reporting-changes FILE` | Required. Every series file gets a `# reporting-change:` note for each change touching its product and measure within its quarters, so the Sources tab shows it. A change the product's own definition note already says (securitized cards before 2010, auto inside other consumer until 2011) points to that note instead of saying it twice. The Peers charts (charge-offs, delinquency) draw a diamond on the pack composite in each quarter one took effect for the product and measure picked |
| (the registry's events) | The same file's `events` (the 2020 drawdowns and the PPP loans in C&I; the firm, 17 Oct 2026) are labelled the same way under `# event:`, shown on Sources as Event, listed under Events on the Reporting changes tab, never called a reporting change and not drawn on the charts |
| `peers build --stated-acquisitions FILE\|none` | Required. The acquisitions the FDIC record cannot see (config/stated-acquisitions.json, each with its filing and the products it brought, with the list's source): the windows holding one are left out for its acquirer, with their own reason, in the products it brought and no others (charge-offs, the delinquency average, 30+ to charge-off); an unknown product is refused, and a product the source does not settle is listed, so left out; a malformed entry or a certificate not on the roster is refused by name; `none` states that none is read. In a book, `peers.stated_acquisitions` (null: none is read) |
| (a series continues across a labelled change) | Where the jump alone left a bank's own windows out, every move in a quarter a reporting change names for the product and measure, and only a change whose own source says it can step a balance in one quarter (`steps_balance` in the registry, question 20; an event never does), the file runs across them instead of starting after them: they are not written, and a `# left-out:` line (Continues across, on Sources) declares them. Every reader accepts that gap and no other (the firm, 17 Oct 2026) |
| The book's `reporting_changes` key | Required: the registry, or null for a book with no Call Report series (refused with a peers section). Given to the peers build, and written whole on the **Reporting changes** tab (after Sources), each heading in the Glossary. Decide's chart draws a diamond along the top of the zones in each quarter a change took effect for the row shown, read from its series files' notes |

**What proves it:** `tests/test_reporting_changes.py` (the registry and each
refusal, the notes on affected and unaffected series, Sources, Decide's marker
recalculated with `formulas`, the tab); `tests/test_peers_cli.py` (the notes
on the files `peers build` writes); `tests/test_peers_workbook.py` (the Peers
markers recalculated). Not opened in Excel.

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

## Internal data (`internal.py`, command `internal`)

KeyBank's own figures by product and segment, one file, run on site only.
The layout and every rule are in `docs/INTERNAL-IMPORT.md`.

| Command | What it does |
|---|---|
| `internal template OUT.csv` | The empty file, every note `[STATE: ...]`, and an empty exclusions file beside it |
| `internal check FILE` | Every problem at once, each naming its line, exit 2: a note or segment description not stated, a missing column, fewer than two of gross, net and recoveries (the third is worked out; three that disagree are refused), past due not cumulative or above the balance, a repeat, a gap, a column named like an identifier, text in a further column |
| `internal series FILE --out-dir DIR` | Per product and segment, net and gross charge-off rates over four quarters, and 30+, 60+ and 90+ rates at quarter-end and as a four-quarter average, by the public series' method. Each file's notes copy the file's own as-of, source, entity and basis, for the Sources tab |
| `internal pull` | The Call Report fields the reconciliation reads, into a cache of its own |
| `internal reconcile` | Per quarter and comparison, the filed balance and charge-offs, less the named exclusions, against internal; the remainder within the stated tolerance or not. Reads the cache only. Delinquency is not reconciled (the buckets differ); the notes give the nearest public measure |

**What proves it:** `tests/test_internal.py`, made-up figures only: each
refusal pinned by its line; the four-quarter rate against a hand-worked
example; the window rule; a written series built through the workbook; a
reconciliation on a small synthetic Call Report cache where named exclusions
explain one gap and another is flagged; refusal without a tolerance. Not yet
run on KeyBank's data, nor against a real cache.

## What was run outside the tool

All public data. These were first run as one-off scripts, kept with the
evidence pack at `C:\Users\ajish\SATC-evidence\threshold-analysis-2026-10-06`.
On 12 Oct 2026 the bank said *"all of it"*, so every row marked "in the tool"
is now built in and tested. The last two rows are still one-offs.

| Analysis | Kept as | Reproducible? |
|---|---|---|
| FDIC pulls 2006–2026 and 1992–2026; merger history | Now `peers pull`. The evidence-pack scripts remain as the earlier record | Yes, in the tool |
| Peer gross and net rates, composite, best and worst | Now `peers build`, Peers tab | Yes, in the tool |
| Balance trends, growth without acquisitions | Now the book-size view on the Peers tab | Yes, in the tool |
| KeyBank other consumer mix (Laurel Road) | Now the mix view on the Peers tab | Yes, in the tool |
| Card post-Covid normalisation, lagged rates | Now the lagged and how-far-it-moved views on the Peers tab | Yes, in the tool |
| Industry series (other consumer as filed and with auto) | Now `peers build --industry-combined` | Yes, in the tool |
| Federal Reserve "other consumer" series, read from the charge-off release | `fedco/`. Parsed inline, with no script kept | Partly |
| Seven-option comparison of card scales, High before and after | Inline only, `make_high.py` for the page | Partly |

*12 Oct 2026: the first engine (`engine.py`, `episodes.py`) and its `cutoffs`
command were retired, on the bank's decision, so the tool has one scale.*
