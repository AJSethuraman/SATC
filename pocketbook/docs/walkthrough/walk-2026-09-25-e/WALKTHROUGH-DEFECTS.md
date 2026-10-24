# Origination cube: defects from the fifth walk (25 Sep 2026)

**What was walked:** the no-commands route of ruling OC-22, on commit `5ef61df`, frozen with `git archive` into scratch:
1. The Tk window: Browse, **1. Set up from this extract**.
2. Start here, Control, Columns, Odd values and Learned, answered cell by cell. This time every Control call that offers a suggestion was given it.
3. **2. Run the cube**, then every result tab.
4. The new parts:
   - the three suggested Control numbers, on Check and in the *what ran* record
   - Losses vs revenue under every revenue option, with the default edges and with `620; 680; 740`
   - a band width (`every 20`), and whether it comes back at the next extract's Set up (a second and third synthetic extract, Q4 and Q1)
   - Split and Three-way, and `driver/noplant.py` again
5. Set up again, Forget with two Runs after it, `cube init` from the answered Control tab, and 29 wrong turns, each in a folder of its own.

The procedure is `PROCEDURE-origination-workbook.pdf` beside this file. The scripts are in `driver/`.

**The book:** `synth.write_extract(n=8000)`, renamed `Consumer book Q3.csv`. It plants a bad pocket (FICO under 620 in Broker), a revolving-debt effect (above the usual debt for the score goes bad 1.8x as often) and asset class 4 at 1.4x. RANR carries no plant.

**The suite at `5ef61df`:** `pytest -q` gave **179 passed** (5 min 8 s, Python 3.12 under xvfb). `tools/mutation_check.py` caught **46 of 47** and exited 1. The one it missed is "boxes by 1.00x again": putting the Control lines back to 1.00x changes no test result. That miss and defect 3 below are the same finding. All 179 tests pass with every defect below present, so none of them is caught.

**What held:**
- **The planted pocket comes out on top** with the default bands, and reads **Losing more, earning the same** on Losses vs revenue: GCO 2.62x the rest of its band, RANR 1.05x. With `620; 680; 740` it's FICO under 620 / Broker, same box: GCO 5.35x, RANR 1.17x. The revenue line on that run is 1.16x, and the RANR test says *in line*, so it stays *the same*. That was the fourth walk's worry, and it holds.
- **The suggestions are worked out and shown on Check:** fewest loans 141 (10 ÷ 7.13%, rounded up), worse at 1.34x, better at 0.75x, revenue at 1.17x and 0.85x. `driver/luckline.py` gets the same numbers from the run's own record. Flags follow the 1.34x line: 1.33x reads *in line* and 1.344x reads *worse, but could be luck*.
- **Boxes agree with their flags and their dollars** on every row (`driver/boxcheck.py`: 0 contradictions in 105 rows). Untested pockets get no box and no colour.
- **The split finds the debt effect** where the score is held fixed: 1.95x and 1.92x against a planted 1.8x. On the no-effect book those grids read 1.16x and 1.15x, with ranges that include 1.
- **Band widths:** `every 20` gives 23 FICO bands, 500 to 920. It's remembered and filled in at the next extract's Set up. `every 1`, `every 0` and `every twenty` are refused.
- **Tie-outs** agree on every run (132; 581 with the number split; 382 with the category split).

Of the eleven walk-4 fixes, seven held on screen and four held in part. None failed outright. The table is at the end.

This walk found **11 defects**, ranked by what each would cost the firm or the bank on a real job.

---

## 1. With the suggested fewest loans, the bank's worst pocket reads "too few loans to test" as soon as pockets get smaller

**What I did:** took every suggestion on Control, including *Fewest loans: Enough for 10 expected losses*, which came out at 141 loans. Then I typed `every 20` in FICO's Band edges (the firm's own example of banding) and ran. Separately, I split every pocket by ASSET_CLASS and ran.

