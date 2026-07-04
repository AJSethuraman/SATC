#!/usr/bin/env bash
# Lint + test, the same checks CI should run.
set -euo pipefail
cd "$(dirname "$0")/.."
uv run ruff check .
uv run pytest
