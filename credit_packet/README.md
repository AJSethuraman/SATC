# credit_packet

Build a source-linked public-company credit research packet from SEC filings.

## Quick start
1. `python bootstrap.py`
2. Edit `.env` and set `SEC_USER_AGENT`
3. Run sample packet build:
   - Mac/Linux: `.venv/bin/python run_sample.py`
   - Windows: `.venv\Scripts\python.exe run_sample.py`

## Excel output (preferred)
Build Excel workbook:
- Mac/Linux:
  - `.venv/bin/python -m credit_packet.cli build --ticker AAPL --years 3 --output outputs/aapl_packet.xlsx`
- Windows:
  - `.venv\Scripts\python.exe -m credit_packet.cli build --ticker AAPL --years 3 --output outputs/aapl_packet.xlsx`

Markdown is still available for plain text review:
- `.venv/bin/python -m credit_packet.cli build --ticker AAPL --years 3 --output outputs/aapl_packet.md`

## What this tool does
- Pulls SEC submissions and company facts.
- Builds annual financial trends and calculated metrics.
- Applies deterministic watchlist rules.
- Extracts filing-language excerpts and change candidates.
- Produces Markdown and Excel packets for manual credit review.

## What this tool does not do
- No automated credit rating.
- No approval/decline recommendation.
- No investment recommendation.
- Final decision remains human.

## SEC_USER_AGENT requirement
SEC requires an identifying user-agent for requests.
Set in `.env`:

`SEC_USER_AGENT="Your Name your.email@example.com"`

## Run tests
- `python -m pytest -q`

## Build for another ticker
- `.venv/bin/python -m credit_packet.cli build --ticker MSFT --years 3 --output outputs/msft_packet.xlsx`
- Optional (if venv is activated):
  - `credit-packet build --ticker MSFT --years 3 --output outputs/msft_packet.xlsx`

## LLM modes
- Default: `LLM_PROVIDER=none` (fully deterministic no-LLM mode).
- Optional local Ollama:
  - `LLM_PROVIDER=ollama`
  - `OLLAMA_BASE_URL=http://localhost:11434`
  - `OLLAMA_MODEL=llama3.1`

## Paths
- Output packets: `outputs/`
- SEC cache: `.cache/sec/`
- Example output: `examples/sample_packet.md`

Manual review required. No automated credit conclusion generated.


## Source-Bound Local LLM Mode
- Default mode: `LLM_PROVIDER=none` (fully deterministic).
- Optional local Ollama mode:
  - Starter for 8GB GPU: `OLLAMA_MODEL=llama3.2:3b`
  - Better quality option: `OLLAMA_MODEL=llama3.1:8b`
- The LLM receives only the structured evidence bundle (company, filings, metrics, flags, excerpts, changes, audit).
- The LLM must cite evidence IDs for substantive points and may not make recommendations/ratings.
- If LLM output is malformed, unsafe, unsupported, or invalid, the system falls back to deterministic summaries.


## Analyst Workbook Output
- `.xlsx` is the preferred review artifact for analysts.
- `.md` remains available for plain text review and automation.
- Workbook includes: Summary, Filing Activity, Financial Trends, Calculated Metrics, Watchlist Flags, Source-Bound Brief, Excerpts, Filing Changes, Review Questions, Memo Shell, Evidence Index, and Sources & Audit.
- Source-Bound Brief shows generation mode and validation status (including deterministic fallback).
- Evidence Index provides source ID traceability.
- Sources & Audit includes run metadata, source documents, field audit tags, and data-quality notes.
- Manual review is required; no automated credit conclusion is produced.