**What the screen said:**
- The window: "Worst for Outcome, share of loans: REV_DEBT 17,187 and over / CHANNEL Broker", the same for the other two loss measures. FICO isn't named (`step-21d-every-20-run.png`).
- **Where it bleeds**, third row: FICO **600 to under 620 / Broker**: 99 loans, **50.51% bad** against 7.13%, 7.67x the book, 4.25x the rest of its band. Flag: **too few loans to test**. On the same row, *Smallest gap it could show*: **2.16x or more**. The fifth row is 580 to under 600 / Broker: 50 loans, 58% bad, the same flag (`defect-1-every-20-planted-pocket-untested.png`).
- Losses vs revenue doesn't list either pocket. They're under the line, so they're left off the tab without a word.
- **Three-way, category split:** the first row is FICO under 654 / Broker / asset class 4: 131 loans, 29.01% bad, 2.11x the rest of its band, **too few loans to test**. 60 of the 77 bad-loan rows read the same, and none is flagged worse (`defect-1b-category-split-untested.png`). The fourth walk, with 30 loans, flagged this pocket *worse*.

**What was true:**
- 600 to under 620 / Broker has **50 bad loans**. The suggestion's own reason is "the loans a pocket needs to expect 10 with the outcome at the book's rate". This pocket has five times that. It also clears the separate *Fewest loans with a loss* line (10) five times over.
- With *30 loans* on the same bands, both pockets are flagged **worse** (wrong turn `every20-30`).
- The design notes already record this failure: "the first version used it as the minimum, and that hid the planted pocket: 531 loans at 6.6x, obviously real. A big gap shows in a small pocket." The suggestion reintroduces that minimum, worked out from the whole book's rate. Any change that makes pockets smaller trips it: narrow bands, a category split, a small book.
- The next extract (Q4) came in with `every 20` already filled in, and ran the same way. Its window named REV_DEBT, not FICO.

**Cost:** the consultant takes the tool's own suggestion and asks for the 20-point bands the firm wanted. The worst pocket in the book, at half its loans going bad, is left out of the headline, the flags and Losses vs revenue. The report goes to the bank without it.

**Fix:** a floor worked out from the book shouldn't refuse a pocket that already has more losses than the floor was meant to guarantee. Either base the suggestion on the pocket's own losses (which *Fewest loans with a loss* already checks), or keep it as evidence only. At the least, the window and Where it bleeds should say how many pockets are under the line and how much excess they hold. A check that goes red: on the synthetic book with `every 20`, 600 to under 620 / Broker must be tested.

## 2. Set up again writes band edges from other workbooks into this one, and clearing the cell doesn't stop it

**What I did:**
- On the main workbook, ran with FICO `every 20`.
- Walked the band-width wrong turns on a copy of the Q4 workbook. One typed `every 2000` on REV_DEBT; another typed `620; 680` on CHANNEL, a category.
- On the Q4 workbook, cleared FICO's cell to go back to five bands, and ran.
- Set up the Q1 extract.
- Pressed Set up again on the main Q3 workbook.

**What the screen said:**
- After Set up again on Q3, the window said "Everything is answered. Press Run the cube." Columns now showed REV_DEBT **`every 2000`** and CHANNEL **`620; 680`**, neither of which had been typed in this workbook. C3 stayed Yes, and nothing was shaded or noted (`step-22c-columns-after-set-up-again.png`, `defect-2-set-up-again-changes-bands.png`).
- The next Run: "Nothing is worse for Outcome, share of loans at these settings." Check: REV_DEBT cut into **25 bands**, 2,000 to 48,000 (`defect-2b-rev-debt-now-25-bands.png`).
- Q1's Set up filled FICO with `every 20` again, although it had been cleared on Q4 before its last Run. CHANNEL got `620; 680`.
- Learned lists "fico; band edges every 20", "category; band edges 620; 680" and "amount; band edges every 2000".

