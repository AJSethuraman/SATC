# Adversarial findings: the economic conditions tool (PR #452), 17 October 2026

A fresh read of `threshold-engine/src/threshold_engine/macro/` against its 96 passing tests, hunting
cases the tests never exercise. Nothing under review was changed. The only deliverable is
`test_findings.py` beside this file: every test in it asserts behaviour the tool should have and fails
against the code as it stands. Run from `threshold-engine/`:

    PYTHONPATH=src python -m pytest -q docs/macro/findings/test_findings.py

Result at the time of writing: **11 failed** (9 findings; two are parametrised over two cases). The
existing suite still reads **96 passed**. There is no Excel here; what Excel does with a file is
listed under *not checked*, not claimed.

## The denominator

| | Count |
|---|---|
| Hypotheses formed from reading the code and the docs | 46 |
| Tried by running code against the tool (synthetic data, no network) | 25 |
| Produced a red test | **9** (11 test cases) |
| Held when run | 16 |
| Judged by reading only, not run | 21 |

Two of the nine were also checked the other way: with a minimal fix patched in at run time (the code
on disk untouched), the test for the unreadable file and the test for the zero-height axis go green.
The other seven fail on an assertion whose cause is plain in the failure line (a `DID NOT RAISE`, an
`IndexError` in the tool, a string shown in full).

## Findings (each is a failing test)

Ranked by what it would cost the teams that read the workbook.

