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

The tool knows no domain. No column name, no list of anything, no outcome
word lives in the code; a test fails if one appears. The question file is
the only place such things live, so a consumer question is a different
file, not different code.

- **Spec:** [`docs/prd-portfolio-analysis-pack.md`](docs/prd-portfolio-analysis-pack.md)
- **Build plan:** issues #364–#372 on the repository, in order
- **Running log:** `../BACKLOG.md` §6c (credit line; not `PLAN.md`)
- **Rulings on the record:** `../canon/CONVICTIONS.md`, *Rulings by project*

**Status:** slices 1 to 5 of 9 built: the tracer bullet; inspect, the
refusals, detected dates, the filter and the outcome forms; steps 1 and 2;
step 4 with the survives/collapses word and `pack suggest`; step 5, step 7,
generic groupings and the consumer example. Step 6, charts, the bundle and
the mutation tool follow in the order the issues give.

## What a built pack contains

| Tab | What it shows |
|---|---|
| `Cover` | The question, the answer in three lines, the loans and events it rests on, and `N of N formula checks agree` |
| `1_Capture` | By origination quarter: loans, how many are younger than the window, blanks in each rule field, how many carry both; then seasoned loans per band for every confounder scheme |
| `2_Prevalence` | By quarter, on seasoned loans: the capture rate (both fields present) and the flag rate (rule fires among those), each with its interval, never merged |
| `3_Gradient` | The outcome rate across buckets of the rule value, each with its interval, its gap from the unflagged base in percentage points and as a multiple, and whether the rates rise at every step |
| `4_Stratified` | For each confounder and band scheme: the flagged and unflagged rates per band, the crude odds ratio beside the pooled one across bands, the share of the effect kept, and one word: survives, collapses, unknown, or no crude effect |
| `5_Decomposition` | For each dimension the question file lists: flagged and unflagged rates per level with intervals, the gap, and the share of all flagged events in the level, most first |
| `7_Control` | The observation that stands regardless: how often the two fields disagree in the seasoned book, the question file's own words on what each field drives, and what it says reacts to the disagreement today |
| `_cube` | The counts every formula reads: loans and events per cell |
| `_config` | Live knobs (confidence level, interval method) and the rebuild knobs for the record |
| `_method` | Notes on what was done, generated from the question file and the counts |
| `_check` | Python's value beside every formula cell and Excel's own verdict on whether they agree |
| `_provenance` | Source file and its hash, row counts, window, dates, generator version |

The step 6 tab arrives with its slice.

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
python tools/render.py demo/pack.xlsx        # PDF + HTML; fails on any error cell
```

The suite builds a 40,000-loan synthetic book with a planted effect and
reads the workbook back through the engine: the gradient must read as
planted, every `_check` row must agree, two builds must be byte-identical,
and the guards must hold (no domain word in the code, no clock read, the
`_xlfn.` prefix on every newer function).

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