**What was true:**
- Edges are remembered at every Run, but only when a cell has something in it. A cleared cell leaves the memory as it was, so the only way back to the default bands is Forget on Learned, which also forgets the column's meaning.
- Set up fills remembered edges into *empty* cells of an existing workbook, not only a new one. The workbook's own answers are kept; its blank ones aren't treated as answers.
- Edges typed on a category are ignored by the Run and still remembered.
- The memory is one file per machine, and can be a shared team folder. On this walk the stray edges came from wrong turns on another copy. On a real job they would come from a colleague's experiment on another client's book.

**Cost:** a second Run of the same book, with nothing changed by the analyst, comes out with different bands, different pockets and a different headline. Nothing on screen says why. A reviewer rerunning a finished job can't reproduce it.

**Fix:** only fill remembered edges into a new workbook, and say so on the row ("Band edges remembered from ..."). Treat a cleared cell as "use the default" and remember that too. Refuse, or at least don't remember, edges on a category.

## 3. The lines on Control don't decide the boxes on Losses vs revenue, but the options and the chart say they do

**What I did:** ran the answered book once per revenue option: luck, 5%, 10%, the loss lines, and your own 0.15. Ran it again with GCO lines of 1.25 and 0.8 instead of the suggested 1.34 and 0.75, and again with 30 fewest loans. Then I read the boxes back (`driver/revenue_options.py`, `driver/pastline.py`).

**What the screen said:**
- Every revenue option gave the same boxes: **0 earning more, 1 earning less**, out of 105 pockets. The 1.25/0.8 GCO lines gave the same boxes as 1.34/0.75.
- On Control, *5 percent either way* explains itself as "Small moves count. Expect many pockets to read as earning more or less." With it, the subtitle says "Revenue counts as more at 1.05x", and 654 to under 686 / Online at **1.16x** reads *About the same on both* (`defect-3-revenue-5-percent-same-boxes.png`).
- The charts draw the four lines dashed, as the edges of the boxes. On the first run, **35 of 104** pockets sit past a GCO line and are boxed *the same* on GCO, plus 8 past a revenue line. With 5% either way, 61 sit past a revenue line and read *earning the same* (`defect-3b-chart-dots-past-the-lines.png`).

**What was true:**
- Since the fourth walk, a side moves off *the same* only when it's past the line *and* its own test says it isn't luck. On this book the test is always the stricter of the two. Any line below it changes nothing.
- The suggested line is below what the tool's own test calls luck. The worse line, 1.34x, is "the gap luck alone can make in a pocket of typical size". It compares a pocket with the book's rate, as if that rate were known exactly. The flag compares it with the rest of its band, which has its own noise, and then allows for testing many pockets at once. The pocket at exactly 1.344x (under 15,449 / asset class 4, 425 loans) has a luck-alone of 16% before the allowance and 34% after. Worked back from the run's own tests, luck alone moves a typical pocket up to about 1.5x.
- The mutation check says the same thing: setting the lines back to 1.00x is the one bug it can't catch.

**Cost:** the firm asked for its own lines and a defensible norm for them (OC-26). The consultant picks one, reads the chart by its dashed lines, and explains the boxes by them. The boxes are set by something else, and the chart shows a third of the pockets on the wrong side of their own box.

**Fix:** either make the suggestion what the tool's own test calls luck (against the same comparison, after the allowance), so the line and the test agree, or drop the lines from the chart and say on Control that the test decides. Rewrite the *5 percent either way* explanation, which is false. A check that goes red: two revenue options that print different lines should give different boxes on a book built for it, or the tab should say why they don't.

## 4. On a book with no debt effect, the Split and Three-way tabs can still be read as finding one

**What I did:** re-ran `driver/noplant.py`, and ran the REV_DEBT split through the window on the same book with the debt plant switched off (`wrong-noplant-split.png`).

