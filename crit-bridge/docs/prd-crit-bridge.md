# PRD: Crit Bridge — what moved the criticized commitments

**Status:** Draft · **Owner:** AJ · **Last updated:** 2026-11-01

---

## 1. Problem

Criticized commitments swing from one period to the next, and the first
question is always the same: *is there something we need to see?* Is it one or
two borrowers? Is it broad, which would point at the economy? Is it one part of
the bank?

Today that answer is built by hand: take the criticized total, then drill into
the bank's business lines and our own grouping until the swing is explained.
The method is simple and repeatable, but it is rebuilt every time, so it is slow
and nothing proves it ties to the total. In a single portfolio the whole
movement is often one or two credits, and a hand build can miss that or mix a
book-growth effect in with a real deterioration.

## 2. Solution

A tool that runs on site on the bank's own loan-level snapshots and writes an
Excel bridge for any two snapshot dates. It starts at the total criticized
change and splits it into what happened (new criticized credits, credits that
left, balance changes on credits already criticized). It then walks down the
firm's own tree (EBU, then MBU, then SBU, then borrower) and ranks borrowers by
how much of the swing each one carries. Concentration is answered by the share
the top 1, 2 and 5 borrowers carry. "Macro-shaped" is answered by how broad the
movement is. NPL can run through the same bridge, so you can see whether the
swing is already in default or still early warning. Every run proves the bridge
ties to both snapshot totals, or it stops.

## 3. Goals & Non-Goals

**Goals**
- Explain the change in criticized $ between two snapshots, exactly (no unexplained residual).
- Show the same change through the bank lens (EBU) and down the tree (MBU, SBU), with the lenses tying to one headline.
- Say how concentrated the swing is, by borrower.
- Say how broad the swing is, without claiming a cause.
- Show the criticized ratio next to the dollars, split into "the criticized pile moved" and "the book grew".
- Optionally run the same bridge on NPL, and show how much criticized $ is also NPL.
- Stay simple: one command in, one workbook out.

**Non-Goals / Out of scope**
- **No macro model.** No regression, no causal claim, no public-series overlay in v1. [LOG]
- **No related-group (connected borrowers) rollup.** The credit is the borrower ID as given. [LOG]
- **No forecasting, no early-warning score, no risk-rating of credits.** It explains what already happened.
- **No competitor data.** `edgar-crit-class-tracker/` and `fdic-peer-monitor/` own that.
- **No real bank data in the repo**, in tests, fixtures, logs or docs. Public/synthetic only.
- **No GUI in v1.** CLI plus workbook. A window can come later, as `threshold-engine` did. [LOG]
- **No inferred defaults.** The tool never guesses a label meaning, a column, a hierarchy, or a missing value.
- Not a general loan-level data warehouse or a migration-matrix tool.

## 4. User Stories

1. As the credit analyst, I want to give two snapshot files and get one bridge workbook, so that I stop rebuilding the drill-down by hand.
2. As the credit analyst, I want the total criticized change split into entrants, exits, balance change on existing criticized credits, so that I can say what kind of movement it is.
3. As the credit analyst, I want the top 1, 2 and 5 borrowers' share of the swing, so that I can answer "is it one or two credits?" with a number.
4. As the credit analyst, I want to see how many borrowers and how many business units moved in the same direction, so that I can tell narrow movement from broad movement.
5. As the credit analyst, I want the bridge shown by EBU (middle market, institutional bank, real estate capital) and then drilled to MBU and SBU, so that I see where in the bank the swing sits.
6. As the credit analyst, I want every borrower in the ranking to show which units its movement came from, so that a borrower split across units is not hidden or double counted.
7. As the credit analyst, I want movement between "criticized" and "classified" reported separately from entering or leaving criticized, so that a downgrade inside the pile isn't read as growth.
8. As the credit analyst, I want the ratio to total commitments next to the dollars, split into pile movement and book growth, so that a growing book isn't read as deterioration.
9. As the credit analyst, I want an NPL bridge when my extract has NPL, plus how much criticized $ is NPL, so that I can tell default from early warning.
10. As the credit analyst, I want the tool to stop when a label is not in my mapping, so that a relabelling cannot pass as a swing.
11. As the credit analyst, I want the tool to stop when the bridge does not tie to the snapshot totals, or when two lenses disagree, so that I never present a number that does not add up.
12. As the credit analyst, I want the tool to stop when an SBU sits under two MBUs, or an MBU under two EBUs, so that the tree I drill down is real.
13. As the credit analyst, I want a chain of several snapshots (for example, consecutive quarters) bridged in one run, so that I can see the movement over time.
14. As a reviewer, I want the workbook to keep its numbers as live formulas where practical and to state the mapping, snapshot dates and tool version, so that I can follow and re-check it.
15. As the credit analyst, I want borrower identifiers in the output exactly as supplied, with no names required, so that sharing the workbook internally exposes nothing the extract did not already carry.

## 5. Requirements

