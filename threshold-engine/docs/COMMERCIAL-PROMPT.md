# Prompt: think through a commercial version of the consumer thresholds work

Hand this whole file to an agent. It is the brief, not a specification: the
agent's job is to come back with a proposal the firm can decide on, not to
build.

---

## Your job

The firm has built a working consumer credit workbook (threshold-engine,
October 2026) that sets risk-rating lines, from 1 Low to 5 High, for a
bank's consumer loan measures, and compares the bank with its peers. Work
out what a **commercial** version would be: which measures, which data,
where each comes from, how each would run through the same method, and
where the method breaks for commercial lending. Come back with a proposal
the firm can act on: a recommendation first, then what you checked, what
you could not, and the decisions that are theirs, each as a question they
can answer in one line.

Do not build anything yet. Do not invent a number, a threshold, a field name
or a data source's coverage: where you have not seen it, say so and say how
it would be checked.

## What already exists, and what it taught us

Read these first; they are the record, and the lessons in them are the
ones a commercial version will hit again.

- `threshold-engine/docs/WHAT-IT-DOES.md`, `books/FOR-A-TEAMMATE.md`,
  `books/README.md`, `LOG.md` (15 October 2026 entries): what the workbook
  is and how it was built and checked.
- `src/threshold_engine/scale.py`: the method, in 60 lines.
- `src/threshold_engine/peers/`: the public peer data (FDIC Call Reports),
  pro forma merger histories, and the SEC filing pull (`classes.py`).
- `docs/tie-out/`: two tie-outs to filed documents; the standard every
  figure is held to.
- `../edgar-crit-class-tracker/`: an existing tool in this repository that
  reads criticized and classified loans by class from each competitor's
  10-Q, the commercial half of competitor surveillance. Start from it.

### The method (what a commercial version would reuse)

