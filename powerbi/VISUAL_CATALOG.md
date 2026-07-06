# KeyBank Credit-Risk Suite — Power BI Visual Catalog

A build sheet for reproducing the suite's dashboards in Power BI Desktop, in
KeyBank house style. Every workbook the suite ships already lands a **flat,
map-ready raw table**; Power BI reads that table and renders the same signal the
Excel dashboard shows — just with slicers, drill, and native maps the locked-down
Excel build can't use.

> **Theme first.** In Power BI Desktop: **View → Themes → Browse for themes →**
> `KeyBank_CreditRisk_Theme.json` (in this folder). Everything below assumes the
> theme is loaded — the heat ramp, the black title bands, the red accent rule,
> and the ALERT/WATCH/OK colors all come from it, so you never hand-pick a color.

---

## 0. The one design rule (so it still looks like KeyBank)

| Token | Hex | Where it goes in Power BI |
|---|---|---|
| INK (warm black) | `#0A0908` | visual **title** background band, table/matrix column headers |
| KEY_RED | `#CC0000` | the **accent rule** under a title; default bar/column/line color; ALERT |
| CRIMSON | `#960019` | ALERT **text**, hyperlink, "classified" series |
| CANVAS | `#F4F1EC` | page background, KPI-card fill, matrix banded row |
| SLATE | `#57534B` | secondary labels, axis text |
| INK_TEXT | `#16130F` | primary data text (never pure black) |
| POSITIVE | `#1E7A47` | improvement / "OK" text |
| Heat ramp | `#BBD3BD` → `#F4F1EC` → `#E0A6A6` | **all** conditional formatting: calm → mid → stress |

