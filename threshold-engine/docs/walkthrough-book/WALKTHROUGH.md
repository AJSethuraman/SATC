# The book walkthrough: one command, then Excel

What the firm asked for, 14 Oct 2026: *"i want you to make it work so i can
generate this workbook at work with the script, it should be debugged and
walked through and tied out."*

This is the walk: the workbook built the way it is built at work, then used in
Excel 16 the way a person uses it (clicking the buttons, typing in the yellow
row, saving, closing and opening it again), and every answer read back from
Excel and set beside an answer written down beforehand from the source files.

## 1. Build

From `threshold-engine/`:

```
python -m threshold_engine peers pull --cache books/ind_cache --first 2006Q1 --last 2026Q2 --products "Credit card" Mortgage "Home equity" "Other consumer" Auto --delinquency yes --mergers 2005-01-01
python -m threshold_engine book books/consumer-public.json consumer-credit.xlsx
```

The walkthrough ran the second command on a copy of the book whose only
change is where the cache is (`prepare.py`): the cache pulled on 14 Oct 2026
was used rather than pulled again. Expected: `Wrote consumer-credit.xlsx: 105
series, 82 quarters; open it on Summary, decide on Decide`. It took 7 min 49 s
on the last run (12 min 42 s on the first), almost all of it the peers build
reading the cache.

## 2. The steps

The steps are cumulative, as a session is: what is typed in one step is still
there in the next.

| Step | What you do | What it shows |
|---|---|---|
| B1 | Open the workbook | It opens on Summary; the tabs in order (Assess, Chart and Peers workings hidden); three slicers, one button each; Decide shows the first series; nothing decided; no links, no errors |
| B2 | Read Summary | All 105 series' latest value and rating equal the reference |
| B3 | On Decide, click Credit card, Nonaccrual, KeyBank | One row; the headline, the lines in words, the Check, and the same measure from the industry and peers |
| B4 | Type 3.5 under How rare High is (z) | Only High's line moves; Thresholds and Summary follow |
| B5 | Leave out 2012Q3 to 2013Q4, the period Decide suggests, with a reason | The lines move as the reference says; Assess lists the period, whole |
| B6, B6b | Clear the reason; type it back | Refused, in words, on Decide; then the lines as in B5 |
| B7 | Accept these lines, with a note | Decided: 1 of 105 |
| B8 | Click Auto, Net charge-offs, KeyBank | Life to date: 15 quarters, its lines and its Check |
| B9 | Click Mortgage, Net charge-offs, Industry | Refused, with the number that would fix it |
| B10 | Save, close, open again | Every decision and setting still there, and the lines with them |

A step passes when every cell it reads says what `steps.json` says: a number
within 1e-9, text exactly.

## 3. How it was run

```
python docs/walkthrough-book/prepare.py PATH-TO-CACHE
python -m threshold_engine book docs/walkthrough-book/out/book.json docs/walkthrough-book/out/consumer-credit.xlsx
python docs/walkthrough-book/expected.py docs/walkthrough-book/out/book.json
copy docs\walkthrough-book\out\consumer-credit.xlsx docs\walkthrough-book\out\walk.xlsx
powershell -NoProfile -ExecutionPolicy Bypass -File docs\walkthrough-book\walk.ps1
python docs/walkthrough-book/compare.py
```

`expected.py` writes the answers from the series CSVs and `scale.py`, never
from the workbook. `walk.ps1` does each step in Excel through Excel's own
automation and reads each answer back. `compare.py` writes `RESULT.md`.

And, separately, that the file opens without Excel repairing it:

```
powershell -NoProfile -ExecutionPolicy Bypass -File tools\check_slicers_in_excel.ps1 -Path docs\walkthrough-book\out\consumer-credit.xlsx -Sheet Decide -Table Decisions -Shapes 4 -Expect "Slicer_Product=Credit card|Slicer_Measure=Net charge-offs|Slicer_Source=Industry (every bank)" -SwitchCache Slicer_Source -SwitchTo KeyBank
```

"No errors" in B1 means none a reader can see: on the visible tabs, outside
hidden rows and columns. The rest are counted by kind and are all #N/A, the
gap a chart leaves where a quarter has no value (on the run of 15 Oct 2026:
Assess 169, Chart 8,470, Decide 249, Peers workings 1,556).

## 4. What it does not prove

- The peer tabs are counted for errors and links (B1) but their numbers are
  not checked against a reference here; `tests/test_peers*.py` hold them.
- One series is tied to the filing (`../tie-out/keybank-card-nonaccrual-2026-10-14/`);
  the other 104 rest on the same code and the reference, not on a filing each.
- Thresholds' latest value is written by the build, not a live formula on
  Data: pasting a corrected quarter into Data moves the lines but not the
  latest value (found by the tie-out).
