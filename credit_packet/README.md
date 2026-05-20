# credit_packet

Build a source-linked public-company credit research packet from SEC filings.

## Quick start
1. `python bootstrap.py`
2. Edit `.env` and set `SEC_USER_AGENT`
3. Run sample packet build:
   - Mac/Linux: `.venv/bin/python run_sample.py`
   - Windows: `.venv\Scripts\python.exe run_sample.py`

## What this tool does
- Pulls SEC submissions and company facts.
- Builds annual financial trends and calculated metrics.
- Applies deterministic watchlist rules.
- Extracts filing-language excerpts and change candidates.
- Produces a Markdown packet for manual credit review.

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
- No activation path:
  - Mac/Linux: `.venv/bin/python -m pytest -q`
  - Windows: `.venv\Scripts\python.exe -m pytest -q`

## Build a packet for another ticker
- No activation path:
  - Mac/Linux: `.venv/bin/python -m credit_packet.cli build --ticker MSFT --years 3 --output outputs/msft_packet.md`
  - Windows: `.venv\Scripts\python.exe -m credit_packet.cli build --ticker MSFT --years 3 --output outputs/msft_packet.md`
- Optional (if venv is activated):
  - `credit-packet build --ticker MSFT --years 3 --output outputs/msft_packet.md`

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