Rule of thumb, same as the workbooks: **black grounds, red leads sparingly,
neutrals breathe.** Red on a page means *look here* — an alert, not decoration.
The heat ramp is deliberately muted (not Power BI's default green/red) so a wall
of banks reads as a calm gradient, and only genuine stress pulls the eye.

**ALERT / WATCH / OK** — bind every status field to these three, everywhere:

| Status | Fill | Text |
|---|---|---|
| `ALERT` | `#E0A6A6` (HEAT_BAD) | `#960019` (CRIMSON), bold |
| `WATCH` | `#EFD7CF` (HEAT_WARM) | `#16130F` |
| `OK` | `#BBD3BD` (HEAT_GOOD) | `#1E7A47` (POSITIVE) |

---

## 1. Data model — how to point Power BI at a workbook

Each `.xlsm` lands its data in a fixed-anchor **raw block** (newest-first, so
rows never shift) plus a computed **watchlist/dashboard** block. For Power BI:

1. **Get data → Excel workbook →** pick the raw table (or the watchlist sheet's
   data range). Use the *table/named-range* if present, else the sheet range.
2. Keep the **key column** typed as **Text** (FIPS codes and CERTs have leading
   zeros — never let Power BI infer them as whole numbers).
3. One workbook = one query. If you want a single cross-template page, load each
   workbook as its own table and relate them on the shared key (state, or CERT).

Two geographic key shapes and two entity key shapes recur across the suite:

| Key | Shape | Templates | Power BI map field |
|---|---|---|---|
| **State** | USPS 2-letter abbrev (`Watchlist` col A `State`) | Macro | *Data category = State or Province*; Power BI resolves `CA`/`TX` natively |
| **County** | 5-digit county FIPS text (`Watchlist` col C `FIPS`) | CFPB mortgage, BLS LAUS | *Data category = County*; shape map: US counties TopoJSON keyed on FIPS |
| **Bank** | FDIC CERT + name | FDIC peer/competitor | matrix rows (no map) |
| **Company** | SEC CIK / ticker + name | EDGAR crit/class | matrix / bar (no map) |

> **State dashboards vs. state key.** In CFPB, the *watchlist* key is the
> 5-digit **county** FIPS; the `Dashboard_State` tab instead carries **2-digit
> state FIPS** and the National row is literally `-----`. Filter National out
> before mapping.

---

## 2. Page-by-page build

Ordered by "wow per minute of build." The first three are the ones worth doing
first — they're what Excel physically cannot render.

### 2.1 Macro Early-Warning — **50-state stress choropleth** ⭐

The headline. A US state fill map shaded by each state's Sahm-style
unemployment gap, with the national early-warning signals beside it.

- **Visual:** *Filled map* (or *Shape map* → Map: `USA: states`).
- **Source:** `macro-early-warning-dashboard` → **`Watchlist`** tab. Columns:
  `State | UR gap | Claims YoY 4wk-MA | Coincident 3m chg | Rank | Status`.
- **Location:** `State` = **2-letter USPS abbreviation** (`CA`, `TX`, …) — set
  the column's **Data category → State or Province**; Power BI resolves the
  abbreviations directly, no name lookup needed.
- **Color saturation measure:** `UR gap` (the Sahm-style unemployment-rate gap =
  mean(latest 3) − min(prior 12)). Map to the diverging heat ramp — the theme
  already sets min `#BBD3BD` / center `#F4F1EC` / max `#E0A6A6`, so higher gap =
  warmer. (Swap in `Claims YoY 4wk-MA` or `Coincident 3m chg` for alternate lenses.)
- **Tooltip:** State, UR gap, Claims YoY, Coincident 3m chg, **Status**.
- **Status semantics (watchlist):** `ALERT` (gap ≥ band), `WATCH` (≥ 0.6×band),
  else **blank** — there is no literal `OK` on the macro watchlist, so a blank
  Status = calm. Bind blank → HEAT_GOOD if you want the calm states shaded.
- **Companion visuals on the same page:**
  - **KPI cards** (top strip): `# states ALERT`, `# states WATCH`, national Sahm
    indicator (`SAHMREALTIME`), yield-curve spread (`T10Y2Y`) latest — pulled from
    the `Dashboard_Conditions` / `Dashboard_Labor` tabs. Card fill CANVAS, number
    Arial 28 INK, category label SLATE 9 — theme handles it.
  - **Recession-shaded line charts** (national signals — see §3): yield curve
    (`T10Y2Y`/`T10Y3M`), initial claims (`ICSA`/`IC4WSA`), lending standards
    (`DRTSCILM`), high-yield spread (`BAMLH0A0HYM2`).
  - **Ranked bar** of the top-10 states by `UR gap` (bars KEY_RED, use the
    `Rank` column, data labels on).

**Why it lands:** Excel in the locked-down build can't draw a real choropleth;
this is the single biggest upgrade Power BI buys the analyst.

### 2.2 CFPB Mortgage — **county delinquency fill map** ⭐

- **Visual:** *Shape map* (US counties) or *Filled map* with county FIPS.
- **Source:** `cfpb-mortgage-monitor` → **`Watchlist`** tab. Columns:
  `County | State | FIPS | 30-89 latest | 30-89 dev 12m | 90+ latest |
  90+ rise streak | Status | Rank`.
- **Location:** `FIPS` = **5-digit county FIPS**, keep as **Text** (leading zeros
  are significant, e.g. `01003` Baldwin AL, `06037` Los Angeles CA, `48201`
  Harris TX) — Data category → County; add `County` + `State` as tooltip/hierarchy.
- **Color:** `90+ latest` (or `30-89 latest`), heat ramp. `90+ rise streak` makes
  a strong secondary lens — consecutive quarters of rising 90+ delinquency.
- **Companion:** matrix (`County` × {`30-89 latest`, `90+ latest`, `Status`}) with
  the §4 conditional format; KPI cards `# counties ALERT`, national `d90` rate
  (the `nat_d90` row from `Raw_CFPB`).
- **Filter:** drop the National (`FIPS = -----`) and any `Status` of `OFF`,
  `REFUSED…`, `SUPPRESSED…`, or `(not yet run)` before mapping — those are the
  gate's own bookkeeping rows, not counties to shade.
- **Drill:** `State` → `County` hierarchy on the map for footprint focus.

### 2.3 FDIC Peer & Competitor — **bank × metric heat matrix** ⭐

The peer grid, exactly as the Excel Peer_Grid tab reads, but with live
conditional formatting and slicers for peer-set toggling.

- **Source:** `fdic-peer-monitor` (`Bank_Peer_Monitor.xlsm`). Four dashboard tabs,
  each a peer grid with header `Bank | CERT | Group | <metric labels…>` and a
  `PEER MEDIAN` row at the foot. Load whichever lane(s) you want to render:
  - `Dashboard_AssetQuality` — `NCLNLSR` (Noncurrent %), `NTLNLSQR` (NCO % q),
    `PD3089R` (30-89 PD %), `LNATRESR` (ALLL/Loans %), `LNRESNCR` (Coverage %),
    `TEXAS` (Texas %)
  - `Dashboard_Capital_Earnings` — `RBC1AAJ` (T1 Leverage), `RBCRWAJ` (Total RBC),
    `EQV` (Equity/Assets), `ROAQ` (ROA q), `NIMY` (NIM), `EEFFR` (Efficiency)
  - `Dashboard_Funding_Concentration` — `LNDEPR` (Loans/Dep %), `BRODEPR`
    (Brokered %), `CRECONR` (CRE Conc %), `UNINSDEPR` (Uninsured Dep %),
    `UNRLZCAPR` (Unrlz Loss/Cap %), `FHLBASSR` (FHLB/Assets %)
- **Visual:** *Matrix*.
  - **Rows:** `Bank` (keep `CERT` as a tooltip/hidden field — it's column 2, the
    real entity key). `Group` (`peer` / `counterparty` / `self`) makes a natural
    row group or slicer; **KeyBank NA (CERT 17534) is the `self` row** — highlight it.
  - **Values:** the lane's metric columns above.
- **Conditional formatting (per value column): Format → Cell elements →
  Background color → Rules**, or Color scale on the diverging heat ramp.
  **Direction matters** — most metrics are "above is worse," but the capital/
  earnings/coverage ones are "below is worse" (`RBC1AAJ`, `RBCRWAJ`, `EQV`,
  `ROAQ`, `NIMY`, `LNATRESR`, `LNRESNCR`): **reverse** the ramp for those.
  Bands come straight from `series_seed.py THRESHOLDS` — see §4.
- **Slicer:** `Group` (peer vs counterparty vs self) from the `[PEERS]` config,
  so the analyst flips between the reg peer group and the counterparty set.
- **Companion cards:** `# banks ALERT` (from the `Watchlist` tab `Status`),
  peer-median for the headline metric, count of banks above the CRE-concentration
  guidance line (`CRECONR ≥ 300`).

**Watchlist tab** — `Bank | CERT | Group | Texas | ALERT flags | WATCH flags |
Rank | Status`. This is the ranked one-line-per-bank roll-up; drive the
`# ALERT`/`# WATCH` KPI cards and a ranked bar (by `Rank` / `ALERT flags`) off it.
Status strings: `ALERT` / `WATCH` / `OK` / `OFF` / `REFUSED…` / blank.

**Consumer + commercial competitor pack** (`Dashboard_LoanBook`, same workbook):
two slot-anchored bands, banks as rows, same `Bank | CERT | Group | <labels>` shape.
- **CONSUMER band** by loan class — Card / Auto / OthCons / Resi 1-4 / HELOC,
  each as 30-89 (`P3…R`) / 90+ (`P9…R`) / nonaccrual (`NA…R`) / annualized NCO
  (`NT…QR`). E.g. `P3CRCDR`, `P9CRCDR`, `NACRCDR`, `NTCRCDQR` for cards.
- **COMMERCIAL floor** by class — Constr / CRE / Multifamily / C&I, same four
  measures (`P3RECONSR`…`NTCIQR`).
- **Visual:** *Clustered bar* or a second matrix — Bank (rows) × class × measure.
  Uniform interagency framing; bars KEY_RED, the NCO (`NT…QR`) series CRIMSON.

### 2.4 EDGAR Criticized / Classified — **stacked criticized bar**

- **Source:** `edgar-crit-class-tracker` (`Crit_Class_Tracker.xlsm`).
- **Stacked bar — one column per bank, segments by grade.** The per-grade dollars
  live in the **member-fact audit rows** inside `Raw_EDGAR` (`FACT_COLS` =
  `period, class_qname, class, member_qname, grade, value_usd, tag, accession`).
  Load those rows, filter to the latest `period`, put `Bank` on the axis,
  `value_usd` as value, and **`grade` as the legend**.
  - Segment colors, calm→severe: `special_mention` `#EFD7CF` →
    `substandard` `#E0A6A6` → `doubtful` `#C97B7B` → `loss` `#960019`. All
    in-family with the theme. (Exclude `grade = pass`, `ignore`, `unmapped` — the
    last is denominator-only; `ignore` is the filer's own `CriticizedMember`
    subtotal, double-counting if kept.)
- **Peer grid — `Dashboard_Criticized`:** `Bank | CIK | Ticker | Family |
  Criticized % | dQoQ pp | dYoY pp | Crit growth % | SM % | Classified % | Status`.
  Render as a matrix with the §4 heat on `Criticized %` / `Classified %` / `SM %`
  (all "above is worse"). **KeyCorp (CIK 91576, ticker KEY) is the self row.**
  `Family` = the filer's disclosure dialect (`grades_full` / `criticized_only` /
  `ig_nig`) — a `criticized_only` filer legitimately has no SM/Sub/Doubtful split,
  so a blank SM% there is `N/A`, not a gap.
