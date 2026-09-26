# Capabilities 4a–4e: scoped, not built (25 Sep 2026)

For the goal in `docs/NEXT-GOAL.md`. Each is scoped against `docs/statistics.md` and
against what the cube will have once fixes 3.1–3.18 land.

**Every one needs dated loans.** In particular:
- origination date and outcome date (fix 3.13);
- an outcome window (3.14);
- a committed pre-spec with the holdout range (3.15).

*26 Sep 2026: the outcome date and the outcome window were removed from the cube by OC-39
(`docs/design.md`): the bleed analysis shows every loan. The origination date and the
pre-spec's holdout stay. Where a capability below needs a dated outcome or a window, that
belongs to the scouting pipeline and is the firm's to settle when the capability is built.*

4a and 4b also use derived columns (3.9).

**Work** is given in working days for one person, including tests and a render check
of the workbook.

---

## 4a. Scouting: a random forest on development vintages only

**What it answers:** which columns, derived ratios included, the book leans on, and
where each one bends. It nominates; it never confirms (B7).

**Data it needs:**
- the extract with origination dates, to split development from holdout by vintage;
- the dated outcome and window;
- the candidate columns, given explicitly, with derived ratios (income ÷ sales) fed in
  as columns in their own right;
- the holdout range, from the pre-spec.

**What it adds:**
- **A Scout tab**, written only from development loans:
  - a permutation-importance ranking: how much the model's rank-ordering (AUC, the
    chance a random bad loan scores above a random good one) drops when each column
    is scrambled;
  - one partial-dependence curve per shortlisted column: the model's bad rate as the
    column moves, holding the rest as they are;
  - suggested bins where each curve bends, for the analyst to write into the
    pre-spec.
- **Check and what-ran** record the development range and the number of holdout loans
  the scout saw, which must be 0.

**What of `docs/scout-vs-measure.py` is kept, changed or dropped:**

| Part | Decision | Why |
|---|---|---|
| Random forest (400 trees, leaves of at least 40, fixed seed) | **Kept** | Matches B7; these settings gave the reference's importances |
| Permutation importance by drop in AUC, 10 repeats, on development loans the forest didn't train on | **Kept** | This is B7's ranking |
| Partial dependence over a grid of the ratio | **Kept, changed** | The grid comes from the column's own quantiles, not a hand-typed list, so it works on any column |
| `make_book`, the synthetic two-seed books | **Changed** | Reads the extract's columns by meaning. Development and validation are split by origination date, not by row position (`Xdev[:28000]`) |
| Holdout kept apart "by convention" (separate arrays) | **Changed** | Holdout loans are removed in code before anything is fitted, and a test proves the scout cannot see one |
| Scoring the frozen forest on the holdout by AUC (the calibration check is in `statistics-examples.py`, not this script) | **Dropped** | B7 says development only. The holdout's one job is the pre-specified test (4b). A model score on the holdout is a second look at it |
| The plain logistic regression with the ratio as a number | **Dropped from the cube, kept in the doc** | It is the worked example of why a straight line misses a cliff (B7), not a step the analyst runs |
| The binned regression with edges typed by hand | **Moved to 4b** | That is the confirmatory test, run from the pre-spec |

**New add-on (the firm, 26 Sep 2026: "Optional add-on"):** scikit-learn, which brings scipy. It is heavier than numpy. It would
be optional: only the Scout tab needs it, and the launcher would offer to install it
the way it does numpy (OC-34). Writing a forest by hand in numpy is possible but
would be a week, and a second implementation to trust.

**Known limits, printed on the tab:**
- importance leans towards columns with many distinct values;
- partial dependence can mislead when columns move together;
- forests are not bit-identical across scikit-learn versions, so the version is
  recorded.

**Work:** about 2 days. The module and tab take a day. The date and holdout guard, and
tests that reproduce B7 on the reference's planted book, take a day (the reference
gives FICO 0.236 and ratio 0.015; cliffs near 0.1 and 2.0).

## 4b. A split column with its own edges or K groups, confirmed on a holdout

**What it answers:** does the column matter, with every loan compared only with loans
in its own pocket, and does the answer hold on a later vintage nobody chose the bins
on?

**Data it needs:**
- the column (a split column or a derived ratio) and its bins or K groups, from the
  pre-spec;
- the strata, which are the pockets;
- the dated outcome and window;
- the development and holdout origination ranges.

**What it adds (per grid, development and holdout side by side):**
- **B3, general association:** does the bad rate differ across the K groups in any
  shape? A χ² on K − 1 degrees of freedom.
- **B4, trend:** does it climb or fall steadily? A χ² on 1 degree of freedom. Read
  with B3: general yes and trend no means a U or a hump.
- **B5, the stratified logistic regression:**
  - an odds ratio per group against the reference, with a 95% interval and a p-value;
  - the likelihood-ratio block test.
