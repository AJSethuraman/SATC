# Handoff: Origination Cube redesign (launcher + Excel workbook)

## Overview
Origination Cube is a desktop tool for a credit-risk analyst. A small **launcher window** reads a loan extract (one row per loan) and writes an **Excel workbook**. The analyst answers professional calls in the workbook, and **Run** fills in the results. The results show which pockets of the book lose more than their share, what each pocket paid and cost, and whether each gap is real (**Worse?**) and big enough to matter (**Material?**). A second mode tests a shortlist of candidate variables: each is found on one set of loans and confirmed on a held-back set, with and without chosen columns held fixed.

This redesign covers every launcher state and every workbook tab. It merges 15 tabs into 10, adds one place to choose tests, and makes it obvious which settings change results live and which need a re-run.

## About the design files
`Origination Cube Redesign.dc.html` is a **design reference built in HTML**. It shows the intended look and behaviour; it is not production code. The job is to recreate it in the real stack:
- **Workbook:** native Microsoft 365 Excel, written by the existing Python runner (openpyxl or XlsxWriter). Use sheets, Excel Tables, conditional formatting, data validation, slicers, native charts, outline grouping and formulas only. Everything in the mock was chosen to be buildable that way. See "Excel build notes".
- **Launcher:** the existing small desktop window (Tk or similar), 720 × 560.

To view the design, open the `.dc.html` in a browser with `support.js` beside it. Click the sheet tabs at the bottom of the workbook frame. On the Pockets tab, the Measure, Pockets and Show slicers work. In launcher L2, the mode toggle and checkboxes work. The Tweaks panel exposes `showPending` (a Control change waiting for a Run) and `startTab`.

## Fidelity
**High fidelity** for layout, colour, hierarchy, copy and column order. Fonts map to Excel fonts (Arial for headers, Calibri for data). Pixel widths in the mock translate to Excel column widths at roughly 7 px per character unit. All data is synthetic, taken from the current screens (8,000 loans). The New variables figures and the two profit measures on Pockets are invented for illustration.

---

## Global rules (apply to every sheet)

1. **Sheet anatomy, top to bottom, the same on every tab:**
   1. **Title band:** row 1, merged across the used width. Fill `INK 0A0908`, white Arial bold 16, a one-line subtitle in `STONE B9B4AC` Arial 10, and a 3 pt **Key Red `CC0000`** bottom border. (Record tab: `SLATE 57534B` fill, `STONE` bottom border.)
   2. **How this tab works:** the only method note on the tab. Rows 3 to ~10, fill `CANVAS F4F1EC`, label column bold, text in a merged wide cell with wrap on. **Group these rows with Excel's outline grouping** so the reader can collapse them with −. Never put method text beside a result row.
   3. **Lines in use now** (result tabs only): KPI tiles made of merged cells, `CANVAS` fill, a **3 pt Key Red top border**, label Calibri 9 `SLATE`, value Arial bold 12. Each value is a **formula pointing to Control**, so it's live. Beside the tiles: "Order and 'Could have caught' are from the last Run, <timestamp>". If any Needs-a-Run cell differs from the last Run, add a line in `CRIMSON 960019` bold: "↻ 1 Control change waits for a Run."
   4. **Selectors** (slicers or dropdown cells), then **result rows only**.
2. **Gridlines off.** Freeze panes just below the column-header row.
3. **Column headers:** `INK` fill, white Arial bold 9, one line.
4. **Alignment:** numbers, verdicts, short answers and status cells are **centred**. Row labels (pocket, band, segment, setting names) and long phrases are **left-aligned**.
5. **No wrapping in result rows.** Every row is one line and every row in a table is the same height. Set column widths to fit the longest value **and** the header. Wrapping is allowed only in method notes.
6. **Symmetry:**
   - Section headers that sit side by side must line up: same row, same height, same fill.
   - Each section has a dark header band, then a `CANVAS` sub-header row naming its columns.
   - Paired sections share label-column widths. Prefer white space to ragged colour blocks. See the Record tab.