1. [P0] Input is a CSV per snapshot (or one CSV with a snapshot-date column) with one row per commitment: snapshot date, borrower ID, commitment $, label, EBU, MBU, SBU. Optional: NPL flag, NPL balance. Column names come from a required column map; none are assumed.
2. [P0] A required label mapping states which labels mean criticized and which mean classified. Classified is a subset of criticized. Any other label is non-criticized only if the mapping says so. An unmapped label stops the run, naming it and its row count.
3. [P0] Headline: criticized $ at each snapshot and the change. Ratio: criticized / total commitments at each snapshot, with the ratio change decomposed into numerator effect and denominator effect that sum exactly to the ratio change.
4. [P0] Borrower-level bridge. Each borrower is exactly one of: entrant, exit, continuing-higher, continuing-lower, unchanged, by criticized $ at the two dates. The bridge categories sum exactly to the headline change.
5. [P0] Tier movement: continuing borrowers' criticized $ that moved between classified and criticized-not-classified is reported on its own and nets to zero on the criticized headline.
6. [P0] Concentration: top 1, 2, 5 borrowers' share of the gross swing and of the net swing, with the borrowers named by ID. When gross swing and net change differ in sign or size, both are shown and labelled.
7. [P0] Breadth: count and share of borrowers moving up, down, unchanged; count of EBUs, MBUs and SBUs moving the same direction as the headline. No causal wording anywhere in the output.
8. [P0] Hierarchy tree: total, EBU, MBU, SBU, borrower, with the bridge categories at each node and every level summing to its parent. A borrower split across units appears under each unit with that unit's slice.
9. [P0] Hierarchy validation: every SBU maps to exactly one MBU and every MBU to exactly one EBU, within and across snapshots. A violation stops the run and names the offenders.
10. [P0] Tie-out on every run: bridge total equals snapshot-to-snapshot headline change; the sum over EBUs equals the headline; the sum over MBUs equals the sum over EBUs; the same for SBUs. Failure stops the run and prints the difference. There is no tolerance setting and no plug line.
11. [P1] Optional NPL: if the NPL columns are mapped, run the same bridge on NPL and report criticized $ held in borrowers that are also NPL at each date. If unmapped, the NPL sheets are absent, not empty.
12. [P1] Multi-snapshot chain: with three or more dates, produce a bridge for each consecutive pair and a summary sheet of headline change and top-1/2/5 share per period.
13. [P1] A Run sheet in the workbook records the tool version, snapshot dates, input file names and row counts, the label mapping, the column map, and each tie-out result.
14. [P1] A plain-English "How to read this" sheet defining each bridge category in one sentence each.
15. [P2] A short narrative line per period, generated from the numbers by fixed templates (for example, "Two borrowers carry 71% of the increase"), never free-form.

## 6. Implementation Decisions

- **Home and shape.** New top-level folder `crit-bridge/`, mirroring `threshold-engine/`: `src/crit_bridge/` package, `tests/`, `pyproject.toml`, README. Python 3.9+, stdlib plus `openpyxl`; test extras `pytest` and `formulas`. Console script `crit-bridge`.
- **Front door.** `crit-bridge bridge --snapshots A.csv B.csv [C.csv ...] --columns columns.json --labels labels.json --out Bridge.xlsx`. Also `crit-bridge template` to write an empty example of the input, the column map and the label mapping, so the first run starts from something real.
- **Core.** One pure function takes parsed rows for two snapshots plus the two config objects and returns a plain result structure (headline, ratio decomposition, borrower classes, tier movement, concentration, breadth, tree, tie-outs). The CLI and the workbook writer are thin wrappers. This is the seam.
- **No defaults, refuse rather than fill.** The column map and the label mapping have no defaults. A missing column, a blank commitment, a non-numeric amount, a duplicate commitment key within a snapshot or an unmapped label stops the run with the row numbers. Following `docs/DESIGN-PRINCIPLES.md`: never invent a value, refuse rather than default.
- **Money arithmetic.** Amounts are parsed to `Decimal` and kept in whole cents. Float is never used for dollars, because the tie-out has to be exact.
- **Borrower categories** by criticized $ at the two dates: entrant (zero then positive), exit (positive then zero), continuing-higher, continuing-lower, unchanged. A borrower with no rows at one date is zero there. The bridge categories are the per-category sum of (to minus from), so they sum to the headline by construction, and the tie-out proves it independently from the totals of the raw rows.
- **Tier movement.** For continuing borrowers, the criticized total is unchanged by a move between tiers. Its effect on classified $ is reported as a separate line, and the criticized bridge does not include it.
- **Ratio decomposition.** Ratio change = numerator effect + denominator effect, computed as: numerator effect = (C1 − C0) / T0, denominator effect = C1 × (1/T1 − 1/T0). These sum exactly to C1/T1 − C0/T0. Stated on the How to read sheet.
- **Concentration measure.** Share of gross swing = a borrower's absolute criticized change over the sum of absolute changes across all borrowers. Share of net change is shown beside it. Both are shown because offsetting movers make a net share exceed 100%.
- **Breadth.** Reported as counts and shares, not a verdict. The word "macro" does not appear in the output.
- **Hierarchy.** Validated as above, then each tree node's bridge is the sum of its commitments' slices. A borrower's per-unit slice is computed from the commitment rows in that unit. Borrower-level categories use the whole-borrower totals; a split borrower's slice in a unit carries the borrower's category.
- **Workbook.** Written with `openpyxl`, in `threshold-engine`'s style: Run sheet, Headline, Bridge, Tree, Borrowers, Concentration, Breadth, Tiers, NPL (conditional), How to read. Totals and the tie-out cells are live formulas over the data sheets so the reviewer can follow them, and the tests recalculate them with `formulas`.
- **Data handling.** Borrower IDs are written exactly as supplied. The tool does not ask for, read, or write borrower names. The repo holds a generator for synthetic books only.
- **Documentation.** `docs/DESIGN-PRINCIPLES.md` gets no change unless implementation strains a principle. If it does, update it in the same commit. A README gives the one-command example and the three-question reading guide.

