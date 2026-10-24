# Origination cube: defects from the walk of 25 Sep 2026

**What was walked:** the analyst's route end to end, as an analyst would do it. Synthetic extract, Control tab filled in Excel, `cube init`, the cube file checked and confirmed, `validate`, `run`, then six wrong turns. The procedure is `PROCEDURE-origination-analysis.pdf` beside this file.

**Against which code:** commit `360a71e` (25 Sep 13:19 UTC). Every command ran between 13:23:35 and 13:26:15. Another session began changing `config.py`, `control.py`, `engine.py`, `profile.py` and `settings.yaml` at 13:26:53, including a new cube-file format (`columns:` with `means:`). **Defects 6, 7 and 8 are about the old cube-file format and may already be superseded.** The rest are in files that weren't touched (`cli.py`, `stats.py`), or on the Control tab, and should be re-checked against the new build.

**The suite:** `pytest -q` gave **87 passed** at that commit (the README says 86). All 87 pass with every defect below present, so none of them catches any of these. `tools/mutation_check.py` was not run.

**The result:** the tool finds the planted pocket. Under 653 / Broker is first in every FICO grid for bad-loan share, booked-weighted bad rate and GCO. With the LOB's own cut points it is under 620 / Broker at 6.3x. The arithmetic ties out (44 of 44 checks). The defects are in what the screens promise and what the analyst is told.

Ranked by what each would cost the firm or the bank with a real extract.

---

## 1. Five Control-tab answers are required, then silently dropped

**What I did:** filled every shaded cell (`step-04-control-filled.png`). Answers: fewest loans with a loss = 10 (C16), materiality = 1% of losses (C18), judged against = the rest of its band (C20), loan age = every loan (C8). The many-tests allowance (C26) stays on its preset.

**What the screen said:** the rows are shaded as "still needs an answer", and `cube init` refuses until they're answered (`wrong-B-empty-shaded-cell.png`). "Takes effect" says **live** or **re-run**. `cube control --read` echoes them all back (`step-05-read-back.png`).

**What was actually true:** `profile.py` (lines 340–345 at `360a71e`) writes only `min_units`, `worse_at`, `better_at`, `confidence` and `power` into the cube file. Loan age, fewest losses, materiality, judged-against and many-tests appear nowhere in `cube.yaml` (`step-07-cube-as-written.png`, lines 42–47). The run output confirms this:
- **Fewest losses = 10 is not applied.** `653 to under 684 / Online` has 9 bad loans (7.14% of 126). It is still tested and gets a word: `vs rest of book 1.54x (p 0.2887): gap could be luck` (`step-11-run-bleed-list.png`).
- **Materiality = 1% is not applied.** Every grid prints the materiality table with "(the level is your call)" and no line drawn.
- **Judged against = rest of band changes nothing.** Both comparisons still print "worse than benchmark", and nothing says which one flags. The option text claims "this picks the one that flags".

`design.md` records these five as "Not wired yet". Nothing the analyst sees says so: not the tab, the cube file, nor the run.

**Cost:** the analyst believes a 10-loss floor and a materiality floor were applied. A pocket with 9 losses goes to the LOB as tested.

**Fix:** until they are wired, either stop requiring these rows, or have the tab (column F), the cube file and every run say "recorded, not yet applied". Don't mark them "live".

## 2. RANR is ranked as a loss, and nobody is asked which way it runs

**Where:** `cube run`, every `ranr_rate` grid (`defect-ranr-direction.png`).

**What the screen said:** `Where it bleeds: excess RANR_AMT over the topline rate, largest first`, then `share of losses / share of volume 1.35x` and `worse than benchmark` for the pockets with the **highest** RANR per booked dollar. On the loan-amount grid, `under 15327.1 / Online` is `3.90x (p <0.0001): worse than benchmark` for RANR.

