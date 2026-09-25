# Origination Cube

**Where does the book bleed?** The tool takes a loan extract and a short cube
file. It cuts the loans by bands (a score band, say) against dimensions (the
channel, say), and compares every pocket's rate with the whole book's
(the topline). The pockets that lose more than their share come out at the
top of a list, in dollars.

This replaces a set of Excel macros that did the same job slowly and kept
breaking their own rules. `docs/vba-findings.md` lists each of those breaks and
the test that stops it coming back. The macros were only a source of ideas, so
this is not a port and the workbook will be designed from scratch.

**Where it's going:** `docs/design.md` sets out the three stages (find, drill,
prove), the Control tab, and the firm's rulings of 25 Sep. The Control tab is
built (`cube control --out control.xlsx`); the rest of the workbook is not.

**Status (25 Sep 2026): slice 1, the engine.** It reads the extract, applies
the cube file, builds every grid, checks each grid against the book's totals,
and prints the result. The workbook is slice 2 and isn't built yet. Nothing
here has met a real extract. Log: `../BACKLOG.md` §6d.

## What one rate cell carries

| Figure | What it is |
|---|---|
| rate | the measure's top divided by its bottom, e.g. `SUM(GCO_AMT) / SUM(ORIG_BAL)` |
| vs topline | the cell's rate divided by the book's rate. The same number is its share of the losses divided by its share of the volume. 2.0x means the pocket loses at twice the book's rate |
| excess | the cell's losses minus what it would have lost at the book's rate. This ranks the pockets, and it adds to zero across a grid |
| vs median | the cell's rate divided by the median rate of the grid's cells, leaving out cells with too few loans |
| reading | worse than benchmark / in line / better than benchmark / too few loans to read, using the thresholds in the file |

Each grid also has an `All` row and an `All` column, so the result for a whole
band or a whole channel sits beside its pockets.

## The cube file

```yaml
name: my_cube
schema_version: 1
key: LOAN_NBR                    # optional; without it the cube runs, with a warning
missing:                         # values that mean "missing", per column
  FICO: {below: -1000}           # the bureau writes -9999 for no score
  CHANNEL: {values: ["UNK"]}
bands:
  - {name: fico, field: FICO, edges: [620, 680, 740]}
dimensions:
  - {name: channel, field: CHANNEL}
measures:
  - {name: bad_rate,  mode: flagwt, flag: BAD_FLAG, per: ORIG_BAL}
  - {name: gco_rate,  mode: sumnum, value: GCO_AMT, per: ORIG_BAL}
  - {name: ranr_rate, mode: sumnum, value: RANR_AMT, per: ORIG_BAL, optional: true}
  - {name: loans,     mode: count}
  - {name: fico_median, mode: median, value: FICO}
benchmark:
  min_units: 30                  # cells with fewer loans are not read
  worse_at: 1.25
  better_at: 0.8
```

- **Every rate names its own bottom with `per:`**, so a ratio of any two columns
  is one line in the file: GCO per balance, RANR per balance, or GCO per RANR.
- **Every band is crossed with every dimension.**
- **Nothing has a default.** A missing line is refused and the error message
  prints the line to add. A misspelled key is refused, not ignored.

## What happens to a value that won't read

It is **never read as zero**. Any of these:

- a blank
- text in a number column
- a flag that isn't 0 or 1
- a value caught by a `missing:` rule

is left out of the top *and* the bottom of the rate it affects, and counted
under "Left out" in the output. The same row still counts in every other
figure it can be read for. In a band or dimension column, the row gets its own
visible row in the grid, such as `(blank)` or `(missing by rule)`, so no loan
disappears from the tie-out.

## Using it

Python 3.10 or later with `openpyxl` and `PyYAML`.

```
pip install -e .
cube synth --out demo                                   # a book with a known answer
cube validate demo/cube.yaml --data demo/loans.csv
cube run demo/cube.yaml --data demo/loans.csv
cube inspect extract.csv                                # every column: kind, blanks, samples
```

In the synthetic book, loans with a score under 620 that came through the
broker channel charge off at about six times the book's rate. `cube run` puts
that pocket first on the bleed list for both the bad-loan rate and the GCO
rate. The RANR grid, which has no planted effect, reads in line everywhere it
has loans.

## Checking it

```
pytest -q                          # 47 tests: one per finding, the arithmetic by hand, the Control tab
python tools/mutation_check.py     # puts each VBA bug back; every one must be caught
```

**Speed** (this container, 25 Sep 2026, pure Python):

- 1,000,000 loans through one grid and five measures: 6.7 s to read the CSV
  plus 19.6 s for the cube.
- At 200,000 loans: 3.5 s for 1 grid, 5.3 s for 4, 8.2 s for 9, so each extra
  grid adds about 0.6 s.
- By extrapolation, not measured: a million loans through 25 grids would take
  about a minute and a half. numpy would cut that to seconds, if the machine at
  the bank has it.
