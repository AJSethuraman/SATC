# Producing a Schedule C profit and loss — the whole job, step by step

**Who this is for.** Anyone doing this job for the first time, or for somebody
else. It takes about twenty minutes with the figures to hand, and it needs
nothing but a browser — no account, no internet connection, no spreadsheet
programme.

**What you end up with.** Two files: a profit and loss statement and a Schedule C
worksheet, as one PDF and one spreadsheet, saved on your own computer.

**The example used throughout.** A self-employed house painter, tax year 2025 —
*Bell & Son Painting*. Real-shaped figures: paint and materials, a van on the
mileage rate, two subcontractors, a small back-bedroom office, no stock. Every
screenshot in this document is that job being done, in order, on 6 September 2026.

**A note on dates, added the same evening.** Every screenshot here is the build
of 6 September 2026, 03:44. Later that day another session fixed several of the
faults this walk found, so on a build after **17:08 that day** five of the
warnings below no longer apply: the stock lines now clear themselves when you
untick the box (step 8), *I am not claiming it* now clears line 30 (step 22),
whole-dollar mode now rounds on screen as well as in the file (step 28), a
refused figure and a listed cost with no amount now both say so in the panel
(steps 19 and 34), and *Clear everything* now asks first (step 38). The steps
and the screens are otherwise unchanged. **If a step does not match, that is
either a fault or an out-of-date procedure, and finding out which is the job.**

<!-- ROUTE -->

---

## The figures this example uses

| Where | What | Figure |
|---|---|---|
| Line 1 | Sales and receipts | 86,417.25 |
| Line 2 | A deposit refunded | 350.00 |
| Line 8 | Advertising — signs, van lettering, local ads | 642.10 |
| Line 9 | Van, from 9,240 business miles at the 2025 rate | 6,468.00 |
| Line 11 | Two subcontract painters | 7,800.00 |
| Line 15 | Public liability insurance | 1,860.00 |
| Line 16b | Interest on the van loan | 481.36 |
| Line 17 | Last year's accountant | 450.00 |
| Line 18 | Office expenses | 212.44 |
| Line 20a | Sprayer and scaffold hire | 380.00 |
| Line 21 | Repairs and servicing | 518.75 |
| Line 22 | Paint, rollers, tape, dust sheets | 12,483.91 |
| Line 23 | Contractor licence | 310.00 |
| Line 24b | Meals, the deductible half of 843.60 | 421.80 |
| Line 25 | Work phone and lock-up electricity | 1,318.44 |
| Part V | Small tools · trade dues · protective clothing | 690.00 · 180.00 · 264.50 |
| Line 30 | Home office, 120 square feet | 600.00 |

**The answer this produces: a net profit of $50,985.95.** If you follow the steps
with these figures and land on that number, the tool is behaving. If you land
somewhere else, one of the steps below did not take.

---

# Part A · Set the job up

## Step 1 · Open the tool

**Open `satcllp.com/tools/schedule-c-profit-and-loss/`.** (Or open the saved
`index.html` file — it works the same either way, including with no internet.)

**A correct screen:** a dark blue header, the three promises under it, and then two
columns — the form on the left starting at *Which year, and whose business*, and a
panel on the right headed *Where you are* with four dashes in it. Both download
buttons at the bottom of that panel are greyed out, and under them it says
*"Nothing has been entered yet."*

![](walkthrough/schedule-c-2026-09-06/step-01-opened.png)

## Step 2 · Pick the tax year

**Set *Tax year* to the year you are doing.** The choices are 2025, 2024 and 2023.

**A correct screen:** the year you picked shows in the box. This matters more than
it looks — the line numbers move between years. Other expenses land on line **27b**
for 2025 and on **27a** for 2023 and 2024, because the IRS swapped them.

![](walkthrough/schedule-c-2026-09-06/step-02-tax-year.png)

## Step 3 · Type the business name

**Type the trading name into *Business name*.** This is what goes at the top of the
statement, so write it the way you want a bank or a preparer to read it.

**A correct screen:** the name in the box, and nothing else has changed.

![](walkthrough/schedule-c-2026-09-06/step-03-business-name.png)

## Step 4 · Say what the business does

