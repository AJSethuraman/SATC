# Roadmap

Phases are ordered by risk reduction: data correctness and lineage first, research
baselines second, ML/AI and intraday sophistication last. Ticks (✅) mark what
exists in the current version; everything else is planned.

A note on scope, adapted from the research brief: the brief describes a
production-grade, full-universe recommendation platform (CRSP security master,
SIP/TAQ cost calibration, vendor estimate/transcript overlays, walk-forward
validation with Deflated Sharpe controls). Those are the right *end-state*
benchmarks, but they are deliberately **not** MVP scope for a local-first tool.
The brief's non-negotiables that *do* apply from day one — point-in-time
timestamps, provenance, survivorship awareness in schema design, grounded
evidence, and "no performance claims until validated" — are baked into the data
model now so later phases don't require a rewrite.

## Phase 0 — Foundation ✅

- ✅ Repo skeleton with layered `src/stock_helper/` architecture
- ✅ Install path via `uv` / pip, single `pyproject.toml`
- ✅ Typed config (`pydantic-settings`) loading `.env`; no secrets in code
- ✅ SEC connector: rate-limited, cached, fair-access compliant
- ✅ Local SQLite database via SQLModel (engine swappable → DuckDB/Postgres later)
- ✅ Structured logging
- ✅ Offline test suite (fixtures, no network)
- ✅ Basic UI shell (Streamlit) + FastAPI skeleton

## Phase 1 — SEC Company Tear Sheet MVP ✅ (thin)

- ✅ Ticker → CIK lookup from SEC company_tickers.json
- ✅ Company submissions pull (filing history, SIC, identity)
- ✅ Company facts (XBRL) pull
- ✅ Filing metadata stored with accession, filed/accepted dates, links
- ✅ Basic facts normalization (us-gaap/dei → canonical metrics, annual series)
- ✅ Basic charts (metric trends; optional non-canonical price chart)
- ✅ First report output (Markdown tear sheet + ReportRun record)
- ⬜ Quarterly-series normalization (currently annual-first)
- ⬜ Fiscal-period alignment edge cases (52/53-week years, period changes)

## Phase 2 — Filing Text and Notes (partially started)

- ✅ Filing archive document download (two latest 10-Ks + latest 10-Q + latest 8-K, opt-in)
- ✅ Heuristic 10-K/10-Q section extraction (MD&A, Risk Factors) — best effort
- ✅ Evidence chunks with stable chunk IDs (`FilingSection`)
- ✅ 8-K item-code extraction (2.02 earnings, 5.02 departures, … with item labels)
- ✅ Searchable filing text (SQLite FTS5 with LIKE fallback; search box in UI)
- ⬜ Robust item-boundary detection across filer formatting variants
- ⬜ Note/footnote extraction (consider SEC Financial Statement & Notes datasets as audit backfill)

## Phase 3 — Rule-Based Signal Engine ✅ (v1) / ⬜ (v2)

- ✅ Signal definitions registry with category, formula, applicability
- ✅ Industry applicability enforcement (banks ≠ industrials)
- ✅ Trend logic (YoY, multi-year direction) and simple thresholds
- ✅ Scorecard output with metric, value, direction, interpretation, source,
  confidence, caveat
- ✅ Disclosure/risk-language signal (word rates from curated finance word lists +
  risk-factor novelty vs prior 10-K; low confidence by design)
- ⬜ Threshold calibration per industry bucket (currently conservative generic cuts)
- ⬜ Accrual quality refinements (balance-sheet vs cash-flow-statement approach)
- ⬜ Full Loughran-McDonald word lists (curated subset shipped)

## Phase 4 — Industry and Peer Context

- ✅ SIC → sector/industry bucket mapping (initial, coarse)
- ✅ Local-universe peer percentiles (same-bucket companies in your database,
  n and tickers always shown — explicitly not a market-wide peer set)
- ✅ Bank metric library from face XBRL: NIM proxy (NII / avg total assets),
  nonaccrual loans, gross charge-offs — honest `UNAVAILABLE` when table-only
- ⬜ NAICS cross-mapping
- ⬜ Market-wide sector distributions (needs a wider fetch universe)
- ⬜ CET1 and other filing-table-only bank metrics (needs table parsing)
- ⬜ Industry-specific report templates

## Phase 5 — Price / Macro Overlay

- ✅ Optional price connector (Stooq, non-canonical, off by default)
- ✅ Trailing P/E and P/S context (unscored by design; gated by ENABLE_PRICE_DATA)
- ✅ 12-1 momentum + 60-day volatility context (descriptive, low confidence)
- ⬜ EV-based multiples (need reliable debt/cash alignment)
- ⬜ FRED/ALFRED macro layer (vintage-aware from the start — never naive latest-revision joins)
- ⬜ Benchmark-relative context

## Phase 6 — AI Layer (design now, implement later)

Interfaces exist in `src/stock_helper/ai/interfaces.py` with no-op/rule-based
implementations. Hard rules when implemented:

- AI never invents metrics; it only summarizes/classifies retrieved evidence
- Every AI output must cite chunk IDs / source references
- "AI disabled" mode preserves all core functionality (this is today's default)

- ✅ Rule-based `RiskExtractor` (selects — never writes — high-density risk
  sentences from risk-factor chunks, citing chunk ids; shown in Filing Evidence)

Planned: Ollama client, local embeddings + vector store over `FilingSection`
chunks, grounded Q&A with a "show evidence" panel, configurable local model.

## Phase 7 — Backtesting and Validation

Nothing in the app claims predictive power until this phase is done.

- ✅ Point-in-time as-of replay in the facts normalizer
  (`build_annual_series(..., as_of=date)`: facts filed later are excluded and
  the originally-filed value wins over later restatements)
- ✅ As-of mode surfaced end to end: DB stores superseded facts, `build-report
  --as-of`, UI point-in-time toggle
- ✅ Signal history persistence (`signal-history`: scorecard replayed at each
  past 10-K/10-Q filing date → SignalHistory rows)
- ✅ Exploratory future-return labels (`--with-outcomes`: next-session entry,
  20/60/120 trading-day horizons from the non-canonical price source; labeled
  "not a backtest" everywhere)
- ⬜ Canonical (cost-aware, dividend-correct) outcome labels
- ⬜ Delisting/survivorship handling (requires a research-grade security master;
  the SEC ticker file alone is not a historical map)
- ⬜ Walk-forward validation with embargo; cost assumptions
- ⬜ Multiple-testing controls (Deflated Sharpe, Reality Check) before any claim
- ⬜ Hit-rate and limitation reporting inside the app

## Phase 8 — Production Hardening

- ⬜ Postgres/DuckDB option (SQLModel keeps this a connection-string change plus
  migration tooling)
- ⬜ Async ingestion, task queue, scheduled refresh
- ⬜ Richer monitoring: fetch lag, parse failure rate, mapping drift
- ⬜ Model registry (only if ML is added)
- ⬜ Exportable audit packet per report run