**What the screen said:**
- **Split, ORIG_BAL x CHANNEL** opens: "This grid holds ORIG_BAL fixed (REV_DEBT's correlation with it: -0.02). It doesn't hold FICO fixed. REV_DEBT's correlation with FICO is -0.53: 0 means unrelated, and the further from 0, the more of this gap may be FICO." Then: "worse in 13 of the 15 pockets ... 1.62 times as often ... Luck alone gives a gap this big under 0.01% of the time ... The gap is about the same size in every pocket" (`defect-4b-no-effect-book-split-sentence.png`).
- **Three-way:** ORIG_BAL 49,158 and over / Broker / REV_DEBT high half, 266 loans, 2.77x the rest of its band, **worse**, shaded red, on all three loss measures. Its caveat is in the 18th column, *What this grid holds fixed* (`defect-4-no-effect-book-three-way.png`).
- On the planted book, 12 of the 14 high-half rows flagged *worse* on the bad-loan share come from ORIG_BAL grids (`driver/threeway.py`).

**What was true:**
- There is no debt effect in this book. The high-debt half of a loan-size pocket is its low-score half.
- The fourth walk's fix is in place: the caveat now comes before the number on Split, and is on every Three-way row, with FICO grids first within each measure. But:
  - both kinds of grid open with "This grid holds ... fixed". The ORIG_BAL grid leads with a column that doesn't matter (correlation -0.02).
  - the warning is "may be FICO", followed by "under 0.01%" and "about the same size in every pocket".
  - on Three-way the caveat is the last of 18 columns. The same 35-word sentence repeats on every row and runs past the row in print (`step-18f-three-way-holds-fixed.png`).

**Cost:** as in the fourth walk, but smaller. A consultant who reads the paragraph's first clause, or the red row, can still tell the bank that large Broker loans with high revolving debt go bad at nearly three times their peers.

**Fix:** lead each paragraph with the one thing that decides whether to quote it: "Don't quote this grid: it doesn't hold FICO fixed, and REV_DEBT moves with FICO (-0.53)." On Three-way, put a short *Holds FICO fixed? Yes/No* column beside the flag, and don't colour a row red when the answer is No.

## 5. A pocket at 1.76x reads "About the same on both" when its test says "could be luck"

**What I did:** read FICO x ASSET_CLASS on Losses vs revenue after the first run.

**What the screen said:** 712 to under 746 / asset class 4: GCO **1.76x**, flag *worse, but could be luck*, box **About the same on both**. 654 to under 686 / 4 at 1.68x and 746 and over / 2 at 1.37x read the same way (`defect-5-same-box-at-1-76x.png`).

**What was true:** the box says "the same" for two different things: no gap, and a gap too noisy to call. The flag beside it says which, but the box is the word that's counted above the table ("About the same on both: 19") and shaded. This is the other face of defect 3: 35 of 104 pockets are in this position on GCO.

**Cost:** a consultant quoting the box tells the LOB a pocket at 1.76x its band's losses is in line. It may be the next quarter's bleeder.

**Fix:** a separate word for "past the line, could be luck", such as "Can't tell yet", or keep the box and add it to the count line.

## 6. Check says "worked out from this book" when nothing was

**What I did:** kept the suggestions for how much worse and better, and typed my own fewest loans, 3000, larger than any pocket (wrong turn S).

**What the screen said:** Check: "Worked out from this book: worse at 1.25x; better at 0.80x (the outcome gap luck alone can make in a pocket of typical size)". Settings: "How much worse than its comparison a pocket must be: **1.25 times**". The revenue row says "the same lines as for losses (no pocket was big enough to work out what luck can do)" (`wrong-min-huge-check.png`).

**What was true:** no pocket reached the floor, so nothing was worked out. 1.25 and 0.8 are fallbacks in the code. "1.25 times" is the wording of the old workbook's option, which nobody picked. The revenue line says so, but the loss lines don't.

**Cost:** low on this book. On a low-default book it's real: at a 1% bad rate the suggested floor is 1,000 loans, and a book of modest size can have no pocket that big. Check would then say a default was worked out from the book.