1. **One unreadable file stops every rating.** A download that is not what the publisher usually
   serves (FHFA's zip replaced by an HTML error page) is recorded by the pull as "could not read", as
   TOOL.md promises. `rate_all` then raises `BadZipFile` instead of listing the three FHFA readings
   under Not rated: `Pull._get` catches `SystemExit`, `ValueError` and `OSError`, and the zip reader
   raises none of them. No rating and no workbook that month until someone deletes the file.
   *Test:* `test_a_file_the_pull_could_not_read_leaves_its_readings_not_rated_rather_than_crashing_the_rating`.
2. **The Sources tab's fingerprint is the manifest's, not the file's.** The SHA-256 is copied from
   the manifest written at pull time; nothing compares it with the file the rating reads. Append a
   row to a CSV in the pull folder (opening it in a spreadsheet and saving does as much): the rating
   reads the changed file, its rating moves, and the workbook publishes the old fingerprint as the
   file it read. *Test:* `test_the_sources_tab_fingerprints_the_file_the_rating_read`.
3. **A series with no rows crashes the workbook when the Sahm reading is shown.** A FRED file with a
   header and no observations is rated "not rated", correctly. With `show_sahm` on, `build` raises
   `IndexError` in `years_axis`, drawing the Sahm chart from an empty list of dates. Without the Sahm
   reading, the same file builds. *Test:*
   `test_a_series_with_no_rows_in_the_pull_does_not_crash_the_workbook_when_the_sahm_reading_is_shown`.
4. **The fourth horizon branch.** Codex found three places that named a change with the wrong side's
   horizon. Settings count over 6 months and rate CPI's change; the what-if counts over 12 and does
   not rate it. The Ratings and States "What if" cell reads *"Change (what if: over 12 months): rated
   as you have it only"*: the only rating in the cell is the 6-month one, and the what-if, whose
   horizon it names, rated nothing. *Test:*
   `test_a_change_rated_as_you_have_it_only_is_not_labelled_with_the_what_ifs_horizon`.
5. **A direction for a reading the series does not carry passes in silence.** An unknown top-level
   key is refused by name; a direction for a series the research states is refused by name. A
   direction for CPI's *level* (never rated) or for a misspelt reading (`chnage`) is accepted and
   ignored. The firm can believe it has set how a reading is read when nothing reads it. *Test:*
   `test_a_direction_for_a_reading_the_series_does_not_carry_is_refused_by_name` (two cases).
6. **A refused pull leaves an empty dated folder.** `pull` makes the day's folder before it checks the
   keys. After a typo, the day's real pull lands in `2026-10-17-2`, and `rate --vintage 2026-10-17` is
   refused although the data is beside it. *Test:* `test_a_refused_pull_leaves_the_cache_as_it_was`.
7. **The not-rated reason is not a sentence, and blames the pull.** A reader meets *"no changes
   readings in the pull"* and *"no values readings in the pull"* in the printout, the Not rated tab
   and the What if tab. For a quarterly series under a 4-month horizon the pull holds every quarter;
   no change can land on a quarter, and the reason says the pull. *Test:*
   `test_the_reason_a_reading_cannot_be_rated_reads_as_english_and_does_not_blame_the_pull` (two cases).
8. **A history of one value gets a chart axis of no height.** `nice_axis(4.0, 4.0)` returns bottom
   and top both 4.0 (also for 0.0 and 100.0: any constant on its step), written to the chart as
   `<c:min>` equal to `<c:max>`. *Test:* `test_a_history_of_one_value_gets_a_chart_axis_with_a_span`.
9. **`pull mortgage_spread` answers "not in the catalog" and points at `list`, which lists it.** A
   derived reading is in the catalog; the pull should fetch its inputs or say which two series to
   pull. *Test:* `test_pulling_a_derived_reading_is_not_called_not_in_the_catalog`.

## Checked and found clean (run)

- **Weekly change:** nearest reading within 3 days taken, one 5 days off ignored; an exact tie (3 days
  either side) takes the earlier reading, as the docstring says.
- **History window** `{"years": 10}` on a monthly series holds exactly 120 readings ending at the
  latest; a reading exactly ten years before the latest is excluded, so the window is ten years, not
  ten years and a month.
- **A history of one reading, or of equal readings:** rated 5 at 100%, every rating line equal to that
  value, the counts sum to the window. This is the documented rule (a record is 100%), not a defect.
- **Percent change** from an earlier reading of 0 or below: no change, nothing filled in. A change to a
  negative reading is computed.
- **A quarterly series under a 6-month horizon** has changes (38 of 40).
- **Sahm with two consecutive missing months:** a gap in the reading, nothing filled in.
- **A series whose every value is blank**, with the Sahm reading shown: not rated, workbook builds.
- **A series with no rows**, Sahm not shown: not rated, workbook builds (the crash is finding 3 only).
- **Workbook structure**, on a what-if workbook from the fixture and on the committed example
  (`examples/economic-conditions-what-if-2026-10-17.xlsx`): no overlapping merged ranges on any sheet;
  every hyperlink names a sheet that exists; every print area names its own sheet; no duplicate series
  `idx` or `order` inside any chart part; every axis crosses one the chart has (the existing test).
- **"Lower is worse" percentile** is the share of the history the reading is at or below in the
  direction of stress (count of readings ≥ x), so the lowest reading is 100%. Checked by hand against
  the existing test's four cases; the docstring's wording is easy to misread, the code is right.
- **The example printout** is consistent with the code's window rule: 360 readings since Oct 1996 for a
  series without the October 2025 gap, 359 with it, 359 since Sep 1996 for the states (which lag a
  month).

## Judged by reading only (not run)

A percentile that lands exactly on a cut-off is exact in floating point (100·k/n divides exactly when
the true value is an integer). The settings refuse `true` where a number belongs, a float where a
whole number belongs, a `history` object with extra keys. `months_back` clamps to short months. Daily
changes compare the same weekday. The mortgage spread takes a yield up to six days old. The what-if's
5×5 matrix and totals are built from the same loop as the rows. Hidden helper columns (N–Q history,
R–S Sahm, T–AG bands, AH–AO what-if lines) do not collide. Sheet names are unique and under 31
characters, including the fixed tabs.

## Not checked

- **Excel itself.** There is no Excel here. Three things LibreOffice forgives that Excel may not, none
  of which can be made a failing test without it: (a) the history, latest-point and dashed-line series
  carry no category reference, so on the shared date axis Excel takes their x positions from the area
  series' categories; (b) four chart groups (one area, three line) share one axis pair; (c) finding 8's
  `min == max` scaling. The firm opening the rebuilt example is still the remaining check, as LOG.md
  says.
- **The real publishers' files.** `read_bls` and `read_fed_ebp` are checked against the fakes the suite
  uses; a change in BLS's markup or the Fed's date format would raise through `rate_reading`
  (`fromisoformat`), which nothing catches. Not tried, since it needs the network.

## Observations (not findings: design, wording, robustness)

- **The bands are drawn over every year; the dashed lines only over the what-if's window.** With
  `history: {"years": 30}` as the firm's own setting, the five bands behind a chart are placed by the
  last 30 years but shaded back to the first reading, while a what-if's dashed lines stop at its
  window's start. The two readings of "where a rating starts" are drawn by different rules on one
  chart. Which rule is right is the firm's call.
- **The history column holds a percent change as 41.49 under a header with no unit**, while the panel
  above shows +41.49%. Consistent within each surface; a reader comparing them has to know.
- **A wrongly shaped answer reads as "not answered."** `"cutoffs": [50, 75, 90, 95]` written without the
  `"answer"` wrapper is refused as "cutoffs: not answered". The refusal is right; the words say the
  firm did not answer when it did, in the wrong place.
- **The glossary names only the baseline's horizon.** With a what-if over 12 months against settings
  over 6, "Change over 12 months" has no glossary entry.
- **The States tab says "not in this pull" for a state whose file is in the pull but holds no values.**
  Unlikely with LAUS data; the same words serve two different facts.
- **`compare.settings_rows` reports `change_for` as differing** when one file says `"all"` and the other
  lists every rated key. True of the text, not of the effect.
