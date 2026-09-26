# The final check (26 Sep 2026)

Step 6 of `docs/NEXT-GOAL.md`: *"The final check is done by an agent that has not seen
the work: facts against sources, arithmetic by running it, the workbook by opening it."*

**Who and what:** an agent that had not seen the work, run on a clean copy of head
`a0f5bd1d`. It was told where the claims are and what the sources are, not what
the work believed. It changed nothing in the repository.

**What it ran:**
- `docs/statistics-examples.py`;
- the cube's own test functions on every worked example in `docs/statistics.md`;
- the full suite, on a clean `git archive`: **441 passed, 1 skipped, of 442** in
  15 min 52 s (the skip is the launcher window: no tkinter in the container);
- `cube synth` and the workbook route, opened with openpyxl and rendered to PDF in
  LibreOffice (about 15 pages read);
- one pocket recomputed by hand from the CSV.

It was told not to run the mutation check. CI ran it on the same head: 169 of 169
caught.

**Result:** 206 claims checked. 181 held, 25 were wrong, and 13 could not be checked.
**No arithmetic error in the cube.** The wrong statements are all in what the work
says about itself: 14 findings.

**Its own incident:** checking one BACKLOG claim, it loaded `tools/mutation_check.py`
from the `da0271a` snapshot. That version had no main guard, so loading it started
the mutation loop. It ran 4 mutations in the agent's scratch copy before it was
stopped. The copy was deleted and re-extracted; the repository was not touched.
The main guard added in `3399858` is what stops this now.

**Its report file:** its tool refused to write one, so it returned the report as a
message. The findings and the denominator below are that report, lightly condensed.
What was done about each is at the end.

---

## Findings, most serious first

**F1. README and design.md say the result tabs are not built. They are.**
- README 14–16: "the rest of the workbook is not" built.
- README 18–20: "The workbook's other tabs, drill-down and `cube prove` are designed,
  not built."
- design.md 20–29 lists the workbook's other tabs under "Proposed".
- In fact, Set up and Run produce 15 tabs. Drill-down and `cube prove` really are
  unbuilt.

**F2. "Every worked example in docs/statistics.md is reproduced by a test" is false
for four sections.**
- The claim is in BACKLOG 1538, README 166 and `stats.py` 5–6.
- Tested: A1, A2, A3, A5, A6, A8, B1, A7, B2, B9.
- Not tested: B3/B4, B5, B6, B7. Those are capabilities 4a–4e, scoped only.

