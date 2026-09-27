# Next goal: profit after losses, and a pre-specified test of a derived column

**Set by the firm, 25 Sep 2026.** It replaces the eighth walk and the Claude Design
hand-off as what this project works on next (both wait until this is done).

This is the in-repo docket. Each item is ticked here when it lands, with the commit
and the test that holds it, so the next session reads its job from the repository
and not from a conversation. The running log is `BACKLOG.md` §6d.

## The goal, in the firm's words

> "RANR is profit after losses — interest income + fees − cost of funds − losses —
> and the cube's outputs, tests and synthetic book should treat it that way; and the
> cube should be ready to test a derived column (income ÷ sales) against a dated
> outcome, on a holdout, from a committed pre-spec."

**What would end it:** every item in steps 1 to 6 below is ticked, or is handed back
as a question with a recommendation. The suite and the mutation check must be green,
and the final check must be done by an agent that has not seen the work: facts
checked against sources, arithmetic checked by running it, and the workbook checked
by opening it.

**Reference for every test:** `docs/statistics.md`. Control's explanations and
Check's wording must match it. The firm supplied it on 25 Sep 2026, and it was
committed unchanged. On 26 Sep, with the firm's yes, its three slips (B1, B3/B4, B7) were
corrected in place, each marked. It cites two scripts kept beside it: `statistics-examples.py`,
which computes every worked example, and `scout-vs-measure.py`, which does the
random-forest scouting and the holdout example in B5 and B7. The firm supplied both
the same evening, and both are committed unchanged beside it. They need numpy,
scipy and scikit-learn. The cube itself needs numpy since OC-34 (26 Sep), and uses
neither scipy nor scikit-learn. *(Until the final check, this said the cube uses
none of the three.)* *(27 Sep 2026, item 9: scouting uses scikit-learn, and scipy, which it brings, as an
optional add-on; nothing else does.)*

**How the work is done:** subagents, one per fix, in parallel where they touch
different files.

## 1. Audit: what the code does now (file:line) and whether it fits the goal

- [x] **a.** Every place RANR is a multiple (pocket ÷ rest): Where it bleeds, Losses vs
      revenue, Control lines, suggested lines, smallest gap. Confirm the two-negatives
      flaw.
- [x] **b.** Which test the OC-31 per-pocket RANR test actually runs, and which tests
      GCO per dollar and share of booked dollars run.
- [x] **c.** How `synth.py` generates RANR. If it is independent of GCO or of balance,
      the fixture contradicts OC-29.
- [x] **d.** What "losses" inside RANR is assumed to be: GCO, net charge-offs, or
      unspecified.
- [x] **e.** Every label, reading and colour rule that calls RANR "revenue" or
      "earning".
- [x] **f.** Whether the cube shows any column's distribution before edges are chosen.
- [x] **g.** What the existing loan-age Control setting does, and whether the outcome
      is a flag as of the extract or is dated.
- [x] **h.** What happens to a pocket below the fewest-loans floor (walk 6 defect 8:
      50 loans, 29 bad, "too few loans to test").
- [x] **i.** Which formula sits under the Split tab's actual-vs-expected: expected from
      the pocket's pooled rate, or from the low half's rate (`docs/statistics.md` A7).
- [x] **j.** Whether the CMH test subtracts ½ (a continuity correction), and whether
      p-values are one- or two-sided.
- [x] **k.** What the other agent's tree code does today: what it trains on, what it
      outputs, and whether it can touch a holdout range. *It is `docs/scout-vs-measure.py`,
      which the firm supplied on 25 Sep 2026.*

## 2. Report the audit before changing source

- [x] Plain English, with each technical term shown and then explained, and every
      count given with its denominator. **Done 25 Sep 2026:**
      `docs/audit-2026-09-25.md`.

## 3. Fixes: what the tool gets wrong or cannot do today that the next run needs

Each is built with a test. The full suite and the mutation check run after each.

- [x] **3.1 p-value, not "Luck alone".** *(Done 26 Sep 2026, merge 89e1798. "Standard error" is defined in the same words on each tab that uses it, Control, Split and Check, not once, because each tab is read on its own.)* Rename it on every tab, Control and Check.
      Readings become "worse, not significant" and "(not significant)". Every
      explanation that says "wobble" says "standard error" instead, and defines it once,
      as `docs/statistics.md` does.
- [x] **3.2 RANR as a difference.** *(Done 26 Sep 2026, merge 89e1798.)* Replace every RANR multiple with the difference in
      percentage points of booked dollars (pocket − rest). Fixed Control lines for RANR
      become ± points or a dollar amount, and "borrow the loss lines" is dropped. The
      OC-31 per-pocket test stays as the suggested option.
