# Origination cube: defects from the second walk (25 Sep 2026)

**What was walked:** the no-commands route of ruling OC-22:
1. The Tkinter window.
2. **1. Set up from this extract**.
3. The workbook's Start here, Control, Columns and Odd values tabs.
4. **2. Run the cube**.
5. The Where it bleeds, Grids, Check, Log and Learned tabs.
6. **Set up** again, and **Forget** on Learned.

Then six wrong turns. The procedure is `PROCEDURE-origination-workbook.pdf` beside this file.

**Against which code:** commit `f2f1032` (14:02 UTC), frozen with `git archive` into scratch after `src/` changed under the walk at 14:08. Commit `8ea7b3d` (14:14) landed mid-walk: it adds "Cut by it?", heat-map grids and plainer copy. **Defects 1 to 12 were re-checked against `8ea7b3d` and all reproduce** (`driver/` has the scripts; the re-check used `book.set_up` / `book.run` directly, not the window). Defects 13 to 16 are about screens `8ea7b3d` redrew, so they need a look on that build.

**The suite at `f2f1032`:** `pytest -q` gave **126 passed**. `tools/mutation_check.py` exited 0, with every mutation caught. All 126 pass with every defect below present, so none of them catches any of these.

**The result:** the planted pocket comes out on top.
- **Recommended bands:** fico under 653 / Broker is first for the bad-loan share (15.76% against 4.58%, 4.16x the rest of the book), for the booked-weighted bad rate and for GCO.
- **The LOB's own edges (620, 680, 740):** it's under 620 / Broker at 34.4%, or 9.01x.
- **RANR** reads as revenue: its rows are shortfalls, and a multiple under 1 is flagged worse.
- **Tie-out:** 44 of 44 checks agree.

The defects are in where the workbook gets its data, what Excel will do to typed values, and what the buttons do to what's already there.

Ranked by what each would cost the firm or the bank on a real job.

---

## 1. A workbook copied to another folder silently runs the old folder's extract

**What I did:** copied the finished workbook into a new folder (`Q4/`), put a new 3,000-loan extract beside it under the same file name (`Consumer book Q3.csv`), picked that extract in the window, and pressed Run. This is how an analyst starts next quarter from last quarter's folder. Bank extracts often keep the same file name every month.

**What the screen said:** "Ran on **5,000** loans; 66 tie-out checks agree", then the usual *Worst for* lines. The Extract box names the Q4 file (`wrong-F-copied-folder-runs-old-extract.png`).

**What was true:** the workbook's hidden `_about` tab stores the extract's **absolute path** at Set up, and `book.run` reads that path (`book.py:457`). It never reads the extract the window names. It ran the old folder's 5,000 loans and wrote those results into the new folder's workbook. Nothing warns. The only sign is a loan count the analyst would have to notice.

**Cost:** an analysis delivered to the LOB on the wrong book, from a workbook sitting beside the right one.

**Fix:** run the extract beside the workbook (the one the window names). Or refuse when `_about`'s path isn't that file, and name both paths.

## 2. Band edges typed without spaces become one edge, and every screen prints it back as three

**What I did:** typed the LOB's FICO cut points in Columns, Band edges, as `620,680,740`. In Excel's usual (US) settings, that is the number 620,680,740 (thousands separators), and Excel displays it as `620,680,740`. The walk put the number 620680740 in the cell, which is what Excel stores.

**What the screen said:**
- **Window:** "Worst for Outcome, share of loans: fico **under 620,680,740** / channel Broker" (`wrong-A2-edges-typed-without-spaces.png`).
- **Check:** "Band edges used: fico **620,680,740**" (`wrong-A2c-check-edges.png`).

Both read exactly like the three edges the analyst meant.

**What was true:** one edge at 620 million. The FICO grid has a single band, *under 620,680,740*, holding every scored loan (`wrong-A2b-grid-has-one-band.png`). So the "worst" pocket is simply the Broker channel. No check compares an edge with the column's own range (300 to 850 for a FICO).

