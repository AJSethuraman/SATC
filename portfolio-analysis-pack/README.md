# Portfolio Analysis Pack

A loan extract plus a short question file in; one self-contained Excel
workbook out. The workbook carries a fixed six-step analysis of one question
of one shape: *loans where this is true — do they go bad more often than
loans where it is not, and is that real or something else in disguise?*

Python does every calculation over the loans and writes a small **count
cube** into the workbook. Every rate, interval and headline word on the
results tabs is an Excel formula over that cube, so a reviewer changes the
confidence level or the interval method on the `_config` tab and the pack
recalculates. Bucket edges, bands and the window are rebuild knobs.

The tool knows no domain and no bank. No column name, no list of anything,
no outcome word lives in the code; a test fails if one appears. The
question file is the only place such things live, so a consumer question
is a different file, not different code. Any extract goes in: whoever holds
the file says what each column is, there, in a question file the tool
writes the skeleton for. Nothing about the file has to reach whoever built
the tool.

- **Spec:** [`docs/prd-portfolio-analysis-pack.md`](docs/prd-portfolio-analysis-pack.md)
- **Build plan:** issues #364–#372 on the repository, in order
- **Running log:** `../BACKLOG.md` §6c (credit line; not `PLAN.md`)
- **Rulings on the record:** `../canon/CONVICTIONS.md`, *Rulings by project*

**Status:** v1 built, all nine slices (18 to 19 September 2026): the ladder
plus door one, the bundle, the render harness and the mutation tool. What is
not built is deferred by ruling and logged in `../BACKLOG.md` §6c: doors two
and three, sweep mode, vintage curves. The first real run at the desk has
not happened; nothing here has met Excel itself.

## What a built pack contains

| Tab | What it shows |
|---|---|
| `Cover` | The question, the answer in three lines, the loans and events it rests on, and `N of N formula checks agree` |
| `1_Capture` | By origination quarter: loans, how many are younger than the window, blanks in each rule field, how many carry both; then seasoned loans per band for every confounder scheme |
| `2_Prevalence` | By quarter, on seasoned loans: the capture rate (both fields present) and the flag rate (rule fires among those), each with its interval, never merged |
| `3_Gradient` | The outcome rate across buckets of the rule value, each with its interval, its gap from the unflagged base in percentage points and as a multiple, and whether the rates rise at every step |
| `4_Stratified` | For each confounder and band scheme: the flagged and unflagged rates per band, the crude odds ratio beside the pooled one across bands, the share of the effect kept, and one word: survives, collapses, unknown, or no crude effect |
| `5_Decomposition` | For each dimension the question file lists: flagged and unflagged rates per level with intervals, the gap, and the share of all flagged events in the level, most first |
| `6_Model` | Two regressions side by side, values only: the flag plus the controls, then plus the confounders. Each term's odds ratio with its interval, the events per parameter printed above, and a small tree printed as plain rules with the loans, events and rate per leaf |
| `7_Control` | The observation that stands regardless: how often the two fields disagree in the seasoned book, the question file's own words on what each field drives, and what it says reacts to the disagreement today |
| `_cube` | The counts every formula reads: loans and events per cell |
| `_config` | Live knobs (confidence level, interval method) and the rebuild knobs for the record |
| `_method` | Notes on what was done, generated from the question file and the counts |
| `_check` | Python's value beside every formula cell and Excel's own verdict on whether they agree |
| `_provenance` | Source file and its hash, row counts, window, dates, generator version |

## Using it

At the desk: Python 3.10 or later with `openpyxl` and `PyYAML`.

```
pip install -e .
```

Look at an extract first. `inspect` lists every column with its kind, how
often it is blank, how many distinct values it holds, five samples, and for
a date-like column which pattern its values fit:

```
pack inspect extract.csv
```

A column of all-digit values such as `20210315` is listed as an integer with
a note that it also reads as a date, because the build will read it as one
if the question file names it as a date column.

Then say what each column is. `init` reads the extract and writes a
question file with every column listed, what was found in each beside it
as a comment, and a `[CONFIRM: ...]` marker on every value that is yours to
choose: the loan number column, the origination date, the two columns of
the ratio, the outcome, whether each column was known when the loan was
made, and what reacts to the contradiction today. Fill them in, delete the
columns the pack should not read, and validate:

```
pack init extract.csv -o question.yaml
pack validate question.yaml --data extract.csv --asof 2026-06-30
```

A file with a marker still in it is refused, and the refusal names every
one. The tool never fills a slot on your behalf.

To see which question files under a folder would be accepted, and why not
when one is refused:

```
pack list configs
```

Ask for band cut points before writing them. `suggest` proposes equal-count
bands by loans, equal-count by events, and round numbers, each with the
loans and events it would give per band and a `thin` mark where a band holds
fewer than ten events. It also prints, marked as information only, the single
cut at which the outcome rate changes most; that one is chosen on the
outcome and is not offered as a scheme for step 4.

```
pack suggest demo/config.yaml --data demo/loans.csv --asof 2026-06-30 --field field_b
```

Make a book with a known answer and build it:

