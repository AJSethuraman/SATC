# Origination Cube

**Where does the book bleed?** The tool takes a loan extract and a short cube
file. It cuts the loans by bands (a score band, say) against dimensions (the
channel, say), and compares every pocket's rate with the whole book's
(the topline). The pockets that lose more than their share come out at the
top of a list, in dollars.

This replaces a set of Excel macros that did the same job slowly and kept
breaking their own rules. `docs/vba-findings.md` lists each of those breaks and
the test that stops it coming back. The macros were only a source of ideas, so
this is not a port, and the workbook was designed from scratch.

**Where it's going:** `docs/design.md` sets out the three stages (find, drill,
prove) and the firm's rulings.

**Status (26 Sep 2026):**
- **Built:** the first stage, find. That means the engine, the launcher and the
  whole workbook: Set up, Control, Columns and every results tab below.
- **Not built:** drill-down, `cube prove`, and the confirmatory test itself
  (capability 4b in `docs/capabilities-scope.md`). The cube has the inputs that
  test needs (the origination date, new columns and the pre-spec), but not the
  test.
- **Not yet met:** a real extract.

The log is `../BACKLOG.md` §6d.

## What an extract must carry

A loan or application number (`key:`), the booked amount (`booked:`), a yes/no
outcome (`outcome:`), GCO dollars (`gco:`) and RANR dollars (`ranr:`). The run
refuses without any of them. Every loan in the extract is run: none is left
out for how old it is or when it went bad, so choose the period before the
extract reaches the cube. From those it builds five core rates on every run:
- the outcome as a share of loans (straight)
- the outcome as a share of booked dollars (weighted)
- GCO per booked dollar
- profit after losses: RANR per booked dollar
- contribution before losses: RANR + GCO per booked dollar

## Using it (no commands)

One-time setup: install Python 3.10 or later from python.org. The cube also
needs three add-ons for Python:
- **numpy**, for the statistics
- **openpyxl**, to read and write Excel files
- **PyYAML**, for its settings files

The window checks for them each time it opens. If any is missing, it says
which and offers **Install now**. If the bank's network blocks the download,
it gives you a note for IT, and **Copy for IT** copies it.

To install them by hand, run this once in a Command Prompt (`py` is the
Python starter that python.org installs). `Install add-ons.bat` in this folder
runs the same thing:

```
py -m pip install --user --upgrade numpy openpyxl PyYAML
```

After that, the whole routine is:

1. Double-click **`Origination Cube.pyw`**. A small window opens.
2. Pick the extract (the loan file from the bank, .csv or .xlsx) and press
   **1. Set up from this extract**. A workbook appears beside the extract.
3. Open the workbook and follow its **Start here** tab:
   - **Control:** first, **What are you running?** Nothing is picked for you,
     and a blank answer stops the Run.
     - *Where the book bleeds:* the grids, the split and the three-way. It
       needs the five columns below and no date.
     - *Finding and testing a new variable:* it also needs a column marked
       *Origination date*, and asks one more thing: **scout first, or test
       from a pre-spec already written?** Scouting isn't built yet, so that
       answer stops the Run and says so. Testing from a pre-spec needs the
       committed pre-spec file named in the last cell (below), and the column
       it tests on Columns.

     Then fill in the other shaded cells. Those are our calls: what's
     material, how many loans is enough, how much worse counts.
   - **Columns:** check what each column is. Anything shaded has its reason
     beside it. Fix any that's wrong from the dropdown, then set "Checked
     every column" to Yes. For a new variable, mark the date each loan was
     made *Origination date*: it is what splits development loans from the
     holdout. Where the book bleeds uses it, if marked, only for one line on
     Check.
   - **Look:** each number column's smallest, median and largest value, its
     most-repeated values, its blanks and codes, and a histogram. Read it
     before typing band edges on Columns.
   - **Odd values:** answer real or missing where you can.
