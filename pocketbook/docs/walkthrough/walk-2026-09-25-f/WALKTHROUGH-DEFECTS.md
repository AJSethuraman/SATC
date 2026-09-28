# Origination cube: defects from the sixth walk (25 Sep 2026)

**What was walked:** the no-commands route of ruling OC-22, on commit `fec5f71`, frozen with `git archive` into scratch:
1. The Tk window: Browse, **1. Set up from this extract**.
2. Start here, Control, Columns, Odd values and Learned, answered cell by cell, taking every suggestion Control offers.
3. **2. Run the cube**, then every result tab.
4. The new parts:
   - Losses vs revenue under every revenue option and three pairs of GCO lines, with the default edges, with `620; 680; 740` and with `every 20`
   - the Split tab's new layout, and `driver/noplant.py` again, through the window
   - Three-way's *Holds FICO fixed?* column
   - Control's *Last Run used*, the window's *Worked out from this book* line, and a small low-default book
   - remembered band edges across three extracts (Q3, Q4, Q1), with a cell cleared
5. Set up again, Forget with two Runs after it, `cube init --control`, and 31 wrong turns, each in a folder of its own.

The procedure is `PROCEDURE-origination-workbook.pdf` beside this file. The scripts are in `driver/`.

**The book:** `synth.write_extract(n=8000)`, renamed `Consumer book Q3.csv`. It plants a bad pocket (FICO under 620 in Broker, 5x the usual rate), a revolving-debt effect (above the usual debt for the score goes bad 1.8x as often) and asset class 4 at 1.4x. RANR carries no plant, so every revenue gap on this book is noise.

**The suite at `fec5f71`:** `pytest -q` gave **184 passed** (6 min 10 s, Python 3.12 under xvfb). `tools/mutation_check.py` caught **49 of 50** and exited 1. The one it missed is "edges leak between workbooks": putting back the line that let another workbook's edges into a Set up changes no test result (the test it names, `only_fill_a_column`, still passes). All 184 tests pass with every defect below present, so none of them is caught.

**What held:**
- **The lines decide the boxes now.** Every revenue option moves the boxes the way its explanation says: 5% either way gives 62 pockets earning more or less, the loss lines give 1. The GCO lines do too: 23 pockets *Losing more* at 1.25x, 18 at 1.34x, 2 at 2x. `driver/pastline.py` finds no dot past a line boxed "the same" (35 on walk 5).
- **The planted pocket with the default bands** reads **Losing more, earning the same**: GCO 2.62x the rest of its band, RANR 1.05x, in every revenue option.
- **The suggested fewest loans is 71** (5 ÷ 7.13%, rounded up), and the pockets walk 5 lost are tested: with `every 20`, FICO 600 to under 620 / Broker (99 loans, 50 bad) is flagged **worse**; with the category split, FICO under 654 / Broker / asset class 4 (131 loans) is **worse**.
- **Set up again no longer writes other workbooks' edges in.** A new workbook gets remembered edges with "Band edges remembered from before: ..." under Look first, shaded. Clearing a cell and running forgets the edge.
- **The Split tab's method block** is accurate against the code: the median split, the ratio, Mantel-Haenszel odds, Cochran's Q, the Benjamini-Hochberg allowance within a grid and measure, the minimums (71 loans, 10 losses). The pocket-level Luck alone figures are adjusted (they repeat, as step-up values do).
- **Three-way:** the *Holds FICO fixed?* column reads *yes* or *no: part of this may be FICO*, and within each measure every *no* row comes after every *yes* row (`driver/threeway.py`, 0 out of order on both books).
- **`every 1`** now says 392 bands, and `every 0.5` 783. `cube init --control` no longer offers `calc` or `luck`.
- **Tie-outs** agree on every run (132; 581 with the number split; 382 with the category split; 571 with the booked amount).
- **Every wrong turn from walk 5 behaves as it did**, or better (the table at the end of the procedure).