- [x] **3.3 Profit wording.** *(Done 26 Sep 2026, merge 89e1798.)* Rename to "Profit after losses: RANR per booked dollar",
      with readings "keeps more / about the same / keeps less".
- [x] **3.4 Contribution before losses.** *(Done 26 Sep 2026, merge 89e1798.)* Add "Contribution before losses per booked
      dollar" = RANR + losses as defined in RANR. That is GCO unless the audit finds
      otherwise; flag it if it should be net charge-offs. Losses vs revenue reads: what
      they paid us / what they cost us / what we kept. Paired readings:
      - losing more + keeps more = "priced for it"
      - losing more + keeps less = "net drain"
      - losing less + keeps less = "safe but idle"
- [x] **3.5 Synthetic RANR.** *(Done 26 Sep 2026, merge 89e1798. Test 4 as written, with 3% of balance added, reads profit "about the same": −0.79 points, not significant. The test holds that result, and an 8% variant reads "priced for it". The test-design write-up the item calls not committed was committed later, as `docs/for-test-design.md` (f430378c).)* RANR = contribution − GCO, where contribution = interest
      on balance over months on book + fees − cost of funds on balance over the same
      months. Plant one pocket priced high enough to be losing more and keeping more.
      Make Tests 2 and 4 from `origination-cube-for-test-design.md` into fixtures (that
      file was sent to the firm, not committed; the fixtures are rebuilt from it).
- [x] **3.6 Permutation test for dollar rates.** *(Done 26 Sep 2026: `perm.py` in merge cfe045b; the Test column reads "shuffled: N of 10,000" from merge 89e1798.)* Replace any t-test or proportion test
      on a dollar rate (GCO per $, RANR per $, share of booked dollars) with a
      within-pocket permutation test, with a fixed seed, reported as "N of 10,000
      shuffles" (`docs/statistics.md` B2).
- [x] **3.7 Exact test below the floor.** *(Done 26 Sep 2026, merge cfe045b: Fisher's exact test below fewest loans, labelled "exact test"; walk 6's 29-of-50 pocket reads "worse"; only fewest losses refuses.)* Below the fewest-loans floor, run Fisher's
      exact test on the yes/no outcome instead of refusing, and label the row "exact
      test". Refuse only below fewest-losses. A test proves the 50-loan, 29-bad pocket
      now gets a verdict.
- [x] **3.8 Look before you cut.** *(Done 26 Sep 2026, merge 72b8806: `look.py`, the Look tab after Columns; scatters added at Run for a number split column.)* At Set up, a Look tab showing, for each number
      column:
      - a histogram
      - the share missing, and the share at sentinel values
      - the five most-repeated exact values, with counts
      - min, median and max

      Plus a scatter of any split column against each band column. Today, edges are
      chosen blind.
- [x] **3.9 Derived column.** *(Done 26 Sep 2026, merge 3dcb3da.)* A ratio of two existing columns, defined on Control
      (numerator, denominator, name). It is recorded in what-ran, usable as a band or
      split column, and gets a Look like any number column.
- [x] **3.10 Period attribute.** *(Done 26 Sep 2026, merge 3dcb3da.)* Amount columns get a period: per year, per month or
      one-time, recorded in what-ran. If a derived ratio's inputs disagree, warn on
      Check; never stop.
- [x] **3.11 Definitions on Control.** *(Done 26 Sep 2026, merge 3dcb3da, but on the Columns tab beside each column, not on Control: the firm to confirm.)* Free text for what each amount column means
      (household vs guarantor income; trailing-twelve actual vs a month × 12), carried
      into what-ran.
- [x] **3.12 Prevalence table.** *(Done 26 Sep 2026, merge 60ba9bc.)* For any split or derived column: loans and dollars per
      group per pocket, with no test attached. A count of the book, not a finding.
- [x] **3.13 Date roles on Columns.** *(Done 26 Sep 2026, merge 3dcb3da.)* Origination date and outcome date. The engine
      derives months on book and months to bad.
      *(26 Sep 2026: the outcome date and the as-of date were removed from the bleed analysis by OC-39, with
      months on book and months to bad. The origination date stays, for the development / holdout split, and
      Check gives its range. See `docs/design.md`, OC-39.)*
