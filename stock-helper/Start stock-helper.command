#!/usr/bin/env bash
# =====================================================================
#  Double-click launcher for the stock-helper Streamlit UI (macOS/Linux).
#  Prefers `uv`; falls back to a plain-Python venv if uv is missing, so it
#  works even if you have never used the terminal. Runs from this file's
#  directory so it works from Finder.
# =====================================================================
set -euo pipefail
cd "$(dirname "$0")" || exit 1

# first-run: make sure a .env exists so SEC_USER_AGENT can be set.
if [[ ! -f .env && -f .env.example ]]; then
  cp .env.example .env
  echo "Created .env from .env.example."
  echo "IMPORTANT: edit .env and set SEC_USER_AGENT to your name + email before"
  echo "fetching SEC data (SEC fair-access rules require it)."
  echo
fi

# path 1: uv is available -> use it.
if command -v uv >/dev/null 2>&1; then
  echo "Using uv..."
  exec uv run stock-helper-ui
fi

echo "uv is not installed. Falling back to a plain-Python virtual environment."
echo "(For the faster uv path, install it: https://docs.astral.sh/uv/ )"
echo

# locate a Python 3 interpreter.
PY=""
if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else
  echo "ERROR: Python 3 was not found. Install Python 3.11+ from"
  echo "https://www.python.org/downloads/ and double-click this file again."
  read -r -p "Press Return to close..." _ || true
  exit 1
fi

# first-run: create the venv and install the app.
if [[ ! -x .venv/bin/python ]]; then
  echo "Creating virtual environment in .venv (one-time, ~1-2 min)..."
  "$PY" -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  echo "Installing stock-helper and dependencies..."
  python -m pip install --upgrade pip >/dev/null
  python -m pip install -e ".[dev]"
else
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "Launching the UI..."
exec stock-helper-ui
