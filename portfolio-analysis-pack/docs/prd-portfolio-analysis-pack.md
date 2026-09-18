# PRD: Portfolio Analysis Pack

**Status:** Draft · **Owner:** AJ Sethuraman · **Last updated:** 2026-09-18

Grilled 18 September 2026 from the handover *"Portfolio Analysis Pack
Generator"*. Every decision below was put to the firm as a question and
answered; the two that touched the record (C9, C11) are ruled on in
`canon/CONVICTIONS.md` under *Rulings by project*. This document is the spec an
agent builds from with no further questions. Where a fact could not be reached
from the build container it is marked **⚑ CONFIRM** and listed in §10.

---

## 1. Problem

A credit-review consultant at a bank is asked a question of one shape, over and
over: *loans where this is true — do they go bad more often than loans where it
is not, and is that real or something else in disguise?* Today that question is
answered by hand in a fresh spreadsheet each time, and the same five mistakes
recur:

- a trend in how often a field was *captured* is read as a trend in behaviour;
- small loans go bad more, and a flag that mostly picks small loans is reported
  as if the flag itself predicted the outcome;
- seasoned and unseasoned originations sit in one rate table;
- a rate is printed without the count it rests on or a range around it, so a
  bucket of 40 loans reads as confidently as one of 4,000;
- the method note is written by hand and is stale the moment a bucket edge moves.

The first question is on a small-business book: the borrower's **stated
personal income exceeds the business's reported sales**. Income is stated and
effectively never verified; sales is also borrower-reported; no expense data
exists, so there is no true business DSCR. Two underwriting decisions point
opposite ways off the two fields (stated income → DTI → borrower qualifies;
reported sales → line assignment → smaller line), so the ratio measures
*disagreement between two decisions*, not outside income. The bank already
holds a field that contradicts a material, unverified input, in some share of
the book, and nothing in the process reacts to it. That last sentence is a
finding whether or not any performance effect is found.

The same shape of question will be asked of **consumer** books next (stated
income against a bureau estimate, on auto or card), so nothing in the tool may
know what a sector, a NAICS code or a small business is.

## 2. Solution

A Python tool, run at the bank's desk on the loan extract as it comes out of the
system, that takes the extract plus a short question file and emits **one
self-contained Excel workbook** containing a fixed six-step analysis (the
*ladder*) and a closing control observation. Python does all the work over the
loans; the workbook holds only a small **count cube** (loans and events per
cell) and derives every rate, interval, gap, monotonicity flag and the
survives/collapses word by **live formula** from it. The reviewer changes the
confidence level or the interval method on the `_config` tab and the pack
recalculates. Bucket edges, bands and the window are rebuild knobs, marked as
such. Every formula has a Python twin and the workbook itself shows whether
they agree. Two builds from the same input are byte-identical. The method
notes are generated from the config and the counts, never written by hand.

## 3. Goals & Non-Goals

**Goals**

- The income-versus-sales question builds from Key's extract and a ten-to-forty
  line question file, at Key's desk, with Python + `openpyxl` + `PyYAML` only.
- The same tool answers a consumer question with a different question file and
  **zero code changes** (a test proves it).
- Every rate carries its denominator, its event count and an interval. Thin
  data announces itself; nothing is gated on statistical power.
- The step-4 word (survives / collapses / unknown / no crude effect) is
  computed by formula from the cube and recomputes when the confidence level
  moves.
- Same input → identical bytes. Diffable.
- Every formula written is checked against Python at test time, and the
  workbook carries its own check (`N of N agree`) for a reader with no Python.
- Each tab carries its provenance and its generated method note.

**Non-Goals / Out of scope** (ruled 18 Sep 2026 unless noted)

- **Doors two and three** (threshold/boundary; residual profiling) and **sweep
  mode**. C11 was *struck for this project*: v1 is the ladder plus door one.
  They keep a config slot and a plug-in seam (§6.1, §6.12) and are logged in
  `BACKLOG.md` §6c. *(The overlap the handover flagged was checked:
  `credit-review-os` Mode B has a binary FRINGE flag and a fringe-vs-core fail
  rate, not a bucketed curve with intervals. Door two is not a rebuild, and is
  not free either.)*
- **Vintage curves.** A fixed window with seasoning exclusion is v1. Logged.
- **A GUI.** Config is YAML; `pack list` / `pack validate` are the only front
  door.
- **Loan-level rows in the workbook.** The firm: *"I don't want a situation
  where excel is the limiting factor because there's too much data."* The
  workbook holds the cube only.
- **A PII guard.** The firm, 18 Sep 2026: *"stop worrying about PII. It is all
  on Key's desk and I already have PII flowing through my work."* No name/TIN
  scan is built. (The cube carries no loan-level rows in any case; the only
  loan-level output is the hygiene refusal file, at the desk.)
- **Repairing data.** The tool refuses on dirt; the analyst cleans the extract.
- **Two outcomes in one pack.** One outcome per config; a second outcome is a
  second config file and a second workbook.
- **numpy / scipy / statsmodels / scikit-learn** anywhere on the build path.
  The desk has none of them. Regression and tree are plain Python.
- **Scoring, monitoring, dashboards, or any LLM in the data path.**
- **Native charts beyond the gradient blocks** (steps 3 and 4).
- **Excel-side bucket edges** (the fine-grid variant). Edges are a rebuild.
- **Permutation importance.** There is no ensemble; a single tree's split
  order is the artifact. The handover's rule applies only if ensembles arrive.
- **Any domain-specific list, mapping or transform in the code** — a sector
  table, a score band, a product family. The firm, 18 Sep 2026: *"i don't
  want to have a sector list - this is supposed to be generic... it should be
  adaptable."* Grouping a column is a generic operation the config asks for
  (§6.15), and any mapping is supplied in the config, never shipped.

## 4. User Stories

Actors: **the reviewer** (the firm, at Key's desk); **the reader** (a credit
officer or committee member opening the workbook with no Python); **a question
author** (the firm, writing the next config, possibly for consumer loans); **a
maintainer/agent** (building or extending the tool).