**Cost:** the LOB is told the cut was at 620/680/740 when it wasn't cut at all.

**Fix:** refuse an edge outside the column's values, and name the cell. Print edges with a separator that can't be misread (for example `620 | 680 | 740`), and say how many bands were made.

## 3. Picking 95% from the dropdown will probably be refused in Excel *(needs one check in Excel)*

**What's likely:** Excel treats a dropdown pick like typing. So a list item written `95%` goes into the cell as the number 0.95, with a percent format, and it still shows as 95%. That is the same behaviour that turns list items like `1-2` into dates.

**What the tool does with it:** the walk put 0.95, formatted as a percentage, in Control!C22.
- **The tab:** shows **95%** in Choose, with *In use* = **not an option** and "That isn't one of the options. Pick from the list..." (`defect-3-95-read-as-095.png`).
- **The window:** refuses with "Control!C22: 0.95 is not an option for 'How sure a difference must be before it counts'."

`read_control` compares `str(chosen)` with the label, and `"0.95"` ≠ `"95%"`.

**Which rows:** every option written as a bare percentage.
- confidence: 90%, 95% and 99%
- power: 90% and 50%

`80% (recommended)` survives because of its suffix. Numbers like `30` work, because `str(30) == "30"`.

**Cost:** if confirmed, the most common answer to a required setting can't be picked, and the screen shows the analyst's own choice as "not an option".

**Fix:** match a numeric cell against each option's value, not only its label. Or give the percent options a label Excel won't parse, like "95 percent". First, confirm in Excel: it takes about five minutes.

## 4. "Checked every column? Yes" carries over to columns nobody has seen

**What I did:** added two columns (CURR_STATUS and DTI) to the extract, as a refreshed file with the same name, pressed Set up, then Run without opening the workbook.

**What the screen said:**
- **Set up:** "2 thing(s) to look at first". Neither is a new column.
- **Columns:** C3 still reads **Yes**, and the two new rows aren't shaded (`wrong-E-new-columns-already-confirmed.png`).
- **Run:** it went through, and "Remembered **11** confirmed answers" (`wrong-E2-new-columns-run.png`).

**What was true:** the memory now records CURR_STATUS = servicing and DTI = dti as **confirmed** on 2026-09-25. No person looked at either (ruling OC-15: suggested, then confirmed by a person). A wrong guess on a new column would be learned as confirmed. It would then outrank every hint on every later extract (OC-17).

**Fix:**
- Clear C3 when Set up finds a column that wasn't on the tab before.
- Shade new columns under Look first ("new since last set up").

## 5. Forget on the Learned tab does nothing for any column in the workbook you run

**What I did:** set CHANNEL to **Forget** on Learned, then saved and ran (`step-18-learned-forget-marked.png`).

**What the screen said:** the run succeeded with "Remembered 9 confirmed answers", and nothing said anything was forgotten (`step-18b-after-run-with-forget.png`). On Learned, CHANNEL is back as **Keep / category**, and *Times* is reset to 1 (`step-18c-learned-after-run.png`).

**What was true:** `book.run` calls `memory.apply_review` (which drops CHANNEL) and then, in the same run, `memory.remember(cfg)`. That re-learns every column on this workbook's Columns tab, which still says CHANNEL = category and C3 = Yes (`book.py:472-473`). The Learned tab's own sentence ("it's dropped the next time you press Run") is true for one line of code.

**Cost:** OC-18's "intuitive way to prune" doesn't prune. The analyst is told nothing, and the only trace is a reset counter.

**Fix:** a Forget on this workbook's Learned tab should stop that column being re-learned from this run. The column should go back to its un-remembered suggestion and be shaded under Look first. The window should also list what was forgotten, `column → meaning`.

## 6. Pressing Set up again deletes the last run's results and the whole Log

**What I did:** after a good run, pressed **1. Set up from this extract** again. The README invites this: "Press Set up again at any time: answers already given are kept."