**Type a short description into *What the business does*.** "House painting and
decorating" — a few words, not a sentence.

**A correct screen:** the description sits under the business name and appears on
the finished statement beside the tax year.

![](walkthrough/schedule-c-2026-09-06/step-04-what-it-does.png)

## Step 5 · Choose how you count income

**Under *How you count income*, pick one.** *When the money arrives* is what most
sole traders use. Pick the same one you picked last year.

**A correct screen:** one of the three is filled in. *When the money arrives* is
already chosen when the page opens.

![](walkthrough/schedule-c-2026-09-06/step-05-how-you-count-income.png)

## Step 6 · Answer whether you worked in it regularly

**Under *Did you work in this business regularly through the year?*, pick Yes or No.**
Neither is pre-chosen, so this one is easy to walk past.

**A correct screen:** one of the two is filled in.

![](walkthrough/schedule-c-2026-09-06/step-06-worked-regularly.png)

## Step 7 · Decide about stock

**Only tick *"I buy or make things to sell, and I count stock"* if you hold things
you intend to sell.** A painter does not: paint goes on the customer's wall, it is
not held for resale. It belongs on line 22 Supplies, not here.

**A correct screen when you tick it to look:** six numbered lines appear —
35 Opening inventory, 36 Purchases, 37 Cost of labour, 38 Materials and supplies,
39 Other costs, 41 Closing inventory.

![](walkthrough/schedule-c-2026-09-06/step-07-stock-opened.png)

## Step 8 · If you typed anything there, clear it before you untick

**Delete anything you typed in the stock lines, and only then untick the box.**

**This step is not optional and the screen will not tell you.** Unticking the box
hides the six lines but keeps whatever is in them in your figures — with no field
left anywhere on the page showing it. Your profit will be wrong and nothing will
say so.

**A correct screen:** the box clear, the six lines gone, and the right-hand panel
back to four dashes. *If Money coming in is showing a figure with nothing typed in
Part I, you have the leftover — tick the box, clear the fields, untick again.*

![](walkthrough/schedule-c-2026-09-06/step-08-stock-skipped.png)

---

# Part B · Money coming in

## Step 9 · Enter everything the business was paid

**Type the year's total takings into line 1, *Sales and receipts*.**
Everything — cash jobs as well as anything that came on a 1099. Commas and a
dollar sign are fine; the box tidies them up.

**A correct screen:** the figure in the box, and *Money coming in* on the right now
shows it.

![](walkthrough/schedule-c-2026-09-06/step-09-sales-and-receipts.png)

## Step 10 · Enter anything you gave back

**Type refunds and credits you gave customers into line 2.** Leave it blank if
there were none — blank means nothing here, not zero.

**A correct screen:** the figure in the box and *Money coming in* has come down by
it.

![](walkthrough/schedule-c-2026-09-06/step-10-refunds.png)

## Step 11 · Check the income total before going on

**Read *Money coming in* in the right-hand panel.** It should be line 1 minus
line 2 — here, 86,417.25 less 350.00 = **$86,067.25**.

**A correct screen:** the panel follows you down the page as you scroll, so this
figure is always visible. If it is not what you expect, fix it now rather than
after twenty expense lines.

![](walkthrough/schedule-c-2026-09-06/step-11-income-total.png)

---

# Part C · Money going out

## Step 12 · Type the everyday expense lines

**Work down Part II and type the figure you are claiming on each line that applies.**
Skip anything that does not. In this example: 8, 11, 15, 16b, 17, 18, 20a, 21, 22,
23 and 25 — the figures are in the table at the top.

**Enter the amount you are claiming, not what you spent.** Schedule C is a
claimed-figures form.

**A correct screen:** each figure sits right-aligned in its box and *Money going
out* climbs as you go. After these eleven lines it reads **$26,457.00**.

![](walkthrough/schedule-c-2026-09-06/step-12-expense-lines.png)

## Step 13 · Line 13 — leave it blank unless you have the figure

**If you have a depreciation schedule or a Form 4562, type the figure. If you do
not, leave line 13 empty and tell your preparer what you bought.**

The tool will not work depreciation out — it depends on what each item cost, when
you started using it, and what you have already claimed in earlier years.