1. As the reviewer, I want to point the tool at Key's extract as exported and
   see every column with its type, null share, distinct count and sample
   values, so that I can write the question file without reshaping the data.
2. As the reviewer, I want the question file to name Key's columns directly in
   each slot, so that the config *is* the mapping and there is no second layer.
3. As the reviewer, I want `pack validate` to stop with the exact line to add
   when a required slot is missing (the flag line, a column's known-when, the
   existing-control line), so that nothing is guessed on my behalf.
4. As the reviewer, I want the build to refuse on dirt (zero or negative values
   in a rule field, non-numeric text, unparseable dates, duplicate loan
   numbers, values outside a plausible range I gave) and write the offending
   loan numbers to a file, so that I clean the extract rather than the tool
   silently reshaping the base.
5. As the reviewer, I want blanks treated as a finding, not dirt: counted by
   origination quarter on the capture tab and excluded from the ratio base,
   so that a field that did not exist in 2019 shows up as exactly that.
6. As the reviewer, I want loans younger than the window at the as-of date
   excluded from every rate table and counted as *unseasoned* on the capture
   tab, so that seasoned and unseasoned originations never share a rate.
7. As the reviewer, I want the outcome to be any yes/no per loan — an event
   date the pack censors at the window, a flag the bank already windowed and
   I declare as such, or a measure taken at the as-of date such as
   outstanding ÷ commitment above a line — so that charge-off, 60+ DPD and
   utilization are each a config, not a code change.
8. As the reviewer, I want prevalence split into two series — how often both
   fields are present, and how often the flag fires among loans where they are
   — so that a capture trend and a flag trend are never merged.
9. As the reviewer, I want the gradient across magnitude buckets of the rule,
   each bucket with its rate, its interval, its gap from the unflagged base in
   percentage points **and** as a multiple, and a printed monotonicity read,
   so that "2.3x" and "+0.8 points" are both in front of me.
10. As the reviewer, I want step 4 to repeat the gradient inside every band of
    every confounder and print one word — survives, collapses, unknown, or no
    crude effect — from the crude odds ratio beside the Mantel-Haenszel pooled
    one, with the threshold on the `_config` tab, so that the headline is a
    rule I can see and move, not a judgement buried in prose.
11. As the reviewer, I want `pack suggest` to propose band cut points from the
    data — equal-count by loans, equal-count by events, nearest round numbers
    — each with loans and events per band and thin bands flagged, and the
    outcome-driven cut printed as information only, so that I choose bands
    with the counts in view and never stratify on the outcome by accident.
12. As the reviewer, I want to keep more than one band scheme per confounder
    and see step 4 under each, so that a finding that depends on where the
    cut fell is visible as such.
13. As the reviewer, I want step 5 to show flagged-versus-unflagged rates with
    intervals across every dimension I list, sorted so concentration is
    obvious, so that "all in one sector" and "spread evenly" read differently.
14. As the reviewer, I want two regressions side by side — flag plus controls,
    then plus the confounders — with odds ratios, intervals, the event count
    and events-per-parameter printed above, so that whether size explains the
    flag is one comparison.
15. As the reviewer, I want a depth-2-to-3 tree printed as plain rules with
    the loans, events and rate in each leaf, so that interactions surface as
    leads.
16. As the reviewer, I want the closing observation generated from the config
    alone for a contradiction-type question — the share of the book where the
    two fields disagree, that the input is unverified, and what (if anything)
    reacts to it today — emitted regardless of what steps 3–6 found.
17. As the reader, I want the cover to state the question, the answer in three
    lines, the number of loans and the number of events, and `N of N formula
    checks agree`, so that I can read the pack without reading the tabs.
18. As the reader, I want to change the confidence level or switch Wilson to
    Clopper-Pearson on one tab and watch every interval and the step-4 word
    recompute, so that I can test the finding's sensitivity myself.
19. As the reader, I want every tab to carry the source file, its hash, the
    row counts, the parameters, the generator version and the run date, so
    that a number can be traced to the file that produced it.
20. As the reader, I want each tab's method note to say which fields, which
    rule, which window, which exclusions, which counts — generated, not
    typed — so that the note cannot be stale.
21. As a question author, I want a `filter` slot so one extract serves several
    packs (one product each), with the filter and the count it left recorded
    in the method note.
22. As a question author, I want the rule to be `ratio` or `difference`, so
    that a question naturally in dollars needs no code.
23. As a question author, I want a consumer question (stated income versus
    bureau estimate, auto, 60+ DPD, score and LTV bands, state and term as
    controls) to build with no code change, and a test that proves it.
24. As a maintainer, I want a test that fails if any column name or domain
    word (income, sales, NAICS, charge-off) appears anywhere in the package
    code, so that the tool stays domain-free by construction; the example
    configs are data, not code, and are the only place such words live.
25. As a maintainer, I want synthetic fixtures with planted answers — a 2.0x
    effect, a null, an effect that vanishes under stratification — and a
    mutation tool that proves each test can go red, so that the suite
    validates something.
26. As a maintainer, I want two builds from identical input to be byte-
    identical and the only difference between two run dates to be the
    provenance cells, so that a pack is diffable.
27. As a maintainer, I want the pure-ASCII bundle to rebuild the pack in a
    clean environment with only `openpyxl` and `PyYAML`, byte-identical to a
    build here, so that transmission through the bank's DLP boundary is
    provably the same deliverable.
28. As a maintainer, I want LibreOffice to open every built pack and render
    every chart to an image that is read before shipping, so that "opened with
    zero dialogs" is never mistaken for "readable".

## 5. Requirements

Priority: [P0] must · [P1] should · [P2] nice.

**Config and input**

1. [P0] The question file is YAML with the schema in §6.1. `pack validate`
   refuses any file missing a required slot and prints the missing line in
   the file's own syntax.