Each measure's lines come from one history, picked per product and measure
(the bank's own, its peers', or every bank's):

| Line | Built from |
|---|---|
| 2 Moderate-Low | median − (Moderate-Low setting) × typical yearly move |
| 3 Moderate / 4 Moderate-High | median ∓ (width) × typical yearly move |
| 5 High | median + z × spread of levels (robust, so one crisis cannot inflate it) |

Every setting is the bank's to type; none has a default. The workbook
refuses rather than fill a gap. For example, it refuses when High would
begin beyond the worst quarter on record, and it says the number that would
fit. A period can be left out (a crisis, a structural break) only with a
reason. Decide shows every setting's range for the history picked
("What fits").

### What the consumer build found, which commercial will meet harder

1. **Losses are lumpy, and short histories cannot rate stress.** KeyBank's
   card history (34 quarters at first) never reached a level the method
   could call High. Commercial losses are lower-frequency and
   higher-severity than consumer: a measure with no stress in its history
   will be refused or rated on another source's lines. Decide which
   measures have the history to stand alone.
2. **A composite weighted by dollars is the big banks.** The peer group's
   card composite barely moved when the regionals were switched off,
   because the five large banks held about 94% of the balances. Commercial
   books are concentrated too. Offer a median (each bank counted once)
   beside the dollar-weighted composite, and say which the lines rest on.
3. **Acquisitions break histories; combine them pro forma.** A bank plus
   every bank it absorbed, before the deal, gives a continuous history
   (Huntington with TCF and Cadence, Capital One with Discover). The rule
   that leaves out a quarter whose book moved more than 25% still catches
   sales and reclassifications the merger record does not.
4. **Reporting changes look like credit events.** The 31 December 2024
   Call Report revisions moved about $56bn out of the industry's "other
   revolving credit plans" in one quarter. The agencies' notices tie those
   revisions to loans to nondepository financial institutions (NDFIs),
   which are commercial, so expect the same break in commercial
   categories. Verify the final form.
5. **A blended line hides what is in it.** "Other consumer" mixed student,
   unsecured and secured loans, so its rate said nothing about unsecured
   lending until each peer's 10-Q classes were read. Commercial has the
   same problem: C&I mixes asset-based, leveraged, middle-market and fund
   finance, and CRE mixes office, multifamily, construction and
   owner-occupied. A bank defines its own classes, and nothing makes it
   split them.
6. **Agents miss sentences.** Three agents reading 10-Qs recorded "not
   stated" for two facts the filings did state, and the tie-out's own
   search found them. Every quote is checked against the filed text by
   script, and every "not stated" is a search, not a zero.
7. **Holding company is not bank.** 10-Qs are the holding company's; Call
   Reports are the bank's. For commercial lending the gap can be larger
   (nonbank subsidiaries, broker-dealers, foreign offices).

### The firm's rules (binding, from the repository's CLAUDE.md and the record)

- Synthetic or public data only in the repository; the bank's internal
  figures are run on site, never committed. Masked or last-4 identifiers
  only.
- Never invent a threshold, weight or scale point; refuse and say what is
  needed. Facts recorded, not inferred. Report what was not checked as
  plainly as what was.
- Every figure in a deliverable ties to a source the firm does not control
  (a filing, an agency release), traced by script, with the denominator.
- The workbook is built by script from the source data, never edited by
  hand, with no macros. It is used in Excel (Microsoft 365) and ships as one
  file with a window.
- Words in the workbook state facts, calculations and rules, in American
  spelling, and give no advice.

## The data to evaluate

For each source: what it holds for commercial lending, how far back, how
often, its basis (bank or holding company, amortized cost or fair value,
quarter-end or flow), whether it is free, and what breaks it. **Check each
against the source itself; the notes below are leads, not facts.**

### Public, and already wired for consumer (extend first)

- **FDIC Call Reports** (api.fdic.gov, the cache `peers pull` fills): RC-C
  balances, RI-B charge-offs and recoveries (year to date), RC-N past due
  and nonaccrual, by loan category. The commercial categories to confirm
  include construction, multifamily, nonfarm nonresidential (owner-occupied
  and other), farmland, commercial and industrial, agricultural production,
  loans to depository institutions, NDFI loans and leases. Also RC-L,
  unused commitments: utilization matters more for commercial lines. Find
  each FDIC field name in the API's definitions; do not guess them.
- **SEC 10-Q and 10-K XBRL** (`peers classes-pull`): ASC 326 amortized
  cost by class and vintage, and **credit quality indicators**: pass,
  special mention, substandard and doubtful by class. That is the
  criticized and classified signal that leads charge-offs, and
  `edgar-crit-class-tracker` already reads it. Each bank tags its own
  members, so a stated mapping per bank, with quotes, is needed (as
  `config/peer-loan-classes.json` does for consumer).

### Public, not yet wired (evaluate)

- **Federal Reserve: charge-off and delinquency rates on loans and leases
  at commercial banks** (quarterly, all banks, by loan type, seasonally
  adjusted and not). A long industry history, possibly longer than the
  Call Report cache.
- **Senior Loan Officer Opinion Survey** (quarterly): standards and demand
  for C&I and CRE. A leading signal, not a loss rate; decide whether it
  rates or only informs.
- **Shared National Credit review** (agencies, annual): criticized shares
  of large syndicated credits, in aggregate.
- **FRED and other public macro series**: CRE price indices, high-yield
  spreads, business bankruptcies (U.S. Courts), industrial production.
  These are context for thresholds, not thresholds.
- **FR Y-9C** (holding company, quarterly, via FFIEC/NIC): the holding
  company view that 10-Qs report against.

### Paid (say what each would add and what it costs, before recommending)

CRE market data (CMBS delinquency, property prices, vacancy by property
type and metro) and default and recovery studies by rating. These are
named so their value can be weighed, not assumed.

### The bank's own (on site only; design the import, never see the data)

Risk rating (PD/LGD grade) by obligor and facility, criticized and
classified, watch list, rating migration, commitments and utilization,
industry (NAICS) and CRE property type, LTV and DSCR, nonaccrual and
charge-offs by segment. The consumer build's internal import layout
(`docs/INTERNAL-IMPORT.md`: segments, $ thousands, every column stated,
refused when not whole) is the pattern.

## Questions your proposal must answer

1. **Which measures?** Rank the candidates: net charge-off rate,
   nonaccrual rate, 90+ and 30–89 past due, criticized and classified
   share, migration, utilization, concentration, growth. Say for each
   whether there is enough history, with a stress period in it, for the
   method to set a High line; and for each that cannot, what its lines
   should rest on instead (industry, peer, a longer public series).
2. **Which segments?** How finely commercial should be cut (C&I, CRE by
   property type, construction, NDFI, leasing, agriculture), given what
   the public data splits and what peers disclose.
3. **Which peers, and weighted how?** The same 15, or commercial peers
   chosen by book mix? Dollar-weighted, median, or both?
4. **Which breaks?** Every known definition change, reclassification and
   acquisition in the commercial categories since 2006, with the quarter.
   Say how each would be handled: combined pro forma, left out with a
   reason, or labeled.
5. **How is each figure tied out?** One figure per source traced to a
   filed document, with the method the consumer tie-outs used.
6. **What would the workbook look like?** The same tabs (Decide, Summary,
   Peers, Peer loan classes, Thresholds), or something commercial needs
   that consumer did not: a criticized view, a concentration view, a
   migration matrix?

## What to hand back

One document:

1. **Recommendation first.** The measures, segments and sources to start
   with, and why, in under a page.
2. **The data table.** Per source: holds, history, frequency, basis, cost,
   breaks, and checked / not checked.
3. **Where the method breaks**, and what you propose for each.
4. **The decisions that are the firm's**, each as a one-line question with
   both outcomes and your recommendation.
5. **What you did not check**, as its own list.

Report the denominator for anything counted ("12 of 15 peers disclose
criticized C&I"). A source you could not reach is a COULD NOT, with the
reason, not a gap left unsaid.