**A correct screen:** under the box, in small grey type: *"From your depreciation
schedule or Form 4562. This tool does not work it out."* If you do put a figure
there, *Worth checking* on the right adds: *"Depreciation usually means Form 4562
goes with the return too."*

![](walkthrough/schedule-c-2026-09-06/step-13-depreciation-refused.png)

## Step 14 · Open the mileage helper

**On line 9, click *Work it out from miles*.**

**A correct screen:** the section opens and warns first: *"Only if you are using
the standard mileage rate. If you are claiming what the vehicle actually cost you,
enter that figure instead — this tool does not work that out."* Below it, an empty
box and a *Use this figure* button.

![](walkthrough/schedule-c-2026-09-06/step-14-mileage-helper-open.png)

## Step 15 · Type your business miles

**Type the business miles from your mileage book into the box.** Miles, not
dollars — the box does not say so.

**A correct screen:** a line appears reading
*"$6,468.00 — 9,240 business miles at 70 cents a mile. Source: IRS Notice 2025-5
(announced in IR-2024-312)."* It names the notice the rate came from; if it does
not, something is wrong.

![](walkthrough/schedule-c-2026-09-06/step-15-mileage-worked-out.png)

## Step 16 · Put the figure on line 9

**Click *Use this figure*.**

**A correct screen:** line 9 now holds `6,468.00`, *Money going out* has risen by
it, and further down the page a new section headed *Your vehicle* has appeared.

**Remember what that figure already covers:** the mileage rate includes the van's
fuel, insurance, servicing and repairs. Do not also claim those on lines 15 and 21.

![](walkthrough/schedule-c-2026-09-06/step-16-mileage-onto-line-9.png)

## Step 17 · Work out the deductible half of your meals

**On line 24b, click *Take half of what I spent* and type what the qualifying meals
cost.**

**Qualifying meals only** — a meal with a business reason, or one on a trip that
kept you away overnight. An ordinary lunch while working locally is not deductible,
and the box will happily halve it for you anyway.

**A correct screen:** *"$421.80 — half of what you spent. Some meals are not half.
Drivers under federal hours-of-service rules deduct 80%, and a few meals count in
full."*

![](walkthrough/schedule-c-2026-09-06/step-17-meals-helper.png)

## Step 18 · Put the meals figure on line 24b

**Click *Use this figure*.**

**A correct screen:** line 24b holds `421.80` and *Money going out* is up by it.

![](walkthrough/schedule-c-2026-09-06/step-18-meals-onto-line-24b.png)

## Step 19 · List the first cost that has no line of its own

**Under *Anything else you spent money on*, type what it was in the left box and
the amount in the right.** Software, bank charges, dues, small tools.

**A correct screen:** both boxes filled and *Money going out* up by the amount.
A row with a description and no amount is dropped without a word, so always fill
in both.

![](walkthrough/schedule-c-2026-09-06/step-19-other-expense-first-row.png)

## Step 20 · Add the rest of them

**Click *Add another* for each further cost, then fill both boxes.** Schedule C has
room for nine; beyond that it goes on an attached list.

**A correct screen:** each row shows a description and an amount, and the total is
carried to line 27b for 2025.

![](walkthrough/schedule-c-2026-09-06/step-20-other-expenses-listed.png)

## Step 21 · Remove any row you do not need

**Click *Remove* on the row.**

**A correct screen:** that row goes and the others are untouched, in order.

![](walkthrough/schedule-c-2026-09-06/step-21-remove-empty-row.png)

---

# Part D · Working from home, and the van

## Step 22 · Choose how you work the home office out

**Under *Working from home*, pick a method.** *The square-foot method* is the
simple one. *The detailed way, on Form 8829* means you work the figure out
elsewhere and type the result. *I am not claiming it* is chosen when the page
opens.

**A correct screen:** one of the three is filled in.

**Watch this one.** Choosing *I am not claiming it* does **not** remove a home
office figure you have already entered — line 30 stays on the page and stays in
your profit. If you decide not to claim, clear line 30 by hand.

![](walkthrough/schedule-c-2026-09-06/step-22-home-method.png)

## Step 23 · Type the square feet

**On line 30, click *Work it out from the square feet* and type the floor area of
the room.** Square feet, not dollars.

