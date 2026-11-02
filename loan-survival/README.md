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

The window has five tabs: Data, Columns, Settings, Tests, Run. It writes the same
settings text the command line reads and calls `loan_survival.run()`, so the RunLog
in the workbook records exactly what was chosen. File → Save selections writes that
text to an `.ini` so a run can be repeated exactly.

Right-click menu: pass the file as the first argument, for example
`pythonw C:\tools\loan_survival\loan_survival_gui.py "%1"`. How the menu is wired
on the work machine is not known yet.

Needs pandas, numpy, openpyxl and tkinter. scipy and matplotlib are optional.

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
