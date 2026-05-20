# Credit Packet

Decision-support credit research packet builder (not an AI analyst). It does **not** produce credit ratings or investment recommendations.

## Philosophy
- Deterministic Python calculations and threshold checks.
- Configurable rule-based watchlist flags.
- Optional source-bound LLM formatting only.
- Human performs final credit judgment.

## Setup
1. Python 3.11+
2. Copy `.env.example` to `.env` and set `SEC_USER_AGENT`.
3. Install: `pip install -e .[dev]`

## Usage
Generate packet:
`python -m credit_packet.cli build --ticker AAPL --years 3 --output outputs/aapl_packet.md`

Run tests:
`pytest`

## Limitations
- SEC XBRL tag consistency differs across companies.
- Excerpt extraction and filing-change detection are deterministic and conservative for manual review.
- LLM mode is optional; with `LLM_PROVIDER=none`, deterministic fallbacks are used.