7. **Tab colours** (`sheet_properties.tabColor`): `CC0000` for tabs you fill in (Start here, Control, Columns, Look), `0A0908` for results (Pockets, Paid cost kept, Grids, Split, New variables), `B9B4AC` for Record.
8. **Input cell styles** (legend at the top of Control):
   - **Changes now:** `CANVAS` fill, 1 px `INK_TEXT 16130F` solid border, bold.
   - **Needs a Run:** white fill, dashed `SLATE` border, bold. The column header carries "↻".
   - **Still needs an answer:** `ALERT_FG F7DEDE` fill.
9. **Verdict cells:**
   - **Worse?** Yes: `F7DEDE` fill, `CRIMSON` bold. Not sure: `CANVAS` fill. No and Too few losses: `SLATE` text, no fill.
   - **Material?** Yes: `MIST E4DFD5` fill, bold. No: plain.
   - The two are always **separate columns**.
10. **Plain words.** Use these column labels:

| Current | New |
|---|---|
| p-value | Chance it's luck |
| worse, not significant | Worse? = Not sure |
| below the line | Material? = No |
| Smallest gap it could show | Could have caught |
| Outcome, share of loans | Bad loans |
| Outcome, share of booked dollars | Bad dollars |
| GCO per booked dollar | Charge-offs |
| RANR per booked dollar | Kept after losses |
| Contribution before losses | Earned before losses (column group: "Paid us") |

---

## Launcher (720 × 560)

**Layout:**
- Title bar.
- **Left step rail**: 196 px wide, fill `CANVAS`, 1 px `MIST` right border. It starts with the app name in bold 15 over a 3 px Key Red rule, followed by five steps: Extract · Set up · Choose tests · Answer in workbook · Run.
- Step markers are 22 px circles:
  - **Done:** `INK` fill with ✓.
  - **Current:** `CC0000` fill with the step number.
  - **To do:** 1.5 px `STONE` outline, grey number.
  - **Blocked:** `CC0000` fill with "!" and a crimson sub-label ("4 left").
- Each step can show a one-line sub-status under its name, such as "loans.csv · 8,000 loans".
- **Main pane:** padding about 20 px, vertical stack.
- **Buttons:** radius 6.
  - **Primary:** `CC0000` fill, white bold 13.
  - **Secondary:** white with a 1 px `STONE` border.
  - **Disabled:** `MIST` fill, `9A958C` text.

**States:**
- **L1 · Opened:** "Pick the loan extract", a path field with Browse…, and an expanded **"How Set up recognises columns"** box holding two dropdowns: "12 values", "50 values". These moved here from Control because they're needed before the workbook exists. Set up is disabled until a file is picked.
- **L2 · Choose tests (new; the one place to choose tests):**
  - A segmented toggle: **Where the book bleeds | Test new variables**.
  - A table listing every extract column: Column · What it is · three control columns that change with the mode.
    - **Test new variables:** Outcome (radio; outcome and dollar columns only) · Test it (checkbox) · Hold fixed (checkbox). Test it and Hold fixed exclude each other on a row. Under the table: "Find on [70% ▾] confirm on the rest", and "Or confirm a saved shortlist [Browse…]" (the pre-spec file).
    - **Where the book bleeds:** Cut into bands (number columns) · Segment by (categories) · Split pockets by (radio, one number column). Outcome columns show "· every measure". *(27 Sep 2026: they show nothing now, and the rows run number columns, categories, outcomes, then key and date.)*
    - Key and date columns are greyed, with no controls.
  - A live summary box (CANVAS, 3 pt red top border): "This will run: 4 inputs (…) against BAD_FLAG, each with and without FICO held fixed: 8 tests, found on 70% and confirmed on 30%." In bleed mode: "2 band columns × 2 segment columns = 4 grids, five measures each; split by REV_DEBT adds 4 more."
  - Footer: "Saved to Control, read-only." and the primary button **Next: answer in the workbook →**.
  - The choices are written to the workbook. Control shows them read-only.
