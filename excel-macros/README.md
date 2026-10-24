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
| `HygieneSaveCopy` | Final Population alone, values only, as a new workbook beside this one (named to the second, so two in a minute do not collide). Refuses unless the status reads *Current*, or when the workbook has never been saved. |

**Refuses rather than guesses:** Build does not run while any column has no decision, while two kept columns would
share a name, when a kept column is no longer on the source sheet, or when a source column has no row on Column
Audit; it lists every one. From its first write until it stamps itself, the status reads *Not built*, so a Build that
stops part-way is never taken for a finished one. The source sheet is never
written to. Every run, and every message shown, is logged on the Hygiene sheet.

## How it is tested, and what that does not prove

`tests/` runs the macros in **LibreOffice**, headless, in its Excel-compatible mode, on a synthetic population with
every problem planted, and compares every count with Python working from the same rows (`pytest -q` in `tests/`;
needs LibreOffice and its Python bridge, `python3-uno`). `tools/mutation_check.py` puts a bug in each guard in turn
and the tests must go red.

### What the tests do not prove

LibreOffice is not Excel. The tests prove the macros' logic; they cannot prove Excel runs them identically.

- **Excel re-reads text a macro writes** ("00123" becomes 123, "2024-01" a date); LibreOffice does not. The macros
  write such text into cells formatted as Text, and the tests check the format, not the conversion. Found by an
  independent review, not by the tests.
- **A mixed column's text held out of the bulk write.** In a column holding numbers and text, text Excel would re-read
  ("#N/A", "=SUM(") is left out of the one write and written alone into a Text cell. The tests check the result's
  format; that the bulk write would otherwise have failed or produced an error value is Excel's behaviour, not
  LibreOffice's, so it is checked only by review.
- **HygieneSaveCopy:** the tests show the copy is made beside the workbook under the right name, and nothing more.
  LibreOffice ignores Excel's FileFormat code and loses the active workbook after the copy closes, so the copy's
  contents and its "Saved copy" log line are first checked on the firm's machine.
- **The error path** is proved with a planted error (`HygieneSelfTest`): the error is logged. LibreOffice let a macro
  past both natural triggers tried (a protected sheet, a chart sheet holding Build's sheet name). That the screen and
  status bar come back afterwards is **not** proved: LibreOffice resets both between macro calls by itself.
- **Compiling:** a module LibreOffice cannot compile runs nothing and reports nothing. Found and worked around: a
  named constant as an `Optional` default; `book`, `path` or `base` as a variable name; a function declared
  `As String()`. Excel compiles all three; the reverse (Excel refusing what LibreOffice takes) is checked only by
  review, for example a Variant passed to a `ByRef ... As String` parameter.

Speed: Profile took 40 s on 17,000 rows × 40 columns in LibreOffice (5 Oct 2026). Not yet timed in Excel;
at that rate a 580-column population is about ten minutes in LibreOffice, and the status bar shows the column count.