2. [P0] Every column the config touches appears in `fields:` with `known:
   at_origination | later`. A `later` column is refused anywhere but
   `outcome`. Missing → refuse, naming the column.
3. [P0] `rule.fires_when` is required (`{op, value}`, op ∈ `> >= < <= == !=`).
   `existing_control` is required (`none` or free text). Neither is defaulted.
4. [P0] Input is CSV (stdlib) or XLSX (openpyxl, first sheet or `--sheet`).
   Column names are used verbatim. Dates are detected per §6.2: typed XLSX
   date cells need nothing; text dates are parsed by the one common pattern
   that fits every value, and that pattern is recorded on `_provenance`;
   when two patterns both fit, the build refuses and prints the candidates
   with a sample value so the reviewer picks one by adding
   `population.date_format`. The line is therefore optional, and when
   present it is applied as given.
5. [P0] `pack inspect DATA` prints, per column: inferred type (integer,
   decimal, date-like, text, mixed), null share, distinct count, five sample
   values, and the date pattern that parses the most date-like values.
6. [P0] `population.filter` (optional) is `{COLUMN: [values]}`; rows not
   matching every entry are dropped before anything else and the drop is
   recorded (rows read → rows after filter) on `_provenance` and in every
   method note.
7. [P0] Hygiene (§6.3) runs in `validate` and `build`; failure exits 2, writes
   `hygiene-<name>.csv` (loan id, column, value, reason) beside the output, and
   builds nothing. Blanks are not a hygiene failure.

**Population, seasoning, outcome**

8. [P0] `--asof YYYY-MM-DD` is required on `build`. Months on book is whole
   calendar months from origination to as-of (§6.4). Loans with months on
   book < `window_months` are excluded from every rate table and counted as
   *unseasoned* on `1_Capture`, by quarter.
9. [P0] Outcome takes exactly one of three forms. **Event date:**
   `{date_field}` — event iff date ≤ origination + window months; later
   events are non-events in-window; blank is non-event. **Bank-windowed
   flag:** `{field, op, value, basis: windowed_by_bank}` — event iff the
   predicate holds; the pack does not window it and the method note says
   so. **Snapshot at as-of:** `{measure, op, value, basis: snapshot_at_asof}`
   where `measure` is a column or a derived `{kind: ratio|difference,
   field_a, field_b}` using the rule's own machinery (utilization =
   outstanding ÷ commitment) — event iff the predicate holds on the value
   at the as-of date; the method note states that months on book vary
   across the base from the window to the oldest seasoned loan, and the
   decomposition by origination year is where that variation is read.
   Seasoning exclusion applies identically to all three.
10. [P0] The word for the outcome in every note and header is
    `outcome.label` from the config. The package contains no outcome name.

**The ladder**

11. [P0] **Step 1, capture.** For every field the rule uses, by origination
    quarter: loans, blank, zero, out-of-range (if `plausible` given, else
    the row reads `not checked`), and the band counts for every confounder
    scheme. Unseasoned count per quarter. Denominator on every row.
12. [P0] **Step 2, prevalence.** By origination quarter, two series that are
    never merged: capture rate = loans with both rule fields present ÷ all
    seasoned loans in the quarter; flag rate = loans where `fires_when`
    holds ÷ loans with both fields present. Each with its Wilson/CP interval.
13. [P0] **Step 3, gradient.** Buckets are `rule.buckets` edges applied to the
    rule value, left-closed `[a, b)`, with an open bottom bucket below the
    first edge and an open top bucket at or above the last. Per bucket:
    loans, events, rate, interval, gap from the unflagged base in percentage
    points, ratio to the base, and the base row itself. A monotonicity read
    over buckets with n > 0: `monotonic increasing`, `monotonic decreasing`,
    or `not monotonic` on point estimates, plus the count of adjacent pairs
    whose intervals do not overlap.
14. [P0] **Step 4, stratified.** For each confounder and each of its schemes:
    the step-3 block repeated inside every band; a 2×2 (flagged/unflagged ×
    event/non-event) per band; the crude odds ratio with a Woolf interval;
    the Mantel-Haenszel pooled odds ratio with the Robins-Breslow-Greenland
    interval; the share of crude log-odds kept; and the printed word per
    §6.7. All by formula.
15. [P0] **Step 5, decomposition.** For every dimension in `decompose_by`:
    per level, flagged loans/events/rate, unflagged loans/events/rate, gap in
    points, ratio, intervals on both rates; rows sorted by flagged events
    descending then label; a `share of all flagged events` column so
    concentration is read off the tab.
16. [P0] **Step 6, model.** Two logistic regressions (§6.9): M1 = flag +
    controls; M2 = M1 + every confounder not already a control (a duplicate
    is skipped and the skip printed). Per term: odds ratio, interval,
    coefficient, standard error. Above each table: loans, events, number of
    estimated coefficients, events per parameter, and a warning line when
    EPP < 10. A depth-`model.tree_depth` (default 3) CART tree (§6.10)
    printed as rules with loans, events, rate and lift per leaf. Values only,
    with a note saying so.
17. [P0] **Step 7, control observation.** Emitted iff `rule_type:
    contradiction`, from the config and step-2 counts alone, regardless of
    steps 3–6: the share of seasoned loans with both fields present where the
    rule fires; that `field_a` is unverified (from `drives`/wording); and the
    `existing_control` line rendered as "nothing acts on it" only when the
    value is `none`.

**Workbook**

18. [P0] Tabs, in order: `Cover`, `1_Capture`, `2_Prevalence`, `3_Gradient`,
    `4_Stratified`, `5_Decomposition`, `6_Model`, `7_Control`, `_cube`,
    `_config`, `_method`, `_check`, `_provenance`. House style from the copied
    `keybank_style.py`; no hard-coded fill or font in a builder.
