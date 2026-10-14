# The walkthrough: rehearsal on public data

Every step is done the way the bank would do it: build the workbook from the
command line, open it in Excel, type into Settings, and read the answer off
the workbook. The expected answer for every cell was written down first, in
[`EXPECTED.md`](EXPECTED.md), by [`expected.py`](expected.py), and committed
before the walkthrough was run. The git history shows that order.

Where the expected answers come from:

- **`scale.py`**, the Python reference the workbook's formulas are held to,
  run on the source CSVs. This checks that Excel computes what the reference
  computes, in Excel 16 itself and not in the `formulas` engine the tests use.
- **LOG.md, 7 Oct 2026.** The card lines with the crisis and the pandemic left
  out were recorded when the scale was agreed: 3.171 / 3.464 / 4.050 / 5.981,
  with 25 / 22 / 29 / 55 / 4 quarters kept in each score. Step W5 must
  reproduce them.
- **The files themselves.** The Run tab's fingerprints are checked against
  SHA-256 taken from the files.
- **The Federal Reserve.** One card line is recomputed by hand from the
  Federal Reserve's own series, in the tie-out (`../tie-out/`).

## 1. Build

From `threshold-engine/`, in a terminal:

```
python -m threshold_engine workbook docs/walkthrough/out/rehearsal.xlsx --series "Credit card=tests/data/cards_nco_ttm.csv" --series "Mortgage=tests/data/mortgage_nco_ttm.csv" --series "Home equity=tests/data/home_equity_nco_ttm.csv" --series "Other consumer=tests/data/other_consumer_as_filed_nco_ttm.csv" --name "Net charge-off rate (TTM)" --unit "%" --direction higher_is_worse --frequency quarterly --smoothing 1 --floor-at-zero yes --moderate-halfwidth 0.5 --low-step 1.0 --high-z 2.5 --on-the-line worse --percentiles 50 75 90 95 --horizon 4 --min-history 41
```

Expected: `Wrote docs\walkthrough\out\rehearsal.xlsx: Credit card, Mortgage, Home equity, Other
consumer, 163 quarters`.

## 2. The steps

Each step starts from the workbook as built. Type what the step says, then
read the cells it lists. After each step, undo what you typed (or close
without saving and reopen).

| Step | What you do | What it shows |
|---|---|---|
| W1 | Open the workbook | Nine tabs, four products, 163 quarters, 35 Glossary terms |
| W2 | Read Thresholds | Every product's median, typical yearly move, worst, four lines, latest value, score and rating, and a blank Check |
| W3.1–W3.4 | On Assess, pick each product in B4 | The quarters in each score, kept and in all, and the lines |
| W4 | Leave out the financial crisis on Credit card | The lines and counts move as the reference says |
| W5 | Add the pandemic as the second leave-out | The rehearsal settings: the 7 Oct numbers, and the Run tab records both leave-outs with their reasons |
| W6–W8 | Change each of the three distances in turn | Thresholds moves, and the dial row for that value on Assess says the same |
| W9a, W9b | Half-width 0, on the line "worse" then "better" | The median is a quarter cards had, so it sits on two lines; the counts differ by the rule |
| W10.1–W10.12 | Make each kind of mistake on purpose | The Check column says why, in words, and the score is blank |
| W11 | Read the Run tab | Fingerprints equal the files' SHA-256 (`certutil -hashfile FILE SHA256`) |
| W12 | Switch Mortgage off on Chart | Mortgage disappears from the chart; cards stays |
| W13 | Read Evidence and Backtest | The same numbers as the `evidence` and `backtest` reference |
| W14a, W14b | A second workbook: cards mirrored as a credit score (800 − 40 × rate), lower is worse | The lines fall; score, counts and the chart's floor equal the reference under each on-the-line rule |

A step passes when every cell it lists says what EXPECTED.md says: a number to
within 1e-9 of it, and text exactly.

## 3. How it was run

[`walk.ps1`](walk.ps1) does the steps in Excel 16 on this machine through
Excel's own automation interface. It types each value into its cell as a
person would, lets Excel recalculate, reads each cell's value back from
Excel, and photographs the tabs named in the steps. Nothing is read from
Python. [`compare.py`](compare.py) puts what Excel said beside what was
expected and writes the result: `RESULT.md` and the exhibit PDF.

```
python docs/walkthrough/expected.py
python -m threshold_engine workbook docs/walkthrough/out/rehearsal.xlsx ...   (the command in section 1)
python -m threshold_engine workbook docs/walkthrough/out/score.xlsx --series "Score=docs/walkthrough/out/score.csv" --name "Score" --unit "points" --direction lower_is_worse --frequency quarterly --smoothing 1 --floor-at-zero no --moderate-halfwidth 0.5 --low-step 1.0 --high-z 2.5 --on-the-line worse --percentiles 50 75 90 95 --horizon 4 --min-history 41
powershell -NoProfile -ExecutionPolicy Bypass -File docs/walkthrough/walk.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File docs/walkthrough/walk.ps1 -Workbook docs/walkthrough/out/score.xlsx -StepsFile steps-low.json -ObservedFile observed-low.json
python docs/walkthrough/compare.py
python docs/walkthrough/build_exhibit.py
```

`expected.py` writes `out/score.csv` (the mirrored series) before the second build. The result is
`RESULT.md` and `WALKTHROUGH-2026-10-13.pdf`, which also says what the run found and fixed.