**Fix:** say "no pocket was big enough, so 1.25x was used" the way the revenue line does, and word the setting as the fallback, not as an option picked.

## 7. "every 1" is refused with the wrong count

**What I did:** typed `every 1`, then `every 0.5`, in FICO's Band edges on the Q4 workbook (wrong turn P).

**What the screen said:** "Columns: every 1 on "FICO" would make **61 bands** (498 to 889). Use a wider band, 50 at most." `every 0.5` said 61 too (`wrong-every1.png`, `wrong-every05.png`).

**What was true:**
- 498 to 889 at every 1 is about 392 bands, and at every 0.5 about 782. The count stops at 61 because the code stops making edges at 60.
- The message names no cell ("Columns:", not Columns!F7).
- "50 at most" reads as a width of at most 50, when it means at most 50 bands.
- `every 0` and `every -5` get "should read like every 20: the word every, then how wide each band is", which they already do. The problem is the number (`wrong-every0.png`).

**Cost:** small, but it's the first thing a user sees when trying a width, and the number is wrong.

**Fix:** count without the cap, name the cell, say "at most 50 bands; for FICO that's every 8 or wider", and for 0 or less say "the width must be more than 0".

## 8. The suggested numbers are only on Check, and the record of the run doesn't say they were suggestions

**What I did:** after the first Run, looked for 141, 1.34 and 0.75 on Control, in the window and in *... - what ran.yaml*.

**What the screen said:**
- **Control**, after the Run: *In use* still reads "Enough for 10 expected losses (suggested)" and "What luck alone can move it (suggested)", with no number (`step-09-control-answered.png`).
- **The window** says nothing about them (`step-11-after-run.png`).
- **What ran:** `min_units: 141`, `worse_at: 1.34`, `better_at: 0.75`, with nothing saying they were worked out, and `revenue_line: luck` with no number.
- **Check** has them all (`step-16-check.png`). It also shows "Loans needed for a 1.34x gap: about 971" a few rows above "fewest loans 141". Where it bleeds shows "Smallest gap it could show: 1.47x" beside a 1.34x line. Three numbers about pocket size, and none of them is explained against the others.

**What was true:**
- The record can rerun the loss lines, but not say they were suggestions.
- It can't show the revenue line: 1.17x is worked out again from whatever grids the next run has, and moved to 1.16x with the LOB's edges.
- The GCO side of each box uses the outcome's luck gap (1.34x). GCO's own is 1.40x (`driver/luckline.py`).

**Cost:** a reviewer reading the file or the record sees numbers but not where they came from, and can't recover the revenue line.

**Fix:** put the worked-out number in *In use* after a Run, drop "(suggested)" there, add one window line ("Worked out from this book: 141 loans, 1.34x, 0.75x, revenue 1.17x"), and write both the choice and the number into the record.

## 9. `cube init` from a Control tab with a suggestion asks for a number, and offers words it then refuses

**What I did:** `cube init loans.csv -o cube.yaml --control` on the answered workbook, then did what the file said.

**What the screen said:** `min_units: "[CONFIRM: fewest loans in a pocket before it is tested? Pick calc / 30 / 100 / 300, or enter your own]"`, and `worse_at` / `better_at` offering `luck / 1.25 / ...`. With `calc` and `luck` typed in, `cube validate` refused: "benchmark.min_units must be a whole number of loans, 2 or more; got 'calc'", and the same for `luck`.

**What was true:**
- It does ask for a number, as it should.
- It offers the two words that can't be used, and doesn't give the number the workbook worked out (141, 1.34, 0.75).
- The revenue line isn't in the cube file at all.

This is the command line, which the users don't use (OC-22), so the cost is low.

**Fix:** leave `calc` and `luck` out of the CONFIRM list, and give the worked-out number as a comment.

## 10. Learned and Columns: remembered edges in codes, and not marked

