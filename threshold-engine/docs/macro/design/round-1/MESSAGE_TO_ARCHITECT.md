# Message to the architect: Macrobook, design round 1

## What this round decides

1. **The Dashboard fits one screen.** Four boxes in one row, both readings in the Overview's columns, the two "together" charts side by side, each series' level and change below. Readings past each series' 1st and 99th percentile are cut by formula (the firm's 1% setting), so Excel's auto axis fits the rest and 2020 no longer flattens the movement chart; a triangle marks each cut reading.
2. **Method notes go to the foot of every tab, collapsed.** Words unchanged. The first series on the Overview moves from row 21 to row 9; the series tab's charts move from row 15 to row 10.
3. **The series tab is two tiles of figures, two charts side by side, then What it is.** The tool's two sentences move from the tiles to the end of What it is, unchanged. Change-only series get one full-width change chart.
4. **One grammar across tabs.** One way each for a reading, a direction, a normal range, a note, a link, a control and a rule (README, "The system"). Two grids: table tabs share the Overview's columns; chart tabs share 24 columns of 72 px.
5. **Tab order follows the Overview**, coloured by group. States moves from 4th to after the core series. No index tab: the Overview and Usable with care are the index.
6. **Direction stays as it is** (▲/▼, bold on MIST, the same both ways); only its font changes, to Calibri 11.
7. **Seven tokens added**, none changed: MACRO_LINK, MACRO_RULE, PICK, DEBT_TYPES, NORMAL_BAND, WHATIF_LINE, OFF_AXIS, plus tab-colour roles.

## Confirm before building

- **The Dashboard's cut uses each series' whole-history percentiles**, written as values on Dashboard data, not percentiles of the window picked (that needs PERCENTILE, outside the 2007 list in the brief). With the cut, the claims movement chart still runs to about +20 typical moves over the full history: that is the firm's 1%. Is 1% right on the Dashboard, or would the firm take a wider cut there only?
- **Off-axis markers on the series tabs too.** New marker-only series on every series chart. Check that LibreOffice and Excel both draw triangles at size 6 without a legend entry.
- **Normal range drawn two ways.** Series tabs keep the MIST band; the Dashboard, all scatter, uses dashed lines. Acceptable, or dashed everywhere?
- **X-axis major unit is fixed at build** (5 years on the big Dashboard charts, 10 on the small). A window shorter than 5 years shows one year label or none.
- **The firm's tab colours.** Slate and stone alternate by topic. If the firm reads the alternation as meaning something, use SLATE for all core series tabs.
- **States as two side-by-side tables**: the build must split the moving-first order into two columns, read down left then right.
- **Row 8 on the series tab exists only with `--compare`**; every row below moves up one without it. Use a named constant for the chart row, as the README's row table assumes the compare build.

## Drawn to shape in the mock, not real

- **Weekly and daily series are drawn monthly** (from `series-by-month.json`); the workbook draws every reading. Their off-chart notes are the workbook's own text, so they count weekly and daily readings.
- **Chart text is Carlito and Arimo**, metric matches for Calibri and Arial; Excel's own glyph spacing and its auto axis rounding will differ slightly (Excel rounds an auto x axis out to a whole major unit).
- **Off-axis notes on the Dashboard** are worked out in JavaScript from the monthly data; the build's formula should give the same counts.
- **Excel chrome** (column letters, row numbers, the tab bar) is drawn, not captured. The fold is at 780 px of grid.
- **What if values** in tiles and the Overview are the example run's (`what-if-pandemic-left-out.json`). Household debt's "History from 2003 Q1" tile is from the tab's text.
- **The Value column's decimals** are today's `#,##0.0#`. If the catalog gains a published-decimals field, use it instead (4.2, not 4.20; 0.88, not 0.9).

## Labels that do not fit, with shorter versions for the firm to choose

| Where | Label | Fits in | Shorter |
|---|---|---|---|
| Dashboard and Household debt headers, 72 px | Change over 12 months | three lines (header row raised to 33 pt) | Change, 12 months |
| Dashboard header, 72 px | Level: at or above | two lines | (fits) |
| Overview tile, J:L | Sahm reading, beside the change | one line at 265 px | Sahm reading |
| Overview tile, M:O | What if: what-if-pandemic-left-out.json | one line at 327 px (file names vary) | What if |
| Series tab tile, T:Y | SAHM READING, BESIDE THE CHANGE | fits | — |
| Usable with care, B (411 px) | Banks tightening nonresidential property loan standards (net %) | fits at 58 wide; at today's 46 it is cut off | — |
| Overview, E (222 px) | index points per $1,000 of yearly income | fits at 31 wide; today's 26 cuts it | — |

New words this round, for the firm to approve or replace (none is a sentence about a reading):
- Series tab field labels "Lowest", "Highest" (from the tool's sentence) and "Sahm's published trigger" (from the Glossary).
- Dashboard levels-chart legend: "<name>: change only" when a pick has no level.
- Dashboard off-axis note: "Off the chart, <name>: N readings run off the top, M off the bottom; the furthest +X typical moves in Mon YYYY." (modelled on the series tab's note).
- What it is gains two labels, "Level" and "Change over 12 months", for the tool's sentences.

## Cuts

- The column header repeated per section (Overview ×5, Usable with care ×4): one frozen header.
- "same direction" in the What if column: blank when a change reads the same; the tile counts them.
- The Change to date when it equals Latest.
- "How this tab works" above the content on every tab: moved to the foot, collapsed, not deleted.
- The Dashboard's "Change in" column: the change's format already says points or %.
- Black column-header bands (States, What it is, What if): canvas headers.
- The six household debt type rows on the Overview: folded under the total.
- The ink section bands on Overview, Usable with care and series tabs: section names over an ink rule. The title band stays the one dark element.