- **Ratio trend:** *Line/column combo* — `criticized_ratio` (`CRIT_RATIO` in
  `RAW_METRIC_COLS`) per bank across filed quarters (`period` axis).
- **Events table — `Dashboard_Mix_Events`** carries `8-K 2.04 | 8-K 2.06 |
  8-K 4.02 | 8-K 1.03 | 8-K 2.02 | Latest 8-K`; the raw feed is the `EVENT_COLS`
  rows (`date, item, form, accession, url`) in `Raw_EDGAR`. Show a chronological
  strip; the **auto-WATCH** items are `2.04` (debt acceleration), `4.02`
  (non-reliance), `1.03` (bankruptcy) — flag those CRIMSON, hyperlink `url`.
- **Cards:** `# filers ALERT` (Watchlist `Status`), `# with rising criticized QoQ`
  (`dQoQ pp > 0`), largest `Classified %`.

### 2.5 National credit dashboards — **recession-shaded trends**

Two templates, both national-only by design (their watchlist lanes structurally
refuse national aggregates and sit as gated geo placeholders), so these pages are
**all time-series, no map**. Both key on **Series ID**.

**FRED Credit-Risk Dashboard** (`fred-credit-risk-dashboard`, three lanes):
- Tabs `Dashboard_Consumer` / `Dashboard_Commercial` / `Dashboard_Price`, columns
  `Tier | Category | Series ID | Title | Latest | Prior | YoY % | Z-score (8) |
  Trend (8q) | Flag`. **Flag is z-score based** (`⚠ ALERT` when the 8-period
  z-score ≥ the `_config` band, default 1.0) — there's no WATCH tier here, so bind
  the card/point color to blank-vs-`⚠ ALERT`, and use the **`Z-score (8)`** column
  as a diverging heat measure (the standardized-stress lens is the whole point).
