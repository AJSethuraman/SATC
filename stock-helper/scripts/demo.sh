#!/usr/bin/env bash
# Zero-network demo: seed a synthetic multi-sector universe and open the UI.
# No SEC/Stooq/FRED access needed — every company is invented to show the engine.
set -euo pipefail
cd "$(dirname "$0")/.."
export DATA_DIR="${DATA_DIR:-demo_data}"
export ENABLE_PRICE_DATA=true
export SEC_USER_AGENT="${SEC_USER_AGENT:-demo (demo@example.com)}"
echo "Seeding synthetic demo universe into $DATA_DIR ..."
uv run python scripts/demo_seed.py
echo "Launching UI (synthetic DEMO data — not real) ..."
uv run stock-helper run-ui
