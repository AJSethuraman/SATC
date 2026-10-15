# Handoff: threshold-engine workbook redesign

## Overview
This redesign changes how the threshold-engine workbook looks and reads, above all the **Assess** tab. Every function stays. Goal: a credit-risk analyst opens the workbook and, without scrolling, sees five things:
- the product
- its latest score
- the Check
- the chart with its five score bands
- every input that moves the chart

A change and its effect are on one screen, and nobody flips between tabs.

The generator is Python + openpyxl (`src/threshold_engine/workbook.py`, styled through `keybank_style.py`). The work is a change to `assess_layout()`, to the style helpers and to chart styling. It is **not** a rewrite. Every formula keeps its meaning.

## About the design files
`Threshold Engine Redesign.dc.html` is a **design reference built in HTML**. It is a live mock of the workbook, drawn cell for cell at Excel's 100% zoom on a 1920×1080 screen. It is not code to ship. Recreate it in openpyxl inside the existing generator. Everything in it is something openpyxl can write:
- fills, fonts, borders
- number formats
- row heights and column widths
- merges
- conditional formatting
- data validation with input messages
- native line, area and column charts

The mock runs the engine's own maths in JavaScript on the real Federal Reserve series. It checks against `Thresholds-sample.xlsx` to the digit: Credit card 3.757 / 0.586 / 6.603 / 3.171 / 3.464 / 4.050 / 5.981, score 3 Moderate. Use it to check behaviour: type in any yellow cell. To see a refusal, set High z to 3.5. To see the bands flip, turn on the `lowerIsWorse` tweak.

Open the file in a browser. It needs `support.js` beside it. The CSV data is fetched from `uploads/threshold-engine-design-pack/code/tests/data/`; Credit card is embedded as a fallback.

## Fidelity
**High fidelity.** Colours, fonts, sizes, row heights, column widths and chart styling are final. The token sheet in the mock (section "Token sheet") is the source of truth and is repeated below.

## Hard constraints (unchanged from the brief)
- **No macros, buttons or code-driven toggles.** A control is only a cell whose value formulas read.
- **One input per fact.** Your settings stays a table with one row per product. The picked row is highlighted; there is no switching input set.
- **No merges on input rows** (Assess rows 19–22 and 26–37), so Excel can clear a row.
- **Fonts:** Arial, Calibri and Consolas only.
- **Every heading on Thresholds and on Assess's inputs keeps a Glossary entry.** `test_workbook.py` enforces this. The existing header labels are kept.
- **Refusal text says exactly why it refuses.** It is unchanged. A new "To fix" sentence is added beside it.

---

## Assess

### Grid
Hide gridlines.

**Column widths** (Excel character units; px = 7w + 5)

| Col | Width | Px | Use |
|---|---|---|---|
| A | 2.71 | 24 | gutter |
| B | 15.00 | 110 | labels, picker, dial Value |
| C–K | 9.00 | 68 | lines and counts |
| L | 53.29 | 378 | notes; chart spans B:L = 1100 px |
| M | 2.71 | 24 | gutter |
| N | 15.00 | 110 | Score, Product |
| O–T | 10.00 | 75 | inputs and numbers |
| U | 14.00 | 103 | Latest marker, Status overflow |
| Z–AC+ | hidden | | existing helpers, unchanged |

**Row heights** (pt)

| Rows | Height | Use |
|---|---|---|
| 1 | 22.5 | title |
| 2 | 13.5 | subtitle |
| 3 | 4.5 | spacer |
| 4 | 12 | field labels |
| 5 | 22.5 | picker, latest quarter and value, score chip |
| 6 | 25.5 | Check |
| 7, 16, 23 | 7.5 | spacers |
| 8, 17, 24, 40, 47, 63 | 16.5 | section titles |
| 9, 18, 41 | 22.5 | two-line headers |
| 15, 38, 88 | 13.5 | notes |
| 39 | 10.5 | spacer |
| 62 | 12 | spacer |
| everything else | 15 | data and input rows |

**Dial blocks** start at rows 64, 72 and 80. Row heights inside each block:
- title: 15 pt
- header: 22.5 pt
- 5 data rows: 15 pt each
- spacer: 22.5 pt

The bottom of the screen falls at about 780 px, which is row 39.