- **Learned** writes a column with edges as its code: "fico; band edges every 20", "category; band edges 620; 680". Columns without edges read "FICO score", "Category".
- **Columns** after Set up shows remembered edges with no word that they're remembered. *Why this was suggested* covers the meaning only (`step-24b-next-extract-columns.png`).
- **The ORIG_BAL grid's Split paragraph** says "REV_DEBT's correlation with ORIG_BAL is -0.02: 0 means unrelated, and the further from 0, the more of this gap may be ORIG_BAL". That caveat is empty at -0.02, and it appears on every FICO paragraph and every Three-way row.

## 11. The Losses vs revenue charts are still hard to read

Seen in `step-13b-chart.png`:
- **The GCO axis still has three ticks:** 0.10x, 1.00x and 10.00x. Every pocket sits between 0.4x and 3x.
- **The dashed lines have no labels,** and the box names aren't on the chart.
- **Dots past a line can be in "the same"** (defect 3), and nothing on the chart says so.

Held since walk 4: 1.00x on both axes, names only for *Losing more* pockets, the count line wrapped.

---

## What I couldn't check

- **Real Excel.** Every tab was seen through LibreOffice and set with openpyxl. Not seen:
  - the charts as Excel draws them
  - whether Excel's validation stops a typed `every 20` or 95 before Run sees it
  - how dropdown picks with "(suggested)" in them are stored
  - conditional shading and column widths
- **Windows.** The file dialog, Segoe UI, **Open the workbook**, and a real Excel lock (simulated with `chattr +i`).
- **A book where the revenue line bites.** On this book no revenue option changed a box (defect 3), so I couldn't see one working. A book with a real RANR effect in pockets of the right size would show whether the line ever matters.
- **A low-default book.** The suggested floor (defect 1) and the fallback (defect 6) matter most at bad rates of 1 to 2%. The synthetic book is at 7.13%.
- **Whether the firm meant the floor to be a gate.** The design notes say the loans needed is "evidence, not a gate". The suggestion is applied as the fewest-loans gate. Which was intended is their call.
- **A team's shared memory.** Defect 2 was produced by one scratch memory file shared across wrong-turn folders. I didn't try two users writing to it.
- **The many-tests allowance across grids.** Still open from walk 4. REV_DEBT 6,559 to under 9,837 / Broker is flagged *earning less* (0.74x) on a book with no RANR effect.
- **Scale.** 8,000, 6,000 and 5,000 loans. Each run took a few seconds.
- **The repository moved during the walk.** Two commits landed after `5ef61df`: `d4988dc` ("a direct test that boxes follow the lines") and `26929c3` ("the Split tab says its method once; every Luck alone figure carries the allowance"). The second may touch defects 3 and 4. I walked `5ef61df` as frozen and didn't look at either.

---

## Where each walk-4 defect stands (seen on screen, `5ef61df`)