19. [P0] `_config` holds the live knobs as named cells: `CONF` (confidence,
    default 0.95), `METHOD` (data-validation list `Wilson`, `Clopper-Pearson`;
    default from config), `SURV_T` (default 0.5). Rebuild knobs (edges,
    bands, window, filter, fires_when) are listed read-only under a
    `rebuild to change` band.
20. [P0] Every rate, interval, gap, ratio, crude and pooled OR, monotonicity
    read and step-4 word is a formula over `_cube` cells and the named knobs.
    Newer functions are written with the `_xlfn.` prefix (`_xlfn.NORM.S.INV`,
    `_xlfn.BETA.INV`); bare spellings render `#NAME?` (tested 18 Sep 2026 in
    LibreOffice 24.2; openpyxl 3.1.5 does not list either function).
21. [P0] `_check`: one row per formula cell — sheet, cell, formula text,
    Python's value, a reference to the live cell, tolerance, and
    `=IF(ABS(live-python)<=tol,"OK","MISMATCH")` (string compare for words).
    `Cover` shows `=COUNTIF(_check!G:G,"OK")&" of "&COUNTA(_check!G:G)&"
    formula checks agree"`. A desk build prints `formula check: not run here
    (no engine); Excel verifies on open` and never `passed`.
22. [P0] `_provenance`: source filename, SHA-256 of the input bytes, rows
    read, rows after filter, rows after hygiene (always equal, or no build),
    seasoned rows, config name and SHA-256, generator version, as-of, run
    date. Every results tab repeats the file name, hash, seasoned count,
    event count, generator version and run date in its header band.
23. [P0] `_method`: the notes for every step, generated from `wording.yaml`
    templates (§6.11) filled with config values and counts. No sentence is
    assembled in code. Each results tab shows its own note beneath its
    header band.
24. [P1] `3_Gradient` and each step-4 block carry a native column chart of the
    bucket rates with custom error bars read from the interval cells.

**Determinism, validation, transmission**

25. [P0] Same config + same input bytes + same `--asof` + same `--run-date` →
    byte-identical `.xlsx` (zip member timestamps pinned, `docProps`
    created/modified pinned to the run date, all iteration orders sorted per
    §6.13). `--run-date` defaults to `--asof`; the clock is never read.
26. [P0] Every formula's Python twin is computed at build time and written to
    `_check`. The test suite recalculates every fixture with the `formulas`
    engine and fails on any MISMATCH.
27. [P0] `pack bundle CONFIG` emits a single pure-ASCII script embedding the
    package and the config (never the data). On the target,
    `python build_pack.py --data X --asof D` rebuilds byte-identically with
    `openpyxl` + `PyYAML` only. The `formulas` engine is not bundled.
28. [P0] The package contains no domain vocabulary (§6.14); a test enforces it.
29. [P0] `pack suggest` per §6.6.
30. [P1] Build time under five minutes at 100,000 loans on a desk machine;
    the build prints its elapsed time per step.

## 6. Implementation Decisions

Folder `portfolio-analysis-pack/`, package `analysis_pack`, console script
`pack`, Python ≥ 3.10, runtime dependencies `openpyxl>=3.1`, `PyYAML>=6.0`;
test extras `pytest`, `formulas>=1.2`. Nothing imports across folders;
`keybank_style.py` is copied in (the two existing copies are byte-identical,
checked 18 Sep 2026). Module shape (behaviour, not paths): `config`
(schema, validation, the missing-line messages), `ingest` (CSV/XLSX → typed
rows, date parsing), `hygiene`, `population` (filter, seasoning, outcome),
`ladder` (steps 1–7 producing the cube and the Python twins), `stats`
(Wilson, Clopper-Pearson, Woolf, Mantel-Haenszel/RBG, IRLS logistic, CART),
`workbook` (openpyxl writer, formulas, check tab, charts, `workbook_bytes`),
`notes` (wording templates → method notes), `synth` (fixture generator),
`bundle`, `cli`.

### 6.1 Config schema

The first instance, complete. Column names are Key's; the ones shown are
placeholders the reviewer replaces after `pack inspect`.

```yaml
name: stated_income_vs_sales
schema_version: 1
rule_type: contradiction          # contradiction | threshold | missingness | hunch
                                  # v1 builds `contradiction` only; the others are
                                  # accepted by the parser and refused by build with
                                  # "door not built in this version".
population:
  loan_id: LOAN_NBR
  origination_date: ORIG_DT
  date_format: "%m/%d/%Y"         # required; `pack inspect` proposes, never applies
  filter:                         # optional; {COLUMN: [allowed values]}
    PRODUCT: [SBL_LOC, SBL_TERM]
fields:                           # every column the pack touches
  STATED_INC: {known: at_origination, plausible: [1000, 50000000]}
  RPT_SALES:  {known: at_origination, plausible: [1000, 500000000]}
  ORIG_AMT:   {known: at_origination}
  NAICS_CD:   {known: at_origination, derive: {kind: prefix, length: 2}}
  ENTITY_TYP: {known: at_origination}
  CO_DT:      {known: later}
rule:
  kind: ratio                     # ratio (a ÷ b) | difference (a − b)
  field_a: STATED_INC
  field_b: RPT_SALES
  fires_when: {op: ">", value: 1.0}
  buckets: [0.5, 1.0, 2.0, 5.0]   # edges; [a, b); open bottom and top
outcome:
  label: charge-off
  date_field: CO_DT
  # or:  field: DPD60_FLAG_24M, op: "==", value: 1, basis: windowed_by_bank
  # or:  measure: {kind: ratio, field_a: OUTSTANDING, field_b: COMMITMENT},
  #      op: ">=", value: 0.9, basis: snapshot_at_asof, label: drawn to the line
window_months: 24
confounders:
  - name: revenue_band
    field: RPT_SALES
    schemes:                      # one or more; step 4 shows each
      by_loans: [250000, 1000000]
      round:    [100000, 500000, 2000000]
  - name: line_band
    field: ORIG_AMT
    edges: [50000, 150000, 500000] # shorthand for one scheme named `edges`
  - name: entity_type
    field: ENTITY_TYP             # categorical column; no edges
controls:
  - {name: origination_year, derived: origination_year}   # always available
  - {name: loan_size, field: ORIG_AMT, as: log}           # log | linear | bands: <scheme edges>
  - {name: industry, field: NAICS_CD}                    # categorical on the derived 2-character group
decompose_by: [industry, line_band, origination_year]
existing_control: none            # required: none | "text naming what reacts today"
drives:                           # narrative only; feeds the step-7 note
  field_a: "DTI — borrower qualifies"
  field_b: "line assignment — smaller line"
model:
  tree_depth: 3                   # 2 or 3
  min_leaf_events: 10
  min_leaf_loans: 100
intervals:
  confidence: 0.95
  method: wilson                  # wilson | clopper_pearson
survives_threshold: 0.5
```