4. Save, close the workbook, and press **2. Run the cube**. The results land in
   the workbook:
   - **Where it bleeds:** every pocket losing more than its share, largest first.
     Each pocket has two dollar figures, its excess over the rest of its band
     and over the book. Control's "judged against" picks one, and that one
     decides the flag, whether the pocket is material and where it ranks.
     The other is shown next to it, for reference.
   - **Losses vs revenue:** what each pocket paid (contribution before
     losses), what it cost (GCO) and what was kept (profit after losses,
     RANR). GCO reads losing more, about the same or losing less by the lines
     on Control. Contribution and profit give the gap itself, e.g. "short of
     its band by 0.80 points ($16,000)". Losing more and keeping more reads
     "priced for it". One chart per grid.
   - **Grids:** heat maps against the book and against the rest of the band.
   - **Split** and **Three-way:** only when a column splits the pockets (below).
   - **Prevalence:** only with a split or a new column. How many loans and
     booked dollars sit in each group (the split's halves or values, a new
     column's bands), pocket by pocket. A count of the book, not a test.
   - **Materiality:** what each materiality level would keep.
   - **Check:** what was run, settings, tie-outs, and what was left out of each rate (a
     blank or unreadable value, never a loan's age). One line says which
     comparison decides each pocket's flag, its dollars and whether it is
     material, and another how a profit reading is worded, with this run's
     own pockets as examples. With a column marked
     Origination date, one line gives the earliest and latest date among the
     loans run and how many have no readable date, so a wrong extract shows on
     the first page. Also the pocket
     budget (the book's bad loans ÷ 5: the most pockets a grid can test) with
     each grid's pocket count and how much of the book sits in testable
     pockets; how many families of tests the run holds, since a single red
     across many is weak evidence; and a warning when a column marked Credit
     product holds more than one product and isn't a band or segment.
   - **Log:** every run and refusal, what each run was, and whether it
     followed its pre-spec and touched the holdout.

**Going a layer deeper.** On Columns, set one column's *Split pockets by it?*
to Yes. A number (revolving debt, say) splits every FICO-by-asset-class pocket
at that pocket's own median, and the Split tab compares the high half with the
low half, pocket by pocket and pooled. Each grid says what it holds fixed:
revolving debt moves with FICO, so a loan-size grid can't tell debt from score,
and it says so with the number. A category repeats each grid once per value.
Either way, every three-way pocket is tested and ranked on the **Three-way**
tab. *Show per pocket* puts a column's median or average in every pocket.
After a Run, the Look tab plots a split number against each band column, so
you can see whether it only re-sorts the band.

![The Split tab: high revolving debt against low, inside each pocket](docs/split.png)

**A confirmatory run.** A column scouted on development loans (income over
sales, say) is tested once, on loans kept back, with settings written down and
committed to git beforehand: the pre-spec (`docs/prespec-example.yaml`; the
format is in `src/origination_cube/prespec.py`). Answer *Finding and testing a
new variable* and *Test from a pre-spec* on Control, and name that file in its
last cell. A file that isn't there or can't be read stops the Run, naming the
cell, and so does a blank cell, a pre-spec whose column isn't on Columns, or a
pre-spec named for Where the book bleeds. Otherwise Check echoes what it says and
the commit it was read from (or that it isn't committed, or was edited since),
and lists, one line each, where the run differs from it; the Log marks such a
run *Deviates from pre-spec*. Every run whose extract holds loans made in the
pre-spec's holdout range is marked *Touched the holdout* in the Log, and Check
counts those runs, so how often the holdout has been looked at stays visible.
Today's cube always differs in one place: it tests each pocket's high half
against its low half, not groups against a reference group.

![Losses vs revenue: paid, cost and kept, and the chart](docs/losses-vs-revenue.png)

If something needs fixing, the window and the Log tab say what and where, in
words, e.g. *Control!C6: "What are you running?" needs an answer.* Press Set up again at any time: answers already given are kept.
What you confirm is remembered for next time; the **Learned** tab lets you set
anything wrongly learned to Forget.

![The launcher after set up](docs/launcher/launcher-02-after-set-up-screen.png)

**What an extract must carry:** a loan or application number, the booked
amount, a yes/no outcome, GCO dollars and RANR dollars. From those, every run
builds:
- the outcome as a share of loans (straight)
- the outcome as a share of booked dollars (weighted)
- GCO per booked dollar
- profit after losses: RANR per booked dollar (less of it is the bleed)
- contribution before losses: RANR + GCO per booked dollar (RANR already has
  GCO taken out)

**What each pocket carries:**
- its rate
- its rate against the book's: a multiple, or for profit a gap in points
- the excess (or, for profit, the shortfall) in dollars, twice: over the
  rest of its band and over the book. The comparison picked on Control
  decides; a pocket alone in its band has no band figure and uses the book's
- a test against the rest of the book and the rest of its band, after the
  allowance for testing many pockets at once
- whether it clears the materiality line
- the smallest gap its size could show

### Underneath (for whoever maintains it)

The same engine is behind a command line, which the tests use:
- `cube synth`
- `cube init`
- `cube validate`
- `cube run`
- `cube control`
- `cube memory`

`tools/shoot_launcher.py` photographs the window in each state on a virtual
display.

## Checking it

```
pytest -q                          # 481 tests: one per finding, the worked examples in docs/statistics.md for every test the cube runs, every Control answer applied, the workbook route, the split, profit after losses (the firm's Tests 2 and 4), the launcher, the pre-spec, the add-on check, the Look tab, the origination date (every loan runs; the range on Check; old lines refused by name) and new columns, the pre-spec checks, the pocket budget, the prevalence table, the tabs' wording, a pocket alone in its band, one comparison deciding the flag, the dollars and materiality, the literal profit wording (the one that opens the window skips without a display)
python tools/mutation_check.py     # puts 189 bugs back (the VBA's and today's rules); every one must be caught
```

**Speed** (this container, 25 Sep 2026, pure Python):

- 1,000,000 loans through one grid and five measures: 6.7 s to read the CSV
  plus 19.6 s for the cube.
- At 200,000 loans: 3.5 s for 1 grid, 5.3 s for 4, 8.2 s for 9, so each extra
  grid adds about 0.6 s.
- By extrapolation, not measured: a million loans through 25 grids would take
  about a minute and a half. numpy would cut that to seconds, if the machine at
  the bank has it.
- The shuffle test for the dollar rates (numpy, 10,000 shuffles; 26 Sep 2026)
  is on top of that, and grows with the loans: the 8,000-loan synthetic book's
  6 grids went from 0.3 s to 6.5 s in the engine (a whole Run, 2.9 s to 7.9 s),
  and at 40,000 loans from 1.4 s to 33 s. Each shuffle is one pass over the
  loans per dollar rate, for the rest of the book and once per band column, so
  by extrapolation, not measured, 200,000 loans would take about 3 minutes.
- Contribution before losses (26 Sep 2026) is a fourth dollar rate to
  shuffle: the same whole Run on 8,000 loans now takes 9.9 s.