**A correct screen:** *"$600.00 — 120 square feet at $5 a square foot. Source: 2025
Instructions for Schedule C, line 30 (Simplified Method)."* Over 300 square feet it
caps at 300 and says so.

![](walkthrough/schedule-c-2026-09-06/step-23-home-square-feet.png)

## Step 24 · Put it on line 30

**Click *Use this figure*.**

**A correct screen:** line 30 holds `600.00`, *Working from home* shows $600.00, and
*Profit for the year* has dropped by it — **$50,985.95**.

![](walkthrough/schedule-c-2026-09-06/step-24-home-onto-line-30.png)

## Step 25 · The vehicle questions appear

**Scroll to *Your vehicle*.** This section only exists because line 9 has a figure
in it; on a return with no car costs it is not there at all.

**A correct screen:** six questions — when you first used it for the business,
three mileage boxes, and four yes/no pairs. *Business miles* is already filled in
with the miles the helper used.

![](walkthrough/schedule-c-2026-09-06/step-25-vehicle-questions-appear.png)

## Step 26 · Answer them

**Fill in the date, the commuting and other miles, and the four yes/no questions.**
*Miles getting to and from work* means commuting — home to the job and back.

**A correct screen:** every question answered, nothing left blank. These go into
the finished document under *What the form also asks*; anything you skip prints
there as "Not answered" and your preparer will come back to you about it.

![](walkthrough/schedule-c-2026-09-06/step-26-vehicle-answers.png)

---

# Part E · Check it, then produce the files

## Step 27 · Read the panel before you download anything

**Read the whole right-hand panel from the top.**

**A correct screen:** four figures — money coming in, money going out, working from
home, and the profit — then the two choices, then two live download buttons. Below
them, *Worth checking* lists anything the tool thinks is worth a second look; on a
clean return it is empty.

![](walkthrough/schedule-c-2026-09-06/step-27-worth-checking.png)

## Step 28 · Choose how the figures are shown

**Leave *How to show the figures* on *Dollars and cents* unless you have a reason
not to.** Cents are what a preparer or a bank wants. *Whole dollars, the way it is
filed* is for matching what will go on the return.

**A correct screen:** the panel figures switch between `$50,985.95` and `$50,985`.

**Known fault:** in whole-dollar mode the panel *cuts* the cents while the file
*rounds* them, so the screen can read a dollar lower than the PDF you are about to
download — $50,985 on screen against 50,986 in the file. The file is the correct
one. Use *Dollars and cents* and the question does not arise.

![](walkthrough/schedule-c-2026-09-06/step-28-whole-dollars.png)

## Step 29 · Download the PDF

**Choose what goes in it — *Both* is the usual answer — then click *Download the
PDF*.**

**A correct screen:** the file saves as
*BusinessName-2025-profit-and-loss.pdf*. Nothing is uploaded; the file is made in
your browser.

![](walkthrough/schedule-c-2026-09-06/step-29-download-pdf.png)

## Step 30 · Download the spreadsheet

**Click *Download the spreadsheet*.**

**A correct screen:** the same name with an `.xlsx` ending. The spreadsheet always
carries both the statement and the worksheet, plus a detail sheet, whatever you
chose for the PDF.

![](walkthrough/schedule-c-2026-09-06/step-30-download-spreadsheet.png)

## Step 31 · The offer appears — after the file, not before

**Scroll to the bottom.**

**A correct screen:** a panel headed *You have your file* that was not there
before. It is hidden until a file has actually been produced. **If you are ever
asked for an email address before a download, you are not on this tool.**

![](walkthrough/schedule-c-2026-09-06/step-31-after-download.png)

---

# Part F · Keep it, check it, put it away

## Step 32 · Keep a draft, if the computer is yours

**Tick *Keep what I have typed on this device* only on your own machine.** It is
off when the page opens, and the draft is stored in that browser and nowhere else.

**A correct screen:** the box ticked. **Do not tick it on a shared or library
computer.**

![](walkthrough/schedule-c-2026-09-06/step-32-keep-a-draft.png)

## Step 33 · Check the draft comes back

**Close the page and open it again.**