A consumer instance differs only in values — it ships as
`configs/examples/stated_vs_bureau_income_auto.yaml`:

```yaml
name: stated_vs_bureau_income_auto
schema_version: 1
rule_type: contradiction
population: {loan_id: ACCT, origination_date: FUND_DT, date_format: "%Y-%m-%d",
             filter: {PRODUCT: [INDIRECT_AUTO]}}
fields:
  STATED_INC:     {known: at_origination, plausible: [6000, 2000000]}
  BUREAU_INC_EST: {known: at_origination, plausible: [6000, 2000000]}
  FICO:           {known: at_origination, plausible: [300, 850]}
  LTV:            {known: at_origination, plausible: [0.1, 2.0]}
  TERM_MO:        {known: at_origination}
  STATE:          {known: at_origination}
  DPD60_DT:       {known: later}
rule: {kind: ratio, field_a: STATED_INC, field_b: BUREAU_INC_EST,
       fires_when: {op: ">", value: 1.5}, buckets: [1.0, 1.5, 2.0, 3.0]}
outcome: {label: "60+ days past due", date_field: DPD60_DT}
window_months: 12
confounders:
  - {name: score_band, field: FICO, edges: [620, 680, 740]}
  - {name: ltv_band, field: LTV, edges: [0.8, 1.0, 1.2]}
controls:
  - {name: origination_year, derived: origination_year}
  - {name: term, field: TERM_MO, as: linear}
  - {name: state, field: STATE}
decompose_by: [state, score_band, origination_year]
existing_control: "income reasonableness test above 150% of the bureau estimate"
model: {tree_depth: 3, min_leaf_events: 10, min_leaf_loans: 100}
intervals: {confidence: 0.95, method: wilson}
survives_threshold: 0.5
```

Validation order and messages: schema → required slots (each missing slot
prints the YAML line to add, e.g. `existing_control: none   # or the control
that reacts today`) → every referenced column exists in `fields:` → every
`fields:` column exists in the data → `known: later` used only in `outcome`
→ `plausible` low < high → confounder schemes strictly increasing → bucket
edges strictly increasing → `rule_type` buildable. Refuse at the first
group, listing every failure in that group.

### 6.2 Ingest and typing

CSV via `csv` with `utf-8-sig`; XLSX via openpyxl read-only. Numeric parse:
strip `$`, `,`, whitespace, parentheses as negative; `%` refused (a rate
column is declared as a decimal). A blank, `NA`, `N/A`, `NULL`, `null`,
`None`, `-` after strip is **blank**. Anything else that fails `Decimal` is
**non-numeric** (hygiene). Dates: a typed XLSX date cell is taken as is.
Text dates are tried against eight common patterns (`%m/%d/%Y`, `%Y-%m-%d`,
`%d/%m/%Y`, `%m/%d/%y`, `%Y%m%d`, `%d-%b-%Y`, `%b %d, %Y`,
`%Y-%m-%dT%H:%M:%S`), per date column, over every non-blank value. Exactly
one pattern fitting every value is a fact: it is used and written to
`_provenance` (`ORIG_DT: %m/%d/%Y, 40,000 of 40,000 parsed`). Two or more
fitting every value (every day ≤ 12, so month-first and day-first both
parse) is ambiguous: the build refuses, prints each candidate with the same
sample value read both ways (`03/04/2021 → 4 March or 3 April`), and names
the line to add (`population.date_format`). No pattern fitting every value:
the values that fail the best pattern are **unparseable** (hygiene) and the
refusal file lists them. `pack inspect` prints the same per-column result.
When `population.date_format` is present it is applied as given and the
detection is skipped.

### 6.3 Hygiene (refuse, report, never repair)

Runs after filter, before seasoning. Failures, each with loan id, column,
value, reason: (a) rule field zero or negative; (b) rule field non-numeric;
(c) any numeric field non-numeric; (d) origination date or outcome date
unparseable; (e) duplicate `loan_id`; (f) value outside `plausible` where
given; (g) `field_b == 0` for `kind: ratio` (already (a)); (h) origination
date after as-of. Blank is never a failure. On any failure: exit 2, write the
CSV, print counts per reason and the file path, build nothing. Where no
`plausible` is given for a field the capture tab prints `range check: not
run` for that field — a third answer, never a pass.

### 6.4 Seasoning and outcome

`months_on_book = (asof.y − o.y)·12 + (asof.m − o.m) − (1 if asof.d < o.d)`.
Seasoned iff `months_on_book ≥ window_months`. Window end = origination plus
`window_months` calendar months, day clamped to month end. Event (date form)
iff outcome date is not blank and ≤ window end; an outcome date before
origination is hygiene failure (d′). Event (bank-windowed flag) iff the
predicate holds; blank is non-event. Event (snapshot) iff the predicate
holds on the measure's value at as-of; a blank measure is non-event and is
counted as blank on `1_Capture`; a derived ratio with a zero denominator is
hygiene failure (a). Loans paid off inside the window without an event are
non-events; the method note says so. For a snapshot outcome the note also
says months on book range from the window to the oldest seasoned loan.

### 6.5 The cube

