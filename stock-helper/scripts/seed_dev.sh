#!/usr/bin/env bash
# Fetch the development seed tickers and build a report for each.
# Run from the stock-helper directory after `uv sync` and configuring .env.
set -euo pipefail
cd "$(dirname "$0")/.."

TICKERS=(AAPL MSFT JPM KEY NVDA COST)

uv run stock-helper init
for ticker in "${TICKERS[@]}"; do
  uv run stock-helper fetch-sec "$ticker"
  uv run stock-helper build-report "$ticker"
done

echo
echo "Seed complete. Launch the UI with: uv run stock-helper run-ui"
