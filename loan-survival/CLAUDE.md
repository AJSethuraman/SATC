# Loan Survival Tool: project brief

## Who this is for
AJ, a CPA in an independent Credit Risk Review (CRR) function at a bank under OCC supervision. CRR challenges the
line of business (LOB); it doesn't run it. AJ builds his own tools and runs them from a right-click menu on his work machine.

**Non-negotiables**
- AJ must be able to **explain every output himself** to managers and examiners. Prefer the simple method that answers the question.
- **Deterministic and auditable.** Same input + same settings = same output. Every run writes a RunLog (file hash, settings verbatim, exclusions, versions).
- **Local only.** No network calls, no data leaves the machine.
- **Minimal dependencies:** pandas, numpy, openpyxl. matplotlib and scipy optional (built-in fallbacks exist). Use **tkinter** (standard library) for the GUI. Installs at work may be blocked, so don't add packages without asking AJ.
- Short, direct communication. Present questions with a recommended option.

## The question it answers
"Did underwriting get better?" For example, AJ's small-business (SB) book has 2021–2025 loans; 2023 looked bad and the LOB says things improved after.
Raw "charge-offs / originations" flatters young loans because they haven't had time to go bad. This tool compares groups
**at the same month on book** (Kaplan-Meier survival curves), so time is handled fairly.

## Files
| File | What |
|---|---|
| `loan_survival.py` | The engine and current CLI. One run: bad-event check, early read, tests, models, economics, then an Excel workbook. |
| `delinquency_outcomes.py` | Older standalone. Its **snapshot mode** (month-end roll-rate matrix) is not merged into the engine yet (see backlog). Its loan mode is already merged. |
| `sample/settings_example.ini` | Settings with all five test types. Format reference for the GUI's save/load. |
| `sample/fake_book.csv` | 6,600 fake loans (2021–2025) with known built-in effects: 2023 is 1.6x worse, FICO is 2x per 50 points lower, income>sales is 1.4x, new_business has no true effect, 15% of bads charge off without hitting 90+. |
| `loan_survival_gui.py` | tkinter front door. Writes the same .ini and calls `run()`; no second engine. |
| `tests/gui_check.py` | Proves the GUI's settings give the CLI's Tests/Models sheets cell for cell. Run under `xvfb-run` on Linux, or plainly on Windows. |
| `tests/validate.py` | **Run after any change to the math.** Checks against a hand-worked example, SciPy (Kaplan-Meier, log-rank), statsmodels (Cox), and plain pandas (economics, bad-event). Mutation-tested: a broken survival formula fails it. |
| `tests/make_fake_*.py` | Generators for the fake data. |

```
python loan_survival.py sample/fake_book.csv --settings sample/settings_example.ini
python loan_survival.py loans.xlsx --write-settings     # starter settings file
python tests/validate.py                                 # must print ALL PASSED
python tests/gui_check.py                                # must print ALL PASSED (window part says SKIP if no tkinter/display)
pythonw loan_survival_gui.py "loans.xlsx"                # the pop-up version
```

## What one run does (and how to explain it)
1. **Bad-event check**: is 90+ days past due a good early stand-in for charge-off? It looks at what happened within N months of first 90+ (charged off / cured / paid off), the lead time, and the share of charge-offs that never hit 90+. With `bad_event = auto`, it uses "earliest of 90+ or charge-off" if at least 60% of 90+ loans charge off and 90+ comes at least 3 months earlier (median); otherwise it uses charge-off. The thresholds are AJ's policy settings, not standards.
2. **Early read**: from fully seasoned vintages, the share of eventual (month-36) bads already seen by month 6/12/18/24. This tells AJ how much a comparison of young cohorts can be trusted. Example: "only 34% of eventual bads show up by month 12."
3. **Tests**, each compared at the same month on book with a log-rank p-value:
   - `group_by = year`: vintages
   - `split_date = 2024-01-01`: before/after a policy change
   - `column = fico` + `cutoffs = 640,660,680`: **backtest a rule** on seasoned loans ("would-have-failed vs passed"). The key output is how much worse the flagged group performed vs how many flagged loans were fine (the cost of the rule).
   - `column = income_gt_sales`: each value of a flag or category
   - `model = fico per -50, income_gt_sales, new_business`: Cox regression. Each factor alone vs together, as a hazard ratio (1.0 = no effect, 2.0 = double the monthly chance of going bad). "Alone high, together near 1.0" means the factor was standing in for the others. The plain-English reading is in the output.
   - Any test can set `orig_from` / `orig_to` (for example, seasoned loans only).
