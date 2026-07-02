# stock-helper

A **local-first stock research helper** that digests SEC filings, XBRL company facts,
and industry context into **evidence-backed signal reports**.

This is *not* a buy/sell bot. It is a grounded research assistant: every signal traces
back to a source document, an accession number, or a calculation over disclosed facts —
with a confidence level and a caveat attached. See [DISCLAIMER.md](DISCLAIMER.md).

> **Core principle:** build the boring, correct, auditable data spine first.
> Then layer scoring. Then layer AI.

## What works today (v0.1 — Phase 0 + thin Phase 1)

- **Install locally** with `uv` (or plain `pip`). One command to initialize.
- **Fetch SEC data** for a ticker: CIK lookup, company submissions (filing history),
  and XBRL company facts, cached on disk and stored in SQLite with full provenance
  (source URL, accession, filed date, retrieved timestamp, parser version).
- **Normalize XBRL facts** into a canonical metric library (revenue, margins, cash
  flow, leverage, share counts, and best-effort banking metrics like deposits and
  credit-loss allowance).
- **Industry awareness from day one**: SIC codes map to industry buckets, and each
  signal declares which buckets it applies to. Banks do not get industrial ratios;
  they get "not applicable" plus bank-specific placeholders.
- **Rule-based signal scorecard**: quality, profitability, growth, cash flow,
  leverage/liquidity, dilution — each result shows metric, value, direction,
  interpretation, source, confidence, and caveat. Missing data is marked
  *unavailable*, never silently zero-filled.
- **Clean Streamlit UI**: Dashboard, Company Tear Sheet, Filing Evidence, Signal
  Scorecard.
- **Markdown tear-sheet reports** generated per ticker per run, stored under
  `data/reports/` and recorded as `ReportRun` rows for auditability.
- **FastAPI layer** exposing companies, metrics, signals, and reports as JSON.
- **Optional price charts** from Stooq (clearly labeled non-canonical; off by default).
- **Best-effort filing section extraction** (MD&A / Risk Factors) from the latest
  10-K/10-Q primary document — an early slice of Phase 2, heuristic and clearly
  labeled as such.
- **Point-in-time replay**: `build-report --as-of`, a UI toggle, and
  `signal-history` rebuild everything as it was knowable on a past date —
  facts filed later are excluded and originally-filed values win over
  restatements. This is the calibration foundation for Phase 7; outcome labels
  (`--with-outcomes`) are exploratory, cost-free, non-canonical, and carry no
  performance claim.

- **Searchable filing text**: 8-K item extraction, SQLite FTS5 full-text search
  over all extracted sections (search box in the UI).
- **Disclosure-language signal**: rule-based word rates (negative / uncertainty /
  litigious / constraining) and risk-factor novelty vs the prior 10-K —
  low-confidence by design, always citing source chunks.
- **Local peer context**: percentile of key metrics vs same-bucket companies in
  your own database, with n and tickers always shown (explicitly not the market).
- **Bank metric library v1**: NIM proxy, nonaccrual loans, charge-offs from face
  XBRL where tagged; honest `UNAVAILABLE` when disclosure is table-only.
- **Market context signals** (gated by `ENABLE_PRICE_DATA`): trailing P/E and
  P/S (deliberately unscored) and 12-1 momentum + volatility, all labeled
  non-canonical.
- **Rule-based risk highlights**: top risk sentences *selected* (never generated)
  from risk-factor chunks with chunk-id citations — the permanent "AI disabled"
  mode of the Phase 6 interfaces.

## What is intentionally NOT built yet

See [ROADMAP.md](ROADMAP.md) for the full plan. Deliberately deferred:

- Footnote extraction and robust section boundaries across all filer formats (Phase 2).
- Market-wide peer distributions — today's percentiles use only your locally
  fetched universe (Phase 4).
- CET1 and table-only bank metrics (need filing-table parsing, Phase 4).
- FRED/ALFRED macro layer and benchmark-relative context (Phase 5).
- Any model-based AI (Phase 6 — interfaces + rule-based fallbacks exist; nothing
  calls an LLM).
- Backtesting, hit rates, or any performance claim (Phase 7 — until then the app
  makes **no predictive claims whatsoever**; the `signal-history --with-outcomes`
  table is a sanity check, not validation).

## Quick start

```bash
cd stock-helper
uv sync --extra dev                     # or: pip install -e ".[dev]"
cp .env.example .env                    # then edit SEC_USER_AGENT (required)
uv run stock-helper init                # create the SQLite database
uv run stock-helper fetch-sec AAPL      # pull SEC submissions + company facts
uv run stock-helper fetch-sec KEY       # a bank, to see industry-aware behavior
uv run stock-helper build-report AAPL   # compute metrics + signals, write Markdown
uv run stock-helper run-ui              # open the Streamlit UI
```

Full instructions, including plain-pip and troubleshooting: [INSTALL.md](INSTALL.md).

## CLI

| Command | What it does |
|---|---|
| `stock-helper init` | Create data folders and initialize the SQLite database |
| `stock-helper fetch-sec TICKER` | Fetch submissions + company facts for a ticker; `--with-documents` also downloads the latest 10-K/10-Q primary document and extracts sections (best-effort) |
| `stock-helper build-report TICKER` | Normalize facts, compute metrics and signals, write a Markdown tear sheet; `--as-of YYYY-MM-DD` builds the point-in-time view (only facts/filings filed by that date, originally-filed values instead of restatements) |
| `stock-helper signal-history TICKER` | Replay the scorecard at each past 10-K/10-Q filing date and store the results; `--with-outcomes` joins exploratory forward returns from the non-canonical price source (not a backtest) |
| `stock-helper run-ui` | Launch the Streamlit UI |
| `stock-helper run-api` | Launch the FastAPI server |
| `stock-helper info TICKER` | Print a quick company summary to the terminal |

Development seed tickers: `AAPL MSFT JPM KEY NVDA COST` (see `scripts/seed_dev.sh`).

## Documentation map

| File | Contents |
|---|---|
| [INSTALL.md](INSTALL.md) | Install, configure, run, troubleshoot |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Layered architecture, data flow, key decisions |
| [DATA_SOURCES.md](DATA_SOURCES.md) | Every data source: endpoint, role, limits, caveats |
| [SIGNAL_DEFINITIONS.md](SIGNAL_DEFINITIONS.md) | Every signal: formula, applicability, interpretation, caveats |
| [ROADMAP.md](ROADMAP.md) | Phases 0–8 with scope and rationale |
| [DISCLAIMER.md](DISCLAIMER.md) | Not investment advice; how to read the outputs |

## Design commitments

1. **Point-in-time thinking.** Facts carry both their fiscal `period_end` and the
   `filed`/`accepted` date. Data only "exists" from the moment it was filed. The
   schema is built so a future backtester can replay what was knowable when.
2. **Provenance everywhere.** Every stored object records source, source URL or
   accession, retrieval timestamp, and parser version where practical.
3. **Honest gaps.** A metric that cannot be computed is shown as *unavailable* with
   the reason. A metric that does not apply to an industry is shown as
   *not applicable* — never forced.
4. **No advice.** Outputs are research aids. Language is "evidence suggests",
   never "this will go up". No predictive accuracy is implied anywhere, because
   nothing has been backtested yet.

## Development

```bash
uv run pytest          # tests run fully offline against fixtures
uv run ruff check .    # lint
```

## License / data usage

SEC EDGAR data is public. This tool respects SEC fair-access guidance: a declared
User-Agent (configured via `.env`), request rate limiting (≤10 req/s, we default far
below), and on-disk caching to avoid repeat pulls.