Of the eleven walk-5 fixes, two held, seven held in part, one did not hold (defect 6, the fallback wording), and one was left open on purpose (the charts). The table is at the end.

This walk found **11 defects**, ranked by what each would cost the firm or the bank on a real job.

---

## 1. With the LOB's own bands, the bank's worst pocket reads "Losing more, earning more"

**What I did:** typed `620; 680; 740` in FICO's Band edges, the LOB's usual cut, and ran with every suggestion taken. Then did the same with `every 20`.

**What the screen said:**
- **Losses vs revenue**, FICO x CHANNEL, first row: FICO **under 620 / Broker**, 176 loans, GCO **5.35x** the rest of its band, flag *worse*; RANR **1.17x**, flag *in line*. Which box: **"Losing more, earning more (revenue g"**, where the cell ends. It's shaded amber, the colour of the *Losing more, earning more* box. The count line above says "Losing more, earning more: 1", and the chart names it in the top-right corner (`defect-1-lob-edges-earning-more.png`).
- The subtitle: "Revenue counts as more at 1.16x or above". That line was worked out on this run.
- With `every 20`: FICO **600 to under 620 / Broker**, 99 loans, GCO 4.63x, RANR 1.20x against a line of 1.18x, same box, same cut-off (`defect-1b-every-20-earning-more.png`).

**What was true:**
- RANR has nothing planted. 1.17x is noise, and the pocket's own RANR test says so: flag *in line*, and the cut-off words are "(revenue gap could be luck)".
- This is the third walk's finding, back. OC-26 exists because the firm read three bleeders in *Losing more, earning more* on revenue 2 to 5% above the book and said: *"I'm definitely not counting your example as a pass simply because the revenue is on par"*. Walk 4 added a luck gate; walk 5 showed the gate made the lines decide nothing; OC-30 removed it and put the luck in brackets. On the default bands the planted pocket's RANR is 1.05x and it lands right. On the two band settings the firm itself asked for, it lands in the box the firm rejected, and the bracket that is meant to rescue it is cut off (defect 2).
- The revenue line is a median over this run's pockets, and it moves with the bands (1.17x, 1.16x, 1.18x). The planted pocket sits within a point or two of it on each, so which box it reads is a coin toss decided by the band edges.

**Cost:** the consultant presents the bank's worst pocket, at five times its band's losses, as one that earns more. The LOB's first question is the firm's own: *do we care?* It's the case the firm already ruled should not read that way.

**Fix:** the firm's call. Options that keep OC-30:
- make the bracket impossible to miss (defect 2);
- when a side is marked luck, name the box by the side that isn't ("Losing more; revenue can't be told from the book");
- keep a luck-marked side out of the box's colour and count.

A check that goes red: on the synthetic book with `620; 680; 740`, FICO under 620 / Broker must not be counted or coloured as *earning more*.

## 2. "(… gap could be luck)" is cut off in the cell, and nothing else shows it

**What I did:** read Losses vs revenue after the first run, as printed and at the column's own width.

**What the screen said:**
- The **Which box** column is too narrow for the bracket. It reads "Losing more, earning the same (loss g", "Losing the same, earning less (revenu", "Losing less, earning the same (loss ga" (`defect-2-luck-mark-cut-off.png`). The next column holds a number, so the text can't run over into it in Excel either.
- **Shading** follows the box and ignores the bracket: FICO 746 and over / asset class 2 at 1.37x, *worse, but could be luck*, is the same red as the planted pocket at 2.62x.
- **The count line** folds them together: "Losing more, earning the same: 4" is 1 plain and 3 marked luck.
- **The chart** names the three biggest *Losing more* pockets. Two of the three named on FICO x ASSET_CLASS are marked luck, and their labels overprint each other (`step-13b-chart.png`).

**What was true:** 43 of the 104 boxes on the first run carry a bracket. With *5 percent either way*, 61 of the 62 revenue moves do. The bracket is the whole of OC-30's answer to "a gap past the line that could be luck", and on screen it is the part that doesn't show.

