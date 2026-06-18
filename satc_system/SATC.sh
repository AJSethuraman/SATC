#!/usr/bin/env bash
# Start SATC (Linux/macOS). Opens the app in your browser.
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "SATC isn't installed yet — running the installer first…"
  bash ./install.sh
fi
# shellcheck disable=SC1091
. .venv/bin/activate
exec satc app
