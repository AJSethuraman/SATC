# Origination Cube: design

**The business argument:** if the overall buy box looks fine, find the places
where it isn't, and prove them. The firm advises the line of business (LOB).
The cube finds the pockets, and the proof stage shows each one is a real group
that can be told apart from its peers, not luck and not something else in
disguise.

Written 25 Sep 2026 from the firm's answers the same day. Slice 1 (the engine)
is built. Everything below it is proposed, and the firm reacts before it is
built.

## The three stages

```
 FIND                        DRILL                         PROVE
 every column alone,         each flagged pocket cut        the pocket as a rule on the
 every band x dimension      by every other column:         loans: does it hold on loans
 -> every pocket ranked      which factor explains          it wasn't found in, how many
    on "Where to look"          the bleed inside it?           dollars, and what the book
                                                               looks like without it
```

All three read the same extract and the same Control tab. Changing a live
setting recalculates the workbook at once. Changing a re-run setting means
running the script again, and every output page prints the settings it was
built with.

## What "every band crossed with every dimension" means (question 1)

- **A band** is a number column cut into ranges: score, DTI, LTV, loan
  amount.
- **A dimension** is a category column: channel, asset class, state, product.
- **A grid** is one band crossed with one dimension. For example, score bands
  down the side and asset class across the top gives score-under-620 × auto,
  score-under-620 × marine, and so on. Each crossing is a **pocket**.

Why cross them all: a problem that only exists in a combination is invisible
on either column alone. For example:

- Under-620 loans run at 1.3x the book's rate. That's worrying but expected.
- Marine loans run at 1.1x. That's fine.
- Under-620 marine loans run at 4x. That's the finding, and neither column
  alone shows it.

The cost is volume. An 80-column extract might hold 10 bands and 10
dimensions: 100 grids and a couple of thousand pockets. So nobody reads the
grids. The **Where to look** tab ranks every pocket from every grid by excess
dollars, shows only the material and significant ones, and links each to its
grid.

It also groups the ones that are the same loans seen twice: "under 620 ×
Broker" and "under 620 × high DTI" may be largely the same loans. The firm
designs the population so every column is there for a reason, so crossing
everything is the recommended setting.

## What a pocket is compared with (question 2: "both, right?")

All three comparisons are shown. The Control tab picks which one raises the
flag.

| Compared with | Example | What it shows |
|---|---|---|
| The whole book (topline) | under-620 marine against everything | Does it stand out overall? The simplest story for the LOB |
| Its parent | under-620 marine against all of under-620 | Does it stand out *within* its band? A band you expected to be bad is only a finding where it's worse than its own peers |
| The rest of its peer group | under-620 marine against under-620 not-marine | The fair test. The parent includes the pocket, so a big pocket pulls its parent toward itself and hides part of the gap. This is the default flag |

Drilling repeats this one level down. Inside a flagged pocket, every other
column is cut. The pocket is now the parent, and each new pocket is compared
with the rest of it. That's the firm's "further categorize it to see if we can
figure out where it's bleeding", done for every column instead of the one
someone thinks of.

## Odd values are raised as questions and never stop the run (question 4)

The firm, on RANR: negative values *look* like a missing-value code but are
real. The engine cannot tell which is which, and it must not guess.

- **The profile pass looks for these patterns:**
  - one value repeated far more than its neighbours at an extreme (-9999, 999,
    all nines)
  - negatives in a column that is almost always positive
  - a spike at exactly zero
  - values outside what the rest of the column suggests
- **Each one becomes a row on a Data questions tab.** The row shows the
  column, the pattern, how many loans it touches, how much of the book's
  losses sit on them, and a sample. Beside it is a dropdown: *real* or
  *treat as missing*.
- **The run does not stop.** Until a question is answered, the values are used
  **as recorded**. That isn't a guess, because it's what the data says. The
  cover says in red: "3 data questions open: results use the values as
  recorded."
- **An answer is kept against the column name and the pattern.** RANR's
  negatives, once marked *real*, are never asked about again. *Treat as
  missing* becomes a rule like the ones in slice 1 (`missing: {FICO: {below:
  -1000}}`), counted wherever it applies.

This reverses the VBA's rule that an undecided REVIEW row stops the run. The
firm asked for that on 25 Sep: surface it "but not by breaking the process and
stopping/restarting". The difference is honest because it's visible: an open
question is on the cover, not buried.

## Materiality applies when the cube is read, never when it's built (question 5)

The firm: *"there should be materiality thresholds within the cube and its
uses, but i don't think for making it... why would we want to totally ignore
them?"*

- **Every pocket is built and kept**, however small. The tie-out needs every
  loan in some pocket, and a small pocket is still information.
- **Thresholds decide what is read, flagged and reported:**
  - fewest loans
  - fewest loans with a loss
  - smallest excess worth reporting
  - how much worse counts as worse
  - how sure
- **Pockets set aside by a threshold get their own list**, "Below the line",
  with the reason and the dollars they hold together. Many small pockets can
  add up to a material amount, and that total is itself a finding.

## The Control tab

