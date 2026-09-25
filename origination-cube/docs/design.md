# Origination Cube: design

**The business argument:** if the overall buy box looks fine, find the places
where it isn't, and prove them. The firm advises the line of business (LOB).
The cube finds the pockets, and the proof stage shows each one is a real group
that can be told apart from its peers, not luck and not something else in
disguise.

**Who decides what.** The firm, 25 Sep 2026:

> i don't want the engine to decide a charge-off amount or something is or is
> not important, that is the professional's judgment to apply. this is meant to
> be a very efficient tool for helping perform such analysis.

So the tool does the arithmetic, runs the tests, and lays out the evidence for
each judgment. The professional makes every call about what matters. Where the
tool can reasonably guess (which column is GCO, which is the key), it suggests,
says why, and waits for a yes.

Written 25 Sep 2026. **Built:**
- the engine
- the per-pocket test
- `cube init`
- the Control tab

**Proposed, and the firm reacts before it's built:**
- the workbook's other tabs
- drill-down
- the proof stage

## The three stages

```
 FIND                        DRILL                         PROVE
 every column alone,         each flagged pocket cut        the pocket as a rule on the
 every band x dimension      by every other column:         loans: does it hold on loans
 -> every pocket ranked      which factor explains          it wasn't found in, how many
    on "Where to look"          the bleed inside it?           dollars, and what the book
                                                               looks like without it
```

All three are commands of the one tool (`cube run`, `cube drill`, `cube
prove`), reading the same extract, the same cube file and the same Control tab.
Each writes what it checked beside what it found.

## Step 0: what an extract must carry, and how the tool finds it (built)

The firm's minimum, 25 Sep 2026. The run refuses if any of these is missing.

| Line | What it is | Why it's required |
|---|---|---|
| `key:` | loan or application number | "or we cannot perform the remapping exercise": every pocket must map back to its loans |
| `booked:` | booked or loan amount | "averages and stuff in consumer tends to be weighted on a reporting level" |
| `outcome:` | any yes/no: charged off, ever delinquent, decided by the system | the binary the rates are built on. `{field: X, is: AUTO}` makes any column yes/no |
| `gco:` | gross charge-off dollars | the ratio comparisons |
| `ranr:` | RANR dollars (negatives kept) | the ratio comparisons |

Every run builds four core rates from these:
- the outcome as a share of loans (straight)
- the outcome as a share of booked dollars (weighted)
- GCO per booked dollar
- RANR per booked dollar

Extras go under `measures:`, and `per: each_loan` gives a straight average of
any column.

The key used to be warn-not-stop in the VBA (D55). It is now required,
because remapping is part of the job.

**`cube init EXTRACT -o cube.yaml`** reads the extract and writes the cube
file with everything filled in that can reasonably be filled in:

- **The five required columns are suggested**, each with its reason, for
  example `gco: GCO_AMT  # SUGGESTED - name contains 'gco'; zero on 95% of
  loans, never negative`. A suggestion needs both the name and the values to
  fit. The name hints are in `settings.yaml`, so a bank's own column names can
  be added there. The file carries `columns_confirmed: no`, and the run refuses
  until a person sets it to `yes`. A wrong suggestion is fixed by typing the
  right column name over it. Where nothing fits, the line asks the question and
  lists the candidates.
- **Every other column is classified**:
  - **band:** numbers with many values
  - **dimension:** text with few values, numbers with few values (term,
    grade), or codes written with leading zeros
  - **key:** a different value on every row
  - **date:** dates
  - **skipped:** empty, or one value only
  - **question:** too many categories to cut by, a mix of numbers and text, or
    a number that differs on every row (an ID or an amount?)

  Only the clear cases are decided. The limits (12 values, 50 values) are
  settings on the Control tab.