`_cube` is one row per cell: `block_id` (e.g. `s3.gradient`, `s4.revenue_band.
by_loans.band2`, `s5.industry.44`), dimension labels, `n`, `events`,
and for step 4 the four 2×2 counts. Results tabs reference cube cells by
address (never SUMIFS over the cube), so the cube is the readable source of
every number and every formula is short. Rows are written in the order the
tabs consume them.

### 6.6 `pack suggest`

For each confounder with a numeric field (and for `--field COL` on demand):
`by_loans` (edges at the 33rd/67th and 25th/50th/75th percentiles of the
non-blank seasoned values), `by_events` (edges chosen so each band holds an
equal share of events, walking the sorted values), `round` (each `by_loans`
edge snapped to the nearest of 1, 2, 2.5, 5 × 10^k). For each: bands with
loans, events, rate, and `thin` where events < 10. Then, marked **not for
step 4 — chosen on the outcome**: the single split of that field that most
reduces Gini impurity on the outcome (the tree's first cut), with the two
rates. Output is text and a YAML snippet ready to paste under `schemes:`.

### 6.7 Formulas (Excel and Python twin)

Named knobs `CONF`, `METHOD`, `SURV_T`; `Z = _xlfn.NORM.S.INV(1-(1-CONF)/2)`
on `_config`. With `X` events, `N` loans:

- Rate: `=IF(N=0,"",X/N)`.
- Wilson (Wilson 1927; Brown, Cai & DasGupta 2001, *Stat. Sci.* 16:101):
  `lo = ((X/N)+Z^2/(2*N))/(1+Z^2/N) - Z/(1+Z^2/N)*SQRT((X/N)*(1-X/N)/N+Z^2/(4*N^2))`,
  `hi` with `+`.
- Clopper-Pearson (Clopper & Pearson 1934, *Biometrika* 26:404):
  `lo = IF(X=0,0,_xlfn.BETA.INV((1-CONF)/2,X,N-X+1))`,
  `hi = IF(X=N,1,_xlfn.BETA.INV(1-(1-CONF)/2,X+1,N-X))`.
- Switch: `=IF(METHOD="Wilson", wilson, cp)`, wrapped `IF(N=0,"",…)`.
- Gap (points): `rate − base_rate`; ratio: `IF(base_rate=0,"",rate/base_rate)`.
- Crude OR over a block's totals `a,b,c,d` (flagged events, flagged
  non-events, unflagged events, unflagged non-events):
  `=IF(OR(a=0,b=0,c=0,d=0),"not estimable",(a*d)/(b*c))`; Woolf interval
  `EXP(LN(OR) ± Z*SQRT(1/a+1/b+1/c+1/d))`.
- Mantel-Haenszel over bands k with totals `n_k` (Mantel & Haenszel 1959,
  *JNCI* 22:719): `OR_MH = SUMPRODUCT(a,d/n)/SUMPRODUCT(b,c/n)`. Variance of
  `LN(OR_MH)` (Robins, Breslow & Greenland 1986, *Biometrics* 42:311) with
  `P=(a+d)/n`, `Q=(b+c)/n`, `R=a*d/n`, `S=b*c/n`:
  `SUMPRODUCT(P,R)/(2*SUM(R)^2) + (SUMPRODUCT(P,S)+SUMPRODUCT(Q,R))/(2*SUM(R)*SUM(S)) + SUMPRODUCT(Q,S)/(2*SUM(S)^2)`;
  interval `EXP(LN(OR_MH) ± Z*SQRT(Var))`. All helper columns live on the
  step-4 block beside the 2×2 rows.
- Share of crude log-odds kept: `kept = LN(OR_MH)/LN(OR_crude)`.
- **The step-4 word** (one cell per block):
  `no crude effect` if the crude interval contains 1.0 (or crude is not
  estimable); else `collapses` if `kept < 1 − SURV_T`; else `survives` if the
  pooled interval excludes 1.0; else `unknown`.
- Monotonicity over buckets with `N>0`: with helper `d_i = rate_i − rate_{i−1}`:
  `IF(SUMPRODUCT(--(d<0))=0,"monotonic increasing",IF(SUMPRODUCT(--(d>0))=0,"monotonic decreasing","not monotonic"))`;
  non-overlap count `SUMPRODUCT(--(lo_i > hi_{i−1}))+SUMPRODUCT(--(hi_i < lo_{i−1}))`.

Python twins use the same arithmetic in `Decimal`-free floats; tolerance on
`_check`: relative `1e-9` for counts, rates, gaps, ratios and ORs; absolute
`1e-6` for interval bounds (engine differences in `BETA.INV`); exact for
words. The `formulas` engine reproduces Wilson, Clopper-Pearson and
`NORM.S.INV` to five decimals against textbook values (x=3, n=10:
CP 0.06674–0.65245, Wilson 0.10779–0.60322; checked 18 Sep 2026).

### 6.8 Ordering and labels

Category levels ordered by loans descending then label ascending; quarters
ascending as `2021Q3`; buckets in edge order with labels `< 0.5`,
`0.5 – 1.0`, …, `≥ 5.0`; bands likewise from their edges, or the column's
own values for categoricals. Blank category → level `(blank)`, always last.

### 6.9 Logistic regression (plain Python)

Design: intercept; the flag (0/1); each control and (M2) confounder. A
categorical enters as dummies against a reference level = the level with the
most loans (printed). A continuous field enters as `ln(x)` when `as: log`
(refused if any x ≤ 0 → build stops naming the field), as `x` when
`linear`, or as band dummies when `bands`. `origination_year` is categorical.
Fit by iteratively reweighted least squares: `β ← β + (XᵀWX)⁻¹Xᵀ(y−p)`,
Gauss-Jordan inversion with partial pivoting, stop at `max|Δβ| < 1e-8` or 25
iterations. Standard errors from the diagonal of `(XᵀWX)⁻¹`; odds ratio
`exp(β)`, interval `exp(β ± z·se)` with `z` from `intervals.confidence`.
Non-convergence, a singular matrix, or any `|β| > 15` → the model prints
`not estimable (separation or singular design)` with the term(s) implicated,
and the cover's model line reads `unknown`. Events per parameter = events ÷
(coefficients excluding intercept); warning line when < 10 (Peduzzi, Concato,
Kemper, Holford & Feinstein 1996, *J. Clin. Epidemiol.* 49:1373). Budget:
the config's controls + confounders; the tool does not select.