### `assess_layout()` changes
- `SET_TOP = 19`: Your settings, N19:R22, one row per product. The settings Check text is in S.
- `LO_TOP = 26`, `LO_ROWS = 12`: Periods left out, N26:T37.
  - N Product, O From, P To, Q Reason.
  - R and S are blank and formatted as part of the Reason box. Draw the outside border only. Nothing reads them; they only give the text room without a merge.
  - T Status (overflows into U).
- Product picker moves to **B5**. Check moves to **B6** (merged B6:U6). Every formula that reads `$B$4` must read `$B$5`.
- Score table: N9 header, N10:N14 rows, columns N–U.
- Main chart is anchored at **B9**, size 1100×464 px (29.1 × 12.3 cm), covering B9:L31.
- Evidence: title in B33, rows B34:B36. Label in B, text in C, overflowing to L.
- Scenarios: title B40, header B41, "As you have it" row 42, "Every quarter" row 43. Scenario chart B45:L61, 1100×340 px.
- What the lines rest on: N40 title, N41 header, N42:N45 rows.
- What each setting does: N47 title, N48 header, N49:N53 rows.
- Dials: section title B63.
  - High's z at 64.
  - Width of Moderate at 72.
  - Moderate-Low begins at 80.
  - Each block: title row, header, 4 values, a "now" row, spacer. Its bar chart sits in N:U over the same 8 rows.

### Top strip (rows 1–6)
- **Row 1, title** (B1:U1, merged): "Assess · set one product's thresholds". Arial 16 bold INK on PAPER, bottom-aligned. The heavy black banner is gone.
- **Row 2, subtitle** (B2:U2, merged): Calibri 11 SLATE. Medium KEY_RED bottom border across B:U, the one red rule on the tab. Text: "Pick a product, leave out periods that do not represent the risk, and set four things. Yellow cells are the only cells you type in; everything else follows as you type."
- **Row 4, field labels:** Arial 9 bold SLATE.
  - B4 Product
  - D4 Latest quarter
  - F4 Latest (%) (right-aligned)
  - H4 Latest score
  - L4 Measure
- **Row 5, values:**
  - B5: the picker. Input style, Calibri 12 bold, list validation of product names.
  - D5:E5 (merged): latest quarter, Calibri 14 bold.
  - F5:G5 (merged): latest value, Calibri 14 bold, right-aligned, `0.000`.
  - H5:J5 (merged): score chip, e.g. "3 Moderate", Arial 11 bold. Conditional formatting gives it a BAND_k fill by score. Refused: ALERT_FG fill, CRIMSON text, "No score: see Check".
  - L5: measure name, SLATE.
- **Row 6, Check** (B6:U6, merged): one formula.
  - Lines stand: "Check: lines stand." in Arial 12 bold INK, then "Every setting is in order and every period left out is whole." in Calibri 11. Fill CANVAS, thin MIST box.
  - Refused: the Thresholds refusal text, then "To fix: …". Fill ALERT_FG, CRIMSON text, thin KEY_RED box. Conditional formatting allows thin borders only.

### "To fix" text
New formula alongside the refusal. Keep it in step with the refusal order on Thresholds (col M). Numbers are computed live.

| Refusal | To fix |
|---|---|
| period not whole | "Finish that row under Periods left out (product, From, To and a reason), or clear all four of its cells." |
| half-width < 0 | "Type 0 or more in Width of Moderate." |
| z ≤ 0 | "Type a number above 0 in How rare High is." |
| step not a number | "Type a number in Moderate-Low begins." |
| too little history | "Put back a period, so that more than a year of quarters is kept." |
| median ≤ 0 | "Put back periods so the quarters kept centre above zero." |
| ML inside Moderate | "Raise Moderate-Low begins above {hw}, or lower Width of Moderate below {ls}." |
| High inside Mod-High | "Raise How rare High is above {CEILING(hw·move/spread, 0.01)}." |
| High beyond worst | "Lower How rare High is to {FLOOR(sg·(worst−median)/spread, 0.01)} or less, or put back a period that went higher/lower." |
| ML ≤ 0 | "Lower Moderate-Low begins to {FLOOR(median/move, 0.01)} or less." |