| # | Walk-4 defect | Now |
|---|---|---|
| 1 | A debt effect reported where the score isn't held fixed | **Held in part.** Split leads each paragraph with what its grid holds fixed. Every Three-way row carries it, with FICO grids first in each measure (`step-18c-split-tab.png`, `step-18f-three-way-holds-fixed.png`). On the no-effect book, ORIG_BAL grids still read 1.62x "under 0.01%", and a red 2.77x row stays. The caveat is the 18th column (defect 4). |
| 2 | Box against the band, dollars against the book | **Held.** Dollars, order and chart names use the box's comparison. 0 of 105 rows contradict their dollars. Only *Losing more* pockets are named (`step-13-losses-vs-revenue.png`, `step-13b-chart.png`). |
| 3 | Untested pockets boxed and coloured | **Held.** "Not tested: too few loans or losses", no colour, off the chart. Pockets under the fewest-loans line are still left off the tab without a word (defect 1). |
| 4 | The luck line | **Held in part.** It is now luck alone (1.17x, not 1.25x), and a side needs its own test, so a small pocket can't cross on noise. It still moves with the bands (1.17x, then 1.16x with the LOB's edges), and Check says so. New: it changes no box on this book, and it's below what the tool's own test calls luck (defect 3). |
| 5 | 95 told to type 0.95, then refused | **Held.** "Type a share between 0.01 and 0.9: for 15%, type 0.15." 0.95 is refused without a hint (`step-13d`, `step-13e`). |
| 6 | The booked amount can split | **Held, by design.** It runs, and the message says "(the booked amount too)" (`wrong-split-booked.png`). |
| 7 | Charts | **Held in part.** 1.00x on both axes, names only for *Losing more*, the count line wraps. Still three GCO ticks, unlabelled lines, no box names (defect 11). |
| 8 | 0.0% beside "under 0.01%" | **Held.** Small values print as 0.02%, 0.01% (`step-12-where-it-bleeds.png`). |
| 9 | Start here after a Run; the message box | **Held.** Start here reads 0 after the Run (`step-17b`). The whole ten-line refusal fits in the box (`step-08`). |
| 10 | Control layout and wording | **Held in part.** "inside that gap" is there, and Check drops "(suggested)". The revenue question still wraps tight against *Is it real* (not changed, as the fix table said). Control's *In use* still shows "(suggested)", and no number (defect 8). |
| 11 | Other wording | **Held.** "an average"; after a Forget the row says "Forgotten on Learned; it was remembered before", and the second Run names CHANNEL; the Learned subtitle; the 2% option; Run with the workbook picked; the full stop after a renamed column; Odd values in the Next line; "Nothing is worse for ..." (`step-20`, `step-23b` to `step-23d`, `wrong-picked-workbook-run.png`). |

---

## Where each defect stands (25 Sep 2026, after the fixes)

The firm decided 1 and 3 (OC-30 in `docs/design.md`). Every fix is held by a test, with a planted bug to prove the test catches it. Seen through LibreOffice.

| # | Defect | Now | Test |
|---|---|---|---|
| 1 | The suggested fewest loans hid the planted pocket | **Fixed.** Suggested at 5 expected losses (about 71 here), the textbook floor. The 99-loan pocket with 50 bad loans is tested | `test_suggested_answers_*` |
| 2 | Other workbooks' band edges written in; clearing didn't undo | **Fixed.** A remembered edge only fills a column the workbook hasn't seen, and says so under Look first. Clearing a cell on a confirmed run forgets the edge | `test_remembered_edges_only_fill_*` |
| 3 | The Control lines didn't decide the boxes | **Fixed the way the firm chose.** The lines decide; a side whose own test calls it luck is marked "(… gap could be luck)" | `test_losses_vs_revenue_boxes_follow_*`, `test_a_luck_gap_keeps_its_box_*` |
| 4 | A no-effect book can read as having a debt effect | **Fixed in part.** The Split tab puts grids that don't hold FICO fixed under their own warning heading. The Three-way tab has a short "Holds FICO fixed?" column and lists those rows last. The numbers themselves are unchanged, since they're what the data says | `test_three_way_rows_say_*` |
| 5 | "About the same" hid a could-be-luck gap | **Fixed** by 3: a 1.76x gap reads "Losing more (loss gap could be luck)" | `test_a_luck_gap_keeps_its_box_*` |
| 6 | Check said "worked out" when a fallback was used | **Fixed.** It names what fell back | — |
| 7 | "every 1" said 61 bands | **Fixed.** It says the real count | `test_a_band_width_too_narrow_*` |
| 8 | Suggested numbers not on Control, in the window or in the record | **Fixed.** A "Last Run used" column on Control, a line in the window, and the revenue line in the record's header | `test_control_shows_what_the_last_run_used` |
| 9 | `cube init` offered calc and luck | **Fixed.** The cube file's [CONFIRM] lists numbers only | — |
| 10 | Remembered edges shown in codes and unmarked | **Fixed in part.** Marked under Look first on Columns. Learned lists them after the meaning | — |
| 11 | Chart gaps | **Open.** The GCO axis still has three ticks, and the lines and boxes aren't labelled on the chart | — |
