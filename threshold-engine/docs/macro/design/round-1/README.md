# Handoff: Macrobook, design round 1

The economic conditions workbook, designed for what its readers come to do. Every function stays; every number is still a value the tool writes, and the Dashboard is still the one tab with formulas. The work is a change to `workbook.py`'s layout and chart styling, plus seven tokens appended to `keybank_style.py` (`keybank_style_additions.py`). It is not a rewrite.

## Files

- `Macrobook Redesign.dc.html`: the mock, drawn cell for cell at Excel's 100% zoom on 1920 × 1080 with the ribbon open, from `data/macro.json` (the pull of 22 Oct 2026, cut down from the brief's `data/*.json`). Open in a browser; it needs `ExcelSheet.dc.html` and `support.js` beside it. The Dashboard's four boxes work. Tweaks: `whatIf` (build with or without `--compare`), `screen` (moves the fold to 1366 × 768).
- `keybank_style_additions.py`: the token sheet, as code to append.
- `MESSAGE_TO_ARCHITECT.md`: decisions, what to confirm, what is drawn to shape, long labels, cuts.

Units below: column widths in Excel units (px = 7w + 5), row heights in points (px = pt × 4/3), chart sizes in cm (and px).

---

## The system (every tab)

### Grid
- **Table tabs** (Overview, Usable with care, States): the Overview's columns, below.
- **Chart tabs** (Dashboard, every series tab, Household debt): A 2.71 · B:Y 24 × 9.57 (72 px each) · Z 2.71. Content B:Y is 1,752 px; half 864 (B:M, N:Y); quarter 432 (B:G, H:M, N:S, T:Y). Charts anchor at B, H, N or T with no offset.
- **Every tab**: row 1 title (27 pt), row 2 links (15 pt), row 3 spacer (6 pt). Gridlines hidden. Column A is the gutter.

### Cell roles

| Role | Font | Fill | Border | Align |
|---|---|---|---|---|
| Title | Arial 16 bold PAPER | INK across A:last (record tabs SLATE) | thick KEY_RED bottom (record: thick STONE) | left, middle |
| Subtitle | Calibri 10 STONE (record: MIST) | as title | as title | in the first column past the title (title length × 12.4 px + 20) |
| Link (row 2, names) | Calibri 10 (row 2) / 11 (tables) MACRO_LINK, no underline | none | none | left |
| Tile label | Arial 9 bold SLATE, indent 1 | CANVAS | thick KEY_RED top; medium PAPER left (the 2 px gap between tiles) | left |
| Tile figure | Arial 12 bold INK_TEXT (Overview, Usable with care) · Arial 14 bold (chart tabs) | CANVAS | medium PAPER left | left |
| Field label (in a tile) | Calibri 9 SLATE, indent 1 | CANVAS | none | left, bottom |
| Field value (in a tile) | Calibri 11 INK_TEXT, indent 1 | CANVAS | none | left |
| Section name | Arial 10 bold INK | none | medium INK bottom across the section's columns | left, bottom |
| Column header | Arial 9 bold SLATE, wrap | CANVAS | thin STONE bottom | as its column's data |
| Data | Calibri 11 INK_TEXT | none | thin MACRO_RULE bottom across the table | numbers and dates right; text left |
| Unit | Calibri 10 SLATE, indent 1 | none | rule | left |
| "change only" | Calibri 10 SLATE | none | rule | right |
| Direction | see `direction_cell` | MIST when moving | thin MACRO_RULE bottom | centre |
| Note (off the chart, credit) | Calibri 10 SLATE, upright, wrap | none | none | left, top |
| Why with care | Calibri 10 SLATE, indent 1, 13.5 pt row under the name | none | thin MACRO_RULE bottom | left, top |
| Input (Dashboard) | Calibri 11 bold INK_TEXT | INPUT | thin INPUT_EDGE; bottom medium PICK[i] on the two series boxes | left |
| "How this tab works" | Arial 9 bold SLATE | CANVAS across the content | none | left |

### Number formats