### Left column
- **Row 8, section title** (B8:L8): "{Product}, net charge-off rate (TTM, %), {first} to {last}, against its five scores". Arial 11 bold INK, medium INK bottom border, no fill.
- **Main chart.** Styling is under Charts below.
- **Evidence** (rows 33–36): title "What the evidence says about {Product}". Three rows: Suggested / Departures / Why. Labels are Arial 9 bold SLATE; text is Calibri 11. It sits level with the periods list it argues for.

### Right column (N:U)
**Scores for {Product}**
- Header: Score | From | To | Quarters kept | Share kept | Every quarter | Share of every | Latest.
- N10:N14 hold "1 Low" … "5 High" with static BAND_1–5 fills, Arial 9 bold. N10 also gets a thin STONE box so Low shows on white.
- In U, the row the latest quarter falls in shows "◀ 2026Q2", bold.
- Note in row 15: "A value on a line takes the worse score, as Your settings says. A loss at or below zero is always 1 Low."

**Your settings**
- Header (two lines, 22.5 pt): Product | Width of Moderate | Moderate-Low begins | How rare High is (z) | A value on a line takes the | Check.
- O:R are inputs. R has a list validation of worse / better.
- N is the product name. Conditional formatting `=$N19=$B$5` gives the picked row a PICKED fill and bold.
- S shows "Lines stand" in SLATE or the refusal in CRIMSON bold.

**Periods left out**
- Header: Product | From | To | Reason | Status.
- From and To keep the existing list validation of real quarters.
- Status: conditional formatting `ISNUMBER(SEARCH("refused",T26))` gives ALERT_FG fill and CRIMSON bold.
- Status text:
  - `"Left out: N quarters"`
  - `"Needs To, a reason: {Product} refused"`
  - `"From is after To: {Product} refused"`
- Note in row 38: "Left-out quarters stay on the chart as grey dots over a dark strip. Select a row's yellow cells and press Delete to put them back."

### Input messages (data validation `promptTitle` / `prompt`, ≤255 chars)
These replace the old wall of italic notes. Put "below" / "above" the other way round when lower is worse.

| Cell | Prompt |
|---|---|
| B5 Product | "Pick a product. Everything on this tab follows it." |
| Width of Moderate | "How wide Moderate is each side of the median, in typical yearly moves. 0.5 is half a year's movement each way. Raise it and more quarters rate Moderate." |
| Moderate-Low begins | "How far below the median score 2 starts, in typical yearly moves. Must be more than Width of Moderate. Raise it and fewer quarters rate Low." |
| How rare High is (z) | "High begins this many spreads above the median (a robust z). 2.5 is rare; 3.5 is the usual line for an outlier. Raise it and fewer quarters rate High." |
| A value on a line takes the | "worse or better: which score a quarter exactly on a line takes." |
| Product (periods) | "Pick the product this period is left out of." |
| From / To | "Pick a quarter from the list of quarters in the data." |
| Reason | "Say why this period does not represent the risk. It is recorded on Run." |

### Below the fold
**What happens if** (B40:L44): this is the old Scenarios table, now directly under the chart.
- Columns are shared with the dials: B label | C–F 2 from…5 from | G–K counts | L note.
- Count headers G–K carry BAND_1–5 fills: "1 Low", "2 Mod-Low", "3 Moderate", "4 Mod-High", "5 High".
- Rows:
  - "As you have it", note "solid lines; counts are quarters kept"
  - "Every quarter", note "dashed lines; same settings, nothing left out"

**What the lines rest on** (N40): Median / Typical yearly move / Spread of levels / Worst, each against "Quarters kept" (bold) and "Every quarter" (SLATE).

**What each setting does** (N47): header "Setting | Raise it and". One line each:
- Width of Moderate: "more quarters rate Moderate."
- Moderate-Low begins: "fewer quarters rate Low. Keep it above Width of Moderate."
- How rare High is (z): "fewer quarters rate High. 2.5 is rare; 3.5 is the usual outlier line."
- A value on a line takes the: "worse: a quarter on a line takes the higher score; better, the lower."
- Leaving a period out: "takes it out of the median, the move and the spread."

**Dials** (row 63+): section title "Dials · one setting at other values, the others as in Your settings; the shaded row is now".
- Each block: table in B:L, with its stacked bar chart beside it in N:U.
- Values:
  - High's z: 2, 2.5, 3, 3.5, now
  - Width: 0.25, 0.5, 0.75, 1, now
  - Moderate-Low: 0.75, 1, 1.5, 2, now