### 6.10 Tree (plain Python)

CART, Gini impurity, binary splits, features = the rule value (numeric) plus
every M2 predictor. Numeric split candidates are midpoints between sorted
distinct values (at most 200 candidates per feature, taken at quantiles when
more); categorical candidates are one level versus the rest, in §6.8 order.
A split is taken only if both children satisfy `min_leaf_loans` and
`min_leaf_events`; ties broken by feature order then candidate order. Depth
≤ `tree_depth`. Output: each leaf as a rule path (`RPT_SALES < 100,000 and
ratio ≥ 2.0`), loans, events, rate, lift = rate ÷ overall rate. No
importance score of any kind is printed.

### 6.11 Method notes and cover wording

`wording.yaml` holds every sentence as a template with `{placeholders}`;
`notes` fills them. Code never concatenates prose (SOFTWARE-TENETS S10). The
cover's three answer lines are chosen from finite variants keyed by the
computed states (monotonicity read, step-4 word per confounder, M2 flag
interval position). Step 7's sentence has two variants keyed on
`existing_control == none`.

### 6.12 Doors two and three: the seam, not the build

`rule_type` is parsed for all four values. `ladder` exposes one entry point
per door taking `(config, population) → (cube_rows, twins, notes)`; v1
registers `contradiction` only and `build` refuses the others with the message
in §6.1. Door two's natural home is a `threshold` entry that reuses the
bucket-with-interval block with finer edges and a bunching count; door three
a `hunch` entry that fits M1 on accepted drivers across all vintages and
profiles residuals. Neither is written in v1.

### 6.13 Determinism

`workbook_bytes` re-packs the saved zip with member timestamps `(1980,1,1)`
and `dcterms:created`/`modified` set to `--run-date` (same technique as
`credit-review-os`, which pins to an epoch; here the run date is the
provenance value and is injected). Every dict iterated for output is sorted
per §6.8; the tree and IRLS are deterministic given input order, and input
rows are sorted by `loan_id` before any step. Random numbers are used only in
`synth`, from an explicit seed. No `datetime.now()` anywhere in the package;
a test greps for it.

### 6.14 Domain-free by construction

A test reads every column name and every `name:` label from the example
configs, plus the words `income, sales, naics, charge, chargeoff, charge-off,
dti, fico, ltv, utilization, sector, sba, small business`, and fails if any
appears (case-insensitive, whole word) in any `.py` under the package. There
is no exception: derivations (§6.15) are generic operations and carry no
vocabulary. Synthetic fixtures use `field_a`, `field_b`, `amount`,
`category_1..n`, `code_1..n`, `outcome_date`.

### 6.15 Derived groupings (generic; the tool ships no list)

A field in `fields:` may carry `derive:`, and the derived value is what every
step sees for that field. Two kinds, chainable in a list, applied in order:

- `{kind: prefix, length: N}` — the first N characters of the value, as
  text. Blank stays blank. A non-blank value shorter than N is hygiene
  (a malformed code), refused with the loan ids.
- `{kind: map, groups: {label: [value, ...]}, other: label}` or
  `{kind: map, groups_file: path.csv, other: label}` (two columns: value,
  group; path relative to the config). A value in no group takes the `other`
  label and is counted on `1_Capture`. If `other` is absent and an unmapped
  value occurs, the build refuses and lists the values — a grouping the
  config did not supply is never invented.

So rolling an industry code to its two-digit group is `prefix 2`; merging
several groups into one (or attaching titles) is a `map` the reviewer writes
if they want it, and the tool never contains that mapping. The same two
operations cover a ZIP to a ZIP3, a product code to a family, a state to a
region. Every derivation used is named in the method note with its kind and
parameters, and the `map`'s group count.

### 6.16 CLI contract

```
pack inspect  DATA [--sheet NAME]
pack validate CONFIG --data DATA [--asof D]         # schema, columns, hygiene
pack suggest  CONFIG --data DATA [--field COL] [--asof D]
pack build    CONFIG --data DATA --asof D [--run-date D] [-o OUT.xlsx]
pack synth    --out DIR [--seed 20260918] [--loans 40000] [--effect 2.0]
              [--confounded] [--null]                # data + matching config
pack bundle   CONFIG [-o build_pack.py]
pack list     [DIR]                                  # configs and their validity
```