**Cost:** everything defect 1 costs, on every grid. A reader counting boxes or scanning colour reads luck as findings.

**Fix:** widen the column (or wrap it), give luck-marked boxes their own lighter fill, and count them apart ("Losing more, earning the same: 1, plus 3 that could be luck"). Leave luck-marked pockets unnamed on the chart. A check that goes red: no box text is wider than its column.

## 3. On a small or low-default book, "Nothing is worse", and a fallback called "worked out from this book"

**What I did:**
- Wrong turn S: typed my own fewest loans, 3,000 (more than any pocket), keeping the luck suggestions for worse and better.
- Wrong turn T: built a 5,000-loan book at a 1.34% bad rate (`driver/lowdefault.py`: the synthetic book with every rate cut to a sixth) and ran it with every suggestion.

**What the screen said:**
- **S, the window:** "Nothing is worse for" all four measures, then "Worked out from this book: worse at 1.25x; better at 0.80x" (`defect-3-fallback-window.png`).
- **S, Control's Last Run used:** "1.25 times (worked out from this book)", "0.8 times (worked out from this book)" (`defect-3b-fallback-control.png`).
- **S, Check:** "Worked out from this book: worse at 1.25x; better at 0.80x (the outcome gap luck alone can make in a pocket of typical size)". Three rows down: "Revenue counts as more or less at 1.25x and 0.80x: the same lines as for losses (no pocket was big enough to work out what luck can do)" (`defect-3c-fallback-check.png`).
- **S, the record:** "# revenue_line worked out from this book: 1.25x and 0.80x".
- **T, the window:** "Nothing is worse" for all four measures, and "Worked out from this book: fewest loans 374; worse at 1.25x; better at 0.80x" (`defect-3d-low-default-book.png`). Where it bleeds: 40 of 42 bad-loan rows read *too few loans to test*. Losses vs revenue: "No pocket has enough loans to place" on every grid.

**What was true:**
- Nothing was worked out. 1.25 and 0.8 are the code's fallbacks. The Check tab's own revenue line says no pocket was big enough.
- This is walk 5's defect 6, marked **fixed** in its status table. The fix is in the code but never reaches the screen: `_suggested` records the fallback on the first pass's result, and the Run is then done again, which makes a new result without it. So Check always says "Worked out". The new window line, Control column and record header repeat the claim in three more places.
- On T, nothing was tested. The suggested floor (5 ÷ 1.34% = 374 loans) is above every pocket (about 330 each). "Nothing is worse ... at these settings" reads as a clean book.

**Cost:** a prime book with a 1 to 2% bad rate is the usual case at a bank, not the edge case. A consultant on a modest extract gets a window saying nothing is worse and a line saying the thresholds were worked out from the book. Neither is true. Both would go into the write-up.

**Fix:** carry the fallback onto the result that's written out. Where it applies, say "no pocket was big enough, so 1.25x was used" everywhere the number appears. When no pocket is tested, the window should say "No pocket was big enough to test (fewest loans 374)", not "Nothing is worse". A check that goes red: wrong turn S's Check, window and record must not say "worked out".

## 4. On Losses vs revenue, the RANR flag and the box use different lines, and "in line" rows are shaded red

**What I did:** read Losses vs revenue after the first run and ran `driver/boxcheck.py` over it.