| What | Format |
|---|---|
| Change, Normal from, Normal to: points | `+0.00;-0.00;0.00` |
| Change, Normal from, Normal to: percent (written as a fraction) | `+0.00%;-0.00%;0.00%` |
| Typical moves | `+0.0;-0.0;0.0` |
| Level: at or above | `0.0%` |
| Value | `#,##0` at 1,000 and over, else `#,##0.0#` (today's) |
| Latest, Change to: daily and weekly | `yyyy-mm-dd` |
| Latest, Change to: monthly | `yyyy-mm` |
| Latest, Change to, Since, History from: quarterly | text, `"2026 Q2"` |
| Since, History from: not quarterly | `yyyy-mm` |
| Balance, $ trillions | `0.000` |
| Share of total | `0.0%` |
| Chart axes | points and typical moves `+0;-0;0` (one decimal when the major unit is under 1); percent the same; level `#,##0` or `0.0`; levels chart `0%` |

### Direction
Kept, as today: "▲ Increasing" and "▼ Decreasing" bold INK on MIST; "Stable" SLATE with no fill. The fill is the same both ways, so it reads as moving, not as good or bad. Font changes from Arial 9 to Calibri 11 (the data font). The white left and right borders go.

### Charts (every chart)
- No chart border, no rounded corners. Plot area PAPER.
- Title Calibri 10 bold INK_TEXT, centred, overlay off.
- Legend only with two or more named lines: **top**, Calibri 9 INK_TEXT. Never at the bottom (it overprints the axis labels in Excel).
- Every series states one line colour in `spPr` and writes no `dPt`: otherwise Excel gives each point a legend entry (the rows of dashes on 22 Oct).
- X axis: decimal years on scatter charts (Dashboard, daily and weekly series) or a date category axis (monthly, quarterly); `tickLblPos = low`; labels Calibri 9 SLATE, format `0`; line STONE 0.75 pt; major tick out; major unit below per chart.
- Y axis: labels Calibri 9 SLATE; line STONE 0.75 pt; title (the unit) Calibri 9 bold INK_TEXT, rotated; crosses at the minimum so the x labels stay at the foot.
- Gridlines: major horizontal only, MACRO_RULE 0.75 pt. No vertical gridlines.
- History line: INK 1.5 pt, no markers, blanks as gaps (`dispBlanksAs="gap"`).
- Normal range (series tabs, Household debt): stacked area, an invisible base at Normal from and a NORMAL_BAND band of (Normal to − Normal from), no outline.
- What-if normal range: two WHATIF_LINE lines, 1 pt, `sysDash`, legend entries deleted.
- Latest: one-point series, circle size 7, PAPER fill, INK 1.5 pt, data label right with its value in the change's format.
- Off the axis (the firm's 1% at each end): the axis bounds are written as today; readings past them are left off as today; **new**, a marker-only series puts a triangle (size 6, fill OFF_AXIS, line SLATE 0.75 pt) at the bound on each reading's date. Legend entry deleted. The note under the chart is unchanged.

---

## Tab order and colours

| # | Tabs | Tab colour |
|---|---|---|
| 1–3 | Overview, Dashboard, What if (with `--compare` only) | INK |
| 4–7 | Jobs: Unemployment, Initial claims, Continuing claims, Payrolls | SLATE |
| 8–13 | Prices and insurance: Prices … Home insurance | STONE |
| 14–23 | Housing and household credit: House prices … Card standards, Household debt | SLATE |
| 24–30 | Business and the economy: Real GDP … Business loan demand | STONE |
| 31–39 | Markets and financial conditions: Prime rate … Yield curve | SLATE |
| 40 | States (was 4th) | INK |
| 41–72 | Usable with care, then its 31 tabs in its order | MIST |
| 73–76 | State data, Glossary, (Not read when there is one), Run, Sources | none |
| hidden | Dashboard data | MIST |

Series tabs follow the Overview's row order exactly, so the tab bar and the front page agree. The topic colours alternate (slate, stone, slate…) only to show where one topic's tabs end.

---

## Overview

**Columns:** A 2.71 · B 58 Series · C 10.71 Latest · D 10.71 Value · E 31 Unit · F 10.71 Level: at or above · G 11.86 Change over 12 months · H 10.71 Change to · I 11.86 Normal from · J 11.86 Normal to · K 14.57 Direction · L 9.29 Typical moves · M 9.29 Since · N 9.29 History from · O 26 What if (with `--compare`). B:O is 1,721 px.

**Rows:**

| Row | pt | Content |
|---|---|---|
| 1 | 27 | Title "Economic conditions"; subtitle in C1 |
| 2 | 15 | B2 link "Dashboard: any two series together"; C2 link "Also read, with care: 31 series" |
| 3 | 6 | spacer |
| 4 | 15 | tile labels |
| 5 | 22 | tile figures |
| 6 | 9 | spacer |
| 7 | 24 | the one column header, B:O |
| 8 | 18 | section "Jobs" |
| 9+ | 15 | series rows; a 6 pt spacer, then an 18 pt section row, before each later topic |
| after the last row | 12, 15 | spacer, then "How this tab works" (CANVAS, B:O) with its entries grouped beneath it, **collapsed** (`hidden=True`, `summaryBelow=False`) |

**Tiles** (row 4 label, row 5 figure): B "From the pull of" · C:D "Changes read" · E "▲ Increasing" · F:G "Stable" · H:I "▼ Decreasing" · J:L "Sahm reading, beside the change" · M:O "What if: …" (link to What if).

**Rows:** one per series in the TOPICS order. **Household debt:** only "Household debt: total" shows; the six types follow it as a group, collapsed. **Change to** is written only when it differs from Latest, then bold. **What if** is written only when the series' change reads another way ("Change Increasing → Stable", bold); blank otherwise.

**Freeze panes:** C8. **Fold** (1920 × 1080): row 45, inside Business and the economy.

---

## Dashboard

**Columns:** the chart-tab grid.

| Row | pt | Content |
|---|---|---|
| 1–3 | 27 / 15 / 6 | title; B2 "Back to Overview"; spacer |
| 4 | 13.5 | field labels, Arial 9 bold SLATE, bottom: B4 "First series", H4 "Second series", N4 "From", Q4 "To" |
| 5 | 21 | the four inputs: B5:G5, H5:M5, N5:P5, Q5:S5 (merged; validation on the first cell). Lists as today |
| 6 | 6 | spacer |
| 7 | 33 | header: B:E Series · F Latest · G Value · H:I Unit · J Level: at or above · K Change over 12 months · L Normal from · M Normal to · N:O Direction · P Typical moves · Q Since · R History from |
| 8, 9 | 15 | the two picks (formulas, as today). B has a thick PICK[i] left border |
| 10 | 6 | spacer |
| 11–24 | 15 | the two "together" charts |
| 25 | 15 | B25:Y25 the off-axis note (formula), Calibri 10 SLATE |
| 26 | 18 | B26:M26 first pick's name (formula), N26:Y26 second's: Arial 10 bold INK over a medium PICK[i] rule |
| 27–38 | 15 | the four small charts (anchored 4 px down, row 27) |
| 40 | 15 | "How this tab works", collapsed |

Row references move: every formula that reads `$C$4`, `$C$5`, `$C$6`, `$C$7` now reads `$B$5`, `$H$5`, `$N$5`, `$Q$5`.

**Charts** (all scatter, x in decimal years, axes auto-fit):

| Chart | Anchor | Size | Contents | X major |
|---|---|---|---|---|
| Both changes over 12 months, in typical moves from each one's median | B11 | 22.86 × 7.41 cm (864 × 280) | pick lines PICK[0], PICK[1] 1.75 pt; ±1 STONE 1.25 pt `sysDash` (one legend entry "Normal movement"); off-axis markers | 5 |
| Both levels: where each sits in its own history | N11 | 22.86 × 7.41 cm | pick lines 1.75 pt; y fixed 0 to 1, major 0.25, `0%`; legend name from a formula cell: the name, or name & ": change only" | 5 |
| Level (×2) | B27, N27 | 11.32 × 6.24 cm (428 × 236) | pick line 1.5 pt; off-axis markers; no legend | 10 |
| Change over 12 months, its normal range dashed (×2) | H27, T27 | 11.32 × 6.24 cm | pick line 1.5 pt; Normal from and to STONE 1.25 pt `sysDash`; off-axis markers; no legend | 10 |

**The spike rule (new formulas, 2007 functions only).** Dashboard data gains, per series, six values: the 1st and 99th percentile of its typical moves, its level, and its change over every month of its history (the firm's 1% at each end). Each drawn column becomes `=IF(ISNUMBER(v),IF(OR(v>hi,v<lo),NA(),v),NA())`, and a marker column `=IF(ISNUMBER(v),IF(v>hi,hi,IF(v<lo,lo,NA())),NA())`. Excel then fits the axis to what is left. The note in row 25 counts the markers and names the furthest reading with INDEX/MATCH/MAX/MIN on the window.

---

## Series tab (one function, 66 tabs)

**Columns:** the chart-tab grid, then the history: AA 10.71 Date · AB 12 Value · AC 14 Change over 12 months · AD 20 Note (were N:Q). Helper columns for the charts follow, hidden, as today.

| Row | pt | Content |
|---|---|---|
| 1–3 | 27 / 15 / 6 | title; B2 "Back to Overview" (care tabs: "Back to Usable with care"), E2 "Dashboard", H2 "What if"; spacer |
| 4 | 18 | tile titles, Arial 9 bold SLATE: B4 "LEVEL" (B:G), H4 "CHANGE OVER 12 MONTHS" (H:S), T4 "SAHM READING, BESIDE THE CHANGE" (T:Y, Unemployment only). AA4:AD4 the history header |
| 5 | 24 | figures. Level: B:C latest value (Arial 14 bold), D:E unit (Calibri 10 SLATE), F:G date (right). Change: H:I direction, J:K change (Arial 14 bold, right), L:M "points"/"percent", N:O date. Sahm: T:U value, V:W "points", X:Y month |
| 6 | 13.5 | field labels. Level: B:C "Level: at or above", D:E "Lowest", F:G "Highest". Change: H:I "Normal from", J:K "Normal to", L:M "Typical moves", N:O "Since", P:Q "History from". Sahm: T:Y "Sahm's published trigger" |
| 7 | 15 | field values, same columns. Change only: B:G "change only" (SLATE) |
| 8 | 15 | with `--compare` only: B "WHAT IF", C:G the level's what-if sentence; H "WHAT IF", I:J the what-if direction, K:S its sentence |
| 9 | 9 | spacer |
| 10–25 | 15 | charts |
| 26 | 27 | off-chart notes, wrapped: B:M under the level chart, N:Y under the change chart (change only: B:Y) |
| 27 | 9 | spacer |
| 28 | 18 | section "What it is", B:M |
| 29+ | 15 per line | label B:C (Calibri 11 bold, top) · text D:M (wrap, top); row height 15 pt × lines, lines = ⌈characters × 6.6 / 710⌉. Rows: Source, Licence, First reading, How it is read, In the research, Note, Break…, then **Level** and **Change over 12 months** carrying the tool's two sentences (moved out of the tiles, unchanged) |
| after | 12, 15 | spacer, "How this tab works" collapsed |

Tile fill CANVAS over rows 4–7 (4–8 with `--compare`), thick KEY_RED top on row 4, medium PAPER left edge on each tile.

**Charts:**

| Chart | Anchor | Size |
|---|---|---|
| Level against its history | B10 | 22.86 × 8.47 cm (864 × 320) |
| Change over 12 months, its normal range shaded | N10 | 22.86 × 8.47 cm |
| Change only: the change chart alone | B10 | 45.72 × 8.47 cm (1728 × 320) |
| Sahm reading (Unemployment) | N28 | 22.86 × 5.82 cm (864 × 220); trigger 0.50 WHATIF_LINE `sysDash` |

X major unit: 10 years when the drawn history is over 60 years, 5 over 12, else 2; 5 on the full-width change chart. Daily and weekly series stay scatter in decimal years.

**Freeze panes:** A4. **Fold:** row 37, inside What it is (the change sentence).

---

## Household debt

Chart-tab grid. Rows 1–3 as a series tab. B2 "Back to Overview", E2 "Dashboard".

| Row | pt | Content |
|---|---|---|
| 4–7 | 18 / 24 / 13.5 / 15 | tiles: B:G "Total, 2026 Q2" ($18.77 trillion, `"$"0.00" trillion"`; History from 2003 Q1). H:S the total's change tile, as a series tab |
| 8 | 9 | spacer |
| 9 | 18 | N9:Y9 section "Each type, latest quarter" |
| 10 | 33 | header: N:O Type, as the NY Fed heads it · P Balance, $ trillions · Q Share of total · R Change over 12 months · S Normal from · T Normal to · U:V Direction · W Typical moves · X Since · Y History from |
| 11–17 | 15 | six types and Total (Total bold, thin INK top rule) |
| 18 | 9 | spacer |
| 19–26 | 15 | the total's change chart |
| 27 | 27 | B:Y the NY Fed credit line (Calibri 10 SLATE, wrap) |
| 29+ | | What it is, as a series tab; "How this tab works" collapsed |

**Charts:** stacked column "Total Debt Balance and Its Composition (the NY Fed's chart, as it reports it)" at B9, 22.86 × 9.74 cm (864 × 368): overlap 100, gap 50, fills DEBT_TYPES, no outlines, legend top, y 0 to 20 major 5 format `0`, x major 2 years. Total change at N19, 22.86 × 4.23 cm (864 × 160), as a series change chart. History stays in N:U → moves to AA:AH.

---

## Usable with care

The Overview's columns B:N (no What if column). Rows 1–3 as the Overview; B2 "Back to Overview". Tiles row 4–5: B "Series read" · C:D "In the group, not read" · E "▲ Increasing" · F:G "Stable" · H:I "▼ Decreasing". Row 7 the header; freeze C8.

Each series takes two rows: its reading (15 pt, as the Overview) and **Why with care** (13.5 pt, B:N merged, Calibri 10 SLATE, indent 1, top), the rule under the second. Then "In the group, not read, and why" (B Series, C:N why) and "Credits the publishers' licences require" (row height by lines). "How this tab works" collapsed at the foot.

## States

Two side-by-side tables of 26 and 25 rows, so all 51 sit above the fold. Each: State 7 · Latest 9.57 · Unemployment rate 9.57 · Level: at or above 9.57 · Change over 12 months 9.57 · Normal from 9.57 · Normal to 9.57 · Direction 14.57 · Typical moves 9.29 · Since 9.29 · History from 9.29 (· What if 13 with `--compare`), A 2.71 and a 2.71 gap column between them. Header row 33 pt; freeze below it. Order unchanged (moving first, then by state), read down the left table then the right.

## What if

Unchanged in content. Ink header bands become canvas headers; section bands become section names; row heights 15 pt (28 pt only where a "what" text needs two lines). The grid and the bar chart keep their places.

## Reference tabs (Glossary, Run, Sources, Not read, State data)

- Title as above in SLATE, thick STONE rule. B2 "Back to Overview".
- Header CANVAS, 18 pt. Rows: Calibri 11, thin MACRO_RULE bottom, top-aligned; row height 15 pt × lines + 3, lines counted at 6.6 px a character.
- No text column wider than 110 (775 px).
- **Glossary:** B 28, C 110. Freeze A5.
- **Run:** B 42, C 40, (D 40), E 110.
- **Sources:** B 44 · C 36 · D 30 · E 34 · F 13 · G 28 · H 26 · I 60 Address · J 66 SHA-256 (Consolas 9 SLATE) · K 44; Address and SHA-256 move to the end.
- **State data:** unchanged; header canvas; freeze B4.
