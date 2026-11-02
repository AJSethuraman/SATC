# Handoff: Consumer Industry Analysis, design round 3 (19 Oct 2026)

Answers `docs/design/BRIEF-2026-10-18.md`. Round 2's hand-off (`docs/design/round-2/README.md`) stays in force; this file says what changes. The mock is `Consumer Industry Analysis Round 3.dc.html` (serve the folder, e.g. `python -m http.server`; it needs `support.js` and `data/` beside it). The notes beside each artboard in the mock are the per-tab reasons; the token sheet and the cuts are at its foot.

## Tab set and order

Work (tab colour INK): **Summary, Decide, Signals, Peers, Thresholds**, Internal (on site only).
Reference (STONE): **Lines by source** (Backtest folded in), **Peer books** (was Peer loan classes), **Evidence**, **Glossary**, **Sources** (Reporting changes folded in), **Run**.
Data (MIST): **Data, Signals data**, Internal data (on site only).
Hidden: Assess, Chart, Peers workings, Signals workings, **Peers data, Peers delinquency data**.

13 visible off site, 15 on site. `book.py` sets the order; `wb[name].sheet_state = "hidden"` for the two peer data tabs; Internal and Internal data are built only when an internal file is given.

## The peer group, one way everywhere

**Pack line.** One cell, Calibri 10 SLATE, under every chart or table that draws on the pack (Signals: every section that uses it; Peers: roster and both charts; Decide: under the chart):

`Peer group · 10 of 15 in · out by the book's rules, 2026Q2: Huntington, First Citizens, M&T, Zions · switched off on Peers: Capital One`

Formula on Peers workings: `TEXTJOIN(", ",TRUE,IF(state="out",bank,""))` etc. over the roster; the three states are `in` (Yes and a rate this quarter), `out` (Yes and no four-quarter average this quarter), `off` (No). Every other tab reads that one cell.

**Roster on Peers.** Row 8 bank names (15 × 120 px = 17.14 units), row 9 Yes/No inputs, row 10 the state word: `in` INK, `out by rule` SLATE italic, `off` STONE with strikethrough (conditional formatting on the Yes/No cell and the state cell).

## Tab by tab (what the generator changes)

### Summary (`summary_tab.py`)
- Columns per panel: B 260 (Measure) · C 64 · D 124 · E 60 · F 56 · G 112 · H 56 · I 112 px (36.4 / 8.4 / 17.0 / 7.9 / 7.3 / 15.3 / 7.3 / 15.3); J 24 px gutter; K–R repeat. No Product column: each product is a header row (Calibri 12 bold, thin INK top rule, 16.5 pt) across the panel, its measures under it.
- Source groups: KeyBank | vs Peer | Peer group | Industry only. Drop Large banks and Industry from 1990.
- Row 2 right: the Large banks strip, `Large banks (Philadelphia Fed) · card accounts paying only the minimum · 10.15% · 2026Q2 · rating —`, Calibri 11, value bold, format `0.00"%"`.
- Row 1 right: `Lines picked: n of 56 · KeyBank rated 4 or 5: n · refused: n`, Arial 12 bold.
- Body rows 15.75 pt. Left panel: Credit card (11 rows), Mortgage, Home equity; right: Other consumer (10), Auto, All consumer, Credit card + Other consumer.
- A rating with no source picked: `—` in SLATE. A source with no series for the row: blank. The Share paying only the minimum row reads `Large banks only` in SLATE italic in the KeyBank rating cell.
- Attention block under the left panel: 5 rows of SORTBY/FILTER over Thresholds (rating desc, value desc) with a fifth column `lines from <source>`; `None rated 4 or 5.` when empty.
- Footnotes: three lines (rating / points / from 1990), Calibri 10 SLATE.

