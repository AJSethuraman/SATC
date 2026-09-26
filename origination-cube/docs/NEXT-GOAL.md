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
none of the three.)*

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