- [x] **3.14 Outcome window.** *(Done 26 Sep 2026, merge 3dcb3da.)* Extend loan age to a true window of N months:
      - It requires the outcome date. Bad means bad within N months.
      - Loans under N months on book are excluded.
      - Check reports the origination range tested and the count excluded.
      - Without an outcome date, the window is refused, with the reason.
      - Where seasoned vintages exist, report the share of eventual losses that had
        landed by month N.
      *(26 Sep 2026: removed from the bleed analysis by OC-39, with the loan age filter it extended: a run now
      shows every loan in the extract. `window_months` is gone from the pre-spec too. See `docs/design.md`,
      OC-39.)*
- [x] **3.15 Pre-spec.** *(Done 26 Sep 2026: the reader `prespec.py` in merge 6001797, wired into Check and the Log in merge 60ba9bc. Until 4b is built, every pre-spec run reads "deviates from pre-spec" on the reference group, because the cube compares halves, not groups against a reference.)* The confirmatory run reads a pre-spec file: bins, strata,
      window, confidence, reference group and holdout origination range.
      - Check echoes the file and the git commit it was read from.
      - If Control disagrees with the pre-spec, warn on Check and label the run
        "deviates from pre-spec" in the Log.
      - Any run whose extract falls inside the holdout range is flagged in the Log, so
        the count of holdout runs is visible.
- [x] **3.16 Pocket budget and coverage on Check.** *(Done 26 Sep 2026, merge 60ba9bc.)*
      - Max testable pockets = expected bad loans ÷ 5 (at the suggested floor), printed
        beside the pocket count Control asks for, with a warning when Control exceeds
        it.
      - The share of loans and of dollars sitting in testable pockets.
- [x] **3.17 Family count on Check.** *(Done 26 Sep 2026, merge 60ba9bc.)* How many grid × rate × comparison families the run
      contains, with one line saying that a single red across many families is weak
      evidence.
- [x] **3.18 Product mix warning.** *(Done 26 Sep 2026, merge 60ba9bc.)* If a credit-product column is present with more than
      one value and is not a cut column, warn on Check that profit per dollar is being
      compared across products. Warn only; the firm decides.

## 4. Capabilities: scope each, do not build

**Scoped 25 Sep 2026:** `docs/capabilities-scope.md`.

For each: the data it needs, what it adds to the outputs, and roughly how much work.

- [x] **4a Scouting step.** Reuse the other agent's tree code where it fits. A random
      forest trained on development vintages only, never the holdout. Permutation
      importance for the shortlist and partial dependence for the shape
      (`docs/statistics.md` B7). Candidate columns include derived ratios, fed in
      explicitly. Say what of the existing code was kept, changed or dropped, and why.
- [x] **4b Split with its own edges / K groups.** Instead of the per-pocket median, with
      the K-group Mantel–Haenszel general-association and trend statistics (B3, B4),
      cross-checked against a stratified logistic regression (B5) to nine digits.
      Holdout: develop on one origination range, confirm on a later one, and report
      both. The pooled test answers "does this column matter"; the per-pocket floors
      only govern the per-pocket readings.
- [x] **4c Loss typing.** For bad loans: contribution ÷ GCO, and months to bad.
      Fraud-shaped vs failure-shaped, reported per pocket as two outcomes.
- [x] **4d Hold-constant check.** When an affordability-at-approval column is present,
      run the split with and without it as a cut, and report whether the split's pooled
      effect survives.
- [x] **4e Concentration.** For a group on a split or derived column: flag rate,
      capture of bad loans and of bad dollars, and lift, on the holdout (B6). No cost or
      benefit inputs.

## 5. Adversarial pass

- [x] *(Done 26 Sep 2026; findings fixed in the commit after 121d3f9, see BACKLOG §6d.)* When the suite and the mutation check are green, hand the statistics module to
      the adversarial brief (`canon:adversarial`). Another agent writes only tests and
      never touches source, with one job: break the arithmetic. Take the findings back
      with the intake and record them in the log.

## 6. Hand back

- [x] Every decision that couldn't be made goes back as a question with both outcomes,
      a recommendation, and a box to answer in. *(Done 26 Sep 2026: 12 decisions and Next,
      on the docket at https://claude.ai/artifact/Dm54ZNHGJWaT9jooucgW4R. The answers are
      read back and logged in `BACKLOG.md` §6d.)*
- [x] Log what ran. *(Done 26 Sep 2026: `BACKLOG.md` §6d, the adversarial pass and the
      final check, whose report is `docs/final-check-2026-09-26.md`.)*

---

# Goal 2 (agreed 26 Sep 2026): the firm's rulings built, and the screens ready to be designed once

