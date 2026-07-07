# Demo

Two ways to see stock-helper working.

## Instant, zero-network (synthetic data)

```
./scripts/demo.sh
```

Seeds a **synthetic** 16-company universe (invented — *not real data*) across
technology, banking, consumer, industrials, and healthcare, spanning archetypes
(quality compounders, deep value, distressed, an earnings manipulator), plus
fake price caches so the full valuation surface renders. Then opens the UI.

`scripts/demo_seed.py` builds the universe; `scripts/demo_screenshot.py` drives
the real Streamlit app with Playwright and captures `demo/screenshots/`.

The screenshots below are the actual app rendered on that synthetic universe:
- `screenshots/01_screener.png` — the cross-sectional screener (value-vs-quality
  scatter, ranked table, flags).
- `screenshots/02_valuation.png` — a company valuation (fair-value bar with an
  uncertainty-scaled margin-of-safety band, live DCF sliders, reverse-DCF).

## Real data (your machine)

```
cp .env.example .env          # set SEC_USER_AGENT (and optionally FRED_API_KEY)
uv run stock-helper init
uv run stock-helper fetch-universe --top 750   # ~6 min; builds industry norms
uv run stock-helper-ui
```

A universe of ~500–800 names is what turns the sector-neutral z-scores and
peer-relative multiples into real **industry norms**. It is resumable and
cached, so it doubles as a weekly refresh.
