#!/usr/bin/env bash
#
# One-command setup + launch for the EDGAR Industry Assumption-Set Tool.
#
#   ./run.sh                                   # first run: sets up, then self-test
#   ./run.sh --sic 5140 --years 7 --out food_dist
#
# Creates a local virtualenv, installs the package once, resolves the
# SEC-required contact email, and launches the tool. Re-runs are instant.
#
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
VENV=".venv"

# 1. Virtualenv + install (idempotent: only does work on first run).
if [ ! -d "$VENV" ]; then
  echo ">> Creating virtual environment in $VENV ..."
  "$PY" -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"

# Use an install marker (not an import check): running from the project dir
# puts it on sys.path, so `import satc_edgar` would falsely pass uninstalled.
if [ ! -f "$VENV/.installed" ]; then
  echo ">> Installing the tool and its (test) dependencies ..."
  pip install --quiet --upgrade pip
  pip install --quiet -e ".[test]"
  touch "$VENV/.installed"
fi

# 2. Resolve the SEC-required contact (User-Agent). SEC rejects requests
#    without a real contact. Precedence:
#      explicit --user-agent arg  >  $EDGAR_USER_AGENT  >  saved .edgar_contact
#      >  interactive prompt (saved for next time).
have_ua=false
for a in "$@"; do
  if [ "$a" = "--user-agent" ]; then have_ua=true; break; fi
done

UA_ARGS=()
if [ "$have_ua" = false ]; then
  if [ -n "${EDGAR_USER_AGENT:-}" ]; then
    UA="$EDGAR_USER_AGENT"
  elif [ -f ".edgar_contact" ]; then
    UA="$(cat .edgar_contact)"
  else
    echo
    echo "SEC EDGAR requires a contact email in every request's User-Agent."
    read -r -p ">> Enter your contact email: " EMAIL
    UA="SATC EDGAR assumption tool ${EMAIL}"
    printf '%s' "$UA" > .edgar_contact
    echo ">> Saved to .edgar_contact (reused automatically next time)."
  fi
  UA_ARGS=(--user-agent "$UA")
fi

# 3. Launch. With no arguments, run a safe end-to-end self-test.
if [ "$#" -eq 0 ]; then
  echo
  echo ">> No arguments given — running --self-test to verify the pipeline."
  echo ">> For a real run, e.g.:  ./run.sh --sic 5140 --years 7 --out food_dist"
  echo
  exec python edgar_assumptions.py --self-test ${UA_ARGS[@]+"${UA_ARGS[@]}"}
fi

exec python edgar_assumptions.py "$@" ${UA_ARGS[@]+"${UA_ARGS[@]}"}