**What's uncertain:** the repo never says what RANR is or which direction is bad. The Control tab, `cube init` and the cube file never ask. If the bank's RANR is revenue-like, where higher is better, this list names the best pockets as the worst. On the synthetic book, RANR is a flat per-loan amount (`synth.py:67`), so small loans score high per dollar. That is an artefact, and it is flagged at p<0.0001.

**Cost:** a RANR pocket quoted to the LOB as bleeding could be the reverse.

**Fix:** ask the direction once (on the Control tab, or as an init question). For RANR, say "share of RANR" rather than "share of losses".

## 3. Bad own values pass the Control tab and `cube init`, then are refused against the YAML, not the cell

**What I did:** typed `95` for 95% in D24 (confidence). Separately, typed `0.9` as the "worse" multiple in D21, and `1.4x` in D21.

**What the screen said:**
- **On the tab, no signal.** `95` shows "Your own value … (a share between 0.5 and 0.999)" with no flag. `1.4x` shows in *In use* as if fine (`wrong-C-sheet-shows-no-problem.png`). Column D has no data validation.
- **`cube control --read` and `cube init` accept `95` and `0.9`** and write them into the cube file (`wrong-E-95-accepted-by-init.png`). `read_control` checks only that an own value is a number, never its range. `1.4x` is refused, and the cell is named.
- **`cube validate` then refuses** with `benchmark.confidence must be a share between 0.5 and 1 … got 95` (`wrong-E-95-refused-by-validate.png`). That names a YAML line, not Control!D24.

**Cost:** the analyst fixes `cube.yaml`. The next `cube init --control` writes 95 back, and they fix it again.

**Fix:** range-check own values in `read_control` using the bounds the tab already prints, and name the cell. Add data validation to column D.

## 4. The bleed list prints a Python `None`, and a p-value for a pocket it says is too small to test

**Where:** `cube run`, grid `fico x channel - gco_rate`, pocket `(missing by rule) / Broker` (`defect-none-in-output.png`):

```
    (missing by rule) / Broker: 23,304 over, 18 loans
      share of losses / share of volume 2.14x
      vs rest of book 2.17x (p 0.5831): too few loans to test
      vs rest of band  (p 0.3089): None
```

**What's true:** the rest of that band (Branch and Online loans with no score) has zero GCO, so there is no multiple. `engine.reading_of` returns `None`, and `cli.report` prints it raw. `_x(None)` leaves the double space. A p-value is printed beside "too few loans to test", on a pocket of 18 loans against a minimum of 30.

**Fix:** print a sentence ("no multiple: the rest of its band has no losses") and drop the p-value when the pocket isn't tested. `cli.py` was not touched by the in-flight changes, so this is still present.

## 5. Typing your own number into the Choose cell puts `#N/A` in two cells

**What I did:** typed `1.4` into C21 (Choose) instead of D21. Excel allows it, because the list validation has `showErrorMessage=False`.

**What the screen said:** *In use* = `#N/A`, *What it means* = `#N/A` (`wrong-D-sheet-shows-NA.png`). The CLI then refuses clearly: `Control!C21: '1.4' is not an option` (`wrong-D-typed-in-choose-cell.png`).

**Fix:** turn on the validation's error alert, or wrap the E and F formulas so they say "type your own value in the next column". This is the most natural wrong turn on the tab.

## 6. Odd values in the outcome and GCO columns aren't raised as questions *(old cube-file format)*

**What's true:** `BAD_FLAG` has one row = `2`, and `GCO_AMT` has one `#N/A`. `cube init` mentions them only in trailing comments ("1 other value(s), counted when read"). The `questions:` list holds only FICO -9999 and negative RANR (`step-07-cube-as-written.png`, lines 12, 26, 52–53). OC-7 says odd values are raised as questions. A `2` in a yes/no outcome is the most important one to raise.

**Mitigation:** the run does count both under "Left out of a figure" (`step-10-run-top.png`).

## 7. `cube init` cuts by the columns it has just named as outcomes *(old cube-file format)*

