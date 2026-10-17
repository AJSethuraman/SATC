# Loan Survival

"Did underwriting get better?" — compares groups of loans **at the same month on
book** (Kaplan-Meier), so young loans are not flattered by not having had time to
go bad. Built for credit review work at a bank; the brief for whoever builds on it
is `CLAUDE.md` in this folder.

Not part of the practice's own software, and it holds no client data. The fake book
in `sample/` is generated.

## Run it

```
python loan_survival.py sample/fake_book.csv --settings sample/settings_example.ini   # command line
pythonw loan_survival_gui.py "C:\path\loans.xlsx"                                      # pop-ups; path optional
```

The window has five steps: Data, Columns, Settings, Comparisons, Run. It writes the same
settings text the command line reads and calls `loan_survival.run()`, so the RunLog
in the workbook records exactly what was chosen. File → Save selections writes that
text to an `.ini` so a run can be repeated exactly.

Right-click menu: pass the file as the first argument, for example
`pythonw C:\tools\loan_survival\loan_survival_gui.py "%1"`. How the menu is wired
on the work machine is not known yet.

Needs pandas, numpy, openpyxl and tkinter. scipy and matplotlib are optional.

## Rules the window follows

The window states none of these. It shows labels, counts and refusals only.

**Data.** One row per loan, CSV or Excel. The as-of date starts as the latest date found in the date columns; anything dated
after it is treated as not yet happened.

**Dates.** Excel day numbers (like 45292) are read as the date they are; any other number in a date column is left out as
unreadable, with the number shown on the Excluded sheet. A column of slash dates is month first unless it holds one that can
only be day first (25/02/2024); then all of it is day first. A column with both is refused. A latest date in the file that is
after today stops the run until the date is fixed or the as-of date is set by hand.

**Rows left out.** Listed on the Excluded sheet with the reason: unreadable date, duplicate loan id, no origination date, a
date before origination, a charge-off after payoff. Rows sharing a loan id that disagree on a mapped column stop the run.

**Settings.** A key or section the tool does not know, a date or cutoff that cannot be read, a repeated section or split date:
the run stops and names it. Column names are read with spaces trimmed. An unreadable-as-UTF-8 CSV is read as Windows-1252, and the
RunLog says so.

**Cutoffs.** The p-value compares the groups that have a value; the "missing" group is shown and not tested. Cutoffs on a column
with no numbers are refused.

**Revenue.** `$1,234.00` and `(50.00)` are read. `loans_with_revenue` is what `net_revenue_per_loan` divides by;
`revenue_unreadable` counts cells with something in them that is not a number.

**Columns.** Required: origination date and charge-off date (blank when the loan has not charged off). Optional:

| Column | Used for |
|---|---|
| First 90+ days past due date | The bad-event check, and the First 90+ or charge-off definition |
| Payoff date | A loan stops being followed at payoff |
| Days past due at as-of | Splits recovered loans from loans still late |
| Net revenue, Loan amount | Net revenue per $1,000 lent, by group |
| Loan ID | Duplicate loans |

A date that cannot be read excludes the loan, and the loan is listed on the Excluded sheet. Each pick is saved to
`loan_survival_gui_memory.json` beside the program; the names picked are tried first on the next file. A column cannot fill two roles.

**Bad event.** *Charge-off*: a loan is bad when it charges off. *First 90+ or charge-off*: bad at whichever comes first;
needs the first 90+ date. *Auto*: First 90+ or charge-off when at least the minimum share of 90+ loans charge off and the
median lead is at least the minimum number of months, otherwise Charge-off. Both minimums are under Advanced; the run says
which one it used.

**Comparisons.** Vintage groups by origination year. Before / after splits at one or more dates. Cutoffs backtests a rule on a
numeric column (below each cutoff against at or above). Flag compares loans where one numeric column is `>`, `>=`, `<`, `<=`,
`==` or `!=` another numeric column or a number, Yes against No; a loan blank on either side is blank. Each value compares the
values of a column with 15 distinct values or fewer. Cox model reports each factor alone and together as a hazard ratio, and takes the same flags as a factor; *per N lower / higher* sets the unit of a number.
A flag is written in the settings file as the column name, for example `column = amount >= 50000` or
`model = fico >= 700, new_business`; a column in the file with exactly that name is used instead. With no comparison added,
the run compares vintages.

**Only loans where** limits a comparison to loans meeting one or more conditions, for example a FICO band. In the settings file:
`where = fico >= 660; fico <= 699`. A condition is a column against a column or a number, as in a flag. A loan blank in a
conditioned column is left out. The Tests sheet shows the conditions in its `orig_window` column. The origination window and the
conditions both apply.

**Seasoned** restricts a comparison to loans opened at least the early-read horizon (months, under Advanced) before the as-of
date. It is the default for cutoffs, each value and the Cox model.

**Text size.** View menu, Ctrl + and Ctrl -. The size is remembered.

## Check it

```
python tests/validate.py                  # math vs hand-worked example, SciPy, statsmodels, plain pandas
xvfb-run python tests/gui_check.py        # Linux; on Windows just: python tests/gui_check.py
```

`validate.py` needs scipy and statsmodels installed as references; the tool does not.
Both print `ALL PASSED`. `gui_check.py` prints `SKIP` for the window part when there is
no tkinter or display, and a SKIP is not a pass.

## Not checked

- Windows, and the Python build at the bank. Everything here ran on Linux, Python 3.12
  for the window and 3.13 for the engine. Whether that Python has tkinter is unknown.
- Real SB data. Only the generated fake book has been run, so column-name guesses in
  `auto_match` are guesses until the real extract's headers are seen.
- Excel opening the workbook. It was read back with pandas, not opened in Excel.
- Whether the Cox piece counts as a "model" under SR 11-7 / OCC 2011-12. Ask model risk
  management before outputs go into a formal report.