- **Visual:** *Line chart* per family with §3 recession shading — consumer
  delinquency (`DRCCLACBS` card, `DRSFRMACBS` SF mortgage), C&I (`DRBLACBS`) and
  CRE (`DRCRELEXFACBS`) delinquency, charge-off rates (`CORCCACBS`, `CORBLACBS`),
  home-price index (`CSUSHPINSA`). Raw tabs: `Raw_Consumer/Commercial/Price`.

**NY Fed Household Debt & Credit** (`bureau-credit-risk-dashboard`):
- Tabs `Dashboard_Balances` / `Dashboard_Delinquency` / `Dashboard_Originations`,
  columns `Category | Series ID | Title | Latest | Prior | Headline | Trend (8) |
  Status` (`Status` = `OK`/`WATCH`/`ALERT`, fixed bands). Raw tab `Raw_HHDC`.
- **Visual:** *Line chart* — 90+ delinquency by product (`hhdc_card_90plus`,
  `hhdc_auto_90plus`, `hhdc_mortgage_90plus`), flow-to-delinquency
  (`hhdc_flow_to_30`, `hhdc_flow_to_90`), and a stacked **balances** area
  (`hhdc_mortgage_balance`, `hhdc_auto_balance`, `hhdc_card_balance`, …) for the
  debt-composition story.

