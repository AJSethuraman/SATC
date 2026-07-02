# Data Sources

Canonical-first layering: official/primary sources are the record; anything else
is an overlay and labeled as such in the UI and reports.

## Active in v0.1

### 1. SEC ticker/CIK mapping
- **Endpoint:** `https://www.sec.gov/files/company_tickers.json`
- **Role:** convenience mapping ticker → CIK → name for *current* filers.
- **Caveats:** SEC does not guarantee accuracy/scope; updated periodically; **not a
  historical security master** (ticker reuse and renames are invisible here).
  Good enough for MVP lookup; Phase 7 backtesting must not rely on it.

### 2. SEC company submissions
- **Endpoint:** `https://data.sec.gov/submissions/CIK##########.json`
- **Role:** company identity (name, SIC, addresses, fiscal year end) and filing
  history (accessions, forms, filed/accepted dates, primary documents).
- **Freshness:** near filing-time; EDGAR indexes reconcile nightly. We store both
  `filed` and `acceptance` datetimes for point-in-time use.
- **Caveats:** only "recent" filings are inline (~1000); older history sits behind
  pagination files (deferred). Post-acceptance corrections can appear later.

### 3. SEC XBRL company facts
- **Endpoint:** `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`
- **Role:** primary structured financials (us-gaap + dei facts across filings).
- **Caveats:** values are **as filed**: custom tags, taxonomy drift across years,
  dimensional facts, restatements. Our normalization picks standard tags only and
  records which tag won; unmapped concepts simply yield "unavailable" metrics.

### 4. SEC filing archive documents
- **Endpoint:** `https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/…`
- **Role:** canonical raw filing text. v0.1 optionally downloads the latest
  10-K/10-Q primary document for heuristic MD&A/Risk-Factor extraction.
- **Caveats:** formatting varies wildly across filers/years; extraction is
  labeled best-effort with a parser version; Phase 2 hardens this.

### 5. Stooq daily prices (optional, OFF by default)
- **Endpoint:** `https://stooq.com/q/d/l/?s={symbol}.us&i=d`
- **Role:** context-only daily close charts. **Non-canonical** — no corporate-
  action guarantees, no survivorship handling, unofficial coverage.
- **Enabled by:** `ENABLE_PRICE_DATA=true`. Everywhere it appears, the UI/report
  labels it "non-canonical price data (Stooq)". Never used in signals in v0.1.

## Fair access & caching policy

- Declared `SEC_USER_AGENT` required (app refuses placeholder value).
- Client-side throttle: minimum interval between SEC requests (~6 req/s worst
  case, below SEC's 10 req/s guidance).
- All responses cached under `data/raw/sec/` with retrieval timestamps;
  re-fetches within `SEC_CACHE_TTL_HOURS` (default 24h) are served from disk.

## Planned (see ROADMAP.md)

| Source | Phase | Role | Notes |
|---|---|---|---|
| SEC Financial Statement & Notes datasets | 2 | Footnote backfill, parser QA | Monthly ZIPs; "as filed"; audit layer, not real-time |
| SEC full-text search | 2 | Ad-hoc discovery/debugging | Not a bulk ETL path |
| FRED / ALFRED | 5 | Macro overlay | ALFRED vintages mandatory for any backtest use — never naive latest-revision joins |
| Exchange corporate actions / research-grade history (e.g. CRSP) | 7 | Survivorship-bias-free backtesting, delistings, permanent IDs | Required before any performance claim; out of scope for a free local MVP |
| Analyst estimates / transcripts (FactSet, LSEG) | 4–6 | Estimate-revision and call-NLP overlays | Enterprise licensing; overlays only, never canonical |
| User notes | 6+ | First-party context | Schema placeholder exists (`UserNote`) |
