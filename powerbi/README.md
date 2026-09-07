# powerbi/ — KeyBank-themed Power BI pack for the credit-risk suite

KeyBank-branded Power BI visuals for the six credit-risk monitoring workbooks.
Style is lifted verbatim from `fdic-peer-monitor/keybank_style.py` (the suite's
single source of style), so a Power BI report and the `.xlsm` dashboards read as
one artifact.

| File | Use |
|---|---|
| **`KeyBank_CreditRisk_Theme.json`** | Import once: Power BI Desktop → **View → Themes → Browse for themes**. Sets the palette, Arial/Calibri fonts, black title bands + red accent rule, the brand-muted heat ramp, and ALERT/WATCH/OK colors. |
| **`VISUAL_CATALOG.md`** | The build sheet — per template, which visual, which workbook tab, exact column/field names, map bindings, and conditional-format bands. Start here. |
| **`keybank_palette_preview.html`** | Open in a browser to see the look before building — KPI strip, state tile map, peer heat matrix, criticized stacked bar, recession-shaded line, and the palette. No live/licensed data. |

## The 30-second version

1. Import the theme.
2. **Get data → Excel workbook →** point at a suite `.xlsm`; pick the `Watchlist`
   (or dashboard) tab. Keep key columns (**FIPS / CERT / CIK / State**) as **Text**.
3. Build the visual named in `VISUAL_CATALOG.md`. The three that Excel physically
   can't do — and so are worth doing first:
   - **State choropleth** (Macro) — 50-state stress, bind on 2-letter state.
   - **County fill map** (CFPB) — mortgage delinquency, bind on 5-digit FIPS.
   - **Peer heat matrix** (FDIC) — banks × metrics, KeyBank heat, `self` row pinned.

Colors, fonts, and heat semantics trace to `keybank_style.py`; metric codes and
threshold bands to `fdic-peer-monitor/PROVENANCE_MAP_FDIC.md` and each template's
`series_seed.py`. Style + build instructions only — no data ships in this folder.