**What's true:** `GCO_AMT` and `RANR_AMT` are written as bands and `BAD_FLAG` as a dimension (`step-07-cube-as-written.png`, lines 26, 27, 31). The file's own comment says "GCO and RANR are left out for you once they are named under measures", but they're named as required columns, not measures. `design.md` says "Once GCO, RANR and the outcome are named, they are left out of the bands and dimensions."

**Mitigation:** the engine drops all three at run time with a WARNING each (`step-09-validate.png`, `wrong-F-bad-flag-left-in.png`), so no figure is wrong. The analyst is still asked to judge lines that don't matter, and every run warns about the tool's own file.

**Fix:** write them under "Not cut by", with the reason.

## 8. `cube init`'s last line points at markers that aren't there *(old cube-file format)*

**What the screen said:** `Next: answer every [CONFIRM: ...] in the file, then cube validate.` (`step-06-init.png`)

**What's true:** with a Control tab, the file has no `[CONFIRM: ...]`. What blocks the run is `columns_confirmed: no`, and the Next line never mentions it. Following it leads straight to a refusal (`wrong-A-validate-before-confirming.png`). The refusal is clear, so this costs one round trip.

## 9. The recommended bands hide the planted pocket's edge, and the edges read oddly

**What's true:** 5 equal-loan bands "(recommended)" put FICO edges at `653, 684, 714, 745.4` (`step-10-run-top.png`). The pocket shows as under 653 / Broker at 3.42x on GCO. With the LOB's 620/680/740 it is under 620 / Broker at 6.33x (`step-12-run-own-edges.png`). It ranks first either way, but at half its size. `design.md` knows this ("Ten bands, or your own edges, sharpen it"), yet nothing on the tab or in `cube init` suggests typing the LOB's own cut points. A `745.4` edge on an integer score, and loan-amount edges like `15327.1 to under 26463.9`, look like software, not a buy box.

**Fix:** round the edges for integer columns and format dollar edges. On the tab, point to own edges when the LOB has them.

## 10. The materiality table on a loan-count rate is in loans but labelled "book losses"

**Where:** every `outcome_loans` grid (`defect-materiality-count-rate.png`): `0.5% of book losses (0): 5 pocket(s)`, `1.0% of book losses (1)`. The figures in brackets are counts of bad loans (1% of 96 ≈ 1), and a floor of 0 keeps everything.

**Fix:** label it "bad loans" for count rates, or leave the table off them.

## 11. The readings don't say which way, and "benchmark" is never defined

- `under 653 / Online … vs rest of band 0.57x (p 0.1010): gap could be luck`. The pocket is **better** than its band, but the words are the same as for a worse pocket, and it sits in a list headed "Where it bleeds" (`step-11-run-bleed-list.png`).
- "worse than benchmark" never says what the benchmark is. On this run it means 1.4x the comparison, significant at 95%.

## 12. Control tab: layout and wording

All of these are in `step-03-control-blank.png` and `defect-header-and-key-column.png`, except where another capture is named.

- **Header collision:** D4 "Or enter your own" runs into E4 "In use" and renders as "Or enter your ownIn use". In Excel, D4 clips because E4 is full.
- **The machine column shows.** Column H, headed `key`, lists `min_age_months`, `compare_to`, `many_tests` and so on. It is outside the print area but not hidden, so it's on the analyst's screen.
- ***In use* shows codes:** `pairs`, `equal_loans`, `bh`, `time`, `peers`, `1% of losses`.
- **Row 24's explanation is a fragment:** "The usual standard. About 1 in 20." It doesn't say 1 in 20 of what (`defect-row24-fragment.png`).
- **It refers to tabs that don't exist:** "the Where to look tab ranks every pocket" (F6), and the option "Only the pairs listed on the Cuts tab".
- **Two shades, one legend.** The grey *n/a* cells are shaded too, but the legend says "Shaded = still needs an answer". On row 20 a grey *n/a* cell sits inside the peach answer area.
- "Needs enough seasoned recent loans" (row 28) reads as a contradiction.