**What the screen said:** the same three lines as a first Set up, ending "Next: fill in the shaded cells on Control and Columns" (there were none left) (`step-17-set-up-again.png`). Start here now says **Last run: not run yet** (`step-17b-start-here-after-set-up-again.png`).

**What was true:** `set_up` builds a new workbook from scratch. It keeps the answers but not Where it bleeds, Grids, Check or Log. The tabs are gone, the Log's history of runs and refusals with them, and "not run yet" is false.

**Cost:** the numbers the analyst was about to send are gone, after pressing a button that was described as safe.

**Fix:** keep the result tabs and the Log through Set up, marked "from the run of <time>, before this set up". At the least, say in the window that Set up clears the results.

## 7. The materiality call has no evidence in the workbook, and its line has no unit

**What's true:**
- **The call is required.** Control makes "Smallest excess loss worth reporting" a required call, and ruling OC-13 says the tool gives the evidence.
- **The evidence is missing.** `design.md` shows it: for every grid, what each level (0.5%, 1%, 2%, 5%, 10%) would keep. The command line printed it. **No tab of the workbook has it.**
- **Check's line has no unit.** It gives *Materiality line: outcome_loans* **2**, *outcome_booked* 75,288, *gco_rate* 41,976 and *ranr_rate* 4,767 (`step-14-check.png`), with machine names and no unit. The first is loans, and the others are dollars of different columns.
- **The rounding contradicts itself.** The loans line is 2.29, shown as **2**. A pocket whose excess shows as **2** is marked *below the line* on Where it bleeds (orig_bal 38,549 to under 49,398 / Branch), so the same number sits either side of the line.

**Cost:** the analyst makes the materiality call blind, which is the call the firm said is theirs to make with evidence.

**Fix:**
- Put the "what each level would keep" table on Check or a tab of its own.
- Label each line in words, with its unit.
- Show the loans line to one decimal place.

## 8. A run refused because the workbook is open still updates the memory and the "what ran" record

**What I did:** locked the workbook, which stands in for having it open in Excel, and pressed Run.

**What the screen said:** "... is open in Excel. Close it, then press Run again." (`wrong-D-run-while-open.png`). That's correct and in words. Set up says the same (`wrong-D2-set-up-while-open.png`).

**What was true:** before trying to save, `book.run` had already done three things:
- applied any Forget rows
- remembered every column again (*Times* went from 4 to 5 in `memory.yaml`)
- rewritten `<book> - what ran.yaml`, whose first line is "Exactly what the last Run used"

So the record describes a run whose results never landed.

**Fix:** check the workbook can be written before running. Or remember and write the record only after the save succeeds.

## 9. Start here's "Where things stand" is only worked out at Set up

After every Control answer was given and a run succeeded, Start here still said **Calls still to make on Control: 8** and **Things to look at first on Columns: 5** (`step-15b-start-here-after-run.png`). Only *Last run* is updated by Run. The first tab the analyst opens says there are eight calls left.

**Fix:** recount on every Run, or replace the counts with formulas over the Control and Columns cells.

## 10. Columns says to answer odd values "at the bottom". The answers are on another tab

FICO and RANR_AMT read: "Used as recorded until you answer it **at the bottom**." (`step-06-columns.png`). There is no bottom. The answers are on the **Odd values** tab. The wording is left over from the old cube file, where `questions:` were at the bottom (`meanings.py:335`). It is still present on `8ea7b3d`.

## 11. "What a pocket is judged against" says to enter your own value in column D, which that row doesn't take

Both the window and the tab's *What it means* cell say: "needs an answer. Pick one, or enter your own in column D." Row 18's column D is a grey *n/a* (`step-05-control-blank.png`, `step-08-run-before-answering.png`). The same sentence is used for every row, whether or not the row has an own-value cell.

## 12. Meaning descriptions cut off at their first comma, and the dropdown shows only codes

`settings.yaml` writes the meanings as YAML flow maps (`{means: category, says: a category to cut by (channel, state, product), ...}`). The comma ends the value. So:
- `category` reads "a category to cut by **(channel**"
- `unknown` reads "not known yet"; the rest, "so not cut by until you say what it is", is lost