4. **Economics**: if `net_revenue` (AJ's consumer data has revenue net of interest expense **and charge-offs**) and `amount` are mapped, it reports total, per loan, and per $1,000 by group. **Only meaningful on seasoned loans.** In the fake book, 2025 looks the most profitable purely because it's young.

## GUI: BUILT 16 Oct 2026 (`loan_survival_gui.py`; AJ wanted pop-ups, not settings files)
The spec below is kept as the contract it was built to. What is NOT proven yet is in README.md under "Not checked".

**Architecture**
- First refactor `loan_survival.main()` into an importable `run(input_path, settings_text, out_path) -> summary` used by both the CLI and the GUI. Keep the CLI working.
- The GUI only **builds settings text** in the existing .ini format and calls `run()`. This keeps one engine, and the RunLog records exactly what the GUI chose.

**Flow** (wizard or tabs)
1. **Data**: file picker, prefilled when launched from right-click (`pythonw loan_survival_gui.py "%1"`). Show row count and a preview. As-of date defaults to the latest date in the file.
2. **Columns**: one dropdown per role (orig_date, chargeoff_date, first_90_date, payoff_date, dpd_asof, net_revenue, amount, loan_id), populated from the file's headers, auto-matched by common aliases, required roles marked. Show how many values fail to parse as dates right on the screen.
3. **Settings**: bad-event radio buttons (auto / charge-off / earliest), each with a one-line explanation. Checkpoints. Thresholds under a collapsed "Advanced" section.
4. **Tests**: a list with Add / Edit / Duplicate / Remove. The Add dialog picks a type (Vintage, Before/after date, Cutoffs, Flag/category, Multi-factor model). Column dropdowns are filtered by type: numeric for cutoffs, few distinct values for category, multi-select with a "per N, lower/higher" scale for model. Optional origination window, with a **"seasoned loans only"** shortcut that sets orig_to = as-of minus the horizon months.
5. **Run**: show status, translate errors into plain English, then offer Open workbook / Open folder.
6. **Save / Load selections** as .ini so a run can be repeated exactly. Optionally remember the last column mapping per file-header signature in a local JSON file next to the script.

**Acceptance**
- `tests/validate.py` still prints ALL PASSED.
- Rebuilding `sample/settings_example.ini` through the GUI on `sample/fake_book.csv` produces the same Tests and Models sheets as the CLI.

## Ask AJ before assuming
- **OS and Python at work.** Probably Windows, not confirmed. Which packages exist? Is tkinter present (some corporate Python builds lack it)?
- **How his right-click menu is wired** (registry entries? a launcher script?), so the GUI plugs in the same way his other tools do.
- **Real column names** in the SB extract. He has charge-off dates, and likely first-90+ dates and multiple month-end snapshots. The SB book has no net revenue yet; consumer does.

## Backlog (after the GUI)
1. Merge snapshot mode (roll-rate matrix from month-end files) from `delinquency_outcomes.py` into the bad-event section.
2. Warn automatically when economics compare groups that aren't seasoned (median months observed below the horizon).
3. Dollar-weighted bad rates (by amount) next to count-based ones.
4. Cutoff chart: bad rate below/above vs cutoff, plus % flagged.
5. Before outputs go into formal CRR reports, AJ should check with model risk management whether the Cox piece counts as a "model" (SR 11-7 / OCC 2011-12).

## Gotchas already hit
- pandas 3 stores text as a string type, not `object`. Use `pd.api.types.is_numeric_dtype`, not `dtype == object`.
- `to_excel` needs `sheet_name=` as a keyword in newer pandas.
- Months on book = whole calendar months (opened 3/15, observed to 4/14 = 0). Events in a month are processed before censoring.
- Bad dates after as-of are treated as not yet happened. Loans are censored at payoff or as-of.