### Decide (`decide_tab.layout()`)
- Columns: A 16 · B 110 · C 200 · D 150 (Lines set from) · E 130 · F G H 84 · I 74 · J K 80 · L 160 · M 170 · N 150 · O P 90 · Q 100 px.
- Slicers: Product over B4:E7, **3 columns** (three rows, 190 px buttons); Measure over F4:Q7, **5 columns** (three rows, 212 px). Rows 4–7: 15 / 18 / 18 / 18 pt. Every row reference below moves down one.
- Row 33 under the chart: the pack line.
- Right panel columns: 220 · 130 · 110 · 90 · 90 · 120 px, so "Large banks (Philadelphia Fed)" fits. Panel "Every source on these lines": five rows; a source with no series shows `—` in STONE across rating and latest, name in STONE.
- Gap measures: Y axis crosses at zero (SLATE 0.75 pt), zone base at the axis minimum; `1 Low` begins-at cell reads `below <line 2>`.

### Signals (`signals_tab.py`, positions only; all formulas unchanged)
- Columns: A 16 px, B–U 20 × 92 px (12.43 units).
- Row 1 title (25.5 pt), right: `Latest quarter 2026Q2 · nothing on this tab is rated`. Row 2 subtitle. Row 4 labels, row 5 inputs (19.5 pt): Product B:D, Measure E:H, Source I:J, Shift K:L, Window M:N; read-only Picked P:U. Row 6: the pack line. Row 7: the **jump row**, one HYPERLINK cell per section (`cell.hyperlink = "#'Signals'!B10"`, Calibri 10 KEY_RED underline). Freeze panes at B8.
- Section head: `quiet_section` (Arial 11 bold, medium INK rule) with the pick's names in the title where they apply (`30+ to charge-off, and the gap to peers · Other consumer`); no subtitle sentence.
- A. Where the dollars are: table B:H (130 · 96 · 46 · 128 · 46 · 120 · 46), header 27 pt wrapped, six rows + total; three small charts (368 × 200) to its right, I:L, M:P, Q:T, titles in the row above each; under the table, a label row and **five Yes/No input cells, one per product** (B:F, 120 px each, "On the charts") — each chart series reads a Signals workings column `=IF(on="Yes",value,NA())`, so a product set to No leaves the charts and the axes refit; each chart's legend holds all five products on two rows above the plot.
- B. 30+ incl. nonaccrual: four standard charts (452 × 220), 5 columns each; pack line under.
- C. 30+ to charge-off and the gap: two headline charts (912 × 264) B:K and L:U; under them a four-row "Gap, priced" table (520 px: 244 · 56 · 220) and the window test table (376 px: 92 · 64 · 76 · 64 · 80); pack line L:U.
- D. The pipeline: three charts 544 × 220 (6 columns); pack line.
- E. Seven signal blocks, each: head row (name with units on the left, `source · span · frequency` right-aligned Calibri 10 SLATE); overlay chart 912 × 264 B:K; raw signal 392 × 120 and raw picked 392 × 120 stacked L:O; fit table P:U, 500 px (290 · 46 · 46 · 78 · 40: Against, Lead, Fit (r), Excl. 2020-23, Qtrs), pick row first on CANVAS bold, |r| ≥ 0.70 bold; **inputs table** under the overlay, then the pack line, three rows (Line, Normal, One yearly move, Shift (quarters), Window), replacing the sentence.
- F. Across products: three charts 544 × 200.
- Chart styling: see tokens. Rescaled chart: Y `+0;-0;0`, major gridlines MIST 0.5 pt at every 1. Gap chart: Y axis fixed at −20 to +20 points (major unit 5, MIST gridlines) so the bounce reads small and an excursion stands out; two area series `=MAX(gap,0)` in GAP_WORSE and `=MIN(gap,0)` in GAP_BETTER under the line.
- "Where the dollars are" for a source without Call Report dollars: `—` in every number cell; the charts draw nothing; the heading stays.

### Peers (`peers/peers_workbook.py`)
- Roster as above; rank table's last column reads `in` / `in · Peer A` / `out by rule` / `off`; pack line under both charts and under the roster. Otherwise round 2.

### Thresholds (`thresholds_tab.py`)
- Columns: B 150 · C 232 · D 146 · E–K 68 × 7 · L 60 · M 116 · N 60 · O 116 · P 60 · Q 116 · R 124 · S 184 px (1,840 px). Check wraps; a refused row is 34.5 pt; the Product cell wraps on a combined product's first row (25.5 pt). Source groups KeyBank | Peer group | Industry only.
- Values `0.00`. Undecided row: blank from D to S. Count top right as on Summary. Freeze at D5. Thin INK top rule per product.

