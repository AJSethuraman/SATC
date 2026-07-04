# Architecture

## Overview

stock-helper is a layered, local-first pipeline. Data moves strictly left to right;
each layer only imports from layers to its left (plus `core/` and `storage/`).

```
connectors → ingestion → parsing → normalization → features → signals → reports
     │                                                                      │
     └────────────────────────── storage (SQLite/SQLModel) ─────────────────┘
                                        │
                              ui (Streamlit) · api (FastAPI) · cli (Typer)
```

| Layer | Package | Responsibility |
|---|---|---|
| Core | `core/` | Typed config (pydantic-settings), structured logging, paths, constants |
| Connectors | `connectors/` | HTTP clients for external sources. Rate limiting, caching, User-Agent. **No business logic.** |
| Ingestion | `ingestion/` | Orchestrate raw pulls, persist raw payloads + DB rows (Company, Filing, CompanyFact) with provenance |
| Parsing | `parsing/` | Filing document → text → sections (MD&A, Risk Factors). Versioned parsers |
| Normalization | `normalization/` | Map raw XBRL concepts to canonical metrics; build clean annual series |
| Features | `features/` | Derived metrics: growth, margins, FCF, accrual proxy, leverage… |
| Industry | `industry/` | SIC → bucket mapping; metric applicability rules per bucket |
| Signals | `signals/` | Rule-based scorecard. Definitions + engine → SignalResult with evidence |
| Reports | `reports/` | Assemble report objects; render Markdown |
| AI | `ai/` | Interfaces only (TextSummarizer, RiskExtractor, …) with no-op impls. Phase 6 |
| Storage | `storage/` | SQLModel tables, engine/session management |
| API | `api/` | FastAPI read-only routes over stored data |
| UI | `ui/` | Streamlit app (Dashboard, Tear Sheet, Evidence, Scorecard) |
| CLI | `cli.py` | Typer entrypoint wiring the layers together |

## Key decisions

### Separation of fetching and computing

`fetch-sec` only acquires and stores. `build-report` only reads the store and
computes. This makes runs reproducible (recompute without refetching), keeps SEC
traffic low, and mirrors the raw-vs-derived split a future backtester needs.

### Point-in-time schema

Every fact row keeps `period_end` **and** `filed_date` (plus `accession`). A fact
is only "knowable" after its filed date. Derived metrics record which accessions
they were computed from. This is cheap now and impossible to retrofit later.

### Raw payloads are immutable

Raw SEC JSON/HTML is cached under `data/raw/sec/` keyed by URL, with retrieval
timestamps. Normalization can be re-run with a newer parser against the same raw
bytes; `parser_version` fields on derived rows record which version produced them.

### Canonical metrics vs raw facts

`CompanyFact` stores selected raw XBRL facts nearly as-filed. `normalization/`
maps candidate tag lists (e.g. `Revenues` → `RevenueFromContractWithCustomer…` →
`SalesRevenueNet`) to one canonical metric each, choosing the candidate with the
best annual coverage and recording the winning tag. `FinancialMetric` stores the
derived values with formula id and input accessions.

### Industry applicability is enforced, not advisory

`industry/sic_buckets.py` maps SIC codes to buckets (`banking`, `insurance`,
`other_financial`, `real_estate`, `utilities`, plus non-financial buckets).
Every signal definition lists applicable buckets (or excludes some). The engine
returns `NOT_APPLICABLE` — the UI renders "n/a", never a bogus number. Banks get
bank signals (deposits trend, credit-loss allowance; NIM/CET1 are declared
placeholders), and do not get current ratio or inventory-style margins.

### Databases

SQLite via SQLModel today. All access goes through `storage/db.py`; the engine is
built from a URL in config, so DuckDB/Postgres later is a connection-string change
plus a migration story — no ORM rewrite.

### AI boundaries (future)

`ai/interfaces.py` defines `TextSummarizer`, `RiskExtractor`,
`FilingQuestionAnswerer`, `EvidenceClassifier` as Protocols. Today's
implementations are no-op/rule-based and the app never requires them. When Ollama
lands (Phase 6): AI only summarizes/classifies retrieved evidence, always cites
chunk IDs, and can be disabled without losing core functionality.

## Data model

Tables (see `storage/models.py`; all carry provenance fields — source, source URL
or accession, retrieved timestamp, and period/filed dates where applicable):

- `Company` — identity: CIK, name, SIC + description, industry bucket, addresses
- `SecurityIdentifier` — ticker/exchange rows per company (schema anticipates
  historical validity ranges; today holds current SEC mappings)
- `Filing` — one row per accession: form, filed/accepted dates, period, URLs
- `FilingDocument` — documents within a filing (primary doc first)
- `FilingSection` — extracted text chunks (section name, chunk id, char offsets, parser version)
- `CompanyFact` — selected raw XBRL facts (taxonomy, tag, unit, value, period, accession, filed)
- `FinancialMetric` — canonical derived metrics per period with formula + inputs
- `SignalDefinitionRow` — snapshot of the code-registered signal definitions (audit)
- `SignalResult` — one row per signal per report run, incl. status/direction/confidence/caveat
- `EvidenceReference` — links signal results to facts, filings, or sections
- `ReportRun` — one row per generated report: when, versions, output path
- `UserNote` — placeholder for Phase 6+ user annotations

## Request path examples

**`stock-helper fetch-sec KEY`**
1. `connectors.sec` resolves KEY → CIK via cached `company_tickers.json`
2. Pulls `submissions/CIK…json` and `api/xbrl/companyfacts/CIK…json` (cached, throttled)
3. `ingestion.sec_ingest` upserts Company (+ SIC → bucket), SecurityIdentifier,
   recent Filings, and selected CompanyFacts

**`stock-helper build-report KEY`**
1. `normalization.facts` builds canonical annual series from CompanyFacts
2. `features.metrics` computes derived metrics → FinancialMetric rows
3. `signals.engine` evaluates the registry with KEY's industry bucket → SignalResults + Evidence
4. `reports.tearsheet` assembles the report object, renders Markdown, records ReportRun

## Testing strategy

All tests run offline. HTTP is faked with `httpx.MockTransport`; SEC payloads are
small fixtures under `tests/fixtures/`. Covered: ticker/CIK lookup, request
wrapper + caching, facts normalization, filing metadata ingestion, metric math,
signal rules, industry applicability, and section extraction heuristics.