- **L3 · Run pressed before everything is answered:**
  - Title: "4 answers needed before Run".
  - If the workbook is open: a `F7DEDE` banner, "The workbook is open in Excel. Save and close it first…".
  - A list of rows, each: red sheet!cell tag (Arial bold 11, e.g. "CONTROL C14") · the question in words · **Open at C14** (opens the workbook at that cell).
  - Run the cube stays disabled.
- **L4 · An add-on is missing:** a full-width `INK` banner under the title bar with a Key Red bottom rule: "One add-on is missing: numpy, which does the statistics." with **Install now**. Below it: the rail at 50% opacity; the extract can still be picked and an existing workbook opened; Set up and Run are disabled.
- **L5 · Run finished:**
  - Three tiles: Pockets worse and material (5) · Charge-offs above their share ($3.83M) · Tie-out checks (660 / 660, `POSITIVE 1E7A47`).
  - Any open data question in a bordered box.
  - Buttons: Run again · **Open at Start here**.

---

## Workbook tabs (10)

### 1. Start here (red tab)
- **Where things stand:** four tiles, each value a formula.
  - Answers still needed · Columns to confirm · Odd values to answer (crimson when above 0) · Changes waiting for a Run.
  - Waiting count: `=COUNTIF(Control!Status,"↻ Waiting for a Run")`. Its tile gets a red top border when above 0.
- **Pending banner** (conditional): `F7DEDE`, "↻ 1 change is waiting for a Run. Fewest losses…: 10 → 15 (Control C17). The result tabs still show the last Run…"
- **What the last Run found:** four tiles, the top-5 "Largest, worse and material" table (charge-offs), then a link to Pockets.
- **The tabs:** three groups (You answer / Results / Record), each with a 4 px top rule in its tab colour.

### 2. Control (red tab)
Replaces Control and absorbs Materiality.
- Legend row showing the three input styles.
- **Block A · Changes now** (INK band, red bottom rule). Columns: Setting · Your answer · Comes to · Last Run used.
  - Worse at 1.25× · Better at 0.80× · Profit counts when "Its own test says so" · How sure 95% · Materiality "1% of the book's charge-offs" → $107,354 · Judged against "The rest of its band".
  - Answers are data-validation dropdowns. Result tabs read these cells **with formulas**, so readings, dollars, colours and verdicts update live. Row order does not.
- **Block B · ↻ Needs a Run** (SLATE band, STONE bottom rule). Columns: Setting · Your answer · Last Run used · Status.
  - Fewest loans for the usual test 30 · Fewest losses before a loss rate is tested 10 · Bands per number column 5 · Where band edges fall · Catch a real gap 80% · Many tests at once "Hold down false finds".
  - Status formula: `=IF(answer<>last,"↻ Waiting for a Run","Same as last Run")`. The waiting state gets conditional format `F7DEDE` with crimson bold.
- **Block C · Chosen in the launcher (read-only):** `MIST` band. What you're running · Cut into bands · Segment by · Split every pocket by.
- **Right panel · What each materiality level keeps** (live, formulas over the pocket data): Level · Dollars · Pockets · Of excess, for 0.5 / 1 / 2 / 5 / 10%. The row in use is bold on CANVAS with ◂. A note gives the same level in other units.