- The "now" row uses a MIST fill and bold, via conditional formatting on `SEARCH("now",$L66)`. It was INPUT yellow, which made it look typeable.
- Refusal notes are in CRIMSON.

---

## Thresholds
- **Columns** A–M: A 15 · B–H 11 · I–J 10 · K 8 · L 15 · M 70.
- **Rows:** 1 22.5 · 2 13.5 · 3 15 · 4 25.5 · 5+ 15. Data stays at **row 5**, so every `Thresholds!$A$5` reference holds.
- **Title:** same pattern as Assess. Arial 16 bold INK, red rule under row 2. Subtitle: "Live: follows every choice on Assess. Candidates for the bank to accept, adjust or reject."
- **Row 3 group headings** (new): Arial 9 bold INK, thin INK bottom.
  - B:D "What the lines rest on"
  - E:H "Each score begins at"
  - I:L "Latest quarter"
  - M "Check"
- **Row 4 headers:** CANVAS fill, Arial 9 bold SLATE, labels unchanged. E4:H4 get BAND_2–5 fills with INK text.
- **K (Score):** conditional formatting gives a BAND_k fill.
- **M (Check):** "Lines stand" in SLATE when blank today (or leave it blank). Refused: ALERT_FG fill, CRIMSON bold.
- Freeze panes at B5.

## Chart tab
- Controls go in one row instead of a column.
  - Row 4: header cells with each product name and a short line swatch in its series colour.
  - Row 5: TRUE/FALSE inputs, one per product.
  - "Bands for" picker beside them.
- Chart at A7, 1500×520 px (39.7 × 13.8 cm).
  - Series SERIES_1–4, 2 pt.
  - Stacked area bands of the "Bands for" product.
  - Legend at the bottom.
- The title rule is STONE, not red.

## Reference tabs (Evidence, Backtest, Glossary, Data, Run)
One quiet pattern:
- Title: Arial 14 bold INK on PAPER, Calibri 11 SLATE subtitle, thin STONE rule. Red is kept for the two live tabs.
- Section names: Arial 11 bold INK over a medium INK bottom border. No black bands.
- Column headers: CANVAS fill, Arial 9 bold SLATE, wrapped.
- Rows: 15 pt with HAIRLINE separators.
- Tab colour: STONE.

Per tab:
- **Evidence:** each product's two tables (spells, temporary departures) sit **side by side** with their own columns, so neither inherits the other's widths. Conditional formatting `ABS(z)>=3.5` gives robust z a BAND_3 fill and bold.
- **Backtest:** one header and one table, a row per product (and per weighting). Group headings: "Spearman: score against" over Level ahead / Change ahead; "Change after, quarters" over 1–5. Format `0.00`.
- **Glossary:** the only tab whose rows wrap. Terms bold, B2 frozen, row height set from estimated lines.
- **Data:** the single header row wraps to three lines (34.5 pt). Column groups alternate CANVAS / MIST header fill: raw / kept / changes … Frozen at B2, `0.000`.
- **Run:** four labelled sections on fixed columns: This build, Files, Periods left out (live), Your settings (live). Files columns: Product | File | Rows | First | Last | SHA-256. The hash goes last in Consolas 9 SLATE, so it never pushes data off screen.

**Tab order:** Assess, Thresholds, Chart, Evidence, Backtest, Glossary, Data, Run. Tab colours: Assess and Thresholds KEY_RED; Chart INK; the rest STONE.

---

## Design tokens

### Colour (hex without #)
| Token | Hex | Use |
|---|---|---|
| INK | 0A0908 | titles, section rules, history line, Chart series 1 |
| KEY_RED | CC0000 | rule under live-tab titles, refused Check edge, Chart series 2 |
| CRIMSON | 960019 | refusal text; 5 High line |
| PAPER | FFFFFF | sheet, chart areas |
| CANVAS | F4F1EC | column headers; Check when lines stand |
| MIST | E4DFD5 | dial "now" row |
| STONE | B9B4AC | header underline, axis lines, reference title rule, left-out dots |
| SLATE | 57534B | labels, notes, left-out strip, Chart series 3 |
| INK_TEXT | 16130F | data |
| ALERT_FG | F7DEDE | refused Check, Status, rows |
| HAIRLINE | E7E2D8 | row separators (exists as `_thin`) |
| INPUT | FFF2CC | every input cell, and nothing else |
| **INPUT_EDGE** (new) | D6B656 | thin border on every input cell |
| PICKED | F6D9A8 | product name of the picked row only |
| BAND_1–5 | F4F1EC, E4DFD5, EFD7CF, E0A6A6, CC8080 | 1 Low … 5 High |
| **LINE_2–4** (new) | 8E877B, B98577, B35A5A | 2/3/4 from, drawn as lines |
| LINE_5 | 960019 | 5 from (= CRIMSON) |
| **SERIES_4** (new) | 9C7A4A | Chart series 4 |