**Agreed with the firm, 26 Sep 2026** (*"we are now on the same page - make sure you docket all of
this so we know what the goal is"*). Goal 1 above is finished except 4b and 4e, which were scoped in
step 4 and are now being built. The rulings behind each item are logged in `BACKLOG.md` §6d and in
`docs/design.md` (OC-38 to OC-40); the project's standing rule is `TENETS.md` T1.

**What would end it:** every item below is ticked, with a test that holds it, the suite and the
mutation check are green in CI, and a run with "Test from a pre-spec" finds the planted
income ÷ sales cliffs on the development loans and confirms them on the held-back ones. Item 10 is
the exception: it waits on the redesign, and the goal ends with it handed over, not built.

**Proceeding autonomously, in this order, unless the firm says otherwise.** The firm's gates still
stop the work: anything a client or the bank reads that changes meaning, and any new tenet.

- [x] **1. 4b + 4e.** K groups with their own edges (Mantel–Haenszel general association and trend,
      cross-checked against conditional logistic regression), develop on one origination range and
      confirm on a later one; concentration (flag rate, capture, lift) on the holdout. Check stops
      reading "deviates" on the reference group. The cliffs are planted in the second synthetic book
      (`test_generic.py`) as well as the first, so finding them is not the code agreeing with its own
      fixture (S32, S18). *(Done 26 Sep 2026. The auto book, dated: US-style contract dates, its own
      edges and reference, cliffs of x3 below 0.05 and x2.5 from 1.50, planted on each loan's odds
      where the first book plants them on the ratio. A "Test from a pre-spec" run finds both on
      development and confirms both on the holdout. The same loans with no cliff are not confirmed on
      either range, although the worst dealer's loans crowd the lowest group, so the book as a whole
      reads a difference there. Two planted bugs: dates read only year-month-day, which the first
      book's goal tests pass, and the pockets forgotten, which the clean copy catches.)*
- [x] **2. The new-variable run needs only what it uses:** key, outcome, origination date, the tested
      columns and strata. Booked, GCO and RANR become optional for it; 4e shows dollars only when they
      are there. OC-14 and the run-kind entry are amended where they sit (S13). *(Done 26 Sep 2026.
      Set up says nothing about the dollar columns once the run is a new variable, and the Run goes
      through without them; the bleed analysis still refuses, naming each. 4e shows GCO whenever
      there is a GCO column, booked or not. A run without them writes no Losses vs revenue tab, and
      its other tabs and Check say nothing about profit, shuffled dollar rates or booked dollars. A
      cube file says it with `run_kind: new_variable`. The second book's cliffs are confirmed from
      its extract with the dollar columns taken out, figure for figure. Amended where the old
      minimum stood: design.md OC-14 and Step 0, the README, Control's answer, the settings and
      config comments, for-test-design.md, vba-findings.md and capabilities-scope.md 4e.)*
- [x] **3. Lean pre-spec.** An outcome plus a shortlist of inputs, each with bins and a reference;
      optional columns to hold fixed, each input reported with and without them (this is 4d); the
      allowance for many tests spread across the shortlist. Strata are suggested and left blank
      (OC-13). The Log records the pre-spec and every held-back run after it, in order; nothing is blocked.
      *(Done 27 Sep 2026, `docs/design.md` OC-49, `tests/test_shortlist.py`. The pre-spec takes `outcome:`
      and `inputs:` (each input's column, bins and reference), every line required; the one-column form is
      still read as a shortlist of one, and the same input written either way gives the same tab, number
      for number. Each verdict allows for every candidate's groups at once by Control's method
      (Benjamini-Hochberg by default), one family per set of loans; the table shows the allowed p-value,
      the tests in full keep the raw ones. New variables has a block and a chart per candidate and a live
      count of candidates holding up; Start here and the launcher's last step count across candidates.
      The launcher fills Test it, Hold fixed and the outcome from the file. The line offered for missing
      strata, and the committed shortlist example, leave them unanswered. On the first book, three inputs
      (income ÷ sales, UTIL with a cliff planted above 0.9, TENURE with nothing planted): the two planted
      hold up with and without FICO and CHANNEL held fixed, TENURE doesn't. Phase 4's loose ends closed:
      Control's panel of levels is hidden on a new-variable run and its method note names only worse at.
      Departure: a shortlist of one now allows for its own groups too; with No allowance the verdicts are
      phase 4's.)*
- [x] **4. T1 sweep.** One method note per tab, near the top, that an outsider can follow. The
      per-row lone-pocket note and the Test column move into it. Every other tab swept against T1's
      check: a column predictable from the settings and the pocket's size is method.
      *(Done in redesign phases (b)–(d): one folding "How this tab works" note per tab; the Test column and the lone-pocket note are off the rows.)*
- [x] **5. Option A.** "Judged against the book" measures points and dollars both against the rest
      of the book. The whole-book tie-out stays on Check. OC-4's "excess adds to zero" is marked
      superseded for the reading, kept for the tie-out.
      *(Done: OC-44, phase (c).)*
- [x] **6. No "not built yet" options.** Control offers only what exists; "Scout first" appears when
      scouting does.
      *(Done in phase (b): Control offers only what exists; the scouting choice says what PocketBook does.)*
- [x] **7. "Worse?" and "Material?" as two columns.** Among the worse pockets, rank by dollars. The
      engine and the workbook's formulas make the same call, proven by recalculation (S3).
      *(Done: phase (c).)*
- [x] **8. Live ordering and counts** with SORT and FILTER (Excel 365). Verified by a LibreOffice new
      enough to calculate them (24.8 or later) in the tests and in CI; where it is older the test
      fails, never skips (S2). This is a stand-in for Excel, not Excel: the workbook stays unproven in
      real Excel until the firm opens it there (design.md, Open (a)).
      *(Replaced by the redesign's rule, 26 Sep 2026: verdicts, dollars and colours live; row order as of the last Run. No SORT or FILTER.)*
- [x] **9. Scouting (4a).** A random forest on the development loans only; scikit-learn an optional
      add-on that CI installs, so the scouting path and its refusal without the add-on both run (S14);
      wide candidates; with and without the held-fixed columns; correlated pairs flagged.
      *(Done 27 Sep 2026, `docs/design.md` OC-50, `tests/test_scout.py`. "Find on 70%, confirm on the rest" is one
      Run in two steps: scouting ranks every column ticked Test it and every new column on the first 70% of the
      loans by origination date (the held-back loans' dates only are read; a test turns every held-back outcome
      over and gets the same shortlist and file), with and without the Hold fixed columns in the forest, against
      a noise floor from shuffled outcomes; suggests bins and a reference from the forest's shape and its own
      splits; flags pairs moving together (rank correlation 0.7 or more); writes the pre-spec beside the workbook
      (strata the Hold fixed columns, or `[CONFIRM: ...]` with none) and logs it before any held-back result; then
      the confirmation reads it as a saved shortlist. A new **Scouting** tab. On the first book with filler, the
      planted income / sales and UTIL rank first and are proposed, TENURE and the filler aren't, and the bins land
      on the planted cliffs (0.1 and 2 for income / sales, 0.9 for UTIL). scikit-learn is the `scout` extra, CI
      installs it, and a test simulates it missing: finding is refused in words, a saved shortlist still confirms.
      Kept, changed and dropped from `scout-vs-measure.py`: the table in OC-50.)*
- [x] **10. Screens: held for the redesign.** The test picker (outcome, shortlist, hold-fixed, the
      tests to run, in one easy place) and any layout change wait for the firm's Claude Design pass
      over the screens published 26 Sep 2026 (https://claude.ai/artifact/8duWJxayMTBtMe1GCPrvAX), so
      they are designed once rather than built twice. The firm, 26 Sep: *"good"*.

**Reordered 26 Sep 2026 after Count Bassy's pass** (C11: do known work upfront). The run's minimum and
the lean pre-spec come straight after 4b, because both reshape what 4b confirms. Bassy also noted that
the goal's first wording ("a dated outcome", "a committed pre-spec") predates OC-39 and the git
question; Goal 2's own end condition above is what counts now.

**Answered by the firm, 26 Sep 2026** (docket https://claude.ai/artifact/U5pHCYek9H7hqehzUvqs8M):
- **The redesign hold covers the launcher, the test picker and the layout only.** Items 4, 6, 7 and 8
  go ahead.
- **Strata are suggested in the label and left blank**, like every other judgment setting (OC-13).
- ~~**Lock first.**~~ *Reopened the same day.* Once explained, the firm: *"i don't think there's a
  reason to have some sort of over the top control in place to make sure we didn't mess with our own
  analysis"*. Proposed instead, and built unless the firm says otherwise: **record, don't block.** The
  Log records when the pre-spec was written, with its fingerprint, and each held-back run after it,
  in order; a pre-spec changed after a held-back run labels that run as a change. Nothing is refused.
  Git is still recorded where it exists. This is built into item 3.

## The redesign arrived (26 Sep 2026), and what it changes

The firm's Claude Design pass is committed unchanged in `docs/redesign-2026-09-26/` (its README is the
spec; `rendered.png` is the reference as rendered here). The firm, the same day, on why suggestions
could not be made: *"just select the workbook first, configure what you can, and then do the workbook
config items so that there are suggestions to be made … it's just a re-order of screens more or
less"*. The redesign's launcher steps are that order: **Extract → Set up → Choose tests → Answer in
workbook → Run.** The cuts are chosen in the launcher before the workbook is written, so the pockets
exist when Control is written, and every suggested setting shows its value there (from the default
edges), refreshed at each Run ("Last Run used").

- **Item 10 is no longer held; it is now the main build,** done in phases, one agent at a time,
  because `book.py` is one file: (a) the launcher's five steps and suggestions at Set up; (b) Start
  here, Control (Changes now / Needs a Run / chosen in the launcher / materiality panel), Columns
  (with Odd values and Learned), Look; (c) Pockets (with Three-way), Paid cost kept, Grids (with
  Prevalence), Split; (d) New variables and Record (Check with Log). House style: the tokens in the design's
  README (the hand-off's `keybank_style.py` is byte-identical to `credit-suite`'s `engine/style.py`,
  and the repo keeps that file in one place, so it is not copied here).
- **Items 4, 6 and 7 are folded into it:** the "How this tab works" note on every tab, Worse? and
  Material? as separate columns, and the Control-options clean-up.
- **Item 8 is replaced by the design's rule:** verdicts, dollars, colours and Material? are live;
  row order is as of the last Run, and the tab says so. No SORT or FILTER is needed.
- **Slicers become dropdown cells** (the design allows "slicers or dropdown cells"). openpyxl cannot
  write slicers and drops them when it re-saves a workbook, and Run re-saves it every time.
- **Phase (a) built, 26 Sep 2026: the launcher's five steps, and suggestions at Set up.** The window
  is `launcher.Flow` (every rule, no Tk) drawn by `launcher.build`, in `house.py`'s colours. Set up
  reads the extract and writes nothing; Choose tests picks the run and its cuts; Next writes the
  workbook, and Control shows the picks read-only under *Chosen in the launcher* (the two column
  limits, what's running and the saved shortlist moved there too). Columns no longer asks *Cut by
  it?* or *Split pockets by it?*. Because the cuts exist when the workbook is written, fewest loans,
  worse at and better at are worked out then, from the default edges, and written beside their
  settings ("suggested: 65, from this extract"); every Run works them out again. Nothing is chosen
  for the analyst (OC-13). A refused Run lists each cell with **Open at**; a finished one shows the
  three tiles. The product is named PocketBook in everything the analyst reads, and its workbook is
  *loans - PocketBook.xlsx*. Left for later phases: the Control restyle into Changes now / Needs a
  Run, and finding new variables on part of the loans (the launcher records the share; the Run asks
  for a saved shortlist).
      *(Built as redesign phases (a)–(d), 26–27 Sep 2026, from the firm's Claude Design pass.)*
- [x] **Phase (b) built, 26 Sep 2026: the tabs the analyst fills in.** Start here, Control, Columns and
  Look each open with the title band (INK, a Key Red rule, a red tab) and one *How this tab works*
  note grouped so it folds away (T1); gridlines off, panes frozen, the three input styles. **Start
  here** counts what is left by formula (answers needed, columns to confirm, odd values to answer,
  changes waiting for a Run), shows the pink pending line naming each waiting change, and after a
  Run the four tiles and the five largest pockets worse and material, their verdicts live; then the
  tabs in their three groups. **Control** is three blocks: *Changes now* (Setting · Your answer ·
  Comes to · Last Run used), *Needs a Run* with `Status` ("↻ Waiting for a Run" / "Same as last Run",
  against what the Run held on the hidden `_used`), *Chosen in the launcher* read-only; the suggested
  values stay beside their settings, and on the right *What each materiality level keeps* (it
  absorbs the Materiality tab), live over names each Run defines. A new-variable run isn't asked
  the profit line, and Check doesn't echo it. **Columns** holds Odd values (Treat as Real / Missing)
  and Learned (Remembered, Forget?) on each column's row, C3 blocking Run until Yes, and *Add a
  column: one divided by another* under the table (it was on Control). **Look** has the mean beside
  the median, the likely code on a red bar of its own, live bars (10 / 20 / 50) and a From / To
  regrouped by SUMIFS from 200 counted slices, red dashed edge lines fed by formula from Columns,
  and the scatters with their correlation, drawn at Set up. A Run loads the workbook once and saves
  it once, and draws Look again only when the split or its band columns change (Run 31.0 s to
  22.2 s at 17,000 × 80). Departures from the spec: *Your answer* keeps its *Or your own* cell
  beside it (reading back is unchanged); each option's meaning is a note on the setting's name rather
  than a column; the p-value keeps its name ("luck" is out, the firm, 26 Sep 2026).
- [x] **Phase (c) built, 26 Sep 2026: the result tabs (26 Sep 2026; `origination-cube/docs/design.md` OC-43, OC-44).**
  Pockets (Where it bleeds and Three-way), Paid cost kept (Losses vs revenue), Grids (with Prevalence
  under its blocks) and Split, to the spec's sections 5 to 8, in `src/origination_cube/results.py`; the
  four old tabs are taken off an older workbook at Run. Each tab: the title band, one grouped method
  note (T1: the Test column and the lone-pocket note are off the rows), lines-in-use tiles read from
  Control with "↻ N Control changes wait for a Run", then dropdowns in place of the slicers (Pockets:
  Measure, Pockets, Show; Paid cost kept: Grid; Grids: Grid and Measure; Split: Grid and Measure), each
  picking rows by INDEX/MATCH over hidden `_list`/`_views`, no SORT/FILTER/LET. Pockets' caption "N
  worse and material · N worse · N shown" is live. **Worse?** and **Material?** are separate columns;
  worse pockets rank first by dollars; order is the last Run's and each tab says so. **Option A built:**
  judged against the book counts points and dollars against the rest of the book (`excess_rest`); the
  whole-book excess stays as the tie-out. Together reads five pairs (adds strong; earns less, not from
  losses). Heat in the spec's tokens by rules that follow the Measure dropdown; loans shaded by share.
  The scatter (log x) is drawn from the table's cells, so it is live. "p-value" everywhere, never
  "luck". `tests/test_result_tabs.py` (21) and `tests/tabs.py` (reads a tab as the analyst sees it);
  old tests moved to the new layout. 20 planted bugs repointed and 24 added (310 in all), plus
  a test that a pytest run printing nothing still gets its verdict. 45 of 45 caught, each run alone. Run at 17,000 × 80: 23.2 s before, 21.7 s after.
  Departures: the scatter is live (the spec said as of the Run); "Earned before losses" and "Earns
  less, not from losses" are allowed past the old no-"earns" test, as the spec's own words; Split adds
  a Measure dropdown and keeps As odds; the other comparison's dollars leave the rows (they stay on
  `_pockets` and the command line). Not checked: real Excel.
- [x] **Phase (d) built, 27 Sep 2026: New variables and Record (27 Sep 2026; `origination-cube/docs/design.md` OC-45 to OC-48).**
  **New variables** (black tab, spec section 9) replaces the Confirmatory test tab, in `confirm_tab.py`: one row per
  group of the pre-spec's column against its reference, **Found** (development, nothing held fixed), **Confirmed**
  on the held-back loans with *Holds up?*, **Confirmed with the held-fixed columns** (the pre-spec's strata) with
  *Still holds?*, then Excess (charge-offs above the group's share on the held-back loans, scaled to the book; bad
  loans without GCO), *Material?* and *In words*; the tiles (Outcome, Candidates, Held fixed, Loans found and held
  back, Material at, live) and a bar chart (Confirmed INK, held fixed KEY_RED, Found STONE when shown) with a dashed
  red line at worse at. The firm's lean pre-spec ruling is built: each input reported with and without the columns
  held fixed (the same conditional logistic regression with every loan in one pocket); the pre-spec needs no `hold`
  list, as its strata are the held-fixed columns, and old pre-specs read unchanged. A saved shortlist hides the
  Found columns and Record names the file. Every statistic the old tab had (B3, B4, the block test, B5 with its
  live range, 4e) is kept under the chart, on both sets of loans, with and without the columns held fixed.
  **Record** (grey tab, section 10, `record.py`) merges Check and the Log: This Run | Settings, Does it add up |
  Tests used, Left out | Every Run, each with the ONYX band, a CANVAS row, one label width and rows one line high
  (a long line goes on in the rows under it and reads back whole); Settings has in use now beside the last Run's,
  shaded while they differ. The Log is kept on the hidden `_log`, so a refusal shows at once; an older workbook's
  Log carries over. **Record, don't block:** the Log records a pre-spec when first read (fingerprint, the date in
  the file, its commit), each held-back run after it in order, and labels a run on a pre-spec changed after a
  held-back run. **Control** asks a new variable only worse at, materiality, confidence and the bands (the bleed's
  floors, better at, judged against, the catch rate and the allowance are hidden); worse at is suggested from the
  confirmation's own groups. **Memory:** the 2.5 GB pre-spec Set up was the harness's Set up without the launcher's
  choices, which cut all 74 columns (1,248 grids) for a suggestion pass run as a bleed; a new variable's Set up now
  builds no grid: 92.7 s and 2.41 GB to 12.8 s and 0.27 GB. The launcher's route at 17,000 × 80, before and after:
  pre-spec Set up 11.0 s / 0.23 GB and 14.0 s / 0.29 GB to 9.8 s / 0.22 GB and 13.8 s / 0.29 GB, Run 4.0 s / 0.21 GB
  both; bleed Set up 12.7 s to 13.2 s (0.28 GB), Run 21.3 s to 21.1 s (0.27 GB). 664 tests (23 new; the tests that
  read Check, the Log and the Confirmatory test read Record and New variables). 18 planted bugs added and 8 repointed, 1 retired (it planted into a sentence no tab shows now): 327 in all. Every planted bug whose test was rewritten or read through a rewritten helper was put back, each alone: 110 of 110 caught, 3 after their tests were strengthened.
  Departures: Found is always hidden today (every new-variable run confirms a saved shortlist); Record's rows wrap
  where a formula or label needs it, and a pair shares row heights; the tab keeps a short folding note; "p-value",
  never "luck". Not checked: real Excel.
- [x] **Items 5 and 7 done with it:** Option A (OC-44) and Worse? / Material? as two columns. Item 4's T1
  sweep is done for the result tabs.

---

# Goal 3 (proposed 27 Sep 2026; silence approves): ready for first use at the bank

Goal 2 is done: all ten items ticked, the last (scouting) merged at 304e933e. Proposed on the docket
(https://claude.ai/artifact/U5pHCYek9H7hqehzUvqs8M), and what the session proceeds with unless the firm
says otherwise:

- [x] **1. The rename sweep.** Folder, package, command and file names to PocketBook; workbooks and cube
      files made under the old name still read.
      *(Done 27 Sep 2026: `origination-cube/` is `pocketbook/`, `src/origination_cube/` is `src/pocketbook/`,
      the command is `pocketbook`, the launcher `PocketBook.pyw`, the memory `$POCKETBOOK_MEMORY` or
      `~/.pocketbook/`. Still read: `$CUBE_MEMORY`, anything kept under `~/.origination-cube/` (memory,
      launcher choices), a workbook named `- Origination Cube.xlsx` (Set up carries its answers over; picked
      as the extract it is refused). Left as they were: entries above dated before the move, the dated
      walk-throughs, audit and redesign folders, and the shuffle test's seed text, which would move every
      p-value. 4 tests and 4 planted bugs added, 371 in all.)*
- [x] **2. A walk-through as the analyst** on the synthetic book, end to end through the launcher's five
      steps, both run kinds, writing the step-by-step procedure with screenshots and the defects only a
      screen shows (canon's walk).
      *(Done 27 Sep 2026: `docs/walkthrough/2026-09-27/PROCEDURE-pocketbook-analyst.pdf` and
      `WALKTHROUGH-DEFECTS.md`. 12 defects, none caught by the suite; 11 fixed with a test and a planted bug
      each, 11 design questions (A to K) left for the firm with a recommendation. 735 tests, 385 planted bugs.
      BACKLOG §6d has the list.)*
- [x] **3. The bank-machine checklist:** numbered steps to install, open in real Excel 365 and check the
      live parts (dropdowns, verdicts, colours, the Look lines), with what each should show.
      *(Done 27 Sep 2026: `docs/BANK-MACHINE-CHECKLIST.pdf` (`.md` the source, `.html` beside it), and
      `tools/bank_kit.py`, which makes `PocketBook.zip` and the offline add-ons for Windows. Every command run
      here or its Linux counterpart; Excel's behaviour marked "check this" throughout. 5 tests in
      `tests/test_bank_checklist.py`. BACKLOG §6d has the detail.)*

**What would end it:** all three done, CI green, and the checklist handed to the firm.
**Open with the firm:** Test 4 at 3% uplift: keep answer C's label *Losing more, profit holding*, or leave it blank
(asked on the docket, 27 Sep 2026; the test expects the label until answered). *(The wording "Earned before losses" /
"Earns less, not from losses" was answered 27 Sep: "Fine for now", kept.)*
**Next:** nothing new is built until the firm has been to the bank machine; what they find decides Goal 4.