- **Odd values are raised as questions and never stop the run**: a -9999
  repeated far outside the rest, or negatives in a mostly positive column
  (RANR's are real, and the tool asks rather than decides). Until you answer,
  the values are used as recorded and every output says so. `missing` turns
  the answer into a rule and `real` closes the question.
- **Nothing is cut by its own outcome.** Once GCO, RANR and the outcome are
  named, they are left out of the bands and dimensions, with a warning saying
  why. A column recorded after the loan was made (a status, days past due) is
  also an outcome. The tool can't tell when a column was recorded, so the file
  says to take such columns out.

## What "every band crossed with every dimension" means

- **A band** is a number column cut into ranges: score, DTI, LTV, loan amount.
- **A dimension** is a category column: channel, asset class, state.
- **A grid** is one band crossed with one dimension. Each crossing is a
  **pocket**.

A problem that only exists in a combination hides on each column alone. For
example, under-620 at 1.3x the book and marine at 1.1x can hide under-620
marine at 4x.

**Bands are yours to set** (the firm: "we could make more or less bands"). Each
band is either:
- **cut points you give**: `edges: [620, 680, 740]`
- **a count**: `count: 5, cut: equal_loans` (equal numbers of loans per band)
  or `cut: round` (the same, snapped to round numbers like 650 and 700)

The edges actually used are printed with every run.

A synthetic run showed why band count matters. The planted pocket sits below
620, but five equal bands put the first edge at 653, which diluted the
pocket's gap from 6.6x to 3.3x. Ten bands, or your own edges, sharpen it.

## Does a pocket underperform, and is it real (built)

Every pocket is compared three ways. Each comparison has its own multiple and
its own test.

| Compared with | What it shows |
|---|---|
| The rest of the book (without the pocket) | Does it stand out overall? |
| The rest of its band (without the pocket) | Does it stand out *within* its band? For example, under-653 Broker against under-653 Branch and Online |
| The rest of its dimension level | The same, the other way |

A fourth figure, **share of losses / share of volume**, is the pocket's rate
over the whole book's rate. It's the bleed measure, and the excess dollars
behind it add to zero across a grid, which the tie-out checks.

**The word for a pocket needs two things:**
- its multiple is past your threshold, and
- the test says the gap is unlikely to be luck at your confidence.

Past the threshold but not significant reads **"gap could be luck"**. Under
your minimum loan count reads **"too few loans to test"**. The word always
comes from the comparison its test made. A test proves this: a pocket holding
60% of the book at 1.4x the rest of it would pass as "in line" if it were
compared with itself included.

The synthetic run shows the within-band view doing its job. Under-653 is worse
than the book, but under-653 Online and Branch are 0.6x the *rest of their
band*. The band's problem is Broker, and Broker alone.

**How the test works.** Each pocket keeps six sums: loans, Σ top, Σ bottom,
Σ top², Σ bottom², and Σ top×bottom. The standard error of a ratio of two sums
comes from those sums (Cochran's ratio estimator). A pocket's peers are its
parent's sums minus its own, so Excel can repeat the arithmetic from the same
six columns. With every loan weighted 1, the test is the textbook
two-proportion z-test, and a test checks that to nine digits.

## How many loans is enough (the firm: "30 sounds low")

The suggestion used to be a fixed 30. It is now worked out from the book:
- **how many loans a pocket needs** before a gap of your size reliably shows
- **the smallest gap each pocket's size could show**

That depends on the book's loss rate, how much loss sizes vary, your
confidence, and how often a real gap should be caught (power). On the
synthetic book, a 1.25x gap needs about 2,800 loans in the bad-loan share,
3,500 in the booked-weighted bad rate, 3,700 in the GCO rate and 450 in the
RANR rate. It shows beside every run.

**It is evidence, not a gate.** The first version used it as the minimum, and
that hid the planted pocket: 531 loans at 6.6x, obviously real. A big gap
shows in a small pocket. So the minimum loan count stays yours (the old
workbook used 30), and only stops a test from running on a handful of loans.
Each pocket's own test decides whether its gap is real.

The calculation agrees with the textbook two-proportion answer within 6% (for
a 4.65% rate: about 2,750 loans for a 1.25x gap and about 200 for 2x). A
dollar rate needs more loans than a count rate, because loss sizes vary; a test
proves that too.

## Is it material (evidence built; the call is yours)

The tool never sets materiality. For every grid it shows what each level
would keep. This is the synthetic book's score × channel grid, GCO rate, as
`cube run` printed it on 25 Sep 2026:

```
Materiality evidence: what each level would keep (the level is your call)
   0.5% of book losses (83,185): 6 pocket(s), 98% of this grid's excess
   1.0% of book losses (166,370): 6 pocket(s), 98% of this grid's excess
   2.0% of book losses (332,741): 3 pocket(s), 82% of this grid's excess
   5.0% of book losses (831,852): 1 pocket(s), 56% of this grid's excess
  10.0% of book losses (1,663,703): 1 pocket(s), 56% of this grid's excess
```

Read it as a trade-off: going from 1% to 2% drops three pockets and 16 points
of the bleed.

You choose on the Control tab: 1% of losses, 5% of losses, no floor, or your
own dollar amount. Pockets under the level are listed below the line with their
combined total, never hidden (ruling OC-8).

## The Control tab (built: `cube control --out control.xlsx`)

Each setting is either **your judgment** or **method**:

- **Your judgment**: opens blank, and the run waits until you choose. Where the
  old workbook had a value, the option says so, but it isn't chosen for you.
- **Method**: opens on the recommended option, which is printed on every
  output.

| Group | Setting | Whose call | Takes effect |
|---|---|---|---|
| What the cube looks at | Which cuts / drill depth | method | re-run |
| | Loan age | **judgment** | re-run |
| How columns are recognised | Few values = category (12) / too many categories (50) | method | re-run |
| | How many bands (5) / where edges fall (equal loans) | method | re-run |
| Is it enough loans to matter | Fewest loans to test / fewest losses | **judgment** | live |
| Is it material | Smallest excess worth reporting | **judgment** | live |
| Does it underperform | Judged against / worse at / better at | **judgment** | live |
| Is it real | Confidence | **judgment** | live |
| | Power, multiple-test allowance | method | live |
| Proving it | Where it's tested (later originations) | method | re-run |

`cube init --control control.xlsx` writes your answers into the cube file.
Without a Control tab, every judgment line stays `[CONFIRM: ...]`.

**Not wired yet:** loan age, fewest losses, materiality, judged-against, and
the multiple-test allowance are on the Control tab, but the engine doesn't
apply them yet. They arrive with the workbook.

## Prove: from the pocket to the loans (proposed)

The firm asked for this to be "integrated into that script ... as a separate
function ... and checks should be built in yes. this has to be auditable".
So `cube prove` runs in the same tool, on the same cube file, and takes a
pocket written as a rule, for example `FICO < 620 AND CHANNEL = Broker`. It
shows:

1. **The group against the rest of its peers:** rate, multiple, test, and the
   allowance for many tests.
2. **That it held on loans it wasn't found in:** later originations, or the
   other half.
3. **That it isn't something else in disguise:** the gap within each level of
   every other column. The Portfolio Analysis Pack's step 4 is copied for
   this, extended from yes/no outcomes to dollar rates.
4. **The buy box with and without it:** the loss rate without the group,
   losses avoided, and volume given up.
5. **The loans:** every key in the group, so the LOB can check them. This is
   why the key is required.

**Auditable means each of these:**
- every figure sits beside the arithmetic that produced it
- every tab ties out to the book
- the output records the extract's hash, row counts and settings
- the list of loans reproduces every number from the loans alone

## Size

The firm's example population is 17,000 rows by about 80 columns. 100 grids
over 17,000 synthetic loans took 3.7 seconds with 1,700 tie-out checks
(measured 25 Sep 2026, before the per-pocket test was added). Pure Python is
enough.

## Rulings, 25 Sep 2026 (OC-1 to OC-4 are in `vba-findings.md`)

- **OC-5:** cross everything and rank it.
- **OC-6:** compare each pocket with the book and with its peers, a level down
  as well.
- **OC-7:** odd values are raised as questions and never stop the run.
- **OC-8:** materiality applies when reading, never when building.
- **OC-9:** a control center with explained options, and your own value
  allowed.
- **OC-10:** a proof stage on the loans themselves.
- **OC-11:** band count and cut points are the professional's to set (*"we could
  make more or less bands"*).
- **OC-12:** columns are recognised as band, dimension or neither by the tool,
  and only the clear cases are decided (*"hopefully we are self-identifying"*).
- **OC-13:** judgment settings are never pre-chosen; the tool gives evidence
  (*"that is the professional's judgment to apply"*).
- **OC-14:** the minimum an extract must carry is a yes/no outcome, GCO, RANR,
  the booked amount and a key. The key becomes required, reversing D55's
  warn-not-stop for this tool.
- **OC-15:** the required columns are suggested with reasons and confirmed by one
  line (*"make assumptions for suggestions but ultimately ask for confirmation
  ... and be able to fix it easily"*).
- **OC-16:** proof is a separate command of the same tool, with its checks built
  in and auditable.

## Open

- **(a) The workbook's other tabs:** Where to look, Data questions, the
  grids, and the check tab. Next to build.
- **(b) The origination date and as-of date columns for loan age.** They can
  be suggested the same way the required columns are.