```
pack synth --out demo
pack validate demo/config.yaml --data demo/loans.csv --asof 2026-06-30
pack build demo/config.yaml --data demo/loans.csv --asof 2026-06-30 -o demo/pack.xlsx
```

`validate` refuses a question file that is missing a required line and prints
the line to add. `build` refuses an extract with values it will not accept
(a zero in a rule field, a duplicate loan number, a date that will not parse,
a value outside a plausible range you gave) and writes the offending rows to
a file beside the output. Blanks are not refused: they are a finding, counted
on the capture tab once slice 3 lands.

Dates are detected. A typed date cell in an XLSX needs nothing. Text dates
are parsed by the one common pattern that fits every value in the column,
and the pattern is recorded on the provenance tab. When two patterns both
fit every value (every day is 12 or under, so month-first and day-first both
read), the build refuses, shows a sample value read both ways, and names the
line to add: `population.date_format`.

The outcome is any yes/no per loan, in one of three forms: an event date the
pack cuts at the window; a flag the bank already windowed, declared as such;
or a measure taken at the as-of date (outstanding over commitment, say) with
either one cut or a list of percentage bands, in which case every step is
shown once per band edge and no single cut is chosen by anyone but the
person writing the file.

The as-of date is required and the run date defaults to it; the clock is
never read, so the same inputs give the same bytes.

## The charts

Every gradient block on `3_Gradient` carries a column chart of the rate per
bucket, and every block on `4_Stratified` carries one of the flagged and
unflagged rates per band. The interval bars on each bar are read from helper
cells beside the table, which are formulas with their own check-tab twins,
so the picture and the numbers cannot disagree. The charts are native Excel
charts and stay live: move the confidence level and the bars move. Every tab
prints one page wide, so a chart sits beside its table on paper and in the
render harness's page images.

## The model step, in plain terms

Step 6 asks: after taking everything else into account, does the flag still
matter, and by how much? A regression is a way of asking that for several
factors at once. The number it gives per factor is an odds ratio: 2.0 on the
flag means flagged loans carry twice the odds of the outcome with the other
factors held fixed, and the interval beside it is the range it plausibly
sits in. Two regressions sit side by side: the flag plus the controls (M1),
and the same plus the confounders (M2). If the flag's ratio falls from M1 to
M2, what was lost is explained by the confounders. Above each table: loans,
events, the number of coefficients estimated, and events per parameter; below
ten the tab says the estimates are unstable and to read the intervals, not
the point estimates. When a term separates the outcome perfectly the fit is
not estimable and the tab names the term rather than printing a number.

The tree beneath is a search for the two- or three-way combination with the
most contrast, printed as plain rules with the loans, events and rate in each
leaf. A lead to check, not a proof. Everything on this tab is a value, not a
formula: a regression cannot be written as a cell, so this is the one tab that
does not recalculate and carries no check-tab twin.

All of it runs in plain Python with no numerical library, because the desk
has none. A 25,000-loan fit takes about a second.

## Getting it to the desk

Binary files do not survive a bank's email filter; plain text does. So the
tool is never sent as a package:

```
pack bundle configs/examples/stated_income_vs_sales.yaml -o build_pack.py
```

writes one pure-ASCII Python script (about 80 KB) that carries the package
and a question file inside it, and never the data. The carried file is only
the default. On the desk, with Python, `openpyxl` and `PyYAML` installed,
any extract is designated there and built there. The way a desk does it is
a form in Excel:

```
python build_pack.py --setup extract.csv
```

The first run writes `question.xlsx` beside the extract: one row per column,
with what it reads as and three sample values, and a dropdown beside each
for its role (loan number, origination date, rule top, rule bottom, how a
loan went bad, group); a second tab holds the word for the event and the
as-of date. Pick in Excel, save, run the same command again, and it reads
the form, refuses anything the loader would (every problem at once, each
with its cell), writes `question.yaml` from it and builds the pack, named
after the two rule columns. `--ask` asks the same things one question at a
time at the keyboard instead. Nothing is edited by hand either way.

The longer way, for scripts and for a question file written by hand:

```
python build_pack.py --inspect extract.csv
python build_pack.py --init extract.csv -o question.yaml
python build_pack.py --validate extract.csv --asof 2026-06-30 --config question.yaml
python build_pack.py --data extract.csv --asof 2026-06-30 --config question.yaml -o pack.xlsx
```

Without `--config`, the carried question file is used. Either way nothing
leaves the desk: not the extract, not its column names.

To try it before there is an extract, the same script writes a made-up
book with a known answer (a planted effect; `--null` for no effect,
`--confounded` for an effect that is size in disguise) and builds from it:

```
python build_pack.py --synth demo
python build_pack.py --data demo/loans.csv --asof 2026-06-30 --config demo/config.yaml -o demo/pack.xlsx
```

Open `demo/pack.xlsx`: the cover should say the gradient rises, every
block survives, and every formula check agrees.

The script prints the SHA-256 of what it wrote. Because the build is
deterministic, that hash equals a build made anywhere else from the same
inputs, which is how a reviewer proves the desk copy is the same
deliverable. A test rebuilds a fixture pack from the bundle in an empty
directory with only those two libraries on the path and compares the hash.

