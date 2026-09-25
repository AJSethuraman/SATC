# VBA findings: where the workbook broke its own rules, and where each one stands

The macros (`M08_Modes`, `M09_Roles`, `M10_ConfigEvents`, `M11_Median`) were
reviewed on 25 Sep 2026 against the rules they state in their own comments:
refuse rather than guess, a blank is not a zero, a missing gate never reads as
a passing gate, and surface a problem instead of quietly working around it.
This file tracks each finding one at a time. **Status** says where it stands in
the Python engine, and **Test** names the test that goes red if the old
behaviour comes back. `python tools/mutation_check.py` puts the VBA bug back
and proves that it does.

## What each finding was, and where it stands

| # | What the VBA did | Status | Test |
|---|---|---|---|
| 1 | `IsNumeric(Empty)` is True, so `CollectValue` added a 0 for every blank borrower and pulled the median down | **Fixed.** A blank is left out and counted | `test_finding_1_*` |
| 2 | The same quirk let an empty cell produce an index of 0.00x, which `ReadingFor` then called "BETTER than benchmark" | **Fixed.** No rate means no index and no reading | `test_finding_2_*` |
| 3 | `GateCount` read a `#REF!` or blank gate cell as 0, which passed the gate | **Fixed.** An unanswered `[CONFIRM: ...]` or a malformed setting refuses the run | `test_finding_3_*` |
| 4 | SUMNUM turned text or error values into 0 in the numerator while the row's weight stayed in the denominator, so the rate came out too low | **Fixed per ruling OC-1.** The row is left out of the top *and* the bottom of that rate and counted on screen. It still counts in every other figure it can be read for | `test_finding_4_*` |
| 5 | The candidate table (rows 234–304), the row hints (209–214) and `Cube Walkthrough!B58` sat at fixed addresses, so an inserted row would drop a READY column without anyone noticing | **Gone.** Every setting is found by its key in the cube file and every column by its name | `test_finding_5_*` |
| 6 | `DomainMeasureColumnSafe` said it trapped error 941 only but trapped every error | **Fixed.** An absent measure is skipped with a warning only when the file marks it `optional: true` (keeps D55); otherwise it refuses. Nothing is swallowed | `test_finding_6_*` |
| 7 | Warnings for a missing key or a missing domain measure went to `Debug.Print`, which nobody sees | **Fixed.** Every warning is printed at the top of the output under WARNINGS | `test_finding_7_*` |
| 8 | Thresholds fell back to 1.25 / 0.8 without saying so, and the layout switched back when B58 was blank | **Fixed per ruling OC-3.** `benchmark:` is a required line, all three values are required, and a misspelled key is refused. Building without comparisons has to be written as `benchmark: none` | `test_finding_8_*` |
| 9 | `GateRow` looped `1 To UsedRange.Rows.Count`, which drops rows when the used range doesn't start at row 1 | **Gone.** There is no sheet scan | — |
| 10 | Error 959 was used for two different errors | **Gone.** Each failure has its own exception type | — |
| — | `System.Collections.ArrayList` needs .NET 3.5 | **Gone** | — |
| — | `Dim mid` hid VBA's `Mid` function | **Gone** | — |
| — | `Worksheet_Change` only fires from the sheet's own code module | **Gone.** The D56 stamp exists because decisions were stored by row. In the cube file every decision is written against a column name, so the problem it guarded against can't happen | — |

## Rulings behind the fixes (25 Sep 2026)

- **OC-1: a value that won't read is counted and shown, not refused.** The firm:
  *"this is a fine fallback - ideally we would have already gone through the
  population to get rid of stuff we do not want."*
- **OC-2: missing-value codes are rules in the cube file.** The firm: *"many rules
  exist, unsure if it is in the macro, around things like numbers under -1000 for
  some items would mean it's actually a value that the bureau is missing."* In the
  file this is `missing: {FICO: {below: -1000}}`. A caught value is counted as
  "missing by rule". It gets its own row when it's in a band or dimension column,
  and is left out when it's in a measure column.
- **OC-3: the thresholds are required.** The firm, on building a new workbook
  rather than porting the old one: *"you can design a workbook and such that goes
  along with this we don't need to be beholden to the original workbook."*
- **OC-4: the point is pockets against the topline.** The firm: *"the idea for
  this specific analysis was inspired by an AI taking GCO RANR And other factors
  and sort of making ratios out of different things and comparing things like
  topline GCOs with pocket GCOs to identify areas with bands that bleed."* So
  every rate cell carries three figures:
  - **vs topline**: the cell's rate divided by the whole book's rate. This equals
    the cell's share of the losses divided by its share of the volume.
  - **excess**: the cell's losses minus what it would have lost at the topline
    rate. Excess adds to zero across a grid, which the tie-out checks.
  - **vs median**: the workbook's option 2 (D61), kept as a second view.
