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

**Status (25 Sep 2026):** the engine, the per-pocket test, `cube init` and the
Control tab are built. The workbook's other tabs, drill-down and `cube prove`
are designed, not built. Nothing here has met a real extract. Log:
`../BACKLOG.md` §6d.

## What an extract must carry

A loan or application number (`key:`), the booked amount (`booked:`), a yes/no
outcome (`outcome:`), GCO dollars (`gco:`) and RANR dollars (`ranr:`). The run
refuses without any of them. From those it builds four core rates on every
run:
- the outcome as a share of loans (straight)
- the outcome as a share of booked dollars (weighted)
- GCO per booked dollar
- RANR per booked dollar

## Using it

Python 3.10 or later with `openpyxl` and `PyYAML`.

```
pip install -e .
cube control --out control.xlsx                 # the Control tab: make your calls in Excel
cube init extract.csv -o cube.yaml --control control.xlsx
cube validate cube.yaml --data extract.csv
cube run cube.yaml --data extract.csv
```

**What `cube init` does:**
- It **suggests what every column means**: key, booked, outcome, GCO, RANR,
  FICO, score, DTI, LTV, dates, servicing data and so on. Each suggestion comes
  with its reason, and the file starts with `columns_confirmed: no`. Change the
  `means:` of any that is wrong, then set it to `yes`. Nothing runs on a
  suggestion you haven't confirmed.
- **What you confirm is remembered**, and suggested first next time.
  `cube memory` lists everything learned; `cube memory --out learned.xlsx`
  lets you prune it with a Keep / Forget dropdown.
- It raises odd values (a -9999 code, negatives in a mostly positive column)
  as questions. The run carries on using the values as recorded, and says so.

**Your calls.** What is material, how many loans are enough, how much worse
counts as worse, and how sure is sure are never filled in for you. They come
from the Control tab, or they are `[CONFIRM: ...]` in the file.

**What each pocket carries:**
- its rate
- share of losses over share of volume (the bleed measure)
- excess dollars over the topline rate (adds to zero across a grid)
- a multiple and a significance test against the rest of the book, the rest of
  its band, and the rest of its dimension level
- the smallest gap its size could show

Every run also prints how many loans a gap of your size needs in this book,
and what each materiality level would keep. That is evidence for your
settings; it is never a setting.

A synthetic book to try it on: `cube synth --out demo`. Loans with a score
under 620 that came through the broker channel charge off at about six times
the book's rate.

## Checking it

```
pytest -q                          # 95 tests: one per finding, the arithmetic by hand, the Control tab, init, memory
python tools/mutation_check.py     # puts 13 bugs back (the VBA's and today's rules); every one must be caught
```

**Speed** (this container, 25 Sep 2026, pure Python):

- 1,000,000 loans through one grid and five measures: 6.7 s to read the CSV
  plus 19.6 s for the cube.
- At 200,000 loans: 3.5 s for 1 grid, 5.3 s for 4, 8.2 s for 9, so each extra
  grid adds about 0.6 s.
- By extrapolation, not measured: a million loans through 25 grids would take
  about a minute and a half. numpy would cut that to seconds, if the machine at
  the bank has it.
