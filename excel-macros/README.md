# Excel macros

Macros the firm keeps in Excel's Personal Macro Workbook (PERSONAL.XLSB), so they work in any workbook on their
machine and never live inside a file that gets sent. Setup, once per computer: `docs/SETUP.md`.

## Hygiene (`macros/Hygiene.bas`)

The firm, 5 Oct 2026: *"It'd be nice to be able to easily take a population and figure out basically how messed up it
is or how we can fix it."* It replaces a workbook whose cleanup ran on live formulas and a separate export snapshot
that drifted from them.

| Macro | Writes |
|---|---|
| `HygieneProfile` | **Column Audit**: per column, the type found, blanks, distinct values (case counts), the three most common, numbers stored as text, dates stored as text, extra spaces, odd characters (control characters, no-break and zero-width spaces), a value repeated in every row, and a column that repeats another row for row. Then four columns for the analyst: Keep? (Keep/Drop), New name, Flag: 1 when (values separated by `;`), Notes. Rerunning keeps those, matched on the column's name. |
| `HygieneBuild` | **Final Population** as plain values: kept columns, renamed, with flags made (1 when the value is in the list, 0 for any other value, blank stays blank). **Row Audit**: every row with a blank in a kept column, and every key value that appears more than once (the key is named on the Hygiene sheet). The **Hygiene** sheet's stamp: when, from which sheet, rows, columns kept and dropped, flags, rows with a blank, duplicate keys, and a status cell that reads *Out of date* once a decision changes after the Build. |
| `HygieneSaveCopy` | Final Population alone, values only, as a new workbook beside this one. Refuses when the status is out of date. |

**Refuses rather than guesses:** Build does not run while any column has no decision, while two kept columns would
share a name, or when a kept column is no longer on the source sheet; it lists every one. The source sheet is never
written to. Every run, and every message shown, is logged on the Hygiene sheet.

## How it is tested, and what that does not prove

`tests/` runs the macros in **LibreOffice**, headless, in its Excel-compatible mode, on a synthetic population with
every problem planted, and compares every count with Python working from the same rows (`pytest -q` in `tests/`;
needs LibreOffice and its Python bridge, `python3-uno`). `tools/mutation_check.py` puts a bug in each guard in turn
and the tests must go red.

LibreOffice is not Excel. The tests prove the macros' logic; they cannot prove Excel runs them identically. Two
differences already found and worked around: a named constant as an `Optional` default does not compile in
LibreOffice, and `book`, `path` or `base` as a variable name stops the whole module compiling there. **HygieneSaveCopy
is not exercised by the tests** (it opens a new workbook and saves it); its first run is the firm's.

Speed: Profile took 40 s on 17,000 rows × 40 columns in LibreOffice (5 Oct 2026). Not yet timed in Excel;
at that rate a 580-column population is about ten minutes in LibreOffice, and the status bar shows the column count.