### 3. Columns (red tab)
Merges Columns, Odd values and Learned.
- "Checked every column? [Yes ▾]" at C3. Run is blocked until it's Yes.
- One row per extract column: Column · Samples · What it is ↻ (dropdown) · Why we think so · Blank · Odd values · Treat as ↻ (Real / Missing; `F7DEDE` while unanswered) · Band edges ↻ ("620; 680; 740" or "every 20"; blank means Control's default) · Remembered ↻ ("Yes · 1 Run · Forget? No").
- Below: **Add a column: one divided by another**, with input rows Name ↻ · Top · Bottom.

### 4. Look (red tab)
- Per number column: a stats block (Loans, Blank, likely code with count and %, Smallest, Median, Largest) and a native **column chart** of counts per step.
  - Bars `INK`; the two tail bars `STONE`.
  - A likely-code value (FICO −9999) gets its **own `CC0000` bar left of the chart**, so it doesn't flatten the rest.
  - The **current band edges from Columns** are drawn as red dashed vertical lines. Build them as an extra series fed by formulas, so they follow Columns live.
- A scatter of the split column against each band column (a random 2,000 loans, the same every Run), with the correlation in the stats block.

### 5. Pockets (black tab)
Merges Where it bleeds and Three-way.
- Lines-in-use tiles: Worse at · Better at · How sure · Material at (unit follows the measure) · Judged against.
- **Three slicers** on one Excel Table:
  - **Measure:** Bad loans · Bad dollars · Charge-offs · Kept after losses · Earned before losses.
  - **Pockets:** Two-way · Split by REV_DEBT.
  - **Show:** All · Worse and material · Worse or not sure.
  - A caption beside them: "N worse and material · N worse · N shown".
- **Columns (two-way):** # · Band · Segment · Loans · This pocket · Rest of band · × rest of band (or Gap in pts for the profit measures) · Excess (Bad loans above share / Dollars above share / Dollars short of band) · Worse? · Chance it's luck · Material? · Could have caught.
- **Split view** adds "REV_DEBT half" after Segment and "Holds FICO fixed?" at the end.
  - Rows from grids that don't hold FICO fixed sort last, in `SLATE` text with no verdict fill, and read "No: may be mostly FICO" in crimson.
- Material? is a live formula: `=IF([@Excess]>=Control!$D$11,"Yes","No")`. Worse? combines Control's line, the confidence level and the stored chance.
- Rows are sorted by excess as of the last Run.

### 6. Paid, cost, kept (black tab)
Replaces Losses vs revenue.
- A grid dropdown (one grid at a time).
- Column groups with a 2 px INK underline: **Paid us · gap vs band** (Gap pts, Dollars) · **Cost us · charge-offs** (× band, Dollars) · **Kept · gap vs band** (Gap pts, Dollars) · Together.
- Cell shading per pair: `F7DEDE` when worse and real, `EAF6EE` when better and real, none when it could be luck.
- **Together** (bold): Priced for it (green) · Net drain (crimson) · Strong (green) · Safe but idle · Earns less, not from losses.
- Native scatter chart: x = charge-off multiple (log scale, 0.1× to 10×), y = profit gap in points (−30 to +20). Dashed lines at 1× and 0. Corner labels. Named dots for any pocket with a Together verdict. "As of the last Run."

### 7. Grids (black tab)
Absorbs Prevalence.
- Two dropdowns, **Grid** and **Measure**. Four blocks are filled by `INDEX/MATCH` (or `FILTER`) formulas: **Rate** · **vs the book** · **vs rest of band** · **Loans** (count, shaded by share of the grid in white→`STONE`; no red or green, because it isn't a test).
- Heat: 3-colour scale `HEAT_GOOD BBD3BD` (0.5×) → `HEAT_MID F4F1EC` (1×) → `HEAT_BAD E0A6A6` (2×), deepening to `CF7777` from 2× up.
- A blank cell means fewer losses than the minimum.

### 8. Split (black tab)
- Grid dropdown, plus a green "Holds FICO fixed" chip.
- Summary table: Measure · Pockets · High half worse in · High vs low, all · Range (95% sure) · Chance it's luck. The pooled ratio is heat-filled.
- The line "Same in every pocket? Bad loans: no sign the gap differs between pockets." sits under the table.
- Two side-by-side grids:
  - **Bad loans, high vs low** per pocket. Real gaps are heat-filled; could-be-luck values show in brackets, unshaded.
  - **Chance it's luck**, bold at 5% or less.

### 9. New variables (black tab, new)
Results for Test new variables mode.
- Tiles: Outcome · Candidates · Held fixed · Loans (5,600 found · 2,400 held back) · Material at (live).
- Column groups:
  - **Found** (Gap, Luck; in grey, because it's where the idea came from)
  - **Confirmed · held back** (Gap, Luck) · Holds up?
  - **Confirmed, FICO held fixed** (Gap, Luck) · Still holds?
  - Then: Excess $ · Material? · In words.
- Holds up? and Still holds?: Yes shows `EAF6EE` with `POSITIVE` bold.
- Bar chart: three bars per candidate (Found `STONE`, Confirmed `INK`, FICO held fixed `CC0000`), with a dashed red line at 1.25×.
- If a saved shortlist file was confirmed, hide the Found columns and name the file on Record.

### 10. Record (grey tab)
Merges Check and Log.
- A **2 × 3 grid of paired sections**: This Run | Settings, then Does it add up | Tests used, then Left out | Every Run, newest first.
- Every section has the same 32 px `ONYX 16130F` header band, a `CANVAS` sub-header naming its columns, 230 px label columns, rows of equal height, and a 2 px ONYX bottom rule.
- Settings has three columns: Setting · In use now · Last Run used. A changed value is shaded `F7DEDE`.

---

## Excel build notes
- **Slicers:** Pockets is one Excel Table holding every pocket for every measure and kind, with Measure and Kind columns; the slicers filter it. openpyxl can't write slicers. Either use XlsxWriter, or ship a template workbook with the slicers already defined and fill the table.
- **Live vs Run:** anything under "Changes now" must be formula-driven on the result tabs: flags, dollars, conditional formats, Material?. Anything under "Needs a Run" is computed in Python. Store "Last Run used" values in a hidden sheet (or `_config`) so the Status formulas can compare.
- **Grouping:** `ws.row_dimensions.group(3, 10, outline_level=1, hidden=False)` for each method note.
- **Data validation:** every Control answer, "What it is", "Treat as" and "Checked every column?".
- **Column widths:** fit the longest value and the header (use the mock's pixel widths ÷ 7), and turn wrap off in result tables.
- **Link targets for the launcher:** Open at cell uses the sheet and cell address the refusal list reports.

## Design tokens
| Token | Hex | Use |
|---|---|---|
| INK | 0A0908 | Title bands, column headers, selected slicer |
| ONYX / INK_TEXT | 16130F | Record section bands, data text |
| KEY_RED | CC0000 | Accent rules, KPI top borders, red tabs, launcher primary |
| CRIMSON | 960019 | Alert text, "Worse? Yes" text |
| PAPER | FFFFFF | Sheet background |
| CANVAS | F4F1EC | Tiles, method notes, sub-headers, Changes-now inputs, "Not sure" |
| MIST | E4DFD5 | Material? Yes, dividers, read-only band |
| STONE | B9B4AC | Disabled, tail bars, faint rules, grey tabs |
| SLATE | 57534B | Secondary text, Needs-a-Run band |
| ALERT_FG | F7DEDE | Worse fill, needs-an-answer, waiting-for-Run |
| POSITIVE / bg | 1E7A47 / EAF6EE | Better, holds up, tie-outs |
| HEAT_GOOD / MID / BAD / BAD2 | BBD3BD / F4F1EC / E0A6A6 / CF7777 | Heat scale |

**Type:**
- Excel: Arial bold 16 (titles), Arial bold 9–10 (headers), Calibri 11 (data), Calibri 9 (notes and captions).
- Launcher: Arial 12–18.
- Row divider: 1 px `EFEBE4`.

## Files
- `Origination Cube Redesign.dc.html`: the full design reference, with launcher L1–L5 and all 10 workbook tabs.
- `support.js`: the runtime the reference needs; keep it beside the HTML.
- `keybank_style.py`: KeyBank Excel tokens and openpyxl helpers. Build the workbook with these so it matches the other KeyBank workbooks.
- `STYLE_SPEC.md`: the KeyBank Excel style rules these tokens come from.
