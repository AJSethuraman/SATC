# UI design notes — valuation & screener

Concrete, borrowed-from-the-best design moves for the Streamlit + Plotly UI.
Derived from how SimplyWall.st, GuruFocus, Morningstar, Koyfin/TIKR present
fundamentals. Applied as a refinement over the built UI. Honest framing is
load-bearing: nothing may read as a buy/sell signal.

## The moves (prioritized)

1. **Fair-value bar, not a gauge.** Horizontal bar 0 → ~2× fair value, a solid
   vertical line at fair value, a distinct marker (▲/◆) at current price, and a
   shaded **margin-of-safety band** so "cheap" is a *zone*, not a point.
   (SimplyWall.st). Gauges imply a needle pointing at a recommendation — avoid.
2. **MoS band width scales with uncertainty** (Morningstar ladder: low 20% →
   high 40% → very-high 50% → extreme 75%). Encoding confidence as band width is
   the strongest "honest, not a signal" device. Base uncertainty on data
   coverage + terminal-value weight + FCF volatility.
3. **Headline 0–100 quality score with its component bars always shown beneath**
   (GuruFocus GF-Score). Never a lone score — show the parts so the user sees why.
4. **Small radar as an identity mark only; horizontal bars are authoritative.**
   Radar area is misleading (scales with the square of values, depends on axis
   order). Never let users compare companies by blob size.
5. **Expandable pass/fail checklists under each pillar** (green tick / grey dash)
   — turns an opaque score into an auditable trail. We already have the per-test
   detail (Piotroski 9, Beneish indices) — surface it in expanders.
6. **Blue/teal ↔ amber diverging palette for cheap↔expensive**, not red/green.
   Colorblind-safe and breaks the "green = buy" reflex; reads as informational.
7. **Saturated red only for true distress** (e.g. Altman distress zone) so red
   stays rare and meaningful; single-hue sequential ramp for the rest of risk.
8. **Redundant encoding:** always pair color with a text/position label; show a
   legend on every heat/ramp. Survives grayscale + colorblindness.
9. **In-cell mini-bars for scores in the screener table** (Koyfin) so a column
   scans as a tiny bar chart.
10. **Light diverging heat on ratio/score columns only (10–20% opacity), never on
    name/ticker columns.** Density without a rainbow.
11. **Value-vs-Quality 2×2 scatter as the screener hero.** x = valuation
    (cheap→expensive), y = quality; quadrant lines at medians; dots sized by
    market cap; faint quadrant labels ("Bargains / Quality at a price / Value
    traps / Avoid"). A whole universe in one honest glance.
12. **Compact flag chips (2–3 max per row)**, muted palette, not prose.
13. **"Warning signs / Good signs" panel with three neutral severity tiers**
    (info-grey / caution-amber / elevated-rust), each naming the model + threshold
    + one plain-language why. Red flags *cluster* — group them; the panel is the
    signal, never a single flag (GuruFocus).
14. **Frame every forensic metric as "model-based *risk*," name the model**
    (Beneish/Altman/Ohlson/Zmijewski/Montier), and keep a standing "research, not
    advice, not an allegation of wrongdoing" disclaimer near the panel.
15. **Summary-first company page, cards grouped by plain-English question:**
    "Is it cheap?" (valuation) · "Is it good?" (quality) · "Is it safe?"
    (distress/forensic) · "Will it grow?" (reverse-DCF / trend). Narrative
    grouping is why SimplyWall.st feels calm.
16. **One accent color and one primary visual per card**; details in
    expanders/tabs. The core calm-vs-cluttered lever.
17. **`font-variant-numeric: tabular-nums`, right-aligned numbers, fixed decimals,
    units in headers.** Highest-ROI polish detail for a finance UI.
18. **Deliberate empty/loading states + "data as of <date>" stamps**; "—" for
    genuinely missing (distinct from 0); never fabricate precision.

## Palette (colorblind-safe, calm on navy/white)

- Valuation ramp (cheap→expensive): teal `#0f766e` → neutral `#8a93a3` → amber `#b45309`.
- Distress: pale `#fdf3dc` → rust `#9a3412`; saturated red `#b91c1c` reserved for the distress zone only.
- Keep fills low-chroma; saturate only the single most important marker/flag on screen.

Sources: SimplyWall.st model repo & valuation/snowflake help; GuruFocus GF-Score/
GF-Value tutorials; Morningstar uncertainty→MoS methodology; Koyfin/TIKR screener
density; Tableau/ColorBrewer colorblind guidance; tabular-figures typography guides.