## Grouping a code column

The tool ships no list of anything. A column of codes is grouped by a
generic step written on the field in the question file: `derive: {kind:
prefix, length: 2}` keeps the first two characters; `derive: {kind: map,
groups: {label: [values]}, other: label}` or `groups_file: path.csv` (two
columns, value and group, beside the question file) puts values into groups
you name. They chain. A value in no group takes the `other` label and is
counted; with no `other` label the build refuses and lists the values.
`configs/examples/stated_vs_bureau_income_auto.yaml` uses a file-backed map
for regions.

A loan with no value in a grouping column is never dropped from a step. It
sits in a level called `(blank)`, always last, on the stratified and
decomposition tabs, and the capture tab counts it. That way every block's
"whole population" figure is the whole population, and a reader can see how
many loans had no value rather than wonder.

## The question file

Every slot names a column in the extract as it comes out of the bank's
system. See `configs/examples/stated_income_vs_sales.yaml` for a complete
one and the spec §6.1 for every slot. Three lines are required and never
guessed: the flag line (`rule.fires_when`), whether each column was known at
origination or later (`fields.<col>.known`), and whether anything already
reacts to the contradiction (`existing_control`).

## Verifying it here

Beyond the desk requirements: `pytest` and the `formulas` engine, which
recalculates the workbook the way Excel would; `libreoffice-calc`, which
renders it (the bare `soffice` in a container reports "source file could not
be loaded" without it); and `poppler-utils` to turn the PDF into page images
that get looked at.

```
pip install -e ".[test]"
pytest -q
python tools/render.py demo/pack.xlsx        # PDF, one PNG per page, HTML; fails on any error cell
```

The render harness writes a PNG per page under `rendered/pages/`. Look at
the gradient and stratified pages before calling a version done: the lesson
in this line is that the first two chartbooks opened cleanly and had no axis
numbers, and a harness reading a cell cannot see that.

The suite builds three 40,000-loan synthetic books (a planted effect, a
null, and an effect that is size in disguise) and reads the workbooks back
through the engine: the gradient must read as planted, the step-4 word must
be survives, no crude effect and collapses respectively, the regressions
must recover the plant and lose it under the confounders, every `_check`
row must agree, two builds must be byte-identical, and the guards must hold
(no domain word in the code, no clock read, the `_xlfn.` prefix on every
newer function).

How long it takes, measured here on 19 September 2026: a 40,000-loan book
builds in about 5 seconds and a 100,000-loan book in about 13. The workbook
is 164 KB either way, because it holds counts rather than loans; the loan
count changes how long Python works, never how big the file Excel opens is.

Then check the checker:

```
python tools/mutation_check.py
```

Nine mutations each break one behaviour in the working tree (the z quantile,
the Clopper-Pearson tail, the pooled odds ratio's direction, seasoning, the
leakage refusal, the flag's side of the line, the `_xlfn.` prefix, the check
tab's tolerance, the decomposition sort) and name the tests that must go
red. The file is restored byte for byte afterwards. CI runs it on every pull
request; a mutation that survives fails the run.

Then run the thing a person actually runs. The exercise harness makes
eleven made-up books with known answers, drives the bundle script from an
empty folder the way a desk would, reads every answer back out of the
workbook the way Excel reads it, renders the pages, and writes one report
that puts what was planted beside what the pack said, scenario by scenario,
with the checks counted:

```
python tools/exercise.py
```

The report is `docs/exercise-report.md`, with the pages beside it, and it
is regenerated whole; a green suite is not a substitute for reading it.
The scenarios: a planted effect; no effect; an effect that is size in
disguise; the outcome as a bank-set flag; the outcome as a measure in
bands; designation of an unseen extract at the desk; four refusals; blanks
counted; the live knobs; same inputs, same file; 100,000 loans.

Then the pass that mutation cannot make: a second model was handed the built
pack with one job, break it, and could write only tests. It tried 35 things
and 16 went red. Fifteen were real and are fixed; the sixteenth was a matter
of judgement and its expectation was restated. All sixteen are in
`tests/test_adversarial.py`, each with the story of what it found, and
`../BACKLOG.md` section 6c lists the 19 it tried that held. The pattern is
the canon skill `adversarial`; run it again whenever the suite has grown
confident.

## What it is not

Not a model that scores loans, not a monitor, not a dashboard. It does not
decide anything. It lays out evidence in a fixed order so the same question
asked next year, or about a different flag, gets the identical treatment.

## For any session working here

**Write for the firm, in plain terms.** The firm, 18 September 2026: *"for this
project be more laymen about super technical explanations so i can understand
what it says."* Show the term, then say what it means, every time: an odds
ratio is "flagged loans have about twice the odds of going bad, other things
held fixed", not a symbol. Recommendations come with the consequence of each
choice. This is canon behaviour 22 applied here on the firm's instruction; it
is not optional for this folder.

**Nothing analytical is decided in the code.** Cut points, bands, thresholds
and labels belong to whoever runs it, in the question file. The firm, the same
day: *"why would we define this in the script when the person running the
test can do it?"*