- **Common:** *Small multiples* for the whole indicator wall on one page; **cards**
  showing latest vs prior for each headline rate, colored by direction. Both feeds
  are **quarterly**, so recession shading uses quarter-keyed NBER flags.

---

## 3. Recession shading (reusable on every line chart)

Power BI has no native "shaded recession bands," but the effect is one of:

- **Preferred — shading measure:** add an NBER recession flag (0/1 by date) as a
  column in the model (a tiny `recession` lookup table keyed on month). Drop a
  second **area** series bound to `flag * [axis max]` behind the line, filled
  MIST `#E4DFD5` at ~60% transparency. It renders as grey bands under the line.
- **Simpler — analytics line/band:** for a single known window, use the
  **Analytics pane → Shading/▚ band** between two constant dates.

Line color KEY_RED for the primary series; comparison/prior series STONE
`#B9B4AC`. Axis and gridlines are already SLATE/`#E7E2D8` from the theme.

---

## 4. Conditional-format bands (bind to the workbook's own thresholds)

The workbooks compute `Status` (ALERT/WATCH/OK) themselves — **prefer binding
color to that `Status` field** (Format by → Field value, or Rules on the string)
rather than re-deriving bands in Power BI. That keeps Power BI honest to the
tie-out: the color you see is the color the workbook computed.

If you *do* want numeric rules on a raw value, mirror the calibrated bands from
`fdic-peer-monitor/series_seed.py THRESHOLDS` (desk-calibrated against live
data). Direction matters — most are "above is worse," capital is "below is worse":

| Metric | WATCH ≥ | ALERT ≥ | Direction |
|---|---|---|---|
| `TEXAS` (Texas ratio) | 25 | 50 | above |
| `NCLNLSR` (noncurrent/loans) | 1.5 | 3.0 | above |
| `UNINSDEPR` (uninsured dep. ratio) | 60 | 75 | above |
| `NTCRCDQR` (credit-card DQ) | 6.0 | 8.0 | above |
| `NARENRESR` / `NARECONSR` (RE nonaccrual) | 4.0 | 7.0 | above |
| `CRECONR` (CRE concentration) | 250 | 300 | above |
| `RBC1AAJ` (tier-1 leverage) | 6.0 | 5.0 | **below** |

> These are the *illustrative desk* bands; the workbook is the source of truth
> and the analyst re-tunes them in `_config`. Don't fork the numbers into Power
> BI as gospel — bind to `Status` where you can.

---

## 5. Cross-template "Book of the Portfolio" (optional one-pager)

If the analyst wants a single command page:

- **Top strip — KPI cards** pulling each workbook's headline count:
  states ALERT (macro), counties ALERT (CFPB), peer banks ALERT (FDIC),
  filers with rising criticized (EDGAR).
- **Left — the state choropleth** (§2.1) as the geographic anchor.
- **Right — the FDIC peer matrix** (§2.3) as the entity anchor.
- **Bottom — a recession-shaded national trend** (§2.5) for the macro backdrop.
- One **date slicer** and one **peer-set slicer** wired across the page.

Everything on it inherits the theme, so it reads as one KeyBank artifact.

---

## 6. Files in this folder

| File | What it is |
|---|---|
| `KeyBank_CreditRisk_Theme.json` | Import into Power BI (View → Themes → Browse). The palette, fonts, heat ramp, black title bands, and ALERT/WATCH/OK colors — all from `keybank_style.py`. |
| `VISUAL_CATALOG.md` | This build sheet. |
| `keybank_palette_preview.html` | Open in a browser: swatch card + mock choropleth / matrix / KPI strip / stacked-criticized bar, so you can see the look before building. |

**Provenance:** colors, fonts, and heat semantics are lifted verbatim from
`fdic-peer-monitor/keybank_style.py` (the suite's single source of style). Metric
codes and threshold bands trace to `fdic-peer-monitor/PROVENANCE_MAP_FDIC.md` and
`series_seed.py`. No licensed data is embedded here — this folder is style +
build instructions only.