**A correct screen:** everything is back — the name, every figure, the listed rows,
the vehicle answers, the method choices — and the panel reads the same profit as
before you left.

![](walkthrough/schedule-c-2026-09-06/step-33-draft-came-back.png)

## Step 34 · What a refused figure looks like

**Recognise this, because you will hit it:** type a figure the tool cannot read —
two decimal points, letters, three decimal places — and it is refused where you
typed it.

**A correct screen:** red text under the box saying what is wrong, for example
*"Use numbers only, like 1234.56"*.

**What the screen does not tell you:** while a figure is refused, both download
buttons go dead with no explanation, and the profit at the top of the panel
silently leaves that line out — so it will be wrong, and it will look plausible.
**If the download buttons are greyed out on a filled-in form, scroll up and look
for red text.**

![](walkthrough/schedule-c-2026-09-06/step-34-a-typo-is-refused.png)

## Step 35 · Look at the whole form once, top to bottom

**Scroll from the top to the bottom and read it.** Two minutes. This is the last
point at which a figure in the wrong box is cheap to fix.

**A correct screen:** every figure where you meant to put it, no red text
anywhere, and the profit at the top matching what you expected before you started.

![](walkthrough/schedule-c-2026-09-06/step-35-finished-form.png)

## Step 36 · Open the PDF and read it

**Open the downloaded PDF. Do not skip this.** A file you have not opened is not a
file you have produced.

**A correct document:** page 1 is the firm's name, then the business name and tax
year, then *Profit and loss* — income, gross income, the expense lines you filled
in, and *Net profit or (loss)* at the bottom. Then *2025 Schedule C worksheet*
begins, in the form's own order, every line including the empty ones. Page 2
finishes Part II and carries Part III, Part V, *What the form also asks* and
*What this tool did not work out*.

**Check three things:** the business name is right, the net profit matches the
screen, and every figure you typed is on the line you meant.

![](walkthrough/schedule-c-2026-09-06/step-36-pdf-opened.png)

## Step 37 · Open the spreadsheet and check the three tabs

**Open the downloaded `.xlsx`.**

**A correct document:** three sheets — *Profit and loss*, *Schedule C 2025*, and
*Detail*. The totals on the worksheet sheet are live formulas, not typed numbers,
so a preparer can change a figure and watch the total follow. *Detail* carries the
listed other expenses, the answers to what the form also asks, and anything the
tool did not work out.

**Blank means blank.** A line nobody filled in is empty, never `0.00` — on a
worksheet those mean different things.

![](walkthrough/schedule-c-2026-09-06/step-37-spreadsheet-opened.png)

## Step 38 · Clear everything when you are done on a machine that is not yours

**Click *Clear everything*.**

**There is no "are you sure".** It wipes the whole form and the saved draft the
instant you click it, and the button sits three lines under *Download the
spreadsheet*. Download your files first.

**A correct screen:** every box empty, the panel back to four dashes, the
keep-a-draft box unticked, and nothing left in the browser.

![](walkthrough/schedule-c-2026-09-06/step-38-cleared.png)

---

# Part G · The check you can run yourself

## Step 39 · Turn the internet off and do it again

**Disconnect from the network, reload the page, type a figure and download a file.**

The tool claims your figures never leave your computer. This is how you check that
claim rather than take it on trust — a page that still works with the network off
cannot be sending anything anywhere.

**A correct screen:** the page loads, the arithmetic still happens, and the PDF
still downloads. On this run the page attempted **zero** network requests.

![](walkthrough/schedule-c-2026-09-06/step-39-works-offline.png)

---

## When something does not match

Every step above says what a correct screen looks like. If one does not match,
it is either a fault in the product or this procedure is out of date, and finding
out which is the job. Faults found on the run that produced this document are
written up in **`WALKTHROUGH-DEFECTS.md`**, ranked by what each would cost.

**The three worth knowing before you start**, on the build these pictures were
taken from: clear the stock lines before you untick that box (step 8);
*I am not claiming it* does not clear line 30 (step 22); and in whole-dollar mode
the screen reads a dollar lower than the file (step 28). All three were fixed
later the same day — see the note at the top — so on a current build those three
screens should behave, and if they do not, that is a regression worth reporting.