Exit codes: 0 OK · 1 error · 2 refused (validation or hygiene). JSON status
on stdout, human summary on stderr (the suite's convention). `build` prints
per-step elapsed seconds and, at the end, the formula-check line from §5.21.

### 6.17 Bundle

Pure ASCII, gzip+base64, embeds the package and the config; takes `--data`
and `--asof` on the target. Never embeds data. A test rebuilds a fixture pack
in an empty directory with a `PYTHONPATH` holding only `openpyxl` and `PyYAML`
and compares SHA-256 to the direct build.

## 7. Testing Decisions

- **Seam 1 — the build on synthetic fixtures, recalculated.**
  `build_pack(config, rows, asof, run_date) -> bytes` on `synth` output, then
  a `Recalc` helper (the `formulas` engine; prior art
  `credit-review-os/tests/recalc.py`) reads cells by `(sheet, address)`. All
  six fixture classes live here.
- **Seam 2 — the CLI on files.** `main([...])` against temp CSV/YAML for every
  refusal message and exit code, `inspect` and `suggest` output, and the
  bundle rebuild in an empty directory (prior art
  `credit-review-os/tests/test_bundle.py`).
- **Harness, not CI — open it.** `tools/render.py` runs LibreOffice headless
  over every built fixture pack: `.xlsx → .pdf`, one PNG per chart, and a
  scan of the PDF text for `#NAME?`, `#DIV/0!`, `#VALUE!`. Its output is
  looked at before a version ships. (Calc had to be installed in the build
  container on 18 Sep 2026; `soffice` alone reports "source file could not be
  loaded" without it. Record that in the README's setup.)
- **Mutation tool.** `tools/mutation_check.py` (prior art
  `credit-suite/tools/mutation_check.py`): each mutation neuters one behaviour
  and names the tests that must go red — `wilson-z-one` (z := 1), `cp-alpha`
  (α := 1−CONF), `mh-swap` (numerator/denominator), `seasoning-off`,
  `leakage-allowed`, `fires-inverted`, `xlfn-prefix-dropped`,
  `check-tolerance-huge`, `sort-off`. A green baseline is demanded first and
  the tree is restored byte-for-byte after.

**What a good test proves — the six fixture classes**

1. **Planted effect.** `synth --effect 2.0` (seed fixed; ~40,000 loans, ~300
   events, confounder-neutral by construction). M1 and M2 odds ratios on the
   flag within ±0.3 of 2.0 **and** both intervals contain 2.0; the gradient
   reads `monotonic increasing`; step 4's word is `survives` for every
   confounder.
2. **Null.** `synth --null`. Both flag intervals contain 1.0; step 4's word is
   `no crude effect`; the cover's answer lines are the no-effect variants;
   step 7 still prints the contradiction share.
3. **Planted confounder.** `synth --confounded`: `field_b` small ⇒ flag fires
   ⇒ outcome driven by `field_b` only. Crude OR > 1.5 with interval excluding
   1.0; pooled OR interval contains 1.0; word `collapses`; M2's flag interval
   contains 1.0 while M1's does not.
4. **Mutation.** `tools/mutation_check.py` exits 0 (every mutation was caught
   by its named tests) and a CI job runs it.
5. **Determinism.** Two builds → identical SHA-256; a build with a different
   `--run-date` differs only in `_provenance`, the header bands and
   `docProps`.
6. **Dual-path.** For every fixture: every formula cell has a `_check` row;
   recalculated value equals the twin within tolerance; the recalculated
   cover reads `N of N formula checks agree` with N = the row count.

Also at seam 1: seasoning (a loan 23 months on book is unseasoned at 24; the
count appears by quarter); capture vs flag series never share a cell; `later`
field refused as a control; `existing_control: none` vs text changes only the
step-7 sentence; the consumer example config builds on renamed synthetic
columns with no code change (S8: generated, not hand-written); no domain word
in the package (§6.14); no `datetime.now()` in the package; every `_xlfn.`
function is prefixed.

> **Data handling.** Real extracts never enter this repository. Every fixture
> is synthetic with generic column names. The only loan-level artifact the
> tool writes is the hygiene refusal CSV, at the desk. No PII scan is built,
> on the firm's instruction (§3).

## 8. Success Metrics

- The income-versus-sales pack builds from the synthetic 40,000-loan fixture,
  opens in LibreOffice with zero error cells, and the recalculated cover reads
  `N of N formula checks agree`.
- The consumer example config builds with zero code changes (test).
- `mutation_check.py` reports every mutation caught.
- Build time printed under five minutes at 100,000 synthetic loans.
- The bundle rebuilds byte-identically with only `openpyxl` and `PyYAML`.

## 9. Milestones

- **M1 (tracer bullet):** config + validate → ingest → filter → hygiene →
  seasoning/outcome → steps 1–3 → workbook with knobs, cube, formulas,
  `_check`, `_provenance`, `_method` → `pack build` → seam-1 planted-effect
  test on the gradient → determinism test → render harness.
- **M2:** steps 4, 5, 7; MH and the word; `suggest`; `inspect`; refusal
  messages; consumer example; domain-free test.
- **M3:** step 6 (IRLS, tree, EPP); null and confounder fixtures; mutation tool.
- **M4:** charts with error bars; bundle; README; BACKLOG entries closed.

## 10. Risks & Open Questions

- **Risk:** plain-Python IRLS and CART at 100k+ loans may exceed the
  five-minute budget. Mitigation: the build prints per-step time; the cube
  steps are O(n); if the model step is the cost, cap tree candidates (§6.10)
  before reaching for a dependency.
- **Assumption (the firm's, 18 Sep 2026):** Key's desk Python has
  `openpyxl` — the credit-review-os bundle ran there. Not re-verified.
- **Risk:** Key's Excel version. `_xlfn.` functions need Excel 2010+; the
  render harness proves LibreOffice, not Excel. First open at the desk is the
  proof.
- **Open question (yours):** Key's column names — written into the config
  at the desk after `pack inspect`.
- **Open question (yours):** the utilization threshold for the second
  config (outstanding ÷ commitment at as-of; the firm named the measure on
  18 Sep 2026), e.g. `>= 0.9`.
- **Open question (yours):** the `existing_control` value for the first
  instance.

## 11. Done Criteria

- [ ] Requirements 1–30 met; user stories 1–28 satisfied.
- [ ] Seam-1 and seam-2 suites green; the six fixture classes present and
      `mutation_check.py` proves each can fail.
- [ ] Every fixture pack rendered by the harness and looked at: no error
      cells, charts have axis numbers and legends off the data.
- [ ] Two builds byte-identical; bundle rebuild byte-identical in an empty
      environment.
- [ ] README (setup incl. `libreoffice-calc`, the CLI, the config schema,
      what the pack is not), `BACKLOG.md` §6c updated, `CLAUDE.md` project
      list updated.
- [ ] `docs/DESIGN-PRINCIPLES.md` unchanged — checked: this project rests on
      *never invent a value* (required slots, `not run` rows), *refuse rather
      than default* (hygiene, missing lines), *facts are recorded, never
      inferred* (`known:` per column, `existing_control`), and strains none.
