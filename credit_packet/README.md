# credit_packet

Local-first public-company credit research **packet builder** using SEC EDGAR JSON + filing documents.

## Purpose
Decision-support workflow for human credit review. This tool does **not** assign credit ratings, recommend approval/decline, or provide investment recommendations.

## Philosophy
- SEC APIs + filing documents are the source of truth.
- Python performs parsing, normalization, calculations, comparisons, and rules.
- Rules engine creates deterministic watchlist flags.
- LLM is optional and source-bound for formatting only.
- Manual review is required for final judgment.

## Setup
1. Python 3.11+
2. Set environment variable:
   - `SEC_USER_AGENT="Your Name your.email@example.com"`
3. Optional LLM:
   - `LLM_PROVIDER=none|ollama`
   - `OLLAMA_BASE_URL=http://localhost:11434`
   - `OLLAMA_MODEL=llama3.1`

## CLI Usage
```bash
python -m credit_packet.cli build --ticker AAPL --years 3 --output outputs/aapl_packet.md
```

## No-LLM mode
Default is `LLM_PROVIDER=none`. Packet generation remains complete and deterministic.

## Testing
```bash
PYTHONPATH=src pytest -q
```

## Troubleshooting
- Missing `SEC_USER_AGENT`: configure it before running.
- SEC network unavailable: retry later; cache lives at `.cache/sec`.
- LLM endpoint unavailable: build continues in deterministic fallback mode.

## Limitations
- XBRL tag conventions differ by issuer; fallback tags are used but missing data may remain unavailable.
- Section extraction is heuristic and may fall back to full-text matching.