Built (this commit): `cube control --out control.xlsx`. Every setting has a
dropdown of options, each with a one-line explanation of what the math does,
plus a cell for your own value. The options and explanations live in
`src/origination_cube/settings.yaml`. The settings:

| Group | Setting | Options | Takes effect |
|---|---|---|---|
| What the cube looks at | Which cuts | every pair (rec.) / singles / named pairs | re-run |
| | Drill depth | none / one level (rec.) / two | re-run |
| | Loan age | all / 12 months / 24 months (rec.) | re-run |
| When a pocket can be read | Fewest loans | 30 (old workbook, rec.) / 100 / 300 | live |
| | Fewest loans with a loss | 5 / 10 (rec.) / 20 | live |
| When a pocket matters | Smallest excess | 1% of losses (rec.) / 5% / none / your $ amount | live |
| | Worse at | 1.25x (old workbook, rec.) / 1.5x / 2x | live |
| | Better at | 0.8x (old workbook, rec.) / 0.67x / 0.5x | live |
| Is it real | Judged against | rest of peer group (rec.) / parent / whole book | live |
| | Confidence | 90% / 95% (rec.) / 99% | live |
| | Many pockets at once | none / Benjamini-Hochberg (rec.) / Bonferroni | live |
| Proving it | Where it's tested | same loans / earlier vs later originations (rec.) / random halves | re-run |

Two of these deserve a sentence each, because they are what separates a lead
from a finding:

- **Many pockets at once.** Scan 2,000 pockets at 95% confidence and about 100
  will look significant by chance alone. The recommended allowance keeps the
  share of lucky finds among the flagged pockets to about 5%.
- **Where it's tested.** A pocket found by searching always looks worse than it
  is, because the search picked it for looking bad. The strongest evidence
  for the LOB is that the pocket, defined on earlier originations, is still
  worse on later ones it was never shown.

### How the tests work

Excel can recalculate these, so confidence and the other live settings can
change on the spot:

- **A loan-count rate** (the share of loans that went bad) is tested as two
  proportions, with the Wilson interval (copied from the Portfolio Analysis
  Pack).
- **A dollar rate** (GCO per balance) is a ratio of two sums, and big loans
  count for more. It is tested with the standard error of a ratio. Python
  writes five sums per pocket (Σy, Σx, Σy², Σx², Σxy) and the count, and Excel
  computes the rest.

## Prove: from the pocket to the loans

Once the Where to look tab has named a pocket, it is written as a rule on the
loans, for example `FICO < 620 AND ASSET_CLASS = Marine`. The rule can be
edited or narrowed, and it produces the evidence the LOB needs:

1. **The group against the rest of its peers.** Rate, gap, interval, and
   significance, after the allowance for many tests.
2. **It held on loans it wasn't found in.** The same rule on later
   originations, or on the other half.
3. **It isn't something else in disguise.** The gap within each level of every
   other column. If under-620 marine is really just "large loans", the gap
   disappears within each loan-size band. The Portfolio Analysis Pack already
   runs this check (its step 4).
4. **The buy box with and without it.** The book's loss rate with the group
   removed, the losses avoided, and the volume given up, as loss avoided per
   dollar of volume. That's the trade-off the LOB will weigh.
5. **The loans themselves.** The key column of every loan in the group, so the
   LOB can check them in their own systems. This is why `key:` matters.

## Size

The firm's example population: 17,000 rows by about 80 columns. At that size
pure Python is fast enough: 100 grids over 17,000 synthetic loans took 3.7
seconds, with 1,700 tie-out checks (measured 25 Sep 2026). numpy isn't
needed unless populations grow past a few hundred thousand rows.

## Rulings recorded 25 Sep 2026 (continuing OC-1 to OC-4 in `vba-findings.md`)

- **OC-5:** cross everything and rank it, rather than read every grid. (*"ideally
  this is very fluid and provides as much as possible"*)
- **OC-6:** every pocket is compared with the whole book, its parent and the rest
  of its peers, and drilling repeats that a level down. (*"both, right?"*)
- **OC-7:** odd values become questions that never stop the run; they are used as
  recorded until answered, and the cover says so. (*"surface for the user to
  determine before going forward somehow? but not by breaking the process"*)
- **OC-8:** materiality applies when the cube is read, never when it's built.
  Pockets under a threshold are listed with their total. (*"why would we want to
  totally ignore them?"*)
- **OC-9:** a control center with a few options per setting, each explained, and
  your own value allowed.
- **OC-10:** a proof stage on the loans themselves: *"if our overall buybox appears
  okay, we should identify the places it isn't and prove it out."*

## Open

- **(a) Where the proof stage lives.** The recommendation is to build it inside
  the cube, on the same extract and Control tab, copying the Portfolio Analysis
  Pack's statistics and its "something else in disguise" check. The alternative
  is to hand the rule to the Pack, whose six steps already do most of it, but
  for one yes-or-no outcome per loan, not dollar rates.
- **(b) The loan-age setting needs two columns the cube doesn't ask for yet:**
  the origination date and an as-of date.
- **(c) Dollar materiality:** does the LOB have a number of its own? If so, it
  goes in as "your own value".
