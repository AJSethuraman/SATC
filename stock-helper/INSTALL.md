# Installing stock-helper

## Easiest path — no terminal needed

1. Install **Python 3.11+** from <https://www.python.org/downloads/>. On Windows,
   tick **"Add python.exe to PATH"** in the installer.
2. Double-click **`Start stock-helper.command`** (macOS/Linux) or
   **`Start stock-helper.bat`** (Windows).

That launcher is self-bootstrapping: it uses [`uv`](https://docs.astral.sh/uv/)
if you have it, otherwise it creates a local virtual environment and installs
everything the first time (~1–2 min), copies `.env` from `.env.example`, and
opens the UI. If Python is missing it tells you exactly what to install. **You do
not need `uv` and you do not need to touch the terminal.**

On first run, open the freshly-created **`.env`** and set `SEC_USER_AGENT` to your
name + email (SEC fair-access rules require it) before fetching data.

The manual steps below are for people who prefer the command line.

## Prerequisites (manual path)

- Python **3.11+**
- [`uv`](https://docs.astral.sh/uv/) (recommended) or plain `pip`
- Internet access to `data.sec.gov` / `www.sec.gov` (and optionally `stooq.com`
  for prices and `fred.stlouisfed.org` for the risk-free rate)

> **Running on Claude Code on the web?** The default sandbox blocks outbound
> access to SEC/Stooq/FRED (you'll see `403` at the proxy), so live fetches fail
> there — the tool is meant to run on your own machine. To fetch inside a web
> environment instead, recreate it with a network policy that allows these hosts:
> `data.sec.gov`, `www.sec.gov`, `stooq.com`, `fred.stlouisfed.org`.

## 1. Install dependencies

With `uv` (recommended):

```bash
cd stock-helper
uv sync --extra dev
```

With plain pip:

```bash
cd stock-helper
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

`uv run <cmd>` prefixes below are unnecessary if you activated a venv.

## 2. Configure

```bash
cp .env.example .env
```

Edit `.env` and set **`SEC_USER_AGENT`**. This is required: SEC fair-access rules
expect a User-Agent identifying you and a contact address, e.g.

```
SEC_USER_AGENT="Jane Doe research (jane@example.com)"
```

The app refuses to call SEC endpoints with the placeholder value.

Optional settings (see `.env.example` for all):

- `ENABLE_PRICE_DATA=true` — enables the non-canonical Stooq daily price connector
  used only for context charts.
- `STOCK_HELPER_DB_URL` — override the default SQLite location.

## 3. Initialize

```bash
uv run stock-helper init
```

Creates `data/` subfolders and the SQLite database with all tables.

## 4. Fetch data and build a report

```bash
uv run stock-helper fetch-sec AAPL
uv run stock-helper fetch-sec KEY
uv run stock-helper build-report AAPL
```

`fetch-sec` pulls the SEC ticker→CIK map (cached), company submissions, and XBRL
company facts. Raw JSON responses are cached under `data/raw/sec/`. Add
`--with-documents` to also download the latest 10-K/10-Q primary document and run
best-effort section extraction (MD&A, Risk Factors).

`build-report` writes a Markdown tear sheet to `data/reports/` and prints its path.

## 5. Launch the UI

```bash
uv run stock-helper run-ui
```

Opens Streamlit (default http://localhost:8501). The API server is separate:

```bash
uv run stock-helper run-api   # default http://localhost:8000, docs at /docs
```

## Seeding all development tickers

```bash
./scripts/seed_dev.sh         # fetches AAPL MSFT JPM KEY NVDA COST + reports
```

## Running tests and lint

```bash
uv run pytest       # offline; uses fixtures under tests/fixtures/
uv run ruff check .
```

## Troubleshooting

- **`SEC_USER_AGENT is not configured`** — edit `.env`; the placeholder value from
  `.env.example` is intentionally rejected.
- **HTTP 403/429 from SEC** — you are being rate limited or your User-Agent is
  missing/generic. The client already throttles below SEC's 10 req/s guidance;
  wait a minute and retry. Cached responses under `data/raw/sec/` are reused for
  `SEC_CACHE_TTL_HOURS` (default 24), so repeat commands do not re-hit SEC.
- **Ticker not found** — the SEC ticker map covers U.S. EDGAR filers; check the
  symbol, or delete `data/raw/sec/company_tickers*` to force a refresh.
- **Empty metrics for a company** — some filers use custom XBRL tags this early
  version does not map. The report will say exactly which canonical metrics were
  unavailable; this is expected behavior, not a crash.