## 13. `cube control --read` answers in machine names

`grids pairs`, `compare_to peers`, `many_tests bh`, `proof time` (`step-05-read-back.png`). The analyst answered questions in words, so the read-back should use the same words.

## 14. `cube synth` writes a cube file with the calls already made, and it runs

`demo/cube.yaml` carries `min_units: 30`, `worse_at: 1.25`, `better_at: 0.8` and `confidence: 0.95`, and has no `columns_confirmed` line. `cube validate demo/cube.yaml` is **accepted** as-is. That is contrary to OC-13 (judgment settings never pre-chosen) and OC-15 (confirm the columns). It's only a demo, but it teaches the analyst that the calls come pre-made.

## 15. Small

- `Left out of a figure`: "1 rows" (`step-10-run-top.png`).
- The `(blank)` row in the loan-amount grids prints a label and no figures (the one loan with a blank amount is out of every booked-dollar rate).
- The README says 86 tests, and the suite has 87.

---

## What I couldn't check

- **Real Excel.** The tab was rendered in LibreOffice Calc (headless), which recalculates the formulas. Excel's drop-downs, the frozen pane and exactly how D4 clips weren't seen. Cells were filled with openpyxl, standing in for typing.
- **RANR's meaning** (defect 2). It is not defined anywhere in the repo.
- **The in-flight build.** Everything here is `360a71e`. The new cube-file format was not walked.
- **`tools/mutation_check.py`** was not run, because the source was changing underneath.
- **Scale.** The walk used 2,000 loans, and the planted pocket held 53 of them. Larger books weren't walked.

---

## Where each defect stands (25 Sep 2026, later the same day)

| # | Status |
|---|---|
| 1 | **Fixed.** Loan age, fewest losses, materiality, judged-against and the many-tests allowance are carried in the cube file and applied. Each has a hand-checked test in `tests/test_calls.py` and a mutation proving that test can fail. Settings nothing applies yet (which cuts, drill depth, proof) are off the tab. |
| 2 | **Fixed by the firm's answer:** *"RANR is a revenue metric - so it is profitability to some degree. bigger is better."* RANR's bleed is now a shortfall under the book's rate, and a pocket earning less reads worse. |
| 3 | **Fixed.** Every typed value has a range. Excel refuses it as it's typed, and the tool refuses it naming the Control cell. |
| 4 | **Fixed.** No Python `None`: a missing comparison says why. |
| 5 | **Fixed.** The dropdown now refuses typing, and both formula cells use IFERROR with a plain sentence. |
| 6 | **Fixed in the new format.** Stray values (a 2 in a 0/1 outcome, text among numbers) are on the look-at-these-first list. |
| 7 | **Fixed in the new format.** Outcome, GCO and RANR are never cut by. |
| 8 | **Fixed in the new format.** The Next line names `columns_confirmed`. |
| 9 | **Open, and the firm's call.** Band count and edges are settings; learning a column's usual edges is proposed. |
| 10 | **Fixed.** The materiality table says what it counts in (loans, or dollars of which column). |
| 11 | **Fixed.** Readings say which way: worse, better, "worse, but could be luck". A flag line says which comparison decided it. |
| 12 | **Fixed.** The header fits, the key column is hidden, "In use" shows words, and the 95% line is a sentence. There are no references to tabs that don't exist, and the n/a cells aren't shaded. |
| 13 | **Fixed.** Read-back prints each question and the chosen words. |
| 14 | **Fixed.** `cube synth` writes only the extract; the route starts at `cube init`. |
| 15 | **Fixed.** Plurals; the README count. The (blank) row in the loan-amount grids is correct (one loan with a blank balance) and stays. |

Not yet re-walked: a second walk follows the workbook-and-launcher front end.
