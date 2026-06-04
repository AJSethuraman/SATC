#!/usr/bin/env bash
# One-command launch for Linesheet Builder (macOS / Linux).
# Creates a virtualenv + installs deps on first run, then starts the app.
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
VENV=".venv"

if [ ! -d "$VENV" ]; then
  echo "Creating virtual environment in $VENV ..."
  "$PYTHON" -m venv "$VENV"
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

# Install/refresh dependencies only when requirements change.
if [ ! -f "$VENV/.deps-installed" ] || [ requirements.txt -nt "$VENV/.deps-installed" ]; then
  echo "Installing dependencies ..."
  python -m pip install --quiet --upgrade pip
  python -m pip install --quiet -r requirements.txt
  touch "$VENV/.deps-installed"
fi

echo "Starting Linesheet Builder at http://localhost:8501  (press Ctrl+C to stop)"
exec streamlit run app.py
