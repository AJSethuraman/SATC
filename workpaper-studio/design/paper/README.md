# Workpaper design package

Two things are designed here, and they have different status.

## 1. The generated workbook ("Paper") — ready to build from
Open `Paper System.html`. It has every screen type, every block, every cell state and a **Build sheet** frame with exact fonts, sizes, colors, fills, borders, row heights, column widths, number formats, conditional formats, validation and protection. Everything is plain Excel cell formatting: no images, shapes or macros.

Decisions that are settled:
- Surface: **Soft stone** `#E4E0D9`. Card = ground +7, field +19, computed −7, not applicable −16, rule −17, field edge −62 (per RGB channel).
- Type: **Arial**. Static text 10–11 pt, headers 10 pt bold caps, results 13 pt bold. Row heights are in the Build sheet.
- Color families (one hue, three shades: dark for band and static text, a mid shade for header bars, light): Navy, Forest, Burgundy, Teal, Plum, Bronze, Graphite. Chosen per tool. Details in `Paper Color Schemes.html`.
- Input text is black. Meaning colors (complete, missing, error) are fixed and never follow the family.
- Value states are distinct: missing, zero, not applicable, excluded, not calculated, locked, error. An incomplete calculation reads **Not calculated** and a missing limit reads **Not tested: limit not confirmed**. Never 0, never a pass.
- Spelling is American English throughout.

## 2. The Studio (tool launcher) — a flow prototype, not final
`Workpaper Studio.html` shows the intended flow: Describe the need, Shape, Look, Check and publish. It uses SAT-C branding (no color schemes). It is interactive but several parts are stand-ins, listed below.

## Known gaps (do not treat as designed)
- Studio: "Download workbook" is a placeholder; no file is generated.
- Studio: "Start from a template" and "copy" options on the old home card were replaced by the Describe screen; only the Describe flow exists.
- Studio: Shape edits update the preview, but list and limit editing (the Lists and limits step) was dropped from the new flow and needs designing again.
- The Paper System page shows the framework, lists, settings and release-check screens in the family dark shade only; the Build sheet lists every style.
- Dusk (dark) and a high-contrast scheme were explored and removed because the surface was fixed. They can come back as separate modes.
- Spacer rows and columns (3 pt, card color) between fields are described in the Build sheet but not yet tested in a real workbook. Build one screen in Excel first and check the field gaps and bevel borders before generating everything.
- The wordmark in the Studio is text plus a gold square, not the logo SVG.

## Files
- `Paper System.html` — screens, blocks, states, Build sheet
- `Paper Color Schemes.html` — family and surface picker with in-progress vs ready comparison
- `Workpaper Studio.html`, `Workpaper Preview.html` — launcher prototype and its live preview
- `workpaper/` — the scripts that render the screens (`wp-tokens.js`, `wp-render.js`, `wp-screens.js`, `wp-recon2.js`, `wp-generic.js`, `wp-themes*.js`)