**F3. design.md's 25 Sep rulings describe behaviour that fixes 3.1–3.3 removed, and
nothing records the change.**
- OC-30 ("revenue gap could be luck"), OC-31 (fixed revenue options "5%, 10%, the
  loss lines", "could-be-luck multiple in brackets") and the Losses vs revenue layout
  at 514–523 (two sides of five columns, multiples).
- The code has points, profit options of each pocket's own test / 0.25 / 0.5 points /
  the materiality line, three sides plus Together, and no "earning" or "could be
  luck".

**F4. The adversarial hypothesis count doesn't add up.** design.md says 33
hypotheses, 4 red, 27 clean: 31. The committed record doesn't state 33.

**F5. Check calls the run's whole loan range "the holdout".** "Deviates from
pre-spec: The holdout is 2021-06-30 to 2024-12-30 in this run" is the origination
range of every loan used. The Holdout row two lines below correctly says 1,733 loans
in 2024-01-01..2024-12-31.

**F6. The README's example error names the wrong cell.** `Control!C16` should be
`Control!C18`: the window and as-of rows moved it down two.

**F7. `synth.py`'s docstring says the priced pocket's rate is 6 points higher.**
`PREMIUM = 0.02` is 2 points, as `test_profit.py` says.

**F8. `synth.py`'s docstring says profit falls where losses climb.** Across score
bands it rises: under 620 keeps 17.68% with 13.51% GCO; 740 and up keeps 4.83% with
2.00% GCO. It holds only within a band at one price.

**F9. Tab wording an analyst would have to look up or would misread.**
- Check: "Cochran-Mantel-Haenszel, with no continuity correction", unexplained.
- Check: "(OC-35)" and "(the firm's call, 25 Sep 2026)", internal references.
- Split: "Same size in every pocket?" reads "yes/no outcome only" on four rows, which
  looks like an answer.
- Columns!D3 still says "New since the last check … set C3 to Yes again" after C3 is
  Yes and the Run succeeded.

**F10. Two NEXT-GOAL statements are no longer true.** The test-design file was
committed (`docs/for-test-design.md`); numpy is a required dependency (OC-34).

**F11. "Standard error" is defined three times, not once** (Control, Split, Check).

**F12. The capabilities scope credits `scout-vs-measure.py` with a calibration check
it doesn't contain.** It scores AUC only; calibration is in `statistics-examples.py`.

**F13. The example pre-spec's group names don't match the tabs.** It says groups are
named "the way the grids name bands: up to 0.09"; the Prevalence tab names that group
"0.02 - 0.09", so one group has two names. The example is also dated 2026-10-01,
after today, and the cube accepts that silently.

**F14. The audit labels an after-allowance p-value as the raw result.** Item h's
"z-test gives p = 2.3 × 10⁻¹⁰" is the figure after the many-tests allowance; the raw
test gives 1.5 × 10⁻¹¹. The rest of the item reproduces exactly.

**The goal is not yet met, and nothing claims it is.** A run can't restrict itself to
holdout loans, and the split tests median halves rather than the pre-spec's bins
against its reference group. Check reports both as deviations; 4b is unbuilt.

## The denominator

- **Checked:** 206 claims. **Held:** 181. **Wrong:** 25, across the 14 findings.
  **Could not check:** 13.
- **Held, by source:**
  - NEXT-GOAL's ticked boxes: 36, each with its test named.
  - Other NEXT-GOAL statements: 4.
  - BACKLOG §6d: 43.
  - design.md: 9.
  - README: 26.
  - The audit: 23, including all three slips in `statistics.md`, recomputed (1.0189;
    groups of 100/400/500/400/100 and 66.4714; 7.64% at 0.10).
  - `capabilities-scope.md` on `scout-vs-measure.py`: 7.
  - `statistics.md` against its scripts: 13.
  - The cube's functions on the worked examples: 10. All match to rounding, or to
    scipy/statsmodels. The shuffle test gives 3,463 hits against the reference's
    3,497, 0.72 standard errors apart.
  - Docstring and example claims: 4.
  - The workbook, opened: 6.
- **The priced pocket, by hand from the CSV,** equals the workbook to the dollar:

  | | Rate | Gap | Over the rest |
  |---|---|---|---|
  | Contribution | 19.5690% | +5.43 pts | $1,983,352 |
  | GCO | 4.6135% | 1.86× | $779,111 |
  | RANR | 14.9555% | +3.30 pts | $1,203,595 |

- **Could not check:**
  - the mutation check (told not to run it; CI did);
  - OC-34's "about 6 minutes";
  - the README's speed notes (11.3 s here against 9.9 s claimed, on different
    grids);
  - "no branch of 131";
  - the count of 33 hypotheses (see F4 below);
  - the audit's O/E 1.620 → 1.237;
  - 4b's claim that B3 equals the conditional score test;
  - a committed pre-spec in a hand-built workbook (the suite covers it);
  - the launcher window;
  - real Excel;
  - "Show per pocket", grids repeated per category value, and the product-mix warning
    shown in a workbook;
  - BACKLOG entries from before the goal;
  - whether `statistics.md` is byte-identical to what the firm supplied.

---

## What was done about each (triage)

Every finding was read and judged before anything changed. All 14 are real. None
touches the arithmetic.

| # | Decision | What changed |
|---|---|---|
| F1 | Fixed | README's status and design.md's "Built / Proposed" say the whole find stage is built; drill-down, `cube prove` and the confirmatory test (4b) are not |
| F2 | Fixed | README, BACKLOG and `stats.py` say 8 of the 12 worked examples are reproduced, the 8 for tests the cube runs; B3–B7 wait on 4a–4e |
| F3 | Fixed | New ruling OC-38 records the switch to profit after losses in points, and OC-30, OC-31 and the Losses vs revenue note each say what it superseded |
| F4 | Fixed | The count was 4 red + 27 clean + 2 reported but not filed = 33. design.md now names the 2; one of them is a question on the hand-back |
| F5 | Being fixed | Check's holdout deviation line |
| F6 | Fixed, with a test | README names `Control!C18`. `test_the_readme_quotes_a_refusal_the_tab_really_gives` fails if the example stops matching a real refusal |
| F7 | Fixed | `synth.py` says 2 points (`PREMIUM`) |
| F8 | Fixed | `synth.py` says the riskiest band keeps the most across bands; losses cut profit within a band at one price |
| F9 | Being fixed | The four wordings on Check, Split and Columns |
| F10 | Fixed | NEXT-GOAL's notes say numpy is required and the test-design file was committed. The firm's own item text is untouched |
| F11 | Kept, note fixed | Each tab that uses "standard error" defines it in the same words, since each tab is read on its own. NEXT-GOAL 3.1's note now says so |
| F12 | Fixed | `capabilities-scope.md` credits the script with AUC only; calibration is in `statistics-examples.py` |
| F13 | Being fixed | Group names and the future date |
| F14 | Fixed | The audit gives the test's own p (1.5 × 10⁻¹¹) and the after-allowance figure (2.3 × 10⁻¹⁰), marked as corrected |