- **The cross-check to nine digits:** B3's statistic is the score test of the
  conditional logistic model at "no effect". The cube computes it two ways:
  - by B3's formula;
  - from the conditional likelihood's own first and second derivatives, taken
    numerically.

  A test holds the two equal to 1e-9. A third check is statsmodels' `ConditionalLogit`
  on a fixed example, with its numbers written into the test (statsmodels is not needed
  to run the cube). B5's odds ratios are cross-checked against
  the Mantel–Haenszel ones, to a tolerance, not nine digits: they are different
  estimators.
- **The rule the goal sets:** the pooled test answers "does this column matter"; the
  per-pocket floors only govern the per-pocket readings. So a pocket too small to read
  still counts in the pooled test.

**Limits:** with hundreds of thin pockets, estimating a constant per pocket biases
B5's odds ratios (B5, "Breaks when"). The fix is conditional logistic regression. The
scope includes it for binary outcomes by the standard recursive computation per
stratum; pockets over a few thousand loans fall back to the unconditional fit, which
is unbiased at that size.

**Work:** about 3 days. B3, B4 and the score cross-check take a day. B5 with the
conditional fit takes a day and a half, written in numpy (no statsmodels on the bank
machine). The two-range report and the tab take half a day.

## 4c. Loss typing: fraud-shaped against failure-shaped

> **Out of the cube (the firm, 26 Sep 2026):** *"This is not something the engine is meant
> to catch. This is non generic. This is meant to be something we may do on a specific study
> or something."* Kept below as the method for such a study; the cube will not build it.

**What it answers:** are the bad loans in a pocket the kind that never paid, or the
kind that paid for a while and then failed? The two call for different fixes.

**Data it needs, per bad loan:**
- GCO;
- contribution before losses (RANR + GCO, OC-35);
- months to bad, from origination date to outcome date (3.13).

**What it adds:**
- Each bad loan typed by two numbers:
  - contribution ÷ GCO: near 0 means it barely paid before it failed;
  - months to bad.
- Per pocket, the two types become **two outcomes**, each tested like the outcome is
  today (A1, or B1 below the floor). They get their own grids and rows on Where it
  bleeds.

**The firm's call:** the cut-offs. For example, fraud-shaped might be "bad within 6
months and contribution under 10% of GCO". The scope proposes those two numbers as
Control settings with suggested values read from the book's own distribution (the
Look tab's histogram of months to bad), and nothing hard-coded.

**Work:** about 1 day once 3.4 and 3.13 exist.

## 4d. The hold-constant check

**What it answers:** does the split's effect survive once affordability at approval
(DTI, PTI, residual income) is held fixed? If it doesn't, the split was affordability
in disguise.

**Data it needs:** a column whose meaning is affordability (the catalog's
`dti`-style ratio, or a derived ratio such as payment ÷ income).

**What it adds:**
- The split's pooled effect twice:
  - with pockets cut by band × segment;
  - with the affordability column added as a cut (its own equal-loan bands).
- Both shown side by side with their intervals and p-values, and one line: "survives:
  1.84× becomes 1.71×, still significant" or "vanishes: 1.84× becomes 1.05×".
- The same correlation warning the Split tab gives today (A9), for the affordability
  column.

**The firm's call, made 26 Sep 2026 ("As proposed"):** 5 affordability bands with equal loans,
set on Control; "survives" means the second interval still excludes 1.

**Work:** about 1 day. The engine already cuts by extra columns; this runs the split
twice and adds one table.

## 4e. Concentration on the holdout

**What it answers:** how big a slice of the book is the group, and how much of the
stress sits inside it (B6)?

**Data it needs:** the holdout loans (the pre-spec's range), the dated outcome and
window, and GCO.

**What it adds, per group of a split or derived column, on the holdout only:**
- **flag rate:** the group's loans ÷ all loans;
- **capture:** bad loans in the group ÷ all bad loans, and the same in GCO dollars;
- **lift:** the group's bad rate ÷ the book's.

It gives no cost or benefit figures; what to do about the group is the line of
business's call. As B6 says, the finding is the lift and the dollars, never the share
of all losses.

**Work:** half a day after the pre-spec and holdout wiring.

---

## In order

| # | Needs first | Work | New add-on |
|---|---|---|---|
| 4e | 3.13, 3.14, 3.15 | ½ day | none |
| 4d | the split (exists) | 1 day | none |
| ~~4c~~ | out of the cube: a study, case by case (the firm, 26 Sep) | — | — |
| 4a | 3.9, 3.13, 3.14, 3.15 | 2 days | scikit-learn (optional) |
| 4b | 3.9, 3.13, 3.14, 3.15; 4a to nominate the bins | 3 days | none (numpy) |

The confirmatory run the goal describes needs 4b and the pre-spec. 4a nominates the
bins that go into the pre-spec, which is why it comes before 4b in use even though it
is not needed to run 4b.