**What the screen said:** FICO 686 to under 712 / asset class 4: GCO 1.18x, *in line*; RANR 0.83x, *in line*. Box: **Losing the same, earning less (revenu…**, shaded red. Under 654 / 3 (RANR 0.80x) and 712 to under 746 / 2 (0.84x) read the same way (`defect-4-ranr-flag-in-line-box-earning-less.png`). Nine rows on the first run have a revenue side of *more* or *less* beside a RANR flag of *in line*. None says *could be luck*.

**What was true:**
- The RANR flag is judged by the loss lines (it would say *worse* at 0.75x or below). The revenue side of the box is judged by the revenue line (0.85x). Two words about one number on one row use two lines, and nothing on the tab says so.
- "Losing the same, earning less" is one of the three red boxes. So a row whose flags both say *in line*, on a book with no RANR effect, is coloured the same as the planted pocket.

**Cost:** a reader sees a red row, looks for the reason, finds two *in line* flags, and stops trusting the colour, or trusts it and reports a revenue shortfall that is noise.

**Fix:** judge the RANR flag on this tab by the revenue line, or say beside the flag which line it uses. Don't colour a box red on a side that's marked luck.

## 5. On a book with no debt effect, the Split and Three-way tabs can still be read as finding one

**What I did:** re-ran `driver/noplant.py`, and ran the REV_DEBT split through the window on the same book with the debt plant switched off.

**What the screen said:**
- **Split:** after the two FICO grids (1.16x, 0.95x to 1.36x, luck alone 13%; 1.15x, 16%) comes the dark red heading "Grids that don't hold FICO fixed. REV_DEBT moves with FICO (correlation -0.53), so part of every gap below may be FICO, not REV_DEBT." Under it, ORIG_BAL x CHANNEL: **1.62x** (1.37x to 1.87x), worse in 13 of 15, luck alone **under 0.01%**, same size in every pocket **yes** (`defect-5-no-effect-book-split.png`).
- **Three-way:** ORIG_BAL 49,158 and over / Broker / REV_DEBT high half, 266 loans, 2.77x its band, **worse**, shaded red, on all three loss measures. The last column says *no: part of this may be FICO*, and the rows are last in their measure (`defect-5b-no-effect-book-three-way.png`).

**What was true:**
- There's no debt effect in this book. All of the 1.62x is FICO, not "part of" it.
- Walk 5's fix is in: the warning heading, the short column, and the order all work. On the no-effect book, 28 ORIG_BAL rows on the bad-loan share are *worse, but could be luck* and 2 are *worse*; on the planted book it's 23 *worse*.
- The summary table under the warning is the strongest-looking table on the tab: the biggest ratio, the smallest luck alone, and "yes" to steady.

**Cost:** smaller than walk 5. A consultant who reads the warning won't quote the table. One who copies the summary table, or sorts Three-way by flag, can still tell the bank that large Broker loans with high revolving debt go bad at nearly three times their peers.

**Fix:** say "may be mostly FICO" or "can't be told from FICO", not "part of". Don't shade a Three-way row red when *Holds FICO fixed?* is *no*. Consider leaving the Luck alone column blank under the warning heading.

## 6. Control's Last Run used column is off the page, and Set up again empties it

**What I did:** looked for the worked-out numbers on Control after the Run, printed the tab, then pressed Set up again.

**What the screen said:**
- The column is there on screen, to the right of the 70-wide *What it means* column and the hidden key column (`step-09-control-answered.png`, rendered with the print area widened by `driver/widen.py`).
- The printed tab doesn't have it: the print area stops at column F (`defect-6-last-run-used-not-printed.png`).
- Four rows are blank in it: the category limits, band count and band placement, though the Run used all four.
- *In use* still reads "What luck alone can move it (suggested)".
- After **Set up again**, the column is gone, header and all, while Where it bleeds and the rest still show that Run's results (`step-22c-control-after-set-up-again.png`).
- Formats differ: "1.34 (worked out from this book)" beside "1.17x and 0.85x".

**What was true:** the numbers are right (71, 1.34, 0.75, 1.17x and 0.85x; `driver/luckline.py` agrees). The window line leaves out the revenue line; the record header has it.

**Cost:** a reviewer given the printed workbook, or opening it after a Set up again, can't see what produced the results. That's what walk 5's defect 8 was about.

**Fix:** put the column inside the print area (or next to *In use*), fill every row, keep it through Set up again, and add the revenue line to the window.

## 7. The edge memory is whatever the last Run of any workbook had

**What I did:** ran the Q3 book with `every 20`, set up Q4, ran band-width wrong turns on Q4 copies, set up Q1, cleared FICO on Q4 and ran, set up Q1 again in a fresh folder.

**What the screen said:**
- Q4's Set up filled FICO with `every 20`, marked "Band edges remembered from before: every 20." and shaded (`step-24b-next-extract-columns.png`).
- Q1's Set up filled FICO `every 20` and CHANNEL **`620; 680`**, both marked. The window said "**2** columns to look at first"; **4** rows are shaded (`defect-7-look-first-count.png`).
- After the Q4 clear-and-run, a fresh Q1 Set up filled nothing.
- Learned lists "amount; band edges every 2000" for REV_DEBT, still a code, where other columns read "Category".

**What was true:**
- Every Run writes every column's edges into the memory, and a blank cell deletes them. So the memory holds the last Run's edges, from whichever workbook ran last. CHANNEL's `620; 680` came from a wrong turn on a different copy; a colleague's old workbook with blank cells would just as quietly erase someone's `every 20`.
- Edges on a category are still accepted without a word, ignored by the Run, remembered and filled into the next workbook (walk 5 asked for this to be refused).
- The Look-first count leaves the edges note out, so the window undercounts.
- The mutation check can't tell whether the walk-5 fix is there (above).

**Cost:** low now that the fill is marked and only reaches new workbooks. On a shared team folder, the next new workbook starts with a stranger's bands, marked in a column the window's count doesn't point to.

**Fix:** remember edges only when a person typed them into a confirmed Columns tab, and forget only on the same workbook's clear. Refuse edges on a category. Count the edges note in "columns to look at first". Make `only_fill_a_column` fail when the mutation is put back.

## 8. Under 20-point bands, a 50-loan pocket with 29 bad loans is still "too few loans to test"

**What I did:** ran `every 20` with the suggested fewest loans (71).

**What the screen said:** Where it bleeds, sixth row: FICO **580 to under 600 / Broker**, 50 loans, **58.00%** bad against 7.13%, 5.63x the rest of its band, **too few loans to test**. It isn't on Losses vs revenue (`step-21e-every-20-where-it-bleeds.png`).

**What was true:** the pocket has 29 bad loans, nearly six times the 5 the floor is meant to guarantee, and three times the separate *Fewest loans with a loss* line (10). It's walk 5's defect 1 at a smaller size: a floor worked out from the whole book's rate refuses a pocket that has far more losses than the floor asks for. Its neighbour, 600 to under 620 / Broker, is tested and flagged, so the finding reaches the bank anyway on this book.

**Cost:** small here. On a book where the worst pocket is the only one in its corner, it would be left out.

**Fix:** as walk 5 said: when a pocket already has at least the expected losses the floor was meant to give, test it.

## 9. The Split tab: the method block is right, and a few things around it aren't plain

Seen in `step-18c-split-how-it-works.png` and `step-18d-split-fico-grid.png`:
- **"The figures are after the allowance for many tests"** is true of the pocket heat maps. The summary table's *Luck alone* is one pooled test per grid and measure, and nothing allows for the sixteen of them. The block doesn't say which is which.
- **Every grid line repeats "0 means unrelated, and the further from 0, the more of this gap may be ..."**, including for ORIG_BAL at -0.02 on the FICO grids, where the caveat is empty. The block exists so this is said once.
- **The heat maps are shaded by the ratio alone.** On the no-effect book a FICO pocket at 2.33x with luck alone 61% is deep red.
- **"Same size in every pocket?"** is filled for the bad-loan share and blank for the other three measures, without a word why.
- **Wording:** "The test weighs the gap against how much each half's rate wobbles at its size" is plain. "Mantel-Haenszel" and "Cochran's Q" are named without a gloss, which is fine for a reviewer and not for the LOB.

## 10. Three-way: a garbled lead sentence, and the new column prints off the page

- **The lead**, as printed: "... they come after the rest. **Each list, losing more than their share (RANR: earning less), largest first.**" Two strings spliced into one sentence.
- **The *Holds FICO fixed?* column** runs past the page's right edge in print: "no: part of this may be FICO" sits outside the frame (`step-18g-three-way-holds-fixed.png`, `defect-5b-no-effect-book-three-way.png`).

## 11. Smaller things

- **Charts (walk 5's defect 11, left open):** still three GCO ticks (0.10x, 1.00x, 10.00x); dashed lines unlabelled; box names absent; labels overprint and run off the plot ("under 620 / Broker" past the right edge).
- **`every 1`:** the count is right now, but the message still names no cell ("Columns:", not Columns!F7), and "Use a wider band, 50 at most" still reads as a width of 50.
- **Losses vs revenue subtitle:** "less at 0.85x or below: what luck alone can move it: in a pocket of typical size, luck alone moves revenue up to 1.17x at 95% sure." Two colons in a row, and "what luck alone can move it" twice.
- **0.95 as the revenue line** is still refused without the hint 95 gets.

---

## What I couldn't check

- **Real Excel.** Every tab was seen through LibreOffice and set with openpyxl. Not seen:
  - whether the Which box text wraps or is cut in Excel (it's cut in the LibreOffice print, and the next cell holds a number)
  - where *Last Run used* lands on a laptop screen, and whether Excel prints it
  - the charts as Excel draws them
  - dropdowns, validation pop-ups and conditional shading as Excel shows them
- **Windows.** The file dialog, Segoe UI, **Open the workbook**, and a real Excel lock (simulated with `chattr +i`).
- **A book with a real revenue effect.** RANR is noise in the synthetic book, so every revenue box off "the same" here is a false one. I couldn't see a true one land.
- **A big low-default book.** Wrong turn T was 5,000 loans at 1.34%: too small for any test, so it shows the wording failure, not whether the 5-expected-losses floor finds a planted pocket at a 1% rate. That needs 50,000 loans or more.
- **Two people sharing one memory file.** Defect 7 comes from one scratch memory shared by the walk's folders. I didn't run two users at once.
- **The repository moved during the walk.** `6c3fe9c` ("test the band-edge leak the way the fifth walk found it") changes a test only, and answers the mutation miss above; defect 7's other points are untouched by it. Two later commits (`674e180`, `beb1606`) put this walk's files in part-way through. I walked `fec5f71` as frozen.
- **Whether the firm meant the revenue line to sit this close to the planted pocket.** Defect 1 turns on RANR 1.17x against a line of 1.16x. Which box the firm wants there is their call; the walk can only show what it reads now.

---

## Where each walk-5 defect stands (seen on screen, `fec5f71`)

| # | Walk-5 defect | Now |
|---|---|---|
| 1 | The suggested fewest loans hid the planted pocket | **Held.** Suggested at 71 (5 expected losses). With `every 20`, 600 to under 620 / Broker (99 loans) is tested and **worse**; with the category split, under 654 / Broker / 4 (131 loans) is **worse** (`step-21e`, `step-19b`). A 50-loan pocket with 29 bad is still untested (defect 8). |
| 2 | Other workbooks' band edges written in; clearing didn't undo | **Held in part.** Set up again writes nothing in (`step-22b`); a new workbook's fill is marked and shaded (`step-24b`); clearing forgets (`step-26`). But the memory is last-Run-wins across workbooks, category edges are still remembered and filled, the window's count leaves them out, and the mutation check can't see the fix (defect 7). |
| 3 | The Control lines didn't decide the boxes | **Held.** Every revenue and GCO option moves the boxes as its explanation says; no dot past a line is boxed "the same" (step 13's table). New cost: under the LOB's bands the planted pocket reads *earning more* (defect 1). |
| 4 | A no-effect book can read as having a debt effect | **Held in part.** Warning heading, *Holds FICO fixed?* column, *no* rows last (`step-18e`, `step-18g`). The 1.62x table and a red 2.77x *worse* row remain; the heading says "part of" (defect 5). |
| 5 | "About the same" hid a could-be-luck gap | **Held in part.** A 1.76x gap now reads "Losing more, earning the same (loss gap could be luck)". The bracket is cut off in the cell, shaded like a real finding and counted with them (defect 2). |
| 6 | Check said "worked out" when a fallback was used | **Did not hold.** Check still says "Worked out from this book: worse at 1.25x" on wrong turn S, and the window, Control and the record now say it too. The fallback is lost when the Run is redone (defect 3). |
| 7 | "every 1" said 61 bands | **Held in part.** It says 392 (783 for 0.5). No cell named; "50 at most" still ambiguous (defect 11). |
| 8 | Suggested numbers not on Control, in the window or in the record | **Held in part.** Window line (no revenue line), record header (with it), Control column. The column is outside the print area, blank on four rows, and emptied by Set up again; *In use* still says "(suggested)" (defect 6). |
| 9 | `cube init` offered calc and luck | **Held.** The [CONFIRM] lists 30 / 100 / 300 and 1.25 / 1.5 / 2.0. It gives no worked-out number as a comment, and the revenue line isn't in the cube file (command line only, OC-22). |
| 10 | Remembered edges in codes and unmarked | **Held in part.** Marked under Look first and shaded. Learned still reads "amount; band edges every 2000"; the window count leaves the note out (defect 7); the empty -0.02 caveat repeats on every FICO grid (defect 9). |
| 11 | Chart gaps | **Open, as the walk-5 table said.** Three GCO ticks, unlabelled lines, no box names; labels now overprint (defect 11). |

---

## Where each defect stands (25 Sep 2026, after the fixes)

The firm decided 1 (OC-31 in `docs/design.md`). Every fix is held by a test, with a planted bug to prove the test catches it. Seen through LibreOffice.

| # | Defect | Now | Test |
|---|---|---|---|
| 1 | Under the LOB's bands, the worst pocket reads "earning more" | **Fixed the way the firm chose.** The suggested revenue option is each pocket's own luck range; the planted pocket reads "Losing more, earning the same" | `test_the_planted_pocket_is_not_read_*` |
| 2 | The luck mark cut off, shaded and counted like a finding | **Fixed.** The box column is wide and wraps; a marked box isn't shaded; the count line gives marked boxes on their own | `test_a_luck_gap_keeps_its_box_*` |
| 3 | A fallback called "worked out"; "Nothing is worse" when nothing was tested | **Fixed.** The fallback reaches the final result: the window, Check and Control say "the usual value". A run with nothing big enough to test says so for each measure | `test_a_suggestion_with_nothing_to_work_from_*` |
| 4 | RANR flag and box on different lines | **Fixed.** The column is now "RANR reading", against the box's own line | `test_the_suggested_revenue_line_*` |
| 5 | A no-effect book can still read as an effect | **Fixed in part.** Split heat maps bracket and don't shade a could-be-luck multiple; the warning heading and Three-way column stay. The pooled numbers for grids that don't hold FICO fixed are what the data says, under the warning | `test_split_gaps_that_could_be_luck_*` |
| 6 | Last Run used off the page; Set up empties it | **Fixed.** In the print area, and kept through Set up | `test_control_shows_what_the_last_run_used` |
| 7 | Edge memory: category edges, the count | **Fixed.** Only band columns' edges are remembered or filled in, and Set up's count includes remembered edges. The memory is still "the last Run of any workbook", by design | — |
| 8 | A 50-loan pocket with 29 bad is "too few loans" | **Open, proposed.** An exact test for small pockets (see the message to the firm) | — |
| 9 | Split tab points | **Fixed.** The block says which figures carry the allowance and glosses Mantel-Haenszel and Cochran's Q. The correlation's meaning is said once. "Same size" reads "yes/no outcome only" where it doesn't apply | `test_split_by_a_number_*` |
| 10 | Three-way lead and print | **Fixed.** One plain sentence; the page is wide enough for the column | — |
| 11 | Smaller things | **Fixed except the charts.** `every 1` names its cell and says "50 bands or fewer"; 0.95 on the revenue row gets "The most it takes is 0.9"; no double colon. The charts are still open | `test_a_band_width_too_narrow_*` |