The first shows on Columns as "Remembered: you confirmed this as a category to cut by (channel on 2026-09-25" (`step-17d-columns-remembered.png`).

Separately, the *What it is* dropdown offers bare codes (key, booked, gco, ranr, fico, score, dti, servicing, amount, category, id, unused, unknown). What each code means is on a hidden tab. The Learned tab shows the same codes.

**Fix:** quote the `says:` strings. Show "code: what it means" in the list, or put the meaning beside the cell.

## 13. Where it bleeds uses machine words and unlabelled units *(f2f1032; redrawn in part on 8ea7b3d)*

Seen in `step-12-where-it-bleeds.png`:
- **Names:** Band and Dimension show `fico`, `orig_bal`, `channel`, not the column names FICO, ORIG_BAL and CHANNEL. The window's *Worst for* lines do the same.
- **Two headers:** there are two columns headed **Pocket**.
- **Excess has no unit.** It is loans for the bad-loan share (the planted pocket's excess shows as "37") and dollars elsewhere, in the same column.
- **p:** it is unexplained and printed as `0.0000` when it is below 0.00005.
- **Untested pockets still get p-values.** "too few losses to test" rows still show them (`(missing by rule) / Broker`: p 0.9883, 0.9795). That's first-walk defect 4's second half, which is still open.
- **A "better" flag in the bleed list.** *fico under 653 / Branch* is material "yes" and flagged **better** in a list titled as pockets losing more than their share. It's right, since the pocket is worse than the book and better than its band. But the Flag heading doesn't say "against the rest of its band"; only the subtitle does.
- **RANR's "Smallest gap it could show"** is printed as 1.28x and similar, above 1, for a measure where the bad direction is below 1.
- **(missing by rule)** is the label for the -9999 FICOs the analyst answered as missing. "Missing, as you answered on Odd values" would say where it came from.

## 14. Grids don't say that RANR is better when higher *(f2f1032; Grids redrawn on 8ea7b3d)*

The RANR blocks look like the loss blocks. In `step-13b-grids-ranr.png`, *under 16,126* is **3.11x** the book in the RANR block, which is the biggest number on the page, and it's the best pocket, not the worst. Block headings are formula-shaped (`(SUM(RANR_AMT) / SUM(ORIG_BAL))`).

## 15. Window wording

- **Scrolled out of sight.** After a Run with nothing answered, the ninth problem, `Columns!C3 ...`, is below the visible box (`step-08-run-before-answering.png`). It's the only one not on Control.
- **Generic plurals:** "5 thing(s) to look at first", "1 value(s) are neither 0 nor 1", "1 value(s) aren't numbers".
- **Code formatting:** backticks in a message: "band edges for \`FICO\` must be rising numbers" (`wrong-A-edges-not-rising.png`).
- **The range said twice.** "needs a share between 0.5 and 0.999, **from 0.5 to 0.999**; got 95" (`wrong-B-out-of-range-numbers.png`). The same doubling is in Excel's own error box for that cell. For a setting whose options are written 90% / 95% / 99%, "type 0.95, not 95" would help more.
- **Next line never changes.** After Set up again, "Next: fill in the shaded cells on Control and Columns" appears with nothing left to fill.
- **Doesn't name the column.** Wrong turn C's message is clear, but it doesn't say which change caused it (CHANNEL, Columns!C8) (`wrong-C-channel-marked-servicing.png`).
- **A dangling reason:** a new column's reason is "name contains 'status'; " with nothing after the semicolon (`wrong-E-new-columns-already-confirmed.png`).

## 16. Layout and print

- **Check:** setting labels are clipped mid-word ("How much worse than its comparisor", "How sure a difference must be befor"). Column B is 40 wide with no wrap, and C is filled, so they're clipped on screen as well as on paper (`step-14-check.png`).
- **Log:** no page setup. It prints the timestamps on one page and the messages on the next, cut off at the right (`step-15-log.png`). It has no heading.
- **Columns:** the Blank percentage runs into Samples ("0%L0000000").
- **Learned:** no title bar, unlike every other tab.
- **Fonts:** headers set bold with no font name print in a serif face in LibreOffice. Not seen in Excel.
- **A leftover record file.** `<book> - what ran.yaml` appears beside the extract with no mention on any tab. The analyst will find a YAML file in the client folder.

---

## What I couldn't check

- **Real Excel.** Everything in the workbook was set with openpyxl and seen through LibreOffice. Not seen:
  - how dropdown picks are stored (defect 3 rests on this, and defect 2 on how "620,680,740" is parsed as it's typed)
  - the validation pop-ups
  - conditional shading in Excel
  - frozen panes
  - column widths on screen
- **Windows:**
  - **Open the workbook** (`os.startfile`) wasn't pressed
  - the Windows file dialog
  - the Segoe UI font
  - an Excel lock on an open file; this was simulated with `chattr +i`, which raises the same `PermissionError`
- **The current build's redrawn screens** (`8ea7b3d`: heat-map Grids, Cut by it?, the new copy). Defects 1 to 12 were re-checked on it without the window. Defects 13 to 16 weren't.
- **Scale.** 5,000 loans. The run took about 1.4 s in the window.

---

## Where each first-walk defect stands (seen on screen, f2f1032)

| # | First walk | Now |
|---|---|---|
| 1 | Five Control answers dropped | **Fixed.** Every one is applied and seen: loan age (Every loan), fewest losses (*too few losses to test* on 29 to 37-loan pockets), materiality (*below the line*), judged against (the subtitle and the flag use the rest of its band), and the allowance is shown in Check. |
| 2 | RANR ranked as a loss | **Fixed** on Where it bleeds: shortfalls, and multiples under 1 flagged worse. **Open** on Grids (defect 14) and in *Smallest gap it could show* (defect 13). |
| 3 | Bad own values pass the tab | **Fixed.** Excel validation is on column D, and Run names the cell (`wrong-B-out-of-range-numbers.png`). The wording repeats the range (defect 15). |
| 4 | Python `None`, p-value on an untested pocket | **Half fixed.** No `None` anywhere. p-values still print on *too few ... to test* rows (defect 13). |
| 5 | Typing in Choose gives `#N/A` | **Fixed.** The dropdown refuses typing, and E and F say "not an option" in words. Defect 3 now reaches that same message by another route. |
| 6 | Odd values in the outcome and GCO not raised | **Fixed.** Columns' Look first shows BAD_FLAG's value of 2 and GCO's non-number. The wording beside FICO and RANR points "at the bottom" (defect 10). |
| 7 | Outcome, GCO and RANR cut by | **Fixed.** Grids are only fico and orig_bal by channel. |
| 8 | Next line points at missing markers | **Superseded.** No cube file. The window's Next line doesn't adapt (defect 15). |
| 9 | Recommended bands hide the pocket; edges read as software | **Partly.** Edges are whole numbers now (653, 685, 715, 747; 16,126 ...). Own edges work on Columns (step 16). Nothing suggests using the LOB's edges, and a comma-typed list is misread (defect 2). Band count is still the firm's call. |
| 10 | Materiality table mislabelled for loans | **Regressed in the workbook.** The table isn't in the workbook at all, and Check's line has no unit (defect 7). |
| 11 | Readings don't say which way; "benchmark" undefined | **Fixed.** worse, better, and "worse, but could be luck"; the subtitle names the comparison. The Flag heading could say it too (defect 13). |
| 12 | Control layout and wording | **Fixed.** The header fits, the key column is hidden, *In use* shows words, row 24 is a sentence, and *n/a* isn't shaded. New: row 18's own-value instruction (defect 11). |
| 13 | Read-back in machine names | **Fixed** for settings: Check lists each question with its words (labels clipped: defect 16). Machine names remain for measures (`outcome_loans`, `gco_rate`) on Check. |
| 14 | `cube synth` pre-makes the calls | **Fixed.** It writes only `loans.csv`. |
| 15 | Small: "1 rows", README count | **Fixed.** The README says 126 and the suite gives 126. New generic plurals: "thing(s)", "value(s)" (defect 15). |

---

## Where each defect stands (25 Sep 2026, after the fixes)

Each fix is held by a test, and `tools/mutation_check.py` puts the bug back to
prove that test goes red. Seen through LibreOffice. Not seen in Excel yet.

| # | Defect | Now | Test |
|---|---|---|---|
| 1 | A copied workbook runs the old folder's extract | **Fixed.** The window hands its extract to Run. Without one, a missing stored path falls back to the same file name beside the workbook | `test_a_copied_workbook_runs_*`, `test_a_moved_pair_*`, `test_run_hands_the_picked_extract_*` |
| 2 | 620,680,740 read as one edge | **Fixed.** The edges cell is text. A whole number of 100,000 or more is refused ("Excel dropped the commas; type them with semicolons"). Any edge outside the column's values is refused, naming the cell and the range. Check says how many bands were made | `test_edges_excel_read_*`, `test_an_edge_outside_*` |
| 3 | 95% stored as 0.95 | **Fixed.** Option labels can't be read as numbers ("95% sure"), and a number in the cell is matched to its option by value | `test_a_pick_is_read_however_excel_stored_it` |
| 4 | Yes carries over to new columns | **Fixed.** A new column clears C3, is shaded "New since the last check", and is named in the window | `test_a_new_column_takes_the_yes_back` |
| 5 | Forget re-learned in the same run | **Fixed.** A forgotten column isn't learned back from that run. The window says what was forgotten | `test_the_learned_tab_prunes_on_the_next_run` |
| 6 | Set up again deletes results and the Log | **Fixed.** Set up rebuilds only the input tabs | `test_set_up_again_keeps_the_last_results` |
| 7 | No materiality evidence, no units | **Fixed.** A Materiality tab shows what each level keeps, per grid. Every line has its unit, and the loans line has one decimal | `test_materiality_tab_*` |
| 8 | A refused run still changes memory and the record | **Fixed.** Checked before anything is touched | `test_a_workbook_open_in_excel_*` |
| 9 | Start here counts go stale | **Fixed.** Run recounts, and Last run gives the time and what ran | `test_start_here_says_when_it_last_ran` |
| 10 | "Answer it at the bottom" | **Fixed.** Now "answer it on the Odd values tab" | `test_odd_values_are_answered_where_the_workbook_asks` |
| 11 | "Enter your own in column D" on a row with no column D | **Fixed.** Those rows say "Pick one from the list", in the window and on the tab | `test_a_row_without_its_own_value_cell_*` |
| 12 | Meaning text cut at commas; dropdown shows codes | **Fixed.** The text is quoted. The dropdown, Columns and Learned show labels ("FICO score", "Servicing data") | `test_odd_values_are_answered_*` |
| 13 | Machine names, two Pocket headers, no unit, p on untested pockets, RANR gap | **Fixed.** Column names as in the extract. Headers are Band column / Band / Segment column / Segment. Excess has an "Excess is in" column. p is blank when untested and reads "under 0.0001". The flag heading names its comparison. RANR's gap reads "or less". The -9999 row reads "(marked missing)" | `test_ranr_is_marked_*` |
| 14 | RANR grids look like loss grids; headings are formulas | **Fixed.** "(more is better)", colours reversed for RANR, and each grid's arithmetic in words | `test_ranr_is_marked_*` |
| 15 | Window wording | **Fixed.** No "(s)", no backticks, the range said once (with "type 0.95" when 95 was typed), a Next line that changes with what's left, the changed column named when nothing is left to cut, no dangling "; ". **Open:** a long problem list can still scroll out of sight in the window | `test_taking_away_every_category_*`, `test_the_range_is_said_once_*` |
| 16 | Layout and print | **Fixed.** Check is wide and wraps. Log has a heading and prints on one page width. Blank and Samples no longer run together. Learned has a title bar. Every font is named. The record file is named on Check | — (seen on render) |