### Type (sizes in pt)
| Use | Font |
|---|---|
| Title, live tabs | Arial 16 bold INK |
| Title, reference tabs | Arial 14 bold INK |
| Subtitle | Calibri 11 SLATE |
| Section title | Arial 11 bold INK |
| Column header | Arial 9 bold SLATE, wrap, vertical centre |
| Field label | Arial 9 bold SLATE |
| Data | Calibri 11 INK_TEXT |
| Input | Calibri 11 bold; picker Calibri 12 bold |
| Latest quarter and value | Calibri 14 bold |
| Score chip / score cells | Arial 11 / 9 bold |
| Check, lines stand | Arial 12 bold INK |
| Check, refused | Arial 12 bold CRIMSON, then Calibri 11 CRIMSON |
| Notes | Calibri 10 SLATE, upright (no italics) |
| Hashes and paths | Consolas 9 SLATE |
| Chart text | Calibri 9 SLATE; legend INK_TEXT; titles 10 bold |

### Number formats
| What | Format |
|---|---|
| lines, latest, median, move, spread, worst | `0.000` (a points measure such as a credit score: `0.0`) |
| shares | `0%` |
| counts | `0` |
| typed settings | `General` |
| robust z | `+0.0;−0.0;0.0` |
| Spearman, backtest change | `0.00` |
| Run dates | `yyyy-mm-dd` |
| main chart y axis (floor at zero) | `0.0;;0.0` |

### Charts
**Main (Assess B9)**
- Bands: stacked area, BAND_1–5, no outline, gap 0.
- History: INK 2.25 pt, no markers.
- Left-out quarters: markers only, circle size 5, fill STONE, line SLATE 0.75 pt.
- Left-out strip: area series, SLATE.
- Latest: one-point series, circle size 7, fill PAPER, line INK 1.5 pt, data label on the left showing category and value.
- No gridlines. X axis `tickLblSkip=20`, `tickMarkSkip=20`. Axis lines STONE 0.75 pt. Chart area has no border and no rounded corners.
- Legend at the bottom, entries for bands and strip helpers deleted (`legendEntry delete=True`). The score table is the band key.

**Scenarios (Assess B45)**
- History INK 1.75 pt.
- Your lines: LINE_2–5 solid, 1.5 pt.
- Every-quarter lines: same colours, `sysDash`.
- Legend at the bottom, dashed entries deleted. The table names them.

**Dials (N:U)**
- Stacked column, overlap 100, gap width 60.
- Fills BAND_1–5, outline STONE 0.5 pt.
- No legend. The band-coloured headers beside each chart are the key.
- Title Calibri 10 bold. Y axis shows 0 and the maximum only.

**Lower is worse:** bands stack the other way (5 High at the bottom) because the area series are written in reverse order. Tables keep 1 Low to 5 High; From and To run downward.

## Assets
None. No images. The numbered dots in the mock are design notes, not workbook content. Turn them off with the `showNotes` tweak.

## Files
- `Threshold Engine Redesign.dc.html`: the live mock, token sheet and per-change reasons. Open it in a browser; it needs `support.js` beside it.
- `support.js`: the runtime for the mock.
- Generator to change (in the design pack):
  - `code/src/threshold_engine/workbook.py`: `assess_layout()`, `LO_TOP`, `SET_TOP`, picker and Check cells, chart styling
  - `code/src/threshold_engine/keybank_style.py`: add INPUT_EDGE, BAND_*, LINE_*, SERIES_4, plus light-title, section-title and header helpers
  - `code/src/threshold_engine/glossary.py`: unchanged unless headings are reworded
  - `code/tests/test_workbook.py`: update row and column constants; add a test that each refusal has a matching "To fix"