## 7. Testing Decisions

- **Seam:** the bridge function in the core (rows and config in, result structure out), plus one end-to-end test of the `crit-bridge bridge` CLI that reads the workbook back. Nothing lower is tested directly. This is the same shape as `threshold-engine`'s CLI and workbook tests.
- **What a good test proves:**
  - **Planted causes.** A synthetic-book generator makes four known cases: (a) one borrower carries most of a swing, (b) broad drift across every EBU, (c) pure book growth with no criticized change in dollars, (d) NPL overlap. Each test asserts the tool names the planted cause (the borrower ID, the breadth counts, the denominator effect, the NPL share).
  - **Tie-out can fail.** A control test corrupts one number, hand-edits a bridge line, and removes a row, and asserts each makes the run stop. A tie-out check that cannot fail proves nothing.
  - **Refusals.** Unmapped label, missing column, duplicate commitment key, SBU under two MBUs, non-numeric amount: each stops with a message naming the offenders.
  - **Split borrower.** A borrower with commitments in two EBUs appears under both, once in the borrower ranking, and the lenses still tie.
  - **Exactness.** Cent-level amounts with awkward fractions tie exactly, with no tolerance.
  - **Workbook.** Recalculated with `formulas`, the live total and tie-out cells equal the Python result.
  - **Opened, not assumed.** A test opens the written workbook and reads sheet names and key cells back, rather than trusting the writer.
- **Data handling and masking:** the repo contains synthetic data only. The generator uses made-up IDs (for example, `B0001`) and no names. A test scans every written workbook and every fixture for anything resembling a real name list or a full tax ID and fails if it finds one. Real extracts are run on site and never committed.

## 8. Success Metrics

- Every run's tie-outs pass or the run stops. There are zero unexplained residuals in any output.
- On each planted-cause book, the tool names the planted borrower, breadth, denominator effect or NPL overlap correctly in 4 of 4 cases.
- On the first real extract, the top borrower the tool ranks matches the one the analyst found by hand for the same two dates.
- A bridge for two snapshots runs in under a minute on an extract of 100,000 commitment rows. (Stated target; measure it and record the result.)

## 9. Milestones / Rollout

- **M1 (MVP):** core bridge, label mapping, hierarchy validation, tie-outs, workbook with Headline, Bridge, Tree, Borrowers, Concentration, Breadth, Tiers, Run, How to read; planted-cause tests (a)–(c); `template` command.
- **M2:** optional NPL bridge and overlap; multi-snapshot chain and summary sheet.
- **M3:** fixed-template narrative lines. Run on a real extract on site and record the comparison to the hand analysis.
- **Later:** a window front door, a related-group rollup, an overlay of public macro series. [LOG]

## 10. Risks & Open Questions

- **Risk:** the label mapping hides a definition change (a regrade). It catches an unmapped label, not a changed meaning behind the same label. Mitigation: the Run sheet prints the mapping and per-label row counts for each date, so a shift is visible.
- **Risk:** breadth is easy to over-read as "macro". Mitigation: no causal wording, and the How to read sheet says the test is descriptive only.
- **Risk:** a borrower split across units makes the unit slices and the whole-borrower categories diverge. Mitigation: specified above and covered by the split-borrower test.
- **Risk:** a different dataset behaves differently from the synthetic one (extra labels, blank units, amended history). The tool refuses rather than guesses.
- **Open question (needs your decision):** the exact column names and label text in your extract. The tool takes a column map, so this does not block the build, but the first real run needs the real names.
- **Open question (needs your decision):** whether the criticized/classified tiers should also be shown as separate labelled lines beyond the two you have today (for example, special mention versus substandard) once your extra labels exist.
- **Open question (needs your decision, on site):** confirm against your own hand analysis that the tool's top borrower for the same two dates is the same one.

## 11. Done Criteria

- [ ] Requirements and user stories met (P0 in M1, P1 in M2).
- [ ] Tests added and passing at the named seam, including the four planted-cause books and the tie-out-can-fail control.
- [ ] Verified by running the real CLI on a synthetic book and opening the workbook (sheet names, key cells, live formulas recalculated).
- [ ] No real data, names or full tax IDs anywhere in the repo.
- [ ] README written with the one-command example; `template` command works from a clean checkout.
- [ ] Deferred items appended to `BACKLOG.md`.
- [ ] On-site comparison against the analyst's hand build recorded (M3).
