#!/usr/bin/env bash
#
# One-step SATC install (macOS / Linux).
#
# Creates a private virtual environment next to this file and installs SATC with
# everything for the fully-local experience (GUI + PDF reading + OCR). Nothing is
# sent anywhere. After this finishes, double-click SATC.command (mac) / run
# ./SATC.sh to start.
#
set -e
cd "$(dirname "$0")"

echo ""
echo "  Installing SATC (this stays entirely on your computer)…"
echo ""

PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
  echo "  ✗ Python 3 is not installed. Install it from https://www.python.org/downloads/ and re-run."
  exit 1
fi

"$PY" -m venv .venv
# shellcheck disable=SC1091
. .venv/bin/activate
python -m pip install --upgrade pip >/dev/null
pip install -e ".[local]"

echo ""
if command -v tesseract >/dev/null 2>&1; then
  echo "  ✓ Local OCR (Tesseract) is installed — scanned docs will be read on this machine."
else
  echo "  • Optional: install Tesseract to read scans locally:"
  echo "      mac:    brew install tesseract"
  echo "      Ubuntu: sudo apt-get install tesseract-ocr"
fi

echo ""
echo "  ✓ Installed.  Start SATC by running:   ./SATC.sh        (or double-click SATC.command on a Mac)"
echo ""
.venv/bin/satc doctor || true
