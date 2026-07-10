# Example outputs

These files show the tool's output **format** for a single SIC code (5140,
food distributors) across revenue tiers.

> ⚠️ **SYNTHETIC DATA — not real SEC filings.** The companies and numbers here
> are deterministically fabricated (see `generate_examples.py`) purely to
> illustrate layout and the cross-tier story. They are *not* a real industry
> benchmark. Run the tool against live EDGAR for actual figures.

| File | What it is |
|---|---|
| `sample_food_dist.summary.md` | The readable per-tier summary: rosters, current vs through-cycle percentile tables, volatility, the 2020 shock, the cross-tier size trend, caveats, and a LOW CONFIDENCE flag on the thin tier. |
| `sample_food_dist.csv` | The auditable raw feed: one row per company per fiscal year with every line item, reconstructed EBITDA (+ method), assigned tier, and all metrics. |

What the example is designed to show:

- **Cross-tier trend** — median Total debt/EBITDA *rises* (~3.6x → ~5.3x) and
  EBITDA/interest and margins *fall* as company size drops. That trend is the
  point: extrapolate it below the smallest public tier toward a private name.
- **2020 shock** — a visible COVID dip (leverage up ~50%, margins down ~1.2pp).
- **LOW CONFIDENCE** — the 250M-1B tier has too few names and is flagged.
- **Roster** — each tier lists its constituent companies.

Regenerate with:

```bash
python examples/generate_examples.py
```