### Lines by source
- Reference treatment (Arial 14 title, STONE rule, MIST header). Columns: B 150 · C 216 · D 150 · E–K 72 × 7 · L 64 · M 64 · N 120 · O 110 · P 260 (wraps; refused rows 34.5 pt) · Q 72 · R 72 · S 64 · T–X 64 × 5.
- Q–S from Backtest, headed "Spearman, value", "Spearman, change", "Quarters tested" (the group label above them: "How predictive, 4 quarters ahead"); the Median/Typical move/Worst columns are headed "Median kept", "Yearly move", "Worst kept" on Thresholds and Lines by source so each header fits two lines at 27 pt; T–X the average change ahead by rating 1–5, `ws.column_dimensions.group('T','X', hidden=True)`.
- Rating fill only on N; `Refused` CRIMSON bold on CANVAS; Check `OK` SLATE or `To fix: …` CRIMSON bold. Values `0.00`. Freeze at E5.

### Internal (`internal_tab.py`)
- Four top blocks on one 16.5 pt pitch with 24 px gutters: products B:C (150 · 190), measures E:F (150 · 250), reliable H:I (230 · 100), coverage K:P (180 · 102 × 5). Seven rows in each mapping list. Reliability table header INK 27 pt wrapped. Used range ends at Z; helper columns move to Internal data.

### Peer books, Evidence, Glossary, Sources, Run, Data, Signals data
- One reference template: title Arial 14 bold, subtitle with thin STONE rule, section heads `quiet_section`, headers MIST / Arial 9 bold INK / 27 pt / STONE rule, 15 pt rows, hairlines `E7E2D8`, filters only on Product, Measure, Source (Bank, Counted as, Tab).
- Peer books: Why column 876 px wrapped Calibri 10; amounts `#,##0` right; words in amount columns SLATE; verdict bold (Not comparable CRIMSON, Clean INTERNAL_TEXT). Second table an Excel table.
- Evidence: two Excel tables, Spells (B:L) and Departures (B:K), Product/Measure/Source on every row with repeats hidden by white font (`=B6=B5`); robust z ≥ 3.5 bold; z `+0.0;-0.0;0.0`.
- Glossary: a `Tab` column first (120 px), Term 240, Meaning 640, Calculation 806, Calibri 10 wrapped. New entries: Pack line, Rescaled, Lead, Fit, Window for the normal, Shift, Jump row.
- Sources: three sections. Shared notes (S1–S4) once; Every series file, one row each (file name only, rows, first, last, shared-note keys, reporting-change quarters, the file's own notes verbatim with `Not stated: …` once in CRIMSON bold); Reporting changes (the old tab's table; source documents as hyperlinks).
- Run: Series folder printed once under This build; Files table with Product/Measure/Source split and file name only; SHA Consolas 9 SLATE; Left out as built beside This build.
- Data, Signals data: `ws.row_dimensions.group(2, 62, hidden=True)`; header 45 pt MIST wrapped with ` · ` between the three parts; Signals data header is the series name, key and source in the two rows above; freeze at B2.

## Tokens added in round 3
`SIGNAL 9C7A4A` (a public signal's line; Large banks), `GAP_WORSE F4CBCB`, `GAP_BETTER E9F1E3`. Everything else is round 2's. Formats, type and chart sizes: the token sheet in the mock.

## Constraints checked
No macros; no merged input cells; decisions stay in the Decide table; every Signals cell that depends on the pick stays a formula; axis bounds untouched (the rescaled chart keeps one standardized axis, with its inputs in a table); words are facts (the pack line's states are the book's own); American spelling.

## Mock data
30+ to charge-off, the gaps, the three drawn signals and their fit numbers, the Backtest columns and the Internal sample are drawn to shape; the extract (`data/`) does not hold them. The rest runs on the extracted Data and Peers data tabs.
